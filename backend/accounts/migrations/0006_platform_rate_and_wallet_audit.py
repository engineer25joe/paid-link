from decimal import Decimal

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def create_default_rate(apps, schema_editor):
    PlatformSettings = apps.get_model("accounts", "PlatformSettings")
    PlatformSettings.objects.get_or_create(pk=1, defaults={"credit_to_kes_rate": Decimal("2.0000")})
    CreditTransaction = apps.get_model("accounts", "CreditTransaction")
    for entry in CreditTransaction.objects.filter(balance_before__isnull=True).iterator():
        entry.balance_before = entry.balance_after - entry.amount
        entry.save(update_fields=["balance_before"])


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0005_creatorapplication"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(model_name="credittransaction", name="administrator", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="credit_adjustments", to=settings.AUTH_USER_MODEL)),
        migrations.AddField(model_name="credittransaction", name="amount_kes", field=models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
        migrations.AddField(model_name="credittransaction", name="balance_before", field=models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
        migrations.AddField(model_name="credittransaction", name="conversion_rate", field=models.DecimalField(blank=True, decimal_places=4, max_digits=12, null=True)),
        migrations.AddField(model_name="credittransaction", name="payment_reference", field=models.CharField(blank=True, max_length=120)),
        migrations.AddField(model_name="credittransaction", name="reason", field=models.CharField(blank=True, max_length=255)),
        migrations.CreateModel(name="PlatformSettings", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("credit_to_kes_rate", models.DecimalField(decimal_places=4, default=2, max_digits=12)),
            ("updated_at", models.DateTimeField(auto_now=True)),
            ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="platform_setting_changes", to=settings.AUTH_USER_MODEL)),
        ]),
        migrations.CreateModel(name="CreditRateHistory", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("rate", models.DecimalField(decimal_places=4, max_digits=12)),
            ("created_at", models.DateTimeField(auto_now_add=True)),
            ("changed_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="credit_rate_changes", to=settings.AUTH_USER_MODEL)),
        ], options={"ordering": ["-created_at"]}),
        migrations.RunPython(create_default_rate, migrations.RunPython.noop),
    ]
