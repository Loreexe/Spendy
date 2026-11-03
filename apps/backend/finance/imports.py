"""CSV import of historical movements (DC-070, DC-071).

The parser and the analyzer are pure enough to be tested without a request:
``parse_csv`` turns the uploaded bytes into raw rows, ``analyze`` validates
them against the profile and ``confirm`` writes the accepted rows atomically.
Nothing is written to disk and nothing is stored before the confirmation.
"""
from __future__ import annotations

import csv
import io
import re
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal
from difflib import SequenceMatcher

from django.db import transaction as db_transaction
from django.db.models import Min, Sum
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import ZERO, Account, Line, Profile, Transaction
from .services import (
    assert_accounts_non_negative,
    first_negative_point,
    format_money,
    running_minimum,
)

HEADER = ("data", "descrizione", "categoria", "conto", "importo")
SEPARATOR = ";"
MAX_ROWS = 5000
MAX_BYTES = 5 * 1024 * 1024
TEMPLATE_FILENAME = "spendy-modello-movimenti.csv"
SIMILAR_RATIO = 0.85

DATE_FORMATS = {
    "DD-MM-YYYY": ("%d-%m-%Y", r"^\d{2}-\d{2}-\d{4}$"),
    "DD/MM/YYYY": ("%d/%m/%Y", r"^\d{2}/\d{2}/\d{4}$"),
    "YYYY-MM-DD": ("%Y-%m-%d", r"^\d{4}-\d{2}-\d{2}$"),
    "YYYY/MM/DD": ("%Y/%m/%d", r"^\d{4}/\d{2}/\d{2}$"),
    "DD.MM.YYYY": ("%d.%m.%Y", r"^\d{2}\.\d{2}\.\d{4}$"),
    "MM-DD-YYYY": ("%m-%d-%Y", r"^\d{2}-\d{2}-\d{4}$"),
    "MM/DD/YYYY": ("%m/%d/%Y", r"^\d{2}/\d{2}/\d{4}$"),
}
DEFAULT_DATE_FORMAT = "DD-MM-YYYY"
DELIMITERS = (";", ",", "\t", "|")
DECIMAL_SEPARATORS = (",", ".")


# --------------------------------------------------------------------------- #
# Template
# --------------------------------------------------------------------------- #


def _example_rows():
    today = timezone.localdate()
    # A day above 12 keeps spreadsheets from guessing the date order.
    example = today.replace(day=25).strftime("%d-%m-%Y")
    return [
        [example, "ESEMPIO — spesa di prova", "esempio", "Contanti", "12,50"],
        [example, "ESEMPIO — entrata di prova", "esempio", "Contanti", "-100,00"],
    ]


def build_template() -> bytes:
    """Downloadable model: UTF-8 with BOM, CRLF and ';' like Excel writes it."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=SEPARATOR, lineterminator="\r\n")
    writer.writerow(HEADER)
    writer.writerows(_example_rows())
    return b"\xef\xbb\xbf" + buffer.getvalue().encode("utf-8")


# --------------------------------------------------------------------------- #
# Format detection
# --------------------------------------------------------------------------- #


def detect_delimiter(text: str) -> str:
    lines = [line for line in text.splitlines() if line.strip()][:30]
    if not lines:
        return SEPARATOR
    best = SEPARATOR
    best_score = (-1.0, False)
    for candidate in DELIMITERS:
        rows = list(csv.reader(lines, delimiter=candidate))
        if not rows:
            continue
        filled = sum(1 for row in rows if len(row) == len(HEADER))
        header_ok = tuple(
            cell.strip().casefold() for cell in rows[0]
        ) == HEADER
        score = (filled / len(rows), header_ok)
        if score > best_score:
            best, best_score = candidate, score
    return best


def detect_date_format(values) -> tuple[str, bool]:
    """Return (format, ambiguous). Ambiguous when DD and MM both fit."""
    dates = [value for value in values if value]
    if not dates:
        return DEFAULT_DATE_FORMAT, False
    candidates = []
    for name, (fmt, pattern) in DATE_FORMATS.items():
        matched = 0
        for value in dates:
            if not re.match(pattern, value):
                continue
            try:
                datetime.strptime(value, fmt)
            except ValueError:
                continue
            matched += 1
        if matched == len(dates):
            candidates.append(name)
    if not candidates:
        return DEFAULT_DATE_FORMAT, False
    preferred = next(
        (
            name
            for name in DATE_FORMATS
            if name in candidates and not name.startswith("MM")
        ),
        candidates[0],
    )
    return preferred, len(candidates) > 1


def detect_decimal_separator(values) -> str:
    comma = dot = 0
    for value in values:
        if re.match(r"^-?\d{1,10},\d{2}$", value):
            comma += 1
        elif re.match(r"^-?\d{1,10}\.\d{2}$", value):
            dot += 1
    if comma == dot:
        return ","
    return "," if comma > dot else "."


# --------------------------------------------------------------------------- #
# Parsing
# --------------------------------------------------------------------------- #


def _file_error(row: int, code: str, message: str) -> dict:
    return {"row": row, "field": "file", "code": code, "message": message}


def parse_csv(raw: bytes, delimiter: str | None = None):
    """Return (raw rows, file errors, delimiter used)."""
    errors: list[dict] = []
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return [], [
            _file_error(
                1,
                "encoding",
                "Il file non è in UTF-8. Salvalo come «CSV UTF-8».",
            )
        ], delimiter or SEPARATOR

    used = delimiter or detect_delimiter(text)
    reader = csv.reader(io.StringIO(text), delimiter=used)
    rows: list[dict] = []
    header = None
    for line_number, cells in enumerate(reader, start=1):
        if not cells or all(not cell.strip() for cell in cells):
            continue
        if header is None:
            header = tuple(cell.strip().casefold() for cell in cells)
            if header != HEADER:
                return [], [
                    _file_error(
                        line_number,
                        "header",
                        "Intestazione non valida: usa il modello scaricato "
                        "(data;descrizione;categoria;conto;importo).",
                    )
                ], used
            continue
        if len(cells) != len(HEADER):
            errors.append(
                _file_error(
                    line_number,
                    "columns",
                    f"La riga ha {len(cells)} colonne invece di {len(HEADER)}.",
                )
            )
            continue
        rows.append(
            {
                "row_number": line_number,
                "date": cells[0].strip(),
                "description": cells[1].strip(),
                "category": cells[2].strip(),
                "account": cells[3].strip(),
                "amount": cells[4].strip(),
                "not_duplicate": False,
            }
        )

    if header is None:
        errors.append(_file_error(1, "empty", "Il file è vuoto o senza intestazione."))
    elif not rows and not errors:
        errors.append(_file_error(1, "empty", "Il file non contiene movimenti."))
    if len(rows) > MAX_ROWS:
        errors.append(
            _file_error(
                1,
                "too_many_rows",
                f"Troppe righe: il massimo è {MAX_ROWS} per file.",
            )
        )
    return rows, errors, used


def parse_date(value: str, date_format: str = DEFAULT_DATE_FORMAT):
    fmt, pattern = DATE_FORMATS.get(date_format, DATE_FORMATS[DEFAULT_DATE_FORMAT])
    if not re.match(pattern, value):
        return None, "La data non corrisponde al formato scelto."
    try:
        return datetime.strptime(value, fmt).date(), None
    except ValueError:
        return None, "La data non esiste."


def parse_amount(value: str, decimal_separator: str = ","):
    separator = decimal_separator if decimal_separator in DECIMAL_SEPARATORS else ","
    other = "." if separator == "," else ","
    label = "virgola" if separator == "," else "punto"
    if other in value:
        return None, (
            f"L'importo deve usare la {label} per i decimali, "
            "senza € e senza separatori delle migliaia."
        )
    pattern = rf"^-?\d{{1,10}}(?:{re.escape(separator)}\d{{1,2}})?$"
    if not re.match(pattern, value):
        example = "1234,56" if separator == "," else "1234.56"
        return None, (
            f"L'importo deve essere un numero con la {label} per i decimali "
            f"(es. 1234 o {example}), senza € e senza migliaia."
        )
    amount = Decimal(value.replace(separator, ".")).quantize(Decimal("0.01"))
    if amount == ZERO:
        return None, "L'importo non può essere zero."
    return amount, None


def normalize_name(value: str) -> str:
    return " ".join(value.split()).casefold()


# --------------------------------------------------------------------------- #
# Analysis
# --------------------------------------------------------------------------- #


def _add_error(row: dict, code: str, field: str, message: str) -> None:
    row["errors"].append({"code": code, "field": field, "message": message})


def _add_warning(row: dict, code: str, message: str) -> None:
    row["warnings"].append({"code": code, "message": message})


def _signed(row: dict) -> Decimal:
    if row["kind"] == "expense":
        return -row["amount_value"]
    return abs(row["amount_value"])


def _prepare_row(index: int, source: dict, date_format: str, decimal_separator: str) -> dict:
    row = {
        "index": index,
        "row_number": int(source.get("row_number") or index + 2),
        "date": str(source.get("date", "")).strip(),
        "description": str(source.get("description", "")).strip(),
        "category": str(source.get("category", "")).strip(),
        "account": str(source.get("account", "")).strip(),
        "amount": str(source.get("amount", "")).strip(),
        "not_duplicate": bool(source.get("not_duplicate")),
        "errors": [],
        "warnings": [],
        "kind": "expense",
        "valid": True,
        "date_value": None,
        "amount_value": None,
        "account_key": "",
    }

    parsed_date, message = parse_date(row["date"], date_format)
    if message:
        _add_error(row, "invalid_date", "date", message)
        row["valid"] = False
    else:
        row["date_value"] = parsed_date

    parsed_amount, message = parse_amount(row["amount"], decimal_separator)
    if message:
        _add_error(row, "invalid_amount", "amount", message)
        row["valid"] = False
    else:
        row["amount_value"] = parsed_amount

    if not row["account"]:
        _add_error(row, "missing_account", "account", "Indica il conto.")
        row["valid"] = False
    elif len(row["account"]) > 100:
        _add_error(
            row, "account_too_long", "account", "Il nome del conto supera 100 caratteri."
        )
        row["valid"] = False
    else:
        row["account_key"] = normalize_name(row["account"])

    if len(row["description"]) > 255:
        _add_error(
            row,
            "description_too_long",
            "description",
            "La descrizione supera 255 caratteri.",
        )
        row["valid"] = False

    if row["description"].upper().startswith("ESEMPIO"):
        _add_error(
            row,
            "example_row",
            "description",
            "Riga di esempio non rimossa: cancellala dal file.",
        )

    return row


def _similar_account(key: str, existing: dict) -> Account | None:
    best = None
    best_ratio = SIMILAR_RATIO
    for candidate_key, account in existing.items():
        ratio = SequenceMatcher(None, key, candidate_key).ratio()
        if ratio >= best_ratio:
            best, best_ratio = account, ratio
    return best


def _duplicate_key(row: dict) -> tuple:
    """Signed amount: an outgoing and an incoming row are never duplicates."""
    return (
        row["date_value"].isoformat(),
        f"{_signed(row):.2f}",
        normalize_name(row["description"]),
        row["account_key"],
    )


def _database_keys(profile: Profile, start: date, end: date) -> set[tuple]:
    keys: set[tuple] = set()
    queryset = (
        Transaction.objects.filter(
            profile=profile,
            kind__in=[Transaction.Kind.INCOME, Transaction.Kind.EXPENSE],
            date__gte=start,
            date__lte=end,
        )
        .prefetch_related("lines__account")
    )
    for operation in queryset:
        for line in operation.lines.all():
            if line.account_id and line.role == Line.Role.PRINCIPAL:
                keys.add(
                    (
                        operation.date.isoformat(),
                        f"{line.amount:.2f}",
                        normalize_name(operation.description),
                        normalize_name(line.account.name),
                    )
                )
    return keys


def _analyze(
    rows: list[dict],
    profile: Profile,
    file_errors=(),
    *,
    delimiter: str | None = None,
    date_format: str | None = None,
    decimal_separator: str | None = None,
):
    date_values = [str(row.get("date", "")).strip() for row in rows]
    amount_values = [str(row.get("amount", "")).strip() for row in rows]
    detected_format, ambiguous = detect_date_format(date_values)
    applied_date_format = date_format or detected_format
    applied_decimal = decimal_separator or detect_decimal_separator(amount_values)
    if applied_decimal not in DECIMAL_SEPARATORS:
        applied_decimal = ","

    prepared = [
        _prepare_row(index, row, applied_date_format, applied_decimal)
        for index, row in enumerate(rows)
    ]
    accounts = list(Account.objects.filter(profile=profile))
    existing = {normalize_name(account.name): account for account in accounts}

    names: dict[str, str] = {}
    for row in prepared:
        if row["account_key"]:
            names.setdefault(row["account_key"], row["account"])

    states: dict[str, tuple[str, Account | None]] = {}
    for key in names:
        if key in existing:
            states[key] = ("existing", existing[key])
        else:
            similar = _similar_account(key, existing)
            states[key] = ("similar", similar) if similar else ("new", None)

    for row in prepared:
        if row["account_key"] in states and states[row["account_key"]][0] == "similar":
            _add_warning(
                row,
                "similar_account",
                f"Il conto «{row['account']}» assomiglia a "
                f"«{states[row['account_key']][1].name}»: verifica il nome.",
            )

    by_account: dict[str, list[dict]] = defaultdict(list)
    for row in prepared:
        if row["valid"]:
            by_account[row["account_key"]].append(row)

    # Opening: a new account starts from zero, so its oldest row must be the
    # only negative one on its date and becomes the account opening. Accounts
    # that already exist keep their own opening and receive plain movements.
    for key, group in by_account.items():
        group.sort(key=lambda row: (row["date_value"], row["index"]))
        for row in group:
            row["kind"] = "expense" if row["amount_value"] > ZERO else "income"
        if key in existing:
            continue
        earliest = group[0]["date_value"]
        first_day = [row for row in group if row["date_value"] == earliest]
        negatives = [row for row in first_day if row["amount_value"] < ZERO]
        if len(negatives) == 1:
            negatives[0]["kind"] = "opening"
        elif not negatives:
            _add_error(
                first_day[0],
                "missing_opening",
                "account",
                "Il conto non ha un saldo iniziale: la prima riga per data "
                "deve essere negativa (entrata).",
            )
        else:
            for row in negatives:
                _add_error(
                    row,
                    "ambiguous_opening",
                    "amount",
                    "Più righe negative nella data più antica: l'apertura "
                    "non è determinabile.",
                )

    # Chronological balance, including the movements already registered.
    account_extra: dict[str, dict] = {}
    for key, group in by_account.items():
        if any(
            error["code"] in {"missing_opening", "ambiguous_opening"}
            for row in group
            for error in row["errors"]
        ):
            continue
        account = existing.get(key)
        start = min(row["date_value"] for row in group)
        current_points: dict[date, Decimal] = defaultdict(lambda: ZERO)
        balance_before = ZERO
        first_movement = None
        if account is not None:
            for day, amount in Line.objects.filter(account=account).values_list(
                "transaction__date", "amount"
            ):
                current_points[day] += amount
            balance_before = (
                Line.objects.filter(
                    account=account, transaction__date__lt=start
                ).aggregate(total=Sum("amount"))["total"]
                or ZERO
            )
            first_movement = (
                Line.objects.filter(account=account).aggregate(
                    first=Min("transaction__date")
                )["first"]
            )
        current_minimum = running_minimum(current_points)

        combined: dict[date, Decimal] = defaultdict(lambda: ZERO)
        for day, amount in current_points.items():
            combined[day] += amount
        for row in group:
            combined[row["date_value"]] += _signed(row)

        if running_minimum(combined) >= min(ZERO, current_minimum):
            account_extra[key] = {
                "balance_before": f"{balance_before:.2f}",
                "start_date": start.isoformat(),
                "first_movement": first_movement.isoformat() if first_movement else None,
            }
            continue
        first_day, running = first_negative_point(combined)
        day_rows = sorted(
            (row for row in group if row["date_value"] == first_day),
            key=lambda row: row["index"],
        )
        balance = running - sum((_signed(row) for row in day_rows), ZERO)
        for row in day_rows:
            before = balance
            balance += _signed(row)
            if balance >= ZERO:
                continue
            if before >= ZERO:
                message = (
                    f"Saldo insufficiente: disponibili {format_money(before)} "
                    f"al {first_day:%d-%m-%Y}."
                )
            else:
                message = (
                    f"Saldo insufficiente: al {first_day:%d-%m-%Y} il saldo "
                    f"risultante è {format_money(balance)}."
                )
            _add_error(row, "insufficient_balance", "amount", message)
            break
        account_extra[key] = {
            "balance_before": f"{balance_before:.2f}",
            "start_date": start.isoformat(),
            "first_movement": first_movement.isoformat() if first_movement else None,
        }

    # Duplicates inside the file.
    file_keys: dict[tuple, list[dict]] = defaultdict(list)
    for row in prepared:
        if row["valid"]:
            file_keys[_duplicate_key(row)].append(row)
    for group in file_keys.values():
        if len(group) < 2:
            continue
        for row in group:
            if row["not_duplicate"]:
                continue
            _add_error(
                row,
                "duplicate_in_file",
                "amount",
                "Riga identica a un'altra del file (stessa data, importo, "
                "descrizione e conto).",
            )

    # Duplicates already present in Spendy.
    dates = [row["date_value"] for row in prepared if row["valid"]]
    if dates:
        db_keys = _database_keys(profile, min(dates), max(dates))
        for row in prepared:
            if not row["valid"] or row["not_duplicate"]:
                continue
            if _duplicate_key(row) in db_keys:
                _add_error(
                    row,
                    "duplicate_in_database",
                    "amount",
                    "Movimento già presente in Spendy (stessa data, importo, "
                    "descrizione e conto).",
                )

    # Overlap warning: the account already has movements in this period.
    overlaps = []
    for key, group in by_account.items():
        account = existing.get(key)
        if account is None:
            continue
        start = min(row["date_value"] for row in group)
        end = max(row["date_value"] for row in group)
        count = (
            Line.objects.filter(
                account=account,
                transaction__date__gte=start,
                transaction__date__lte=end,
            )
            .values("transaction_id")
            .distinct()
            .count()
        )
        if count:
            overlaps.append(
                {
                    "account": account.name,
                    "movements": count,
                    "from": start.isoformat(),
                    "to": end.isoformat(),
                }
            )

    account_entries = []
    for key, name in names.items():
        state, related = states[key]
        count = sum(1 for row in prepared if row["account_key"] == key)
        entry = {
            "name": related.name if state == "existing" else name,
            "normalized": key,
            "state": state,
            "similar_to": related.name if state == "similar" else None,
            "will_create": state != "existing",
            "rows": count,
        }
        entry.update(account_extra.get(key, {}))
        account_entries.append(entry)
    account_entries.sort(key=lambda entry: entry["name"].casefold())

    income_total = sum(
        (
            abs(row["amount_value"])
            for row in prepared
            if row["valid"] and row["kind"] == "income"
        ),
        ZERO,
    )
    expense_total = sum(
        (
            row["amount_value"]
            for row in prepared
            if row["valid"] and row["kind"] == "expense"
        ),
        ZERO,
    )
    openings_total = sum(
        (
            abs(row["amount_value"])
            for row in prepared
            if row["valid"] and row["kind"] == "opening"
        ),
        ZERO,
    )
    available_total = openings_total + income_total
    net_total = available_total - expense_total
    covered_by_openings = (
        expense_total - income_total if expense_total > income_total else ZERO
    )

    balances = []
    for entry in account_entries:
        key = entry["normalized"]
        group = by_account.get(key, [])
        account = existing.get(key)
        base = account.balance if account is not None else ZERO
        delta = sum((_signed(row) for row in group), ZERO)
        balances.append(
            {"name": entry["name"], "final_balance": f"{base + delta:.2f}"}
        )

    row_errors = [row for row in prepared if row["errors"]]
    can_confirm = not file_errors and not row_errors

    payload = {
        "header": list(HEADER),
        "format": {
            "delimiter": delimiter or SEPARATOR,
            "date_format": applied_date_format,
            "decimal_separator": applied_decimal,
            "ambiguous": ambiguous,
        },
        "rows": [
            {
                "index": row["index"],
                "row_number": row["row_number"],
                "date": row["date"],
                "description": row["description"],
                "category": row["category"],
                "account": row["account"],
                "amount": row["amount"],
                "kind": row["kind"] if row["valid"] else None,
                "errors": row["errors"],
                "warnings": row["warnings"],
                "not_duplicate": row["not_duplicate"],
            }
            for row in prepared
        ],
        "accounts": account_entries,
        "overlaps": overlaps,
        "file_errors": list(file_errors),
        "summary": {
            "rows_total": len(prepared),
            "rows_ok": sum(1 for row in prepared if not row["errors"]),
            "rows_error": len(row_errors),
            "accounts_to_create": sum(
                1 for entry in account_entries if entry["will_create"]
            ),
            "income_total": f"{income_total:.2f}",
            "expense_total": f"{expense_total:.2f}",
            "openings_total": f"{openings_total:.2f}",
            "available_total": f"{available_total:.2f}",
            "covered_by_openings": f"{covered_by_openings:.2f}",
            "net_total": f"{net_total:.2f}",
            "balances": balances,
            "can_confirm": can_confirm,
        },
    }

    plan = [
        {
            "account_key": row["account_key"],
            "kind": row["kind"],
            "amount": abs(row["amount_value"]),
            "date": row["date_value"],
            "description": row["description"],
        }
        for row in prepared
        if row["valid"] and not row["errors"]
    ]
    return payload, plan


def analyze(
    rows: list[dict],
    profile: Profile,
    file_errors=(),
    *,
    delimiter: str | None = None,
    date_format: str | None = None,
    decimal_separator: str | None = None,
) -> dict:
    payload, _ = _analyze(
        rows,
        profile,
        file_errors,
        delimiter=delimiter,
        date_format=date_format,
        decimal_separator=decimal_separator,
    )
    return payload


def confirm(
    rows: list[dict],
    profile: Profile,
    *,
    date_format: str | None = None,
    decimal_separator: str | None = None,
) -> dict:
    payload, plan = _analyze(
        rows,
        profile,
        date_format=date_format,
        decimal_separator=decimal_separator,
    )
    if not payload["summary"]["can_confirm"]:
        raise ValidationError(
            {
                "detail": (
                    "Ci sono ancora errori: correggili o scarta le righe "
                    "prima di importare."
                )
            }
        )

    accounts = {
        normalize_name(account.name): account
        for account in Account.objects.filter(profile=profile)
    }
    created: list[str] = []
    with db_transaction.atomic():
        for entry in payload["accounts"]:
            if not entry["will_create"]:
                continue
            account = Account.objects.create(
                profile=profile,
                name=entry["name"],
                type=Account.Type.OTHER,
                initial_balance=ZERO,
            )
            accounts[entry["normalized"]] = account
            created.append(account.name)

        proposed = [
            (accounts[item["account_key"]], item["amount"] * (-1 if item["kind"] == "expense" else 1), item["date"])
            for item in plan
        ]
        assert_accounts_non_negative(proposed)

        for item in plan:
            operation = Transaction.objects.create(
                profile=profile,
                kind=item["kind"],
                date=item["date"],
                description=item["description"],
                amount=item["amount"],
            )
            signed = (
                item["amount"]
                if item["kind"] in (Transaction.Kind.INCOME, Transaction.Kind.OPENING)
                else -item["amount"]
            )
            Line.objects.create(
                transaction=operation,
                account=accounts[item["account_key"]],
                amount=signed,
                role=Line.Role.PRINCIPAL,
            )

    balances = [
        {
            "name": accounts[entry["normalized"]].name,
            "balance": f"{accounts[entry['normalized']].balance:.2f}",
        }
        for entry in payload["accounts"]
    ]
    balances.sort(key=lambda item: item["name"].casefold())
    return {
        "created_accounts": created,
        "created_transactions": len(plan),
        "income_total": payload["summary"]["income_total"],
        "expense_total": payload["summary"]["expense_total"],
        "openings_total": payload["summary"]["openings_total"],
        "available_total": payload["summary"]["available_total"],
        "covered_by_openings": payload["summary"]["covered_by_openings"],
        "net_total": payload["summary"]["net_total"],
        "accounts": balances,
    }
