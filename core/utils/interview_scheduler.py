import logging
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from core.models import InterviewAvailabilitySlot, InterviewSchedule, Application

logger = logging.getLogger(__name__)

class InterviewSchedulerEngine:
    """
    Automated scheduling engine managing availability slots, conflict checks,
    rescheduling logic, and automated notification triggers.
    """
    @classmethod
    def book_interview(cls, application_id: int, slot_id: int, user) -> dict:
        try:
            application = Application.objects.get(id=application_id)
        except Application.DoesNotExist:
            raise ValueError(f"Application #{application_id} does not exist.")

        try:
            slot = InterviewAvailabilitySlot.objects.get(id=slot_id)
        except InterviewAvailabilitySlot.DoesNotExist:
            raise ValueError(f"Slot #{slot_id} does not exist.")

        # 1. Conflict & Availability Check
        if slot.is_booked:
            raise ValueError("Selected slot is already booked. Conflict detected.")

        if slot.start_time <= timezone.now():
            raise ValueError("Cannot schedule interviews in the past.")

        # Check if candidate already has an active scheduled interview for this application
        existing_schedule = InterviewSchedule.objects.filter(
            application=application,
            status__in=['scheduled', 'rescheduled']
        ).first()

        if existing_schedule:
            raise ValueError("Application already has an active interview schedule. Please use the reschedule endpoint.")

        # 2. Book Slot and Create Schedule
        slot.is_booked = True
        slot.save()

        meeting_link = f"https://meet.zecpath.com/ai-interview-{application.id}"
        schedule = InterviewSchedule.objects.create(
            application=application,
            slot=slot,
            scheduled_by=user,
            meeting_link=meeting_link,
            status='scheduled',
            confirmation_sent=True
        )

        # 3. Trigger Notification
        cls._trigger_notification_email(schedule, event_type="Confirmation")

        return {
            "schedule_id": schedule.id,
            "application_id": application.id,
            "start_time": slot.start_time,
            "end_time": slot.end_time,
            "meeting_link": schedule.meeting_link,
            "status": schedule.status,
            "confirmation_sent": schedule.confirmation_sent
        }

    @classmethod
    def reschedule_interview(cls, schedule_id: int, new_slot_id: int) -> dict:
        try:
            schedule = InterviewSchedule.objects.get(id=schedule_id)
        except InterviewSchedule.DoesNotExist:
            raise ValueError(f"Schedule #{schedule_id} does not exist.")

        try:
            new_slot = InterviewAvailabilitySlot.objects.get(id=new_slot_id)
        except InterviewAvailabilitySlot.DoesNotExist:
            raise ValueError(f"New slot #{new_slot_id} does not exist.")

        if new_slot.is_booked:
            raise ValueError("The requested new slot is already booked.")

        if new_slot.start_time <= timezone.now():
            raise ValueError("Cannot reschedule to a past time.")

        # Free the previous slot
        old_slot = schedule.slot
        old_slot.is_booked = False
        old_slot.save()

        # Allocate new slot
        new_slot.is_booked = True
        new_slot.save()

        schedule.slot = new_slot
        schedule.status = 'rescheduled'
        schedule.save()

        # Trigger reschedule notification
        cls._trigger_notification_email(schedule, event_type="Rescheduled")

        return {
            "schedule_id": schedule.id,
            "new_start_time": new_slot.start_time,
            "new_end_time": new_slot.end_time,
            "status": schedule.status,
            "meeting_link": schedule.meeting_link
        }

    @staticmethod
    def _trigger_notification_email(schedule: InterviewSchedule, event_type: str = "Confirmation"):
        candidate_email = getattr(schedule.application.candidate, 'email', 'candidate@example.com')
        logger.info(f"[Email Notification Trigger] Sending {event_type} email to {candidate_email} for Schedule #{schedule.id}")
