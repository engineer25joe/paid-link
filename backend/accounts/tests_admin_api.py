from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from content.models import Content
from payments.models import CreatorWithdrawal
from purchases.models import Purchase
from .models import CreditTransaction


class AdminManagementApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user("manage_admin", password="pw")
        self.admin.profile.role = "admin"
        self.admin.profile.save()
        self.creator = User.objects.create_user("manage_creator", password="pw")
        self.creator.profile.role = "creator"
        self.creator.profile.credits = Decimal("100.00")
        self.creator.profile.phone_number = "254712345678"
        self.creator.profile.save()
        self.learner = User.objects.create_user("manage_learner", password="pw")
        self.other = User.objects.create_user("another_learner", password="pw")
        self.content = Content.objects.create(creator=self.creator, title="Course", description="Desc",
                                              content_type="pdf", price=Decimal("25.00"), is_published=True,
                                              file_url="https://private.example/file")
        self.purchase = Purchase.objects.create(user=self.learner, content=self.content,
                                                amount_paid=Decimal("25.00"))
        self.ledger = CreditTransaction.objects.create(user=self.creator, transaction_type="topup",
                                                       amount=Decimal("100.00"), balance_after=Decimal("100.00"),
                                                       idempotency_key="admin-test-key")
        self.withdrawal = CreatorWithdrawal.objects.create(creator=self.creator, phone_number="254712345678",
                                                           amount=Decimal("20.00"))

    def auth(self, user):
        self.client.force_authenticate(user)

    def test_admin_management_lists_and_stats(self):
        self.auth(self.admin)
        stats = self.client.get("/api/admin/dashboard/")
        self.assertEqual(stats.status_code, 200)
        self.assertEqual(stats.data["total_users"], 4)
        self.assertEqual(stats.data["creators"], 1)
        self.assertEqual(stats.data["learners"], 2)
        self.assertEqual(stats.data["published_content"], 1)
        self.assertEqual(stats.data["total_purchases"], 1)
        self.assertEqual(stats.data["total_purchase_value"], "25.00")
        self.assertEqual(stats.data["pending_withdrawals"], 1)
        for path in ("users/", "creators/", "learners/", "content/", "purchases/", "ledger/", "withdrawals/"):
            with self.subTest(path=path):
                response = self.client.get("/api/admin/" + path)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data["count"], 1 if path not in ("users/", "learners/") else (4 if path == "users/" else 2))

    def test_details_filter_and_search_are_scoped_to_resource(self):
        self.auth(self.admin)
        self.assertEqual(self.client.get(f"/api/admin/creators/{self.creator.pk}/").status_code, 200)
        self.assertEqual(self.client.get(f"/api/admin/learners/{self.creator.pk}/").status_code, 404)
        response = self.client.get("/api/admin/users/?role=creator&search=manage_")
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(self.client.get(f"/api/admin/purchases/{self.purchase.pk}/").data["user_username"], "manage_learner")
        self.assertEqual(self.client.get(f"/api/admin/withdrawals/{self.withdrawal.pk}/").data["phone_number"], "********5678")

    def test_sensitive_fields_are_never_serialized(self):
        self.withdrawal.callback_token = "callback-secret"
        self.withdrawal.reconciliation_token = "reconciliation-secret"
        self.withdrawal.provider_result_data = {"SecurityCredential": "provider-secret"}
        self.withdrawal.save()
        self.auth(self.admin)
        response = self.client.get(f"/api/admin/withdrawals/{self.withdrawal.pk}/")
        rendered = str(response.data)
        for secret in ("callback-secret", "reconciliation-secret", "provider-secret", "SecurityCredential"):
            self.assertNotIn(secret, rendered)
        user_data = self.client.get(f"/api/admin/users/{self.creator.pk}/").data
        self.assertNotIn("password", user_data)
        self.assertNotIn("file_url", self.client.get(f"/api/admin/content/{self.content.pk}/").data)

    def test_regular_users_are_denied_management_and_actions(self):
        paths = ("/api/admin/dashboard/", "/api/admin/users/", "/api/admin/creators/",
                 "/api/admin/learners/", "/api/admin/content/", "/api/admin/purchases/",
                 "/api/admin/ledger/", "/api/admin/withdrawals/")
        for user in (self.creator, self.learner):
            self.auth(user)
            for path in paths:
                with self.subTest(user=user.username, path=path):
                    self.assertEqual(self.client.get(path).status_code, 403)
            self.assertEqual(self.client.post(f"/api/admin/withdrawals/{self.withdrawal.pk}/approve/").status_code, 403)
            self.assertEqual(self.client.post(f"/api/admin/withdrawals/{self.withdrawal.pk}/cancel/").status_code, 403)
            self.assertEqual(self.client.post(f"/api/admin/withdrawals/{self.withdrawal.pk}/reconcile/").status_code, 403)

    def test_admin_approval_and_cancel_use_existing_reserved_balance_flow(self):
        self.auth(self.admin)
        response = self.client.post(f"/api/admin/withdrawals/{self.withdrawal.pk}/approve/")
        self.assertEqual(response.status_code, 200)
        self.withdrawal.refresh_from_db()
        self.creator.profile.refresh_from_db()
        self.assertEqual(self.withdrawal.status, "approved_reserved")
        self.assertEqual(self.creator.profile.credits, Decimal("80.00"))
        self.assertTrue(CreditTransaction.objects.filter(idempotency_key=f"withdrawal:{self.withdrawal.pk}:reserve").exists())
        self.assertEqual(self.client.post(f"/api/admin/withdrawals/{self.withdrawal.pk}/cancel/").status_code, 200)
        self.withdrawal.refresh_from_db()
        self.creator.profile.refresh_from_db()
        self.assertEqual(self.withdrawal.status, "cancelled")
        self.assertEqual(self.creator.profile.credits, Decimal("100.00"))
        self.assertTrue(CreditTransaction.objects.filter(idempotency_key=f"withdrawal:{self.withdrawal.pk}:release").exists())

    def test_admin_rejects_invalid_withdrawal_state_and_reconciliation_not_found(self):
        self.auth(self.admin)
        self.withdrawal.status = "paid"
        self.withdrawal.save(update_fields=["status"])
        self.assertEqual(self.client.post(f"/api/admin/withdrawals/{self.withdrawal.pk}/approve/").status_code, 400)
        self.assertEqual(self.client.post(f"/api/admin/withdrawals/{self.withdrawal.pk}/cancel/").status_code, 400)
        self.assertEqual(self.client.post("/api/admin/payments/99999/reconcile/").status_code, 404)
