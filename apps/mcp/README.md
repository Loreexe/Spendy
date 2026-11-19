# Spendy MCP service

Servizio MCP (Streamable HTTP) che espone i tool di Spendy ai client come
Claude Code o Hermes. Non accede al database: inoltra le chiamate all'API v1
con il token del client; il backend applica permessi, rate limit e audit.

## Avvio locale

Il backend deve essere raggiungibile e avere almeno un token MCP configurato
in Impostazioni → MCP.

```bash
SPENDY_BACKEND_URL=http://127.0.0.1:8000 \
  SPENDY_BACKEND_HOST_HEADER=localhost python apps/mcp/server.py
# endpoint: http://127.0.0.1:8001/mcp
# health:   http://127.0.0.1:8001/health
```

## Client

Configura il client MCP con:

- trasporto **Streamable HTTP**;
- URL: `https://<dominio>/mcp` (in LAN: `http://<IP-LXC>:8080/mcp`);
- header `Authorization: Bearer <token>`, con un token creato in
  **Spendy → Impostazioni → MCP** da un account normale.

Claude Code:

```bash
claude mcp add --transport http spendy \
  http://<IP-LXC>:8080/mcp \
  --header "Authorization: Bearer <token>"
```

Non usare un token della sezione **Dispositivi**: il token MCP inizia già con
`mcp_`; incollalo interamente dopo `Bearer`, senza aggiungere un secondo `mcp_`. I tool visibili sono solo quelli abilitati per quel token; le
operazioni non abilitate vengono rifiutate dal backend con `403`.

Per diagnosticare il token senza chiamare un tool:

```bash
curl -sS http://<IP-LXC>:8080/api/v1/mcp/context/ \
  -H "Authorization: Bearer <token>"
```

Deve restituire `permissions` e l’elenco delle operazioni; un token dispositivo
o revocato riceve `401`.

## Verifica

Dopo il deploy usa lo smoke test riutilizzabile:

```bash
MCP_URL="https://<dominio>/mcp" MCP_TOKEN="mcp_..." \
  python3 scripts/mcp_smoke_test.py --write
```

Per lo staging segui [deploy/STAGING-MCP.md](../../deploy/STAGING-MCP.md).
