# Spendy

Fondamenta tecniche di Spendy: monorepo con backend Django/DRF, frontend
React/TypeScript, PostgreSQL e Docker Compose. In questa fase **non** sono
presenti funzionalità finanziarie.

## Struttura

- `apps/backend/` — Django 6 + DRF, autenticazione a sessione, account e admin.
- `apps/frontend/` — React 19 + TypeScript + Vite, servito da Nginx.
- `packages/` — spazio per contratti e codice condiviso (vuoto per ora).
- `compose.yaml` — PostgreSQL, backend e frontend.
- `.github/workflows/ci.yml` — controlli backend, frontend e Compose.

## Avvio con Docker Compose

```bash
cp .env.example .env
# Cambiare DJANGO_SECRET_KEY, POSTGRES_PASSWORD e gli host prima dell'uso.
docker compose up --build
```

Il frontend risponde su `http://localhost:8080` e inoltra `/api` al backend.
PostgreSQL non è pubblicato all'esterno. Il primo setup dell'admin `admin` è
consentito **solo da localhost o Tailscale** (DC-052): in produzione accedere
all'app tramite Tailscale e completare il setup prima di esporla con NPM.

> Nota per il solo sviluppo locale con Docker: la richiesta dal browser arriva
> al backend tramite il gateway Docker, che non è considerato localhost. Per
> provare il setup in locale usare il backend e il frontend in modalità
> sviluppo (sotto), oppure aggiungere temporaneamente la rete bridge Docker a
> `SETUP_ALLOWED_CIDRS` nel proprio `.env`.

### Variabili da impostare in produzione

- `DJANGO_SECRET_KEY`: valore casuale lungo e diverso da quello di esempio.
- `POSTGRES_PASSWORD`: password robusta.
- `DJANGO_ALLOWED_HOSTS`: hostname/IP Tailscale e dominio pubblico usati per
  raggiungere l'app (separati da virgola).
- `CSRF_TRUSTED_ORIGINS`: origini complete, ad esempio
  `https://spendy.example.com`.
- `SECURE_COOKIES=1` quando l'app è servita in HTTPS tramite NPM.
- `SETUP_ALLOWED_CIDRS`: lasciare i valori predefiniti (localhost/Tailscale).

NPM deve inoltrare `X-Forwarded-Proto: https`; il frontend Nginx lo propaga al
backend.

## Sviluppo

Backend:

```bash
python3 -m venv .venv
.venv/bin/pip install -r apps/backend/requirements.txt
cd apps/backend
../../.venv/bin/python manage.py migrate
../../.venv/bin/python manage.py runserver
```

Senza `POSTGRES_HOST` il backend usa SQLite solo come comodità locale; Docker e
CI usano PostgreSQL.

Frontend (in un altro terminale):

```bash
cd apps/frontend
npm install
npm run dev
```

Vite serve `http://localhost:5173` e proxya `/api` su `http://localhost:8000`.

## Verifiche

```bash
cd apps/backend && ../../.venv/bin/python manage.py test
cd apps/frontend && npm run lint && npm run build
docker compose config
```

## Sicurezza

- `.env` non è versionato; i segnaposto in `.env.example` vanno sostituiti.
- Nessun segreto o dato finanziario reale deve essere inserito nel repository.
- La prima password dell'admin si imposta una sola volta e il setup viene
  disabilitato in modo permanente.
- La registrazione richiede l'approvazione dell'admin, salvo impostazione
  esplicita di registrazione aperta.
