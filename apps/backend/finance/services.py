from decimal import Decimal

from django.db.models import Sum

from .models import ZERO, Account, SavingsAccount


def account_balance(account: Account) -> Decimal:
    return account.lines.aggregate(total=Sum("amount"))["total"] or ZERO


def savings_balance(savings: SavingsAccount, exclude_transaction=None) -> Decimal:
    queryset = savings.lines.all()
    if exclude_transaction is not None:
        queryset = queryset.exclude(transaction=exclude_transaction)
    return queryset.aggregate(total=Sum("amount"))["total"] or ZERO
