#!/usr/bin/env bash
#
# Test di regressione per scripts/update.sh.
# Crea un repository temporaneo con un remote locale e simula Docker/curl, poi
# esegue lo script via standard input (come nel bootstrap) per verificare che i
# comandi figli non consumino il resto dello script.
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UPDATE_SCRIPT="$SCRIPT_DIR/update.sh"
BASE="$(mktemp -d)"
trap 'rm -rf "$BASE"' EXIT

fail() {
    echo "TEST FALLITO: $*" >&2
    exit 1
}

mkdir -p "$BASE/bin"
cat > "$BASE/bin/docker" <<'EOF'
#!/usr/bin/env bash
if [ "$1" = "compose" ] && [ "$2" = "build" ]; then
    if [ "${FAIL_TARGET:-0}" = "1" ] && [ "$(cat VERSION)" = "0.6.0" ]; then
        exit 1
    fi
    exit 0
fi
if [ "$1" = "compose" ] && [ "$2" = "up" ]; then
    exit 0
fi
if [ "$1" = "compose" ] && [ "$2" = "exec" ]; then
    for arg in "$@"; do
        if [ "$arg" = "printenv" ]; then
            printf '%s\n' "${SPENDY_VERSION:-}"
            exit 0
        fi
    done
    exit 0
fi
exit 0
EOF
cat > "$BASE/bin/curl" <<'EOF'
#!/usr/bin/env bash
if [ -f maintenance/on ]; then
    printf 503
else
    printf 200
fi
EOF
chmod +x "$BASE/bin/docker" "$BASE/bin/curl"
export PATH="$BASE/bin:$PATH"

git init -q --bare "$BASE/origin.git"
git init -q "$BASE/work"
cd "$BASE/work"
git config user.email test@example.com
git config user.name Test
mkdir -p scripts
cp "$UPDATE_SCRIPT" scripts/update.sh
chmod +x scripts/update.sh
printf '.env\nmaintenance/\n' > .gitignore
printf 'SPENDY_VERSION=0.5.0\n' > .env
printf '0.5.0\n' > VERSION
git add .gitignore VERSION scripts/update.sh
git commit -qm "release 0.5.0"
git tag -a v0.5.0 -m v0.5.0
git remote add origin "$BASE/origin.git"
git push -q origin HEAD:main --tags

echo "Test 1: aggiornamento via stdin ..."
SPENDY_ROOT="$BASE/work" bash -s -- --no-backup v0.5.0 < scripts/update.sh
[ -f maintenance/on ] && fail "manutenzione ancora attiva dopo il successo"
grep -q '^SPENDY_VERSION=0.5.0$' .env || fail ".env non aggiornato"
[ "$(git show HEAD:VERSION)" = "0.5.0" ] || fail "HEAD inatteso"

echo "Test 2: rollback dopo build fallita ..."
printf '0.6.0\n' > VERSION
git add VERSION
git commit -qm "release 0.6.0"
git tag -a v0.6.0 -m v0.6.0
git push -q origin HEAD:main --tags
git checkout -q v0.5.0
set +e
FAIL_TARGET=1 SPENDY_ROOT="$BASE/work" bash -s -- --no-backup v0.6.0 \
    < scripts/update.sh > "$BASE/rollback.log" 2>&1
code=$?
set -e
if [ "$code" -ne 1 ]; then
    cat "$BASE/rollback.log" >&2
    fail "exit code del rollback: $code (atteso 1)"
fi
grep -q "Rollback completato" "$BASE/rollback.log" ||
    fail "messaggio di rollback assente"
[ -f maintenance/on ] && fail "manutenzione ancora attiva dopo il rollback"
grep -q '^SPENDY_VERSION=0.5.0$' .env || fail ".env non ripristinato"
[ "$(git show HEAD:VERSION)" = "0.5.0" ] || fail "HEAD non ripristinato"

echo "Test update.sh: OK"
