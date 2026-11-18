from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from accounts.permissions import IsGlobalAdmin
from accounts.views import McpContextView, McpPublicCatalogView

urlpatterns = [
    path(
        "api/v1/schema/",
        SpectacularAPIView.as_view(permission_classes=[IsGlobalAdmin]),
        name="v1-schema",
    ),
    path(
        "api/v1/docs/",
        SpectacularSwaggerView.as_view(
            url_name="v1-schema", permission_classes=[IsGlobalAdmin]
        ),
        name="v1-docs",
    ),
    # Legacy web API (kept for the existing frontend).
    path("api/", include("core.urls")),
    path("api/auth/", include("accounts.auth_urls")),
    path("api/admin/", include("accounts.admin_urls")),
    path("api/finance/", include("finance.urls")),
    # Versioned API for the native client (DC-103).
    path("api/v1/", include(("core.urls", "core"), namespace="v1-core")),
    path(
        "api/v1/auth/",
        include(("accounts.v1_auth_urls", "auth"), namespace="v1-auth"),
    ),
    path(
        "api/v1/admin/",
        include(("accounts.admin_urls", "admin"), namespace="v1-admin"),
    ),
    path(
        "api/v1/finance/",
        include(("finance.urls", "finance"), namespace="v1-finance"),
    ),
    path("api/v1/mcp/catalog/", McpPublicCatalogView.as_view(), name="mcp-public-catalog"),
    path("api/v1/mcp/context/", McpContextView.as_view(), name="mcp-context"),
]
