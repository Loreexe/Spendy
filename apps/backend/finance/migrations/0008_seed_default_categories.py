# Data migration: preset categories per profile, existing movements to "Altro".

from django.db import migrations

from finance.models import DEFAULT_CATEGORIES, DEFAULT_CATEGORY_NAME


def seed_categories(apps, schema_editor):
    Profile = apps.get_model("finance", "Profile")
    Category = apps.get_model("finance", "Category")
    Transaction = apps.get_model("finance", "Transaction")
    for profile in Profile.objects.all().iterator():
        existing = set(
            Category.objects.filter(profile=profile).values_list(
                "name", flat=True
            )
        )
        to_create = [
            Category(
                profile=profile,
                name=name,
                is_preset=True,
                is_default=(name == DEFAULT_CATEGORY_NAME),
            )
            for name in DEFAULT_CATEGORIES
            if name not in existing
        ]
        Category.objects.bulk_create(to_create)
        default = Category.objects.get(
            profile=profile, name=DEFAULT_CATEGORY_NAME
        )
        if not default.is_default:
            default.is_default = True
            default.save(update_fields=("is_default",))
        Transaction.objects.filter(
            profile=profile, category__isnull=True
        ).update(category=default)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0007_category_transaction_category_tag_transaction_tags_and_more'),
    ]

    operations = [
        migrations.RunPython(seed_categories, noop),
    ]
