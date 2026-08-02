from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import *

urlpatterns = [
    # Auth Endpoints
    path('auth/signup/', SignupAPIView.as_view(), name='signup'),
    path('auth/login/', LoginAPIView.as_view(), name='login'),
    path('auth/logout/', LogoutAPIView.as_view(), name='logout'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # Profile Endpoints
    path('profile/candidate/', CandidateProfileAPIView.as_view(), name='candidate-profile'),
    path('profile/candidate/resume/', ResumeUploadAPIView.as_view(), name='resume-upload'),
    path('profile/employer/', EmployerProfileAPIView.as_view(), name='employer-profile'),

    # Public Job Discovery & Search (Day 17)
    path('jobs/', PublicJobListAPIView.as_view(), name='public-job-list'),

    # Employer Job Management
    path('employer/jobs/create/', EmployerJobCreateAPIView.as_view(), name='employer-job-create'),
    path('employer/jobs/<int:pk>/', EmployerJobDetailAPIView.as_view(), name='employer-job-detail'),

    # Application & Admin Endpoints
    path('applications/create/', ApplicationCreateAPIView.as_view(), name='application-create'),
    path('admin/users/', AdminUserListAPIView.as_view(), name='admin-users'),
    path('admin/employers/<int:employer_id>/verify/', AdminVerifyEmployerAPIView.as_view(), name='admin-verify-employer'),
]