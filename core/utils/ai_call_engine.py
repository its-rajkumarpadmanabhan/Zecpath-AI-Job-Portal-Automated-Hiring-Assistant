import logging
from datetime import timedelta
from django.utils import timezone
from core.models import AICall, Application

logger = logging.getLogger(__name__)

# Configurable defaults
AI_CALL_ATS_THRESHOLD = 75.0
DEFAULT_CALLING_WINDOW_START = 9   # 9:00 AM
DEFAULT_CALLING_WINDOW_END = 18    # 6:00 PM
MAX_RETRY_COUNT = 3

def check_eligibility(application, ats_threshold=AI_CALL_ATS_THRESHOLD):
    """
    Evaluates if an application is eligible for an AI Screening Call.
    Rules:
    1. Job must be 'active'.
    2. ATS score must meet or exceed the score threshold.
    3. Candidate user must be active and profile not soft-deleted.
    
    Returns:
        (is_eligible: bool, reason: str)
    """
    if application.job.status != 'active':
        reason = f"Job status is '{application.job.status}' (must be 'active')"
        logger.info(f"App #{application.id} not eligible: {reason}")
        return False, reason

    if application.ats_score < ats_threshold:
        reason = f"ATS score ({application.ats_score}%) is below threshold ({ats_threshold}%)"
        logger.info(f"App #{application.id} not eligible: {reason}")
        return False, reason

    candidate_user = application.candidate
    if not candidate_user.is_active:
        reason = "Candidate user account is inactive"
        logger.info(f"App #{application.id} not eligible: {reason}")
        return False, reason

    candidate_profile = getattr(candidate_user, 'candidate_profile', None)
    if candidate_profile and candidate_profile.is_deleted:
        reason = "Candidate profile is soft-deleted"
        logger.info(f"App #{application.id} not eligible: {reason}")
        return False, reason

    return True, "Eligible for AI Screening Call"


def is_within_calling_window(dt=None, window_start=DEFAULT_CALLING_WINDOW_START, window_end=DEFAULT_CALLING_WINDOW_END):
    """
    Checks if a given datetime (or current time if None) falls within permitted calling hours.
    """
    if dt is None:
        dt = timezone.now()
    return window_start <= dt.hour < window_end


def get_next_valid_call_time(base_time=None, delay_minutes=5, window_start=DEFAULT_CALLING_WINDOW_START, window_end=DEFAULT_CALLING_WINDOW_END):
    """
    Calculates scheduled call time based on delay_minutes.
    If the target time falls outside permitted calling hours [window_start, window_end],
    shifts scheduled time to window_start of current or next day.
    """
    if base_time is None:
        base_time = timezone.now()

    target_time = base_time + timedelta(minutes=delay_minutes)

    if target_time.hour < window_start:
        # Before calling window today -> shift to window_start today
        target_time = target_time.replace(hour=window_start, minute=0, second=0, microsecond=0)
    elif target_time.hour >= window_end:
        # After calling window today -> shift to window_start tomorrow
        next_day = target_time + timedelta(days=1)
        target_time = next_day.replace(hour=window_start, minute=0, second=0, microsecond=0)

    return target_time


def trigger_ai_call(application, delay_minutes=5, ats_threshold=AI_CALL_ATS_THRESHOLD, force=False):
    """
    Checks eligibility and schedules an AI Call for an application.
    If force=True, bypasses score and job status checks (useful for recruiter manual override).
    
    Returns:
        (ai_call: AICall|None, message: str)
    """
    if not force:
        is_eligible, reason = check_eligibility(application, ats_threshold=ats_threshold)
        if not is_eligible:
            return None, f"Eligibility failed: {reason}"

    # Check existing call status
    if hasattr(application, 'ai_call'):
        existing_call = application.ai_call
        if existing_call.status == 'completed':
            return existing_call, "AI Call already completed for this application"
        elif existing_call.status in ['queued', 'in_progress']:
            return existing_call, f"AI Call already in '{existing_call.status}' state"
        elif existing_call.status in ['failed', 'cancelled']:
            # Re-queue existing failed/cancelled call
            scheduled_time = get_next_valid_call_time(delay_minutes=delay_minutes)
            existing_call.status = 'queued'
            existing_call.scheduled_at = scheduled_time
            existing_call.error_notes = None
            existing_call.retry_count = 0
            existing_call.save()

            _dispatch_call_task(existing_call)
            return existing_call, f"Re-queued previously {existing_call.status} AI Call"

    # Create new AI Call
    scheduled_time = get_next_valid_call_time(delay_minutes=delay_minutes)
    ai_call = AICall.objects.create(
        application=application,
        status='queued',
        scheduled_at=scheduled_time
    )

    logger.info(f"AI Call queued for App #{application.id} at {scheduled_time}")
    _dispatch_call_task(ai_call)

    return ai_call, "AI Call queued successfully"


def retry_ai_call(ai_call, delay_minutes=5):
    """
    Retries a failed or cancelled AI Call if max retries limit is not exceeded.
    
    Returns:
        (success: bool, message: str)
    """
    if ai_call.status == 'completed':
        return False, "Cannot retry a completed call"

    if ai_call.retry_count >= MAX_RETRY_COUNT:
        return False, f"Maximum retry attempts ({MAX_RETRY_COUNT}) reached for this call"

    scheduled_time = get_next_valid_call_time(delay_minutes=delay_minutes)
    ai_call.status = 'queued'
    ai_call.scheduled_at = scheduled_time
    ai_call.retry_count += 1
    ai_call.error_notes = f"Manual retry attempt #{ai_call.retry_count}"
    ai_call.save()

    _dispatch_call_task(ai_call)
    logger.info(f"Retrying AI Call #{ai_call.id} (Attempt #{ai_call.retry_count})")
    return True, f"AI Call scheduled for retry attempt #{ai_call.retry_count}"


def cancel_ai_call(ai_call, reason="Cancelled by user"):
    """
    Cancels a queued or in_progress AI Call.
    """
    if ai_call.status == 'completed':
        return False, "Cannot cancel a completed call"

    ai_call.status = 'cancelled'
    ai_call.error_notes = reason
    ai_call.save()
    logger.info(f"AI Call #{ai_call.id} cancelled: {reason}")
    return True, "AI Call cancelled successfully"


def _dispatch_call_task(ai_call):
    """
    Schedules Celery task execution for an AI Call.
    """
    try:
        from core.tasks import execute_ai_call_task
        execute_ai_call_task.apply_async(
            args=[ai_call.id],
            eta=ai_call.scheduled_at
        )
    except Exception as exc:
        logger.warning(f"Celery dispatch note for AICall #{ai_call.id}: {exc}")

