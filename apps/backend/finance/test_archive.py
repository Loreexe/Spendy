"""Tests for the profile archive export and restore (DC-074)."""
import io
import json
import zipfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from accounts.models import User
from .models import Account, Line, SavingsAccount, Transaction
from .tests import FinanceTestBase


class ArchiveTestBase(FinanceTestBase):
    def export_archive(self):
        response = self.client.get(reverse("finance-export-archive"))
        self.assertEqual(response.status_code, 200)
        return response

    def unpack(self, content):
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            return {
                name: archive.read(name)
                for name in archive.namelist()
            }

    def repack(self, contents):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            for name, content in contents.items():
                archive.writestr(name, content)
        return buffer.getvalue()

    def analyze(self, content, filename="backup.zip"):
        upload = SimpleUploadedFile(
            filename, content, content_type="application/zip"
        )
        return self.client.post(
            reverse("finance-import-archive-analyze"),
            {"file": upload},
            format="multipart",
        )

    def confirm(self, content, filename="backup.zip"):
        upload = SimpleUploadedFile(
            filename, content, content_type="application/zip"
        )
        return self.client.post(
            reverse("finance-import-archive-confirm"),
            {"file": upload},
            format="multipart",
        )

    def make_data(self):
        account = self.create_account(initial="1000.00").data
        other = self.create_account(name="Risparmi", initial="500.00").data
        savings = self.create_savings(account["id"], name="Salute").data

        self.create_transaction(
            {
                "kind": "transfer",
                "date": self.today.isoformat(),
                "description": "Versamento",
                "amount": "200.00",
                "from_account": account["id"],
                "to_savings": savings["id"],
            }
        )
        self.create_transaction(
            {
                "kind": "expense",
                "date": self.today.isoformat(),
                "description": "Visita",
                "amount": "150.00",
                "savings": savings["id"],
                "confirm_coverage": True,
            }
        )
        self.create_transaction(
            {
                "kind": "transfer",
                "date": self.today.isoformat(),
                "description": "Giroconto",
                "amount": "200.00",
                "from_account": account["id"],
                "to_account": other["id"],
            }
        )
        self.create_transaction(
            {
                "kind": "income",
                "date": self.today.isoformat(),
                "description": "Stipendio",
                "amount": "300.00",
                "account": account["id"],
            }
        )
        self.create_transaction(
            {
                "kind": "expense",
                "date": self.today.isoformat(),
                "description": "Spesa",
                "amount": "50.00",
                "account": account["id"],
            }
        )
        return account, other, savings


class ArchiveExportTests(ArchiveTestBase):
    def test_archive_has_expected_files_and_headers(self):
        self.make_data()
        response = self.export_archive()
        self.assertEqual(response["Content-Type"], "application/zip")
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertIn("spendy-archivio-", response["Content-Disposition"])
        self.assertIn(".zip", response["Content-Disposition"])

        contents = self.unpack(response.content)
        self.assertEqual(
            set(contents),
            {
                "conti.csv",
                "salvadanai.csv",
                "movimenti.csv",
                "righe.csv",
                "manifest.json",
            },
        )
        for name in ("conti.csv", "salvadanai.csv", "movimenti.csv", "righe.csv"):
            self.assertTrue(contents[name].startswith(b"\xef\xbb\xbf"))
            self.assertIn(b"\r\n", contents[name])
        self.assertTrue(
            contents["conti.csv"].decode("utf-8-sig").splitlines()[0].startswith(
                "id;nome;tipo_codice;tipo_etichetta;saldo_iniziale"
            )
        )

    def test_manifest_counts_and_checksums(self):
        self.make_data()
        contents = self.unpack(self.export_archive().content)
        manifest = json.loads(contents["manifest.json"].decode("utf-8"))
        self.assertEqual(manifest["schema"], 1)
        self.assertEqual(manifest["scopo"], "backup-profilo")
        self.assertEqual(manifest["valuta"], "EUR")
        self.assertEqual(
            manifest["conteggi"],
            {"conti": 2, "salvadanai": 1, "movimenti": 7, "righe": 11},
        )
        for name in ("conti.csv", "salvadanai.csv", "movimenti.csv", "righe.csv"):
            self.assertIn(name, manifest["file"])
            self.assertIn("sha256", manifest["file"][name])

    def test_archive_contains_both_sides_of_transfers_and_savings_lines(self):
        _, _, savings = self.make_data()
        contents = self.unpack(self.export_archive().content)
        lines = contents["righe.csv"].decode("utf-8-sig").splitlines()
        self.assertTrue(any("transfer_out" in line for line in lines))
        self.assertTrue(any("transfer_in" in line for line in lines))
        self.assertTrue(any("technical" in line for line in lines))
        self.assertTrue(any(";Salute;" in line for line in lines))
        self.assertTrue(
            any(
                str(savings["id"]) in line and ";Salute;" in line
                for line in lines
            )
        )

    def test_archive_requires_profile(self):
        admin = User.objects.get(is_global_admin=True)
        self.client.force_authenticate(user=admin)
        response = self.client.get(reverse("finance-export-archive"))
        self.assertEqual(response.status_code, 403)

    def test_empty_profile_produces_valid_archive(self):
        contents = self.unpack(self.export_archive().content)
        manifest = json.loads(contents["manifest.json"].decode("utf-8"))
        self.assertEqual(
            manifest["conteggi"],
            {"conti": 0, "salvadanai": 0, "movimenti": 0, "righe": 0},
        )
        for name in ("conti.csv", "salvadanai.csv", "movimenti.csv", "righe.csv"):
            self.assertEqual(len(contents[name].decode("utf-8-sig").splitlines()), 1)


class ArchiveRestoreTests(ArchiveTestBase):
    def setUp(self):
        super().setUp()
        self.make_data()
        self.content = self.export_archive().content
        self.source_profile = self.user.finance_profile

    def other_user(self, email="altro@example.com"):
        return User.objects.create_user(
            email=email,
            password="Spendy-Fondamenta-2026",
            status=User.Status.ACTIVE,
        )

    def test_analyze_shows_summary(self):
        self.client.force_authenticate(user=self.other_user())
        response = self.analyze(self.content)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["can_restore"])
        self.assertEqual(response.data["summary"]["accounts"], 2)
        self.assertEqual(response.data["summary"]["savings"], 1)
        self.assertEqual(response.data["summary"]["transactions"], 7)
        self.assertEqual(response.data["summary"]["lines"], 11)
        self.assertEqual(response.data["summary"]["accounts_total"], "1550.00")
        self.assertEqual(response.data["summary"]["savings_total"], "50.00")

    def test_restore_reproduces_counts_and_balances(self):
        target = self.other_user()
        self.client.force_authenticate(user=target)
        response = self.confirm(self.content)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["accounts"], 2)
        self.assertEqual(response.data["savings"], 1)
        self.assertEqual(response.data["transactions"], 7)
        self.assertEqual(response.data["lines"], 11)
        self.assertEqual(response.data["accounts_total"], "1550.00")
        self.assertEqual(response.data["savings_total"], "50.00")

        profile = target.finance_profile
        account = Account.objects.get(profile=profile, name="Contanti")
        other = Account.objects.get(profile=profile, name="Risparmi")
        savings = SavingsAccount.objects.get(profile=profile, name="Salute")
        self.assertEqual(account.balance, 850)
        self.assertEqual(other.balance, 700)
        self.assertEqual(savings.balance, 50)
        self.assertEqual(savings.backing_account, account)
        self.assertEqual(Transaction.objects.filter(profile=profile).count(), 7)
        self.assertEqual(Line.objects.filter(transaction__profile=profile).count(), 11)

    def test_restore_is_blocked_on_non_empty_profile(self):
        response = self.analyze(self.content)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["can_restore"])
        self.assertIn("profilo contiene già dati", response.data["blocked_reason"])

        confirm = self.confirm(self.content)
        self.assertEqual(confirm.status_code, 400)
        self.assertEqual(Account.objects.filter(profile=self.source_profile).count(), 2)

    def test_restore_does_not_touch_other_profiles(self):
        target = self.other_user()
        self.client.force_authenticate(user=target)
        self.assertEqual(self.confirm(self.content).status_code, 201)
        self.client.force_authenticate(user=self.user)
        self.assertEqual(
            Account.objects.filter(profile=self.source_profile).count(), 2
        )
        self.assertEqual(
            Line.objects.filter(transaction__profile=self.source_profile).count(), 11
        )

    def test_tampered_csv_is_rejected(self):
        contents = self.unpack(self.content)
        contents["conti.csv"] = contents["conti.csv"].replace(
            b"Contanti", b"ContantX"
        )
        response = self.analyze(self.repack(contents))
        self.assertEqual(response.status_code, 400)
        self.assertIn("checksum", str(response.data))

    def test_unsupported_schema_is_rejected(self):
        contents = self.unpack(self.content)
        manifest = json.loads(contents["manifest.json"].decode("utf-8"))
        manifest["schema"] = 99
        contents["manifest.json"] = json.dumps(manifest).encode("utf-8")
        response = self.analyze(self.repack(contents))
        self.assertEqual(response.status_code, 400)
        self.assertIn("non supportata", str(response.data))

    def test_invalid_zip_is_rejected(self):
        response = self.analyze(b"not a zip")
        self.assertEqual(response.status_code, 400)

    def test_global_admin_cannot_restore(self):
        admin = User.objects.get(is_global_admin=True)
        self.client.force_authenticate(user=admin)
        response = self.analyze(self.content)
        self.assertEqual(response.status_code, 403)

    def test_empty_archive_restores_empty_profile(self):
        self.client.force_authenticate(user=self.other_user("vuoto@example.com"))
        empty = self.export_archive().content
        self.client.force_authenticate(user=self.other_user("dest@example.com"))
        response = self.confirm(empty)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["accounts"], 0)
        self.assertEqual(response.data["transactions"], 0)
