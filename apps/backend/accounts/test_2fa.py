"""Test della 2FA TOTP (DC-121): setup, login, codici di recupero, anti-replay."""
from __future__ import annotations

import time

from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from . import totp
from .models import RecoveryCode, User
from .tests import VALID_PASSWORD, complete_setup


def current_code(secret: str) -> str:
    return totp.code_for_counter(secret, int(time.time()) // totp.PERIOD_SECONDS)


def counter_code(secret: str, counter: int) -> str:
    return totp.code_for_counter(secret, counter)


def enable_2fa(user: User) -> str:
    secret = totp.generate_secret()
    user.totp_secret = secret
    user.totp_enabled = True
    user.totp_confirmed_at = timezone.now()
    user.save(
        update_fields=[
            "totp_secret",
            "totp_enabled",
            "totp_confirmed_at",
        ]
    )
    return secret


class TwoFactorLoginTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.admin = complete_setup()
        self.secret = enable_2fa(self.admin)

    def login(self, identifier="admin", password=VALID_PASSWORD):
        return self.client.post(
            reverse("auth-login"),
            {"identifier": identifier, "password": password},
        )

    def test_password_only_login_returns_challenge_without_session(self):
        response = self.login()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["two_factor_required"])
        self.assertTrue(response.data["challenge"])
        self.assertNotIn("user", response.data)
        self.assertNotIn("sessionid", self.client.cookies)

    def test_valid_code_completes_login_and_opens_session(self):
        response = self.login()
        challenge = response.data["challenge"]
        counter = int(time.time()) // totp.PERIOD_SECONDS
        verify = self.client.post(
            reverse("auth-2fa-verify"),
            {"challenge": challenge, "code": counter_code(self.secret, counter)},
        )
        self.assertEqual(verify.status_code, 200)
        self.assertEqual(verify.data["user"]["username"], "admin")
        self.assertTrue(verify.data["user"]["totp_enabled"])
        self.assertIn("sessionid", self.client.cookies)

        admin_page = self.client.get(reverse("admin-users"))
        self.assertEqual(admin_page.status_code, 200)

    def test_wrong_code_does_not_open_session(self):
        response = self.login()
        verify = self.client.post(
            reverse("auth-2fa-verify"),
            {"challenge": response.data["challenge"], "code": "000000"},
        )
        self.assertEqual(verify.status_code, 400)
        self.assertEqual(verify.data["code"], "invalid_code")
        self.assertNotIn("sessionid", self.client.cookies)

    def test_totp_code_cannot_be_replayed(self):
        response = self.login()
        challenge = response.data["challenge"]
        counter = int(time.time()) // totp.PERIOD_SECONDS
        code = counter_code(self.secret, counter)
        first = self.client.post(
            reverse("auth-2fa-verify"),
            {"challenge": challenge, "code": code},
        )
        self.assertEqual(first.status_code, 200)
        self.client.cookies.clear()
        replay = self.client.post(
            reverse("auth-2fa-verify"),
            {"challenge": challenge, "code": code},
        )
        self.assertEqual(replay.status_code, 400)
        self.assertEqual(replay.data["code"], "invalid_code")

    def test_invalid_challenge_is_rejected(self):
        response = self.client.post(
            reverse("auth-2fa-verify"),
            {"challenge": "non-firmato", "code": "123456"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "invalid_challenge")

    def test_recovery_code_logs_in_once(self):
        RecoveryCode.objects.create(
            user=self.admin,
            code_hash=totp.hash_recovery_code("ABCD-EFGH-IJKL"),
        )
        response = self.login()
        challenge = response.data["challenge"]
        first = self.client.post(
            reverse("auth-2fa-verify"),
            {"challenge": challenge, "code": "abcd efgh ijkl"},
        )
        self.assertEqual(first.status_code, 200)
        self.client.cookies.clear()
        replay = self.client.post(
            reverse("auth-2fa-verify"),
            {"challenge": challenge, "code": "ABCD-EFGH-IJKL"},
        )
        self.assertEqual(replay.status_code, 400)
        self.assertEqual(replay.data["code"], "invalid_code")


class TwoFactorSetupTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.admin = complete_setup()
        self.client.force_authenticate(user=self.admin)

    def test_setup_confirm_and_status(self):
        setup = self.client.post(reverse("auth-2fa-setup"))
        self.assertEqual(setup.status_code, 200)
        self.assertTrue(setup.data["secret"])
        self.assertTrue(setup.data["otpauth_uri"].startswith("otpauth://totp/"))

        wrong = self.client.post(
            reverse("auth-2fa-confirm"), {"code": "000000"}
        )
        self.assertEqual(wrong.status_code, 400)
        self.assertEqual(wrong.data["code"], "invalid_code")

        counter = int(time.time()) // totp.PERIOD_SECONDS
        confirm = self.client.post(
            reverse("auth-2fa-confirm"),
            {"code": counter_code(setup.data["secret"], counter)},
        )
        self.assertEqual(confirm.status_code, 200)
        self.assertTrue(confirm.data["enabled"])
        self.assertEqual(len(confirm.data["recovery_codes"]), totp.RECOVERY_CODE_COUNT)

        status = self.client.get(reverse("auth-2fa-status"))
        self.assertEqual(status.status_code, 200)
        self.assertTrue(status.data["enabled"])
        self.assertEqual(
            status.data["recovery_codes_remaining"],
            totp.RECOVERY_CODE_COUNT,
        )

        again = self.client.post(reverse("auth-2fa-setup"))
        self.assertEqual(again.status_code, 409)

    def test_confirm_without_setup_is_rejected(self):
        response = self.client.post(
            reverse("auth-2fa-confirm"), {"code": "123456"}
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "two_factor_setup_required")

    def test_disable_requires_password_and_code(self):
        setup = self.client.post(reverse("auth-2fa-setup"))
        counter = int(time.time()) // totp.PERIOD_SECONDS
        self.client.post(
            reverse("auth-2fa-confirm"),
            {"code": counter_code(setup.data["secret"], counter)},
        )

        wrong_password = self.client.post(
            reverse("auth-2fa-disable"),
            {"password": "sbagliata", "code": "123456"},
        )
        self.assertEqual(wrong_password.status_code, 400)
        self.assertEqual(wrong_password.data["code"], "invalid_password")

        disable = self.client.post(
            reverse("auth-2fa-disable"),
            {
                "password": VALID_PASSWORD,
                "code": counter_code(setup.data["secret"], counter + 1),
            },
        )
        self.assertEqual(disable.status_code, 200)
        self.assertFalse(disable.data["enabled"])
        self.admin.refresh_from_db()
        self.assertFalse(self.admin.totp_enabled)
        self.assertEqual(self.admin.totp_secret, "")

    def test_recovery_codes_can_be_regenerated(self):
        setup = self.client.post(reverse("auth-2fa-setup"))
        counter = int(time.time()) // totp.PERIOD_SECONDS
        self.client.post(
            reverse("auth-2fa-confirm"),
            {"code": counter_code(setup.data["secret"], counter)},
        )
        first = self.client.post(
            reverse("auth-2fa-recovery-codes"),
            {
                "password": VALID_PASSWORD,
                "code": counter_code(setup.data["secret"], counter + 1),
            },
        )
        self.assertEqual(first.status_code, 200)
        self.assertEqual(len(first.data["recovery_codes"]), totp.RECOVERY_CODE_COUNT)
        self.assertEqual(
            self.admin.recovery_codes.count(), totp.RECOVERY_CODE_COUNT
        )


class TwoFactorTokenLoginTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.admin = complete_setup()
        self.user = User.objects.create_user(
            email="token-2fa@example.com",
            password=VALID_PASSWORD,
            status=User.Status.ACTIVE,
        )
        self.secret = enable_2fa(self.user)

    def test_token_login_with_2fa_returns_token_after_code(self):
        response = self.client.post(
            reverse("v1-auth:login"),
            {
                "identifier": "token-2fa@example.com",
                "password": VALID_PASSWORD,
                "device_name": "Pixel",
                "platform": "android",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["two_factor_required"])
        self.assertNotIn("token", response.data)

        counter = int(time.time()) // totp.PERIOD_SECONDS
        verify = self.client.post(
            reverse("v1-auth:two-factor-verify"),
            {
                "challenge": response.data["challenge"],
                "code": counter_code(self.secret, counter),
            },
        )
        self.assertEqual(verify.status_code, 200)
        self.assertEqual(verify.data["token_type"], "Bearer")
        self.assertTrue(verify.data["token"])

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {verify.data['token']}")
        me = self.client.get(reverse("v1-auth:me"))
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.data["user"]["email"], "token-2fa@example.com")

    def test_admin_cannot_use_token_login(self):
        enable_2fa(self.admin)
        response = self.client.post(
            reverse("v1-auth:login"),
            {"identifier": "admin", "password": VALID_PASSWORD},
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["code"], "admin_uses_web")

    def test_status_endpoint_is_unauthenticated_for_anonymous(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(reverse("auth-2fa-status"))
        self.assertEqual(response.status_code, 401)
