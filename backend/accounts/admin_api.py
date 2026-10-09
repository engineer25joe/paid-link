from decimal import Decimal

from django.contrib.auth.models import User
from django.db.models import Count, Q, Sum, Value, DecimalField
from django.db.models.functions import Coalesce
from rest_framework import permissions
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from content.models import Content
from payments.models import CreatorWithdrawal, MpesaPayment
from purchases.models import Purchase
from .earnings import mask_phone_number
from .models import CreditTransaction


class IsPlatformAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and
                    hasattr(request.user, "profile") and request.user.profile.role == "admin")


class AdminPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 100


class AdminListView(APIView):
    permission_classes = [IsPlatformAdmin]
    model = None
    fields = ()
    select_related = ()
    search_fields = ()

    def get_queryset(self):
        qs = self.model.objects.all()
        if self.select_related:
            qs = qs.select_related(*self.select_related)
        for key, field in getattr(self, "filters", {}).items():
            value = self.request.query_params.get(key)
            if value is not None:
                qs = qs.filter(**{field: value})
        search = self.request.query_params.get("search", "").strip()
        if search and self.search_fields:
            query = Q()
            for field in self.search_fields:
                query |= Q(**{f"{field}__icontains": search})
            qs = qs.filter(query)
        return qs.order_by("-pk")

    def serialize(self, obj):
        data = {}
        for field in self.fields:
            if field == "phone_number" and isinstance(obj, User):
                data[field] = mask_phone_number(obj.profile.phone_number)
            elif field == "phone_number":
                data[field] = mask_phone_number(obj.phone_number)
            elif field == "role":
                data[field] = obj.profile.role
            elif field == "credits":
                data[field] = str(obj.profile.credits)
            elif field == "is_verified":
                data[field] = obj.profile.is_verified
            elif field == "username" and hasattr(obj, "user"):
                data[field] = obj.user.username
            elif field == "email" and hasattr(obj, "user"):
                data[field] = obj.user.email
            elif field == "creator_username":
                data[field] = obj.creator.username
            elif field == "user_username":
                data[field] = obj.user.username
            elif field == "content_title":
                data[field] = obj.content.title
            elif field == "approved_by_username":
                data[field] = obj.approved_by.username if obj.approved_by else None
            elif field == "amount_paid":
                data[field] = str(obj.amount_paid)
            elif field == "amount":
                data[field] = str(obj.amount)
            elif field == "price":
                data[field] = str(obj.price)
            elif field == "balance_after":
                data[field] = str(obj.balance_after)
            else:
                value = getattr(obj, field)
                data[field] = value.isoformat() if hasattr(value, "isoformat") else value
        return data

    def get(self, request):
        qs = self.get_queryset()
        paginator = AdminPagination()
        page = paginator.paginate_queryset(qs, request, view=self)
        return paginator.get_paginated_response([self.serialize(obj) for obj in page])


class AdminDetailView(AdminListView):
    def get(self, request, pk):
        try:
            obj = self.get_queryset().get(pk=pk)
        except self.model.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound()
        return Response(self.serialize(obj))


class DashboardStatsView(APIView):
    permission_classes = [IsPlatformAdmin]

    def get(self, request):
        users = User.objects.count()
        roles = User.objects.values("profile__role").annotate(total=Count("pk"))
        role_counts = {row["profile__role"]: row["total"] for row in roles}
        purchase_value = Purchase.objects.aggregate(total=Coalesce(
            Sum("amount_paid"), Value(Decimal("0.00")),
            output_field=DecimalField(max_digits=14, decimal_places=2))) ["total"]
        return Response({
            "total_users": users,
            "learners": role_counts.get("learner", 0),
            "creators": role_counts.get("creator", 0),
            "published_content": Content.objects.filter(is_published=True).count(),
            "total_purchases": Purchase.objects.count(),
            "total_purchase_value": str(purchase_value),
            "pending_withdrawals": CreatorWithdrawal.objects.filter(status="pending").count(),
            "unresolved_payment_records": (
                MpesaPayment.objects.filter(status__in=("pending", "outcome_unknown")).count() +
                CreatorWithdrawal.objects.filter(status__in=("submitting", "provider_pending", "outcome_unknown")).count()
            ),
        })


class UserList(AdminListView):
    model = User
    fields = ("id", "username", "email", "first_name", "last_name", "is_active", "date_joined", "role", "phone_number", "credits", "is_verified")
    select_related = ("profile",)
    search_fields = ("username", "email", "first_name", "last_name")
    filters = {"role": "profile__role", "is_active": "is_active"}


class CreatorList(UserList):
    def get_queryset(self):
        return super().get_queryset().filter(profile__role="creator")


class LearnerList(UserList):
    def get_queryset(self):
        return super().get_queryset().filter(profile__role="learner")


class ContentList(AdminListView):
    model = Content
    fields = ("id", "creator_username", "title", "description", "content_type", "price", "thumbnail_url", "is_published", "created_at", "updated_at")
    select_related = ("creator",)
    search_fields = ("title", "description", "creator__username")
    filters = {"creator": "creator_id", "is_published": "is_published", "content_type": "content_type"}


class PurchaseList(AdminListView):
    model = Purchase
    fields = ("id", "user_username", "content_title", "amount_paid", "purchased_at")
    select_related = ("user", "content")
    search_fields = ("user__username", "content__title")
    filters = {"user": "user_id", "content": "content_id"}


class LedgerList(AdminListView):
    model = CreditTransaction
    fields = ("id", "user_username", "transaction_type", "amount", "balance_after", "description", "created_at", "idempotency_key")
    select_related = ("user",)
    search_fields = ("user__username", "description", "idempotency_key")
    filters = {"user": "user_id", "transaction_type": "transaction_type"}


class WithdrawalList(AdminListView):
    model = CreatorWithdrawal
    fields = ("id", "creator_username", "amount", "status", "payout_status", "phone_number", "approved_by_username", "approved_at", "created_at", "updated_at", "failure_reason", "callback_discrepancy", "refund_recorded_at", "provider_failure_verified_at")
    select_related = ("creator", "approved_by")
    search_fields = ("creator__username", "failure_reason", "callback_discrepancy")
    filters = {"creator": "creator_id", "status": "status", "payout_status": "payout_status"}


class WithdrawalDetail(WithdrawalList):
    def get(self, request, pk):
        return AdminDetailView.get(self, request, pk)


class UserDetail(UserList):
    def get(self, request, pk):
        return AdminDetailView.get(self, request, pk)


class CreatorDetail(CreatorList):
    def get(self, request, pk):
        return AdminDetailView.get(self, request, pk)


class LearnerDetail(LearnerList):
    def get(self, request, pk):
        return AdminDetailView.get(self, request, pk)


class ContentDetail(ContentList):
    def get(self, request, pk):
        return AdminDetailView.get(self, request, pk)


class PurchaseDetail(PurchaseList):
    def get(self, request, pk):
        return AdminDetailView.get(self, request, pk)
