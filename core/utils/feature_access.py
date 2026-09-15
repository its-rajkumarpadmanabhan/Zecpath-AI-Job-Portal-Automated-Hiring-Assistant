from django.core.exceptions import PermissionDenied
from core.models import UserSubscription, Job

class FeatureAccessController:
    """Enforces tier-specific usage limits (job posts, candidate view allowances)."""

    @classmethod
    def can_post_job(cls, user) -> tuple[bool, str]:
        """Validates whether employer has exceeded allowed active job postings."""
        sub = UserSubscription.objects.filter(user=user).select_related('plan').first()
        if not sub or not sub.is_access_allowed:
            return False, "Active subscription required to post jobs."

        max_allowed = sub.plan.max_active_jobs
        if max_allowed == -1:
            return True, "Unlimited job postings allowed."

        active_jobs_count = Job.objects.filter(employer=user, status='active').count()
        if active_jobs_count >= max_allowed:
            return False, f"Job posting limit reached ({active_jobs_count}/{max_allowed}). Upgrade your plan to post more."

        return True, "Authorized to post job."

    @classmethod
    def can_view_candidate_profile(cls, user) -> tuple[bool, str]:
        """Restricts candidate browsing quotas based on tier."""
        sub = UserSubscription.objects.filter(user=user).select_related('plan').first()
        if not sub or not sub.is_access_allowed:
            return False, "Active subscription required to access candidate database."

        if sub.plan.name == 'free' and sub.monthly_candidate_views_used >= 10:
            return False, "Monthly candidate view limit of 10 reached for Free Tier. Upgrade to Pro for unlimited access."

        sub.monthly_candidate_views_used += 1
        sub.save(update_fields=['monthly_candidate_views_used'])
        return True, "Access granted."
