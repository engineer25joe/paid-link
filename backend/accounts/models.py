from django.contrib.auth.models import User
from django.db import models


def effective_role(user):
    if user.is_superuser or (hasattr(user, "profile") and user.profile.role == "admin"):
        return "admin"
    return user.profile.role if hasattr(user, "profile") else "learner"


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ("learner", "Learner"),
        ("creator", "Content Creator"),
        ("admin", "Admin"),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    creator_created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="created_creator_accounts",
    )
    phone_number = models.CharField(
        max_length=13,
        blank=True,
        null=True,
        unique=True,
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default="learner",
    )
    credits = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.username



class CreditTransaction(models.Model):
    TRANSACTION_TYPES = [
        ("topup", "Top Up"),
        ("purchase", "Purchase"),
        ("refund", "Refund"),
        ("withdrawal", "Withdrawal"),
        ("adjustment", "Adjustment"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="credit_transactions",
    )
    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPES,
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )
    balance_after = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )
    description = models.CharField(
        max_length=255,
        blank=True,
    )
    # NULL for legacy rows; all new balance events carry a stable unique key.
    idempotency_key = models.CharField(
        max_length=160,
        null=True,
        blank=True,
        unique=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.transaction_type} - {self.amount}"


class CreatorApplication(models.Model):
    STATUS_CHOICES = [("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected")]
    applicant = models.ForeignKey(User, on_delete=models.CASCADE, related_name="creator_applications")
    motivation = models.TextField(max_length=2000)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="pending")
    decided_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="creator_application_decisions")
    decided_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(
            fields=["applicant"], condition=models.Q(status__in=["pending", "approved"]),
            name="one_active_creator_application_per_user",
        )]
