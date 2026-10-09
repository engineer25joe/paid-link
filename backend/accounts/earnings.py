from decimal import Decimal

from django.db.models import Count, DecimalField, Max, Q, Sum, Value
from django.db.models.functions import Coalesce
from rest_framework import generics, permissions, serializers
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from content.models import Content
from payments.models import CreatorWithdrawal
from purchases.models import Purchase

from .models import CreditTransaction, UserProfile


ZERO_MONEY = Value(Decimal("0.00"), output_field=DecimalField(max_digits=12, decimal_places=2))
SUCCESSFUL_WITHDRAWAL_STATUSES = ("paid", "completed")
UNRESOLVED_WITHDRAWAL_STATUSES = (
    "pending", "approved_reserved", "submitting", "provider_pending", "outcome_unknown",
    "payout_failed_verified", "approved", "processing",
)


class CreatorDashboardPermission(permissions.BasePermission):
    """Creators and admins may view only records scoped to their own account."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.profile.role in {"creator", "admin"}
        )


class CreatorHistoryPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 100


class CreatorHistoryView(APIView):
    permission_classes = [CreatorDashboardPermission]
    serializer_class = None

    def paginated_response(self, queryset, request):
        paginator = CreatorHistoryPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        return paginator.get_paginated_response(self.serializer_class(page, many=True).data)


class CreatorEarningsSummaryView(APIView):
    permission_classes = [CreatorDashboardPermission]

    def get(self, request):
        creator_id = request.user.pk
        sales = Purchase.objects.filter(content__creator_id=creator_id).aggregate(
            total_sales=Count("pk"),
            gross_earnings=Coalesce(Sum("amount_paid"), ZERO_MONEY),
        )
        withdrawal_totals = CreatorWithdrawal.objects.filter(creator_id=creator_id).aggregate(
            total_withdrawn=Coalesce(
                Sum("amount", filter=Q(status__in=SUCCESSFUL_WITHDRAWAL_STATUSES)), ZERO_MONEY,
            ),
            pending_processing=Coalesce(
                Sum("amount", filter=Q(status__in=UNRESOLVED_WITHDRAWAL_STATUSES)), ZERO_MONEY,
            ),
        )
        published_contents = Content.objects.filter(creator_id=creator_id, is_published=True).count()
        balance = UserProfile.objects.only("credits").get(user_id=creator_id).credits
        return Response({
            "total_sales_count": sales["total_sales"],
            "gross_earnings": str(sales["gross_earnings"]),
            "available_credit_balance": str(balance),
            "total_withdrawn": str(withdrawal_totals["total_withdrawn"]),
            "pending_processing_withdrawal_amount": str(withdrawal_totals["pending_processing"]),
            "published_contents_count": published_contents,
        })


class ContentEarningsSerializer(serializers.Serializer):
    content_id = serializers.IntegerField(source="id")
    title = serializers.CharField()
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    purchase_count = serializers.IntegerField()
    gross_sales = serializers.DecimalField(max_digits=12, decimal_places=2)
    latest_purchase_at = serializers.DateTimeField(allow_null=True)


class CreatorEarningsByContentView(generics.ListAPIView):
    permission_classes = [CreatorDashboardPermission]
    serializer_class = ContentEarningsSerializer
    pagination_class = None

    def get_queryset(self):
        return Content.objects.filter(creator_id=self.request.user.pk).annotate(
            purchase_count=Count("purchases"),
            gross_sales=Coalesce(Sum("purchases__amount_paid"), ZERO_MONEY),
            latest_purchase_at=Max("purchases__purchased_at"),
        ).order_by("title", "pk")


class CreditTransactionSerializer(serializers.ModelSerializer):
    timestamp = serializers.DateTimeField(source="created_at", read_only=True)

    class Meta:
        model = CreditTransaction
        fields = ("id", "transaction_type", "amount", "balance_after", "description", "timestamp", "idempotency_key")
        read_only_fields = fields


class CreatorTransactionHistoryView(CreatorHistoryView):
    serializer_class = CreditTransactionSerializer

    def get(self, request):
        queryset = CreditTransaction.objects.filter(user_id=request.user.pk).order_by("-created_at", "-pk")
        return self.paginated_response(queryset, request)


def mask_phone_number(phone_number):
    value = str(phone_number or "")
    visible = value[-4:]
    return ("*" * max(len(value) - 4, 4)) + visible


class CreatorWithdrawalSerializer(serializers.ModelSerializer):
    phone_number = serializers.SerializerMethodField()

    class Meta:
        model = CreatorWithdrawal
        fields = (
            "id", "amount", "status", "payout_status", "phone_number", "created_at", "updated_at",
            "approved_at", "refund_recorded_at", "provider_failure_verified_at", "failure_reason",
            "callback_discrepancy",
        )
        read_only_fields = fields

    def get_phone_number(self, withdrawal):
        return mask_phone_number(withdrawal.phone_number)


class CreatorWithdrawalHistoryView(CreatorHistoryView):
    serializer_class = CreatorWithdrawalSerializer

    def get(self, request):
        queryset = CreatorWithdrawal.objects.filter(creator_id=request.user.pk).only(
            "id", "creator_id", "amount", "status", "payout_status", "phone_number", "created_at", "updated_at",
            "approved_at", "refund_recorded_at", "provider_failure_verified_at", "failure_reason", "callback_discrepancy",
        ).order_by("-created_at", "-pk")
        return self.paginated_response(queryset, request)
