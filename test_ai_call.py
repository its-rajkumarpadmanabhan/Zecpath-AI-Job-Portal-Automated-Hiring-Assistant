import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zecpath_backend.settings')
django.setup()

from django.conf import settings
settings.CELERY_TASK_ALWAYS_EAGER = True
settings.CELERY_TASK_STORE_EAGER_RESULT = True
settings.CELERY_RESULT_BACKEND = 'cache+memory://'

from core.models import User, Candidate, Employer, Job, Application, AICall
from core.utils.automation_engine import evaluate_and_apply_auto_action

def run_test():
    print("--- Starting AI Call Engine Test ---")
    
    # 1. Create a Recruiter/Employer
    recruiter, _ = User.objects.get_or_create(email="test_recruiter@example.com", defaults={"name": "Test Recruiter", "role": "recruiter", "is_active": True})
    employer, _ = Employer.objects.get_or_create(user=recruiter, defaults={"company_name": "Test Company"})
    
    # 2. Create an Active Job
    job, _ = Job.objects.get_or_create(
        title="Test Software Engineer",
        employer=recruiter,
        defaults={
            "company": "Test Company", 
            "description": "Test Description", 
            "skills_required": "Python", 
            "experience_required": "2 years",
            "status": "active"
        }
    )
    # Ensure job is active in case it was already created as inactive
    job.status = 'active'
    job.save()

    # 3. Create an Active Candidate
    user_cand, _ = User.objects.get_or_create(email="test_cand@example.com", defaults={"name": "Test Candidate", "role": "candidate", "is_active": True})
    user_cand.is_active = True
    user_cand.save()
    candidate, _ = Candidate.objects.get_or_create(user=user_cand, defaults={"is_deleted": False})
    candidate.is_deleted = False
    candidate.save()

    # 4. Create an Application with a high ATS Score
    app, created = Application.objects.get_or_create(
        candidate=user_cand,
        job=job,
        defaults={"status": "applied", "ats_score": 85.0}
    )
    if not created:
        app.status = 'applied'
        app.ats_score = 85.0
        # clear existing AICall to test properly
        AICall.objects.filter(application=app).delete()
        app.save()

    print(f"Created Application: {app} with score {app.ats_score}")

    # 5. Trigger the automation engine
    prev_status, new_status, action = evaluate_and_apply_auto_action(app)
    print(f"Action Taken: {action}")
    print(f"New Status: {new_status}")

    # 6. Verify AICall was created
    ai_calls = AICall.objects.filter(application=app)
    if ai_calls.exists():
        ai_call = ai_calls.first()
        print(f"SUCCESS: AI Call generated with status '{ai_call.status}', scheduled at {ai_call.scheduled_at}")
    else:
        print("FAILED: No AI Call was generated!")

if __name__ == '__main__':
    run_test()
