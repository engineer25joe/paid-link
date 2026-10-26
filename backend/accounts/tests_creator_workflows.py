from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from decimal import Decimal
import uuid
from unittest.mock import patch

from .models import CreatorApplication, CreditTransaction
from payments.models import MpesaPayment


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class CreatorWorkflowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.learner = User.objects.create_user("applicant", password="valid-password")
        self.admin = User.objects.create_superuser("siteadmin", "admin@example.test", "valid-password")

    def test_learner_can_apply_pending_and_pending_user_cannot_upload(self):
        self.client.force_authenticate(self.learner)
        response = self.client.post("/api/accounts/creator/applications/", {"motivation": "I teach mathematics."})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["application"]["status"], "pending")
        self.assertEqual(self.client.post("/api/content/create/", {}).status_code, 403)
        self.assertEqual(self.client.get("/api/accounts/creator/applications/").data["application"]["status"], "pending")

    def test_admin_approves_and_rejects_applications_and_only_approval_grants_creator(self):
        application = CreatorApplication.objects.create(applicant=self.learner, motivation="Teach")
        self.client.force_authenticate(self.admin)
        response = self.client.post(f"/api/admin/creator-applications/{application.pk}/decision/", {"status": "approved"})
        self.assertEqual(response.status_code, 200)
        self.learner.profile.refresh_from_db()
        self.assertEqual(self.learner.profile.role, "creator")
        self.assertIsNotNone(CreatorApplication.objects.get(pk=application.pk).decided_at)
        self.assertEqual(self.client.post(f"/api/admin/creator-applications/{application.pk}/decision/", {"status": "rejected"}).status_code, 400)

        second = User.objects.create_user("second", password="valid-password")
        rejected = CreatorApplication.objects.create(applicant=second, motivation="Teach")
        self.client.post(f"/api/admin/creator-applications/{rejected.pk}/decision/", {"status": "rejected"})
        second.profile.refresh_from_db()
        self.assertEqual(second.profile.role, "learner")

    def test_learner_cannot_decide_application_or_create_creator(self):
        application = CreatorApplication.objects.create(applicant=self.learner, motivation="Teach")
        self.client.force_authenticate(self.learner)
        self.assertEqual(self.client.post(f"/api/admin/creator-applications/{application.pk}/decision/", {"status": "approved"}).status_code, 403)
        self.assertEqual(self.client.post("/api/admin/creators/create/", {}).status_code, 403)

    def test_superuser_profile_is_admin_and_can_create_creator(self):
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.get("/api/accounts/profile/").data["role"], "admin")
        response = self.client.post("/api/admin/creators/create/", {
            "username": "newcreator", "email": "creator@example.test", "password": "Str0ng-unique-password-2026!",
        })
        self.assertEqual(response.status_code, 201)
        creator = User.objects.get(username="newcreator")
        self.assertEqual(creator.profile.role, "creator")
        self.assertEqual(creator.profile.creator_created_by, self.admin)
        self.assertTrue(creator.check_password("Str0ng-unique-password-2026!"))

    def test_same_django_credentials_work_through_frontend_jwt_login(self):
        response = self.client.post("/api/accounts/login/", {"username": "siteadmin", "password": "valid-password"})
        self.assertEqual(response.status_code, 200)
        profile = self.client.get("/api/accounts/profile/", HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
        self.assertEqual(profile.status_code, 200)
        self.assertEqual(profile.data["role"], "admin")

    def test_login_uses_current_backend_password_after_password_change(self):
        self.admin.set_password("changed-backend-password")
        self.admin.save(update_fields=["password"])
        old = self.client.post("/api/accounts/login/", {"username": "siteadmin", "password": "valid-password"})
        new = self.client.post("/api/accounts/login/", {"username": "siteadmin", "password": "changed-backend-password"})
        self.assertEqual(old.status_code, 401)
        self.assertEqual(new.status_code, 200)

    def test_normal_and_inactive_users_cannot_use_admin_api(self):
        learner = User.objects.create_user("normal", password="normal-password")
        self.client.force_authenticate(learner)
        self.assertEqual(self.client.get("/api/admin/dashboard/").status_code, 403)
        learner.is_active = False
        learner.save(update_fields=["is_active"])
        self.client.force_authenticate(user=None)
        response = self.client.post("/api/accounts/login/", {"username": "normal", "password": "normal-password"})
        self.assertEqual(response.status_code, 401)

    def test_admin_can_suspend_and_reactivate_creator(self):
        creator = User.objects.create_user("account_creator", password="valid-password")
        creator.profile.role = "creator"
        creator.profile.save()
        self.client.force_authenticate(self.admin)
        url = f"/api/admin/users/{creator.pk}/status/"
        self.assertEqual(self.client.patch(url, {"is_active": False}, format="json").status_code, 200)
        creator.refresh_from_db()
        self.assertFalse(creator.is_active)
        self.assertEqual(self.client.patch(url, {"is_active": True}, format="json").status_code, 200)
        creator.refresh_from_db()
        self.assertTrue(creator.is_active)

    def test_wallet_history_is_owner_scoped_and_cannot_be_written_by_client(self):
        other = User.objects.create_user("wallet-other", password="valid-password")
        CreditTransaction.objects.create(user=self.learner, transaction_type="topup", amount=Decimal("10"), balance_after=Decimal("10"), idempotency_key="wallet-owner")
        CreditTransaction.objects.create(user=other, transaction_type="topup", amount=Decimal("20"), balance_after=Decimal("20"), idempotency_key="wallet-other")
        MpesaPayment.objects.create(user=other, phone_number="254712345678", amount=Decimal("20"), status="pending")
        self.client.force_authenticate(self.learner)
        history = self.client.get("/api/accounts/wallet/transactions/")
        self.assertEqual(len(history.data["transactions"]), 1)
        self.assertEqual(history.data["transactions"][0]["amount"], "10.00")
        self.assertEqual(history.data["payments"], [])
        self.assertEqual(self.client.post("/api/accounts/wallet/transactions/", {"credits": "5000"}).status_code, 405)
        self.learner.profile.refresh_from_db()
        self.assertEqual(self.learner.profile.credits, Decimal("0.00"))
        self.client.force_authenticate(user=None)
        self.assertEqual(self.client.get("/api/accounts/wallet/transactions/").status_code, 401)

    @override_settings(MPESA_CALLBACK_URL="https://api.example.test/api/payments/mpesa/callback/")
    def test_topup_request_remains_pending_without_server_verified_callback(self):
        self.client.force_authenticate(self.learner)
        with patch("payments.views.initiate_stk_push", return_value={"ResponseCode": "0", "CheckoutRequestID": "checkout-test"}):
            response = self.client.post("/api/payments/mpesa/initiate/", {"amount": "100", "phone_number": "254712345678", "idempotency_key": str(uuid.uuid4())}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], "pending")
        self.learner.profile.refresh_from_db()
        self.assertEqual(self.learner.profile.credits, Decimal("0.00"))

    def test_suspension_blocks_creator_upload_permission(self):
        creator = User.objects.create_user("creator", password="valid-password", is_active=False)
        creator.profile.role = "creator"
        creator.profile.save()
        self.client.force_authenticate(creator)
        self.assertEqual(self.client.post("/api/content/create/", {}).status_code, 403)
