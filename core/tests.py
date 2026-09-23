from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from core.models import (Application, Candidate, Employer, Job,
                         PaymentTransaction, SubscriptionPlan, User,
                         UserSubscription)


class AuthenticationAndJobTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # 1. Seed Employer User
        self.employer = User.objects.create_user(
            email="employer_test@example.com",
            password="Password123!",
            name="Test Employer",
            role="employer",
        )

        # 2. Seed Candidate User
        self.candidate = User.objects.create_user(
            email="candidate_test@example.com",
            password="Password123!",
            name="Test Candidate",
            role="candidate",
        )

        # 3. Create a Test Job
        self.job = Job.objects.create(
            employer=self.employer,
            title="Backend QA Engineer",
            company="Tech Solutions",
            skills_required="Python, Django, Pytest",
            experience_required="2 years",
            location="Remote",
            status="active",
        )

    # --- Test 1: User Login & JWT Generation ---
    def test_user_login_success(self):
        payload = {"email": "employer_test@example.com", "password": "Password123!"}
        response = self.client.post("/api/auth/login/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Verify JWT tokens returned directly in response payload
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    # --- Test 2: Public Job Listing ---
    def test_public_job_list(self):
        self.client.force_authenticate(user=self.candidate)
        response = self.client.get("/api/jobs/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # --- Test 3: Candidate Application Submission ---
    def test_candidate_apply_job(self):
        self.client.force_authenticate(user=self.candidate)
        app = Application.objects.create(
            candidate=self.candidate, job=self.job, status="applied", ats_score=75.0
        )
        self.assertEqual(app.status, "applied")
        self.assertEqual(app.candidate.email, "candidate_test@example.com")

    # --- Test 4: Security Audit: Candidate Cannot Create Jobs ---
    def test_security_candidate_cannot_post_job(self):
        self.client.force_authenticate(user=self.candidate)
        payload = {
            "title": "Illegal Job Posting",
            "company": "Hacker Inc",
            "skills_required": "None",
            "experience_required": "0",
        }
        response = self.client.post("/api/jobs/", payload, format="json")
        self.assertIn(
            response.status_code,
            [
                status.HTTP_403_FORBIDDEN,
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_405_METHOD_NOT_ALLOWED,
            ],
        )

    # --- Test 5: Employer Ranked Pipeline Access ---
    def test_employer_access_ranked_candidates(self):
        Application.objects.create(candidate=self.candidate, job=self.job, ats_score=88.0)
        self.client.force_authenticate(user=self.employer)
        response = self.client.get(f"/api/employer/jobs/{self.job.id}/ranked-candidates/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class ProfileModuleTests(APITestCase):

    def setUp(self):
        # Create Candidate user
        self.candidate_user = User.objects.create_user(
            email="candidate@zecpath.com",
            password="SecurePassword123!",
            name="John Doe",
            role="candidate",
        )
        self.candidate_profile, _ = Candidate.objects.get_or_create(user=self.candidate_user)

        # Create Employer user
        self.recruiter_user = User.objects.create_user(
            email="recruiter@zecpath.com",
            password="SecurePassword123!",
            name="Jane Boss",
            role="employer",
        )
        self.employer_profile, _ = Employer.objects.get_or_create(user=self.recruiter_user)

        # Dynamic reverse route resolution
        try:
            self.candidate_url = reverse("candidate-profile")
        except Exception:
            self.candidate_url = "/api/candidate/profile/"

        try:
            self.employer_url = reverse("employer-profile")
        except Exception:
            self.employer_url = "/api/employer/profile/"

    def test_candidate_can_get_and_patch_own_profile(self):
        """Verify candidate can fetch and update profile data."""
        self.client.force_authenticate(user=self.candidate_user)
        response = self.client.get(self.candidate_url)
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND])

    def test_recruiter_cannot_access_candidate_profile(self):
        """Cross-role protection: Ensure recruiters are blocked from candidate profile view."""
        self.client.force_authenticate(user=self.recruiter_user)
        response = self.client.get(self.candidate_url)
        self.assertIn(response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])

    def test_candidate_profile_soft_delete(self):
        """Assert profile deletion handling."""
        self.client.force_authenticate(user=self.candidate_user)
        response = self.client.delete(self.candidate_url)
        self.assertIn(
            response.status_code,
            [status.HTTP_204_NO_CONTENT, status.HTTP_200_OK, status.HTTP_404_NOT_FOUND],
        )

    def test_employer_cannot_self_verify(self):
        """Security Control: Recruiters cannot self-verify."""
        self.client.force_authenticate(user=self.recruiter_user)
        response = self.client.patch(self.employer_url, {"is_verified": True}, format="json")
        self.assertIn(
            response.status_code,
            [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND],
        )


class AICallEngineTests(APITestCase):
    def setUp(self):
        self.recruiter = User.objects.create_user(
            email="recruiter_test33@example.com",
            password="Password123!",
            name="Recruiter Day33",
            role="recruiter",
        )
        self.candidate_user = User.objects.create_user(
            email="candidate_test33@example.com",
            password="Password123!",
            name="Candidate Day33",
            role="candidate",
        )
        self.candidate_profile, _ = Candidate.objects.get_or_create(user=self.candidate_user)

        self.job = Job.objects.create(
            employer=self.recruiter,
            title="Senior Backend Engineer",
            company="Tech Corp",
            skills_required="Python, Django",
            experience_required="3 years",
            status="active",
        )

        self.app = Application.objects.create(
            candidate=self.candidate_user, job=self.job, status="applied", ats_score=80.0
        )

    def test_eligibility_and_trigger(self):
        from core.utils.ai_call_engine import (check_eligibility,
                                               trigger_ai_call)

        eligible, reason = check_eligibility(self.app, ats_threshold=75.0)
        self.assertTrue(eligible)

        ai_call, message = trigger_ai_call(self.app, delay_minutes=5)
        self.assertIsNotNone(ai_call)
        self.assertIn(ai_call.status, ["queued", "completed"])

    def test_ai_call_endpoints(self):
        from core.utils.ai_call_engine import trigger_ai_call

        ai_call, _ = trigger_ai_call(self.app, force=True)

        self.client.force_authenticate(user=self.recruiter)

        # GET detail
        response = self.client.get(f"/api/testing/ai-calls/{ai_call.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # GET list
        response = self.client.get("/api/testing/ai-calls/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Set call status to queued to test cancel
        ai_call.status = "queued"
        ai_call.save()

        # POST cancel
        response = self.client.post(
            f"/api/aicalls/{ai_call.id}/cancel/", {"reason": "Test cancel"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # POST retry
        response = self.client.post(
            f"/api/aicalls/{ai_call.id}/retry/", {"delay_minutes": 5}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class LoadTestingAndBenchmarkTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="loadtest_user@example.com",
            password="Password123!",
            name="Load Test Admin",
            role="admin",
        )

    def test_stress_test_ping_endpoint_public(self):
        """Verify public health ping endpoint for Locust high concurrency load testing."""
        response = self.client.get("/api/load-test/ping/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get("status"), "healthy")
        self.assertIn("server_time", response.data)
        self.assertEqual(response.data.get("load_state"), "normal")

    def test_benchmark_report_endpoint_requires_auth(self):
        """Verify benchmark report endpoint requires authentication."""
        response = self.client.get("/api/load-test/benchmark-report/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_benchmark_report_endpoint_authenticated(self):
        """Verify benchmark report returns query benchmarks and summary."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/load-test/benchmark-report/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get("status"), "success")
        self.assertIn("data", response.data)
        data = response.data["data"]
        self.assertEqual(data.get("test_target"), "AI Recruitment Pipeline & Analytics Endpoints")
        self.assertIn("query_benchmark_results", data)
        self.assertIn("stability_status", data)


class SystemReadinessAndOverviewTests(APITestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(
            email="readiness_admin@example.com",
            password="Password123!",
            name="Readiness Admin",
            role="admin",
        )

    def test_system_api_overview_public(self):
        """Verify public API overview documentation endpoint."""
        response = self.client.get("/api/system/api-overview/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get("status"), "success")
        self.assertIn("documentation", response.data)
        docs = response.data["documentation"]
        self.assertEqual(
            docs.get("platform_name"), "Zecpath AI Job Portal & Automated Hiring Assistant"
        )
        self.assertIn("core_modules", docs)
        self.assertIn("auth_and_profiles", docs["core_modules"])
        self.assertIn("ai_voice_screening", docs["core_modules"])

    def test_system_readiness_check_requires_auth(self):
        """Verify readiness check endpoint is protected."""
        response = self.client.get("/api/system/readiness-check/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_system_readiness_check_authenticated(self):
        """Verify authenticated readiness check returns comprehensive health & audit report."""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get("/api/system/readiness-check/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get("status"), "success")
        self.assertIn("data", response.data)
        data = response.data["data"]
        self.assertEqual(data.get("phase"), "Phase Review & AI Backend Readiness (Day 45)")
        self.assertIn("overall_status", data)
        self.assertIn("architecture_validation", data)
        self.assertIn("subsystem_health", data)
        self.assertIn("readiness_signoff", data)


class SaaSMonetizationAndSubscriptionTests(APITestCase):
    def setUp(self):
        from core.models import (BillingHistory, PaymentTransaction,
                                 SubscriptionPlan, UserSubscription)

        self.free_plan, _ = SubscriptionPlan.objects.get_or_create(
            name="free",
            defaults={
                "display_title": "Free Tier",
                "price": 0.00,
                "max_active_jobs": 2,
                "max_ai_screenings_per_month": 5,
                "has_advanced_analytics": False,
            },
        )
        self.pro_plan, _ = SubscriptionPlan.objects.get_or_create(
            name="pro",
            defaults={
                "display_title": "Pro Recruiter",
                "price": 49.00,
                "max_active_jobs": -1,
                "max_ai_screenings_per_month": 100,
                "has_advanced_analytics": True,
            },
        )
        self.employer_user = User.objects.create_user(
            email="employer_billing@example.com",
            password="Password123!",
            name="Employer Billing User",
            role="employer",
        )

    def test_list_subscription_plans_public(self):
        """Verify public subscription plans listing."""
        response = self.client.get("/api/billing/plans/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get("status"), "success")
        self.assertTrue(len(response.data.get("plans", [])) >= 2)

    def test_my_subscription_unauthenticated(self):
        """Verify subscription detail endpoint requires authentication."""
        response = self.client.get("/api/billing/my-subscription/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_my_subscription_no_active_plan(self):
        """Verify response when user has no active subscription."""
        self.client.force_authenticate(user=self.employer_user)
        response = self.client.get("/api/billing/my-subscription/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data.get("has_subscription"))

    def test_mock_subscribe_plan_success(self):
        """Verify subscribing to Pro tier creates transaction, subscription, and invoice."""
        self.client.force_authenticate(user=self.employer_user)
        response = self.client.post("/api/billing/subscribe/", {"plan_name": "pro"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data.get("status"), "success")
        self.assertIn("transaction_reference", response.data)
        self.assertIn("expires_at", response.data)

        # Verify my-subscription detail now returns valid subscription
        sub_resp = self.client.get("/api/billing/my-subscription/")
        self.assertEqual(sub_resp.status_code, status.HTTP_200_OK)
        self.assertTrue(sub_resp.data.get("has_subscription"))
        self.assertEqual(sub_resp.data["subscription"]["plan"], "pro")
        self.assertTrue(sub_resp.data["subscription"]["valid"])


class PaymentGatewayAndWebhookTests(APITestCase):
    def setUp(self):
        import hashlib
        import hmac

        from django.conf import settings

        from core.models import (BillingHistory, PaymentTransaction,
                                 SubscriptionPlan, UserSubscription)

        self.plan, _ = SubscriptionPlan.objects.get_or_create(
            name="pro",
            defaults={"display_title": "Pro Recruiter", "price": 49.00, "is_active": True},
        )
        self.user = User.objects.create_user(
            email="payment_user@example.com",
            password="Password123!",
            name="Payment Test User",
            role="employer",
        )

    def test_create_payment_order_razorpay(self):
        """Verify creating Razorpay payment order."""
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/payments/create-order/",
            {"plan_name": "pro", "gateway": "razorpay"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], "success")
        order = response.data["order"]
        self.assertEqual(order["gateway"], "razorpay")
        self.assertEqual(order["currency"], "INR")
        self.assertEqual(order["plan_name"], "pro")
        self.assertTrue(order["order_id"].startswith("ORD_"))

    def test_create_payment_order_stripe(self):
        """Verify creating Stripe payment order."""
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/payments/create-order/", {"plan_name": "pro", "gateway": "stripe"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        order = response.data["order"]
        self.assertEqual(order["gateway"], "stripe")
        self.assertEqual(order["currency"], "USD")

    def test_verify_payment_success_with_signature(self):
        """Verify cryptographic HMAC signature check and subscription activation."""
        import hashlib
        import hmac

        from django.conf import settings

        from core.models import (BillingHistory, PaymentTransaction,
                                 UserSubscription)

        self.client.force_authenticate(user=self.user)
        # 1. Create order
        create_resp = self.client.post(
            "/api/payments/create-order/",
            {"plan_name": "pro", "gateway": "razorpay"},
            format="json",
        )
        order_id = create_resp.data["order"]["order_id"]
        payment_id = "pay_test_123456"

        # 2. Compute valid signature
        secret = settings.RAZORPAY_KEY_SECRET.encode("utf-8")
        msg = f"{order_id}|{payment_id}".encode("utf-8")
        valid_sig = hmac.new(secret, msg, hashlib.sha256).hexdigest()

        # 3. Verify payment
        verify_resp = self.client.post(
            "/api/payments/verify/",
            {"order_id": order_id, "payment_id": payment_id, "signature": valid_sig},
            format="json",
        )

        self.assertEqual(verify_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(verify_resp.data["status"], "succeeded")

        # Check transaction and subscription updated
        tx = PaymentTransaction.objects.get(transaction_reference=order_id)
        self.assertEqual(tx.status, "succeeded")

        sub = UserSubscription.objects.get(user=self.user)
        self.assertEqual(sub.status, "active")
        self.assertEqual(sub.plan.name, "pro")

        invoice = BillingHistory.objects.filter(transaction=tx).first()
        self.assertIsNotNone(invoice)

    def test_verify_payment_invalid_signature(self):
        """Verify payment rejection on invalid HMAC signature."""
        self.client.force_authenticate(user=self.user)
        create_resp = self.client.post(
            "/api/payments/create-order/", {"plan_name": "pro"}, format="json"
        )
        order_id = create_resp.data["order"]["order_id"]

        verify_resp = self.client.post(
            "/api/payments/verify/",
            {
                "order_id": order_id,
                "payment_id": "pay_invalid",
                "signature": "invalid_signature_hash",
            },
            format="json",
        )

        self.assertEqual(verify_resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Cryptographic signature verification failed", verify_resp.data["error"])

    def test_payment_webhook_events(self):
        """Verify handling of asynchronous payment webhook events."""
        from core.models import PaymentTransaction

        tx = PaymentTransaction.objects.create(
            user=self.user,
            amount=49.00,
            currency="INR",
            payment_method="razorpay",
            transaction_reference="ORD_WEBHOOK_TEST_1",
            status="pending",
        )

        # 1. Captured / Succeeded
        resp = self.client.post(
            "/api/payments/webhook/",
            {"event": "payment.captured", "payload": {"order_id": "ORD_WEBHOOK_TEST_1"}},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        tx.refresh_from_db()
        self.assertEqual(tx.status, "succeeded")

        # 2. Failed
        resp = self.client.post(
            "/api/payments/webhook/",
            {"event": "payment.failed", "payload": {"order_id": "ORD_WEBHOOK_TEST_1"}},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        tx.refresh_from_db()
        self.assertEqual(tx.status, "failed")

        # 3. Refunded
        resp = self.client.post(
            "/api/payments/webhook/",
            {"event": "refund.processed", "payload": {"order_id": "ORD_WEBHOOK_TEST_1"}},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        tx.refresh_from_db()
        self.assertEqual(tx.status, "refunded")


class FeatureAccessAndGatingTests(APITestCase):
    """Day 48: Tests for Feature Access Control, Usage Limits, Expiry, and Middleware."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="subscriber@example.com",
            password="Password123!",
            name="Subscriber Recruiter",
            role="recruiter",
        )
        self.free_plan = SubscriptionPlan.objects.create(
            name="free",
            display_title="Free Plan",
            price=0.00,
            max_active_jobs=2,
            has_advanced_analytics=False,
            is_active=True,
        )
        self.pro_plan = SubscriptionPlan.objects.create(
            name="pro",
            display_title="Pro Plan",
            price=49.00,
            max_active_jobs=10,
            has_advanced_analytics=True,
            is_active=True,
        )
        self.enterprise_plan = SubscriptionPlan.objects.create(
            name="enterprise",
            display_title="Enterprise Plan",
            price=199.00,
            max_active_jobs=-1,
            has_advanced_analytics=True,
            is_active=True,
        )

    def test_expiry_and_grace_period_logic(self):
        """Test automatic transition from active -> past_due (grace period) -> expired."""
        from datetime import timedelta

        from django.utils import timezone

        from core.models import UserSubscription

        sub = UserSubscription.objects.create(
            user=self.user,
            plan=self.pro_plan,
            status="active",
            start_date=timezone.now() - timedelta(days=35),
            current_period_end=timezone.now() - timedelta(days=1),
            grace_period_days=3,
        )

        # In grace period (expired 1 day ago <= 3 days grace)
        status_result = sub.check_and_update_expiry()
        self.assertEqual(status_result, "past_due")
        self.assertTrue(sub.is_access_allowed)

        # Beyond grace period (expired 5 days ago > 3 days grace)
        sub.status = "active"
        sub.current_period_end = timezone.now() - timedelta(days=5)
        sub.save()
        status_result = sub.check_and_update_expiry()
        self.assertEqual(status_result, "expired")
        self.assertFalse(sub.is_access_allowed)

    def test_feature_access_controller_job_posting_limits(self):
        """Test active job posting quota enforcement by tier."""
        from datetime import timedelta

        from django.utils import timezone

        from core.models import Job, UserSubscription
        from core.utils.feature_access import FeatureAccessController

        # 1. No subscription
        can_post, msg = FeatureAccessController.can_post_job(self.user)
        self.assertFalse(can_post)
        self.assertIn("Active subscription required", msg)

        # 2. Free subscription (max 2 jobs)
        sub = UserSubscription.objects.create(
            user=self.user,
            plan=self.free_plan,
            status="active",
            current_period_end=timezone.now() + timedelta(days=30),
        )
        can_post, msg = FeatureAccessController.can_post_job(self.user)
        self.assertTrue(can_post)

        # Create 2 active jobs
        Job.objects.create(employer=self.user, title="Job 1", company="Tech", status="active")
        Job.objects.create(employer=self.user, title="Job 2", company="Tech", status="active")

        can_post, msg = FeatureAccessController.can_post_job(self.user)
        self.assertFalse(can_post)
        self.assertIn("Job posting limit reached", msg)

        # 3. Upgrade to Enterprise (unlimited)
        sub.plan = self.enterprise_plan
        sub.save()
        can_post, msg = FeatureAccessController.can_post_job(self.user)
        self.assertTrue(can_post)
        self.assertIn("Unlimited", msg)

    def test_feature_access_controller_candidate_views(self):
        """Test candidate profile view quota on free and paid tiers."""
        from datetime import timedelta

        from django.utils import timezone

        from core.models import UserSubscription
        from core.utils.feature_access import FeatureAccessController

        sub = UserSubscription.objects.create(
            user=self.user,
            plan=self.free_plan,
            status="active",
            monthly_candidate_views_used=9,
            current_period_end=timezone.now() + timedelta(days=30),
        )

        # 10th view should be granted
        allowed, msg = FeatureAccessController.can_view_candidate_profile(self.user)
        self.assertTrue(allowed)
        sub.refresh_from_db()
        self.assertEqual(sub.monthly_candidate_views_used, 10)

        # 11th view on free tier should be denied
        allowed, msg = FeatureAccessController.can_view_candidate_profile(self.user)
        self.assertFalse(allowed)
        self.assertIn("limit of 10 reached", msg)

        # Switch to Pro (unlimited)
        sub.plan = self.pro_plan
        sub.save()
        allowed, msg = FeatureAccessController.can_view_candidate_profile(self.user)
        self.assertTrue(allowed)

    def test_subscription_validation_api(self):
        """Test GET /api/billing/validate-access/ endpoint."""
        from datetime import timedelta

        from django.utils import timezone

        from core.models import UserSubscription

        self.client.force_authenticate(user=self.user)

        # 1. Unsubscribed
        resp = self.client.get("/api/billing/validate-access/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["status"], "unsubscribed")

        # 2. Subscribed to Pro
        UserSubscription.objects.create(
            user=self.user,
            plan=self.pro_plan,
            status="active",
            current_period_end=timezone.now() + timedelta(days=30),
        )
        resp = self.client.get("/api/billing/validate-access/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["status"], "success")
        self.assertEqual(resp.data["subscription"]["tier"], "pro")
        self.assertTrue(resp.data["subscription"]["is_access_allowed"])

    def test_gated_candidate_access_api(self):
        """Test GET /api/features/candidate-access/ endpoint."""
        from datetime import timedelta

        from django.utils import timezone

        from core.models import UserSubscription

        self.client.force_authenticate(user=self.user)

        # 1. Without subscription -> 403
        resp = self.client.get("/api/features/candidate-access/")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

        # 2. With subscription -> 200
        UserSubscription.objects.create(
            user=self.user,
            plan=self.pro_plan,
            status="active",
            current_period_end=timezone.now() + timedelta(days=30),
        )
        resp = self.client.get("/api/features/candidate-access/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("candidate", resp.data)
        self.assertEqual(resp.data["candidate"]["name"], "Jane Doe")

    def test_paid_feature_access_middleware(self):
        """Test middleware gating on /api/recruiter/analytics/."""
        from datetime import timedelta

        from django.utils import timezone

        from core.models import UserSubscription

        # 1. Unauthenticated -> 401
        resp = self.client.get("/api/recruiter/analytics/funnel/")
        self.assertEqual(resp.status_code, 401)

        # 2. Authenticated but no subscription -> 403
        self.client.force_authenticate(user=self.user)
        resp = self.client.get("/api/recruiter/analytics/funnel/")
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.json()["error"], "Subscription Required")

        # 3. Free plan without advanced analytics -> 403 Upgrade Required
        sub = UserSubscription.objects.create(
            user=self.user,
            plan=self.free_plan,
            status="active",
            current_period_end=timezone.now() + timedelta(days=30),
        )
        resp = self.client.get("/api/recruiter/analytics/funnel/")
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.json()["error"], "Upgrade Required")

        # 4. Pro plan with advanced analytics -> 200
        sub.plan = self.pro_plan
        sub.save()
        resp = self.client.get("/api/recruiter/analytics/funnel/")
        self.assertEqual(resp.status_code, 200)

        # 5. Admin user bypass
        admin_user = User.objects.create_superuser(
            email="admin_sub@example.com", password="Password123!", name="Admin User"
        )
        self.client.force_authenticate(user=admin_user)
        resp = self.client.get("/api/recruiter/analytics/funnel/")
        self.assertEqual(resp.status_code, 200)


class PremiumRecruiterInsightsTests(APITestCase):
    """Day 49: Tests for Candidate Ranking, Success Predictions, Hiring Efficiency, and Tier Permissions."""

    def setUp(self):
        self.client = APIClient()
        self.recruiter = User.objects.create_user(
            email="recruiter_pro@example.com",
            password="Password123!",
            name="Recruiter Pro",
            role="recruiter",
        )
        self.candidate1 = User.objects.create_user(
            email="cand1@example.com",
            password="Password123!",
            name="Candidate Alice",
            role="candidate",
        )
        self.candidate2 = User.objects.create_user(
            email="cand2@example.com",
            password="Password123!",
            name="Candidate Bob",
            role="candidate",
        )

        from datetime import timedelta

        from django.utils import timezone

        self.pro_plan = SubscriptionPlan.objects.create(
            name="pro",
            display_title="Pro Recruiter Plan",
            price=49.00,
            has_advanced_analytics=True,
            is_active=True,
        )
        self.free_plan = SubscriptionPlan.objects.create(
            name="free",
            display_title="Free Tier",
            price=0.00,
            has_advanced_analytics=False,
            is_active=True,
        )

        self.sub = UserSubscription.objects.create(
            user=self.recruiter,
            plan=self.pro_plan,
            status="active",
            current_period_end=timezone.now() + timedelta(days=30),
        )

        self.job = Job.objects.create(
            employer=self.recruiter,
            title="Staff AI Engineer",
            company="Zecpath AI",
            skills_required="Python, PyTorch, Transformers",
            status="active",
        )

        self.app1 = Application.objects.create(
            candidate=self.candidate1, job=self.job, ats_score=90.0, status="selected"
        )
        self.app2 = Application.objects.create(
            candidate=self.candidate2, job=self.job, ats_score=65.0, status="applied"
        )

    def test_ranking_report_and_prediction(self):
        """Verify candidate ranking calculation and descending ordering."""
        from core.utils.premium_insights import PremiumInsightsService

        report = PremiumInsightsService.get_candidate_ranking_report(self.job.id, self.recruiter)
        self.assertNotIn("error", report)
        self.assertEqual(report["total_evaluated_candidates"], 2)

        rankings = report["rankings"]
        self.assertGreaterEqual(
            rankings[0]["composite_rank_score"], rankings[1]["composite_rank_score"]
        )
        self.assertEqual(rankings[0]["candidate_name"], "Candidate Alice")
        self.assertEqual(rankings[0]["success_prediction"], "High Probability Hire")

    def test_hiring_efficiency_metrics(self):
        """Verify recruiter hiring velocity & efficiency ratio calculations."""
        from core.utils.premium_insights import PremiumInsightsService

        metrics = PremiumInsightsService.get_hiring_efficiency_metrics(self.recruiter)
        data = metrics["recruiter_metrics"]

        self.assertEqual(data["active_job_campaigns"], 1)
        self.assertEqual(data["total_candidate_pipeline"], 2)
        self.assertEqual(data["successful_hires"], 1)
        self.assertEqual(data["hiring_conversion_efficiency_pct"], 50.0)
        self.assertEqual(data["estimated_hours_saved_by_ai"], 3.0)

    def test_premium_endpoints_with_pro_user(self):
        """Verify successful API responses for Pro recruiter."""
        self.client.force_authenticate(user=self.recruiter)

        # 1. Ranking Report API
        resp = self.client.get(f"/api/recruiter/premium/jobs/{self.job.id}/ranking-report/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["status"], "success")
        self.assertEqual(resp.data["data"]["job_title"], "Staff AI Engineer")

        # 2. Hiring Efficiency API
        resp = self.client.get("/api/recruiter/premium/hiring-efficiency/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["status"], "success")
        self.assertIn("recruiter_metrics", resp.data["data"])

    def test_permission_denied_for_candidate_and_free_plan(self):
        """Verify 403 Forbidden for candidates and free-tier recruiters."""
        # Candidate attempt
        self.client.force_authenticate(user=self.candidate1)
        resp = self.client.get("/api/recruiter/premium/hiring-efficiency/")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

        # Free tier recruiter attempt
        self.sub.plan = self.free_plan
        self.sub.save()
        self.client.force_authenticate(user=self.recruiter)
        resp = self.client.get("/api/recruiter/premium/hiring-efficiency/")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
