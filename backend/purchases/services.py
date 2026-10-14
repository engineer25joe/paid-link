from django.db import transaction

from accounts.models import PlatformSettings
from accounts.services import credits_for_kes, deduct_credits, validate_kes_price
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

    setting = PlatformSettings.current()
    price_kes = validate_kes_price(content.price_kes)
    # Round required purchase credits up to the next cent so a rounding
    # remainder can never let a buyer pay less than the stored KES price.
    credits = credits_for_kes(price_kes, setting.credit_to_kes_rate)

    purchase = Purchase.objects.create(
        user=user,
        content=content,
        amount_paid=price_kes,
        credits_charged=credits,
        conversion_rate=setting.credit_to_kes_rate,
    )

    new_balance = deduct_credits(
        user,
        credits,
        description=f"Purchase: {content.title}",
        transaction_type="purchase",
        idempotency_key=f"purchase:{purchase.pk}",
        amount_kes=price_kes,
        conversion_rate=setting.credit_to_kes_rate,
    )

    return new_balance
