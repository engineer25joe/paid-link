from rest_framework import serializers

from .models import Content


class ContentSerializer(serializers.ModelSerializer):
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
            "thumbnail_url",
            "is_published",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "creator",
            "creator_username",
            "created_at",
            "updated_at",
        ]


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