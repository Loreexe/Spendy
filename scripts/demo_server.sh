#!/usr/bin/env bash
# Spendy — avvio rapido del server demo (backend Django + frontend Vite).
#
# Uso:
#   ./scripts/demo_server.sh up        avvia i server e termina (terminale normale)
#   ./scripts/demo_server.sh run       avvia e resta in attesa (per l'agente in sandbox,
#                                      da lanciare come background job persistente)
#   ./scripts/demo_server.sh down      ferma i server avviati dallo script
#   ./scripts/demo_server.sh status    mostra stato e URL
#
# Opzioni:
#   --no-restore        non ricopia lo snapshot demo (usa il db corrente)
#   --api-port N        porta backend (default 8000)
#   --web-port N        porta frontend (default 5173)
#
# Comportamento: ripristina demo/spendy-demo.sqlite3 (con backup del db corrente),
# applica le migrazioni Django e avvia i due server su 0.0.0.0, attendendo che
# rispondano prima di stampare gli URL.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="$ROOT/demo/run"
PYTHON="$ROOT/.venv/bin/python"
API_PORT="${API_PORT:-8000}"
WEB_PORT="${WEB_PORT:-5173}"
RESTORE=1
MODE="${1:-up}"

shift || true
while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-restore) RESTORE=0 ;;
    --api-port) API_PORT="$2"; shift ;;
    --web-port) WEB_PORT="$2"; shift ;;
    -h|--help)
      sed -n '2,20p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
      exit 0 ;;
    *) echo "Opzione sconosciuta: $1" >&2; exit 2 ;;
  esac
  shift
done

API_PID_FILE="$RUN_DIR/api.pid"
WEB_PID_FILE="$RUN_DIR/web.pid"
API_LOG="$RUN_DIR/api.log"
WEB_LOG="$RUN_DIR/web.log"

mkdir -p "$RUN_DIR"

# `hostname -I` non c'è ovunque: fallback su `ip`.
all_ips() {
  hostname -I 2>/dev/null | tr ' ' '\n' || ip -4 -o addr show scope global 2>/dev/null | awk '{print $4}' | cut -d/ -f1
}

lan_ips() {
  all_ips | grep -E '^(10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[01])\.)'
}

tailscale_ip() {
  all_ips | grep -E '^100\.' | head -1
}

api_ok() { curl -fsS -m 2 "http://127.0.0.1:$API_PORT/api/v1/health/" >/dev/null 2>&1; }
web_ok() { curl -fsS -m 2 "http://127.0.0.1:$WEB_PORT/" >/dev/null 2>&1; }

pid_alive() { [[ -f "$1" ]] && kill -0 "$(cat "$1")" 2>/dev/null; }

print_info() {
  local tail
  tail="$(tailscale_ip || true)"
  echo
  echo "Server demo Spendy attivo"
  echo "  Web:              http://127.0.0.1:$WEB_PORT"
  for ip in $(lan_ips); do echo "  Web (rete locale): http://$ip:$WEB_PORT"; done
  echo "  API (app Android): http://127.0.0.1:$API_PORT/api/v1/  (health: /api/v1/health/)"
  for ip in $(lan_ips); do echo "  API (rete locale): http://$ip:$API_PORT"; done
  [[ -n "$tail" ]] && echo "  API (Tailscale):   http://$tail:$API_PORT"
  echo
  echo "  Utente demo:  demo@spendy.test / Demo-Preview-2026"
  echo "  Secondo account (test cambio utente): demo2@spendy.test / Demo-Preview-2026"
  echo "  Admin web:    admin / Admin-Preview-2026"
  echo
  echo "  Log:  $API_LOG  ·  $WEB_LOG"
  echo "  Stop: $ROOT/scripts/demo_server.sh down"
  echo
}

start_api() {
  if api_ok; then
    echo "Backend già attivo su :$API_PORT"
    return 0
  fi
  ( cd "$ROOT" && exec env DJANGO_DEBUG=1 SECURE_COOKIES=0 \
      DJANGO_ALLOWED_HOSTS="$ALLOWED_HOSTS" \
      "$PYTHON" apps/backend/manage.py runserver "0.0.0.0:$API_PORT" --noreload ) \
      >"$API_LOG" 2>&1 &
  echo $! > "$API_PID_FILE"
}

start_web() {
  if web_ok; then
    echo "Frontend già attivo su :$WEB_PORT"
    return 0
  fi
  ( cd "$ROOT/apps/frontend" && exec ./node_modules/.bin/vite --host 0.0.0.0 --port "$WEB_PORT" ) \
    >"$WEB_LOG" 2>&1 &
  echo $! > "$WEB_PID_FILE"
}

wait_ready() {
  local i
  for i in $(seq 1 40); do
    api_ok && web_ok && return 0
    sleep 1
  done
  echo "I server non hanno risposto in tempo. Controlla i log:" >&2
  tail -n 20 "$API_LOG" 2>/dev/null >&2 || true
  tail -n 20 "$WEB_LOG" 2>/dev/null >&2 || true
  return 1
}

stop_all() {
  local pid
  for f in "$API_PID_FILE" "$WEB_PID_FILE"; do
    if pid_alive "$f"; then
      pid="$(cat "$f")"
      kill "$pid" 2>/dev/null || true
      sleep 0.5
      kill -9 "$pid" 2>/dev/null || true
      echo "Fermato pid $pid ($(basename "$f" .pid))"
    fi
    rm -f "$f"
  done
}

# Secondo account demo, utile per provare il cambio utente nell'app Android.
ensure_demo2() {
  ( cd "$ROOT" && env DJANGO_DEBUG=1 SECURE_COOKIES=0 \
      "$PYTHON" apps/backend/manage.py shell -c "
from accounts.models import User
u, _ = User.objects.get_or_create(username='demo2', defaults={'email': 'demo2@spendy.test', 'first_name': 'Demo', 'last_name': 'Due'})
u.set_password('Demo-Preview-2026')
u.status = 'active'
u.save()
" ) >/dev/null 2>&1 || echo "Avviso: impossibile garantire l'account demo2." >&2
}

start_all() {
  [[ -x "$PYTHON" ]] || { echo "Manca .venv/bin/python: crea prima l'ambiente Python." >&2; exit 1; }
  [[ -x "$ROOT/apps/frontend/node_modules/.bin/vite" ]] || {
    echo "Mancano le dipendenze frontend: esegui 'npm install' in apps/frontend." >&2
    exit 1
  }

  if api_ok && web_ok; then
    echo "Server demo già in esecuzione."
    return 0
  fi

  if [[ "$RESTORE" == "1" ]]; then
    "$ROOT/scripts/load_demo.sh"
  else
    echo "Ripristino snapshot demo saltato (--no-restore)."
  fi

  ALLOWED_HOSTS="localhost,127.0.0.1"
  for ip in $(all_ips || true); do
    [[ "$ip" == 127.* ]] && continue
    ALLOWED_HOSTS="$ALLOWED_HOSTS,$ip"
  done
  export ALLOWED_HOSTS

  echo "Applico le migrazioni Django…"
  ( cd "$ROOT" && env DJANGO_DEBUG=1 SECURE_COOKIES=0 \
      DJANGO_ALLOWED_HOSTS="$ALLOWED_HOSTS" \
      "$PYTHON" apps/backend/manage.py migrate --noinput ) >/dev/null 2>&1 \
    || { echo "Migrazioni fallite, vedi $API_LOG" >&2; exit 1; }

  ensure_demo2

  echo "Avvio backend su :$API_PORT e frontend su :$WEB_PORT…"
  start_api
  start_web
  wait_ready
}

case "$MODE" in
  up)
    start_all
    print_info
    ;;
  run)
    start_all
    print_info
    trap 'echo; echo "Arresto server demo…"; stop_all; exit 0' INT TERM
    echo "In esecuzione (run). Premi Ctrl-C o usa 'down' da un altro terminale."
    while :; do sleep 30; done
    ;;
  down)
    stop_all
    ;;
  status)
    if api_ok; then echo "Backend: OK su :$API_PORT"; else echo "Backend: non attivo su :$API_PORT"; fi
    if web_ok; then echo "Frontend: OK su :$WEB_PORT"; else echo "Frontend: non attivo su :$WEB_PORT"; fi
    if api_ok && web_ok; then print_info; fi
    ;;
  *)
    echo "Uso: $0 {up|run|down|status} [--no-restore] [--api-port N] [--web-port N]" >&2
    exit 2
    ;;
esac
