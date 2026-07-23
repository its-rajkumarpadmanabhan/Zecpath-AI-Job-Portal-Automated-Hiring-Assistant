import os

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate



from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from .permissions import IsCandidate
from .serializers import ResumeUploadSerializer

from .models import Job, User ,Employer
from .serializers import JobSerializer, UserSerializer, SignupSerializer, ApplicationSerializer,CandidateProfileSerializer, EmployerProfileSerializer
from .permissions import IsEmployer, IsCandidate, IsAdmin



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
    permission_classes = [IsAuthenticated, IsCandidate]
    parser_classes = [MultiPartParser, FormParser]  # Required for handling file uploads

    def post(self, request):
        candidate = request.user.candidate_profile

        # Delete previous physical file if replacing an existing resume
        if candidate.resume and os.path.isfile(candidate.resume.path):
            os.remove(candidate.resume.path)

        serializer = ResumeUploadSerializer(candidate, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "message": "Resume uploaded successfully!",
                "resume_url": candidate.resume.url
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)