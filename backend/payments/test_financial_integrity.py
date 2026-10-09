from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
import os
from unittest.mock import Mock, patch
import secrets
from urllib.parse import parse_qs, urlsplit

import requests
from django.contrib.auth.models import User
from django.db import close_old_connections
from django.test import SimpleTestCase, TransactionTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from accounts.models import CreditTransaction, UserProfile
from accounts.services import add_credits, adjust_credits, deduct_credits, validate_b2c_amount, validate_money, validate_mpesa_amount
from content.models import Content
from payments.models import CreatorWithdrawal, MpesaPayment
from payments.services import (
    refund_failed_withdrawal,
    send_b2c_payment_request,
    request_b2c_status_reconciliation,
    verify_stk_transaction,
)
from payments.views import (
    AdminCancelWithdrawalView,
    AdminApproveWithdrawalView,
    AdminReconcilePaymentView,
    AdminReconcileWithdrawalView,
    CreatorWithdrawalRequestView,
    b2c_result_callback,
    mpesa_callback,
)
from purchases.services import purchase_content


class FinancialIntegrityTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.factory = APIRequestFactory()
        self.creator = User.objects.create_user("creator", password="test")
        self.admin = User.objects.create_user("admin", password="test")
        self.creator.profile.role = "creator"
        self.creator.profile.save()
        self.admin.profile.role = "admin"
        self.admin.profile.save()

    def withdrawal(self, status="pending", amount="50"):
        return CreatorWithdrawal.objects.create(
            creator=self.creator, phone_number="254712345678",
            amount=Decimal(amount), status=status,
        )

    def approve(self, wid):
        request = self.factory.post(f"/withdrawals/{wid}/approve/")
        force_authenticate(request, self.admin)
        return AdminApproveWithdrawalView.as_view()(request, withdrawal_id=wid)

    def b2c_callback(self, withdrawal, result_code, **params):
        result = {
            "OriginatorConversationID": withdrawal.originator_conversation_id,
            "ConversationID": withdrawal.conversation_id,
            "ResultCode": result_code,
            "ResultDesc": "provider result",
        }
        if params:
            result["ResultParameters"] = {"ResultParameter": [
                {"Key": key, "Value": value} for key, value in params.items()
            ]}
        request = self.factory.post("/mpesa/b2c/result/?callback_token=" + withdrawal.callback_token, {"Result": result}, format="json")
        return b2c_result_callback(request)

    def b2c_status_callback(self, withdrawal, result_code, **params):
        result = {"OriginalConversationID": withdrawal.originator_conversation_id,
                  "ResultType": 0, "ResultCode": result_code, "ResultDesc": "provider status"}
        result["ResultParameters"] = {"ResultParameter": [{"Key": k, "Value": v} for k, v in params.items()]}
        request = self.factory.post("/mpesa/b2c/result/?reconciliation=1&callback_token=" + withdrawal.reconciliation_token,
                                    {"Result": result}, format="json")
        return b2c_result_callback(request)

    def callback_ready_withdrawal(self, amount="50"):
        withdrawal = self.withdrawal("provider_pending", amount)
        withdrawal.originator_conversation_id = f"origin-{withdrawal.pk}"
        withdrawal.conversation_id = f"conversation-{withdrawal.pk}"
        withdrawal.callback_token = secrets.token_hex(32)
        withdrawal.save()
        return withdrawal

    def test_money_validation_rejects_invalid_and_fractional(self):
        for value in ("0", "-1", "NaN", "Infinity", "1.001", "10000000000"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_money(value)
        self.assertEqual(validate_money("125"), Decimal("125"))
        for validator in (validate_mpesa_amount, validate_b2c_amount):
            with self.assertRaises(ValueError):
                validator("250001")
        with self.assertRaises(ValueError):
            validate_b2c_amount("9")

    def test_double_withdrawal_approval_debits_once(self):
        profile = self.creator.profile
        profile.credits = Decimal("100")
        profile.save()
        w = self.withdrawal()
        self.assertEqual(self.approve(w.pk).status_code, 200)
        self.assertEqual(self.approve(w.pk).status_code, 400)
        profile.refresh_from_db()
        self.assertEqual(profile.credits, Decimal("50"))
        self.assertEqual(CreditTransaction.objects.filter(idempotency_key=f"withdrawal:{w.pk}:reserve").count(), 1)

    def test_cancellation_releases_reserved_balance_once_before_submission(self):
        self.creator.profile.credits = Decimal("100")
        self.creator.profile.save()
        w = self.withdrawal()
        self.approve(w.pk)
        request = self.factory.post(f"/withdrawals/{w.pk}/cancel/")
        force_authenticate(request, self.admin)
        self.assertEqual(AdminCancelWithdrawalView.as_view()(request, withdrawal_id=w.pk).status_code, 200)
        request = self.factory.post(f"/withdrawals/{w.pk}/cancel/")
        force_authenticate(request, self.admin)
        self.assertEqual(AdminCancelWithdrawalView.as_view()(request, withdrawal_id=w.pk).status_code, 400)
        self.creator.profile.refresh_from_db()
        self.assertEqual(self.creator.profile.credits, Decimal("100"))
        self.assertEqual(CreditTransaction.objects.filter(idempotency_key=f"withdrawal:{w.pk}:release").count(), 1)

    def test_concurrent_withdrawal_approval_debits_once(self):
        self.creator.profile.credits = Decimal("50")
        self.creator.profile.save()
        w = self.withdrawal()

        def run(_):
            close_old_connections()
            try:
                return self.approve(w.pk).status_code
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(run, range(2)))
        self.creator.profile.refresh_from_db()
        self.assertEqual(self.creator.profile.credits, Decimal("0"))
        self.assertEqual(CreditTransaction.objects.filter(idempotency_key=f"withdrawal:{w.pk}:reserve").count(), 1)
        self.assertIn(200, results)

    def test_concurrent_withdrawal_requests_respect_pending_reservations(self):
        self.creator.profile.credits = Decimal("50")
        self.creator.profile.save()

        def run(_):
            close_old_connections()
            try:
                request = self.factory.post("/withdrawals/request/", {"amount": "40", "phone_number": "0712345678"}, format="json")
                force_authenticate(request, self.creator)
                return CreatorWithdrawalRequestView.as_view()(request).status_code
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(run, range(2)))
        self.assertEqual(results.count(201), 1)
        self.assertEqual(results.count(400), 1)

    def test_double_and_concurrent_refund_are_idempotent(self):
        w = self.withdrawal("payout_failed_verified")
        w.payout_status = "payout_failed_verified"
        from django.utils import timezone
        w.provider_failure_verified_at = timezone.now()
        w.save()
        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(lambda _: refund_failed_withdrawal(w.pk), range(2)))
        self.assertEqual(CreditTransaction.objects.filter(idempotency_key=f"withdrawal:{w.pk}:refund").count(), 1)
        w.refresh_from_db()
        self.assertEqual(w.status, "refunded")
        self.assertEqual(w.payout_status, "payout_failed_verified")
        self.creator.profile.refresh_from_db()
        self.assertEqual(self.creator.profile.credits, Decimal("50"))

    def test_b2c_duplicate_success_is_idempotent(self):
        w = self.callback_ready_withdrawal()
        payload = {"TransactionAmount": 50, "ReceiverPartyPublicName": "254712345678 - Creator", "TransactionReceipt": "RCP1"}
        self.b2c_callback(w, 0, **payload)
        self.b2c_callback(w, 0, **payload)
        w.refresh_from_db()
        self.assertEqual(w.status, "outcome_unknown")
        w.reconciliation_token = secrets.token_hex(32)
        w.save(update_fields=["reconciliation_token"])
        self.b2c_status_callback(w, 0, **payload)
        self.b2c_status_callback(w, 0, **payload)
        w.refresh_from_db()
        self.assertEqual(w.status, "paid")
        self.assertEqual(self.creator.profile.credits, Decimal("0"))

    def test_b2c_amount_and_recipient_mismatches_do_not_mutate_balance(self):
        w = self.callback_ready_withdrawal()
        self.b2c_callback(w, 0, TransactionAmount=49,
                          ReceiverPartyPublicName="254712345678 - Creator")
        w.refresh_from_db()
        self.assertEqual(w.status, "outcome_unknown")
        w2 = self.callback_ready_withdrawal()
        self.b2c_callback(w2, 0, TransactionAmount=50,
                          ReceiverPartyPublicName="254700000000 - Other")
        w2.refresh_from_db()
        self.assertEqual(w2.status, "outcome_unknown")
        self.assertEqual(self.creator.profile.credits, Decimal("0"))

    def test_b2c_duplicate_failure_refunds_once(self):
        self.creator.profile.credits = Decimal("0")
        self.creator.profile.save()
        w = self.callback_ready_withdrawal()
        self.b2c_callback(w, 1)
        self.b2c_callback(w, 1)
        w.refresh_from_db()
        self.assertEqual(w.status, "outcome_unknown")
        self.assertEqual(self.creator.profile.credits, Decimal("0"))
        w.reconciliation_token = secrets.token_hex(32)
        w.save(update_fields=["reconciliation_token"])
        self.b2c_status_callback(w, 1)
        w.refresh_from_db()
        self.assertEqual(w.status, "refunded")
        self.assertEqual(w.payout_status, "payout_failed_verified")
        self.creator.profile.refresh_from_db()
        self.assertEqual(self.creator.profile.credits, Decimal("50"))
        self.assertEqual(CreditTransaction.objects.filter(idempotency_key=f"withdrawal:{w.pk}:refund").count(), 1)

    def test_forged_b2c_failure_and_success_callbacks_never_settle(self):
        self.creator.profile.credits = Decimal("0")
        self.creator.profile.save()
        w = self.callback_ready_withdrawal()
        payload = {"OriginatorConversationID": w.originator_conversation_id,
                   "ResultCode": 1, "ResultDesc": "forged"}
        request = self.factory.post("/mpesa/b2c/result/?callback_token=wrong", {"Result": payload}, format="json")
        self.assertEqual(b2c_result_callback(request).status_code, 403)
        self.b2c_callback(w, 1)
        w.refresh_from_db()
        self.assertEqual(w.status, "outcome_unknown")
        self.assertEqual(self.creator.profile.credits, Decimal("0"))
        w.reconciliation_token = secrets.token_hex(32)
        w.save(update_fields=["reconciliation_token"])
        self.b2c_status_callback(w, 0)
        w.refresh_from_db()
        self.assertEqual(w.status, "outcome_unknown")
        self.assertEqual(self.creator.profile.credits, Decimal("0"))

    def test_b2c_verified_status_requires_amount_and_recipient_and_matches_them(self):
        for fields in (
            {"TransactionAmount": 50, "TransactionReceipt": "R1"},
            {"TransactionAmount": 49, "ReceiverPartyPublicName": "254712345678 - Creator", "TransactionReceipt": "R2"},
            {"TransactionAmount": 50, "ReceiverPartyPublicName": "254700000000 - Other", "TransactionReceipt": "R3"},
        ):
            w = self.callback_ready_withdrawal()
            w.reconciliation_token = secrets.token_hex(32)
            w.save(update_fields=["reconciliation_token"])
            self.b2c_status_callback(w, 0, **fields)
            w.refresh_from_db()
            self.assertEqual(w.status, "provider_pending")
            self.assertEqual(self.creator.profile.credits, Decimal("0"))

    def test_b2c_reconciliation_rejects_wrong_original_conversation_and_result_type(self):
        for changes in ({"OriginalConversationID": "wrong"}, {"ResultType": 1}):
            w = self.callback_ready_withdrawal()
            w.reconciliation_token = secrets.token_hex(32)
            w.save(update_fields=["reconciliation_token"])
            result = {"OriginalConversationID": w.originator_conversation_id, "ResultType": 0,
                      "ResultCode": 0, "ResultParameters": {"ResultParameter": [
                          {"Key": "TransactionAmount", "Value": 50},
                          {"Key": "ReceiverPartyPublicName", "Value": "254712345678 - Creator"},
                          {"Key": "TransactionReceipt", "Value": "R-CORR"},
                      ]}}
            result.update(changes)
            request = self.factory.post(
                "/mpesa/b2c/result/?reconciliation=1&callback_token=" + w.reconciliation_token,
                {"Result": result}, format="json",
            )
            b2c_result_callback(request)
            w.refresh_from_db()
            self.assertEqual(w.status, "provider_pending")
            self.assertTrue(w.callback_discrepancy)

    def test_b2c_duplicate_paid_receipt_becomes_discrepancy_not_integrity_error(self):
        existing = self.callback_ready_withdrawal()
        existing.status = "paid"
        existing.payout_status = "paid"
        existing.mpesa_receipt_number = "SHARED-RECEIPT"
        existing.save(update_fields=["status", "payout_status", "mpesa_receipt_number"])
        candidate = self.callback_ready_withdrawal()
        candidate.reconciliation_token = secrets.token_hex(32)
        candidate.save(update_fields=["reconciliation_token"])
        response = self.b2c_status_callback(
            candidate, 0, TransactionAmount=50,
            ReceiverPartyPublicName="254712345678 - Creator", TransactionReceipt="SHARED-RECEIPT",
        )
        candidate.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(candidate.status, "provider_pending")
        self.assertIn("receipt", candidate.callback_discrepancy.lower())
        self.assertIsNone(candidate.mpesa_receipt_number)
        self.assertEqual(CreditTransaction.objects.filter(idempotency_key=f"withdrawal:{candidate.pk}:refund").count(), 0)

    def test_reconciliation_endpoints_reject_non_admins(self):
        withdrawal = self.withdrawal("outcome_unknown")
        payment = MpesaPayment.objects.create(user=self.creator, phone_number="254712345678",
                                              amount=Decimal("50"), checkout_request_id="auth-checkout")
        request = self.factory.post("/withdrawals/1/reconcile/")
        force_authenticate(request, self.creator)
        with patch("payments.views.request_b2c_status_reconciliation") as reconcile:
            response = AdminReconcileWithdrawalView.as_view()(request, withdrawal_id=withdrawal.pk)
        self.assertEqual(response.status_code, 403)
        reconcile.assert_not_called()
        request = self.factory.post(f"/mpesa/payments/{payment.pk}/reconcile/")
        force_authenticate(request, self.creator)
        with patch("payments.views.verify_stk_transaction") as verify:
            response = AdminReconcilePaymentView.as_view()(request, payment_id=payment.pk)
        self.assertEqual(response.status_code, 403)
        verify.assert_not_called()

    @patch("payments.services.requests.post")
    @patch("payments.services.get_mpesa_access_token", return_value="mock-token")
    def test_stk_provider_query_uses_selected_host_and_checkout_id(self, _token, post):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"ResultCode": "0"}
        post.return_value = response
        payment = MpesaPayment.objects.create(user=self.creator, phone_number="254712345678",
                                              amount=Decimal("50"), checkout_request_id="query-checkout")
        from django.test import override_settings
        with override_settings(MPESA_BASE_URL="https://sandbox.example.test", MPESA_SHORTCODE="123", MPESA_PASSKEY="key"):
            verified, data = verify_stk_transaction(payment, {})
        self.assertTrue(verified)
        self.assertEqual(data["ResultCode"], "0")
        self.assertEqual(post.call_args.args[0], "https://sandbox.example.test/mpesa/stkpushquery/v1/query")
        self.assertEqual(post.call_args.kwargs["json"]["CheckoutRequestID"], "query-checkout")

    @patch("payments.services.requests.post")
    @patch("payments.services.get_mpesa_access_token", return_value="mock-token")
    def test_b2c_reconciliation_query_is_correlated_and_uses_separate_callback_token(self, _token, post):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"ResponseCode": "0", "ConversationID": "query-conversation"}
        post.return_value = response
        withdrawal = self.callback_ready_withdrawal()
        from django.test import override_settings
        with override_settings(
            MPESA_BASE_URL="https://sandbox.example.test",
            MPESA_B2C_INITIATOR_NAME="test-initiator", MPESA_B2C_SECURITY_CREDENTIAL="credential",
            MPESA_B2C_SHORTCODE="123", MPESA_B2C_RECONCILIATION_URL="https://app.example.test/api/payments/mpesa/b2c/result/",
            MPESA_B2C_TIMEOUT_URL="https://app.example.test/api/payments/mpesa/b2c/timeout/",
        ):
            request_b2c_status_reconciliation(withdrawal)
        self.assertEqual(post.call_args.args[0], "https://sandbox.example.test/mpesa/transactionstatus/v1/query")
        payload = post.call_args.kwargs["json"]
        self.assertEqual(payload["OriginalConversationID"], withdrawal.originator_conversation_id)
        callback = urlsplit(payload["ResultURL"])
        callback_query = parse_qs(callback.query)
        self.assertEqual(callback_query["reconciliation"], ["1"])
        self.assertEqual(callback_query["callback_token"], [withdrawal.reconciliation_token])
        self.assertNotEqual(withdrawal.reconciliation_token, withdrawal.callback_token)

    def test_successful_payout_is_not_reversed_by_late_failure(self):
        w = self.callback_ready_withdrawal()
        w.reconciliation_token = secrets.token_hex(32)
        w.save(update_fields=["reconciliation_token"])
        self.b2c_status_callback(w, 0, TransactionAmount=50,
                                 ReceiverPartyPublicName="254712345678 - Creator", TransactionReceipt="RCP-LATE")
        w.refresh_from_db()
        self.assertEqual(w.status, "paid")
        self.b2c_callback(w, 1)
        w.refresh_from_db()
        self.assertEqual(w.status, "paid")
        self.assertEqual(CreditTransaction.objects.filter(idempotency_key=f"withdrawal:{w.pk}:refund").count(), 0)

    def test_concurrent_conflicting_b2c_callbacks_have_one_terminal_result(self):
        self.creator.profile.credits = Decimal("0")
        self.creator.profile.save()
        w = self.callback_ready_withdrawal()

        def run(code):
            close_old_connections()
            try:
                return self.b2c_callback(w, code).status_code
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(run, (0, 1)))
        w.refresh_from_db()
        self.creator.profile.refresh_from_db()
        self.assertEqual(w.status, "outcome_unknown")
        self.assertEqual(self.creator.profile.credits, Decimal("0"))
        self.assertEqual(CreditTransaction.objects.filter(idempotency_key=f"withdrawal:{w.pk}:refund").count(), int(w.status == "refunded"))

    def test_late_conflicting_b2c_callbacks_do_not_reverse_terminal_state(self):
        w = self.callback_ready_withdrawal()
        self.b2c_callback(w, 0)
        w.reconciliation_token = secrets.token_hex(32)
        w.save(update_fields=["reconciliation_token"])
        self.b2c_status_callback(w, 0, TransactionAmount=50,
                                 ReceiverPartyPublicName="254712345678 - Creator", TransactionReceipt="RCP2")
        self.b2c_callback(w, 1)
        w.refresh_from_db()
        self.assertEqual(w.status, "paid")
        self.assertEqual(self.creator.profile.credits, Decimal("0"))

        w2 = self.callback_ready_withdrawal()
        self.creator.profile.credits = Decimal("0")
        self.creator.profile.save()
        self.b2c_callback(w2, 1)
        w2.reconciliation_token = secrets.token_hex(32)
        w2.save(update_fields=["reconciliation_token"])
        self.b2c_status_callback(w2, 1)
        self.b2c_callback(w2, 0)
        w2.refresh_from_db()
        self.assertEqual(w2.status, "refunded")
        self.creator.profile.refresh_from_db()
        self.assertEqual(self.creator.profile.credits, Decimal("50"))

    @patch("payments.services.requests.post")
    @patch("payments.services.get_mpesa_access_token", return_value="mock-token")
    def test_timeout_enters_unknown_without_retry_or_refund(self, _token, post):
        from django.test import override_settings
        w = self.withdrawal("approved_reserved")
        post.side_effect = requests.Timeout("mock timeout")
        with override_settings(MPESA_B2C_INITIATOR_NAME="name", MPESA_B2C_SECURITY_CREDENTIAL="credential",
                              MPESA_B2C_SHORTCODE="123", MPESA_B2C_RESULT_URL="https://example.test/result",
                              MPESA_B2C_TIMEOUT_URL="https://example.test/timeout"):
            with self.assertRaises(requests.Timeout):
                send_b2c_payment_request(w.pk)
            w.refresh_from_db()
            self.assertEqual(w.status, "outcome_unknown")
            with self.assertRaises(ValueError):
                send_b2c_payment_request(w.pk)
        self.assertEqual(post.call_count, 1)
        self.assertEqual(CreditTransaction.objects.filter(idempotency_key=f"withdrawal:{w.pk}:refund").count(), 0)

    @patch("payments.services.requests.post", side_effect=requests.ConnectionError("mock connection loss"))
    @patch("payments.services.get_mpesa_access_token", return_value="mock-token")
    def test_connection_loss_enters_unknown_without_refund(self, _token, _post):
        from django.test import override_settings
        w = self.withdrawal("approved_reserved")
        with override_settings(MPESA_B2C_INITIATOR_NAME="name", MPESA_B2C_SECURITY_CREDENTIAL="credential",
                              MPESA_B2C_SHORTCODE="123", MPESA_B2C_RESULT_URL="https://example.test/result",
                              MPESA_B2C_TIMEOUT_URL="https://example.test/timeout"):
            with self.assertRaises(requests.ConnectionError):
                send_b2c_payment_request(w.pk)
        w.refresh_from_db()
        self.assertEqual(w.status, "outcome_unknown")
        self.assertEqual(CreditTransaction.objects.filter(idempotency_key=f"withdrawal:{w.pk}:refund").count(), 0)

    @patch("payments.services.requests.post")
    @patch("payments.services.get_mpesa_access_token", return_value="mock-token")
    def test_duplicate_b2c_submission_is_rejected_and_response_id_saved(self, _token, post):
        from django.test import override_settings
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"ConversationID": "conv-123", "ResponseCode": "0"}
        post.return_value = response
        w = self.withdrawal("approved_reserved")
        with override_settings(MPESA_B2C_INITIATOR_NAME="name", MPESA_B2C_SECURITY_CREDENTIAL="credential",
                              MPESA_B2C_SHORTCODE="123", MPESA_B2C_RESULT_URL="https://example.test/result",
                              MPESA_B2C_TIMEOUT_URL="https://example.test/timeout"):
            send_b2c_payment_request(w.pk)
            w.refresh_from_db()
            self.assertEqual(w.conversation_id, "conv-123")
            self.assertEqual(w.status, "provider_pending")
            with self.assertRaises(ValueError):
                send_b2c_payment_request(w.pk)
        self.assertEqual(post.call_count, 1)

    def test_fractional_zero_negative_and_invalid_api_amounts_rejected(self):
        for amount in ("0", "-5", "1.25", "NaN", "Infinity", "250001"):
            request = self.factory.post("/mpesa/initiate/", {"amount": amount, "phone_number": "0712345678"}, format="json")
            force_authenticate(request, self.creator)
            response = __import__("payments.views", fromlist=["InitiateMpesaPaymentView"]).InitiateMpesaPaymentView.as_view()(request)
            self.assertEqual(response.status_code, 400, amount)

    def test_stk_duplicate_success_credits_once(self):
        payment = MpesaPayment.objects.create(user=self.creator, phone_number="254712345678", amount=Decimal("50"), checkout_request_id="checkout-1", callback_token=secrets.token_hex(32))
        body = {"Body": {"stkCallback": {"CheckoutRequestID": "checkout-1", "ResultCode": 0,
                "ResultDesc": "Success", "CallbackMetadata": {"Item": [
                    {"Name": "Amount", "Value": 50}, {"Name": "MpesaReceiptNumber", "Value": "STK1"}]}}}}
        with patch("payments.views.verify_stk_transaction", return_value=(True, {"ResultCode": "0"})):
            for _ in range(2):
                request = self.factory.post("/mpesa/callback/?callback_token=" + payment.callback_token, body, format="json")
                mpesa_callback(request)
        self.creator.profile.refresh_from_db()
        self.assertEqual(self.creator.profile.credits, Decimal("50"))
        self.assertEqual(CreditTransaction.objects.filter(idempotency_key=f"topup:payment:{payment.pk}").count(), 1)

    def test_stk_amount_mismatch_is_unknown_without_credit(self):
        payment = MpesaPayment.objects.create(user=self.creator, phone_number="254712345678", amount=Decimal("50"), checkout_request_id="checkout-2", callback_token=secrets.token_hex(32))
        body = {"Body": {"stkCallback": {"CheckoutRequestID": "checkout-2", "ResultCode": 0,
                "CallbackMetadata": {"Item": [{"Name": "Amount", "Value": 49}, {"Name": "MpesaReceiptNumber", "Value": "STK2"}]}}}}
        mpesa_callback(self.factory.post("/mpesa/callback/?callback_token=" + payment.callback_token, body, format="json"))
        payment.refresh_from_db()
        self.assertEqual(payment.status, "outcome_unknown")
        self.assertEqual(self.creator.profile.credits, Decimal("0"))

    def test_known_checkout_id_cannot_forge_stk_credit_and_missing_verification_stays_unknown(self):
        payment = MpesaPayment.objects.create(user=self.creator, phone_number="254712345678", amount=Decimal("50"),
                                              checkout_request_id="known-checkout", callback_token=secrets.token_hex(32))
        body = {"Body": {"stkCallback": {"CheckoutRequestID": payment.checkout_request_id, "ResultCode": 0,
                "CallbackMetadata": {"Item": [{"Name": "Amount", "Value": 50},
                                                {"Name": "MpesaReceiptNumber", "Value": "FORGED"}]}}}}
        forged = self.factory.post("/mpesa/callback/?callback_token=wrong", body, format="json")
        self.assertEqual(mpesa_callback(forged).status_code, 403)
        with patch("payments.views.verify_stk_transaction", side_effect=TimeoutError("unavailable")):
            request = self.factory.post("/mpesa/callback/?callback_token=" + payment.callback_token, body, format="json")
            mpesa_callback(request)
        payment.refresh_from_db()
        self.creator.profile.refresh_from_db()
        self.assertEqual(payment.status, "outcome_unknown")
        self.assertEqual(self.creator.profile.credits, Decimal("0"))

    def test_stk_receipt_reuse_is_unknown_without_duplicate_credit(self):
        first = MpesaPayment.objects.create(user=self.creator, phone_number="254712345678", amount=Decimal("50"),
                                            checkout_request_id="receipt-1", callback_token=secrets.token_hex(32),
                                            mpesa_receipt_number="DUPLICATE")
        second = MpesaPayment.objects.create(user=self.creator, phone_number="254712345678", amount=Decimal("50"),
                                             checkout_request_id="receipt-2", callback_token=secrets.token_hex(32))
        body = {"Body": {"stkCallback": {"CheckoutRequestID": second.checkout_request_id, "ResultCode": 0,
                "CallbackMetadata": {"Item": [{"Name": "Amount", "Value": 50},
                                                {"Name": "MpesaReceiptNumber", "Value": "DUPLICATE"}]}}}}
        with patch("payments.views.verify_stk_transaction", return_value=(True, {"ResultCode": "0"})):
            mpesa_callback(self.factory.post("/mpesa/callback/?callback_token=" + second.callback_token, body, format="json"))
        second.refresh_from_db()
        self.assertEqual(second.status, "outcome_unknown")
        self.assertIsNone(second.mpesa_receipt_number)
        self.assertEqual(CreditTransaction.objects.filter(idempotency_key=f"topup:payment:{second.pk}").count(), 0)

    def test_stk_phone_is_normalized_and_invalid_phone_rejected_before_payment_creation(self):
        from payments.views import InitiateMpesaPaymentView
        request = self.factory.post("/mpesa/initiate/", {"amount": "50", "phone_number": "0712345678"}, format="json")
        force_authenticate(request, self.creator)
        from django.test import override_settings
        with override_settings(MPESA_CALLBACK_URL="https://example.test/callback"), \
             patch("payments.views.initiate_stk_push", return_value={"ResponseCode": "0", "CheckoutRequestID": "c-valid"}):
            response = InitiateMpesaPaymentView.as_view()(request)
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(MpesaPayment.objects.get(pk=response.data["payment_id"]).phone_number, "254712345678")
        request = self.factory.post("/mpesa/initiate/", {"amount": "50", "phone_number": "not-a-phone"}, format="json")
        force_authenticate(request, self.creator)
        before = MpesaPayment.objects.count()
        self.assertEqual(InitiateMpesaPaymentView.as_view()(request).status_code, 400)
        self.assertEqual(MpesaPayment.objects.count(), before)

    def test_stk_failure_terminal_then_duplicate_is_idempotent(self):
        payment = MpesaPayment.objects.create(user=self.creator, phone_number="254712345678", amount=Decimal("50"), checkout_request_id="checkout-3", callback_token=secrets.token_hex(32))
        body = {"Body": {"stkCallback": {"CheckoutRequestID": "checkout-3", "ResultCode": 1, "ResultDesc": "Failed"}}}
        for _ in range(2):
            mpesa_callback(self.factory.post("/mpesa/callback/?callback_token=" + payment.callback_token, body, format="json"))
        payment.refresh_from_db()
        self.assertEqual(payment.status, "outcome_unknown")
        self.assertEqual(self.creator.profile.credits, Decimal("0"))

    @patch("payments.views.initiate_stk_push", side_effect=requests.Timeout("mock timeout"))
    def test_stk_uncertain_response_is_not_classified_as_definite_failure(self, _initiate):
        from payments.views import InitiateMpesaPaymentView
        request = self.factory.post("/mpesa/initiate/", {"amount": "50", "phone_number": "0712345678"}, format="json")
        force_authenticate(request, self.creator)
        response = InitiateMpesaPaymentView.as_view()(request)
        payment = MpesaPayment.objects.get(pk=response.data["payment_id"])
        self.assertEqual(response.status_code, 202)
        self.assertEqual(payment.status, "outcome_unknown")

    def test_ledger_and_balance_consistency_for_account_services(self):
        add_credits(self.creator, "100", idempotency_key="test:topup")
        deduct_credits(self.creator, "30", idempotency_key="test:purchase")
        self.creator.profile.refresh_from_db()
        total = CreditTransaction.objects.filter(user=self.creator).aggregate(total=__import__("django.db.models", fromlist=["Sum"]).Sum("amount"))["total"]
        self.assertEqual(self.creator.profile.credits, total)
        self.assertEqual(CreditTransaction.objects.filter(user=self.creator).exclude(idempotency_key__isnull=False).count(), 0)

    def test_purchase_uses_shared_locked_ledger_service(self):
        self.creator.profile.credits = Decimal("100")
        self.creator.profile.save()
        content = Content.objects.create(
            creator=self.admin, title="Lesson", description="Lesson description",
            content_type="pdf", price=Decimal("25"), is_published=True,
        )
        self.assertEqual(purchase_content(self.creator, content.pk), Decimal("75"))
        event = CreditTransaction.objects.get(transaction_type="purchase", user=self.creator)
        self.assertEqual(event.idempotency_key, f"purchase:{content.purchases.get(user=self.creator).pk}")

    def test_adjustment_requires_and_reuses_unique_ledger_key(self):
        self.assertEqual(adjust_credits(self.creator, "25", "manual correction", "adjustment:one"), Decimal("25"))
        self.assertEqual(adjust_credits(self.creator, "25", "manual correction", "adjustment:one"), Decimal("25"))
        self.creator.profile.refresh_from_db()
        self.assertEqual(self.creator.profile.credits, Decimal("25"))
        self.assertEqual(CreditTransaction.objects.filter(idempotency_key="adjustment:one").count(), 1)


class PasswordContractTests(TransactionTestCase):
    def test_stk_password_returns_password_and_timestamp(self):
        from django.test import override_settings
        from payments.services import generate_password
        with override_settings(MPESA_SHORTCODE="123", MPESA_PASSKEY="test-passkey"):
            password, timestamp = generate_password()
        self.assertEqual(len(timestamp), 14)
        self.assertTrue(password)

    def test_logging_filter_redacts_callback_bearer_tokens(self):
        import logging
        from config.settings import RedactCallbackTokenFilter
        record = logging.LogRecord("test", logging.INFO, "", 0,
                                   "request failed for /callback/?callback_token=%s&retry=1",
                                   ("sensitive-test-token",), None)
        self.assertTrue(RedactCallbackTokenFilter().filter(record))
        rendered = record.getMessage()
        self.assertNotIn("sensitive-test-token", rendered)
        self.assertIn("callback_token=[REDACTED]", rendered)


class ConfigurationContractTests(SimpleTestCase):
    def test_environment_helpers_and_mpesa_environment_selection(self):
        from config.settings import env_bool, env_csv, mpesa_base_url
        from unittest.mock import patch as env_patch

        with env_patch.dict(os.environ, {
            "PAIDLINK_TEST_BOOL": "yes",
            "PAIDLINK_TEST_LIST": "https://one.example, https://two.example,,",
        }):
            self.assertTrue(env_bool("PAIDLINK_TEST_BOOL", False))
            self.assertEqual(env_csv("PAIDLINK_TEST_LIST"), ["https://one.example", "https://two.example"])
        self.assertEqual(mpesa_base_url("sandbox"), "https://sandbox.safaricom.co.ke")
        self.assertEqual(mpesa_base_url("production"), "https://api.safaricom.co.ke")
        with self.assertRaises(ValueError):
            mpesa_base_url("unknown")
