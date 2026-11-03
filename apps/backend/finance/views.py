from datetime import date

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ZERO, Account, Line, Profile, SavingsAccount, Transaction
from .services import assert_accounts_non_negative
from .serializers import (
    AccountCreateSerializer,
    AccountSerializer,
    AccountUpdateSerializer,
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
        period_balance = (
            Line.objects.filter(
                account__profile=profile,
                transaction__date__gte=start,
                transaction__date__lte=end,
            )
            .exclude(transaction__kind=Transaction.Kind.OPENING)
            .aggregate(total=Sum("amount"))["total"]
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
            limit = min(int(request.query_params.get("limit", 100)), 500)
        except (TypeError, ValueError):
            limit = 100
        return Response(
            {
                "transactions": TransactionSerializer(
                    queryset[:limit], many=True
                ).data
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
        operation.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
