from django.urls import path

from .views import (
    AvatarView,
    CsrfView,
    DeviceDetailView,
    DeviceListView,
    LoginView,
    LogoutView,
    MeView,
    PairingApproveView,
    PairingClaimView,
    PairingCompleteView,
    PairingListCreateView,
    PairingRejectView,
    PairingStatusView,
    PasswordChangeView,
    RegisterView,
    SetupStatusView,
    SetupView,
)

urlpatterns = [
    path("csrf/", CsrfView.as_view(), name="auth-csrf"),
    path("setup-status/", SetupStatusView.as_view(), name="auth-setup-status"),
    path("setup/", SetupView.as_view(), name="auth-setup"),
    path("login/", LoginView.as_view(), name="auth-login"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("me/", MeView.as_view(), name="auth-me"),
    path("avatar/", AvatarView.as_view(), name="auth-avatar"),
    path("password/", PasswordChangeView.as_view(), name="auth-password"),
    path("devices/", DeviceListView.as_view(), name="auth-devices"),
    path(
        "devices/<int:device_id>/",
        DeviceDetailView.as_view(),
        name="auth-device-detail",
    ),
    path(
        "pairings/",
        PairingListCreateView.as_view(),
        name="auth-pairings",
    ),
    path(
        "pairings/claim/",
        PairingClaimView.as_view(),
        name="auth-pairing-claim",
    ),
    path(
        "pairings/<uuid:pairing_id>/approve/",
        PairingApproveView.as_view(),
        name="auth-pairing-approve",
    ),
    path(
        "pairings/<uuid:pairing_id>/reject/",
        PairingRejectView.as_view(),
        name="auth-pairing-reject",
    ),
    path(
        "pairings/<uuid:pairing_id>/status/",
        PairingStatusView.as_view(),
        name="auth-pairing-status",
    ),
    path(
        "pairings/<uuid:pairing_id>/complete/",
        PairingCompleteView.as_view(),
        name="auth-pairing-complete",
    ),
]
