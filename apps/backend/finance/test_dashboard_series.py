"""Tests for the dashboard series endpoint (DC-087)."""

from django.urls import reverse

from .models import Category
from .tests import FinanceTestBase


class DashboardSeriesTests(FinanceTestBase):
    def setUp(self):
        super().setUp()
        self.account = self.create_account(initial="1000.00").data

    def get_series(self, **params):
        query = "&".join(f"{key}={value}" for key, value in params.items())
        url = reverse("finance-dashboard-series")
        return self.client.get(f"{url}?{query}" if query else url)

    def test_buckets_track_running_balance(self):
        food = Category.objects.get(profile__user=self.user, name="Alimentari")
        self.create_transaction(
            {
                "kind": "expense",
                "date": self.today.isoformat(),
                "description": "Spesa",
                "amount": "200.00",
                "account": self.account["id"],
                "category_id": food.id,
            }
        )
        start = self.today.replace(day=1).isoformat()
        response = self.get_series(start=start, end=self.today.isoformat())
        self.assertEqual(response.status_code, 200)
        buckets = response.data["buckets"]
        self.assertTrue(len(buckets) >= 1)
        self.assertEqual(buckets[-1]["saldo"], "800.00")
        self.assertEqual(buckets[-1]["patrimonio"], "800.00")
        for point in buckets:
            self.assertIn("date", point)
            self.assertIn("saldo", point)
            self.assertIn("patrimonio", point)

    def test_by_category_sums_expenses(self):
        food = Category.objects.get(profile__user=self.user, name="Alimentari")
        self.create_transaction(
            {
                "kind": "expense",
                "date": self.today.isoformat(),
                "description": "Spesa",
                "amount": "200.00",
                "account": self.account["id"],
                "category_id": food.id,
            }
        )
        self.create_transaction(
            {
                "kind": "income",
                "date": self.today.isoformat(),
                "description": "Stipendio",
                "amount": "50.00",
                "account": self.account["id"],
                "category_id": food.id,
            }
        )
        start = self.today.replace(day=1).isoformat()
        response = self.get_series(start=start, end=self.today.isoformat())
        rows = {
            entry["name"]: entry["total"] for entry in response.data["by_category"]
        }
        icons = {
            entry["name"]: entry["icon"] for entry in response.data["by_category"]
        }
        self.assertEqual(rows.get("Alimentari"), "200.00")
        self.assertEqual(icons.get("Alimentari"), "shopping-cart")
        self.assertNotIn("Altro", rows)

    def test_long_period_uses_weekly_buckets(self):
        response = self.get_series(start="2026-01-01", end="2026-11-05")
        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(len(response.data["buckets"]), 95)

    def test_reversed_period_is_rejected(self):
        response = self.get_series(start="2026-11-05", end="2026-11-01")
        self.assertEqual(response.status_code, 400)
