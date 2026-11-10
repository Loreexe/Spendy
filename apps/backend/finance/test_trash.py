"""Tests for soft delete, trash, restore and purge (DC-088)."""

from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from .models import (
    Account,
    Automation,
    Category,
    InvestmentOperation,
    InvestmentPosition,
    SavingsAccount,
    Tag,
    Transaction,
    purge_trash,
)
from .tests import FinanceTestBase


class TrashTestBase(FinanceTestBase):
    def setUp(self):
        super().setUp()
        self.account = self.create_account(initial="1000.00").data

    def trash(self, params=None):
        url = reverse("finance-trash")
        if params:
            url += "?" + "&".join(f"{key}={value}" for key, value in params.items())
        return self.client.get(url)

    def restore(self, item_type, item_id):
        return self.client.post(
            reverse("finance-trash-restore"),
            {"type": item_type, "id": item_id},
            format="json",
        )

    def purge(self, item_type, item_id):
        return self.client.post(
            reverse("finance-trash-purge"),
            {"type": item_type, "id": item_id},
            format="json",
        )

    def empty(self):
        return self.client.post(reverse("finance-trash-empty"))

    def make_expense(self, description="Spesa", amount="40.00", **extra):
        payload = {
            "kind": "expense",
            "date": self.today.isoformat(),
            "description": description,
            "amount": amount,
            "account": self.account["id"],
        }
        payload.update(extra)
        return self.create_transaction(payload)


class MovementTrashTests(TrashTestBase):
    def test_delete_hides_everywhere_and_restore_brings_back(self):
        food = Category.objects.get(profile__user=self.user, name="Alimentari")
        created = self.make_expense(
            "Supermercato", "120.00", category_id=food.id, tags=["casa"]
        )
        movement_id = created.data["id"]
        deleted = self.client.delete(
            reverse("finance-transaction-detail", args=[movement_id])
        )
        self.assertEqual(deleted.status_code, 204)
        self.assertEqual(
            self.client.get(reverse("finance-transactions")).data["count"], 1
        )
        dashboard = self.client.get(reverse("finance-dashboard")).data
        # Spesa eliminata: nessun flusso; l'apertura del conto non è un flusso.
        self.assertEqual(dashboard["period_balance"], "0.00")
        self.assertEqual(Account.objects.get(pk=self.account["id"]).balance, 1000)
        trashed = self.trash()
        self.assertEqual(trashed.data["count"], 1)
        self.assertEqual(trashed.data["items"][0]["type"], "movement")
        self.assertEqual(
            trashed.data["items"][0]["deleted_by"], "finanza@example.com"
        )
        restored = self.restore("movement", movement_id)
        self.assertEqual(restored.status_code, 200)
        self.assertEqual(
            self.client.get(reverse("finance-transactions")).data["count"], 2
        )
        self.assertEqual(Account.objects.get(pk=self.account["id"]).balance, 880)

    def test_deleted_movement_cannot_be_edited_or_deleted_twice(self):
        created = self.make_expense()
        movement_id = created.data["id"]
        self.client.delete(reverse("finance-transaction-detail", args=[movement_id]))
        again = self.client.delete(
            reverse("finance-transaction-detail", args=[movement_id])
        )
        self.assertEqual(again.status_code, 400)

    def test_investment_movement_cannot_be_restored_from_trash(self):
        self.client.put(
            reverse("finance-investment-account"),
            {"account": self.account["id"]},
            format="json",
        )
        position = self.client.post(
            reverse("finance-investments"), {"name": "ETF"}, format="json"
        ).data
        operation = self.client.post(
            reverse("finance-investment-operations", args=[position["id"]]),
            {
                "kind": "buy",
                "date": self.today.isoformat(),
                "quantity": "2",
                "unit_price": "100.00",
            },
            format="json",
        ).data
        movement_id = operation["transaction"]
        self.assertIsNotNone(movement_id)
        Transaction.all_objects.get(pk=movement_id).soft_delete()
        response = self.restore("movement", movement_id)
        self.assertEqual(response.status_code, 400)


class AccountSavingsTrashTests(TrashTestBase):
    def test_account_soft_delete_and_restore(self):
        empty = self.create_account(name="Vuoto", initial="0.00").data
        account_id = empty["id"]
        response = self.client.delete(
            reverse("finance-account-detail", args=[account_id])
        )
        self.assertEqual(response.status_code, 204)
        listed = self.client.get(reverse("finance-accounts"))
        self.assertEqual(
            [item["id"] for item in listed.data["accounts"]],
            [self.account["id"]],
        )
        self.assertEqual(self.trash().data["count"], 1)
        self.assertEqual(self.restore("account", account_id).status_code, 200)
        self.assertEqual(
            len(self.client.get(reverse("finance-accounts")).data["accounts"]),
            2,
        )

    def test_savings_delete_moves_residual_and_trashes_automations(self):
        savings = self.create_savings(self.account["id"], name="Salute").data
        self.client.post(
            reverse("finance-transactions"),
            {
                "kind": "transfer",
                "date": self.today.isoformat(),
                "description": "Versamento",
                "amount": "100.00",
                "from_account": self.account["id"],
                "to_savings": savings["id"],
            },
            format="json",
        )
        automation = self.client.post(
            reverse("finance-automations"),
            {
                "savings": savings["id"],
                "source_account": self.account["id"],
                "amount": "10.00",
                "interval_count": 1,
                "interval_unit": "month",
                "next_run_on": self.today.isoformat(),
            },
            format="json",
        )
        self.assertEqual(automation.status_code, 201)
        deleted = self.client.delete(
            reverse("finance-savings-detail", args=[savings["id"]])
        )
        self.assertEqual(deleted.status_code, 204)
        trashed_types = sorted(
            item["type"] for item in self.trash().data["items"]
        )
        self.assertIn("savings", trashed_types)
        self.assertIn("automation", trashed_types)
        account = Account.objects.get(pk=self.account["id"])
        self.assertEqual(account.balance, 1000)
        restored = self.restore("savings", savings["id"])
        self.assertEqual(restored.status_code, 200)


class CategoryTagTrashTests(TrashTestBase):
    def test_category_restore_clash(self):
        created = self.client.post(
            reverse("finance-categories"), {"name": "Viaggi"}, format="json"
        ).data
        self.client.delete(
            reverse("finance-category-detail", args=[created["id"]])
        )
        again = self.client.post(
            reverse("finance-categories"), {"name": "viaggi"}, format="json"
        )
        self.assertEqual(again.status_code, 201)
        response = self.restore("category", created["id"])
        self.assertEqual(response.status_code, 400)

    def test_tag_reuse_restores_trashed_tag(self):
        movement = self.make_expense("Spesa", "10.00", tags=["casa"])
        tag = Tag.objects.get(profile__user=self.user, name="casa")
        self.client.delete(reverse("finance-tag-detail", args=[tag.id]))
        listed = self.client.get(reverse("finance-transactions"))
        self.assertEqual(listed.data["transactions"][0]["tags"], [])
        second = self.make_expense("Altra", "5.00", tags=["casa"])
        self.assertEqual(second.data["tags"], ["casa"])
        self.assertFalse(
            Tag.all_objects.filter(
                profile__user=self.user, name="casa", is_deleted=True
            ).exists()
        )


class PurgeTests(TrashTestBase):
    def test_purge_removes_only_expired(self):
        old = self.make_expense("Vecchia", "10.00")
        recent = self.make_expense("Recente", "10.00")
        for movement in (old.data["id"], recent.data["id"]):
            self.client.delete(
                reverse("finance-transaction-detail", args=[movement])
            )
        old_obj = Transaction.all_objects.get(pk=old.data["id"])
        old_obj.deleted_at = timezone.now() - timedelta(days=31)
        old_obj.save(update_fields=("deleted_at",))
        from django.core.management import call_command

        call_command("purge_trash")
        self.assertFalse(
            Transaction.all_objects.filter(pk=old.data["id"]).exists()
        )
        self.assertTrue(
            Transaction.all_objects.filter(pk=recent.data["id"]).exists()
        )
        self.assertEqual(self.trash().data["count"], 1)

    def test_empty_trash_purges_everything(self):
        self.make_expense("Una", "10.00")
        self.make_expense("Due", "5.00")
        for item in self.client.get(reverse("finance-transactions")).data[
            "transactions"
        ]:
            if item["kind"] == "opening":
                continue
            self.client.delete(
                reverse("finance-transaction-detail", args=[item["id"]])
            )
        self.assertEqual(self.trash().data["count"], 2)
        response = self.empty()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["purged"], 2)
        self.assertEqual(self.trash().data["count"], 0)


class AutomationTrashTests(TrashTestBase):
    def test_deleted_automation_disappears_and_stops(self):
        savings = self.create_savings(self.account["id"], name="Salute").data
        automation = self.client.post(
            reverse("finance-automations"),
            {
                "savings": savings["id"],
                "source_account": self.account["id"],
                "amount": "10.00",
                "interval_count": 1,
                "interval_unit": "month",
                "next_run_on": self.today.isoformat(),
            },
            format="json",
        ).data
        deleted = self.client.delete(
            reverse("finance-automation-detail", args=[automation["id"]])
        )
        self.assertEqual(deleted.status_code, 204)
        listed = self.client.get(reverse("finance-automations"))
        self.assertEqual(listed.data["automations"], [])
        self.assertEqual(
            Automation.all_objects.filter(pk=automation["id"]).count(), 1
        )
        restored = self.restore("automation", automation["id"])
        self.assertEqual(restored.status_code, 200)
        listed = self.client.get(reverse("finance-automations"))
        self.assertEqual(len(listed.data["automations"]), 1)

    def test_restore_automation_with_trashed_savings_is_blocked(self):
        savings = self.create_savings(self.account["id"], name="Salute").data
        automation = self.client.post(
            reverse("finance-automations"),
            {
                "savings": savings["id"],
                "source_account": self.account["id"],
                "amount": "10.00",
                "interval_count": 1,
                "interval_unit": "month",
                "next_run_on": self.today.isoformat(),
            },
            format="json",
        ).data
        self.client.delete(reverse("finance-savings-detail", args=[savings["id"]]))
        response = self.restore("automation", automation["id"])
        self.assertEqual(response.status_code, 400)
