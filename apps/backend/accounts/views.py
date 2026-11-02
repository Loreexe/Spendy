from django.contrib.auth import login, logout
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.net import get_client_ip, is_setup_address_allowed

from .models import GlobalSettings, User
from .permissions import IsGlobalAdmin
from .serializers import (
    GlobalSettingsSerializer,
    LoginSerializer,
    ProfileUpdateSerializer,
    RegisterSerializer,
    SetupSerializer,
    UserSerializer,
)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfView(APIView):
    permission_classes = [AllowAny]
    authentication_classes: list = []

    def get(self, request):
        return Response({"detail": "CSRF cookie impostato."})


class SetupStatusView(APIView):
    permission_classes = [AllowAny]
    authentication_classes: list = []

    def get(self, request):
        settings = GlobalSettings.load()
        private = is_setup_address_allowed(get_client_ip(request))
        return Response(
            {
                "setup_required": not settings.setup_completed,
                "can_setup": (not settings.setup_completed) and private,
                "client_is_private": private,
                "registration_mode": settings.registration_mode,
                "admin_username": "admin",
            }
        )


class SetupView(APIView):
    """Set the first password of the global administrator.

    Only available from the private network (localhost/Tailscale) and only
    until the setup has been completed; afterwards the endpoint is disabled.
    """

    permission_classes = [AllowAny]
    authentication_classes: list = []

    def post(self, request):
        settings = GlobalSettings.load()
        if settings.setup_completed:
            return Response(
                {"detail": "Il setup è già stato completato.", "code": "already_completed"},
                status=status.HTTP_409_CONFLICT,
            )
        if not is_setup_address_allowed(get_client_ip(request)):
            return Response(
                {
                    "detail": "Il setup è consentito solo da localhost o Tailscale.",
                    "code": "private_network_required",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        admin = User.objects.filter(is_global_admin=True).first()
        if admin is None:
            return Response(
                {"detail": "Amministratore globale non inizializzato."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        serializer = SetupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        password = serializer.validated_data["password"]
        try:
            validate_password(password, user=admin)
        except DjangoValidationError as exc:
            return Response(
                {"password": list(exc.messages)}, status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            admin.set_password(password)
            admin.status = User.Status.ACTIVE
            admin.save(update_fields=["password", "status", "updated_at"])
            settings.setup_completed = True
            settings.save(update_fields=["setup_completed", "updated_at"])

        login(request, admin, backend="accounts.backends.EmailOrUsernameBackend")
        return Response({"user": UserSerializer(admin).data, "setup_completed": True})


class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes: list = []

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        identifier = serializer.validated_data["identifier"].strip()
        password = serializer.validated_data["password"]

        user = (
            User.objects.filter(email__iexact=identifier).first()
            or User.objects.filter(username__iexact=identifier).first()
        )
        if user is None:
            User().set_password(password)  # mitigate timing attacks
            return Response(
                {"detail": "Credenziali non valide.", "code": "invalid_credentials"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not user.check_password(password):
            return Response(
                {"detail": "Credenziali non valide.", "code": "invalid_credentials"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if user.status != User.Status.ACTIVE:
            messages = {
                User.Status.PENDING: (
                    "Account in attesa di approvazione da parte dell'amministratore.",
                    "pending",
                ),
                User.Status.REJECTED: ("Account rifiutato.", "rejected"),
                User.Status.DISABLED: ("Account disabilitato.", "disabled"),
            }
            detail, code = messages.get(
                user.status, ("Account non attivo.", "inactive")
            )
            return Response({"detail": detail, "code": code}, status=status.HTTP_403_FORBIDDEN)

        login(request, user, backend="accounts.backends.EmailOrUsernameBackend")
        return Response({"user": UserSerializer(user).data})


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response({"detail": "Sessione terminata."})


class MeView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        user = request.user
        if not user or not user.is_authenticated:
            return Response({"user": None})
        return Response({"user": UserSerializer(user).data})

    def patch(self, request):
        user = request.user
        if not user or not user.is_authenticated:
            return Response(status=status.HTTP_403_FORBIDDEN)
        serializer = ProfileUpdateSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        if "email" in serializer.validated_data:
            email = serializer.validated_data["email"]
            if not email and not user.is_global_admin:
                return Response(
                    {"email": ["L'email è obbligatoria per un account normale."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            user.email = email or None
            user.save(update_fields=["email", "updated_at"])
        return Response({"user": UserSerializer(user).data})


class RegisterView(APIView):
    permission_classes = [AllowAny]
    authentication_classes: list = []

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {
                "user": UserSerializer(user).data,
                "pending": user.status == User.Status.PENDING,
                "detail": (
                    "Registrazione completata: l'account è in attesa di approvazione."
                    if user.status == User.Status.PENDING
                    else "Registrazione completata: puoi accedere."
                ),
            },
            status=status.HTTP_201_CREATED,
        )


class AdminUserListView(APIView):
    permission_classes = [IsGlobalAdmin]

    def get(self, request):
        queryset = User.objects.order_by("date_joined")
        status_filter = request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return Response({"users": UserSerializer(queryset, many=True).data})


class AdminUserDecisionView(APIView):
    permission_classes = [IsGlobalAdmin]

    def post(self, request, user_id: int, decision: str):
        user = get_object_or_404(User, pk=user_id)
        if user.is_global_admin:
            return Response(
                {"detail": "Non puoi modificare l'amministratore globale."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if decision == "approve":
            user.status = User.Status.ACTIVE
        elif decision == "reject":
            user.status = User.Status.REJECTED
        else:
            return Response(
                {"detail": "Decisione non valida."}, status=status.HTTP_400_BAD_REQUEST
            )
        user.save(update_fields=["status", "updated_at"])
        return Response({"user": UserSerializer(user).data})


class AdminSettingsView(APIView):
    permission_classes = [IsGlobalAdmin]

    def get(self, request):
        return Response(GlobalSettingsSerializer(GlobalSettings.load()).data)

    def patch(self, request):
        settings = GlobalSettings.load()
        serializer = GlobalSettingsSerializer(
            settings, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
