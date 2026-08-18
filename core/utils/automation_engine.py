from core.models import Application
from .notification_service import trigger_application_status_notification

# Default Threshold Cutoffs (Percentages)
DEFAULT_SHORTLIST_THRESHOLD = 70.0
DEFAULT_REJECT_THRESHOLD = 40.0


def evaluate_and_apply_auto_action(application, shortlist_threshold=DEFAULT_SHORTLIST_THRESHOLD, reject_threshold=DEFAULT_REJECT_THRESHOLD):
    """
    Evaluates an application's ATS score against cutoffs, automatically updates its status,
    and fires event-based email notifications on status change.
    """
    prev_status = application.status
    score = application.ats_score
    action_taken = "no_change"

    # 1. Check Shortlist Cutoff
    if score >= shortlist_threshold:
        application.status = "shortlisted"
        action_taken = "auto_shortlisted"

    # 2. Check Rejection Cutoff
    elif score < reject_threshold:
        application.status = "rejected"
        action_taken = "auto_rejected"

    # 3. Otherwise remain in 'applied' / under review
    else:
        action_taken = "retained_for_manual_review"

    # Save and trigger notification if status changed
    if prev_status != application.status:
        application.save()
        trigger_application_status_notification(application)
        
        # Trigger AI Screening call if auto shortlisted
        if action_taken == "auto_shortlisted":
            from .ai_call_engine import trigger_ai_call
            trigger_ai_call(application)

    return prev_status, application.status, action_taken


def process_batch_auto_shortlist(job, shortlist_threshold=DEFAULT_SHORTLIST_THRESHOLD, reject_threshold=DEFAULT_REJECT_THRESHOLD):
    """
    Batch processes all 'applied' status applications for a job posting.
    """
    pending_applications = Application.objects.filter(job=job, status='applied')
    
    summary = {
        "total_processed": 0,
        "auto_shortlisted": 0,
        "auto_rejected": 0,
        "under_review": 0
    }

    for app in pending_applications:
        _, new_status, action = evaluate_and_apply_auto_action(
            app, shortlist_threshold, reject_threshold
        )
        summary["total_processed"] += 1

        if action == "auto_shortlisted":
            summary["auto_shortlisted"] += 1
        elif action == "auto_rejected":
            summary["auto_rejected"] += 1
        else:
            summary["under_review"] += 1

    return summary