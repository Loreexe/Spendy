"""TOTP (RFC 6238) e codici di recupero, senza dipendenze esterne.

Il segreto è conservato nel database (protetto dal disco cifrato e dai backup
cifrati); l'app non salva mai il segreto nei log né lo restituisce dopo il
setup. I codici di recupero sono monouso e salvati solo come hash SHA-256:
sono generati con 60 bit di entropia, quindi l'hash non salato è sufficiente.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import struct
from datetime import datetime, timezone
from urllib.parse import quote, urlencode

DIGITS = 6
PERIOD_SECONDS = 30
WINDOW_STEPS = 1
ISSUER = "Spendy"
SECRET_BYTES = 20
RECOVERY_CODE_COUNT = 10
RECOVERY_CODE_LENGTH = 12
RECOVERY_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"


def generate_secret() -> str:
    """Return a new base32 secret without padding (160 bit)."""
    return (
        base64.b32encode(secrets.token_bytes(SECRET_BYTES))
        .decode("ascii")
        .rstrip("=")
    )


def _decode_secret(secret: str) -> bytes:
    padded = secret.strip().upper()
    padded += "=" * ((8 - len(padded) % 8) % 8)
    return base64.b32decode(padded)


def _time_counter(moment: datetime | None = None) -> int:
    value = moment or datetime.now(timezone.utc)
    return int(value.timestamp() // PERIOD_SECONDS)


def code_for_counter(secret: str, counter: int) -> str:
    digest = hmac.new(
        _decode_secret(secret), struct.pack(">Q", counter), hashlib.sha1
    ).digest()
    offset = digest[-1] & 0x0F
    value = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return f"{value % (10 ** DIGITS):0{DIGITS}d}"


def verify_code(
    secret: str, code: str, moment: datetime | None = None
) -> int | None:
    """Return the TOTP counter matching ``code`` within the accepted window."""
    cleaned = "".join(char for char in (code or "") if char.isdigit())
    if len(cleaned) != DIGITS:
        return None
    current = _time_counter(moment)
    for offset in range(-WINDOW_STEPS, WINDOW_STEPS + 1):
        counter = current + offset
        expected = code_for_counter(secret, counter)
        if hmac.compare_digest(expected, cleaned):
            return counter
    return None


def provisioning_uri(secret: str, account_name: str) -> str:
    label = quote(f"{ISSUER}:{account_name}")
    query = urlencode(
        {
            "secret": secret,
            "issuer": ISSUER,
            "algorithm": "SHA1",
            "digits": DIGITS,
            "period": PERIOD_SECONDS,
        }
    )
    return f"otpauth://totp/{label}?{query}"


def _normalize_recovery_code(value: str) -> str:
    return "".join(char for char in (value or "").upper() if char.isalnum())


def hash_recovery_code(value: str) -> str:
    return hashlib.sha256(
        _normalize_recovery_code(value).encode("utf-8")
    ).hexdigest()


def generate_recovery_codes(count: int = RECOVERY_CODE_COUNT) -> list[str]:
    codes: list[str] = []
    while len(codes) < count:
        raw = "".join(
            secrets.choice(RECOVERY_ALPHABET)
            for _ in range(RECOVERY_CODE_LENGTH)
        )
        formatted = "-".join(
            raw[index : index + 4]
            for index in range(0, RECOVERY_CODE_LENGTH, 4)
        )
        if formatted not in codes:
            codes.append(formatted)
    return codes
