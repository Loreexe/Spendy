"""Test del servizio MCP: token, errori HTTP e filtro tools/list."""
from __future__ import annotations

import asyncio
import unittest
from urllib.error import HTTPError
from unittest.mock import patch

import server


class BearerTests(unittest.TestCase):
    def test_bearer_value(self):
        self.assertEqual(server._bearer_value("Bearer mcp_abc"), "mcp_abc")
        self.assertEqual(server._bearer_value("bearer mcp_abc"), "mcp_abc")
        self.assertEqual(server._bearer_value("mcp_abc"), "")
        self.assertEqual(server._bearer_value(""), "")


class EnabledOperationsTests(unittest.TestCase):
    def test_401_becomes_actionable_error(self):
        error = HTTPError("http://backend", 401, "Unauthorized", {}, None)
        with patch("server._fetch_json", side_effect=error):
            with self.assertRaisesRegex(ValueError, "401"):
                server.fetch_enabled_operations("Bearer mcp_x")

    def test_permissions_are_returned(self):
        payload = {"permissions": {"accounts.list": "read"}}
        with patch("server._fetch_json", return_value=payload):
            self.assertEqual(
                server.fetch_enabled_operations("Bearer mcp_x"),
                {"accounts.list"},
            )


class ListToolsTests(unittest.TestCase):
    def setUp(self):
        self.server = server.SpendyMCPServer("test")

        async def dummy(ctx, params=None):  # pragma: no cover - schema soltanto
            return {}

        self.server.add_tool(dummy, name="accounts_list")
        server.TOOL_TO_OPERATION["accounts_list"] = "accounts.list"
        self.context = server._current_authorization.set("Bearer device-token")

    def tearDown(self):
        server._current_authorization.reset(self.context)

    def test_device_token_is_rejected_with_clear_message(self):
        with self.assertRaisesRegex(ValueError, "mcp_"):
            asyncio.run(self.server.list_tools())

    def test_valid_token_filters_tools(self):
        server._current_authorization.set("Bearer mcp_x")
        with patch(
            "server.fetch_enabled_operations", return_value={"accounts.list"}
        ):
            tools = asyncio.run(self.server.list_tools())
        self.assertEqual([tool.name for tool in tools], ["accounts_list"])

    def test_valid_token_without_permissions_returns_nothing(self):
        server._current_authorization.set("Bearer mcp_x")
        with patch("server.fetch_enabled_operations", return_value=set()):
            tools = asyncio.run(self.server.list_tools())
        self.assertEqual(tools, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
