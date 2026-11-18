"""Test del nucleo MCP lato backend: token, permessi, rate limit, audit, tag AI."""
from __future__ import annotations

import json
import time
import tempfile
from pathlib import Path

from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase

from finance.models import Profile, Tag, Transaction

from .models import AuditEvent, McpToken, User
from .tests import VALID_PASSWORD, complete_setup


def make_user(email="mcp@example.com") -> User:
    return User.objects.create_user(
        email=email, password=VALID_PASSWORD, status=User.Status.ACTIVE
    )


class McpTokenApiTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = make_user()
        self.admin = complete_setup()
        self.client.force_authenticate(user=self.user)

    def create_token(self, name="Claude Code", password=VALID_PASSWORD):
        return self.client.post(
            reverse("auth-mcp-tokens"),
            {"name": name, "password": password},
        )

    def test_catalog_is_available_and_groups_operations(self):
        response = self.client.get(reverse("auth-mcp-catalog"))
        self.assertEqual(response.status_code, 200)
        areas = {area["area"] for area in response.data["areas"]}
        self.assertIn("Conti", areas)
        self.assertIn("Import/Export", areas)

    def test_token_creation_requires_password_and_returns_secret_once(self):
        wrong = self.create_token(password="sbagliata")
        self.assertEqual(wrong.status_code, 400)
        self.assertEqual(wrong.data["code"], "invalid_password")

        response = self.create_token()
        self.assertEqual(response.status_code, 201)
        raw = response.data["token"]
        self.assertTrue(raw.startswith("mcp_"))
        self.assertEqual(response.data["token_data"]["permissions"], {})
        token = McpToken.objects.get(pk=response.data["token_data"]["id"])
        self.assertEqual(token.key_hash, McpToken.hash_key(raw))
        self.assertNotIn(raw, json.dumps(response.data["token_data"]))

    def test_global_admin_cannot_create_token(self):
        self.client.force_authenticate(user=self.admin)
        response = self.create_token()
        self.assertEqual(response.status_code, 400)

    def test_permission_matrix_validation(self):
        token_id = self.create_token().data["token_data"]["id"]
        response = self.client.patch(
            reverse("auth-mcp-token-detail", args=[token_id]),
            {
                "password": VALID_PASSWORD,
                "permissions": {"accounts.list": "write"},
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        response = self.client.patch(
            reverse("auth-mcp-token-detail", args=[token_id]),
            {
                "password": VALID_PASSWORD,
                "permissions": {"accounts.delete": "write", "accounts.list": "read"},
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["permissions"],
            {"accounts.delete": "write", "accounts.list": "read"},
        )

    def test_revoke_requires_password_and_blocks_token(self):
        created = self.create_token()
        token_id = created.data["token_data"]["id"]
        raw = created.data["token"]
        wrong = self.client.post(
            reverse("auth-mcp-token-revoke", args=[token_id]),
            {"password": "sbagliata"},
        )
        self.assertEqual(wrong.status_code, 400)
        revoked = self.client.post(
            reverse("auth-mcp-token-revoke", args=[token_id]),
            {"password": VALID_PASSWORD},
        )
        self.assertEqual(revoked.status_code, 200)
        token = McpToken.objects.get(pk=token_id)
        self.assertIsNotNone(token.revoked_at)

        api = APIClient()
        api.credentials(HTTP_AUTHORIZATION=f"Bearer {raw}")
        response = api.get("/api/v1/finance/accounts/")
        self.assertEqual(response.status_code, 401)


class McpAuthorizationTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = make_user()
        self.client.force_authenticate(user=self.user)
        # Crea il profilo con una richiesta di sessione.
        self.client.get("/api/v1/finance/accounts/")
        created = self.client.post(
            reverse("auth-mcp-tokens"),
            {"name": "Hermes", "password": VALID_PASSWORD},
        )
        self.token_id = created.data["token_data"]["id"]
        self.raw = created.data["token"]

    def grant(self, permissions: dict):
        response = self.client.patch(
            reverse("auth-mcp-token-detail", args=[self.token_id]),
            {"password": VALID_PASSWORD, "permissions": permissions},
            format="json",
        )
        self.assertEqual(response.status_code, 200)

    def token_client(self) -> APIClient:
        api = APIClient()
        api.credentials(HTTP_AUTHORIZATION=f"Bearer {self.raw}")
        return api

    def test_default_deny_and_audit(self):
        response = self.token_client().get("/api/v1/finance/accounts/")
        self.assertEqual(response.status_code, 403)
        event = AuditEvent.objects.filter(
            action=AuditEvent.Action.MCP_CALL
        ).latest("created_at")
        self.assertEqual(event.metadata["result"], "denied")
        self.assertEqual(event.metadata["reason"], "permission_denied")

    def test_read_permission_allows_reads_but_not_writes(self):
        self.grant({"accounts.list": "read"})
        api = self.token_client()
        self.assertEqual(api.get("/api/v1/finance/accounts/").status_code, 200)
        denied = api.post(
            "/api/v1/finance/accounts/",
            {"name": "Contanti", "type": "cash", "initial_balance": "100.00"},
            format="json",
        )
        self.assertEqual(denied.status_code, 403)

    def test_write_permission_allows_create(self):
        self.grant({"accounts.list": "read", "accounts.create": "write"})
        api = self.token_client()
        created = api.post(
            "/api/v1/finance/accounts/",
            {"name": "Contanti", "type": "cash", "initial_balance": "100.00"},
            format="json",
        )
        self.assertEqual(created.status_code, 201)
        allowed = AuditEvent.objects.filter(
            action=AuditEvent.Action.MCP_CALL,
            metadata__result="ok",
        ).latest("created_at")
        self.assertEqual(allowed.target, "accounts.create")
        self.assertIn("duration_ms", allowed.metadata)

    @override_settings(
        MCP_RATE_LIMIT_PER_MINUTE=2, MCP_WRITE_RATE_LIMIT_PER_MINUTE=2
    )
    def test_rate_limit(self):
        cache.clear()
        self.grant({"accounts.list": "read"})
        api = self.token_client()
        self.assertEqual(api.get("/api/v1/finance/accounts/").status_code, 200)
        self.assertEqual(api.get("/api/v1/finance/accounts/").status_code, 200)
        blocked = api.get("/api/v1/finance/accounts/")
        self.assertEqual(blocked.status_code, 429)
        event = AuditEvent.objects.filter(
            action=AuditEvent.Action.MCP_CALL,
            metadata__result="denied",
            metadata__reason="rate_limit",
        )
        self.assertTrue(event.exists())

    def test_ai_tag_on_transaction_written_via_mcp(self):
        self.grant(
            {
                "accounts.list": "read",
                "accounts.create": "write",
                "transactions.create": "write",
                "transactions.update": "write",
            }
        )
        api = self.token_client()
        account = api.post(
            "/api/v1/finance/accounts/",
            {"name": "Contanti", "type": "cash", "initial_balance": "100.00"},
            format="json",
        ).data
        response = api.post(
            "/api/v1/finance/transactions/",
            {
                "kind": "expense",
                "date": "2026-11-18",
                "description": "Spesa creata via MCP",
                "amount": "10.00",
                "account": account["id"],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertIn("AI", response.data["tags"])
        transaction = Transaction.objects.get(pk=response.data["id"])
        self.assertTrue(transaction.tags.filter(name="AI").exists())

        updated = api.patch(
            f"/api/v1/finance/transactions/{transaction.pk}/",
            {
                "kind": "expense",
                "date": "2026-11-18",
                "description": "Modificata via MCP",
                "amount": "10.00",
                "account": account["id"],
            },
            format="json",
        )
        self.assertEqual(updated.status_code, 200)
        self.assertIn("AI", updated.data["tags"])

    def test_session_write_does_not_add_ai_tag(self):
        account = self.client.post(
            "/api/v1/finance/accounts/",
            {"name": "Contanti", "type": "cash", "initial_balance": "100.00"},
            format="json",
        ).data
        response = self.client.post(
            "/api/v1/finance/transactions/",
            {
                "kind": "expense",
                "date": "2026-11-18",
                "description": "Spesa manuale",
                "amount": "10.00",
                "account": account["id"],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertNotIn("AI", response.data["tags"])
        self.assertFalse(
            Transaction.objects.get(pk=response.data["id"])
            .tags.filter(name="AI")
            .exists()
        )


class McpServiceContractTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = make_user()
        self.client.force_authenticate(user=self.user)

    def test_public_catalog_exposes_methods_and_paths(self):
        response = APIClient().get(reverse("mcp-public-catalog"))
        self.assertEqual(response.status_code, 200)
        operations = response.data["operations"]
        accounts = next(
            operation
            for operation in operations
            if operation["id"] == "accounts.list"
        )
        self.assertEqual(accounts["method"], "GET")
        self.assertTrue(accounts["path"].startswith("/api/v1/finance/"))
        detail = next(
            operation
            for operation in operations
            if operation["id"] == "transactions.get"
        )
        self.assertIn("{id}", detail["path"])
        public = APIClient().get(
            reverse("mcp-public-catalog"), REMOTE_ADDR="8.8.8.8"
        )
        self.assertEqual(public.status_code, 403)

    def test_context_returns_token_permissions_without_matrix(self):
        created = self.client.post(
            reverse("auth-mcp-tokens"),
            {"name": "Claude Code", "password": VALID_PASSWORD},
        )
        token_id = created.data["token_data"]["id"]
        self.client.patch(
            reverse("auth-mcp-token-detail", args=[token_id]),
            {
                "password": VALID_PASSWORD,
                "permissions": {"accounts.list": "read"},
            },
            format="json",
        )
        api = APIClient()
        api.credentials(
            HTTP_AUTHORIZATION=f"Bearer {created.data['token']}"
        )
        context = api.get("/api/v1/mcp/context/")
        self.assertEqual(context.status_code, 200)
        self.assertEqual(context.data["permissions"], {"accounts.list": "read"})
        self.assertIn("accounts.list", context.data["operations"])


class McpAdminToggleTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.admin = complete_setup()
        self.client.force_authenticate(user=self.admin)
        self.directory = tempfile.TemporaryDirectory()
        self.control_file = str(Path(self.directory.name) / "state.json")
        self.override = override_settings(MCP_CONTROL_FILE=self.control_file)
        self.override.enable()

    def tearDown(self):
        self.override.disable()
        self.directory.cleanup()

    def test_status_and_toggle_are_admin_only(self):
        anonymous = APIClient()
        self.assertIn(
            anonymous.get(reverse("admin-mcp")).status_code, (401, 403)
        )
        status = self.client.get(reverse("admin-mcp"))
        self.assertEqual(status.status_code, 200)
        self.assertFalse(status.data["enabled"])

        toggled = self.client.post(
            reverse("admin-mcp-toggle"), {"enabled": True}
        )
        self.assertEqual(toggled.status_code, 200)
        self.assertTrue(toggled.data["enabled"])
        saved = json.loads(Path(self.control_file).read_text())
        self.assertTrue(saved["enabled"])
        self.assertTrue(
            AuditEvent.objects.filter(
                action=AuditEvent.Action.MCP_SERVICE_TOGGLE
            ).exists()
        )
        self.assertTrue(self.client.get(reverse("admin-mcp")).data["enabled"])
