# Day 32 – Background Jobs & Async Processing (Celery + Redis)

## 📌 Overview & Learning Objective
In high-throughput recruitment platforms like **Zecpath**, performing heavy computational tasks—such as AI model inference, ATS score matching, PDF resume parsing, or sending external emails—directly inside synchronous HTTP request handlers can cause request timeouts, slow response times, and poor user experience.

**Day 32** introduces asynchronous background task processing to the Zecpath backend architecture using **Celery** as the distributed task worker framework and **Redis** as the in-memory message broker.

---

## 1. Async Processing Concepts

### 1.1 Why Background Jobs Are Needed
When a candidate uploads a resume or applies for a job, the backend performs multiple operations:
1. Extracting text from binary files (PDF/DOCX).
2. NLP string tokenization and JSON parsing.
3. Calculating composite ATS match algorithms against job requirements.
4. Dispatching HTML/text notification emails to candidates and recruiters.

If executed **synchronously**:
* The HTTP response is blocked until all operations complete ($2-5+$ seconds).
* Heavy traffic spikes exhaust Django server worker threads, leading to HTTP 504 Gateway Timeouts.

With **background job queues**:
* Django immediately returns a fast response (e.g., `202 Accepted` with a `task_id`) in under $50\text{ms}$.
* Heavy tasks are pushed to a Redis queue and executed asynchronously by dedicated background worker processes.

### 1.2 Synchronous vs. Asynchronous Task Execution

```
SYNCHRONOUS FLOW (Blocking):
Client ---> HTTP POST ---> Django Request Handler ---> [ Parse Resume (3s) + Send Email (2s) ] ---> HTTP 200 OK (5s total delay)

ASYNCHRONOUS FLOW (Non-blocking with Celery + Redis):
Client ---> HTTP POST ---> Django Request Handler ---> Enqueue Task to Redis ---> HTTP 202 Accepted (20ms delay)
                                                              |
                                                              v
                                                    [ Celery Worker Pool ]
                                                    - Parses Resume
                                                    - Computes ATS Score
                                                    - Delivers Notification Email
```

| Dimension | Synchronous Tasks | Asynchronous Tasks (Celery) |
| :--- | :--- | :--- |
| **Execution Context** | Main web request thread | Independent background worker process |
| **User Latency** | User waits for task completion | Instant response; background processing |
| **Error Isolation** | Unhandled task error crashes HTTP request | Task retries automatically; user request succeeds |
| **Scalability** | Limited by web worker capacity | Horizontally scalable by spinning up more Celery nodes |

---

## 2. Celery + Redis Architecture & Setup

### 2.1 Installed Dependencies
* `celery >= 5.3.0`: Task queue manager and worker engine.
* `redis >= 5.0.0`: In-memory data store acting as Celery Broker & Result Backend.

### 2.2 Project Structure Integrations
* [celery.py](file:///c:/Users/Rajkumar/Desktop/Zecpath-AI-Job-Portal-Automated-Hiring-Assistant/zecpath_backend/celery.py): Instantiates Celery app instance `zecpath_backend` and autodiscovers tasks across installed Django apps.
* [__init__.py](file:///c:/Users/Rajkumar/Desktop/Zecpath-AI-Job-Portal-Automated-Hiring-Assistant/zecpath_backend/__init__.py): Exposes `celery_app` when Django initializes.
* [settings.py](file:///c:/Users/Rajkumar/Desktop/Zecpath-AI-Job-Portal-Automated-Hiring-Assistant/zecpath_backend/settings.py): Defines Redis connections and Beat schedules.

```python
# Celery Broker & Result Store Settings
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'
```

---

## 3. Implemented Task Queues (`core/tasks.py`)

All task queues are implemented in [tasks.py](file:///c:/Users/Rajkumar/Desktop/Zecpath-AI-Job-Portal-Automated-Hiring-Assistant/core/tasks.py):

### 3.1 Task Queue 1: Email Notification Delivery
* **Function**: `@shared_task` `send_async_application_status_email_task(application_id)`
* **Description**: Offloads status update email generation and SMTP delivery. Includes automatic retries (`max_retries=3`, delay `60s`).
* **Integration**: Invoked seamlessly via [notification_service.py](file:///c:/Users/Rajkumar/Desktop/Zecpath-AI-Job-Portal-Automated-Hiring-Assistant/core/utils/notification_service.py).

### 3.2 Task Queue 2: Resume Extraction & NLP Parsing
* **Function**: `@shared_task` `async_parse_resume_task(candidate_id)`
* **Description**: Parses PDF/DOCX files, performs NLP extraction of skills and experience, and persists structured data to candidate profiles asynchronously.
* **Endpoint**: `POST /api/candidate/resume/parse-async/` ([views.py](file:///c:/Users/Rajkumar/Desktop/Zecpath-AI-Job-Portal-Automated-Hiring-Assistant/core/views.py#L877)).

### 3.3 Task Queue 3: AI Model Call & ATS Score Calculation
* **Function**: `@shared_task` `async_compute_ats_score_task(application_id)`
* **Description**: Computes weighted ATS match scores (50% skills, 30% experience, 20% role relevance) and applies threshold rules (Shortlist $\ge 70\%$, Reject $< 40\%$).
* **Endpoint**: `POST /api/employer/jobs/<job_id>/async-auto-screen/` ([views.py](file:///c:/Users/Rajkumar/Desktop/Zecpath-AI-Job-Portal-Automated-Hiring-Assistant/core/views.py#L907)).

---

## 4. Cron Jobs & Scheduler Configuration (Celery Beat)

Periodic tasks (cron jobs) are managed by **Celery Beat**, which dispatches tasks to Celery workers according to specified schedules defined in [settings.py](file:///c:/Users/Rajkumar/Desktop/Zecpath-AI-Job-Portal-Automated-Hiring-Assistant/zecpath_backend/settings.py).

### 4.1 Configured Beat Schedule
```python
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    # Cron 1: Automatically screen pending job applications every hour
    'periodic-auto-screening-hourly': {
        'task': 'core.tasks.periodic_batch_auto_screening_task',
        'schedule': crontab(minute=0),
    },
    # Cron 2: Generate system metrics digest every midnight
    'periodic-analytics-digest-daily': {
        'task': 'core.tasks.periodic_system_analytics_digest_task',
        'schedule': crontab(hour=0, minute=0),
    },
}
```

---

## 5. Execution Guide & Deployment Commands

### Step 1: Start Redis Broker
```bash
redis-server
```

### Step 2: Launch Celery Worker Pool
```bash
# Windows / Linux environment
celery -A zecpath_backend worker --loglevel=info -P threads
```

### Step 3: Launch Celery Beat Scheduler (Periodic Tasks)
```bash
celery -A zecpath_backend beat --loglevel=info
```

### Step 4: Local Development Eager Mode (No Redis Required)
For local testing environments without Redis running, set `CELERY_TASK_ALWAYS_EAGER = True` in `.env` or `settings.py` to execute tasks synchronously within the main thread.

---

## 🎯 Deliverables & Summary Checklist
- [x] Celery configuration created (`zecpath_backend/celery.py`).
- [x] Redis message broker & result backend configured in `settings.py`.
- [x] Email, resume parsing, and ATS AI task queues implemented in `core/tasks.py`.
- [x] Hourly & daily Celery Beat cron schedules configured.
- [x] Async REST API endpoints exposed in `core/urls.py` & `core/views.py`.
- [x] Comprehensive documentation added in `docs/DAY32_ASYNC_CELERY_REDIS.md`.
