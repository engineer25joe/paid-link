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
    price = serializers.DecimalField(source="content.price", max_digits=10, decimal_places=2, read_only=True)
    thumbnail_url = serializers.URLField(source="content.thumbnail_url", allow_null=True, read_only=True)

    class Meta:
        model = Purchase
        fields = ("id", "content_id", "title", "description", "content_type", "price", "thumbnail_url", "amount_paid", "purchased_at")


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
                        "amount_paid": str(content.price),
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
