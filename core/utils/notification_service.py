
import threading
from django.core.mail import send_mail
from django.conf import settings

def send_async_email(subject, text_message, html_message, recipient_list):
    """
    Executes email sending inside a separate background thread 
    to keep API response times lightning fast.
    """
    def _send():
        try:
            send_mail(
                subject=subject,
                message=text_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=recipient_list,
                html_message=html_message,
                fail_silently=False
            )
            print(f"✅ Notification email successfully sent to {recipient_list}")
        except Exception as e:
            print(f"❌ Failed to deliver email to {recipient_list}: {str(e)}")

    # Spin up background thread
    thread = threading.Thread(target=_send)
    thread.start()


def trigger_application_status_notification(application):
    """
    Triggers event-based email notifications based on application status transitions.
    """
    candidate = application.candidate
    job = application.job
    status = application.status.lower()

    if status == 'shortlisted':
        subject = f"Congratulations! You've been shortlisted for {job.title} at {job.company}"
        text_message = f"Hello {candidate.name},\n\nGreat news! Your profile was shortlisted for {job.title}."
        html_message = f"""
            <h3>Congratulations, {candidate.name}!</h3>
            <p>We are pleased to inform you that you have been <b>shortlisted</b> for the position of <strong>{job.title}</strong> at <strong>{job.company}</strong>.</p>
            <p>Our hiring team will be in touch with you shortly regarding the next steps.</p>
            <br/><p>Best regards,<br/>The Hiring Team</p>
        """
    elif status == 'rejected':
        subject = f"Update regarding your application for {job.title}"
        text_message = f"Hello {candidate.name},\n\nThank you for applying for {job.title}."
        html_message = f"""
            <h3>Hello {candidate.name},</h3>
            <p>Thank you for taking the time to apply for the <strong>{job.title}</strong> position at <strong>{job.company}</strong>.</p>
            <p>After careful consideration, we regret to inform you that we will not be moving forward with your application at this time.</p>
            <br/><p>Best regards,<br/>The Hiring Team</p>
        """
    elif status == 'applied':
        subject = f"Application Received: {job.title}"
        text_message = f"Hello {candidate.name},\n\nWe received your application for {job.title}."
        html_message = f"""
            <h3>Hello {candidate.name},</h3>
            <p>Your application for <strong>{job.title}</strong> at <strong>{job.company}</strong> has been successfully submitted!</p>
            <br/><p>Best regards,<br/>The Hiring Team</p>
        """
    else:
        return

    # Trigger background worker thread
    send_async_email(
        subject=subject,
        text_message=text_message,
        html_message=html_message,
        recipient_list=[candidate.email]
    )