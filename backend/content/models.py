from django.contrib.auth.models import User
from django.db import models


class Content(models.Model):
    CONTENT_TYPES = [
        ("pdf", "PDF"),
        ("video", "Video"),
    ]

    creator = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="contents",
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    content_type = models.CharField(
        max_length=10,
        choices=CONTENT_TYPES,
    )
    # Money is the creator-set source of truth; credits are derived at checkout.
    price_kes = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    # Temporary source-compatibility for existing integrations while clients
    # migrate to the explicit KES field.
    @property
    def price(self):
        return self.price_kes

    @price.setter
    def price(self, value):
        self.price_kes = value

    # Temporary URL field used by the current development content.
    file_url = models.URLField(
        blank=True,
        null=True,
    )

    # Cloudinary public identifier for the protected file.
    cloudinary_public_id = models.CharField(
        max_length=500,
        blank=True,
        null=True,
    )

    thumbnail_url = models.URLField(
        blank=True,
        null=True,
    )
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title
