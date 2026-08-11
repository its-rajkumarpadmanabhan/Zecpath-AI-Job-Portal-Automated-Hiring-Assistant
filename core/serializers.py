import os

from .models import Candidate

from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password

from .models import User, Job, Application, Candidate, Employer,ApplicationAuditLog

class CandidateProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Candidate
        fields = ['id', 'skills', 'education', 'experience', 'expected_salary', 'resume', 'is_deleted']
        read_only_fields = ['id', 'is_deleted']  # deletion happens via the DELETE action, not PATCH

class EmployerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employer
        fields = ['id', 'company_name', 'website', 'domain', 'company_size', 'is_verified', 'is_deleted']
        read_only_fields = ['id', 'is_verified', 'is_deleted']  # only admin can verify, not self-edit

class JobSerializer(serializers.ModelSerializer):
    employer_email = serializers.ReadOnlyField(source='employer.email')

    class Meta:
        model = Job
        fields = [
            'id', 'employer', 'employer_email', 'title', 'company', 'description', 
            'skills_required', 'experience_required', 'salary_min', 'salary_max', 
            'location', 'job_type', 'status', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'employer', 'created_at', 'updated_at']

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = '__all__'

class SignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ['id', 'name', 'email', 'phone', 'role', 'password']

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)
    
class ApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Application
        fields = ['id', 'job', 'status', 'applied_at']  # candidate is set server-side, not from input

class ResumeUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Candidate
        fields = ['resume']

    def validate_resume(self, value):
        # 1. Size Validation (Max 5MB)
        max_size_mb = 5
        if value.size > max_size_mb * 1024 * 1024:
            raise serializers.ValidationError(f"File size cannot exceed {max_size_mb}MB.")

        # 2. File Extension Validation
        ext = os.path.splitext(value.name)[1].lower()
        valid_extensions = ['.pdf', '.doc', '.docx']
        if ext not in valid_extensions:
            raise serializers.ValidationError("Only PDF, DOC, and DOCX file formats are allowed.")

        return value

class ApplicationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Application
        fields = ['id', 'job', 'applied_at', 'status']
        read_only_fields = ['id', 'applied_at', 'status']

    def validate_job(self, value):
        # Job status check
        if value.status != 'active':
            raise serializers.ValidationError("You can only apply to active job listings.")
        return value

    def validate(self, attrs):
        user = self.context['request'].user
        job = attrs['job']
        
        # Duplicate application prevention
        if Application.objects.filter(candidate=user, job=job).exists():
            raise serializers.ValidationError({"detail": "You have already applied for this job."})
        
        return attrs


class ApplicationDetailSerializer(serializers.ModelSerializer):
    job_title = serializers.CharField(source='job.title', read_only=True)
    company = serializers.CharField(source='job.company', read_only=True)
    location = serializers.CharField(source='job.location', read_only=True)

    class Meta:
        model = Application
        fields = ['id', 'job', 'job_title', 'company', 'location', 'status', 'applied_at', 'resume_snapshot']

# Aliases for detailed view serializers
FullCandidateDetailSerializer = CandidateProfileSerializer
FullEmployerDetailSerializer = EmployerProfileSerializer

class ApplicationStatusUpdateSerializer(serializers.ModelSerializer):
    notes = serializers.CharField(write_only=True, required=False, allow_blank=True)

    # Updated to match your exact Application model STATUS_CHOICES
    VALID_TRANSITIONS = {
        'applied': ['under_review', 'shortlisted', 'rejected'],
        'under_review': ['shortlisted', 'rejected'],
        'shortlisted': ['hired', 'rejected'],
        'hired': [],     # Terminal stage (locked)
        'rejected': []    # Terminal stage (locked)
    }

    class Meta:
        model = Application
        fields = ['status', 'notes']

    def validate_status(self, value):
        current_status = self.instance.status

        # 1. Lock check for terminal states
        if current_status in ['hired', 'rejected']:
            raise serializers.ValidationError(
                f"Cannot modify application. Stage is locked at '{current_status}'."
            )

        # 2. Validate allowed status transition
        allowed_next_statuses = self.VALID_TRANSITIONS.get(current_status, [])
        if value not in allowed_next_statuses:
            raise serializers.ValidationError(
                f"Invalid transition from '{current_status}' to '{value}'."
            )

        return value

    def update(self, instance, validated_data):
        notes = validated_data.pop('notes', '')
        old_status = instance.status
        new_status = validated_data.get('status', old_status)

        instance.status = new_status
        instance.save()

        ApplicationAuditLog.objects.create(
            application=instance,
            previous_status=old_status,
            new_status=new_status,
            performed_by=self.context['request'].user,
            notes=notes
        )

        return instance


class EmployerDashboardAnalyticsSerializer(serializers.Serializer):
    total_jobs_posted = serializers.IntegerField()
    active_jobs_count = serializers.IntegerField()
    total_applications_received = serializers.IntegerField()
    shortlist_ratio = serializers.FloatField()
    applications_by_status = serializers.DictField()


class EmployerApplicantListSerializer(serializers.ModelSerializer):
    candidate_id = serializers.IntegerField(source='candidate.id', read_only=True)
    candidate_name = serializers.CharField(source='candidate.name', read_only=True)
    candidate_email = serializers.CharField(source='candidate.email', read_only=True)
    job_title = serializers.CharField(source='job.title', read_only=True)

    class Meta:
        model = Application
        fields = [
            'id', 'candidate_id', 'candidate_name', 'candidate_email', 
            'job', 'job_title', 'status', 'applied_at', 'resume_snapshot'
        ]

from rest_framework import serializers
from .models import Application, Job

class CandidateApplicationTrackerSerializer(serializers.ModelSerializer):
    job_title = serializers.CharField(source='job.title', read_only=True)
    company_name = serializers.CharField(source='job.company', read_only=True)
    location = serializers.CharField(source='job.location', read_only=True)
    job_type = serializers.CharField(source='job.job_type', read_only=True)

    class Meta:
        model = Application
        fields = [
            'id', 'job', 'job_title', 'company_name', 
            'location', 'job_type', 'status', 'applied_at'
        ]


class RecommendedJobSerializer(serializers.ModelSerializer):
    employer_email = serializers.CharField(source='employer.email', read_only=True)

    class Meta:
        model = Job
        fields = [
            'id', 'title', 'company', 'location', 
            'job_type', 'skills_required', 'status', 'employer_email'
        ]