from decimal import Decimal

from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
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
from .models import CreditTransaction, CreditRateHistory, PlatformSettings, CreatorApplication, UserProfile, effective_role
from .services import adjust_credits, validate_credits
from decimal import InvalidOperation
import uuid


class IsPlatformAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and effective_role(request.user) == "admin")


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
            elif field == "creator_created_by_username":
                data[field] = obj.profile.creator_created_by.username if obj.profile.creator_created_by else None
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
            elif field == "balance_before":
                data[field] = str(obj.balance_before) if obj.balance_before is not None else None
            elif field == "administrator_username":
                data[field] = obj.administrator.username if obj.administrator else None
            elif field in {"amount_kes", "conversion_rate"}:
                value = getattr(obj, field)
                data[field] = str(value) if value is not None else None
            elif field in {"reason", "payment_reference"}:
                data[field] = getattr(obj, field)
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
        roles = User.objects.filter(is_superuser=False).values("profile__role").annotate(total=Count("pk"))
        role_counts = {row["profile__role"]: row["total"] for row in roles}
        purchase_value = Purchase.objects.aggregate(total=Coalesce(
            Sum("amount_paid"), Value(Decimal("0.00")),
            output_field=DecimalField(max_digits=14, decimal_places=2))) ["total"]
        guest_sales = MpesaPayment.objects.filter(status="completed", guest_access__isnull=False).aggregate(
            total=Sum("amount"), count=Count("pk"))
        total_purchase_value = purchase_value + (guest_sales["total"] or Decimal("0.00"))
        return Response({
            "total_users": users,
            "learners": role_counts.get("learner", 0),
            "creators": role_counts.get("creator", 0),
            "published_content": Content.objects.filter(is_published=True).count(),
            "total_purchases": Purchase.objects.count() + guest_sales["count"],
            "total_purchase_value": f"{total_purchase_value:.2f}",
            "pending_withdrawals": CreatorWithdrawal.objects.filter(status="pending").count(),
            "unresolved_payment_records": (
                MpesaPayment.objects.filter(status__in=("pending", "outcome_unknown")).count() +
                CreatorWithdrawal.objects.filter(status__in=("submitting", "provider_pending", "outcome_unknown")).count()
            ),
        })


class UserList(AdminListView):
    model = User
    fields = ("id", "username", "email", "first_name", "last_name", "is_active", "is_superuser", "date_joined", "role", "phone_number", "credits", "is_verified", "creator_created_by_username")
    select_related = ("profile", "profile__creator_created_by")
    search_fields = ("username", "email", "first_name", "last_name")
    filters = {"is_active": "is_active"}

    def get_queryset(self):
        qs = super().get_queryset()
        role = self.request.query_params.get("role")
        if role == "admin":
            qs = qs.filter(Q(profile__role="admin") | Q(is_superuser=True))
        elif role:
            qs = qs.filter(profile__role=role, is_superuser=False)
        return qs

    def serialize(self, obj):
        data = super().serialize(obj)
        data["role"] = effective_role(obj)
        return data


class CreatorApplicationList(APIView):
    permission_classes = [IsPlatformAdmin]

    def get(self, request):
        apps = CreatorApplication.objects.select_related("applicant", "decided_by").all()
        paginator = AdminPagination()
        page = paginator.paginate_queryset(apps, request, view=self)
        return paginator.get_paginated_response([{ "id": app.pk, "username": app.applicant.username,
            "email": app.applicant.email, "motivation": app.motivation, "status": app.status,
            "created_at": app.created_at.isoformat(), "decided_at": app.decided_at.isoformat() if app.decided_at else None,
            "decided_by_username": app.decided_by.username if app.decided_by else None}
            for app in page])


class CreatorApplicationDecision(APIView):
    permission_classes = [IsPlatformAdmin]

    def post(self, request, application_id):
        decision = request.data.get("status")
        if decision not in {"approved", "rejected"}:
            return Response({"error": "Decision must be approved or rejected."}, status=400)
        with transaction.atomic():
            try:
                application = CreatorApplication.objects.select_for_update().select_related("applicant").get(pk=application_id)
            except CreatorApplication.DoesNotExist:
                return Response({"error": "Application not found."}, status=404)
            if application.status != "pending":
                return Response({"error": "Only pending applications can be decided."}, status=400)
            application.status = decision
            application.decided_by = request.user
            application.decided_at = timezone.now()
            application.save(update_fields=["status", "decided_by", "decided_at", "updated_at"])
            if decision == "approved":
                application.applicant.profile.role = "creator"
                application.applicant.profile.save(update_fields=["role", "updated_at"])
        return Response({"application_id": application.pk, "status": application.status})


class AdminCreatorCreate(APIView):
    permission_classes = [IsPlatformAdmin]

    def post(self, request):
        username = str(request.data.get("username", "")).strip()
        email = str(request.data.get("email", "")).strip()
        password = request.data.get("password", "")
        if not username or not email or not password:
            return Response({"error": "Username, email, and an initial password are required."}, status=400)
        if User.objects.filter(username=username).exists() or User.objects.filter(email__iexact=email).exists():
            return Response({"error": "Username or email is already in use."}, status=400)
        try:
            validate_password(password, user=User(username=username, email=email))
        except ValidationError as exc:
            return Response({"error": list(exc.messages)}, status=400)
        with transaction.atomic():
            creator = User.objects.create_user(username=username, email=email, password=password)
            creator.profile.role = "creator"
            creator.profile.creator_created_by = request.user
            creator.profile.save(update_fields=["role", "creator_created_by", "updated_at"])
        return Response({"id": creator.pk, "username": creator.username, "role": "creator"}, status=201)


class AdminUserStatus(APIView):
    permission_classes = [IsPlatformAdmin]

    def patch(self, request, user_id):
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({"error": "User not found."}, status=404)
        if user.pk == request.user.pk or user.is_superuser:
            return Response({"error": "This administrator account cannot be suspended here."}, status=400)
        active = request.data.get("is_active")
        if not isinstance(active, bool):
            return Response({"error": "is_active must be a boolean."}, status=400)
        user.is_active = active
        user.save(update_fields=["is_active"])
        return Response({"id": user.pk, "is_active": user.is_active})


class CreatorList(UserList):
    def get_queryset(self):
        return super().get_queryset().filter(profile__role="creator")


class LearnerList(UserList):
    def get_queryset(self):
        return super().get_queryset().filter(profile__role="learner", is_superuser=False)


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
    fields = ("id", "user_username", "transaction_type", "amount", "balance_before", "balance_after", "description", "reason", "administrator_username", "amount_kes", "conversion_rate", "payment_reference", "created_at", "idempotency_key")
    select_related = ("user", "administrator")
    search_fields = ("user__username", "description", "idempotency_key")
    filters = {"user": "user_id", "transaction_type": "transaction_type"}

    def serialize(self, obj):
        data = super().serialize(obj)
        data["administrator_username"] = obj.administrator.username if obj.administrator else None
        for key in ("balance_before", "amount_kes", "conversion_rate"):
            value = getattr(obj, key)
            data[key] = str(value) if value is not None else None
        data["amount"] = str(obj.amount)
        data["balance_after"] = str(obj.balance_after)
        data["reason"] = obj.reason
        data["payment_reference"] = obj.payment_reference
        return data


class AdminWalletUsers(APIView):
    permission_classes = [IsPlatformAdmin]

    def get(self, request):
        query = str(request.query_params.get("search", "")).strip()
        if len(query) < 2:
            return Response({"results": []})
        users = User.objects.filter(Q(username__icontains=query) | Q(email__icontains=query)).select_related("profile")[:30]
        return Response({"results": [{"id": user.pk, "username": user.username, "email": user.email,
            "credits": str(user.profile.credits)} for user in users]})


class AdminWalletAdjustment(APIView):
    permission_classes = [IsPlatformAdmin]

    def post(self, request, user_id):
        direction = request.data.get("direction")
        reason = str(request.data.get("reason", "")).strip()
        key = str(request.data.get("idempotency_key", "")).strip()
        if direction not in {"add", "remove"} or not reason or len(reason) > 255:
            return Response({"error": "Choose add or remove and provide a reason of at most 255 characters."}, status=400)
        try:
            amount = validate_credits(request.data.get("amount"))
            key = str(uuid.UUID(key)) if key else str(uuid.uuid4())
        except (ValueError, TypeError, InvalidOperation, AttributeError):
            return Response({"error": "Enter a valid positive amount and adjustment reference."}, status=400)
        try:
            with transaction.atomic():
                target = User.objects.select_for_update().select_related("profile").get(pk=user_id)
                signed_amount = amount if direction == "add" else -amount
                balance = adjust_credits(target, signed_amount, reason,
                    f"admin-adjustment:{key}", administrator=request.user, reason=reason)
                entry = CreditTransaction.objects.get(idempotency_key=f"admin-adjustment:{key}")
        except User.DoesNotExist:
            return Response({"error": "User not found."}, status=404)
        except ValueError as error:
            return Response({"error": str(error)}, status=400)
        return Response({"status": "completed", "user": target.username, "amount": str(entry.amount),
            "balance_before": str(entry.balance_before), "balance_after": str(balance), "reason": entry.reason})


class AdminCreditRate(APIView):
    permission_classes = [IsPlatformAdmin]

    def get(self, request):
        setting = PlatformSettings.current()
        history = CreditRateHistory.objects.select_related("changed_by")[:20]
        return Response({"rate": str(setting.credit_to_kes_rate), "updated_at": setting.updated_at,
            "updated_by": setting.updated_by.username if setting.updated_by else None,
            "history": [{"rate": str(item.rate), "changed_by": item.changed_by.username,
                         "created_at": item.created_at} for item in history]})

    def put(self, request):
        try:
            rate = Decimal(str(request.data.get("rate")))
        except (InvalidOperation, TypeError, ValueError):
            return Response({"error": "Enter a valid positive conversion rate."}, status=400)
        if not rate.is_finite() or rate <= 0 or rate.as_tuple().exponent < -4 or rate > Decimal("99999999.9999"):
            return Response({"error": "Rate must be positive and have no more than four decimal places."}, status=400)
        with transaction.atomic():
            setting = PlatformSettings.objects.select_for_update().get(pk=1)
            if setting.credit_to_kes_rate != rate:
                setting.credit_to_kes_rate = rate
                setting.updated_by = request.user
                setting.save(update_fields=["credit_to_kes_rate", "updated_by", "updated_at"])
                CreditRateHistory.objects.create(rate=rate, changed_by=request.user)
        return Response({"rate": str(setting.credit_to_kes_rate), "updated_at": setting.updated_at,
                         "updated_by": request.user.username})


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
