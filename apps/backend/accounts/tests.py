from django.contrib.auth.hashers import make_password
from django.urls import reverse
from rest_framework.test import APITestCase

from .models import GlobalSettings, User

VALID_PASSWORD = "Spendy-Fondamenta-2026"


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
        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.data)

    def test_weak_password_is_refused(self):
        response = self.register(password="12345678")
        self.assertEqual(response.status_code, 400)
        self.assertIn("password", response.data)

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


class AuthTests(APITestCase):
    def setUp(self):
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


class HealthTests(APITestCase):
    def test_health_reports_database(self):
        response = self.client.get(reverse("health"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "ok")
