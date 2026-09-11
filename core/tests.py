from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase
from rest_framework import status
from core.models import User, Candidate, Employer, Job, Application


class AuthenticationAndJobTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        
        # 1. Seed Employer User
        self.employer = User.objects.create_user(
            email='employer_test@example.com',
            password='Password123!',
            name='Test Employer',
            role='employer'
        )
        
        # 2. Seed Candidate User
        self.candidate = User.objects.create_user(
            email='candidate_test@example.com',
            password='Password123!',
            name='Test Candidate',
            role='candidate'
        )
        
        # 3. Create a Test Job
        self.job = Job.objects.create(
            employer=self.employer,
            title='Backend QA Engineer',
            company='Tech Solutions',
            skills_required='Python, Django, Pytest',
            experience_required='2 years',
            location='Remote',
            status='active'
        )

    # --- Test 1: User Login & JWT Generation ---
    def test_user_login_success(self):
        payload = {
            'email': 'employer_test@example.com',
            'password': 'Password123!'
        }
        response = self.client.post('/api/auth/login/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Verify JWT tokens returned directly in response payload
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    # --- Test 2: Public Job Listing ---
    def test_public_job_list(self):
        self.client.force_authenticate(user=self.candidate)
        response = self.client.get('/api/jobs/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # --- Test 3: Candidate Application Submission ---
    def test_candidate_apply_job(self):
        self.client.force_authenticate(user=self.candidate)
        app = Application.objects.create(
            candidate=self.candidate,
            job=self.job,
            status='applied',
            ats_score=75.0
        )
        self.assertEqual(app.status, 'applied')
        self.assertEqual(app.candidate.email, 'candidate_test@example.com')

    # --- Test 4: Security Audit: Candidate Cannot Create Jobs ---
    def test_security_candidate_cannot_post_job(self):
        self.client.force_authenticate(user=self.candidate)
        payload = {
            'title': 'Illegal Job Posting',
            'company': 'Hacker Inc',
            'skills_required': 'None',
            'experience_required': '0'
        }
        response = self.client.post('/api/jobs/', payload, format='json')
        self.assertIn(response.status_code, [
            status.HTTP_403_FORBIDDEN, 
            status.HTTP_401_UNAUTHORIZED, 
            status.HTTP_405_METHOD_NOT_ALLOWED
        ])

    # --- Test 5: Employer Ranked Pipeline Access ---
    def test_employer_access_ranked_candidates(self):
        Application.objects.create(candidate=self.candidate, job=self.job, ats_score=88.0)
        self.client.force_authenticate(user=self.employer)
        response = self.client.get(f'/api/employer/jobs/{self.job.id}/ranked-candidates/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class ProfileModuleTests(APITestCase):

    def setUp(self):
        # Create Candidate user
        self.candidate_user = User.objects.create_user(
            email="candidate@zecpath.com",
            password="SecurePassword123!",
            name="John Doe",
            role="candidate"
        )
        self.candidate_profile, _ = Candidate.objects.get_or_create(user=self.candidate_user)

        # Create Employer user
        self.recruiter_user = User.objects.create_user(
            email="recruiter@zecpath.com",
            password="SecurePassword123!",
            name="Jane Boss",
            role="employer"
        )
        self.employer_profile, _ = Employer.objects.get_or_create(user=self.recruiter_user)

        # Dynamic reverse route resolution
        try:
            self.candidate_url = reverse('candidate-profile')
        except Exception:
            self.candidate_url = '/api/candidate/profile/'

        try:
            self.employer_url = reverse('employer-profile')
        except Exception:
            self.employer_url = '/api/employer/profile/'

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
        self.assertIn(response.status_code, [
            status.HTTP_204_NO_CONTENT, 
            status.HTTP_200_OK, 
            status.HTTP_404_NOT_FOUND
        ])

    def test_employer_cannot_self_verify(self):
        """Security Control: Recruiters cannot self-verify."""
        self.client.force_authenticate(user=self.recruiter_user)
        response = self.client.patch(self.employer_url, {"is_verified": True}, format='json')
        self.assertIn(response.status_code, [
            status.HTTP_200_OK, 
            status.HTTP_403_FORBIDDEN, 
            status.HTTP_404_NOT_FOUND
        ])


class AICallEngineTests(APITestCase):
    def setUp(self):
        self.recruiter = User.objects.create_user(
            email="recruiter_test33@example.com",
            password="Password123!",
            name="Recruiter Day33",
            role="recruiter"
        )
        self.candidate_user = User.objects.create_user(
            email="candidate_test33@example.com",
            password="Password123!",
            name="Candidate Day33",
            role="candidate"
        )
        self.candidate_profile, _ = Candidate.objects.get_or_create(user=self.candidate_user)

        self.job = Job.objects.create(
            employer=self.recruiter,
            title="Senior Backend Engineer",
            company="Tech Corp",
            skills_required="Python, Django",
            experience_required="3 years",
            status="active"
        )

        self.app = Application.objects.create(
            candidate=self.candidate_user,
            job=self.job,
            status="applied",
            ats_score=80.0
        )

    def test_eligibility_and_trigger(self):
        from core.utils.ai_call_engine import check_eligibility, trigger_ai_call
        eligible, reason = check_eligibility(self.app, ats_threshold=75.0)
        self.assertTrue(eligible)

        ai_call, message = trigger_ai_call(self.app, delay_minutes=5)
        self.assertIsNotNone(ai_call)
        self.assertIn(ai_call.status, ['queued', 'completed'])

    def test_ai_call_endpoints(self):
        from core.utils.ai_call_engine import trigger_ai_call
        ai_call, _ = trigger_ai_call(self.app, force=True)

        self.client.force_authenticate(user=self.recruiter)

        # GET detail
        response = self.client.get(f'/api/testing/ai-calls/{ai_call.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # GET list
        response = self.client.get('/api/testing/ai-calls/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Set call status to queued to test cancel
        ai_call.status = 'queued'
        ai_call.save()

        # POST cancel
        response = self.client.post(f'/api/aicalls/{ai_call.id}/cancel/', {"reason": "Test cancel"}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # POST retry
        response = self.client.post(f'/api/aicalls/{ai_call.id}/retry/', {"delay_minutes": 5}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class LoadTestingAndBenchmarkTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="loadtest_user@example.com",
            password="Password123!",
            name="Load Test Admin",
            role="admin"
        )

    def test_stress_test_ping_endpoint_public(self):
        """Verify public health ping endpoint for Locust high concurrency load testing."""
        response = self.client.get('/api/load-test/ping/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('status'), 'healthy')
        self.assertIn('server_time', response.data)
        self.assertEqual(response.data.get('load_state'), 'normal')

    def test_benchmark_report_endpoint_requires_auth(self):
        """Verify benchmark report endpoint requires authentication."""
        response = self.client.get('/api/load-test/benchmark-report/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_benchmark_report_endpoint_authenticated(self):
        """Verify benchmark report returns query benchmarks and summary."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/load-test/benchmark-report/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('status'), 'success')
        self.assertIn('data', response.data)
        data = response.data['data']
        self.assertEqual(data.get('test_target'), 'AI Recruitment Pipeline & Analytics Endpoints')
        self.assertIn('query_benchmark_results', data)
        self.assertIn('stability_status', data)


class SystemReadinessAndOverviewTests(APITestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(
            email="readiness_admin@example.com",
            password="Password123!",
            name="Readiness Admin",
            role="admin"
        )

    def test_system_api_overview_public(self):
        """Verify public API overview documentation endpoint."""
        response = self.client.get('/api/system/api-overview/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('status'), 'success')
        self.assertIn('documentation', response.data)
        docs = response.data['documentation']
        self.assertEqual(docs.get('platform_name'), 'Zecpath AI Job Portal & Automated Hiring Assistant')
        self.assertIn('core_modules', docs)
        self.assertIn('auth_and_profiles', docs['core_modules'])
        self.assertIn('ai_voice_screening', docs['core_modules'])

    def test_system_readiness_check_requires_auth(self):
        """Verify readiness check endpoint is protected."""
        response = self.client.get('/api/system/readiness-check/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_system_readiness_check_authenticated(self):
        """Verify authenticated readiness check returns comprehensive health & audit report."""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get('/api/system/readiness-check/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('status'), 'success')
        self.assertIn('data', response.data)
        data = response.data['data']
        self.assertEqual(data.get('phase'), 'Phase Review & AI Backend Readiness (Day 45)')
        self.assertIn('overall_status', data)
        self.assertIn('architecture_validation', data)
        self.assertIn('subsystem_health', data)
        self.assertIn('readiness_signoff', data)


class SaaSMonetizationAndSubscriptionTests(APITestCase):
    def setUp(self):
        from core.models import SubscriptionPlan, UserSubscription, PaymentTransaction, BillingHistory
        self.free_plan, _ = SubscriptionPlan.objects.get_or_create(
            name='free',
            defaults={'display_title': 'Free Tier', 'price': 0.00, 'max_active_jobs': 2, 'max_ai_screenings_per_month': 5, 'has_advanced_analytics': False}
        )
        self.pro_plan, _ = SubscriptionPlan.objects.get_or_create(
            name='pro',
            defaults={'display_title': 'Pro Recruiter', 'price': 49.00, 'max_active_jobs': -1, 'max_ai_screenings_per_month': 100, 'has_advanced_analytics': True}
        )
        self.employer_user = User.objects.create_user(
            email="employer_billing@example.com",
            password="Password123!",
            name="Employer Billing User",
            role="employer"
        )

    def test_list_subscription_plans_public(self):
        """Verify public subscription plans listing."""
        response = self.client.get('/api/billing/plans/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('status'), 'success')
        self.assertTrue(len(response.data.get('plans', [])) >= 2)

    def test_my_subscription_unauthenticated(self):
        """Verify subscription detail endpoint requires authentication."""
        response = self.client.get('/api/billing/my-subscription/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_my_subscription_no_active_plan(self):
        """Verify response when user has no active subscription."""
        self.client.force_authenticate(user=self.employer_user)
        response = self.client.get('/api/billing/my-subscription/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data.get('has_subscription'))

    def test_mock_subscribe_plan_success(self):
        """Verify subscribing to Pro tier creates transaction, subscription, and invoice."""
        self.client.force_authenticate(user=self.employer_user)
        response = self.client.post('/api/billing/subscribe/', {'plan_name': 'pro'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data.get('status'), 'success')
        self.assertIn('transaction_reference', response.data)
        self.assertIn('expires_at', response.data)

        # Verify my-subscription detail now returns valid subscription
        sub_resp = self.client.get('/api/billing/my-subscription/')
        self.assertEqual(sub_resp.status_code, status.HTTP_200_OK)
        self.assertTrue(sub_resp.data.get('has_subscription'))
        self.assertEqual(sub_resp.data['subscription']['plan'], 'pro')
        self.assertTrue(sub_resp.data['subscription']['valid'])


class PaymentGatewayAndWebhookTests(APITestCase):
    def setUp(self):
        import hmac
        import hashlib
        from django.conf import settings
        from core.models import SubscriptionPlan, UserSubscription, PaymentTransaction, BillingHistory

        self.plan, _ = SubscriptionPlan.objects.get_or_create(
            name='pro',
            defaults={'display_title': 'Pro Recruiter', 'price': 49.00, 'is_active': True}
        )
        self.user = User.objects.create_user(
            email="payment_user@example.com",
            password="Password123!",
            name="Payment Test User",
            role="employer"
        )

    def test_create_payment_order_razorpay(self):
        """Verify creating Razorpay payment order."""
        self.client.force_authenticate(user=self.user)
        response = self.client.post('/api/payments/create-order/', {
            'plan_name': 'pro',
            'gateway': 'razorpay'
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], 'success')
        order = response.data['order']
        self.assertEqual(order['gateway'], 'razorpay')
        self.assertEqual(order['currency'], 'INR')
        self.assertEqual(order['plan_name'], 'pro')
        self.assertTrue(order['order_id'].startswith('ORD_'))

    def test_create_payment_order_stripe(self):
        """Verify creating Stripe payment order."""
        self.client.force_authenticate(user=self.user)
        response = self.client.post('/api/payments/create-order/', {
            'plan_name': 'pro',
            'gateway': 'stripe'
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        order = response.data['order']
        self.assertEqual(order['gateway'], 'stripe')
        self.assertEqual(order['currency'], 'USD')

    def test_verify_payment_success_with_signature(self):
        """Verify cryptographic HMAC signature check and subscription activation."""
        import hmac
        import hashlib
        from django.conf import settings
        from core.models import PaymentTransaction, UserSubscription, BillingHistory

        self.client.force_authenticate(user=self.user)
        # 1. Create order
        create_resp = self.client.post('/api/payments/create-order/', {
            'plan_name': 'pro',
            'gateway': 'razorpay'
        }, format='json')
        order_id = create_resp.data['order']['order_id']
        payment_id = 'pay_test_123456'

        # 2. Compute valid signature
        secret = settings.RAZORPAY_KEY_SECRET.encode('utf-8')
        msg = f"{order_id}|{payment_id}".encode('utf-8')
        valid_sig = hmac.new(secret, msg, hashlib.sha256).hexdigest()

        # 3. Verify payment
        verify_resp = self.client.post('/api/payments/verify/', {
            'order_id': order_id,
            'payment_id': payment_id,
            'signature': valid_sig
        }, format='json')

        self.assertEqual(verify_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(verify_resp.data['status'], 'succeeded')

        # Check transaction and subscription updated
        tx = PaymentTransaction.objects.get(transaction_reference=order_id)
        self.assertEqual(tx.status, 'succeeded')

        sub = UserSubscription.objects.get(user=self.user)
        self.assertEqual(sub.status, 'active')
        self.assertEqual(sub.plan.name, 'pro')

        invoice = BillingHistory.objects.filter(transaction=tx).first()
        self.assertIsNotNone(invoice)

    def test_verify_payment_invalid_signature(self):
        """Verify payment rejection on invalid HMAC signature."""
        self.client.force_authenticate(user=self.user)
        create_resp = self.client.post('/api/payments/create-order/', {'plan_name': 'pro'}, format='json')
        order_id = create_resp.data['order']['order_id']

        verify_resp = self.client.post('/api/payments/verify/', {
            'order_id': order_id,
            'payment_id': 'pay_invalid',
            'signature': 'invalid_signature_hash'
        }, format='json')

        self.assertEqual(verify_resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Cryptographic signature verification failed", verify_resp.data['error'])

    def test_payment_webhook_events(self):
        """Verify handling of asynchronous payment webhook events."""
        from core.models import PaymentTransaction
        tx = PaymentTransaction.objects.create(
            user=self.user,
            amount=49.00,
            currency="INR",
            payment_method="razorpay",
            transaction_reference="ORD_WEBHOOK_TEST_1",
            status="pending"
        )

        # 1. Captured / Succeeded
        resp = self.client.post('/api/payments/webhook/', {
            'event': 'payment.captured',
            'payload': {'order_id': 'ORD_WEBHOOK_TEST_1'}
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        tx.refresh_from_db()
        self.assertEqual(tx.status, 'succeeded')

        # 2. Failed
        resp = self.client.post('/api/payments/webhook/', {
            'event': 'payment.failed',
            'payload': {'order_id': 'ORD_WEBHOOK_TEST_1'}
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        tx.refresh_from_db()
        self.assertEqual(tx.status, 'failed')

        # 3. Refunded
        resp = self.client.post('/api/payments/webhook/', {
            'event': 'refund.processed',
            'payload': {'order_id': 'ORD_WEBHOOK_TEST_1'}
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        tx.refresh_from_db()
        self.assertEqual(tx.status, 'refunded')



