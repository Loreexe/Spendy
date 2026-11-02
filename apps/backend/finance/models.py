from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Q, Sum

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


class Transaction(models.Model):
    class Kind(models.TextChoices):
        OPENING = "opening", "Apertura"
        INCOME = "income", "Entrata"
        EXPENSE = "expense", "Spesa"
        TRANSFER = "transfer", "Trasferimento"

    profile = models.ForeignKey(
        Profile, on_delete=models.CASCADE, related_name="transactions"
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
