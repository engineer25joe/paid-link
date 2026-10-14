from decimal import Decimal

from django.db import migrations, models


def migrate_legacy_credit_prices(apps, schema_editor):
    Content = apps.get_model("content", "Content")
    # Legacy price values were credits. At the initial KES 2/credit rate,
    # multiply once so old listings preserve their credit equivalent.
    for item in Content.objects.all().iterator():
        item.price_kes = (item.price * Decimal("2.0000")).quantize(Decimal("0.01"))
        item.save(update_fields=["price_kes"])


def restore_legacy_credit_prices(apps, schema_editor):
    Content = apps.get_model("content", "Content")
    for item in Content.objects.all().iterator():
        item.price_kes = (item.price_kes / Decimal("2.0000")).quantize(Decimal("0.01"))
        item.save(update_fields=["price_kes"])


class Migration(migrations.Migration):
    dependencies = [("content", "0002_content_cloudinary_public_id"), ("accounts", "0006_platform_rate_and_wallet_audit")]
    operations = [
        migrations.RenameField(model_name="content", old_name="price", new_name="price_kes"),
        migrations.RunPython(migrate_legacy_credit_prices, restore_legacy_credit_prices),
    ]
