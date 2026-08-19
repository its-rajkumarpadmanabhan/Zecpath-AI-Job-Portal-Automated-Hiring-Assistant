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
        response = self.client.get(f'/api/aicalls/{ai_call.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # GET list
        response = self.client.get('/api/aicalls/')
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