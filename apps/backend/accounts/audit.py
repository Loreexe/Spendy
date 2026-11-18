"""Registrazione centralizzata degli eventi sensibili (V05, Fase S)."""
from __future__ import annotations

import logging
from typing import Any

from core.net import get_client_ip

from .models import AuditEvent, User

logger = logging.getLogger(__name__)


def record_audit(
    request,
    action: str,
    actor: User | None = None,
    target: str = "",
    metadata: dict[str, Any] | None = None,
) -> None:
    """Append an audit event; failures never break the main operation."""
    try:
        ip = get_client_ip(request) if request is not None else None
        user_agent = (
            request.META.get("HTTP_USER_AGENT", "")[:255]
            if request is not None
            else ""
        )
        AuditEvent.objects.create(
            actor=actor,
            action=action,
            target=(target or "")[:200],
            ip=str(ip) if ip is not None else None,
            user_agent=user_agent,
            metadata=metadata or {},
        )
    except Exception:  # pragma: no cover - l'audit non deve rompere l'azione
        logger.exception("Registrazione audit non riuscita per %s", action)
