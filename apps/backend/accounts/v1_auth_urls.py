from django.urls import path

from .views import (
    AvatarView,
    CsrfView,
    DeviceDetailView,
    DeviceListView,
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
    TokenLoginView,
    TokenLogoutView,
)

urlpatterns = [
    path("csrf/", CsrfView.as_view(), name="csrf"),
    path("setup-status/", SetupStatusView.as_view(), name="setup-status"),
    path("setup/", SetupView.as_view(), name="setup"),
    path("login/", TokenLoginView.as_view(), name="login"),
    path("logout/", TokenLogoutView.as_view(), name="logout"),
    path("register/", RegisterView.as_view(), name="register"),
    path("me/", MeView.as_view(), name="me"),
    path("avatar/", AvatarView.as_view(), name="avatar"),
    path("password/", PasswordChangeView.as_view(), name="password"),
    path("devices/", DeviceListView.as_view(), name="devices"),
    path(
        "devices/<int:device_id>/",
        DeviceDetailView.as_view(),
        name="device-detail",
    ),
    path("pairings/", PairingListCreateView.as_view(), name="pairings"),
    path("pairings/claim/", PairingClaimView.as_view(), name="pairing-claim"),
    path(
        "pairings/<uuid:pairing_id>/approve/",
        PairingApproveView.as_view(),
        name="pairing-approve",
    ),
    path(
        "pairings/<uuid:pairing_id>/reject/",
        PairingRejectView.as_view(),
        name="pairing-reject",
    ),
    path(
        "pairings/<uuid:pairing_id>/status/",
        PairingStatusView.as_view(),
        name="pairing-status",
    ),
    path(
        "pairings/<uuid:pairing_id>/complete/",
        PairingCompleteView.as_view(),
        name="pairing-complete",
    ),
]
