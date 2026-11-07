#!/usr/bin/env bash
# Ripristina il database demo locale (solo sviluppo/prove, mai produzione).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE="$ROOT/demo/spendy-demo.sqlite3"
TARGET="$ROOT/apps/backend/db.sqlite3"

if [[ ! -f "$SOURCE" ]]; then
  echo "Snapshot demo non trovato: $SOURCE" >&2
  exit 1
fi

if [[ -f "$TARGET" ]]; then
  BACKUP="$TARGET.bak.$(date +%Y%m%d%H%M%S)"
  cp -f "$TARGET" "$BACKUP"
  echo "Backup del database corrente: $BACKUP"
fi

cp -f "$SOURCE" "$TARGET"
echo "Database demo ripristinato in $TARGET"
echo
echo "Avvia backend e frontend:"
echo "  DJANGO_DEBUG=1 SECURE_COOKIES=0 DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1 \\"
echo "    .venv/bin/python apps/backend/manage.py runserver 127.0.0.1:8000"
echo "  (cd apps/frontend && npm run dev -- --host 127.0.0.1 --port 5173)"
echo
echo "Accesso demo: demo@spendy.test / Demo-Preview-2026"
