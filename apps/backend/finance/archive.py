"""Profile archive: ZIP of CSV files for personal backup and migration (DC-074).

The archive is intentionally simple and self-describing: six CSV files plus a
JSON manifest with counts and SHA-256 checksums. ``build_archive`` exports a
profile; ``analyze_archive`` validates an uploaded archive; ``restore_archive``
writes it back into an empty profile inside a single transaction. Archives with
``schema`` 1 (before investments) are still analyzed and restored.

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
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from django.conf import settings
from django.db import connection
from django.db import transaction as db_transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .csv_safety import restore_csv_text, sanitize_csv_text
from .models import (
    ZERO,
    DEFAULT_CATEGORY_NAME,
    Account,
    Category,
    InvestmentOperation,
    InvestmentPosition,
    Line,
    Profile,
    SavingsAccount,
    Tag,
    Transaction,
    ensure_default_categories,
)

SCHEMA = 3
SUPPORTED_SCHEMAS = {1, 2, 3}
SCOPE = "backup-profilo"
DELIMITER = ";"
BOM = b"\xef\xbb\xbf"
MANIFEST_NAME = "manifest.json"
MONEY_PLACES = Decimal("0.01")
QUANTITY_PLACES = Decimal("0.00000001")

MAX_ARCHIVE_BYTES = 25 * 1024 * 1024
MAX_UNCOMPRESSED_BYTES = 100 * 1024 * 1024
MAX_ENTRIES = 12

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
SCHEMA3_TRANSACTION_HEADER = TRANSACTION_HEADER + (
    "categoria_id",
    "categoria_nome",
)
CATEGORY_HEADER = (
    "id",
    "nome",
    "predefinita",
    "iniziale",
)
TAG_HEADER = (
    "id",
    "nome",
)
MOVTAG_HEADER = (
    "movimento_id",
    "tag_id",
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
POSITION_HEADER = (
    "id",
    "nome",
    "categoria_codice",
    "categoria_etichetta",
    "identificativo",
    "prezzo_corrente",
    "data_prezzo",
    "archiviata",
    "creato_il",
    "aggiornato_il",
)
INVESTMENT_OPERATION_HEADER = (
    "id",
    "posizione_id",
    "posizione",
    "tipo_codice",
    "tipo_etichetta",
    "data",
    "quantita",
    "prezzo_unitario",
    "controvalore_lordo",
    "commissione",
    "importo_contante",
    "movimento_id",
    "conto_id",
    "conto",
    "descrizione",
    "creato_il",
    "aggiornato_il",
)

CSV_HEADERS = {
    "conti.csv": ACCOUNT_HEADER,
    "salvadanai.csv": SAVINGS_HEADER,
    "movimenti.csv": SCHEMA3_TRANSACTION_HEADER,
    "righe.csv": LINE_HEADER,
    "posizioni.csv": POSITION_HEADER,
    "operazioni_investimenti.csv": INVESTMENT_OPERATION_HEADER,
    "categorie.csv": CATEGORY_HEADER,
    "tag.csv": TAG_HEADER,
    "movimento_tag.csv": MOVTAG_HEADER,
}
SCHEMA1_CSV = frozenset(
    {"conti.csv", "salvadanai.csv", "movimenti.csv", "righe.csv"}
)
SCHEMA2_CSV = frozenset(
    {
        "conti.csv",
        "salvadanai.csv",
        "movimenti.csv",
        "righe.csv",
        "posizioni.csv",
        "operazioni_investimenti.csv",
    }
)
SCHEMA3_CSV = frozenset(CSV_HEADERS)
INVESTMENT_CSV = ("posizioni.csv", "operazioni_investimenti.csv")
ARCHIVE_NAMES_BY_SCHEMA = {
    1: SCHEMA1_CSV | {MANIFEST_NAME},
    2: SCHEMA2_CSV | {MANIFEST_NAME},
    3: SCHEMA3_CSV | {MANIFEST_NAME},
}


# --------------------------------------------------------------------------- #
# Formatting helpers
# --------------------------------------------------------------------------- #


def _money(value) -> str:
    return f"{Decimal(value):.2f}".replace(".", ",")


def _quantity(value) -> str:
    return f"{Decimal(value):.8f}".replace(".", ",")


def _optional_amount(value) -> str:
    return "" if value is None else _money(value)


def _optional_quantity(value) -> str:
    return "" if value is None else _quantity(value)


def _round_money(value) -> Decimal:
    return Decimal(value).quantize(MONEY_PLACES, rounding=ROUND_HALF_UP)


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


def _position_rows(positions) -> list[list]:
    return [
        [
            position.id,
            sanitize_csv_text(position.name),
            position.category,
            position.get_category_display() if position.category else "",
            sanitize_csv_text(position.identifier),
            _optional_quantity(position.current_price),
            position.price_updated_on.isoformat() if position.price_updated_on else "",
            "1" if position.archived else "0",
            _iso(position.created_at),
            _iso(position.updated_at),
        ]
        for position in positions
    ]


def _operation_rows(operations) -> list[list]:
    rows = []
    for operation in operations:
        movement_id = operation.transaction_id or ""
        account_id = ""
        account_name = ""
        if operation.transaction is not None:
            for line in operation.transaction.lines.all():
                if (
                    line.role == Line.Role.PRINCIPAL
                    and line.account_id is not None
                ):
                    account_id = line.account_id
                    account_name = line.account.name
                    break
        rows.append(
            [
                operation.id,
                operation.position_id,
                sanitize_csv_text(operation.position.name),
                operation.kind,
                operation.get_kind_display(),
                operation.date.isoformat(),
                _optional_quantity(operation.quantity),
                _optional_quantity(operation.unit_price),
                _optional_amount(operation.gross_amount),
                _money(operation.commission),
                _money(operation.cash_amount),
                movement_id,
                account_id,
                sanitize_csv_text(account_name),
                sanitize_csv_text(operation.description),
                _iso(operation.created_at),
                _iso(operation.updated_at),
            ]
        )
    return rows


def _investment_files(positions, operations) -> dict[str, bytes]:
    return {
        "posizioni.csv": _csv_bytes(
            POSITION_HEADER, _position_rows(positions)
        ),
        "operazioni_investimenti.csv": _csv_bytes(
            INVESTMENT_OPERATION_HEADER, _operation_rows(operations)
        ),
    }


def _investment_queryset(profile: Profile):
    positions = list(
        InvestmentPosition.objects.filter(profile=profile).order_by("id")
    )
    operations = list(
        InvestmentOperation.objects.filter(profile=profile)
        .select_related("position", "transaction")
        .prefetch_related("transaction__lines__account")
        .order_by("id")
    )
    return positions, operations


def build_investment_files(profile: Profile) -> dict[str, bytes]:
    """Return the two investment CSV files, isolated to a profile."""
    with db_transaction.atomic():
        positions, operations = _investment_queryset(profile)
    return _investment_files(positions, operations)


def build_investment_archive(profile: Profile) -> bytes:
    """Return a ZIP with only the two investment CSV files."""
    files = build_investment_files(profile)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in INVESTMENT_CSV:
            archive.writestr(name, files[name])
    return buffer.getvalue()


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
            Transaction.objects.filter(profile=profile)
            .select_related("category")
            .order_by("id")
        )
        categories = list(
            Category.objects.filter(profile=profile).order_by("id")
        )
        tags = list(Tag.objects.filter(profile=profile).order_by("id"))
        tag_pairs = list(
            Transaction.tags.through.objects.filter(
                transaction__profile=profile
            )
            .order_by("transaction_id", "tag_id")
            .values_list("transaction_id", "tag_id")
        )
        lines = list(
            Line.objects.filter(
                transaction__profile=profile, transaction__is_deleted=False
            )
            .select_related("account", "savings")
            .order_by("id")
        )
        positions, operations = _investment_queryset(profile)

    account_names = {account.id: account.name for account in accounts}
    savings_names = {entry.id: entry.name for entry in savings}

    account_rows = [
        [
            account.id,
            sanitize_csv_text(account.name),
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
            sanitize_csv_text(entry.name),
            entry.backing_account_id,
            sanitize_csv_text(entry.backing_account.name),
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
            sanitize_csv_text(operation.description),
            _money(operation.amount),
            _iso(operation.created_at),
            _iso(operation.updated_at),
            operation.category_id or "",
            sanitize_csv_text(
                operation.category.name if operation.category_id else ""
            ),
        ]
        for operation in transactions
    ]
    category_rows = [
        [
            entry.id,
            sanitize_csv_text(entry.name),
            "1" if entry.is_preset else "0",
            "1" if entry.is_default else "0",
        ]
        for entry in categories
    ]
    tag_rows = [
        [entry.id, sanitize_csv_text(entry.name)] for entry in tags
    ]
    movtag_rows = [list(pair) for pair in tag_pairs]
    line_rows = [
        [
            line.id,
            line.transaction_id,
            line.account_id or "",
            sanitize_csv_text(account_names.get(line.account_id, "")),
            line.savings_id or "",
            sanitize_csv_text(savings_names.get(line.savings_id, "")),
            line.role,
            line.get_role_display(),
            _money(line.amount),
        ]
        for line in lines
    ]

    files = {
        "conti.csv": _csv_bytes(ACCOUNT_HEADER, account_rows),
        "salvadanai.csv": _csv_bytes(SAVINGS_HEADER, savings_rows),
        "movimenti.csv": _csv_bytes(SCHEMA3_TRANSACTION_HEADER, transaction_rows),
        "righe.csv": _csv_bytes(LINE_HEADER, line_rows),
        "categorie.csv": _csv_bytes(CATEGORY_HEADER, category_rows),
        "tag.csv": _csv_bytes(TAG_HEADER, tag_rows),
        "movimento_tag.csv": _csv_bytes(MOVTAG_HEADER, movtag_rows),
    }
    files.update(_investment_files(positions, operations))
    counts = {
        "conti": len(account_rows),
        "salvadanai": len(savings_rows),
        "movimenti": len(transaction_rows),
        "righe": len(line_rows),
        "categorie": len(category_rows),
        "tag": len(tag_rows),
        "movimento_tag": len(movtag_rows),
        "posizioni": len(positions),
        "operazioni_investimenti": len(operations),
    }
    file_meta = {
        name: {
            "righe": counts[name.removesuffix(".csv")],
            "sha256": hashlib.sha256(files[name]).hexdigest(),
        }
        for name in CSV_HEADERS
    }
    manifest = {
        "schema": SCHEMA,
        "scopo": SCOPE,
        "generato_il": timezone.now().isoformat(),
        "versione_app": _app_version(),
        "profilo": _profile_name(profile),
        "valuta": "EUR",
        "conto_investimenti_id": profile.investment_account_id,
        "conto_investimenti": (
            profile.investment_account.name
            if profile.investment_account_id
            else ""
        ),
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
            "Categorie e tag sono inclusi in categorie.csv, tag.csv e "
            "movimento_tag.csv.",
            "Le operazioni di investimento sono incluse solo in questo "
            "archivio e nell'export dedicato, non nel registro Movimenti.",
            "Le date di creazione e aggiornamento sono informative: il "
            "ripristino ricrea i record con date correnti.",
        ],
    }

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in CSV_HEADERS:
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


def _parse_number(value: str, where: str, places: Decimal) -> Decimal:
    text = str(value).strip().replace(" ", "")
    if not text:
        _fail(f"{where}: importo mancante.")
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    else:
        text = text.replace(",", ".")
    try:
        return Decimal(text).quantize(places, rounding=ROUND_HALF_UP)
    except InvalidOperation:
        _fail(f"{where}: importo non valido.")


def _parse_decimal(value: str, where: str) -> Decimal:
    return _parse_number(value, where, MONEY_PLACES)


def _parse_quantity(value: str, where: str) -> Decimal:
    return _parse_number(value, where, QUANTITY_PLACES)


def _parse_optional_decimal(value: str, where: str) -> Decimal | None:
    return _parse_decimal(value, where) if str(value).strip() else None


def _parse_optional_quantity(value: str, where: str) -> Decimal | None:
    return _parse_quantity(value, where) if str(value).strip() else None


def _parse_optional_date(value: str, where: str) -> date | None:
    return _parse_date(value, where) if str(value).strip() else None


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


def _csv_rows(contents: dict[str, bytes], name: str, schema: int) -> list[list[str]]:
    if name == "movimenti.csv" and schema < 3:
        header = TRANSACTION_HEADER
    else:
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
        if (
            set(names) not in ARCHIVE_NAMES_BY_SCHEMA.values()
            or len(names) != len(set(names))
        ):
            _fail(
                "L'archivio deve contenere i CSV del formato 1, 2 o 3, "
                "con manifest.json."
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
        for name in names:
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
    if manifest.get("schema") not in SUPPORTED_SCHEMAS:
        _fail("Versione dell'archivio non supportata.")
    if manifest.get("scopo") != SCOPE:
        _fail("L'archivio non è un backup di un profilo Spendy.")
    return manifest


def _check_checksums(
    contents: dict[str, bytes],
    manifest: dict,
    rows: dict,
    csv_names,
):
    files = manifest.get("file")
    if not isinstance(files, dict):
        _fail("Il manifest non contiene l'elenco dei file.")
    for name in csv_names:
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
        name = restore_csv_text(row[1].strip())
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
        name = restore_csv_text(row[1].strip())
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


def _parse_transactions(
    rows: list[list[str]], schema: int
) -> list[dict]:
    result = []
    seen: set[int] = set()
    kinds = set(Transaction.Kind.values)
    expected = len(TRANSACTION_HEADER) if schema < 3 else len(
        SCHEMA3_TRANSACTION_HEADER
    )
    for number, row in enumerate(rows, start=2):
        where = f"movimenti.csv, riga {number}"
        if len(row) != expected:
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
        description = restore_csv_text(row[4])
        if len(description) > 255:
            _fail(f"{where}: descrizione troppo lunga.")
        entry: dict = {
            "id": transaction_id,
            "kind": kind,
            "date": _parse_date(row[3], where),
            "description": description,
            "amount": amount,
        }
        if schema >= 3:
            raw_category_id = row[8].strip()
            category_id = (
                _parse_int(raw_category_id, where) if raw_category_id else None
            )
            category_name = restore_csv_text(row[9].strip())
            if len(category_name) > 60:
                _fail(f"{where}: nome della categoria troppo lungo.")
            entry["category_id"] = category_id
            entry["category_name"] = category_name
        result.append(entry)
    return result


def _parse_categories(rows: list[list[str]]) -> list[dict]:
    result = []
    seen: set[int] = set()
    names: set[str] = set()
    for number, row in enumerate(rows, start=2):
        where = f"categorie.csv, riga {number}"
        if len(row) != len(CATEGORY_HEADER):
            _fail(f"{where}: numero di colonne non valido.")
        category_id = _parse_int(row[0], where)
        if category_id in seen:
            _fail(f"{where}: identificativo duplicato.")
        seen.add(category_id)
        name = restore_csv_text(row[1].strip())
        if not name or len(name) > 60:
            _fail(f"{where}: nome della categoria non valido.")
        if name.casefold() in names:
            _fail(f"{where}: nome della categoria duplicato.")
        names.add(name.casefold())
        result.append(
            {
                "id": category_id,
                "name": name,
                "is_preset": _parse_bool(row[2].strip(), where),
                "is_default": _parse_bool(row[3].strip(), where),
            }
        )
    defaults = [entry for entry in result if entry["is_default"]]
    if len(defaults) != 1:
        _fail("categorie.csv: deve esistere una sola categoria iniziale.")
    return result


def _parse_tags(rows: list[list[str]]) -> list[dict]:
    result = []
    seen: set[int] = set()
    names: set[str] = set()
    for number, row in enumerate(rows, start=2):
        where = f"tag.csv, riga {number}"
        if len(row) != len(TAG_HEADER):
            _fail(f"{where}: numero di colonne non valido.")
        tag_id = _parse_int(row[0], where)
        if tag_id in seen:
            _fail(f"{where}: identificativo duplicato.")
        seen.add(tag_id)
        name = restore_csv_text(row[1].strip())
        if not name or len(name) > 30:
            _fail(f"{where}: nome del tag non valido.")
        if name in names:
            _fail(f"{where}: nome del tag duplicato.")
        names.add(name)
        result.append({"id": tag_id, "name": name})
    return result


def _parse_movtags(
    rows: list[list[str]],
    transaction_ids: set[int],
    tag_ids: set[int],
) -> list[dict]:
    result = []
    seen: set[tuple[int, int]] = set()
    for number, row in enumerate(rows, start=2):
        where = f"movimento_tag.csv, riga {number}"
        if len(row) != len(MOVTAG_HEADER):
            _fail(f"{where}: numero di colonne non valido.")
        pair = (_parse_int(row[0].strip(), where), _parse_int(row[1].strip(), where))
        if pair in seen:
            _fail(f"{where}: assegnazione duplicata.")
        seen.add(pair)
        if pair[0] not in transaction_ids:
            _fail(f"{where}: movimento inesistente.")
        if pair[1] not in tag_ids:
            _fail(f"{where}: tag inesistente.")
        result.append({"transaction_id": pair[0], "tag_id": pair[1]})
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


def _parse_positions(rows: list[list[str]]) -> list[dict]:
    result = []
    seen: set[int] = set()
    categories = set(InvestmentPosition.Category.values)
    for number, row in enumerate(rows, start=2):
        where = f"posizioni.csv, riga {number}"
        if len(row) != len(POSITION_HEADER):
            _fail(f"{where}: numero di colonne non valido.")
        position_id = _parse_int(row[0], where)
        if position_id in seen:
            _fail(f"{where}: identificativo duplicato.")
        seen.add(position_id)
        name = restore_csv_text(row[1].strip())
        if not name or len(name) > 120:
            _fail(f"{where}: nome della posizione non valido.")
        category = row[2].strip()
        if category and category not in categories:
            _fail(f"{where}: categoria non valida.")
        identifier = restore_csv_text(row[4].strip())
        if len(identifier) > 32:
            _fail(f"{where}: identificativo troppo lungo.")
        price = _parse_optional_quantity(row[5], where)
        if price is not None and price < ZERO:
            _fail(f"{where}: prezzo corrente negativo.")
        price_date = _parse_optional_date(row[6], where)
        result.append(
            {
                "id": position_id,
                "name": name,
                "category": category,
                "identifier": identifier,
                "current_price": price,
                "price_updated_on": price_date,
                "archived": _parse_bool(row[7], where),
            }
        )
    return result


def _parse_investment_operations(rows: list[list[str]]) -> list[dict]:
    result = []
    seen: set[int] = set()
    kinds = set(InvestmentOperation.Kind.values)
    for number, row in enumerate(rows, start=2):
        where = f"operazioni_investimenti.csv, riga {number}"
        if len(row) != len(INVESTMENT_OPERATION_HEADER):
            _fail(f"{where}: numero di colonne non valido.")
        operation_id = _parse_int(row[0], where)
        if operation_id in seen:
            _fail(f"{where}: identificativo duplicato.")
        seen.add(operation_id)
        kind = row[3].strip()
        if kind not in kinds:
            _fail(f"{where}: tipo di operazione non valido.")
        movement_id = row[11].strip()
        account_id = row[12].strip()
        description = restore_csv_text(row[14])
        if len(description) > 255:
            _fail(f"{where}: descrizione troppo lunga.")
        result.append(
            {
                "id": operation_id,
                "position_id": _parse_int(row[1], where),
                "kind": kind,
                "date": _parse_date(row[5], where),
                "quantity": _parse_optional_quantity(row[6], where),
                "unit_price": _parse_optional_quantity(row[7], where),
                "gross_amount": _parse_optional_decimal(row[8], where),
                "commission": _parse_decimal(row[9], where),
                "cash_amount": _parse_decimal(row[10], where),
                "transaction_id": (
                    _parse_int(movement_id, where) if movement_id else None
                ),
                "account_id": _parse_int(account_id, where) if account_id else None,
                "description": description,
            }
        )
    return result


def _validate_investments(
    accounts: list[dict],
    transactions: list[dict],
    lines: list[dict],
    positions: list[dict],
    operations: list[dict],
):
    position_ids = {entry["id"] for entry in positions}
    account_ids = {entry["id"] for entry in accounts}
    transactions_by_id = {entry["id"]: entry for entry in transactions}
    lines_by_transaction: dict[int, list[dict]] = defaultdict(list)
    for line in lines:
        lines_by_transaction[line["transaction_id"]].append(line)

    transaction_kinds = {
        InvestmentOperation.Kind.BUY: Transaction.Kind.INVESTMENT_BUY,
        InvestmentOperation.Kind.SELL: Transaction.Kind.INVESTMENT_SELL,
        InvestmentOperation.Kind.DIVIDEND: Transaction.Kind.INVESTMENT_DIVIDEND,
    }
    operations_by_position: dict[int, list[dict]] = defaultdict(list)
    for operation in operations:
        where = f"operazioni_investimenti.csv, operazione {operation['id']}"
        if operation["position_id"] not in position_ids:
            _fail(f"{where}: la posizione non esiste nell'archivio.")
        if operation["kind"] == InvestmentOperation.Kind.OPENING:
            if operation["transaction_id"] is not None:
                _fail(f"{where}: l'apertura non deve avere un movimento.")
            if operation["account_id"] is not None:
                _fail(f"{where}: l'apertura non deve avere un conto.")
            if operation["cash_amount"] != ZERO:
                _fail(f"{where}: l'apertura non muove contante.")
            if operation["commission"] != ZERO:
                _fail(f"{where}: l'apertura non prevede commissioni.")
        else:
            if operation["commission"] < ZERO:
                _fail(f"{where}: la commissione non può essere negativa.")
            if operation["transaction_id"] is None:
                _fail(f"{where}: manca il movimento collegato.")
            movement = transactions_by_id.get(operation["transaction_id"])
            if movement is None:
                _fail(f"{where}: il movimento collegato non esiste.")
            if movement["kind"] != transaction_kinds[operation["kind"]]:
                _fail(f"{where}: il tipo del movimento non è coerente.")
            if movement["amount"] != operation["cash_amount"]:
                _fail(f"{where}: l'importo del movimento non è coerente.")
            if operation["account_id"] not in account_ids:
                _fail(f"{where}: il conto non esiste nell'archivio.")
            related = lines_by_transaction.get(operation["transaction_id"], [])
            if len(related) != 1:
                _fail(f"{where}: il movimento deve avere una sola riga.")
            line = related[0]
            if line["role"] != Line.Role.PRINCIPAL:
                _fail(f"{where}: la riga del movimento non è principale.")
            if line["account_id"] != operation["account_id"]:
                _fail(f"{where}: la riga non punta al conto indicato.")
            expected = (
                -operation["cash_amount"]
                if operation["kind"] == InvestmentOperation.Kind.BUY
                else operation["cash_amount"]
            )
            if line["amount"] != expected:
                _fail(f"{where}: la riga del movimento non quadra.")
            if operation["cash_amount"] <= ZERO:
                _fail(f"{where}: l'importo in contante deve essere positivo.")

        if operation["kind"] == InvestmentOperation.Kind.DIVIDEND:
            if operation["commission"] != ZERO:
                _fail(f"{where}: il dividendo non prevede commissioni.")
            if (
                operation["quantity"] is not None
                or operation["unit_price"] is not None
                or operation["gross_amount"] is not None
            ):
                _fail(f"{where}: il dividendo non prevede quantità o prezzo.")
        else:
            if operation["quantity"] is None or operation["quantity"] <= ZERO:
                _fail(f"{where}: la quantità deve essere maggiore di zero.")
            if operation["unit_price"] is None or operation["unit_price"] <= ZERO:
                _fail(f"{where}: il prezzo unitario deve essere maggiore di zero.")
            if (
                operation["gross_amount"] is None
                or operation["gross_amount"] <= ZERO
            ):
                _fail(f"{where}: il controvalore deve essere maggiore di zero.")
            if operation["kind"] in (
                InvestmentOperation.Kind.BUY,
                InvestmentOperation.Kind.SELL,
            ):
                expected_cash = (
                    operation["gross_amount"] + operation["commission"]
                    if operation["kind"] == InvestmentOperation.Kind.BUY
                    else operation["gross_amount"] - operation["commission"]
                )
                if operation["cash_amount"] != expected_cash:
                    _fail(
                        f"{where}: il contante non quadra con il controvalore."
                    )
        operations_by_position[operation["position_id"]].append(operation)

    for position_id, entries in operations_by_position.items():
        openings = [
            entry
            for entry in entries
            if entry["kind"] == InvestmentOperation.Kind.OPENING
        ]
        if len(openings) > 1:
            _fail(
                "operazioni_investimenti.csv: una posizione può avere una sola "
                "apertura."
            )
        ordered = sorted(entries, key=lambda entry: (entry["date"], entry["id"]))
        if openings and ordered[0]["kind"] != InvestmentOperation.Kind.OPENING:
            _fail(
                "operazioni_investimenti.csv: l'apertura deve essere la prima "
                "operazione della posizione."
            )
        held = Decimal("0.00000000")
        for entry in ordered:
            if entry["kind"] == InvestmentOperation.Kind.OPENING:
                held = entry["quantity"]
            elif entry["kind"] == InvestmentOperation.Kind.BUY:
                held = held + entry["quantity"]
            elif entry["kind"] == InvestmentOperation.Kind.SELL:
                if entry["quantity"] > held:
                    _fail(
                        "operazioni_investimenti.csv: vendita superiore alla "
                        f"quantità posseduta (posizione {position_id})."
                    )
                held = held - entry["quantity"]


def _validate(
    manifest: dict,
    schema: int,
    accounts: list[dict],
    savings: list[dict],
    transactions: list[dict],
    lines: list[dict],
    positions: list[dict],
    operations: list[dict],
    categories: list[dict] | None = None,
    tags: list[dict] | None = None,
    movtags: list[dict] | None = None,
):
    account_ids = {entry["id"] for entry in accounts}
    savings_ids = {entry["id"] for entry in savings}
    transaction_ids = {entry["id"] for entry in transactions}
    if schema >= 3:
        category_ids = {entry["id"] for entry in (categories or [])}
        for entry in transactions:
            if entry.get("category_id") is not None and entry.get(
                "category_id"
            ) not in category_ids:
                _fail(
                    f"movimenti.csv: il movimento {entry['id']} indica una "
                    "categoria inesistente."
                )

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
        elif operation["kind"] in (
            Transaction.Kind.EXPENSE,
            Transaction.Kind.INVESTMENT_BUY,
        ):
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

    if schema == 1:
        investment_kinds = {
            Transaction.Kind.INVESTMENT_BUY,
            Transaction.Kind.INVESTMENT_SELL,
            Transaction.Kind.INVESTMENT_DIVIDEND,
        }
        if any(
            operation["kind"] in investment_kinds for operation in transactions
        ):
            _fail(
                "Un archivio schema 1 non può contenere movimenti di "
                "investimento."
            )
    if schema >= 2:
        _validate_investments(
            accounts, transactions, lines, positions, operations
        )
        investment_account_id = manifest.get("conto_investimenti_id")
        if (
            investment_account_id is not None
            and investment_account_id not in account_ids
        ):
            _fail(
                "Il conto degli investimenti del manifest non esiste "
                "nell'archivio."
            )

    counts = manifest.get("conteggi")
    expected_counts = {
        "conti": len(accounts),
        "salvadanai": len(savings),
        "movimenti": len(transactions),
        "righe": len(lines),
    }
    if schema == 2:
        expected_counts["posizioni"] = len(positions)
        expected_counts["operazioni_investimenti"] = len(operations)
    if schema >= 3:
        expected_counts["posizioni"] = len(positions)
        expected_counts["operazioni_investimenti"] = len(operations)
        expected_counts["categorie"] = len(categories or [])
        expected_counts["tag"] = len(tags or [])
        expected_counts["movimento_tag"] = len(movtags or [])
    if counts != expected_counts:
        _fail("I conteggi del manifest non corrispondono ai file.")


def _profile_has_data(profile: Profile) -> bool:
    return (
        Account.objects.filter(profile=profile).exists()
        or SavingsAccount.objects.filter(profile=profile).exists()
        or Transaction.objects.filter(profile=profile).exists()
        or InvestmentPosition.objects.filter(profile=profile).exists()
    )


def _parse_archive(raw: bytes):
    contents = _read_zip(raw)
    manifest = _read_manifest(contents)
    schema = manifest["schema"]
    csv_names = {1: SCHEMA1_CSV, 2: SCHEMA2_CSV, 3: SCHEMA3_CSV}[schema]
    expected_names = ARCHIVE_NAMES_BY_SCHEMA[schema]
    if set(contents) != expected_names:
        _fail("I file dell'archivio non corrispondono alla versione indicata.")
    parsed_rows = {
        name: _csv_rows(contents, name, schema) for name in csv_names
    }
    _check_checksums(contents, manifest, parsed_rows, csv_names)
    accounts = _parse_accounts(parsed_rows["conti.csv"])
    savings = _parse_savings(parsed_rows["salvadanai.csv"])
    transactions = _parse_transactions(parsed_rows["movimenti.csv"], schema)
    lines = _parse_lines(parsed_rows["righe.csv"])
    if schema == 2:
        positions = _parse_positions(parsed_rows["posizioni.csv"])
        operations = _parse_investment_operations(
            parsed_rows["operazioni_investimenti.csv"]
        )
        categories, tags, movtags = [], [], []
    elif schema == 3:
        positions = _parse_positions(parsed_rows["posizioni.csv"])
        operations = _parse_investment_operations(
            parsed_rows["operazioni_investimenti.csv"]
        )
        categories = _parse_categories(parsed_rows["categorie.csv"])
        tags = _parse_tags(parsed_rows["tag.csv"])
        movtags = _parse_movtags(
            parsed_rows["movimento_tag.csv"],
            {entry["id"] for entry in transactions},
            {entry["id"] for entry in tags},
        )
    else:
        positions, operations = [], []
        categories, tags, movtags = [], [], []
    _validate(
        manifest,
        schema,
        accounts,
        savings,
        transactions,
        lines,
        positions,
        operations,
        categories,
        tags,
        movtags,
    )
    return (
        manifest,
        accounts,
        savings,
        transactions,
        lines,
        positions,
        operations,
        categories,
        tags,
        movtags,
    )


# --------------------------------------------------------------------------- #
# Analysis
# --------------------------------------------------------------------------- #


def _investment_totals(positions: list[dict], operations: list[dict]) -> dict:
    held = {
        position["id"]: Decimal("0.00000000") for position in positions
    }
    cost = {position["id"]: ZERO for position in positions}
    for entry in sorted(
        operations, key=lambda item: (item["position_id"], item["date"], item["id"])
    ):
        position_id = entry["position_id"]
        if entry["kind"] == InvestmentOperation.Kind.OPENING:
            held[position_id] = entry["quantity"]
            cost[position_id] = _round_money(entry["gross_amount"])
        elif entry["kind"] == InvestmentOperation.Kind.BUY:
            held[position_id] = held[position_id] + entry["quantity"]
            cost[position_id] = _round_money(
                cost[position_id] + entry["gross_amount"] + entry["commission"]
            )
        elif entry["kind"] == InvestmentOperation.Kind.SELL:
            sold = entry["quantity"]
            previous = cost[position_id]
            removed = (
                previous
                if sold == held[position_id]
                else _round_money(previous * sold / held[position_id])
            )
            held[position_id] = held[position_id] - sold
            cost[position_id] = (
                ZERO if held[position_id] == 0 else _round_money(previous - removed)
            )
    total_cost = _round_money(sum(cost.values(), ZERO))
    total_value = ZERO
    for position in positions:
        if position["current_price"] is not None:
            total_value = total_value + _round_money(
                held[position["id"]] * position["current_price"]
            )
    return {
        "cost": total_cost,
        "value": _round_money(total_value),
        "held": held,
        "cost_by_position": cost,
    }


def _summary(
    accounts: list[dict],
    savings: list[dict],
    transactions: list[dict],
    lines: list[dict],
    positions: list[dict],
    operations: list[dict],
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
    investment = _investment_totals(positions, operations)
    dates = [operation["date"] for operation in transactions]
    return {
        "accounts": len(accounts),
        "savings": len(savings),
        "transactions": len(transactions),
        "lines": len(lines),
        "positions": len(positions),
        "investment_operations": len(operations),
        "from": min(dates).isoformat() if dates else None,
        "to": max(dates).isoformat() if dates else None,
        "accounts_total": f"{accounts_total:.2f}",
        "savings_total": f"{savings_total:.2f}",
        "investments_cost": f"{investment['cost']:.2f}",
        "investments_value": f"{investment['value']:.2f}",
        "patrimony_total": (
            f"{accounts_total + savings_total + investment['cost']:.2f}"
        ),
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
    (
        manifest,
        accounts,
        savings,
        transactions,
        lines,
        positions,
        operations,
        categories,
        tags,
        movtags,
    ) = _parse_archive(raw)
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
            "conto_investimenti_id": manifest.get("conto_investimenti_id"),
            "conto_investimenti": manifest.get("conto_investimenti"),
            "conteggi": manifest.get("conteggi"),
        },
        "summary": _summary(
            accounts, savings, transactions, lines, positions, operations
        ),
        "warnings": warnings,
    }


# --------------------------------------------------------------------------- #
# Restore
# --------------------------------------------------------------------------- #


def restore_archive(raw: bytes, profile: Profile) -> dict:
    (
        manifest,
        accounts,
        savings,
        transactions,
        lines,
        positions,
        operations,
        categories,
        tags,
        movtags,
    ) = _parse_archive(raw)
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

        if manifest.get("schema", 1) >= 3:
            Category.objects.filter(profile=profile).delete()
            Tag.objects.filter(profile=profile).delete()
            category_objects = [
                Category(
                    profile=profile,
                    name=entry["name"],
                    is_preset=entry["is_preset"],
                    is_default=entry["is_default"],
                )
                for entry in categories
            ]
            Category.objects.bulk_create(category_objects)
            category_map = {
                entry["id"]: category
                for entry, category in zip(categories, category_objects)
            }
            tag_objects = [
                Tag(profile=profile, name=entry["name"]) for entry in tags
            ]
            Tag.objects.bulk_create(tag_objects)
            tag_map = {
                entry["id"]: tag
                for entry, tag in zip(tags, tag_objects)
            }
        else:
            defaults = ensure_default_categories(profile)
            default_category = defaults[DEFAULT_CATEGORY_NAME]
            category_map = {}
            tag_map = {}

        transaction_objects = [
            Transaction(
                profile=profile,
                kind=entry["kind"],
                date=entry["date"],
                description=entry["description"],
                amount=entry["amount"],
                category=(
                    category_map.get(entry["category_id"])
                    if manifest.get("schema", 1) >= 3
                    else default_category
                ),
            )
            for entry in transactions
        ]
        Transaction.objects.bulk_create(transaction_objects)
        transaction_map = {
            entry["id"]: operation
            for entry, operation in zip(transactions, transaction_objects)
        }
        if manifest.get("schema", 1) >= 3 and movtags:
            through = Transaction.tags.through
            through.objects.bulk_create(
                [
                    through(
                        transaction_id=transaction_map[item["transaction_id"]].id,
                        tag_id=tag_map[item["tag_id"]].id,
                    )
                    for item in movtags
                ]
            )

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

        position_objects = [
            InvestmentPosition(
                profile=profile,
                name=entry["name"],
                category=entry["category"],
                identifier=entry["identifier"],
                current_price=entry["current_price"],
                price_updated_on=entry["price_updated_on"],
                archived=entry["archived"],
            )
            for entry in positions
        ]
        InvestmentPosition.objects.bulk_create(position_objects)
        position_map = {
            entry["id"]: position
            for entry, position in zip(positions, position_objects)
        }

        InvestmentOperation.objects.bulk_create(
            [
                InvestmentOperation(
                    profile=profile,
                    position=position_map[entry["position_id"]],
                    kind=entry["kind"],
                    date=entry["date"],
                    quantity=entry["quantity"],
                    unit_price=entry["unit_price"],
                    gross_amount=entry["gross_amount"],
                    commission=entry["commission"],
                    cash_amount=entry["cash_amount"],
                    description=entry["description"],
                    transaction=(
                        transaction_map[entry["transaction_id"]]
                        if entry["transaction_id"] is not None
                        else None
                    ),
                )
                for entry in operations
            ]
        )

        investment_account_id = manifest.get("conto_investimenti_id")
        if investment_account_id is not None:
            Profile.objects.filter(pk=profile.pk).update(
                investment_account=account_map[investment_account_id]
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
    investment = _investment_totals(positions, operations)
    return {
        "accounts": len(account_objects),
        "savings": len(savings_objects),
        "transactions": len(transaction_objects),
        "lines": len(lines),
        "positions": len(position_objects),
        "investment_operations": len(operations),
        "accounts_total": f"{accounts_total:.2f}",
        "savings_total": f"{savings_total:.2f}",
        "investments_cost": f"{investment['cost']:.2f}",
        "investments_value": f"{investment['value']:.2f}",
        "patrimony_total": (
            f"{accounts_total + savings_total + investment['cost']:.2f}"
        ),
        "balances": {
            "accounts": account_balances,
            "savings": savings_balances,
        },
    }
