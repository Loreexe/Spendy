import hashlib
import secrets
import uuid
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower
from django.utils import timezone


class UserManager(BaseUserManager):
    def create_user(self, email=None, password=None, **extra_fields):
        if email:
            email = self.normalize_email(email).lower()
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email=None, password=None, **extra_fields):
        extra_fields.setdefault("is_global_admin", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("status", User.Status.ACTIVE)
        return self.create_user(email=email, password=password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """Account of Spendy.

    A normal account authenticates with email/password and may link external
    identities later. The global administrator is the single account with
    ``is_global_admin=True``; it has no financial profile.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "In attesa di approvazione"
        ACTIVE = "active", "Attivo"
        REJECTED = "rejected", "Rifiutato"
        DISABLED = "disabled", "Disabilitato"

    username = models.CharField(max_length=150, null=True, blank=True, unique=True)
    email = models.EmailField(null=True, blank=True)
    first_name = models.CharField(max_length=80, blank=True)
    last_name = models.CharField(max_length=80, blank=True)
    avatar = models.BinaryField(null=True, blank=True)
    avatar_content_type = models.CharField(max_length=40, blank=True)
    avatar_updated_at = models.DateTimeField(null=True, blank=True)
    is_global_admin = models.BooleanField(default=False)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING
    )
    # 2FA TOTP (DC-121): il segreto è restituito solo durante il setup.
    totp_secret = models.CharField(max_length=64, blank=True, default="")
    totp_enabled = models.BooleanField(default=False)
    totp_confirmed_at = models.DateTimeField(null=True, blank=True)
    totp_last_counter = models.BigIntegerField(null=True, blank=True)
    date_joined = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS: list[str] = []

    objects = UserManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                Lower("email"),
                condition=Q(email__isnull=False),
                name="accounts_user_email_ci_unique",
            ),
            models.UniqueConstraint(
                Lower("username"),
                condition=Q(username__isnull=False),
                name="accounts_user_username_ci_unique",
            ),
            models.UniqueConstraint(
                fields=["is_global_admin"],
                condition=Q(is_global_admin=True),
                name="accounts_unique_global_admin",
            ),
            models.CheckConstraint(
                condition=Q(email__isnull=False) | Q(username__isnull=False),
                name="accounts_user_has_identifier",
            ),
        ]

    def __str__(self) -> str:
        return self.email or self.username or f"utente {self.pk}"

    @property
    def is_active(self) -> bool:  # type: ignore[override]
        return self.status == self.Status.ACTIVE

    @property
    def is_staff(self) -> bool:
        return self.is_global_admin

    def get_full_name(self) -> str:
        name = f"{self.first_name} {self.last_name}".strip()
        return name or self.email or self.username or ""

    def get_short_name(self) -> str:
        return self.first_name or self.get_full_name()

    @property
    def has_2fa(self) -> bool:
        return bool(self.totp_enabled and self.totp_secret)


class RecoveryCode(models.Model):
    """Codice di recupero monouso per la 2FA (DC-121)."""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="recovery_codes"
    )
    code_hash = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "code_hash"],
                name="accounts_recovery_code_unique",
            ),
        ]

    def __str__(self) -> str:
        return f"codice di recupero {self.pk} ({'usato' if self.used_at else 'attivo'})"


class AuditEvent(models.Model):
    """Registro append-only delle azioni sensibili (V05, Fase S).

    Non contiene password, token o dati finanziari: solo attore, azione,
    indirizzo IP, user agent e pochi metadati espliciti.
    """

    class Action(models.TextChoices):
        SETUP_COMPLETED = "setup_completed", "Setup amministratore completato"
        LOGIN_SUCCESS = "login_success", "Accesso riuscito"
        LOGIN_FAILED = "login_failed", "Accesso fallito"
        TOKEN_LOGIN = "token_login", "Accesso da dispositivo"
        TWO_FACTOR_VERIFIED = "2fa_verified", "Secondo fattore verificato"
        TWO_FACTOR_FAILED = "2fa_failed", "Secondo fattore fallito"
        TWO_FACTOR_SETUP = "2fa_setup", "Configurazione 2FA avviata"
        TWO_FACTOR_ENABLED = "2fa_enabled", "2FA attivata"
        TWO_FACTOR_DISABLED = "2fa_disabled", "2FA disattivata"
        RECOVERY_CODES = "2fa_recovery_codes", "Codici di recupero rigenerati"
        PASSWORD_CHANGED = "password_changed", "Password cambiata"
        ADMIN_APPROVE = "admin_approve", "Account approvato"
        ADMIN_REJECT = "admin_reject", "Account rifiutato"
        ADMIN_SETTINGS = "admin_settings", "Impostazioni globali modificate"
        DEVICE_REVOKED = "device_revoked", "Dispositivo revocato"
        PAIRING_APPROVED = "pairing_approved", "Pairing approvato"
        PAIRING_REJECTED = "pairing_rejected", "Pairing rifiutato"
        SESSIONS_REVOKED = "sessions_revoked", "Sessioni revocate"
        SESSION_EXPIRED = "session_expired", "Sessione scaduta"
        MCP_CALL = "mcp_call", "Chiamata MCP"
        MCP_TOKEN_CREATED = "mcp_token_created", "Token MCP creato"
        MCP_TOKEN_REVOKED = "mcp_token_revoked", "Token MCP revocato"
        MCP_PERMISSIONS_CHANGED = "mcp_permissions_changed", "Permessi MCP modificati"
        MCP_SERVICE_TOGGLE = "mcp_service_toggle", "Servizio MCP acceso/spento"

    actor = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_events",
    )
    action = models.CharField(
        max_length=40, choices=Action.choices, db_index=True
    )
    target = models.CharField(max_length=200, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.created_at:%Y-%m-%d %H:%M} {self.action}"


class McpToken(models.Model):
    """Token di un client MCP, con permessi per singola operazione (DC-123).

    Il valore in chiaro esiste solo nella risposta di creazione; il database
    conserva l'hash SHA-256 e i permessi espliciti (default deny).
    """

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="mcp_tokens"
    )
    name = models.CharField(max_length=100)
    prefix = models.CharField(max_length=12, db_index=True)
    key_hash = models.CharField(max_length=64, unique=True)
    permissions = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.name} ({self.prefix}…)"

    @staticmethod
    def hash_key(raw_key: str) -> str:
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    @classmethod
    def issue(cls, user: User, name: str):
        raw_key = "mcp_" + secrets.token_urlsafe(32)
        token = cls.objects.create(
            user=user,
            name=(name or "Client MCP").strip()[:100],
            prefix=raw_key[:12],
            key_hash=cls.hash_key(raw_key),
            permissions={},
        )
        return token, raw_key

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None

    def revoke(self) -> None:
        if self.revoked_at is None:
            self.revoked_at = timezone.now()
            self.save(update_fields=["revoked_at"])

    def permission_for(self, operation) -> str | None:
        level = (self.permissions or {}).get(operation.id)
        if operation.kind == "read":
            return level if level in {"read", "write"} else None
        return level if level == "write" else None


class ExternalIdentity(models.Model):
    """External identity (OIDC provider) linked to an account.

    The model is ready for the SSO milestone: no provider is enabled in the
    foundations. At least one active credential is enforced by the account
    service, not by deleting the last credential here.
    """

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="external_identities"
    )
    provider = models.CharField(max_length=64)
    subject = models.CharField(max_length=255)
    email = models.EmailField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "subject"],
                name="accounts_identity_provider_subject_unique",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.provider}:{self.subject}"


class GlobalSettings(models.Model):
    """Singleton with the global settings of the instance."""

    class RegistrationMode(models.TextChoices):
        APPROVAL = "approval", "Registrazione con approvazione"
        OPEN = "open", "Registrazione aperta"

    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    registration_mode = models.CharField(
        max_length=16,
        choices=RegistrationMode.choices,
        default=RegistrationMode.APPROVAL,
    )
    setup_completed = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "impostazioni globali"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls) -> "GlobalSettings":
        settings, _ = cls.objects.get_or_create(pk=1)
        return settings


class DeviceToken(models.Model):
    """Token permanente di un dispositivo, revocabile (DC-103).

    Il token in chiaro esiste solo nella risposta di login/completamento del
    pairing; il database conserva esclusivamente l'hash SHA-256.
    """

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="device_tokens"
    )
    name = models.CharField(max_length=100, blank=True)
    platform = models.CharField(max_length=32, default="android")
    prefix = models.CharField(max_length=12, db_index=True)
    key_hash = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.name or self.platform} ({self.prefix}…)"

    @staticmethod
    def hash_key(raw_key: str) -> str:
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    @classmethod
    def issue(cls, user: User, name: str = "", platform: str = "android"):
        raw_key = secrets.token_urlsafe(32)
        token = cls.objects.create(
            user=user,
            name=(name or "").strip()[:100],
            platform=(platform or "android").strip()[:32] or "android",
            prefix=raw_key[:8],
            key_hash=cls.hash_key(raw_key),
        )
        return token, raw_key

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None

    def revoke(self) -> None:
        if self.revoked_at is None:
            self.revoked_at = timezone.now()
            self.save(update_fields=["revoked_at"])


class DevicePairing(models.Model):
    """Pairing QR a token monouso, approvato sul dispositivo di origine."""

    class Status(models.TextChoices):
        PENDING = "pending", "In attesa di scansione"
        CLAIMED = "claimed", "In attesa di approvazione"
        APPROVED = "approved", "Approvato"
        CONSUMED = "consumed", "Completato"
        REJECTED = "rejected", "Rifiutato"
        EXPIRED = "expired", "Scaduto"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="device_pairings"
    )
    code_hash = models.CharField(max_length=64, unique=True)
    origin_token = models.ForeignKey(
        DeviceToken,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="pairings",
    )
    origin_session_key = models.CharField(max_length=40, blank=True)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING
    )
    new_device_name = models.CharField(max_length=100, blank=True)
    new_device_platform = models.CharField(max_length=32, blank=True)
    claim_hash = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    claimed_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    consumed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"pairing {self.pk} ({self.status})"

    @staticmethod
    def hash_code(raw_code: str) -> str:
        return hashlib.sha256(raw_code.encode("utf-8")).hexdigest()

    @classmethod
    def create(
        cls,
        user: User,
        origin_token: DeviceToken | None = None,
        origin_session_key: str = "",
    ):
        raw_code = secrets.token_urlsafe(24)
        pairing = cls.objects.create(
            user=user,
            code_hash=cls.hash_code(raw_code),
            origin_token=origin_token,
            origin_session_key=origin_session_key,
            expires_at=timezone.now()
            + timedelta(seconds=getattr(settings, "DEVICE_PAIRING_TTL_SECONDS", 300)),
        )
        return pairing, raw_code

    @property
    def is_expired(self) -> bool:
        return timezone.now() >= self.expires_at
