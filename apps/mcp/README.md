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

- URL: `https://<dominio>/mcp`;
- header `Authorization: Bearer mcp_...` (token creato in Spendy).

I tool visibili sono solo quelli abilitati per quel token; le operazioni non
abilitate vengono rifiutate dal backend con `403`.

## Verifica

Dopo il deploy usa lo smoke test riutilizzabile:

```bash
MCP_URL="https://<dominio>/mcp" MCP_TOKEN="mcp_..." \
  python3 scripts/mcp_smoke_test.py --write
```

Per lo staging segui [deploy/STAGING-MCP.md](../../deploy/STAGING-MCP.md).
