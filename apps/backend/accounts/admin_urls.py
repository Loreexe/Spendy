from django.urls import path

from .views import AdminSettingsView, AdminUserDecisionView, AdminUserListView

urlpatterns = [
    path("users/", AdminUserListView.as_view(), name="admin-users"),
    path(
        "users/<int:user_id>/<str:decision>/",
        AdminUserDecisionView.as_view(),
        name="admin-user-decision",
    ),
    path("settings/", AdminSettingsView.as_view(), name="admin-settings"),
]
