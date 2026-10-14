from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from content.models import Content
from .models import GuestContentAccess, MpesaPayment, SharedContentShare
from .services import settle_mpesa_payment


@override_settings(MPESA_CALLBACK_URL="https://api.example.test/api/payments/mpesa/callback/", PUBLIC_WEB_URL="https://paidlinkweb.onrender.com")
class GuestShareFeatureTests(TestCase):
    def setUp(self):
        self.creator = User.objects.create_user("share-creator", password="Strong-Password-123!")
        self.creator.profile.role = "creator"
        self.creator.profile.save()
        self.client = APIClient()
        self.content = Content.objects.create(creator=self.creator, title="Shared PDF", description="Test", content_type="pdf", price_kes=Decimal("100"), is_published=True)

    def create_share(self, body=None):
        self.client.force_authenticate(self.creator)
        with patch("payments.share_views.initiate_stk_push", return_value={"ResponseCode": "0", "CheckoutRequestID": "guest-checkout", "MerchantRequestID": "guest-merchant"}):
            response = self.client.post("/api/payments/shares/", body or {"content_id": self.content.pk}, format="json")
        self.assertEqual(response.status_code, 201)
        return response.data

    def test_default_expiry_limit_and_public_view_has_no_file_url(self):
        data = self.create_share()
        share = SharedContentShare.objects.get(pk=data["id"])
        self.assertEqual(share.max_uses, 2)
        self.assertAlmostEqual((share.expires_at - timezone.now()).total_seconds(), 7200, delta=5)
        public = self.client.get(f"/api/payments/shared/{share.token}/")
        self.assertEqual(public.status_code, 200)
        self.assertNotIn("file_url", public.data["content"])

    def test_guest_payment_reserves_use_and_verified_payment_creates_separate_expiring_access(self):
        data = self.create_share({"content_id": self.content.pk, "expires_in_hours": 1, "access_duration_hours": 1, "max_uses": 1})
        share = SharedContentShare.objects.get(pk=data["id"])
        self.client.force_authenticate(user=None)
        response = self.client.post(f"/api/payments/shared/{share.token}/payments/", {"phone_number": "254712345678"}, format="json")
        self.assertEqual(response.status_code, 202)
        payment = MpesaPayment.objects.get(guest_share=share)
        self.assertEqual(share.__class__.objects.get(pk=share.pk).reserved_count, 1)
        settle_mpesa_payment(payment.pk, "RCP12345", {"verified": True})
        access = GuestContentAccess.objects.get(payment=payment)
        self.assertNotEqual(access.token, payment.guest_payment_token)
        self.assertEqual(share.__class__.objects.get(pk=share.pk).used_count, 1)
        status_response = self.client.get(f"/api/payments/guest-payments/{payment.guest_payment_token}/")
        self.assertEqual(status_response.data["status"], "completed")
        self.assertTrue(status_response.data["access_url"].endswith(access.token))
        capped = self.client.post(f"/api/payments/shared/{share.token}/payments/", {"phone_number": "254712345678"}, format="json")
        self.assertEqual(capped.status_code, 410)
        self.client.force_authenticate(self.creator)
        earnings = self.client.get("/api/accounts/creator/earnings/summary/")
        per_content = self.client.get("/api/accounts/creator/earnings/content/")
        self.assertEqual(earnings.data["total_sales_count"], 1)
        self.assertEqual(earnings.data["gross_earnings"], "100.00")
        self.assertEqual(per_content.data[0]["gross_sales"], "100.00")
        access.expires_at = timezone.now() - timedelta(seconds=1)
        access.save(update_fields=["expires_at"])
        self.client.force_authenticate(user=None)
        self.assertEqual(self.client.get(f"/api/payments/guest-access/{access.token}/").status_code, 410)

    def test_expired_and_revoked_links_reject_new_payment_and_access(self):
        data = self.create_share()
        share = SharedContentShare.objects.get(pk=data["id"])
        share.expires_at = timezone.now() - timedelta(seconds=1)
        share.save(update_fields=["expires_at"])
        self.client.force_authenticate(user=None)
        self.assertEqual(self.client.post(f"/api/payments/shared/{share.token}/payments/", {"phone_number": "254712345678"}, format="json").status_code, 410)
        share.expires_at = timezone.now() + timedelta(hours=1)
        share.status = "revoked"
        share.save(update_fields=["expires_at", "status"])
        self.assertEqual(self.client.get(f"/api/payments/shared/{share.token}/").data["status"], "REVOKED")
