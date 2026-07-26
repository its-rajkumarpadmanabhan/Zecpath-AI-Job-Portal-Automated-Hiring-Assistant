import os

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
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