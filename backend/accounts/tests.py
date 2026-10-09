from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from content.models import Content
from payments.models import CreatorWithdrawal
from purchases.models import Purchase

from .models import CreditTransaction
from .earnings import (
    CreatorEarningsByContentView,
    CreatorEarningsSummaryView,
    CreatorTransactionHistoryView,
    CreatorWithdrawalHistoryView,
)


class CreatorEarningsApiTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.creator = User.objects.create_user("earnings_creator", password="test")
        self.creator.profile.role = "creator"
        self.creator.profile.credits = Decimal("66.00")
        self.creator.profile.save()
        self.other_creator = User.objects.create_user("other_earnings_creator", password="test")
        self.other_creator.profile.role = "creator"
        self.other_creator.profile.credits = Decimal("9.00")
        self.other_creator.profile.save()
        self.learner = User.objects.create_user("earnings_learner", password="test")
        self.second_learner = User.objects.create_user("earnings_learner_two", password="test")
        self.admin = User.objects.create_user("earnings_admin", password="test")
        self.admin.profile.role = "admin"
        self.admin.profile.save()

        self.content_a = self.make_content(self.creator, "Book Alpha", "20.00", published=True)
        self.content_b = self.make_content(self.creator, "Video Beta", "35.00", published=True)
        self.content_zero = self.make_content(self.creator, "Unpublished", "12.00", published=False)
        self.other_content = self.make_content(self.other_creator, "Private Other", "80.00", published=True)

    @staticmethod
    def make_content(creator, title, price, published):
        return Content.objects.create(
            creator=creator, title=title, description="Description", content_type="pdf",
            price=Decimal(price), is_published=published,
        )

    def make_purchase(self, user, content, amount, days_ago=0):
        purchase = Purchase.objects.create(user=user, content=content, amount_paid=Decimal(amount))
        if days_ago:
            Purchase.objects.filter(pk=purchase.pk).update(purchased_at=timezone.now() - timedelta(days=days_ago))
            purchase.refresh_from_db()
        return purchase

    def call_view(self, view, user, method="get", path="/"):
        request = getattr(self.factory, method)(path)
        force_authenticate(request, user)
        return view.as_view()(request)

    def test_learners_are_rejected_from_all_creator_financial_endpoints(self):
        endpoints = (
            CreatorEarningsSummaryView,
            CreatorEarningsByContentView,
            CreatorTransactionHistoryView,
            CreatorWithdrawalHistoryView,
        )
        for view in endpoints:
            with self.subTest(view=view.__name__):
                response = self.call_view(view, self.learner)
                self.assertEqual(response.status_code, 403)

    def test_creator_data_is_scoped_to_authenticated_creator_and_admin_is_self_scoped(self):
        self.make_purchase(self.learner, self.content_a, "20.00")
        self.make_purchase(self.second_learner, self.other_content, "80.00")
        CreditTransaction.objects.create(user=self.creator, transaction_type="topup", amount=Decimal("5.00"), balance_after=Decimal("66.00"), idempotency_key="own-key")
        CreditTransaction.objects.create(user=self.other_creator, transaction_type="topup", amount=Decimal("9.00"), balance_after=Decimal("9.00"), idempotency_key="other-key")
        CreatorWithdrawal.objects.create(creator=self.creator, phone_number="254712345678", amount=Decimal("10"))
        CreatorWithdrawal.objects.create(creator=self.other_creator, phone_number="254700000000", amount=Decimal("20"))

        content_response = self.call_view(CreatorEarningsByContentView, self.creator)
        self.assertEqual({row["content_id"] for row in content_response.data},
                         {self.content_a.pk, self.content_b.pk, self.content_zero.pk})
        other_content_response = self.call_view(CreatorEarningsByContentView, self.other_creator)
        self.assertEqual({row["content_id"] for row in other_content_response.data}, {self.other_content.pk})

        tx_response = self.call_view(CreatorTransactionHistoryView, self.creator)
        self.assertEqual([row["idempotency_key"] for row in tx_response.data["results"]], ["own-key"])
        withdrawal_response = self.call_view(CreatorWithdrawalHistoryView, self.creator)
        self.assertEqual(len(withdrawal_response.data["results"]), 1)
        self.assertEqual(withdrawal_response.data["results"][0]["amount"], "10.00")

        admin_response = self.call_view(CreatorEarningsByContentView, self.admin)
        self.assertEqual(admin_response.data, [])

    def test_summary_aggregates_sales_balance_withdrawals_and_published_count(self):
        self.make_purchase(self.learner, self.content_a, "20.00", days_ago=3)
        self.make_purchase(self.second_learner, self.content_a, "20.00", days_ago=1)
        self.make_purchase(self.learner, self.content_b, "35.00")
        self.make_purchase(self.second_learner, self.other_content, "80.00")
        for amount, state in (("10.00", "paid"), ("5.00", "pending"), ("7.00", "provider_pending"),
                              ("3.00", "payout_failed_verified"), ("4.00", "refunded"), ("9.00", "cancelled")):
            CreatorWithdrawal.objects.create(creator=self.creator, phone_number="254712345678",
                                             amount=Decimal(amount), status=state)
        before_balance = self.creator.profile.credits
        before_ledger_count = CreditTransaction.objects.filter(user=self.creator).count()

        response = self.call_view(CreatorEarningsSummaryView, self.creator)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {
            "total_sales_count": 3,
            "gross_earnings": "75.00",
            "available_credit_balance": "66.00",
            "total_withdrawn": "10.00",
            "pending_processing_withdrawal_amount": "15.00",
            "published_contents_count": 2,
        })
        self.creator.profile.refresh_from_db()
        self.assertEqual(self.creator.profile.credits, before_balance)
        self.assertEqual(CreditTransaction.objects.filter(user=self.creator).count(), before_ledger_count)

    def test_content_aggregation_includes_multiple_purchases_zero_sales_and_latest_date(self):
        self.make_purchase(self.learner, self.content_a, "20.00", days_ago=4)
        latest_a = self.make_purchase(self.second_learner, self.content_a, "20.00", days_ago=1)
        self.make_purchase(self.learner, self.content_b, "35.00")

        with self.assertNumQueries(1):
            response = self.call_view(CreatorEarningsByContentView, self.creator)

        by_id = {row["content_id"]: row for row in response.data}
        self.assertEqual(by_id[self.content_a.pk]["title"], "Book Alpha")
        self.assertEqual(by_id[self.content_a.pk]["price"], "20.00")
        self.assertEqual(by_id[self.content_a.pk]["purchase_count"], 2)
        self.assertEqual(by_id[self.content_a.pk]["gross_sales"], "40.00")
        self.assertEqual(by_id[self.content_a.pk]["latest_purchase_at"], timezone.localtime(latest_a.purchased_at).isoformat())
        self.assertEqual(by_id[self.content_b.pk]["gross_sales"], "35.00")
        self.assertEqual(by_id[self.content_zero.pk]["purchase_count"], 0)
        self.assertEqual(by_id[self.content_zero.pk]["gross_sales"], "0.00")
        self.assertIsNone(by_id[self.content_zero.pk]["latest_purchase_at"])

    def test_transaction_history_uses_ledger_and_returns_required_fields(self):
        event = CreditTransaction.objects.create(
            user=self.creator, transaction_type="withdrawal", amount=Decimal("-20.00"),
            balance_after=Decimal("66.00"), description="Withdrawal reserve", idempotency_key="withdrawal:1:reserve",
        )
        response = self.call_view(CreatorTransactionHistoryView, self.creator)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0], {
            "id": event.pk,
            "transaction_type": "withdrawal",
            "amount": "-20.00",
            "balance_after": "66.00",
            "description": "Withdrawal reserve",
            "timestamp": timezone.localtime(event.created_at).isoformat(),
            "idempotency_key": "withdrawal:1:reserve",
        })

    def test_withdrawal_history_masks_phone_and_omits_callback_tokens(self):
        withdrawal = CreatorWithdrawal.objects.create(
            creator=self.creator, phone_number="254712345678", amount=Decimal("25.00"),
            status="outcome_unknown", payout_status="outcome_unknown", failure_reason="Provider timeout",
            callback_discrepancy="Reconciliation pending", callback_token="callback-secret",
            reconciliation_token="reconciliation-secret",
        )
        response = self.call_view(CreatorWithdrawalHistoryView, self.creator)
        self.assertEqual(response.status_code, 200)
        row = response.data["results"][0]
        self.assertEqual(row["amount"], "25.00")
        self.assertEqual(row["status"], "outcome_unknown")
        self.assertEqual(row["payout_status"], "outcome_unknown")
        self.assertEqual(row["phone_number"], "********5678")
        self.assertEqual(row["failure_reason"], "Provider timeout")
        self.assertEqual(row["callback_discrepancy"], "Reconciliation pending")
        self.assertNotIn("callback_token", row)
        self.assertNotIn("reconciliation_token", row)

    def test_zero_sales_creator_returns_decimal_zero_values(self):
        response = self.call_view(CreatorEarningsSummaryView, self.other_creator)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["total_sales_count"], 0)
        self.assertEqual(response.data["gross_earnings"], "0.00")
        self.assertEqual(response.data["total_withdrawn"], "0.00")
        self.assertEqual(response.data["pending_processing_withdrawal_amount"], "0.00")
        self.assertEqual(response.data["published_contents_count"], 1)
