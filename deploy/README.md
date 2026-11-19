# Backup globale di Spendy

Questa procedura è per l'host LXC, non per il container web. Produce ogni 15
minuti un pacchetto cifrato con:

- dump PostgreSQL in formato custom (`db.dump`);
- `.env`, `compose.yaml` e `VERSION` (`config.tar.gz`);
- `manifest.json` con data, versione e checksum SHA-256.

Il pacchetto viene cifrato con **age** e caricato su Backblaze B2 con **rclone**.
La copia locale resta in `/var/backups/spendy`; il pannello admin legge lo stato
da `backup-status/status.json`.

## Automazioni periodiche

`compose.yaml` avvia anche `automation-worker`, che esegue ogni minuto
`python manage.py run_automations`. Non serve un cron sull'host: il worker usa
la stessa immagine e lo stesso database del backend. Dopo un aggiornamento
Compose lo ricrea automaticamente; per controllarlo:

```bash
docker compose ps automation-worker
docker compose logs --tail=50 automation-worker
```

Le attese del retry si configurano in `.env` con
`SPENDY_AUTOMATION_MAX_ATTEMPTS` e `SPENDY_AUTOMATION_RETRY_DELAYS`.

## Prerequisiti sull'host

```bash
apt install age rclone python3
```

Serve inoltre Docker Compose funzionante e il repository Spendy sull'host, ad
esempio in `/opt/spendy`.

## 1. Backblaze B2

1. Crea un account Backblaze e un bucket **privato** chiamato `SpendyBackup`.
2. Crea una **Application Key** con accesso limitato a quel bucket e permessi
   Read and Write. Conserva `keyID` e `applicationKey`.
3. Sull'host crea `/root/.config/rclone/rclone.conf` con:

```ini
[b2]
type = b2
account = KEY_ID
key = APPLICATION_KEY
hard_delete = true
```

Imposta i permessi:

```bash
chmod 700 /root/.config/rclone
chmod 600 /root/.config/rclone/rclone.conf
```

Verifica:

```bash
sudo rclone lsd b2:
```

Il servizio systemd gira come root, quindi la configurazione deve essere quella
di root. Il bucket deve restare privato: i file sono già cifrati con age, ma non
vanno resi pubblici.

## 2. Chiave age

Genera la coppia di chiavi su una macchina fidata:

```bash
age-keygen -o age.key
```

- La chiave **pubblica** (`age1...`) va in `SPENDY_AGE_RECIPIENT`.
- La chiave **privata** va nel password manager.
- Per il test automatico mensile, copia la chiave privata sull'host in
  `/etc/spendy-backup/age.key` con permessi `600` e proprietario `root`.

La chiave privata non deve mai finire nel repository o in un backup non
cifrato.

## 3. Configurazione

```bash
sudo install -d -m 700 /etc/spendy-backup
sudo cp deploy/backup.env.example /etc/spendy-backup.env
sudo chmod 600 /etc/spendy-backup.env
sudo editor /etc/spendy-backup.env
```

Imposta almeno:

- `SPENDY_AGE_RECIPIENT`;
- `SPENDY_RCLONE_REMOTE` (ad esempio `b2:SpendyBackup`);
- `SPENDY_BACKUP_STATUS_FILE` con il percorso del repository;
- `SPENDY_AGE_IDENTITY_FILE=/etc/spendy-backup/age.key`;
- `SPENDY_EXTRA_BACKUP_PATHS` (opzionale): percorsi assoluti di configurazione
  e certificati NPM o altri dati dell'host da includere nel bundle cifrato, ad
  esempio `/var/lib/docker/volumes/npm_data/_data` se NPM usa un volume Docker.
  Separare più percorsi con virgola o riga. Il bundle resta cifrato con age.

## 4. systemd

I file in `deploy/systemd/` usano `/opt/spendy` come percorso del repository.
Modificalo se necessario, poi:

```bash
sudo cp deploy/systemd/spendy-*.service deploy/systemd/spendy-*.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now spendy-backup.timer
sudo systemctl enable --now spendy-restore-test.timer
sudo systemctl enable --now spendy-healthcheck.timer
```

Verifica:

```bash
systemctl list-timers 'spendy-*'
sudo systemctl start spendy-backup.service
sudo journalctl -u spendy-backup.service -n 100
```

Le unità `spendy-backup.service` e `spendy-restore-test.service` hanno
`OnFailure=spendy-alert@%N.service`: un fallimento avvia l'invio dell'alert.

## 4bis. Alert e monitoraggio

Gli alert usano un webhook compatibile **ntfy** (`SPENDY_ALERT_WEBHOOK`). Il
messaggio contiene solo host, unità, ora e il problema rilevato: nessun dato
finanziario e nessun segreto. Se il webhook non è impostato, l'alert resta nel
journal.

Configurazione consigliata (permessi `600`, proprietario `root`):

```bash
sudo install -m 600 /dev/null /etc/spendy-alert.env
sudo editor /etc/spendy-alert.env
```

```bash
SPENDY_ALERT_WEBHOOK=https://ntfy.example.com/spendy-<topic-privato>
SPENDY_DOMAIN=spendy.example.com
```

Puoi mettere le stesse variabili in `/etc/spendy-backup.env`; le unità leggono
entrambi i file. `scripts/healthcheck.py`, eseguito ogni 10 minuti, controlla:

- età dell'ultimo backup riuscito (default 30 minuti) e stato `failed`;
- spazio disco (default allarme all'85%);
- scadenza del certificato TLS del dominio (default 14 giorni), se
  `SPENDY_DOMAIN` è impostato.

Prova manuale:

```bash
sudo sh -c 'set -a; . /etc/spendy-backup.env; [ -f /etc/spendy-alert.env ] && . /etc/spendy-alert.env; set +a; /usr/bin/python3 /opt/spendy/scripts/alert.py test'
sudo sh -c 'set -a; . /etc/spendy-backup.env; [ -f /etc/spendy-alert.env ] && . /etc/spendy-alert.env; set +a; /usr/bin/python3 /opt/spendy/scripts/healthcheck.py'
```

Per un uptime esterno usa Uptime Kuma o Healthchecks.io su
`https://<dominio>/api/health/` (intervallo 1–5 minuti) e configura l'alert
sullo stesso canale. NPM rinnova il certificato Let's Encrypt; il controllo di
`healthcheck.py` segnala se il rinnovo non è andato a buon fine.

```bash
sudo systemctl start spendy-healthcheck.service
sudo journalctl -u spendy-healthcheck.service -n 50
```

## 4ter. Servizio MCP

Il servizio MCP è un container separato (`apps/mcp`), con profilo Compose
`mcp`, che parla con l'API Spendy e non accede al database. È **spento di
default** e si accende dal pannello admin (Impostazioni globali → MCP).

Prima del primo avvio crea la cartella del flag con i permessi dell'utente
backend (UID 10001):

```bash
cd /opt/spendy
sudo install -d -m 775 -o 10001 -g 10001 mcp-control
```

- Flag: `mcp-control/state.json` (`{"enabled": true|false}`), montato nel
  backend; il pannello lo scrive.
- Applicazione del flag: `spendy-mcp-toggle.timer` esegue ogni minuto
  [scripts/mcp_toggle.sh](../scripts/mcp_toggle.sh), che esegue solo
  `docker compose --profile mcp up -d mcp` oppure `docker compose stop mcp`.
  Nessun socket Docker è montato nel container web.
- Endpoint: NPM inoltra il dominio al frontend (porta 8080); il frontend Nginx
  inoltra `/mcp` al servizio `mcp:8001`. I client usano
  `https://<dominio>/mcp` con `Authorization: Bearer <token>` (il token include già `mcp_`).
- Aggiornamento: `./scripts/update.sh <tag>` ricostruisce anche l'immagine MCP
  e la avvia solo se il flag è attivo; il rollback rispetta lo stesso flag.

Installazione delle unità di toggle:

```bash
sudo cp deploy/systemd/spendy-mcp-toggle.* /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now spendy-mcp-toggle.timer
sudo systemctl list-timers 'spendy-mcp-toggle*'
```

Verifica manuale:

```bash
docker compose --profile mcp up -d mcp
docker compose exec -T mcp python -c \
  "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8001/health', timeout=3).read().decode())"
curl -sS https://<dominio>/mcp -H 'Authorization: Bearer <token>' ...
```

In assenza di token validi l'endpoint rifiuta le chiamate; le operazioni non
abilitate per il token sono rifiutate dal backend con `403` e registrate
nell'audit. Il servizio non espone tool di amministrazione o sicurezza.

Verifica su staging: [STAGING-MCP.md](./STAGING-MCP.md) e smoke test
[scripts/mcp_smoke_test.py](../scripts/mcp_smoke_test.py).

## 5. Prova manuale

```bash
cd /opt/spendy
sudo sh -c 'set -a; . /etc/spendy-backup.env; set +a; python3 scripts/backup_global.py backup'
sudo sh -c 'set -a; . /etc/spendy-backup.env; set +a; python3 scripts/backup_global.py restore-test'
```

Il test di ripristino crea un database temporaneo, ripristina l'ultimo backup,
verifica `accounts_user` e lo elimina.

## 6. Stato nel pannello admin

`compose.yaml` monta `./backup-status` in `/app/backup-status` in sola lettura.
Il job scrive `status.json`; la sezione **Sistema** mostra ultimo backup, esito,
copia offsite, ultimo successo e test di ripristino.

## Aggiornamento a una release

Sull'host LXC, dalla root del repository (`/opt/spendy`):

```bash
./scripts/update.sh --dry-run v0.6.0   # verifica prerequisiti, non modifica nulla
./scripts/update.sh v0.6.0             # applica la release
```

**Prima esecuzione (bootstrap).** Se il checkout non contiene ancora
`scripts/update.sh`, recupera il tag ed esegui lo script senza modificare il
working tree:

```bash
VERSION=v0.4.2
cd /opt/spendy
export SPENDY_ROOT=/opt/spendy
git fetch --tags origin
git show "$VERSION:scripts/update.sh" > /tmp/spendy-update.sh
bash /tmp/spendy-update.sh "$VERSION"
rm -f /tmp/spendy-update.sh
```

Non usare `git show ... | bash -s`: i comandi figli possono leggere lo stdin e
consumare il resto dello script, facendolo terminare in anticipo. Il file
temporaneo evita il problema.

Il rollback parte dal commit attualmente estratto, quindi il bootstrap da una
release precedente funziona come gli aggiornamenti successivi. `SPENDY_ROOT` è
obbligatorio quando lo script viene eseguito da fuori dal repository.

Lo script richiede un **working tree pulito** e un `.env` presente, poi:

1. recupera i tag e verifica che il tag esista sul remote `origin` e che il
   commit locale coincida con quello remoto;
2. controlla che `VERSION` nel tag coincida con `vX.Y.Z` e rifiuta un
   downgrade senza `--allow-downgrade`;
3. crea un backup locale del database in `backups/` (salvo `--no-backup`);
4. attiva la pagina di manutenzione (`maintenance/on`), applica il tag in
   modalità detached, allinea `SPENDY_VERSION` nel `.env`, ricostruisce e
   avvia i container;
5. attende l'health check del backend, verifica la versione attiva e il
   frontend, poi rimuove la manutenzione;
6. se uno dei passi fallisce, ripristina il commit precedente e ricostruisce.
   Il **database non viene ripristinato automaticamente**: le migrazioni già
   applicate restano. Se il rollback non basta, usare il ripristino completo
   dalla sezione successiva.

Note operative:

- La prima esecuzione su una versione precedente a questo script non mostra la
  pagina di manutenzione, perché il container frontend non ha ancora il volume
  `maintenance/`. Dalla successiva il comportamento è completo.
- Il rollback automatico è pensato per errori di build, avvio o health check;
  non annulla migrazioni irreversibili.
- La manutenzione si può gestire anche a mano: `touch maintenance/on` attiva,
  `rm maintenance/on` disattiva. La pagina è servita con stato `503`.
- Il backup locale è in chiaro e va trattato come dato finanziario: usa
  `./scripts/backup.sh` solo per il rollback e conservalo fuori dal repository.
- Il controllo della versione attiva viene saltato per release anteriori alla
  `0.3.0`, che non esponevano `SPENDY_VERSION`.

## Ripristino completo su un host pulito

1. Recupera dal password manager la chiave privata age.
2. Scarica l'ultimo file `spendy-*.tar.age` da Backblaze B2.
3. Decifra e scompatta:

```bash
age --decrypt --identity age.key -o bundle.tar.gz spendy-....tar.age
tar -xzf bundle.tar.gz
```

4. Ricrea `.env` da `config.tar.gz` (contiene segreti: maneggia con cautela).
   Il bundle può contenere anche `extra/NN-<nome>/…`: sono i percorsi indicati
   in `SPENDY_EXTRA_BACKUP_PATHS` (configurazione e certificati NPM, dati
   dell'host). Il manifest cifrato elenca i percorsi originali; ripristinali
   nella stessa posizione. Se ripristini NPM, ferma il suo servizio prima di
   sostituire database e certificati.
5. Avvia PostgreSQL e ripristina il dump:

```bash
docker compose up -d db
docker compose exec -T db sh -c 'createdb -U "$POSTGRES_USER" spendy_restore'
docker compose exec -T db sh -c 'pg_restore -U "$POSTGRES_USER" -d spendy_restore --no-owner --no-privileges' < db.dump
```

6. Verifica i dati, poi sostituisci il database di produzione solo dopo un
   backup dello stato corrente.
7. Avvia backend e frontend e verifica `/api/health/`.
8. Misura e annota il tempo di ripristino: deve restare entro l'RTO di 24 ore.

Il ripristino completo non è automatizzato: è una procedura documentata e va
provata su un ambiente pulito prima di considerarla verificata.
