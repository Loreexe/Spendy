# Spendy

**Gestione delle finanze personali, self-hosted.**

Spendy è un'app web per tenere sotto controllo conti, movimenti e salvadanai.
Nasce per essere ospitata sul proprio server, senza servizi finanziari esterni e
senza integrazioni bancarie.

[![CI](https://github.com/Loreexe/Spendy/actions/workflows/ci.yml/badge.svg)](https://github.com/Loreexe/Spendy/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/Loreexe/Spendy?label=release)](https://github.com/Loreexe/Spendy/releases)
[![License: GPL-3.0](https://img.shields.io/badge/license-GPL--3.0-blue.svg)](LICENSE)

> **Stato:** release **`v0.2.0`**. Il progetto è in sviluppo attivo:
> le funzionalità di base sono utilizzabili, ma gruppi, investimenti, automazioni,
> MCP e notifiche non sono ancora implementati.

## Funzionalità

- **Dashboard** con saldo totale, patrimonio, saldo del periodo, entrate e uscite.
- **Conti personali** con nome, tipo, saldo iniziale e archiviazione.
- **Movimenti**: entrate, spese, trasferimenti tra conti e modifica/annullamento.
- **Salvadanai** con conto di appoggio, versamenti e prelievi.
- **Pagamento di spese dal salvadanaio**, con movimenti tecnici e copertura
  parziale dal conto di appoggio.
- **Eliminazione dei salvadanai** con trasferimento del saldo residuo.
- **Importazione dei movimenti da CSV**, con modello scaricabile, anteprima
  correggibile, controllo dei duplicati e riepilogo prima della conferma.
- **Saldi mai negativi**: ogni operazione che porterebbe un conto sotto zero
  viene rifiutata con il saldo disponibile.
- **Isolamento tra profili**: ogni account normale ha il proprio spazio
  finanziario; l'admin globale non ha un profilo finanziario.
- **Autenticazione** email/password, registrazione con approvazione e setup
  iniziale protetto.

## Stack

| Componente | Tecnologia |
| --- | --- |
| Backend | Python, Django 6, Django REST Framework |
| Database | PostgreSQL 16 |
| Frontend | React 19, TypeScript, Vite |
| Serving | Nginx |
| Deployment | Docker Compose |
| CI | GitHub Actions |

I dati finanziari restano nel database PostgreSQL. Il repository contiene solo
codice e configurazione, mai dati reali.

## Struttura

```text
apps/
  backend/       Django + DRF, autenticazione e API finance
  frontend/      React + TypeScript, build servita da Nginx
packages/        spazio per contratti e codice condiviso
compose.yaml     PostgreSQL, backend e frontend
.env.example     variabili di ambiente di esempio
VERSION          versione corrente
```

## Avvio rapido con Docker

Requisiti: Docker Engine e Docker Compose plugin.

```bash
git clone https://github.com/Loreexe/Spendy.git
cd Spendy
cp .env.example .env
```

Modifica `.env` prima dell'avvio:

- `DJANGO_SECRET_KEY`: valore casuale lungo;
- `POSTGRES_PASSWORD`: password robusta;
- `DJANGO_ALLOWED_HOSTS`: host/IP usati per raggiungere l'app;
- `CSRF_TRUSTED_ORIGINS`: origini complete, ad esempio `https://spendy.example.com`.

Poi:

```bash
docker compose up -d --build
docker compose ps
curl http://localhost:8080/api/health/
```

Il frontend risponde su `http://localhost:8080` e inoltra `/api` al backend.
PostgreSQL non è pubblicato all'esterno.

### Primo setup dell'admin

Il primo setup è consentito solo da **localhost o Tailscale** (DC-052).

1. Accedi a `http://<host>:8080`.
2. Imposta la password dell'utente `admin`.
3. Il setup si disabilita in modo permanente.

> In sviluppo locale con Docker il browser arriva al backend tramite il gateway
> Docker, che non è considerato localhost. Usa il backend e il frontend in
> modalità sviluppo, oppure aggiungi temporaneamente la rete bridge Docker a
> `SETUP_ALLOWED_CIDRS` nel `.env`.

## Sviluppo locale

### Backend

```bash
python3 -m venv .venv
.venv/bin/pip install -r apps/backend/requirements.txt
cd apps/backend
../../.venv/bin/python manage.py migrate
../../.venv/bin/python manage.py runserver
```

Senza `POSTGRES_HOST` il backend usa SQLite solo come comodità locale; Docker e
CI usano PostgreSQL.

### Frontend

In un altro terminale:

```bash
cd apps/frontend
npm install
npm run dev
```

Vite serve `http://localhost:5173` e proxya `/api` su `http://localhost:8000`.

## Test e controlli

```bash
cd apps/backend && ../../.venv/bin/python manage.py test
cd apps/frontend && npm run lint && npm run build
docker compose config
```

Stato verificato per `v0.2.3`: **93 test backend**, lint e build frontend,
configurazione Compose valida e flusso UI completo.

## Importazione dei movimenti

Dal menu **Importa** puoi scaricare un modello CSV e caricare il tuo registro
storico. Il file viene analizzato **prima** di scrivere qualsiasi dato: le righe
con errori si possono correggere o scartare, e solo dopo la conferma
l'importazione avviene in modo atomico.

Il file deve essere un CSV UTF-8 con queste colonne:

```csv
data;descrizione;categoria;conto;importo
25-11-2026;Spesa di prova;esempio;Contanti;12,50
25-11-2026;Entrata di prova;esempio;Contanti;-100,00
```

- il formato della data, il separatore di colonna e il separatore decimale
  vengono **rilevati automaticamente** e si possono correggere dall'anteprima
  (es. `GG-MM-AAAA`, `AAAA-MM-GG`, `;` o `,`, virgola o punto decimale);
- importi senza `€` e senza migliaia; gli interi sono accettati
  (`150` equivale a `150,00`);
- importo positivo = uscita, negativo = entrata;
- la prima riga per data di un **nuovo conto** è la sua apertura e deve essere
  negativa; i conti esistenti ricevono solo movimenti;
- se importi in un conto già esistente, il suo saldo iniziale resta quello già
  registrato: righe più vecchie dell'apertura possono risultare in un saldo
  insufficiente nel passato. Per uno storico completo usa un conto nuovo, che
  l'importazione crea con l'apertura presa dal file;
- ogni riga è indipendente: trasferimenti e salvadanai non sono importabili;
- la colonna `categoria` è accettata ma ignorata, in attesa della funzionalità;
- righe identiche nel file o già presenti nell'app sono segnalate come
  duplicati; puoi scartarle oppure confermare singolarmente che non lo sono.

## Configurazione di produzione

- Servire l'app tramite **HTTPS** con Nginx Proxy Manager.
- Impostare `SECURE_COOKIES=1` quando HTTPS è attivo.
- Impostare `DJANGO_ALLOWED_HOSTS` e `CSRF_TRUSTED_ORIGINS` con il dominio reale.
- Non esporre PostgreSQL.
- Conservare il volume PostgreSQL e includerlo nel backup.
- Non mantenere `SETUP_ALLOWED_CIDRS` aperto alla LAN dopo il primo setup.

Per l'accesso iniziale è consigliato **Tailscale**; l'esposizione pubblica
richiede ancora hardening, rate limiting, verifica email, 2FA e monitoraggio.

## Sicurezza e privacy

- Non inserire mai `.env`, dump del database, backup o dati finanziari reali nel
  repository.
- I segreti vanno conservati fuori dal repository e ruotati se esposti.
- Il database è la fonte di verità: nessun saldo viene mantenuto solo in memoria.
- La documentazione interna del progetto non è inclusa nel repository pubblico.

## Limiti attuali

- Gruppi, investimenti, automazioni periodiche, MCP e notifiche non sono inclusi.
- Il cambio del conto di appoggio di un salvadanaio non è ancora disponibile.
- Deploy su Proxmox/NPM, verifica email, SSO e 2FA non sono completati.

## Licenza

Spendy è distribuito sotto **GNU General Public License v3.0** (SPDX:
`GPL-3.0-only`). Vedi il file [LICENSE](LICENSE).

Copyright (C) 2026 Loreexe.
