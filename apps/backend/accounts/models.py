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
