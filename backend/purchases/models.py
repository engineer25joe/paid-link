from django.contrib.auth.models import User
from django.db import models

from content.models import Content


class Purchase(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="purchases",
    )
    content = models.ForeignKey(
        Content,
        on_delete=models.CASCADE,
        related_name="purchases",
    )
    amount_paid = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )
    credits_charged = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    conversion_rate = models.DecimalField(max_digits=12, decimal_places=4, default=2)
    purchased_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "content"],
                name="unique_user_content_purchase",
            )
        ]
        ordering = ["-purchased_at"]

    def __str__(self):
        return f"{self.user.username} - {self.content.title}"
