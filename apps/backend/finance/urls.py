from django.urls import path

from .export_views import ExportTransactionsView
from .import_views import (
    ImportAnalyzeView,
    ImportConfirmView,
    ImportTemplateView,
)
from .views import (
    AccountDetailView,
    AccountListCreateView,
    DashboardView,
    ProfileView,
    SavingsAccountDetailView,
    SavingsAccountListCreateView,
    TransactionDetailView,
    TransactionListCreateView,
)

urlpatterns = [
    path("profile/", ProfileView.as_view(), name="finance-profile"),
    path("dashboard/", DashboardView.as_view(), name="finance-dashboard"),
    path("accounts/", AccountListCreateView.as_view(), name="finance-accounts"),
    path(
        "accounts/<int:pk>/",
        AccountDetailView.as_view(),
        name="finance-account-detail",
    ),
    path("savings/", SavingsAccountListCreateView.as_view(), name="finance-savings"),
    path(
        "savings/<int:pk>/",
        SavingsAccountDetailView.as_view(),
        name="finance-savings-detail",
    ),
    path(
        "transactions/",
        TransactionListCreateView.as_view(),
        name="finance-transactions",
    ),
    path(
        "transactions/<int:pk>/",
        TransactionDetailView.as_view(),
        name="finance-transaction-detail",
    ),
    path(
        "export/",
        ExportTransactionsView.as_view(),
        name="finance-export",
    ),
    path(
        "import/template/",
        ImportTemplateView.as_view(),
        name="finance-import-template",
    ),
    path(
        "import/analyze/",
        ImportAnalyzeView.as_view(),
        name="finance-import-analyze",
    ),
    path(
        "import/confirm/",
        ImportConfirmView.as_view(),
        name="finance-import-confirm",
    ),
]
