from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    message = "Only admins can perform this action."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (request.user.is_staff or request.user.is_superuser)
        )
class IsAdminUserRole(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            (request.user.is_staff or getattr(request.user, 'role', '') == 'admin')
        )

class IsEmployer(BasePermission):
    """Allows access only to authenticated users with the employer/recruiter role."""
    def has_permission(self, request, view):
        return bool(
            request.user 
            and request.user.is_authenticated 
            and getattr(request.user, 'role', None) in ['recruiter', 'employer']
        )


class IsEmployerAndOwner(BasePermission):
    """Allows access only to the employer who created the job post."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == 'recruiter')

    def has_object_permission(self, request, view, obj):
        return obj.employer == request.user


class IsCandidate(BasePermission):
    message = "Only candidates can perform this action."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == "candidate"
        )


class RequiresActiveSubscription(BasePermission):
    """Requires the authenticated user to hold an active paid or free subscription."""
    message = "An active subscription plan is required to access this feature."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        sub = getattr(request.user, 'subscription', None)
        return sub is not None and sub.is_valid


class RequiresTier(BasePermission):
    """Base class for tier-specific feature gates."""
    required_tiers = []

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        sub = getattr(request.user, 'subscription', None)
        if not sub or not sub.is_valid:
            return False
        return sub.plan.name in self.required_tiers


class RequiresProOrEnterpriseTier(RequiresTier):
    """Gates access to advanced recruiter analytics and high-volume tools."""
    required_tiers = ['pro', 'enterprise']
    message = "This endpoint requires an active Pro or Enterprise subscription."


# ==============================================================================
# DAY 49: PREMIUM RECRUITER INSIGHTS PERMISSIONS & THROTTLING
# ==============================================================================
from rest_framework.throttling import SimpleRateThrottle

class IsRecruiterWithPaidPlan(BasePermission):
    """Requires the caller to be an employer/recruiter with an active Pro or Enterprise plan."""
    message = "Access restricted: Requires a Recruiter account with an active Pro or Enterprise plan."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        # Admin bypass
        if getattr(request.user, 'role', '') == 'admin' or request.user.is_staff or getattr(request.user, 'is_superuser', False):
            return True

        # Validate Recruiter / Employer role
        user_role = str(getattr(request.user, 'role', '')).lower()
        if user_role not in ['employer', 'recruiter']:
            return False

        # Validate Active Subscription & Tier Entitlements
        sub = getattr(request.user, 'subscription', None)
        if not sub or not sub.is_access_allowed:
            return False

        return sub.plan.name in ['pro', 'enterprise']


class PremiumInsightsRateThrottle(SimpleRateThrottle):
    """Prevents quota abuse and scraping on high-overhead premium insights."""
    scope = 'premium_insights'
    rate = '15/minute'

    def get_cache_key(self, request, view):
        if request.user.is_authenticated:
            return f"throttle_premium_user_{request.user.id}"
        return self.get_ident(request)
