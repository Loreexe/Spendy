"""Servizio MCP di Spendy: adattatore tra MCP e l'API v1 (DC-123).

Il servizio non accede al database: ogni tool inoltra la richiesta all'API
Spendy con l'header ``Authorization`` del client. Il backend applica token,
permessi per operazione, rate limit e audit.
"""
from __future__ import annotations

import asyncio
import base64
import json
import os
import sys
from contextvars import ContextVar
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from mcp.server.mcpserver import Context, MCPServer

BACKEND_URL = os.environ.get("SPENDY_BACKEND_URL", "http://backend:8000").rstrip("/")
HOST = os.environ.get("MCP_HOST", "0.0.0.0")
PORT = int(os.environ.get("MCP_PORT", "8001"))
TIMEOUT = float(os.environ.get("SPENDY_MCP_BACKEND_TIMEOUT", "20"))
BACKEND_HOST_HEADER = os.environ.get("SPENDY_BACKEND_HOST_HEADER", "localhost")

_current_authorization: ContextVar[str] = ContextVar(
    "spendy_mcp_authorization", default=""
)
TOOL_TO_OPERATION: dict[str, str] = {}


def _fetch_json(url: str, authorization: str = "") -> dict:
    request = Request(
        url,
        headers={"Accept": "application/json", "Host": BACKEND_HOST_HEADER},
    )
    if authorization:
        request.add_header("Authorization", authorization)
    with urlopen(request, timeout=TIMEOUT) as response:
        return json.loads(response.read().decode("utf-8"))


def load_operations() -> list[dict]:
    try:
        payload = _fetch_json(f"{BACKEND_URL}/api/v1/mcp/catalog/")
    except (OSError, ValueError, URLError) as exc:
        print(f"[mcp] catalogo non caricato: {exc}", file=sys.stderr, flush=True)
        return []
    return list(payload.get("operations", []))


def fetch_enabled_operations(authorization: str) -> set[str] | None:
    try:
        payload = _fetch_json(
            f"{BACKEND_URL}/api/v1/mcp/context/", authorization
        )
    except (OSError, ValueError, URLError):
        return None
    permissions = payload.get("permissions") or {}
    return set(permissions.keys())


def _authorization_from(ctx: Context) -> str:
    headers = ctx.headers or {}
    for key, value in headers.items():
        if str(key).lower() == "authorization":
            return str(value)
    return ""


def _call_backend(authorization: str, operation: dict, params: dict):
    path = operation["path"]
    method = operation["method"]
    payload = dict(params or {})
    if operation.get("needs_id"):
        item_id = payload.pop("id", None)
        if item_id is None:
            raise ValueError("Parametro 'id' obbligatorio per questa operazione.")
        path = path.replace("{id}", str(item_id))
    url = f"{BACKEND_URL}{path}"
    headers = {
        "Accept": "application/json",
        "Authorization": authorization,
        "Host": BACKEND_HOST_HEADER,
    }
    data = None
    if method in {"GET", "DELETE"}:
        if payload:
            url += "?" + urlencode(payload, doseq=True)
    else:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = Request(url, data=data, method=method, headers=headers)
    try:
        with urlopen(request, timeout=TIMEOUT) as response:
            content_type = response.headers.get("Content-Type", "")
            body = response.read()
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        try:
            parsed = json.loads(detail)
            message = parsed.get("detail") or parsed
        except ValueError:
            message = detail[:500]
        raise ValueError(f"Spendy API {exc.code}: {message}") from exc
    except URLError as exc:
        raise ValueError(f"Spendy API non raggiungibile: {exc.reason}") from exc
    if "application/json" in content_type:
        return json.loads(body.decode("utf-8"))
    return {
        "content_type": content_type or "application/octet-stream",
        "content_base64": base64.b64encode(body).decode("ascii"),
    }


def make_tool(operation: dict):
    async def tool(ctx: Context, params: dict | None = None) -> dict:
        authorization = _authorization_from(ctx)
        if not authorization:
            raise ValueError("Token MCP mancante nell'header Authorization.")
        return await asyncio.to_thread(
            _call_backend, authorization, operation, params or {}
        )

    tool.__name__ = operation["tool_name"]
    tool.__doc__ = (
        f"{operation['label']} — {operation['method']} {operation['path']}"
    )
    return tool


class SpendyMCPServer(MCPServer):
    async def list_tools(self):
        tools = await super().list_tools()
        authorization = _current_authorization.get()
        if not authorization:
            return tools
        enabled = await asyncio.to_thread(
            fetch_enabled_operations, authorization
        )
        if enabled is None:
            return tools
        return [
            tool
            for tool in tools
            if TOOL_TO_OPERATION.get(tool.name) in enabled
        ]


class BearerMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return
        headers = dict(scope.get("headers", []))
        raw = headers.get(b"authorization", b"").decode("utf-8", "replace")
        context_token = _current_authorization.set(raw)
        try:
            await self.app(scope, receive, send)
        finally:
            _current_authorization.reset(context_token)


def build_app():
    operations = load_operations()
    mcp = SpendyMCPServer(
        "Spendy",
        version=os.environ.get("SPENDY_VERSION", "0.0.0"),
        instructions=(
            "Gestisci le finanze personali Spendy rispettando i permessi del "
            "token. Le scritture sono immediate e tracciate; i movimenti scritti "
            "via MCP ricevono il tag AI."
        ),
    )
    for operation in operations:
        TOOL_TO_OPERATION[operation["tool_name"]] = operation["id"]
        mcp.add_tool(
            make_tool(operation),
            name=operation["tool_name"],
            description=f"{operation['label']} ({operation['kind']})",
        )
    app = mcp.streamable_http_app(
        streamable_http_path="/mcp",
        json_response=True,
        stateless_http=True,
        host=HOST,
    )

    async def health(request):
        from starlette.responses import JSONResponse

        return JSONResponse({"status": "ok", "tools": len(operations)})

    from starlette.routing import Route

    app.router.routes.append(Route("/health", health))
    return BearerMiddleware(app)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(build_app(), host=HOST, port=PORT)
