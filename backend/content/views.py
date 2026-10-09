from rest_framework import generics, permissions, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Content
from .serializers import (
    ContentSerializer,
    ProtectedContentSerializer,
)
from .services import (
    generate_private_content_url,
    upload_content_file,
)


class IsCreatorOrAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        return request.user.profile.role in ["creator", "admin"]


class ContentListView(generics.ListAPIView):
    serializer_class = ContentSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return Content.objects.filter(
            is_published=True
        ).order_by("-created_at")


class ContentCreateView(APIView):
    permission_classes = [IsCreatorOrAdmin]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        required_fields = [
            "title",
            "description",
            "content_type",
            "price",
            "file",
        ]

        for field in required_fields:
            if field not in request.data:
                return Response(
                    {
                        "error": f"{field} is required."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        try:
            upload_result = upload_content_file(
                request.FILES["file"],
                request.data["content_type"],
            )
        except ValueError as error:
            return Response(
                {
                    "error": str(error)
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        content = Content.objects.create(
            creator=request.user,
            title=request.data["title"],
            description=request.data["description"],
            content_type=request.data["content_type"],
            price=request.data["price"],
            thumbnail_url=request.data.get(
                "thumbnail_url",
                "",
            ),
            is_published=request.data.get(
                "is_published",
                "false",
            ).lower() == "true",
            cloudinary_public_id=upload_result[
                "public_id"
            ],
        )

        serializer = ContentSerializer(content)

        return Response(
            {
                "message": "Content uploaded successfully.",
                "content": serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )


class ContentAccessView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, content_id):
        try:
            content = Content.objects.get(
                id=content_id,
                is_published=True,
            )
        except Content.DoesNotExist:
            return Response(
                {
                    "error": "Content not found or unavailable."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        has_purchased = content.purchases.filter(
            user=request.user
        ).exists()

        if not has_purchased:
            return Response(
                {
                    "error": (
                        "You must purchase this content "
                        "before accessing it."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            secure_url = generate_private_content_url(
                content
            )
        except ValueError as error:
            return Response(
                {
                    "error": str(error)
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            {
                "message": "Content access granted.",
                "content": {
                    "id": content.id,
                    "title": content.title,
                    "content_type": content.content_type,
                    "file_url": secure_url,
                },
            },
            status=status.HTTP_200_OK,
        )


class MyContentListView(generics.ListAPIView):
    serializer_class = ContentSerializer
    permission_classes = [IsCreatorOrAdmin]

    def get_queryset(self):
        return Content.objects.filter(
            creator=self.request.user
        ).order_by("-created_at")


class MyContentUpdateView(APIView):
    permission_classes = [IsCreatorOrAdmin]

    def patch(self, request, content_id):
        try:
            content = Content.objects.get(
                id=content_id,
                creator=request.user,
            )
        except Content.DoesNotExist:
            if request.user.profile.role == "admin":
                try:
                    content = Content.objects.get(
                        id=content_id
                    )
                except Content.DoesNotExist:
                    return Response(
                        {
                            "error": "Content not found."
                        },
                        status=status.HTTP_404_NOT_FOUND,
                    )
            else:
                return Response(
                    {
                        "error": "Content not found."
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

        allowed_fields = [
            "title",
            "description",
            "price",
            "thumbnail_url",
            "is_published",
        ]

        for field in allowed_fields:
            if field in request.data:
                setattr(
                    content,
                    field,
                    request.data[field],
                )

        content.save()

        serializer = ContentSerializer(content)

        return Response(
            {
                "message": "Content updated successfully.",
                "content": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class MyContentPublishView(APIView):
    permission_classes = [IsCreatorOrAdmin]

    def patch(self, request, content_id):
        try:
            content = Content.objects.get(
                id=content_id,
                creator=request.user,
            )
        except Content.DoesNotExist:
            if request.user.profile.role == "admin":
                try:
                    content = Content.objects.get(
                        id=content_id
                    )
                except Content.DoesNotExist:
                    return Response(
                        {
                            "error": "Content not found."
                        },
                        status=status.HTTP_404_NOT_FOUND,
                    )
            else:
                return Response(
                    {
                        "error": "Content not found."
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

        if "is_published" not in request.data:
            return Response(
                {
                    "error": "is_published is required."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        value = request.data["is_published"]

        if isinstance(value, bool):
            is_published = value
        elif isinstance(value, str):
            if value.lower() == "true":
                is_published = True
            elif value.lower() == "false":
                is_published = False
            else:
                return Response(
                    {
                        "error": (
                            "is_published must be "
                            "true or false."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            return Response(
                {
                    "error": (
                        "is_published must be "
                        "true or false."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        content.is_published = is_published
        content.save(update_fields=["is_published", "updated_at"])

        serializer = ContentSerializer(content)

        return Response(
            {
                "message": (
                    "Content published successfully."
                    if is_published
                    else "Content unpublished successfully."
                ),
                "content": serializer.data,
            },
            status=status.HTTP_200_OK,
        )