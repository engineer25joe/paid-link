from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("payments", "0004_creatorwithdrawal_payout_status")]

    operations = [
        migrations.AddField(
            model_name="mpesapayment",
            name="callback_token",
            field=models.CharField(blank=True, max_length=64, null=True, unique=True),
        ),
        migrations.AddField(
            model_name="mpesapayment",
            name="reconciliation_token",
            field=models.CharField(blank=True, max_length=64, null=True, unique=True),
        ),
        migrations.AddField(
            model_name="mpesapayment",
            name="callback_data",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="creatorwithdrawal",
            name="callback_token",
            field=models.CharField(blank=True, max_length=64, null=True, unique=True),
        ),
        migrations.AddField(
            model_name="creatorwithdrawal",
            name="reconciliation_token",
            field=models.CharField(blank=True, max_length=64, null=True, unique=True),
        ),
    ]
