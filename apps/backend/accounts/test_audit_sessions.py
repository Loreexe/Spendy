"""Test di audit log e politica sessioni (Fase S)."""
from __future__ import annotations

import json
import time
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from .models import AuditEvent, User
from .tests import NEW_PASSWORD, VALID_PASSWORD, complete_setup


class AuditLogTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.admin = complete_setup()

    def login(self, identifier="admin", password=VALID_PASSWORD):
        return self.client.post(
            reverse("auth-login"),
            {"identifier": identifier, "password": password},
        )

    def test_successful_and_failed_login_are_recorded(self):
        self.login()
        self.assertTrue(
            AuditEvent.objects.filter(
                action=AuditEvent.Action.LOGIN_SUCCESS,
                actor=self.admin,
            ).exists()
        )
        self.client.post(reverse("auth-logout"))
        self.client.post(
            reverse("auth-login"),
            {"identifier": "admin", "password": "sbagliata"},
        )
        failed = AuditEvent.objects.filter(
            action=AuditEvent.Action.LOGIN_FAILED
        ).latest("created_at")
        self.assertEqual(failed.actor, self.admin)
        self.assertEqual(failed.metadata.get("reason"), "invalid_password")

    def test_password_change_and_admin_decision_are_recorded(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            reverse("auth-password"),
            {
                "current_password": VALID_PASSWORD,
                "new_password": NEW_PASSWORD,
                "new_password_confirm": NEW_PASSWORD,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            AuditEvent.objects.filter(
                action=AuditEvent.Action.PASSWORD_CHANGED,
                actor=self.admin,
            ).exists()
        )

        user = User.objects.create_user(
            email="da-approvare@example.com",
            password=VALID_PASSWORD,
            status=User.Status.PENDING,
        )
        self.client.post(
            reverse("admin-user-decision", args=[user.pk, "approve"])
        )
        event = AuditEvent.objects.filter(
            action=AuditEvent.Action.ADMIN_APPROVE
        ).latest("created_at")
        self.assertEqual(event.target, "da-approvare@example.com")

    def test_2fa_events_are_recorded(self):
        self.client.force_authenticate(user=self.admin)
        setup = self.client.post(reverse("auth-2fa-setup"))
        self.assertEqual(setup.status_code, 200)
        from . import totp

        counter = int(time.time()) // totp.PERIOD_SECONDS
        self.client.post(
            reverse("auth-2fa-confirm"),
            {"code": totp.code_for_counter(setup.data["secret"], counter)},
        )
        self.assertTrue(
            AuditEvent.objects.filter(
                action=AuditEvent.Action.TWO_FACTOR_ENABLED
            ).exists()
        )
        self.client.post(
            reverse("auth-2fa-disable"),
            {
                "password": VALID_PASSWORD,
                "code": totp.code_for_counter(setup.data["secret"], counter + 1),
            },
        )
        self.assertTrue(
            AuditEvent.objects.filter(
                action=AuditEvent.Action.TWO_FACTOR_DISABLED
            ).exists()
        )

    def test_audit_endpoint_is_admin_only(self):
        anonymous = self.client.get(reverse("admin-audit"))
        self.assertIn(anonymous.status_code, (401, 403))
        self.client.force_authenticate(user=self.admin)
        self.login()
        response = self.client.get(reverse("admin-audit"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["events"])
        actions = {event["action"] for event in response.data["events"]}
        self.assertIn("login_success", actions)

    def test_retention_command_deletes_only_old_events(self):
        old = AuditEvent.objects.create(
            action=AuditEvent.Action.LOGIN_SUCCESS,
            actor=self.admin,
        )
        AuditEvent.objects.filter(pk=old.pk).update(
            created_at=timezone.now() - timedelta(days=400)
        )
        recent = AuditEvent.objects.create(
            action=AuditEvent.Action.LOGIN_SUCCESS,
            actor=self.admin,
        )
        call_command("purge_audit_events", "--days", "180")
        self.assertFalse(AuditEvent.objects.filter(pk=old.pk).exists())
        self.assertTrue(AuditEvent.objects.filter(pk=recent.pk).exists())


class SessionPolicyTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.admin = complete_setup()

    def login(self, client: APIClient):
        response = client.post(
            reverse("auth-login"),
            {"identifier": "admin", "password": VALID_PASSWORD},
        )
        self.assertEqual(response.status_code, 200)
        return client

    def test_session_policy_values(self):
        self.assertEqual(settings.SESSION_COOKIE_AGE, 43200)
        self.assertEqual(settings.SESSION_IDLE_TIMEOUT_SECONDS, 7200)
        self.assertFalse(settings.SESSION_EXPIRE_AT_BROWSER_CLOSE)

    def test_idle_timeout_expires_session(self):
        client = self.login(APIClient())
        session = client.session
        session["last_activity"] = time.time() - 7300
        session.save()
        response = client.get(reverse("auth-me"))
        self.assertEqual(response.status_code, 401)
        self.assertEqual(json.loads(response.content)["code"], "session_expired")
        self.assertTrue(
            AuditEvent.objects.filter(
                action=AuditEvent.Action.SESSION_EXPIRED
            ).exists()
        )

    def test_revoke_other_sessions_keeps_current(self):
        first = self.login(APIClient())
        second = self.login(APIClient())
        response = first.post(reverse("auth-sessions-revoke-others"))
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(response.data["revoked_sessions"], 1)
        still = first.get(reverse("auth-me"))
        self.assertIsNotNone(still.data["user"])
        revoked = second.get(reverse("auth-me"))
        self.assertIsNone(revoked.data["user"])
        self.assertTrue(
            AuditEvent.objects.filter(
                action=AuditEvent.Action.SESSIONS_REVOKED
            ).exists()
        )

    def test_session_info_reports_policy_and_other_sessions(self):
        first = self.login(APIClient())
        self.login(APIClient())
        response = first.get(reverse("auth-sessions"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["session_cookie_age"], 43200)
        self.assertEqual(response.data["idle_timeout"], 7200)
        self.assertEqual(response.data["other_sessions"], 1)
