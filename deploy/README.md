# Backup globale di Spendy

Questa procedura è per l'host LXC, non per il container web. Produce ogni 15
minuti un pacchetto cifrato con:

- dump PostgreSQL in formato custom (`db.dump`);
- `.env`, `compose.yaml` e `VERSION` (`config.tar.gz`);
- `manifest.json` con data, versione e checksum SHA-256.

Il pacchetto viene cifrato con **age** e caricato su Backblaze B2 con **rclone**.
La copia locale resta in `/var/backups/spendy`; il pannello admin legge lo stato
da `backup-status/status.json`.

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
- `SPENDY_AGE_IDENTITY_FILE=/etc/spendy-backup/age.key`.

## 4. systemd

I file in `deploy/systemd/` usano `/opt/spendy` come percorso del repository.
Modificalo se necessario, poi:

```bash
sudo cp deploy/systemd/spendy-*.service deploy/systemd/spendy-*.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now spendy-backup.timer
sudo systemctl enable --now spendy-restore-test.timer
```

Verifica:

```bash
systemctl list-timers 'spendy-*'
sudo systemctl start spendy-backup.service
sudo journalctl -u spendy-backup.service -n 100
```

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

## Ripristino completo su un host pulito

1. Recupera dal password manager la chiave privata age.
2. Scarica l'ultimo file `spendy-*.tar.age` da Backblaze B2.
3. Decifra e scompatta:

```bash
age --decrypt --identity age.key -o bundle.tar.gz spendy-....tar.age
tar -xzf bundle.tar.gz
```

4. Ricrea `.env` da `config.tar.gz` (contiene segreti: maneggia con cautela).
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
