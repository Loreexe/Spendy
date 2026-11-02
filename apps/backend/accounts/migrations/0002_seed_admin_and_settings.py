from django.contrib.auth.hashers import make_password
from django.db import migrations


def seed_admin_and_settings(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    GlobalSettings = apps.get_model("accounts", "GlobalSettings")

    GlobalSettings.objects.get_or_create(pk=1)

    if not User.objects.filter(is_global_admin=True).exists():
        admin = User(
            username="admin",
            email=None,
            is_global_admin=True,
            status="active",
            password=make_password(None),
        )
        admin.save()


def remove_seed(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    User.objects.filter(is_global_admin=True, username="admin").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_admin_and_settings, remove_seed),
    ]
