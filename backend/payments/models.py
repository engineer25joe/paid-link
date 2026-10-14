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
        null=True,
        blank=True,
        related_name="mpesa_payments",
    )
    phone_number = models.CharField(max_length=20)
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )
    credits_awarded = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    conversion_rate = models.DecimalField(max_digits=12, decimal_places=4, default=2)
    guest_share = models.ForeignKey("SharedContentShare", on_delete=models.PROTECT, null=True, blank=True, related_name="payments")
    guest_payment_token = models.CharField(max_length=64, blank=True, null=True, unique=True)
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

    def save(self, *args, **kwargs):
        # Old internal fixtures/imports omit the new quote fields. Preserve the
        # historical 1 KES == 1 credit contract for those records only.
        if self._state.adding and self.user_id and not self.credits_awarded:
            self.credits_awarded = self.amount
            self.conversion_rate = 1
        super().save(*args, **kwargs)

    def __str__(self):
        username = self.user.username if self.user_id else "Guest"
        return (
            f"{username} - "
            f"KES {self.amount} - "
            f"{self.status}"
        )


class SharedContentShare(models.Model):
    STATUS_CHOICES = [("active", "Active"), ("revoked", "Revoked")]
    content = models.ForeignKey("content.Content", on_delete=models.PROTECT, related_name="shares")
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="content_shares")
    token = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
    access_duration_seconds = models.PositiveIntegerField(default=7200)
    max_uses = models.PositiveIntegerField(default=2)
    used_count = models.PositiveIntegerField(default=0)
    reserved_count = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="active")
    revoked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class GuestContentAccess(models.Model):
    payment = models.OneToOneField(MpesaPayment, on_delete=models.PROTECT, related_name="guest_access")
    share = models.ForeignKey(SharedContentShare, on_delete=models.PROTECT, related_name="guest_accesses")
    token = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


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
