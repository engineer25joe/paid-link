from django.db import connection
from django.db.utils import DatabaseError
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthView(APIView):
    """Minimal liveness/readiness probe with no configuration or exception details."""

    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        except DatabaseError:
            return Response({"status": "unavailable"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response({"status": "ok"}, status=status.HTTP_200_OK)
