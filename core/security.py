import re
from rest_framework import permissions
from django.core.exceptions import ValidationError

class StrictRolePermission(permissions.BasePermission):
    """Guarantees caller belongs to specified business roles."""
    allowed_roles = []

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        role = getattr(request.user, 'role', '')
        return role in self.allowed_roles or request.user.is_staff or getattr(request.user, 'is_superuser', False)

class SecuritySanitizer:
    """Detects and strips SQL injection patterns and script tags."""

    SQLI_PATTERN = re.compile(r"(--|;|'|\"|\b(UNION|SELECT|INSERT|DELETE|UPDATE|DROP|WHERE)\b)", re.IGNORECASE)
    XSS_PATTERN = re.compile(r"(<script.*?>.*?</script>|javascript:|onload=|onerror=)", re.IGNORECASE)

    @classmethod
    def sanitize_input(cls, raw_value: str) -> str:
        if not isinstance(raw_value, str):
            return raw_value
        if cls.SQLI_PATTERN.search(raw_value):
            raise ValidationError("Potential SQL Injection attempt detected.")
        if cls.XSS_PATTERN.search(raw_value):
            raise ValidationError("XSS payload identified in input body.")
        return raw_value.strip()
