from django.http import JsonResponse
from django.utils import timezone

from core.models import UserSubscription


class PaidFeatureAccessMiddleware:
    """
    Middleware that intercepts requests to premium endpoints, verifies
    subscription validity, checks grace periods, and enforces access boundaries.
    """

    def __init__(self, get_response):
        self.get_response = get_response

        # Gated endpoints requiring an active paid subscription
        self.gated_prefixes = [
            "/api/recruiter/analytics/",
            "/api/recruiter/applications/",
            "/api/monitoring/audit-trails/",
        ]

    def __call__(self, request):
        path = request.path

        if any(path.startswith(prefix) for prefix in self.gated_prefixes):
            # Resolve user from request.user, DRF force_auth, or JWT
            user = getattr(request, "user", None)
            if not user or not user.is_authenticated:
                if hasattr(request, "_force_auth_user") and request._force_auth_user:
                    user = request._force_auth_user
                    request.user = user
                else:
                    from rest_framework_simplejwt.authentication import \
                        JWTAuthentication

                    try:
                        auth_res = JWTAuthentication().authenticate(request)
                        if auth_res is not None:
                            user, _ = auth_res
                            request.user = user
                    except Exception:
                        pass

            if not user or not user.is_authenticated:
                return JsonResponse(
                    {"error": "Authentication required for premium services."}, status=401
                )

            # Admins bypass subscription checks
            if (
                getattr(user, "role", "") == "admin"
                or getattr(user, "is_staff", False)
                or getattr(user, "is_superuser", False)
            ):
                return self.get_response(request)

            sub = UserSubscription.objects.filter(user=user).select_related("plan").first()
            if not sub:
                return JsonResponse(
                    {
                        "error": "Subscription Required",
                        "detail": "An active subscription is required to access this feature.",
                    },
                    status=403,
                )

            # Validate expiration and grace period
            if not sub.is_access_allowed:
                return JsonResponse(
                    {
                        "error": "Subscription Expired",
                        "detail": f"Your plan status is '{sub.status}'. Please renew to regain access.",
                    },
                    status=403,
                )

            # Check tier entitlements for advanced analytics
            if "/api/recruiter/analytics/" in path and not sub.plan.has_advanced_analytics:
                return JsonResponse(
                    {
                        "error": "Upgrade Required",
                        "detail": "Advanced Recruiter Analytics requires a Pro or Enterprise plan.",
                    },
                    status=403,
                )

        return self.get_response(request)
