#!/usr/bin/env python3
"""Controlli operativi di Spendy: backup, disco e certificato TLS.

Eseguito dal timer systemd sull'host LXC. Se trova un problema invia un alert
tramite ``scripts/alert.py`` (webhook ntfy) e lo scrive nel journal; non espone
dati finanziari né segreti.

Variabili (vedi ``deploy/backup.env.example``):
    SPENDY_BACKUP_STATUS_FILE       default /opt/spendy/backup-status/status.json
    SPENDY_BACKUP_MAX_AGE_MINUTES   default 30
    SPENDY_DISK_PATH                default /
    SPENDY_DISK_MAX_PERCENT         default 85
    SPENDY_DOMAIN                   opzionale, abilita il controllo TLS
    SPENDY_CERT_MIN_DAYS            default 14
"""
from __future__ import annotations

import json
import os
import shutil
import socket
import ssl
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from alert import send_alert

DEFAULT_STATUS_FILE = "/opt/spendy/backup-status/status.json"


def parse_iso(value: str | None) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def check_backup(
    status_file: str | Path,
    max_age_minutes: int,
    now: datetime | None = None,
) -> list[str]:
    moment = now or datetime.now(timezone.utc)
    path = Path(status_file)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return [f"stato del backup non leggibile in {path}"]
    if not isinstance(data, dict):
        return [f"stato del backup non valido in {path}"]

    problems: list[str] = []
    if data.get("status") == "failed":
        problems.append(
            "l'ultimo backup è fallito: "
            + str(data.get("last_error") or "nessun dettaglio")
        )
    last_success = parse_iso(data.get("last_success"))
    if last_success is None:
        last_run = parse_iso(data.get("last_run"))
        if last_run is None or moment - last_run > _minutes(max_age_minutes):
            problems.append(
                "nessun backup riuscito registrato "
                f"(ultimo tentativo: {data.get('last_run') or 'assente'})"
            )
    elif moment - last_success > _minutes(max_age_minutes):
        problems.append(
            "ultimo backup riuscito troppo vecchio: "
            f"{last_success.isoformat()} "
            f"(soglia {max_age_minutes} minuti)"
        )
    return problems


def check_disk(path: str, max_percent: int) -> list[str]:
    try:
        usage = shutil.disk_usage(path)
    except OSError as exc:
        return [f"disco non verificabile ({path}): {exc}"]
    percent = usage.used / usage.total * 100 if usage.total else 0
    if percent >= max_percent:
        return [
            f"spazio disco su {path} al {percent:.0f}% "
            f"(soglia {max_percent}%)"
        ]
    return []


def _days_until(timestamp: float, now: datetime | None = None) -> float:
    moment = now or datetime.now(timezone.utc)
    return (timestamp - moment.timestamp()) / 86400


def _certificate_timestamp(domain: str) -> float:
    context = ssl.create_default_context()
    with socket.create_connection((domain, 443), timeout=8) as sock:
        with context.wrap_socket(sock, server_hostname=domain) as tls:
            certificate = tls.getpeercert()
    not_after = certificate.get("notAfter") if certificate else None
    if not not_after:
        raise ssl.SSLError("certificato senza data di scadenza")
    return ssl.cert_time_to_seconds(not_after)


def check_certificate(
    domain: str,
    min_days: int,
    now: datetime | None = None,
) -> list[str]:
    if not domain:
        return []
    try:
        timestamp = _certificate_timestamp(domain)
    except (OSError, ssl.SSLError, ValueError) as exc:
        return [f"certificato TLS di {domain} non verificabile: {exc}"]
    days = _days_until(timestamp, now)
    if days < min_days:
        return [
            f"certificato TLS di {domain} in scadenza: "
            f"{days:.0f} giorni (soglia {min_days})"
        ]
    return []


def _minutes(value: int) -> timedelta:
    return timedelta(minutes=value)


def run_checks(environ: dict[str, str] | None = None) -> list[str]:
    env = environ if environ is not None else os.environ
    problems: list[str] = []
    problems.extend(
        check_backup(
            env.get("SPENDY_BACKUP_STATUS_FILE", DEFAULT_STATUS_FILE),
            int(env.get("SPENDY_BACKUP_MAX_AGE_MINUTES", "30")),
        )
    )
    problems.extend(
        check_disk(
            env.get("SPENDY_DISK_PATH", "/"),
            int(env.get("SPENDY_DISK_MAX_PERCENT", "85")),
        )
    )
    problems.extend(
        check_certificate(
            env.get("SPENDY_DOMAIN", "").strip(),
            int(env.get("SPENDY_CERT_MIN_DAYS", "14")),
        )
    )
    return problems


def main() -> int:
    problems = run_checks()
    if not problems:
        print("healthcheck Spendy: nessun problema", flush=True)
        return 0
    message = "\n".join(f"- {problem}" for problem in problems)
    print(f"healthcheck Spendy: problemi\n{message}", file=sys.stderr, flush=True)
    send_alert("Spendy — controllo operativo", message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
