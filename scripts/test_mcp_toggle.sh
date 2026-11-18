#!/usr/bin/env bash
# Test del toggle host-side MCP: verifica solo i comandi Docker emessi.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE="$(mktemp -d)"
trap 'rm -rf "$BASE"' EXIT

mkdir -p "$BASE/bin" "$BASE/repo/mcp-control"
cat > "$BASE/bin/docker" <<'DOCKER'
#!/usr/bin/env bash
printf '%s\n' "$*" >> "$DOCKER_LOG"
DOCKER
chmod +x "$BASE/bin/docker"
cp "$SCRIPT_DIR/mcp_toggle.sh" "$BASE/repo/mcp_toggle.sh"
chmod +x "$BASE/repo/mcp_toggle.sh"

printf '{"enabled": true}\n' > "$BASE/repo/mcp-control/state.json"
DOCKER_LOG="$BASE/on.log" SPENDY_ROOT="$BASE/repo" \
    PATH="$BASE/bin:$PATH" SPENDY_MCP_CONTROL_FILE="$BASE/repo/mcp-control/state.json" \
    "$BASE/repo/mcp_toggle.sh"
grep -q -- "--profile mcp up -d --no-deps mcp" "$BASE/on.log" ||
    { echo "TEST FALLITO: avvio MCP assente" >&2; exit 1; }

printf '{"enabled": false}\n' > "$BASE/repo/mcp-control/state.json"
DOCKER_LOG="$BASE/off.log" SPENDY_ROOT="$BASE/repo" \
    PATH="$BASE/bin:$PATH" SPENDY_MCP_CONTROL_FILE="$BASE/repo/mcp-control/state.json" \
    "$BASE/repo/mcp_toggle.sh"
grep -q -- "stop mcp" "$BASE/off.log" ||
    { echo "TEST FALLITO: stop MCP assente" >&2; exit 1; }

printf 'non-json\n' > "$BASE/repo/mcp-control/state.json"
DOCKER_LOG="$BASE/invalid.log" SPENDY_ROOT="$BASE/repo" \
    PATH="$BASE/bin:$PATH" SPENDY_MCP_CONTROL_FILE="$BASE/repo/mcp-control/state.json" \
    "$BASE/repo/mcp_toggle.sh"
grep -q -- "stop mcp" "$BASE/invalid.log" ||
    { echo "TEST FALLITO: flag non valido non spegne" >&2; exit 1; }

echo "Test mcp_toggle.sh: OK"
