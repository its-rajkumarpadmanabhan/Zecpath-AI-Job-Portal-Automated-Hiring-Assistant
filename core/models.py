from django.db import models


class User(models.Model):
    """
    A demo 'User' model representing a candidate/recruiter record for the
    Zecpath domain (kept separate from Django's built-in auth.User, which
    Django itself uses for login/authentication).
    """
    name = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True)
    role = models.CharField(
        max_length=20,
        choices=[("candidate", "Candidate"), ("recruiter", "Recruiter")],
        default="candidate",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.role})"


class Employer(models.Model):
    """One-to-one profile extension of User for recruiter/employer accounts."""
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="employer_profile"
    )
    company_name = models.CharField(max_length=200)
    website = models.URLField(blank=True)

    def __str__(self):
        return self.company_name


class Candidate(models.Model):
    """One-to-one profile extension of User for candidate accounts."""
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="candidate_profile"
    )
    resume = models.FileField(upload_to="resumes/", blank=True)
    skills = models.TextField(blank=True)

    def __str__(self):
        return self.user.name


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