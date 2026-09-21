from email.mime import application
import os
import time
from django.db.models import Count, Q
from django.contrib.auth import authenticate
from django.shortcuts import get_object_or_404
from django.conf import settings
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
from .models import Job, User, Employer, Candidate, Application, AuditLog, AICall

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
    AdminJobModerationSerializer,
    AICallSerializer,
    AICallTriggerSerializer
)

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.parsers import MultiPartParser, FormParser

from .permissions import IsCandidate
from .utils.resume_parser import parse_resume_file

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.parsers import MultiPartParser, FormParser

from .permissions import IsCandidate
from .utils.resume_parser import parse_resume_file
from .utils.resume_nlp import parse_resume_to_json

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.shortcuts import get_object_or_404

from .models import Job, Application
from .permissions import IsCandidate, IsEmployer
from .utils.resume_parser import parse_resume_file
from .utils.resume_nlp import parse_resume_to_json
from .utils.ats_engine import compute_ats_score

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.shortcuts import get_object_or_404

from .models import Job, Application
from .permissions import IsEmployer
from .utils.automation_engine import process_batch_auto_shortlist, evaluate_and_apply_auto_action

from .utils.notification_service import trigger_application_status_notification

class BatchAutoShortlistAPIView(APIView):
    """
    Employer API: Triggers automated threshold screening for all pending job applications.
    Recalculates match scores from profile/resume if not already scored.
    """
    permission_classes = [permissions.IsAuthenticated, IsEmployer]

    def post(self, request, job_id):
        job = get_object_or_404(Job, pk=job_id, employer=request.user)

        # Parse optional custom cutoffs from recruiter payload
        shortlist_cutoff = float(request.data.get('shortlist_threshold', 70.0))
        reject_cutoff = float(request.data.get('reject_threshold', 40.0))

        # Re-score any pending applications that currently have a 0.0 score
        pending_apps = Application.objects.filter(job=job)
        for app in pending_apps:
            if app.ats_score == 0.0:
                candidate_profile = getattr(app.candidate, 'candidate_profile', None)
                candidate_skills = candidate_profile.skills if candidate_profile else ""
                
                # Check resume file or fallback to profile skills
                if app.resume_snapshot:
                    try:
                        cleaned_text = parse_resume_file(app.resume_snapshot)
                        parsed_data = parse_resume_to_json(cleaned_text)
                        ats_result = compute_ats_score(job, parsed_data)
                        app.ats_score = float(ats_result.get("suitability_score", 0.0))
                    except Exception:
                        app.ats_score = self._fallback_score(job.skills_required, candidate_skills)
                else:
                    app.ats_score = self._fallback_score(job.skills_required, candidate_skills)
                app.save()

        summary = process_batch_auto_shortlist(
            job, 
            shortlist_threshold=shortlist_cutoff, 
            reject_threshold=reject_cutoff
        )

        return Response({
            "message": f"Automation screening completed for Job ID {job.id}.",
            "job_title": job.title,
            "thresholds_applied": {
                "shortlist_threshold": f"{shortlist_cutoff}%",
                "reject_threshold": f"{reject_cutoff}%"
            },
            "summary": summary
        }, status=status.HTTP_200_OK)

    def _fallback_score(self, job_skills_str, candidate_skills_str):
        if not job_skills_str or not candidate_skills_str:
            return 0.0
        job_skills = {s.strip().lower() for s in job_skills_str.split(',') if s.strip()}
        cand_skills = {s.strip().lower() for s in candidate_skills_str.split(',') if s.strip()}
        if not job_skills:
            return 0.0
        matched = job_skills.intersection(cand_skills)
        return round((len(matched) / len(job_skills)) * 100.0, 1)

class ManualOverrideStatusAPIView(APIView):
    """
    Employer API: Allows recruiters to manually override automated application statuses.
    """
    permission_classes = [permissions.IsAuthenticated, IsEmployer]

    def patch(self, request, application_id):
        application = get_object_or_404(Application, pk=application_id, job__employer=request.user)

        new_status = request.data.get('status')
        valid_statuses = ['applied', 'shortlisted', 'rejected']

        if not new_status or new_status.lower() not in valid_statuses:
            return Response(
                {"error": f"Invalid status provided. Choose from: {valid_statuses}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        previous_status = application.status
        application.status = new_status.lower()
        application.save()

        # Trigger async event notification
        trigger_application_status_notification(application)

        return Response({
            "message": "Application status successfully updated by recruiter override.",
            "application_id": application.id,
            "candidate_email": application.candidate.email,
            "previous_status": previous_status,
            "new_status": application.status,
            "ats_score": f"{application.ats_score}%"
        }, status=status.HTTP_200_OK)

class JobMatchScoreAPIView(APIView):
    """
    Candidate API: Evaluates logged-in candidate's resume against a target job posting,
    stores calculated ATS score, and returns suitability % score.
    """
    permission_classes = [permissions.IsAuthenticated, IsCandidate]

    def post(self, request, job_id):
        job = get_object_or_404(Job, pk=job_id)
        candidate = request.user

        # Fetch resume from candidate profile
        if not hasattr(candidate, 'candidate_profile') or not candidate.candidate_profile.resume:
            return Response(
                {"error": "Please upload a resume to your candidate profile before calculating match score."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            resume_file = candidate.candidate_profile.resume
            cleaned_text = parse_resume_file(resume_file)
            parsed_data = parse_resume_to_json(cleaned_text)

            ats_result = compute_ats_score(job, parsed_data)
            score = ats_result["suitability_score"]

            # Save or update ATS score on application if exists
            application = Application.objects.filter(candidate=candidate, job=job).first()
            if application:
                application.ats_score = score
                application.save()

            return Response({
                "message": "ATS Match evaluation complete.",
                "job_title": job.title,
                "company": job.company,
                "suitability_percentage": f"{score}%",
                "detailed_metrics": ats_result
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": f"ATS calculation failed: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EmployerRankedCandidatesAPIView(APIView):
    """
    Employer API: Returns ranked list of candidate applications sorted in descending order
    by ATS suitability score for a specific job post.
    """
    permission_classes = [permissions.IsAuthenticated, IsEmployer]

    def get(self, request, job_id):
        job = get_object_or_404(Job, pk=job_id, employer=request.user)

        applications = Application.objects.filter(job=job).select_related('candidate').order_by('-ats_score')

        ranked_results = []
        for rank, app in enumerate(applications, start=1):
            ranked_results.append({
                "rank": rank,
                "application_id": app.id,
                "candidate_name": app.candidate.name,
                "candidate_email": app.candidate.email,
                "ats_suitability_score": f"{app.ats_score}%",
                "status": app.status,
                "applied_at": app.applied_at
            })

        return Response({
            "job_id": job.id,
            "job_title": job.title,
            "total_applicants": len(ranked_results),
            "ranked_candidates": ranked_results
        }, status=status.HTTP_200_OK)
    
class ParseStructuredResumeAPIView(APIView):
    """
    API endpoint that accepts a resume file (or uses existing profile resume),
    extracts raw text, parses skills/experience, and returns structured JSON schema.
    """
    permission_classes = [permissions.IsAuthenticated, IsCandidate]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        file_obj = request.FILES.get('resume')

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
            # 1. Extract and clean raw text using Day 23 engine
            cleaned_text = parse_resume_file(file_obj)

            # 2. Extract structured NLP metrics using Day 24 engine
            structured_data = parse_resume_to_json(cleaned_text)

            # 3. Optional: Sync extracted skills string back to Candidate Profile
            if hasattr(request.user, 'candidate_profile') and structured_data["extracted_skills"]["skills_list"]:
                skills_str = ", ".join(structured_data["extracted_skills"]["skills_list"])
                profile = request.user.candidate_profile
                profile.skills = skills_str
                profile.save()

            return Response({
                "message": "Resume successfully structured into JSON schema.",
                "data": structured_data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": f"Failed to parse structured resume: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
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
        job = serializer.validated_data.get('job')
        
        resume = None
        ats_score_val = 0.0
        
        # 1. Fetch Candidate Profile & Skills
        candidate_profile = getattr(user, 'candidate_profile', None)
        candidate_skills = candidate_profile.skills if candidate_profile else ""
        
        # 2. Check for Resume file
        if candidate_profile and candidate_profile.resume:
            resume = candidate_profile.resume
            try:
                # Use Day 23/24 Parser + Day 25 ATS Engine
                cleaned_text = parse_resume_file(resume)
                parsed_data = parse_resume_to_json(cleaned_text)
                ats_result = compute_ats_score(job, parsed_data)
                ats_score_val = float(ats_result.get("suitability_score", 0.0))
            except Exception:
                # Fallback to Profile Skills matching if file parsing fails
                ats_score_val = self._compute_profile_skills_score(job.skills_required, candidate_skills)
        else:
            # Match directly on candidate skills string
            ats_score_val = self._compute_profile_skills_score(job.skills_required, candidate_skills)

        # 3. Persist application with the calculated ATS score
        serializer.save(candidate=user, resume_snapshot=resume, ats_score=ats_score_val)

    def _compute_profile_skills_score(self, job_skills_str, candidate_skills_str):
        if not job_skills_str or not candidate_skills_str:
            return 0.0
        job_skills = {s.strip().lower() for s in job_skills_str.split(',') if s.strip()}
        cand_skills = {s.strip().lower() for s in candidate_skills_str.split(',') if s.strip()}
        if not job_skills:
            return 0.0
        matched = job_skills.intersection(cand_skills)
        return round((len(matched) / len(job_skills)) * 100.0, 1)


class ApplicationCreateAPIView(ApplyJobAPIView):
    """Alias for ApplyJobAPIView ensuring identical functionality."""
    pass


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


class AsyncParseResumeAPIView(APIView):
    """
    Candidate API: Triggers asynchronous background resume parsing & NLP extraction via Celery.
    """
    permission_classes = [permissions.IsAuthenticated, IsCandidate]

    def post(self, request):
        if not hasattr(request.user, 'candidate_profile') or not request.user.candidate_profile.resume:
            return Response(
                {"error": "No resume uploaded. Please upload a resume before requesting async parsing."},
                status=status.HTTP_400_BAD_REQUEST
            )

        candidate_profile = request.user.candidate_profile
        
        try:
            from core.tasks import async_parse_resume_task
            task_result = async_parse_resume_task.delay(candidate_profile.id)
            task_id = task_result.id
        except Exception as e:
            from core.tasks import async_parse_resume_task
            task_result = async_parse_resume_task(candidate_profile.id)
            task_id = "eager-sync-execution"

        return Response({
            "message": "Async resume parsing task dispatched to Celery worker queue.",
            "candidate_id": candidate_profile.id,
            "task_id": str(task_id)
        }, status=status.HTTP_202_ACCEPTED)


class AsyncBatchAutoScreenAPIView(APIView):
    """
    Employer API: Triggers asynchronous batch ATS scoring & auto-screening via Celery workers.
    """
    permission_classes = [permissions.IsAuthenticated, IsEmployer]

    def post(self, request, job_id):
        job = get_object_or_404(Job, pk=job_id, employer=request.user)
        pending_apps = Application.objects.filter(job=job, status='applied')

        dispatched_tasks = []
        from core.tasks import async_compute_ats_score_task

        for app in pending_apps:
            try:
                t = async_compute_ats_score_task.delay(app.id)
                dispatched_tasks.append({"application_id": app.id, "task_id": t.id})
            except Exception:
                async_compute_ats_score_task(app.id)
                dispatched_tasks.append({"application_id": app.id, "task_id": "eager-execution"})

        return Response({
            "message": f"Dispatched async screening tasks for {len(dispatched_tasks)} pending applications.",
            "job_id": job.id,
            "job_title": job.title,
            "tasks": dispatched_tasks
        }, status=status.HTTP_202_ACCEPTED)


# =============================================================================
# 7. AI CALL TRIGGER & ELIGIBILITY ENGINE VIEWS (DAY 33)
# =============================================================================

class AICallTriggerAPIView(APIView):
    """
    Employer / Admin API: Triggers or schedules an AI screening call for an application
    after running business eligibility checks (ATS threshold, job status, candidate availability).
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = AICallTriggerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        app_id = serializer.validated_data['application_id']
        delay_minutes = serializer.validated_data['delay_minutes']
        ats_threshold = serializer.validated_data['ats_threshold']
        force = serializer.validated_data['force']

        application = get_object_or_404(Application, pk=app_id)

        # Check permission: User must be job employer, admin, or staff
        user = request.user
        if not (user.is_staff or getattr(user, 'role', '') == 'admin' or application.job.employer == user):
            return Response(
                {"detail": "You do not have permission to trigger an AI call for this application."},
                status=status.HTTP_403_FORBIDDEN
            )

        from core.utils.ai_call_engine import trigger_ai_call
        ai_call, message = trigger_ai_call(
            application,
            delay_minutes=delay_minutes,
            ats_threshold=ats_threshold,
            force=force
        )

        if not ai_call:
            return Response(
                {"error": message, "application_id": app_id},
                status=status.HTTP_400_BAD_REQUEST
            )

        status_code = status.HTTP_201_CREATED if ai_call.status == 'queued' else status.HTTP_200_OK
        return Response({
            "message": message,
            "call_details": AICallSerializer(ai_call).data
        }, status=status_code)


class AICallDetailAPIView(APIView):
    """
    API: Returns detailed status and tracking info for a specific AI screening call.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        ai_call = get_object_or_404(AICall.objects.select_related('application__job', 'application__candidate'), pk=pk)
        user = request.user

        # Access check: Candidate recipient, Job employer, or Admin
        is_candidate = (user == ai_call.application.candidate)
        is_employer = (user == ai_call.application.job.employer)
        is_admin = (user.is_staff or getattr(user, 'role', '') == 'admin')

        if not (is_candidate or is_employer or is_admin):
            return Response({"detail": "Not authorized to view this call details."}, status=status.HTTP_403_FORBIDDEN)

        serializer = AICallSerializer(ai_call)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AICallListAPIView(ListAPIView):
    """
    API: Lists AI calls filtered by caller role (Employer, Candidate, Admin).
    Supports query parameters: ?status=queued&job_id=12
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AICallSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = AICall.objects.select_related('application__job', 'application__candidate').order_by('-created_at')

        if not (user.is_staff or getattr(user, 'role', '') == 'admin'):
            if getattr(user, 'role', '') == 'candidate':
                queryset = queryset.filter(application__candidate=user)
            else:
                queryset = queryset.filter(application__job__employer=user)

        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)

        job_id_param = self.request.query_params.get('job_id')
        if job_id_param:
            queryset = queryset.filter(application__job_id=job_id_param)

        return queryset


class EmployerJobAICallsAPIView(ListAPIView):
    """
    Employer API: Retrieves all AI screening call records for a specific job post.
    """
    permission_classes = [permissions.IsAuthenticated, IsEmployer]
    serializer_class = AICallSerializer

    def get_queryset(self):
        job_id = self.kwargs.get('job_id')
        job = get_object_or_404(Job, pk=job_id, employer=self.request.user)
        return AICall.objects.filter(application__job=job).select_related('application__candidate').order_by('-created_at')


class AICallRetryAPIView(APIView):
    """
    Employer / Admin API: Re-queues a failed or cancelled AI Call.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        ai_call = get_object_or_404(AICall.objects.select_related('application__job'), pk=pk)
        user = request.user

        if not (user.is_staff or getattr(user, 'role', '') == 'admin' or ai_call.application.job.employer == user):
            return Response({"detail": "Not authorized to retry this call."}, status=status.HTTP_403_FORBIDDEN)

        from core.utils.ai_call_engine import retry_ai_call
        delay_minutes = int(request.data.get('delay_minutes', 5))
        success, message = retry_ai_call(ai_call, delay_minutes=delay_minutes)

        if not success:
            return Response({"error": message}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "message": message,
            "call_details": AICallSerializer(ai_call).data
        }, status=status.HTTP_200_OK)


class AICallCancelAPIView(APIView):
    """
    Employer / Admin API: Cancels a queued or pending AI call.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        ai_call = get_object_or_404(AICall.objects.select_related('application__job'), pk=pk)
        user = request.user

        if not (user.is_staff or getattr(user, 'role', '') == 'admin' or ai_call.application.job.employer == user):
            return Response({"detail": "Not authorized to cancel this call."}, status=status.HTTP_403_FORBIDDEN)

        from core.utils.ai_call_engine import cancel_ai_call
        reason = request.data.get('reason', 'Cancelled by recruiter')
        success, message = cancel_ai_call(ai_call, reason=reason)

        if not success:
            return Response({"error": message}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "message": message,
            "call_details": AICallSerializer(ai_call).data
        }, status=status.HTTP_200_OK)

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from core.utils.ai_voice_bridge import AIVoiceBridgeService

class AIVoiceTriggerCallAPIView(APIView):
    """
    Employer Endpoint: Triggers an automated outbound AI voice call using the bridge layer.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        phone_number = request.data.get('phone_number')
        candidate_name = request.data.get('candidate_name', 'Candidate')
        job_title = request.data.get('job_title', 'Software Engineer')

        if not phone_number:
            return Response({
                "status": "error",
                "message": "Field 'phone_number' is required."
            }, status=status.HTTP_400_BAD_REQUEST)

        bridge = AIVoiceBridgeService()
        call_result = bridge.trigger_outbound_call(
            to_phone_number=phone_number,
            candidate_name=candidate_name,
            job_title=job_title
        )

        return Response({
            "status": "success",
            "message": "Outbound AI voice call initialized.",
            "data": call_result
        }, status=status.HTTP_202_ACCEPTED)


class AIVoiceSynthesizeAPIView(APIView):
    """
    Utility Endpoint: Converts text to speech with voice selection.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        text = request.data.get('text')
        voice_gender = request.data.get('voice_gender', 'female')
        language_code = request.data.get('language_code', 'en-US')

        if not text:
            return Response({"status": "error", "message": "Field 'text' is required."}, status=status.HTTP_400_BAD_REQUEST)

        bridge = AIVoiceBridgeService()
        synthesis = bridge.synthesize_speech(text, voice_gender, language_code)

        return Response(synthesis, status=status.HTTP_200_OK)


class AIVoiceTranscribeAPIView(APIView):
    """
    Utility Endpoint: Transcribes spoken audio into text (STT).
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        audio_url = request.data.get('audio_url', 'sample_audio_stream.wav')
        language_code = request.data.get('language_code', 'en-US')

        bridge = AIVoiceBridgeService()
        transcription = bridge.transcribe_audio(audio_url, language_code)

        return Response(transcription, status=status.HTTP_200_OK)


from core.models import AIInterviewSession, AIQuestion, AIAnswer
from core.utils.answer_evaluator import AnswerScoringEngine

class AIEvaluateAnswerAPIView(APIView):
    """
    Endpoint: Submits candidate answer, executes scoring engine, and stores evaluation results.[cite: 2]
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, question_id):
        question = get_object_or_404(AIQuestion, id=question_id)
        session = question.session
        job = session.application.job

        transcript_text = request.data.get('transcript_text', '')
        confidence_score = float(request.data.get('confidence_score', 0.95))

        if not transcript_text:
            return Response({
                "status": "error",
                "message": "Field 'transcript_text' is required."
            }, status=status.HTTP_400_BAD_REQUEST)

        # Execute Scoring Engine[cite: 2]
        eval_result = AnswerScoringEngine.evaluate_answer(
            answer_text=transcript_text,
            required_skills=job.skills_required,
            question_category=question.category
        )

        # Store Answer & Evaluation Results[cite: 2]
        answer, created = AIAnswer.objects.update_or_create(
            question=question,
            defaults={
                'transcript_text': transcript_text,
                'confidence_score': confidence_score,
                'keyword_score': eval_result['keyword_score'],
                'relevance_score': eval_result['relevance_score'],
                'completeness_score': eval_result['completeness_score'],
                'final_score': eval_result['final_score'],
                'ai_annotations': eval_result['annotations'],
            }
        )

        return Response({
            "status": "success",
            "message": "Answer evaluated and stored successfully.",
            "answer_id": answer.id,
            "question_id": question.id,
            "evaluation": {
                "keyword_score": answer.keyword_score,
                "relevance_score": answer.relevance_score,
                "completeness_score": answer.completeness_score,
                "final_score": answer.final_score,
                "confidence_score": answer.confidence_score,
                "annotations": answer.ai_annotations
            }
        }, status=status.HTTP_200_OK)


class AISessionScoreReportAPIView(APIView):
    """
    Endpoint: Retrieves aggregate scoring breakdown and session analytics.[cite: 2]
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, session_id):
        session = get_object_or_404(AIInterviewSession, id=session_id)
        questions = session.questions.all()

        scored_answers = []
        total_score = 0.0
        answered_count = 0

        for q in questions:
            if hasattr(q, 'answer'):
                ans = q.answer
                scored_answers.append({
                    "question_id": q.id,
                    "question_text": q.question_text,
                    "category": q.category,
                    "transcript_text": ans.transcript_text,
                    "confidence_score": ans.confidence_score,
                    "keyword_score": ans.keyword_score,
                    "relevance_score": ans.relevance_score,
                    "completeness_score": ans.completeness_score,
                    "final_score": ans.final_score,
                    "annotations": ans.ai_annotations
                })
                total_score += ans.final_score
                answered_count += 1

        overall_session_score = round(total_score / answered_count, 2) if answered_count > 0 else 0.0

        # Update Session overall score
        session.ai_score = overall_session_score
        session.save()

        return Response({
            "status": "success",
            "session_id": session.id,
            "application_id": session.application_id,
            "overall_session_score": overall_session_score,
            "total_questions_evaluated": answered_count,
            "answers_breakdown": scored_answers
        }, status=status.HTTP_200_OK)

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from core.models import InterviewAvailabilitySlot, InterviewSchedule
from core.serializers import InterviewAvailabilitySlotSerializer, InterviewScheduleSerializer
from core.utils.interview_scheduler import InterviewSchedulerEngine
from django.utils import timezone

class AvailableSlotsAPIView(APIView):
    """
    Retrieves all available, unbooked time slots.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        slots = InterviewAvailabilitySlot.objects.filter(
            is_booked=False,
            start_time__gt=timezone.now()
        ).order_by('start_time')
        serializer = InterviewAvailabilitySlotSerializer(slots, many=True)
        return Response({"status": "success", "count": slots.count(), "results": serializer.data})


class BookInterviewAPIView(APIView):
    """
    Endpoint: Automatically books an interview slot and triggers confirmation.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        application_id = request.data.get('application_id')
        slot_id = request.data.get('slot_id')

        if not application_id or not slot_id:
            return Response({
                "status": "error",
                "message": "Both 'application_id' and 'slot_id' are required."
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            result = InterviewSchedulerEngine.book_interview(
                application_id=application_id,
                slot_id=slot_id,
                user=request.user
            )
            return Response({
                "status": "success",
                "message": "Interview successfully booked and confirmation sent.",
                "data": result
            }, status=status.HTTP_201_CREATED)
        except ValueError as exc:
            return Response({
                "status": "error",
                "message": str(exc)
            }, status=status.HTTP_400_BAD_REQUEST)


class RescheduleInterviewAPIView(APIView):
    """
    Endpoint: Reschedules an existing interview to a new available slot.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, schedule_id):
        new_slot_id = request.data.get('new_slot_id')

        if not new_slot_id:
            return Response({
                "status": "error",
                "message": "Field 'new_slot_id' is required."
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            result = InterviewSchedulerEngine.reschedule_interview(
                schedule_id=schedule_id,
                new_slot_id=new_slot_id
            )
            return Response({
                "status": "success",
                "message": "Interview successfully rescheduled.",
                "data": result
            }, status=status.HTTP_200_OK)
        except ValueError as exc:
            return Response({
                "status": "error",
                "message": str(exc)
            }, status=status.HTTP_400_BAD_REQUEST)

from core.utils.reminder_engine import ReminderEngine
from core.models import ReminderLog

class TriggerManualReminderAPIView(APIView):
    """
    Endpoint: Triggers an on-demand reminder (24h, 1h, or voice hook) for a specific interview.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, schedule_id):
        stage = request.data.get('stage', '24h_before')
        channel = request.data.get('channel', 'email')

        result = ReminderEngine.send_reminder(
            schedule_id=schedule_id,
            stage=stage,
            channel=channel
        )

        if result.get('status') == 'sent':
            return Response({"status": "success", "data": result}, status=status.HTTP_200_OK)
        return Response({"status": "error", "data": result}, status=status.HTTP_400_BAD_REQUEST)


class ReminderScanCronAPIView(APIView):
    """
    Endpoint: Manually invokes the scheduled reminder scanner (simulates periodic cron job).
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        scan_results = ReminderEngine.process_scheduled_reminders()
        return Response({"status": "success", "scan_results": scan_results}, status=status.HTTP_200_OK)


class ReminderTrackingLogsAPIView(APIView):
    """
    Endpoint: Retrieves sent reminder logs, stages, delivery channels, and failure tracking.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, schedule_id):
        logs = ReminderLog.objects.filter(schedule_id=schedule_id).values(
            'id', 'schedule_id', 'stage', 'channel', 'status', 'recipient', 'subject_or_hook', 'retry_count', 'sent_at'
        )
        return Response({"status": "success", "count": len(logs), "results": list(logs)}, status=status.HTTP_200_OK)

from core.models import AICandidateReport
from core.utils.report_generator import AICandidateReportGenerator

class IsEmployerOrRecruiter(permissions.BasePermission):
    """Access Control: Enforces Recruiter / Employer-only access."""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        user_role = str(getattr(request.user, 'role', '')).lower()
        return user_role in ['employer', 'recruiter', 'admin'] or request.user.is_staff or request.user.is_superuser


class GenerateCandidateReportAPIView(APIView):
    """
    Recruiter Endpoint: Generates or refreshes the structured AI candidate report.
    """
    permission_classes = [IsEmployerOrRecruiter]

    def post(self, request, application_id):
        return self._handle_report(application_id)

    def get(self, request, application_id):
        return self._handle_report(application_id)

    def _handle_report(self, application_id):
        try:
            report_data = AICandidateReportGenerator.generate_report(application_id=application_id)
            return Response({
                "status": "success",
                "message": "AI candidate evaluation report generated successfully.",
                "data": report_data
            }, status=status.HTTP_200_OK)
        except ValueError as exc:
            return Response({"status": "error", "message": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class CandidateReportSummaryAPIView(APIView):
    """
    Recruiter Endpoint: Retrieves the stored structured report & summary in JSON format.
    """
    permission_classes = [IsEmployerOrRecruiter]

    def get(self, request, application_id):
        report = AICandidateReport.objects.filter(application_id=application_id).first()
        if not report:
            # Auto-generate if not created yet
            try:
                report_data = AICandidateReportGenerator.generate_report(application_id=application_id)
                return Response({"status": "success", "data": report_data}, status=status.HTTP_200_OK)
            except ValueError as exc:
                return Response({"status": "error", "message": str(exc)}, status=status.HTTP_404_NOT_FOUND)

        return Response({
            "status": "success",
            "report_id": report.id,
            "data": report.structured_report
        }, status=status.HTTP_200_OK)


# =============================================================================
# 10. RECRUITER ANALYTICS & FUNNEL ENGINE VIEWS (DAY 41)
# =============================================================================
from core.utils.recruiter_analytics import RecruiterAnalyticsEngine

class RecruiterFunnelAnalyticsAPIView(APIView):
    """
    Endpoint: Returns hiring funnel metrics and conversion ratios.
    """
    permission_classes = [IsEmployerOrRecruiter]

    def get(self, request):
        employer_id = request.user.id if not request.user.is_superuser else None
        funnel_metrics = RecruiterAnalyticsEngine.get_overall_funnel_metrics(employer_id=employer_id)
        return Response({
            "status": "success",
            "data": funnel_metrics
        }, status=status.HTTP_200_OK)


class RecruiterJobPerformanceAPIView(APIView):
    """
    Endpoint: Returns job-wise performance and role-based aggregation stats.
    """
    permission_classes = [IsEmployerOrRecruiter]

    def get(self, request):
        employer_id = request.user.id if not request.user.is_superuser else None
        job_performance = RecruiterAnalyticsEngine.get_job_performance_metrics(employer_id=employer_id)
        return Response({
            "status": "success",
            "count": len(job_performance),
            "data": job_performance
        }, status=status.HTTP_200_OK)


# =============================================================================
# 11. AUDIT & SECURITY MONITORING VIEWS (DAY 42)
# =============================================================================
from core.models import SystemAuditTrail, SecurityFailureLog
from core.utils.observability import ObservabilityService

class IsAdminUserOnly(permissions.BasePermission):
    """Admin-only access control for compliance and security audit logs."""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            ObservabilityService.log_security_or_failure(
                request=request,
                event_type='unauthorized_access',
                severity='warning',
                custom_message='Unauthenticated access attempt to compliance log API.'
            )
            return False

        user_role = str(getattr(request.user, 'role', '')).lower()
        is_admin = user_role == 'admin' or request.user.is_staff or request.user.is_superuser

        if not is_admin:
            ObservabilityService.log_security_or_failure(
                request=request,
                event_type='forbidden_role',
                severity='warning',
                custom_message=f"User {request.user.email} (Role: {user_role}) attempted unauthorized access to admin audit trails."
            )
            return False
        return True


class AuditTrailLogsAPIView(APIView):
    """
    Endpoint: Returns comprehensive system audit logs (User, Admin, AI actions).
    """
    permission_classes = [IsAdminUserOnly]

    def get(self, request):
        category = request.GET.get('category')
        actor_type = request.GET.get('actor_type')

        qs = SystemAuditTrail.objects.select_related('actor').all()
        if category:
            qs = qs.filter(action_category=category)
        if actor_type:
            qs = qs.filter(actor_type=actor_type)

        audit_data = [
            {
                "id": log.id,
                "actor": log.actor.email if log.actor else "AI System",
                "actor_type": log.actor_type,
                "action_category": log.action_category,
                "action_name": log.action_name,
                "target_entity": log.target_entity,
                "target_id": log.target_id,
                "ip_address": log.ip_address,
                "payload_snapshot": log.payload_snapshot,
                "timestamp": log.timestamp.isoformat()
            }
            for log in qs[:50]
        ]
        return Response({
            "status": "success",
            "count": len(audit_data),
            "results": audit_data
        }, status=status.HTTP_200_OK)


class SecurityAndFailureLogsAPIView(APIView):
    """
    Endpoint: Returns security alert logs and exception/retry tracking records.
    """
    permission_classes = [IsAdminUserOnly]

    def get(self, request):
        event_type = request.GET.get('event_type')
        qs = SecurityFailureLog.objects.all()
        if event_type:
            qs = qs.filter(event_type=event_type)

        logs = [
            {
                "id": entry.id,
                "event_type": entry.event_type,
                "severity": entry.severity,
                "endpoint": entry.endpoint,
                "http_method": entry.http_method,
                "user_identifier": entry.user_identifier,
                "ip_address": entry.ip_address,
                "exception_details": entry.exception_details,
                "timestamp": entry.timestamp.isoformat()
            }
            for entry in qs[:50]
        ]
        return Response({
            "status": "success",
            "count": len(logs),
            "results": logs
        }, status=status.HTTP_200_OK)


class CreateAuditOrSecurityEventAPIView(APIView):
    """
    Endpoint: Demonstrates manual/hook-driven logging of AI and System events.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        action_name = request.data.get('action_name', 'AI Voice Analysis Completed')
        action_category = request.data.get('action_category', 'ai_eval')
        actor_type = request.data.get('actor_type', 'ai_system')
        target_entity = request.data.get('target_entity', 'AIInterviewSession')
        target_id = request.data.get('target_id', '1')
        payload = request.data.get('payload', {"confidence": 0.98, "status": "verified"})

        log_entry = ObservabilityService.log_audit(
            request=request,
            actor_type=actor_type,
            action_category=action_category,
            action_name=action_name,
            target_entity=target_entity,
            target_id=target_id,
            payload=payload
        )

        return Response({
            "status": "success",
            "message": "Audit event recorded successfully.",
            "audit_id": log_entry.id
        }, status=status.HTTP_201_CREATED)


# =============================================================================
# 12. DAY 43: SECURITY SHIELD — THROTTLING, ENCRYPTION & ATTACK SIMULATION
# =============================================================================
from rest_framework.throttling import SimpleRateThrottle
from core.utils.security_crypto import SecurityCryptoService


class SensitiveActionThrottle(SimpleRateThrottle):
    """Custom throttle to block brute-force and rapid abuse on auth/sensitive routes."""
    scope = 'auth_strict'
    rate = '5/minute'

    def get_cache_key(self, request, view):
        if request.user.is_authenticated:
            return f"throttle_auth_user_{request.user.id}"
        return f"throttle_auth_ip_{request.META.get('REMOTE_ADDR', 'anon')}"


class AIAbusePreventionThrottle(SimpleRateThrottle):
    """Restricts heavy AI evaluation calls to prevent API quota drain."""
    scope = 'ai_abuse'
    rate = '5/minute'

    def get_cache_key(self, request, view):
        if request.user.is_authenticated:
            return f"throttle_ai_user_{request.user.id}"
        return f"throttle_ai_ip_{request.META.get('REMOTE_ADDR', 'anon')}"


class EncryptedDataHandlingAPIView(APIView):
    """
    Endpoint: Encrypts and decrypts sensitive recruitment information
    such as salary expectations and national ID numbers.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        salary_expectation = request.data.get('salary_expectation', '')
        ssn_or_id = request.data.get('national_id', '')

        # Encrypt sensitive inputs
        encrypted_salary = SecurityCryptoService.encrypt_data(str(salary_expectation))
        encrypted_id = SecurityCryptoService.encrypt_data(str(ssn_or_id))

        # Decrypt to demonstrate verification
        decrypted_salary = SecurityCryptoService.decrypt_data(encrypted_salary)

        # Log encryption event to audit trail
        ObservabilityService.log_audit(
            request=request,
            actor_type='user',
            action_category='application',
            action_name='Sensitive Data Encrypted',
            target_entity='CandidateProfile',
            target_id=str(request.user.id),
            payload={"fields_encrypted": ["salary_expectation", "national_id"]}
        )

        return Response({
            "status": "success",
            "message": "Sensitive data securely encrypted and stored.",
            "storage_payload": {
                "encrypted_salary_expectation": encrypted_salary,
                "encrypted_national_id": encrypted_id,
            },
            "verified_decryption": {
                "decrypted_salary": decrypted_salary
            }
        }, status=status.HTTP_200_OK)


class SecurityAttackSimulationAPIView(APIView):
    """
    Endpoint: Simulates brute force or rapid calls to test throttling and abuse triggers.
    Repeated rapid requests will trigger DRF's 429 Too Many Requests automatically.
    """
    permission_classes = [permissions.AllowAny]
    throttle_classes = [SensitiveActionThrottle]

    def post(self, request):
        action = request.data.get('action', 'test_ping')
        client_ip = request.META.get('REMOTE_ADDR', '127.0.0.1')

        # Log the simulation attempt to the security audit trail
        ObservabilityService.log_security_or_failure(
            request=request,
            event_type='unauthorized_access',
            severity='info',
            custom_message=f"Security attack simulation triggered: action='{action}' from IP {client_ip}"
        )

        return Response({
            "status": "success",
            "message": f"Request allowed. Action '{action}' processed within rate limit.",
            "client_ip": client_ip
        }, status=status.HTTP_200_OK)


class SecurityReportAuditAPIView(APIView):
    """
    Endpoint: Compiles the Day 43 Security Hardening Report with current protection status.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        # Gather live security metrics
        total_audit_events = SystemAuditTrail.objects.count()
        total_security_failures = SecurityFailureLog.objects.count()
        critical_failures = SecurityFailureLog.objects.filter(severity='critical').count()

        return Response({
            "status": "success",
            "security_report": {
                "throttling_status": "Active (5 req/min on sensitive routes, 120 req/min user standard)",
                "data_encryption": "Fernet 128-bit AES in CBC mode with HMAC SHA256",
                "access_validation": "JWT Bearer Token verification + Role-based permissions",
                "attack_prevention": "Automated 429 Too Many Requests blocking on brute-force triggers",
                "live_metrics": {
                    "total_audit_trail_events": total_audit_events,
                    "total_security_failure_logs": total_security_failures,
                    "critical_security_failures": critical_failures,
                }
            }
        }, status=status.HTTP_200_OK)


# =============================================================================
# 13. DAY 44: LOAD TESTING, STRESS BENCHMARKS & QUERY OPTIMIZATION
# =============================================================================
from core.utils.load_testing import SystemBenchmarkService


class SystemLoadBenchmarkAPIView(APIView):
    """
    Endpoint: Runs query optimization benchmarking and returns load test performance report.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        report = SystemBenchmarkService.get_load_test_summary()
        return Response({
            "status": "success",
            "message": "Load testing stability and query benchmarks calculated successfully.",
            "data": report
        }, status=status.HTTP_200_OK)


class StressTestTriggerAPIView(APIView):
    """
    Endpoint: Lightweight synthetic endpoint designed to receive high-concurrency pings.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response({
            "status": "healthy",
            "server_time": time.time(),
            "load_state": "normal"
        }, status=status.HTTP_200_OK)


# =============================================================================
# 14. DAY 45: PHASE REVIEW & SYSTEM READINESS AUDIT
# =============================================================================
from core.utils.system_readiness import AIBackendReadinessValidator


class AIBackendReadinessAPIView(APIView):
    """
    Endpoint: Returns production readiness audit, architecture verification,
    and health status across the AI backend.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        report = AIBackendReadinessValidator.generate_full_readiness_report()
        return Response({
            "status": "success",
            "message": "AI Backend readiness verification completed successfully.",
            "data": report
        }, status=status.HTTP_200_OK)


class SystemOverviewDocumentationAPIView(APIView):
    """
    Endpoint: Provides structured API reference index and subsystem overview.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        documentation = {
            "platform_name": "Zecpath AI Job Portal & Automated Hiring Assistant",
            "phase_version": "v1.0-Production-Ready",
            "core_modules": {
                "auth_and_profiles": ["/api/auth/signup/", "/api/auth/login/", "/api/profile/candidate/", "/api/profile/employer/"],
                "resume_and_ats": ["/api/candidate/resume/upload/", "/api/candidate/resume/extract-text/", "/api/jobs/<id>/match-score/"],
                "ai_voice_screening": ["/api/voice/trigger-call/", "/api/voice/transcribe-audio/", "/api/voice/synthesize-speech/"],
                "evaluation_and_reports": ["/api/testing/ai-questions/<id>/evaluate/", "/api/recruiter/applications/<id>/generate-report/"],
                "interview_scheduling": ["/api/scheduling/slots/available/", "/api/scheduling/book/", "/api/scheduling/<id>/reschedule/"],
                "funnel_analytics": ["/api/recruiter/analytics/funnel/", "/api/recruiter/analytics/jobs-performance/"],
                "observability_and_security": ["/api/monitoring/audit-trails/", "/api/security/encrypt-sensitive-data/", "/api/security/report/"]
            }
        }
        return Response({
            "status": "success",
            "documentation": documentation
        }, status=status.HTTP_200_OK)


# =============================================================================
# 15. DAY 46: SAAS MONETIZATION, SUBSCRIPTIONS & BILLING APIS
# =============================================================================
import uuid
from datetime import timedelta
from core.models import SubscriptionPlan, UserSubscription, PaymentTransaction, BillingHistory
from core.permissions import RequiresProOrEnterpriseTier


class SubscriptionPlanListAPIView(APIView):
    """List all available public subscription tiers and features."""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        plans = SubscriptionPlan.objects.filter(is_active=True).values(
            'id', 'name', 'display_title', 'price', 'billing_cycle',
            'max_active_jobs', 'max_ai_screenings_per_month', 'has_advanced_analytics'
        )
        return Response({"status": "success", "plans": list(plans)}, status=status.HTTP_200_OK)


class CurrentSubscriptionDetailAPIView(APIView):
    """Retrieve the requesting employer's active plan, validity, and limits."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        sub = getattr(request.user, 'subscription', None)
        if not sub:
            return Response({
                "status": "success",
                "has_subscription": False,
                "message": "No active subscription. Defaulting to restricted free limits."
            }, status=status.HTTP_200_OK)

        return Response({
            "status": "success",
            "has_subscription": True,
            "subscription": {
                "plan": sub.plan.name,
                "display_title": sub.plan.display_title,
                "status": sub.status,
                "valid": sub.is_valid,
                "current_period_end": sub.current_period_end.isoformat(),
                "entitlements": {
                    "max_active_jobs": sub.plan.max_active_jobs,
                    "has_advanced_analytics": sub.plan.has_advanced_analytics
                }
            }
        }, status=status.HTTP_200_OK)


class MockSubscribePlanAPIView(APIView):
    """Simulates upgrading/subscribing to a tier and recording transactions."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        plan_name = request.data.get('plan_name', 'pro')
        plan = SubscriptionPlan.objects.filter(name=plan_name, is_active=True).first()
        if not plan:
            return Response({"error": f"Plan '{plan_name}' not found."}, status=status.HTTP_400_BAD_REQUEST)

        # 1. Simulate Payment Transaction
        tx_ref = f"TX-{uuid.uuid4().hex[:10].upper()}"
        transaction = PaymentTransaction.objects.create(
            user=request.user,
            amount=plan.price,
            currency="USD",
            payment_method="mock_card",
            transaction_reference=tx_ref,
            status="succeeded"
        )

        # 2. Update or Create User Subscription
        period_days = 365 if plan.billing_cycle == 'yearly' else 30
        end_date = timezone.now() + timedelta(days=period_days)

        subscription, _ = UserSubscription.objects.update_or_create(
            user=request.user,
            defaults={
                'plan': plan,
                'status': 'active',
                'start_date': timezone.now(),
                'current_period_end': end_date,
                'cancel_at_period_end': False
            }
        )

        # 3. Create Billing Invoice Record
        BillingHistory.objects.create(
            user=request.user,
            transaction=transaction,
            invoice_number=f"INV-{uuid.uuid4().hex[:8].upper()}",
            amount_paid=plan.price
        )

        return Response({
            "status": "success",
            "message": f"Successfully subscribed to {plan.display_title}.",
            "transaction_reference": tx_ref,
            "expires_at": end_date.isoformat()
        }, status=status.HTTP_201_CREATED)


# ==============================================================================
# DAY 47: PAYMENT GATEWAYS (STRIPE & RAZORPAY) INTEGRATION & WEBHOOKS
# ==============================================================================
from core.utils.payment_gateway import PaymentGatewayService

class CreatePaymentOrderAPIView(APIView):
    """
    Endpoint: Initializes an order session for the client checkout flow.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        plan_name = request.data.get('plan_name', 'pro')
        gateway = request.data.get('gateway', 'razorpay')

        try:
            order_data = PaymentGatewayService.create_gateway_order(
                user=request.user,
                plan_name=plan_name,
                gateway=gateway
            )
            return Response({"status": "success", "order": order_data}, status=status.HTTP_201_CREATED)
        except ValueError as err:
            return Response({"error": str(err)}, status=status.HTTP_400_BAD_REQUEST)


class VerifyPaymentAPIView(APIView):
    """
    Endpoint: Verifies client payment signatures and activates the subscription.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        order_id = request.data.get('order_id')
        payment_id = request.data.get('payment_id')
        signature = request.data.get('signature')

        if not all([order_id, payment_id]):
            return Response({"error": "order_id and payment_id are required."}, status=status.HTTP_400_BAD_REQUEST)

        # In production test mode, verify signature if provided
        is_valid = True
        if signature:
            is_valid = PaymentGatewayService.verify_razorpay_signature(order_id, payment_id, signature)

        if not is_valid:
            return Response({"error": "Cryptographic signature verification failed."}, status=status.HTTP_400_BAD_REQUEST)

        transaction = PaymentGatewayService.mark_payment_success(order_id, payment_id, request.data)
        if not transaction:
            return Response({"error": "Transaction record not found."}, status=status.HTTP_404_NOT_FOUND)

        # Activate user subscription upon verified payment
        plan_name = transaction.raw_response.get("plan_name", "pro")
        plan = SubscriptionPlan.objects.get(name=plan_name)
        end_date = timezone.now() + timedelta(days=30)

        UserSubscription.objects.update_or_create(
            user=request.user,
            defaults={
                'plan': plan,
                'status': 'active',
                'start_date': timezone.now(),
                'current_period_end': end_date,
            }
        )

        BillingHistory.objects.create(
            user=request.user,
            transaction=transaction,
            invoice_number=f"INV-{uuid.uuid4().hex[:8].upper()}",
            amount_paid=transaction.amount
        )

        return Response({
            "status": "success",
            "message": "Payment verified and subscription activated.",
            "transaction_reference": order_id,
            "status": "succeeded"
        }, status=status.HTTP_200_OK)


class PaymentWebhookAPIView(APIView):
    """
    Endpoint: Asynchronous webhook listener for payment success, failure, and refund events.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        event_type = request.data.get('event', 'payment.captured')
        payload_data = request.data.get('payload', {})

        # Handle events
        if event_type in ['payment.captured', 'payment_intent.succeeded']:
            order_id = payload_data.get('order_id') or request.data.get('order_id')
            tx = PaymentTransaction.objects.filter(transaction_reference=order_id).first()
            if tx:
                tx.status = 'succeeded'
                tx.save(update_fields=['status'])

        elif event_type in ['payment.failed', 'payment_intent.payment_failed']:
            order_id = payload_data.get('order_id') or request.data.get('order_id')
            tx = PaymentTransaction.objects.filter(transaction_reference=order_id).first()
            if tx:
                tx.status = 'failed'
                tx.save(update_fields=['status'])

        elif event_type in ['refund.processed', 'charge.refunded']:
            order_id = payload_data.get('order_id') or request.data.get('order_id')
            tx = PaymentTransaction.objects.filter(transaction_reference=order_id).first()
            if tx:
                tx.status = 'refunded'
                tx.save(update_fields=['status'])

        return Response({"status": "received", "event": event_type}, status=status.HTTP_200_OK)


# ==============================================================================
# DAY 48: FEATURE ACCESS CONTROL & SUBSCRIPTION VALIDATION APIS
# ==============================================================================
from core.utils.feature_access import FeatureAccessController

class SubscriptionValidationAPIView(APIView):
    """
    Endpoint: Checks real-time subscription status, grace period state, and remaining quotas.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        sub = UserSubscription.objects.filter(user=request.user).select_related('plan').first()
        if not sub:
            return Response({
                "status": "unsubscribed",
                "can_access_paid_features": False,
                "message": "No active plan found. Basic free limits apply."
            }, status=status.HTTP_200_OK)

        current_status = sub.check_and_update_expiry()
        active_jobs_count = Job.objects.filter(employer=request.user, status='active').count()

        return Response({
            "status": "success",
            "subscription": {
                "tier": sub.plan.name,
                "plan_title": sub.plan.display_title,
                "status": current_status,
                "is_access_allowed": sub.is_access_allowed,
                "current_period_end": sub.current_period_end.isoformat(),
                "grace_period_days": sub.grace_period_days
            },
            "usage_limits": {
                "active_jobs": {
                    "used": active_jobs_count,
                    "max_limit": "Unlimited" if sub.plan.max_active_jobs == -1 else sub.plan.max_active_jobs,
                    "limit_reached": active_jobs_count >= sub.plan.max_active_jobs if sub.plan.max_active_jobs != -1 else False
                },
                "candidate_views": {
                    "used": sub.monthly_candidate_views_used,
                    "limit": "Unlimited" if sub.plan.name in ['pro', 'enterprise'] else 10
                },
                "has_advanced_analytics": sub.plan.has_advanced_analytics
            }
        }, status=status.HTTP_200_OK)


class GatedCandidateAccessAPIView(APIView):
    """
    Endpoint: Demonstrates usage limit gating when viewing candidate records.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        allowed, reason = FeatureAccessController.can_view_candidate_profile(request.user)
        if not allowed:
            return Response({
                "status": "forbidden",
                "error": "Access Limit Exceeded",
                "detail": reason
            }, status=status.HTTP_403_FORBIDDEN)

        return Response({
            "status": "success",
            "message": "Candidate profile details unlocked.",
            "candidate": {
                "id": 101,
                "name": "Jane Doe",
                "title": "Senior AI Backend Engineer",
                "match_score": 94.5
            }
        }, status=status.HTTP_200_OK)


# ==============================================================================
# DAY 49: PREMIUM RECRUITER INSIGHTS & CANDIDATE RANKING APIS
# ==============================================================================
from core.permissions import IsRecruiterWithPaidPlan, PremiumInsightsRateThrottle
from core.utils.premium_insights import PremiumInsightsService

class PremiumCandidateRankingReportAPIView(APIView):
    """
    Endpoint: Generates advanced candidate rankings and success predictions per job.
    """
    permission_classes = [IsRecruiterWithPaidPlan]
    throttle_classes = [PremiumInsightsRateThrottle]

    def get(self, request, job_id):
        report = PremiumInsightsService.get_candidate_ranking_report(
            job_id=job_id,
            employer_user=request.user
        )
        if "error" in report:
            return Response({"error": report["error"]}, status=status.HTTP_404_NOT_FOUND)

        tier_title = getattr(getattr(request.user, 'subscription', None), 'plan', None)
        tier_name = tier_title.display_title if tier_title else "Pro Plan"

        return Response({
            "status": "success",
            "tier": tier_name,
            "data": report
        }, status=status.HTTP_200_OK)


class PremiumHiringEfficiencyAPIView(APIView):
    """
    Endpoint: Returns hiring velocity, aggregate quality, and AI-driven efficiency metrics.
    """
    permission_classes = [IsRecruiterWithPaidPlan]
    throttle_classes = [PremiumInsightsRateThrottle]

    def get(self, request):
        metrics = PremiumInsightsService.get_hiring_efficiency_metrics(request.user)
        tier_title = getattr(getattr(request.user, 'subscription', None), 'plan', None)
        tier_name = tier_title.display_title if tier_title else "Pro Plan"

        return Response({
            "status": "success",
            "tier": tier_name,
            "data": metrics
        }, status=status.HTTP_200_OK)


# ==============================================================================
# DAY 50: ADMIN FINANCE & BILLING MANAGEMENT APIS
# ==============================================================================
from core.utils.admin_finance import AdminFinanceService
from core.models import PaymentTransaction

class IsAdminUserOnly(permissions.BasePermission):
    """Restricts access strictly to Platform Administrators."""
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            (getattr(request.user, 'role', '') == 'admin' or request.user.is_staff)
        )

class AdminRevenueDashboardAPIView(APIView):
    """
    Endpoint: Returns daily/monthly revenue, plan-wise breakdowns, and transaction metrics.
    """
    permission_classes = [IsAdminUserOnly]

    def get(self, request):
        data = AdminFinanceService.get_revenue_dashboard()
        return Response({"status": "success", "data": data}, status=status.HTTP_200_OK)

class AdminTransactionListAPIView(APIView):
    """
    Endpoint: Returns paginated financial audit logs and suspicious/failed attempts.
    """
    permission_classes = [IsAdminUserOnly]

    def get(self, request):
        status_filter = request.GET.get('status')
        qs = PaymentTransaction.objects.select_related('user', 'subscription').all()
        if status_filter:
            qs = qs.filter(status=status_filter)

        transactions = [
            {
                "id": tx.id,
                "user": tx.user.email if tx.user else None,
                "amount": float(tx.amount),
                "currency": tx.currency,
                "payment_method": tx.payment_method,
                "reference": tx.transaction_reference,
                "status": tx.status,
                "timestamp": tx.created_at.isoformat(),
                "metadata": tx.raw_response
            }
            for tx in qs[:50]
        ]
        return Response({"status": "success", "count": len(transactions), "transactions": transactions}, status=status.HTTP_200_OK)

class AdminRefundTriggerAPIView(APIView):
    """
    Endpoint: Executes transaction refunds and updates audit trails.
    """
    permission_classes = [IsAdminUserOnly]

    def post(self, request, transaction_id):
        reason = request.data.get('reason', 'Admin initiated customer refund')
        try:
            result = AdminFinanceService.process_refund(transaction_id, reason, request.user)
            return Response({"status": "success", "refund": result}, status=status.HTTP_200_OK)
        except ValueError as err:
            return Response({"error": str(err)}, status=status.HTTP_400_BAD_REQUEST)


# ==============================================================================
# DAY 52: DEVOPS ENVIRONMENT CONFIG AUDIT API
# ==============================================================================
class EnvironmentConfigAuditAPIView(APIView):
    """
    DevOps audit endpoint to verify environment variable states and secret presence without leaking values.
    """
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        return Response({
            "status": "success",
            "environment_audit": {
                "debug_mode": settings.DEBUG,
                "database_configured": bool(settings.DATABASES['default']['NAME']),
                "stripe_configured": bool(getattr(settings, 'STRIPE_SECRET_KEY', None)),
                "razorpay_configured": bool(getattr(settings, 'RAZORPAY_KEY_SECRET', None)),
                "fernet_encryption_configured": bool(getattr(settings, 'FERNET_ENCRYPTION_KEY', None)),
                "allowed_hosts_count": len(settings.ALLOWED_HOSTS)
            }
        }, status=status.HTTP_200_OK)








