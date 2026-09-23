import logging
import traceback

from core.models import SecurityFailureLog, SystemAuditTrail

logger = logging.getLogger("observability")


class ObservabilityService:
    """Central logging, audit trailing, failure tracking, and security monitoring service."""

    @staticmethod
    def get_client_ip(request) -> str:
        if not request:
            return "127.0.0.1"
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "127.0.0.1")

    @classmethod
    def log_audit(
        cls,
        request=None,
        actor=None,
        actor_type="user",
        action_category="application",
        action_name="",
        target_entity="",
        target_id=None,
        payload=None,
    ) -> SystemAuditTrail:
        """Records user, admin, or AI system actions."""
        ip_addr = cls.get_client_ip(request) if request else "127.0.0.1"
        u_agent = request.META.get("HTTP_USER_AGENT", "System") if request else "System"
        actor_user = actor or (request.user if request and request.user.is_authenticated else None)

        audit_entry = SystemAuditTrail.objects.create(
            actor=actor_user,
            actor_type=actor_type,
            action_category=action_category,
            action_name=action_name,
            target_entity=target_entity,
            target_id=str(target_id) if target_id else None,
            ip_address=ip_addr,
            user_agent=u_agent,
            payload_snapshot=payload or {},
        )
        logger.info(
            f"[AUDIT TRAIL] {actor_type.upper()} '{action_name}' on {target_entity} #{target_id}"
        )
        return audit_entry

    @classmethod
    def log_security_or_failure(
        cls,
        request=None,
        event_type="unauthorized_access",
        severity="warning",
        exception=None,
        custom_message=None,
    ) -> SecurityFailureLog:
        """Records security violations, unauthorized access, or system failures."""
        endpoint = request.path if request else "Internal System"
        method = request.method if request else "SYS"
        ip_addr = cls.get_client_ip(request) if request else "127.0.0.1"
        user_id = str(request.user) if request and request.user.is_authenticated else "Anonymous"

        stack = traceback.format_exc() if exception else None
        details = str(exception) if exception else (custom_message or "Security policy alert")

        log_entry = SecurityFailureLog.objects.create(
            event_type=event_type,
            severity=severity,
            endpoint=endpoint,
            http_method=method,
            user_identifier=user_id,
            ip_address=ip_addr,
            exception_details=details,
            stack_trace=stack if stack != "NoneType: None\n" else None,
        )
        logger.warning(
            f"[SECURITY/FAILURE LOG] [{severity.upper()}] {event_type} on {method} {endpoint}: {details}"
        )
        return log_entry
