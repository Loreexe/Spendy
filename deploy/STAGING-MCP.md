# Staging MCP — checklist di verifica

Da eseguire su una copia/staging dell'LXC, prima della produzione. Non usare
dati reali se non necessario; il token MCP dà accesso al profilo del suo
proprietario.

## 1. Preparazione

```bash
cd /opt/spendy-staging
sudo install -d -m 775 -o 10001 -g 10001 mcp-control
cp .env .env.bak
# .env: dominio staging in DJANGO_ALLOWED_HOSTS/CSRF_TRUSTED_ORIGINS,
# SPENDY_FRONTEND_BIND=<IP staging>, MCP disattivato
./scripts/update.sh --dry-run <tag>
./scripts/update.sh <tag>
sudo cp deploy/systemd/spendy-mcp-toggle.* /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now spendy-mcp-toggle.timer
```

Verifica base: frontend, `/api/health/`, login admin, **2FA** admin.

## 2. Token e servizio

1. Accedi come account normale proprietario del profilo.
2. **Impostazioni → MCP → Nuovo token**: nome `staging-smoke`.
3. Abilita per il test: conti (elenco, crea), movimenti (elenco, crea),
   dashboard (lettura). Salva con password.
4. Copia il token una sola volta (non incollarlo in chat/log).
5. Accedi come admin e accendi **Servizio MCP**; attendi il timer (≤1 min).

```bash
export MCP_URL="https://<staging-dominio>/mcp"
read -rs MCP_TOKEN   # incolla il token, Invio
export MCP_TOKEN
```

## 3. Smoke test

```bash
python3 scripts/mcp_smoke_test.py \
  --expect-tools accounts_list,accounts_create,transactions_list,transactions_create,dashboard_get
```

Con scrittura e tag AI:

```bash
python3 scripts/mcp_smoke_test.py --write \
  --expect-tools accounts_list,accounts_create,transactions_list,transactions_create,dashboard_get
```

Permesso negato (tool non abilitato):

```bash
python3 scripts/mcp_smoke_test.py --denied categories_list
```

Attesi: `initialize`, elenco tool filtrato, lettura, scrittura con tag `AI`,
rifiuto del tool non abilitato.

## 4. Revoca e rate limit

- Revoca il token da **Impostazioni → MCP**: lo smoke test deve fallire con
  `401`/errore MCP.
- Crea un token di prova e invia rapidamente più chiamate dello stesso tool:
  oltre **60/min** (o 20 scritture/min) deve comparire `429`/errore MCP.

## 5. Toggle reale

Con **Servizio MCP** acceso, verifica:

```bash
curl -s -o /dev/null -w '%{http_code}\n' "$MCP_URL"
```

- Acceso: endpoint raggiungibile (200/4xx di protocollo, non 502).
- Spegni dal pannello admin e attendi il timer: `502`.
- Riaccendi: endpoint di nuovo raggiungibile e smoke test verde.

## 6. Aggiornamento e rollback

```bash
./scripts/update.sh --dry-run <tag-successivo>
./scripts/update.sh <tag-successivo>
python3 scripts/mcp_smoke_test.py ...
```

Ripeti su una release precedente controllando che il flag MCP venga rispettato
e che lo stack web resti sano. Non forzare il rollback del database.

## 7. Audit e client reale

- Nel pannello admin, **Registro attività** deve mostrare eventi `mcp_call`
  con esito, tool e durata, senza payload finanziari completi.
- Configura **Claude Code** o **Hermes** con URL `https://<staging>/mcp` e
  header `Authorization: Bearer mcp_...`; prova una lettura e una scrittura.
- Verifica che le operazioni non abilitate siano assenti da `tools/list` e
  rifiutate se chiamate direttamente.

## 8. Esito

Annota in `.spendy-wiki/ROADMAP.md` § «Fase T» (T5) data, tag, esito, tool
provati e problemi. Solo dopo il verde su staging si passa alla produzione.
