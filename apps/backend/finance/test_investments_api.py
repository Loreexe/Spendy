"""API tests for the investments section (DC-082/DC-083)."""

from decimal import Decimal

from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import User
from .models import (
    Account,
    InvestmentOperation,
    InvestmentPosition,
    Profile,
    Transaction,
)

D = Decimal


class InvestmentApiTestBase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="invest-api@example.com",
            password="Spendy-Investimenti-2026",
            status=User.Status.ACTIVE,
        )
        self.client.force_authenticate(user=self.user)
        self.today = timezone.localdate()

    def create_account(self, name="Conto", initial="0.00"):
        response = self.client.post(
            reverse("finance-accounts"),
            {"name": name, "type": "checking", "initial_balance": initial},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        return response.data

    def set_account(self, account_id):
        return self.client.put(
            reverse("finance-investment-account"),
            {"account": account_id},
            format="json",
        )

    def create_position(self, **overrides):
        payload = {"name": "ETF Mondo"}
        payload.update(overrides)
        return self.client.post(
            reverse("finance-investments"), payload, format="json"
        )

    def add_operation(self, position_id, payload):
        return self.client.post(
            reverse("finance-investment-operations", args=[position_id]),
            payload,
            format="json",
        )

    def detail(self, position_id):
        return self.client.get(
            reverse("finance-investment-detail", args=[position_id])
        )

    def dashboard(self, **params):
        return self.client.get(reverse("finance-dashboard"), params)


class PositionApiTests(InvestmentApiTestBase):
    def test_empty_list_has_summary_and_no_account(self):
        response = self.client.get(reverse("finance-investments"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["positions"], [])
        self.assertIsNone(response.data["investment_account"])
        self.assertEqual(response.data["summary"]["total_cost"], "0.00")
        self.assertEqual(response.data["summary"]["positions_without_price"], 0)

    def test_create_position_with_opening_is_atomic_and_derived(self):
        response = self.create_position(
            category="etf",
            identifier="IE00B4L5Y983",
            current_price="105.20",
            opening={
                "date": self.today.isoformat(),
                "quantity": "10",
                "total_cost": "1000.00",
            },
        )
        self.assertEqual(response.status_code, 201)
        data = response.data
        self.assertEqual(data["quantity"], "10.00000000")
        self.assertEqual(data["cost"], "1000.00")
        self.assertEqual(data["average_cost"], "100.00000000")
        self.assertEqual(data["current_value"], "1052.00")
        self.assertEqual(data["unrealized_gain"], "52.00")
        self.assertEqual(data["category_label"], "ETF")
        self.assertEqual(data["price_updated_on"], self.today.isoformat())

        position = InvestmentPosition.objects.get(pk=data["id"])
        opening = position.operations.get()
        self.assertEqual(opening.kind, InvestmentOperation.Kind.OPENING)
        self.assertIsNone(opening.transaction)
        self.assertEqual(Transaction.objects.count(), 0)

    def test_invalid_opening_rolls_back_the_position(self):
        response = self.create_position(
            opening={
                "date": self.today.isoformat(),
                "quantity": "0",
                "total_cost": "1000.00",
            }
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(InvestmentPosition.objects.count(), 0)
        self.assertEqual(InvestmentOperation.objects.count(), 0)

    def test_create_position_without_opening(self):
        response = self.create_position()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["quantity"], "0.00000000")
        self.assertEqual(response.data["cost"], "0.00")

    def test_detail_returns_position_summary_and_operations(self):
        account = self.create_account(initial="1000.00")
        self.set_account(account["id"])
        position = self.create_position(
            current_price="110.00",
            opening={
                "date": self.today.isoformat(),
                "quantity": "10",
                "total_cost": "1000.00",
            },
        ).data
        self.add_operation(
            position["id"],
            {
                "kind": "buy",
                "date": self.today.isoformat(),
                "quantity": "2",
                "unit_price": "100.00",
                "commission": "1.50",
            },
        )

        response = self.detail(position["id"])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["position"]["quantity"], "12.00000000")
        self.assertEqual(response.data["summary"]["cost"], "1201.50")
        self.assertEqual(len(response.data["operations"]), 2)
        buy = response.data["operations"][1]
        self.assertEqual(buy["kind"], "buy")
        self.assertEqual(buy["account"], account["id"])
        self.assertEqual(buy["cash_amount"], "201.50")

    def test_patch_position_name_and_price_sets_update_date(self):
        position = self.create_position().data
        response = self.client.patch(
            reverse("finance-investment-detail", args=[position["id"]]),
            {"name": "ETF Aggiornato", "current_price": "99.50"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "ETF Aggiornato")
        self.assertEqual(response.data["current_price"], "99.50")
        self.assertEqual(response.data["price_updated_on"], self.today.isoformat())

    def test_negative_current_price_is_rejected(self):
        response = self.create_position(current_price="-1.00")
        self.assertEqual(response.status_code, 400)
        self.assertIn("current_price", response.data)

        position = self.create_position(current_price="1.00").data
        response = self.client.patch(
            reverse("finance-investment-detail", args=[position["id"]]),
            {"current_price": "-0.01"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("current_price", response.data)

    def test_price_updated_on_is_server_controlled(self):
        position = self.create_position(current_price="100.00").data
        response = self.client.patch(
            reverse("finance-investment-detail", args=[position["id"]]),
            {
                "current_price": "99.50",
                "price_updated_on": "2000-01-01",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["price_updated_on"], self.today.isoformat())
        stored = InvestmentPosition.objects.get(pk=position["id"])
        self.assertEqual(stored.price_updated_on, self.today)

        response = self.client.patch(
            reverse("finance-investment-detail", args=[position["id"]]),
            {"price_updated_on": "2001-01-01"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        stored.refresh_from_db()
        self.assertEqual(stored.price_updated_on, self.today)

    def test_position_delete_requires_no_operations(self):
        with_operations = self.create_position(
            opening={
                "date": self.today.isoformat(),
                "quantity": "1",
                "total_cost": "10.00",
            }
        ).data
        response = self.client.delete(
            reverse("finance-investment-detail", args=[with_operations["id"]])
        )
        self.assertEqual(response.status_code, 400)
        self.assertTrue(
            InvestmentPosition.objects.filter(pk=with_operations["id"]).exists()
        )

        empty = self.create_position().data
        response = self.client.delete(
            reverse("finance-investment-detail", args=[empty["id"]])
        )
        self.assertEqual(response.status_code, 204)
        self.assertFalse(InvestmentPosition.objects.filter(pk=empty["id"]).exists())

    def test_archive_only_when_quantity_is_zero(self):
        account = self.create_account(initial="1000.00")
        self.set_account(account["id"])
        position = self.create_position(
            opening={
                "date": self.today.isoformat(),
                "quantity": "10",
                "total_cost": "1000.00",
            }
        ).data
        response = self.client.patch(
            reverse("finance-investment-detail", args=[position["id"]]),
            {"archived": True},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

        self.add_operation(
            position["id"],
            {
                "kind": "sell",
                "date": self.today.isoformat(),
                "quantity": "10",
                "unit_price": "110.00",
            },
        )
        response = self.client.patch(
            reverse("finance-investment-detail", args=[position["id"]]),
            {"archived": True},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["archived"])

        response = self.add_operation(
            position["id"],
            {
                "kind": "buy",
                "date": self.today.isoformat(),
                "quantity": "1",
                "unit_price": "100.00",
            },
        )
        self.assertEqual(response.status_code, 400)


class OperationApiTests(InvestmentApiTestBase):
    def setUp(self):
        super().setUp()
        self.account = self.create_account(initial="1000.00")
        self.set_account(self.account["id"])
        self.position = self.create_position(
            current_price="110.00",
            opening={
                "date": self.today.isoformat(),
                "quantity": "10",
                "total_cost": "1000.00",
            },
        ).data

    def test_buy_uses_investment_account(self):
        response = self.add_operation(
            self.position["id"],
            {
                "kind": "buy",
                "date": self.today.isoformat(),
                "quantity": "2",
                "unit_price": "100.00",
                "commission": "1.50",
            },
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["gross_amount"], "200.00")
        self.assertEqual(response.data["cash_amount"], "201.50")
        self.assertEqual(response.data["account"], self.account["id"])
        self.assertEqual(
            Account.objects.get(pk=self.account["id"]).balance, D("798.50")
        )
        movement = Transaction.objects.get(kind=Transaction.Kind.INVESTMENT_BUY)
        self.assertEqual(movement.amount, D("201.50"))
        self.assertEqual(movement.lines.get().amount, D("-201.50"))

    def test_buy_with_total_amount(self):
        response = self.add_operation(
            self.position["id"],
            {
                "kind": "buy",
                "date": self.today.isoformat(),
                "quantity": "2",
                "total_amount": "205.00",
                "commission": "1.50",
            },
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["unit_price"], "102.50000000")
        self.assertEqual(response.data["cash_amount"], "206.50")

    def test_buy_without_account_is_rejected_but_opening_is_allowed(self):
        self.set_account(None)
        response = self.add_operation(
            self.position["id"],
            {
                "kind": "buy",
                "date": self.today.isoformat(),
                "quantity": "1",
                "unit_price": "100.00",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            Transaction.objects.filter(
                kind=Transaction.Kind.INVESTMENT_BUY
            ).count(),
            0,
        )

        second = self.create_position(
            opening={
                "date": self.today.isoformat(),
                "quantity": "3",
                "total_cost": "30.00",
            }
        )
        self.assertEqual(second.status_code, 201)

    def test_sell_uses_average_cost_and_realized_gain(self):
        response = self.add_operation(
            self.position["id"],
            {
                "kind": "sell",
                "date": self.today.isoformat(),
                "quantity": "2",
                "unit_price": "110.00",
                "commission": "1.00",
            },
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["cash_amount"], "219.00")
        self.assertEqual(response.data["cost_removed"], "200.00")
        self.assertEqual(response.data["realized_gain"], "19.00")

    def test_dividend_increases_cash_and_keeps_cost(self):
        response = self.add_operation(
            self.position["id"],
            {
                "kind": "dividend",
                "date": self.today.isoformat(),
                "amount": "12.40",
                "description": "Dividendo trimestrale",
            },
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["cash_amount"], "12.40")
        self.assertIsNone(response.data["quantity"])
        self.assertEqual(
            Account.objects.get(pk=self.account["id"]).balance, D("1012.40")
        )
        detail = self.detail(self.position["id"])
        self.assertEqual(detail.data["summary"]["cost"], "1000.00")

    def test_buy_with_invalid_values_is_rejected(self):
        invalid_quantity = self.add_operation(
            self.position["id"],
            {
                "kind": "buy",
                "date": self.today.isoformat(),
                "quantity": "0",
                "unit_price": "100.00",
            },
        )
        self.assertEqual(invalid_quantity.status_code, 400)

        negative_fee = self.add_operation(
            self.position["id"],
            {
                "kind": "buy",
                "date": self.today.isoformat(),
                "quantity": "1",
                "unit_price": "100.00",
                "commission": "-1.00",
            },
        )
        self.assertEqual(negative_fee.status_code, 400)

    def test_quantity_price_overflow_is_rejected_with_400(self):
        response = self.add_operation(
            self.position["id"],
            {
                "kind": "buy",
                "date": self.today.isoformat(),
                "quantity": "9999999999999999.99999999",
                "unit_price": "9999999999999999.99999999",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(
            Transaction.objects.filter(
                kind=Transaction.Kind.INVESTMENT_BUY
            ).exists()
        )

    def test_operation_kind_is_immutable(self):
        operation = self.add_operation(
            self.position["id"],
            {
                "kind": "buy",
                "date": self.today.isoformat(),
                "quantity": "1",
                "unit_price": "100.00",
            },
        ).data
        response = self.client.patch(
            reverse("finance-investment-operation-detail", args=[operation["id"]]),
            {"kind": "sell"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            InvestmentOperation.objects.get(pk=operation["id"]).kind,
            InvestmentOperation.Kind.BUY,
        )

    def test_edit_buy_recalculates_later_sell(self):
        rich = self.create_account("Ricco", initial="10000.00")
        self.set_account(rich["id"])
        buy = self.add_operation(
            self.position["id"],
            {
                "kind": "buy",
                "date": self.today.isoformat(),
                "quantity": "10",
                "unit_price": "100.00",
            },
        ).data
        self.add_operation(
            self.position["id"],
            {
                "kind": "sell",
                "date": self.today.isoformat(),
                "quantity": "5",
                "unit_price": "120.00",
            },
        )
        before = self.detail(self.position["id"]).data["summary"]["realized_gain"]
        self.assertEqual(before, "100.00")

        response = self.client.patch(
            reverse("finance-investment-operation-detail", args=[buy["id"]]),
            {"unit_price": "200.00"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        after = self.detail(self.position["id"]).data["summary"]["realized_gain"]
        self.assertEqual(after, "-150.00")
        self.assertEqual(
            Account.objects.get(pk=rich["id"]).balance, D("8600.00")
        )

    def test_delete_operation_removes_account_movement(self):
        operation = self.add_operation(
            self.position["id"],
            {
                "kind": "dividend",
                "date": self.today.isoformat(),
                "amount": "12.40",
            },
        ).data
        response = self.client.delete(
            reverse("finance-investment-operation-detail", args=[operation["id"]])
        )
        self.assertEqual(response.status_code, 204)
        self.assertEqual(
            Account.objects.get(pk=self.account["id"]).balance, D("1000.00")
        )
        self.assertFalse(
            Transaction.objects.filter(
                kind=Transaction.Kind.INVESTMENT_DIVIDEND
            ).exists()
        )

    def test_operations_are_rejected_when_position_is_archived(self):
        self.add_operation(
            self.position["id"],
            {
                "kind": "sell",
                "date": self.today.isoformat(),
                "quantity": "10",
                "unit_price": "110.00",
            },
        )
        self.client.patch(
            reverse("finance-investment-detail", args=[self.position["id"]]),
            {"archived": True},
            format="json",
        )
        response = self.add_operation(
            self.position["id"],
            {
                "kind": "dividend",
                "date": self.today.isoformat(),
                "amount": "1.00",
            },
        )
        self.assertEqual(response.status_code, 400)


class AccountSettingTests(InvestmentApiTestBase):
    def test_change_account_keeps_past_operations_on_old_account(self):
        first = self.create_account("Primo", initial="1000.00")
        second = self.create_account("Secondo", initial="1000.00")
        self.set_account(first["id"])
        position = self.create_position(
            opening={
                "date": self.today.isoformat(),
                "quantity": "10",
                "total_cost": "1000.00",
            }
        ).data
        old_buy = self.add_operation(
            position["id"],
            {
                "kind": "buy",
                "date": self.today.isoformat(),
                "quantity": "1",
                "unit_price": "100.00",
            },
        ).data

        response = self.set_account(second["id"])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["investment_account"]["id"], second["id"])

        new_buy = self.add_operation(
            position["id"],
            {
                "kind": "buy",
                "date": self.today.isoformat(),
                "quantity": "1",
                "unit_price": "100.00",
            },
        ).data
        self.assertEqual(
            InvestmentOperation.objects.get(pk=old_buy["id"])
            .transaction.lines.get()
            .account_id,
            first["id"],
        )
        self.assertEqual(
            InvestmentOperation.objects.get(pk=new_buy["id"])
            .transaction.lines.get()
            .account_id,
            second["id"],
        )

    def test_account_must_belong_to_profile(self):
        other = User.objects.create_user(
            email="altro-profilo@example.com",
            password="Spendy-Investimenti-2026",
            status=User.Status.ACTIVE,
        )
        other_profile = Profile.objects.create(user=other)
        foreign = Account.objects.create(
            profile=other_profile, name="Estero", initial_balance=D("10.00")
        )
        response = self.set_account(foreign.id)
        self.assertEqual(response.status_code, 400)

    def test_archived_account_cannot_be_assigned(self):
        account = self.create_account()
        Account.objects.filter(pk=account["id"]).update(archived=True)
        response = self.set_account(account["id"])
        self.assertEqual(response.status_code, 400)

    def test_assigned_account_cannot_be_deleted_or_archived(self):
        account = self.create_account(initial="100.00")
        self.set_account(account["id"])

        response = self.client.patch(
            reverse("finance-account-detail", args=[account["id"]]),
            {"archived": True},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("investimenti", response.data["detail"])

        response = self.client.delete(
            reverse("finance-account-detail", args=[account["id"]])
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("investimenti", response.data["detail"])

    def test_operation_on_archived_account_is_rejected(self):
        account = self.create_account(initial="1000.00")
        self.set_account(account["id"])
        position = self.create_position(
            opening={
                "date": self.today.isoformat(),
                "quantity": "10",
                "total_cost": "1000.00",
            }
        ).data
        Account.objects.filter(pk=account["id"]).update(archived=True)

        response = self.add_operation(
            position["id"],
            {
                "kind": "buy",
                "date": self.today.isoformat(),
                "quantity": "1",
                "unit_price": "100.00",
            },
        )
        self.assertEqual(response.status_code, 400)


class DashboardIntegrationTests(InvestmentApiTestBase):
    def setUp(self):
        super().setUp()
        self.account = self.create_account(initial="1000.00")
        self.set_account(self.account["id"])
        self.position = self.create_position(
            current_price="110.00",
            opening={
                "date": self.today.isoformat(),
                "quantity": "10",
                "total_cost": "500.00",
            },
        ).data
        self.add_operation(
            self.position["id"],
            {
                "kind": "buy",
                "date": self.today.isoformat(),
                "quantity": "2",
                "unit_price": "100.00",
                "commission": "1.50",
            },
        )
        self.add_operation(
            self.position["id"],
            {
                "kind": "sell",
                "date": self.today.isoformat(),
                "quantity": "1",
                "unit_price": "110.00",
                "commission": "1.00",
            },
        )
        self.add_operation(
            self.position["id"],
            {
                "kind": "dividend",
                "date": self.today.isoformat(),
                "amount": "12.40",
            },
        )

    def test_dashboard_investment_totals(self):
        response = self.dashboard(start="2000-01-01", end=self.today.isoformat())
        self.assertEqual(response.status_code, 200)
        data = response.data
        self.assertEqual(data["total_investments_cost"], "643.04")
        self.assertEqual(data["total_investments_value"], "1210.00")
        self.assertEqual(data["total_investments_unrealized"], "566.96")
        self.assertEqual(data["positions_without_price"], 0)
        self.assertEqual(data["period_investments_realized"], "50.54")
        self.assertEqual(data["period_dividends"], "12.40")

        self.assertEqual(data["total_balance"], "919.90")
        self.assertEqual(data["total_patrimony"], "1562.94")
        self.assertEqual(data["period_balance"], "919.90")
        self.assertEqual(data["income_total"], "12.40")
        self.assertEqual(data["expense_total"], "0.00")

    def test_recent_transactions_exclude_investments(self):
        response = self.dashboard(start="2000-01-01", end=self.today.isoformat())
        kinds = [item["kind"] for item in response.data["recent_transactions"]]
        self.assertNotIn(Transaction.Kind.INVESTMENT_BUY, kinds)
        self.assertNotIn(Transaction.Kind.INVESTMENT_SELL, kinds)
        self.assertNotIn(Transaction.Kind.INVESTMENT_DIVIDEND, kinds)

    def test_position_without_price_is_counted(self):
        self.create_position(
            name="Senza prezzo",
            opening={
                "date": self.today.isoformat(),
                "quantity": "1",
                "total_cost": "10.00",
            },
        )
        response = self.dashboard(start="2000-01-01", end=self.today.isoformat())
        self.assertEqual(response.data["positions_without_price"], 1)
        self.assertEqual(response.data["total_investments_cost"], "653.04")

    def test_transaction_register_and_export_exclude_investments(self):
        listing = self.client.get(reverse("finance-transactions"))
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.data["count"], 1)
        self.assertEqual(listing.data["transactions"][0]["kind"], "opening")

        export = self.client.get(reverse("finance-export"))
        text = export.content.decode("utf-8-sig")
        self.assertNotIn("Acquisto investimento", text)
        self.assertNotIn("Vendita investimento", text)
        self.assertNotIn("Dividendo", text)

    def test_investment_movement_cannot_be_edited_from_register(self):
        movement = Transaction.objects.get(kind=Transaction.Kind.INVESTMENT_BUY)
        response = self.client.patch(
            reverse("finance-transaction-detail", args=[movement.id]),
            {"kind": "expense", "date": self.today.isoformat(), "amount": "1.00"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Investimenti", response.data["detail"])

        response = self.client.delete(
            reverse("finance-transaction-detail", args=[movement.id])
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Investimenti", response.data["detail"])
        self.assertTrue(Transaction.objects.filter(pk=movement.id).exists())


class IsolationTests(InvestmentApiTestBase):
    def test_other_profile_cannot_see_or_touch_investments(self):
        account = self.create_account(initial="1000.00")
        self.set_account(account["id"])
        position = self.create_position(
            opening={
                "date": self.today.isoformat(),
                "quantity": "10",
                "total_cost": "1000.00",
            }
        ).data

        other = User.objects.create_user(
            email="isolato@example.com",
            password="Spendy-Investimenti-2026",
            status=User.Status.ACTIVE,
        )
        self.client.force_authenticate(user=other)

        listing = self.client.get(reverse("finance-investments"))
        self.assertEqual(listing.data["positions"], [])
        self.assertIsNone(listing.data["investment_account"])

        self.assertEqual(self.detail(position["id"]).status_code, 400)
        response = self.add_operation(
            position["id"],
            {
                "kind": "dividend",
                "date": self.today.isoformat(),
                "amount": "1.00",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(InvestmentOperation.objects.filter(profile__user=other).count(), 0)

    def test_global_admin_has_no_access(self):
        admin = User.objects.get(is_global_admin=True)
        self.client.force_authenticate(user=admin)
        response = self.client.get(reverse("finance-investments"))
        self.assertEqual(response.status_code, 403)
        response = self.client.put(
            reverse("finance-investment-account"), {"account": None}, format="json"
        )
        self.assertEqual(response.status_code, 403)


class SavingsInvestmentSourceTests(InvestmentApiTestBase):
    """Il denaro degli investimenti può arrivare da un salvadanaio."""

    def setUp(self):
        super().setUp()
        self.account = self.create_account(initial="1000.00")
        savings = self.client.post(
            reverse("finance-savings"),
            {"name": "Riserva", "backing_account": self.account["id"]},
            format="json",
        )
        self.assertEqual(savings.status_code, 201)
        self.savings = savings.data
        moved = self.client.post(
            reverse("finance-transactions"),
            {
                "kind": "transfer",
                "date": self.today.isoformat(),
                "amount": "500.00",
                "from_account": self.account["id"],
                "to_savings": self.savings["id"],
            },
            format="json",
        )
        self.assertEqual(moved.status_code, 201)
        self.position = self.create_position(
            current_price="110.00",
            opening={
                "date": self.today.isoformat(),
                "quantity": "10",
                "total_cost": "1000.00",
            },
        ).data

    def set_savings(self):
        return self.client.put(
            reverse("finance-investment-account"),
            {"savings": self.savings["id"]},
            format="json",
        )

    def balances(self):
        self.account = self.client.get(
            reverse("finance-account-detail", args=[self.account["id"]])
        ).data
        self.savings = self.client.get(
            reverse("finance-savings-detail", args=[self.savings["id"]])
        ).data
        return D(self.account["balance"]), D(self.savings["balance"])

    def test_selecting_savings_clears_the_account(self):
        response = self.set_savings()
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data["investment_account"])
        self.assertEqual(response.data["investment_savings"]["id"], self.savings["id"])
        listing = self.client.get(reverse("finance-investments"))
        self.assertEqual(listing.data["investment_savings"]["id"], self.savings["id"])
        self.assertIsNone(listing.data["investment_account"])

    def test_buy_comes_from_savings_and_leaves_account_untouched(self):
        self.set_savings()
        account_before, savings_before = self.balances()
        response = self.add_operation(
            self.position["id"],
            {
                "kind": "buy",
                "date": self.today.isoformat(),
                "quantity": "2",
                "unit_price": "100.00",
                "commission": "1.50",
            },
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["cash_amount"], "201.50")
        account_after, savings_after = self.balances()
        self.assertEqual(account_after, account_before)
        self.assertEqual(savings_after, savings_before - D("201.50"))
        movement = Transaction.objects.get(kind=Transaction.Kind.INVESTMENT_BUY)
        self.assertEqual(movement.lines.count(), 3)
        self.assertEqual(
            movement.lines.get(savings__isnull=False).amount, D("-201.50")
        )

    def test_sell_returns_money_to_savings(self):
        self.set_savings()
        _, savings_before = self.balances()
        response = self.add_operation(
            self.position["id"],
            {
                "kind": "sell",
                "date": self.today.isoformat(),
                "quantity": "1",
                "unit_price": "120.00",
            },
        )
        self.assertEqual(response.status_code, 201)
        _, savings_after = self.balances()
        self.assertEqual(savings_after, savings_before + D("120.00"))

    def test_insufficient_savings_balance_is_rejected(self):
        self.set_savings()
        response = self.add_operation(
            self.position["id"],
            {
                "kind": "buy",
                "date": self.today.isoformat(),
                "quantity": "100",
                "unit_price": "100.00",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            InvestmentOperation.objects.filter(kind="buy").count(), 0
        )

    def test_edit_and_delete_keep_savings_consistent(self):
        self.set_savings()
        _, savings_before = self.balances()
        buy = self.add_operation(
            self.position["id"],
            {
                "kind": "buy",
                "date": self.today.isoformat(),
                "quantity": "2",
                "unit_price": "100.00",
            },
        )
        self.assertEqual(buy.status_code, 201)
        _, after_buy = self.balances()
        self.assertEqual(after_buy, savings_before - D("200.00"))

        edited = self.client.patch(
            reverse("finance-investment-operation-detail", args=[buy.data["id"]]),
            {"quantity": "1"},
            format="json",
        )
        self.assertEqual(edited.status_code, 200)
        account_after, savings_after = self.balances()
        self.assertEqual(savings_after, savings_before - D("100.00"))
        self.assertEqual(account_after, D("500.00"))

        deleted = self.client.delete(
            reverse("finance-investment-operation-detail", args=[buy.data["id"]])
        )
        self.assertEqual(deleted.status_code, 204)
        _, savings_final = self.balances()
        self.assertEqual(savings_final, savings_before)


class AutoArchiveTests(InvestmentApiTestBase):
    def setUp(self):
        super().setUp()
        self.account = self.create_account(initial="1000.00")
        self.set_account(self.account["id"])
        self.position = self.create_position(
            opening={
                "date": self.today.isoformat(),
                "quantity": "2",
                "unit_price": "100.00",
            }
        ).data

    def test_selling_everything_archives_the_position(self):
        sell = self.add_operation(
            self.position["id"],
            {
                "kind": "sell",
                "date": self.today.isoformat(),
                "quantity": "2",
                "unit_price": "110.00",
            },
        )
        self.assertEqual(sell.status_code, 201)
        position = InvestmentPosition.objects.get(pk=self.position["id"])
        self.assertIs(position.archived, True)
        listing = self.client.get(reverse("finance-investments"))
        row = next(p for p in listing.data["positions"] if p["id"] == self.position["id"])
        self.assertTrue(row["archived"])

    def test_deleting_the_closing_sell_reactivates(self):
        sell = self.add_operation(
            self.position["id"],
            {
                "kind": "sell",
                "date": self.today.isoformat(),
                "quantity": "2",
                "unit_price": "110.00",
            },
        ).data
        deleted = self.client.delete(
            reverse("finance-investment-operation-detail", args=[sell["id"]])
        )
        self.assertEqual(deleted.status_code, 204)
        position = InvestmentPosition.objects.get(pk=self.position["id"])
        self.assertIs(position.archived, False)

    def test_new_empty_position_is_not_auto_archived(self):
        empty = self.create_position(name="Solo idea").data
        position = InvestmentPosition.objects.get(pk=empty["id"])
        self.assertIs(position.archived, False)


class TwoOfThreeValuesTests(InvestmentApiTestBase):
    """Quantità, prezzo e totale: bastano due valori, il terzo si ricava."""

    def setUp(self):
        super().setUp()
        self.account = self.create_account(initial="5000.00")
        self.set_account(self.account["id"])
        self.position = self.create_position(
            opening={
                "date": self.today.isoformat(),
                "quantity": "10",
                "unit_price": "100.00",
            }
        ).data

    def test_buy_with_price_and_total_derives_quantity(self):
        response = self.add_operation(
            self.position["id"],
            {
                "kind": "buy",
                "date": self.today.isoformat(),
                "unit_price": "100.00",
                "total_amount": "250.00",
            },
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Decimal(response.data["quantity"]), D("2.5"))
        self.assertEqual(response.data["gross_amount"], "250.00")

    def test_three_values_are_rejected(self):
        response = self.add_operation(
            self.position["id"],
            {
                "kind": "buy",
                "date": self.today.isoformat(),
                "quantity": "2",
                "unit_price": "100.00",
                "total_amount": "200.00",
            },
        )
        self.assertEqual(response.status_code, 400)

    def test_edit_with_price_and_total_derives_quantity(self):
        buy = self.add_operation(
            self.position["id"],
            {
                "kind": "buy",
                "date": self.today.isoformat(),
                "quantity": "1",
                "unit_price": "100.00",
            },
        ).data
        edited = self.client.patch(
            reverse("finance-investment-operation-detail", args=[buy["id"]]),
            {"unit_price": "200.00", "total_amount": "300.00"},
            format="json",
        )
        self.assertEqual(edited.status_code, 200)
        self.assertEqual(Decimal(edited.data["quantity"]), D("1.5"))

    def test_opening_with_price_and_total(self):
        response = self.create_position(
            name="Senza quantità",
            opening={
                "date": self.today.isoformat(),
                "unit_price": "50.00",
                "total_cost": "500.00",
            },
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Decimal(response.data["quantity"]), D("10"))
