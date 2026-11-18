#!/usr/bin/env python3
"""Smoke test MCP contro un endpoint Spendy reale (staging/produzione).

Uso:
    MCP_URL=https://staging.example.com/mcp MCP_TOKEN=mcp_... \\
        python3 scripts/mcp_smoke_test.py

Opzioni:
    --url URL          alternativa a MCP_URL
    --token TOKEN      alternativa a MCP_TOKEN (meglio passarlo da ambiente)
    --write            prova anche una scrittura e verifica il tag AI
    --expect-tools     elenco separato da virgole di tool attesi
    --denied NAME      tool che deve essere rifiutato (permesso assente)
    --timeout SECONDI  default 30

Non stampa il token. Esce 0 se tutti i controlli passano, 1 altrimenti.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import date

PROTOCOL_VERSION = "2025-06-18"


def rpc(url: str, token: str, method: str, params: dict | None, timeout: float):
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params or {},
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "Authorization": f"Bearer {token}",
            "MCP-Protocol-Version": PROTOCOL_VERSION,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:500]
        raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"endpoint non raggiungibile: {exc.reason}") from exc
    if raw.startswith("event:") or raw.startswith("data:"):
        for line in raw.splitlines():
            if line.startswith("data:"):
                raw = line[5:].strip()
                break
    data = json.loads(raw)
    if "error" in data:
        raise RuntimeError(f"errore MCP: {data['error']}")
    return data.get("result", {})


def content_text(result: dict) -> str:
    content = result.get("content") or []
    if not content:
        return ""
    item = content[0]
    return item.get("text", "") if isinstance(item, dict) else str(item)


def call_tool(url, token, name, arguments, timeout):
    result = rpc(
        url,
        token,
        "tools/call",
        {"name": name, "arguments": {"params": arguments}},
        timeout,
    )
    if result.get("isError"):
        raise RuntimeError(f"{name} ha restituito errore: {content_text(result)[:300]}")
    return result


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=os.environ.get("MCP_URL", ""))
    parser.add_argument("--token", default=os.environ.get("MCP_TOKEN", ""))
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--expect-tools", default="")
    parser.add_argument("--denied", default="")
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args(argv)
    if not args.url or not args.token:
        parser.error("servono MCP_URL e MCP_TOKEN (o --url/--token)")

    try:
        init = rpc(args.url, args.token, "initialize", {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": "spendy-smoke", "version": "1.0"},
        }, args.timeout)
        server = init.get("serverInfo", {})
        print(f"initialize: {server.get('name')} {server.get('version')}")

        tools = sorted(
            tool["name"]
            for tool in rpc(args.url, args.token, "tools/list", {}, args.timeout)["tools"]
        )
        print("tools:", ", ".join(tools) if tools else "(nessuno)")
        if not tools:
            raise RuntimeError("tools/list vuoto: controlla permessi/token/servizio")
        if args.expect_tools:
            expected = {name.strip() for name in args.expect_tools.split(",") if name.strip()}
            if set(tools) != expected:
                raise RuntimeError(f"tool inattesi: attesi {sorted(expected)}, ottenuti {tools}")

        if args.denied:
            result = rpc(
                args.url,
                args.token,
                "tools/call",
                {"name": args.denied, "arguments": {"params": {}}},
                args.timeout,
            )
            if not result.get("isError"):
                raise RuntimeError(f"{args.denied} non è stato rifiutato")
            print(f"denied: {args.denied} rifiutato correttamente")

        if args.write:
            accounts = json.loads(content_text(call_tool(
                args.url, args.token, "accounts_list", {}, args.timeout
            )))
            account_id = None
            if accounts.get("accounts"):
                account_id = accounts["accounts"][0]["id"]
            elif "accounts_create" in tools:
                created = json.loads(content_text(call_tool(
                    args.url, args.token, "accounts_create",
                    {"name": "Smoke MCP", "type": "cash", "initial_balance": "10.00"},
                    args.timeout,
                )))
                account_id = created["id"]
            if account_id is None:
                raise RuntimeError("nessun conto disponibile e accounts_create non abilitato")
            description = f"Smoke MCP {date.today().isoformat()}"
            call_tool(args.url, args.token, "transactions_create", {
                "kind": "expense",
                "date": date.today().isoformat(),
                "description": description,
                "amount": "1.00",
                "account": account_id,
            }, args.timeout)
            listed = json.loads(content_text(call_tool(
                args.url, args.token, "transactions_list", {"limit": 10}, args.timeout
            )))
            target = next(
                (item for item in listed.get("transactions", []) if item.get("description") == description),
                None,
            )
            if target is None:
                raise RuntimeError("movimento creato non trovato in transactions_list")
            if "AI" not in (target.get("tags") or []):
                raise RuntimeError("tag AI assente sul movimento creato via MCP")
            print("write: movimento creato con tag AI")

        print("MCP SMOKE TEST: OK")
        return 0
    except Exception as exc:  # noqa: BLE001 - smoke test leggibile
        print(f"MCP SMOKE TEST FALLITO: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
