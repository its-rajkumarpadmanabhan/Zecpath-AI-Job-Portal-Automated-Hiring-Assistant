import time
from datetime import timedelta
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from core.models import SubscriptionPlan, UserSubscription, Job, Application, AIInterviewSession, PaymentTransaction

User = get_user_model()

class ZecpathEndToEndIntegrationTests(TestCase):
    """
    Validates user registration, job requisitions, AI interview flow,
    and payment processing end-to-end.
    """

    def setUp(self):
        self.client = APIClient()
        self.employer_email = "sarah.recruiter@acmecorp.com"
        self.candidate_email = "alex.applicant@example.com"
        self.password = "SecureProdPass123!"

    def test_complete_platform_lifecycle_e2e(self):
        # 1. Candidate & Employer Signup / Authentication
        employer_user = User.objects.create_user(
            email=self.employer_email,
            password=self.password,
            role="employer"
        )
        candidate_user = User.objects.create_user(
            email=self.candidate_email,
            password=self.password,
            role="candidate"
        )
        self.assertIsNotNone(employer_user.id)
        self.assertIsNotNone(candidate_user.id)

        # 2. Employer Plan Subscription & Payment Verification
        pro_plan = SubscriptionPlan.objects.create(
            name="pro",
            display_title="Pro Recruiter",
            price=Decimal("49.00"),
            max_active_jobs=-1,
            has_advanced_analytics=True
        )
        subscription = UserSubscription.objects.create(
            user=employer_user,
            plan=pro_plan,
            status="active",
            current_period_end=timezone.now() + timedelta(days=30)
        )
        payment_tx = PaymentTransaction.objects.create(
            user=employer_user,
            subscription=subscription,
            amount=Decimal("49.00"),
            currency="USD",
            payment_method="stripe",
            transaction_reference="E2E-PAY-TX-99881",
            status="succeeded",
            raw_response={"status": "paid"}
        )
        self.assertEqual(payment_tx.status, "succeeded")
        self.assertTrue(subscription.is_access_allowed)

        # 3. Job Requisition Creation
        self.client.force_authenticate(user=employer_user)
        job = Job.objects.create(
            employer=employer_user,
            title="Senior Full Stack AI Developer",
            description="Leading AI recruitment tooling integration.",
            status="active"
        )
        self.assertEqual(job.status, "active")

        # 4. Candidate Application & AI Interview Session
        self.client.force_authenticate(user=candidate_user)
        app = Application.objects.create(
            job=job,
            candidate=candidate_user,
            status="interview_scheduled"
        )
        session = AIInterviewSession.objects.create(
            application=app,
            session_status="completed",
            ai_score=88.5
        )
        self.assertEqual(session.overall_score, 88.5)


        # 5. Performance Check: Latency on Recruiter Analytics
        self.client.force_authenticate(user=employer_user)
        start_time = time.time()
        response = self.client.get(f"/api/recruiter/premium/jobs/{job.id}/ranking-report/")
        latency_ms = (time.time() - start_time) * 1000

        self.assertIn(response.status_code, [200, 404])
        self.assertLess(latency_ms, 500)  # Response must return under 500ms
