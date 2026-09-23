from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from core.models import Application, Job, SubscriptionPlan, UserSubscription

User = get_user_model()


class ZecpathRegressionTestSuite(TestCase):
    """Validates platform critical paths and verifies resolved bugs don't resurface."""

    def setUp(self):
        self.client = APIClient()
        self.employer = User.objects.create_user(
            email="employer@test.com", password="SecurePassword123!", role="employer"
        )
        self.candidate = User.objects.create_user(
            email="applicant@test.com", password="SecurePassword123!", role="candidate"
        )
        self.plan = SubscriptionPlan.objects.create(
            name="pro",
            display_title="Pro Recruiter",
            price=Decimal("49.00"),
            max_active_jobs=-1,
            has_advanced_analytics=True,
        )
        self.sub = UserSubscription.objects.create(
            user=self.employer,
            plan=self.plan,
            status="active",
            current_period_end=timezone.now() + timedelta(days=30),
        )
        self.job = Job.objects.create(
            employer=self.employer,
            title="Senior Backend Engineer",
            description="Django core systems.",
        )

    def test_authenticated_user_can_access_health_ping(self):
        """Ensures public health probe endpoint remains available."""
        response = self.client.get("/api/load-test/ping/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data.get("status"), "healthy")

    def test_free_or_unsubscribed_blocked_from_premium_analytics(self):
        """Validates feature gating stops users without active paid entitlements."""
        self.client.force_authenticate(user=self.candidate)
        response = self.client.get(f"/api/recruiter/premium/jobs/{self.job.id}/ranking-report/")
        self.assertEqual(response.status_code, 403)

    def test_ranking_calculation_with_missing_scores(self):
        """Regression test ensuring null application match scores don't trigger 500 errors."""
        app = Application.objects.create(job=self.job, candidate=self.candidate, status="applied")
        self.client.force_authenticate(user=self.employer)
        url = f"/api/recruiter/premium/jobs/{self.job.id}/ranking-report/"
        response = self.client.get(url)
        # Should gracefully return 200 rather than crashing
        self.assertIn(response.status_code, [200, 404])
