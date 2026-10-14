from datetime import timedelta
from decimal import Decimal, InvalidOperation
import secrets

from django.conf import settings
from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.throttling import AnonRateThrottle
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import PlatformSettings, effective_role
from accounts.services import validate_mpesa_amount
from content.models import Content
from content.services import generate_private_content_url
from .models import GuestContentAccess, MpesaPayment, SharedContentShare
from .services import callback_url_with_token, initiate_stk_push, normalize_mpesa_phone


DEFAULT_SHARE_HOURS = 2
MAX_SHARE_HOURS = 24 * 30
MAX_SHARE_USES = 1000


def share_state(share, now=None):
    now = now or timezone.now()
    if share.status == "revoked":
        return "REVOKED"
    if share.expires_at <= now:
        return "EXPIRED"
    if share.used_count + share.reserved_count >= share.max_uses:
        return "LIMIT REACHED"
    return "ACTIVE"


def safe_response(response):
    response["Cache-Control"] = "no-store, private"
    response["Referrer-Policy"] = "no-referrer"
    response["X-Content-Type-Options"] = "nosniff"
    return response


def share_data(share, request):
    return {
        "id": share.pk,
        "content_title": share.content.title,
        "content_id": share.content_id,
        "share_url": f"{getattr(settings, 'PUBLIC_WEB_URL', 'https://paidlinkweb.onrender.com').rstrip('/')}/shared/{share.token}",
        "created_by": share.created_by.username,
        "created_at": share.created_at,
        "expires_at": share.expires_at,
        "access_duration_seconds": share.access_duration_seconds,
        "max_uses": share.max_uses,
        "successful_uses": share.used_count,
        "remaining_uses": max(0, share.max_uses - share.used_count - share.reserved_count),
        "status": share_state(share),
    }


class ShareCollection(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        role = effective_role(request.user)
        if role not in {"creator", "admin"}:
            return Response({"error": "Creator or administrator access required."}, status=403)
        rows = SharedContentShare.objects.select_related("content", "created_by")
        if role != "admin":
            rows = rows.filter(created_by=request.user)
        return safe_response(Response({"results": [share_data(item, request) for item in rows[:200]]}))

    def post(self, request):
        role = effective_role(request.user)
        if role not in {"creator", "admin"}:
            return Response({"error": "Creator or administrator access required."}, status=403)
        try:
            content_id = int(request.data.get("content_id"))
            max_uses = int(request.data.get("max_uses", 2))
            hours = Decimal(str(request.data.get("expires_in_hours", DEFAULT_SHARE_HOURS)))
            access_hours = Decimal(str(request.data.get("access_duration_hours", DEFAULT_SHARE_HOURS)))
            if not hours.is_finite() or hours <= 0 or hours > MAX_SHARE_HOURS:
                raise ValueError()
            if not access_hours.is_finite() or access_hours <= 0 or access_hours > MAX_SHARE_HOURS:
                raise ValueError()
            if max_uses < 1 or max_uses > MAX_SHARE_USES:
                raise ValueError()
        except (ValueError, TypeError, InvalidOperation):
            return Response({"error": "Use a valid published content ID, expiry (up to 30 days), and maximum purchases (1–1000)."}, status=400)
        try:
            item = Content.objects.get(pk=content_id, is_published=True)
        except Content.DoesNotExist:
            return Response({"error": "Published content was not found."}, status=404)
        share = SharedContentShare.objects.create(content=item, created_by=request.user,
            token=secrets.token_urlsafe(32), expires_at=timezone.now() + timedelta(seconds=int(hours * 3600)),
            access_duration_seconds=int(access_hours * 3600), max_uses=max_uses)
        return safe_response(Response(share_data(share, request), status=201))


class ShareRevoke(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, share_id):
        role = effective_role(request.user)
        if role not in {"creator", "admin"}:
            return Response({"error": "Creator or administrator access required."}, status=403)
        try:
            with transaction.atomic():
                share = SharedContentShare.objects.select_for_update().get(pk=share_id)
                if role != "admin" and share.created_by_id != request.user.id:
                    return Response({"error": "You may revoke only links you created."}, status=403)
                if share.status != "revoked":
                    share.status = "revoked"
                    share.revoked_at = timezone.now()
                    share.save(update_fields=["status", "revoked_at"])
        except SharedContentShare.DoesNotExist:
            return Response({"error": "Share was not found."}, status=404)
        return Response({"status": share_state(share)})


class PublicShareDetail(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, token):
        try:
            share = SharedContentShare.objects.select_related("content", "created_by").get(token=token)
        except SharedContentShare.DoesNotExist:
            return safe_response(Response({"error": "This share link is invalid."}, status=404))
        state = share_state(share)
        response = {"status": state, "expires_at": share.expires_at,
            "remaining_uses": max(0, share.max_uses - share.used_count - share.reserved_count)}
        if state == "ACTIVE" and share.content.is_published:
            rate = PlatformSettings.current().credit_to_kes_rate
            response["content"] = {"title": share.content.title, "description": share.content.description,
                "content_type": share.content.content_type, "price_kes": str(share.content.price_kes),
                "creator_username": share.content.creator.username, "conversion_rate": str(rate)}
        elif share.content.is_published is False and state == "ACTIVE":
            response["status"] = "UNAVAILABLE"
        return safe_response(Response(response))


class GuestPaymentCreate(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AnonRateThrottle]

    def post(self, request, token):
        try:
            phone = normalize_mpesa_phone(request.data.get("phone_number", ""))
        except ValueError as exc:
            return Response({"error": str(exc)}, status=400)
        setting = PlatformSettings.current()
        try:
            with transaction.atomic():
                share = SharedContentShare.objects.select_for_update().select_related("content").get(token=token)
                if share_state(share) != "ACTIVE" or not share.content.is_published:
                    return Response({"error": "This share link has expired, been revoked, or reached its purchase limit."}, status=410)
                amount = validate_mpesa_amount(share.content.price_kes)
                share.reserved_count += 1
                share.save(update_fields=["reserved_count"])
                payment_token = secrets.token_urlsafe(32)
                payment = MpesaPayment.objects.create(user=None, guest_share=share, guest_payment_token=payment_token,
                    phone_number=phone, amount=amount, credits_awarded=0, conversion_rate=setting.credit_to_kes_rate,
                    callback_token=secrets.token_hex(32))
        except SharedContentShare.DoesNotExist:
            return Response({"error": "This share link is invalid."}, status=404)
        except ValueError as exc:
            return Response({"error": str(exc)}, status=400)

        try:
            result = initiate_stk_push(phone, amount, f"EBGUEST-{payment.pk}", "ElimuBang shared content",
                callback_url=callback_url_with_token(settings.MPESA_CALLBACK_URL, payment.callback_token))
            with transaction.atomic():
                payment = MpesaPayment.objects.select_for_update().get(pk=payment.pk)
                payment.merchant_request_id = result.get("MerchantRequestID")
                payment.checkout_request_id = result.get("CheckoutRequestID")
                code = result.get("ResponseCode")
                if code not in ("0", 0, None):
                    payment.status = "failed"
                    share = SharedContentShare.objects.select_for_update().get(pk=payment.guest_share_id)
                    share.reserved_count = max(0, share.reserved_count - 1)
                    share.save(update_fields=["reserved_count"])
                elif not result.get("CheckoutRequestID"):
                    payment.status = "outcome_unknown"
                payment.result_description = str(result.get("ResponseDescription", ""))[:500]
                payment.save(update_fields=["merchant_request_id", "checkout_request_id", "status", "result_description", "updated_at"])
        except Exception:
            with transaction.atomic():
                payment = MpesaPayment.objects.select_for_update().get(pk=payment.pk)
                payment.status = "outcome_unknown"
                payment.result_description = "Provider response requires reconciliation."
                payment.save(update_fields=["status", "result_description", "updated_at"])
        response = Response({"status": payment.status, "amount_kes": str(payment.amount),
            "payment_token": payment.guest_payment_token, "message": "Check your phone and approve the M-Pesa prompt. Access follows provider verification."}, status=202)
        return safe_response(response)


class GuestPaymentStatus(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, token):
        try:
            payment = MpesaPayment.objects.select_related("guest_share").get(guest_payment_token=token, guest_share__isnull=False)
        except MpesaPayment.DoesNotExist:
            return safe_response(Response({"error": "Payment was not found."}, status=404))
        payload = {"status": payment.status, "amount_kes": str(payment.amount), "content_title": payment.guest_share.content.title}
        if payment.status == "completed":
            try:
                access = payment.guest_access
                if access.expires_at > timezone.now() and access.share.status == "active":
                    payload.update({"access_url": f"/guest-access/{access.token}", "access_expires_at": access.expires_at})
                else:
                    payload["status"] = "completed_no_access"
            except GuestContentAccess.DoesNotExist:
                payload["status"] = "completed_no_access"
        return safe_response(Response(payload))


class GuestContentView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, token):
        try:
            access = GuestContentAccess.objects.select_related("share__content", "payment").get(token=token)
        except GuestContentAccess.DoesNotExist:
            return safe_response(Response({"error": "Guest access link is invalid."}, status=404))
        if access.expires_at <= timezone.now() or access.share.status != "active" or not access.share.content.is_published:
            return safe_response(Response({"error": "This guest access link has expired or been revoked."}, status=410))
        try:
            remaining_seconds = int((access.expires_at - timezone.now()).total_seconds())
            if remaining_seconds <= 0:
                return safe_response(Response({"error": "This guest access link has expired."}, status=410))
            url = generate_private_content_url(access.share.content, expires_in_seconds=min(300, remaining_seconds))
        except ValueError as exc:
            return safe_response(Response({"error": str(exc)}, status=404))
        response = Response({"content": {"title": access.share.content.title,
            "description": access.share.content.description, "content_type": access.share.content.content_type,
            "file_url": url}, "expires_at": access.expires_at})
        return safe_response(response)
