#!/usr/bin/env python3
"""Test dei controlli operativi (alert, backup, disco, certificato)."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from alert import send_alert
from healthcheck import (
    check_backup,
    check_certificate,
    check_disk,
    parse_iso,
    run_checks,
)

NOW = datetime(2026, 11, 13, 12, 0, tzinfo=timezone.utc)


class BackupChecksTests(unittest.TestCase):
    def _status(self, payload: dict) -> Path:
        directory = tempfile.mkdtemp()
        path = Path(directory) / "status.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_recent_success_has_no_problems(self):
        path = self._status(
            {
                "status": "ok",
                "last_success": (NOW - timedelta(minutes=5)).isoformat(),
            }
        )
        self.assertEqual(check_backup(path, 30, now=NOW), [])

    def test_stale_success_is_reported(self):
        path = self._status(
            {
                "status": "ok",
                "last_success": (NOW - timedelta(minutes=90)).isoformat(),
            }
        )
        problems = check_backup(path, 30, now=NOW)
        self.assertTrue(problems)
        self.assertIn("troppo vecchio", problems[0])

    def test_failed_backup_is_reported(self):
        path = self._status(
            {
                "status": "failed",
                "last_success": NOW.isoformat(),
                "last_error": "B2 non raggiungibile",
            }
        )
        problems = check_backup(path, 30, now=NOW)
        self.assertTrue(any("fallito" in problem for problem in problems))

    def test_missing_status_is_reported(self):
        problems = check_backup("/percorso/inesistente/status.json", 30, now=NOW)
        self.assertTrue(problems)

    def test_parse_iso_handles_naive_and_invalid(self):
        self.assertEqual(
            parse_iso("2026-11-13T12:00:00").tzinfo, timezone.utc
        )
        self.assertIsNone(parse_iso("non-una-data"))


class DiskAndCertificateTests(unittest.TestCase):
    def test_disk_threshold(self):
        usage = type("Usage", (), {"used": 90, "total": 100, "free": 10})()
        with patch("healthcheck.shutil.disk_usage", return_value=usage):
            self.assertTrue(check_disk("/", 85))
            self.assertEqual(check_disk("/", 95), [])

    def test_certificate_expiring_soon(self):
        soon = NOW.timestamp() + 10 * 86400
        with patch("healthcheck._certificate_timestamp", return_value=soon):
            problems = check_certificate("spendy.example.com", 14, now=NOW)
        self.assertTrue(problems)
        self.assertIn("scadenza", problems[0])

    def test_certificate_valid_is_ok(self):
        later = NOW.timestamp() + 60 * 86400
        with patch("healthcheck._certificate_timestamp", return_value=later):
            self.assertEqual(
                check_certificate("spendy.example.com", 14, now=NOW), []
            )

    def test_certificate_unreachable_is_reported(self):
        with patch(
            "healthcheck._certificate_timestamp", side_effect=OSError("down")
        ):
            problems = check_certificate("spendy.example.com", 14, now=NOW)
        self.assertTrue(problems)


class RunChecksTests(unittest.TestCase):
    def test_run_checks_aggregates_sources(self):
        directory = tempfile.mkdtemp()
        path = Path(directory) / "status.json"
        path.write_text(
            json.dumps(
                {
                    "status": "ok",
                    "last_success": (NOW - timedelta(minutes=5)).isoformat(),
                }
            ),
            encoding="utf-8",
        )
        usage = type("Usage", (), {"used": 95, "total": 100, "free": 5})()
        with patch("healthcheck.shutil.disk_usage", return_value=usage):
            problems = run_checks(
                {
                    "SPENDY_BACKUP_STATUS_FILE": str(path),
                    "SPENDY_BACKUP_MAX_AGE_MINUTES": "30",
                    "SPENDY_DISK_MAX_PERCENT": "85",
                    "SPENDY_DOMAIN": "",
                }
            )
        self.assertTrue(any("disco" in problem for problem in problems))


class AlertTests(unittest.TestCase):
    def test_without_webhook_alert_is_logged_only(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(send_alert("titolo", "messaggio"))

    def test_failure_message_contains_unit(self):
        from alert import failure_message

        self.assertIn("spendy-backup.service", failure_message("spendy-backup.service"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
