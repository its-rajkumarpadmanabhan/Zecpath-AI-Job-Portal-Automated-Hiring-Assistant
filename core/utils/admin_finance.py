from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, Q, Sum
from django.utils import timezone

from core.models import BillingHistory, PaymentTransaction, UserSubscription


class AdminFinanceService:
    @classmethod
    def get_revenue_dashboard(cls) -> dict:
        now = timezone.now()
        thirty_days_ago = now - timedelta(days=30)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # 1. Platform Totals
        total_rev = PaymentTransaction.objects.filter(status="succeeded").aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0.00")

        daily_rev = PaymentTransaction.objects.filter(
            status="succeeded", created_at__gte=today_start
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        monthly_rev = PaymentTransaction.objects.filter(
            status="succeeded", created_at__gte=thirty_days_ago
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        # 2. Plan-Wise Revenue Breakdown
        plan_breakdown = list(
            UserSubscription.objects.values("plan__display_title", "plan__name").annotate(
                subscriber_count=Count("id"), estimated_mrr=Sum("plan__price")
            )
        )

        # 3. Transaction Statistics
        tx_stats = PaymentTransaction.objects.aggregate(
            total_txs=Count("id"),
            failed_txs=Count("id", filter=Q(status="failed")),
            refunded_txs=Count("id", filter=Q(status="refunded")),
        )

        return {
            "currency": "USD",
            "gross_revenue": float(total_rev),
            "daily_revenue": float(daily_rev),
            "monthly_revenue": float(monthly_rev),
            "plan_wise_metrics": plan_breakdown,
            "transaction_statistics": tx_stats,
        }

    @classmethod
    def process_refund(cls, transaction_id: int, reason: str, admin_user) -> dict:
        tx = PaymentTransaction.objects.filter(id=transaction_id).first()
        if not tx:
            raise ValueError("Transaction not found.")

        if tx.status != "succeeded":
            raise ValueError(f"Cannot refund transaction with status '{tx.status}'.")

        # Update transaction status
        tx.status = "refunded"
        if not isinstance(tx.raw_response, dict):
            tx.raw_response = {}
        tx.raw_response.update(
            {
                "refunded_at": timezone.now().isoformat(),
                "refunded_by": getattr(admin_user, "email", str(admin_user)),
                "refund_reason": reason,
            }
        )
        tx.save(update_fields=["status", "raw_response"])

        # Suspend or reset user subscription if tied to this transaction
        if tx.subscription:
            tx.subscription.status = "canceled"
            tx.subscription.save(update_fields=["status"])

        return {
            "transaction_id": tx.id,
            "reference": tx.transaction_reference,
            "amount_refunded": float(tx.amount),
            "status": tx.status,
        }
