from rest_framework import serializers

from .models import Content
from accounts.models import PlatformSettings
from accounts.services import credits_for_kes


class ContentSerializer(serializers.ModelSerializer):
    price = serializers.SerializerMethodField()
    price_kes = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    conversion_rate = serializers.SerializerMethodField()
    creator_username = serializers.CharField(
        source="creator.username",
        read_only=True,
    )

    class Meta:
        model = Content
        fields = [
            "id",
            "creator",
            "creator_username",
            "title",
            "description",
            "content_type",
            "price",
            "price_kes",
            "conversion_rate",
            "thumbnail_url",
            "is_published",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "creator",
            "creator_username",
            "price",
            "price_kes",
            "conversion_rate",
            "created_at",
            "updated_at",
        ]

    def _conversion_rate(self):
        # Cache once per response so a catalogue page does not query settings
        # for every content row and again for its derived-credit display.
        if "credit_to_kes_rate" not in self.context:
            self.context["credit_to_kes_rate"] = PlatformSettings.current().credit_to_kes_rate
        return self.context["credit_to_kes_rate"]

    def get_conversion_rate(self, obj):
        return str(self._conversion_rate())

    def get_price(self, obj):
        return str(credits_for_kes(obj.price_kes, self._conversion_rate()))


class ProtectedContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Content
        fields = [
            "id",
            "title",
            "content_type",
            "file_url",
        ]
        read_only_fields = [
            "id",
            "title",
            "content_type",
            "file_url",
        ]
