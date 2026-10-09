import base64
import uuid
from urllib.parse import urlencode, urlsplit, urlunsplit, parse_qsl
from datetime import datetime
from decimal import Decimal

import requests
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from accounts.models import UserProfile
from accounts.services import add_credits, validate_b2c_amount, validate_money, validate_mpesa_amount
from .models import CreatorWithdrawal


def get_mpesa_access_token():
    response = requests.get(
        f"{settings.MPESA_BASE_URL}/oauth/v1/generate?grant_type=client_credentials",
        auth=(settings.MPESA_CONSUMER_KEY, settings.MPESA_CONSUMER_SECRET),
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def generate_password():
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    raw = f"{settings.MPESA_SHORTCODE}{settings.MPESA_PASSKEY}{timestamp}"
    return base64.b64encode(raw.encode()).decode(), timestamp


def callback_url_with_token(url, token, extra=None):
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query["callback_token"] = token
    if extra:
        query.update(extra)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def verify_stk_transaction(payment, callback):
    """Query Daraja before crediting; the incoming callback is only a hint."""
    token = get_mpesa_access_token()
    password, timestamp = generate_password()
    response = requests.post(
        f"{settings.MPESA_BASE_URL}/mpesa/stkpushquery/v1/query",
        json={"BusinessShortCode": settings.MPESA_SHORTCODE, "Password": password,
              "Timestamp": timestamp, "CheckoutRequestID": payment.checkout_request_id},
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    # Daraja query's ResultCode is the transaction result; ResponseCode only means query accepted.
    return isinstance(data, dict) and str(data.get("ResultCode")) == "0", data


def request_b2c_status_reconciliation(withdrawal):
    """Submit Daraja's asynchronous transaction-status query; never resubmit a payout."""
    token = get_mpesa_access_token()
    base = settings.MPESA_B2C_RECONCILIATION_URL
    if not all((settings.MPESA_B2C_INITIATOR_NAME, settings.MPESA_B2C_SECURITY_CREDENTIAL,
                settings.MPESA_B2C_SHORTCODE, base, withdrawal.originator_conversation_id)):
        raise ValueError("B2C reconciliation configuration or transaction ID is missing.")
    callback_token = uuid.uuid4().hex
    withdrawal.reconciliation_token = callback_token
    withdrawal.save(update_fields=["reconciliation_token", "updated_at"])
    response = requests.post(
        f"{settings.MPESA_BASE_URL}/mpesa/transactionstatus/v1/query",
        json={"Initiator": settings.MPESA_B2C_INITIATOR_NAME,
              "SecurityCredential": settings.MPESA_B2C_SECURITY_CREDENTIAL,
              "CommandID": "TransactionStatusQuery",
              "OriginalConversationID": withdrawal.originator_conversation_id,
              "PartyA": settings.MPESA_B2C_SHORTCODE, "IdentifierType": "4",
              "ResultURL": callback_url_with_token(base, callback_token, {"reconciliation": "1"}),
              "QueueTimeOutURL": callback_url_with_token(settings.MPESA_B2C_TIMEOUT_URL, withdrawal.callback_token),
              "Remarks": f"Reconcile withdrawal {withdrawal.pk}", "Occasion": "Payout reconciliation"},
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, timeout=30,
    )
    response.raise_for_status()
    return response.json()


def initiate_stk_push(phone_number, amount, account_reference, transaction_description, callback_url=None):
    amount = validate_mpesa_amount(amount)
    access_token = get_mpesa_access_token()
    password, timestamp = generate_password()
    response = requests.post(
        f"{settings.MPESA_BASE_URL}/mpesa/stkpush/v1/processrequest",
        json={
            "BusinessShortCode": settings.MPESA_SHORTCODE,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": int(amount),  # validate_money guarantees whole KES first.
            "PartyA": phone_number,
            "PartyB": settings.MPESA_SHORTCODE,
            "PhoneNumber": phone_number,
            "CallBackURL": callback_url or settings.MPESA_CALLBACK_URL,
            "AccountReference": account_reference,
            "TransactionDesc": transaction_description,
        },
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


@transaction.atomic
def refund_failed_withdrawal(withdrawal_id, failure_reason=""):
    withdrawal = CreatorWithdrawal.objects.select_for_update().get(pk=withdrawal_id)
    if withdrawal.status == "refunded":
        profile = UserProfile.objects.get(user=withdrawal.creator)
        return profile.credits
    if withdrawal.payout_status != "payout_failed_verified" or not withdrawal.provider_failure_verified_at:
        raise ValueError("Only a verified terminal provider failure can be refunded.")
    key = f"withdrawal:{withdrawal.pk}:refund"
    balance = add_credits(
        withdrawal.creator,
        validate_money(withdrawal.amount),
        transaction_type="refund",
        description=f"Verified B2C failure refund for withdrawal #{withdrawal.pk}",
        idempotency_key=key,
    )
    withdrawal.status = "refunded"
    withdrawal.refund_recorded_at = timezone.now()
    if failure_reason:
        withdrawal.failure_reason = failure_reason
    withdrawal.save(update_fields=["status", "refund_recorded_at", "failure_reason", "updated_at"])
    return balance


def normalize_mpesa_phone(phone_number):
    phone = str(phone_number).strip()
    if phone.startswith("+"):
        phone = phone[1:]
    if phone.startswith(("07", "01")):
        phone = "254" + phone[1:]
    if not phone.isdigit() or len(phone) != 12 or not phone.startswith(("2547", "2541")):
        raise ValueError("Phone number must be a valid Kenyan M-Pesa number.")
    return phone


@transaction.atomic
def claim_b2c_submission(withdrawal_id):
    withdrawal = CreatorWithdrawal.objects.select_for_update().get(pk=withdrawal_id)
    if withdrawal.status != "approved_reserved":
        raise ValueError("Only reserved withdrawals can be submitted.")
    if withdrawal.originator_conversation_id:
        raise ValueError("A payout submission already exists for this withdrawal.")
    phone = normalize_mpesa_phone(withdrawal.phone_number)
    amount = validate_b2c_amount(withdrawal.amount)
    if not all((settings.MPESA_B2C_INITIATOR_NAME, settings.MPESA_B2C_SECURITY_CREDENTIAL,
                settings.MPESA_B2C_SHORTCODE, settings.MPESA_B2C_RESULT_URL,
                settings.MPESA_B2C_TIMEOUT_URL)):
        raise ValueError("M-Pesa B2C configuration is incomplete.")
    originator = f"PL-{withdrawal.pk}-{uuid.uuid4().hex}"
    callback_token = uuid.uuid4().hex
    withdrawal.status = "submitting"
    withdrawal.payout_status = "submitting"
    withdrawal.originator_conversation_id = originator
    withdrawal.callback_token = callback_token
    withdrawal.save(update_fields=["status", "payout_status", "originator_conversation_id", "callback_token", "updated_at"])
    return {
        "withdrawal_id": withdrawal.pk,
        "originator_conversation_id": originator,
        "phone_number": phone,
        "amount": amount,
        "callback_token": callback_token,
    }


def _mark_submission_unknown(withdrawal_id, originator, reason):
    with transaction.atomic():
        withdrawal = CreatorWithdrawal.objects.select_for_update().get(pk=withdrawal_id)
        if withdrawal.originator_conversation_id == originator and withdrawal.status == "submitting":
            withdrawal.status = "outcome_unknown"
            withdrawal.payout_status = "outcome_unknown"
            withdrawal.failure_reason = str(reason)[:2000]
            withdrawal.save(update_fields=["status", "payout_status", "failure_reason", "updated_at"])


def send_b2c_payment_request(withdrawal_id):
    """Claim once and submit outside a DB transaction; never retry uncertain outcomes."""
    submission = claim_b2c_submission(withdrawal_id)
    try:
        token = get_mpesa_access_token()
        response = requests.post(
            f"{settings.MPESA_BASE_URL}/mpesa/b2c/v3/paymentrequest",
            json={
                "OriginatorConversationID": submission["originator_conversation_id"],
                "InitiatorName": settings.MPESA_B2C_INITIATOR_NAME,
                "SecurityCredential": settings.MPESA_B2C_SECURITY_CREDENTIAL,
                "CommandID": "BusinessPayment",
                "Amount": int(submission["amount"]),  # validated in claim_b2c_submission.
                "PartyA": int(settings.MPESA_B2C_SHORTCODE),
                "PartyB": int(submission["phone_number"]),
                "Remarks": f"Creator withdrawal #{withdrawal_id}",
                "QueueTimeOutURL": callback_url_with_token(settings.MPESA_B2C_TIMEOUT_URL, submission["callback_token"]),
                "ResultURL": callback_url_with_token(settings.MPESA_B2C_RESULT_URL, submission["callback_token"]),
                "Occasion": f"Paid Link withdrawal #{withdrawal_id}",
            },
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict) or not data.get("ConversationID"):
            raise ValueError("Provider response lacked ConversationID; outcome requires reconciliation.")
    except Exception as exc:
        _mark_submission_unknown(withdrawal_id, submission["originator_conversation_id"], exc)
        raise

    with transaction.atomic():
        withdrawal = CreatorWithdrawal.objects.select_for_update().get(pk=withdrawal_id)
        if withdrawal.originator_conversation_id != submission["originator_conversation_id"]:
            raise ValueError("Payout correlation changed during submission.")
        withdrawal.conversation_id = data["ConversationID"]
        withdrawal.provider_result_data = data
        if withdrawal.status == "submitting":
            withdrawal.status = "provider_pending"
            withdrawal.payout_status = "provider_pending"
        withdrawal.save(update_fields=["conversation_id", "provider_result_data", "status", "payout_status", "updated_at"])
    return data


def record_provider_failure(withdrawal, result_code, description, callback_data):
    withdrawal.status = "payout_failed_verified"
    withdrawal.payout_status = "payout_failed_verified"
    withdrawal.result_code = str(result_code)
    withdrawal.result_description = str(description or "")
    withdrawal.provider_failure_verified_at = timezone.now()
    withdrawal.provider_result_data = callback_data
    withdrawal.save(update_fields=[
        "status", "payout_status", "result_code", "result_description", "provider_failure_verified_at",
        "provider_result_data", "updated_at",
    ])
    return refund_failed_withdrawal(withdrawal.pk, description or "")
