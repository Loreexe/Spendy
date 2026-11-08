import io
import json
import os
import tempfile
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from django.test import SimpleTestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from config.settings import read_version
from core.system import is_newer, parse_version

from .models import DevicePairing, GlobalSettings, User

VALID_PASSWORD = "Spendy-Fondamenta-2026"
NEW_PASSWORD = "Spendy-Nuova-Password-2026"


def complete_setup(password: str = VALID_PASSWORD) -> User:
    admin = User.objects.get(is_global_admin=True)
    admin.set_password(password)
    admin.status = User.Status.ACTIVE
    admin.save()
    settings = GlobalSettings.load()
    settings.setup_completed = True
    settings.save()
    return admin


class SetupTests(APITestCase):
    def test_admin_is_seeded_with_unusable_password(self):
        admin = User.objects.get(is_global_admin=True)
        self.assertEqual(admin.username, "admin")
        self.assertFalse(admin.has_usable_password())
        self.assertFalse(GlobalSettings.load().setup_completed)

    def test_setup_status_from_private_network(self):
        response = self.client.get(reverse("auth-setup-status"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["setup_required"])
        self.assertTrue(response.data["can_setup"])
        self.assertTrue(response.data["client_is_private"])
        self.assertEqual(response.data["admin_username"], "admin")

    def test_setup_status_from_public_address(self):
        response = self.client.get(
            reverse("auth-setup-status"), REMOTE_ADDR="8.8.8.8"
        )
        self.assertFalse(response.data["can_setup"])
        self.assertFalse(response.data["client_is_private"])

    def test_setup_status_from_lan_is_not_enough(self):
        response = self.client.get(
            reverse("auth-setup-status"), REMOTE_ADDR="192.168.1.50"
        )
        self.assertFalse(response.data["can_setup"])

    def test_forwarded_header_is_ignored_from_untrusted_peer(self):
        response = self.client.get(
            reverse("auth-setup-status"),
            REMOTE_ADDR="8.8.8.8",
            HTTP_X_FORWARDED_FOR="100.100.10.20",
        )
        self.assertFalse(response.data["can_setup"])

    def test_setup_uses_forwarded_for_only_from_trusted_proxy(self):
        response = self.client.get(
            reverse("auth-setup-status"),
            REMOTE_ADDR="172.18.0.2",
            HTTP_X_FORWARDED_FOR="8.8.8.8",
        )
        self.assertFalse(response.data["client_is_private"])

        response = self.client.get(
            reverse("auth-setup-status"),
            REMOTE_ADDR="172.18.0.2",
            HTTP_X_FORWARDED_FOR="100.100.10.20",
        )
        self.assertTrue(response.data["client_is_private"])

    def test_setup_refused_from_public_address(self):
        response = self.client.post(
            reverse("auth-setup"),
            {"password": VALID_PASSWORD, "password_confirm": VALID_PASSWORD},
            REMOTE_ADDR="8.8.8.8",
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["code"], "private_network_required")
        self.assertFalse(GlobalSettings.load().setup_completed)

    def test_setup_sets_admin_password_and_disables_endpoint(self):
        response = self.client.post(
            reverse("auth-setup"),
            {"password": VALID_PASSWORD, "password_confirm": VALID_PASSWORD},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["setup_completed"])

        admin = User.objects.get(is_global_admin=True)
        self.assertTrue(admin.check_password(VALID_PASSWORD))
        self.assertTrue(GlobalSettings.load().setup_completed)

        again = self.client.post(
            reverse("auth-setup"),
            {"password": "Altra-Password-2026", "password_confirm": "Altra-Password-2026"},
        )
        self.assertEqual(again.status_code, 409)

    def test_setup_rejects_mismatched_passwords(self):
        response = self.client.post(
            reverse("auth-setup"),
            {"password": VALID_PASSWORD, "password_confirm": "diversa-password"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("password_confirm", response.data)


class RegistrationTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.admin = complete_setup()

    def register(self, email="utente@example.com", password=VALID_PASSWORD):
        return self.client.post(
            reverse("auth-register"),
            {
                "email": email,
                "password": password,
                "password_confirm": password,
            },
        )

    def test_registration_defaults_to_pending(self):
        response = self.register()
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data["pending"])
        user = User.objects.get(email="utente@example.com")
        self.assertEqual(user.status, User.Status.PENDING)

        login = self.client.post(
            reverse("auth-login"),
            {"identifier": "utente@example.com", "password": VALID_PASSWORD},
        )
        self.assertEqual(login.status_code, 403)
        self.assertEqual(login.data["code"], "pending")

    def test_duplicate_email_is_case_insensitive(self):
        self.register("Utente@Example.com")
        response = self.register("utente@example.com")
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data["pending"])
        self.assertEqual(set(response.data.keys()), {"pending", "detail"})
        self.assertEqual(
            User.objects.filter(email__iexact="utente@example.com").count(), 1
        )

    def test_registration_does_not_reveal_existing_email(self):
        first = self.register("Utente@Example.com")
        second = self.register("utente@example.com")
        self.assertEqual(second.status_code, first.status_code)
        self.assertEqual(second.data, first.data)

    @patch("accounts.views.RegisterSerializer.save", side_effect=IntegrityError)
    def test_duplicate_during_save_is_neutral(self, _save):
        response = self.register()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(set(response.data.keys()), {"pending", "detail"})
        self.assertFalse(User.objects.filter(email="utente@example.com").exists())

    def test_duplicate_email_in_open_mode_is_neutral(self):
        self.client.force_authenticate(user=self.admin)
        self.client.patch(reverse("admin-settings"), {"registration_mode": "open"})
        self.client.force_authenticate(user=None)
        first = self.register("utente@example.com")
        second = self.register("utente@example.com")
        self.assertEqual(second.status_code, 201)
        self.assertEqual(second.data, first.data)
        self.assertFalse(second.data["pending"])
        self.assertEqual(
            User.objects.filter(email__iexact="utente@example.com").count(), 1
        )

    def test_weak_password_is_refused(self):
        response = self.register(password="12345678")
        self.assertEqual(response.status_code, 400)
        self.assertIn("password", response.data)

    def test_registration_is_rate_limited(self):
        for index in range(5):
            response = self.register(email=f"utente{index}@example.com")
            self.assertEqual(response.status_code, 201)

        response = self.register(email="utente-blocco@example.com")
        self.assertEqual(response.status_code, 429)

    def test_admin_approves_pending_user(self):
        self.register()
        user = User.objects.get(email="utente@example.com")
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            reverse("admin-user-decision", args=[user.pk, "approve"])
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["user"]["status"], User.Status.ACTIVE)

        self.client.force_authenticate(user=None)
        login = self.client.post(
            reverse("auth-login"),
            {"identifier": "utente@example.com", "password": VALID_PASSWORD},
        )
        self.assertEqual(login.status_code, 200)

    def test_admin_rejects_pending_user(self):
        self.register()
        user = User.objects.get(email="utente@example.com")
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            reverse("admin-user-decision", args=[user.pk, "reject"])
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["user"]["status"], User.Status.REJECTED)

        self.client.force_authenticate(user=None)
        login = self.client.post(
            reverse("auth-login"),
            {"identifier": "utente@example.com", "password": VALID_PASSWORD},
        )
        self.assertEqual(login.status_code, 403)
        self.assertEqual(login.data["code"], "rejected")

    def test_open_registration_creates_active_account(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(
            reverse("admin-settings"), {"registration_mode": "open"}
        )
        self.assertEqual(response.status_code, 200)
        self.client.force_authenticate(user=None)

        response = self.register()
        self.assertEqual(response.status_code, 201)
        self.assertFalse(response.data["pending"])

        login = self.client.post(
            reverse("auth-login"),
            {"identifier": "utente@example.com", "password": VALID_PASSWORD},
        )
        self.assertEqual(login.status_code, 200)

    def test_normal_user_cannot_use_admin_endpoints(self):
        self.register()
        user = User.objects.get(email="utente@example.com")
        user.status = User.Status.ACTIVE
        user.save()
        self.client.force_authenticate(user=user)

        self.assertEqual(self.client.get(reverse("admin-users")).status_code, 403)
        self.assertEqual(self.client.get(reverse("admin-settings")).status_code, 403)
        self.assertEqual(self.client.get(reverse("admin-system")).status_code, 403)


class DeviceTokenTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.admin = complete_setup()
        self.user = User.objects.create_user(
            email="token@example.com",
            password=VALID_PASSWORD,
            status=User.Status.ACTIVE,
        )

    def login(self, identifier="token@example.com", password=VALID_PASSWORD):
        return self.client.post(
            reverse("v1-auth:login"),
            {
                "identifier": identifier,
                "password": password,
                "device_name": "Realme GT7",
                "platform": "android",
            },
        )

    def test_token_login_returns_bearer_and_authenticates(self):
        response = self.login()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["token_type"], "Bearer")
        self.assertTrue(response.data["token"])
        self.assertEqual(response.data["device"]["name"], "Realme GT7")
        self.assertNotIn("sessionid", self.client.cookies)

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {response.data['token']}"
        )
        me = self.client.get(reverse("v1-auth:me"))
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.data["user"]["email"], "token@example.com")

    def test_token_login_rejects_admin(self):
        admin = self.admin
        response = self.login("admin", VALID_PASSWORD)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["code"], "admin_uses_web")
        self.assertFalse(admin.device_tokens.exists())

    def test_logout_revokes_token(self):
        token = self.login().data["token"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual(self.client.post(reverse("v1-auth:logout")).status_code, 200)
        # Il token revocato non autentica più.
        self.assertEqual(self.client.get(reverse("v1-auth:me")).status_code, 401)

    def test_devices_list_rename_and_revoke(self):
        token = self.login().data["token"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        devices = self.client.get(reverse("v1-auth:devices"))
        self.assertEqual(devices.status_code, 200)
        self.assertEqual(len(devices.data["devices"]), 1)
        self.assertTrue(devices.data["devices"][0]["is_current"])

        device_id = devices.data["devices"][0]["id"]
        renamed = self.client.patch(
            reverse("v1-auth:device-detail", args=[device_id]),
            {"name": "Telefono personale"},
            format="json",
        )
        self.assertEqual(renamed.status_code, 200)
        self.assertEqual(renamed.data["name"], "Telefono personale")

        revoked = self.client.delete(
            reverse("v1-auth:device-detail", args=[device_id])
        )
        self.assertEqual(revoked.status_code, 200)
        self.client.credentials()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual(self.client.get(reverse("v1-auth:me")).status_code, 401)

    def test_password_change_can_revoke_other_tokens(self):
        first = self.login().data["token"]
        second = self.login().data["token"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {first}")
        response = self.client.post(
            reverse("v1-auth:password"),
            {
                "current_password": VALID_PASSWORD,
                "new_password": NEW_PASSWORD,
                "new_password_confirm": NEW_PASSWORD,
                "revoke_other_devices": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["revoked_devices"], 1)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {second}")
        self.assertEqual(self.client.get(reverse("v1-auth:me")).status_code, 401)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {first}")
        self.assertEqual(self.client.get(reverse("v1-auth:me")).status_code, 200)

    def test_pairing_requires_origin_approval_and_is_single_use(self):
        origin_token = self.login().data["token"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {origin_token}")
        created = self.client.post(reverse("v1-auth:pairings"))
        self.assertEqual(created.status_code, 201)
        code = created.data["code"]
        pairing_id = created.data["pairing"]["id"]
        self.assertTrue(created.data["qr_payload"].startswith("spendy://pair?"))

        self.client.credentials()
        claimed = self.client.post(
            reverse("v1-auth:pairing-claim"),
            {"code": code, "device_name": "Tablet", "platform": "android"},
            format="json",
        )
        self.assertEqual(claimed.status_code, 200)
        claim = claimed.data["claim_token"]

        status = self.client.get(
            reverse("v1-auth:pairing-status", args=[pairing_id]),
            HTTP_X_PAIRING_CLAIM=claim,
        )
        self.assertEqual(status.status_code, 200)
        self.assertEqual(status.data["status"], "claimed")

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {origin_token}")
        approved = self.client.post(
            reverse("v1-auth:pairing-approve", args=[pairing_id])
        )
        self.assertEqual(approved.status_code, 200)
        self.assertEqual(approved.data["status"], "approved")

        self.client.credentials()
        completed = self.client.post(
            reverse("v1-auth:pairing-complete", args=[pairing_id]),
            HTTP_X_PAIRING_CLAIM=claim,
        )
        self.assertEqual(completed.status_code, 201)
        self.assertTrue(completed.data["token"])
        self.assertEqual(completed.data["device"]["name"], "Tablet")

        again = self.client.post(
            reverse("v1-auth:pairing-complete", args=[pairing_id]),
            HTTP_X_PAIRING_CLAIM=claim,
        )
        self.assertEqual(again.status_code, 409)
        self.assertEqual(again.data["code"], "pairing_used")

    def test_pairing_cannot_be_approved_by_another_device(self):
        origin_token = self.login().data["token"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {origin_token}")
        pairing_id = self.client.post(reverse("v1-auth:pairings")).data["pairing"]["id"]

        other_token = self.login().data["token"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {other_token}")
        response = self.client.post(
            reverse("v1-auth:pairing-approve", args=[pairing_id])
        )
        self.assertEqual(response.status_code, 403)

    def test_pairing_expires(self):
        origin_token = self.login().data["token"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {origin_token}")
        created = self.client.post(reverse("v1-auth:pairings"))
        code = created.data["code"]
        pairing_id = created.data["pairing"]["id"]
        self.client.credentials()
        claim = self.client.post(
            reverse("v1-auth:pairing-claim"),
            {"code": code, "device_name": "Tablet"},
            format="json",
        ).data["claim_token"]
        DevicePairing.objects.filter(pk=pairing_id).update(
            expires_at=timezone.now() - timedelta(seconds=1)
        )
        response = self.client.get(
            reverse("v1-auth:pairing-status", args=[pairing_id]),
            HTTP_X_PAIRING_CLAIM=claim,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "expired")


class VersionTests(SimpleTestCase):
    def test_env_variable_has_precedence(self):
        with patch.dict(os.environ, {"SPENDY_VERSION": "9.9.9"}):
            self.assertEqual(read_version(), "9.9.9")

    def test_version_file_is_the_fallback(self):
        root = Path(settings.BASE_DIR).parent.parent
        version_file = root / "VERSION"
        if not version_file.exists():
            self.skipTest("VERSION non è presente nell'immagine backend")
        expected = version_file.read_text(encoding="utf-8").strip()
        clean_env = {
            name: value
            for name, value in os.environ.items()
            if name != "SPENDY_VERSION"
        }
        with patch.dict(os.environ, clean_env, clear=True):
            self.assertEqual(read_version(), expected)


class AdminSystemTests(APITestCase):
    def setUp(self):
        self.admin = complete_setup()
        self.client.force_authenticate(user=self.admin)

    @override_settings(SPENDY_VERSION="0.3.0")
    def test_system_returns_version_and_database_without_network(self):
        with patch("core.system.urllib.request.urlopen") as urlopen:
            response = self.client.get(reverse("admin-system"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["current_version"], "0.3.0")
        self.assertEqual(response.data["database"], "ok")
        self.assertIsNone(response.data["checked_at"])
        self.assertIsNone(response.data["latest"])
        self.assertFalse(response.data["update_available"])
        self.assertIsNone(response.data["backup"])
        urlopen.assert_not_called()

    @override_settings(SPENDY_VERSION="0.3.0")
    def test_system_reads_backup_status(self):
        with tempfile.TemporaryDirectory() as directory:
            status_path = Path(directory) / "status.json"
            status_path.write_text(
                json.dumps(
                    {
                        "last_run": "2026-11-04T12:00:00+00:00",
                        "last_success": "2026-11-04T12:00:00+00:00",
                        "status": "ok",
                        "offsite": "ok",
                        "last_error": None,
                        "restore_test": {
                            "last_run": "2026-11-01T03:00:00+00:00",
                            "last_success": "2026-11-01T03:00:00+00:00",
                            "status": "ok",
                            "error": None,
                        },
                    }
                ),
                encoding="utf-8",
            )
            with override_settings(BACKUP_STATUS_FILE=str(status_path)):
                response = self.client.get(reverse("admin-system"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["backup"]["status"], "ok")
        self.assertEqual(response.data["backup"]["offsite"], "ok")
        self.assertEqual(
            response.data["backup"]["restore_test"]["status"], "ok"
        )

    @override_settings(SPENDY_VERSION="0.3.0")
    @patch("core.system.urllib.request.urlopen")
    def test_check_reports_newer_release(self, urlopen):
        urlopen.return_value = io.BytesIO(
            json.dumps(
                {
                    "tag_name": "v0.4.0",
                    "html_url": (
                        "https://github.com/Loreexe/Spendy/releases/tag/v0.4.0"
                    ),
                    "published_at": "2026-11-05T10:00:00Z",
                    "body": "Novità della release",
                    "prerelease": False,
                    "draft": False,
                }
            ).encode()
        )

        response = self.client.get(reverse("admin-system"), {"check": "1"})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["update_available"])
        self.assertEqual(response.data["latest"]["version"], "0.4.0")
        self.assertEqual(response.data["latest"]["tag"], "v0.4.0")
        self.assertEqual(response.data["latest"]["notes"], "Novità della release")
        self.assertIsNotNone(response.data["checked_at"])
        self.assertIsNone(response.data["error"])

    @override_settings(SPENDY_VERSION="0.4.0")
    @patch("core.system.urllib.request.urlopen")
    def test_check_reports_no_update_when_versions_match(self, urlopen):
        urlopen.return_value = io.BytesIO(
            json.dumps(
                {
                    "tag_name": "v0.4.0",
                    "html_url": (
                        "https://github.com/Loreexe/Spendy/releases/tag/v0.4.0"
                    ),
                    "published_at": "2026-11-05T10:00:00Z",
                    "body": "",
                    "prerelease": False,
                    "draft": False,
                }
            ).encode()
        )

        response = self.client.get(reverse("admin-system"), {"check": "1"})

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["update_available"])
        self.assertEqual(response.data["latest"]["version"], "0.4.0")

    @patch("core.system.urllib.request.urlopen")
    def test_check_handles_network_error(self, urlopen):
        urlopen.side_effect = URLError("offline")

        response = self.client.get(reverse("admin-system"), {"check": "1"})

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data["latest"])
        self.assertIn("non raggiungibile", response.data["error"])
        self.assertIsNotNone(response.data["checked_at"])

    @patch("core.system.urllib.request.urlopen")
    def test_check_handles_missing_release(self, urlopen):
        urlopen.side_effect = HTTPError(
            "https://api.github.com/", 404, "Not Found", {}, None
        )

        response = self.client.get(reverse("admin-system"), {"check": "1"})

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data["latest"])
        self.assertIn("Nessuna release", response.data["error"])

    @patch("core.system.urllib.request.urlopen")
    def test_check_ignores_prerelease_payload(self, urlopen):
        urlopen.return_value = io.BytesIO(
            json.dumps(
                {
                    "tag_name": "v0.4.0-rc1",
                    "prerelease": True,
                    "draft": False,
                }
            ).encode()
        )

        response = self.client.get(reverse("admin-system"), {"check": "1"})

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data["latest"])
        self.assertIn("prerelease", response.data["error"])

    def test_version_comparison(self):
        self.assertTrue(is_newer("0.3.0", "0.4.0"))
        self.assertFalse(is_newer("0.3.0", "0.3.0"))
        self.assertFalse(is_newer("0.3.0", "0.2.9"))
        self.assertIsNone(parse_version("not-a-version"))
        self.assertIsNone(parse_version("v0.4.0-rc1"))


class LoginLockoutTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            email="lockout@example.com", password=VALID_PASSWORD
        )
        self.user.status = User.Status.ACTIVE
        self.user.save()

    def tearDown(self):
        cache.clear()

    def login(self, password: str):
        return self.client.post(
            reverse("auth-login"),
            {"identifier": "lockout@example.com", "password": password},
        )

    @override_settings(LOGIN_MAX_ATTEMPTS=3, LOGIN_LOCKOUT_SECONDS=60)
    def test_lockout_after_repeated_failures(self):
        for _ in range(3):
            self.assertEqual(self.login("wrong-password").status_code, 400)

        response = self.login(VALID_PASSWORD)
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.data["code"], "too_many_attempts")
        self.assertEqual(response["Retry-After"], "60")

    @override_settings(LOGIN_MAX_ATTEMPTS=3, LOGIN_LOCKOUT_SECONDS=60)
    def test_successful_login_clears_failures(self):
        for _ in range(2):
            self.assertEqual(self.login("wrong-password").status_code, 400)

        self.assertEqual(self.login(VALID_PASSWORD).status_code, 200)

        for _ in range(3):
            self.assertEqual(self.login("wrong-password").status_code, 400)
        self.assertEqual(self.login(VALID_PASSWORD).status_code, 429)


class AuthTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.admin = complete_setup()
        self.user = User.objects.create_user(
            email="persona@example.com",
            password=VALID_PASSWORD,
            status=User.Status.ACTIVE,
        )

    def test_login_and_logout(self):
        response = self.client.post(
            reverse("auth-login"),
            {"identifier": "persona@example.com", "password": VALID_PASSWORD},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["user"]["email"], "persona@example.com")

        me = self.client.get(reverse("auth-me"))
        self.assertEqual(me.status_code, 200)
        self.assertIsNotNone(me.data["user"])

        response = self.client.post(reverse("auth-logout"))
        self.assertEqual(response.status_code, 200)
        me = self.client.get(reverse("auth-me"))
        self.assertIsNone(me.data["user"])

    def test_login_is_case_insensitive_on_email(self):
        response = self.client.post(
            reverse("auth-login"),
            {"identifier": "PERSONA@example.com", "password": VALID_PASSWORD},
        )
        self.assertEqual(response.status_code, 200)

    def test_invalid_credentials(self):
        response = self.client.post(
            reverse("auth-login"),
            {"identifier": "persona@example.com", "password": "password-errata"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "invalid_credentials")

    def test_anonymous_me(self):
        response = self.client.get(reverse("auth-me"))
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data["user"])

    def test_admin_can_add_optional_email(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(
            reverse("auth-me"), {"email": "admin@example.com"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["user"]["email"], "admin@example.com")

    def test_normal_user_cannot_remove_email(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(reverse("auth-me"), {"email": ""})
        self.assertEqual(response.status_code, 400)

    def test_user_can_set_username_and_login_with_it(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            reverse("auth-me"), {"username": "persona.uno"}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["user"]["username"], "persona.uno")
        self.client.force_authenticate(user=None)
        login = self.client.post(
            reverse("auth-login"),
            {"identifier": "persona.uno", "password": VALID_PASSWORD},
        )
        self.assertEqual(login.status_code, 200)
        self.assertEqual(login.data["user"]["username"], "persona.uno")

    def test_username_must_be_unique_case_insensitive(self):
        User.objects.create_user(
            username="occupato",
            email="altro@example.com",
            password=VALID_PASSWORD,
            status=User.Status.ACTIVE,
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            reverse("auth-me"), {"username": "OCCUPATO"}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("username", response.data)

    def test_username_validation_rules(self):
        self.client.force_authenticate(user=self.user)
        for bad in ("ab", "con spazio", "admin", "simbolo@!"):
            response = self.client.patch(
                reverse("auth-me"), {"username": bad}, format="json"
            )
            self.assertEqual(
                response.status_code, 400, f"{bad} doveva essere rifiutato"
            )

    def test_username_is_case_insensitive_at_login(self):
        self.client.force_authenticate(user=self.user)
        self.client.patch(
            reverse("auth-me"), {"username": "PersonaUno"}, format="json"
        )
        self.client.force_authenticate(user=None)
        login = self.client.post(
            reverse("auth-login"),
            {"identifier": "personauno", "password": VALID_PASSWORD},
        )
        self.assertEqual(login.status_code, 200)

    def test_admin_username_is_not_editable(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(
            reverse("auth-me"), {"username": "nuovo-admin"}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.username, "admin")

    def test_names_are_saved_and_exposed(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            reverse("auth-me"),
            {"first_name": "Ada", "last_name": "Lovelace"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["user"]["first_name"], "Ada")
        self.assertEqual(response.data["user"]["display_name"], "Ada Lovelace")
        self.user.refresh_from_db()
        self.assertEqual(self.user.get_full_name(), "Ada Lovelace")

    def test_avatar_upload_validation_and_delete(self):
        self.client.force_authenticate(user=self.user)
        png = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
            b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00"
            b"\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
            b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        upload = SimpleUploadedFile("avatar.png", png, content_type="image/png")
        response = self.client.post(
            reverse("auth-avatar"), {"avatar": upload}, format="multipart"
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["user"]["has_avatar"])
        image = self.client.get(reverse("auth-avatar"))
        self.assertEqual(image.status_code, 200)
        self.assertEqual(image["Content-Type"], "image/png")

        bad_type = SimpleUploadedFile(
            "avatar.txt", b"not-an-image", content_type="text/plain"
        )
        rejected = self.client.post(
            reverse("auth-avatar"), {"avatar": bad_type}, format="multipart"
        )
        self.assertEqual(rejected.status_code, 400)

        removed = self.client.delete(reverse("auth-avatar"))
        self.assertEqual(removed.status_code, 200)
        self.assertFalse(removed.data["user"]["has_avatar"])
        self.assertEqual(
            self.client.get(reverse("auth-avatar")).status_code, 404
        )

    def test_password_change(self):
        self.client.force_authenticate(user=self.user)
        wrong = self.client.post(
            reverse("auth-password"),
            {
                "current_password": "sbagliata",
                "new_password": NEW_PASSWORD,
                "new_password_confirm": NEW_PASSWORD,
            },
            format="json",
        )
        self.assertEqual(wrong.status_code, 400)

        mismatch = self.client.post(
            reverse("auth-password"),
            {
                "current_password": VALID_PASSWORD,
                "new_password": NEW_PASSWORD,
                "new_password_confirm": "diversa",
            },
            format="json",
        )
        self.assertEqual(mismatch.status_code, 400)

        ok = self.client.post(
            reverse("auth-password"),
            {
                "current_password": VALID_PASSWORD,
                "new_password": NEW_PASSWORD,
                "new_password_confirm": NEW_PASSWORD,
            },
            format="json",
        )
        self.assertEqual(ok.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(NEW_PASSWORD))
        # La sessione resta valida dopo il cambio.
        self.assertIsNotNone(self.client.get(reverse("auth-me")).data["user"])


class HealthTests(APITestCase):
    def test_health_reports_database(self):
        response = self.client.get(reverse("health"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "ok")
