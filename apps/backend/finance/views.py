from datetime import date

from django.db import transaction
from django.db.models import Count, Sum
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .automations import (
    cancel_open_executions,
    process_automation,
    resolve_pending,
    run_for_profile,
)
from .investments import (
    INVESTMENT_TRANSACTION_KINDS,
    delete_operation,
    portfolio_summary,
    recalculate_position,
    set_investment_account,
)
from .models import (
    ZERO,
    DEFAULT_CATEGORY_NAME,
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
    ensure_default_categories,
    match_category,
)
from .services import assert_accounts_non_negative
from .serializers import (
    AccountCreateSerializer,
    AccountSerializer,
    AccountUpdateSerializer,
    AutomationExecutionSerializer,
    AutomationSerializer,
    AutomationWriteSerializer,
    InvestmentAccountSerializer,
    InvestmentOperationCreateSerializer,
    InvestmentOperationSerializer,
    InvestmentOperationUpdateSerializer,
    InvestmentPositionCreateSerializer,
    InvestmentPositionSerializer,
    InvestmentPositionSummarySerializer,
    InvestmentPositionUpdateSerializer,
    InvestmentSummarySerializer,
    NotificationSerializer,
    ProfileSerializer,
    SavingsAccountCreateSerializer,
    SavingsAccountSerializer,
    SavingsAccountUpdateSerializer,
    TransactionSerializer,
    TransactionWriteSerializer,
)


class FinanceView(APIView):
    permission_classes = [IsAuthenticated]

    def get_profile(self, request) -> Profile:
        if request.user.is_global_admin:
            raise PermissionDenied(
                "L'amministratore globale non ha un profilo finanziario."
            )
        profile, created = Profile.objects.get_or_create(
            user=request.user,
            defaults={
                "display_name": request.user.email
                or request.user.username
                or ""
            },
        )
        if created:
            ensure_default_categories(profile)
        return profile


class ProfileView(FinanceView):
    def get(self, request):
        profile = self.get_profile(request)
        return Response(ProfileSerializer(profile).data)

    def patch(self, request):
        profile = self.get_profile(request)
        serializer = ProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class DashboardView(FinanceView):
    def get(self, request):
        profile = self.get_profile(request)
        today = timezone.localdate()
        start = self._parse_date(request.query_params.get("start"), today.replace(day=1))
        end = self._parse_date(request.query_params.get("end"), today)
        if start > end:
            raise ValidationError({"detail": "La data iniziale supera quella finale."})

        accounts = list(Account.objects.filter(profile=profile))
        savings = list(SavingsAccount.objects.filter(profile=profile))
        investments = portfolio_summary(profile)

        total_balance = sum((account.balance for account in accounts), ZERO)
        total_savings = sum((savings_account.balance for savings_account in savings), ZERO)
        # The period balance is the variation of the total balance, so the
        # account openings inside the period count too (DC-012, REQ-DASH-05).
        period_balance = (
            Line.objects.filter(
                account__profile=profile,
                transaction__date__gte=start,
                transaction__date__lte=end,
                transaction__is_deleted=False,
            ).aggregate(total=Sum("amount"))["total"]
            or ZERO
        )
        income_total = (
            Transaction.objects.filter(
                profile=profile,
                kind__in=(
                    Transaction.Kind.INCOME,
                    Transaction.Kind.INVESTMENT_DIVIDEND,
                ),
                date__gte=start,
                date__lte=end,
            ).aggregate(total=Sum("amount"))["total"]
            or ZERO
        )
        expense_total = (
            Transaction.objects.filter(
                profile=profile,
                kind=Transaction.Kind.EXPENSE,
                date__gte=start,
                date__lte=end,
            ).aggregate(total=Sum("amount"))["total"]
            or ZERO
        )
        recent = (
            Transaction.objects.filter(profile=profile)
            .exclude(kind__in=INVESTMENT_TRANSACTION_KINDS)
            .prefetch_related("lines__account", "lines__savings")
            .order_by("-date", "-id")[:10]
        )
        period_realized, period_dividends = self._period_investments(
            profile, start, end
        )

        return Response(
            {
                "total_balance": f"{total_balance:.2f}",
                "total_savings": f"{total_savings:.2f}",
                "total_patrimony": (
                    f"{total_balance + total_savings + investments['total_cost']:.2f}"
                ),
                "total_investments_cost": f"{investments['total_cost']:.2f}",
                "total_investments_value": f"{investments['total_value']:.2f}",
                "total_investments_unrealized": (
                    f"{investments['total_unrealized']:.2f}"
                ),
                "positions_without_price": investments["positions_without_price"],
                "period_investments_realized": f"{period_realized:.2f}",
                "period_dividends": f"{period_dividends:.2f}",
                "period_balance": f"{period_balance:.2f}",
                "income_total": f"{income_total:.2f}",
                "expense_total": f"{expense_total:.2f}",
                "period": {"start": start.isoformat(), "end": end.isoformat()},
                "accounts": AccountSerializer(accounts, many=True).data,
                "savings": SavingsAccountSerializer(savings, many=True).data,
                "recent_transactions": TransactionSerializer(recent, many=True).data,
            }
        )

    @staticmethod
    def _period_investments(profile: Profile, start: date, end: date):
        realized = ZERO
        for position in profile.investment_positions.all():
            for row in recalculate_position(position)["operations"]:
                operation = row["operation"]
                if (
                    operation.kind == InvestmentOperation.Kind.SELL
                    and start <= operation.date <= end
                ):
                    realized += row["realized_gain"]
        dividends = (
            InvestmentOperation.objects.filter(
                profile=profile,
                kind=InvestmentOperation.Kind.DIVIDEND,
                date__gte=start,
                date__lte=end,
            ).aggregate(total=Sum("cash_amount"))["total"]
            or ZERO
        )
        return realized, dividends

    @staticmethod
    def _parse_date(value, default: date) -> date:
        if not value:
            return default
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise ValidationError({"detail": f"Data non valida: {value}."}) from exc


class DashboardSeriesView(FinanceView):
    """Time buckets and per-category expenses for the dashboard charts."""

    def get(self, request):
        from datetime import timedelta

        profile = self.get_profile(request)
        today = timezone.localdate()
        start = DashboardView._parse_date(
            request.query_params.get("start"), today.replace(day=1)
        )
        end = DashboardView._parse_date(
            request.query_params.get("end"), today
        )
        if start > end:
            raise ValidationError(
                {"detail": "La data iniziale supera quella finale."}
            )

        span = (end - start).days
        step = 1 if span <= 62 else 7
        buckets: list[date] = []
        cursor = start
        while cursor <= end:
            buckets.append(cursor)
            cursor += timedelta(days=step)
        if buckets[-1] != end:
            buckets.append(end)
        buckets = buckets[:95]

        account_lines = Line.objects.filter(
            account__profile=profile,
            transaction__is_deleted=False,
        ).order_by("transaction__date", "id")
        savings_lines = Line.objects.filter(
            savings__profile=profile,
            transaction__is_deleted=False,
        ).order_by("transaction__date", "id")
        cost_steps: list[list[tuple[date, Decimal]]] = []
        for position in profile.investment_positions.all():
            cost_steps.append(
                [
                    (row["operation"].date, row["cost_after"])
                    for row in recalculate_position(position)["operations"]
                ]
            )

        points = []
        for bucket in buckets:
            saldo = (
                account_lines.filter(transaction__date__lte=bucket).aggregate(
                    total=Sum("amount")
                )["total"]
                or ZERO
            )
            savings = (
                savings_lines.filter(transaction__date__lte=bucket).aggregate(
                    total=Sum("amount")
                )["total"]
                or ZERO
            )
            invested = ZERO
            for steps in cost_steps:
                current = ZERO
                for op_date, cost_after in steps:
                    if op_date > bucket:
                        break
                    current = cost_after
                invested += current
            points.append(
                {
                    "date": bucket.isoformat(),
                    "saldo": f"{saldo:.2f}",
                    "patrimonio": f"{saldo + savings + invested:.2f}",
                }
            )

        by_category = (
            Transaction.objects.filter(
                profile=profile,
                kind=Transaction.Kind.EXPENSE,
                date__gte=start,
                date__lte=end,
            )
            .exclude(category__isnull=True)
            .values("category__id", "category__name")
            .annotate(total=Sum("amount"))
            .order_by("-total")
        )
        return Response(
            {
                "buckets": points,
                "by_category": [
                    {
                        "id": entry["category__id"],
                        "name": entry["category__name"],
                        "total": f"{entry['total']:.2f}",
                    }
                    for entry in by_category
                ],
            }
        )


class AccountListCreateView(FinanceView):
    def get(self, request):
        profile = self.get_profile(request)
        accounts = Account.objects.filter(profile=profile)
        return Response({"accounts": AccountSerializer(accounts, many=True).data})

    def post(self, request):
        profile = self.get_profile(request)
        serializer = AccountCreateSerializer(
            data=request.data, context={"profile": profile}
        )
        serializer.is_valid(raise_exception=True)
        account = serializer.save()
        return Response(
            AccountSerializer(account).data, status=status.HTTP_201_CREATED
        )


class AccountDetailView(FinanceView):
    def get_object(self, request, pk: int) -> Account:
        profile = self.get_profile(request)
        try:
            return Account.objects.get(pk=pk, profile=profile)
        except Account.DoesNotExist as exc:
            raise ValidationError({"detail": "Conto non trovato."}) from exc

    def get(self, request, pk: int):
        return Response(AccountSerializer(self.get_object(request, pk)).data)

    def patch(self, request, pk: int):
        account = self.get_object(request, pk)
        serializer = AccountUpdateSerializer(account, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        if serializer.validated_data.get("archived") and account.investment_profiles.exists():
            return Response(
                {
                    "detail": (
                        "Il conto è il conto degli investimenti: cambia conto "
                        "prima di archiviarlo."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer.save()
        return Response(AccountSerializer(account).data)

    def delete(self, request, pk: int):
        account = self.get_object(request, pk)
        if account.investment_profiles.exists():
            return Response(
                {
                    "detail": (
                        "Il conto è il conto degli investimenti: cambia conto "
                        "prima di eliminarlo."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if account.savings_accounts.exists():
            return Response(
                {"detail": "Il conto è usato come appoggio di un salvadanaio."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if account.automations.exists():
            return Response(
                {"detail": "Il conto è usato da un'automazione periodica."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if account.lines.exists():
            return Response(
                {"detail": "Il conto ha movimenti: puoi solo archiviarlo."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        account.soft_delete(request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class SavingsAccountListCreateView(FinanceView):
    def get(self, request):
        profile = self.get_profile(request)
        savings = SavingsAccount.objects.filter(profile=profile).select_related(
            "backing_account"
        )
        return Response({"savings": SavingsAccountSerializer(savings, many=True).data})

    def post(self, request):
        profile = self.get_profile(request)
        serializer = SavingsAccountCreateSerializer(
            data=request.data, context={"profile": profile}
        )
        serializer.is_valid(raise_exception=True)
        savings = serializer.save()
        return Response(
            SavingsAccountSerializer(savings).data, status=status.HTTP_201_CREATED
        )


class SavingsAccountDetailView(FinanceView):
    def get_object(self, request, pk: int) -> SavingsAccount:
        profile = self.get_profile(request)
        try:
            return SavingsAccount.objects.select_related("backing_account").get(
                pk=pk, profile=profile
            )
        except SavingsAccount.DoesNotExist as exc:
            raise ValidationError({"detail": "Salvadanaio non trovato."}) from exc

    def get(self, request, pk: int):
        return Response(SavingsAccountSerializer(self.get_object(request, pk)).data)

    def patch(self, request, pk: int):
        savings = self.get_object(request, pk)
        serializer = SavingsAccountUpdateSerializer(
            savings, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(SavingsAccountSerializer(savings).data)

    def delete(self, request, pk: int):
        savings = self.get_object(request, pk)
        balance = savings.balance
        with transaction.atomic():
            for automation in savings.automations.all():
                cancel_open_executions(
                    automation, AutomationExecution.FailureCode.RULE_DELETED
                )
                Notification.objects.filter(
                    profile=savings.profile,
                    automation=automation,
                    kind=Notification.Kind.AUTOMATION_PENDING,
                    read_at__isnull=True,
                ).update(read_at=timezone.now())
                automation.soft_delete(request.user)
            if balance != ZERO:
                transfer = Transaction.objects.create(
                    profile=savings.profile,
                    kind=Transaction.Kind.TRANSFER,
                    date=timezone.localdate(),
                    description=f"Saldo residuo salvadanaio {savings.name}",
                    amount=abs(balance),
                    category=match_category(savings.profile, ""),
                )
                Line.objects.create(
                    transaction=transfer,
                    account=savings.backing_account,
                    amount=balance,
                    role=Line.Role.TRANSFER_IN
                    if balance > ZERO
                    else Line.Role.TRANSFER_OUT,
                )
            savings.soft_delete(request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class TransactionListCreateView(FinanceView):
    def get(self, request):
        profile = self.get_profile(request)
        queryset = (
            Transaction.objects.filter(profile=profile)
            .exclude(kind__in=INVESTMENT_TRANSACTION_KINDS)
            .select_related("category")
            .prefetch_related("tags", "lines__account", "lines__savings")
            .order_by("-date", "-id")
        )
        account_id = request.query_params.get("account")
        savings_id = request.query_params.get("savings")
        if account_id:
            queryset = queryset.filter(lines__account_id=account_id)
        if savings_id:
            queryset = queryset.filter(lines__savings_id=savings_id)
        start = request.query_params.get("start")
        end = request.query_params.get("end")
        if start:
            queryset = queryset.filter(date__gte=start)
        if end:
            queryset = queryset.filter(date__lte=end)
        category_id = request.query_params.get("category")
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        tag = (request.query_params.get("tag") or "").strip()
        if tag:
            queryset = queryset.filter(tags__name=tag)
        if account_id or savings_id or tag:
            queryset = queryset.distinct()
        try:
            limit = min(max(int(request.query_params.get("limit", 100)), 1), 500)
        except (TypeError, ValueError):
            limit = 100
        try:
            offset = max(int(request.query_params.get("offset", 0)), 0)
        except (TypeError, ValueError):
            offset = 0
        total = queryset.count()
        return Response(
            {
                "transactions": TransactionSerializer(
                    queryset[offset : offset + limit], many=True
                ).data,
                "count": total,
            }
        )

    def post(self, request):
        profile = self.get_profile(request)
        serializer = TransactionWriteSerializer(
            data=request.data, context={"profile": profile}
        )
        serializer.is_valid(raise_exception=True)
        operation = serializer.save()
        operation = (
            Transaction.objects.select_related("category")
            .prefetch_related("tags", "lines__account", "lines__savings")
            .get(pk=operation.pk)
        )
        return Response(
            TransactionSerializer(operation).data, status=status.HTTP_201_CREATED
        )


class TransactionDetailView(FinanceView):
    def get_object(self, request, pk: int) -> Transaction:
        profile = self.get_profile(request)
        try:
            return (
                Transaction.objects.select_related("category")
                .prefetch_related("tags", "lines__account", "lines__savings")
                .get(pk=pk, profile=profile)
            )
        except Transaction.DoesNotExist as exc:
            raise ValidationError({"detail": "Movimento non trovato."}) from exc

    def get(self, request, pk: int):
        return Response(TransactionSerializer(self.get_object(request, pk)).data)

    def patch(self, request, pk: int):
        operation = self.get_object(request, pk)
        if operation.kind in INVESTMENT_TRANSACTION_KINDS:
            return Response(
                {
                    "detail": (
                        "Le operazioni di investimento si modificano dalla "
                        "pagina Investimenti."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if operation.kind == Transaction.Kind.OPENING:
            return Response(
                {"detail": "Il movimento di apertura non è modificabile."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = TransactionWriteSerializer(
            operation,
            data=request.data,
            context={"profile": operation.profile, "exclude_transaction": operation},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        operation = (
            Transaction.objects.select_related("category")
            .prefetch_related("tags", "lines__account", "lines__savings")
            .get(pk=operation.pk)
        )
        AutomationExecution.objects.filter(transaction=operation).update(
            corrected=True, updated_at=timezone.now()
        )
        return Response(TransactionSerializer(operation).data)

    def delete(self, request, pk: int):
        operation = self.get_object(request, pk)
        if operation.kind in INVESTMENT_TRANSACTION_KINDS:
            return Response(
                {
                    "detail": (
                        "Le operazioni di investimento si eliminano dalla "
                        "pagina Investimenti."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if operation.kind == Transaction.Kind.OPENING:
            return Response(
                {"detail": "Il movimento di apertura non è eliminabile."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        affected_accounts = [
            line.account
            for line in operation.lines.all()
            if line.account_id is not None
        ]
        assert_accounts_non_negative(
            accounts=affected_accounts, exclude_transaction=operation
        )
        with transaction.atomic():
            execution = AutomationExecution.objects.filter(
                transaction=operation
            ).first()
            if execution is not None:
                execution.transaction = None
                execution.status = AutomationExecution.Status.CANCELLED
                execution.failure_code = AutomationExecution.FailureCode.CANCELLED
                execution.failure_message = "Movimento annullato manualmente."
                execution.next_retry_at = None
                execution.save(
                    update_fields=(
                        "transaction",
                        "status",
                        "failure_code",
                        "failure_message",
                        "next_retry_at",
                        "updated_at",
                    )
                )
            operation.soft_delete(request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


def _category_payload(category: Category) -> dict:
    return {
        "id": category.id,
        "name": category.name,
        "is_preset": category.is_preset,
        "is_default": category.is_default,
    }


class CategoryListCreateView(FinanceView):
    def get(self, request):
        profile = self.get_profile(request)
        ensure_default_categories(profile)
        categories = Category.objects.filter(profile=profile).order_by(
            "-is_default", "name"
        )
        return Response([_category_payload(item) for item in categories])

    def post(self, request):
        profile = self.get_profile(request)
        name = str(request.data.get("name", "")).strip()
        if not name or len(name) > 60:
            raise ValidationError(
                {"name": "Indica un nome da 1 a 60 caratteri."}
            )
        if Category.objects.filter(
            profile=profile, name__iexact=name
        ).exists():
            raise ValidationError({"name": "Esiste già questa categoria."})
        ensure_default_categories(profile)
        category = Category.objects.create(profile=profile, name=name)
        return Response(
            _category_payload(category), status=status.HTTP_201_CREATED
        )


class CategoryDetailView(FinanceView):
    def _get_object(self, request, pk: int) -> Category:
        profile = self.get_profile(request)
        try:
            return Category.objects.get(pk=pk, profile=profile)
        except Category.DoesNotExist as exc:
            raise ValidationError({"detail": "Categoria non trovata."}) from exc

    def patch(self, request, pk: int):
        category = self._get_object(request, pk)
        if category.is_default:
            raise ValidationError(
                {"detail": 'La categoria "Altro" non si può rinominare.'}
            )
        name = str(request.data.get("name", "")).strip()
        if not name or len(name) > 60:
            raise ValidationError(
                {"name": "Indica un nome da 1 a 60 caratteri."}
            )
        if (
            Category.objects.filter(profile=category.profile, name__iexact=name)
            .exclude(pk=category.pk)
            .exists()
        ):
            raise ValidationError({"name": "Esiste già questa categoria."})
        category.name = name
        category.save(update_fields=("name", "updated_at"))
        return Response(_category_payload(category))

    def delete(self, request, pk: int):
        category = self._get_object(request, pk)
        if category.is_default:
            raise ValidationError(
                {"detail": 'La categoria "Altro" non si può eliminare.'}
            )
        default = match_category(category.profile, "")
        with transaction.atomic():
            Transaction.objects.filter(category=category).update(
                category=default
            )
            category.soft_delete(request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class TagListCreateView(FinanceView):
    def get(self, request):
        profile = self.get_profile(request)
        tags = Tag.objects.filter(profile=profile).order_by("name")
        return Response([{"id": item.id, "name": item.name} for item in tags])

    def post(self, request):
        profile = self.get_profile(request)
        name = str(request.data.get("name", "")).strip()
        if not name or len(name) > 30:
            raise ValidationError(
                {"name": "Indica un nome da 1 a 30 caratteri."}
            )
        tag, _ = Tag.objects.get_or_create(profile=profile, name=name)
        return Response(
            {"id": tag.id, "name": tag.name},
            status=status.HTTP_201_CREATED,
        )


class TagDetailView(FinanceView):
    def delete(self, request, pk: int):
        profile = self.get_profile(request)
        try:
            tag = Tag.objects.get(pk=pk, profile=profile)
        except Tag.DoesNotExist as exc:
            raise ValidationError({"detail": "Tag non trovato."}) from exc
        tag.soft_delete(request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


TRASH_TYPES = (
    "movement",
    "account",
    "savings",
    "automation",
    "position",
    "operation",
    "category",
    "tag",
)


def _trash_label(entry) -> str:
    name = getattr(entry, "name", "") or ""
    if name:
        return name
    description = getattr(entry, "description", "") or ""
    if description:
        return description
    return str(entry)


def _trash_entry(item_type: str, entry) -> dict:
    author = getattr(entry, "deleted_by", None)
    return {
        "type": item_type,
        "id": entry.id,
        "label": _trash_label(entry),
        "deleted_at": entry.deleted_at.isoformat() if entry.deleted_at else None,
        "deleted_by": (
            author.email or author.username if author is not None else None
        ),
    }


def _trash_queryset(profile: Profile, item_type: str):
    mapping = {
        "movement": Transaction.all_objects.filter(
            profile=profile,
        ).exclude(kind__in=INVESTMENT_TRANSACTION_KINDS),
        "account": Account.all_objects.filter(profile=profile),
        "savings": SavingsAccount.all_objects.filter(profile=profile),
        "automation": Automation.all_objects.filter(profile=profile),
        "position": InvestmentPosition.all_objects.filter(profile=profile),
        "operation": InvestmentOperation.all_objects.filter(profile=profile),
        "category": Category.all_objects.filter(profile=profile),
        "tag": Tag.all_objects.filter(profile=profile),
    }
    return mapping[item_type].filter(is_deleted=True)


class TrashView(FinanceView):
    def get(self, request):
        profile = self.get_profile(request)
        item_type = request.query_params.get("type", "")
        types = [item_type] if item_type in TRASH_TYPES else list(TRASH_TYPES)
        items: list[dict] = []
        for kind in types:
            for entry in _trash_queryset(profile, kind).order_by("-deleted_at"):
                items.append(_trash_entry(kind, entry))
        items.sort(key=lambda item: item["deleted_at"] or "", reverse=True)
        return Response({"items": items, "count": len(items)})


class TrashRestoreView(FinanceView):
    def post(self, request):
        profile = self.get_profile(request)
        item_type = request.data.get("type", "")
        try:
            item_id = int(request.data.get("id"))
        except (TypeError, ValueError):
            raise ValidationError({"detail": "Elemento non valido."})
        if item_type not in TRASH_TYPES:
            raise ValidationError({"detail": "Tipo non valido."})
        try:
            entry = _trash_queryset(profile, item_type).get(pk=item_id)
        except Exception as exc:
            raise ValidationError(
                {"detail": "Elemento non trovato nel cestino."}
            ) from exc
        if item_type in ("category", "tag"):
            clash = (
                Category.objects.filter(
                    profile=profile, name__iexact=entry.name
                ).exists()
                if item_type == "category"
                else Tag.objects.filter(profile=profile, name=entry.name).exists()
            )
            if clash:
                raise ValidationError(
                    {
                        "detail": (
                            f'Esiste già "{entry.name}": rinomina o elimina '
                            "l'elemento attivo prima di ripristinare."
                        )
                    }
                )
        if item_type == "automation":
            try:
                containers = [entry.savings, entry.source_account]
            except (SavingsAccount.DoesNotExist, Account.DoesNotExist):
                raise ValidationError(
                    {
                        "detail": (
                            "Il conto o salvadanaio collegato non esiste più."
                        )
                    }
                )
            if any(
                container is not None and container.is_deleted
                for container in containers
            ):
                raise ValidationError(
                    {
                        "detail": (
                            "Il conto o salvadanaio collegato è nel cestino: "
                            "ripristinalo prima."
                        )
                    }
                )
        if item_type == "movement":
            if entry.kind in INVESTMENT_TRANSACTION_KINDS:
                raise ValidationError(
                    {
                        "detail": (
                            "Le operazioni di investimento si gestiscono dalla "
                            "pagina Investimenti."
                        )
                    }
                )
            for line in entry.lines.all():
                container = line.account or line.savings
                if container is not None and container.is_deleted:
                    raise ValidationError(
                        {
                            "detail": (
                                "Il conto o salvadanaio del movimento è nel "
                                "cestino: ripristinalo prima."
                            )
                        }
                    )
        if item_type == "operation" and entry.transaction_id is not None:
            try:
                movement = Transaction.all_objects.get(
                    pk=entry.transaction_id, profile=profile
                )
            except Transaction.DoesNotExist as exc:
                raise ValidationError(
                    {"detail": "Il movimento collegato non esiste più."}
                ) from exc
            if movement.is_deleted:
                movement.restore()
        entry.restore()
        return Response(_trash_entry(item_type, entry))


class TrashPurgeView(FinanceView):
    def post(self, request):
        profile = self.get_profile(request)
        item_type = request.data.get("type", "")
        try:
            item_id = int(request.data.get("id"))
        except (TypeError, ValueError):
            raise ValidationError({"detail": "Elemento non valido."})
        if item_type not in TRASH_TYPES:
            raise ValidationError({"detail": "Tipo non valido."})
        try:
            entry = _trash_queryset(profile, item_type).get(pk=item_id)
        except Exception as exc:
            raise ValidationError(
                {"detail": "Elemento non trovato nel cestino."}
            ) from exc
        if item_type == "account" and (
            Transaction.all_objects.filter(lines__account=entry).exists()
            or Automation.all_objects.filter(source_account=entry).exists()
        ):
            raise ValidationError(
                {
                    "detail": (
                        "Il conto ha movimenti o automazioni: "
                        "non si può eliminare."
                    )
                }
            )
        entry.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class TrashEmptyView(FinanceView):
    def post(self, request):
        profile = self.get_profile(request)
        removed = 0
        for kind in TRASH_TYPES:
            for entry in _trash_queryset(profile, kind):
                if kind == "account" and (
                    Transaction.all_objects.filter(
                        lines__account=entry
                    ).exists()
                    or Automation.all_objects.filter(
                        source_account=entry
                    ).exists()
                ):
                    continue
                entry.delete()
                removed += 1
        return Response({"purged": removed})


class SuggestCategoryView(FinanceView):
    """Rule-based category suggestion (no ML): history, then account, then default."""

    def get(self, request):
        profile = self.get_profile(request)
        description = (request.query_params.get("description") or "").strip()
        account_id = request.query_params.get("account")
        base = Transaction.objects.filter(profile=profile).exclude(
            kind__in=[
                Transaction.Kind.TRANSFER,
                *INVESTMENT_TRANSACTION_KINDS,
            ]
        )
        category = None
        source = "default"
        if len(description) >= 3:
            match = (
                base.filter(description__icontains=description)
                .exclude(category__isnull=True)
                .values("category")
                .annotate(count=Count("id"))
                .order_by("-count")
                .first()
            )
            if match is not None:
                category = Category.objects.filter(pk=match["category"]).first()
                source = "history"
        if category is None and account_id:
            match = (
                base.filter(lines__account_id=account_id)
                .exclude(category__isnull=True)
                .values("category")
                .annotate(count=Count("id"))
                .order_by("-count")
                .first()
            )
            if match is not None:
                category = Category.objects.filter(pk=match["category"]).first()
                source = "account"
        if category is None:
            category = match_category(profile, "")
        return Response(
            {"category": _category_payload(category), "source": source}
        )


def _get_position(profile: Profile, pk: int) -> InvestmentPosition:
    try:
        return InvestmentPosition.objects.get(pk=pk, profile=profile)
    except InvestmentPosition.DoesNotExist as exc:
        raise ValidationError({"detail": "Posizione non trovata."}) from exc


def _position_ledger(position: InvestmentPosition):
    ledger = recalculate_position(position)
    rows = {row["operation"].pk: row for row in ledger["operations"]}
    return ledger, rows


def _operation_payload(operation: InvestmentOperation):
    _, rows = _position_ledger(operation.position)
    return InvestmentOperationSerializer(
        operation, context={"ledger_rows": rows}
    ).data


def _account_payload(account: Account | None):
    return AccountSerializer(account).data if account is not None else None


class InvestmentListCreateView(FinanceView):
    def get(self, request):
        profile = self.get_profile(request)
        positions = list(profile.investment_positions.all())
        return Response(
            {
                "investment_account": _account_payload(profile.investment_account),
                "summary": InvestmentSummarySerializer(
                    portfolio_summary(profile)
                ).data,
                "positions": InvestmentPositionSerializer(
                    positions, many=True
                ).data,
            }
        )

    def post(self, request):
        profile = self.get_profile(request)
        serializer = InvestmentPositionCreateSerializer(
            data=request.data, context={"profile": profile}
        )
        serializer.is_valid(raise_exception=True)
        position = serializer.save()
        return Response(
            InvestmentPositionSerializer(position).data,
            status=status.HTTP_201_CREATED,
        )


class InvestmentDetailView(FinanceView):
    def get_object(self, request, pk: int) -> InvestmentPosition:
        profile = self.get_profile(request)
        return _get_position(profile, pk)

    def get(self, request, pk: int):
        position = self.get_object(request, pk)
        ledger, rows = _position_ledger(position)
        operations = position.operations.select_related("transaction").all()
        return Response(
            {
                "position": InvestmentPositionSerializer(
                    position, context={"_ledger_cache": {position.pk: ledger}}
                ).data,
                "summary": InvestmentPositionSummarySerializer(ledger).data,
                "operations": InvestmentOperationSerializer(
                    operations, many=True, context={"ledger_rows": rows}
                ).data,
            }
        )

    def patch(self, request, pk: int):
        position = self.get_object(request, pk)
        serializer = InvestmentPositionUpdateSerializer(
            position, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        position = serializer.save()
        return Response(InvestmentPositionSerializer(position).data)

    def delete(self, request, pk: int):
        position = self.get_object(request, pk)
        if position.operations.exists():
            return Response(
                {
                    "detail": (
                        "La posizione ha operazioni: elimina prima le operazioni."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        position.soft_delete(request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class InvestmentAccountView(FinanceView):
    def put(self, request):
        profile = self.get_profile(request)
        data = request.data
        if "investment_account" in data and "account" not in data:
            data = {**data, "account": data["investment_account"]}
        serializer = InvestmentAccountSerializer(
            data=data, context={"profile": profile}
        )
        serializer.is_valid(raise_exception=True)
        profile = set_investment_account(
            profile, serializer.validated_data["account"]
        )
        return Response(
            {"investment_account": _account_payload(profile.investment_account)}
        )


class InvestmentOperationCreateView(FinanceView):
    def post(self, request, pk: int):
        profile = self.get_profile(request)
        position = _get_position(profile, pk)
        serializer = InvestmentOperationCreateSerializer(
            data=request.data, context={"position": position}
        )
        serializer.is_valid(raise_exception=True)
        operation = serializer.save()
        return Response(
            _operation_payload(operation), status=status.HTTP_201_CREATED
        )


class InvestmentOperationDetailView(FinanceView):
    def get_object(self, request, pk: int) -> InvestmentOperation:
        profile = self.get_profile(request)
        try:
            return InvestmentOperation.objects.select_related(
                "transaction", "position"
            ).get(pk=pk, profile=profile)
        except InvestmentOperation.DoesNotExist as exc:
            raise ValidationError(
                {"detail": "Operazione non trovata."}
            ) from exc

    def patch(self, request, pk: int):
        operation = self.get_object(request, pk)
        serializer = InvestmentOperationUpdateSerializer(
            operation, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        operation = serializer.save()
        return Response(_operation_payload(operation))

    def delete(self, request, pk: int):
        operation = self.get_object(request, pk)
        delete_operation(operation, request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class AutomationListCreateView(FinanceView):
    def get(self, request):
        profile = self.get_profile(request)
        automations = Automation.objects.filter(
            profile=profile
        ).select_related("savings", "source_account")
        return Response(
            {
                "automations": AutomationSerializer(
                    automations, many=True
                ).data
            }
        )

    def post(self, request):
        profile = self.get_profile(request)
        serializer = AutomationWriteSerializer(
            data=request.data, context={"profile": profile}
        )
        serializer.is_valid(raise_exception=True)
        automation = serializer.save()
        automation = Automation.objects.select_related(
            "savings", "source_account"
        ).get(pk=automation.pk)
        return Response(
            AutomationSerializer(automation).data,
            status=status.HTTP_201_CREATED,
        )


class AutomationDetailView(FinanceView):
    def get_object(self, request, pk: int) -> Automation:
        profile = self.get_profile(request)
        try:
            return Automation.objects.select_related(
                "savings", "source_account"
            ).get(pk=pk, profile=profile)
        except Automation.DoesNotExist as exc:
            raise ValidationError({"detail": "Automazione non trovata."}) from exc

    def get(self, request, pk: int):
        return Response(
            AutomationSerializer(self.get_object(request, pk)).data
        )

    def patch(self, request, pk: int):
        automation = self.get_object(request, pk)
        serializer = AutomationWriteSerializer(
            automation,
            data=request.data,
            partial=True,
            context={"profile": automation.profile},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        automation.refresh_from_db()
        return Response(AutomationSerializer(automation).data)

    def delete(self, request, pk: int):
        automation = self.get_object(request, pk)
        with transaction.atomic():
            cancel_open_executions(
                automation, AutomationExecution.FailureCode.RULE_DELETED
            )
            Notification.objects.filter(
                profile=automation.profile,
                automation=automation,
                kind=Notification.Kind.AUTOMATION_PENDING,
                read_at__isnull=True,
            ).update(read_at=timezone.now())
            automation.soft_delete(request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class AutomationRunView(FinanceView):
    def post(self, request, pk: int):
        profile = self.get_profile(request)
        try:
            automation = Automation.objects.get(pk=pk, profile=profile)
        except Automation.DoesNotExist as exc:
            raise ValidationError({"detail": "Automazione non trovata."}) from exc
        outcome = process_automation(automation)
        automation.refresh_from_db()
        return Response(
            {
                "outcome": outcome,
                "automation": AutomationSerializer(automation).data,
            }
        )


class AutomationRunAllView(FinanceView):
    def post(self, request):
        profile = self.get_profile(request)
        outcome = run_for_profile(profile)
        return Response({"outcome": outcome})


class AutomationResolveView(FinanceView):
    def post(self, request, pk: int):
        profile = self.get_profile(request)
        try:
            automation = Automation.objects.get(pk=pk, profile=profile)
        except Automation.DoesNotExist as exc:
            raise ValidationError({"detail": "Automazione non trovata."}) from exc
        if automation.status != Automation.Status.ACTIVE:
            raise ValidationError(
                {
                    "detail": (
                        "Riattiva l'automazione prima di recuperare le "
                        "occorrenze perse."
                    )
                }
            )
        recover = request.data.get("recover")
        if not isinstance(recover, list):
            raise ValidationError(
                {"recover": "Indica la lista delle occorrenze da recuperare."}
            )
        try:
            recover_ids = {int(value) for value in recover}
        except (TypeError, ValueError) as exc:
            raise ValidationError(
                {"recover": "Gli identificatori devono essere numeri."}
            ) from exc

        pending_ids = set(
            automation.executions.filter(
                status=AutomationExecution.Status.PENDING
            ).values_list("id", flat=True)
        )
        unknown = recover_ids - pending_ids
        if unknown:
            raise ValidationError(
                {
                    "recover": (
                        "Alcune occorrenze non sono in attesa: "
                        + ", ".join(str(value) for value in sorted(unknown))
                    )
                }
            )
        outcome = resolve_pending(automation, recover_ids)
        automation.refresh_from_db()
        return Response(
            {
                "outcome": outcome,
                "automation": AutomationSerializer(automation).data,
            }
        )


class AutomationExecutionListView(FinanceView):
    def get(self, request):
        profile = self.get_profile(request)
        queryset = AutomationExecution.objects.filter(profile=profile)
        automation_id = request.query_params.get("automation")
        status_filter = request.query_params.get("status")
        if automation_id:
            queryset = queryset.filter(automation_ref=automation_id)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        try:
            limit = min(max(int(request.query_params.get("limit", 100)), 1), 500)
        except (TypeError, ValueError):
            limit = 100
        total = queryset.count()
        return Response(
            {
                "executions": AutomationExecutionSerializer(
                    queryset[:limit], many=True
                ).data,
                "count": total,
            }
        )


class NotificationListView(FinanceView):
    def get(self, request):
        profile = self.get_profile(request)
        queryset = Notification.objects.filter(profile=profile)
        if request.query_params.get("unread") in {"1", "true", "yes"}:
            queryset = queryset.filter(read_at__isnull=True)
        unread_count = Notification.objects.filter(
            profile=profile, read_at__isnull=True
        ).count()
        try:
            limit = min(max(int(request.query_params.get("limit", 50)), 1), 200)
        except (TypeError, ValueError):
            limit = 50
        return Response(
            {
                "notifications": NotificationSerializer(
                    queryset[:limit], many=True
                ).data,
                "unread_count": unread_count,
            }
        )


class NotificationReadView(FinanceView):
    def post(self, request):
        profile = self.get_profile(request)
        queryset = Notification.objects.filter(
            profile=profile, read_at__isnull=True
        )
        ids = request.data.get("ids")
        if ids is not None:
            if not isinstance(ids, list):
                raise ValidationError({"ids": "Indica una lista di notifiche."})
            try:
                ids = [int(value) for value in ids]
            except (TypeError, ValueError) as exc:
                raise ValidationError(
                    {"ids": "Gli identificatori devono essere numeri."}
                ) from exc
            queryset = queryset.filter(pk__in=ids)
        queryset.update(read_at=timezone.now())
        unread_count = Notification.objects.filter(
            profile=profile, read_at__isnull=True
        ).count()
        return Response({"unread_count": unread_count})
