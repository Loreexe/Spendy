from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from accounts.models import User
from .imports import parse_amount, parse_csv, parse_date
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
        self.assertIn("data;descrizione;categoria;conto;importo", text)
        self.assertIn("ESEMPIO", text)
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
        rows, errors = parse_csv(csv_file(VALID_ROWS))
        self.assertEqual(errors, [])
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["date"], "01-10-2026")
        self.assertEqual(rows[0]["account"], "Contanti")

    def test_wrong_header(self):
        rows, errors = parse_csv(csv_file(VALID_ROWS, header="data;importo"))
        self.assertEqual(rows, [])
        self.assertEqual(errors[0]["code"], "header")

    def test_wrong_column_count(self):
        rows, errors = parse_csv(csv_file([["01-10-2026", "Solo due"]]))
        self.assertEqual(rows, [])
        self.assertEqual(errors[0]["code"], "columns")

    def test_quoted_semicolon_is_accepted(self):
        data = (
            "data;descrizione;categoria;conto;importo\r\n"
            '01-10-2026;"Caffè; cornetto";bar;Contanti;3,50\r\n'
        ).encode("utf-8-sig")
        rows, errors = parse_csv(data)
        self.assertEqual(errors, [])
        self.assertEqual(rows[0]["description"], "Caffè; cornetto")

    def test_non_utf8_is_rejected(self):
        rows, errors = parse_csv("caffè".encode("latin-1"))
        self.assertEqual(rows, [])
        self.assertEqual(errors[0]["code"], "encoding")

    def test_date_rules(self):
        self.assertEqual(parse_date("03-11-2026")[0].isoformat(), "2026-11-03")
        self.assertIsNotNone(parse_date("3-11-2026")[1])
        self.assertIsNotNone(parse_date("2026-11-03")[1])
        self.assertIsNotNone(parse_date("32-11-2026")[1])

    def test_amount_rules(self):
        self.assertEqual(parse_amount("12,50")[0], Decimal("12.50"))
        self.assertEqual(parse_amount("-100,00")[0], Decimal("-100.00"))
        self.assertIsNotNone(parse_amount("12.50")[1])
        self.assertIsNotNone(parse_amount("1.234,56")[1])
        self.assertIsNotNone(parse_amount("€12,50")[1])
        self.assertIsNotNone(parse_amount("0,00")[1])
        self.assertIsNotNone(parse_amount("12")[1])


class AnalyzeTests(ImportTestBase):
    def test_valid_file_creates_account_with_opening(self):
        response = self.upload(VALID_ROWS)
        self.assertEqual(response.status_code, 200)
        data = response.data
        self.assertTrue(data["summary"]["can_confirm"])
        self.assertEqual(data["summary"]["accounts_to_create"], 1)
        self.assertEqual(data["summary"]["openings_total"], "1000.00")
        self.assertEqual(data["summary"]["expense_total"], "12.50")
        self.assertEqual(data["summary"]["net_total"], "987.50")
        self.assertEqual(data["rows"][0]["kind"], "opening")
        self.assertEqual(data["rows"][1]["kind"], "expense")
        self.assertEqual(data["accounts"][0]["state"], "new")

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


class ConfirmTests(ImportTestBase):
    def test_confirm_creates_accounts_and_movements(self):
        response = self.confirm_rows(self.json_rows(VALID_ROWS))
        self.assertEqual(response.status_code, 201)
        data = response.data
        self.assertEqual(data["created_accounts"], ["Contanti"])
        self.assertEqual(data["created_transactions"], 2)
        self.assertEqual(data["openings_total"], "1000.00")
        self.assertEqual(data["expense_total"], "12.50")
        self.assertEqual(data["net_total"], "987.50")

        account = Account.objects.get(name="Contanti")
        self.assertEqual(account.initial_balance, Decimal("0.00"))
        self.assertEqual(account.balance, Decimal("987.50"))
        opening = Transaction.objects.get(kind=Transaction.Kind.OPENING)
        self.assertEqual(opening.amount, Decimal("1000.00"))
        expense = Transaction.objects.get(kind=Transaction.Kind.EXPENSE)
        self.assertEqual(expense.date.isoformat(), "2026-10-02")
        self.assertEqual(expense.lines.get().amount, Decimal("-12.50"))

    def test_confirm_rejects_rows_with_errors(self):
        response = self.confirm_rows(
            self.json_rows([["01-10-2026", "Spesa", "spesa", "Contanti", "10,00"]])
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Account.objects.count(), 0)
        self.assertEqual(Transaction.objects.count(), 0)

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
