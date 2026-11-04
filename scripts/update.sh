#!/usr/bin/env bash
#
# Aggiorna Spendy a una release Git verificata.
# Va eseguito sull'host LXC dalla root del repository, con lo stack attivo.
#
# Uso:
#   ./scripts/update.sh v0.5.0
#   ./scripts/update.sh --latest
#   ./scripts/update.sh --dry-run v0.5.0
#
# La procedura:
#   1. rifiuta un working tree sporco e verifica che il tag esista sul remote;
#   2. controlla che il file VERSION del tag coincida con il nome del tag;
#   3. crea un backup locale del database prima di modificare i container;
#   4. attiva la pagina di manutenzione, applica il tag, ricostruisce e avvia;
#   5. aspetta l'health check e la versione attesa, poi rimuove la manutenzione;
#   6. in caso di errore ripristina il commit precedente e ricostruisce.
#
# Il rollback automatico non ripristina il database: le migrazioni già applicate
# restano. Per un ripristino completo usare deploy/README.md.
#
set -euo pipefail

if [ -n "${SPENDY_ROOT:-}" ]; then
    ROOT_DIR="$(cd "$SPENDY_ROOT" && pwd)"
elif [ -n "${BASH_SOURCE[0]:-}" ]; then
    ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
else
    echo "Errore: eseguire lo script dal repository o impostare SPENDY_ROOT." >&2
    exit 1
fi
cd "$ROOT_DIR"

HEALTH_ATTEMPTS=60
HEALTH_INTERVAL=2
COMPOSE=(docker compose)
TAG=""
USE_LATEST=0
DRY_RUN=0
SKIP_BACKUP=0
ALLOW_DOWNGRADE=0

usage() {
    cat <<'EOF'
Uso: ./scripts/update.sh [opzioni] vX.Y.Z

Opzioni:
  --latest            usa l'ultimo tag vX.Y.Z disponibile in locale
  --dry-run           verifica i prerequisiti senza modificare nulla
  --no-backup         salta il backup locale prima dell'aggiornamento
  --allow-downgrade   consente di applicare un tag più vecchio della versione corrente
  -h, --help          mostra questo messaggio
EOF
}

die() {
    echo "Errore: $*" >&2
    exit 1
}

version_lt() {
    [ "$1" != "$2" ] &&
        [ "$(printf '%s\n%s\n' "$1" "$2" | sort -V | head -n 1)" = "$1" ]
}

while [ $# -gt 0 ]; do
    case "$1" in
        --latest) USE_LATEST=1 ;;
        --dry-run) DRY_RUN=1 ;;
        --no-backup) SKIP_BACKUP=1 ;;
        --allow-downgrade) ALLOW_DOWNGRADE=1 ;;
        -h|--help) usage; exit 0 ;;
        -*) die "opzione sconosciuta: $1" ;;
        *)
            [ -z "$TAG" ] || die "indicare un solo tag"
            TAG="$1"
            ;;
    esac
    shift
done

if [ "$USE_LATEST" -eq 1 ] && [ -n "$TAG" ]; then
    die "--latest e un tag esplicito sono incompatibili"
fi
command -v git >/dev/null || die "git non trovato"
command -v docker >/dev/null || die "docker non trovato"
command -v curl >/dev/null || die "curl non trovato"
git rev-parse --is-inside-work-tree >/dev/null 2>&1 ||
    die "eseguire lo script dalla root del repository Spendy"
[ -f .env ] || die "file .env mancante: create la configurazione prima di aggiornare"

if ! git diff --quiet || ! git diff --cached --quiet; then
    git status --short
    die "il working tree non è pulito: commit o annulla le modifiche prima di aggiornare"
fi
if [ -n "$(git ls-files --others --exclude-standard)" ]; then
    git status --short --untracked-files=all
    die "ci sono file non tracciati non ignorati: spostali o aggiungili a .gitignore"
fi

echo "Recupero i tag dal remote ..."
git fetch --tags --prune origin || die "impossibile recuperare i tag da origin"

if [ "$USE_LATEST" -eq 1 ]; then
    if ! TAG="$(
        git tag --list 'v*' |
            grep -E '^v[0-9]+\.[0-9]+\.[0-9]+$' |
            sort -V |
            tail -n 1
    )"; then
        TAG=""
    fi
    [ -n "$TAG" ] || die "nessun tag vX.Y.Z trovato"
fi

[ -n "$TAG" ] || {
    usage >&2
    die "specificare un tag vX.Y.Z oppure --latest"
}
[[ "$TAG" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]] || die "tag non valido: $TAG (atteso vX.Y.Z)"
VERSION="${TAG#v}"

git rev-parse -q --verify "refs/tags/$TAG" >/dev/null || die "tag $TAG assente in locale"
LOCAL_COMMIT="$(git rev-parse "$TAG^{commit}")"
if ! REMOTE_COMMIT="$(
    git ls-remote --tags origin "refs/tags/$TAG" "refs/tags/$TAG^{}" |
        awk -v annotated="refs/tags/$TAG^{}" \
            '$2 == annotated { print $1; found=1 } END { if (!found) exit 0 }'
)"; then
    die "impossibile interrogare il remote origin"
fi
if [ -z "$REMOTE_COMMIT" ]; then
    if ! REMOTE_COMMIT="$(
        git ls-remote --tags origin "refs/tags/$TAG" |
            awk -v plain="refs/tags/$TAG" '$2 == plain { print $1 }'
    )"; then
        die "impossibile interrogare il remote origin"
    fi
fi
[ -n "$REMOTE_COMMIT" ] || die "tag $TAG non presente sul remote origin"
[ "$LOCAL_COMMIT" = "$REMOTE_COMMIT" ] ||
    die "il tag $TAG locale ($LOCAL_COMMIT) non coincide con il remote ($REMOTE_COMMIT)"

TAG_VERSION="$(git show "$TAG:VERSION" 2>/dev/null | tr -d '[:space:]')" || TAG_VERSION=""
[ -n "$TAG_VERSION" ] || die "il tag $TAG non contiene il file VERSION"
[ "$TAG_VERSION" = "$VERSION" ] ||
    die "VERSION nel tag ($TAG_VERSION) non coincide con il tag ($TAG)"

if [ "$(git cat-file -t "$TAG")" != "tag" ]; then
    echo "Avviso: $TAG è un tag leggero, non annotato."
fi

CURRENT_VERSION="$(tr -d '[:space:]' < VERSION 2>/dev/null || true)"
if [ "$ALLOW_DOWNGRADE" -eq 0 ] && [ -n "$CURRENT_VERSION" ] &&
    version_lt "$VERSION" "$CURRENT_VERSION"; then
    die "il tag $TAG è più vecchio della versione corrente $CURRENT_VERSION (usa --allow-downgrade)"
fi

echo "Aggiornamento a $TAG (versione $VERSION)"
echo "  commit: $LOCAL_COMMIT"
echo "  versione corrente: ${CURRENT_VERSION:-sconosciuta}"

if [ "$DRY_RUN" -eq 1 ]; then
    echo "Dry run: prerequisiti verificati, nessuna modifica applicata."
    exit 0
fi

if [ "$SKIP_BACKUP" -eq 0 ]; then
    echo "Backup locale del database ..."
    ./scripts/backup.sh < /dev/null
fi

PREVIOUS_COMMIT="$(git rev-parse HEAD)"
PREVIOUS_VERSION="$(tr -d '[:space:]' < VERSION 2>/dev/null || true)"
MAINTENANCE_FILE="$ROOT_DIR/maintenance/on"
MAINTENANCE_ARMED=0
mkdir -p "$ROOT_DIR/maintenance"

on_exit() {
    if [ "$MAINTENANCE_ARMED" -eq 1 ]; then
        echo "Attenzione: la modalità manutenzione è ancora attiva." >&2
        echo "Controlla l'errore, poi esegui 'rm maintenance/on' e riprova." >&2
    fi
}
trap on_exit EXIT
trap 'exit 130' INT TERM

touch "$MAINTENANCE_FILE"
MAINTENANCE_ARMED=1
echo "Modalità manutenzione attiva."

rollback() {
    local reason="$1"
    MAINTENANCE_ARMED=0
    echo "ERRORE: $reason" >&2
    echo "Rollback a $PREVIOUS_COMMIT (versione ${PREVIOUS_VERSION:-sconosciuta}) ..." >&2
    touch "$MAINTENANCE_FILE"
    if ! git checkout --detach "$PREVIOUS_COMMIT"; then
        echo "Rollback non riuscito: checkout di $PREVIOUS_COMMIT fallito." >&2
        echo "La modalità manutenzione resta attiva; ripristina manualmente il repository." >&2
        exit 2
    fi
    if [ -n "$PREVIOUS_VERSION" ]; then
        export SPENDY_VERSION="$PREVIOUS_VERSION"
    else
        unset SPENDY_VERSION || true
    fi
    if ! set_env_version "$PREVIOUS_VERSION"; then
        echo "Avviso: impossibile ripristinare SPENDY_VERSION nel .env; il container usa la variabile esportata." >&2
    fi
    if "${COMPOSE[@]}" build < /dev/null &&
        "${COMPOSE[@]}" up -d --remove-orphans < /dev/null; then
        if wait_for_backend && wait_for_version "$PREVIOUS_VERSION"; then
            rm -f "$MAINTENANCE_FILE"
            echo "Rollback completato: Spendy è di nuovo attivo con la versione precedente." >&2
            echo "Il database potrebbe aver ricevuto migrazioni della versione nuova: verifica prima di riprovare." >&2
            exit 1
        fi
    fi
    echo "Rollback non riuscito: la modalità manutenzione resta attiva." >&2
    echo "Controlla 'docker compose logs' e ripristina il backup se necessario." >&2
    exit 2
}

set_env_version() {
    local version="$1"
    if [ -z "$version" ]; then
        return 0
    fi
    if grep -q '^SPENDY_VERSION=' .env; then
        sed -i "s/^SPENDY_VERSION=.*/SPENDY_VERSION=$version/" .env
    else
        printf '\nSPENDY_VERSION=%s\n' "$version" >> .env
    fi
}

wait_for_backend() {
    local attempt
    for ((attempt = 1; attempt <= HEALTH_ATTEMPTS; attempt++)); do
        if "${COMPOSE[@]}" exec -T backend python -c \
            "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health/', timeout=3).read()" \
            >/dev/null 2>&1 < /dev/null; then
            return 0
        fi
        sleep "$HEALTH_INTERVAL"
    done
    return 1
}

wait_for_version() {
    local expected="$1"
    local running
    [ -n "$expected" ] || return 0
    if version_lt "$expected" "0.3.0"; then
        echo "Avviso: $expected non espone SPENDY_VERSION; salto il controllo di versione." >&2
        return 0
    fi
    running="$("${COMPOSE[@]}" exec -T backend printenv SPENDY_VERSION < /dev/null 2>/dev/null | tr -d '[:space:]' || true)"
    [ "$running" = "$expected" ]
}

frontend_status() {
    local status
    status="$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 http://127.0.0.1:8080/ 2>/dev/null || true)"
    printf '%s' "${status:-000}"
}

wait_for_frontend_up() {
    local attempt status
    for ((attempt = 1; attempt <= HEALTH_ATTEMPTS; attempt++)); do
        status="$(frontend_status)"
        case "$status" in
            200 | 503) return 0 ;;
        esac
        sleep "$HEALTH_INTERVAL"
    done
    return 1
}

wait_for_frontend_ok() {
    local attempt
    for ((attempt = 1; attempt <= HEALTH_ATTEMPTS; attempt++)); do
        [ "$(frontend_status)" = "200" ] && return 0
        sleep "$HEALTH_INTERVAL"
    done
    return 1
}

git checkout --detach "$TAG" || rollback "checkout di $TAG fallito"
set_env_version "$VERSION" || rollback "scrittura di SPENDY_VERSION nel .env fallita"
export SPENDY_VERSION="$VERSION"

echo "Ricostruzione delle immagini ..."
"${COMPOSE[@]}" build < /dev/null || rollback "build delle immagini fallita"

echo "Avvio dello stack ..."
"${COMPOSE[@]}" up -d --remove-orphans < /dev/null || rollback "avvio dello stack fallito"

echo "Attendo l'health check del backend ..."
wait_for_backend || rollback "il backend non risponde all'health check"
wait_for_version "$VERSION" || rollback "la versione attiva non è $VERSION"

echo "Verifico il frontend ..."
wait_for_frontend_up || rollback "il frontend non risponde dopo l'aggiornamento"
rm -f "$MAINTENANCE_FILE"
MAINTENANCE_ARMED=0
if ! wait_for_frontend_ok; then
    touch "$MAINTENANCE_FILE"
    MAINTENANCE_ARMED=1
    rollback "il frontend non risponde con 200 dopo la rimozione della manutenzione"
fi
echo "Aggiornamento completato: Spendy $VERSION è attivo."
