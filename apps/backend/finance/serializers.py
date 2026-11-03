from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from .models import ZERO, Account, Line, Profile, SavingsAccount, Transaction
from .services import assert_accounts_non_negative, savings_balance


def money(value: Decimal) -> str:
    return f"{value:.2f}"


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ("id", "display_name", "created_at")


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

    class Meta:
        model = Transaction
        fields = (
            "id",
            "kind",
            "kind_label",
            "date",
            "description",
            "amount",
            "lines",
            "created_at",
            "updated_at",
        )

    def get_amount(self, obj: Transaction) -> str:
        return money(obj.amount)


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
        ):
            self._check_owner(attrs.get(key), profile, key)

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
        transaction_obj = Transaction.objects.create(
            profile=profile,
            kind=validated_data["kind"],
            date=validated_data["date"],
            description=validated_data.get("description", ""),
            amount=validated_data["amount"],
        )
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
        instance.save()
        instance.lines.all().delete()
        Line.objects.bulk_create(
            [Line(transaction=instance, **line) for line in self._lines]
        )
        return instance


class DashboardSerializer(serializers.Serializer):
    """Only used for schema/documentation; the dashboard is built in the view."""

    total_balance = serializers.CharField()
    total_savings = serializers.CharField()
    total_patrimony = serializers.CharField()
    period_balance = serializers.CharField()
    income_total = serializers.CharField()
    expense_total = serializers.CharField()
