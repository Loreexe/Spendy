"""Tests for the profile archive export and restore (DC-074)."""
import csv
import hashlib
import io
import json
import zipfile
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from accounts.models import User
from .models import (
    Account,
    Automation,
    AutomationExecution,
    Category,
    InvestmentOperation,
    InvestmentPosition,
    Line,
    Profile,
    SavingsAccount,
    Transaction,
)
from .tests import FinanceTestBase

CSV_NAMES = (
    "conti.csv",
    "salvadanai.csv",
    "movimenti.csv",
    "righe.csv",
    "posizioni.csv",
    "operazioni_investimenti.csv",
    "categorie.csv",
    "tag.csv",
    "movimento_tag.csv",
    "automazioni.csv",
    "esecuzioni_automazioni.csv",
)


class ArchiveTestBase(FinanceTestBase):
    def export_archive(self):
        response = self.client.get(reverse("finance-export-archive"))
        self.assertEqual(response.status_code, 200)
        return response

    def export_investments(self):
        response = self.client.get(reverse("finance-investment-export"))
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

    def csv_rows(self, contents, name):
        text = contents[name].decode("utf-8-sig")
        return list(csv.reader(io.StringIO(text), delimiter=";"))

    def write_csv(self, contents, name, rows):
        buffer = io.StringIO()
        writer = csv.writer(buffer, delimiter=";", lineterminator="\r\n")
        writer.writerows(rows)
        contents[name] = b"\xef\xbb\xbf" + buffer.getvalue().encode("utf-8")
        manifest = json.loads(contents["manifest.json"].decode("utf-8"))
        manifest["file"][name]["righe"] = len(rows) - 1
        manifest["file"][name]["sha256"] = hashlib.sha256(
            contents[name]
        ).hexdigest()
        manifest["conteggi"][name[:-4]] = len(rows) - 1
        contents["manifest.json"] = json.dumps(manifest).encode("utf-8")

    def set_cell(self, contents, name, where, column, value):
        rows = self.csv_rows(contents, name)
        index = {key: position for position, key in enumerate(rows[0])}
        for row in rows[1:]:
            if all(row[index[key]] == expected for key, expected in where.items()):
                row[index[column]] = value
                break
        else:
            self.fail(f"Riga non trovata in {name}: {where}")
        self.write_csv(contents, name, rows)

    def as_schema1(self, content):
        contents = self.unpack(content)
        manifest = json.loads(contents["manifest.json"].decode("utf-8"))
        for name in (
            "posizioni.csv",
            "operazioni_investimenti.csv",
            "categorie.csv",
            "tag.csv",
            "movimento_tag.csv",
            "automazioni.csv",
            "esecuzioni_automazioni.csv",
            "profilo.json",
        ):
            del contents[name]
            manifest["file"].pop(name, None)
            manifest["conteggi"].pop(name[:-4], None)
        # Rimuove la colonna UUID dallo schema 4.
        for name in ("conti.csv", "salvadanai.csv", "movimenti.csv"):
            rows = self.csv_rows(contents, name)
            stripped = [row[:-1] for row in rows]
            buffer = io.StringIO()
            writer = csv.writer(buffer, delimiter=";", lineterminator="\r\n")
            writer.writerows(stripped)
            contents[name] = (
                b"\xef\xbb\xbf" + buffer.getvalue().encode("utf-8")
            )
            manifest["file"][name]["sha256"] = hashlib.sha256(
                contents[name]
            ).hexdigest()
            manifest["file"][name]["righe"] = len(stripped) - 1
            manifest["conteggi"][name[:-4]] = len(stripped) - 1
        rows = self.csv_rows(contents, "movimenti.csv")
        stripped = [row[:8] for row in rows]
        buffer = io.StringIO()
        writer = csv.writer(buffer, delimiter=";", lineterminator="\r\n")
        writer.writerows(stripped)
        contents["movimenti.csv"] = (
            b"\xef\xbb\xbf" + buffer.getvalue().encode("utf-8")
        )
        manifest["schema"] = 1
        manifest["file"]["movimenti.csv"]["sha256"] = hashlib.sha256(
            contents["movimenti.csv"]
        ).hexdigest()
        manifest["file"]["movimenti.csv"]["righe"] = len(stripped) - 1
        manifest["conteggi"]["movimenti"] = len(stripped) - 1
        manifest.pop("conto_investimenti_id", None)
        manifest.pop("conto_investimenti", None)
        contents["manifest.json"] = json.dumps(manifest).encode("utf-8")
        return self.repack(contents)

    def as_schema4(self, content):
        """Downgrade uno schema 5 togliendo ``ora`` e ``icona``."""
        contents = self.unpack(content)
        manifest = json.loads(contents["manifest.json"].decode("utf-8"))
        for name in ("movimenti.csv", "categorie.csv"):
            rows = self.csv_rows(contents, name)
            stripped = [row[:-1] for row in rows]
            buffer = io.StringIO()
            writer = csv.writer(buffer, delimiter=";", lineterminator="\r\n")
            writer.writerows(stripped)
            contents[name] = (
                b"\xef\xbb\xbf" + buffer.getvalue().encode("utf-8")
            )
            manifest["file"][name]["sha256"] = hashlib.sha256(
                contents[name]
            ).hexdigest()
            manifest["file"][name]["righe"] = len(stripped) - 1
            manifest["conteggi"][name[:-4]] = len(stripped) - 1
        manifest["schema"] = 4
        contents["manifest.json"] = json.dumps(manifest).encode("utf-8")
        return self.repack(contents)

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

    def make_investment_data(self):
        account = self.create_account(name="Investimenti", initial="1000.00").data
        response = self.client.put(
            reverse("finance-investment-account"),
            {"account": account["id"]},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        position = self.client.post(
            reverse("finance-investments"),
            {
                "name": "ETF Mondo",
                "category": "etf",
                "identifier": "IE00B4L5Y983",
                "current_price": "105.20",
                "opening": {
                    "date": self.today.isoformat(),
                    "quantity": "10",
                    "total_cost": "1000.00",
                },
            },
            format="json",
        ).data
        for payload in (
            {
                "kind": "buy",
                "date": self.today.isoformat(),
                "quantity": "2",
                "unit_price": "102.50",
                "commission": "1.50",
                "description": "PAC",
            },
            {
                "kind": "sell",
                "date": self.today.isoformat(),
                "quantity": "1",
                "unit_price": "110.00",
                "commission": "1.00",
            },
            {
                "kind": "dividend",
                "date": self.today.isoformat(),
                "amount": "12.40",
            },
        ):
            response = self.client.post(
                reverse("finance-investment-operations", args=[position["id"]]),
                payload,
                format="json",
            )
            self.assertEqual(response.status_code, 201)
        return account, position

    def other_user(self, email="altro@example.com"):
        return User.objects.create_user(
            email=email,
            password="Spendy-Fondamenta-2026",
            status=User.Status.ACTIVE,
        )

    def create_foreign_position(self):
        other = self.other_user("estero@example.com")
        profile = Profile.objects.create(user=other)
        position = InvestmentPosition.objects.create(
            profile=profile, name="Segreto"
        )
        InvestmentOperation.objects.create(
            profile=profile,
            position=position,
            kind=InvestmentOperation.Kind.OPENING,
            date=self.today,
            quantity=Decimal("1"),
            unit_price=Decimal("1"),
            gross_amount=Decimal("1"),
        )
        return other, position


class ArchiveExportTests(ArchiveTestBase):
    def test_schema5_archive_contains_category_icons_and_movement_times(self):
        self.make_data()
        contents = self.unpack(self.export_archive().content)
        manifest = json.loads(contents["manifest.json"].decode("utf-8"))
        self.assertEqual(manifest["schema"], 5)
        self.assertIn("Schema 5", " ".join(manifest["note"]))

        categories = self.csv_rows(contents, "categorie.csv")
        category_columns = {
            key: index for index, key in enumerate(categories[0])
        }
        icons = {
            row[category_columns["nome"]]: row[category_columns["icona"]]
            for row in categories[1:]
        }
        self.assertEqual(icons["Altro"], "tag")
        self.assertEqual(icons["Alimentari"], "shopping-cart")

        movements = self.csv_rows(contents, "movimenti.csv")
        movement_columns = {
            key: index for index, key in enumerate(movements[0])
        }
        self.assertTrue(
            all(row[movement_columns["ora"]] for row in movements[1:])
        )

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
            set(CSV_NAMES) | {"manifest.json", "profilo.json"},
        )
        for name in CSV_NAMES:
            self.assertTrue(contents[name].startswith(b"\xef\xbb\xbf"))
            self.assertIn(b"\r\n", contents[name])
        self.assertTrue(
            contents["conti.csv"].decode("utf-8-sig").splitlines()[0].startswith(
                "id;nome;tipo_codice;tipo_etichetta;saldo_iniziale"
            )
        )
        self.assertTrue(
            contents["posizioni.csv"]
            .decode("utf-8-sig")
            .splitlines()[0]
            .startswith("id;nome;categoria_codice;categoria_etichetta")
        )
        self.assertTrue(
            contents["operazioni_investimenti.csv"]
            .decode("utf-8-sig")
            .splitlines()[0]
            .startswith("id;posizione_id;posizione;tipo_codice")
        )
        self.assertTrue(
            contents["movimenti.csv"].decode("utf-8-sig").splitlines()[0].endswith(
                ";uuid;ora"
            )
        )
        self.assertTrue(
            contents["categorie.csv"].decode("utf-8-sig").splitlines()[0].endswith(
                ";uuid;icona"
            )
        )

    def test_manifest_counts_and_checksums(self):
        self.make_data()
        contents = self.unpack(self.export_archive().content)
        manifest = json.loads(contents["manifest.json"].decode("utf-8"))
        self.assertEqual(manifest["schema"], 5)
        self.assertEqual(manifest["scopo"], "backup-profilo")
        self.assertEqual(manifest["valuta"], "EUR")
        self.assertEqual(
            manifest["conteggi"],
            {
                "conti": 2,
                "salvadanai": 1,
                "movimenti": 7,
                "righe": 11,
                "posizioni": 0,
                "operazioni_investimenti": 0,
                "categorie": 9,
                "tag": 0,
                "movimento_tag": 0,
                "automazioni": 0,
                "esecuzioni_automazioni": 0,
            },
        )
        for name in CSV_NAMES:
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
            {
                "conti": 0,
                "salvadanai": 0,
                "movimenti": 0,
                "righe": 0,
                "posizioni": 0,
                "operazioni_investimenti": 0,
                "categorie": 9,
                "tag": 0,
                "movimento_tag": 0,
                "automazioni": 0,
                "esecuzioni_automazioni": 0,
            },
        )
        for name in CSV_NAMES:
            if name == "categorie.csv":
                # Il profilo vuoto ha comunque le 9 categorie predefinite.
                self.assertEqual(
                    len(contents[name].decode("utf-8-sig").splitlines()), 10
                )
            else:
                self.assertEqual(
                    len(contents[name].decode("utf-8-sig").splitlines()), 1
                )

    def test_schema5_archive_contains_positions_and_operations(self):
        account, _ = self.make_investment_data()
        contents = self.unpack(self.export_archive().content)
        manifest = json.loads(contents["manifest.json"].decode("utf-8"))
        self.assertEqual(manifest["schema"], 5)
        self.assertEqual(manifest["conteggi"]["posizioni"], 1)
        self.assertEqual(manifest["conteggi"]["operazioni_investimenti"], 4)
        self.assertEqual(manifest["conto_investimenti_id"], account["id"])
        self.assertEqual(manifest["conto_investimenti"], "Investimenti")

        positions = self.csv_rows(contents, "posizioni.csv")
        self.assertEqual(len(positions), 2)
        self.assertEqual(positions[1][1], "ETF Mondo")
        self.assertEqual(positions[1][2], "etf")
        self.assertEqual(positions[1][5], "105,20000000")

        operations = self.csv_rows(contents, "operazioni_investimenti.csv")
        self.assertEqual(len(operations), 5)
        header = {key: index for index, key in enumerate(operations[0])}
        opening = next(
            row
            for row in operations[1:]
            if row[header["tipo_codice"]] == "opening"
        )
        self.assertEqual(opening[header["movimento_id"]], "")
        self.assertEqual(opening[header["conto_id"]], "")
        self.assertEqual(opening[header["importo_contante"]], "0,00")

    def test_dedicated_export_returns_only_investment_csvs(self):
        self.make_investment_data()
        self.create_foreign_position()
        response = self.export_investments()
        self.assertEqual(response["Content-Type"], "application/zip")
        self.assertIn("spendy-investimenti-", response["Content-Disposition"])
        contents = self.unpack(response.content)
        self.assertEqual(
            set(contents),
            {"posizioni.csv", "operazioni_investimenti.csv"},
        )
        positions = self.csv_rows(contents, "posizioni.csv")
        self.assertEqual(len(positions), 2)
        self.assertEqual(positions[1][1], "ETF Mondo")
        self.assertNotIn("Segreto", contents["posizioni.csv"].decode("utf-8-sig"))
        operations = self.csv_rows(contents, "operazioni_investimenti.csv")
        self.assertEqual(len(operations), 5)
        for name in ("posizioni.csv", "operazioni_investimenti.csv"):
            self.assertTrue(contents[name].startswith(b"\xef\xbb\xbf"))
            self.assertIn(b"\r\n", contents[name])

    def test_dedicated_export_requires_profile(self):
        admin = User.objects.get(is_global_admin=True)
        self.client.force_authenticate(user=admin)
        response = self.client.get(reverse("finance-investment-export"))
        self.assertEqual(response.status_code, 403)


class ArchiveRestoreTests(ArchiveTestBase):
    def setUp(self):
        super().setUp()
        self.make_data()
        self.content = self.export_archive().content
        self.source_profile = self.user.finance_profile

    def test_analyze_shows_summary(self):
        self.client.force_authenticate(user=self.other_user())
        response = self.analyze(self.content)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["can_restore"])
        self.assertEqual(response.data["summary"]["accounts"], 2)
        self.assertEqual(response.data["summary"]["savings"], 1)
        self.assertEqual(response.data["summary"]["transactions"], 7)
        self.assertEqual(response.data["summary"]["lines"], 11)
        self.assertEqual(response.data["summary"]["positions"], 0)
        self.assertEqual(response.data["summary"]["investment_operations"], 0)
        self.assertEqual(response.data["summary"]["accounts_total"], "1550.00")
        self.assertEqual(response.data["summary"]["savings_total"], "50.00")
        self.assertEqual(response.data["summary"]["investments_cost"], "0.00")
        self.assertEqual(response.data["summary"]["investments_value"], "0.00")
        self.assertEqual(response.data["summary"]["patrimony_total"], "1600.00")

    def test_restore_reproduces_counts_and_balances(self):
        target = self.other_user()
        self.client.force_authenticate(user=target)
        response = self.confirm(self.content)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["accounts"], 2)
        self.assertEqual(response.data["savings"], 1)
        self.assertEqual(response.data["transactions"], 7)
        self.assertEqual(response.data["lines"], 11)
        self.assertEqual(response.data["positions"], 0)
        self.assertEqual(response.data["investment_operations"], 0)
        self.assertEqual(response.data["accounts_total"], "1550.00")
        self.assertEqual(response.data["savings_total"], "50.00")
        self.assertEqual(response.data["patrimony_total"], "1600.00")

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
        self.assertEqual(response.data["positions"], 0)

    def test_schema1_archive_is_still_analyzed_and_restored(self):
        schema1 = self.as_schema1(self.content)
        target = self.other_user("schema1@example.com")
        self.client.force_authenticate(user=target)

        analysis = self.analyze(schema1)
        self.assertEqual(analysis.status_code, 200)
        self.assertTrue(analysis.data["can_restore"])
        self.assertEqual(analysis.data["manifest"]["schema"], 1)
        self.assertEqual(analysis.data["summary"]["positions"], 0)
        self.assertEqual(analysis.data["summary"]["investments_cost"], "0.00")
        self.assertEqual(analysis.data["summary"]["accounts_total"], "1550.00")

        restored = self.confirm(schema1)
        self.assertEqual(restored.status_code, 201)
        self.assertEqual(restored.data["accounts"], 2)
        self.assertEqual(restored.data["savings"], 1)
        self.assertEqual(restored.data["transactions"], 7)
        self.assertEqual(restored.data["positions"], 0)
        self.assertEqual(restored.data["investment_operations"], 0)
        self.assertEqual(restored.data["patrimony_total"], "1600.00")

        # Schema 1: ora 12:00 e icona dalle categorie predefinite.
        profile = target.finance_profile
        self.assertTrue(
            all(
                movement.time.isoformat() == "12:00:00"
                for movement in Transaction.objects.filter(profile=profile)
            )
        )
        self.assertEqual(
            Transaction.objects.get(
                profile=profile, description="Stipendio"
            ).category.icon,
            "tag",
        )


class ArchiveSchema5Tests(ArchiveTestBase):
    def test_schema5_includes_uuid_automations_and_profile_without_theme(self):
        account = self.create_account(initial="100.00").data
        savings = self.create_savings(account["id"], name="Vacanze").data
        profile = self.user.finance_profile
        profile.theme = "light"
        profile.save(update_fields=["theme"])
        self.user.first_name = "Ada"
        self.user.last_name = "Lovelace"
        self.user.save(update_fields=["first_name", "last_name"])
        automation = Automation.objects.create(
            profile=profile,
            kind=Automation.Kind.TRANSFER,
            savings_id=savings["id"],
            source_account_id=account["id"],
            amount=Decimal("25.00"),
            description="Vacanze",
            interval_count=1,
            interval_unit=Automation.IntervalUnit.MONTH,
            anchor_day=1,
            next_run_on=self.today,
            status=Automation.Status.ACTIVE,
        )
        AutomationExecution.objects.create(
            profile=profile,
            automation=automation,
            automation_ref=automation.pk,
            automation_name="Vacanze",
            kind=Automation.Kind.TRANSFER,
            description="Vacanze",
            scheduled_date=self.today,
            amount=Decimal("25.00"),
            source_account_id=account["id"],
            source_account_name="Contanti",
            savings_id=savings["id"],
            savings_name="Vacanze",
            status=AutomationExecution.Status.SUCCEEDED,
        )
        archive_bytes = self.export_archive().content
        contents = self.unpack(archive_bytes)
        manifest = json.loads(contents["manifest.json"].decode("utf-8"))
        self.assertEqual(manifest["schema"], 5)
        self.assertIn("automazioni.csv", contents)
        self.assertIn("esecuzioni_automazioni.csv", contents)
        self.assertIn("profilo.json", contents)
        profile_data = json.loads(contents["profilo.json"].decode("utf-8"))
        self.assertEqual(profile_data["nome"], "Ada")
        self.assertNotIn("tema", profile_data)
        self.assertTrue(
            self.csv_rows(contents, "conti.csv")[0][-1] == "uuid"
        )
        automation_rows = self.csv_rows(contents, "automazioni.csv")
        self.assertEqual(automation_rows[0][1], "uuid")
        self.assertEqual(len(automation_rows), 2)
        self.assertEqual(automation_rows[1][1], str(automation.uuid))

        target = self.other_user("schema4@example.com")
        self.client.force_authenticate(user=target)
        restored = self.confirm(archive_bytes)
        self.assertEqual(restored.status_code, 201)
        self.assertEqual(restored.data["automations"], 1)
        self.assertEqual(restored.data["automation_executions"], 1)
        target_profile = target.finance_profile
        restored_automation = Automation.objects.get(profile=target_profile)
        self.assertEqual(restored_automation.savings.name, "Vacanze")
        self.assertEqual(restored_automation.source_account.name, "Contanti")
        self.assertEqual(restored_automation.amount, Decimal("25.00"))
        self.assertEqual(
            AutomationExecution.objects.get(profile=target_profile).automation,
            restored_automation,
        )
        self.assertEqual(target.first_name, "Ada")
        self.assertEqual(target_profile.theme, "dark")


class ArchiveSchema5RestoreTests(ArchiveTestBase):
    def make_icon_time_data(self):
        account = self.create_account(initial="1000.00").data
        category = self.client.post(
            reverse("finance-categories"),
            {"name": "Viaggi", "icon": "plane"},
            format="json",
        ).data
        movement = self.create_transaction(
            {
                "kind": "expense",
                "date": self.today.isoformat(),
                "description": "Treno",
                "amount": "40.00",
                "account": account["id"],
                "category_id": category["id"],
                "time": "06:45",
            }
        )
        self.assertEqual(movement.status_code, 201)
        midnight = self.create_transaction(
            {
                "kind": "expense",
                "date": self.today.isoformat(),
                "description": "Mezzanotte",
                "amount": "1.00",
                "account": account["id"],
                "category_id": category["id"],
                "time": "00:00",
            }
        )
        self.assertEqual(midnight.status_code, 201)
        return account, category

    def test_schema5_round_trip_preserves_icon_and_time(self):
        self.make_icon_time_data()
        content = self.export_archive().content
        contents = self.unpack(content)
        manifest = json.loads(contents["manifest.json"].decode("utf-8"))
        self.assertEqual(manifest["schema"], 5)

        movements = self.csv_rows(contents, "movimenti.csv")
        movement_columns = {
            key: index for index, key in enumerate(movements[0])
        }
        treno = next(
            row
            for row in movements[1:]
            if row[movement_columns["descrizione"]] == "Treno"
        )
        self.assertEqual(treno[movement_columns["ora"]], "06:45")
        categories = self.csv_rows(contents, "categorie.csv")
        category_columns = {
            key: index for index, key in enumerate(categories[0])
        }
        viaggi = next(
            row
            for row in categories[1:]
            if row[category_columns["nome"]] == "Viaggi"
        )
        self.assertEqual(viaggi[category_columns["icona"]], "plane")

        target = self.other_user("schema5@example.com")
        self.client.force_authenticate(user=target)
        restored = self.confirm(content)
        self.assertEqual(restored.status_code, 201)
        profile = target.finance_profile
        movement = Transaction.objects.get(profile=profile, description="Treno")
        self.assertEqual(movement.time.isoformat(), "06:45:00")
        self.assertEqual(movement.category.name, "Viaggi")
        self.assertEqual(movement.category.icon, "plane")
        midnight = Transaction.objects.get(
            profile=profile, description="Mezzanotte"
        )
        self.assertEqual(midnight.time.isoformat(), "00:00:00")

    def test_schema4_restore_uses_default_icon_and_midday_time(self):
        self.make_icon_time_data()
        schema4 = self.as_schema4(self.export_archive().content)
        target = self.other_user("schema4@example.com")
        self.client.force_authenticate(user=target)
        analysis = self.analyze(schema4)
        self.assertEqual(analysis.status_code, 200)
        self.assertEqual(analysis.data["manifest"]["schema"], 4)
        self.assertTrue(analysis.data["can_restore"])

        restored = self.confirm(schema4)
        self.assertEqual(restored.status_code, 201)
        profile = target.finance_profile
        movement = Transaction.objects.get(profile=profile, description="Treno")
        self.assertEqual(movement.time.isoformat(), "12:00:00")
        # «Viaggi» non è una categoria predefinita: icona di ripiego.
        self.assertEqual(movement.category.icon, "tag")
        self.assertEqual(
            Category.objects.get(profile=profile, name="Alimentari").icon,
            "shopping-cart",
        )


class ArchiveInvestmentRestoreTests(ArchiveTestBase):
    def setUp(self):
        super().setUp()
        self.account, self.position = self.make_investment_data()
        self.content = self.export_archive().content

    def test_analyze_schema2_summary(self):
        self.client.force_authenticate(user=self.other_user())
        response = self.analyze(self.content)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["can_restore"])
        summary = response.data["summary"]
        self.assertEqual(summary["accounts"], 1)
        self.assertEqual(summary["positions"], 1)
        self.assertEqual(summary["investment_operations"], 4)
        self.assertEqual(summary["accounts_total"], "914.90")
        self.assertEqual(summary["investments_cost"], "1105.96")
        self.assertEqual(summary["investments_value"], "1157.20")
        self.assertEqual(summary["patrimony_total"], "2020.86")
        self.assertEqual(
            response.data["manifest"]["conto_investimenti_id"],
            self.account["id"],
        )

    def test_restore_schema2_recreates_positions_operations_and_movements(self):
        target = self.other_user("ripristino@example.com")
        self.client.force_authenticate(user=target)
        response = self.confirm(self.content)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["accounts"], 1)
        self.assertEqual(response.data["positions"], 1)
        self.assertEqual(response.data["investment_operations"], 4)
        self.assertEqual(response.data["transactions"], 4)
        self.assertEqual(response.data["lines"], 4)
        self.assertEqual(response.data["investments_cost"], "1105.96")
        self.assertEqual(response.data["investments_value"], "1157.20")
        self.assertEqual(response.data["patrimony_total"], "2020.86")

        profile = Profile.objects.get(user=target)
        account = Account.objects.get(profile=profile, name="Investimenti")
        self.assertEqual(profile.investment_account, account)
        self.assertEqual(account.balance, Decimal("914.90"))

        position = InvestmentPosition.objects.get(
            profile=profile, name="ETF Mondo"
        )
        self.assertEqual(position.category, "etf")
        self.assertEqual(position.identifier, "IE00B4L5Y983")
        self.assertEqual(position.current_price, Decimal("105.20"))
        self.assertEqual(position.operations.count(), 4)

        opening = position.operations.get(
            kind=InvestmentOperation.Kind.OPENING
        )
        self.assertIsNone(opening.transaction)
        self.assertEqual(opening.cash_amount, Decimal("0.00"))
        self.assertEqual(opening.quantity, Decimal("10.00000000"))
        self.assertEqual(
            Transaction.objects.filter(
                profile=profile,
                kind__in=(
                    Transaction.Kind.INVESTMENT_BUY,
                    Transaction.Kind.INVESTMENT_SELL,
                    Transaction.Kind.INVESTMENT_DIVIDEND,
                ),
            ).count(),
            3,
        )

    def test_restore_is_blocked_when_profile_has_positions(self):
        target = self.other_user("posseduto@example.com")
        profile = Profile.objects.create(user=target)
        InvestmentPosition.objects.create(profile=profile, name="Esistente")
        self.client.force_authenticate(user=target)

        analysis = self.analyze(self.content)
        self.assertEqual(analysis.status_code, 200)
        self.assertFalse(analysis.data["can_restore"])
        self.assertIn("profilo contiene già dati", analysis.data["blocked_reason"])
        self.assertEqual(self.confirm(self.content).status_code, 400)

    def test_position_reference_must_exist(self):
        contents = self.unpack(self.content)
        self.set_cell(
            contents,
            "operazioni_investimenti.csv",
            {"tipo_codice": "buy"},
            "posizione_id",
            "9999",
        )
        response = self.analyze(self.repack(contents))
        self.assertEqual(response.status_code, 400)
        self.assertIn("posizione non esiste", str(response.data))

    def test_oversell_is_rejected(self):
        contents = self.unpack(self.content)
        self.set_cell(
            contents,
            "operazioni_investimenti.csv",
            {"tipo_codice": "sell"},
            "quantita",
            "100,00000000",
        )
        response = self.analyze(self.repack(contents))
        self.assertEqual(response.status_code, 400)
        self.assertIn("vendita superiore", str(response.data))

    def test_incoherent_movement_is_rejected(self):
        contents = self.unpack(self.content)
        self.set_cell(
            contents,
            "operazioni_investimenti.csv",
            {"tipo_codice": "buy"},
            "importo_contante",
            "1,00",
        )
        response = self.analyze(self.repack(contents))
        self.assertEqual(response.status_code, 400)
        self.assertIn("non è coerente", str(response.data))

    def test_wrong_counts_are_rejected(self):
        contents = self.unpack(self.content)
        manifest = json.loads(contents["manifest.json"].decode("utf-8"))
        manifest["conteggi"]["posizioni"] = 5
        contents["manifest.json"] = json.dumps(manifest).encode("utf-8")
        response = self.analyze(self.repack(contents))
        self.assertEqual(response.status_code, 400)
        self.assertIn("conteggi", str(response.data))


class ArchiveCsvSafetyTests(ArchiveTestBase):
    def test_formula_cells_are_escaped_and_round_trip_unchanged(self):
        self.make_data()
        _, position = self.make_investment_data()
        profile = Profile.objects.get(user=self.user)
        Account.objects.filter(profile=profile, name="Contanti").update(
            name="=SUM(A1)"
        )
        SavingsAccount.objects.filter(profile=profile, name="Salute").update(
            name="+Salute"
        )
        Transaction.objects.filter(profile=profile, kind="income").update(
            description="@Stipendio"
        )
        InvestmentPosition.objects.filter(pk=position["id"]).update(
            name="-ETF", identifier="=IE00"
        )
        buy = InvestmentOperation.objects.get(
            position_id=position["id"], kind=InvestmentOperation.Kind.BUY
        )
        InvestmentOperation.objects.filter(pk=buy.pk).update(description="+PAC")

        content = self.export_archive().content
        contents = self.unpack(content)

        account_names = [row[1] for row in self.csv_rows(contents, "conti.csv")[1:]]
        self.assertIn("'=SUM(A1)", account_names)
        savings_rows = self.csv_rows(contents, "salvadanai.csv")[1:]
        self.assertIn("'+Salute", [row[1] for row in savings_rows])
        transaction_descriptions = [
            row[4] for row in self.csv_rows(contents, "movimenti.csv")[1:]
        ]
        self.assertIn("'@Stipendio", transaction_descriptions)
        position_rows = self.csv_rows(contents, "posizioni.csv")[1:]
        self.assertIn("'-ETF", [row[1] for row in position_rows])
        self.assertIn("'=IE00", [row[4] for row in position_rows])
        operation_descriptions = [
            row[14]
            for row in self.csv_rows(contents, "operazioni_investimenti.csv")[1:]
        ]
        self.assertIn("'+PAC", operation_descriptions)
        line_rows = self.csv_rows(contents, "righe.csv")[1:]
        self.assertIn("'=SUM(A1)", [row[3] for row in line_rows])
        self.assertTrue(
            any(
                row[8].startswith("-") and not row[8].startswith("'")
                for row in line_rows
            )
        )

        target = self.other_user("roundtrip@example.com")
        self.client.force_authenticate(user=target)
        self.assertEqual(self.confirm(content).status_code, 201)

        target_profile = Profile.objects.get(user=target)
        self.assertTrue(
            Account.objects.filter(
                profile=target_profile, name="=SUM(A1)"
            ).exists()
        )
        self.assertTrue(
            SavingsAccount.objects.filter(
                profile=target_profile, name="+Salute"
            ).exists()
        )
        self.assertTrue(
            Transaction.objects.filter(
                profile=target_profile,
                kind="income",
                description="@Stipendio",
            ).exists()
        )
        restored_position = InvestmentPosition.objects.get(
            profile=target_profile, name="-ETF"
        )
        self.assertEqual(restored_position.identifier, "=IE00")
        self.assertTrue(
            InvestmentOperation.objects.filter(
                position=restored_position,
                kind=InvestmentOperation.Kind.BUY,
                description="+PAC",
            ).exists()
        )


class ArchiveRestoreSafetyTests(ArchiveTestBase):
    def setUp(self):
        super().setUp()
        self.make_investment_data()
        self.content = self.export_archive().content

    def test_negative_commission_is_rejected(self):
        for kind in ("buy", "sell"):
            contents = self.unpack(self.content)
            self.set_cell(
                contents,
                "operazioni_investimenti.csv",
                {"tipo_codice": kind},
                "commissione",
                "-1,00",
            )
            response = self.analyze(self.repack(contents))
            self.assertEqual(response.status_code, 400)
            self.assertIn("commissione non può essere negativa", str(response.data))

    def test_opening_commission_is_rejected(self):
        contents = self.unpack(self.content)
        self.set_cell(
            contents,
            "operazioni_investimenti.csv",
            {"tipo_codice": "opening"},
            "commissione",
            "1,00",
        )
        response = self.analyze(self.repack(contents))
        self.assertEqual(response.status_code, 400)
        self.assertIn("apertura non prevede commissioni", str(response.data))

    def test_dividend_commission_is_rejected(self):
        contents = self.unpack(self.content)
        self.set_cell(
            contents,
            "operazioni_investimenti.csv",
            {"tipo_codice": "dividend"},
            "commissione",
            "1,00",
        )
        response = self.analyze(self.repack(contents))
        self.assertEqual(response.status_code, 400)
        self.assertIn("dividendo non prevede commissioni", str(response.data))
