from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from content.models import Content

from .services import purchase_content


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