from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Q, Sum
from django.utils import timezone

ZERO = Decimal("0.00")


class Profile(models.Model):
    """Personal profile: exactly one per normal account (DC-013)."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="finance_profile",
    )
    display_name = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.display_name or self.user.get_full_name()


class Account(models.Model):
    class Type(models.TextChoices):
        CASH = "cash", "Contanti"
        CHECKING = "checking", "Conto corrente"
        CARD = "card", "Carta"
        OTHER = "other", "Altro"

    profile = models.ForeignKey(
        Profile, on_delete=models.CASCADE, related_name="accounts"
    )
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=16, choices=Type.choices, default=Type.OTHER)
    initial_balance = models.DecimalField(
        max_digits=12, decimal_places=2, default=ZERO
    )
    currency = models.CharField(max_length=3, default="EUR", editable=False)
    archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name", "id")

    def __str__(self) -> str:
        return self.name

    @property
    def balance(self) -> Decimal:
        return self.lines.aggregate(total=Sum("amount"))["total"] or ZERO


class SavingsAccount(models.Model):
    """Savings container with its own balance and a backing account (DC-011)."""

    profile = models.ForeignKey(
        Profile, on_delete=models.CASCADE, related_name="savings_accounts"
    )
    name = models.CharField(max_length=100)
    backing_account = models.ForeignKey(
        Account, on_delete=models.PROTECT, related_name="savings_accounts"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name", "id")

    def __str__(self) -> str:
        return self.name

    @property
    def balance(self) -> Decimal:
        return self.lines.aggregate(total=Sum("amount"))["total"] or ZERO


class Automation(models.Model):
    """Recurring rule: a savings transfer or an expense (DC-014, DC-080).

    Only temporal, periodic rules are implemented. The model stays generic so
    that conditional triggers can be added later without changing how
    occurrences and their snapshots are stored.
    """

    class Kind(models.TextChoices):
        TRANSFER = "transfer", "Versamento su salvadanaio"
        EXPENSE = "expense", "Spesa ricorrente"

    class Frequency(models.TextChoices):
        DAILY = "daily", "Ogni giorno"
        WEEKLY = "weekly", "Ogni settimana"
        MONTHLY = "monthly", "Ogni mese"
        YEARLY = "yearly", "Ogni anno"

    class Status(models.TextChoices):
        ACTIVE = "active", "Attiva"
        PAUSED = "paused", "In pausa"
        SUSPENDED = "suspended", "Sospesa"

    profile = models.ForeignKey(
        Profile, on_delete=models.CASCADE, related_name="automations"
    )
    kind = models.CharField(
        max_length=16, choices=Kind.choices, default=Kind.TRANSFER
    )
    savings = models.ForeignKey(
        SavingsAccount,
        on_delete=models.CASCADE,
        related_name="automations",
        null=True,
        blank=True,
    )
    source_account = models.ForeignKey(
        Account,
        on_delete=models.SET_NULL,
        related_name="automations",
        null=True,
        blank=True,
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.CharField(max_length=255, blank=True)
    frequency = models.CharField(
        max_length=16, choices=Frequency.choices, default=Frequency.MONTHLY
    )
    next_run_on = models.DateField()
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.ACTIVE
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("next_run_on", "id")
        constraints = [
            models.CheckConstraint(
                condition=Q(amount__gt=0),
                name="finance_automation_amount_positive",
            ),
            models.CheckConstraint(
                condition=(
                    Q(kind="transfer", savings__isnull=False)
                    | Q(kind="expense", savings__isnull=True)
                ),
                name="finance_automation_kind_target",
            ),
        ]

    def __str__(self) -> str:
        if self.kind == self.Kind.EXPENSE:
            return f"{self.amount} · {self.description or 'Spesa ricorrente'}"
        return f"{self.amount} → {self.savings} ({self.get_frequency_display()})"

    @property
    def is_active(self) -> bool:
        return self.status == self.Status.ACTIVE


class Transaction(models.Model):
    class Kind(models.TextChoices):
        OPENING = "opening", "Apertura"
        INCOME = "income", "Entrata"
        EXPENSE = "expense", "Spesa"
        TRANSFER = "transfer", "Trasferimento"

    profile = models.ForeignKey(
        Profile, on_delete=models.CASCADE, related_name="transactions"
    )
    automation = models.ForeignKey(
        Automation,
        on_delete=models.SET_NULL,
        related_name="transactions",
        null=True,
        blank=True,
    )
    kind = models.CharField(max_length=16, choices=Kind.choices)
    date = models.DateField()
    description = models.CharField(max_length=255, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-date", "-id")
        constraints = [
            models.CheckConstraint(
                condition=Q(amount__gt=0), name="finance_transaction_amount_positive"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.get_kind_display()} {self.amount}"


class Line(models.Model):
    """Signed movement on an account or savings container.

    A positive amount increases the balance, a negative amount decreases it.
    Internal transfers have lines that sum to zero; income/expense have the
    external side represented implicitly by the transaction kind.
    """

    class Role(models.TextChoices):
        PRINCIPAL = "principal", "Principale"
        TECHNICAL = "technical", "Tecnico"
        TRANSFER_OUT = "transfer_out", "Trasferimento in uscita"
        TRANSFER_IN = "transfer_in", "Trasferimento in entrata"

    transaction = models.ForeignKey(
        Transaction, on_delete=models.CASCADE, related_name="lines"
    )
    account = models.ForeignKey(
        Account, on_delete=models.CASCADE, related_name="lines", null=True, blank=True
    )
    savings = models.ForeignKey(
        SavingsAccount,
        on_delete=models.CASCADE,
        related_name="lines",
        null=True,
        blank=True,
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    role = models.CharField(
        max_length=16, choices=Role.choices, default=Role.PRINCIPAL
    )

    class Meta:
        ordering = ("id",)
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(account__isnull=False, savings__isnull=True)
                    | Q(account__isnull=True, savings__isnull=False)
                ),
                name="finance_line_exactly_one_target",
            ),
        ]

    def __str__(self) -> str:
        target = self.account or self.savings
        return f"{target} {self.amount}"


class AutomationExecution(models.Model):
    """One scheduled occurrence of a savings automation (DC-019/DC-020).

    The occurrence key is the rule id plus the original scheduled date. The
    rule reference is copied into ``automation_ref`` and the display fields are
    snapshots, so the execution history survives when the rule or the savings
    container is deleted (DC-017, OQ-AUT-10).
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Prevista"
        RUNNING = "running", "In corso"
        SUCCEEDED = "succeeded", "Riuscita"
        FAILED = "failed", "Fallita"
        SKIPPED = "skipped", "Saltata"
        CANCELLED = "cancelled", "Annullata"

    class FailureCode(models.TextChoices):
        INSUFFICIENT_BALANCE = "insufficient_balance", "Saldo insufficiente"
        MISSING_DATA = "missing_data", "Dato mancante"
        TECHNICAL_ERROR = "technical_error", "Errore tecnico"
        NOT_SELECTED = "not_selected", "Non selezionata"
        RULE_DELETED = "rule_deleted", "Regola eliminata"
        CANCELLED = "cancelled", "Annullata"

    automation = models.ForeignKey(
        Automation,
        on_delete=models.SET_NULL,
        related_name="executions",
        null=True,
        blank=True,
    )
    automation_ref = models.PositiveBigIntegerField(db_index=True)
    automation_name = models.CharField(max_length=255)
    kind = models.CharField(
        max_length=16,
        choices=Automation.Kind.choices,
        default=Automation.Kind.TRANSFER,
    )
    description = models.CharField(max_length=255, blank=True)
    profile = models.ForeignKey(
        Profile, on_delete=models.CASCADE, related_name="automation_executions"
    )
    scheduled_date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    source_account = models.ForeignKey(
        Account,
        on_delete=models.SET_NULL,
        related_name="automation_executions",
        null=True,
        blank=True,
    )
    source_account_name = models.CharField(max_length=100, blank=True)
    savings = models.ForeignKey(
        SavingsAccount,
        on_delete=models.SET_NULL,
        related_name="automation_executions",
        null=True,
        blank=True,
    )
    savings_name = models.CharField(max_length=100, blank=True)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING
    )
    attempts = models.PositiveSmallIntegerField(default=0)
    next_retry_at = models.DateTimeField(null=True, blank=True)
    failure_code = models.CharField(
        max_length=32, choices=FailureCode.choices, blank=True
    )
    failure_message = models.CharField(max_length=255, blank=True)
    corrected = models.BooleanField(default=False)
    transaction = models.OneToOneField(
        Transaction,
        on_delete=models.SET_NULL,
        related_name="automation_execution",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("scheduled_date", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("automation_ref", "scheduled_date"),
                name="finance_automation_occurrence_unique",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.automation_name} {self.scheduled_date} ({self.status})"


class Notification(models.Model):
    """In-app notification, used first for savings automation events."""

    class Kind(models.TextChoices):
        AUTOMATION_PENDING = "automation_pending", "Scelta da fare"
        AUTOMATION_SKIPPED = "automation_skipped", "Occorrenza saltata"
        AUTOMATION_SUSPENDED = "automation_suspended", "Automazione sospesa"

    profile = models.ForeignKey(
        Profile, on_delete=models.CASCADE, related_name="notifications"
    )
    automation = models.ForeignKey(
        Automation,
        on_delete=models.SET_NULL,
        related_name="notifications",
        null=True,
        blank=True,
    )
    execution = models.ForeignKey(
        AutomationExecution,
        on_delete=models.SET_NULL,
        related_name="notifications",
        null=True,
        blank=True,
    )
    kind = models.CharField(max_length=32, choices=Kind.choices)
    message = models.CharField(max_length=255)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at", "-id")

    def __str__(self) -> str:
        return self.message

    @property
    def is_read(self) -> bool:
        return self.read_at is not None

    def mark_read(self) -> None:
        if self.read_at is None:
            self.read_at = timezone.now()
            self.save(update_fields=("read_at",))
