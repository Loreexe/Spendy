from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from .investments import (
    create_operation,
    recalculate_position,
    set_position_archived,
    update_operation,
)
from .models import (
    ZERO,
    Account,
    AutomationExecution,
    Category,
    InvestmentOperation,
    InvestmentPosition,
    Line,
    Notification,
    Profile,
    SavingsAccount,
    Automation,
    Tag,
    Transaction,
    match_category,
    resolve_tags,
)
from .services import assert_accounts_non_negative, savings_balance


def money(value: Decimal) -> str:
    return f"{value:.2f}"


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ("id", "display_name", "theme", "created_at")


class AccountSerializer(serializers.ModelSerializer):
    balance = serializers.SerializerMethodField()
    type_label = serializers.CharField(source="get_type_display", read_only=True)

    class Meta:
        model = Account
        fields = (
            "id",
            "name",
            "type",
            "type_label",
            "initial_balance",
            "currency",
            "archived",
            "balance",
            "created_at",
            "updated_at",
        )

    def get_balance(self, obj: Account) -> str:
        return money(obj.balance)


class AccountCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ("name", "type", "initial_balance")

    def validate_initial_balance(self, value: Decimal) -> Decimal:
        if value < ZERO:
            raise serializers.ValidationError(
                "Il saldo iniziale non può essere negativo."
            )
        return value

    def create(self, validated_data):
        profile = self.context["profile"]
        initial_balance = validated_data.get("initial_balance", ZERO)
        with transaction.atomic():
            account = Account.objects.create(profile=profile, **validated_data)
            if initial_balance != ZERO:
                opening = Transaction.objects.create(
                    profile=profile,
                    kind=Transaction.Kind.OPENING,
                    date=timezone.localdate(),
                    description="Saldo iniziale",
                    amount=abs(initial_balance),
                )
                Line.objects.create(
                    transaction=opening,
                    account=account,
                    amount=initial_balance,
                    role=Line.Role.PRINCIPAL,
                )
        return account


class AccountUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ("name", "type", "archived")


class SavingsAccountSerializer(serializers.ModelSerializer):
    backing_account_name = serializers.CharField(
        source="backing_account.name", read_only=True
    )
    balance = serializers.SerializerMethodField()

    class Meta:
        model = SavingsAccount
        fields = (
            "id",
            "name",
            "backing_account",
            "backing_account_name",
            "balance",
            "created_at",
            "updated_at",
        )

    def get_balance(self, obj: SavingsAccount) -> str:
        return money(obj.balance)


class SavingsAccountCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavingsAccount
        fields = ("name", "backing_account")

    def validate_backing_account(self, account: Account) -> Account:
        profile = self.context["profile"]
        if account.profile_id != profile.id:
            raise serializers.ValidationError("Il conto non appartiene al profilo.")
        if account.archived:
            raise serializers.ValidationError("Il conto di appoggio è archiviato.")
        return account

    def create(self, validated_data):
        validated_data["profile"] = self.context["profile"]
        return SavingsAccount.objects.create(**validated_data)


class SavingsAccountUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavingsAccount
        fields = ("name",)


class AutomationSerializer(serializers.ModelSerializer):
    savings_name = serializers.SerializerMethodField()
    source_account_name = serializers.SerializerMethodField()
    kind_label = serializers.CharField(source="get_kind_display", read_only=True)
    interval_label = serializers.CharField(read_only=True)
    interval_unit_label = serializers.CharField(
        source="get_interval_unit_display", read_only=True
    )
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    pending_count = serializers.SerializerMethodField()

    class Meta:
        model = Automation
        fields = (
            "id",
            "kind",
            "kind_label",
            "savings",
            "savings_name",
            "source_account",
            "source_account_name",
            "amount",
            "description",
            "interval_count",
            "interval_unit",
            "interval_unit_label",
            "interval_label",
            "anchor_day",
            "advance_notice_days",
            "next_run_on",
            "status",
            "status_label",
            "pending_count",
            "created_at",
            "updated_at",
        )

    def get_savings_name(self, obj: Automation):
        return obj.savings.name if obj.savings_id else None

    def get_source_account_name(self, obj: Automation):
        return obj.source_account.name if obj.source_account_id else None

    def get_pending_count(self, obj: Automation) -> int:
        return obj.executions.filter(
            status=AutomationExecution.Status.PENDING
        ).count()


class AutomationWriteSerializer(serializers.ModelSerializer):
    amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal("0.01")
    )
    savings = serializers.PrimaryKeyRelatedField(
        queryset=SavingsAccount.objects.all(), required=False, allow_null=True
    )
    source_account = serializers.PrimaryKeyRelatedField(
        queryset=Account.objects.all(), required=True
    )
    interval_count = serializers.IntegerField(min_value=1, max_value=999)
    advance_notice_days = serializers.IntegerField(
        min_value=0, max_value=30, required=False
    )

    class Meta:
        model = Automation
        fields = (
            "kind",
            "savings",
            "source_account",
            "amount",
            "description",
            "interval_count",
            "interval_unit",
            "advance_notice_days",
            "next_run_on",
            "status",
        )

    def _check_owner(self, obj, label: str):
        profile = self.context["profile"]
        if obj is not None and obj.profile_id != profile.id:
            raise serializers.ValidationError(
                {label: "L'elemento non appartiene al profilo."}
            )

    def validate_savings(self, savings: SavingsAccount | None) -> SavingsAccount | None:
        if savings is not None:
            self._check_owner(savings, "savings")
        return savings

    def validate_source_account(self, account: Account) -> Account:
        self._check_owner(account, "source_account")
        if account.archived:
            raise serializers.ValidationError(
                {"source_account": "Il conto di partenza è archiviato."}
            )
        return account

    def validate_status(self, value: str) -> str:
        if value == Automation.Status.SUSPENDED:
            raise serializers.ValidationError(
                {
                    "status": (
                        "La sospensione è decisa dal sistema dopo i tentativi "
                        "falliti. Usa «In pausa» o «Attiva»."
                    )
                }
            )
        return value

    def validate(self, attrs):
        kind = attrs.get(
            "kind", getattr(self.instance, "kind", Automation.Kind.TRANSFER)
        )
        savings = attrs.get(
            "savings", getattr(self.instance, "savings", None)
        )
        description = attrs.get(
            "description", getattr(self.instance, "description", "")
        )

        if self.instance is not None and "kind" in attrs:
            if attrs["kind"] != self.instance.kind:
                raise serializers.ValidationError(
                    {
                        "kind": (
                            "Il tipo di automazione non è modificabile dopo "
                            "la creazione."
                        )
                    }
                )

        if kind == Automation.Kind.EXPENSE:
            if savings is not None:
                raise serializers.ValidationError(
                    {"savings": "Una spesa ricorrente non usa un salvadanaio."}
                )
            if not (description or "").strip():
                raise serializers.ValidationError(
                    {"description": "Indica la descrizione della spesa."}
                )
        else:
            if savings is None:
                raise serializers.ValidationError(
                    {"savings": "Indica il salvadanaio di destinazione."}
                )

        next_run_on = attrs.get(
            "next_run_on", getattr(self.instance, "next_run_on", None)
        )
        if (
            self.instance is None
            or "next_run_on" in attrs
            or "interval_unit" in attrs
        ):
            if next_run_on is not None:
                attrs["anchor_day"] = next_run_on.day
        return attrs

    def create(self, validated_data):
        validated_data["profile"] = self.context["profile"]
        return Automation.objects.create(**validated_data)


class AutomationExecutionSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    failure_label = serializers.CharField(
        source="get_failure_code_display", read_only=True
    )
    amount = serializers.SerializerMethodField()

    class Meta:
        model = AutomationExecution
        fields = (
            "id",
            "automation",
            "automation_ref",
            "automation_name",
            "kind",
            "description",
            "scheduled_date",
            "amount",
            "source_account",
            "source_account_name",
            "savings",
            "savings_name",
            "status",
            "status_label",
            "attempts",
            "next_retry_at",
            "failure_code",
            "failure_label",
            "failure_message",
            "corrected",
            "transaction",
            "created_at",
            "updated_at",
        )

    def get_amount(self, obj: AutomationExecution) -> str:
        return money(obj.amount)


class NotificationSerializer(serializers.ModelSerializer):
    kind_label = serializers.CharField(source="get_kind_display", read_only=True)
    is_read = serializers.BooleanField(read_only=True)

    class Meta:
        model = Notification
        fields = (
            "id",
            "kind",
            "kind_label",
            "message",
            "automation",
            "execution",
            "occurrence_date",
            "alert_date",
            "read_at",
            "is_read",
            "created_at",
        )


class LineSerializer(serializers.ModelSerializer):
    target_type = serializers.SerializerMethodField()
    account_name = serializers.SerializerMethodField()
    savings_name = serializers.SerializerMethodField()
    amount = serializers.SerializerMethodField()

    class Meta:
        model = Line
        fields = (
            "id",
            "target_type",
            "account",
            "account_name",
            "savings",
            "savings_name",
            "amount",
            "role",
        )

    def get_target_type(self, obj: Line) -> str:
        return "account" if obj.account_id else "savings"

    def get_account_name(self, obj: Line):
        return obj.account.name if obj.account_id else None

    def get_savings_name(self, obj: Line):
        return obj.savings.name if obj.savings_id else None

    def get_amount(self, obj: Line) -> str:
        return money(obj.amount)


class TransactionSerializer(serializers.ModelSerializer):
    lines = LineSerializer(many=True, read_only=True)
    kind_label = serializers.CharField(source="get_kind_display", read_only=True)
    amount = serializers.SerializerMethodField()
    automation_name = serializers.SerializerMethodField()
    category = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()

    class Meta:
        model = Transaction
        fields = (
            "id",
            "kind",
            "kind_label",
            "date",
            "description",
            "amount",
            "automation",
            "automation_name",
            "category",
            "tags",
            "lines",
            "created_at",
            "updated_at",
        )

    def get_category(self, obj: Transaction):
        if obj.category_id is None:
            return None
        return {
            "id": obj.category_id,
            "name": obj.category.name,
            "is_default": obj.category.is_default,
        }

    def get_tags(self, obj: Transaction) -> list:
        return [tag.name for tag in obj.tags.all()]

    def get_amount(self, obj: Transaction) -> str:
        return money(obj.amount)

    def get_automation_name(self, obj: Transaction):
        if obj.automation_id is None:
            return None
        try:
            automation = Automation.all_objects.get(pk=obj.automation_id)
        except Automation.DoesNotExist:
            return None
        if automation.kind == Automation.Kind.EXPENSE:
            return automation.description or "Spesa ricorrente"
        if automation.savings_id is None:
            return None
        try:
            savings = SavingsAccount.all_objects.get(pk=automation.savings_id)
        except SavingsAccount.DoesNotExist:
            return None
        return savings.name


class TransactionWriteSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(
        choices=[
            Transaction.Kind.INCOME,
            Transaction.Kind.EXPENSE,
            Transaction.Kind.TRANSFER,
        ]
    )
    date = serializers.DateField()
    description = serializers.CharField(
        required=False, allow_blank=True, max_length=255
    )
    amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal("0.01")
    )

    account = serializers.PrimaryKeyRelatedField(
        queryset=Account.objects.all(), required=False, allow_null=True
    )
    savings = serializers.PrimaryKeyRelatedField(
        queryset=SavingsAccount.objects.all(), required=False, allow_null=True
    )
    from_account = serializers.PrimaryKeyRelatedField(
        queryset=Account.objects.all(), required=False, allow_null=True
    )
    to_account = serializers.PrimaryKeyRelatedField(
        queryset=Account.objects.all(), required=False, allow_null=True
    )
    from_savings = serializers.PrimaryKeyRelatedField(
        queryset=SavingsAccount.objects.all(), required=False, allow_null=True
    )
    to_savings = serializers.PrimaryKeyRelatedField(
        queryset=SavingsAccount.objects.all(), required=False, allow_null=True
    )
    confirm_coverage = serializers.BooleanField(
        required=False, default=False, write_only=True
    )
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        required=False,
        allow_null=True,
    )
    tags = serializers.ListField(
        child=serializers.CharField(max_length=30),
        required=False,
    )

    def _check_owner(self, obj, profile, label: str):
        if obj is not None and obj.profile_id != profile.id:
            raise serializers.ValidationError(
                {label: "L'elemento non appartiene al profilo."}
            )

    def _check_active_account(self, account, label: str):
        if account is not None and account.archived:
            raise serializers.ValidationError({label: "Il conto è archiviato."})

    def validate(self, attrs):
        profile = self.context["profile"]
        exclude = self.context.get("exclude_transaction")
        kind = attrs["kind"]
        amount: Decimal = attrs["amount"]
        lines: list[dict] = []

        for key in (
            "account",
            "savings",
            "from_account",
            "to_account",
            "from_savings",
            "to_savings",
            "category_id",
        ):
            self._check_owner(attrs.get(key), profile, key)
        if attrs.get("category_id") is not None and attrs[
            "category_id"
        ].is_deleted:
            raise serializers.ValidationError(
                {"category_id": "La categoria è nel cestino."}
            )

        account = attrs.get("account")
        savings = attrs.get("savings")
        from_account = attrs.get("from_account")
        to_account = attrs.get("to_account")
        from_savings = attrs.get("from_savings")
        to_savings = attrs.get("to_savings")

        if kind == Transaction.Kind.INCOME:
            if account is None:
                raise serializers.ValidationError(
                    {"account": "Indica il conto dell'entrata."}
                )
            if any(
                value is not None
                for value in (savings, from_account, to_account, from_savings, to_savings)
            ):
                raise serializers.ValidationError(
                    "Un'entrata usa solo il campo account."
                )
            self._check_active_account(account, "account")
            lines.append(
                {
                    "account": account,
                    "amount": amount,
                    "role": Line.Role.PRINCIPAL,
                }
            )

        elif kind == Transaction.Kind.EXPENSE:
            if any(
                value is not None
                for value in (from_account, to_account, from_savings, to_savings)
            ):
                raise serializers.ValidationError(
                    "Una spesa usa account oppure savings, non i campi di trasferimento."
                )
            if (account is None) == (savings is None):
                raise serializers.ValidationError(
                    {"account": "Indica un solo conto o salvadanaio per la spesa."}
                )

            if account is not None:
                self._check_active_account(account, "account")
                lines.append(
                    {
                        "account": account,
                        "amount": -amount,
                        "role": Line.Role.PRINCIPAL,
                    }
                )
            else:
                available = savings_balance(savings, exclude_transaction=exclude)
                if available < amount and not attrs.get("confirm_coverage"):
                    raise serializers.ValidationError(
                        {
                            "code": "insufficient_savings",
                            "available": money(available),
                            "confirm_coverage": (
                                "Saldo del salvadanaio insufficiente: disponibili "
                                f"{money(available)}. Conferma l'uso del conto di "
                                "appoggio per la parte mancante."
                            ),
                        }
                    )
                savings_portion = min(available, amount)
                if savings_portion < ZERO:
                    savings_portion = ZERO
                if savings_portion > ZERO:
                    lines.append(
                        {
                            "savings": savings,
                            "amount": -savings_portion,
                            "role": Line.Role.PRINCIPAL,
                        }
                    )
                    lines.append(
                        {
                            "account": savings.backing_account,
                            "amount": savings_portion,
                            "role": Line.Role.TECHNICAL,
                        }
                    )
                lines.append(
                    {
                        "account": savings.backing_account,
                        "amount": -amount,
                        "role": Line.Role.PRINCIPAL,
                    }
                )

        elif kind == Transaction.Kind.TRANSFER:
            if any(value is not None for value in (account, savings)):
                raise serializers.ValidationError(
                    "Un trasferimento non usa i campi account/savings."
                )
            source_count = sum(
                value is not None for value in (from_account, from_savings)
            )
            destination_count = sum(
                value is not None for value in (to_account, to_savings)
            )
            if source_count != 1 or destination_count != 1:
                raise serializers.ValidationError(
                    "Indica una sola origine e una sola destinazione."
                )
            if from_savings is not None and to_savings is not None:
                raise serializers.ValidationError(
                    "Il trasferimento diretto tra salvadanai non è ammesso."
                )
            if from_account is not None and to_account is not None:
                if from_account.id == to_account.id:
                    raise serializers.ValidationError(
                        "Origine e destinazione devono essere diverse."
                    )
                self._check_active_account(from_account, "from_account")
                self._check_active_account(to_account, "to_account")
                lines.append(
                    {
                        "account": from_account,
                        "amount": -amount,
                        "role": Line.Role.TRANSFER_OUT,
                    }
                )
                lines.append(
                    {
                        "account": to_account,
                        "amount": amount,
                        "role": Line.Role.TRANSFER_IN,
                    }
                )
            elif from_account is not None and to_savings is not None:
                self._check_active_account(from_account, "from_account")
                lines.append(
                    {
                        "account": from_account,
                        "amount": -amount,
                        "role": Line.Role.TRANSFER_OUT,
                    }
                )
                lines.append(
                    {
                        "savings": to_savings,
                        "amount": amount,
                        "role": Line.Role.TRANSFER_IN,
                    }
                )
            else:
                available = savings_balance(
                    from_savings, exclude_transaction=exclude
                )
                if available < amount:
                    raise serializers.ValidationError(
                        {
                            "code": "insufficient_savings",
                            "available": money(available),
                            "amount": (
                                "Saldo del salvadanaio insufficiente: disponibili "
                                f"{money(available)}."
                            ),
                        }
                    )
                self._check_active_account(to_account, "to_account")
                lines.append(
                    {
                        "savings": from_savings,
                        "amount": -amount,
                        "role": Line.Role.TRANSFER_OUT,
                    }
                )
                lines.append(
                    {
                        "account": to_account,
                        "amount": amount,
                        "role": Line.Role.TRANSFER_IN,
                    }
                )

        self._lines = lines

        affected = [
            (line["account"], line["amount"], attrs["date"])
            for line in lines
            if line.get("account") is not None
        ]
        assert_accounts_non_negative(
            affected, exclude_transaction=self.context.get("exclude_transaction")
        )

        if exclude is not None:
            affected: dict[int, Decimal] = {}
            for line in lines:
                savings_obj = line.get("savings")
                if savings_obj is not None:
                    affected[savings_obj.id] = (
                        affected.get(savings_obj.id, ZERO) + line["amount"]
                    )
            for savings_id, net in affected.items():
                savings_obj = SavingsAccount.objects.get(pk=savings_id)
                available = savings_balance(
                    savings_obj, exclude_transaction=exclude
                )
                if available + net < ZERO:
                    raise serializers.ValidationError(
                        {
                            "savings": (
                                "L'operazione renderebbe negativo il saldo del "
                                "salvadanaio."
                            )
                        }
                    )

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        profile = self.context["profile"]
        category = validated_data.get("category_id") or match_category(
            profile, ""
        )
        tag_names = validated_data.get("tags", [])
        transaction_obj = Transaction.objects.create(
            profile=profile,
            kind=validated_data["kind"],
            date=validated_data["date"],
            description=validated_data.get("description", ""),
            amount=validated_data["amount"],
            category=category,
        )
        transaction_obj.tags.set(resolve_tags(profile, tag_names))
        Line.objects.bulk_create(
            [Line(transaction=transaction_obj, **line) for line in self._lines]
        )
        return transaction_obj

    @transaction.atomic
    def update(self, instance, validated_data):
        instance.kind = validated_data["kind"]
        instance.date = validated_data["date"]
        instance.description = validated_data.get("description", "")
        instance.amount = validated_data["amount"]
        if "category_id" in validated_data:
            instance.category = validated_data[
                "category_id"
            ] or match_category(instance.profile, "")
        instance.save()
        if "tags" in validated_data:
            instance.tags.set(
                resolve_tags(instance.profile, validated_data["tags"])
            )
        instance.lines.all().delete()
        Line.objects.bulk_create(
            [Line(transaction=instance, **line) for line in self._lines]
        )
        return instance


def _quantity(value) -> str | None:
    return None if value is None else f"{value:.8f}"


class InvestmentPositionSummarySerializer(serializers.Serializer):
    """Derived values of one position, built from the ledger service."""

    quantity = serializers.CharField()
    average_cost = serializers.CharField()
    cost = serializers.CharField()
    current_value = serializers.CharField(allow_null=True)
    unrealized_gain = serializers.CharField(allow_null=True)
    realized_gain = serializers.CharField()
    dividends = serializers.CharField()
    has_price = serializers.BooleanField()


class InvestmentSummarySerializer(serializers.Serializer):
    """Aggregate of every position of a profile."""

    total_cost = serializers.CharField()
    total_value = serializers.CharField()
    total_unrealized = serializers.CharField()
    positions_without_price = serializers.IntegerField()
    realized_gain = serializers.CharField()
    dividends = serializers.CharField()


class InvestmentPositionSerializer(serializers.ModelSerializer):
    category_label = serializers.CharField(source="get_category_display", read_only=True)
    current_price = serializers.SerializerMethodField()
    quantity = serializers.SerializerMethodField()
    average_cost = serializers.SerializerMethodField()
    cost = serializers.SerializerMethodField()
    current_value = serializers.SerializerMethodField()
    unrealized_gain = serializers.SerializerMethodField()
    realized_gain = serializers.SerializerMethodField()
    dividends = serializers.SerializerMethodField()
    has_price = serializers.SerializerMethodField()

    class Meta:
        model = InvestmentPosition
        fields = (
            "id",
            "name",
            "category",
            "category_label",
            "identifier",
            "current_price",
            "price_updated_on",
            "archived",
            "quantity",
            "average_cost",
            "cost",
            "current_value",
            "unrealized_gain",
            "realized_gain",
            "dividends",
            "has_price",
            "created_at",
            "updated_at",
        )

    def _ledger(self, obj: InvestmentPosition) -> dict:
        cache = self.context.setdefault("_ledger_cache", {})
        if obj.pk not in cache:
            cache[obj.pk] = recalculate_position(obj)
        return cache[obj.pk]

    def get_current_price(self, obj: InvestmentPosition):
        return None if obj.current_price is None else money(obj.current_price)

    def get_quantity(self, obj: InvestmentPosition):
        return _quantity(self._ledger(obj)["quantity"])

    def get_average_cost(self, obj: InvestmentPosition):
        return _quantity(self._ledger(obj)["average_cost"])

    def get_cost(self, obj: InvestmentPosition):
        return money(self._ledger(obj)["cost"])

    def get_current_value(self, obj: InvestmentPosition):
        value = self._ledger(obj)["current_value"]
        return None if value is None else money(value)

    def get_unrealized_gain(self, obj: InvestmentPosition):
        value = self._ledger(obj)["unrealized_gain"]
        return None if value is None else money(value)

    def get_realized_gain(self, obj: InvestmentPosition):
        return money(self._ledger(obj)["realized_gain"])

    def get_dividends(self, obj: InvestmentPosition):
        return money(self._ledger(obj)["dividends"])

    def get_has_price(self, obj: InvestmentPosition):
        return self._ledger(obj)["has_price"]


class InvestmentOperationSerializer(serializers.ModelSerializer):
    kind_label = serializers.CharField(source="get_kind_display", read_only=True)
    quantity = serializers.SerializerMethodField()
    unit_price = serializers.SerializerMethodField()
    gross_amount = serializers.SerializerMethodField()
    commission = serializers.SerializerMethodField()
    cash_amount = serializers.SerializerMethodField()
    account = serializers.SerializerMethodField()
    account_name = serializers.SerializerMethodField()
    cost_removed = serializers.SerializerMethodField()
    realized_gain = serializers.SerializerMethodField()

    class Meta:
        model = InvestmentOperation
        fields = (
            "id",
            "position",
            "kind",
            "kind_label",
            "date",
            "quantity",
            "unit_price",
            "gross_amount",
            "commission",
            "cash_amount",
            "description",
            "transaction",
            "account",
            "account_name",
            "cost_removed",
            "realized_gain",
            "created_at",
            "updated_at",
        )

    def _row(self, obj: InvestmentOperation) -> dict | None:
        rows = self.context.get("ledger_rows")
        if rows is not None:
            return rows.get(obj.pk)
        for row in recalculate_position(obj.position)["operations"]:
            if row["operation"].pk == obj.pk:
                return row
        return None

    def get_quantity(self, obj: InvestmentOperation):
        return _quantity(obj.quantity)

    def get_unit_price(self, obj: InvestmentOperation):
        return _quantity(obj.unit_price)

    def get_gross_amount(self, obj: InvestmentOperation):
        value = obj.gross_amount
        return None if value is None else money(value)

    def get_commission(self, obj: InvestmentOperation):
        return money(obj.commission)

    def get_cash_amount(self, obj: InvestmentOperation):
        return money(obj.cash_amount)

    def _principal_line(self, obj: InvestmentOperation):
        if obj.transaction_id is None:
            return None
        return obj.transaction.lines.filter(role=Line.Role.PRINCIPAL).first()

    def get_account(self, obj: InvestmentOperation):
        line = self._principal_line(obj)
        return line.account_id if line is not None else None

    def get_account_name(self, obj: InvestmentOperation):
        line = self._principal_line(obj)
        return line.account.name if line is not None else None

    def get_cost_removed(self, obj: InvestmentOperation):
        row = self._row(obj)
        return money(row["cost_removed"]) if row is not None else "0.00"

    def get_realized_gain(self, obj: InvestmentOperation):
        row = self._row(obj)
        return money(row["realized_gain"]) if row is not None else "0.00"


class InvestmentOpeningSerializer(serializers.Serializer):
    date = serializers.DateField()
    quantity = serializers.DecimalField(max_digits=24, decimal_places=8)
    unit_price = serializers.DecimalField(
        max_digits=24, decimal_places=8, required=False, allow_null=True
    )
    total_cost = serializers.DecimalField(
        max_digits=14, decimal_places=2, required=False, allow_null=True
    )
    total_amount = serializers.DecimalField(
        max_digits=14, decimal_places=2, required=False, allow_null=True
    )
    description = serializers.CharField(
        required=False, allow_blank=True, max_length=255
    )


class InvestmentPositionCreateSerializer(serializers.ModelSerializer):
    opening = InvestmentOpeningSerializer(required=False, write_only=True)

    class Meta:
        model = InvestmentPosition
        fields = ("name", "category", "identifier", "current_price", "opening")

    def validate_current_price(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError(
                "Il prezzo corrente non può essere negativo."
            )
        return value

    @transaction.atomic
    def create(self, validated_data):
        opening = validated_data.pop("opening", None)
        position = InvestmentPosition.objects.create(
            profile=self.context["profile"], **validated_data
        )
        if position.current_price is not None:
            position.price_updated_on = timezone.localdate()
            position.save(update_fields=("price_updated_on",))
        if opening is not None:
            total = opening.get("total_amount")
            if total is None:
                total = opening.get("total_cost")
            create_operation(
                position,
                kind=InvestmentOperation.Kind.OPENING,
                date=opening["date"],
                quantity=opening["quantity"],
                unit_price=opening.get("unit_price"),
                total_amount=total,
                description=opening.get("description", ""),
            )
        return position


class InvestmentPositionUpdateSerializer(serializers.ModelSerializer):
    price_updated_on = serializers.DateField(read_only=True)

    class Meta:
        model = InvestmentPosition
        fields = (
            "name",
            "category",
            "identifier",
            "current_price",
            "price_updated_on",
            "archived",
        )

    def validate_current_price(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError(
                "Il prezzo corrente non può essere negativo."
            )
        return value

    def update(self, instance, validated_data):
        archived = validated_data.pop("archived", serializers.empty)
        if archived is not serializers.empty:
            instance = set_position_archived(instance, archived)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        if "current_price" in validated_data:
            instance.price_updated_on = (
                None if validated_data["current_price"] is None else timezone.localdate()
            )
        instance.save()
        return instance


class InvestmentAccountSerializer(serializers.Serializer):
    account = serializers.PrimaryKeyRelatedField(
        queryset=Account.objects.all(), allow_null=True
    )

    def validate_account(self, account: Account | None) -> Account | None:
        if account is not None:
            profile = self.context["profile"]
            if account.profile_id != profile.id:
                raise serializers.ValidationError(
                    "Il conto non appartiene al profilo."
                )
            if account.archived:
                raise serializers.ValidationError("Il conto è archiviato.")
        return account


class InvestmentOperationCreateSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=InvestmentOperation.Kind.choices)
    date = serializers.DateField()
    quantity = serializers.DecimalField(
        max_digits=24, decimal_places=8, required=False, allow_null=True
    )
    unit_price = serializers.DecimalField(
        max_digits=24, decimal_places=8, required=False, allow_null=True
    )
    total_amount = serializers.DecimalField(
        max_digits=14, decimal_places=2, required=False, allow_null=True
    )
    commission = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True
    )
    amount = serializers.DecimalField(
        max_digits=14, decimal_places=2, required=False, allow_null=True
    )
    description = serializers.CharField(
        required=False, allow_blank=True, max_length=255
    )

    def create(self, validated_data):
        return create_operation(self.context["position"], **validated_data)


class InvestmentOperationUpdateSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(
        choices=InvestmentOperation.Kind.choices, required=False
    )
    date = serializers.DateField(required=False)
    quantity = serializers.DecimalField(
        max_digits=24, decimal_places=8, required=False, allow_null=True
    )
    unit_price = serializers.DecimalField(
        max_digits=24, decimal_places=8, required=False, allow_null=True
    )
    total_amount = serializers.DecimalField(
        max_digits=14, decimal_places=2, required=False, allow_null=True
    )
    commission = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True
    )
    amount = serializers.DecimalField(
        max_digits=14, decimal_places=2, required=False, allow_null=True
    )
    description = serializers.CharField(
        required=False, allow_blank=True, max_length=255
    )

    def validate(self, attrs):
        instance = self.instance
        if "kind" in attrs and attrs["kind"] != instance.kind:
            raise serializers.ValidationError(
                {"kind": "Il tipo di operazione non è modificabile."}
            )
        if (
            "amount" in attrs
            and instance.kind != InvestmentOperation.Kind.DIVIDEND
        ):
            raise serializers.ValidationError(
                {"amount": "L'importo si usa solo per il dividendo."}
            )
        return attrs

    def update(self, instance, validated_data):
        validated_data.pop("kind", None)
        return update_operation(instance, **validated_data)


class DashboardSerializer(serializers.Serializer):
    """Only used for schema/documentation; the dashboard is built in the view."""

    total_balance = serializers.CharField()
    total_savings = serializers.CharField()
    total_patrimony = serializers.CharField()
    total_investments_cost = serializers.CharField()
    total_investments_value = serializers.CharField()
    total_investments_unrealized = serializers.CharField()
    positions_without_price = serializers.IntegerField()
    period_investments_realized = serializers.CharField()
    period_dividends = serializers.CharField()
    period_balance = serializers.CharField()
    income_total = serializers.CharField()
    expense_total = serializers.CharField()
