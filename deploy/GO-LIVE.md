# Spendy — guida di go-live con Nginx Proxy Manager

Questa guida accompagna l'esposizione di Spendy su un dominio pubblico con
NPM e HTTPS. **Non esegue nulla da sola**: i comandi vanno lanciati sull'host
giusto (NPM, LXC di produzione, router/Proxmox) e verificati uno per uno.
Sostituisci i segnaposto `<DOMINIO>`, `<IP_LXC>`, `<IP_NPM>`, `<IP_PUBBLICO>`.

> Prima di iniziare: NPM e TLS non sono ancora applicati. La 2FA dell'admin è
> implementata nel workspace e il flusso API è stato provato sul demo; attivala
> prima dell'esposizione e fai una verifica visiva nel browser.

## 0. Decisioni e prerequisiti

- Dominio scelto e registrabile; accesso al pannello DNS.
- NPM aggiornato, raggiungibile in LAN e con pannello di amministrazione non
  esposto a Internet.
- LXC di produzione aggiornato alla release che vuoi esporre e con setup admin
  completato.
- IP statico o DDNS per la linea di casa; IPv6 gestito o disabilitato.
- Password manager pronto per: chiave age, `DJANGO_SECRET_KEY`, password
  PostgreSQL, password admin, credenziali NPM, chiave B2 e codici di recupero
  2FA.

## 1. Staging (prima di toccare la produzione)

1. Clona l'LXC (o usa uno snapshot Proxmox) e assegna un IP di test.
2. Copia il repository e crea un `.env` di staging con un dominio di test
   (`staging.<DOMINIO>` o hosts file) e segreti diversi.
3. Sull'LXC di staging esegui `docker compose up -d --build` e verifica
   `/api/health/`.
4. Prova su staging:
   - `./scripts/update.sh --dry-run <tag>` e poi l'aggiornamento reale;
   - rollback (interrompi il servizio o usa una release precedente);
   - ripristino del backup in un database temporaneo;
   - login admin, 2FA, pairing Android via HTTPS.
5. Non usare dati reali di produzione su staging; se serve un campione,
   ripristina un backup e trattalo come dato sensibile.
6. Alla fine distruggi lo staging o mantienilo spento.

## 2. Dominio e DNS

- Blocca il trasferimento del dominio (registrar lock), attiva la 2FA
  sull'account del registrar, il rinnovo automatico e la privacy WHOIS.
- Record:
  - `A <DOMINIO> <IP_PUBBLICO>` (e `AAAA` solo se IPv6 è configurato e
    protetto dal firewall);
  - `CAA <DOMINIO> issue "letsencrypt.org"`;
  - TTL basso (300 s) durante il cutover, poi alza.
- Se l'IP di casa cambia, configura un DDNS (o il client DNS del provider) e
  verifica che il record si aggiorni.
- Non pubblicare record email sul dominio finché non configuri SPF, DKIM e
  DMARC.
- Verifica: `dig +short A <DOMINIO>`, `dig +short AAAA <DOMINIO>`,
  `dig +short CAA <DOMINIO>`.

## 3. Firewall e rete

Regola d'oro: **da Internet devono arrivare solo 80 e 443 al reverse proxy**.
Tutto il resto (SSH, 8006, 81, 8080, 8000, 5432) resta su LAN/Tailscale.

- Router: port forwarding solo TCP 80/443 verso `<IP_NPM>`; niente UPnP, niente
  DMZ; se il router ha IPv6, applica le stesse regole al firewall IPv6.
- NPM: `81` (pannello) e SSH raggiungibili solo da LAN/Tailscale; 80/443
  pubblici.
- LXC app: `SPENDY_FRONTEND_BIND=<IP_LXC>` nel `.env`, così la `8080` non è su
  `0.0.0.0`; consenti la `8080` solo da `<IP_NPM>` (e dalla LAN/Tailscale per
  manutenzione).
- Docker: le porte pubblicate bypassano UFW; aggiungi regole `DOCKER-USER`
  (o usa il firewall Proxmox) per bloccare la `8080` da WAN.
- Proxmox: firewall attivo sull'LXC, pannello `8006` non raggiungibile da
  Internet.
- Verifica da una rete esterna: `nmap -Pn -p 80,443,8080,8000,5432,81,8006
  <IP_PUBBLICO>` → solo 80/443 aperti.

## 4. Nginx Proxy Manager

1. Aggiorna NPM all'ultima versione stabile e cambia le credenziali admin
   predefinite; abilita la 2FA se la versione la supporta.
2. Limita il pannello `81` a LAN/Tailscale (firewall o Access List).
3. Backup della configurazione NPM: la cartella dati (database, proxy host,
   certificati) va inclusa nel backup dell'host o in `SPENDY_EXTRA_BACKUP_PATHS`.
4. Crea un **Proxy Host**:
   - Domain: `<DOMINIO>`;
   - Scheme: `http`;
   - Forward Hostname/IP: `<IP_LXC>`;
   - Forward Port: `8080`;
   - Block Common Exploits: attivo;
   - Websockets: non necessario.
5. In **Advanced** incolla [spendy-advanced.conf](./npm/spendy-advanced.conf)
   (include `X-Forwarded-For` e `X-Forwarded-Proto` sovrascritti, limiti body e
   timeout). Non aggiungere un secondo header HSTS qui.
6. **SSL**: richiedi Let's Encrypt (HTTP-01, la porta 80 deve essere
   raggiungibile durante l'emissione), attiva **Force SSL**, **HTTP/2** e
   **HSTS** (`max-age=31536000`). Preload solo quando il dominio è stabile.
7. Verifica il rinnovo automatico e configura l'alert di scadenza
   (`SPENDY_DOMAIN` in `scripts/healthcheck.py`).

Se usi Cloudflare davanti a NPM, non applicare l'overwrite di `X-Forwarded-For`
senza configurare i real IP di Cloudflare: aggiunge complessità. Per la prima
esposizione è più semplice NPM diretto.

## 4bis. MCP (opzionale)

Se vuoi collegare Claude Code, Hermes o un altro client MCP:

1. Prepara la cartella del flag con i permessi dell'utente backend:
   ```bash
   cd /opt/spendy
   sudo install -d -m 775 -o 10001 -g 10001 mcp-control
   ```
2. Accedi come admin e apri **Impostazioni globali → MCP**: il servizio è
   spento di default. Accendilo quando vuoi esporlo.
3. Sull'host installa l'unità che applica il flag:
   ```bash
   sudo cp deploy/systemd/spendy-mcp-toggle.* /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now spendy-mcp-toggle.timer
   ```
4. Crea il token nell'account proprietario del profilo (**Impostazioni → MCP**),
   scegli le operazioni abilitate e copia il token una sola volta.
5. Configura il client con URL `https://<DOMINIO>/mcp` e header
   `Authorization: Bearer mcp_...`.
6. Verifica:
   ```bash
   curl -sS -o /dev/null -w '%{http_code}\n' https://<DOMINIO>/mcp
   docker compose exec -T mcp python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8001/health', timeout=3).read().decode())"
   ```
   L'endpoint segue la raggiungibilità dell'app: ora LAN/Tailscale, poi
   pubblico quando lo sarà il dominio. Senza token validi risponde con errore;
   le operazioni disabilitate sono rifiutate dal backend e registrate.

Prima della produzione esegui la checklist [STAGING-MCP.md](./STAGING-MCP.md)
e lo smoke test `scripts/mcp_smoke_test.py`.

## 5. Configurazione dell'app

Nel `.env` dell'LXC di produzione:

```bash
DJANGO_ALLOWED_HOSTS=<DOMINIO>,<IP_LXC>,<nome-tailscale>
CSRF_TRUSTED_ORIGINS=https://<DOMINIO>
SECURE_COOKIES=1
SECURE_SSL_REDIRECT=1
SECURE_HSTS_SECONDS=0
SPENDY_FRONTEND_BIND=<IP_LXC>
TRUSTED_PROXY_CIDRS=127.0.0.0/8,172.16.0.0/12,<IP_NPM>
SETUP_ALLOWED_CIDRS=127.0.0.0/8,::1/128,100.64.0.0/10,fd7a:115c:a1e0::/48
SESSION_COOKIE_AGE=43200
SPENDY_SESSION_IDLE_TIMEOUT_SECONDS=7200
SPENDY_AUDIT_RETENTION_DAYS=180
```

- Ruota i segreti prima dell'esposizione: `DJANGO_SECRET_KEY` nuovo, password
  PostgreSQL nuova (con `ALTER USER` coordinato), password admin, chiave B2,
  credenziali NPM. `.env` con permessi `600`.
- Applica la release scelta (`./scripts/update.sh <tag>`) e verifica
  `/api/health/`; per sole modifiche di configurazione `docker compose up -d`
  dopo aver controllato `docker compose config`.
- Verifica che il setup admin sia completato.
- Accedi come admin, apri **Impostazioni → Sicurezza** e attiva la **2FA TOTP**;
  salva i codici di recupero fuori dal server.

## 6. Verifiche di accettazione

Eseguile da una rete esterna, non solo dalla LAN.

| Verifica | Comando / metodo | Atteso |
| --- | --- | --- |
| Porte | `nmap` esterno | solo 80/443 |
| TLS | SSL Labs, `openssl s_client -connect <DOMINIO>:443` | A/A+, TLS 1.2+ |
| Header | `curl -sSI https://<DOMINIO>/` | HSTS, CSP, XFO, nosniff, Referrer, Permissions |
| Cookie | login dal browser, DevTools | `Secure`, `HttpOnly`, `SameSite=Lax` |
| Health | `curl -sS https://<DOMINIO>/api/health/` | `status: ok`, versione attesa |
| OpenAPI | `curl -s -o /dev/null -w '%{http_code}' https://<DOMINIO>/api/v1/schema/` | 401/403 |
| Rate limit | 12 login errati di fila | `429`; anche inviando `X-Forwarded-For` falsi |
| Lockout | 5 errori stesso identificativo | `429` con `Retry-After` |
| 2FA | login admin | richiesta del codice; codice errato rifiutato |
| Registrazione | email già presente | risposta neutra, nessun duplicato |
| Backup | `python3 scripts/backup_global.py backup` | status `ok`; `restore-test` verde |
| Alert | `systemctl start spendy-alert@prova.service` | notifica ricevuta sul canale |
| Android | pairing/login da telefono | solo HTTPS, token revocato al logout |
| Log | `journalctl`/log NPM | nessun errore 5xx anomalo o scansione evidente |

Consiglia anche:

- [SSL Labs](https://www.ssllabs.com/ssltest/) e [securityheaders.com](https://securityheaders.com/);
- scansione ZAP baseline su staging o produzione (senza attacchi distruttivi);
- `pip-audit` e `npm audit` prima della release.

## 7. Ordine del go-live

1. Staging verde (aggiornamento, rollback, ripristino, 2FA).
2. Backup manuale e verifica dello stato.
3. Rotazione segreti e `.env` di produzione.
4. Riavvio stack e health interno.
5. NPM Proxy Host + certificato + Force SSL + HSTS.
6. Verifiche di accettazione esterne.
7. Attivazione 2FA (se non già fatta) e salvataggio codici.
8. Apertura: lascia attiva la registrazione con approvazione; nessuna
   promozione pubblica.
9. Monitoraggio 24–48 ore: accessi falliti, 5xx, disco, backup, certificato.

## 8. Rollback e accesso di emergenza

- **Tailscale resta la via di emergenza**: verifica che l'LXC sia raggiungibile
  dalla tua rete Tailscale anche con NPM spento.
- Per fermare l'esposizione: disabilita il Proxy Host in NPM (o metti la
  manutenzione con `touch maintenance/on`); l'app resta raggiungibile da LAN.
- `scripts/update.sh` fa rollback automatico su build o health check falliti;
  non annulla le migrazioni del database. Per un ripristino dati usa
  [deploy/README.md](./README.md) § «Ripristino completo».
- Se il certificato non si rinnova: controlla la porta 80, i log NPM e l'alert
  `SPENDY_DOMAIN`; NPM può usare la sfida DNS se la 80 è bloccata.
- In caso di sospetta compromissione: revoca i token dei dispositivi, cambia la
  password admin, ruota `DJANGO_SECRET_KEY` (invalida le sessioni), ripristina
  il backup solo dopo aver verificato l'integrità.

## 9. Checklist finale

- [ ] Dominio bloccato, 2FA registrar, rinnovo automatico, privacy WHOIS.
- [ ] A/AAAA e CAA corretti; TTL basso in cutover.
- [ ] Solo 80/443 esposti; `8080`/`8006`/`81`/`8000`/`5432` chiusi da WAN.
- [ ] NPM aggiornato, pannello ristretto, backup config/certificati.
- [ ] Proxy Host + Advanced + Let's Encrypt + Force SSL + HTTP/2 + HSTS.
- [ ] `.env` di produzione completo, segreti ruotati, permessi `600`.
- [ ] Release attesa e health check verde.
- [ ] Setup completato e 2FA admin attiva con codici salvati.
- [ ] Verifiche di accettazione superate.
- [ ] Backup + restore test + alert verificati.
- [ ] Tailscale di emergenza provato.
- [ ] Monitoraggio 24–48 ore e revisione log.
