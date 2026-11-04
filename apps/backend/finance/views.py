from datetime import date

from django.db import transaction
from django.db.models import Sum
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
from .models import (
    ZERO,
    Account,
    AutomationExecution,
    Line,
    Notification,
    Profile,
    SavingsAccount,
    Automation,
    Transaction,
)
from .services import assert_accounts_non_negative
from .serializers import (
    AccountCreateSerializer,
    AccountSerializer,
    AccountUpdateSerializer,
    AutomationExecutionSerializer,
    AutomationSerializer,
    AutomationWriteSerializer,
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
        profile, _ = Profile.objects.get_or_create(
            user=request.user,
            defaults={"display_name": request.user.email or request.user.username or ""},
        )
        return profile


class ProfileView(FinanceView):
    def get(self, request):
        profile = self.get_profile(request)
        return Response(ProfileSerializer(profile).data)


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

        total_balance = sum((account.balance for account in accounts), ZERO)
        total_savings = sum((savings_account.balance for savings_account in savings), ZERO)
        # The period balance is the variation of the total balance, so the
        # account openings inside the period count too (DC-012, REQ-DASH-05).
        period_balance = (
            Line.objects.filter(
                account__profile=profile,
                transaction__date__gte=start,
                transaction__date__lte=end,
            ).aggregate(total=Sum("amount"))["total"]
            or ZERO
        )
        income_total = (
            Transaction.objects.filter(
                profile=profile,
                kind=Transaction.Kind.INCOME,
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
            .prefetch_related("lines__account", "lines__savings")
            .order_by("-date", "-id")[:10]
        )

        return Response(
            {
                "total_balance": f"{total_balance:.2f}",
                "total_savings": f"{total_savings:.2f}",
                "total_patrimony": f"{total_balance + total_savings:.2f}",
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
    def _parse_date(value, default: date) -> date:
        if not value:
            return default
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise ValidationError({"detail": f"Data non valida: {value}."}) from exc


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
        serializer.save()
        return Response(AccountSerializer(account).data)

    def delete(self, request, pk: int):
        account = self.get_object(request, pk)
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
        account.delete()
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
            if balance != ZERO:
                transfer = Transaction.objects.create(
                    profile=savings.profile,
                    kind=Transaction.Kind.TRANSFER,
                    date=timezone.localdate(),
                    description=f"Saldo residuo salvadanaio {savings.name}",
                    amount=abs(balance),
                )
                Line.objects.create(
                    transaction=transfer,
                    account=savings.backing_account,
                    amount=balance,
                    role=Line.Role.TRANSFER_IN
                    if balance > ZERO
                    else Line.Role.TRANSFER_OUT,
                )
            savings.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class TransactionListCreateView(FinanceView):
    def get(self, request):
        profile = self.get_profile(request)
        queryset = (
            Transaction.objects.filter(profile=profile)
            .prefetch_related("lines__account", "lines__savings")
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
        if account_id or savings_id:
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
        operation = Transaction.objects.prefetch_related(
            "lines__account", "lines__savings"
        ).get(pk=operation.pk)
        return Response(
            TransactionSerializer(operation).data, status=status.HTTP_201_CREATED
        )


class TransactionDetailView(FinanceView):
    def get_object(self, request, pk: int) -> Transaction:
        profile = self.get_profile(request)
        try:
            return Transaction.objects.prefetch_related(
                "lines__account", "lines__savings"
            ).get(pk=pk, profile=profile)
        except Transaction.DoesNotExist as exc:
            raise ValidationError({"detail": "Movimento non trovato."}) from exc

    def get(self, request, pk: int):
        return Response(TransactionSerializer(self.get_object(request, pk)).data)

    def patch(self, request, pk: int):
        operation = self.get_object(request, pk)
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
        operation = Transaction.objects.prefetch_related(
            "lines__account", "lines__savings"
        ).get(pk=operation.pk)
        AutomationExecution.objects.filter(transaction=operation).update(
            corrected=True, updated_at=timezone.now()
        )
        return Response(TransactionSerializer(operation).data)

    def delete(self, request, pk: int):
        operation = self.get_object(request, pk)
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
            operation.delete()
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
            automation.delete()
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
