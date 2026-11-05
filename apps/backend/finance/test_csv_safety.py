from django.test import SimpleTestCase

from .csv_safety import restore_csv_text, sanitize_csv_text


class CsvSafetyTests(SimpleTestCase):
    def test_dangerous_prefixes_are_escaped_and_reversible(self):
        for value in ("=foo", "+1", "-1", "@cmd", "\tcell", "\rcell"):
            escaped = sanitize_csv_text(value)
            self.assertEqual(escaped, "'" + value)
            self.assertEqual(restore_csv_text(escaped), value)

    def test_leading_apostrophe_is_escaped_and_reversible(self):
        for value, escaped in (
            ("'=foo", "''=foo"),
            ("''=foo", "'''=foo"),
            ("'hello", "''hello"),
            ("'", "''"),
        ):
            self.assertEqual(sanitize_csv_text(value), escaped)
            self.assertEqual(restore_csv_text(escaped), value)

    def test_plain_cells_are_left_unchanged(self):
        for value in ("hello", "100,00", "2026-01-01", "Caffè", "nota"):
            self.assertEqual(sanitize_csv_text(value), value)
            self.assertEqual(restore_csv_text(value), value)
