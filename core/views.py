import os

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .permissions import IsEmployer, IsEmployerAndOwner
from rest_framework.generics import CreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from rest_framework import status, permissions
from rest_framework.pagination import PageNumberPagination
from rest_framework.generics import ListAPIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from .permissions import IsCandidate
from .serializers import ResumeUploadSerializer
from rest_framework.filters import SearchFilter, OrderingFilter
from .models import Job, User ,Employer,Candidate
from .serializers import *
from .serializers import JobSerializer, FullCandidateDetailSerializer, FullEmployerDetailSerializer
from django_filters.rest_framework import DjangoFilterBackend
from .permissions import IsEmployer, IsCandidate, IsAdmin
from rest_framework.generics import UpdateAPIView
from rest_framework.permissions import IsAuthenticated
from .models import Application
from .serializers import ApplicationStatusUpdateSerializer
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404

from .models import Job, Application
from .permissions import IsEmployer
from .serializers import (
    JobSerializer, 
    EmployerApplicantListSerializer, RecommendedJobSerializer,
    EmployerDashboardAnalyticsSerializer)
from rest_framework import generics, filters
from rest_framework.permissions import AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from .models import Job
from .serializers import JobSerializer
from core.filters import JobFilter

# 1. Candidate Applied Jobs & Timeline Tracking API
class CandidateAppliedJobsAPIView(ListAPIView):
    """
    Lists all jobs applied by the logged-in candidate with application status.
    """
    permission_classes = [permissions.IsAuthenticated, IsCandidate]
    serializer_class = CandidateApplicationTrackerSerializer

    def get_queryset(self):
        return Application.objects.filter(
            candidate=self.request.user
        ).select_related('job').order_by('-applied_at')


# 2. Application Status Timeline Details API
class CandidateApplicationDetailAPIView(APIView):
    """
    Returns timeline details for a specific application.
    """
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


# 3. Profile-Based Job Recommendation Engine (Basic Matching)
class CandidateRecommendedJobsAPIView(ListAPIView):
    """
    Recommends active jobs to candidates based on basic skill matching.
    """
    permission_classes = [permissions.IsAuthenticated, IsCandidate]
    serializer_class = RecommendedJobSerializer

    def get_queryset(self):
        user = self.request.user
        
        # Exclude jobs candidate already applied for
        applied_job_ids = Application.objects.filter(candidate=user).values_list('job_id', flat=True)
        
        queryset = Job.objects.filter(status='active').exclude(id__in=applied_job_ids)

        # Basic skill-matching filter if candidate profile skills exist
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
# 1. Job List API View (Paginated, Searchable & Filterable)
class JobListAPIView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = JobSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]

    # Filtering parameters
    filterset_fields = ['is_active', 'location']

    # Keyword Search fields
    search_fields = ['title', 'description', 'location']

    # Ordering fields
    ordering_fields = ['created_at', 'salary']
    ordering = ['-created_at']

    def get_queryset(self):
        # select_related avoids N+1 queries when accessing employer/user relationship
        return Job.objects.filter(is_deleted=False).select_related('employer', 'employer__user')

# Update CandidateDetailListView:
class CandidateDetailListView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CandidateProfileSerializer  # Updated name
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['is_deleted']
    search_fields = ['user__name', 'user__email', 'skills']
    ordering_fields = ['id']

    def get_queryset(self):
        return Candidate.objects.filter(is_deleted=False).select_related('user')

# Update EmployerDetailListView:
class EmployerDetailListView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = EmployerProfileSerializer  # Updated name
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['is_verified', 'is_deleted', 'domain']
    search_fields = ['company_name', 'domain', 'user__email']
    ordering_fields = ['company_name']

    def get_queryset(self):
        return Employer.objects.filter(is_deleted=False).select_related('user')

# ---------- Jobs ----------

class JobListAPIView(APIView):
    def get(self, request):
        jobs = Job.objects.all()
        serializer = JobSerializer(jobs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class JobCreateAPIView(APIView):
    permission_classes = [IsEmployer]

    def post(self, request):
        serializer = JobSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(posted_by=request.user.employer_profile)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ---------- Applications ----------

class ApplicationCreateAPIView(APIView):
    permission_classes = [IsCandidate]

    def post(self, request):
        serializer = ApplicationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(candidate=request.user.candidate_profile)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ---------- Admin ----------

class AdminUserListAPIView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        users = User.objects.all()
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


# ---------- Auth (Day 9, unchanged) ----------

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
        


#-------------------------------------------------------------------------------
# ---------- Profiles ----------

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



# ---------- Resume Upload API View ----------

class ResumeUploadAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, *args, **kwargs):
        candidate = request.user.candidate_profile
        file_obj = request.FILES.get('resume')

        if not file_obj:
            return Response({"error": "No resume file provided."}, status=status.HTTP_400_BAD_REQUEST)

        # File Size Validation (Max 5MB)
        if file_obj.size > 5 * 1024 * 1024:
            return Response({"error": "File size exceeds 5MB limit."}, status=status.HTTP_400_BAD_REQUEST)

        # Extension Validation
        ext = file_obj.name.split('.')[-1].lower()
        if ext not in ['pdf', 'doc', 'docx']:
            return Response({"error": "Unsupported file format. Allowed: .pdf, .doc, .docx"}, status=status.HTTP_400_BAD_REQUEST)

        # Safely remove old physical file if replacing
        if bool(candidate.resume):
            try:
                if os.path.isfile(candidate.resume.path):
                    os.remove(candidate.resume.path)
            except (ValueError, FileNotFoundError):
                pass  # Skip if no physical file exists on disk

        candidate.resume = file_obj
        candidate.save()

        return Response({
            "message": "Resume uploaded successfully!",
            "resume_url": candidate.resume.url
        }, status=status.HTTP_200_OK)



    # Create or use a standard pagination class
class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

class JobListAPIView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = JobSerializer
    pagination_class = StandardResultsSetPagination  # Enforces paginated wrapper
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]

    filterset_fields = ['company', 'title']
    search_fields = ['title', 'description', 'company']
    ordering_fields = ['created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        return Job.objects.all().order_by('-created_at')

from rest_framework.exceptions import NotFound

class EmployerJobCreateAPIView(CreateAPIView):
    permission_classes = [IsAuthenticated, IsEmployer]
    serializer_class = JobSerializer

    def perform_create(self, serializer):
        user = self.request.user
        if not user or not user.is_authenticated:
            raise NotFound("User account not found.")
        serializer.save(employer=user)

class EmployerJobDetailAPIView(RetrieveUpdateDestroyAPIView):
    """Allows recruiters to retrieve, update, or deactivate/close jobs they own."""
    permission_classes = [IsAuthenticated, IsEmployerAndOwner]
    serializer_class = JobSerializer
    queryset = Job.objects.all()

from django.shortcuts import get_object_or_404

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



class PublicJobListAPIView(generics.ListAPIView):
    """
    Public API for candidates to list, filter, and search active jobs.
    """
    authentication_classes = []  # <-- Disables token requirement for this endpoint
    permission_classes = [AllowAny]  # <-- Allows public unauthenticated access
    
    serializer_class = JobSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = JobFilter
    search_fields = ['title', 'company', 'skills_required', 'description']
    ordering_fields = ['created_at', 'salary_min', 'salary_max']
    ordering = ['-created_at']

    def get_queryset(self):
        return Job.objects.filter(status='active').select_related('employer')

class IsCandidatePermission(permissions.BasePermission):
    """
    Custom permission to ensure only candidates can submit applications.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'candidate'

class ApplyJobAPIView(generics.CreateAPIView):
    """
    API for candidates to apply for an active job.
    """
    serializer_class = ApplicationCreateSerializer
    permission_classes = [IsCandidatePermission]

    def perform_create(self, serializer):
        user = self.request.user
        
        # Bind candidate profile's uploaded resume as a snapshot if available
        resume = None
        if hasattr(user, 'candidate_profile') and user.candidate_profile.resume:
            resume = user.candidate_profile.resume

        serializer.save(candidate=user, resume_snapshot=resume)


class CandidateApplicationListAPIView(generics.ListAPIView):
    """
    API for candidates to view their application history / tracking list.
    """
    serializer_class = ApplicationDetailSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Ownership check: Candidates can only access their own applications
        return Application.objects.filter(candidate=self.request.user).select_related('job')


# 1. Employer Own Jobs Management API
class EmployerMyJobsAPIView(ListAPIView):
    permission_classes = [permissions.IsAuthenticated, IsEmployer]
    serializer_class = JobSerializer

    def get_queryset(self):
        # Removed non-existent 'is_deleted' filter
        return Job.objects.filter(
            employer=self.request.user
        ).order_by('-created_at')


# 2. Employer Candidate Pipeline & Applicant Filtering API
class EmployerCandidatePipelineAPIView(ListAPIView):
    permission_classes = [permissions.IsAuthenticated, IsEmployer]
    serializer_class = EmployerApplicantListSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = Application.objects.filter(
            job__employer=user
        ).select_related('candidate', 'job')

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


# 3. Employer Analytics & Metrics API
class EmployerDashboardAnalyticsAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsEmployer]

    def get(self, request):
        user = request.user
        
        # Removed non-existent 'is_deleted' filter
        employer_jobs = Job.objects.filter(employer=user)
        total_jobs = employer_jobs.count()
        active_jobs = employer_jobs.filter(status='active').count()

        employer_apps = Application.objects.filter(job__employer=user)
        total_apps = employer_apps.count()

        # ATS Status Breakdown
        status_counts = employer_apps.values('status').annotate(count=Count('status'))
        status_dict = {item['status']: item['count'] for item in status_counts}

        # Shortlist Ratio Calculation
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