"""Catalogo delle operazioni MCP e risoluzione dalla richiesta HTTP (DC-123)."""
from __future__ import annotations

from dataclasses import dataclass

from django.urls import NoReverseMatch, reverse


@dataclass(frozen=True)
class McpOperation:
    id: str
    area: str
    label: str
    view_name: str
    method: str
    kind: str  # "read" | "write"


OPERATIONS: tuple[McpOperation, ...] = (
    # Profilo
    McpOperation("profile.get", "Profilo", "Leggi profilo", "finance-profile", "GET", "read"),
    # Dashboard e ricerca
    McpOperation("dashboard.get", "Dashboard e ricerca", "Riepilogo dashboard", "finance-dashboard", "GET", "read"),
    McpOperation("dashboard.series", "Dashboard e ricerca", "Serie temporali", "finance-dashboard-series", "GET", "read"),
    McpOperation("search", "Dashboard e ricerca", "Ricerca globale", "finance-search", "GET", "read"),
    # Conti
    McpOperation("accounts.list", "Conti", "Elenco conti", "finance-accounts", "GET", "read"),
    McpOperation("accounts.create", "Conti", "Crea conto", "finance-accounts", "POST", "write"),
    McpOperation("accounts.get", "Conti", "Dettaglio conto", "finance-account-detail", "GET", "read"),
    McpOperation("accounts.update", "Conti", "Modifica conto", "finance-account-detail", "PATCH", "write"),
    McpOperation("accounts.delete", "Conti", "Elimina conto", "finance-account-detail", "DELETE", "write"),
    # Movimenti
    McpOperation("transactions.list", "Movimenti", "Elenco movimenti", "finance-transactions", "GET", "read"),
    McpOperation("transactions.create", "Movimenti", "Crea movimento", "finance-transactions", "POST", "write"),
    McpOperation("transactions.get", "Movimenti", "Dettaglio movimento", "finance-transaction-detail", "GET", "read"),
    McpOperation("transactions.update", "Movimenti", "Modifica movimento", "finance-transaction-detail", "PATCH", "write"),
    McpOperation("transactions.delete", "Movimenti", "Elimina movimento", "finance-transaction-detail", "DELETE", "write"),
    # Cestino
    McpOperation("trash.list", "Cestino", "Elenco cestino", "finance-trash", "GET", "read"),
    McpOperation("trash.restore", "Cestino", "Ripristina elemento", "finance-trash-restore", "POST", "write"),
    McpOperation("trash.purge", "Cestino", "Elimina definitivamente", "finance-trash-purge", "POST", "write"),
    McpOperation("trash.empty", "Cestino", "Svuota cestino", "finance-trash-empty", "POST", "write"),
    # Categorie e tag
    McpOperation("categories.list", "Categorie e tag", "Elenco categorie", "finance-categories", "GET", "read"),
    McpOperation("categories.create", "Categorie e tag", "Crea categoria", "finance-categories", "POST", "write"),
    McpOperation("categories.get", "Categorie e tag", "Dettaglio categoria", "finance-category-detail", "GET", "read"),
    McpOperation("categories.update", "Categorie e tag", "Modifica categoria", "finance-category-detail", "PATCH", "write"),
    McpOperation("categories.delete", "Categorie e tag", "Elimina categoria", "finance-category-detail", "DELETE", "write"),
    McpOperation("categories.suggest", "Categorie e tag", "Suggerisci categoria", "finance-suggest-category", "POST", "read"),
    McpOperation("tags.list", "Categorie e tag", "Elenco tag", "finance-tags", "GET", "read"),
    McpOperation("tags.create", "Categorie e tag", "Crea tag", "finance-tags", "POST", "write"),
    McpOperation("tags.get", "Categorie e tag", "Dettaglio tag", "finance-tag-detail", "GET", "read"),
    McpOperation("tags.update", "Categorie e tag", "Modifica tag", "finance-tag-detail", "PATCH", "write"),
    McpOperation("tags.delete", "Categorie e tag", "Elimina tag", "finance-tag-detail", "DELETE", "write"),
    # Salvadanai
    McpOperation("savings.list", "Salvadanai", "Elenco salvadanai", "finance-savings", "GET", "read"),
    McpOperation("savings.create", "Salvadanai", "Crea salvadanaio", "finance-savings", "POST", "write"),
    McpOperation("savings.get", "Salvadanai", "Dettaglio salvadanaio", "finance-savings-detail", "GET", "read"),
    McpOperation("savings.update", "Salvadanai", "Modifica salvadanaio", "finance-savings-detail", "PATCH", "write"),
    McpOperation("savings.delete", "Salvadanai", "Elimina salvadanaio", "finance-savings-detail", "DELETE", "write"),
    # Investimenti
    McpOperation("investments.list", "Investimenti", "Elenco posizioni", "finance-investments", "GET", "read"),
    McpOperation("investments.open", "Investimenti", "Apri posizione", "finance-investments", "POST", "write"),
    McpOperation("investments.get", "Investimenti", "Dettaglio posizione", "finance-investment-detail", "GET", "read"),
    McpOperation("investments.update", "Investimenti", "Modifica posizione", "finance-investment-detail", "PATCH", "write"),
    McpOperation("investments.delete", "Investimenti", "Elimina posizione", "finance-investment-detail", "DELETE", "write"),
    McpOperation("investments.operations.create", "Investimenti", "Crea operazione", "finance-investment-operations", "POST", "write"),
    McpOperation("investments.operations.update", "Investimenti", "Modifica operazione", "finance-investment-operation-detail", "PATCH", "write"),
    McpOperation("investments.operations.delete", "Investimenti", "Elimina operazione", "finance-investment-operation-detail", "DELETE", "write"),
    McpOperation("investments.account.get", "Investimenti", "Leggi conto investimenti", "finance-investment-account", "GET", "read"),
    McpOperation("investments.account.update", "Investimenti", "Modifica conto investimenti", "finance-investment-account", "PATCH", "write"),
    McpOperation("investments.export", "Investimenti", "Esporta investimenti", "finance-investment-export", "GET", "read"),
    # Automazioni
    McpOperation("automations.list", "Automazioni", "Elenco automazioni", "finance-automations", "GET", "read"),
    McpOperation("automations.create", "Automazioni", "Crea automazione", "finance-automations", "POST", "write"),
    McpOperation("automations.get", "Automazioni", "Dettaglio automazione", "finance-automation-detail", "GET", "read"),
    McpOperation("automations.update", "Automazioni", "Modifica automazione", "finance-automation-detail", "PATCH", "write"),
    McpOperation("automations.delete", "Automazioni", "Elimina automazione", "finance-automation-detail", "DELETE", "write"),
    McpOperation("automations.run", "Automazioni", "Esegui automazione", "finance-automation-run", "POST", "write"),
    McpOperation("automations.run_all", "Automazioni", "Esegui tutte le automazioni", "finance-automations-run", "POST", "write"),
    McpOperation("automations.resolve", "Automazioni", "Risolvi occorrenze", "finance-automation-resolve", "POST", "write"),
    McpOperation("automations.executions", "Automazioni", "Storico esecuzioni", "finance-automation-executions", "GET", "read"),
    # Notifiche
    McpOperation("notifications.list", "Notifiche", "Elenco notifiche", "finance-notifications", "GET", "read"),
    McpOperation("notifications.read", "Notifiche", "Segna notifiche lette", "finance-notifications-read", "POST", "write"),
    # Import/Export
    McpOperation("export.transactions", "Import/Export", "Esporta movimenti", "finance-export", "GET", "read"),
    McpOperation("export.archive", "Import/Export", "Esporta archivio", "finance-export-archive", "GET", "read"),
    McpOperation("import.template", "Import/Export", "Scarica template CSV", "finance-import-template", "GET", "read"),
    McpOperation("import.analyze", "Import/Export", "Analizza CSV", "finance-import-analyze", "POST", "read"),
    McpOperation("import.confirm", "Import/Export", "Conferma import CSV", "finance-import-confirm", "POST", "write"),
    McpOperation("import.archive_analyze", "Import/Export", "Analizza archivio", "finance-import-archive-analyze", "POST", "read"),
    McpOperation("import.archive_confirm", "Import/Export", "Conferma import archivio", "finance-import-archive-confirm", "POST", "write"),
)

BY_ID = {operation.id: operation for operation in OPERATIONS}
BY_VIEW_METHOD = {
    (operation.view_name, operation.method): operation for operation in OPERATIONS
}


def resolve_operation(request) -> McpOperation | None:
    """Resolve the catalog operation from the actual route and HTTP method."""
    if not request.path.startswith("/api/v1/finance/"):
        return None
    match = getattr(request, "resolver_match", None)
    if match is None:
        return None
    return BY_VIEW_METHOD.get((match.url_name, request.method.upper()))


def catalog() -> list[dict]:
    """Grouped catalog for the settings UI."""
    groups: dict[str, list[dict]] = {}
    for operation in OPERATIONS:
        groups.setdefault(operation.area, []).append(
            {
                "id": operation.id,
                "label": operation.label,
                "kind": operation.kind,
            }
        )
    return [
        {"area": area, "operations": operations}
        for area, operations in groups.items()
    ]


def operations_with_paths() -> list[dict]:
    """Catalog enriched with concrete API paths for the MCP service."""
    result: list[dict] = []
    for operation in OPERATIONS:
        path = None
        needs_id = False
        for kwargs in ({}, {"pk": 1}):
            try:
                path = reverse(
                    f"v1-finance:{operation.view_name}", kwargs=kwargs
                )
            except NoReverseMatch:
                continue
            needs_id = bool(kwargs)
            break
        if path is None:
            continue
        if needs_id:
            path = path.replace("/1/", "/{id}/")
        result.append(
            {
                "id": operation.id,
                "area": operation.area,
                "label": operation.label,
                "kind": operation.kind,
                "method": operation.method,
                "path": path,
                "needs_id": needs_id,
                "tool_name": operation.id.replace(".", "_"),
            }
        )
    return result
