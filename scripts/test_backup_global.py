import importlib.util
import json
import os
import tempfile
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("backup_global.py")
SPEC = importlib.util.spec_from_file_location("backup_global", MODULE_PATH)
backup_global = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(backup_global)


class BucketNameTests(unittest.TestCase):
    def test_bucket_names(self):
        moment = datetime(2026, 11, 4, 12, 0, tzinfo=timezone.utc)
        self.assertEqual(
            backup_global.bucket_name(moment, "daily"), "spendy-2026-11-04.tar.age"
        )
        self.assertEqual(
            backup_global.bucket_name(moment, "weekly"), "spendy-2026-W45.tar.age"
        )
        self.assertEqual(
            backup_global.bucket_name(moment, "monthly"), "spendy-2026-11.tar.age"
        )


class RetentionTests(unittest.TestCase):
    def test_prune_local_keeps_newest_by_name(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            for day in range(1, 6):
                (path / f"spendy-2026-11-{day:02d}.tar.age").write_text("x")
            removed = backup_global.prune_local(path, 3)
            remaining = sorted(item.name for item in path.glob("*.tar.age"))
            self.assertEqual(len(removed), 2)
            self.assertEqual(
                remaining,
                [
                    "spendy-2026-11-03.tar.age",
                    "spendy-2026-11-04.tar.age",
                    "spendy-2026-11-05.tar.age",
                ],
            )

    def test_prune_incremental_removes_old_files(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            old = path / "spendy-old.tar.age"
            new = path / "spendy-new.tar.age"
            old.write_text("old")
            new.write_text("new")
            old_time = time.time() - 49 * 3600
            os.utime(old, (old_time, old_time))
            removed = backup_global.prune_incremental(path, 48)
            self.assertEqual(removed, [old])
            self.assertFalse(old.exists())
            self.assertTrue(new.exists())


class LatestBackupTests(unittest.TestCase):
    def test_latest_backup_searches_all_buckets(self):
        with tempfile.TemporaryDirectory() as directory:
            original = backup_global.BACKUP_DIR
            try:
                backup_global.BACKUP_DIR = Path(directory)
                for bucket in ("incremental", "daily", "weekly", "monthly"):
                    (Path(directory) / bucket).mkdir()
                old = Path(directory) / "daily" / "spendy-old.tar.age"
                new = Path(directory) / "weekly" / "spendy-new.tar.age"
                old.write_text("old")
                new.write_text("new")
                old_time = time.time() - 3600
                os.utime(old, (old_time, old_time))
                self.assertEqual(backup_global.latest_backup(), new)
            finally:
                backup_global.BACKUP_DIR = original


class StatusTests(unittest.TestCase):
    def test_write_and_read_status(self):
        with tempfile.TemporaryDirectory() as directory:
            original = backup_global.STATUS_FILE
            try:
                backup_global.STATUS_FILE = Path(directory) / "status.json"
                backup_global.write_status(
                    last_run="2026-11-04T12:00:00+00:00",
                    status="ok",
                    restore_test={"status": "ok"},
                )
                status = backup_global.read_status()
                self.assertEqual(status["status"], "ok")
                self.assertEqual(status["restore_test"]["status"], "ok")
                self.assertEqual(oct(backup_global.STATUS_FILE.stat().st_mode & 0o777), "0o644")
                self.assertEqual(json.loads(backup_global.STATUS_FILE.read_text())["status"], "ok")
            finally:
                backup_global.STATUS_FILE = original


if __name__ == "__main__":
    unittest.main()
