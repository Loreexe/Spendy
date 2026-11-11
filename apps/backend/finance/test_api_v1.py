from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import User

from .models import Account, Category, Profile, Transaction


class ApiV1Tests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="v1@example.com",
            password="Spendy-Fondamenta-2026",
            status=User.Status.ACTIVE,
        )
        self.client.force_authenticate(user=self.user)
        self.today = timezone.localdate()
        self.account = self.client.post(
            reverse("v1-finance:finance-accounts"),
            {"name": "Contanti", "type": "cash", "initial_balance": "500.00"},
            format="json",
        ).data

    def transaction_payload(self, description="Spesa", amount="10.00"):
        return {
            "kind": "expense",
            "date": self.today.isoformat(),
            "description": description,
            "amount": amount,
            "account": self.account["id"],
        }

    def test_token_authenticates_v1_finance(self):
        login = self.client.post(
            reverse("v1-auth:login"),
            {
                "identifier": "v1@example.com",
                "password": "Spendy-Fondamenta-2026",
                "device_name": "Test",
            },
            format="json",
        )
        self.assertEqual(login.status_code, 200)
        self.client.force_authenticate(user=None)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {login.data['token']}"
        )
        dashboard = self.client.get(reverse("v1-finance:finance-dashboard"))
        self.assertEqual(dashboard.status_code, 200)
        self.assertIn("total_balance", dashboard.data)

    def test_v1_finance_is_reachable_and_exposes_uuid(self):
        response = self.client.get(reverse("v1-finance:finance-accounts"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("uuid", response.data["accounts"][0])
        self.assertTrue(Profile.objects.filter(user=self.user).exists())

    def test_global_search_finds_movements_accounts_and_categories(self):
        self.client.post(
            reverse("v1-finance:finance-transactions"),
            self.transaction_payload("Cena al ristorante"),
            format="json",
        )
        response = self.client.get(
            reverse("v1-finance:finance-search"), {"q": "cena"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["transactions"]), 1)
        self.assertEqual(
            response.data["transactions"][0]["description"],
            "Cena al ristorante",
        )
        self.assertEqual(response.data["accounts"], [])

        accounts = self.client.get(
            reverse("v1-finance:finance-search"), {"q": "cont"}
        )
        self.assertEqual(len(accounts.data["accounts"]), 1)

    def test_idempotency_key_replays_the_same_response(self):
        url = reverse("v1-finance:finance-transactions")
        payload = self.transaction_payload()
        first = self.client.post(
            url, payload, format="json", HTTP_IDEMPOTENCY_KEY="abc-123"
        )
        second = self.client.post(
            url, payload, format="json", HTTP_IDEMPOTENCY_KEY="abc-123"
        )
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        self.assertEqual(second.headers.get("Idempotent-Replayed"), "true")
        self.assertEqual(first.data["id"], second.data["id"])
        self.assertEqual(
            Transaction.objects.filter(profile__user=self.user).count(), 2
        )  # apertura del conto + spesa

    def test_idempotency_key_with_different_body_conflicts(self):
        url = reverse("v1-finance:finance-transactions")
        self.client.post(
            url,
            self.transaction_payload("Prima"),
            format="json",
            HTTP_IDEMPOTENCY_KEY="same-key",
        )
        response = self.client.post(
            url,
            self.transaction_payload("Seconda"),
            format="json",
            HTTP_IDEMPOTENCY_KEY="same-key",
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["code"], "idempotency_key_reused")

    def test_errors_have_stable_codes(self):
        self.client.force_authenticate(user=None)
        self.client.credentials(HTTP_AUTHORIZATION="Bearer invalid-token")
        unauthorized = self.client.get(reverse("v1-finance:finance-dashboard"))
        self.assertEqual(unauthorized.status_code, 401)
        self.assertEqual(unauthorized.data["code"], "authentication_failed")
        self.client.credentials()
        self.client.force_authenticate(user=self.user)

        invalid = self.client.post(
            reverse("v1-finance:finance-transactions"),
            {"kind": "expense"},
            format="json",
        )
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(invalid.data["code"], "validation_error")

    def test_openapi_schema_is_available(self):
        response = self.client.get(reverse("v1-schema"))
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn("/api/v1/finance/transactions/", body)
        self.assertIn("/api/v1/auth/login/", body)
        # Il contratto 0.8.4 espone ora e icona.
        self.assertIn("time", body)
        self.assertIn("icon", body)

    def test_movement_time_and_category_icon_are_exposed(self):
        category = Category.objects.get(
            profile__user=self.user, name="Alimentari"
        )
        response = self.client.post(
            reverse("v1-finance:finance-transactions"),
            {
                **self.transaction_payload("Cena al ristorante"),
                "time": "20:15",
                "category_id": category.id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["time"], "20:15")
        self.assertEqual(response.data["category"]["icon"], "shopping-cart")

        listing = self.client.get(reverse("v1-finance:finance-transactions"))
        movement = next(
            item
            for item in listing.data["transactions"]
            if item["description"] == "Cena al ristorante"
        )
        self.assertIn("time", movement)
        self.assertIn("icon", movement["category"])

    def test_global_search_exposes_category_icon(self):
        Category.objects.get(profile__user=self.user, name="Alimentari")
        response = self.client.get(
            reverse("v1-finance:finance-search"), {"q": "alim"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["categories"][0]["icon"], "shopping-cart"
        )
