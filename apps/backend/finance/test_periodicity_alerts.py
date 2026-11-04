from datetime import date, timedelta

from django.urls import reverse
from django.utils import timezone

from .automations import next_occurrence, process_automation
from .models import Automation, AutomationExecution, Notification, Transaction
from .test_automations import AutomationTestBase


class CustomPeriodicityTests(AutomationTestBase):
    def test_every_two_weeks(self):
        response = self.create_automation(
            interval_count=2, interval_unit="week"
        )
        self.assertEqual(response.status_code, 201, response.data)
        rule = response.data
        self.assertEqual(rule["interval_label"], "Ogni 2 settimane")
        self.run_automation(rule["id"])
        automation = Automation.objects.get(pk=rule["id"])
        self.assertEqual(automation.next_run_on, self.today + timedelta(days=14))

    def test_every_45_days(self):
        rule = self.create_automation(
            interval_count=45, interval_unit="day"
        ).data
        self.assertEqual(rule["interval_label"], "Ogni 45 giorni")
        self.run_automation(rule["id"])
        automation = Automation.objects.get(pk=rule["id"])
        self.assertEqual(automation.next_run_on, self.today + timedelta(days=45))

    def test_every_three_months(self):
        rule = self.create_automation(
            interval_count=3, interval_unit="month"
        ).data
        self.assertEqual(rule["interval_label"], "Ogni 3 mesi")
        start = self.today
        expected_month = (start.month - 1 + 3) % 12 + 1
        expected_year = start.year + (start.month - 1 + 3) // 12
        self.run_automation(rule["id"])
        automation = Automation.objects.get(pk=rule["id"])
        self.assertEqual(automation.next_run_on.year, expected_year)
        self.assertEqual(automation.next_run_on.month, expected_month)

    def test_month_end_keeps_the_anchor_day(self):
        january = date(2027, 1, 31)
        february = next_occurrence(january, "month", 1, 31)
        march = next_occurrence(february, "month", 1, 31)
        self.assertEqual(february, date(2027, 2, 28))
        self.assertEqual(march, date(2027, 3, 31))

        every_two_months = next_occurrence(january, "month", 2, 31)
        self.assertEqual(every_two_months, date(2027, 3, 31))

    def test_anchor_day_is_set_from_the_first_run(self):
        rule = self.create_automation(
            interval_unit="month",
            next_run_on="2027-01-31",
        ).data
        self.assertEqual(rule["anchor_day"], 31)

    def test_invalid_custom_interval_is_rejected(self):
        response = self.create_automation(interval_count=0)
        self.assertEqual(response.status_code, 400)
        self.assertIn("interval_count", response.data)

    def test_invalid_notice_days_are_rejected(self):
        response = self.create_automation(advance_notice_days=31)
        self.assertEqual(response.status_code, 400)
        self.assertIn("advance_notice_days", response.data)


class LowBalanceAlertTests(AutomationTestBase):
    def poor_account(self, initial="50.00"):
        return self.client.post(
            reverse("finance-accounts"),
            {"name": "Povero", "type": "cash", "initial_balance": initial},
            format="json",
        ).data

    def test_alert_when_projected_balance_is_insufficient(self):
        poor = self.poor_account()
        rule = self.create_automation(
            source_account=poor["id"],
            amount="100.00",
            next_run_on=(self.today + timedelta(days=3)).isoformat(),
            advance_notice_days=3,
        ).data
        response = self.run_automation(rule["id"])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["outcome"]["alerts"], 1)

        notification = Notification.objects.get(
            profile=self.profile,
            kind=Notification.Kind.AUTOMATION_LOW_BALANCE,
        )
        self.assertIn("Tra 3 giorni", notification.message)
        self.assertEqual(notification.occurrence_date, self.today + timedelta(days=3))
        self.assertEqual(notification.alert_date, self.today)
        self.assertFalse(
            Transaction.objects.filter(
                profile=self.profile, automation_id=rule["id"]
            ).exists()
        )

    def test_sufficient_projected_balance_does_not_alert(self):
        rule = self.create_automation(
            amount="100.00",
            next_run_on=(self.today + timedelta(days=3)).isoformat(),
            advance_notice_days=3,
        ).data
        response = self.run_automation(rule["id"])
        self.assertEqual(response.data["outcome"]["alerts"], 0)
        self.assertFalse(
            Notification.objects.filter(
                profile=self.profile,
                kind=Notification.Kind.AUTOMATION_LOW_BALANCE,
            ).exists()
        )

    def test_alert_can_be_disabled(self):
        poor = self.poor_account()
        rule = self.create_automation(
            source_account=poor["id"],
            amount="100.00",
            next_run_on=(self.today + timedelta(days=3)).isoformat(),
            advance_notice_days=0,
        ).data
        response = self.run_automation(rule["id"])
        self.assertEqual(response.data["outcome"]["alerts"], 0)
        self.assertFalse(
            Notification.objects.filter(
                profile=self.profile,
                kind=Notification.Kind.AUTOMATION_LOW_BALANCE,
            ).exists()
        )

    def test_alert_is_not_duplicated_on_the_same_day(self):
        poor = self.poor_account()
        rule = self.create_automation(
            source_account=poor["id"],
            amount="100.00",
            next_run_on=(self.today + timedelta(days=3)).isoformat(),
            advance_notice_days=3,
        ).data
        automation = Automation.objects.get(pk=rule["id"])
        process_automation(automation, today=self.today)
        process_automation(automation, today=self.today)
        self.assertEqual(
            Notification.objects.filter(
                profile=self.profile,
                kind=Notification.Kind.AUTOMATION_LOW_BALANCE,
            ).count(),
            1,
        )

    def test_alert_is_repeated_each_day_until_due(self):
        poor = self.poor_account()
        rule = self.create_automation(
            source_account=poor["id"],
            amount="100.00",
            next_run_on=(self.today + timedelta(days=3)).isoformat(),
            advance_notice_days=3,
        ).data
        automation = Automation.objects.get(pk=rule["id"])
        process_automation(automation, today=self.today)
        process_automation(automation, today=self.today + timedelta(days=1))
        alerts = Notification.objects.filter(
            profile=self.profile,
            kind=Notification.Kind.AUTOMATION_LOW_BALANCE,
        )
        self.assertEqual(alerts.count(), 2)
        self.assertEqual(
            set(alerts.values_list("alert_date", flat=True)),
            {self.today, self.today + timedelta(days=1)},
        )

    def test_alert_applies_to_savings_transfers_too(self):
        poor = self.poor_account()
        rule = self.create_automation(
            source_account=poor["id"],
            amount="100.00",
            next_run_on=(self.today + timedelta(days=3)).isoformat(),
            advance_notice_days=3,
        ).data
        self.run_automation(rule["id"])
        notification = Notification.objects.get(
            profile=self.profile,
            kind=Notification.Kind.AUTOMATION_LOW_BALANCE,
        )
        self.assertIn("eseguito", notification.message)

    def test_projection_includes_other_active_automations(self):
        account = self.client.post(
            reverse("finance-accounts"),
            {
                "name": "Due abbonamenti",
                "type": "cash",
                "initial_balance": "100.00",
            },
            format="json",
        ).data
        first = self.create_automation(
            source_account=account["id"],
            amount="60.00",
            next_run_on=(self.today + timedelta(days=2)).isoformat(),
            advance_notice_days=3,
        ).data
        second = self.create_automation(
            source_account=account["id"],
            amount="60.00",
            next_run_on=(self.today + timedelta(days=3)).isoformat(),
            advance_notice_days=3,
        ).data
        automation = Automation.objects.get(pk=second["id"])
        process_automation(automation, today=self.today)
        notification = Notification.objects.get(
            profile=self.profile,
            kind=Notification.Kind.AUTOMATION_LOW_BALANCE,
            automation_id=second["id"],
        )
        self.assertIn("saldo previsto", notification.message)
        self.assertIn("-", notification.message)
        # The first rule is due before the second and is part of the projection.
        self.assertTrue(Automation.objects.filter(pk=first["id"]).exists())

    def test_no_alert_on_the_due_day(self):
        poor = self.poor_account()
        rule = self.create_automation(
            source_account=poor["id"],
            amount="100.00",
            next_run_on=self.today.isoformat(),
            advance_notice_days=3,
        ).data
        response = self.run_automation(rule["id"])
        self.assertEqual(response.data["outcome"]["alerts"], 0)
        self.assertFalse(
            Notification.objects.filter(
                profile=self.profile,
                kind=Notification.Kind.AUTOMATION_LOW_BALANCE,
            ).exists()
        )
        execution = AutomationExecution.objects.get(automation_ref=rule["id"])
        self.assertEqual(execution.status, "skipped")
