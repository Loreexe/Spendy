from datetime import timedelta
from unittest import mock

from django.core.management import call_command
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import User
from . import automations
from .models import (
    Account,
    AutomationExecution,
    Notification,
    Profile,
    Automation,
    Transaction,
)


class AutomationTestBase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="automazioni@example.com",
            password="Spendy-Fondamenta-2026",
            status=User.Status.ACTIVE,
        )
        self.client.force_authenticate(user=self.user)
        self.today = timezone.localdate()
        self.account = self.client.post(
            reverse("finance-accounts"),
            {"name": "Contanti", "type": "cash", "initial_balance": "0.00"},
            format="json",
        ).data
        self.client.post(
            reverse("finance-transactions"),
            {
                "kind": "income",
                "date": (self.today - timedelta(days=10)).isoformat(),
                "description": "Saldo di partenza",
                "amount": "1000.00",
                "account": self.account["id"],
            },
            format="json",
        )
        self.savings = self.client.post(
            reverse("finance-savings"),
            {"name": "Salute", "backing_account": self.account["id"]},
            format="json",
        ).data
        self.profile = Profile.objects.get(user=self.user)

    def create_automation(self, **overrides):
        payload = {
            "savings": self.savings["id"],
            "source_account": self.account["id"],
            "amount": "100.00",
            "interval_count": 1,
            "interval_unit": "month",
            "next_run_on": self.today.isoformat(),
        }
        payload.update(overrides)
        return self.client.post(
            reverse("finance-automations"), payload, format="json"
        )

    def run_automation(self, automation_id):
        return self.client.post(
            reverse("finance-automation-run", args=[automation_id])
        )

    def run_all(self):
        return self.client.post(reverse("finance-automations-run"))

    def automation_transactions(self):
        return Transaction.objects.filter(
            profile=self.profile, automation__isnull=False
        ).order_by("date", "id")

    def executions(self, automation_id, status=None):
        url = reverse("finance-automation-executions")
        if status:
            url = f"{url}?automation={automation_id}&status={status}"
        else:
            url = f"{url}?automation={automation_id}"
        return self.client.get(url).data["executions"]


class AutomationCreationTests(AutomationTestBase):
    def test_create_and_list_rule(self):
        response = self.create_automation()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["savings_name"], "Salute")
        self.assertEqual(response.data["source_account_name"], "Contanti")
        self.assertEqual(response.data["status"], "active")
        self.assertEqual(response.data["pending_count"], 0)

        listing = self.client.get(reverse("finance-automations"))
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(len(listing.data["automations"]), 1)

    def test_rejects_foreign_accounts(self):
        other = User.objects.create_user(
            email="altro@example.com",
            password="Spendy-Fondamenta-2026",
            status=User.Status.ACTIVE,
        )
        self.client.force_authenticate(user=other)
        response = self.create_automation()
        self.assertEqual(response.status_code, 400)

    def test_archived_source_account_is_rejected(self):
        self.client.patch(
            reverse("finance-account-detail", args=[self.account["id"]]),
            {"archived": True},
            format="json",
        )
        response = self.create_automation()
        self.assertEqual(response.status_code, 400)
        self.assertIn("source_account", response.data)

    def test_system_status_cannot_be_set_manually(self):
        automation = self.create_automation().data
        response = self.client.patch(
            reverse("finance-automation-detail", args=[automation["id"]]),
            {"status": "suspended"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)


class AutomationExecutionTests(AutomationTestBase):
    def test_single_due_occurrence_creates_transfer_and_never_duplicates(self):
        automation = self.create_automation().data
        response = self.run_automation(automation["id"])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["outcome"]["executed"], 1)

        transactions = self.automation_transactions()
        self.assertEqual(transactions.count(), 1)
        operation = transactions.get()
        self.assertEqual(operation.date, self.today)
        self.assertEqual(operation.amount, 100)
        self.assertEqual(str(operation.automation_id), str(automation["id"]))
        self.assertEqual(Account.objects.get(pk=self.account["id"]).balance, 900)
        self.assertEqual(
            operation.lines.get(savings_id=self.savings["id"]).amount, 100
        )

        execution = AutomationExecution.objects.get(automation_ref=automation["id"])
        self.assertEqual(execution.status, AutomationExecution.Status.SUCCEEDED)
        self.assertEqual(execution.transaction_id, operation.id)

        second = self.run_automation(automation["id"])
        self.assertEqual(second.data["outcome"]["executed"], 0)
        self.assertEqual(self.automation_transactions().count(), 1)

    def test_single_missed_occurrence_is_recovered_automatically(self):
        automation = self.create_automation(
            interval_unit="month",
            next_run_on=(self.today - timedelta(days=1)).isoformat(),
        ).data
        response = self.run_automation(automation["id"])
        self.assertEqual(response.data["outcome"]["executed"], 1)

        operation = self.automation_transactions().get()
        self.assertEqual(operation.date, self.today - timedelta(days=1))

    def test_multiple_missed_occurrences_require_an_explicit_choice(self):
        automation = self.create_automation(
            interval_unit="day",
            next_run_on=(self.today - timedelta(days=2)).isoformat(),
        ).data
        response = self.run_automation(automation["id"])
        self.assertEqual(response.data["outcome"]["pending_choice"], 3)
        self.assertEqual(self.automation_transactions().count(), 0)

        pending = self.executions(automation["id"], "pending")
        self.assertEqual(len(pending), 3)
        self.assertTrue(
            Notification.objects.filter(
                profile=self.profile,
                kind=Notification.Kind.AUTOMATION_PENDING,
                read_at__isnull=True,
            ).exists()
        )

        chosen = [pending[0]["id"], pending[2]["id"]]
        resolved = self.client.post(
            reverse("finance-automation-resolve", args=[automation["id"]]),
            {"recover": chosen},
            format="json",
        )
        self.assertEqual(resolved.status_code, 200)
        self.assertEqual(resolved.data["outcome"]["recovered"], 2)
        self.assertEqual(resolved.data["outcome"]["skipped"], 1)

        transactions = list(self.automation_transactions())
        self.assertEqual(len(transactions), 2)
        self.assertEqual(
            [item.date for item in transactions],
            [self.today - timedelta(days=2), self.today],
        )
        skipped = self.executions(automation["id"], "skipped")
        self.assertEqual(len(skipped), 1)
        self.assertEqual(skipped[0]["failure_code"], "not_selected")

        again = self.run_automation(automation["id"])
        self.assertEqual(again.data["outcome"]["executed"], 0)
        self.assertEqual(self.automation_transactions().count(), 2)

    def test_pending_occurrence_keeps_the_original_snapshot(self):
        automation = self.create_automation(
            interval_unit="day",
            next_run_on=(self.today - timedelta(days=1)).isoformat(),
        ).data
        self.run_automation(automation["id"])
        pending = self.executions(automation["id"], "pending")
        self.assertEqual(len(pending), 2)

        changed = self.client.patch(
            reverse("finance-automation-detail", args=[automation["id"]]),
            {"amount": "500.00"},
            format="json",
        )
        self.assertEqual(changed.status_code, 200)

        resolved = self.client.post(
            reverse("finance-automation-resolve", args=[automation["id"]]),
            {"recover": [pending[0]["id"]]},
            format="json",
        )
        self.assertEqual(resolved.status_code, 200)
        self.assertEqual(self.automation_transactions().get().amount, 100)

    def test_insufficient_balance_skips_and_keeps_the_rule_active(self):
        poor = self.client.post(
            reverse("finance-accounts"),
            {"name": "Povero", "type": "cash", "initial_balance": "50.00"},
            format="json",
        ).data
        automation = self.create_automation(source_account=poor["id"]).data
        response = self.run_automation(automation["id"])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.automation_transactions().count(), 0)

        execution = AutomationExecution.objects.get(automation_ref=automation["id"])
        self.assertEqual(execution.status, AutomationExecution.Status.SKIPPED)
        self.assertEqual(
            execution.failure_code,
            AutomationExecution.FailureCode.INSUFFICIENT_BALANCE,
        )
        self.assertEqual(
            Automation.objects.get(pk=automation["id"]).status,
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

    def test_missing_source_data_skips_the_occurrence(self):
        automation = self.create_automation().data
        self.client.patch(
            reverse("finance-account-detail", args=[self.account["id"]]),
            {"archived": True},
            format="json",
        )
        response = self.run_automation(automation["id"])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.automation_transactions().count(), 0)
        execution = AutomationExecution.objects.get(automation_ref=automation["id"])
        self.assertEqual(execution.status, AutomationExecution.Status.SKIPPED)
        self.assertEqual(
            execution.failure_code, AutomationExecution.FailureCode.MISSING_DATA
        )
        self.assertEqual(
            Automation.objects.get(pk=automation["id"]).status,
            Automation.Status.ACTIVE,
        )

    @override_settings(AUTOMATION_MAX_ATTEMPTS=3, AUTOMATION_RETRY_DELAYS=[0, 0, 0])
    def test_technical_error_retries_with_the_original_date(self):
        automation = self.create_automation().data
        original = automations._apply_effect
        calls = {"count": 0}

        def flaky(*args, **kwargs):
            calls["count"] += 1
            if calls["count"] <= 2:
                raise RuntimeError("errore temporaneo")
            return original(*args, **kwargs)

        with mock.patch("finance.automations._apply_effect", side_effect=flaky):
            first = self.run_automation(automation["id"])
            self.assertEqual(first.status_code, 200)
            execution = AutomationExecution.objects.get(
                automation_ref=automation["id"]
            )
            self.assertEqual(execution.status, AutomationExecution.Status.FAILED)
            self.assertEqual(execution.attempts, 1)

            second = self.run_automation(automation["id"])
            self.assertEqual(second.status_code, 200)
            execution.refresh_from_db()
            self.assertEqual(execution.status, AutomationExecution.Status.FAILED)
            self.assertEqual(execution.attempts, 2)

            third = self.run_automation(automation["id"])
            self.assertEqual(third.status_code, 200)

        execution.refresh_from_db()
        self.assertEqual(execution.status, AutomationExecution.Status.SUCCEEDED)
        self.assertEqual(execution.attempts, 3)
        operation = self.automation_transactions().get()
        self.assertEqual(operation.date, self.today)
        self.assertEqual(self.automation_transactions().count(), 1)

    @override_settings(AUTOMATION_MAX_ATTEMPTS=2, AUTOMATION_RETRY_DELAYS=[0, 0])
    def test_technical_error_suspends_the_rule_after_max_attempts(self):
        automation = self.create_automation().data
        with mock.patch(
            "finance.automations._apply_effect",
            side_effect=RuntimeError("sempre rotto"),
        ):
            self.run_automation(automation["id"])
            self.run_automation(automation["id"])

        execution = AutomationExecution.objects.get(automation_ref=automation["id"])
        self.assertEqual(execution.status, AutomationExecution.Status.FAILED)
        self.assertEqual(execution.attempts, 2)
        self.assertIsNone(execution.next_retry_at)
        rule = Automation.objects.get(pk=automation["id"])
        self.assertEqual(rule.status, Automation.Status.SUSPENDED)
        self.assertTrue(
            Notification.objects.filter(
                profile=self.profile,
                kind=Notification.Kind.AUTOMATION_SUSPENDED,
                automation=rule,
            ).exists()
        )
        self.assertEqual(self.automation_transactions().count(), 0)

        third = self.run_automation(automation["id"])
        self.assertEqual(third.status_code, 200)
        self.assertEqual(self.automation_transactions().count(), 0)

    def test_paused_rule_waits_until_resumed(self):
        automation = self.create_automation().data
        self.client.patch(
            reverse("finance-automation-detail", args=[automation["id"]]),
            {"status": "paused"},
            format="json",
        )
        paused = self.run_automation(automation["id"])
        self.assertEqual(paused.status_code, 200)
        self.assertEqual(self.automation_transactions().count(), 0)
        self.assertFalse(
            AutomationExecution.objects.filter(
                automation_ref=automation["id"]
            ).exists()
        )

        self.client.patch(
            reverse("finance-automation-detail", args=[automation["id"]]),
            {"status": "active"},
            format="json",
        )
        self.run_automation(automation["id"])
        self.assertEqual(self.automation_transactions().count(), 1)


class AutomationEffectsTests(AutomationTestBase):
    def test_generated_movement_uses_the_real_execution_time(self):
        from datetime import time

        automation = self.create_automation().data
        with mock.patch(
            "finance.automations.current_local_time",
            return_value=time(7, 25),
        ):
            self.run_automation(automation["id"])
        operation = self.automation_transactions().get()
        self.assertEqual(operation.time, time(7, 25))

    def test_editing_the_generated_movement_marks_the_occurrence_corrected(self):
        automation = self.create_automation().data
        self.run_automation(automation["id"])
        operation = self.automation_transactions().get()
        execution = AutomationExecution.objects.get(automation_ref=automation["id"])

        response = self.client.patch(
            reverse("finance-transaction-detail", args=[operation.id]),
            {
                "kind": "transfer",
                "date": self.today.isoformat(),
                "amount": "50.00",
                "from_account": self.account["id"],
                "to_savings": self.savings["id"],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        execution.refresh_from_db()
        self.assertEqual(execution.status, AutomationExecution.Status.SUCCEEDED)
        self.assertTrue(execution.corrected)
        self.assertEqual(
            Automation.objects.get(pk=automation["id"]).status,
            Automation.Status.ACTIVE,
        )

    def test_deleting_the_generated_movement_cancels_the_occurrence(self):
        automation = self.create_automation().data
        self.run_automation(automation["id"])
        operation = self.automation_transactions().get()

        response = self.client.delete(
            reverse("finance-transaction-detail", args=[operation.id])
        )
        self.assertEqual(response.status_code, 204)
        execution = AutomationExecution.objects.get(automation_ref=automation["id"])
        self.assertEqual(execution.status, AutomationExecution.Status.CANCELLED)
        self.assertIsNone(execution.transaction_id)

        self.run_automation(automation["id"])
        self.assertEqual(self.automation_transactions().count(), 0)

    def test_deleting_the_rule_preserves_the_execution_history(self):
        automation = self.create_automation().data
        self.run_automation(automation["id"])
        response = self.client.delete(
            reverse("finance-automation-detail", args=[automation["id"]])
        )
        self.assertEqual(response.status_code, 204)
        self.assertFalse(
            Automation.objects.filter(pk=automation["id"]).exists()
        )
        execution = AutomationExecution.objects.get(automation_ref=automation["id"])
        self.assertEqual(execution.automation_id, automation["id"])
        self.assertTrue(
            Automation.all_objects.filter(pk=automation["id"]).exists()
        )
        self.assertEqual(execution.status, AutomationExecution.Status.SUCCEEDED)
        self.assertTrue(
            Transaction.objects.filter(
                profile=self.profile,
                description__startswith="Versamento automatico",
            ).exists()
        )

    def test_deleting_the_savings_container_removes_the_rule(self):
        automation = self.create_automation().data
        self.run_automation(automation["id"])
        response = self.client.delete(
            reverse("finance-savings-detail", args=[self.savings["id"]])
        )
        self.assertEqual(response.status_code, 204)
        self.assertFalse(
            Automation.objects.filter(pk=automation["id"]).exists()
        )
        execution = AutomationExecution.objects.get(automation_ref=automation["id"])
        self.assertEqual(execution.automation_id, automation["id"])


class AutomationWorkerTests(AutomationTestBase):
    def test_management_command_processes_due_rules(self):
        automation = self.create_automation().data
        call_command("run_automations")
        self.assertEqual(self.automation_transactions().count(), 1)
        self.assertEqual(
            AutomationExecution.objects.get(
                automation_ref=automation["id"]
            ).status,
            AutomationExecution.Status.SUCCEEDED,
        )

    def test_run_all_endpoint(self):
        self.create_automation()
        response = self.run_all()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["outcome"]["rules"], 1)
        self.assertEqual(self.automation_transactions().count(), 1)

    def test_notifications_can_be_marked_as_read(self):
        automation = self.create_automation(
            interval_unit="day",
            next_run_on=(self.today - timedelta(days=1)).isoformat(),
        ).data
        self.run_automation(automation["id"])
        listing = self.client.get(reverse("finance-notifications"))
        self.assertEqual(listing.data["unread_count"], 1)

        response = self.client.post(
            reverse("finance-notifications-read"), {}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["unread_count"], 0)
