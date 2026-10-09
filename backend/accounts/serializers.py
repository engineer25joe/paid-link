from django.contrib.auth.models import User
from rest_framework import serializers

from .models import UserProfile


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        min_length=8
    )
    phone_number = serializers.CharField(
        required=True,
        allow_blank=False
    )

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "password",
            "phone_number",
        ]

    def create(self, validated_data):
        phone_number = validated_data.pop("phone_number", "")
        password = validated_data.pop("password")

        user = User.objects.create_user(
            password=password,
            **validated_data
        )

        user.profile.phone_number = phone_number
        user.profile.save()

        return user