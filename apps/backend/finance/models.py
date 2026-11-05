from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Q, Sum
from django.utils import timezone

ZERO = Decimal("0.00")

TRASH_RETENTION_DAYS = 30


class ActiveManager(models.Manager):
    """Default manager: hides soft-deleted rows (DC-088)."""

    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class SoftDeleteModel(models.Model):
    """Soft delete with 30-day retention: rows stay queryable via all_objects."""

    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True

    def soft_delete(self, user=None):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        if user is not None:
            self.deleted_by = user
        self.save(update_fields=("is_deleted", "deleted_at", "deleted_by"))

    def restore(self):
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
        self.save(update_fields=("is_deleted", "deleted_at", "deleted_by"))


class Profile(models.Model):
    """Personal profile: exactly one per normal account (DC-013)."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="finance_profile",
    )
    display_name = models.CharField(max_length=120, blank=True)
    theme = models.CharField(
        max_length=5,
        choices=[("dark", "Scuro"), ("light", "Chiaro")],
        default="dark",
    )
    investment_account = models.ForeignKey(
        "Account",
        on_delete=models.SET_NULL,
        related_name="investment_profiles",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.display_name or self.user.get_full_name()


class Category(SoftDeleteModel):
    """Movement category: one per transaction, preset or personal (DC-086)."""

    profile = models.ForeignKey(
        Profile, on_delete=models.CASCADE, related_name="categories"
    )
    name = models.CharField(max_length=60)
    is_preset = models.BooleanField(default=False)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("profile", "name"),
                condition=Q(is_deleted=False),
                name="finance_category_unique_name",
            ),
        ]

    def __str__(self) -> str:
        return self.name


DEFAULT_CATEGORIES = (
    "Altro",
    "Alimentari",
    "Casa e bollette",
    "Trasporti",
    "Salute",
    "Svago e tempo libero",
    "Shopping",
    "Lavoro e studio",
    "Risparmio",
)

DEFAULT_CATEGORY_NAME = "Altro"


def ensure_default_categories(profile: Profile) -> dict[str, Category]:
    """Create the preset categories (including default "Altro") if missing."""
    existing = {
        category.name: category
        for category in Category.objects.filter(profile=profile)
    }
    result = dict(existing)
    for name in DEFAULT_CATEGORIES:
        if name in result:
            continue
        result[name] = Category.objects.create(
            profile=profile,
            name=name,
            is_preset=True,
            is_default=(name == DEFAULT_CATEGORY_NAME),
        )
    default = result.get(DEFAULT_CATEGORY_NAME)
    if default is not None and not default.is_default:
        default.is_default = True
        default.save(update_fields=("is_default", "updated_at"))
    return result


class Tag(SoftDeleteModel):
    """Free-form movement label, unique per profile (DC-086)."""

    profile = models.ForeignKey(
        Profile, on_delete=models.CASCADE, related_name="tags"
    )
    name = models.CharField(max_length=30)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("profile", "name"),
                condition=Q(is_deleted=False),
                name="finance_tag_unique_name",
            ),
        ]

    def __str__(self) -> str:
        return self.name


MAX_TAGS_PER_TRANSACTION = 10


def normalize_tag_name(value: object) -> str:
    return str(value or "").strip()


def purge_trash() -> int:
    """Hard-delete soft-deleted rows older than the retention window."""
    from datetime import timedelta

    cutoff = timezone.now() - timedelta(days=TRASH_RETENTION_DAYS)
    removed = 0
    for model in (
        Transaction,
        Automation,
        InvestmentOperation,
        InvestmentPosition,
        SavingsAccount,
        Account,
        Category,
        Tag,
    ):
        for entry in model.all_objects.filter(
            is_deleted=True, deleted_at__lt=cutoff
        ):
            if isinstance(entry, Account) and (
                Transaction.all_objects.filter(lines__account=entry).exists()
                or Automation.all_objects.filter(
                    source_account=entry
                ).exists()
            ):
                continue
            entry.delete()
            removed += 1
    return removed
    return str(value or "").strip()


def resolve_tags(profile: Profile, names: list) -> list[Tag]:
    """Get-or-create tags for normalized names (max 10, empties dropped).

    Reusing the name of a trashed tag restores it.
    """
    seen: list[str] = []
    for raw in names or []:
        name = normalize_tag_name(raw)
        if not name or name in seen:
            continue
        seen.append(name)
        if len(seen) >= MAX_TAGS_PER_TRANSACTION:
            break
    resolved = []
    for name in seen:
        tag = (
            Tag.all_objects.filter(profile=profile, name=name)
            .order_by("is_deleted", "-id")
            .first()
        )
        if tag is None:
            tag = Tag.objects.create(profile=profile, name=name)
        elif tag.is_deleted:
            tag.restore()
        resolved.append(tag)
    return resolved


def match_category(profile: Profile, text: str) -> Category:
    """Match a free-text category to a profile category, else default."""
    wanted = (text or "").strip()
    if wanted:
        found = Category.objects.filter(
            profile=profile, name__iexact=wanted
        ).first()
        if found is not None:
            return found
    defaults = ensure_default_categories(profile)
    return defaults[DEFAULT_CATEGORY_NAME]


class Account(SoftDeleteModel):
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
        return (
            self.lines.filter(transaction__is_deleted=False).aggregate(
                total=Sum("amount")
            )["total"]
            or ZERO
        )


class SavingsAccount(SoftDeleteModel):
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
        return (
            self.lines.filter(transaction__is_deleted=False).aggregate(
                total=Sum("amount")
            )["total"]
            or ZERO
        )


class Automation(SoftDeleteModel):
    """Recurring rule: a savings transfer or an expense (DC-014, DC-080).

    Only temporal, periodic rules are implemented. The model stays generic so
    that conditional triggers can be added later without changing how
    occurrences and their snapshots are stored.
    """

    class Kind(models.TextChoices):
        TRANSFER = "transfer", "Versamento su salvadanaio"
        EXPENSE = "expense", "Spesa ricorrente"

    class IntervalUnit(models.TextChoices):
        DAY = "day", "Giorni"
        WEEK = "week", "Settimane"
        MONTH = "month", "Mesi"
        YEAR = "year", "Anni"

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
    interval_count = models.PositiveSmallIntegerField(default=1)
    interval_unit = models.CharField(
        max_length=8, choices=IntervalUnit.choices, default=IntervalUnit.MONTH
    )
    anchor_day = models.PositiveSmallIntegerField(default=1)
    advance_notice_days = models.PositiveSmallIntegerField(default=3)
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
            models.CheckConstraint(
                condition=Q(interval_count__gte=1),
                name="finance_automation_interval_count_positive",
            ),
            models.CheckConstraint(
                condition=Q(anchor_day__gte=1, anchor_day__lte=31),
                name="finance_automation_anchor_day_valid",
            ),
            models.CheckConstraint(
                condition=Q(advance_notice_days__lte=30),
                name="finance_automation_notice_days_valid",
            ),
        ]

    @property
    def interval_label(self) -> str:
        count = self.interval_count
        singular = {
            self.IntervalUnit.DAY: "giorno",
            self.IntervalUnit.WEEK: "settimana",
            self.IntervalUnit.MONTH: "mese",
            self.IntervalUnit.YEAR: "anno",
        }[self.interval_unit]
        if count == 1:
            return f"Ogni {singular}"
        plural = {
            self.IntervalUnit.DAY: "giorni",
            self.IntervalUnit.WEEK: "settimane",
            self.IntervalUnit.MONTH: "mesi",
            self.IntervalUnit.YEAR: "anni",
        }[self.interval_unit]
        return f"Ogni {count} {plural}"

    def __str__(self) -> str:
        if self.kind == self.Kind.EXPENSE:
            return f"{self.amount} · {self.description or 'Spesa ricorrente'}"
        return f"{self.amount} → {self.savings} ({self.interval_label})"

    @property
    def is_active(self) -> bool:
        return self.status == self.Status.ACTIVE


class Transaction(SoftDeleteModel):
    class Kind(models.TextChoices):
        OPENING = "opening", "Apertura"
        INCOME = "income", "Entrata"
        EXPENSE = "expense", "Spesa"
        TRANSFER = "transfer", "Trasferimento"
        INVESTMENT_BUY = "investment_buy", "Acquisto investimento"
        INVESTMENT_SELL = "investment_sell", "Vendita investimento"
        INVESTMENT_DIVIDEND = "investment_dividend", "Dividendo"

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
    kind = models.CharField(max_length=19, choices=Kind.choices)
    date = models.DateField()
    description = models.CharField(max_length=255, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="transactions",
    )
    tags = models.ManyToManyField(Tag, blank=True, related_name="transactions")
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
        AUTOMATION_LOW_BALANCE = "automation_low_balance", "Saldo previsto insufficiente"

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
    occurrence_date = models.DateField(null=True, blank=True)
    alert_date = models.DateField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at", "-id")
        constraints = [
            models.UniqueConstraint(
                fields=("automation", "kind", "occurrence_date", "alert_date"),
                name="finance_notification_alert_unique",
            ),
        ]

    def __str__(self) -> str:
        return self.message

    @property
    def is_read(self) -> bool:
        return self.read_at is not None

    def mark_read(self) -> None:
        if self.read_at is None:
            self.read_at = timezone.now()
            self.save(update_fields=("read_at",))


class InvestmentPosition(SoftDeleteModel):
    """A holding tracked by quantity and unit price (DC-082/DC-083).

    Derived values (quantity, cost, gains) are never stored: they are always
    rebuilt from the operations by ``finance.investments``.
    """

    class Category(models.TextChoices):
        STOCK = "stock", "Azione"
        ETF = "etf", "ETF"
        BOND = "bond", "Obbligazione"
        FUND = "fund", "Fondo"
        CRYPTO = "crypto", "Crypto"
        REAL_ESTATE = "real_estate", "Immobile"
        OTHER = "other", "Altro"

    profile = models.ForeignKey(
        Profile, on_delete=models.CASCADE, related_name="investment_positions"
    )
    name = models.CharField(max_length=120)
    category = models.CharField(
        max_length=16, choices=Category.choices, blank=True
    )
    identifier = models.CharField(max_length=32, blank=True)
    current_price = models.DecimalField(
        max_digits=18, decimal_places=8, null=True, blank=True
    )
    price_updated_on = models.DateField(null=True, blank=True)
    archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name", "id")

    def __str__(self) -> str:
        return self.name


class InvestmentOperation(SoftDeleteModel):
    """One movement of an investment position.

    ``cash_amount`` is the signed source of truth for the account movement:
    always positive, with the direction given by the kind.
    """

    class Kind(models.TextChoices):
        OPENING = "opening", "Apertura"
        BUY = "buy", "Acquisto"
        SELL = "sell", "Vendita"
        DIVIDEND = "dividend", "Dividendo"

    profile = models.ForeignKey(
        Profile, on_delete=models.CASCADE, related_name="investment_operations"
    )
    position = models.ForeignKey(
        InvestmentPosition, on_delete=models.PROTECT, related_name="operations"
    )
    kind = models.CharField(max_length=16, choices=Kind.choices)
    date = models.DateField()
    quantity = models.DecimalField(
        max_digits=24, decimal_places=8, null=True, blank=True
    )
    unit_price = models.DecimalField(
        max_digits=24, decimal_places=8, null=True, blank=True
    )
    gross_amount = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    commission = models.DecimalField(
        max_digits=12, decimal_places=2, default=ZERO
    )
    cash_amount = models.DecimalField(max_digits=14, decimal_places=2, default=ZERO)
    description = models.CharField(max_length=255, blank=True)
    transaction = models.OneToOneField(
        Transaction,
        on_delete=models.PROTECT,
        related_name="investment_operation",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("date", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("position",),
                condition=Q(kind="opening"),
                name="finance_investment_one_opening_per_position",
            ),
            models.CheckConstraint(
                condition=Q(cash_amount__gte=0),
                name="finance_investment_cash_non_negative",
            ),
            models.CheckConstraint(
                condition=(
                    Q(kind="opening", transaction__isnull=True)
                    | (~Q(kind="opening") & Q(transaction__isnull=False))
                ),
                name="finance_investment_transaction_matches_kind",
            ),
            models.CheckConstraint(
                condition=(
                    Q(kind="opening", cash_amount=0, commission=0)
                    | ~Q(kind="opening")
                ),
                name="finance_investment_opening_has_no_cash",
            ),
            models.CheckConstraint(
                condition=(
                    Q(kind="dividend", quantity__isnull=True, unit_price__isnull=True)
                    | (~Q(kind="dividend") & Q(quantity__gt=0))
                ),
                name="finance_investment_quantity_matches_kind",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.get_kind_display()} {self.position} ({self.date})"
