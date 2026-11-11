from datetime import timedelta
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from accounts.models import User
from .imports import (
    detect_date_format,
    detect_decimal_separator,
    detect_delimiter,
    parse_amount,
    parse_csv,
    parse_date,
    parse_time,
)
from .models import Account, Transaction
from .tests import FinanceTestBase


def csv_file(rows, header="data;descrizione;categoria;conto;importo"):
    body = "\r\n".join([header, *[";".join(row) for row in rows]]) + "\r\n"
    return body.encode("utf-8-sig")


def row(date, description, category, account, amount, not_duplicate=False):
    return {
        "date": date,
        "description": description,
        "category": category,
        "account": account,
        "amount": amount,
        "not_duplicate": not_duplicate,
    }


VALID_ROWS = [
    ["01-10-2026", "Saldo iniziale", "altro", "Contanti", "-1000,00"],
    ["02-10-2026", "Spesa di prova", "spesa", "Contanti", "12,50"],
]


class ImportTestBase(FinanceTestBase):
    def upload(self, rows, header=None):
        data = csv_file(rows) if header is None else csv_file(rows, header)
        upload = SimpleUploadedFile("movimenti.csv", data, content_type="text/csv")
        return self.client.post(
            reverse("finance-import-analyze"), {"file": upload}, format="multipart"
        )

    def analyze_rows(self, rows):
        return self.client.post(
            reverse("finance-import-analyze"), {"rows": rows}, format="json"
        )

    def confirm_rows(self, rows):
        return self.client.post(
            reverse("finance-import-confirm"), {"rows": rows}, format="json"
        )

    def json_rows(self, rows):
        return [row(*item) for item in rows]


class TemplateTests(ImportTestBase):
    def test_template_download(self):
        response = self.client.get(reverse("finance-import-template"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response["Content-Type"].startswith("text/csv"))
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertIn(".csv", response["Content-Disposition"])
        content = response.content
        self.assertTrue(content.startswith(b"\xef\xbb\xbf"))
        text = content.decode("utf-8-sig")
        self.assertIn("data;descrizione;categoria;conto;importo;ora", text)
        self.assertIn("ESEMPIO", text)
        self.assertIn(";12:30", text)
        self.assertIn("\r\n", text)

    def test_global_admin_cannot_download(self):
        admin = User.objects.get(is_global_admin=True)
        self.client.force_authenticate(user=admin)
        response = self.client.get(reverse("finance-import-template"))
        self.assertEqual(response.status_code, 403)

    def test_authentication_required(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(reverse("finance-import-template"))
        self.assertIn(response.status_code, (401, 403))


class ParserTests(FinanceTestBase):
    def test_valid_file(self):
        rows, errors, delimiter = parse_csv(csv_file(VALID_ROWS))
        self.assertEqual(errors, [])
        self.assertEqual(delimiter, ";")
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["date"], "01-10-2026")
        self.assertEqual(rows[0]["account"], "Contanti")

    def test_wrong_header(self):
        rows, errors, _ = parse_csv(csv_file(VALID_ROWS, header="data;importo"))
        self.assertEqual(rows, [])
        self.assertEqual(errors[0]["code"], "header")

    def test_wrong_column_count(self):
        rows, errors, _ = parse_csv(csv_file([["01-10-2026", "Solo due"]]))
        self.assertEqual(rows, [])
        self.assertEqual(errors[0]["code"], "columns")

    def test_quoted_semicolon_is_accepted(self):
        data = (
            "data;descrizione;categoria;conto;importo\r\n"
            '01-10-2026;"Caffè; cornetto";bar;Contanti;3,50\r\n'
        ).encode("utf-8-sig")
        rows, errors, _ = parse_csv(data)
        self.assertEqual(errors, [])
        self.assertEqual(rows[0]["description"], "Caffè; cornetto")
        self.assertEqual(rows[0]["time"], "")

    def test_six_columns_with_time_are_accepted(self):
        data = (
            "data;descrizione;categoria;conto;importo;ora\r\n"
            "01-10-2026;Caffè;bar;Contanti;1,20;9:05\r\n"
        ).encode("utf-8-sig")
        rows, errors, _ = parse_csv(data)
        self.assertEqual(errors, [])
        self.assertEqual(rows[0]["time"], "9:05")

    def test_five_columns_are_still_accepted(self):
        rows, errors, _ = parse_csv(csv_file(VALID_ROWS))
        self.assertEqual(errors, [])
        self.assertEqual(rows[0]["time"], "")

    def test_mixed_five_and_six_columns_are_accepted(self):
        data = (
            "data;descrizione;categoria;conto;importo;ora\r\n"
            "01-10-2026;Prima;altro;Contanti;-10,00;08:00\r\n"
            "02-10-2026;Seconda;altro;Contanti;-20,00\r\n"
        ).encode("utf-8-sig")
        rows, errors, _ = parse_csv(data)
        self.assertEqual(errors, [])
        self.assertEqual(rows[0]["time"], "08:00")
        self.assertEqual(rows[1]["time"], "")

    def test_non_utf8_is_rejected(self):
        rows, errors, _ = parse_csv("caffè".encode("latin-1"))
        self.assertEqual(rows, [])
        self.assertEqual(errors[0]["code"], "encoding")

    def test_comma_delimiter_is_detected(self):
        data = (
            "data,descrizione,categoria,conto,importo\r\n"
            "2026-10-01,Saldo,altro,Contanti,-1000.00\r\n"
        ).encode("utf-8-sig")
        rows, errors, delimiter = parse_csv(data)
        self.assertEqual(errors, [])
        self.assertEqual(delimiter, ",")
        self.assertEqual(rows[0]["amount"], "-1000.00")

    def test_date_rules(self):
        self.assertEqual(parse_date("03-11-2026")[0].isoformat(), "2026-11-03")
        self.assertIsNotNone(parse_date("3-11-2026")[1])
        self.assertIsNotNone(parse_date("2026-11-03")[1])
        self.assertIsNotNone(parse_date("32-11-2026")[1])
        self.assertEqual(
            parse_date("2026-11-03", "YYYY-MM-DD")[0].isoformat(), "2026-11-03"
        )
        self.assertEqual(
            parse_date("03/11/2026", "DD/MM/YYYY")[0].isoformat(), "2026-11-03"
        )

    def test_amount_rules(self):
        self.assertEqual(parse_amount("12,50")[0], Decimal("12.50"))
        self.assertEqual(parse_amount("-100,00")[0], Decimal("-100.00"))
        self.assertEqual(parse_amount("12.50", ".")[0], Decimal("12.50"))
        self.assertEqual(parse_amount("150")[0], Decimal("150.00"))
        self.assertEqual(parse_amount("12,5")[0], Decimal("12.50"))
        self.assertIsNotNone(parse_amount("12.50")[1])
        self.assertIsNotNone(parse_amount("1.234,56")[1])
        self.assertIsNotNone(parse_amount("€12,50")[1])
        self.assertIsNotNone(parse_amount("0,00")[1])
        self.assertIsNotNone(parse_amount("12,345")[1])

    def test_time_rules(self):
        from datetime import time

        self.assertEqual(parse_time("12:00")[0], time(12, 0))
        self.assertEqual(parse_time("9:05")[0], time(9, 5))
        self.assertEqual(parse_time("23:59")[0], time(23, 59))
        self.assertEqual(parse_time("")[0], time(12, 0))
        self.assertEqual(parse_time("   ")[0], time(12, 0))
        self.assertIsNotNone(parse_time("24:00")[1])
        self.assertIsNotNone(parse_time("9:5")[1])
        self.assertIsNotNone(parse_time("9.05")[1])
        self.assertIsNotNone(parse_time("mezzogiorno")[1])


class FormatDetectionTests(FinanceTestBase):
    def test_delimiter(self):
        self.assertEqual(detect_delimiter("a;b;c;d;e\n1;2;3;4;5"), ";")
        self.assertEqual(detect_delimiter("a,b,c,d,e\n1,2,3,4,5"), ",")

    def test_date_format(self):
        self.assertEqual(detect_date_format(["2026-10-01", "2026-11-03"]), ("YYYY-MM-DD", False))
        self.assertEqual(detect_date_format(["03/11/2026", "25/12/2026"]), ("DD/MM/YYYY", False))
        self.assertEqual(detect_date_format(["03-11-2026", "04-12-2026"]), ("DD-MM-YYYY", True))

    def test_decimal_separator(self):
        self.assertEqual(detect_decimal_separator(["12,50", "-100,00"]), ",")
        self.assertEqual(detect_decimal_separator(["12.50", "-100.00"]), ".")


class AnalyzeTests(ImportTestBase):
    def test_valid_file_creates_account_with_opening(self):
        response = self.upload(VALID_ROWS)
        self.assertEqual(response.status_code, 200)
        data = response.data
        self.assertTrue(data["summary"]["can_confirm"])
        self.assertEqual(data["summary"]["accounts_to_create"], 1)
        self.assertEqual(data["summary"]["openings_total"], "1000.00")
        self.assertEqual(data["summary"]["expense_total"], "12.50")
        self.assertEqual(data["summary"]["available_total"], "1000.00")
        self.assertEqual(data["summary"]["covered_by_openings"], "12.50")
        self.assertEqual(data["summary"]["net_total"], "987.50")
        self.assertEqual(data["rows"][0]["kind"], "opening")
        self.assertEqual(data["rows"][1]["kind"], "expense")
        self.assertEqual(data["accounts"][0]["state"], "new")

    def test_covered_by_openings_is_zero_when_income_covers_expenses(self):
        response = self.upload(
            [
                ["01-10-2026", "Saldo", "altro", "Contanti", "-100,00"],
                ["02-10-2026", "Entrata", "altro", "Contanti", "-200,00"],
                ["03-10-2026", "Spesa", "spesa", "Contanti", "150,00"],
            ]
        )
        self.assertTrue(response.data["summary"]["can_confirm"])
        self.assertEqual(response.data["summary"]["covered_by_openings"], "0.00")
        self.assertEqual(response.data["summary"]["available_total"], "300.00")

    def test_missing_opening_is_an_error(self):
        response = self.upload(
            [
                ["01-10-2026", "Spesa subito", "spesa", "Contanti", "10,00"],
            ]
        )
        codes = [error["code"] for error in response.data["rows"][0]["errors"]]
        self.assertIn("missing_opening", codes)
        self.assertFalse(response.data["summary"]["can_confirm"])

    def test_ambiguous_opening_is_an_error(self):
        response = self.upload(
            [
                ["01-10-2026", "Prima entrata", "altro", "Contanti", "-100,00"],
                ["01-10-2026", "Seconda entrata", "altro", "Contanti", "-50,00"],
            ]
        )
        codes = [
            error["code"]
            for item in response.data["rows"]
            for error in item["errors"]
        ]
        self.assertIn("ambiguous_opening", codes)
        self.assertFalse(response.data["summary"]["can_confirm"])

    def test_insufficient_balance_is_an_error(self):
        response = self.upload(
            [
                ["01-10-2026", "Saldo", "altro", "Contanti", "-10,00"],
                ["02-10-2026", "Spesa", "spesa", "Contanti", "20,00"],
            ]
        )
        codes = [
            error["code"]
            for item in response.data["rows"]
            for error in item["errors"]
        ]
        self.assertIn("insufficient_balance", codes)
        self.assertFalse(response.data["summary"]["can_confirm"])

    def test_insufficient_balance_message_uses_italian_amounts(self):
        response = self.upload(
            [
                ["01-10-2026", "Saldo", "altro", "Contanti", "-10,00"],
                ["02-10-2026", "Spesa", "spesa", "Contanti", "20,00"],
            ]
        )
        message = response.data["rows"][1]["errors"][0]["message"]
        self.assertIn("disponibili 10,00", message)
        self.assertNotIn("10.00", message)

    def test_moving_row_date_can_fix_the_balance(self):
        base = [
            ["01-01-2024", "Saldo", "altro", "Contanti", "-100,00"],
            ["02-01-2024", "Spesa", "spesa", "Contanti", "120,00"],
            ["03-01-2024", "Entrata", "altro", "Contanti", "-30,00"],
        ]
        first = self.upload(base)
        codes = [e["code"] for item in first.data["rows"] for e in item["errors"]]
        self.assertIn("insufficient_balance", codes)

        fixed = [
            ["01-01-2024", "Saldo", "altro", "Contanti", "-100,00"],
            ["04-01-2024", "Spesa", "spesa", "Contanti", "120,00"],
            ["03-01-2024", "Entrata", "altro", "Contanti", "-30,00"],
        ]
        second = self.upload(fixed)
        codes = [e["code"] for item in second.data["rows"] for e in item["errors"]]
        self.assertNotIn("insufficient_balance", codes)
        self.assertTrue(second.data["summary"]["can_confirm"])

    def test_existing_account_reports_starting_balance(self):
        self.create_account(initial="100.00")
        tomorrow = (self.today + timedelta(days=1)).strftime("%d-%m-%Y")
        response = self.upload([[tomorrow, "Spesa", "spesa", "Contanti", "5,00"]])
        account = response.data["accounts"][0]
        self.assertEqual(account["balance_before"], "100.00")
        self.assertEqual(account["start_date"], (self.today + timedelta(days=1)).isoformat())
        self.assertEqual(account["state"], "existing")

    def test_comma_delimiter_iso_dates_and_dot_decimals(self):
        data = (
            "data,descrizione,categoria,conto,importo\r\n"
            "2026-01-10,Saldo,altro,Contanti,-1000.00\r\n"
            "2026-02-10,Spesa,spesa,Contanti,12.50\r\n"
        ).encode("utf-8-sig")
        upload = SimpleUploadedFile("movimenti.csv", data, content_type="text/csv")
        response = self.client.post(
            reverse("finance-import-analyze"), {"file": upload}, format="multipart"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["format"]["delimiter"], ",")
        self.assertEqual(response.data["format"]["date_format"], "YYYY-MM-DD")
        self.assertEqual(response.data["format"]["decimal_separator"], ".")
        self.assertTrue(response.data["summary"]["can_confirm"])
        self.assertEqual(response.data["rows"][0]["kind"], "opening")

    def test_same_day_rows_only_blame_the_row_that_goes_negative(self):
        response = self.upload(
            [
                ["01-01-2025", "Saldo", "altro", "Contanti", "-10,00"],
                ["02-01-2025", "Prima spesa", "spesa", "Contanti", "8,00"],
                ["02-01-2025", "Seconda spesa", "spesa", "Contanti", "5,00"],
            ]
        )
        first, second = response.data["rows"][1], response.data["rows"][2]
        self.assertEqual(first["errors"], [])
        self.assertEqual(second["errors"][0]["code"], "insufficient_balance")
        self.assertIn("disponibili 2,00", second["errors"][0]["message"])

    def test_duplicate_in_file(self):
        response = self.upload(
            [
                ["01-10-2026", "Saldo", "altro", "Contanti", "-100,00"],
                ["02-10-2026", "Caffè", "bar", "Contanti", "1,20"],
                ["02-10-2026", "Caffè", "bar", "Contanti", "1,20"],
            ]
        )
        codes = [
            error["code"]
            for item in response.data["rows"]
            for error in item["errors"]
        ]
        self.assertEqual(codes.count("duplicate_in_file"), 2)

    def test_opposite_signs_are_not_duplicates(self):
        account = self.create_account(initial="100.00").data
        today = self.today.strftime("%d-%m-%Y")
        response = self.upload(
            [
                [today, "Scambio di soldi", "trasferimento", "Contanti", "10"],
                [today, "Scambio di soldi", "trasferimento", "Contanti", "-10"],
            ]
        )
        codes = [error["code"] for item in response.data["rows"] for error in item["errors"]]
        self.assertNotIn("duplicate_in_file", codes)
        self.assertTrue(response.data["summary"]["can_confirm"])

    def test_not_duplicate_ack_clears_the_error(self):
        rows = self.json_rows(
            [
                ["01-10-2026", "Saldo", "altro", "Contanti", "-100,00"],
                ["02-10-2026", "Caffè", "bar", "Contanti", "1,20"],
                ["02-10-2026", "Caffè", "bar", "Contanti", "1,20"],
            ]
        )
        rows[1]["not_duplicate"] = True
        rows[2]["not_duplicate"] = True
        response = self.analyze_rows(rows)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["summary"]["can_confirm"])

    def test_duplicate_in_database(self):
        account = self.create_account(initial="100.00").data
        self.create_transaction(
            {
                "kind": "expense",
                "date": self.today.isoformat(),
                "description": "Caffè",
                "amount": "1.20",
                "account": account["id"],
            }
        )
        today = self.today.strftime("%d-%m-%Y")
        response = self.upload([[today, "Caffè", "bar", "Contanti", "1,20"]])
        codes = [error["code"] for error in response.data["rows"][0]["errors"]]
        self.assertIn("duplicate_in_database", codes)

    def test_example_row_is_an_error(self):
        response = self.upload(
            [["01-10-2026", "ESEMPIO — spesa", "esempio", "Contanti", "10,00"]]
        )
        codes = [error["code"] for error in response.data["rows"][0]["errors"]]
        self.assertIn("example_row", codes)

    def test_existing_account_needs_no_opening_and_shows_overlap(self):
        account = self.create_account(initial="100.00").data
        self.create_transaction(
            {
                "kind": "expense",
                "date": self.today.isoformat(),
                "description": "Già presente",
                "amount": "1.00",
                "account": account["id"],
            }
        )
        today = self.today.strftime("%d-%m-%Y")
        response = self.upload([[today, "Nuova spesa", "spesa", "Contanti", "5,00"]])
        self.assertTrue(response.data["summary"]["can_confirm"])
        self.assertEqual(response.data["accounts"][0]["state"], "existing")
        self.assertEqual(len(response.data["overlaps"]), 1)

    def test_import_into_existing_account_cannot_go_negative(self):
        self.create_account(initial="10.00")
        today = self.today.strftime("%d-%m-%Y")
        response = self.upload([[today, "Troppo", "spesa", "Contanti", "20,00"]])
        codes = [error["code"] for error in response.data["rows"][0]["errors"]]
        self.assertIn("insufficient_balance", codes)

    def test_similar_account_name_is_a_warning(self):
        self.create_account(name="Conto Corrente")
        response = self.upload(
            [
                ["01-10-2026", "Saldo", "altro", "Conto corrent", "-100,00"],
                ["02-10-2026", "Spesa", "spesa", "Conto corrent", "10,00"],
            ]
        )
        account = response.data["accounts"][0]
        self.assertEqual(account["state"], "similar")
        self.assertEqual(account["similar_to"], "Conto Corrente")
        self.assertTrue(response.data["rows"][0]["warnings"])

    def test_bad_amount_is_an_error(self):
        response = self.upload(
            [["01-10-2026", "Saldo", "altro", "Contanti", "-1.000,00"]]
        )
        codes = [error["code"] for error in response.data["rows"][0]["errors"]]
        self.assertIn("invalid_amount", codes)

    def test_empty_rows_payload_is_rejected(self):
        response = self.analyze_rows([])
        self.assertEqual(response.status_code, 400)

    def test_time_is_optional_and_defaults_to_noon(self):
        self.create_account(initial="100.00")
        today = self.today.strftime("%d-%m-%Y")
        response = self.upload(
            [
                [today, "Senza ora", "spesa", "Contanti", "5,00"],
                [today, "Con ora", "spesa", "Contanti", "6,00", "18:45"],
            ]
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["rows"][0]["time"], "12:00")
        self.assertEqual(response.data["rows"][1]["time"], "18:45")
        self.assertTrue(response.data["summary"]["can_confirm"])

    def test_invalid_time_is_a_row_error(self):
        self.create_account(initial="100.00")
        today = self.today.strftime("%d-%m-%Y")
        response = self.upload(
            [
                [today, "Senza ora", "spesa", "Contanti", "5,00"],
                [today, "Ora sbagliata", "spesa", "Contanti", "6,00", "25:99"],
            ]
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["rows"][1]["errors"][0]["code"], "invalid_time"
        )
        self.assertEqual(
            response.data["rows"][1]["errors"][0]["field"], "time"
        )
        self.assertFalse(response.data["summary"]["can_confirm"])

    def test_duplicates_ignore_the_time_column(self):
        self.create_account(initial="100.00")
        today = self.today.strftime("%d-%m-%Y")
        response = self.upload(
            [
                [today, "Caffè", "bar", "Contanti", "1,20", "08:00"],
                [today, "Caffè", "bar", "Contanti", "1,20", "18:00"],
            ]
        )
        codes = [
            error["code"]
            for item in response.data["rows"]
            for error in item["errors"]
        ]
        self.assertEqual(codes.count("duplicate_in_file"), 2)


class ConfirmTests(ImportTestBase):
    def test_confirm_creates_accounts_and_movements(self):
        response = self.confirm_rows(self.json_rows(VALID_ROWS))
        self.assertEqual(response.status_code, 201)
        data = response.data
        self.assertEqual(data["created_accounts"], ["Contanti"])
        self.assertEqual(data["created_transactions"], 2)
        self.assertEqual(data["openings_total"], "1000.00")
        self.assertEqual(data["expense_total"], "12.50")
        self.assertEqual(data["available_total"], "1000.00")
        self.assertEqual(data["covered_by_openings"], "12.50")
        self.assertEqual(data["net_total"], "987.50")

        account = Account.objects.get(name="Contanti")
        self.assertEqual(account.initial_balance, Decimal("0.00"))
        self.assertEqual(account.balance, Decimal("987.50"))
        opening = Transaction.objects.get(kind=Transaction.Kind.OPENING)
        self.assertEqual(opening.amount, Decimal("1000.00"))
        self.assertEqual(opening.time.isoformat(), "12:00:00")
        expense = Transaction.objects.get(kind=Transaction.Kind.EXPENSE)
        self.assertEqual(expense.date.isoformat(), "2026-10-02")
        self.assertEqual(expense.time.isoformat(), "12:00:00")
        self.assertEqual(expense.lines.get().amount, Decimal("-12.50"))

    def test_confirm_preserves_the_imported_time(self):
        rows = self.json_rows(VALID_ROWS)
        rows[0]["time"] = "08:15"
        rows[1]["time"] = "19:40"
        response = self.confirm_rows(rows)
        self.assertEqual(response.status_code, 201)
        opening = Transaction.objects.get(kind=Transaction.Kind.OPENING)
        self.assertEqual(opening.time.isoformat(), "08:15:00")
        expense = Transaction.objects.get(kind=Transaction.Kind.EXPENSE)
        self.assertEqual(expense.time.isoformat(), "19:40:00")

    def test_confirm_rejects_rows_with_errors(self):
        response = self.confirm_rows(
            self.json_rows([["01-10-2026", "Spesa", "spesa", "Contanti", "10,00"]])
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Account.objects.count(), 0)
        self.assertEqual(Transaction.objects.count(), 0)

    def test_confirm_with_explicit_date_format(self):
        rows = self.json_rows(
            [
                ["03/11/2026", "Saldo", "altro", "Contanti", "-100,00"],
                ["04/11/2026", "Spesa", "spesa", "Contanti", "10,00"],
            ]
        )
        response = self.client.post(
            reverse("finance-import-confirm"),
            {"rows": rows, "date_format": "MM/DD/YYYY", "decimal_separator": ","},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        expense = Transaction.objects.get(kind=Transaction.Kind.EXPENSE)
        self.assertEqual(expense.date.isoformat(), "2026-04-11")

    def test_second_import_of_the_same_file_is_blocked(self):
        payload = self.json_rows(VALID_ROWS)
        first = self.confirm_rows(payload)
        self.assertEqual(first.status_code, 201)
        second = self.confirm_rows(payload)
        self.assertEqual(second.status_code, 400)
        self.assertEqual(Transaction.objects.count(), 2)

    def test_global_admin_cannot_import(self):
        admin = User.objects.get(is_global_admin=True)
        self.client.force_authenticate(user=admin)
        response = self.confirm_rows(self.json_rows(VALID_ROWS))
        self.assertEqual(response.status_code, 403)


class ExportTests(FinanceTestBase):
    def test_export_csv(self):
        account = self.create_account(initial="100.00").data
        today = self.today.strftime("%d-%m-%Y")
        self.create_transaction(
            {
                "kind": "expense",
                "date": self.today.isoformat(),
                "description": "Caffè",
                "amount": "1.20",
                "account": account["id"],
                "time": "09:15",
            }
        )
        self.create_transaction(
            {
                "kind": "income",
                "date": self.today.isoformat(),
                "description": "Entrata",
                "amount": "50.00",
                "account": account["id"],
                "time": "18:45",
            }
        )
        response = self.client.get(reverse("finance-export"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response["Content-Type"].startswith("text/csv"))
        self.assertIn("attachment", response["Content-Disposition"])
        text = response.content.decode("utf-8-sig")
        self.assertTrue(response.content.startswith(b"\xef\xbb\xbf"))
        lines = text.splitlines()
        self.assertEqual(
            lines[0], "data;descrizione;categoria;conto;importo;ora"
        )
        self.assertIn(f"{today};Caffè;Altro;Contanti;1,20;09:15", lines)
        self.assertIn(f"{today};Entrata;Altro;Contanti;-50,00;18:45", lines)
        self.assertTrue(
            any(";Apertura;Contanti;-100,00;12:00" in line for line in lines)
        )
        # L'export a 6 colonne resta importabile.
        rows, errors, _ = parse_csv(response.content)
        self.assertEqual(errors, [])
        self.assertIn("09:15", [row["time"] for row in rows])

    def test_export_respects_date_filter(self):
        account = self.create_account(initial="100.00").data
        self.create_transaction(
            {
                "kind": "expense",
                "date": self.today.isoformat(),
                "amount": "1.00",
                "account": account["id"],
            }
        )
        future = (self.today + timedelta(days=1)).isoformat()
        response = self.client.get(
            reverse("finance-export"),
            {"start": future, "end": future},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.content.decode("utf-8-sig").splitlines()), 1)

    def test_export_requires_profile(self):
        admin = User.objects.get(is_global_admin=True)
        self.client.force_authenticate(user=admin)
        response = self.client.get(reverse("finance-export"))
        self.assertEqual(response.status_code, 403)

    def test_export_neutralizes_formula_cells_but_not_amounts(self):
        account = self.create_account(name="@Conto", initial="100.00").data
        self.create_transaction(
            {
                "kind": "expense",
                "date": self.today.isoformat(),
                "description": "=HYPERLINK(\"http://example.com\")",
                "amount": "1.20",
                "account": account["id"],
                "time": "10:00",
            }
        )
        self.create_transaction(
            {
                "kind": "income",
                "date": self.today.isoformat(),
                "description": "+Entrata",
                "amount": "50.00",
                "account": account["id"],
                "time": "20:30",
            }
        )
        response = self.client.get(reverse("finance-export"))
        self.assertEqual(response.status_code, 200)
        lines = response.content.decode("utf-8-sig").splitlines()
        self.assertTrue(any("'=HYPERLINK" in line for line in lines))
        self.assertTrue(any(";'+Entrata;Altro;'@Conto;" in line for line in lines))
        self.assertTrue(any(line.endswith(";-50,00;20:30") for line in lines))
        self.assertFalse(any("'-50,00" in line for line in lines))
