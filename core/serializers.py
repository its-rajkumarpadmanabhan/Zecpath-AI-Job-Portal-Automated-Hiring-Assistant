import os

from .models import Candidate

from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password

from .models import User, Job, Application, Candidate, Employer

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
    class Meta:
        model = Job
        fields = ['id', 'title', 'company', 'description', 'posted_by', 'created_at']
        read_only_fields = ['posted_by']

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



# Aliases for detailed view serializers
FullCandidateDetailSerializer = CandidateProfileSerializer
FullEmployerDetailSerializer = EmployerProfileSerializer