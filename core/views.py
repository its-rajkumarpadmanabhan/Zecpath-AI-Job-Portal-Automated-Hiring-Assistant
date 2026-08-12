import os
from django.db.models import Count, Q
from django.contrib.auth import authenticate
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend

from rest_framework import status, permissions, generics, filters
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView, CreateAPIView, RetrieveUpdateDestroyAPIView, UpdateAPIView
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework_simplejwt.tokens import RefreshToken

# Models
from .models import Job, User, Employer, Candidate, Application, AuditLog

# Custom Permissions
from .permissions import (
    IsEmployer, 
    IsEmployerAndOwner, 
    IsCandidate, 
    IsAdmin, 
    IsAdminUserRole
)

# Filters
from core.filters import JobFilter

# Serializers
from .serializers import (
    JobSerializer,
    SignupSerializer,
    UserSerializer,
    CandidateProfileSerializer,
    EmployerProfileSerializer,
    ResumeUploadSerializer,
    ApplicationSerializer,
    ApplicationCreateSerializer,
    ApplicationDetailSerializer,
    ApplicationStatusUpdateSerializer,
    EmployerApplicantListSerializer,
    EmployerDashboardAnalyticsSerializer,
    CandidateApplicationTrackerSerializer,
    RecommendedJobSerializer,
    AuditLogSerializer,
    AdminUserManagementSerializer,
    AdminJobModerationSerializer
)

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.parsers import MultiPartParser, FormParser

from .permissions import IsCandidate
from .utils.resume_parser import parse_resume_file

class ExtractResumeTextAPIView(APIView):
    """
    API endpoint for candidates to upload or re-parse their resume file and return cleaned text.
    """
    permission_classes = [permissions.IsAuthenticated, IsCandidate]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        file_obj = request.FILES.get('resume')

        # Fallback to candidate's existing saved resume if no file is uploaded in request
        if not file_obj:
            candidate_profile = getattr(request.user, 'candidate_profile', None)
            if candidate_profile and candidate_profile.resume:
                file_obj = candidate_profile.resume
            else:
                return Response(
                    {"error": "No resume file provided or found in profile."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        try:
            extracted_text = parse_resume_file(file_obj)
            return Response({
                "message": "Resume text successfully extracted and cleaned.",
                "character_count": len(extracted_text),
                "extracted_text": extracted_text
            }, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": f"Failed to process file: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
# =============================================================================
# 1. AUTHENTICATION VIEWS
# =============================================================================

class SignupAPIView(APIView):
    permission_classes = []

    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            return Response({
                "user": serializer.data,
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginAPIView(APIView):
    permission_classes = []

    def post(self, request):
        user = authenticate(
            request,
            email=request.data.get("email"),
            password=request.data.get("password"),
        )
        if user is None:
            return Response({"detail": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
        refresh = RefreshToken.for_user(user)
        return Response({
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }, status=status.HTTP_200_OK)


class LogoutAPIView(APIView):
    def post(self, request):
        try:
            token = RefreshToken(request.data["refresh"])
            token.blacklist()
            return Response(status=status.HTTP_205_RESET_CONTENT)
        except Exception:
            return Response(status=status.HTTP_400_BAD_REQUEST)


# =============================================================================
# 2. PROFILE & RESUME MANAGEMENT VIEWS
# =============================================================================

class CandidateProfileAPIView(APIView):
    permission_classes = [IsCandidate]

    def get(self, request):
        profile = request.user.candidate_profile
        return Response(CandidateProfileSerializer(profile).data)

    def patch(self, request):
        profile = request.user.candidate_profile
        serializer = CandidateProfileSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request):
        profile = request.user.candidate_profile
        profile.is_deleted = True
        profile.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class EmployerProfileAPIView(APIView):
    permission_classes = [IsEmployer]

    def get(self, request):
        profile = request.user.employer_profile
        return Response(EmployerProfileSerializer(profile).data)

    def patch(self, request):
        profile = request.user.employer_profile
        serializer = EmployerProfileSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request):
        profile = request.user.employer_profile
        profile.is_deleted = True
        profile.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CandidateDetailListView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CandidateProfileSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['is_deleted']
    search_fields = ['user__name', 'user__email', 'skills']
    ordering_fields = ['id']

    def get_queryset(self):
        return Candidate.objects.filter(is_deleted=False).select_related('user')


class EmployerDetailListView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = EmployerProfileSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['is_verified', 'is_deleted', 'domain']
    search_fields = ['company_name', 'domain', 'user__email']
    ordering_fields = ['company_name']

    def get_queryset(self):
        return Employer.objects.filter(is_deleted=False).select_related('user')


class ResumeUploadAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, *args, **kwargs):
        candidate = request.user.candidate_profile
        file_obj = request.FILES.get('resume')

        if not file_obj:
            return Response({"error": "No resume file provided."}, status=status.HTTP_400_BAD_REQUEST)

        if file_obj.size > 5 * 1024 * 1024:
            return Response({"error": "File size exceeds 5MB limit."}, status=status.HTTP_400_BAD_REQUEST)

        ext = file_obj.name.split('.')[-1].lower()
        if ext not in ['pdf', 'doc', 'docx']:
            return Response({"error": "Unsupported file format. Allowed: .pdf, .doc, .docx"}, status=status.HTTP_400_BAD_REQUEST)

        if bool(candidate.resume):
            try:
                if os.path.isfile(candidate.resume.path):
                    os.remove(candidate.resume.path)
            except (ValueError, FileNotFoundError):
                pass

        candidate.resume = file_obj
        candidate.save()

        return Response({
            "message": "Resume uploaded successfully!",
            "resume_url": candidate.resume.url
        }, status=status.HTTP_200_OK)


# =============================================================================
# 3. PUBLIC & SEARCHABLE JOB VIEWS
# =============================================================================

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class JobListAPIView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = JobSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]

    filterset_fields = ['company', 'title']
    search_fields = ['title', 'description', 'company']
    ordering_fields = ['created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        return Job.objects.all().order_by('-created_at')


class PublicJobListAPIView(generics.ListAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    serializer_class = JobSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = JobFilter
    search_fields = ['title', 'company', 'skills_required', 'description']
    ordering_fields = ['created_at', 'salary_min', 'salary_max']
    ordering = ['-created_at']

    def get_queryset(self):
        return Job.objects.filter(status='active').select_related('employer')


# =============================================================================
# 4. EMPLOYER MANAGEMENT & ANALYTICS VIEWS
# =============================================================================

class EmployerJobCreateAPIView(CreateAPIView):
    permission_classes = [IsAuthenticated, IsEmployer]
    serializer_class = JobSerializer

    def perform_create(self, serializer):
        user = self.request.user
        serializer.save(employer=user)


class EmployerJobDetailAPIView(RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, IsEmployerAndOwner]
    serializer_class = JobSerializer
    queryset = Job.objects.all()


class EmployerMyJobsAPIView(ListAPIView):
    permission_classes = [permissions.IsAuthenticated, IsEmployer]
    serializer_class = JobSerializer

    def get_queryset(self):
        return Job.objects.filter(employer=self.request.user).order_by('-created_at')


class EmployerCandidatePipelineAPIView(ListAPIView):
    permission_classes = [permissions.IsAuthenticated, IsEmployer]
    serializer_class = EmployerApplicantListSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = Application.objects.filter(job__employer=user).select_related('candidate', 'job')

        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)

        search_param = self.request.query_params.get('search')
        if search_param:
            queryset = queryset.filter(
                Q(candidate__name__icontains=search_param) |
                Q(candidate__email__icontains=search_param) |
                Q(job__title__icontains=search_param)
            )

        return queryset


class EmployerDashboardAnalyticsAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsEmployer]

    def get(self, request):
        user = request.user
        employer_jobs = Job.objects.filter(employer=user)
        total_jobs = employer_jobs.count()
        active_jobs = employer_jobs.filter(status='active').count()

        employer_apps = Application.objects.filter(job__employer=user)
        total_apps = employer_apps.count()

        status_counts = employer_apps.values('status').annotate(count=Count('status'))
        status_dict = {item['status']: item['count'] for item in status_counts}

        shortlisted_count = status_dict.get('shortlisted', 0) + status_dict.get('hired', 0)
        shortlist_ratio = round((shortlisted_count / total_apps * 100), 2) if total_apps > 0 else 0.0

        analytics_data = {
            "total_jobs_posted": total_jobs,
            "active_jobs_count": active_jobs,
            "total_applications_received": total_apps,
            "shortlist_ratio": shortlist_ratio,
            "applications_by_status": status_dict
        }

        serializer = EmployerDashboardAnalyticsSerializer(analytics_data)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ApplicationStatusUpdateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk):
        application = get_object_or_404(Application, pk=pk)
        serializer = ApplicationStatusUpdateSerializer(
            application, 
            data=request.data, 
            partial=True,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response({
            "message": "Status updated successfully",
            "data": serializer.data
        }, status=status.HTTP_200_OK)


# =============================================================================
# 5. CANDIDATE APPLICATION & DASHBOARD VIEWS (DAY 21)
# =============================================================================

class ApplyJobAPIView(generics.CreateAPIView):
    serializer_class = ApplicationCreateSerializer
    permission_classes = [permissions.IsAuthenticated, IsCandidate]

    def perform_create(self, serializer):
        user = self.request.user
        resume = None
        if hasattr(user, 'candidate_profile') and user.candidate_profile.resume:
            resume = user.candidate_profile.resume

        serializer.save(candidate=user, resume_snapshot=resume)


class CandidateApplicationListAPIView(generics.ListAPIView):
    serializer_class = ApplicationDetailSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Application.objects.filter(candidate=self.request.user).select_related('job')


class CandidateAppliedJobsAPIView(ListAPIView):
    permission_classes = [permissions.IsAuthenticated, IsCandidate]
    serializer_class = CandidateApplicationTrackerSerializer

    def get_queryset(self):
        return Application.objects.filter(
            candidate=self.request.user
        ).select_related('job').order_by('-applied_at')


class CandidateApplicationDetailAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsCandidate]

    def get(self, request, pk):
        try:
            application = Application.objects.select_related('job').get(
                pk=pk, candidate=request.user
            )
        except Application.DoesNotExist:
            return Response(
                {"detail": "Application not found or unauthorized."}, 
                status=status.HTTP_404_NOT_FOUND
            )

        timeline = [
            {"stage": "applied", "label": "Application Submitted", "completed": True},
            {"stage": "shortlisted", "label": "Under Review / Shortlisted", "completed": application.status in ['shortlisted', 'hired']},
            {"stage": "hired", "label": "Hired", "completed": application.status == 'hired'}
        ]

        data = {
            "application_id": application.id,
            "job_title": application.job.title,
            "company": application.job.company,
            "current_status": application.status,
            "applied_at": application.applied_at,
            "timeline": timeline
        }
        return Response(data, status=status.HTTP_200_OK)


class CandidateRecommendedJobsAPIView(ListAPIView):
    permission_classes = [permissions.IsAuthenticated, IsCandidate]
    serializer_class = RecommendedJobSerializer

    def get_queryset(self):
        user = self.request.user
        applied_job_ids = Application.objects.filter(candidate=user).values_list('job_id', flat=True)
        queryset = Job.objects.filter(status='active').exclude(id__in=applied_job_ids)

        user_skills = getattr(user, 'skills', '')
        if user_skills:
            skill_list = [s.strip() for s in user_skills.split(',') if s.strip()]
            query = Q()
            for skill in skill_list:
                query |= Q(skills_required__icontains=skill) | Q(title__icontains=skill)
            
            matched_qs = queryset.filter(query)
            if matched_qs.exists():
                return matched_qs.order_by('-created_at')

        return queryset.order_by('-created_at')


# =============================================================================
# 6. ADMIN CONTROL PANEL VIEWS (DAY 22)
# =============================================================================

class AdminUserListAPIView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        users = User.objects.all()
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AdminVerifyEmployerAPIView(APIView):
    permission_classes = [IsAdmin]

    def patch(self, request, employer_id):
        try:
            employer = Employer.objects.get(id=employer_id)
        except Employer.DoesNotExist:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        employer.is_verified = True
        employer.save()
        return Response(EmployerProfileSerializer(employer).data)


class AdminSystemStatsAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminUserRole]

    def get(self, request):
        stats = {
            "total_users": User.objects.count(),
            "total_candidates": User.objects.filter(role="candidate").count(),
            "total_employers": User.objects.filter(role="employer").count(),
            "total_jobs_posted": Job.objects.count(),
            "active_jobs": Job.objects.filter(status="active").count(),
            "total_applications": Application.objects.count(),
            "applications_by_status": dict(
                Application.objects.values_list('status').annotate(count=Count('status'))
            )
        }
        return Response(stats, status=status.HTTP_200_OK)


class AdminToggleUserStatusAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminUserRole]

    def patch(self, request, pk):
        try:
            target_user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        target_user.is_active = not target_user.is_active
        target_user.save()

        action_str = "unblocked" if target_user.is_active else "blocked"
        
        AuditLog.objects.create(
            admin=request.user,
            target_user=target_user,
            action=f"User {action_str.capitalize()}",
            details=f"Admin toggled active status for user {target_user.email} to {target_user.is_active}."
        )

        return Response(
            {"detail": f"User {target_user.email} has been successfully {action_str}."},
            status=status.HTTP_200_OK
        )


class AdminModerateJobAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminUserRole]

    def delete(self, request, pk):
        try:
            job = Job.objects.get(pk=pk)
        except Job.DoesNotExist:
            return Response({"detail": "Job not found."}, status=status.HTTP_404_NOT_FOUND)

        job_title = job.title
        job.delete()

        AuditLog.objects.create(
            admin=request.user,
            action="Job Deleted (Spam Moderation)",
            details=f"Admin removed spam job post '{job_title}' (ID: {pk})."
        )

        return Response(
            {"detail": f"Job '{job_title}' removed successfully."},
            status=status.HTTP_200_OK
        )


class AdminAuditLogListAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminUserRole]

    def get(self, request):
        logs = AuditLog.objects.all().order_by('-created_at')[:50]
        serializer = AuditLogSerializer(logs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    


class ApplicationCreateAPIView(generics.CreateAPIView):
    serializer_class = ApplicationCreateSerializer
    permission_classes = [permissions.IsAuthenticated, IsCandidate]

    def perform_create(self, serializer):
        user = self.request.user
        resume = None
        if hasattr(user, 'candidate_profile') and user.candidate_profile.resume:
            resume = user.candidate_profile.resume

        serializer.save(candidate=user, resume_snapshot=resume)