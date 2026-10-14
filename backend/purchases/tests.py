from decimal import Decimal
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient

# Create your tests here.


class PurchaseHistoryOwnershipTests(TestCase):
    def test_purchase_history_returns_only_authenticated_users_records(self):
        from content.models import Content
        from .models import Purchase
        owner = User.objects.create_user("purchase_owner", password="test")
        another = User.objects.create_user("purchase_other", password="test")
        item = Content.objects.create(creator=owner, title="Protected", description="Course",
                                      content_type="pdf", price=Decimal("15.00"), is_published=True)
        Purchase.objects.create(user=owner, content=item, amount_paid=Decimal("15.00"))
        client = APIClient()
        client.force_authenticate(another)
        self.assertEqual(client.get("/api/purchases/").data, [])
        client.force_authenticate(owner)
        result = client.get("/api/purchases/")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.data[0]["content_id"], item.pk)
        self.assertNotIn("file_url", result.data[0])
