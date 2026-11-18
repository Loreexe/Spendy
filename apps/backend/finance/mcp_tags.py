"""Tag AI sui movimenti scritti durante una richiesta MCP (DC-123)."""
from __future__ import annotations

from .models import Tag

AI_TAG_NAME = "AI"


def apply_ai_tag(transaction) -> None:
    """Add the normal, auto-created ``AI`` tag to a movement if missing."""
    if not transaction.profile_id or transaction.is_deleted:
        return
    if transaction.tags.filter(name=AI_TAG_NAME).exists():
        return
    tag, _ = Tag.objects.get_or_create(
        profile=transaction.profile, name=AI_TAG_NAME
    )
    transaction.tags.add(tag)


def apply_ai_tag_if_mcp(transaction) -> None:
    """Apply the AI tag only during an MCP request for the same profile."""
    from accounts.mcp_context import current_mcp_token

    token = current_mcp_token()
    if token is None or not transaction.profile_id or transaction.is_deleted:
        return
    if transaction.profile.user_id != token.user_id:
        return
    apply_ai_tag(transaction)
