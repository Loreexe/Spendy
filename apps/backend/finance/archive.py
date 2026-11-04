"""Profile archive: ZIP of CSV files for personal backup and migration (DC-074).

The archive is intentionally simple and self-describing: four CSV files plus a
JSON manifest with counts and SHA-256 checksums. ``build_archive`` exports a
profile; ``analyze_archive`` validates an uploaded archive; ``restore_archive``
writes it back into an empty profile inside a single transaction.

The CSV files use the same Italian conventions as the movements export: UTF-8
with BOM, ``;`` delimiter, CRLF and comma decimals. Dates are ISO-8601 so the
archive stays unambiguous; the register export keeps its human format.
"""
from __future__ import annotations

import csv
import hashlib
import hmac
import io
import json
import zipfile
from collections import defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.db import connection
from django.db import transaction as db_transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import ZERO, Account, Line, Profile, SavingsAccount, Transaction

SCHEMA = 1
SCOPE = "backup-profilo"
DELIMITER = ";"
BOM = b"\xef\xbb\xbf"
MANIFEST_NAME = "manifest.json"

MAX_ARCHIVE_BYTES = 25 * 1024 * 1024
MAX_UNCOMPRESSED_BYTES = 100 * 1024 * 1024
MAX_ENTRIES = 8

ACCOUNT_HEADER = (
    "id",
    "nome",
    "tipo_codice",
    "tipo_etichetta",
    "saldo_iniziale",
    "valuta",
    "archiviato",
    "creato_il",
    "aggiornato_il",
)
SAVINGS_HEADER = (
    "id",
    "nome",
    "conto_appoggio_id",
    "conto_appoggio",
    "creato_il",
    "aggiornato_il",
)
TRANSACTION_HEADER = (
    "id",
    "tipo_codice",
    "tipo_etichetta",
    "data",
    "descrizione",
    "importo",
    "creato_il",
    "aggiornato_il",
)
LINE_HEADER = (
    "id",
    "movimento_id",
    "conto_id",
    "conto",
    "salvadanaio_id",
    "salvadanaio",
    "ruolo_codice",
    "ruolo_etichetta",
    "importo_firmato",
)

CSV_HEADERS = {
    "conti.csv": ACCOUNT_HEADER,
    "salvadanai.csv": SAVINGS_HEADER,
    "movimenti.csv": TRANSACTION_HEADER,
    "righe.csv": LINE_HEADER,
}
ARCHIVE_NAMES = set(CSV_HEADERS) | {MANIFEST_NAME}


# --------------------------------------------------------------------------- #
# Formatting helpers
# --------------------------------------------------------------------------- #


def _money(value) -> str:
    return f"{Decimal(value):.2f}".replace(".", ",")


def _iso(value) -> str:
    if value is None:
        return ""
    if timezone.is_aware(value):
        value = timezone.localtime(value)
    return value.isoformat()


def _csv_bytes(header, rows) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=DELIMITER, lineterminator="\r\n")
    writer.writerow(header)
    writer.writerows(rows)
    return BOM + buffer.getvalue().encode("utf-8")


def _app_version() -> str:
    return getattr(settings, "SPENDY_VERSION", "0.0.0")


def _profile_name(profile: Profile) -> str:
    return (
        profile.display_name
        or profile.user.get_full_name()
        or profile.user.username
        or ""
    )


def _fail(message: str):
    raise ValidationError({"file": message})


# --------------------------------------------------------------------------- #
# Export
# --------------------------------------------------------------------------- #


def build_archive(profile: Profile) -> bytes:
    """Return the ZIP bytes for a profile archive."""
    already_atomic = connection.in_atomic_block
    with db_transaction.atomic():
        if connection.vendor == "postgresql" and not already_atomic:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"
                )
        accounts = list(
            Account.objects.filter(profile=profile).order_by("id")
        )
        savings = list(
            SavingsAccount.objects.filter(profile=profile)
            .select_related("backing_account")
            .order_by("id")
        )
        transactions = list(
            Transaction.objects.filter(profile=profile).order_by("id")
        )
        lines = list(
            Line.objects.filter(transaction__profile=profile)
            .select_related("account", "savings")
            .order_by("id")
        )

    account_names = {account.id: account.name for account in accounts}
    savings_names = {entry.id: entry.name for entry in savings}

    account_rows = [
        [
            account.id,
            account.name,
            account.type,
            account.get_type_display(),
            _money(account.initial_balance),
            account.currency,
            "1" if account.archived else "0",
            _iso(account.created_at),
            _iso(account.updated_at),
        ]
        for account in accounts
    ]
    savings_rows = [
        [
            entry.id,
            entry.name,
            entry.backing_account_id,
            entry.backing_account.name,
            _iso(entry.created_at),
            _iso(entry.updated_at),
        ]
        for entry in savings
    ]
    transaction_rows = [
        [
            operation.id,
            operation.kind,
            operation.get_kind_display(),
            operation.date.isoformat(),
            operation.description,
            _money(operation.amount),
            _iso(operation.created_at),
            _iso(operation.updated_at),
        ]
        for operation in transactions
    ]
    line_rows = [
        [
            line.id,
            line.transaction_id,
            line.account_id or "",
            account_names.get(line.account_id, ""),
            line.savings_id or "",
            savings_names.get(line.savings_id, ""),
            line.role,
            line.get_role_display(),
            _money(line.amount),
        ]
        for line in lines
    ]

    files = {
        "conti.csv": _csv_bytes(ACCOUNT_HEADER, account_rows),
        "salvadanai.csv": _csv_bytes(SAVINGS_HEADER, savings_rows),
        "movimenti.csv": _csv_bytes(TRANSACTION_HEADER, transaction_rows),
        "righe.csv": _csv_bytes(LINE_HEADER, line_rows),
    }
    counts = {
        "conti": len(account_rows),
        "salvadanai": len(savings_rows),
        "movimenti": len(transaction_rows),
        "righe": len(line_rows),
    }
    file_meta = {}
    for name, key in (
        ("conti.csv", "conti"),
        ("salvadanai.csv", "salvadanai"),
        ("movimenti.csv", "movimenti"),
        ("righe.csv", "righe"),
    ):
        content = files[name]
        file_meta[name] = {
            "righe": counts[key],
            "sha256": hashlib.sha256(content).hexdigest(),
        }
    manifest = {
        "schema": SCHEMA,
        "scopo": SCOPE,
        "generato_il": timezone.now().isoformat(),
        "versione_app": _app_version(),
        "profilo": _profile_name(profile),
        "valuta": "EUR",
        "formato": {
            "encoding": "utf-8-sig",
            "delimitatore": DELIMITER,
            "fine_riga": "CRLF",
            "decimali": ",",
            "date": "ISO-8601",
        },
        "conteggi": counts,
        "file": file_meta,
        "note": [
            "Backup personale del profilo: non sostituisce il backup globale "
            "del sistema.",
            "La categoria non è memorizzata nel modello e non è esportata.",
            "Le date di creazione e aggiornamento sono informative: il "
            "ripristino ricrea i record con date correnti.",
        ],
    }

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in ("conti.csv", "salvadanai.csv", "movimenti.csv", "righe.csv"):
            archive.writestr(name, files[name])
        archive.writestr(
            MANIFEST_NAME,
            json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8"),
        )
    return buffer.getvalue()


# --------------------------------------------------------------------------- #
# Parsing helpers
# --------------------------------------------------------------------------- #


def _parse_int(value: str, where: str) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        _fail(f"{where}: identificativo non valido.")


def _parse_decimal(value: str, where: str) -> Decimal:
    text = str(value).strip().replace(" ", "")
    if not text:
        _fail(f"{where}: importo mancante.")
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    else:
        text = text.replace(",", ".")
    try:
        return Decimal(text).quantize(Decimal("0.01"))
    except InvalidOperation:
        _fail(f"{where}: importo non valido.")


def _parse_date(value: str, where: str) -> date:
    try:
        return date.fromisoformat(str(value).strip())
    except ValueError:
        _fail(f"{where}: data non valida.")


def _parse_bool(value: str, where: str) -> bool:
    text = str(value).strip().lower()
    if text in {"1", "true", "si", "sì"}:
        return True
    if text in {"0", "false", "no", ""}:
        return False
    _fail(f"{where}: valore booleano non valido.")


def _csv_rows(contents: dict[str, bytes], name: str) -> list[list[str]]:
    header = CSV_HEADERS[name]
    try:
        text = contents[name].decode("utf-8-sig")
    except UnicodeDecodeError:
        _fail(f"{name}: il file non è in UTF-8.")
    rows = [row for row in csv.reader(io.StringIO(text), delimiter=DELIMITER) if row]
    if not rows:
        _fail(f"{name}: file vuoto.")
    if tuple(rows[0]) != header:
        _fail(f"{name}: intestazione non valida.")
    return rows[1:]


def _read_zip(raw: bytes) -> dict[str, bytes]:
    if not raw:
        _fail("Carica un archivio ZIP.")
    if len(raw) > MAX_ARCHIVE_BYTES:
        _fail(
            "L'archivio supera "
            f"{MAX_ARCHIVE_BYTES // (1024 * 1024)} MB."
        )
    try:
        archive = zipfile.ZipFile(io.BytesIO(raw))
    except zipfile.BadZipFile:
        _fail("Il file non è un archivio ZIP valido.")
    try:
        infos = archive.infolist()
        if len(infos) > MAX_ENTRIES:
            _fail("L'archivio contiene troppi file.")
        names = [info.filename for info in infos]
        if set(names) != ARCHIVE_NAMES or len(names) != len(set(names)):
            _fail(
                "L'archivio deve contenere solo conti.csv, salvadanai.csv, "
                "movimenti.csv, righe.csv e manifest.json."
            )
        if any(
            info.is_dir() or "/" in info.filename or "\\" in info.filename
            for info in infos
        ):
            _fail("L'archivio contiene percorsi non validi.")
        if any(info.flag_bits & 0x1 for info in infos):
            _fail("Gli archivi protetti da password non sono supportati.")
        if sum(info.file_size for info in infos) > MAX_UNCOMPRESSED_BYTES:
            _fail("L'archivio non compresso è troppo grande.")
        contents: dict[str, bytes] = {}
        for name in ARCHIVE_NAMES:
            try:
                contents[name] = archive.read(name)
            except (RuntimeError, zipfile.BadZipFile):
                _fail(f"Impossibile leggere {name} dall'archivio.")
        return contents
    finally:
        archive.close()


def _read_manifest(contents: dict[str, bytes]) -> dict:
    try:
        manifest = json.loads(contents[MANIFEST_NAME].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        _fail("Il manifest non è un JSON valido.")
    if not isinstance(manifest, dict):
        _fail("Il manifest non è valido.")
    if manifest.get("schema") != SCHEMA:
        _fail("Versione dell'archivio non supportata.")
    if manifest.get("scopo") != SCOPE:
        _fail("L'archivio non è un backup di un profilo Spendy.")
    return manifest


def _check_checksums(contents: dict[str, bytes], manifest: dict, rows: dict):
    files = manifest.get("file")
    if not isinstance(files, dict):
        _fail("Il manifest non contiene l'elenco dei file.")
    for name in CSV_HEADERS:
        entry = files.get(name)
        if not isinstance(entry, dict):
            _fail(f"Il manifest non descrive {name}.")
        expected = entry.get("sha256")
        if not isinstance(expected, str):
            _fail(f"Il manifest non contiene il checksum di {name}.")
        actual = hashlib.sha256(contents[name]).hexdigest()
        if not hmac.compare_digest(expected, actual):
            _fail(f"Il file {name} non corrisponde al checksum del manifest.")
        if entry.get("righe") != len(rows[name]):
            _fail(f"Il numero di righe di {name} non corrisponde al manifest.")


def _parse_accounts(rows: list[list[str]]) -> list[dict]:
    result = []
    seen: set[int] = set()
    types = set(Account.Type.values)
    for number, row in enumerate(rows, start=2):
        where = f"conti.csv, riga {number}"
        if len(row) != len(ACCOUNT_HEADER):
            _fail(f"{where}: numero di colonne non valido.")
        account_id = _parse_int(row[0], where)
        if account_id in seen:
            _fail(f"{where}: identificativo duplicato.")
        seen.add(account_id)
        name = row[1].strip()
        if not name or len(name) > 100:
            _fail(f"{where}: nome del conto non valido.")
        account_type = row[2].strip()
        if account_type not in types:
            _fail(f"{where}: tipo di conto non valido.")
        initial = _parse_decimal(row[4], where)
        if initial < ZERO:
            _fail(f"{where}: saldo iniziale negativo.")
        result.append(
            {
                "id": account_id,
                "name": name,
                "type": account_type,
                "initial_balance": initial,
                "archived": _parse_bool(row[6], where),
            }
        )
    return result


def _parse_savings(rows: list[list[str]]) -> list[dict]:
    result = []
    seen: set[int] = set()
    for number, row in enumerate(rows, start=2):
        where = f"salvadanai.csv, riga {number}"
        if len(row) != len(SAVINGS_HEADER):
            _fail(f"{where}: numero di colonne non valido.")
        savings_id = _parse_int(row[0], where)
        if savings_id in seen:
            _fail(f"{where}: identificativo duplicato.")
        seen.add(savings_id)
        name = row[1].strip()
        if not name or len(name) > 100:
            _fail(f"{where}: nome del salvadanaio non valido.")
        result.append(
            {
                "id": savings_id,
                "name": name,
                "backing_account_id": _parse_int(row[2], where),
            }
        )
    return result


def _parse_transactions(rows: list[list[str]]) -> list[dict]:
    result = []
    seen: set[int] = set()
    kinds = set(Transaction.Kind.values)
    for number, row in enumerate(rows, start=2):
        where = f"movimenti.csv, riga {number}"
        if len(row) != len(TRANSACTION_HEADER):
            _fail(f"{where}: numero di colonne non valido.")
        transaction_id = _parse_int(row[0], where)
        if transaction_id in seen:
            _fail(f"{where}: identificativo duplicato.")
        seen.add(transaction_id)
        kind = row[1].strip()
        if kind not in kinds:
            _fail(f"{where}: tipo di movimento non valido.")
        amount = _parse_decimal(row[5], where)
        if amount <= ZERO:
            _fail(f"{where}: l'importo deve essere maggiore di zero.")
        description = row[4]
        if len(description) > 255:
            _fail(f"{where}: descrizione troppo lunga.")
        result.append(
            {
                "id": transaction_id,
                "kind": kind,
                "date": _parse_date(row[3], where),
                "description": description,
                "amount": amount,
            }
        )
    return result


def _parse_lines(rows: list[list[str]]) -> list[dict]:
    result = []
    seen: set[int] = set()
    roles = set(Line.Role.values)
    for number, row in enumerate(rows, start=2):
        where = f"righe.csv, riga {number}"
        if len(row) != len(LINE_HEADER):
            _fail(f"{where}: numero di colonne non valido.")
        line_id = _parse_int(row[0], where)
        if line_id in seen:
            _fail(f"{where}: identificativo duplicato.")
        seen.add(line_id)
        account_id = row[2].strip()
        savings_id = row[4].strip()
        if bool(account_id) == bool(savings_id):
            _fail(
                f"{where}: la riga deve indicare un solo conto o salvadanaio."
            )
        role = row[6].strip()
        if role not in roles:
            _fail(f"{where}: ruolo della riga non valido.")
        result.append(
            {
                "id": line_id,
                "transaction_id": _parse_int(row[1], where),
                "account_id": _parse_int(account_id, where) if account_id else None,
                "savings_id": _parse_int(savings_id, where) if savings_id else None,
                "role": role,
                "amount": _parse_decimal(row[8], where),
            }
        )
    return result


def _validate(
    manifest: dict,
    accounts: list[dict],
    savings: list[dict],
    transactions: list[dict],
    lines: list[dict],
):
    account_ids = {entry["id"] for entry in accounts}
    savings_ids = {entry["id"] for entry in savings}
    transaction_ids = {entry["id"] for entry in transactions}

    for entry in savings:
        if entry["backing_account_id"] not in account_ids:
            _fail(
                f"salvadanai.csv: il conto di appoggio del salvadanaio "
                f"«{entry['name']}» non esiste nell'archivio."
            )

    lines_by_transaction: dict[int, list[dict]] = defaultdict(list)
    for line in lines:
        if line["transaction_id"] not in transaction_ids:
            _fail(
                f"righe.csv: il movimento {line['transaction_id']} non esiste "
                "nell'archivio."
            )
        if line["account_id"] is not None and line["account_id"] not in account_ids:
            _fail(
                f"righe.csv: il conto {line['account_id']} non esiste "
                "nell'archivio."
            )
        if line["savings_id"] is not None and line["savings_id"] not in savings_ids:
            _fail(
                f"righe.csv: il salvadanaio {line['savings_id']} non esiste "
                "nell'archivio."
            )
        lines_by_transaction[line["transaction_id"]].append(line)

    for operation in transactions:
        related = lines_by_transaction.get(operation["id"], [])
        if not related:
            _fail(
                f"movimenti.csv: il movimento {operation['id']} non ha righe."
            )
        net = sum((line["amount"] for line in related), ZERO)
        if operation["kind"] == Transaction.Kind.TRANSFER:
            expected = ZERO
        elif operation["kind"] == Transaction.Kind.EXPENSE:
            expected = -operation["amount"]
        else:
            expected = operation["amount"]
        if net != expected:
            _fail(
                f"movimenti.csv: le righe del movimento {operation['id']} "
                "non quadrano con l'importo."
            )
        if operation["kind"] == Transaction.Kind.OPENING:
            for line in related:
                if line["account_id"] is None:
                    _fail(
                        "movimenti.csv: un movimento di apertura può riferirsi "
                        "solo a un conto."
                    )

    counts = manifest.get("conteggi")
    expected_counts = {
        "conti": len(accounts),
        "salvadanai": len(savings),
        "movimenti": len(transactions),
        "righe": len(lines),
    }
    if counts != expected_counts:
        _fail("I conteggi del manifest non corrispondono ai file.")


def _profile_has_data(profile: Profile) -> bool:
    return (
        Account.objects.filter(profile=profile).exists()
        or SavingsAccount.objects.filter(profile=profile).exists()
        or Transaction.objects.filter(profile=profile).exists()
    )


def _parse_archive(raw: bytes):
    contents = _read_zip(raw)
    manifest = _read_manifest(contents)
    parsed_rows = {
        name: _csv_rows(contents, name) for name in CSV_HEADERS
    }
    _check_checksums(contents, manifest, parsed_rows)
    accounts = _parse_accounts(parsed_rows["conti.csv"])
    savings = _parse_savings(parsed_rows["salvadanai.csv"])
    transactions = _parse_transactions(parsed_rows["movimenti.csv"])
    lines = _parse_lines(parsed_rows["righe.csv"])
    _validate(manifest, accounts, savings, transactions, lines)
    return manifest, accounts, savings, transactions, lines


# --------------------------------------------------------------------------- #
# Analysis
# --------------------------------------------------------------------------- #


def _summary(
    accounts: list[dict],
    savings: list[dict],
    transactions: list[dict],
    lines: list[dict],
) -> dict:
    account_balances: dict[int, Decimal] = defaultdict(lambda: ZERO)
    savings_balances: dict[int, Decimal] = defaultdict(lambda: ZERO)
    for line in lines:
        if line["account_id"] is not None:
            account_balances[line["account_id"]] += line["amount"]
        elif line["savings_id"] is not None:
            savings_balances[line["savings_id"]] += line["amount"]

    accounts_total = sum(account_balances.values(), ZERO)
    savings_total = sum(savings_balances.values(), ZERO)
    dates = [operation["date"] for operation in transactions]
    return {
        "accounts": len(accounts),
        "savings": len(savings),
        "transactions": len(transactions),
        "lines": len(lines),
        "from": min(dates).isoformat() if dates else None,
        "to": max(dates).isoformat() if dates else None,
        "accounts_total": f"{accounts_total:.2f}",
        "savings_total": f"{savings_total:.2f}",
        "patrimony_total": f"{accounts_total + savings_total:.2f}",
        "balances": {
            "accounts": sorted(
                (
                    {
                        "name": entry["name"],
                        "balance": f"{account_balances[entry['id']]:.2f}",
                    }
                    for entry in accounts
                ),
                key=lambda item: item["name"].casefold(),
            ),
            "savings": sorted(
                (
                    {
                        "name": entry["name"],
                        "balance": f"{savings_balances[entry['id']]:.2f}",
                    }
                    for entry in savings
                ),
                key=lambda item: item["name"].casefold(),
            ),
        },
    }


def analyze_archive(raw: bytes, profile: Profile) -> dict:
    manifest, accounts, savings, transactions, lines = _parse_archive(raw)
    has_data = _profile_has_data(profile)
    warnings = []
    if manifest.get("versione_app") not in (None, _app_version()):
        warnings.append(
            "L'archivio è stato creato con una versione diversa di Spendy: "
            "controlla l'anteprima prima di ripristinare."
        )
    if manifest.get("valuta") not in (None, "EUR"):
        warnings.append(
            "L'archivio usa una valuta diversa da EUR: i dati non verranno "
            "convertiti."
        )
    return {
        "can_restore": not has_data,
        "blocked_reason": (
            "Il profilo contiene già dati. Il ripristino è consentito solo su "
            "un profilo vuoto."
            if has_data
            else None
        ),
        "manifest": {
            "schema": manifest.get("schema"),
            "generato_il": manifest.get("generato_il"),
            "versione_app": manifest.get("versione_app"),
            "profilo": manifest.get("profilo"),
            "valuta": manifest.get("valuta"),
            "conteggi": manifest.get("conteggi"),
        },
        "summary": _summary(accounts, savings, transactions, lines),
        "warnings": warnings,
    }


# --------------------------------------------------------------------------- #
# Restore
# --------------------------------------------------------------------------- #


def restore_archive(raw: bytes, profile: Profile) -> dict:
    _, accounts, savings, transactions, lines = _parse_archive(raw)
    if _profile_has_data(profile):
        _fail(
            "Il profilo contiene già dati. Il ripristino è consentito solo su "
            "un profilo vuoto."
        )

    with db_transaction.atomic():
        Profile.objects.select_for_update().get(pk=profile.pk)
        if _profile_has_data(profile):
            _fail(
                "Il profilo contiene già dati. Il ripristino è consentito solo "
                "su un profilo vuoto."
            )

        account_objects = [
            Account(
                profile=profile,
                name=entry["name"],
                type=entry["type"],
                initial_balance=entry["initial_balance"],
                archived=entry["archived"],
            )
            for entry in accounts
        ]
        Account.objects.bulk_create(account_objects)
        account_map = {
            entry["id"]: account
            for entry, account in zip(accounts, account_objects)
        }

        savings_objects = [
            SavingsAccount(
                profile=profile,
                name=entry["name"],
                backing_account=account_map[entry["backing_account_id"]],
            )
            for entry in savings
        ]
        SavingsAccount.objects.bulk_create(savings_objects)
        savings_map = {
            entry["id"]: savings_account
            for entry, savings_account in zip(savings, savings_objects)
        }

        transaction_objects = [
            Transaction(
                profile=profile,
                kind=entry["kind"],
                date=entry["date"],
                description=entry["description"],
                amount=entry["amount"],
            )
            for entry in transactions
        ]
        Transaction.objects.bulk_create(transaction_objects)
        transaction_map = {
            entry["id"]: operation
            for entry, operation in zip(transactions, transaction_objects)
        }

        Line.objects.bulk_create(
            [
                Line(
                    transaction=transaction_map[entry["transaction_id"]],
                    account=(
                        account_map[entry["account_id"]]
                        if entry["account_id"] is not None
                        else None
                    ),
                    savings=(
                        savings_map[entry["savings_id"]]
                        if entry["savings_id"] is not None
                        else None
                    ),
                    amount=entry["amount"],
                    role=entry["role"],
                )
                for entry in lines
            ]
        )

    account_balances = sorted(
        (
            {"name": account.name, "balance": f"{account.balance:.2f}"}
            for account in account_objects
        ),
        key=lambda item: item["name"].casefold(),
    )
    savings_balances = sorted(
        (
            {
                "name": savings_account.name,
                "balance": f"{savings_account.balance:.2f}",
            }
            for savings_account in savings_objects
        ),
        key=lambda item: item["name"].casefold(),
    )
    accounts_total = sum((account.balance for account in account_objects), ZERO)
    savings_total = sum(
        (savings_account.balance for savings_account in savings_objects), ZERO
    )
    return {
        "accounts": len(account_objects),
        "savings": len(savings_objects),
        "transactions": len(transaction_objects),
        "lines": len(lines),
        "accounts_total": f"{accounts_total:.2f}",
        "savings_total": f"{savings_total:.2f}",
        "patrimony_total": f"{accounts_total + savings_total:.2f}",
        "balances": {
            "accounts": account_balances,
            "savings": savings_balances,
        },
    }
