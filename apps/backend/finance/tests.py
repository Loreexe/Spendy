from datetime import timedelta
from decimal import Decimal
from unittest import mock

from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import User
from .models import Account, Line, Profile, SavingsAccount, Transaction


class FinanceTestBase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="finanza@example.com",
            password="Spendy-Fondamenta-2026",
            status=User.Status.ACTIVE,
        )
        self.client.force_authenticate(user=self.user)
        self.today = timezone.localdate()

    def create_account(self, name="Contanti", initial="0.00", type_="cash"):
        return self.client.post(
            reverse("finance-accounts"),
            {"name": name, "type": type_, "initial_balance": initial},
            format="json",
        )

    def create_savings(self, account_id, name="Salute"):
        return self.client.post(
            reverse("finance-savings"),
            {"name": name, "backing_account": account_id},
            format="json",
        )

    def create_transaction(self, payload):
        return self.client.post(
            reverse("finance-transactions"), payload, format="json"
        )


class ProfileTests(FinanceTestBase):
    def test_profile_is_created_lazily_once(self):
        first = self.client.get(reverse("finance-profile"))
        second = self.client.get(reverse("finance-profile"))
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(Profile.objects.filter(user=self.user).count(), 1)

    def test_global_admin_has_no_financial_profile(self):
        admin = User.objects.get(is_global_admin=True)
        self.client.force_authenticate(user=admin)
        response = self.client.get(reverse("finance-dashboard"))
        self.assertEqual(response.status_code, 403)

    def test_theme_defaults_to_dark_and_is_exposed(self):
        response = self.client.get(reverse("finance-profile"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["theme"], "dark")

    def test_theme_can_be_switched_to_light(self):
        response = self.client.patch(
            reverse("finance-profile"), {"theme": "light"}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["theme"], "light")
        self.assertEqual(
            Profile.objects.get(user=self.user).theme, "light"
        )

    def test_theme_can_follow_the_system(self):
        response = self.client.patch(
            reverse("finance-profile"), {"theme": "system"}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["theme"], "system")
        self.assertEqual(
            Profile.objects.get(user=self.user).theme, "system"
        )

    def test_theme_rejects_unknown_values(self):
        response = self.client.patch(
            reverse("finance-profile"), {"theme": "sepia"}, format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_global_admin_cannot_change_theme(self):
        admin = User.objects.get(is_global_admin=True)
        self.client.force_authenticate(user=admin)
        response = self.client.patch(
            reverse("finance-profile"), {"theme": "light"}, format="json"
        )
        self.assertEqual(response.status_code, 403)


class AccountTests(FinanceTestBase):
    def test_account_with_initial_balance_creates_opening_movement(self):
        response = self.create_account(initial="100.00")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["balance"], "100.00")

        account = Account.objects.get(pk=response.data["id"])
        self.assertEqual(account.balance, 100)
        opening = Transaction.objects.get(profile=account.profile, kind="opening")
        self.assertEqual(opening.amount, 100)
        self.assertEqual(opening.lines.get().account, account)
        self.assertEqual(opening.time.isoformat(), "12:00:00")

    def test_zero_initial_balance_does_not_create_movement(self):
        response = self.create_account(initial="0.00")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Transaction.objects.count(), 0)

    def test_negative_initial_balance_is_rejected(self):
        response = self.create_account(initial="-25.50")
        self.assertEqual(response.status_code, 400)
        self.assertIn("initial_balance", response.data)

    def test_account_with_movements_cannot_be_deleted(self):
        account = self.create_account(initial="10.00").data
        response = self.client.delete(
            reverse("finance-account-detail", args=[account["id"]])
        )
        self.assertEqual(response.status_code, 400)

    def test_empty_account_can_be_deleted(self):
        account = self.create_account().data
        response = self.client.delete(
            reverse("finance-account-detail", args=[account["id"]])
        )
        self.assertEqual(response.status_code, 204)

    def test_account_can_be_archived(self):
        account = self.create_account().data
        response = self.client.patch(
            reverse("finance-account-detail", args=[account["id"]]),
            {"archived": True},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["archived"])


class TransactionTests(FinanceTestBase):
    def setUp(self):
        super().setUp()
        self.account = self.create_account(initial="1000.00").data

    def test_income_and_expense(self):
        income = self.create_transaction(
            {
                "kind": "income",
                "date": self.today.isoformat(),
                "description": "Stipendio",
                "amount": "500.00",
                "account": self.account["id"],
            }
        )
        self.assertEqual(income.status_code, 201)

        expense = self.create_transaction(
            {
                "kind": "expense",
                "date": self.today.isoformat(),
                "description": "Spesa",
                "amount": "120.00",
                "account": self.account["id"],
            }
        )
        self.assertEqual(expense.status_code, 201)

        account = Account.objects.get(pk=self.account["id"])
        self.assertEqual(account.balance, 1380)

    def test_account_transfer_counts_both_sides(self):
        other = self.create_account(name="Banca", initial="0.00").data
        response = self.create_transaction(
            {
                "kind": "transfer",
                "date": self.today.isoformat(),
                "description": "Giroconto",
                "amount": "200.00",
                "from_account": self.account["id"],
                "to_account": other["id"],
            }
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Account.objects.get(pk=self.account["id"]).balance, 800)
        self.assertEqual(Account.objects.get(pk=other["id"]).balance, 200)

        dashboard = self.client.get(reverse("finance-dashboard"))
        # Entrate/Uscite sono i movimenti dei conti: il trasferimento genera
        # un'uscita dal conto di origine e un'entrata sul conto di destinazione;
        # l'apertura iniziale di 1000 è un'entrata del periodo.
        self.assertEqual(dashboard.data["income_total"], "1200.00")
        self.assertEqual(dashboard.data["expense_total"], "200.00")
        self.assertEqual(dashboard.data["period_balance"], "1000.00")

    def test_transfer_to_savings_and_back(self):
        savings = self.create_savings(self.account["id"]).data
        deposit = self.create_transaction(
            {
                "kind": "transfer",
                "date": self.today.isoformat(),
                "description": "Versamento",
                "amount": "100.00",
                "from_account": self.account["id"],
                "to_savings": savings["id"],
            }
        )
        self.assertEqual(deposit.status_code, 201)
        self.assertEqual(SavingsAccount.objects.get(pk=savings["id"]).balance, 100)
        self.assertEqual(Account.objects.get(pk=self.account["id"]).balance, 900)

        withdrawal = self.create_transaction(
            {
                "kind": "transfer",
                "date": self.today.isoformat(),
                "description": "Prelievo",
                "amount": "40.00",
                "from_savings": savings["id"],
                "to_account": self.account["id"],
            }
        )
        self.assertEqual(withdrawal.status_code, 201)
        self.assertEqual(SavingsAccount.objects.get(pk=savings["id"]).balance, 60)
        self.assertEqual(Account.objects.get(pk=self.account["id"]).balance, 940)

    def test_direct_savings_transfer_is_rejected(self):
        savings_a = self.create_savings(self.account["id"], name="A").data
        savings_b = self.create_savings(self.account["id"], name="B").data
        response = self.create_transaction(
            {
                "kind": "transfer",
                "date": self.today.isoformat(),
                "amount": "10.00",
                "from_savings": savings_a["id"],
                "to_savings": savings_b["id"],
            }
        )
        self.assertEqual(response.status_code, 400)

    def test_transaction_update_and_delete_recalculate(self):
        response = self.create_transaction(
            {
                "kind": "expense",
                "date": self.today.isoformat(),
                "amount": "50.00",
                "account": self.account["id"],
            }
        )
        transaction_id = response.data["id"]
        self.assertEqual(Account.objects.get(pk=self.account["id"]).balance, 950)

        updated = self.client.patch(
            reverse("finance-transaction-detail", args=[transaction_id]),
            {
                "kind": "expense",
                "date": self.today.isoformat(),
                "amount": "30.00",
                "account": self.account["id"],
            },
            format="json",
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(Account.objects.get(pk=self.account["id"]).balance, 970)

        deleted = self.client.delete(
            reverse("finance-transaction-detail", args=[transaction_id])
        )
        self.assertEqual(deleted.status_code, 204)
        self.assertEqual(Account.objects.get(pk=self.account["id"]).balance, 1000)

    def test_opening_movement_cannot_be_modified_or_deleted(self):
        opening = Transaction.objects.get(
            profile=Profile.objects.get(user=self.user), kind=Transaction.Kind.OPENING
        )
        patched = self.client.patch(
            reverse("finance-transaction-detail", args=[opening.id]),
            {
                "kind": "income",
                "date": self.today.isoformat(),
                "amount": "1.00",
                "account": self.account["id"],
            },
            format="json",
        )
        self.assertEqual(patched.status_code, 400)
        deleted = self.client.delete(
            reverse("finance-transaction-detail", args=[opening.id])
        )
        self.assertEqual(deleted.status_code, 400)
        self.assertEqual(Account.objects.get(pk=self.account["id"]).balance, 1000)

    def test_transaction_time_is_optional_and_written_as_hh_mm(self):
        created = self.create_transaction(
            {
                "kind": "expense",
                "date": self.today.isoformat(),
                "description": "Caffè",
                "amount": "1.20",
                "account": self.account["id"],
                "time": "09:05",
            }
        )
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.data["time"], "09:05")
        stored = Transaction.objects.get(pk=created.data["id"])
        self.assertEqual(stored.time.isoformat(), "09:05:00")

    def test_midnight_time_is_not_replaced_by_the_current_time(self):
        created = self.create_transaction(
            {
                "kind": "expense",
                "date": self.today.isoformat(),
                "description": "Mezzanotte",
                "amount": "1.00",
                "account": self.account["id"],
                "time": "00:00",
            }
        )
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.data["time"], "00:00")
        self.assertEqual(
            Transaction.objects.get(pk=created.data["id"]).time.isoformat(),
            "00:00:00",
        )

    def test_transaction_without_time_uses_current_local_time(self):
        from datetime import time as dt_time

        with mock.patch(
            "finance.serializers.current_local_time",
            return_value=dt_time(8, 5),
        ):
            created = self.create_transaction(
                {
                    "kind": "expense",
                    "date": self.today.isoformat(),
                    "description": "Spesa",
                    "amount": "2.00",
                    "account": self.account["id"],
                }
            )
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.data["time"], "08:05")
        self.assertEqual(
            Transaction.objects.get(pk=created.data["id"]).time, dt_time(8, 5)
        )

    def test_transaction_patch_without_time_keeps_the_existing_one(self):
        created = self.create_transaction(
            {
                "kind": "expense",
                "date": self.today.isoformat(),
                "description": "Caffè",
                "amount": "1.20",
                "account": self.account["id"],
                "time": "18:45",
            }
        ).data
        updated = self.client.patch(
            reverse("finance-transaction-detail", args=[created["id"]]),
            {
                "kind": "expense",
                "date": self.today.isoformat(),
                "description": "Caffè",
                "amount": "1.50",
                "account": self.account["id"],
            },
            format="json",
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.data["time"], "18:45")

        changed = self.client.patch(
            reverse("finance-transaction-detail", args=[created["id"]]),
            {
                "kind": "expense",
                "date": self.today.isoformat(),
                "description": "Caffè",
                "amount": "1.50",
                "account": self.account["id"],
                "time": "06:30",
            },
            format="json",
        )
        self.assertEqual(changed.status_code, 200)
        self.assertEqual(changed.data["time"], "06:30")

    def test_transactions_are_ordered_by_date_time_and_id_descending(self):
        for moment in ("09:00", "18:00"):
            self.create_transaction(
                {
                    "kind": "expense",
                    "date": self.today.isoformat(),
                    "description": moment,
                    "amount": "1.00",
                    "account": self.account["id"],
                    "time": moment,
                }
            )
        listing = self.client.get(reverse("finance-transactions")).data[
            "transactions"
        ]
        movements = [
            item for item in listing if item["kind"] == Transaction.Kind.EXPENSE
        ]
        self.assertEqual([item["time"] for item in movements], ["18:00", "09:00"])
        self.assertEqual(movements[0]["description"], "18:00")


class SavingsPaymentTests(FinanceTestBase):
    def setUp(self):
        super().setUp()
        self.account = self.create_account(initial="100.00").data
        self.savings = self.create_savings(self.account["id"]).data

    def deposit(self, amount="100.00"):
        return self.create_transaction(
            {
                "kind": "transfer",
                "date": self.today.isoformat(),
                "amount": amount,
                "from_account": self.account["id"],
                "to_savings": self.savings["id"],
            }
        )

    def test_full_savings_payment_uses_technical_line(self):
        self.deposit("100.00")
        response = self.create_transaction(
            {
                "kind": "expense",
                "date": self.today.isoformat(),
                "description": "Medicine",
                "amount": "50.00",
                "savings": self.savings["id"],
            }
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(SavingsAccount.objects.get(pk=self.savings["id"]).balance, 50)
        self.assertEqual(Account.objects.get(pk=self.account["id"]).balance, 0)

        transaction = Transaction.objects.get(pk=response.data["id"])
        self.assertEqual(transaction.lines.count(), 3)
        self.assertTrue(
            transaction.lines.filter(role=Line.Role.TECHNICAL, amount=50).exists()
        )

        dashboard = self.client.get(reverse("finance-dashboard"))
        # Pagamento dal salvadanaio: sul conto di appoggio la riga tecnica
        # (+50) è un'entrata e la riga principale (−50) un'uscita; il saldo
        # del periodo resta 0.
        self.assertEqual(dashboard.data["income_total"], "150.00")
        self.assertEqual(dashboard.data["expense_total"], "150.00")
        self.assertEqual(dashboard.data["period_balance"], "0.00")

    def test_partial_savings_payment_requires_confirmation(self):
        self.deposit("30.00")
        payload = {
            "kind": "expense",
            "date": self.today.isoformat(),
            "description": "Medicine",
            "amount": "50.00",
            "savings": self.savings["id"],
        }
        response = self.create_transaction(payload)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"][0], "insufficient_savings")
        self.assertEqual(response.data["available"][0], "30.00")
        self.assertEqual(SavingsAccount.objects.get(pk=self.savings["id"]).balance, 30)

        payload["confirm_coverage"] = True
        response = self.create_transaction(payload)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(SavingsAccount.objects.get(pk=self.savings["id"]).balance, 0)
        self.assertEqual(Account.objects.get(pk=self.account["id"]).balance, 50)

    def test_savings_withdrawal_rejects_insufficient_balance(self):
        response = self.create_transaction(
            {
                "kind": "transfer",
                "date": self.today.isoformat(),
                "amount": "10.00",
                "from_savings": self.savings["id"],
                "to_account": self.account["id"],
            }
        )
        self.assertEqual(response.status_code, 400)

    def test_delete_savings_transfers_residual_balance(self):
        self.deposit("100.00")
        response = self.client.delete(
            reverse("finance-savings-detail", args=[self.savings["id"]])
        )
        self.assertEqual(response.status_code, 204)
        self.assertFalse(SavingsAccount.objects.filter(pk=self.savings["id"]).exists())
        self.assertEqual(Account.objects.get(pk=self.account["id"]).balance, 100)
        self.assertTrue(
            Transaction.objects.filter(
                profile=Profile.objects.get(user=self.user), kind="transfer"
            ).exists()
        )

    def test_update_cannot_make_savings_negative(self):
        self.deposit("30.00")
        expense = self.create_transaction(
            {
                "kind": "expense",
                "date": self.today.isoformat(),
                "amount": "30.00",
                "savings": self.savings["id"],
            }
        )
        self.assertEqual(expense.status_code, 201)
        deposit = Transaction.objects.filter(
            profile=Profile.objects.get(user=self.user), kind="transfer"
        ).first()
        response = self.client.patch(
            reverse("finance-transaction-detail", args=[deposit.id]),
            {
                "kind": "transfer",
                "date": self.today.isoformat(),
                "amount": "20.00",
                "from_account": self.account["id"],
                "to_savings": self.savings["id"],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(SavingsAccount.objects.get(pk=self.savings["id"]).balance, 0)


class DashboardAndIsolationTests(FinanceTestBase):
    def test_dashboard_totals(self):
        account = self.create_account(initial="1000.00").data
        savings = self.create_savings(account["id"]).data
        self.create_transaction(
            {
                "kind": "transfer",
                "date": self.today.isoformat(),
                "amount": "200.00",
                "from_account": account["id"],
                "to_savings": savings["id"],
            }
        )
        self.create_transaction(
            {
                "kind": "income",
                "date": self.today.isoformat(),
                "amount": "100.00",
                "account": account["id"],
            }
        )
        response = self.client.get(reverse("finance-dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["total_balance"], "900.00")
        self.assertEqual(response.data["total_savings"], "200.00")
        self.assertEqual(response.data["total_patrimony"], "1100.00")
        # Movimenti dei conti: apertura 1000 + entrata 100 − trasferimento 200.
        self.assertEqual(response.data["income_total"], "1100.00")
        self.assertEqual(response.data["expense_total"], "200.00")
        self.assertEqual(response.data["period_balance"], "900.00")

    def test_account_period_balances_sum_to_period_balance(self):
        account = self.create_account(initial="1000.00").data
        other = self.create_account(name="Banca", initial="0.00").data
        savings = self.create_savings(account["id"]).data
        self.create_transaction(
            {
                "kind": "transfer",
                "date": self.today.isoformat(),
                "amount": "200.00",
                "from_account": account["id"],
                "to_savings": savings["id"],
            }
        )
        self.create_transaction(
            {
                "kind": "transfer",
                "date": self.today.isoformat(),
                "amount": "50.00",
                "from_account": account["id"],
                "to_account": other["id"],
            }
        )
        self.create_transaction(
            {
                "kind": "income",
                "date": self.today.isoformat(),
                "amount": "100.00",
                "account": account["id"],
            }
        )
        response = self.client.get(reverse("finance-dashboard"))
        self.assertEqual(response.status_code, 200)
        # La somma delle variazioni del periodo dei singoli conti deve coincidere
        # con il Saldo del periodo, che a sua volta è Entrate − Uscite.
        period_total = sum(
            (Decimal(item["period_balance"]) for item in response.data["accounts"]),
            Decimal("0"),
        )
        self.assertEqual(period_total, Decimal(response.data["period_balance"]))
        self.assertEqual(
            Decimal(response.data["income_total"])
            - Decimal(response.data["expense_total"]),
            Decimal(response.data["period_balance"]),
        )
        self.assertEqual(response.data["income_total"], "1150.00")
        self.assertEqual(response.data["expense_total"], "250.00")
        self.assertEqual(response.data["period_balance"], "900.00")

    def test_entrate_uscite_are_account_movements(self):
        account = self.create_account(initial="1000.00").data
        savings = self.create_savings(account["id"]).data
        self.create_transaction(
            {
                "kind": "income",
                "date": self.today.isoformat(),
                "amount": "100.00",
                "account": account["id"],
            }
        )
        self.create_transaction(
            {
                "kind": "expense",
                "date": self.today.isoformat(),
                "amount": "40.00",
                "account": account["id"],
            }
        )
        self.create_transaction(
            {
                "kind": "transfer",
                "date": self.today.isoformat(),
                "amount": "200.00",
                "from_account": account["id"],
                "to_savings": savings["id"],
            }
        )
        # Spesa pagata dal salvadanaio: ponte tecnico, i conti non si muovono.
        self.create_transaction(
            {
                "kind": "expense",
                "date": self.today.isoformat(),
                "amount": "30.00",
                "savings": savings["id"],
            }
        )
        response = self.client.get(reverse("finance-dashboard"))
        # Movimenti dei conti: aperture, redditi, spese, trasferimenti e
        # ponte tecnico del salvadanaio contano tutti col loro segno.
        self.assertEqual(response.data["income_total"], "1130.00")
        self.assertEqual(response.data["expense_total"], "270.00")
        self.assertEqual(response.data["period_balance"], "860.00")

    def test_deleted_transactions_are_excluded_from_flows(self):
        account = self.create_account(initial="1000.00").data
        created = self.create_transaction(
            {
                "kind": "expense",
                "date": self.today.isoformat(),
                "amount": "50.00",
                "account": account["id"],
            }
        )
        Transaction.objects.filter(pk=created.data["id"]).update(is_deleted=True)
        response = self.client.get(reverse("finance-dashboard"))
        # La spesa eliminata non conta; l'apertura del conto invece sì.
        self.assertEqual(response.data["income_total"], "1000.00")
        self.assertEqual(response.data["expense_total"], "0.00")
        self.assertEqual(response.data["period_balance"], "1000.00")

    def test_full_range_period_balance_includes_opening(self):
        account = self.create_account(initial="1000.00").data
        self.create_transaction(
            {
                "kind": "expense",
                "date": self.today.isoformat(),
                "amount": "40.00",
                "account": account["id"],
            }
        )
        self.create_transaction(
            {
                "kind": "income",
                "date": self.today.isoformat(),
                "amount": "10.00",
                "account": account["id"],
            }
        )
        response = self.client.get(
            reverse("finance-dashboard"),
            {"start": "2000-01-01", "end": self.today.isoformat()},
        )
        # Il saldo del periodo è Entrate − Uscite e include l'apertura:
        # 1010 − 40 = 970, pari alla variazione dei saldi dei conti.
        self.assertEqual(response.data["income_total"], "1010.00")
        self.assertEqual(response.data["expense_total"], "40.00")
        self.assertEqual(response.data["period_balance"], "970.00")
        self.assertEqual(response.data["total_balance"], "970.00")

    def test_accounts_expose_period_value_and_total_with_savings(self):
        account = self.create_account(initial="1000.00").data
        savings = self.create_savings(account["id"]).data
        self.create_transaction(
            {
                "kind": "transfer",
                "date": self.today.isoformat(),
                "amount": "200.00",
                "from_account": account["id"],
                "to_savings": savings["id"],
            }
        )
        self.create_transaction(
            {
                "kind": "expense",
                "date": self.today.isoformat(),
                "amount": "50.00",
                "account": account["id"],
            }
        )
        response = self.client.get(reverse("finance-dashboard"))
        row = response.data["accounts"][0]
        self.assertEqual(row["period_balance"], "750.00")
        # Saldo effettivo (750) + salvadanaio collegato (200).
        self.assertEqual(row["total_with_savings"], "950.00")

    def test_full_range_dashboard_clamps_start_to_first_activity(self):
        self.create_account(initial="1000.00")
        response = self.client.get(
            reverse("finance-dashboard"),
            {"start": "2000-01-01", "end": self.today.isoformat()},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["period"]["start"], self.today.isoformat())
        self.assertEqual(response.data["period"]["end"], self.today.isoformat())

    def test_full_range_series_covers_data_and_ends_today(self):
        account = self.create_account(initial="1000.00").data
        # Conto aperto 20 giorni fa: "Tutto" deve coprire i dati, non troncare
        # ai primi 95 bucket (bug del periodo lungo).
        Account.objects.filter(pk=account["id"]).update(
            created_at=timezone.now() - timedelta(days=20)
        )
        self.create_transaction(
            {
                "kind": "expense",
                "date": self.today.isoformat(),
                "amount": "40.00",
                "account": account["id"],
            }
        )
        response = self.client.get(
            reverse("finance-dashboard-series"),
            {"start": "2000-01-01", "end": self.today.isoformat()},
        )
        self.assertEqual(response.status_code, 200)
        buckets = response.data["buckets"]
        self.assertGreaterEqual(len(buckets), 2)
        self.assertLessEqual(len(buckets), 95)
        self.assertEqual(buckets[-1]["date"], self.today.isoformat())
        dates = [bucket["date"] for bucket in buckets]
        self.assertEqual(dates, sorted(set(dates)))
        self.assertEqual(buckets[-1]["saldo"], "960.00")

    def test_long_series_never_exceeds_95_points(self):
        self.create_account(initial="500.00")
        response = self.client.get(
            reverse("finance-dashboard-series"),
            {
                "start": (self.today - timedelta(days=3000)).isoformat(),
                "end": self.today.isoformat(),
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(len(response.data["buckets"]), 95)
        self.assertEqual(
            response.data["buckets"][-1]["date"], self.today.isoformat()
        )

    def test_period_before_first_activity_stays_empty(self):
        self.create_account(initial="1000.00")
        start = (self.today - timedelta(days=60)).isoformat()
        end = (self.today - timedelta(days=30)).isoformat()
        response = self.client.get(
            reverse("finance-dashboard"),
            {"start": start, "end": end},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["period"]["start"], start)
        self.assertEqual(response.data["period"]["end"], end)

    def test_month_filter(self):
        response = self.client.get(
            reverse("finance-dashboard"),
            {
                "start": (self.today - timedelta(days=400)).isoformat(),
                "end": self.today.isoformat(),
            },
        )
        self.assertEqual(response.status_code, 200)

    def test_other_user_cannot_access_resources(self):
        account = self.create_account(initial="10.00").data
        other = User.objects.create_user(
            email="altro@example.com",
            password="Spendy-Fondamenta-2026",
            status=User.Status.ACTIVE,
        )
        self.client.force_authenticate(user=other)
        self.assertEqual(
            self.client.get(reverse("finance-account-detail", args=[account["id"]])).status_code,
            400,
        )
        self.assertEqual(
            self.client.get(reverse("finance-accounts")).data["accounts"], []
        )
