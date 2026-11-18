"""Contesto della richiesta MCP, usato per il tag AI sui movimenti."""
from __future__ import annotations

from contextvars import ContextVar, Token as ContextToken

_current_mcp_token: ContextVar[object | None] = ContextVar(
    "current_mcp_token", default=None
)


def set_current_mcp_token(token) -> ContextToken:
    return _current_mcp_token.set(token)


def reset_current_mcp_token(context: ContextToken) -> None:
    _current_mcp_token.reset(context)


def current_mcp_token():
    return _current_mcp_token.get()
