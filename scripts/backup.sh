#!/usr/bin/env bash
#
# Crea un dump PostgreSQL di Spendy in una directory esclusa da Git.
# Va eseguito dalla root del repository, con lo stack Docker Compose attivo.
#
# Uso:
#   ./scripts/backup.sh
#   BACKUP_DIR=/percorso/sicuro ./scripts/backup.sh
#
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

BACKUP_DIR="${BACKUP_DIR:-$ROOT_DIR/backups}"
umask 077
mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR" 2>/dev/null || true

timestamp="$(date +%Y-%m-%d_%H%M%S)"
target="$BACKUP_DIR/spendy-$timestamp.sql"
if [ -e "$target" ]; then
    echo "Errore: esiste già $target; attendi un secondo e riprova." >&2
    exit 1
fi
tmp="$(mktemp "$BACKUP_DIR/.spendy-$timestamp.XXXXXX")"
trap 'rm -f "$tmp"' EXIT

if [ -z "$(docker compose ps -q db 2>/dev/null)" ]; then
    echo "Errore: il servizio db non risulta attivo. Avvia lo stack con 'docker compose up -d'." >&2
    exit 1
fi

echo "Creazione backup in $target ..."
docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' >"$tmp"

if [ ! -s "$tmp" ]; then
    echo "Errore: il dump è vuoto; backup non creato." >&2
    exit 1
fi

mv "$tmp" "$target"
trap - EXIT
chmod 600 "$target"
sha256sum "$target" >"$target.sha256"
chmod 600 "$target.sha256"

echo "Backup completato: $target"
echo "Checksum:          $target.sha256"
