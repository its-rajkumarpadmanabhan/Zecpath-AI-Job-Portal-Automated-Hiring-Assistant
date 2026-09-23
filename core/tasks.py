import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_async_application_status_email_task(self, application_id):
    """
    Task Queue 1: Email Sending Task
    Offloads sending notification emails for application status updates.
    """
    from core.models import Application

    try:
        application = Application.objects.select_related("candidate", "job").get(pk=application_id)
        candidate = application.candidate
        job = application.job

        subject = f"Zecpath Update: Your application status for '{job.title}'"
        message = (
            f"Hello {candidate.name},\n\n"
            f"Your application status for the position '{job.title}' at '{job.company}' "
            f"has been updated to: {application.get_status_display().upper()}.\n\n"
            f"Log in to your Zecpath candidate dashboard to track details.\n\n"
            f"Best regards,\n"
            f"The Zecpath Hiring Assistant Team"
        )

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[candidate.email],
            fail_silently=False,
        )
        logger.info(
            f"Async email sent successfully to {candidate.email} for application #{application_id}"
        )
        return {"status": "success", "recipient": candidate.email, "application_id": application_id}
    except Application.DoesNotExist:
        logger.error(f"Application #{application_id} not found for async email dispatch.")
        return {"status": "error", "message": "Application not found"}
    except Exception as exc:
        logger.error(f"Failed to send async email for application #{application_id}: {exc}")
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def async_parse_resume_task(self, candidate_id):
    """
    Task Queue 2: Resume Parsing Task
    Extracts text from candidate resume file (PDF/DOCX) asynchronously,
    runs NLP extraction, and populates Candidate profile skills & experience.
    """
    from core.models import Candidate
    from core.utils.resume_nlp import parse_resume_to_json
    from core.utils.resume_parser import parse_resume_file

    try:
        candidate_profile = Candidate.objects.get(pk=candidate_id)
        if not candidate_profile.resume:
            return {"status": "skipped", "reason": "No resume file attached"}

        # 1. Parse raw text from file
        cleaned_text = parse_resume_file(candidate_profile.resume)

        # 2. Extract structured JSON
        parsed_json = parse_resume_to_json(cleaned_text)

        # 3. Update candidate profile fields
        extracted_skills = parsed_json.get("extracted_skills", {}).get("skills_list", [])
        if extracted_skills:
            candidate_profile.skills = ", ".join(extracted_skills)

        summary_data = parsed_json.get("professional_summary", {})
        if summary_data.get("years_of_experience"):
            candidate_profile.experience = f"{summary_data.get('years_of_experience')} years in {summary_data.get('target_role', 'Software')}"

        candidate_profile.save()
        logger.info(f"Async resume parsing completed for candidate profile #{candidate_id}")
        return {
            "status": "success",
            "candidate_id": candidate_id,
            "skills_extracted": len(extracted_skills),
            "parsed_data": parsed_json,
        }
    except Candidate.DoesNotExist:
        logger.error(f"Candidate #{candidate_id} not found for async resume parsing.")
        return {"status": "error", "message": "Candidate profile not found"}
    except Exception as exc:
        logger.error(f"Error during async resume parsing for candidate #{candidate_id}: {exc}")
        raise self.retry(exc=exc)


@shared_task(bind=True)
def async_compute_ats_score_task(self, application_id):
    """
    Task Queue 3: AI Call & ATS Score Calculation Trigger Task
    Calculates ATS score for an application against job requirements asynchronously,
    updates application score, and applies auto-shortlist/rejection threshold rules.
    """
    from core.models import Application
    from core.utils.ats_engine import compute_ats_score
    from core.utils.automation_engine import evaluate_and_apply_auto_action
    from core.utils.resume_nlp import parse_resume_to_json
    from core.utils.resume_parser import parse_resume_file

    try:
        app = Application.objects.select_related("job", "candidate").get(pk=application_id)
        job = app.job

        # Parse resume snapshot if present, else fallback to candidate profile skills
        if app.resume_snapshot:
            try:
                cleaned_text = parse_resume_file(app.resume_snapshot)
                parsed_data = parse_resume_to_json(cleaned_text)
            except Exception:
                cand_skills = getattr(app.candidate, "candidate_profile", None)
                skills_str = cand_skills.skills if cand_skills else ""
                parsed_data = {
                    "extracted_skills": {
                        "skills_list": [s.strip() for s in skills_str.split(",") if s.strip()]
                    },
                    "professional_summary": {"years_of_experience": 0, "target_role": ""},
                }
        else:
            cand_skills = getattr(app.candidate, "candidate_profile", None)
            skills_str = cand_skills.skills if cand_skills else ""
            parsed_data = {
                "extracted_skills": {
                    "skills_list": [s.strip() for s in skills_str.split(",") if s.strip()]
                },
                "professional_summary": {"years_of_experience": 0, "target_role": ""},
            }

        # Calculate ATS match score
        ats_result = compute_ats_score(job, parsed_data)
        app.ats_score = float(ats_result.get("suitability_score", 0.0))
        app.save()

        # Apply automated threshold evaluation
        prev_status, new_status, action = evaluate_and_apply_auto_action(app)

        logger.info(
            f"Async ATS scoring completed for App #{application_id}: Score={app.ats_score}%, Status={new_status}"
        )
        return {
            "status": "success",
            "application_id": application_id,
            "ats_score": app.ats_score,
            "previous_status": prev_status,
            "new_status": new_status,
            "action_taken": action,
        }
    except Application.DoesNotExist:
        logger.error(f"Application #{application_id} not found for async ATS scoring.")
        return {"status": "error", "message": "Application not found"}


@shared_task
def periodic_batch_auto_screening_task():
    """
    Cron Task 1: Hourly Periodic Task (Celery Beat)
    Scans all active job postings and triggers auto-screening on pending applications.
    """
    from core.models import Job
    from core.utils.automation_engine import process_batch_auto_shortlist

    logger.info("Executing periodic_batch_auto_screening_task cron job...")
    active_jobs = Job.objects.filter(status="active")
    total_screened = 0

    for job in active_jobs:
        summary = process_batch_auto_shortlist(job)
        total_screened += summary.get("total_processed", 0)

    logger.info(
        f"Periodic auto-screening cron completed. Total applications screened: {total_screened}"
    )
    return {
        "status": "completed",
        "active_jobs_checked": active_jobs.count(),
        "total_screened": total_screened,
    }


@shared_task
def periodic_system_analytics_digest_task():
    """
    Cron Task 2: Daily Periodic Task (Celery Beat)
    Generates daily operational system metrics digest.
    """
    from core.models import Application, Job, User

    total_users = User.objects.count()
    total_candidates = User.objects.filter(role="candidate").count()
    total_recruiters = User.objects.filter(role="recruiter").count()
    active_jobs = Job.objects.filter(status="active").count()
    total_applications = Application.objects.count()
    shortlisted_applications = Application.objects.filter(status="shortlisted").count()

    digest_summary = (
        f"--- Zecpath Daily System Analytics Digest ---\n"
        f"Total Registered Users: {total_users} (Candidates: {total_candidates}, Recruiters: {total_recruiters})\n"
        f"Active Job Postings: {active_jobs}\n"
        f"Total Applications Received: {total_applications}\n"
        f"Total Candidates Shortlisted: {shortlisted_applications}\n"
    )

    logger.info(digest_summary)
    return {
        "status": "digest_generated",
        "total_users": total_users,
        "active_jobs": active_jobs,
        "total_applications": total_applications,
        "shortlisted_applications": shortlisted_applications,
    }


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def execute_ai_call_task(self, ai_call_id):
    """
    Task Queue 4: AI Call Execution Task
    Simulates making a third-party API call (e.g., Twilio, Bland AI) for the AI screening.
    Handles scheduling, calling windows, status tracking, and failure retries.
    """
    from django.utils import timezone

    from core.models import AICall

    try:
        ai_call = AICall.objects.select_related("application__job", "application__candidate").get(
            pk=ai_call_id
        )

        if ai_call.status in ["completed", "cancelled"]:
            logger.info(f"AICall #{ai_call_id} skipped: status is '{ai_call.status}'")
            return {"status": "skipped", "reason": f"Call already {ai_call.status}"}

        # Mark as in progress
        ai_call.status = "in_progress"
        ai_call.save(update_fields=["status", "updated_at"])

        logger.info(
            f"Initiating AI call to candidate ({ai_call.application.candidate.email}) for App #{ai_call.application_id}..."
        )

        # Mark call as completed
        ai_call.status = "completed"
        ai_call.completed_at = timezone.now()
        ai_call.error_notes = None
        ai_call.save(update_fields=["status", "completed_at", "error_notes", "updated_at"])

        logger.info(f"AI call completed successfully for App #{ai_call.application_id}.")
        return {
            "status": "success",
            "ai_call_id": ai_call_id,
            "completed_at": ai_call.completed_at.isoformat(),
        }

    except AICall.DoesNotExist:
        logger.error(f"AICall #{ai_call_id} not found.")
        return {"status": "error", "message": "AICall not found"}
    except Exception as exc:
        try:
            ai_call = AICall.objects.get(pk=ai_call_id)
            ai_call.retry_count = self.request.retries + 1
            ai_call.error_notes = f"Execution failure: {str(exc)}"
            ai_call.status = "failed" if self.request.retries >= self.max_retries else "queued"
            ai_call.save(update_fields=["retry_count", "error_notes", "status", "updated_at"])
        except Exception:
            pass
        logger.error(f"Failed to execute AI call #{ai_call_id}: {exc}")
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_interview_confirmation_email_task(self, schedule_id):
    """
    Task Queue 5: Interview Scheduling Confirmation
    Sends an email to the candidate when an interview is scheduled or rescheduled.
    """
    from core.models import InterviewSchedule

    try:
        schedule = InterviewSchedule.objects.select_related(
            "application__candidate", "application__job", "slot"
        ).get(pk=schedule_id)

        candidate = schedule.application.candidate
        job = schedule.application.job
        slot = schedule.slot

        if not slot:
            return {"status": "skipped", "reason": "No slot assigned"}

        action = "Scheduled" if schedule.status == "scheduled" else "Rescheduled"

        subject = f"Zecpath: Interview {action} for '{job.title}'"
        message = (
            f"Hello {candidate.name},\n\n"
            f"Your interview for the position '{job.title}' at '{job.company}' "
            f"has been successfully {action.lower()}.\n\n"
            f"Date: {slot.date}\n"
            f"Time: {slot.start_time} - {slot.end_time}\n"
        )
        if schedule.meeting_link:
            message += f"Meeting Link: {schedule.meeting_link}\n"

        message += (
            f"\nLog in to your Zecpath dashboard for more details or if you need to reschedule.\n\n"
            f"Best regards,\n"
            f"The Zecpath Hiring Assistant Team"
        )

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[candidate.email],
            fail_silently=False,
        )
        logger.info(
            f"Interview confirmation email sent successfully to {candidate.email} for schedule #{schedule_id}"
        )
        return {"status": "success", "recipient": candidate.email, "schedule_id": schedule_id}
    except InterviewSchedule.DoesNotExist:
        logger.error(f"InterviewSchedule #{schedule_id} not found for email dispatch.")
        return {"status": "error", "message": "InterviewSchedule not found"}
    except Exception as exc:
        logger.error(
            f"Failed to send interview confirmation email for schedule #{schedule_id}: {exc}"
        )
        raise self.retry(exc=exc)


from core.utils.reminder_engine import ReminderEngine


@shared_task(name="scan_and_send_interview_reminders")
def scan_and_send_interview_reminders_task():
    """Daily / hourly cron job scanning upcoming interviews and dispatching reminders."""
    return ReminderEngine.process_scheduled_reminders()
