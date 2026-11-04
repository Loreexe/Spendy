from datetime import timedelta
from unittest import mock

from django.core.management import call_command
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from .models import (
    Account,
    Automation,
    AutomationExecution,
    Notification,
    Transaction,
)
from .test_automations import AutomationTestBase


class RecurringExpenseTestBase(AutomationTestBase):
    def create_expense(
        self,
        *,
        next_run_on=None,
        frequency="monthly",
        amount="100.00",
        description="Netflix",
        source_account=None,
        **overrides,
    ):
        run_on = next_run_on or self.today
        if hasattr(run_on, "isoformat"):
            run_on = run_on.isoformat()
        payload = {
            "kind": "expense",
            "source_account": source_account or self.account["id"],
            "amount": amount,
            "description": description,
            "frequency": frequency,
            "next_run_on": run_on,
        }
        payload.update(overrides)
        return self.client.post(
            reverse("finance-automations"), payload, format="json"
        )


class RecurringExpenseCreationTests(RecurringExpenseTestBase):
    def test_create_recurring_expense(self):
        response = self.create_expense()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["kind"], "expense")
        self.assertEqual(response.data["kind_label"], "Spesa ricorrente")
        self.assertIsNone(response.data["savings"])
        self.assertIsNone(response.data["savings_name"])
        self.assertEqual(response.data["description"], "Netflix")
        self.assertEqual(response.data["source_account_name"], "Contanti")

    def test_expense_requires_description(self):
        response = self.create_expense(description="")
        self.assertEqual(response.status_code, 400)
        self.assertIn("description", response.data)

    def test_expense_rejects_savings_target(self):
        response = self.create_expense(savings=self.savings["id"])
        self.assertEqual(response.status_code, 400)
        self.assertIn("savings", response.data)

    def test_transfer_still_requires_savings(self):
        response = self.create_automation(kind="transfer", savings=None)
        self.assertEqual(response.status_code, 400)
        self.assertIn("savings", response.data)

    def test_kind_cannot_change_after_creation(self):
        rule = self.create_expense().data
        response = self.client.patch(
            reverse("finance-automation-detail", args=[rule["id"]]),
            {"kind": "transfer", "savings": self.savings["id"]},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("kind", response.data)


class RecurringExpenseExecutionTests(RecurringExpenseTestBase):
    def test_due_expense_creates_an_expense_transaction(self):
        rule = self.create_expense().data
        response = self.run_automation(rule["id"])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["outcome"]["executed"], 1)

        operation = Transaction.objects.get(
            profile=self.profile, automation_id=rule["id"]
        )
        self.assertEqual(operation.kind, Transaction.Kind.EXPENSE)
        self.assertEqual(operation.date, self.today)
        self.assertEqual(operation.amount, 100)
        self.assertEqual(operation.description, "Netflix")
        self.assertEqual(operation.lines.count(), 1)
        line = operation.lines.get()
        self.assertEqual(line.account_id, self.account["id"])
        self.assertEqual(line.amount, -100)
        self.assertIsNone(line.savings_id)
        self.assertEqual(Account.objects.get(pk=self.account["id"]).balance, 900)

        execution = AutomationExecution.objects.get(automation_ref=rule["id"])
        self.assertEqual(execution.kind, Automation.Kind.EXPENSE)
        self.assertEqual(execution.description, "Netflix")
        self.assertEqual(execution.status, AutomationExecution.Status.SUCCEEDED)

        detail = self.client.get(
            reverse("finance-transaction-detail", args=[operation.id])
        )
        self.assertEqual(detail.data["kind"], "expense")
        self.assertEqual(detail.data["automation_name"], "Netflix")

    def test_expense_is_not_duplicated(self):
        rule = self.create_expense().data
        self.run_automation(rule["id"])
        second = self.run_automation(rule["id"])
        self.assertEqual(second.data["outcome"]["executed"], 0)
        self.assertEqual(
            Transaction.objects.filter(
                profile=self.profile, automation_id=rule["id"]
            ).count(),
            1,
        )

    def test_insufficient_balance_skips_the_expense(self):
        poor = self.client.post(
            reverse("finance-accounts"),
            {"name": "Povero", "type": "cash", "initial_balance": "50.00"},
            format="json",
        ).data
        rule = self.create_expense(source_account=poor["id"]).data
        response = self.run_automation(rule["id"])
        self.assertEqual(response.status_code, 200)

        self.assertFalse(
            Transaction.objects.filter(
                profile=self.profile, automation_id=rule["id"]
            ).exists()
        )
        execution = AutomationExecution.objects.get(automation_ref=rule["id"])
        self.assertEqual(execution.status, AutomationExecution.Status.SKIPPED)
        self.assertEqual(
            execution.failure_code,
            AutomationExecution.FailureCode.INSUFFICIENT_BALANCE,
        )
        self.assertEqual(
            Automation.objects.get(pk=rule["id"]).status,
            Automation.Status.ACTIVE,
        )
        self.assertTrue(
            Notification.objects.filter(
                profile=self.profile,
                kind=Notification.Kind.AUTOMATION_SKIPPED,
                execution=execution,
            ).exists()
        )
        self.assertEqual(Account.objects.get(pk=poor["id"]).balance, 50)

    def test_missing_account_skips_the_expense(self):
        rule = self.create_expense().data
        self.client.patch(
            reverse("finance-account-detail", args=[self.account["id"]]),
            {"archived": True},
            format="json",
        )
        self.run_automation(rule["id"])
        execution = AutomationExecution.objects.get(automation_ref=rule["id"])
        self.assertEqual(execution.status, AutomationExecution.Status.SKIPPED)
        self.assertEqual(
            execution.failure_code, AutomationExecution.FailureCode.MISSING_DATA
        )
        self.assertFalse(
            Transaction.objects.filter(
                profile=self.profile, automation_id=rule["id"]
            ).exists()
        )

    def test_multiple_missed_expenses_require_a_choice(self):
        rule = self.create_expense(
            frequency="daily",
            next_run_on=(self.today - timedelta(days=1)).isoformat(),
        ).data
        response = self.run_automation(rule["id"])
        self.assertEqual(response.data["outcome"]["pending_choice"], 2)
        self.assertFalse(
            Transaction.objects.filter(
                profile=self.profile, automation_id=rule["id"]
            ).exists()
        )

        pending = self.executions(rule["id"], "pending")
        resolved = self.client.post(
            reverse("finance-automation-resolve", args=[rule["id"]]),
            {"recover": [pending[0]["id"]]},
            format="json",
        )
        self.assertEqual(resolved.status_code, 200)
        self.assertEqual(resolved.data["outcome"]["recovered"], 1)
        operation = Transaction.objects.get(
            profile=self.profile, automation_id=rule["id"]
        )
        self.assertEqual(operation.date, self.today - timedelta(days=1))
        self.assertEqual(operation.kind, Transaction.Kind.EXPENSE)

    def test_editing_and_deleting_the_generated_expense(self):
        rule = self.create_expense().data
        self.run_automation(rule["id"])
        operation = Transaction.objects.get(
            profile=self.profile, automation_id=rule["id"]
        )
        execution = AutomationExecution.objects.get(automation_ref=rule["id"])

        updated = self.client.patch(
            reverse("finance-transaction-detail", args=[operation.id]),
            {
                "kind": "expense",
                "date": self.today.isoformat(),
                "description": "Netflix corretto",
                "amount": "80.00",
                "account": self.account["id"],
            },
            format="json",
        )
        self.assertEqual(updated.status_code, 200)
        execution.refresh_from_db()
        self.assertTrue(execution.corrected)
        self.assertEqual(execution.status, AutomationExecution.Status.SUCCEEDED)

        deleted = self.client.delete(
            reverse("finance-transaction-detail", args=[operation.id])
        )
        self.assertEqual(deleted.status_code, 204)
        execution.refresh_from_db()
        self.assertEqual(execution.status, AutomationExecution.Status.CANCELLED)
        self.assertIsNone(execution.transaction_id)

        self.run_automation(rule["id"])
        self.assertFalse(
            Transaction.objects.filter(
                profile=self.profile, automation_id=rule["id"]
            ).exists()
        )

    def test_deleting_savings_does_not_remove_expense_rules(self):
        rule = self.create_expense().data
        response = self.client.delete(
            reverse("finance-savings-detail", args=[self.savings["id"]])
        )
        self.assertEqual(response.status_code, 204)
        self.assertTrue(Automation.objects.filter(pk=rule["id"]).exists())

    def test_dashboard_includes_the_automatic_expense(self):
        rule = self.create_expense().data
        self.run_automation(rule["id"])
        dashboard = self.client.get(reverse("finance-dashboard"))
        self.assertEqual(dashboard.data["expense_total"], "100.00")
        self.assertEqual(dashboard.data["total_balance"], "900.00")

    def test_management_command_processes_expenses(self):
        rule = self.create_expense().data
        call_command("run_automations")
        self.assertTrue(
            Transaction.objects.filter(
                profile=self.profile, automation_id=rule["id"]
            ).exists()
        )

    @override_settings(AUTOMATION_MAX_ATTEMPTS=1, AUTOMATION_RETRY_DELAYS=[0])
    def test_technical_failure_uses_the_expense_description(self):
        rule = self.create_expense().data
        with mock.patch(
            "finance.automations._apply_effect",
            side_effect=RuntimeError("errore tecnico"),
        ):
            self.run_automation(rule["id"])
        execution = AutomationExecution.objects.get(automation_ref=rule["id"])
        self.assertEqual(execution.status, AutomationExecution.Status.FAILED)
        notification = Notification.objects.get(
            profile=self.profile,
            kind=Notification.Kind.AUTOMATION_SUSPENDED,
        )
        self.assertIn("Netflix", notification.message)


class RecurringExpenseRuleLifecycleTests(RecurringExpenseTestBase):
    def test_paused_expense_does_not_run_until_resumed(self):
        rule = self.create_expense().data
        self.client.patch(
            reverse("finance-automation-detail", args=[rule["id"]]),
            {"status": "paused"},
            format="json",
        )
        self.run_automation(rule["id"])
        self.assertFalse(
            Transaction.objects.filter(
                profile=self.profile, automation_id=rule["id"]
            ).exists()
        )

        self.client.patch(
            reverse("finance-automation-detail", args=[rule["id"]]),
            {"status": "active"},
            format="json",
        )
        self.run_automation(rule["id"])
        self.assertTrue(
            Transaction.objects.filter(
                profile=self.profile, automation_id=rule["id"]
            ).exists()
        )

    def test_deleting_the_expense_rule_preserves_the_history(self):
        rule = self.create_expense().data
        self.run_automation(rule["id"])
        response = self.client.delete(
            reverse("finance-automation-detail", args=[rule["id"]])
        )
        self.assertEqual(response.status_code, 204)
        execution = AutomationExecution.objects.get(automation_ref=rule["id"])
        self.assertIsNone(execution.automation_id)
        self.assertEqual(execution.status, AutomationExecution.Status.SUCCEEDED)
        self.assertTrue(
            Transaction.objects.filter(
                profile=self.profile,
                description="Netflix",
            ).exists()
        )
