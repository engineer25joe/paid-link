from rest_framework import generics, permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from content.models import Content

from .services import purchase_content
from .models import Purchase


class LearnerPurchaseSerializer(serializers.ModelSerializer):
    content_id = serializers.IntegerField(source="content.id", read_only=True)
    title = serializers.CharField(source="content.title", read_only=True)
    description = serializers.CharField(source="content.description", read_only=True)
    content_type = serializers.CharField(source="content.content_type", read_only=True)
    price = serializers.SerializerMethodField()
    price_kes = serializers.DecimalField(source="content.price_kes", max_digits=10, decimal_places=2, read_only=True)
    credits_charged = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    conversion_rate = serializers.DecimalField(max_digits=12, decimal_places=4, read_only=True)
    thumbnail_url = serializers.URLField(source="content.thumbnail_url", allow_null=True, read_only=True)

    class Meta:
        model = Purchase
        fields = ("id", "content_id", "title", "description", "content_type", "price", "price_kes", "credits_charged", "conversion_rate", "thumbnail_url", "amount_paid", "purchased_at")

    def get_price(self, obj):
        return str(obj.credits_charged)


class MyPurchasesView(generics.ListAPIView):
    serializer_class = LearnerPurchaseSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        return Purchase.objects.filter(user=self.request.user).select_related("content").order_by("-purchased_at")


class PurchaseContentView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, content_id):
        try:
            new_balance = purchase_content(
                request.user,
                content_id,
            )

            content = Content.objects.get(
                id=content_id,
                is_published=True,
            )

            return Response(
                {
                    "message": "Content purchased successfully.",
                    "purchase": {
                        "content_id": content.id,
                        "title": content.title,
                        "amount_paid": str(content.price_kes),
                        "credits_charged": str(content.purchases.get(user=request.user).credits_charged),
                        "conversion_rate": str(content.purchases.get(user=request.user).conversion_rate),
                    },
                    "remaining_credits": str(new_balance),
                },
                status=status.HTTP_201_CREATED,
            )

        except Content.DoesNotExist:
            return Response(
                {
                    "error": "Content not found or unavailable."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        except ValueError as error:
            return Response(
                {
                    "error": str(error)
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
