"""Accounting service for investment positions (DC-082/DC-083).

Derived values are never stored: the ledger is rebuilt from the operations
ordered by ``(date, id)`` every time. Money is rounded to 2 decimals with
commercial rounding (DC-015), quantities and unit prices to 8 decimals.
"""

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.db import transaction
from rest_framework.exceptions import ValidationError

from .models import (
    ZERO,
    Account,
    InvestmentOperation,
    InvestmentPosition,
    Line,
    Profile,
    SavingsAccount,
    Transaction,
)
from .services import assert_accounts_non_negative, savings_balance

MONEY = Decimal("0.01")
QUANTITY = Decimal("0.00000001")
UNSET = object()

KIND_TRANSACTION = {
    InvestmentOperation.Kind.BUY: Transaction.Kind.INVESTMENT_BUY,
    InvestmentOperation.Kind.SELL: Transaction.Kind.INVESTMENT_SELL,
    InvestmentOperation.Kind.DIVIDEND: Transaction.Kind.INVESTMENT_DIVIDEND,
}
KIND_LABEL = {
    InvestmentOperation.Kind.OPENING: "Apertura",
    InvestmentOperation.Kind.BUY: "Acquisto",
    InvestmentOperation.Kind.SELL: "Vendita",
    InvestmentOperation.Kind.DIVIDEND: "Dividendo",
}
INVESTMENT_TRANSACTION_KINDS = tuple(KIND_TRANSACTION.values())


def money(value) -> Decimal:
    return Decimal(value).quantize(MONEY, rounding=ROUND_HALF_UP)


def quantity(value) -> Decimal:
    return Decimal(value).quantize(QUANTITY, rounding=ROUND_HALF_UP)


def _error(field: str, message: str, code: str) -> ValidationError:
    return ValidationError({field: message, "code": code})


def _validate_quantity(raw) -> Decimal:
    if raw is None:
        raise _error("quantity", "La quantità è obbligatoria.", "invalid_quantity")
    value = quantity(raw)
    if value <= 0:
        raise _error("quantity", "La quantità deve essere maggiore di zero.", "invalid_quantity")
    return value


def _validate_commission(raw) -> Decimal:
    value = money(raw or ZERO)
    if value < ZERO:
        raise _error(
            "commission", "La commissione non può essere negativa.", "invalid_commission"
        )
    return value


def _resolve_price(raw_quantity, unit_price, total_amount):
    """Return quantity, unit price (8 dec) and gross amount (2 dec).

    Servono due valori su tre (quantità, prezzo unitario, controvalore); il
    terzo si ricava sempre.
    """
    provided = [
        value
        for value in (raw_quantity, unit_price, total_amount)
        if value is not None
    ]
    if len(provided) < 2:
        raise _error(
            "quantity",
            "Indica due valori tra quantità, prezzo unitario e controvalore.",
            "missing_price",
        )
    if len(provided) > 2:
        raise _error(
            "unit_price",
            "Indica solo due valori tra quantità, prezzo unitario e controvalore.",
            "ambiguous_price",
        )

    if raw_quantity is not None and unit_price is not None:
        qty = _validate_quantity(raw_quantity)
        price = quantity(unit_price)
        if price <= 0:
            raise _error(
                "unit_price",
                "Il prezzo unitario deve essere maggiore di zero.",
                "invalid_unit_price",
            )
        try:
            gross = money(qty * price)
        except (InvalidOperation, OverflowError):
            raise _error(
                "unit_price",
                "Il controvalore calcolato è troppo grande.",
                "invalid_unit_price",
            )
    elif raw_quantity is not None:
        qty = _validate_quantity(raw_quantity)
        gross = money(total_amount)
        if gross <= 0:
            raise _error(
                "total_amount",
                "Il controvalore deve essere maggiore di zero.",
                "invalid_total_amount",
            )
        try:
            price = (gross / qty).quantize(QUANTITY, rounding=ROUND_HALF_UP)
        except (InvalidOperation, OverflowError):
            raise _error(
                "total_amount",
                "Il prezzo calcolato è troppo grande.",
                "invalid_total_amount",
            )
    else:
        price = quantity(unit_price)
        if price <= 0:
            raise _error(
                "unit_price",
                "Il prezzo unitario deve essere maggiore di zero.",
                "invalid_unit_price",
            )
        gross = money(total_amount)
        if gross <= 0:
            raise _error(
                "total_amount",
                "Il controvalore deve essere maggiore di zero.",
                "invalid_total_amount",
            )
        try:
            qty = (gross / price).quantize(QUANTITY, rounding=ROUND_HALF_UP)
        except (InvalidOperation, OverflowError):
            raise _error(
                "quantity",
                "La quantità calcolata è troppo grande.",
                "invalid_quantity",
            )
        if qty <= 0:
            raise _error(
                "quantity",
                "La quantità calcolata deve essere maggiore di zero.",
                "invalid_quantity",
            )
    if gross <= 0:
        raise _error(
            "total_amount",
            "Il controvalore deve essere maggiore di zero.",
            "invalid_total_amount",
        )
    return qty, price, gross


def _operation_values(kind, *, quantity_value, unit_price, total_amount, commission, amount):
    """Normalize user input into stored operation fields."""
    if kind == InvestmentOperation.Kind.DIVIDEND:
        if quantity_value is not None or unit_price is not None or total_amount is not None:
            raise _error(
                "quantity",
                "Il dividendo non prevede quantità o prezzo.",
                "invalid_dividend",
            )
        if amount is None:
            raise _error("amount", "L'importo è obbligatorio.", "invalid_amount")
        cash = money(amount)
        if cash <= 0:
            raise _error(
                "amount", "L'importo deve essere maggiore di zero.", "invalid_amount"
            )
        return {
            "quantity": None,
            "unit_price": None,
            "gross_amount": None,
            "commission": ZERO,
            "cash_amount": cash,
        }

    qty, price, gross = _resolve_price(quantity_value, unit_price, total_amount)
    if kind == InvestmentOperation.Kind.OPENING:
        fee = ZERO
        cash = ZERO
    else:
        fee = _validate_commission(commission)
        cash = money(gross + fee) if kind == InvestmentOperation.Kind.BUY else money(
            gross - fee
        )
        if cash <= 0:
            raise _error(
                "commission",
                "La commissione non può raggiungere il controvalore.",
                "invalid_commission",
            )
    return {
        "quantity": qty,
        "unit_price": price,
        "gross_amount": gross,
        "commission": fee,
        "cash_amount": cash,
    }


def _description(position, kind, description) -> str:
    return description or f"{position.name} · {KIND_LABEL[kind]}"


def _investment_source(profile: Profile) -> tuple[str, SavingsAccount | None, Account]:
    """Fonte del denaro: un conto, oppure un salvadanaio (via conto di appoggio)."""
    if profile.investment_savings_id is not None:
        savings = profile.investment_savings
        account = savings.backing_account
        if account.archived:
            raise _error(
                "account",
                "Il conto di appoggio del salvadanaio è archiviato.",
                "archived_investment_account",
            )
        return "savings", savings, account
    account = profile.investment_account
    if account is None:
        raise _error(
            "account",
            "Scegli un conto (o un salvadanaio) per gli investimenti prima di "
            "registrare l'operazione.",
            "missing_investment_account",
        )
    if account.archived:
        raise _error(
            "account",
            "Il conto degli investimenti è archiviato.",
            "archived_investment_account",
        )
    return "account", None, account


def _signed_cash(kind, cash: Decimal) -> Decimal:
    if kind == InvestmentOperation.Kind.BUY:
        return -cash
    return cash


def _operation_account(operation: InvestmentOperation) -> Account:
    line = (
        operation.transaction.lines.filter(
            role=Line.Role.PRINCIPAL, account__isnull=False
        )
        .order_by("-id")
        .first()
    )
    return line.account


def recalculate_position(position: InvestmentPosition) -> dict:
    """Rebuild quantity, cost and gains from the operations of a position."""
    operations = list(position.operations.order_by("date", "id"))
    held = Decimal("0.00000000")
    cost = ZERO
    realized = ZERO
    dividends = ZERO
    rows = []
    opening_seen = False

    for index, operation in enumerate(operations):
        kind = operation.kind
        row = {
            "operation": operation,
            "quantity_after": held,
            "cost_after": cost,
            "cost_removed": ZERO,
            "realized_gain": ZERO,
            "cash_flow": ZERO,
        }
        if kind == InvestmentOperation.Kind.OPENING:
            if opening_seen or index != 0:
                raise _error(
                    "kind",
                    "L'apertura deve essere la prima e unica operazione di apertura.",
                    "invalid_opening",
                )
            opening_seen = True
            held = quantity(operation.quantity)
            cost = money(operation.gross_amount)
        elif kind == InvestmentOperation.Kind.BUY:
            held = quantity(held + quantity(operation.quantity))
            cost = money(cost + money(operation.gross_amount) + money(operation.commission))
            row["cash_flow"] = -money(operation.cash_amount)
        elif kind == InvestmentOperation.Kind.SELL:
            sold = quantity(operation.quantity)
            if sold > held:
                raise _error(
                    "quantity",
                    "Vendita superiore alla quantità posseduta alla data dell'operazione.",
                    "insufficient_quantity",
                )
            removed = cost if sold == held else money(cost * sold / held)
            held = quantity(held - sold)
            cost = ZERO if held == 0 else money(cost - removed)
            gain = money(money(operation.cash_amount) - removed)
            realized = money(realized + gain)
            row["cost_removed"] = removed
            row["realized_gain"] = gain
            row["cash_flow"] = money(operation.cash_amount)
        elif kind == InvestmentOperation.Kind.DIVIDEND:
            dividends = money(dividends + money(operation.cash_amount))
            row["cash_flow"] = money(operation.cash_amount)
        else:  # pragma: no cover - guarded by the model choices
            raise _error("kind", "Tipo di operazione non valido.", "invalid_kind")

        row["quantity_after"] = held
        row["cost_after"] = cost
        rows.append(row)

    current_value = None
    unrealized = None
    if position.current_price is not None:
        current_value = money(held * quantity(position.current_price))
        unrealized = money(current_value - cost)
    average_cost = ZERO if held == 0 else (cost / held).quantize(
        QUANTITY, rounding=ROUND_HALF_UP
    )
    return {
        "quantity": held,
        "cost": cost,
        "average_cost": average_cost,
        "current_value": current_value,
        "unrealized_gain": unrealized,
        "realized_gain": realized,
        "dividends": dividends,
        "has_price": position.current_price is not None,
        "operations": rows,
    }


def position_summary(position: InvestmentPosition) -> dict:
    return recalculate_position(position)


def portfolio_summary(profile: Profile) -> dict:
    """Aggregate the summaries of every position of a profile."""
    total_cost = ZERO
    total_value = ZERO
    total_unrealized = ZERO
    realized = ZERO
    dividends = ZERO
    without_price = 0
    for position in profile.investment_positions.all():
        ledger = recalculate_position(position)
        total_cost = money(total_cost + ledger["cost"])
        realized = money(realized + ledger["realized_gain"])
        dividends = money(dividends + ledger["dividends"])
        if ledger["current_value"] is None:
            without_price += 1
        else:
            total_value = money(total_value + ledger["current_value"])
            total_unrealized = money(total_unrealized + ledger["unrealized_gain"])
    return {
        "total_cost": total_cost,
        "total_value": total_value,
        "total_unrealized": total_unrealized,
        "positions_without_price": without_price,
        "realized_gain": realized,
        "dividends": dividends,
    }


def set_investment_source(profile: Profile, *, account=None, savings=None) -> Profile:
    """Imposta la fonte unica del denaro: un conto oppure un salvadanaio."""
    with transaction.atomic():
        locked = Profile.objects.select_for_update().get(pk=profile.pk)
        if savings is not None:
            if not isinstance(savings, SavingsAccount):
                savings = SavingsAccount.objects.get(pk=savings)
            if savings.profile_id != locked.pk:
                raise _error(
                    "savings",
                    "Il salvadanaio deve appartenere allo stesso profilo.",
                    "savings_profile_mismatch",
                )
            if savings.backing_account.archived:
                raise _error(
                    "savings",
                    "Il conto di appoggio del salvadanaio è archiviato.",
                    "archived_investment_account",
                )
            locked.investment_savings = savings
            locked.investment_account = None
            locked.save(
                update_fields=("investment_savings", "investment_account")
            )
            return locked
        if account is not None:
            if not isinstance(account, Account):
                account = Account.objects.get(pk=account)
            if account.profile_id != locked.pk:
                raise _error(
                    "investment_account",
                    "Il conto deve appartenere allo stesso profilo.",
                    "account_profile_mismatch",
                )
            if account.archived:
                raise _error(
                    "investment_account",
                    "Il conto degli investimenti non può essere archiviato.",
                    "archived_investment_account",
                )
        locked.investment_account = account
        locked.investment_savings = None
        locked.save(update_fields=("investment_account", "investment_savings"))
        return locked


def set_investment_account(profile: Profile, account) -> Profile:
    return set_investment_source(profile, account=account)


def set_position_archived(position: InvestmentPosition, archived: bool) -> InvestmentPosition:
    with transaction.atomic():
        locked = InvestmentPosition.objects.select_for_update().get(pk=position.pk)
        if archived:
            ledger = recalculate_position(locked)
            if ledger["quantity"] != 0:
                raise _error(
                    "archived",
                    "Puoi archiviare la posizione solo quando la quantità è zero.",
                    "position_still_open",
                )
        locked.archived = archived
        locked.save(update_fields=("archived",))
        return locked


def _lock_position(position: InvestmentPosition) -> InvestmentPosition:
    # No select_related here: investment_account is a nullable FK and PostgreSQL
    # rejects FOR UPDATE on the nullable side of an outer join.
    return InvestmentPosition.objects.select_for_update().get(pk=position.pk)


def _sync_archived(position: InvestmentPosition) -> None:
    """Una posizione chiusa (quantità zero) si archivia da sola.

    Riaprirla con un'operazione o eliminare la vendita che l'aveva chiusa la
    riporta tra le attive.
    """
    ledger = recalculate_position(position)
    quantity = ledger["quantity"]
    if quantity == 0 and position.operations.exists():
        if not position.archived:
            position.archived = True
            position.save(update_fields=("archived",))
    elif quantity > 0 and position.archived:
        position.archived = False
        position.save(update_fields=("archived",))


def _create_transaction(position, kind, day, amount, description):
    source_kind, savings, account = _investment_source(position.profile)
    signed = _signed_cash(kind, amount)
    movement = Transaction.objects.create(
        profile=position.profile,
        kind=KIND_TRANSACTION[kind],
        date=day,
        description=_description(position, kind, description),
        amount=amount,
    )
    if source_kind == "savings" and savings is not None:
        # Come una spesa dal salvadanaio: il conto di appoggio fa da ponte
        # (uscite tecniche compensate), il saldo del salvadanaio cambia.
        if signed < ZERO:
            available = savings_balance(savings)
            if available < amount:
                raise _error(
                    "savings",
                    "Saldo del salvadanaio insufficiente: disponibili "
                    f"{available:.2f}.",
                    "insufficient_savings",
                )
        Line.objects.create(
            transaction=movement,
            savings=savings,
            amount=signed,
            role=Line.Role.PRINCIPAL,
        )
        Line.objects.create(
            transaction=movement,
            account=account,
            amount=-signed,
            role=Line.Role.TECHNICAL,
        )
        Line.objects.create(
            transaction=movement,
            account=account,
            amount=signed,
            role=Line.Role.PRINCIPAL,
        )
        return movement
    assert_accounts_non_negative([(account, signed, day)])
    Line.objects.create(
        transaction=movement,
        account=account,
        amount=signed,
        role=Line.Role.PRINCIPAL,
    )
    return movement


def create_operation(
    position: InvestmentPosition,
    *,
    kind: str,
    date,
    quantity=None,
    unit_price=None,
    total_amount=None,
    commission=None,
    amount=None,
    description="",
) -> InvestmentOperation:
    """Create an opening, buy, sell or dividend and its account movement."""
    if kind not in InvestmentOperation.Kind.values:
        raise _error("kind", "Tipo di operazione non valido.", "invalid_kind")
    with transaction.atomic():
        locked = _lock_position(position)
        if locked.archived:
            raise _error(
                "position", "La posizione è archiviata.", "archived_position"
            )
        if kind == InvestmentOperation.Kind.OPENING and locked.operations.exists():
            raise _error(
                "kind",
                "L'apertura è consentita solo quando la posizione non ha altre operazioni.",
                "opening_not_first",
            )
        values = _operation_values(
            kind,
            quantity_value=quantity,
            unit_price=unit_price,
            total_amount=total_amount,
            commission=commission,
            amount=amount,
        )
        operation = InvestmentOperation(
            profile=locked.profile,
            position=locked,
            kind=kind,
            date=date,
            description=description,
            **values,
        )
        if kind != InvestmentOperation.Kind.OPENING:
            operation.transaction = _create_transaction(
                locked, kind, date, values["cash_amount"], description
            )
        operation.save()
        recalculate_position(locked)
        _sync_archived(locked)
        return operation


def update_operation(operation: InvestmentOperation, **changes) -> InvestmentOperation:
    """Update an operation, keeping its kind and account, then recalculate."""
    with transaction.atomic():
        position = _lock_position(operation.position)
        locked = InvestmentOperation.objects.select_related("transaction").get(
            pk=operation.pk
        )
        kind = locked.kind
        day = changes.get("date", locked.date)
        description = changes.get("description", locked.description)

        if kind == InvestmentOperation.Kind.DIVIDEND:
            if {"quantity", "unit_price", "total_amount"} & changes.keys():
                raise _error(
                    "quantity",
                    "Il dividendo non prevede quantità o prezzo.",
                    "invalid_dividend",
                )
            values = _operation_values(
                kind,
                quantity_value=None,
                unit_price=None,
                total_amount=None,
                commission=None,
                amount=changes.get("amount", locked.cash_amount),
            )
        else:
            explicit = {
                key: changes[key]
                for key in ("quantity", "unit_price", "total_amount")
                if key in changes
            }
            if len(explicit) == 3:
                raise _error(
                    "unit_price",
                    "Indica solo due valori tra quantità, prezzo unitario e "
                    "controvalore.",
                    "ambiguous_price",
                )
            if len(explicit) == 2:
                q_input = explicit.get("quantity")
                p_input = explicit.get("unit_price")
                t_input = explicit.get("total_amount")
            elif "quantity" in explicit:
                q_input = explicit["quantity"]
                p_input = locked.unit_price
                t_input = None
            elif "unit_price" in explicit:
                q_input = locked.quantity
                p_input = explicit["unit_price"]
                t_input = None
            elif "total_amount" in explicit:
                q_input = locked.quantity
                p_input = None
                t_input = explicit["total_amount"]
            else:
                q_input = locked.quantity
                p_input = None
                t_input = locked.gross_amount
            values = _operation_values(
                kind,
                quantity_value=q_input,
                unit_price=p_input,
                total_amount=t_input,
                commission=changes.get("commission", locked.commission),
                amount=None,
            )

        movement = locked.transaction
        if movement is not None:
            account = _operation_account(locked)
            signed = _signed_cash(kind, values["cash_amount"])
            savings_line = (
                movement.lines.filter(savings__isnull=False).first()
            )
            if savings_line is None:
                assert_accounts_non_negative(
                    [(account, signed, day)], exclude_transaction=movement
                )
            elif signed < ZERO:
                available = savings_balance(
                    savings_line.savings, exclude_transaction=movement
                )
                if available < -signed:
                    raise _error(
                        "savings",
                        "Saldo del salvadanaio insufficiente: disponibili "
                        f"{available:.2f}.",
                        "insufficient_savings",
                    )
            movement.date = day
            movement.amount = values["cash_amount"]
            if "description" in changes:
                movement.description = _description(position, kind, description)
            movement.save(update_fields=("date", "amount", "description"))
            for line in movement.lines.all():
                line.amount = (
                    -signed if line.role == Line.Role.TECHNICAL else signed
                )
                line.save(update_fields=("amount",))

        for field, value in values.items():
            setattr(locked, field, value)
        locked.date = day
        locked.description = description
        locked.save()
        recalculate_position(position)
        _sync_archived(position)
        return locked


def delete_operation(operation: InvestmentOperation, user=None) -> None:
    """Soft-delete an operation and its account movement (DC-088)."""
    with transaction.atomic():
        position = _lock_position(operation.position)
        locked = InvestmentOperation.objects.select_related("transaction").get(
            pk=operation.pk
        )
        movement = locked.transaction
        if movement is not None:
            assert_accounts_non_negative(
                accounts=[_operation_account(locked)], exclude_transaction=movement
            )
        locked.soft_delete(user)
        if movement is not None:
            movement.soft_delete(user)
        recalculate_position(position)
        _sync_archived(position)
