import os
import uuid
from datetime import timedelta
from django.conf import settings
from django.db import models
from django.utils import timezone
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
    title = models.CharField(max_length=255, db_index=True)  # Indexed for search queries
    company = models.CharField(max_length=255)
    description = models.TextField()
    skills_required = models.TextField(help_text="Comma-separated skills (e.g. Python, Django, DRF)")
    experience_required = models.CharField(max_length=100, help_text="e.g. 2-4 years")
    salary_min = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    salary_max = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    location = models.CharField(max_length=255, default='Remote')
    job_type = models.CharField(max_length=20, choices=JOB_TYPES, default='full_time')
    status = models.CharField(max_length=20, choices=JOB_STATUS, default='active', db_index=True) # Indexed for active filtering

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            # Composite index for filtering active public jobs sorted by creation date
            models.Index(fields=['status', '-created_at']),
            # Index for fast search of active requisitions by employer
            models.Index(fields=['employer', 'status'], name='idx_job_employer_status'),
            # Composite index for filtering jobs by role type and creation date
            models.Index(fields=['job_type', 'created_at'], name='idx_job_type_created'),
        ]

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
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='applied', db_index=True) # Indexed for status queries
    applied_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    ats_score = models.FloatField(default=0.0, db_index=True, help_text="Calculated ATS suitability score percentage (0-100)")

    class Meta:
        unique_together = ('candidate', 'job')
        ordering = ['-applied_at']
        indexes = [
            # Composite index for fast recruiter queries ordering applicants by rank/score
            models.Index(fields=['job', '-ats_score']),
            # High-cardinality index for recruiter candidate pipelines
            models.Index(fields=['job', 'status'], name='idx_app_job_status'),
            # Composite index for tracking candidate submission timelines
            models.Index(fields=['candidate', 'created_at'], name='idx_app_cand_created'),
        ]


    def __str__(self):
        return f"{self.candidate.email} - {self.job.title}"


class AICall(models.Model):
    STATUS_CHOICES = (
        ('queued', 'Queued'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    )

    application = models.OneToOneField(
        'Application', 
        on_delete=models.CASCADE, 
        related_name='ai_call'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='queued', db_index=True)
    scheduled_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)
    retry_count = models.IntegerField(default=0)
    error_notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"AI Call for App #{self.application_id} - {self.status}"


class AIInterviewSession(models.Model):
    SESSION_STATUS_CHOICES = (
        ('initiated', 'Initiated'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('abandoned', 'Abandoned'),
    )

    application = models.ForeignKey(
        'Application',
        on_delete=models.CASCADE,
        related_name='interview_sessions'
    )
    session_status = models.CharField(
        max_length=20, 
        choices=SESSION_STATUS_CHOICES, 
        default='initiated'
    )
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.PositiveIntegerField(default=0)
    
    # Transcript & Scoring Output
    transcript = models.TextField(blank=True, null=True)  # Raw full transcript
    structured_transcript = models.JSONField(default=list, blank=True)  # Structured Q&A JSON
    ai_score = models.FloatField(null=True, blank=True)
    ai_feedback = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'ai_interview_sessions'
        ordering = ['-started_at']

    def __str__(self):
        return f"AI Session #{self.id} - App #{self.application_id} ({self.session_status})"


# ------------------------------------------------------------------------------
# 2. AI Question & Candidate Answer Breakdown
# ------------------------------------------------------------------------------
class AIQuestion(models.Model):
    session = models.ForeignKey(
        AIInterviewSession,
        on_delete=models.CASCADE,
        related_name='questions'
    )
    question_order = models.PositiveIntegerField(default=1)
    question_text = models.TextField()
    category = models.CharField(max_length=100, default='Technical')  # Technical, Behavioral, Situational
    asked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ai_interview_questions'
        ordering = ['question_order']

    def __str__(self):
        return f"Q{self.question_order} for Session #{self.session_id}"


class AIAnswer(models.Model):
    question = models.OneToOneField(
        AIQuestion,
        on_delete=models.CASCADE,
        related_name='answer'
    )
    transcript_text = models.TextField()  # Voice-to-text converted output
    confidence_score = models.FloatField(default=1.0)  # STT model confidence
    audio_duration_seconds = models.FloatField(default=0.0)
    sentiment = models.CharField(max_length=50, blank=True, null=True)  # Positive, Neutral, Negative
    
    # Day 37 Evaluation Breakdown Metrics
    keyword_score = models.FloatField(default=0.0)      # 0 - 100
    relevance_score = models.FloatField(default=0.0)    # 0 - 100
    completeness_score = models.FloatField(default=0.0) # 0 - 100
    final_score = models.FloatField(default=0.0)        # Normalized Weighted Total
    ai_annotations = models.JSONField(default=dict, blank=True)  # AI commentary & matched keywords

    answered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ai_interview_answers'

    def __str__(self):
        return f"Answer for Q#{self.question_id} (Score: {self.final_score})"


# ------------------------------------------------------------------------------
# 3. Call Audit Logs (Compliance & Auditing)
# ------------------------------------------------------------------------------
class CallLog(models.Model):
    CALL_EVENT_CHOICES = (
        ('triggered', 'Triggered'),
        ('connected', 'Connected'),
        ('transcribing', 'Transcribing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('retried', 'Retried'),
    )

    session = models.ForeignKey(
        AIInterviewSession,
        on_delete=models.CASCADE,
        related_name='call_logs',
        null=True,
        blank=True
    )
    triggered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='triggered_call_logs'
    )
    event = models.CharField(max_length=30, choices=CALL_EVENT_CHOICES)
    trigger_reason = models.CharField(max_length=255, default='Auto-Screening Criteria Met')
    meta_data = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ai_call_audit_logs'
        ordering = ['-timestamp']

    def __str__(self):
        return f"AuditLog: {self.event} at {self.timestamp} by {self.triggered_by}"

# ------------------------------------------------------------------------------
# 1. Interviewer Availability Slots
# ------------------------------------------------------------------------------
class InterviewAvailabilitySlot(models.Model):
    employer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='availability_slots'
    )
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    is_booked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'interview_availability_slots'
        ordering = ['start_time']

    def __str__(self):
        return f"Slot {self.id} for {self.employer.email}: {self.start_time} - {self.end_time} (Booked: {self.is_booked})"


# ------------------------------------------------------------------------------
# 2. Automated Interview Schedule
# ------------------------------------------------------------------------------
class InterviewSchedule(models.Model):
    STATUS_CHOICES = (
        ('scheduled', 'Scheduled'),
        ('rescheduled', 'Rescheduled'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    )

    application = models.ForeignKey(
        'Application',
        on_delete=models.CASCADE,
        related_name='schedules'
    )
    slot = models.OneToOneField(
        InterviewAvailabilitySlot,
        on_delete=models.CASCADE,
        related_name='schedule'
    )
    scheduled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    interview_type = models.CharField(max_length=50, default='AI Voice Screening')
    meeting_link = models.URLField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    confirmation_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'interview_schedules'
        ordering = ['-created_at']

    def __str__(self):
        return f"Schedule #{self.id} - App #{self.application_id} at {self.slot.start_time} ({self.status})"

class ReminderLog(models.Model):
    """Tracks every reminder attempt, stage, channel, and delivery status."""
    STAGE_CHOICES = (
        ('24h_before', '24 Hours Before'),
        ('1h_before', '1 Hour Before'),
        ('immediate', 'Immediate Follow-up'),
    )
    CHANNEL_CHOICES = (
        ('email', 'Email'),
        ('voice', 'Voice Call Hook'),
        ('sms', 'SMS'),
    )
    STATUS_CHOICES = (
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('retried', 'Retried'),
    )

    schedule = models.ForeignKey(
        'InterviewSchedule',
        on_delete=models.CASCADE,
        related_name='reminder_logs'
    )
    stage = models.CharField(max_length=20, choices=STAGE_CHOICES)
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES, default='email')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='sent')
    recipient = models.CharField(max_length=255)
    subject_or_hook = models.CharField(max_length=255)
    error_message = models.TextField(blank=True, null=True)
    retry_count = models.PositiveIntegerField(default=0)
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ai_interview_reminder_logs'
        ordering = ['-sent_at']

    def __str__(self):
        return f"Reminder [{self.stage} - {self.channel}] for Schedule #{self.schedule_id} -> {self.status}"

class AICandidateReport(models.Model):
    """
    Stores aggregated evaluation reports combining ATS scores, AI screening scores,
    identified strengths, risks, and overall hiring recommendations.
    """
    RECOMMENDATION_CHOICES = (
        ('strong_hire', 'Strong Hire'),
        ('hire', 'Hire'),
        ('neutral', 'Needs Second Review'),
        ('do_not_hire', 'Do Not Hire'),
    )

    application = models.OneToOneField(
        'Application',
        on_delete=models.CASCADE,
        related_name='ai_candidate_report'
    )
    ats_score = models.FloatField(default=0.0)
    ai_interview_score = models.FloatField(default=0.0)
    composite_score = models.FloatField(default=0.0)
    recommendation = models.CharField(max_length=30, choices=RECOMMENDATION_CHOICES, default='hire')
    executive_summary = models.TextField()
    strengths = models.JSONField(default=list, blank=True)
    risks = models.JSONField(default=list, blank=True)
    structured_report = models.JSONField(default=dict, blank=True)
    generated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ai_candidate_reports'
        ordering = ['-generated_at']

    def __str__(self):
        return f"Report for App #{self.application_id} - Score: {self.composite_score} ({self.recommendation})"


# ------------------------------------------------------------------------------
# Day 42: System Audit & Security Compliance Models
# ------------------------------------------------------------------------------
class SystemAuditTrail(models.Model):
    """Tracks critical User, Admin, and AI actions for system compliance."""
    ACTOR_TYPE_CHOICES = (
        ('user', 'User Action'),
        ('admin', 'Admin Action'),
        ('ai_system', 'AI System Action'),
    )
    ACTION_CATEGORY_CHOICES = (
        ('auth', 'Authentication & Access'),
        ('job', 'Job Management'),
        ('application', 'Application Status Change'),
        ('ai_eval', 'AI Screening & Scoring'),
        ('scheduling', 'Interview Scheduling'),
        ('admin_mod', 'Admin Moderation'),
    )

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_trails'
    )
    actor_type = models.CharField(max_length=20, choices=ACTOR_TYPE_CHOICES, default='user')
    action_category = models.CharField(max_length=30, choices=ACTION_CATEGORY_CHOICES)
    action_name = models.CharField(max_length=150)
    target_entity = models.CharField(max_length=100, blank=True, null=True)
    target_id = models.CharField(max_length=50, blank=True, null=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, null=True)
    payload_snapshot = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'system_audit_trails'
        ordering = ['-timestamp']

    def __str__(self):
        return f"[{self.actor_type.upper()}] {self.action_name} by {self.actor or 'System'} at {self.timestamp}"


class SecurityFailureLog(models.Model):
    """Tracks unauthorized access attempts, system exceptions, and retried operations."""
    SEVERITY_CHOICES = (
        ('info', 'Informational'),
        ('warning', 'Security Warning'),
        ('critical', 'Critical Security Failure'),
    )
    EVENT_TYPE_CHOICES = (
        ('unauthorized_access', 'Unauthorized Access Attempt'),
        ('forbidden_role', 'Role Permission Violation'),
        ('system_exception', 'System Runtime Exception'),
        ('service_retry', 'Service Retry Failure'),
    )

    event_type = models.CharField(max_length=50, choices=EVENT_TYPE_CHOICES)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='warning')
    endpoint = models.CharField(max_length=255)
    http_method = models.CharField(max_length=10)
    user_identifier = models.CharField(max_length=150, blank=True, null=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    exception_details = models.TextField(blank=True, null=True)
    stack_trace = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'system_security_failure_logs'
        ordering = ['-timestamp']

    def __str__(self):
        return f"[{self.severity.upper()}] {self.event_type} at {self.endpoint} ({self.timestamp})"


# ------------------------------------------------------------------------------
# Day 46: SaaS Monetization, Subscriptions, & Billing Models
# ------------------------------------------------------------------------------
class SubscriptionPlan(models.Model):
    """Defines available SaaS pricing tiers and feature entitlements."""
    TIER_CHOICES = (
        ('free', 'Free Tier'),
        ('pro', 'Pro Tier'),
        ('enterprise', 'Enterprise Tier'),
    )
    BILLING_CYCLE_CHOICES = (
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    )

    name = models.CharField(max_length=50, choices=TIER_CHOICES, unique=True)
    display_title = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    billing_cycle = models.CharField(max_length=20, choices=BILLING_CYCLE_CHOICES, default='monthly')
    max_active_jobs = models.IntegerField(default=2)  # -1 for unlimited
    max_ai_screenings_per_month = models.IntegerField(default=5)  # -1 for unlimited
    has_advanced_analytics = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'subscription_plans'

    def __str__(self):
        return f"{self.display_title} (${self.price}/{self.billing_cycle})"


class UserSubscription(models.Model):
    """Tracks active subscriptions, renewals, and statuses per employer."""
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('past_due', 'Past Due'),
        ('canceled', 'Canceled'),
        ('expired', 'Expired'),
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='subscription'
    )
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT, related_name='subscriptions')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    start_date = models.DateTimeField(default=timezone.now)
    current_period_end = models.DateTimeField()
    cancel_at_period_end = models.BooleanField(default=False)
    grace_period_days = models.IntegerField(default=3)
    monthly_job_posts_used = models.IntegerField(default=0)
    monthly_ai_screenings_used = models.IntegerField(default=0)
    monthly_candidate_views_used = models.IntegerField(default=0)
    last_usage_reset = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_subscriptions'

    def __str__(self):
        return f"{self.user.email} - {self.plan.name} ({self.status})"

    def check_and_update_expiry(self):
        """Automatically checks subscription status, grace period, and deactivates expired plans."""
        now = timezone.now()
        if self.status == 'active' and now > self.current_period_end:
            grace_deadline = self.current_period_end + timedelta(days=self.grace_period_days)
            if now <= grace_deadline:
                self.status = 'past_due'  # In grace period
            else:
                self.status = 'expired'   # Deactivated
            self.save(update_fields=['status'])
        return self.status

    @property
    def is_access_allowed(self):
        """Allows access if plan is active or in grace period."""
        status = self.check_and_update_expiry()
        return status in ['active', 'past_due']

    @property
    def is_valid(self):
        return self.is_access_allowed


class PaymentTransaction(models.Model):
    """Records individual payment charges, gate attempts, and external IDs."""
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('succeeded', 'Succeeded'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='transactions')
    subscription = models.ForeignKey(UserSubscription, on_delete=models.SET_NULL, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default='USD')
    payment_method = models.CharField(max_length=50, default='stripe')
    transaction_reference = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    raw_response = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'payment_transactions'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.transaction_reference} - {self.amount} {self.currency} ({self.status})"


class BillingHistory(models.Model):
    """Maintains invoices and recurring billing logs for audit and compliance."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='billing_invoices')
    transaction = models.OneToOneField(PaymentTransaction, on_delete=models.CASCADE, related_name='invoice')
    invoice_number = models.CharField(max_length=100, unique=True)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    invoice_pdf_url = models.URLField(blank=True, null=True)
    issued_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'billing_history'
        ordering = ['-issued_at']

    def __str__(self):
        return f"Invoice {self.invoice_number} - {self.user.email}"

