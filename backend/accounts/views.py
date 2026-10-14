from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from rest_framework import generics, permissions, throttling
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.views import APIView

from .serializers import UserRegistrationSerializer
from .models import CreatorApplication, CreditTransaction, effective_role
from payments.models import MpesaPayment


class ThrottledTokenObtainPairView(TokenObtainPairView):
    throttle_classes = [throttling.ScopedRateThrottle]
    throttle_scope = "login"


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [throttling.ScopedRateThrottle]
    throttle_scope = "registration"

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
                    "role": effective_role(user),
                    "credits": str(user.profile.credits),
                },
                "tokens": {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                },
            },
            status=201,
        )

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
                "role": effective_role(user),
                "credits": str(profile.credits),
                "is_verified": profile.is_verified,
                "is_active": user.is_active,
            }
        )


class CreatorApplicationView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        application = CreatorApplication.objects.filter(applicant=request.user).first()
        return Response({"application": serialize_application(application) if application else None})

    def post(self, request):
        if effective_role(request.user) != "learner":
            return Response({"error": "Only learner accounts may apply."}, status=400)
        motivation = str(request.data.get("motivation", "")).strip()
        if not motivation or len(motivation) > 2000:
            return Response({"error": "Provide a reason of 1 to 2000 characters."}, status=400)
        application = CreatorApplication.objects.filter(applicant=request.user).first()
        if application and application.status != "rejected":
            return Response({"error": "An application is already pending or approved."}, status=400)
        try:
            with transaction.atomic():
                application = CreatorApplication.objects.create(applicant=request.user, motivation=motivation)
        except IntegrityError:
            return Response({"error": "An application is already pending or approved."}, status=400)
        return Response({"application": serialize_application(application)}, status=201)


def serialize_application(application):
    if application is None:
        return None
    return {"id": application.pk, "username": application.applicant.username,
            "motivation": application.motivation, "status": application.status,
            "created_at": application.created_at.isoformat(),
            "decided_at": application.decided_at.isoformat() if application.decided_at else None,
            "decided_by_username": application.decided_by.username if application.decided_by else None}


class WalletHistoryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        rows = CreditTransaction.objects.filter(user=request.user).order_by("-created_at")[:100]
        payments = MpesaPayment.objects.filter(user=request.user).order_by("-created_at")[:50]
        return Response({"transactions": [{"id": row.pk, "type": row.transaction_type,
            "amount": str(row.amount), "balance_after": str(row.balance_after),
            "description": row.description, "created_at": row.created_at.isoformat()}
            for row in rows], "payments": [{"id": payment.pk, "type": "topup",
            "amount": str(payment.amount), "status": payment.status,
            "reference": payment.mpesa_receipt_number,
            "created_at": payment.created_at.isoformat()} for payment in payments]})
