from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from core.models import PaymentTransaction, SubscriptionPlan, UserSubscription


class BillingDomainService:
    """Encapsulates subscription lifecycle transitions and transaction auditing."""

    @classmethod
    @transaction.atomic
    def activate_subscription(
        cls, user, plan_name: str, reference: str, amount: Decimal
    ) -> UserSubscription:
        plan = SubscriptionPlan.objects.get(name=plan_name)
        now = timezone.now()
        sub, _ = UserSubscription.objects.select_for_update().get_or_create(
            user=user,
            defaults={
                "plan": plan,
                "status": "active",
                "start_date": now,
                "current_period_end": now + timedelta(days=30),
            },
        )
        sub.plan = plan
        sub.status = "active"
        sub.current_period_end = now + timedelta(days=30)
        sub.save()

        PaymentTransaction.objects.create(
            user=user,
            subscription=sub,
            amount=amount,
            currency="USD",
            payment_method="stripe",
            transaction_reference=reference,
            status="succeeded",
            raw_response={"channel": "web_checkout"},
        )
        return sub
