#!/usr/bin/env bash
# Accende/spegne solo il container MCP in base al flag scritto dal pannello.
set -euo pipefail

if [ -n "${SPENDY_ROOT:-}" ]; then
    ROOT="$(cd "$SPENDY_ROOT" && pwd)"
else
    ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fi
cd "$ROOT"

STATE="${SPENDY_MCP_CONTROL_FILE:-$ROOT/mcp-control/state.json}"
DOCKER=(docker compose)
ENV_ARGS=()
if [ -n "${SPENDY_COMPOSE_ENV_FILE:-}" ]; then
    ENV_ARGS=(--env-file "$SPENDY_COMPOSE_ENV_FILE")
fi

command -v docker >/dev/null || { echo "docker non trovato" >&2; exit 1; }
command -v python3 >/dev/null || { echo "python3 non trovato" >&2; exit 1; }

LOCK_FILE="${SPENDY_MCP_LOCK:-/run/lock/spendy-mcp-toggle.lock}"
if { exec 9>"$LOCK_FILE"; } 2>/dev/null; then
    if command -v flock >/dev/null; then
        flock -n 9 || exit 0
    fi
fi

enabled="$(python3 - "$STATE" <<'PY'
import json
import sys
try:
    with open(sys.argv[1], encoding="utf-8") as handle:
        data = json.load(handle)
except Exception:
    print("0")
else:
    print("1" if data.get("enabled") else "0")
PY
)"

if [ "$enabled" = "1" ]; then
    echo "MCP: attivo, avvio del container ..."
    "${DOCKER[@]}" "${ENV_ARGS[@]}" --profile mcp up -d --no-deps mcp
else
    echo "MCP: disattivato, stop del container ..."
    "${DOCKER[@]}" "${ENV_ARGS[@]}" stop mcp >/dev/null 2>&1 || true
fi
