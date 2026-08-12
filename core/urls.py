from django.urls import path
from .views import (
    # Auth Views
    ExtractResumeTextAPIView,
    SignupAPIView,
    LoginAPIView,
    LogoutAPIView,
    
    # Profile & Resume Views
    CandidateProfileAPIView,
    EmployerProfileAPIView,
    CandidateDetailListView,
    EmployerDetailListView,
    ResumeUploadAPIView,
    
    # Job Listing Views
    JobListAPIView,
    PublicJobListAPIView,
    
    # Employer Dashboard & Pipeline Views
    EmployerJobCreateAPIView,
    EmployerJobDetailAPIView,
    EmployerMyJobsAPIView,
    EmployerCandidatePipelineAPIView,
    EmployerDashboardAnalyticsAPIView,
    ApplicationStatusUpdateAPIView,
    
    # Candidate Dashboard & Application Views (Day 21)
    ApplicationCreateAPIView,
    ApplyJobAPIView,
    CandidateApplicationListAPIView,
    CandidateAppliedJobsAPIView,
    CandidateApplicationDetailAPIView,
    CandidateRecommendedJobsAPIView,
    
    # Admin Control Panel Views (Day 22)
    AdminUserListAPIView,
    AdminVerifyEmployerAPIView,
    AdminSystemStatsAPIView,
    AdminToggleUserStatusAPIView,
    AdminModerateJobAPIView,
    AdminAuditLogListAPIView
)

urlpatterns = [
    # Auth Routes
    path('auth/signup/', SignupAPIView.as_view(), name='signup'),
    path('auth/login/', LoginAPIView.as_view(), name='login'),
    path('auth/logout/', LogoutAPIView.as_view(), name='logout'),

    # Profile & Resume Management Routes
    path('profile/candidate/', CandidateProfileAPIView.as_view(), name='candidate-profile'),
    path('profile/employer/', EmployerProfileAPIView.as_view(), name='employer-profile'),
    path('profiles/candidates/', CandidateDetailListView.as_view(), name='candidate-list'),
    path('profiles/employers/', EmployerDetailListView.as_view(), name='employer-list'),
    path('candidate/resume/upload/', ResumeUploadAPIView.as_view(), name='resume-upload'),

    # Jobs & Search Routes
    path('jobs/', JobListAPIView.as_view(), name='job-list'),
    path('jobs/public/', PublicJobListAPIView.as_view(), name='public-job-list'),

    # Employer Management & Pipeline Routes
    path('employer/jobs/create/', EmployerJobCreateAPIView.as_view(), name='employer-job-create'),
    path('employer/jobs/<int:pk>/', EmployerJobDetailAPIView.as_view(), name='employer-job-detail'),
    path('employer/dashboard/my-jobs/', EmployerMyJobsAPIView.as_view(), name='employer-my-jobs'),
    path('employer/dashboard/pipeline/', EmployerCandidatePipelineAPIView.as_view(), name='employer-pipeline'),
    path('employer/dashboard/analytics/', EmployerDashboardAnalyticsAPIView.as_view(), name='employer-analytics'),
    path('applications/<int:pk>/status/', ApplicationStatusUpdateAPIView.as_view(), name='application-status-update'),

    # Candidate Application & Dashboard Routes (Day 21)
    path('applications/create/', ApplicationCreateAPIView.as_view(), name='application-create'),
    path('jobs/apply/', ApplyJobAPIView.as_view(), name='apply-job'),
    path('candidate/applications/', CandidateApplicationListAPIView.as_view(), name='candidate-applications'),
    path('candidate/dashboard/applied-jobs/', CandidateAppliedJobsAPIView.as_view(), name='candidate-applied-jobs'),
    path('candidate/dashboard/applications/<int:pk>/', CandidateApplicationDetailAPIView.as_view(), name='candidate-application-detail'),
    path('candidate/dashboard/recommendations/', CandidateRecommendedJobsAPIView.as_view(), name='candidate-recommendations'),

    # Admin Control Panel Routes (Day 22)
    path('admin/users/', AdminUserListAPIView.as_view(), name='admin-user-list'),
    path('admin/employer/<int:employer_id>/verify/', AdminVerifyEmployerAPIView.as_view(), name='admin-verify-employer'),
    path('admin/stats/', AdminSystemStatsAPIView.as_view(), name='admin-stats'),
    path('admin/users/<int:pk>/toggle-status/', AdminToggleUserStatusAPIView.as_view(), name='admin-toggle-user'),
    path('admin/jobs/<int:pk>/moderate/', AdminModerateJobAPIView.as_view(), name='admin-moderate-job'),
    path('admin/audit-logs/', AdminAuditLogListAPIView.as_view(), name='admin-audit-logs'),

    path('candidate/resume/extract-text/', ExtractResumeTextAPIView.as_view(), name='resume-extract-text'),
]