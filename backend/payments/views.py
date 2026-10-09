from decimal import Decimal, InvalidOperation
import secrets

from django.db import IntegrityError, transaction
from django.conf import settings
from django.db.models import Sum
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import UserProfile
from accounts.services import add_credits, deduct_credits, validate_b2c_amount, validate_money, validate_mpesa_amount
from .models import CreatorWithdrawal, MpesaPayment
from .services import (
    normalize_mpesa_phone,
    callback_url_with_token,
    send_b2c_payment_request,
    record_provider_failure,
    initiate_stk_push,
    verify_stk_transaction,
    request_b2c_status_reconciliation,
)


class InitiateMpesaPaymentView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            amount = validate_mpesa_amount(request.data.get("amount"))
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        try:
            phone = normalize_mpesa_phone(request.data.get("phone_number", ""))
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        payment = MpesaPayment.objects.create(user=request.user, phone_number=phone, amount=amount,
                                              callback_token=secrets.token_hex(32))
        try:
            result = initiate_stk_push(phone, amount, f"PAIDLINK-{payment.pk}", "Paid Link credit top-up",
                                       callback_url=callback_url_with_token(settings.MPESA_CALLBACK_URL, payment.callback_token))
            with transaction.atomic():
                payment = MpesaPayment.objects.select_for_update().get(pk=payment.pk)
                payment.merchant_request_id = result.get("MerchantRequestID")
                payment.checkout_request_id = result.get("CheckoutRequestID")
                response_code = result.get("ResponseCode")
                payment.result_code = str(response_code or "")
                payment.result_description = result.get("ResponseDescription", "")
                if payment.status not in {"completed", "failed", "cancelled"}:
                    if response_code not in (None, "0", 0):
                        payment.status = "failed"
                    elif response_code in ("0", 0) and not payment.checkout_request_id:
                        payment.status = "outcome_unknown"
                        payment.result_description = "Provider response lacked CheckoutRequestID; reconcile before retrying."
                    elif response_code is None:
                        payment.status = "outcome_unknown"
                        payment.result_description = "Provider response lacked ResponseCode; reconcile before retrying."
                payment.save(update_fields=["merchant_request_id", "checkout_request_id", "result_code",
                                            "result_description", "status", "updated_at"])
            return Response({"payment_id": payment.pk, "status": payment.status,
                             "checkout_request_id": payment.checkout_request_id}, status=status.HTTP_201_CREATED)
        except Exception as exc:
            # An exception after submission may mean Safaricom accepted it.
            with transaction.atomic():
                payment = MpesaPayment.objects.select_for_update().get(pk=payment.pk)
                if payment.status == "pending":
                    payment.status = "outcome_unknown"
                    payment.result_description = str(exc)[:2000]
                    payment.save(update_fields=["status", "result_description", "updated_at"])
            return Response({"payment_id": payment.pk, "status": payment.status,
                             "message": "Provider outcome requires reconciliation."},
                            status=status.HTTP_202_ACCEPTED)


class CreatorWithdrawalRequestView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        if user.profile.role != "creator":
            return Response({"error": "Only content creators can request withdrawals."}, status=403)
        try:
            amount = validate_b2c_amount(request.data.get("amount"))
            phone = normalize_mpesa_phone(request.data.get("phone_number", ""))
        except ValueError as exc:
            return Response({"error": str(exc)}, status=400)
        with transaction.atomic():
            profile = UserProfile.objects.select_for_update().get(user=user)
            pending = CreatorWithdrawal.objects.filter(creator=user, status="pending").aggregate(
                total=Sum("amount")
            )["total"] or Decimal("0")
            if profile.credits - pending < amount:
                return Response({"error": "Insufficient available balance."}, status=400)
            withdrawal = CreatorWithdrawal.objects.create(
                creator=user, phone_number=phone, amount=amount, status="pending"
            )
        return Response({"withdrawal": {"id": withdrawal.pk, "amount": str(withdrawal.amount),
                         "phone_number": withdrawal.phone_number, "status": withdrawal.status}}, status=201)


class AdminWithdrawalListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.profile.role != "admin":
            return Response({"error": "Admin access required."}, status=403)
        withdrawals = CreatorWithdrawal.objects.select_related("creator", "approved_by")
        return Response({"withdrawals": [{
            "id": w.pk, "creator": w.creator.username, "phone_number": w.phone_number,
            "amount": str(w.amount), "status": w.status,
            "approved_by": w.approved_by.username if w.approved_by else None,
            "approved_at": w.approved_at, "created_at": w.created_at, "updated_at": w.updated_at,
        } for w in withdrawals]})


class AdminApproveWithdrawalView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, withdrawal_id):
        if request.user.profile.role != "admin":
            return Response({"error": "Admin access required."}, status=403)
        try:
            with transaction.atomic():
                withdrawal = CreatorWithdrawal.objects.select_for_update().select_related("creator").get(pk=withdrawal_id)
                if withdrawal.status != "pending":
                    return Response({"error": "Only pending withdrawals can be approved."}, status=400)
                profile = UserProfile.objects.select_for_update().get(user=withdrawal.creator)
                amount = validate_b2c_amount(withdrawal.amount)
                if profile.credits < amount:
                    withdrawal.status = "rejected"
                    withdrawal.failure_reason = "Creator has insufficient available balance."
                    withdrawal.save(update_fields=["status", "failure_reason", "updated_at"])
                    return Response({"error": withdrawal.failure_reason}, status=400)
                profile.credits = deduct_credits(
                    withdrawal.creator, amount,
                    description=f"Withdrawal #{withdrawal.pk} reserved",
                    transaction_type="withdrawal",
                    idempotency_key=f"withdrawal:{withdrawal.pk}:reserve",
                )
                withdrawal.status = "approved_reserved"
                withdrawal.approved_by = request.user
                withdrawal.approved_at = timezone.now()
                withdrawal.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])
        except CreatorWithdrawal.DoesNotExist:
            return Response({"error": "Withdrawal not found."}, status=404)
        return Response({"message": "Withdrawal approved and funds reserved.", "withdrawal_id": withdrawal.pk,
                         "status": withdrawal.status, "remaining_credits": str(profile.credits)})


class AdminSubmitWithdrawalView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, withdrawal_id):
        if request.user.profile.role != "admin":
            return Response({"error": "Admin access required."}, status=403)
        try:
            result = send_b2c_payment_request(withdrawal_id)
        except CreatorWithdrawal.DoesNotExist:
            return Response({"error": "Withdrawal not found."}, status=404)
        except ValueError as exc:
            return Response({"error": str(exc)}, status=400)
        except Exception:
            # send_b2c_payment_request persists outcome_unknown on uncertain responses.
            return Response({"status": "outcome_unknown", "message": "Reconciliation required."}, status=202)
        return Response({"status": "provider_pending", "conversation_id": result.get("ConversationID")}, status=202)


class AdminReconcileWithdrawalView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, withdrawal_id):
        if request.user.profile.role != "admin":
            return Response({"error": "Admin access required."}, status=403)
        try:
            with transaction.atomic():
                withdrawal = CreatorWithdrawal.objects.select_for_update().get(pk=withdrawal_id)
                if withdrawal.status not in {"submitting", "provider_pending", "outcome_unknown"}:
                    return Response({"error": "Only unresolved withdrawals can be reconciled."}, status=400)
            response_data = request_b2c_status_reconciliation(withdrawal)
        except CreatorWithdrawal.DoesNotExist:
            return Response({"error": "Withdrawal not found."}, status=404)
        except Exception:
            return Response({"status": "outcome_unknown", "message": "Provider reconciliation is pending."}, status=202)
        return Response({"status": "outcome_unknown", "message": "Provider reconciliation query accepted.",
                         "provider_response": response_data}, status=202)


class AdminReconcilePaymentView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, payment_id):
        if request.user.profile.role != "admin":
            return Response({"error": "Admin access required."}, status=403)
        try:
            with transaction.atomic():
                payment = MpesaPayment.objects.select_for_update().get(pk=payment_id)
                if payment.status == "completed":
                    return Response({"status": "completed"})
                if payment.status not in {"pending", "outcome_unknown"} or not payment.checkout_request_id:
                    return Response({"error": "Only unresolved payments with a provider ID can be reconciled."}, status=400)
                callback = payment.callback_data or {}
            try:
                verified, provider_data = verify_stk_transaction(payment, callback)
            except Exception:
                return Response({"status": "outcome_unknown", "message": "Provider verification unavailable."}, status=202)
            if not verified:
                return Response({"status": "outcome_unknown", "message": "Provider has not verified payment."}, status=202)
            metadata = _stk_metadata(callback)
            receipt = metadata.get("MpesaReceiptNumber")
            try:
                callback_amount = Decimal(str(metadata.get("Amount")))
                if not receipt or not callback_amount.is_finite() or callback_amount != validate_money(payment.amount):
                    return Response({"status": "outcome_unknown", "message": "Callback data does not match the payment."}, status=202)
            except (ValueError, TypeError, InvalidOperation):
                return Response({"status": "outcome_unknown", "message": "Callback data is incomplete."}, status=202)
            with transaction.atomic():
                payment = MpesaPayment.objects.select_for_update().get(pk=payment_id)
                if payment.status == "completed":
                    return Response({"status": "completed"})
                try:
                    with transaction.atomic():
                        payment.mpesa_receipt_number = receipt
                        payment.status = "completed"
                        payment.result_description = str(provider_data)[:2000]
                        payment.save(update_fields=["mpesa_receipt_number", "status", "result_description", "updated_at"])
                        add_credits(payment.user, payment.amount, transaction_type="topup",
                                    description=f"M-Pesa top-up {receipt}", idempotency_key=f"topup:payment:{payment.pk}")
                except IntegrityError:
                    payment.refresh_from_db()
                    payment.status = "outcome_unknown"
                    payment.result_description = "Verified receipt conflicts with another payment."
                    payment.save(update_fields=["status", "result_description", "updated_at"])
                    return Response({"status": "outcome_unknown", "message": "Receipt discrepancy recorded."}, status=202)
        except MpesaPayment.DoesNotExist:
            return Response({"error": "Payment not found."}, status=404)
        return Response({"status": "completed"})


class AdminCancelWithdrawalView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, withdrawal_id):
        if request.user.profile.role != "admin":
            return Response({"error": "Admin access required."}, status=403)
        try:
            with transaction.atomic():
                withdrawal = CreatorWithdrawal.objects.select_for_update().get(pk=withdrawal_id)
                if withdrawal.status == "pending":
                    withdrawal.status = "rejected"
                    withdrawal.save(update_fields=["status", "updated_at"])
                    return Response({"status": withdrawal.status})
                if withdrawal.status != "approved_reserved" or withdrawal.originator_conversation_id:
                    return Response({"error": "Only an unsubmitted reserved withdrawal can be cancelled."}, status=400)
                profile = UserProfile.objects.select_for_update().get(user=withdrawal.creator)
                key = f"withdrawal:{withdrawal.pk}:release"
                amount = validate_money(withdrawal.amount)
                profile.credits = add_credits(
                    withdrawal.creator, amount,
                    transaction_type="adjustment",
                    description=f"Release reservation for withdrawal #{withdrawal.pk}",
                    idempotency_key=key,
                )
                withdrawal.status = "cancelled"
                withdrawal.save(update_fields=["status", "updated_at"])
        except CreatorWithdrawal.DoesNotExist:
            return Response({"error": "Withdrawal not found."}, status=404)
        return Response({"status": withdrawal.status, "remaining_credits": str(profile.credits)})


def _stk_metadata(callback):
    items = callback.get("CallbackMetadata", {}).get("Item", [])
    return {item.get("Name"): item.get("Value") for item in items if isinstance(item, dict)}


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def mpesa_callback(request):
    callback = request.data.get("Body", {}).get("stkCallback", {})
    checkout_id = callback.get("CheckoutRequestID")
    if not checkout_id:
        return Response({"ResultCode": 1, "ResultDesc": "Missing CheckoutRequestID."}, status=400)
    try:
        with transaction.atomic():
            payment = MpesaPayment.objects.select_for_update().get(checkout_request_id=checkout_id)
            if not payment.callback_token or not secrets.compare_digest(
                str(request.query_params.get("callback_token", "")), payment.callback_token
            ):
                return Response({"ResultCode": 1, "ResultDesc": "Callback authorization failed."}, status=403)
            if payment.status == "completed":
                return Response({"ResultCode": 0, "ResultDesc": "Already processed."})
            if payment.status == "failed":
                return Response({"ResultCode": 0, "ResultDesc": "Terminal payment state."})
            payment.callback_data = callback
            code = callback.get("ResultCode")
            payment.result_code = str(code)
            payment.result_description = str(callback.get("ResultDesc", ""))
            if str(code) != "0":
                payment.status = "outcome_unknown"
                payment.result_description = "Untrusted callback failure; reconcile with provider status query."
                payment.save(update_fields=["status", "result_code", "result_description", "callback_data", "updated_at"])
                return Response({"ResultCode": 0, "ResultDesc": "Failure recorded."})
            metadata = _stk_metadata(callback)
            receipt, paid = metadata.get("MpesaReceiptNumber"), metadata.get("Amount")
            try:
                callback_amount = Decimal(str(paid))
                valid = callback_amount.is_finite() and callback_amount == validate_money(payment.amount)
            except (ValueError, InvalidOperation, TypeError):
                valid = False
            if not receipt or not valid:
                payment.status = "outcome_unknown"
                payment.result_description = "Successful callback metadata missing or amount mismatch; reconcile provider transaction."
                payment.save(update_fields=["status", "result_code", "result_description", "callback_data", "updated_at"])
                return Response({"ResultCode": 0, "ResultDesc": "Discrepancy recorded for reconciliation."})
            # The callback is only a hint. A separate authenticated Daraja query must confirm success.
            try:
                verified, verification_data = verify_stk_transaction(payment, callback)
            except Exception as exc:
                payment.status = "outcome_unknown"
                payment.result_description = f"Provider verification unavailable: {str(exc)[:500]}"
                payment.save(update_fields=["status", "result_code", "result_description", "callback_data", "updated_at"])
                return Response({"ResultCode": 0, "ResultDesc": "Reconciliation required."})
            if not verified:
                payment.status = "outcome_unknown"
                payment.result_description = "Provider status query did not verify successful payment."
                payment.save(update_fields=["status", "result_code", "result_description", "updated_at"])
                return Response({"ResultCode": 0, "ResultDesc": "Reconciliation required."})
            if MpesaPayment.objects.filter(mpesa_receipt_number=receipt).exclude(pk=payment.pk).exists():
                payment.status = "outcome_unknown"
                payment.result_description = "Receipt number is already attached to another payment."
                payment.save(update_fields=["status", "result_code", "result_description", "updated_at"])
                return Response({"ResultCode": 0, "ResultDesc": "Receipt discrepancy recorded."})
            try:
                with transaction.atomic():
                    payment.mpesa_receipt_number = receipt
                    payment.status = "completed"
                    payment.result_description = str(verification_data)[:2000]
                    payment.save(update_fields=["status", "result_code", "result_description", "mpesa_receipt_number", "callback_data", "updated_at"])
                    add_credits(payment.user, payment.amount, transaction_type="topup",
                                description=f"M-Pesa top-up {receipt}", idempotency_key=f"topup:payment:{payment.pk}")
            except IntegrityError:
                payment.refresh_from_db()
                payment.status = "outcome_unknown"
                payment.result_description = "Provider receipt conflicts with another recorded payment."
                payment.save(update_fields=["status", "result_description", "updated_at"])
                return Response({"ResultCode": 0, "ResultDesc": "Receipt discrepancy recorded."})
    except MpesaPayment.DoesNotExist:
        return Response({"ResultCode": 1, "ResultDesc": "Payment not found."}, status=404)
    return Response({"ResultCode": 0, "ResultDesc": "Callback processed."})


def _result_parameters(result):
    params = result.get("ResultParameters", {}).get("ResultParameter", [])
    return {item.get("Key"): item.get("Value") for item in params if isinstance(item, dict)}


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def b2c_result_callback(request):
    if request.query_params.get("reconciliation") == "1":
        token = str(request.query_params.get("callback_token", ""))
        result = request.data.get("Result", {})
        try:
            with transaction.atomic():
                withdrawal = CreatorWithdrawal.objects.select_for_update().get(reconciliation_token=token)
                if not secrets.compare_digest(withdrawal.reconciliation_token or "", token):
                    return Response({"ResultCode": 1}, status=403)
                if withdrawal.status in {"paid", "refunded", "payout_failed_verified"}:
                    return Response({"ResultCode": 0})
                if result.get("OriginalConversationID") != withdrawal.originator_conversation_id or result.get("ResultType") != 0:
                    withdrawal.callback_discrepancy = "Status response did not correlate to the original transaction."
                    withdrawal.save(update_fields=["callback_discrepancy", "updated_at"])
                    return Response({"ResultCode": 0})
                params = _result_parameters(result)
                code = result.get("ResultCode")
                if str(code) == "0":
                    amount = Decimal(str(params.get("TransactionAmount")))
                    recipient = params.get("ReceiverPartyPublicName") or params.get("ReceiverParty")
                    digits = "".join(ch for ch in str(recipient or "") if ch.isdigit())
                    if (not amount.is_finite() or amount != validate_money(withdrawal.amount)
                            or normalize_mpesa_phone(withdrawal.phone_number) not in digits
                            or not params.get("TransactionReceipt")):
                        withdrawal.callback_discrepancy = "Status response lacks matching amount, recipient, or receipt."
                        withdrawal.save(update_fields=["callback_discrepancy", "updated_at"])
                        return Response({"ResultCode": 0})
                    try:
                        with transaction.atomic():
                            withdrawal.status = "paid"
                            withdrawal.payout_status = "paid"
                            withdrawal.result_code = "0"
                            withdrawal.mpesa_receipt_number = params["TransactionReceipt"]
                            withdrawal.provider_result_data = request.data
                            withdrawal.reconciliation_token = None
                            withdrawal.save(update_fields=["status", "payout_status", "result_code", "mpesa_receipt_number",
                                                           "provider_result_data", "reconciliation_token", "updated_at"])
                    except IntegrityError:
                        withdrawal.refresh_from_db()
                        withdrawal.callback_discrepancy = "Provider receipt is already attached to another withdrawal."
                        withdrawal.reconciliation_token = None
                        withdrawal.save(update_fields=["callback_discrepancy", "reconciliation_token", "updated_at"])
                        return Response({"ResultCode": 0, "ResultDesc": "Receipt discrepancy recorded for reconciliation."})
                elif code is not None:
                    withdrawal.reconciliation_token = None
                    withdrawal.save(update_fields=["reconciliation_token", "updated_at"])
                    record_provider_failure(withdrawal, code, result.get("ResultDesc", ""), request.data)
                return Response({"ResultCode": 0})
        except CreatorWithdrawal.DoesNotExist:
            return Response({"ResultCode": 1}, status=404)
        except (ValueError, InvalidOperation, TypeError):
            return Response({"ResultCode": 0})
    result = request.data.get("Result", {})
    originator = result.get("OriginatorConversationID")
    if not originator:
        return Response({"ResultCode": 1}, status=400)
    try:
        with transaction.atomic():
            withdrawal = CreatorWithdrawal.objects.select_for_update().get(originator_conversation_id=originator)
            if not withdrawal.callback_token or not secrets.compare_digest(
                str(request.query_params.get("callback_token", "")), withdrawal.callback_token
            ):
                return Response({"ResultCode": 1}, status=403)
            if withdrawal.originator_conversation_id != originator:
                return Response({"ResultCode": 1}, status=400)
            if withdrawal.status in {"paid", "refunded", "payout_failed_verified", "completed", "cancelled", "failed"}:
                # Legacy terminals and all new terminals are immutable here.
                return Response({"ResultCode": 0})
            allowed = {"submitting", "provider_pending", "outcome_unknown", "processing"}
            if withdrawal.status not in allowed:
                withdrawal.callback_discrepancy = f"Callback received in state {withdrawal.status}."
                withdrawal.save(update_fields=["callback_discrepancy", "conversation_id", "updated_at"])
                return Response({"ResultCode": 0})
            # Initial B2C callbacks only trigger reconciliation; they never settle money.
            withdrawal.provider_result_data = request.data
            withdrawal.status = "outcome_unknown"
            withdrawal.payout_status = "outcome_unknown"
            withdrawal.result_description = "Callback received; independent transaction-status reconciliation required."
            withdrawal.save(update_fields=["status", "payout_status", "provider_result_data", "result_description", "updated_at"])
            return Response({"ResultCode": 0, "ResultDesc": "Reconciliation required."})
    except CreatorWithdrawal.DoesNotExist:
        return Response({"ResultCode": 1}, status=404)
    except (ValueError, InvalidOperation):
        # Bad optional callback fields are discrepancies; never refund on parse failure.
        return Response({"ResultCode": 0})
    return Response({"ResultCode": 0})


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def b2c_timeout_callback(request):
    result = request.data.get("Result", request.data)
    originator = result.get("OriginatorConversationID")
    if not originator:
        return Response({"ResultCode": 1}, status=400)
    try:
        with transaction.atomic():
            withdrawal = CreatorWithdrawal.objects.select_for_update().get(originator_conversation_id=originator)
            if not withdrawal.callback_token or not secrets.compare_digest(
                str(request.query_params.get("callback_token", "")), withdrawal.callback_token
            ):
                return Response({"ResultCode": 1}, status=403)
            if withdrawal.status in {"submitting", "provider_pending"}:
                withdrawal.status = "outcome_unknown"
                withdrawal.payout_status = "outcome_unknown"
                withdrawal.result_description = str(result.get("ResultDesc", "Provider timeout; reconciliation required."))
                withdrawal.provider_result_data = request.data
                withdrawal.save(update_fields=["status", "payout_status", "result_description", "provider_result_data", "updated_at"])
    except CreatorWithdrawal.DoesNotExist:
        return Response({"ResultCode": 1}, status=404)
    return Response({"ResultCode": 0})
