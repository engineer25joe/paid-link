from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .models import CreditRateHistory, CreditTransaction, PlatformSettings
from content.models import Content
from purchases.models import Purchase
from purchases.services import purchase_content
from .services import credits_for_kes


class WalletRateFeatureTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("wallet-admin", "admin@example.test", "Strong-Password-123!")
        self.learner = User.objects.create_user("wallet-learner", password="Strong-Password-123!")
        self.other = User.objects.create_user("wallet-other", password="Strong-Password-123!")
        self.client = APIClient()

    def test_admin_adjustments_are_reasoned_immutable_and_owner_visible(self):
        self.client.force_authenticate(self.admin)
        search = self.client.get("/api/admin/wallet/users/?search=wallet-learner")
        self.assertEqual(search.status_code, 200)
        url = f"/api/admin/wallet/users/{self.learner.pk}/adjust/"
        missing_reason = self.client.post(url, {"direction": "add", "amount": "20"}, format="json")
        self.assertEqual(missing_reason.status_code, 400)
        response = self.client.post(url, {"direction": "add", "amount": "20", "reason": "Promotion"}, format="json")
        self.assertEqual(response.status_code, 200)
        entry = CreditTransaction.objects.get(user=self.learner)
        self.assertEqual((entry.balance_before, entry.balance_after, entry.administrator, entry.reason),
                         (Decimal("0.00"), Decimal("20.00"), self.admin, "Promotion"))
        self.client.force_authenticate(self.learner)
        self.assertEqual(self.client.get("/api/accounts/wallet/transactions/").data["transactions"][0]["administrator"], self.admin.username)
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.post(url, {"direction": "add", "amount": 1, "reason": "No"}, format="json").status_code, 403)
        with self.assertRaises(Exception):
            entry.delete()

    def test_conversion_change_keeps_purchase_snapshot(self):
        item = Content.objects.create(creator=self.admin, title="KES resource", description="D", content_type="pdf", price_kes=Decimal("100.00"), is_published=True)
        self.learner.profile.credits = Decimal("100.00")
        self.learner.profile.save()
        self.assertEqual(PlatformSettings.current().credit_to_kes_rate, Decimal("2.0000"))
        purchase_content(self.learner, item.pk)
        purchase = Purchase.objects.get(user=self.learner, content=item)
        self.assertEqual((purchase.amount_paid, purchase.credits_charged, purchase.conversion_rate),
                         (Decimal("100.00"), Decimal("50.00"), Decimal("2.0000")))
        self.client.force_authenticate(self.admin)
        changed = self.client.put("/api/admin/settings/credit-rate/", {"rate": "1.0000"}, format="json")
        self.assertEqual(changed.status_code, 200)
        purchase.refresh_from_db()
        self.assertEqual((purchase.amount_paid, purchase.credits_charged, purchase.conversion_rate),
                         (Decimal("100.00"), Decimal("50.00"), Decimal("2.0000")))
        self.assertEqual(CreditRateHistory.objects.get().changed_by, self.admin)

    def test_purchase_credit_rounding_never_undercharges_and_topup_never_overawards(self):
        self.assertEqual(credits_for_kes("100", "3"), Decimal("33.34"))
        self.assertEqual(credits_for_kes("100", "3", topup=True), Decimal("33.33"))
