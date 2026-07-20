from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from core.models import User, Candidate, Employer

class ProfileModuleTests(APITestCase):

    def setUp(self):
        # Create a Candidate user (Signal auto-creates Candidate profile)
        self.candidate_user = User.objects.create_user(
            email="candidate@zecpath.com",
            password="SecurePassword123!",
            name="John Doe",
            role="candidate"
        )
        self.candidate_profile = self.candidate_user.candidate_profile

        # Create a Recruiter user (Signal auto-creates Employer profile)
        self.recruiter_user = User.objects.create_user(
            email="recruiter@zecpath.com",
            password="SecurePassword123!",
            name="Jane Boss",
            role="recruiter"
        )
        self.employer_profile = self.recruiter_user.employer_profile

        # API Endpoints from URLs configuration
        self.candidate_url = reverse('candidate-profile')
        self.employer_url = reverse('employer-profile')

    def test_candidate_can_get_and_patch_own_profile(self):
        """Verify candidate can fetch and partially update their profile data."""
        self.client.force_authenticate(user=self.candidate_user)
        
        # Test GET profile endpoint
        response = self.client.get(self.candidate_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['skills'], '')

        # Test PATCH profile endpoint
        update_data = {"skills": "Python, Django, REST API", "expected_salary": "95000.00"}
        response = self.client.patch(self.candidate_url, update_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify changes hit the database
        self.candidate_profile.refresh_from_db()
        self.assertEqual(self.candidate_profile.skills, "Python, Django, REST API")

    def test_recruiter_cannot_access_candidate_profile(self):
        """Cross-role protection: Ensure recruiters are blocked from the candidate profile view."""
        self.client.force_authenticate(user=self.recruiter_user)
        response = self.client.get(self.candidate_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_candidate_profile_soft_delete(self):
        """Assert that deleting a profile sets 'is_deleted=True' rather than purging it from the DB."""
        self.client.force_authenticate(user=self.candidate_user)
        
        # Run DELETE action
        response = self.client.delete(self.candidate_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Verify database record still exists but is safely flagged
        self.candidate_profile.refresh_from_db()
        self.assertTrue(self.candidate_profile.is_deleted)

    def test_employer_cannot_self_verify(self):
        """Security Control: Recruiters shouldn't be able to turn on their own verified flag via client data."""
        self.client.force_authenticate(user=self.recruiter_user)
        
        # Attempt to patch 'is_verified' to True
        response = self.client.patch(self.employer_url, {"is_verified": True}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check that it remained False due to serializer read_only_fields policy
        self.employer_profile.refresh_from_db()
        self.assertFalse(self.employer_profile.is_verified)