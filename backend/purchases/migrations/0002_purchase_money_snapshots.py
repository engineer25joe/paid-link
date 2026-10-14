from decimal import Decimal

from django.db import migrations, models


def preserve_purchase_values(apps, schema_editor):
    Purchase = apps.get_model("purchases", "Purchase")
    for purchase in Purchase.objects.all().iterator():
        legacy_credits = purchase.amount_paid
        purchase.amount_paid = (legacy_credits * Decimal("2.0000")).quantize(Decimal("0.01"))
        purchase.credits_charged = legacy_credits
        purchase.conversion_rate = Decimal("2.0000")
        purchase.save(update_fields=["amount_paid", "credits_charged", "conversion_rate"])


def restore_legacy_purchase_values(apps, schema_editor):
    Purchase = apps.get_model("purchases", "Purchase")
    for purchase in Purchase.objects.all().iterator():
        purchase.amount_paid = (purchase.amount_paid / Decimal("2.0000")).quantize(Decimal("0.01"))
        purchase.save(update_fields=["amount_paid"])


class Migration(migrations.Migration):
    dependencies = [("purchases", "0001_initial"), ("content", "0003_money_pricing")]
    operations = [
        migrations.AlterField(model_name="purchase", name="amount_paid", field=models.DecimalField(decimal_places=2, max_digits=12)),
        migrations.AddField(model_name="purchase", name="credits_charged", field=models.DecimalField(decimal_places=2, default=0, max_digits=12)),
        migrations.AddField(model_name="purchase", name="conversion_rate", field=models.DecimalField(decimal_places=4, default=2, max_digits=12)),
        migrations.RunPython(preserve_purchase_values, restore_legacy_purchase_values),
    ]
