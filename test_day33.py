import os
import django
from datetime import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zecpath_backend.settings')
django.setup()

from django.conf import settings
settings.CELERY_TASK_ALWAYS_EAGER = True
settings.CELERY_TASK_STORE_EAGER_RESULT = True
settings.CELERY_RESULT_BACKEND = 'cache+memory://'

from rest_framework.test import APIClient
from core.models import User, Candidate, Employer, Job, Application, AICall
from core.utils.ai_call_engine import (
    check_eligibility, 
    trigger_ai_call, 
    retry_ai_call, 
    cancel_ai_call,
    get_next_valid_call_time,
    is_within_calling_window
)
from core.utils.automation_engine import evaluate_and_apply_auto_action
from core.tasks import execute_ai_call_task

def run_day33_tests():
    print("==================================================")
    print("  REAL-WORLD DAY 33 ENGINE & API VERIFICATION    ")
    print("==================================================")

    # 1. Setup Real-world Test Data
    recruiter, _ = User.objects.get_or_create(
        email="sarah.jenkins@nexustech.io",
        defaults={"name": "Sarah Jenkins", "role": "recruiter", "is_active": True}
    )
    employer_profile, _ = Employer.objects.get_or_create(
        user=recruiter, 
        defaults={
            "company_name": "Nexus Cloud Technologies",
            "domain": "Cloud Infrastructure & AI",
            "company_size": "250-500 employees",
            "is_verified": True
        }
    )

    active_job, _ = Job.objects.get_or_create(
        title="Senior AI Infrastructure & Backend Engineer",
        employer=recruiter,
        defaults={
            "company": "Nexus Cloud Technologies",
            "description": "Building high-throughput distributed pipelines, real-time AI model orchestrations, and REST microservices in Python & Django.",
            "skills_required": "Python, Django, FastAPI, Celery, Redis, PostgreSQL, Docker, Kubernetes",
            "experience_required": "5+ years",
            "salary_min": 140000.00,
            "salary_max": 180000.00,
            "location": "San Francisco, CA (Hybrid)",
            "job_type": "full_time",
            "status": "active"
        }
    )
    active_job.status = 'active'
    active_job.save()

    closed_job, _ = Job.objects.get_or_create(
        title="Legacy System Support Specialist",
        employer=recruiter,
        defaults={
            "company": "Nexus Cloud Technologies",
            "description": "Archived role for backend legacy maintenance.",
            "skills_required": "COBOL, Perl",
            "experience_required": "10 years",
            "status": "closed"
        }
    )
    closed_job.status = 'closed'
    closed_job.save()

    candidate_user, _ = User.objects.get_or_create(
        email="alex.rivera@devmail.org",
        defaults={"name": "Alex Rivera", "role": "candidate", "is_active": True}
    )
    candidate_user.is_active = True
    candidate_user.save()

    candidate_profile, _ = Candidate.objects.get_or_create(
        user=candidate_user, 
        defaults={
            "skills": "Python, Django, FastAPI, Celery, Redis, PostgreSQL, Docker, Kubernetes",
            "education": "B.S. in Computer Science - UC Berkeley",
            "experience": "5 years building backend services and AI task queues.",
            "expected_salary": 160000.00,
            "is_deleted": False
        }
    )
    candidate_profile.is_deleted = False
    candidate_profile.save()

    # Clear prior test AICall records for an explicit clean run
    AICall.objects.all().delete()
    Application.objects.filter(candidate=candidate_user).delete()

    app_high_score = Application.objects.create(
        candidate=candidate_user,
        job=active_job,
        status='applied',
        ats_score=92.5
    )

    app_low_score = Application.objects.create(
        candidate=candidate_user,
        job=closed_job,
        status='applied',
        ats_score=48.0
    )

    print("\n--- Test 1: Real-World Eligibility Rules Engine ---")
    eligible, reason = check_eligibility(app_high_score, ats_threshold=75.0)
    print(f"Candidate '{candidate_user.name}' ({app_high_score.ats_score}% ATS score) Eligibility: {eligible} (Reason: {reason})")
    assert eligible is True, "High score active application must be eligible"

    eligible_low, reason_low = check_eligibility(app_low_score, ats_threshold=75.0)
    print(f"Candidate '{candidate_user.name}' (Closed Job Application) Eligibility: {eligible_low} (Reason: {reason_low})")
    assert eligible_low is False, "Closed job application must NOT be eligible"

    print("\n--- Test 2: Time-Window Scheduling Calculation ---")
    next_time = get_next_valid_call_time(delay_minutes=15)
    print(f"Calculated scheduled call time: {next_time} (Hour: {next_time.hour} UTC)")
    assert 9 <= next_time.hour <= 18, "Next call time hour must fall within calling window [9, 18]"

    print("\n--- Test 3: Event-Driven Auto Screening & Call Trigger ---")
    prev_status, new_status, action = evaluate_and_apply_auto_action(app_high_score)
    print(f"Auto-action taken: {action}, Updated status: {new_status}")
    assert new_status == 'shortlisted', "App score 92.5% >= 70.0% must be auto-shortlisted"
    assert hasattr(app_high_score, 'ai_call'), "AI Call record must be created on auto-shortlisting"
    ai_call = app_high_score.ai_call
    print(f"Created AICall: ID={ai_call.id}, Candidate={candidate_user.email}, Status={ai_call.status}, ScheduledAt={ai_call.scheduled_at}")
    assert ai_call.status in ['queued', 'completed'], "AICall status should be queued or completed in eager mode"

    print("\n--- Test 4: Real Task Execution & Retry Logic ---")
    call_to_retry = AICall.objects.create(
        application=app_low_score,
        status='failed',
        scheduled_at=next_time,
        error_notes="Network timeout during carrier connection"
    )
    success_retry, retry_msg = retry_ai_call(call_to_retry)
    print(f"Retry Attempt #1 Result: Success={success_retry}, Message={retry_msg}")
    assert success_retry is True
    assert call_to_retry.retry_count == 1
    assert call_to_retry.status == 'queued'

    success_cancel, cancel_msg = cancel_ai_call(call_to_retry, reason="Recruiter manually cancelled schedule")
    print(f"Cancel Action Result: Success={success_cancel}, Message={cancel_msg}")
    assert success_cancel is True
    assert call_to_retry.status == 'cancelled'

    print("\n--- Test 5: Real-World REST API Endpoint Verification ---")
    client = APIClient()
    client.force_authenticate(user=recruiter)

    # API 1: Trigger AI Call via POST /api/aicalls/trigger/
    trigger_payload = {
        "application_id": app_high_score.id,
        "delay_minutes": 10,
        "ats_threshold": 75.0,
        "force": True
    }
    res_trigger = client.post('/api/aicalls/trigger/', trigger_payload, format='json')
    print(f"POST /api/aicalls/trigger/ -> Status: {res_trigger.status_code}, Response Data: {res_trigger.data}")
    assert res_trigger.status_code in [200, 201]

    call_id = res_trigger.data['call_details']['id']

    # API 2: Get Call Details GET /api/aicalls/<id>/
    res_detail = client.get(f'/api/aicalls/{call_id}/')
    print(f"GET /api/aicalls/{call_id}/ -> Status: {res_detail.status_code}, Status text: {res_detail.data.get('status')}")
    assert res_detail.status_code == 200

    # API 3: List Employer Job Calls GET /api/employer/jobs/<job_id>/ai-calls/
    res_job_calls = client.get(f'/api/employer/jobs/{active_job.id}/ai-calls/')
    print(f"GET /api/employer/jobs/{active_job.id}/ai-calls/ -> Status: {res_job_calls.status_code}, Total records: {len(res_job_calls.data)}")
    assert res_job_calls.status_code == 200
    assert len(res_job_calls.data) >= 1

    # API 4: Cancel Call POST /api/aicalls/<id>/cancel/
    res_cancel = client.post(f'/api/aicalls/{call_to_retry.id}/cancel/', {"reason": "Recruiter modified calendar"}, format='json')
    print(f"POST /api/aicalls/{call_to_retry.id}/cancel/ -> Status: {res_cancel.status_code}, Message: {res_cancel.data.get('message')}")
    assert res_cancel.status_code == 200

    # API 5: Retry Call POST /api/aicalls/<id>/retry/
    res_retry = client.post(f'/api/aicalls/{call_to_retry.id}/retry/', {"delay_minutes": 5}, format='json')
    print(f"POST /api/aicalls/{call_to_retry.id}/retry/ -> Status: {res_retry.status_code}, Call Status: {res_retry.data.get('call_details', {}).get('status')}")
    assert res_retry.status_code == 200
    assert res_retry.data['call_details']['status'] == 'queued'

    print("\n==================================================")
    print("  REAL-WORLD DAY 33 ENGINE VERIFICATION COMPLETE! ")
    print("==================================================")

if __name__ == '__main__':
    run_day33_tests()
