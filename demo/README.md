# Spendy — ambiente demo

Questa cartella conserva il database SQLite usato per le prove e per le
dimostrazioni locali. **Non è un backup reale e non contiene dati veri.**

## Contenuto

- `spendy-demo.sqlite3` — snapshot del database demo (profilo
  `demo@spendy.test`, password `Demo-Preview-2026`).
- `README.md` — questo file.

Il database è escluso da Git (`.gitignore`) e viaggia con la cartella del
progetto tramite Nextcloud.

> **Nota (2026-11-09):** lo snapshot è stato riallineato alle migrazioni del
> backend `0.8.1` (`accounts.0004_devicetoken_devicepairing`,
> `finance.0012`, `finance.0013`), che mancavano e facevano fallire il login.
> Se il backend introduce nuove migrazioni, dopo `load_demo.sh` eseguire
> `DJANGO_DEBUG=1 .venv/bin/python apps/backend/manage.py migrate`.

## Dati presenti

- 3 conti, 2 salvadanai con versamenti;
- 4 mesi di movimenti demo (32 al mese) con categorie e tag;
- automazioni attive e voci nel cestino;
- 6 posizioni di investimento con aperture, acquisti, vendite e dividendi;
- nome, foto profilo e impostazioni del profilo demo.

## Avvio rapido con lo script

```bash
./scripts/demo_server.sh up      # ripristina il demo e avvia backend + frontend
./scripts/demo_server.sh status  # stato e URL
./scripts/demo_server.sh down    # ferma i server
```

Lo script ripristina lo snapshot (con backup del database corrente), applica le
migrazioni e crea/aggiorna il secondo account demo `demo2@spendy.test` (utile per
provare il cambio utente nell'app Android). Da un agente in sandbox, avviare
`./scripts/demo_server.sh run` come background job persistente: vedi
[RULES.md](../.spendy-wiki/RULES.md) § «Procedure rapide: server demo e app Android».

## Ripristinare il demo

Dalla radice del progetto:

```bash
./scripts/load_demo.sh
```

Lo script salva un backup del database corrente (`*.bak.<timestamp>`), copia lo
snapshot demo in `apps/backend/db.sqlite3` e stampa le istruzioni per avviare
backend e frontend.

## Avvio rapido

```bash
# backend
DJANGO_DEBUG=1 SECURE_COOKIES=0 \
  DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1 \
  .venv/bin/python apps/backend/manage.py runserver 127.0.0.1:8000

# frontend (altro terminale)
cd apps/frontend && npm run dev -- --host 127.0.0.1 --port 5173
```

Accesso: `demo@spendy.test` / `Demo-Preview-2026`.
Admin globale: `admin` / `Admin-Preview-2026`.
