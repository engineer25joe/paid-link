from decimal import Decimal, InvalidOperation
from uuid import uuid4

from django.db import transaction

from .models import CreditTransaction, UserProfile


MAX_KES_AMOUNT = Decimal("9999999999.99")
MAX_MPESA_TRANSACTION = Decimal("250000")


def validate_money(value):
    """Return a positive whole-KES Decimal fitting our ledger/provider fields."""
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError("Invalid amount.")
    if not amount.is_finite():
        raise ValueError("Amount must be finite.")
    if amount.as_tuple().exponent < -2:
        raise ValueError("Amount has excessive decimal precision.")
    if amount <= 0:
        raise ValueError("Amount must be greater than zero.")
    if amount != amount.to_integral_value():
        raise ValueError("Amount must be a whole KES amount.")
    if amount > MAX_KES_AMOUNT:
        raise ValueError("Amount exceeds the supported maximum.")
    return amount


def validate_mpesa_amount(value):
    amount = validate_money(value)
    if amount > MAX_MPESA_TRANSACTION:
        raise ValueError("Amount exceeds the M-Pesa per-transaction maximum.")
    return amount


def validate_b2c_amount(value):
    amount = validate_mpesa_amount(value)
    if amount < Decimal("10"):
        raise ValueError("B2C withdrawals must be at least KES 10.")
    return amount


def _key(key, prefix):
    return key or f"{prefix}:{uuid4().hex}"


@transaction.atomic
def add_credits(user, amount, transaction_type="topup", description="", idempotency_key=None):
    amount = validate_money(amount)
    if transaction_type not in {"topup", "refund", "adjustment"}:
        raise ValueError("Invalid credit transaction type.")
    idempotency_key = _key(idempotency_key, transaction_type)
    profile = UserProfile.objects.select_for_update().get(user=user)
    existing = CreditTransaction.objects.filter(idempotency_key=idempotency_key).first()
    if existing:
        if existing.user_id != user.id or existing.amount != amount or existing.transaction_type != transaction_type:
            raise ValueError("Idempotency key was already used for another event.")
        return existing.balance_after
    profile.credits += amount
    if profile.credits > MAX_KES_AMOUNT:
        raise ValueError("Balance exceeds the supported maximum.")
    profile.save(update_fields=["credits", "updated_at"])
    CreditTransaction.objects.create(
        user=user,
        transaction_type=transaction_type,
        amount=amount,
        balance_after=profile.credits,
        description=description,
        idempotency_key=idempotency_key,
    )
    return profile.credits


@transaction.atomic
def deduct_credits(user, amount, description="", transaction_type="purchase", idempotency_key=None):
    amount = validate_money(amount)
    if transaction_type not in {"purchase", "withdrawal", "adjustment"}:
        raise ValueError("Invalid debit transaction type.")
    idempotency_key = _key(idempotency_key, transaction_type)
    profile = UserProfile.objects.select_for_update().get(user=user)
    existing = CreditTransaction.objects.filter(idempotency_key=idempotency_key).first()
    if existing:
        if existing.user_id != user.id or existing.amount != -amount or existing.transaction_type != transaction_type:
            raise ValueError("Idempotency key was already used for another event.")
        return existing.balance_after
    if profile.credits < amount:
        raise ValueError("Insufficient credits.")
    profile.credits -= amount
    profile.save(update_fields=["credits", "updated_at"])
    CreditTransaction.objects.create(
        user=user,
        transaction_type=transaction_type,
        amount=-amount,
        balance_after=profile.credits,
        description=description,
        idempotency_key=idempotency_key,
    )
    return profile.credits


@transaction.atomic
def adjust_credits(user, amount, description, idempotency_key):
    """Apply an explicitly keyed signed balance adjustment atomically."""
    try:
        value = Decimal(str(amount))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError("Invalid amount.")
    if not value.is_finite() or value == 0:
        raise ValueError("Adjustment must be a finite nonzero amount.")
    validate_money(abs(value))
    if not idempotency_key or len(idempotency_key) > 160:
        raise ValueError("A valid idempotency key is required for an adjustment.")
    profile = UserProfile.objects.select_for_update().get(user=user)
    existing = CreditTransaction.objects.filter(idempotency_key=idempotency_key).first()
    if existing:
        if existing.user_id != user.id or existing.amount != value:
            raise ValueError("Idempotency key was already used for another event.")
        return existing.balance_after
    new_balance = profile.credits + value
    if new_balance < 0:
        raise ValueError("Adjustment would create a negative balance.")
    if new_balance > MAX_KES_AMOUNT:
        raise ValueError("Balance exceeds the supported maximum.")
    profile.credits = new_balance
    profile.save(update_fields=["credits", "updated_at"])
    CreditTransaction.objects.create(
        user=user,
        transaction_type="adjustment",
        amount=value,
        balance_after=new_balance,
        description=description,
        idempotency_key=idempotency_key,
    )
    return new_balance
