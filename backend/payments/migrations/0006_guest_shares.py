import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from decimal import Decimal


def preserve_legacy_topup_values(apps, schema_editor):
    MpesaPayment = apps.get_model("payments", "MpesaPayment")
    for payment in MpesaPayment.objects.filter(user__isnull=False).iterator():
        payment.credits_awarded = payment.amount
        payment.conversion_rate = Decimal("1.0000")
        payment.save(update_fields=["credits_awarded", "conversion_rate"])


class Migration(migrations.Migration):
    dependencies = [
        ("payments", "0005_callback_tokens"),
        ("content", "0003_money_pricing"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(model_name="mpesapayment", name="user", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="mpesa_payments", to=settings.AUTH_USER_MODEL)),
        migrations.AddField(model_name="mpesapayment", name="conversion_rate", field=models.DecimalField(decimal_places=4, default=2, max_digits=12)),
        migrations.AddField(model_name="mpesapayment", name="credits_awarded", field=models.DecimalField(decimal_places=2, default=0, max_digits=12)),
        migrations.AddField(model_name="mpesapayment", name="guest_payment_token", field=models.CharField(blank=True, max_length=64, null=True, unique=True)),
        migrations.RunPython(preserve_legacy_topup_values, migrations.RunPython.noop),
        migrations.CreateModel(name="SharedContentShare", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("token", models.CharField(max_length=64, unique=True)),
            ("expires_at", models.DateTimeField()),
            ("access_duration_seconds", models.PositiveIntegerField(default=7200)),
            ("max_uses", models.PositiveIntegerField(default=2)),
            ("used_count", models.PositiveIntegerField(default=0)),
            ("reserved_count", models.PositiveIntegerField(default=0)),
            ("status", models.CharField(choices=[("active", "Active"), ("revoked", "Revoked")], default="active", max_length=10)),
            ("revoked_at", models.DateTimeField(blank=True, null=True)),
            ("created_at", models.DateTimeField(auto_now_add=True)),
            ("content", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="shares", to="content.content")),
            ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="content_shares", to=settings.AUTH_USER_MODEL)),
        ], options={"ordering": ["-created_at"]}),
        migrations.AddField(model_name="mpesapayment", name="guest_share", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="payments", to="payments.sharedcontentshare")),
        migrations.CreateModel(name="GuestContentAccess", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("token", models.CharField(max_length=64, unique=True)),
            ("expires_at", models.DateTimeField()),
            ("created_at", models.DateTimeField(auto_now_add=True)),
            ("payment", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="guest_access", to="payments.mpesapayment")),
            ("share", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="guest_accesses", to="payments.sharedcontentshare")),
        ], options={"ordering": ["-created_at"]}),
    ]
