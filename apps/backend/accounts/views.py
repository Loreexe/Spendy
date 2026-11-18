import secrets
import time
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.sessions.models import Session
from django.contrib.auth.hashers import make_password
from django.contrib.auth.password_validation import validate_password
from django.core import signing
from django.core.cache import cache
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.net import get_client_ip, is_setup_address_allowed
from core.throttling import ClientIpScopedRateThrottle

from . import totp
from .audit import record_audit
from .mcp import catalog, operations_with_paths
from .mcp_control import read_state, state_path, write_state
from .models import (
    AuditEvent,
    DevicePairing,
    DeviceToken,
    GlobalSettings,
    McpToken,
    RecoveryCode,
    User,
)
from .permissions import IsGlobalAdmin
from .serializers import (
    AuditEventSerializer,
    McpPermissionsSerializer,
    McpServiceToggleSerializer,
    McpTokenCreateSerializer,
    McpTokenRevokeSerializer,
    McpTokenSerializer,
    DevicePairingSerializer,
    DeviceTokenRenameSerializer,
    DeviceTokenSerializer,
    GlobalSettingsSerializer,
    LoginSerializer,
    PairingClaimSerializer,
    PairingClaimTokenSerializer,
    PasswordChangeSerializer,
    ProfileUpdateSerializer,
    RegisterSerializer,
    SetupSerializer,
    TwoFactorConfirmSerializer,
    TwoFactorDisableSerializer,
    TwoFactorRecoveryCodesSerializer,
    TwoFactorVerifySerializer,
    UserSerializer,
)


def _login_lockout_key(request, identifier: str) -> str:
    client = get_client_ip(request)
    return f"login-lockout:{client or 'unknown'}:{identifier.strip().lower()}"


def _record_login_failure(key: str, attempts: int) -> int:
    attempts += 1
    cache.set(key, attempts, timeout=settings.LOGIN_LOCKOUT_SECONDS)
    return attempts


def _too_many_attempts_response() -> Response:
    response = Response(
        {
            "detail": "Troppi tentativi di accesso. Riprova più tardi.",
            "code": "too_many_attempts",
        },
        status=status.HTTP_429_TOO_MANY_REQUESTS,
    )
    response["Retry-After"] = str(settings.LOGIN_LOCKOUT_SECONDS)
    return response


# 2FA TOTP (DC-121): la sfida firmata vale 5 minuti e non crea la sessione
# finché il secondo fattore non è verificato.
TWO_FACTOR_CHALLENGE_SALT = "spendy-2fa-challenge"
TWO_FACTOR_CHALLENGE_MAX_AGE = 300
TWO_FACTOR_CODE_MIN_LENGTH = 6


def _issue_2fa_challenge(
    user: User,
    mode: str,
    identifier: str,
    device_name: str = "",
    platform: str = "android",
) -> str:
    return signing.dumps(
        {
            "uid": user.pk,
            "mode": mode,
            "identifier": identifier,
            "dn": device_name[:100],
            "pf": platform[:32],
        },
        salt=TWO_FACTOR_CHALLENGE_SALT,
        compress=True,
    )


def _load_2fa_challenge(raw: str) -> dict | None:
    try:
        payload = signing.loads(
            raw,
            salt=TWO_FACTOR_CHALLENGE_SALT,
            max_age=TWO_FACTOR_CHALLENGE_MAX_AGE,
        )
    except (signing.BadSignature, signing.SignatureExpired):
        return None
    if not isinstance(payload, dict) or not isinstance(payload.get("uid"), int):
        return None
    if payload.get("mode") not in {"session", "token"}:
        return None
    return payload


def _consume_second_factor(user: User, code: str) -> str | None:
    """Consume a TOTP code (with anti-replay) or a one-time recovery code."""
    candidate = (code or "").strip()
    if user.totp_secret:
        counter = totp.verify_code(user.totp_secret, candidate)
        if counter is not None:
            if (
                user.totp_last_counter is not None
                and counter <= user.totp_last_counter
            ):
                return None
            user.totp_last_counter = counter
            user.save(update_fields=["totp_last_counter"])
            return "totp"

    with transaction.atomic():
        recovery = (
            RecoveryCode.objects.select_for_update()
            .filter(
                user=user,
                code_hash=totp.hash_recovery_code(candidate),
                used_at__isnull=True,
            )
            .first()
        )
        if recovery is None:
            return None
        recovery.used_at = timezone.now()
        recovery.save(update_fields=["used_at"])
    return "recovery"


def _invalidate_other_sessions(user: User, current_session_key: str | None) -> int:
    """Elimina subito le altre sessioni web dell'utente.

    Django invalida già le sessioni al cambio password tramite l'hash di
    sessione; questa pulizia rende immediata la revoca e libera le righe.
    """
    deleted = 0
    for session in Session.objects.filter(
        expire_date__gte=timezone.now()
    ).iterator():
        data = session.get_decoded()
        if data.get("_auth_user_id") != str(user.pk):
            continue
        if current_session_key and session.session_key == current_session_key:
            continue
        session.delete()
        deleted += 1
    return deleted


def _mark_session_activity(request) -> None:
    request.session["last_activity"] = time.time()


def _other_session_count(user: User, current_session_key: str | None) -> int:
    count = 0
    for session in Session.objects.filter(
        expire_date__gte=timezone.now()
    ).iterator():
        data = session.get_decoded()
        if data.get("_auth_user_id") != str(user.pk):
            continue
        if current_session_key and session.session_key == current_session_key:
            continue
        count += 1
    return count


def _replace_recovery_codes(user: User) -> list[str]:
    plain_codes = totp.generate_recovery_codes()
    with transaction.atomic():
        RecoveryCode.objects.filter(user=user).delete()
        RecoveryCode.objects.bulk_create(
            [
                RecoveryCode(
                    user=user, code_hash=totp.hash_recovery_code(code)
                )
                for code in plain_codes
            ]
        )
    return plain_codes


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
        _mark_session_activity(request)
        record_audit(
            request, AuditEvent.Action.SETUP_COMPLETED, actor=admin
        )
        return Response({"user": UserSerializer(admin).data, "setup_completed": True})


class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes: list = []
    throttle_classes = [ClientIpScopedRateThrottle]
    throttle_scope = "login"
    create_session = True
    issue_token = False

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        identifier = serializer.validated_data["identifier"].strip()
        password = serializer.validated_data["password"]

        lockout_key = _login_lockout_key(request, identifier)
        attempts = cache.get(lockout_key, 0)
        if attempts >= settings.LOGIN_MAX_ATTEMPTS:
            return _too_many_attempts_response()

        user = (
            User.objects.filter(email__iexact=identifier).first()
            or User.objects.filter(username__iexact=identifier).first()
        )
        if user is None:
            User().set_password(password)  # mitigate timing attacks
            _record_login_failure(lockout_key, attempts)
            # Non registrare identificativi inesistenti: evita di riempire
            # l'audit con email casuali da tentativi automatizzati.
            return Response(
                {"detail": "Credenziali non valide.", "code": "invalid_credentials"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not user.check_password(password):
            _record_login_failure(lockout_key, attempts)
            record_audit(
                request,
                AuditEvent.Action.LOGIN_FAILED,
                actor=user,
                metadata={"reason": "invalid_password"},
            )
            return Response(
                {"detail": "Credenziali non valide.", "code": "invalid_credentials"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if user.status != User.Status.ACTIVE:
            _record_login_failure(lockout_key, attempts)
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
            record_audit(
                request,
                AuditEvent.Action.LOGIN_FAILED,
                actor=user,
                metadata={"reason": code},
            )
            return Response({"detail": detail, "code": code}, status=status.HTTP_403_FORBIDDEN)

        if self.issue_token and user.is_global_admin:
            return Response(
                {
                    "detail": "L'amministratore globale usa il pannello web.",
                    "code": "admin_uses_web",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if user.has_2fa:
            return Response(
                {
                    "two_factor_required": True,
                    "challenge": _issue_2fa_challenge(
                        user,
                        "session" if self.create_session else "token",
                        identifier,
                        serializer.validated_data.get("device_name", ""),
                        serializer.validated_data.get("platform") or "android",
                    ),
                    "detail": "Inserisci il codice di verifica a due fattori.",
                }
            )

        cache.delete(lockout_key)
        if self.create_session:
            login(request, user, backend="accounts.backends.EmailOrUsernameBackend")
            _mark_session_activity(request)
            record_audit(
                request, AuditEvent.Action.LOGIN_SUCCESS, actor=user
            )

        payload = {"user": UserSerializer(user).data}
        if self.issue_token:
            token, raw_key = DeviceToken.issue(
                user,
                name=serializer.validated_data.get("device_name", ""),
                platform=serializer.validated_data.get("platform", "android"),
            )
            record_audit(
                request,
                AuditEvent.Action.TOKEN_LOGIN,
                actor=user,
                target=token.name,
                metadata={"platform": token.platform},
            )
            payload.update(
                {
                    "token": raw_key,
                    "token_type": "Bearer",
                    "device": DeviceTokenSerializer(token).data,
                }
            )
        return Response(payload)


class TokenLoginView(LoginView):
    """Login per l'app nativa: restituisce un token senza creare una sessione."""

    create_session = False
    issue_token = True


class TokenLogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        token = request.auth
        if isinstance(token, DeviceToken):
            token.revoke()
        if getattr(request, "session", None) and request.session.session_key:
            logout(request)
        return Response({"detail": "Dispositivo disconnesso."})


class TwoFactorVerifyView(APIView):
    """Secondo fattore dopo la password: apre la sessione o emette il token."""

    permission_classes = [AllowAny]
    authentication_classes: list = []
    throttle_classes = [ClientIpScopedRateThrottle]
    throttle_scope = "two_factor"

    def post(self, request):
        serializer = TwoFactorVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = _load_2fa_challenge(serializer.validated_data["challenge"])
        if payload is None:
            record_audit(
                request,
                AuditEvent.Action.TWO_FACTOR_FAILED,
                metadata={"reason": "invalid_challenge"},
            )
            return Response(
                {
                    "detail": "Sfida scaduta o non valida. Accedi di nuovo.",
                    "code": "invalid_challenge",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        user = User.objects.filter(pk=payload["uid"]).first()
        if user is None or not user.is_active or not user.has_2fa:
            return Response(
                {
                    "detail": "Verifica a due fattori non disponibile.",
                    "code": "two_factor_unavailable",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if _consume_second_factor(user, serializer.validated_data["code"]) is None:
            record_audit(
                request,
                AuditEvent.Action.TWO_FACTOR_FAILED,
                actor=user,
                metadata={"reason": "invalid_code", "mode": payload["mode"]},
            )
            return Response(
                {"detail": "Codice non valido.", "code": "invalid_code"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        record_audit(
            request,
            AuditEvent.Action.TWO_FACTOR_VERIFIED,
            actor=user,
            metadata={"mode": payload["mode"]},
        )
        cache.delete(
            _login_lockout_key(request, payload.get("identifier", ""))
        )
        if payload["mode"] == "session":
            login(request, user, backend="accounts.backends.EmailOrUsernameBackend")
            _mark_session_activity(request)
            record_audit(
                request,
                AuditEvent.Action.LOGIN_SUCCESS,
                actor=user,
                metadata={"two_factor": True},
            )
            return Response({"user": UserSerializer(user).data})

        token, raw_key = DeviceToken.issue(
            user,
            name=payload.get("dn", ""),
            platform=payload.get("pf") or "android",
        )
        record_audit(
            request,
            AuditEvent.Action.TOKEN_LOGIN,
            actor=user,
            target=token.name,
            metadata={"platform": token.platform, "two_factor": True},
        )
        return Response(
            {
                "user": UserSerializer(user).data,
                "token": raw_key,
                "token_type": "Bearer",
                "device": DeviceTokenSerializer(token).data,
            }
        )


class TwoFactorStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response(
            {
                "enabled": user.has_2fa,
                "confirmed_at": user.totp_confirmed_at,
                "recovery_codes_remaining": user.recovery_codes.filter(
                    used_at__isnull=True
                ).count(),
                "issuer": totp.ISSUER,
                "digits": totp.DIGITS,
                "period": totp.PERIOD_SECONDS,
            }
        )


class TwoFactorSetupView(APIView):
    """Genera un nuovo segreto TOTP; non attiva la 2FA prima della conferma."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        if user.has_2fa:
            return Response(
                {
                    "detail": "La verifica a due fattori è già attiva.",
                    "code": "two_factor_already_enabled",
                },
                status=status.HTTP_409_CONFLICT,
            )
        secret = totp.generate_secret()
        user.totp_secret = secret
        user.totp_enabled = False
        user.totp_confirmed_at = None
        user.totp_last_counter = None
        user.save(
            update_fields=[
                "totp_secret",
                "totp_enabled",
                "totp_confirmed_at",
                "totp_last_counter",
            ]
        )
        record_audit(
            request, AuditEvent.Action.TWO_FACTOR_SETUP, actor=user
        )
        account_name = user.username or user.email or f"utente-{user.pk}"
        return Response(
            {
                "secret": secret,
                "otpauth_uri": totp.provisioning_uri(secret, account_name),
                "issuer": totp.ISSUER,
                "digits": totp.DIGITS,
                "period": totp.PERIOD_SECONDS,
            }
        )


class TwoFactorConfirmView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        if user.has_2fa:
            return Response(
                {
                    "detail": "La verifica a due fattori è già attiva.",
                    "code": "two_factor_already_enabled",
                },
                status=status.HTTP_409_CONFLICT,
            )
        if not user.totp_secret:
            return Response(
                {
                    "detail": "Avvia prima la configurazione.",
                    "code": "two_factor_setup_required",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = TwoFactorConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        counter = totp.verify_code(
            user.totp_secret, serializer.validated_data["code"]
        )
        if counter is None:
            record_audit(
                request,
                AuditEvent.Action.TWO_FACTOR_FAILED,
                actor=user,
                metadata={"reason": "confirm_invalid_code"},
            )
            return Response(
                {"detail": "Codice non valido.", "code": "invalid_code"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.totp_enabled = True
        user.totp_confirmed_at = timezone.now()
        user.totp_last_counter = counter
        user.save(
            update_fields=[
                "totp_enabled",
                "totp_confirmed_at",
                "totp_last_counter",
            ]
        )
        plain_codes = _replace_recovery_codes(user)
        record_audit(
            request, AuditEvent.Action.TWO_FACTOR_ENABLED, actor=user
        )
        return Response({"enabled": True, "recovery_codes": plain_codes})


class TwoFactorDisableView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        if not user.has_2fa:
            return Response(
                {
                    "detail": "La verifica a due fattori non è attiva.",
                    "code": "two_factor_not_enabled",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = TwoFactorDisableSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not user.check_password(serializer.validated_data["password"]):
            return Response(
                {
                    "detail": "La password attuale non è corretta.",
                    "code": "invalid_password",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if _consume_second_factor(user, serializer.validated_data["code"]) is None:
            return Response(
                {"detail": "Codice non valido.", "code": "invalid_code"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.totp_secret = ""
        user.totp_enabled = False
        user.totp_confirmed_at = None
        user.totp_last_counter = None
        user.save(
            update_fields=[
                "totp_secret",
                "totp_enabled",
                "totp_confirmed_at",
                "totp_last_counter",
            ]
        )
        user.recovery_codes.all().delete()
        record_audit(
            request, AuditEvent.Action.TWO_FACTOR_DISABLED, actor=user
        )
        return Response({"enabled": False, "detail": "2FA disattivata."})


class TwoFactorRecoveryCodesView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        if not user.has_2fa:
            return Response(
                {
                    "detail": "La verifica a due fattori non è attiva.",
                    "code": "two_factor_not_enabled",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = TwoFactorRecoveryCodesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not user.check_password(serializer.validated_data["password"]):
            return Response(
                {
                    "detail": "La password attuale non è corretta.",
                    "code": "invalid_password",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if _consume_second_factor(user, serializer.validated_data["code"]) is None:
            return Response(
                {"detail": "Codice non valido.", "code": "invalid_code"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        plain_codes = _replace_recovery_codes(user)
        record_audit(
            request, AuditEvent.Action.RECOVERY_CODES, actor=user
        )
        return Response({"recovery_codes": plain_codes})


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response({"detail": "Sessione terminata."})


class SessionInfoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        current = (
            request.session.session_key
            if getattr(request, "session", None)
            else None
        )
        return Response(
            {
                "session_cookie_age": settings.SESSION_COOKIE_AGE,
                "idle_timeout": settings.SESSION_IDLE_TIMEOUT_SECONDS,
                "other_sessions": _other_session_count(request.user, current),
            }
        )


class SessionRevokeOthersView(APIView):
    """Termina tutte le altre sessioni web dell'utente."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        current = (
            request.session.session_key
            if getattr(request, "session", None)
            else None
        )
        revoked = _invalidate_other_sessions(request.user, current)
        record_audit(
            request,
            AuditEvent.Action.SESSIONS_REVOKED,
            actor=request.user,
            metadata={"revoked": revoked},
        )
        return Response({"revoked_sessions": revoked})


class McpPublicCatalogView(APIView):
    """Catalogo con method/path per il servizio MCP (nessun dato utente)."""

    permission_classes = [AllowAny]
    authentication_classes: list = []

    def get(self, request):
        client = get_client_ip(request)
        if client is None or not (client.is_private or client.is_loopback):
            return Response(
                {"detail": "Catalogo MCP disponibile solo dalla rete interna."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return Response({"operations": operations_with_paths()})


class McpContextView(APIView):
    """Contesto del token MCP: permessi abilitati per filtrare tools/list."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        token = getattr(request.auth, "name", "")
        permissions = getattr(request.auth, "permissions", {}) or {}
        return Response(
            {
                "name": token,
                "permissions": permissions,
                "operations": [
                    operation["id"]
                    for operation in operations_with_paths()
                ],
            }
        )


class McpCatalogView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"areas": catalog()})


class McpTokenListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        tokens = request.user.mcp_tokens.all()
        return Response(
            {"tokens": McpTokenSerializer(tokens, many=True).data}
        )

    def post(self, request):
        user = request.user
        if user.is_global_admin:
            return Response(
                {
                    "detail": "L'amministratore globale non ha un profilo per i token MCP."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = McpTokenCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not user.check_password(serializer.validated_data["password"]):
            return Response(
                {
                    "detail": "La password attuale non è corretta.",
                    "code": "invalid_password",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        token, raw_key = McpToken.issue(
            user, serializer.validated_data["name"]
        )
        record_audit(
            request,
            AuditEvent.Action.MCP_TOKEN_CREATED,
            actor=user,
            target=token.name,
        )
        return Response(
            {
                "token": raw_key,
                "token_data": McpTokenSerializer(token).data,
            },
            status=status.HTTP_201_CREATED,
        )


class McpTokenDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get(self, request, token_id: int) -> McpToken:
        return get_object_or_404(request.user.mcp_tokens, pk=token_id)

    def get(self, request, token_id: int):
        return Response(McpTokenSerializer(self._get(request, token_id)).data)

    def patch(self, request, token_id: int):
        token = self._get(request, token_id)
        if not token.is_active:
            return Response(
                {"detail": "Il token è revocato."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = McpPermissionsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not request.user.check_password(
            serializer.validated_data["password"]
        ):
            return Response(
                {
                    "detail": "La password attuale non è corretta.",
                    "code": "invalid_password",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        token.permissions = serializer.validated_data["permissions"]
        token.save(update_fields=["permissions"])
        record_audit(
            request,
            AuditEvent.Action.MCP_PERMISSIONS_CHANGED,
            actor=request.user,
            target=token.name,
            metadata={"enabled": len(token.permissions)},
        )
        return Response(McpTokenSerializer(token).data)


class McpTokenRevokeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, token_id: int):
        token = get_object_or_404(
            request.user.mcp_tokens, pk=token_id
        )
        serializer = McpTokenRevokeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not request.user.check_password(
            serializer.validated_data["password"]
        ):
            return Response(
                {
                    "detail": "La password attuale non è corretta.",
                    "code": "invalid_password",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        token.revoke()
        record_audit(
            request,
            AuditEvent.Action.MCP_TOKEN_REVOKED,
            actor=request.user,
            target=token.name,
        )
        return Response(McpTokenSerializer(token).data)


class AdminMcpStatusView(APIView):
    permission_classes = [IsGlobalAdmin]

    def get(self, request):
        state = read_state()
        return Response(
            {
                "enabled": state["enabled"],
                "active_tokens": McpToken.objects.filter(
                    revoked_at__isnull=True
                ).count(),
                "control_file": str(state_path()),
            }
        )


class AdminMcpToggleView(APIView):
    permission_classes = [IsGlobalAdmin]

    def post(self, request):
        serializer = McpServiceToggleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        enabled = serializer.validated_data["enabled"]
        state = write_state(enabled)
        record_audit(
            request,
            AuditEvent.Action.MCP_SERVICE_TOGGLE,
            actor=request.user,
            metadata={"enabled": enabled},
        )
        return Response(
            {
                "enabled": state["enabled"],
                "active_tokens": McpToken.objects.filter(
                    revoked_at__isnull=True
                ).count(),
            }
        )


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
        if "username" in serializer.validated_data:
            if user.is_global_admin:
                return Response(
                    {
                        "username": [
                            "Il nome utente dell'amministratore globale non è modificabile."
                        ]
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            user.username = serializer.validated_data["username"] or None
            user.save(update_fields=["username", "updated_at"])
        name_fields = [
            field
            for field in ("first_name", "last_name")
            if field in serializer.validated_data
        ]
        if name_fields:
            for field in name_fields:
                setattr(
                    user, field, serializer.validated_data[field].strip()
                )
            user.save(update_fields=[*name_fields, "updated_at"])
        return Response({"user": UserSerializer(user).data})


AVATAR_TYPES = {"image/png", "image/jpeg", "image/webp"}
MAX_AVATAR_BYTES = 300 * 1024


class AvatarView(APIView):
    """Avatar stored in the database: survives backups with no extra media volume."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if not user.avatar:
            return Response(status=status.HTTP_404_NOT_FOUND)
        response = HttpResponse(
            bytes(user.avatar),
            content_type=user.avatar_content_type or "image/png",
        )
        response["Cache-Control"] = "private, max-age=86400"
        return response

    def post(self, request):
        upload = request.FILES.get("avatar")
        if upload is None:
            return Response(
                {"avatar": ["Scegli un'immagine."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        content_type = (upload.content_type or "").lower()
        if content_type not in AVATAR_TYPES:
            return Response(
                {"avatar": ["Formato non supportato: usa PNG, JPEG o WebP."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if upload.size > MAX_AVATAR_BYTES:
            return Response(
                {"avatar": ["L'immagine supera i 300 KB."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user = request.user
        user.avatar = upload.read()
        user.avatar_content_type = content_type
        user.avatar_updated_at = timezone.now()
        user.save(
            update_fields=[
                "avatar",
                "avatar_content_type",
                "avatar_updated_at",
                "updated_at",
            ]
        )
        return Response({"user": UserSerializer(user).data})

    def delete(self, request):
        user = request.user
        user.avatar = None
        user.avatar_content_type = ""
        user.avatar_updated_at = None
        user.save(
            update_fields=[
                "avatar",
                "avatar_content_type",
                "avatar_updated_at",
                "updated_at",
            ]
        )
        return Response({"user": UserSerializer(user).data})


class PasswordChangeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PasswordChangeSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        user = request.user
        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password", "updated_at"])
        if _current_token(request) is None:
            update_session_auth_hash(request, user)

        current_session_key = (
            request.session.session_key
            if getattr(request, "session", None)
            else None
        )
        revoked_sessions = _invalidate_other_sessions(user, current_session_key)
        request.session["last_activity"] = time.time()
        record_audit(
            request,
            AuditEvent.Action.PASSWORD_CHANGED,
            actor=user,
            metadata={"revoked_sessions": revoked_sessions},
        )

        revoked = 0
        if request.data.get("revoke_other_devices") in {True, "true", "1", 1}:
            tokens = user.device_tokens.filter(revoked_at__isnull=True)
            current = _current_token(request)
            if current is not None:
                tokens = tokens.exclude(pk=current.pk)
            revoked = tokens.count()
            tokens.update(revoked_at=timezone.now())
        return Response(
            {
                "detail": "Password aggiornata.",
                "revoked_devices": revoked,
                "revoked_sessions": revoked_sessions,
            }
        )


class RegisterView(APIView):
    permission_classes = [AllowAny]
    authentication_classes: list = []
    throttle_classes = [ClientIpScopedRateThrottle]
    throttle_scope = "register"

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        pending = (
            GlobalSettings.load().registration_mode
            != GlobalSettings.RegistrationMode.OPEN
        )
        email = serializer.validated_data["email"]
        # Un'email già registrata riceve la stessa risposta di una nuova
        # registrazione, senza creare un account: la registrazione non deve
        # consentire l'enumerazione degli account (BUG-007).
        if User.objects.filter(email__iexact=email).exists():
            # Calcola comunque un hash: evita che la risposta per un'email già
            # presente sia riconoscibile dai tempi di risposta.
            make_password(serializer.validated_data["password"])
            return self._response(pending)
        try:
            with transaction.atomic():
                user = serializer.save()
        except IntegrityError:
            # Duplicato inserito tra il controllo e il salvataggio.
            return self._response(pending)
        return self._response(user.status == User.Status.PENDING)

    @staticmethod
    def _response(pending: bool) -> Response:
        return Response(
            {
                "pending": pending,
                "detail": (
                    "Registrazione completata: l'account è in attesa di approvazione."
                    if pending
                    else "Registrazione completata: puoi accedere."
                ),
            },
            status=status.HTTP_201_CREATED,
        )


class AdminAuditView(APIView):
    """Ultimi eventi di audit, in sola lettura (admin globale)."""

    permission_classes = [IsGlobalAdmin]

    def get(self, request):
        try:
            limit = int(request.query_params.get("limit", "100"))
        except (TypeError, ValueError):
            limit = 100
        limit = max(1, min(limit, 200))
        events = AuditEvent.objects.select_related("actor")
        action = request.query_params.get("action", "").strip()
        if action:
            events = events.filter(action=action)
        return Response(
            {
                "events": [
                    AuditEventSerializer(event).data
                    for event in events[:limit]
                ]
            }
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
        record_audit(
            request,
            AuditEvent.Action.ADMIN_APPROVE
            if decision == "approve"
            else AuditEvent.Action.ADMIN_REJECT,
            actor=request.user,
            target=user.email or user.username or str(user.pk),
        )
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
        record_audit(
            request,
            AuditEvent.Action.ADMIN_SETTINGS,
            actor=request.user,
            metadata={
                "fields": sorted(serializer.validated_data.keys())
            },
        )
        return Response(serializer.data)


def _current_token(request) -> DeviceToken | None:
    token = getattr(request, "auth", None)
    return token if isinstance(token, DeviceToken) else None


def _pairing_origin_matches(request, pairing: DevicePairing) -> bool:
    token = _current_token(request)
    if pairing.origin_token_id:
        return token is not None and token.pk == pairing.origin_token_id
    if pairing.origin_session_key:
        session_key = getattr(request.session, "session_key", None)
        return bool(session_key) and session_key == pairing.origin_session_key
    return False


def _mark_expired(pairing: DevicePairing) -> None:
    if pairing.status not in {
        DevicePairing.Status.CONSUMED,
        DevicePairing.Status.REJECTED,
        DevicePairing.Status.EXPIRED,
    }:
        pairing.status = DevicePairing.Status.EXPIRED
        pairing.save(update_fields=["status"])


class DeviceListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        tokens = request.user.device_tokens.filter(revoked_at__isnull=True)
        return Response(
            {
                "devices": DeviceTokenSerializer(
                    tokens,
                    many=True,
                    context={"current_token_id": getattr(_current_token(request), "pk", None)},
                ).data
            }
        )


class DeviceDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get(self, request, device_id: int) -> DeviceToken:
        return get_object_or_404(request.user.device_tokens, pk=device_id)

    def patch(self, request, device_id: int):
        device = self._get(request, device_id)
        serializer = DeviceTokenRenameSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        device.name = serializer.validated_data["name"].strip()
        device.save(update_fields=["name"])
        return Response(
            DeviceTokenSerializer(
                device,
                context={"current_token_id": getattr(_current_token(request), "pk", None)},
            ).data
        )

    def delete(self, request, device_id: int):
        device = self._get(request, device_id)
        device.revoke()
        record_audit(
            request,
            AuditEvent.Action.DEVICE_REVOKED,
            actor=request.user,
            target=device.name or device.prefix,
            metadata={"platform": device.platform},
        )
        if _current_token(request) and _current_token(request).pk == device.pk:
            if getattr(request, "session", None) and request.session.session_key:
                logout(request)
        return Response({"detail": "Dispositivo revocato."})


class PairingListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        token = _current_token(request)
        session_key = getattr(request.session, "session_key", None)
        queryset = request.user.device_pairings.exclude(
            status__in=[
                DevicePairing.Status.CONSUMED,
                DevicePairing.Status.REJECTED,
                DevicePairing.Status.EXPIRED,
            ]
        )
        if token is not None:
            queryset = queryset.filter(origin_token=token)
        elif session_key:
            queryset = queryset.filter(origin_session_key=session_key)
        else:
            queryset = queryset.none()
        return Response({"pairings": DevicePairingSerializer(queryset, many=True).data})

    def post(self, request):
        token = _current_token(request)
        session_key = ""
        if token is None:
            if not request.session.session_key:
                request.session.save()
            session_key = request.session.session_key
        pairing, raw_code = DevicePairing.create(
            request.user,
            origin_token=token,
            origin_session_key=session_key,
        )
        server_url = request.build_absolute_uri("/").rstrip("/")
        return Response(
            {
                "pairing": DevicePairingSerializer(pairing).data,
                "code": raw_code,
                "server_url": server_url,
                "qr_payload": "spendy://pair?"
                + urlencode({"server": server_url, "code": raw_code}),
            },
            status=status.HTTP_201_CREATED,
        )


class PairingApproveView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pairing_id):
        pairing = get_object_or_404(
            request.user.device_pairings, pk=pairing_id
        )
        if not _pairing_origin_matches(request, pairing):
            return Response(
                {"detail": "Solo il dispositivo che ha generato il QR può approvare."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if pairing.is_expired:
            _mark_expired(pairing)
            return Response(
                {"detail": "Pairing scaduto.", "code": "pairing_expired"},
                status=status.HTTP_410_GONE,
            )
        if pairing.status != DevicePairing.Status.CLAIMED:
            return Response(
                {"detail": "Il pairing non è in attesa di approvazione."},
                status=status.HTTP_409_CONFLICT,
            )
        pairing.status = DevicePairing.Status.APPROVED
        pairing.approved_at = timezone.now()
        pairing.save(update_fields=["status", "approved_at"])
        record_audit(
            request,
            AuditEvent.Action.PAIRING_APPROVED,
            actor=request.user,
            target=str(pairing.pk),
            metadata={"device": pairing.new_device_name},
        )
        return Response(DevicePairingSerializer(pairing).data)


class PairingRejectView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pairing_id):
        pairing = get_object_or_404(
            request.user.device_pairings, pk=pairing_id
        )
        if not _pairing_origin_matches(request, pairing):
            return Response(
                {"detail": "Solo il dispositivo che ha generato il QR può rifiutare."},
                status=status.HTTP_403_FORBIDDEN,
            )
        pairing.status = DevicePairing.Status.REJECTED
        pairing.save(update_fields=["status"])
        record_audit(
            request,
            AuditEvent.Action.PAIRING_REJECTED,
            actor=request.user,
            target=str(pairing.pk),
        )
        return Response(DevicePairingSerializer(pairing).data)


class PairingClaimView(APIView):
    permission_classes = [AllowAny]
    authentication_classes: list = []
    throttle_classes = [ClientIpScopedRateThrottle]
    throttle_scope = "pairing"

    def post(self, request):
        serializer = PairingClaimSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        code = serializer.validated_data["code"].strip()
        pairing = DevicePairing.objects.filter(
            code_hash=DevicePairing.hash_code(code)
        ).first()
        if pairing is None:
            return Response(
                {"detail": "Codice di pairing non valido.", "code": "invalid_pairing"},
                status=status.HTTP_404_NOT_FOUND,
            )
        if pairing.is_expired:
            _mark_expired(pairing)
            return Response(
                {"detail": "Pairing scaduto.", "code": "pairing_expired"},
                status=status.HTTP_410_GONE,
            )
        if pairing.status != DevicePairing.Status.PENDING:
            return Response(
                {"detail": "Codice di pairing già utilizzato.", "code": "pairing_used"},
                status=status.HTTP_409_CONFLICT,
            )
        raw_claim = secrets.token_urlsafe(32)
        pairing.claim_hash = DevicePairing.hash_code(raw_claim)
        pairing.status = DevicePairing.Status.CLAIMED
        pairing.new_device_name = serializer.validated_data.get(
            "device_name", ""
        ).strip()[:100]
        pairing.new_device_platform = (
            serializer.validated_data.get("platform", "android").strip()[:32]
            or "android"
        )
        pairing.claimed_at = timezone.now()
        pairing.save(
            update_fields=[
                "claim_hash",
                "status",
                "new_device_name",
                "new_device_platform",
                "claimed_at",
            ]
        )
        return Response(
            {
                "pairing": DevicePairingSerializer(pairing).data,
                "claim_token": raw_claim,
            }
        )


class PairingStatusView(APIView):
    permission_classes = [AllowAny]
    authentication_classes: list = []

    def get(self, request, pairing_id):
        pairing = get_object_or_404(DevicePairing, pk=pairing_id)
        raw_claim = request.headers.get("X-Pairing-Claim", "")
        if not raw_claim or pairing.claim_hash != DevicePairing.hash_code(raw_claim):
            return Response(
                {"detail": "Claim non valido.", "code": "invalid_claim"},
                status=status.HTTP_403_FORBIDDEN,
            )
        if pairing.is_expired and pairing.status not in {
            DevicePairing.Status.CONSUMED,
            DevicePairing.Status.REJECTED,
            DevicePairing.Status.EXPIRED,
        }:
            _mark_expired(pairing)
        return Response(DevicePairingSerializer(pairing).data)


class PairingCompleteView(APIView):
    permission_classes = [AllowAny]
    authentication_classes: list = []
    throttle_classes = [ClientIpScopedRateThrottle]
    throttle_scope = "pairing"

    def post(self, request, pairing_id):
        pairing = get_object_or_404(DevicePairing, pk=pairing_id)
        raw_claim = request.headers.get("X-Pairing-Claim", "")
        if not raw_claim or pairing.claim_hash != DevicePairing.hash_code(raw_claim):
            return Response(
                {"detail": "Claim non valido.", "code": "invalid_claim"},
                status=status.HTTP_403_FORBIDDEN,
            )
        if pairing.is_expired:
            _mark_expired(pairing)
            return Response(
                {"detail": "Pairing scaduto.", "code": "pairing_expired"},
                status=status.HTTP_410_GONE,
            )
        if pairing.status == DevicePairing.Status.CONSUMED:
            return Response(
                {"detail": "Pairing già completato.", "code": "pairing_used"},
                status=status.HTTP_409_CONFLICT,
            )
        if pairing.status != DevicePairing.Status.APPROVED:
            return Response(
                {"detail": "Pairing non ancora approvato.", "code": "pairing_not_approved"},
                status=status.HTTP_409_CONFLICT,
            )
        token, raw_key = DeviceToken.issue(
            pairing.user,
            name=pairing.new_device_name,
            platform=pairing.new_device_platform or "android",
        )
        pairing.status = DevicePairing.Status.CONSUMED
        pairing.consumed_at = timezone.now()
        pairing.save(update_fields=["status", "consumed_at"])
        return Response(
            {
                "user": UserSerializer(pairing.user).data,
                "token": raw_key,
                "token_type": "Bearer",
                "device": DeviceTokenSerializer(token).data,
            },
            status=status.HTTP_201_CREATED,
        )


# Serializer hints for the OpenAPI schema (DC-103).
LoginView.serializer_class = LoginSerializer
TokenLoginView.serializer_class = LoginSerializer
MeView.serializer_class = UserSerializer
PasswordChangeView.serializer_class = PasswordChangeSerializer
RegisterView.serializer_class = RegisterSerializer
SetupView.serializer_class = SetupSerializer
DeviceListView.serializer_class = DeviceTokenSerializer
DeviceDetailView.serializer_class = DeviceTokenSerializer
PairingListCreateView.serializer_class = DevicePairingSerializer
PairingApproveView.serializer_class = DevicePairingSerializer
PairingRejectView.serializer_class = DevicePairingSerializer
PairingClaimView.serializer_class = PairingClaimSerializer
PairingStatusView.serializer_class = DevicePairingSerializer
PairingCompleteView.serializer_class = UserSerializer
