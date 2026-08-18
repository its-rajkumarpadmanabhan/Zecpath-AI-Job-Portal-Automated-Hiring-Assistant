import logging
from datetime import timedelta
from django.utils import timezone
from core.models import AICall, Application

logger = logging.getLogger(__name__)

# Configurable thresholds
AI_CALL_ATS_THRESHOLD = 75.0


def check_eligibility(application):
    """
    Evaluates if an application is eligible for an AI Screening Call.
    1. Job must be 'active'.
    2. ATS score must be above the threshold.
    3. Candidate must be active and not deleted.
    """
    if application.job.status != 'active':
        logger.info(f"App #{application.id} not eligible for AI call: Job is {application.job.status}")
        return False
        
    if application.ats_score < AI_CALL_ATS_THRESHOLD:
        logger.info(f"App #{application.id} not eligible for AI call: Score {application.ats_score} < {AI_CALL_ATS_THRESHOLD}")
        return False
        
    candidate_user = application.candidate
    if not candidate_user.is_active or candidate_user.candidate_profile.is_deleted:
        logger.info(f"App #{application.id} not eligible for AI call: Candidate is inactive or deleted")
        return False

    return True


def trigger_ai_call(application, delay_minutes=5):
    """
    Checks eligibility and schedules an AI Call for the candidate.
    """
    if not check_eligibility(application):
        return None

    # Check if a call is already scheduled or completed
    if hasattr(application, 'ai_call'):
        logger.info(f"App #{application.id} already has an AI call scheduled/completed.")
        return application.ai_call

    # Create the AI Call record
    scheduled_time = timezone.now() + timedelta(minutes=delay_minutes)
    ai_call = AICall.objects.create(
        application=application,
        status='queued',
        scheduled_at=scheduled_time
    )
    
    logger.info(f"AI Call queued for App #{application.id} at {scheduled_time}")

    # Schedule the celery task
    from core.tasks import execute_ai_call_task
    execute_ai_call_task.apply_async(
        args=[ai_call.id], 
        eta=scheduled_time
    )

    return ai_call
