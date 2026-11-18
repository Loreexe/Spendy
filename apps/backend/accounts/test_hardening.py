"""Test dei fix P0: throttle reale, documentazione API e sessioni."""
from __future__ import annotations

from django.core.cache import cache
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase

from .tests import NEW_PASSWORD, VALID_PASSWORD, complete_setup


class ClientIpThrottleTests(APITestCase):
    def setUp(self):
        cache.clear()

    def test_login_throttle_ignores_spoofed_xff(self):
        last = None
        for index in range(11):
            last = self.client.post(
                reverse("auth-login"),
                {
                    "identifier": f"nessuno{index}@example.com",
                    "password": "password-sbagliata",
                },
                REMOTE_ADDR="172.18.0.2",
                HTTP_X_FORWARDED_FOR=f"203.0.113.{index}, 8.8.8.8",
            )
            if index < 10:
                self.assertEqual(last.status_code, 400)
        self.assertIsNotNone(last)
        self.assertEqual(last.status_code, 429)


class ApiDocumentationTests(APITestCase):
    def test_schema_and_docs_are_admin_only(self):
        anonymous = self.client.get(reverse("v1-schema"))
        self.assertIn(anonymous.status_code, (401, 403))
        anonymous_docs = self.client.get(reverse("v1-docs"))
        self.assertIn(anonymous_docs.status_code, (401, 403))

        admin = complete_setup()
        self.client.force_authenticate(user=admin)
        self.assertEqual(self.client.get(reverse("v1-schema")).status_code, 200)
        self.assertEqual(self.client.get(reverse("v1-docs")).status_code, 200)


class PasswordChangeSessionTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.admin = complete_setup()
        self.first = APIClient()
        self.second = APIClient()
        for client in (self.first, self.second):
            response = client.post(
                reverse("auth-login"),
                {"identifier": "admin", "password": VALID_PASSWORD},
            )
            self.assertEqual(response.status_code, 200)

    def test_password_change_revokes_other_web_sessions(self):
        response = self.first.post(
            reverse("auth-password"),
            {
                "current_password": VALID_PASSWORD,
                "new_password": NEW_PASSWORD,
                "new_password_confirm": NEW_PASSWORD,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(response.data["revoked_sessions"], 1)

        revoked = self.second.get(reverse("auth-me"))
        self.assertEqual(revoked.status_code, 200)
        self.assertIsNone(revoked.data["user"])

        still_valid = self.first.get(reverse("auth-me"))
        self.assertEqual(still_valid.status_code, 200)
        self.assertIsNotNone(still_valid.data["user"])
