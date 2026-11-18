"""Flag host-side per accendere/spegnere il servizio MCP (DC-123)."""
from __future__ import annotations

import json
import os
from pathlib import Path

from django.conf import settings

DEFAULT_STATE = {"enabled": False}


def state_path() -> Path:
    return Path(
        getattr(
            settings,
            "MCP_CONTROL_FILE",
            str(Path(settings.BASE_DIR) / "mcp-control" / "state.json"),
        )
    )


def read_state() -> dict:
    try:
        data = json.loads(state_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return dict(DEFAULT_STATE)
    if not isinstance(data, dict):
        return dict(DEFAULT_STATE)
    return {"enabled": bool(data.get("enabled", False))}


def write_state(enabled: bool) -> dict:
    path = state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    payload = {"enabled": bool(enabled)}
    temporary.write_text(
        json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8"
    )
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)
    return payload
