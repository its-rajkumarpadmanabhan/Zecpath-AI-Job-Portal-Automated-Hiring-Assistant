import hashlib
import hmac
import uuid
from decimal import Decimal

from django.conf import settings

from core.models import PaymentTransaction, SubscriptionPlan


class PaymentGatewayService:
    """Manages order creation and cryptographic signature checks for Razorpay and Stripe."""

    @classmethod
    def create_gateway_order(cls, user, plan_name: str, gateway: str = "razorpay") -> dict:
        """Initializes a payment session and returns order details to the client."""
        plan = SubscriptionPlan.objects.filter(name=plan_name, is_active=True).first()
        if not plan:
            raise ValueError(f"Plan '{plan_name}' does not exist.")

        amount_in_cents = int(plan.price * 100)
        order_reference = f"ORD_{uuid.uuid4().hex[:12].upper()}"

        transaction = PaymentTransaction.objects.create(
            user=user,
            amount=plan.price,
            currency="USD" if gateway == "stripe" else "INR",
            payment_method=gateway,
            transaction_reference=order_reference,
            status="pending",
            raw_response={"plan_name": plan.name, "amount_cents": amount_in_cents},
        )

        return {
            "order_id": order_reference,
            "gateway": gateway,
            "plan_name": plan.name,
            "amount": float(plan.price),
            "currency": transaction.currency,
            "key_id": (
                settings.RAZORPAY_KEY_ID if gateway == "razorpay" else settings.STRIPE_PUBLIC_KEY
            ),
        }

    @classmethod
    def verify_razorpay_signature(cls, order_id: str, payment_id: str, signature: str) -> bool:
        """Verifies HMAC SHA256 signature to protect against payment tampering and fraud."""
        secret = settings.RAZORPAY_KEY_SECRET.encode("utf-8")
        message = f"{order_id}|{payment_id}".encode("utf-8")
        generated_signature = hmac.new(secret, message, hashlib.sha256).hexdigest()
        return hmac.compare_digest(generated_signature, signature)

    @classmethod
    def mark_payment_success(cls, order_id: str, payment_id: str, payload: dict = None):
        """Updates transaction state and provisions the subscription."""
        tx = PaymentTransaction.objects.filter(transaction_reference=order_id).first()
        if tx:
            tx.status = "succeeded"
            tx.raw_response.update({"payment_id": payment_id, "verification": payload or {}})
            tx.save(update_fields=["status", "raw_response"])
        return tx
