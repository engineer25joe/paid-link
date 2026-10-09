from django.contrib.auth.models import User
from django.db import models


class MpesaPayment(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("outcome_unknown", "Outcome Unknown"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("cancelled", "Cancelled"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="mpesa_payments",
    )
    phone_number = models.CharField(max_length=20)
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )
    merchant_request_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        unique=True,
    )
    checkout_request_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        unique=True,
    )
    mpesa_receipt_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        unique=True,
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
    )
    result_code = models.CharField(
        max_length=20,
        blank=True,
        null=True,
    )
    result_description = models.TextField(
        blank=True,
    )
    callback_token = models.CharField(max_length=64, blank=True, null=True, unique=True)
    reconciliation_token = models.CharField(max_length=64, blank=True, null=True, unique=True)
    callback_data = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(
        auto_now_add=True,
    )
    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"{self.user.username} - "
            f"KES {self.amount} - "
            f"{self.status}"
        )


class CreatorWithdrawal(models.Model):
    PAYOUT_STATUS_CHOICES = [
        ("not_submitted", "Not Submitted"),
        ("legacy_unknown", "Legacy Outcome Unknown"),
        ("submitting", "Submitting"),
        ("provider_pending", "Provider Pending"),
        ("outcome_unknown", "Outcome Unknown"),
        ("paid", "Paid"),
        ("payout_failed_verified", "Verified Payout Failure"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending Approval"),
        ("approved_reserved", "Approved and Reserved"),
        ("submitting", "Submitting to Provider"),
        ("provider_pending", "Provider Pending"),
        ("outcome_unknown", "Outcome Unknown"),
        ("paid", "Paid"),
        ("payout_failed_verified", "Verified Payout Failure"),
        ("refunded", "Refunded"),
        # Retained so existing financial records remain readable.
        ("approved", "Approved"),
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("rejected", "Rejected"),
        ("cancelled", "Cancelled"),
    ]

    creator = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="creator_withdrawals",
    )

    phone_number = models.CharField(
        max_length=20,
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    status = models.CharField(
        max_length=32,
        choices=STATUS_CHOICES,
        default="pending",
    )

    payout_status = models.CharField(
        max_length=32,
        choices=PAYOUT_STATUS_CHOICES,
        default="not_submitted",
    )

    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_withdrawals",
    )

    approved_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    originator_conversation_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        unique=True,
    )

    conversation_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        unique=True,
    )

    mpesa_receipt_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        unique=True,
    )

    result_code = models.CharField(
        max_length=20,
        blank=True,
        null=True,
    )

    result_description = models.TextField(
        blank=True,
    )

    failure_reason = models.TextField(
        blank=True,
    )

    refund_recorded_at = models.DateTimeField(null=True, blank=True)
    provider_failure_verified_at = models.DateTimeField(null=True, blank=True)
    provider_result_data = models.JSONField(null=True, blank=True)
    callback_discrepancy = models.TextField(blank=True)
    callback_token = models.CharField(max_length=64, blank=True, null=True, unique=True)
    reconciliation_token = models.CharField(max_length=64, blank=True, null=True, unique=True)

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"{self.creator.username} - "
            f"KES {self.amount} - "
            f"{self.status}"
        )
