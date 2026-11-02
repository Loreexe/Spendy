from django.urls import include, path

urlpatterns = [
    path("api/", include("core.urls")),
    path("api/auth/", include("accounts.auth_urls")),
    path("api/admin/", include("accounts.admin_urls")),
    path("api/finance/", include("finance.urls")),
]
