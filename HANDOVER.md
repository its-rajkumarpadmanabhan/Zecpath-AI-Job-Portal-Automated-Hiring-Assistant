# Zecpath AI Recruitment Platform — Project Handover Document

## 1. System Architecture Overview

```
                        ┌──────────────────────────────────────────────┐
                        │      Client Applications / Postman / Web     │
                        └──────────────────────┬───────────────────────┘
                                               │ HTTPS / Bearer JWT
                                               ▼
                        ┌──────────────────────────────────────────────┐
                        │       Nginx Reverse Proxy & Static CDN       │
                        └──────────────────────┬───────────────────────┘
                                               │ Unix Socket
                                               ▼
                        ┌──────────────────────────────────────────────┐
                        │         Gunicorn WSGI Application Cluster    │
                        └──────────────────────┬───────────────────────┘
                                               │
     ┌─────────────────────────────────────────┼────────────────────────────────────────┐
     ▼                                         ▼                                        ▼
┌─────────────────────────┐       ┌─────────────────────────┐       ┌─────────────────────────┐
│     Core Services       │       │    AI Voice & NLP       │       │   Billing & Gateways    │
│  - User Auth & RBAC     │       │  - Real-time Audio STT  │       │  - Stripe / Razorpay    │
│  - Job Postings         │       │  - ATS Keyword Matcher  │       │  - Tier Feature Gating  │
│  - Application Funnel   │       │  - Composite AI Scoring │       │  - Automated Refunds    │
└────────────┬────────────┘       └────────────┬────────────┘       └────────────┬────────────┘
             │                                 │                                 │
             └─────────────────────────────────┼─────────────────────────────────┘
                                               │
                                               ▼
                        ┌──────────────────────────────────────────────┐
                        │         PostgreSQL Database Cluster          │
                        │   (Composite Indexes, Read/Write Caching)    │
                        └──────────────────────────────────────────────┘
```

## 2. System Inventory & Repositories
* **Repository:** `zecpath-ai-job-portal-automated-hiring-assistant`
* **Runtime Framework:** Python 3.12+ / Django 5.x–6.x / Django REST Framework
* **Production Stack:** Gunicorn (WSGI), Nginx (Reverse Proxy), PostgreSQL, Redis, AWS S3 / CloudFront CDN

## 3. Environment Secrets Required
Ensure the following variables are defined in `.env`:
* `SECRET_KEY`, `DEBUG=False`, `ALLOWED_HOSTS`
* `DATABASE_URL` (PostgreSQL connection string) / `DB_ENGINE`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`
* `REDIS_URL` (Redis cache & Celery broker)
* `STRIPE_PUBLIC_KEY`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`
* `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`
* `FERNET_ENCRYPTION_KEY`
* `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_STORAGE_BUCKET_NAME`, `AWS_S3_REGION_NAME`, `CLOUDFRONT_DOMAIN`

## 4. Live Demo Execution & Core Workflow Runbook

### A. Employer Workflow
1. **Authentication**: Submit credentials to `POST /api/auth/login/` to receive JWT token pair.
2. **Subscription Activation**: Confirm active subscription with `GET /api/billing/validate-access/` or subscribe via `POST /api/billing/subscribe/`.
3. **Requisition Deployment**: Submit `POST /api/jobs/` with job parameters (required skills, experience, and salary boundaries).

### B. Candidate Application & AI Interview Workflow
1. **Apply to Opening**: Submit an application via `POST /api/applications/` alongside resume document or upload via direct pre-signed URL `POST /api/storage/resumes/presigned-upload/`.
2. **AI Screening Session**: Connect to `POST /api/voice/trigger-call/` to initiate speech evaluation and automated questioning.
3. **Automated Evaluation**: Candidate audio responses are processed and assigned an AI composite match score (`POST /api/testing/ai-questions/<id>/evaluate/`).

### C. Recruiter Monetization & Decision Dashboard
1. **Executive Ranking Report**: Access `GET /api/recruiter/premium/jobs/<id>/ranking-report/` to view weighted ATS + AI interview rankings and predicted candidate success categories.
2. **Platform Financial Metrics**: Platform admin reviews aggregate platform performance via `GET /api/admin/finance/dashboard/`.

## 5. Operations & Maintenance Cheatsheet
* **Start/Restart Web Daemon:** `sudo systemctl restart gunicorn`
* **Reload Reverse Proxy:** `sudo systemctl reload nginx`
* **Execute Pending Migrations:** `python manage.py migrate --noinput`
* **Collect Static Assets:** `python manage.py collectstatic --noinput`
* **Inspect Live Production Logs:** `journalctl -u gunicorn -f -n 100`

## 6. Documentation References
* **Interactive Swagger UI:** `http://<HOST>/api/docs/swagger/`
* **Redoc Reference:** `http://<HOST>/api/docs/redoc/`
* **OpenAPI Raw Schema:** `http://<HOST>/api/schema/`
* **QA Signoff Health Check:** `GET /api/qa/final-signoff/`
