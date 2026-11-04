import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("finance", "0002_automationexecution_savingsautomation_notification_and_more"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="SavingsAutomation",
            new_name="Automation",
        ),
        migrations.AddField(
            model_name="automation",
            name="kind",
            field=models.CharField(
                choices=[
                    ("transfer", "Versamento su salvadanaio"),
                    ("expense", "Spesa ricorrente"),
                ],
                default="transfer",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="automation",
            name="description",
            field=models.CharField(blank=True, default="", max_length=255),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="automation",
            name="savings",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="automations",
                to="finance.savingsaccount",
            ),
        ),
        migrations.AlterField(
            model_name="automation",
            name="profile",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="automations",
                to="finance.profile",
            ),
        ),
        migrations.AlterField(
            model_name="automation",
            name="source_account",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="automations",
                to="finance.account",
            ),
        ),
        migrations.AddConstraint(
            model_name="automation",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    models.Q(("kind", "transfer"), ("savings__isnull", False)),
                    models.Q(("kind", "expense"), ("savings__isnull", True)),
                    _connector="OR",
                ),
                name="finance_automation_kind_target",
            ),
        ),
        migrations.AddField(
            model_name="automationexecution",
            name="kind",
            field=models.CharField(
                choices=[
                    ("transfer", "Versamento su salvadanaio"),
                    ("expense", "Spesa ricorrente"),
                ],
                default="transfer",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="automationexecution",
            name="description",
            field=models.CharField(blank=True, default="", max_length=255),
            preserve_default=False,
        ),
    ]
