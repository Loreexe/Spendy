from django.urls import path

from .views import (
    CsrfView,
    LoginView,
    LogoutView,
    MeView,
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
]
