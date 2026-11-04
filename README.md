# Spendy

**Gestione delle finanze personali, self-hosted.**

Spendy è un'app web per tenere sotto controllo conti, movimenti e salvadanai.
Nasce per essere ospitata sul proprio server, senza servizi finanziari esterni e
senza integrazioni bancarie.

[![CI](https://github.com/Loreexe/Spendy/actions/workflows/ci.yml/badge.svg)](https://github.com/Loreexe/Spendy/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/Loreexe/Spendy?label=release)](https://github.com/Loreexe/Spendy/releases)
[![License: GPL-3.0](https://img.shields.io/badge/license-GPL--3.0-blue.svg)](LICENSE)

> **Stato:** release **`v0.5.1`**, che include le automazioni per salvadanai e
> spese ricorrenti. Il progetto è in sviluppo attivo: gruppi, investimenti, MCP
> e notifiche push/email non sono ancora implementati.

## Funzionalità

- **Dashboard** con saldo totale, patrimonio, saldo del periodo, entrate e uscite.
- **Conti personali** con nome, tipo, saldo iniziale e archiviazione.
- **Movimenti**: entrate, spese, trasferimenti tra conti e modifica/annullamento.
- **Salvadanai** con conto di appoggio, versamenti e prelievi.
- **Pagamento di spese dal salvadanaio**, con movimenti tecnici e copertura
  parziale dal conto di appoggio.
- **Eliminazione dei salvadanai** con trasferimento del saldo residuo.
- **Automazioni periodiche**: trasferimenti ricorrenti verso i salvadanai e
  spese ricorrenti come abbonamenti, affitto o palestra, con recupero delle
  occorrenze perse, gestione dei fallimenti, storico delle esecuzioni e
  notifiche in-app.
- **Importazione dei movimenti da CSV**, con modello scaricabile, anteprima
  correggibile, controllo dei duplicati e riepilogo prima della conferma.
- **Backup personale del profilo**: archivio ZIP con conti, salvadanai,
  movimenti e righe contabili in CSV, manifesto con checksum e ripristino
  guidato su un profilo vuoto. Distinto dal backup globale del database.
- **Saldi mai negativi**: ogni operazione che porterebbe un conto sotto zero
  viene rifiutata con il saldo disponibile.
- **Isolamento tra profili**: ogni account normale ha il proprio spazio
  finanziario; l'admin globale non ha un profilo finanziario.
- **Autenticazione** email/password, registrazione con approvazione e setup
  iniziale protetto.
- **Sistema (admin)**: controllo manuale delle release GitHub, versione
  backend/frontend, stato del database e stato del backup globale, in sola
  lettura.
- **Backup globale automatico**: dump PostgreSQL ogni 15 minuti, configurazione
  cifrata con age, copia su Backblaze B2 tramite rclone e test di ripristino
  mensile. La procedura è in [deploy/README.md](deploy/README.md).

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
scripts/         backup globale e test di ripristino
deploy/          unità systemd, backup e configurazione NPM
compose.yaml     PostgreSQL, backend, worker delle automazioni e frontend
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

Il primo setup è consentito solo da **localhost o Tailscale**.

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
export DJANGO_DEBUG=1
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
cd apps/backend && DJANGO_DEBUG=1 ../../.venv/bin/python manage.py test
cd apps/frontend && npm run lint && npm run build
docker compose config
```

Stato verificato: **166 test backend**, **8 test** del controllo versioni,
**5 test** dello script di backup, lint e build frontend, configurazione Compose
valida, configurazione Nginx e pagina di manutenzione verificate, procedura di
aggiornamento provata in dry-run e con Docker simulato (successo e rollback).
La release `v0.5.1` include le automazioni per salvadanai e spese ricorrenti,
verificate anche con PostgreSQL e con il worker Compose; la sezione Sistema, il
backup globale e l'hardening pre-esposizione restano inclusi dalle release
precedenti. Backup reale su Backblaze B2, test di ripristino automatico e
ripristino completo su host pulito eseguiti con successo.

## Automazioni periodiche

Dalla pagina **Automazioni** puoi creare due tipi di regola:

- un **versamento periodico** da un conto a un salvadanaio;
- una **spesa ricorrente** da un conto, ad esempio Netflix, l'affitto o la
  palestra.

L'importo è fisso e la periodicità può essere giornaliera, settimanale, mensile
o annuale. Il servizio `automation-worker` in `compose.yaml` controlla le
scadenze ogni minuto; puoi anche forzare il controllo dalla pagina o con:

```bash
docker compose exec backend python manage.py run_automations
```

Comportamento:

- ogni occorrenza ha una chiave univoca (regola + data prevista), quindi un
  riavvio o un doppio controllo non crea movimenti duplicati;
- una sola occorrenza persa viene recuperata automaticamente con la **data
  originale**; con due o più occorrenze perse l'app chiede quali recuperare e
  salta le altre;
- saldo insufficiente o dati mancanti: l'occorrenza viene saltata con una
  notifica e la regola resta attiva;
- errore tecnico: fino a 3 tentativi con attese crescenti (60, 300 e 900
  secondi, configurabili con `SPENDY_AUTOMATION_MAX_ATTEMPTS` e
  `SPENDY_AUTOMATION_RETRY_DELAYS`); esauriti i tentativi la regola viene
  sospesa e l'utente avvisato;
- modificare o annullare un movimento generato aggiorna lo stato
  dell'occorrenza e non la riesegue;
- eliminare un salvadanaio rimuove i versamenti collegati ma non le spese
  ricorrenti; in entrambi i casi lo storico delle esecuzioni resta disponibile;
- una spesa ricorrente genera un normale movimento di spesa, quindi entra nella
  dashboard, nel registro e nelle esportazioni.

Le notifiche sono per ora **in-app**, nella pagina Automazioni. Canale e
preferenze delle notifiche, parametri definitivi del retry e sorte dello storico
alla cancellazione della regola restano da confermare.

## Importazione dei movimenti

Dalla pagina **Account → Import / Export** puoi scaricare un modello CSV e
caricare il tuo registro storico. Il file viene analizzato **prima** di scrivere
qualsiasi dato: le righe con errori si possono correggere o scartare, e solo dopo
la conferma l'importazione avviene in modo atomico.

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
  duplicati (stesso segno: un'uscita e un'entrata dello stesso importo non lo
  sono); puoi scartarle oppure confermare singolarmente che non lo sono.

### Esportazione

Dal registro movimenti, **Esporta CSV** scarica i movimenti filtrati con le
stesse colonne e la stessa convenzione di segno dell'importazione, così il file
può essere aperto in un foglio di calcolo o reimportato. La colonna `categoria`
contiene il tipo del movimento (Apertura, Entrata, Spesa, Trasferimento). I
trasferimenti diventano una riga per conto; dei salvadanai viene esportata solo
la parte che passa dal conto.

### Backup personale del profilo

Da **Account → Import / Export** puoi scaricare un archivio ZIP con tutti i dati
del profilo:

- `conti.csv`, `salvadanai.csv`, `movimenti.csv`, `righe.csv`;
- `manifest.json` con data, versione, conteggi e checksum SHA-256.

L'archivio conserva anche le due parti dei trasferimenti, le righe tecniche dei
salvadanai e le coperture parziali. Può essere ricaricato con **Ripristina un
archivio** su un profilo vuoto: Spendy valida il contenuto, mostra un'anteprima e
scrive in modo atomico. Le regole di automazione e il loro storico non sono
ancora incluse in questo archivio CSV: sono protette dal backup globale del
database PostgreSQL. Il ripristino è pensato per il passaggio a un altro server;
non sostituisce il backup globale.

## Configurazione di produzione

- Servire l'app tramite **HTTPS** con Nginx Proxy Manager: procedura e header
  in [deploy/npm/README.md](deploy/npm/README.md).
- Impostare `SECURE_COOKIES=1` quando HTTPS è attivo.
- Impostare `SECURE_SSL_REDIRECT=1` se NPM non forza già HTTPS.
- Impostare `DJANGO_SECRET_KEY` con un valore casuale lungo: senza questa
  variabile il backend non parte quando `DJANGO_DEBUG=0`.
- Impostare `DJANGO_ALLOWED_HOSTS` e `CSRF_TRUSTED_ORIGINS` con il dominio reale.
- Non esporre PostgreSQL.
- Conservare il volume PostgreSQL e includerlo nel backup.
- Non mantenere `SETUP_ALLOWED_CIDRS` aperto alla LAN dopo il primo setup.

Il frontend Nginx invia già `Content-Security-Policy`, `X-Content-Type-Options`,
`X-Frame-Options`, `Referrer-Policy` e `Permissions-Policy`. HSTS va gestito da
NPM per evitare header duplicati.

### Aggiornamento e backup

L'aggiornamento a una release si esegue sull'host con lo script dedicato, che
verifica il tag, crea un backup locale, attiva la pagina di manutenzione,
ricostruisce lo stack e fa rollback in caso di errore:

```bash
./scripts/update.sh --dry-run v0.5.1
./scripts/update.sh v0.5.1
```

Dettagli e limiti in [deploy/README.md](deploy/README.md#aggiornamento-a-una-release).

Per un backup manuale del database, lo script incluso scrive in `backups/`
(escluso da Git), imposta i permessi a `600` e genera un checksum SHA-256:

```bash
./scripts/backup.sh
```

Non lanciare `git add .` con dump o backup presenti nella directory del
progetto: `*.sql`, `*.dump` e `backups/` sono esclusi, ma i file già tracciati
restano nella storia del repository.

### Backup globale automatico

Il backup globale del database e della configurazione, cifrato con age e
caricato su Backblaze B2 tramite rclone, è descritto in
[deploy/README.md](deploy/README.md). Include dump PostgreSQL, `.env`,
`compose.yaml`, manifesto con checksum e un test di ripristino mensile.
Lo stato è visibile nella sezione **Sistema** del pannello admin.

Per l'accesso iniziale è consigliato **Tailscale**; l'esposizione pubblica
richiede ancora hardening, rate limiting, verifica email, 2FA e monitoraggio.

## Sicurezza e privacy

- Non inserire mai `.env`, dump del database, backup o dati finanziari reali nel
  repository.
- I segreti vanno conservati fuori dal repository e ruotati se esposti.
- Login e registrazione hanno rate limiting; dopo 5 tentativi falliti per lo
  stesso IP e identificativo, l'accesso resta bloccato per 15 minuti.
- Il database è la fonte di verità: nessun saldo viene mantenuto solo in memoria.

## Limiti attuali

- Gruppi, investimenti, MCP e notifiche push/email non sono inclusi.
- Le spese ricorrenti usano solo un conto, non un salvadanaio come metodo di
  pagamento; gli importi variabili e le categorie automatiche non sono ancora
  disponibili.
- Il cambio del conto di appoggio di un salvadanaio non è ancora disponibile.
- L'LXC su Proxmox è già stato creato e ospita l'app; configurazione NPM, verifica email, SSO e 2FA non sono completati.

## Licenza

Spendy è distribuito sotto **GNU General Public License v3.0** (SPDX:
`GPL-3.0-only`). Vedi il file [LICENSE](LICENSE).

Copyright (C) 2026 Loreexe.
