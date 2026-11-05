"""Tests for categories, tags and the category suggestion (DC-086)."""

from django.urls import reverse

from .models import Category, Tag, Transaction, ensure_default_categories
from .tests import FinanceTestBase


class CategoryTests(FinanceTestBase):
    def setUp(self):
        super().setUp()
        self.account = self.create_account(initial="1000.00").data

    def list_categories(self):
        return self.client.get(reverse("finance-categories"))

    def test_list_seeds_default_categories(self):
        response = self.list_categories()
        self.assertEqual(response.status_code, 200)
        names = [item["name"] for item in response.data]
        self.assertIn("Altro", names)
        self.assertEqual(names[0], "Altro")
        self.assertTrue(response.data[0]["is_default"])

    def test_create_category_and_duplicate_rejected(self):
        created = self.client.post(
            reverse("finance-categories"), {"name": "Viaggi"}, format="json"
        )
        self.assertEqual(created.status_code, 201)
        self.assertFalse(created.data["is_default"])
        duplicate = self.client.post(
            reverse("finance-categories"), {"name": "  viaggi "}, format="json"
        )
        self.assertEqual(duplicate.status_code, 400)

    def test_default_category_cannot_be_renamed_or_deleted(self):
        default_id = self.list_categories().data[0]["id"]
        renamed = self.client.patch(
            reverse("finance-category-detail", args=[default_id]),
            {"name": "Varie"},
            format="json",
        )
        self.assertEqual(renamed.status_code, 400)
        deleted = self.client.delete(
            reverse("finance-category-detail", args=[default_id])
        )
        self.assertEqual(deleted.status_code, 400)

    def test_delete_reassigns_movements_to_default(self):
        created = self.client.post(
            reverse("finance-categories"), {"name": "Viaggi"}, format="json"
        ).data
        movement = self.create_transaction(
            {
                "kind": "expense",
                "date": self.today.isoformat(),
                "description": "Treno",
                "amount": "40.00",
                "account": self.account["id"],
                "category_id": created["id"],
                "tags": ["lavoro"],
            }
        )
        self.assertEqual(movement.status_code, 201)
        self.assertEqual(movement.data["category"]["name"], "Viaggi")
        self.assertEqual(movement.data["tags"], ["lavoro"])
        deleted = self.client.delete(
            reverse("finance-category-detail", args=[created["id"]])
        )
        self.assertEqual(deleted.status_code, 204)
        movement_id = movement.data["id"]
        transaction = Transaction.objects.get(pk=movement_id)
        self.assertEqual(transaction.category.name, "Altro")
        self.assertEqual(
            [tag.name for tag in transaction.tags.all()], ["lavoro"]
        )

    def test_transaction_without_category_defaults_to_altro(self):
        movement = self.create_transaction(
            {
                "kind": "expense",
                "date": self.today.isoformat(),
                "description": "Spesa",
                "amount": "10.00",
                "account": self.account["id"],
            }
        )
        self.assertEqual(movement.status_code, 201)
        self.assertEqual(movement.data["category"]["name"], "Altro")
        self.assertEqual(movement.data["tags"], [])

    def test_update_replaces_category_and_tags(self):
        first = self.client.post(
            reverse("finance-categories"), {"name": "Viaggi"}, format="json"
        ).data
        movement = self.create_transaction(
            {
                "kind": "expense",
                "date": self.today.isoformat(),
                "description": "Treno",
                "amount": "40.00",
                "account": self.account["id"],
            }
        ).data
        updated = self.client.patch(
            reverse("finance-transaction-detail", args=[movement["id"]]),
            {
                "kind": "expense",
                "date": self.today.isoformat(),
                "description": "Treno",
                "amount": "40.00",
                "account": self.account["id"],
                "category_id": first["id"],
                "tags": ["lavoro", "extra"],
            },
            format="json",
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.data["category"]["name"], "Viaggi")
        self.assertEqual(updated.data["tags"], ["lavoro", "extra"])

    def test_filters_by_category_and_tag(self):
        food = Category.objects.get(
            profile__user=self.user, name="Alimentari"
        )
        self.create_transaction(
            {
                "kind": "expense",
                "date": self.today.isoformat(),
                "description": "Spesa",
                "amount": "10.00",
                "account": self.account["id"],
                "category_id": food.id,
                "tags": ["casa"],
            }
        )
        self.create_transaction(
            {
                "kind": "expense",
                "date": self.today.isoformat(),
                "description": "Cinema",
                "amount": "12.00",
                "account": self.account["id"],
            }
        )
        by_category = self.client.get(
            reverse("finance-transactions") + f"?category={food.id}"
        )
        self.assertEqual(by_category.data["count"], 1)
        by_tag = self.client.get(reverse("finance-transactions") + "?tag=casa")
        self.assertEqual(by_tag.data["count"], 1)
        self.assertEqual(by_tag.data["transactions"][0]["description"], "Spesa")

    def test_cross_profile_category_rejected(self):
        from accounts.models import User

        from .models import Profile

        intruder = User.objects.create_user(
            email="intruso@example.com",
            password="Spendy-Fondamenta-2026",
            status=User.Status.ACTIVE,
        )
        intruder_profile, _ = Profile.objects.get_or_create(user=intruder)
        foreign = ensure_default_categories(intruder_profile)["Altro"]
        self.assertNotEqual(foreign.profile.user, self.user)
        response = self.create_transaction(
            {
                "kind": "expense",
                "date": self.today.isoformat(),
                "description": "Spesa",
                "amount": "10.00",
                "account": self.account["id"],
                "category_id": foreign.id,
            }
        )
        self.assertEqual(response.status_code, 400)


class SuggestCategoryTests(FinanceTestBase):
    def setUp(self):
        super().setUp()
        self.account = self.create_account(initial="1000.00").data

    def test_suggests_default_without_history(self):
        response = self.client.get(reverse("finance-suggest-category"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["category"]["name"], "Altro")
        self.assertEqual(response.data["source"], "default")

    def test_suggests_from_description_history(self):
        food = Category.objects.get(profile__user=self.user, name="Alimentari")
        self.create_transaction(
            {
                "kind": "expense",
                "date": self.today.isoformat(),
                "description": "Supermercato Esselunga",
                "amount": "30.00",
                "account": self.account["id"],
                "category_id": food.id,
            }
        )
        response = self.client.get(
            reverse("finance-suggest-category") + "?description=esselunga"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["category"]["name"], "Alimentari")
        self.assertEqual(response.data["source"], "history")

    def test_suggests_from_account_usage(self):
        food = Category.objects.get(profile__user=self.user, name="Alimentari")
        self.create_transaction(
            {
                "kind": "expense",
                "date": self.today.isoformat(),
                "description": "Spesa",
                "amount": "30.00",
                "account": self.account["id"],
                "category_id": food.id,
            }
        )
        response = self.client.get(
            reverse("finance-suggest-category")
            + f"?description=xy&account={self.account['id']}"
        )
        self.assertEqual(response.data["category"]["name"], "Alimentari")
        self.assertEqual(response.data["source"], "account")


class TagTests(FinanceTestBase):
    def test_tag_crud(self):
        listed = self.client.get(reverse("finance-tags"))
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.data, [])
        created = self.client.post(
            reverse("finance-tags"), {"name": "lavoro"}, format="json"
        )
        self.assertEqual(created.status_code, 201)
        again = self.client.post(
            reverse("finance-tags"), {"name": "lavoro"}, format="json"
        )
        self.assertEqual(again.status_code, 201)
        self.assertEqual(
            Tag.objects.filter(profile__user=self.user).count(), 1
        )
        deleted = self.client.delete(
            reverse("finance-tag-detail", args=[created.data["id"]])
        )
        self.assertEqual(deleted.status_code, 204)
        self.assertFalse(
            Tag.objects.filter(profile__user=self.user).exists()
        )

    def test_tag_names_are_validated(self):
        response = self.client.post(
            reverse("finance-tags"), {"name": "   "}, format="json"
        )
        self.assertEqual(response.status_code, 400)


class ImportCategoryTests(FinanceTestBase):
    def setUp(self):
        super().setUp()
        self.account = self.create_account(initial="1000.00").data

    def confirm_rows(self, rows):
        return self.client.post(
            reverse("finance-import-confirm"), {"rows": rows}, format="json"
        )

    def test_import_maps_free_text_category(self):
        today = self.today.strftime("%d-%m-%Y")
        response = self.confirm_rows(
            [
                {
                    "date": today,
                    "description": "Supermercato",
                    "category": "ALIMENTARI",
                    "account": "Contanti",
                    "amount": "25,00",
                    "not_duplicate": True,
                },
                {
                    "date": today,
                    "description": "Varie",
                    "category": "sconosciuta",
                    "account": "Contanti",
                    "amount": "5,00",
                    "not_duplicate": True,
                },
            ]
        )
        self.assertEqual(response.status_code, 201)
        matched = Transaction.objects.get(description="Supermercato")
        self.assertEqual(matched.category.name, "Alimentari")
        fallback = Transaction.objects.get(description="Varie")
        self.assertEqual(fallback.category.name, "Altro")


class ExportCategoryTests(FinanceTestBase):
    def setUp(self):
        super().setUp()
        self.account = self.create_account(initial="100.00").data

    def test_export_writes_real_category_name(self):
        food = Category.objects.get(profile__user=self.user, name="Alimentari")
        self.create_transaction(
            {
                "kind": "expense",
                "date": self.today.isoformat(),
                "description": "Caffè",
                "amount": "1.20",
                "account": self.account["id"],
                "category_id": food.id,
            }
        )
        response = self.client.get(reverse("finance-export"))
        self.assertEqual(response.status_code, 200)
        text = response.content.decode("utf-8-sig")
        today = self.today.strftime("%d-%m-%Y")
        self.assertIn(f"{today};Caffè;Alimentari;Contanti;1,20", text.splitlines())


class ArchiveCategoryTests(FinanceTestBase):
    def setUp(self):
        super().setUp()
        self.account = self.create_account(initial="1000.00").data
        food = Category.objects.get(profile__user=self.user, name="Alimentari")
        movement = self.create_transaction(
            {
                "kind": "expense",
                "date": self.today.isoformat(),
                "description": "Supermercato",
                "amount": "30.00",
                "account": self.account["id"],
                "category_id": food.id,
                "tags": ["casa", "settimanale"],
            }
        )
        self.assertEqual(movement.status_code, 201)

    def export_bytes(self):
        from django.urls import reverse as url_reverse

        response = self.client.get(url_reverse("finance-export-archive"))
        self.assertEqual(response.status_code, 200)
        return response.content

    def unpack(self, content):
        import io
        import zipfile

        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            return {name: archive.read(name) for name in archive.namelist()}

    def analyze(self, content):
        from django.core.files.uploadedfile import SimpleUploadedFile

        upload = SimpleUploadedFile(
            "backup.zip", content, content_type="application/zip"
        )
        return self.client.post(
            reverse("finance-import-archive-analyze"),
            {"file": upload},
            format="multipart",
        )

    def confirm(self, content):
        from django.core.files.uploadedfile import SimpleUploadedFile

        upload = SimpleUploadedFile(
            "backup.zip", content, content_type="application/zip"
        )
        return self.client.post(
            reverse("finance-import-archive-confirm"),
            {"file": upload},
            format="multipart",
        )

    def test_schema3_round_trip_preserves_categories_and_tags(self):
        import json

        from accounts.models import User

        target = User.objects.create_user(
            email="archivio@example.com",
            password="Spendy-Fondamenta-2026",
            status=User.Status.ACTIVE,
        )
        content = self.export_bytes()
        self.client.force_authenticate(user=target)
        response = self.confirm(content)
        self.assertEqual(response.status_code, 201)
        profile = target.finance_profile
        restored = Transaction.objects.get(
            profile=profile, description="Supermercato"
        )
        self.assertEqual(restored.category.name, "Alimentari")
        self.assertEqual(
            sorted(tag.name for tag in restored.tags.all()),
            ["casa", "settimanale"],
        )
        self.assertTrue(
            Category.objects.filter(profile=profile, name="Altro").exists()
        )
        manifest_names = json.loads(
            self.unpack(self.export_bytes())["manifest.json"].decode("utf-8")
        )
        self.assertEqual(manifest_names["schema"], 3)

    def test_schema2_restore_assigns_default_category(self):
        import csv as csv_module
        import hashlib
        import io
        import json
        import zipfile

        from accounts.models import User

        contents = self.unpack(self.export_bytes())
        rows = list(
            csv_module.reader(
                io.StringIO(contents["movimenti.csv"].decode("utf-8-sig")),
                delimiter=";",
            )
        )
        stripped = [row[:8] for row in rows]
        buffer = io.StringIO()
        writer = csv_module.writer(buffer, delimiter=";", lineterminator="\r\n")
        writer.writerows(stripped)
        contents["movimenti.csv"] = (
            b"\xef\xbb\xbf" + buffer.getvalue().encode("utf-8")
        )
        for obsolete in ("categorie.csv", "tag.csv", "movimento_tag.csv"):
            del contents[obsolete]
        manifest = json.loads(contents["manifest.json"].decode("utf-8"))
        manifest["schema"] = 2
        for obsolete in ("categorie", "tag", "movimento_tag"):
            manifest["conteggi"].pop(obsolete, None)
            manifest["file"].pop(
                {
                    "categorie": "categorie.csv",
                    "tag": "tag.csv",
                    "movimento_tag": "movimento_tag.csv",
                }[obsolete],
                None,
            )
        manifest["file"]["movimenti.csv"]["sha256"] = hashlib.sha256(
            contents["movimenti.csv"]
        ).hexdigest()
        manifest["file"]["movimenti.csv"]["righe"] = len(stripped) - 1
        contents["manifest.json"] = json.dumps(
            manifest, ensure_ascii=False
        ).encode("utf-8")
        downgraded = io.BytesIO()
        with zipfile.ZipFile(downgraded, "w", zipfile.ZIP_DEFLATED) as archive:
            for name, content in contents.items():
                archive.writestr(name, content)

        target = User.objects.create_user(
            email="vecchio@example.com",
            password="Spendy-Fondamenta-2026",
            status=User.Status.ACTIVE,
        )
        self.client.force_authenticate(user=target)
        analyzed = self.analyze(downgraded.getvalue())
        self.assertEqual(analyzed.status_code, 200)
        self.assertTrue(analyzed.data["can_restore"])
        confirmed = self.confirm(downgraded.getvalue())
        self.assertEqual(confirmed.status_code, 201)
        restored = Transaction.objects.get(
            profile=target.finance_profile, description="Supermercato"
        )
        self.assertEqual(restored.category.name, "Altro")
        self.assertEqual(list(restored.tags.all()), [])
