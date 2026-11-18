"""Timeout di inattività delle sessioni web e registrazione della scadenza."""
from __future__ import annotations

import time

from django.conf import settings
from django.contrib.auth import logout
from django.http import JsonResponse

from .audit import record_audit
from .mcp_context import reset_current_mcp_token
from .models import AuditEvent

ACTIVITY_KEY = "last_activity"
UPDATE_INTERVAL_SECONDS = 60


class SessionIdleTimeoutMiddleware:
    """Chiude la sessione dopo ``SESSION_IDLE_TIMEOUT_SECONDS`` di inattività.

    La durata assoluta resta gestita da ``SESSION_COOKIE_AGE``. Per le API la
    scadenza risponde ``401`` con codice ``session_expired``; il frontend
    reindirizza al login. L'attività viene aggiornata al massimo una volta al
    minuto per non scrivere la sessione a ogni richiesta.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            now = time.time()
            last = request.session.get(ACTIVITY_KEY)
            try:
                last_value = float(last) if last is not None else None
            except (TypeError, ValueError):
                last_value = None

            timeout = int(
                getattr(settings, "SESSION_IDLE_TIMEOUT_SECONDS", 7200)
            )
            if last_value is not None and now - last_value > timeout:
                record_audit(
                    request,
                    AuditEvent.Action.SESSION_EXPIRED,
                    actor=user,
                )
                logout(request)
                if request.path.startswith("/api/"):
                    return JsonResponse(
                        {
                            "detail": "Sessione scaduta per inattività.",
                            "code": "session_expired",
                        },
                        status=401,
                    )

            if last_value is None or now - last_value > UPDATE_INTERVAL_SECONDS:
                request.session[ACTIVITY_KEY] = now

        return self.get_response(request)


class McpAuditMiddleware:
    """Registra l'esito delle chiamate MCP autorizzate (DC-123)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        started = time.monotonic()
        response = None
        try:
            response = self.get_response(request)
            return response
        finally:
            token = getattr(request, "_mcp_token", None)
            if token is not None:
                status = getattr(response, "status_code", 500)
                record_audit(
                    request,
                    AuditEvent.Action.MCP_CALL,
                    actor=token.user,
                    target=getattr(request, "_mcp_operation", ""),
                    metadata={
                        "result": "ok" if status < 400 else "error",
                        "status": status,
                        "duration_ms": int(
                            (time.monotonic() - started) * 1000
                        ),
                    },
                )
            context = getattr(request, "_mcp_context", None)
            if context is not None:
                reset_current_mcp_token(context)
