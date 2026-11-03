from datetime import timedelta
from decimal import Decimal

from django.urls import reverse

from .models import Account, Line, Profile, Transaction, ZERO
from .tests import FinanceTestBase


class BalanceRuleTests(FinanceTestBase):
    """DC-069: an account balance can never go below zero."""

    def expense(self, account_id, amount, day=None):
        return self.create_transaction(
            {
                "kind": "expense",
                "date": (day or self.today).isoformat(),
                "description": "Spesa",
                "amount": amount,
                "account": account_id,
            }
        )

    def income(self, account_id, amount, day=None):
        return self.create_transaction(
            {
                "kind": "income",
                "date": (day or self.today).isoformat(),
                "description": "Entrata",
                "amount": amount,
                "account": account_id,
            }
        )

    def test_expense_above_balance_is_rejected(self):
        account = self.create_account(initial="50.00").data
        response = self.expense(account["id"], "60.00")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"][0], "insufficient_account_balance")
        self.assertEqual(response.data["available"][0], "50.00")
        self.assertEqual(Account.objects.get(pk=account["id"]).balance, 50)

    def test_expense_equal_to_balance_is_allowed(self):
        account = self.create_account(initial="50.00").data
        response = self.expense(account["id"], "50.00")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Account.objects.get(pk=account["id"]).balance, ZERO)

    def test_transfer_above_balance_is_rejected(self):
        source = self.create_account(initial="100.00").data
        target = self.create_account(name="Banca").data
        response = self.create_transaction(
            {
                "kind": "transfer",
                "date": self.today.isoformat(),
                "amount": "150.00",
                "from_account": source["id"],
                "to_account": target["id"],
            }
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"][0], "insufficient_account_balance")
        self.assertEqual(Account.objects.get(pk=source["id"]).balance, 100)

    def test_savings_deposit_above_balance_is_rejected(self):
        account = self.create_account(initial="100.00").data
        savings = self.create_savings(account["id"]).data
        response = self.create_transaction(
            {
                "kind": "transfer",
                "date": self.today.isoformat(),
                "amount": "150.00",
                "from_account": account["id"],
                "to_savings": savings["id"],
            }
        )
        self.assertEqual(response.status_code, 400)

    def test_savings_payment_cannot_make_backing_account_negative(self):
        account = self.create_account(initial="100.00").data
        savings = self.create_savings(account["id"]).data
        self.create_transaction(
            {
                "kind": "transfer",
                "date": self.today.isoformat(),
                "amount": "90.00",
                "from_account": account["id"],
                "to_savings": savings["id"],
            }
        )
        response = self.create_transaction(
            {
                "kind": "expense",
                "date": self.today.isoformat(),
                "description": "Spesa",
                "amount": "120.00",
                "savings": savings["id"],
                "confirm_coverage": True,
            }
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"][0], "insufficient_account_balance")

    def test_backdated_expense_that_breaks_the_past_is_rejected(self):
        account = self.create_account(initial="100.00").data
        tomorrow = self.today + timedelta(days=1)
        self.income(account["id"], "100.00")
        self.expense(account["id"], "190.00", day=tomorrow)
        self.assertEqual(Account.objects.get(pk=account["id"]).balance, 10)

        response = self.expense(account["id"], "50.00")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"][0], "insufficient_account_balance")

    def test_delete_income_that_breaks_a_later_expense_is_rejected(self):
        account = self.create_account(initial="100.00").data
        income = self.income(account["id"], "100.00")
        self.expense(account["id"], "150.00")
        response = self.client.delete(
            reverse("finance-transaction-detail", args=[income.data["id"]])
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Account.objects.get(pk=account["id"]).balance, 50)

    def test_delete_expense_is_allowed(self):
        account = self.create_account(initial="100.00").data
        expense = self.expense(account["id"], "40.00")
        response = self.client.delete(
            reverse("finance-transaction-detail", args=[expense.data["id"]])
        )
        self.assertEqual(response.status_code, 204)
        self.assertEqual(Account.objects.get(pk=account["id"]).balance, 100)

    def test_patch_amount_above_balance_is_rejected(self):
        account = self.create_account(initial="100.00").data
        expense = self.expense(account["id"], "10.00")
        response = self.client.patch(
            reverse("finance-transaction-detail", args=[expense.data["id"]]),
            {
                "kind": "expense",
                "date": self.today.isoformat(),
                "amount": "500.00",
                "account": account["id"],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Account.objects.get(pk=account["id"]).balance, 90)

    def test_patch_date_backwards_is_rejected(self):
        account = self.create_account(initial="10.00").data
        tomorrow = self.today + timedelta(days=1)
        self.income(account["id"], "100.00", day=tomorrow)
        expense = self.expense(account["id"], "90.00", day=tomorrow)
        self.assertEqual(Account.objects.get(pk=account["id"]).balance, 20)

        response = self.client.patch(
            reverse("finance-transaction-detail", args=[expense.data["id"]]),
            {
                "kind": "expense",
                "date": self.today.isoformat(),
                "amount": "90.00",
                "account": account["id"],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"][0], "insufficient_account_balance")

    def test_account_already_negative_can_be_corrected(self):
        profile, _ = Profile.objects.get_or_create(user=self.user)
        account = Account.objects.create(
            profile=profile,
            name="Rosso",
            type=Account.Type.OTHER,
            initial_balance=Decimal("-50.00"),
        )
        opening = Transaction.objects.create(
            profile=profile,
            kind=Transaction.Kind.OPENING,
            date=self.today,
            description="Saldo iniziale",
            amount=Decimal("50.00"),
        )
        Line.objects.create(
            transaction=opening,
            account=account,
            amount=Decimal("-50.00"),
        )

        allowed = self.income(account.id, "10.00")
        self.assertEqual(allowed.status_code, 201)
        self.assertEqual(Account.objects.get(pk=account.id).balance, -40)

        rejected = self.expense(account.id, "40.00")
        self.assertEqual(rejected.status_code, 400)
