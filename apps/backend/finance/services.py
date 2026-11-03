from collections import defaultdict
from datetime import date
from decimal import Decimal

from django.db.models import Sum
from rest_framework.exceptions import ValidationError

from .models import ZERO, Account, Line, SavingsAccount


def format_money(value: Decimal) -> str:
    return f"{value:.2f}".replace(".", ",")


def account_balance(account: Account) -> Decimal:
    return account.lines.aggregate(total=Sum("amount"))["total"] or ZERO


def savings_balance(savings: SavingsAccount, exclude_transaction=None) -> Decimal:
    queryset = savings.lines.all()
    if exclude_transaction is not None:
        queryset = queryset.exclude(transaction=exclude_transaction)
    return queryset.aggregate(total=Sum("amount"))["total"] or ZERO


def running_minimum(points: dict[date, Decimal]) -> Decimal:
    """Lowest running balance over a timeline, never above zero.

    The timeline starts from zero: an account with no movements has a
    minimum of zero, which is exactly the ``min(0, actual)`` bound used to
    allow operations on accounts that were already negative before DC-069.
    """
    total = ZERO
    minimum = ZERO
    for day in sorted(points):
        total += points[day]
        if total < minimum:
            minimum = total
    return minimum


def first_negative_point(points: dict[date, Decimal]):
    """First date where the running balance drops below zero."""
    total = ZERO
    for day in sorted(points):
        total += points[day]
        if total < ZERO:
            return day, total
    return None, None


def assert_accounts_non_negative(
    proposed_lines=(),
    *,
    exclude_transaction=None,
    accounts=None,
):
    """Reject operations that would make an account balance negative (DC-069).

    The check is chronological: every point of the account timeline must stay
    at zero or above, not just the final balance. Accounts that were already
    negative before this rule may still be corrected as long as the operation
    does not make their minimum worse.
    """
    proposed: dict[int, dict[date, Decimal]] = defaultdict(
        lambda: defaultdict(lambda: ZERO)
    )
    targets: dict[int, Account] = {}

    for account, amount, day in proposed_lines:
        proposed[account.id][day] += amount
        targets[account.id] = account
    for account in accounts or ():
        targets[account.id] = account

    excluded: dict[int, dict[date, Decimal]] = defaultdict(
        lambda: defaultdict(lambda: ZERO)
    )
    if exclude_transaction is not None:
        for line in exclude_transaction.lines.all():
            if line.account_id is not None:
                excluded[line.account_id][exclude_transaction.date] += line.amount

    for account_id, account in targets.items():
        rows = Line.objects.filter(account=account).values_list(
            "transaction__date", "amount", "transaction_id"
        )
        current: dict[date, Decimal] = defaultdict(lambda: ZERO)
        after: dict[date, Decimal] = defaultdict(lambda: ZERO)
        for day, amount, transaction_id in rows:
            current[day] += amount
            if exclude_transaction is None or transaction_id != exclude_transaction.id:
                after[day] += amount
        for day, amount in proposed.get(account_id, {}).items():
            after[day] += amount

        current_minimum = running_minimum(current)
        after_minimum = running_minimum(after)
        if after_minimum >= min(ZERO, current_minimum):
            continue

        day, running = first_negative_point(after)
        if day is None:
            day, running = (max(after) if after else None), after_minimum
        available = (
            running
            - proposed.get(account_id, {}).get(day, ZERO)
            + excluded.get(account_id, {}).get(day, ZERO)
        )
        if day is not None and available >= ZERO:
            message = (
                f"Saldo insufficiente sul conto {account.name}: disponibili "
                f"{format_money(available)} al {day:%d-%m-%Y}."
            )
        elif day is not None:
            message = (
                f"Saldo insufficiente sul conto {account.name}: al "
                f"{day:%d-%m-%Y} il saldo risultante è "
                f"{format_money(available)}."
            )
        else:
            message = (
                f"Saldo insufficiente sul conto {account.name}: il saldo "
                f"risultante è {format_money(available)}."
            )
        raise ValidationError(
            {
                "amount": message,
                "code": "insufficient_account_balance",
                "available": f"{available:.2f}",
                "date": day.isoformat() if day else None,
            }
        )
