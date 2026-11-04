from datetime import date
from decimal import Decimal

from django.db.models.deletion import ProtectedError
from django.test import TestCase
from rest_framework.exceptions import ValidationError

from accounts.models import User
from .investments import (
    create_operation,
    delete_operation,
    portfolio_summary,
    position_summary,
    recalculate_position,
    set_investment_account,
    set_position_archived,
    update_operation,
)
from .models import (
    Account,
    InvestmentOperation,
    InvestmentPosition,
    Line,
    Profile,
    Transaction,
)

D = Decimal


class InvestmentTestBase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="investimenti@example.com",
            password="Spendy-Investimenti-2026",
            status=User.Status.ACTIVE,
        )
        self.profile = Profile.objects.create(user=self.user)
        self.today = date(2026, 2, 1)
        self.start = date(2026, 1, 1)

    def make_account(self, name="Conto", initial="1000.00", profile=None):
        profile = profile or self.profile
        account = Account.objects.create(
            profile=profile, name=name, initial_balance=D(initial)
        )
        if D(initial) != 0:
            movement = Transaction.objects.create(
                profile=profile,
                kind=Transaction.Kind.OPENING,
                date=self.start,
                description="Saldo iniziale",
                amount=D(initial),
            )
            Line.objects.create(
                transaction=movement, account=account, amount=D(initial)
            )
        return account

    def make_position(self, name="ETF Mondo", current_price=None):
        return InvestmentPosition.objects.create(
            profile=self.profile, name=name, current_price=current_price
        )

    def opening(self, position, quantity="10", total="1000.00", day=None):
        return create_operation(
            position,
            kind=InvestmentOperation.Kind.OPENING,
            date=day or self.start,
            quantity=quantity,
            total_amount=total,
        )

    def buy(self, position, quantity="2", unit_price="100.00", commission="0.00", day=None):
        return create_operation(
            position,
            kind=InvestmentOperation.Kind.BUY,
            date=day or self.today,
            quantity=quantity,
            unit_price=unit_price,
            commission=commission,
        )

    def sell(self, position, quantity="2", unit_price="110.00", commission="0.00", day=None):
        return create_operation(
            position,
            kind=InvestmentOperation.Kind.SELL,
            date=day or self.today,
            quantity=quantity,
            unit_price=unit_price,
            commission=commission,
        )

    def dividend(self, position, amount="12.40", day=None):
        return create_operation(
            position,
            kind=InvestmentOperation.Kind.DIVIDEND,
            date=day or self.today,
            amount=amount,
        )


class OpeningTests(InvestmentTestBase):
    def test_opening_sets_quantity_and_cost_without_account_movement(self):
        account = self.make_account()
        set_investment_account(self.profile, account)
        position = self.make_position()
        transactions_before = Transaction.objects.count()
        lines_before = Line.objects.count()

        operation = self.opening(position, quantity="10", total="1000.00")
        ledger = recalculate_position(position)

        self.assertIsNone(operation.transaction)
        self.assertEqual(Transaction.objects.count(), transactions_before)
        self.assertEqual(Line.objects.count(), lines_before)
        self.assertEqual(ledger["quantity"], D("10"))
        self.assertEqual(ledger["cost"], D("1000.00"))
        self.assertEqual(ledger["average_cost"], D("100"))
        self.assertEqual(account.balance, D("1000.00"))

    def test_opening_is_allowed_without_investment_account(self):
        position = self.make_position()
        self.opening(position)
        self.assertEqual(recalculate_position(position)["quantity"], D("10"))

    def test_only_one_opening_per_position(self):
        position = self.make_position()
        self.opening(position)
        with self.assertRaises(ValidationError):
            self.opening(position)

    def test_opening_after_other_operations_is_rejected(self):
        position = self.make_position()
        set_investment_account(self.profile, self.make_account("Banca"))
        self.buy(position)
        with self.assertRaises(ValidationError):
            self.opening(position)

    def test_opening_unit_price_derived_from_total(self):
        position = self.make_position()
        operation = self.opening(position, quantity="3", total="100.00")
        self.assertEqual(operation.unit_price, D("33.33333333"))
        self.assertEqual(operation.gross_amount, D("100.00"))
        self.assertEqual(operation.cash_amount, D("0.00"))


class BuyTests(InvestmentTestBase):
    def setUp(self):
        super().setUp()
        self.account = self.make_account()
        set_investment_account(self.profile, self.account)

    def test_buy_adds_quantity_cost_and_commission(self):
        position = self.make_position()
        self.opening(position, quantity="10", total="1000.00")
        operation = self.buy(
            position, quantity="2", unit_price="102.50", commission="1.50"
        )
        ledger = recalculate_position(position)

        self.assertEqual(operation.gross_amount, D("205.00"))
        self.assertEqual(operation.cash_amount, D("206.50"))
        self.assertEqual(operation.transaction.kind, Transaction.Kind.INVESTMENT_BUY)
        self.assertEqual(operation.transaction.amount, D("206.50"))
        line = operation.transaction.lines.get()
        self.assertEqual(line.amount, D("-206.50"))
        self.assertEqual(line.account_id, self.account.id)
        self.assertEqual(self.account.balance, D("793.50"))
        self.assertEqual(ledger["quantity"], D("12"))
        self.assertEqual(ledger["cost"], D("1206.50"))
        self.assertEqual(ledger["average_cost"], D("100.54166667"))

    def test_buy_with_total_amount(self):
        position = self.make_position()
        self.opening(position)
        operation = create_operation(
            position,
            kind=InvestmentOperation.Kind.BUY,
            date=self.today,
            quantity="2",
            total_amount="205.00",
            commission="1.50",
        )
        self.assertEqual(operation.unit_price, D("102.5"))
        self.assertEqual(operation.gross_amount, D("205.00"))
        self.assertEqual(operation.cash_amount, D("206.50"))

    def test_buy_rejected_when_account_would_go_negative(self):
        account = self.make_account("Scarso", initial="50.00")
        set_investment_account(self.profile, account)
        position = self.make_position()
        self.opening(position, quantity="10", total="1000.00")
        with self.assertRaises(ValidationError):
            self.buy(position, quantity="1", unit_price="100.00")
        self.assertEqual(
            InvestmentOperation.objects.filter(kind=InvestmentOperation.Kind.BUY).count(),
            0,
        )
        self.assertEqual(
            Transaction.objects.filter(kind=Transaction.Kind.INVESTMENT_BUY).count(),
            0,
        )

    def test_buy_rejected_without_investment_account(self):
        set_investment_account(self.profile, None)
        position = self.make_position()
        with self.assertRaises(ValidationError):
            self.buy(position)


class SellTests(InvestmentTestBase):
    def setUp(self):
        super().setUp()
        self.account = self.make_account()
        set_investment_account(self.profile, self.account)

    def test_partial_sell_uses_average_cost_and_realized_gain(self):
        position = self.make_position()
        self.opening(position, quantity="10", total="1000.00")
        self.buy(position, quantity="2", unit_price="100.00", commission="1.50")
        operation = self.sell(
            position, quantity="2", unit_price="110.00", commission="1.00"
        )
        ledger = recalculate_position(position)

        self.assertEqual(operation.gross_amount, D("220.00"))
        self.assertEqual(operation.cash_amount, D("219.00"))
        self.assertEqual(operation.transaction.kind, Transaction.Kind.INVESTMENT_SELL)
        self.assertEqual(self.account.balance, D("1017.50"))
        self.assertEqual(ledger["quantity"], D("10"))
        self.assertEqual(ledger["cost"], D("1001.25"))
        self.assertEqual(ledger["realized_gain"], D("18.75"))
        row = ledger["operations"][-1]
        self.assertEqual(row["cost_removed"], D("200.25"))
        self.assertEqual(row["realized_gain"], D("18.75"))

    def test_total_sell_zeroes_cost(self):
        position = self.make_position()
        self.opening(position, quantity="10", total="1000.00")
        self.sell(position, quantity="10", unit_price="120.00", commission="1.00")
        ledger = recalculate_position(position)

        self.assertEqual(ledger["quantity"], D("0"))
        self.assertEqual(ledger["cost"], D("0"))
        self.assertEqual(ledger["average_cost"], D("0"))
        self.assertEqual(ledger["realized_gain"], D("199.00"))

    def test_sell_above_quantity_is_rejected(self):
        position = self.make_position()
        self.opening(position, quantity="10", total="1000.00")
        with self.assertRaises(ValidationError):
            self.sell(position, quantity="11", unit_price="110.00")
        self.assertEqual(
            InvestmentOperation.objects.filter(
                position=position, kind=InvestmentOperation.Kind.SELL
            ).count(),
            0,
        )

    def test_sell_with_commission_above_gross_is_rejected(self):
        position = self.make_position()
        self.opening(position, quantity="10", total="1000.00")
        with self.assertRaises(ValidationError):
            self.sell(position, quantity="1", unit_price="10.00", commission="10.00")

    def test_sell_cash_never_makes_account_negative(self):
        position = self.make_position()
        self.opening(position, quantity="10", total="1000.00")
        self.sell(position, quantity="5", unit_price="100.00")
        self.assertEqual(self.account.balance, D("1500.00"))


class DividendTests(InvestmentTestBase):
    def test_dividend_increases_cash_and_keeps_cost(self):
        account = self.make_account()
        set_investment_account(self.profile, account)
        position = self.make_position()
        self.opening(position, quantity="10", total="1000.00")
        operation = self.dividend(position, amount="12.40")
        ledger = recalculate_position(position)

        self.assertIsNone(operation.quantity)
        self.assertIsNone(operation.unit_price)
        self.assertIsNone(operation.gross_amount)
        self.assertEqual(operation.cash_amount, D("12.40"))
        self.assertEqual(operation.transaction.kind, Transaction.Kind.INVESTMENT_DIVIDEND)
        self.assertEqual(operation.transaction.lines.get().amount, D("12.40"))
        self.assertEqual(account.balance, D("1012.40"))
        self.assertEqual(ledger["quantity"], D("10"))
        self.assertEqual(ledger["cost"], D("1000.00"))
        self.assertEqual(ledger["dividends"], D("12.40"))

    def test_dividend_rejects_quantity(self):
        account = self.make_account()
        set_investment_account(self.profile, account)
        position = self.make_position()
        with self.assertRaises(ValidationError):
            create_operation(
                position,
                kind=InvestmentOperation.Kind.DIVIDEND,
                date=self.today,
                amount="10.00",
                quantity="1",
            )


class EditAndDeleteTests(InvestmentTestBase):
    def setUp(self):
        super().setUp()
        self.account = self.make_account(initial="10000.00")
        set_investment_account(self.profile, self.account)

    def test_edit_buy_recalculates_later_sell(self):
        position = self.make_position()
        self.opening(position, quantity="10", total="1000.00")
        buy = self.buy(position, quantity="10", unit_price="100.00")
        sell = self.sell(position, quantity="5", unit_price="120.00")
        before = recalculate_position(position)
        self.assertEqual(before["realized_gain"], D("100.00"))

        update_operation(buy, unit_price="200.00")
        after = recalculate_position(position)
        self.assertEqual(after["cost"], D("2250.00"))
        self.assertEqual(after["realized_gain"], D("-150.00"))
        sell_row = [row for row in after["operations"] if row["operation"].pk == sell.pk][0]
        self.assertEqual(sell_row["cost_removed"], D("750.00"))

    def test_edit_that_makes_sell_invalid_is_rolled_back(self):
        position = self.make_position()
        opening = self.opening(position, quantity="10", total="1000.00")
        self.sell(position, quantity="5", unit_price="120.00")
        with self.assertRaises(ValidationError):
            update_operation(opening, quantity="4")
        opening.refresh_from_db()
        self.assertEqual(opening.quantity, D("10"))
        self.assertEqual(recalculate_position(position)["quantity"], D("5"))

    def test_delete_buy_that_invalidates_sell_is_rejected(self):
        position = self.make_position()
        self.opening(position, quantity="10", total="1000.00")
        buy = self.buy(position, quantity="5", unit_price="100.00")
        self.sell(position, quantity="12", unit_price="120.00")
        with self.assertRaises(ValidationError):
            delete_operation(buy)
        self.assertTrue(InvestmentOperation.objects.filter(pk=buy.pk).exists())
        self.assertEqual(recalculate_position(position)["quantity"], D("3"))

    def test_delete_sell_recalculates_ledger(self):
        position = self.make_position()
        self.opening(position, quantity="10", total="1000.00")
        sell = self.sell(position, quantity="4", unit_price="120.00")
        delete_operation(sell)
        ledger = recalculate_position(position)
        self.assertEqual(ledger["quantity"], D("10"))
        self.assertEqual(ledger["cost"], D("1000.00"))
        self.assertEqual(ledger["realized_gain"], D("0"))
        self.assertFalse(
            Transaction.objects.filter(kind=Transaction.Kind.INVESTMENT_SELL).exists()
        )

    def test_delete_dividend_removes_account_movement(self):
        position = self.make_position()
        self.opening(position, quantity="10", total="1000.00")
        dividend = self.dividend(position, amount="12.40")
        delete_operation(dividend)
        self.assertEqual(self.account.balance, D("10000.00"))
        self.assertFalse(
            Transaction.objects.filter(
                kind=Transaction.Kind.INVESTMENT_DIVIDEND
            ).exists()
        )

    def test_kind_cannot_be_changed_through_update(self):
        position = self.make_position()
        self.opening(position, quantity="10", total="1000.00")
        buy = self.buy(position)
        update_operation(buy, date=self.today, quantity="3")
        buy.refresh_from_db()
        self.assertEqual(buy.kind, InvestmentOperation.Kind.BUY)


class DeleteAccountBalanceTests(InvestmentTestBase):
    """Deleting a cash-in operation must not leave the account negative."""

    def setUp(self):
        super().setUp()
        self.account = self.make_account(initial="100.00")
        set_investment_account(self.profile, self.account)
        self.position = self.make_position()
        self.opening(self.position, quantity="10", total="1000.00")

    def spend(self, amount, day):
        movement = Transaction.objects.create(
            profile=self.profile,
            kind=Transaction.Kind.EXPENSE,
            date=day,
            description="Spesa",
            amount=D(amount),
        )
        Line.objects.create(
            transaction=movement, account=self.account, amount=-D(amount)
        )
        return movement

    def test_delete_sell_that_would_make_account_negative_is_rejected(self):
        sell = self.sell(self.position, quantity="5", unit_price="200.00")
        self.spend("900.00", date(2026, 2, 10))
        self.assertEqual(self.account.balance, D("200.00"))

        with self.assertRaises(ValidationError):
            delete_operation(sell)

        self.assertTrue(InvestmentOperation.objects.filter(pk=sell.pk).exists())
        self.assertTrue(
            Transaction.objects.filter(kind=Transaction.Kind.INVESTMENT_SELL).exists()
        )
        self.assertEqual(self.account.balance, D("200.00"))

    def test_delete_dividend_that_would_make_account_negative_is_rejected(self):
        dividend = self.dividend(self.position, amount="100.00")
        self.spend("200.00", date(2026, 2, 10))
        self.assertEqual(self.account.balance, D("0.00"))

        with self.assertRaises(ValidationError):
            delete_operation(dividend)

        self.assertTrue(InvestmentOperation.objects.filter(pk=dividend.pk).exists())
        self.assertEqual(self.account.balance, D("0.00"))

    def test_delete_without_balance_impact_is_allowed(self):
        dividend = self.dividend(self.position, amount="100.00")
        self.assertEqual(self.account.balance, D("200.00"))

        delete_operation(dividend)

        self.assertEqual(self.account.balance, D("100.00"))
        self.assertFalse(
            InvestmentOperation.objects.filter(pk=dividend.pk).exists()
        )


class PositionRulesTests(InvestmentTestBase):
    def test_current_value_and_unrealized_gain(self):
        position = self.make_position(current_price=D("105.20"))
        self.opening(position, quantity="10", total="1000.00")
        ledger = recalculate_position(position)
        self.assertTrue(ledger["has_price"])
        self.assertEqual(ledger["current_value"], D("1052.00"))
        self.assertEqual(ledger["unrealized_gain"], D("52.00"))

    def test_position_without_price_has_no_value(self):
        position = self.make_position()
        self.opening(position, quantity="10", total="1000.00")
        ledger = recalculate_position(position)
        self.assertFalse(ledger["has_price"])
        self.assertIsNone(ledger["current_value"])
        self.assertIsNone(ledger["unrealized_gain"])

    def test_position_cannot_be_deleted_with_operations(self):
        position = self.make_position()
        self.opening(position)
        with self.assertRaises(ProtectedError):
            position.delete()

    def test_archive_only_when_quantity_is_zero(self):
        account = self.make_account()
        set_investment_account(self.profile, account)
        position = self.make_position()
        self.opening(position, quantity="10", total="1000.00")
        with self.assertRaises(ValidationError):
            set_position_archived(position, True)

        self.sell(position, quantity="10", unit_price="100.00")
        set_position_archived(position, True)
        position.refresh_from_db()
        self.assertTrue(position.archived)
        with self.assertRaises(ValidationError):
            self.buy(position)

    def test_fractional_quantity_rounding(self):
        account = self.make_account()
        set_investment_account(self.profile, account)
        position = self.make_position()
        self.opening(position, quantity="3", total="100.00")
        self.buy(position, quantity="0.5", unit_price="33.33333333")
        self.sell(position, quantity="0.25", unit_price="40.00", commission="0.10")
        ledger = recalculate_position(position)
        self.assertEqual(ledger["quantity"], D("3.25"))
        self.assertEqual(ledger["cost"], D("108.34"))
        self.assertEqual(ledger["realized_gain"], D("1.57"))

    def test_money_rounding_is_commercial(self):
        position = self.make_position()
        operation = self.opening(position, quantity="1", total="0.005")
        self.assertEqual(operation.gross_amount, D("0.01"))


class AccountTests(InvestmentTestBase):
    def test_set_investment_account_validates_profile(self):
        other_user = User.objects.create_user(
            email="altro@example.com",
            password="Spendy-Investimenti-2026",
            status=User.Status.ACTIVE,
        )
        other_profile = Profile.objects.create(user=other_user)
        other_account = self.make_account("Altro", profile=other_profile)
        with self.assertRaises(ValidationError):
            set_investment_account(self.profile, other_account)

    def test_archived_account_cannot_be_assigned(self):
        account = self.make_account()
        account.archived = True
        account.save(update_fields=("archived",))
        with self.assertRaises(ValidationError):
            set_investment_account(self.profile, account)

    def test_operation_rejected_on_archived_account(self):
        account = self.make_account()
        set_investment_account(self.profile, account)
        position = self.make_position()
        self.opening(position)
        account.archived = True
        account.save(update_fields=("archived",))
        with self.assertRaises(ValidationError):
            self.buy(position)

    def test_changing_account_keeps_past_operations_on_old_account(self):
        first = self.make_account("Primo")
        second = self.make_account("Secondo")
        set_investment_account(self.profile, first)
        position = self.make_position()
        self.opening(position, quantity="10", total="1000.00")
        old_buy = self.buy(position, quantity="1", unit_price="100.00")
        self.assertEqual(old_buy.transaction.lines.get().account_id, first.id)

        set_investment_account(self.profile, second)
        new_buy = self.buy(position, quantity="1", unit_price="100.00")
        self.assertEqual(new_buy.transaction.lines.get().account_id, second.id)
        self.assertEqual(old_buy.transaction.lines.get().account_id, first.id)

        update_operation(old_buy, quantity="2")
        self.assertEqual(old_buy.transaction.lines.get().account_id, first.id)

    def test_portfolio_summary_aggregates_positions(self):
        account = self.make_account()
        set_investment_account(self.profile, account)
        first = self.make_position("ETF", current_price=D("110.00"))
        second = self.make_position("Azione")
        self.opening(first, quantity="10", total="1000.00")
        self.opening(second, quantity="5", total="500.00")
        summary = portfolio_summary(self.profile)
        self.assertEqual(summary["total_cost"], D("1500.00"))
        self.assertEqual(summary["total_value"], D("1100.00"))
        self.assertEqual(summary["total_unrealized"], D("100.00"))
        self.assertEqual(summary["positions_without_price"], 1)

    def test_position_summary_matches_recalculation(self):
        position = self.make_position(current_price=D("105.20"))
        self.opening(position, quantity="10", total="1000.00")
        self.assertEqual(position_summary(position), recalculate_position(position))
