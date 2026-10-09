from django.db import transaction

from accounts.services import deduct_credits, validate_money
from content.models import Content

from .models import Purchase


@transaction.atomic
def purchase_content(user, content_id):
    content = Content.objects.select_for_update().get(
        id=content_id,
        is_published=True,
    )

    if Purchase.objects.filter(
        user=user,
        content=content,
    ).exists():
        raise ValueError("You have already purchased this content.")

    price = validate_money(content.price)

    purchase = Purchase.objects.create(
        user=user,
        content=content,
        amount_paid=price,
    )

    new_balance = deduct_credits(
        user,
        price,
        description=f"Purchase: {content.title}",
        transaction_type="purchase",
        idempotency_key=f"purchase:{purchase.pk}",
    )

    return new_balance
