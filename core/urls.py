from django.urls import path
from .views import (
    # Auth Views
    EmployerRankedCandidatesAPIView,
    ExtractResumeTextAPIView,
    JobMatchScoreAPIView,
    ManualOverrideStatusAPIView,
    ParseStructuredResumeAPIView,
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
    AdminAuditLogListAPIView,
    BatchAutoShortlistAPIView,

    # Day 32 Async Views
    AsyncParseResumeAPIView,
    AsyncBatchAutoScreenAPIView
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

    # Day 23    
    path('candidate/resume/extract-text/', ExtractResumeTextAPIView.as_view(), name='resume-extract-text'),

    # Day 24 Structured Resume Parsing Route
    path('candidate/resume/parse-structured/', ParseStructuredResumeAPIView.as_view(), name='resume-parse-structured'),

    # Day 25 ATS Matching & Ranking Routes
    path('jobs/<int:job_id>/match-score/', JobMatchScoreAPIView.as_view(), name='job-match-score'),
    path('employer/jobs/<int:job_id>/ranked-candidates/', EmployerRankedCandidatesAPIView.as_view(), name='employer-ranked-candidates'),



    # Day 26 Automation & Workflow Routes
    path('employer/jobs/<int:job_id>/auto-screen/', BatchAutoShortlistAPIView.as_view(), name='employer-auto-screen'),
    path('employer/applications/<int:application_id>/override-status/', ManualOverrideStatusAPIView.as_view(), name='employer-override-status'),

    # Day 32 Background Jobs & Async Routes (Celery + Redis)
    path('candidate/resume/parse-async/', AsyncParseResumeAPIView.as_view(), name='resume-parse-async'),
    path('employer/jobs/<int:job_id>/async-auto-screen/', AsyncBatchAutoScreenAPIView.as_view(), name='employer-async-auto-screen'),
]

# Quick endpoints for Postman testing
from rest_framework import viewsets
from .models import AICall, AIInterviewSession, CallLog
from .serializers import AICallSerializer, AIInterviewSessionSerializer, CallLogSerializer, AIQuestionSerializer, AIAnswerSerializer
from .models import AIQuestion, AIAnswer
from rest_framework.routers import DefaultRouter

class AICallViewSet(viewsets.ModelViewSet):
    queryset = AICall.objects.all()
    serializer_class = AICallSerializer

class AIInterviewSessionViewSet(viewsets.ModelViewSet):
    queryset = AIInterviewSession.objects.all()
    serializer_class = AIInterviewSessionSerializer

class AIQuestionViewSet(viewsets.ModelViewSet):
    queryset = AIQuestion.objects.all()
    serializer_class = AIQuestionSerializer

class AIAnswerViewSet(viewsets.ModelViewSet):
    queryset = AIAnswer.objects.all()
    serializer_class = AIAnswerSerializer

class CallLogViewSet(viewsets.ModelViewSet):
    queryset = CallLog.objects.all()
    serializer_class = CallLogSerializer

router = DefaultRouter()
router.register(r'testing/ai-calls', AICallViewSet, basename='test-aicalls')
router.register(r'testing/ai-sessions', AIInterviewSessionViewSet, basename='test-aisessions')
router.register(r'testing/ai-questions', AIQuestionViewSet, basename='test-aiquestions')
router.register(r'testing/ai-answers', AIAnswerViewSet, basename='test-aianswers')
router.register(r'testing/call-logs', CallLogViewSet, basename='test-calllogs')


urlpatterns += router.urls

from .views import (
    EmployerJobAICallsAPIView,
    AICallRetryAPIView,
    AICallCancelAPIView,
    AIVoiceTriggerCallAPIView,
    AIVoiceSynthesizeAPIView,
    AIVoiceTranscribeAPIView
)

urlpatterns += [
    path('employer/jobs/<int:job_id>/ai-calls/', EmployerJobAICallsAPIView.as_view(), name='employer-job-ai-calls'),
    path('aicalls/<int:pk>/retry/', AICallRetryAPIView.as_view(), name='aicall-retry'),
    path('aicalls/<int:pk>/cancel/', AICallCancelAPIView.as_view(), name='aicall-cancel'),
    path('voice/trigger-call/', AIVoiceTriggerCallAPIView.as_view(), name='voice-trigger-call'),
    path('voice/synthesize-speech/', AIVoiceSynthesizeAPIView.as_view(), name='voice-synthesize-speech'),
    path('voice/transcribe-audio/', AIVoiceTranscribeAPIView.as_view(), name='voice-transcribe-audio'),
]

from .views import AIEvaluateAnswerAPIView, AISessionScoreReportAPIView

urlpatterns += [
    path('testing/ai-questions/<int:question_id>/evaluate/', AIEvaluateAnswerAPIView.as_view(), name='ai-evaluate-answer'),
    path('testing/ai-sessions/<int:session_id>/scores/', AISessionScoreReportAPIView.as_view(), name='ai-session-scores'),
]

from .views import (
    AvailableSlotsAPIView,
    BookInterviewAPIView,
    RescheduleInterviewAPIView
)

urlpatterns += [
    path('scheduling/slots/available/', AvailableSlotsAPIView.as_view(), name='scheduling-slots-available'),
    path('scheduling/book/', BookInterviewAPIView.as_view(), name='scheduling-book'),
    path('scheduling/<int:schedule_id>/reschedule/', RescheduleInterviewAPIView.as_view(), name='scheduling-reschedule'),
]

from .views import (
    TriggerManualReminderAPIView,
    ReminderScanCronAPIView,
    ReminderTrackingLogsAPIView
)

urlpatterns += [
    path('scheduling/reminders/scan/', ReminderScanCronAPIView.as_view(), name='scheduling-reminders-scan'),
    path('scheduling/<int:schedule_id>/send-reminder/', TriggerManualReminderAPIView.as_view(), name='scheduling-send-reminder'),
    path('scheduling/<int:schedule_id>/reminder-logs/', ReminderTrackingLogsAPIView.as_view(), name='scheduling-reminder-logs'),
]

from .views import GenerateCandidateReportAPIView, CandidateReportSummaryAPIView

urlpatterns += [
    path('recruiter/applications/<int:application_id>/generate-report/', GenerateCandidateReportAPIView.as_view(), name='recruiter-generate-report'),
    path('recruiter/applications/<int:application_id>/report-summary/', CandidateReportSummaryAPIView.as_view(), name='recruiter-report-summary'),
]

# Day 41: Recruiter Analytics & Funnel Routes
from .views import (
    RecruiterFunnelAnalyticsAPIView,
    RecruiterJobPerformanceAPIView
)

urlpatterns += [
    path('recruiter/analytics/funnel/', RecruiterFunnelAnalyticsAPIView.as_view(), name='recruiter-analytics-funnel'),
    path('recruiter/analytics/jobs-performance/', RecruiterJobPerformanceAPIView.as_view(), name='recruiter-analytics-jobs-performance'),
]

# Day 42: Audit & Security Monitoring Routes
from .views import (
    AuditTrailLogsAPIView,
    SecurityAndFailureLogsAPIView,
    CreateAuditOrSecurityEventAPIView,
)

urlpatterns += [
    path('monitoring/audit-trails/', AuditTrailLogsAPIView.as_view(), name='monitoring-audit-trails'),
    path('monitoring/security-logs/', SecurityAndFailureLogsAPIView.as_view(), name='monitoring-security-logs'),
    path('monitoring/log-event/', CreateAuditOrSecurityEventAPIView.as_view(), name='monitoring-log-event'),
]

# Day 43: Security Shield — Throttling, Encryption & Attack Simulation Routes
from .views import (
    EncryptedDataHandlingAPIView,
    SecurityAttackSimulationAPIView,
    SecurityReportAuditAPIView,
)

urlpatterns += [
    path('security/encrypt-sensitive-data/', EncryptedDataHandlingAPIView.as_view(), name='security-encrypt-sensitive-data'),
    path('security/simulate-attack/', SecurityAttackSimulationAPIView.as_view(), name='security-simulate-attack'),
    path('security/report/', SecurityReportAuditAPIView.as_view(), name='security-report'),
]

# Day 44: Load Testing, Stress Benchmarks & Query Optimization Routes
from .views import SystemLoadBenchmarkAPIView, StressTestTriggerAPIView

urlpatterns += [
    path('load-test/benchmark-report/', SystemLoadBenchmarkAPIView.as_view(), name='load-test-benchmark-report'),
    path('load-test/ping/', StressTestTriggerAPIView.as_view(), name='load-test-ping'),
]

# Day 45: Phase Review & AI Backend Readiness Routes
from .views import (
    AIBackendReadinessAPIView,
    SystemOverviewDocumentationAPIView,
)

urlpatterns += [
    path('system/readiness-check/', AIBackendReadinessAPIView.as_view(), name='system-readiness-check'),
    path('system/api-overview/', SystemOverviewDocumentationAPIView.as_view(), name='system-api-overview'),
]

# Day 46: SaaS Monetization, Subscriptions & Billing Routes
from .views import (
    SubscriptionPlanListAPIView,
    CurrentSubscriptionDetailAPIView,
    MockSubscribePlanAPIView
)

urlpatterns += [
    path('billing/plans/', SubscriptionPlanListAPIView.as_view(), name='billing-plans'),
    path('billing/my-subscription/', CurrentSubscriptionDetailAPIView.as_view(), name='billing-my-subscription'),
    path('billing/subscribe/', MockSubscribePlanAPIView.as_view(), name='billing-subscribe'),
]

# Day 47: Payment Gateways (Stripe & Razorpay) Routes
from .views import (
    CreatePaymentOrderAPIView,
    VerifyPaymentAPIView,
    PaymentWebhookAPIView,
)

urlpatterns += [
    path('payments/create-order/', CreatePaymentOrderAPIView.as_view(), name='payment-create-order'),
    path('payments/verify/', VerifyPaymentAPIView.as_view(), name='payment-verify'),
    path('payments/webhook/', PaymentWebhookAPIView.as_view(), name='payment-webhook'),
]



