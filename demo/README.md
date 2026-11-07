# Spendy — ambiente demo

Questa cartella conserva il database SQLite usato per le prove e per le
dimostrazioni locali. **Non è un backup reale e non contiene dati veri.**

## Contenuto

- `spendy-demo.sqlite3` — snapshot del database demo (profilo
  `demo@spendy.test`, password `Demo-Preview-2026`).
- `README.md` — questo file.

Il database è escluso da Git (`.gitignore`) e viaggia con la cartella del
progetto tramite Nextcloud.

## Dati presenti

- 3 conti, 2 salvadanai con versamenti;
- 4 mesi di movimenti demo (32 al mese) con categorie e tag;
- automazioni attive e voci nel cestino;
- 6 posizioni di investimento con aperture, acquisti, vendite e dividendi;
- nome, foto profilo e impostazioni del profilo demo.

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
