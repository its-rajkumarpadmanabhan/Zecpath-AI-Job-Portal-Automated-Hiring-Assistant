# Implementation Plan - Day 32: Background Jobs & Async Processing (Celery + Redis)

Implement asynchronous task execution using **Celery** and **Redis** for the Zecpath backend. This offloads heavy/latency-sensitive operations—such as email notifications, resume text parsing, AI ATS match scoring, and scheduled cron jobs—from the synchronous HTTP request-response lifecycle.

## User Review Required

> [!IMPORTANT]
> Celery uses **Redis** as its message broker (`redis://localhost:6379/0`). In development environments where Redis is not running locally, Celery tasks can run in eager mode (`CELERY_TASK_ALWAYS_EAGER = True`) or connect to a running Redis service via `CELERY_BROKER_URL`.

## Proposed Changes

### Requirements & Configuration

#### [MODIFY] [requirements.txt](file:///c:/Users/Rajkumar/Desktop/Zecpath-AI-Job-Portal-Automated-Hiring-Assistant/requirements.txt)
- Add `celery` and `redis` dependencies.

#### [NEW] [celery.py](file:///c:/Users/Rajkumar/Desktop/Zecpath-AI-Job-Portal-Automated-Hiring-Assistant/zecpath_backend/celery.py)
- Instantiate the Celery app `zecpath_backend`.
- Configure Celery to read settings from `django.conf:settings` with the `CELERY` namespace.
- Enable automatic task discovery across installed Django apps (`app.autodiscover_tasks()`).

#### [MODIFY] [__init__.py](file:///c:/Users/Rajkumar/Desktop/Zecpath-AI-Job-Portal-Automated-Hiring-Assistant/zecpath_backend/__init__.py)
- Import `celery_app` as `celery_app` so it loads on Django startup.

#### [MODIFY] [settings.py](file:///c:/Users/Rajkumar/Desktop/Zecpath-AI-Job-Portal-Automated-Hiring-Assistant/zecpath_backend/settings.py)
- Configure `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND` (default `redis://localhost:6379/0`).
- Configure Celery task options (`CELERY_ACCEPT_CONTENT`, `CELERY_TASK_SERIALIZER`, `CELERY_TIMEZONE`).
- Configure `CELERY_BEAT_SCHEDULE` for periodic cron jobs (e.g. hourly auto-screening and daily system analytics digests).

---

### Task Queues & Logic

#### [NEW] [tasks.py](file:///c:/Users/Rajkumar/Desktop/Zecpath-AI-Job-Portal-Automated-Hiring-Assistant/core/tasks.py)
- `@shared_task` **`send_async_application_status_email_task(application_id)`**: Offloads email notifications for application status updates.
- `@shared_task` **`async_parse_resume_task(candidate_id)`**: Offloads resume extraction (PDF/DOCX) and NLP JSON structuring.
- `@shared_task` **`async_compute_ats_score_task(application_id)`**: Offloads heavy ATS match calculation and auto-screening logic.
- `@shared_task` **`periodic_batch_auto_screening_task()`**: Cron task running hourly via Celery Beat to automatically screen pending job applications.
- `@shared_task` **`periodic_system_analytics_digest_task()`**: Cron task running daily to generate system performance metrics.

#### [MODIFY] [notification_service.py](file:///c:/Users/Rajkumar/Desktop/Zecpath-AI-Job-Portal-Automated-Hiring-Assistant/core/utils/notification_service.py)
- Update notification trigger to dispatch `send_async_application_status_email_task.delay(application.id)` instead of blocking the main HTTP request thread.

#### [MODIFY] [views.py](file:///c:/Users/Rajkumar/Desktop/Zecpath-AI-Job-Portal-Automated-Hiring-Assistant/core/views.py) & [urls.py](file:///c:/Users/Rajkumar/Desktop/Zecpath-AI-Job-Portal-Automated-Hiring-Assistant/core/urls.py)
- Add endpoints to trigger async resume parsing (`/api/candidate/resume/parse-async/`) and async batch screening (`/api/employer/jobs/<job_id>/async-auto-screen/`).

---

### Documentation & Learning Scope

#### [NEW] [DAY32_ASYNC_CELERY_REDIS.md](file:///c:/Users/Rajkumar/Desktop/Zecpath-AI-Job-Portal-Automated-Hiring-Assistant/docs/DAY32_ASYNC_CELERY_REDIS.md)
- Complete learning documentation detailing async processing concepts, Celery + Redis architecture, worker setup commands, task queue design, and cron beat configuration.
