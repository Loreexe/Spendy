#!/usr/bin/env python3
"""Invio di alert operativi di Spendy tramite webhook (formato ntfy).

Uso:
    python3 scripts/alert.py failure <unità-systemd>
    python3 scripts/alert.py test

Il messaggio non contiene dati finanziari né segreti: solo host, unità e ora.
Se ``SPENDY_ALERT_WEBHOOK`` non è impostato l'alert finisce solo nel journal,
così la configurazione minima resta sicura e non silenziosa.
"""
from __future__ import annotations

import os
import socket
import sys
from datetime import datetime, timezone
from urllib.error import URLError
from urllib.request import Request, urlopen

WEBHOOK_ENV = "SPENDY_ALERT_WEBHOOK"
HOSTNAME = socket.gethostname()
TIMEOUT_SECONDS = 10


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def send_alert(title: str, message: str, priority: str = "high") -> bool:
    """Send a plain-text alert; return False when no webhook is configured."""
    url = os.environ.get(WEBHOOK_ENV, "").strip()
    if not url:
        print(f"[alert] {title}: {message}", file=sys.stderr, flush=True)
        return False
    request = Request(
        url,
        data=message.encode("utf-8"),
        headers={
            "Title": title,
            "Priority": priority,
            "Tags": "warning",
            "Content-Type": "text/plain; charset=utf-8",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            response.read()
    except (URLError, TimeoutError, OSError) as exc:
        print(f"[alert] invio non riuscito: {exc}", file=sys.stderr, flush=True)
        return False
    print(f"[alert] inviato: {title}", flush=True)
    return True


def failure_message(unit: str) -> str:
    name = unit if "." in unit else f"{unit}.service"
    return (
        f"Unità {name} fallita su {HOSTNAME} alle {_now_iso()}.\n"
        f"Controlla: journalctl -u {name}"
    )


def main(argv: list[str]) -> int:
    kind = argv[1] if len(argv) > 1 else "failure"
    detail = argv[2] if len(argv) > 2 else "spendy"
    if kind == "test":
        send_alert(
            "Spendy — prova alert",
            f"Alert di prova da {HOSTNAME} alle {_now_iso()}.",
            priority="default",
        )
        return 0
    message = failure_message(detail)
    send_alert("Spendy — errore operativo", message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
