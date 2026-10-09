from django.contrib.auth.models import User
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.views import APIView

from .serializers import UserRegistrationSerializer


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.save()

        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "message": "Account created successfully.",
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "role": user.profile.role,
                    "credits": str(user.profile.credits),
                },
                "tokens": {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                },
            },
            status=201,
        )

from rest_framework.views import APIView


class ProfileView(APIView):
    def get(self, request):
        user = request.user
        profile = user.profile

        return Response(
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "phone_number": profile.phone_number,
                "role": profile.role,
                "credits": str(profile.credits),
                "is_verified": profile.is_verified,
            }
        )