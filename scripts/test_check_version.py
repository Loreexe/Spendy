import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("check_version.py")
SPEC = importlib.util.spec_from_file_location("check_version", MODULE_PATH)
check_version = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(check_version)


class CheckVersionTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        (self.root / "apps" / "frontend").mkdir(parents=True)

    def tearDown(self):
        self.directory.cleanup()

    def write(self, version="0.4.0", compose="0.4.0", frontend="0.4.0", env="0.4.0"):
        (self.root / "VERSION").write_text(f"{version}\n", encoding="utf-8")
        (self.root / "compose.yaml").write_text(
            f"      SPENDY_VERSION: ${{SPENDY_VERSION:-{compose}}}\n",
            encoding="utf-8",
        )
        (self.root / ".env.example").write_text(
            f"SPENDY_VERSION={env}\n", encoding="utf-8"
        )
        (self.root / "apps" / "frontend" / "package.json").write_text(
            json.dumps({"version": frontend}), encoding="utf-8"
        )
        (self.root / "apps" / "frontend" / "package-lock.json").write_text(
            json.dumps({"version": frontend, "packages": {"": {"version": frontend}}}),
            encoding="utf-8",
        )

    def test_all_versions_match(self):
        self.write()
        self.assertEqual(check_version.check(self.root), [])

    def test_reports_each_divergent_version(self):
        self.write(compose="0.3.0", frontend="0.3.0", env="0.3.0")
        problems = check_version.check(self.root)
        self.assertEqual(len(problems), 5)
        self.assertTrue(all("atteso 0.4.0" in problem for problem in problems))

    def test_missing_declared_file(self):
        self.write()
        (self.root / "compose.yaml").unlink()
        problems = check_version.check(self.root)
        self.assertEqual(len(problems), 1)
        self.assertIn("Impossibile leggere le versioni dichiarate", problems[0])

    def test_malformed_package_json(self):
        self.write()
        (self.root / "apps" / "frontend" / "package.json").write_text(
            "{non-json", encoding="utf-8"
        )
        problems = check_version.check(self.root)
        self.assertEqual(len(problems), 1)
        self.assertIn("Impossibile leggere le versioni dichiarate", problems[0])

    def test_package_json_with_wrong_type(self):
        self.write()
        (self.root / "apps" / "frontend" / "package.json").write_text(
            "[]", encoding="utf-8"
        )
        problems = check_version.check(self.root)
        self.assertEqual(len(problems), 1)
        self.assertIn("Impossibile leggere le versioni dichiarate", problems[0])

    def test_empty_env_version(self):
        self.write(env="")
        problems = check_version.check(self.root)
        self.assertEqual(len(problems), 1)
        self.assertIn(".env.example: versione non trovata", problems[0])

    def test_invalid_version_file(self):
        self.write(version="0.4")
        problems = check_version.check(self.root)
        self.assertIn("VERSION non è una versione x.y.z valida", problems[0])

    def test_missing_version_file(self):
        problems = check_version.check(self.root)
        self.assertEqual(len(problems), 1)
        self.assertIn("Impossibile leggere VERSION", problems[0])


if __name__ == "__main__":
    unittest.main()
