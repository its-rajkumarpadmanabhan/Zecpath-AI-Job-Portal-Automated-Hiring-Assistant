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
    """Allows access only to authenticated users with the employer role."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and getattr(request.user, 'role', None) == 'employer')

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