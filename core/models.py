import os
import uuid
from django.conf import settings
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.contrib.auth.base_user import BaseUserManager

class AuditLog(models.Model):
    admin = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='admin_actions'
    )
    action = models.CharField(max_length=255)
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='audit_targets'
    )
    target_job = models.ForeignKey(
        'Job', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='audit_jobs'
    )
    details = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.admin.email} - {self.action} at {self.created_at}"

    def __str__(self):
        return f"{self.admin.email} - {self.action} at {self.created_at}"

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("is_verified", True)
        extra_fields.setdefault("role", "recruiter")
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom user model for the Zecpath domain. Now Django's real
    AUTH_USER_MODEL -- handles login/authentication itself, with a
    role field distinguishing candidates from recruiters.
    """
    name = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True)
    role = models.CharField(
        max_length=20,
        choices=[("candidate", "Candidate"), ("recruiter", "Recruiter")],
        default="candidate",
    )
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name", "role"]

    def __str__(self):
        return f"{self.name} ({self.role})"

def candidate_resume_path(instance, filename):
    # Extract file extension (e.g. .pdf, .docx)
    ext = filename.split('.')[-1]
    # Unique filename using UUID: e.g. resumes/candidate_1_a1b2c3d4.pdf
    filename = f"candidate_{instance.user.id}_{uuid.uuid4().hex[:8]}.{ext}"
    return os.path.join('resumes', filename)

class Candidate(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="candidate_profile")
    resume = models.FileField(upload_to=candidate_resume_path, blank=True, null=True)
    skills = models.TextField(blank=True)
    education = models.TextField(blank=True)
    experience = models.TextField(blank=True)
    expected_salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_deleted = models.BooleanField(default=False)

class Employer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="employer_profile")
    company_name = models.CharField(max_length=200)
    website = models.URLField(blank=True)
    domain = models.CharField(max_length=100, blank=True)
    company_size = models.CharField(max_length=50, blank=True)
    is_verified = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)  # soft delete



class Job(models.Model):
    JOB_TYPES = (
        ('full_time', 'Full Time'),
        ('part_time', 'Part Time'),
        ('contract', 'Contract'),
        ('internship', 'Internship'),
        ('remote', 'Remote'),
    )

    JOB_STATUS = (
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('closed', 'Closed'),
    )

    employer = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='jobs'
    )
    title = models.CharField(max_length=255)
    company = models.CharField(max_length=255)
    description = models.TextField()
    skills_required = models.TextField(help_text="Comma-separated skills (e.g. Python, Django, DRF)")
    experience_required = models.CharField(max_length=100, help_text="e.g. 2-4 years")
    salary_min = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    salary_max = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    location = models.CharField(max_length=255, default='Remote')
    job_type = models.CharField(max_length=20, choices=JOB_TYPES, default='full_time')
    status = models.CharField(max_length=20, choices=JOB_STATUS, default='active')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} at {self.company}"

class ApplicationAuditLog(models.Model):
    application = models.ForeignKey(
        'Application', 
        on_delete=models.CASCADE, 
        related_name='audit_logs'
    )
    previous_status = models.CharField(max_length=50)
    new_status = models.CharField(max_length=50)
    performed_by = models.ForeignKey(
        'User', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    ats_score = models.FloatField(default=0.0, help_text="Calculated ATS suitability score percentage (0-100)")

    def __str__(self):
        return f"App #{self.application_id}: {self.previous_status} -> {self.new_status}"

class Application(models.Model):
    STATUS_CHOICES = (
        ('applied', 'Applied'),
        ('under_review', 'Under Review'),
        ('shortlisted', 'Shortlisted'),
        ('rejected', 'Rejected'),
        ('hired', 'Hired'),
    )

    candidate = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='applications'
    )
    job = models.ForeignKey(
        'Job', 
        on_delete=models.CASCADE, 
        related_name='applications'
    )
    resume_snapshot = models.FileField(upload_to='application_resumes/', null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='applied')
    applied_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Prevents duplicate applications for the exact same job by the same candidate
        unique_together = ('candidate', 'job')
        ordering = ['-applied_at']

    def __str__(self):
        return f"{self.candidate.email} - {self.job.title}"