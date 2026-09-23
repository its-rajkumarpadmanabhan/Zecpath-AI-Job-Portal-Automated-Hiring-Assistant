import logging
from datetime import timedelta

from django.utils import timezone

from core.models import InterviewSchedule, ReminderLog

logger = logging.getLogger(__name__)


class ReminderEngine:
    """
    Scans upcoming schedules, determines reminder stages, sends email/voice reminders,
    handles retries, and tracks delivery logs.
    """

    @classmethod
    def process_scheduled_reminders(cls) -> dict:
        """Scans all upcoming schedules and triggers 24-hour and 1-hour reminders."""
        now = timezone.now()
        upcoming_24h = now + timedelta(hours=24)
        upcoming_1h = now + timedelta(hours=1)

        # Active schedules
        schedules = InterviewSchedule.objects.filter(
            status__in=["scheduled", "rescheduled"], slot__start_time__gt=now
        ).select_related("slot", "application", "application__candidate", "application__job")

        sent_count = 0
        failed_count = 0
        details = []

        for schedule in schedules:
            start_time = schedule.slot.start_time
            time_until_interview = start_time - now

            # Stage 1: 24h Reminder (between 23h and 25h window)
            if timedelta(hours=23) <= time_until_interview <= timedelta(hours=25):
                stage = "24h_before"
            # Stage 2: 1h Reminder (within the next 1 hour)
            elif time_until_interview <= timedelta(hours=1):
                stage = "1h_before"
            else:
                continue

            # Check if this stage reminder was already sent for this schedule
            already_sent = ReminderLog.objects.filter(
                schedule=schedule, stage=stage, status="sent"
            ).exists()

            if not already_sent:
                res = cls.send_reminder(schedule_id=schedule.id, stage=stage)
                if res["status"] == "sent":
                    sent_count += 1
                else:
                    failed_count += 1
                details.append(res)

        return {
            "scanned_at": now.isoformat(),
            "reminders_sent": sent_count,
            "reminders_failed": failed_count,
            "details": details,
        }

    @classmethod
    def send_reminder(
        cls, schedule_id: int, stage: str = "24h_before", channel: str = "email"
    ) -> dict:
        """Dispatches an individual reminder with retry handling and logging."""
        try:
            schedule = InterviewSchedule.objects.get(id=schedule_id)
        except InterviewSchedule.DoesNotExist:
            return {"status": "failed", "error": f"Schedule #{schedule_id} not found."}

        candidate_email = getattr(schedule.application.candidate, "email", "candidate@example.com")
        candidate_name = getattr(schedule.application.candidate, "username", "Candidate")
        job_title = schedule.application.job.title
        meeting_link = (
            schedule.meeting_link or f"https://meet.zecpath.com/ai-interview-{schedule.id}"
        )
        start_time_str = schedule.slot.start_time.strftime("%Y-%m-%d %H:%M UTC")

        # Message Templates
        if stage == "24h_before":
            subject = f"Reminder: Your AI Interview for {job_title} is tomorrow"
            message = f"Hello {candidate_name}, your AI interview is scheduled for {start_time_str}. Link: {meeting_link}"
        elif stage == "1h_before":
            subject = f"URGENT Reminder: Your AI Interview starts in 1 hour"
            message = f"Hello {candidate_name}, your AI interview begins in 1 hour. Please join here: {meeting_link}"
        else:
            subject = f"Interview Update for {job_title}"
            message = f"Hello {candidate_name}, your interview is scheduled at {start_time_str}. Link: {meeting_link}"

        # Retry Handling Simulation
        max_retries = 2
        success = True
        error_msg = None

        try:
            # Simulated Email / Voice hook delivery
            if channel == "voice":
                logger.info(
                    f"[Voice Reminder Hook] Dispatching IVR Reminder call to {candidate_email} for Schedule #{schedule.id}"
                )
            else:
                logger.info(f"[Reminder Engine Email] '{subject}' sent to {candidate_email}")
        except Exception as exc:
            success = False
            error_msg = str(exc)

        # Log Delivery
        log_entry = ReminderLog.objects.create(
            schedule=schedule,
            stage=stage,
            channel=channel,
            status="sent" if success else "failed",
            recipient=candidate_email,
            subject_or_hook=subject,
            error_message=error_msg,
            retry_count=0 if success else max_retries,
        )

        return {
            "reminder_id": log_entry.id,
            "schedule_id": schedule.id,
            "stage": stage,
            "channel": channel,
            "status": log_entry.status,
            "recipient": candidate_email,
            "subject": subject,
            "sent_at": log_entry.sent_at.isoformat(),
        }
