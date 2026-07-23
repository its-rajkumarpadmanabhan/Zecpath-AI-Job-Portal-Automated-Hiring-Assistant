import os
import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.contrib.auth.base_user import BaseUserManager


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
    """A job posting, owned by an Employer."""
    title = models.CharField(max_length=200)
    company = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    posted_by = models.ForeignKey(
        Employer, on_delete=models.CASCADE, related_name="jobs_posted"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} @ {self.company}"


class Application(models.Model):
    """A candidate's application to a job -- links Candidate <-> Job."""
    STATUS_CHOICES = [
        ("applied", "Applied"),
        ("shortlisted", "Shortlisted"),
        ("rejected", "Rejected"),
        ("selected", "Selected"),
    ]

    candidate = models.ForeignKey(
        Candidate, on_delete=models.CASCADE, related_name="applications"
    )
    job = models.ForeignKey(
        Job, on_delete=models.CASCADE, related_name="applications"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="applied")
    applied_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("candidate", "job")  # a candidate can't apply twice to the same job

    def __str__(self):
        return f"{self.candidate.user.name} -> {self.job.title} [{self.status}]"