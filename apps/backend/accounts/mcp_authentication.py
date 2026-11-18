"""Autenticazione e autorizzazione dei token MCP sulle API v1 (DC-123)."""
from __future__ import annotations

import time
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied, Throttled

from .audit import record_audit
from .mcp import resolve_operation
from .mcp_context import set_current_mcp_token
from .models import AuditEvent, McpToken


class McpTokenAuthentication(BaseAuthentication):
    keyword = "Bearer"

    def authenticate(self, request):
        header = get_authorization_header(request).split()
        if len(header) != 2 or header[0].lower() != self.keyword.lower().encode():
            return None
        try:
            raw_key = header[1].decode("utf-8")
        except UnicodeError:
            return None
        if not raw_key.startswith("mcp_"):
            return None

        token = (
            McpToken.objects.select_related("user")
            .filter(key_hash=McpToken.hash_key(raw_key), revoked_at__isnull=True)
            .first()
        )
        if token is None:
            raise AuthenticationFailed("Token MCP non valido o revocato.")
        if not token.user.is_active:
            raise AuthenticationFailed("Account non attivo.")

        django_request = request._request
        is_context = django_request.path.rstrip("/") == "/api/v1/mcp/context"
        operation = resolve_operation(django_request)
        if is_context:
            operation = None
        elif operation is None:
            self._deny(
                django_request, token, None, "operation_not_exposed"
            )
            raise PermissionDenied("Operazione non esposta via MCP.")
        if not is_context and token.permission_for(operation) is None:
            self._deny(django_request, token, operation, "permission_denied")
            raise PermissionDenied(
                "Operazione non consentita per questo token."
            )
        if not is_context:
            self._check_rate_limit(django_request, token, operation)

        now = timezone.now()
        if token.last_used_at is None or now - token.last_used_at > timedelta(
            minutes=1
        ):
            McpToken.objects.filter(pk=token.pk).update(last_used_at=now)
            token.last_used_at = now

        context = set_current_mcp_token(token)
        django_request._mcp_token = token
        django_request._mcp_operation = (
            operation.id if operation is not None else "mcp.context"
        )
        django_request._mcp_context = context
        return (token.user, token)

    def authenticate_header(self, request) -> str:
        return self.keyword

    def _deny(self, request, token, operation, reason: str) -> None:
        record_audit(
            request,
            AuditEvent.Action.MCP_CALL,
            actor=token.user,
            target=operation.id if operation is not None else request.path,
            metadata={"result": "denied", "reason": reason},
        )

    def _check_rate_limit(self, request, token, operation) -> None:
        minute = int(time.time()) // 60
        limit = int(getattr(settings, "MCP_RATE_LIMIT_PER_MINUTE", 60))
        key = f"mcp-rate:{token.pk}:{minute}"
        count = cache.get(key, 0)
        if count >= limit:
            self._deny(request, token, operation, "rate_limit")
            raise Throttled(
                detail="Troppe richieste MCP. Riprova tra poco.",
                wait=60 - int(time.time()) % 60,
            )
        cache.set(key, count + 1, timeout=120)

        if operation.kind != "write":
            return
        write_limit = int(
            getattr(settings, "MCP_WRITE_RATE_LIMIT_PER_MINUTE", 20)
        )
        write_key = f"mcp-write:{token.pk}:{minute}"
        write_count = cache.get(write_key, 0)
        if write_count >= write_limit:
            self._deny(request, token, operation, "write_rate_limit")
            raise Throttled(
                detail="Troppe scritture MCP. Riprova tra poco.",
                wait=60 - int(time.time()) % 60,
            )
        cache.set(write_key, write_count + 1, timeout=120)
