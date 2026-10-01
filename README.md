# 🚀 Zecpath AI Recruitment Platform & Automated Hiring Assistant

[![Python Version](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-6.0-green.svg)](https://www.djangoproject.com/)
[![DRF](https://img.shields.io/badge/DRF-3.15-red.svg)](https://www.django-rest-framework.org/)
[![Celery](https://img.shields.io/badge/Celery-5.3-brightgreen.svg)](https://docs.celeryq.dev/)
[![Redis](https://img.shields.io/badge/Redis-Cache%20%26%20Broker-red.svg)](https://redis.io/)
[![Google Gemini](https://img.shields.io/badge/AI-Google%20Gemini%202.5-orange.svg)](https://ai.google.dev/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

An enterprise-grade, asynchronous AI-powered recruitment backend and Applicant Tracking System (ATS). **Zecpath** streamlines the entire hiring pipeline: from direct cloud resume uploads and semantic ATS matching to automated voice AI interviews, interview slot scheduling, SaaS monetization, and executive recruiter analytics.

---

## 📌 Table of Contents
- [System Architecture](#-system-architecture)
- [Key Features & Capabilities](#-key-features--capabilities)
- [End-to-End Workflow](#-end-to-end-workflow)
- [Technology Stack](#-technology-stack)
- [Project Directory Structure](#-project-directory-structure)
- [API Reference & Key Endpoints](#-api-reference--key-endpoints)
- [Environment Variables](#-environment-variables)
- [Local Installation & Setup](#-local-installation--setup)
- [Background Workers & Celery Tasks](#-background-workers--celery-tasks)
- [Security & Compliance](#-security--compliance)

---

## 🏛 System Architecture

```
                        ┌──────────────────────────────────────────────┐
                        │      Client Applications / Web / Postman     │
                        └──────────────────────┬───────────────────────┘
                                               │ HTTPS / Bearer JWT
                                               ▼
                        ┌──────────────────────────────────────────────┐
                        │       Nginx Reverse Proxy & Static CDN       │
                        └──────────────────────┬───────────────────────┘
                                               │
                                               ▼
                        ┌──────────────────────────────────────────────┐
                        │     Gunicorn WSGI / Django REST Framework    │
                        └──────┬──────────────────────┬──────────────┬─┘
                               │                      │              │
         ┌─────────────────────┘                      │              └─────────────────────┐
         ▼                                            ▼                                    ▼
┌─────────────────────────┐              ┌─────────────────────────┐          ┌─────────────────────────┐
│     Core Services       │              │    AI Voice & NLP       │          │   Billing & Gateways    │
│  - User Auth & RBAC     │              │  - Real-time Audio STT  │          │  - Stripe / Razorpay    │
│  - Job Postings & Feed  │              │  - ATS Keyword Matcher  │          │  - Tier Feature Gating  │
│  - Application Pipeline │              │  - Gemini Evaluation    │          │  - Invoicing & Refunds  │
└────────────┬────────────┘              └────────────┬────────────┘          └────────────┬────────────┘
             │                                        │                                    │
             └─────────────────────────┬──────────────┴────────────────────────────────────┘
                                       │
                      ┌────────────────┴────────────────┐
                      ▼                                 ▼
         ┌─────────────────────────┐       ┌─────────────────────────┐
         │   PostgreSQL Database   │       │   Redis Broker & Cache  │
         │  (Indexes, Audit Trail) │       │ (Celery Queue, Throttles│
         └─────────────────────────┘       └────────────┬────────────┘
                                                        │
                                                        ▼
                                           ┌─────────────────────────┐
                                           │   Celery Worker Pool    │
                                           │  - Async Resume Parsing │
                                           │  - ATS Score Processor  │
                                           │  - Hourly/Daily Crons   │
                                           └─────────────────────────┘
```

---

## 🌟 Key Features & Capabilities

### 1. 📄 Automated Resume Parsing & NLP Extraction
* Extracts raw text from candidate `.pdf` and `.docx` files.
* Uses NLP algorithms to structure unstructured text into candidate skills, experience years, and target roles.

### 2. 🎯 ATS Scoring & Automated Screening
* Computes cosine similarity and keyword alignment between candidate resumes and job requisitions.
* Automatically tags applications as `shortlisted` or `rejected` based on configured suitability thresholds.

### 3. 🎙️ AI Voice Screening & Answer Evaluation
* Simulates automated phone/audio interviews with real-time Speech-to-Text (STT) and Text-to-Speech (TTS).
* Integrates with **Google Gemini (`gemini-2.5-flash`)** to evaluate candidate answers for technical depth, communication clarity, and accuracy.

### 4. 📅 Smart Interview Scheduling & Cron Reminders
* Candidate availability slot reservation and self-service rescheduling.
* Celery Beat background scheduler scans pending interviews and dispatches multi-channel email reminders.

### 5. 📊 Recruiter Analytics & Executive Reports
* Conversion funnel metrics (Applied $\rightarrow$ Shortlisted $\rightarrow$ Screened $\rightarrow$ Hired).
* Automated PDF summary report generation comparing multi-candidate rankings.

### 6. 💳 SaaS Monetization & Feature Gating
* Multi-tiered subscription models (Starter, Professional, Enterprise) gating premium candidate pools and high-volume AI calls.
* Full webhook handling and payment verification for **Stripe** and **Razorpay**.

### 7. 🛡️ Enterprise Security & Rate Limiting
* Hardened JWT lifecycle with 15-minute access expiration, automatic refresh rotation, and Redis token blacklisting.
* Role-Based Access Control (RBAC: Candidate, Recruiter, Admin).
* AES Fernet encryption for sensitive PII data and audit trails for compliance.

---

## 🔄 End-to-End Workflow

```
[1. Employer Posts Job] ──> [2. Candidate Uploads Resume] ──> [3. Celery Async NLP & ATS Match]
                                                                          │
                                    ┌─────────────────────────────────────┴─────────────────────────────────────┐
                                    ▼ (ATS Score >= Threshold)                                                  ▼ (ATS Score < Threshold)
                         [4. Auto-Shortlist Application]                                              [Auto-Rejection + Email]
                                    │
                                    ▼
                         [5. Trigger AI Voice Interview]
                                    │
                                    ▼
                         [6. Gemini LLM Answer Evaluation]
                                    │
                                    ▼
                         [7. Book Recruiter Interview Slot]
                                    │
                                    ▼
                         [8. Recruiter Dashboard & Final PDF Report]
```

1. **Requisition**: Recruiter posts a job vacancy specifying required skills, experience, and salary brackets.
2. **Application**: Candidate uploads their resume (via direct S3 pre-signed URL) and applies for the position.
3. **Async Screening**: A background Celery worker extracts the resume text, generates embeddings, computes the ATS match score, and updates candidate status.
4. **Voice Interview**: Candidates qualifying the ATS score receive an AI voice call screening with automated technical questions.
5. **AI Scoring**: Audio responses are transcribed and evaluated by Gemini for scoring.
6. **Final Selection**: Recruiter reviews composite ranking reports and schedules the final hiring round.

---

## 💻 Technology Stack

| Component | Technology / Library |
| :--- | :--- |
| **Backend Framework** | Python 3.12+, Django 6.0, Django REST Framework (DRF) |
| **Database** | PostgreSQL (Production) / SQLite3 (Development) |
| **Task Queue & Caching** | Celery 5.3+, Redis 7.x, Celery Beat |
| **AI / LLM Engine** | Google Gemini API (`gemini-2.5-flash`), Cosine Similarity ATS Matcher |
| **Audio & NLP** | PyPDF, python-docx, Fast-Whisper / WebRTC Audio Bridge |
| **Payment Gateways** | Stripe API, Razorpay SDK |
| **Cloud & Storage** | AWS S3 (Resumes & Media), CloudFront CDN |
| **Authentication & Security** | SimpleJWT (Rotation & Blacklist), Fernet AES Encryption |
| **API Documentation** | OpenAPI 3.0 / DRF Spectacular (Swagger UI & Redoc) |

---

## 📁 Project Directory Structure

```text
zecpath-ai-job-portal/
├── core/                           # Primary Application Engine
│   ├── models.py                   # 20+ Models: User, Job, Application, AICall, Subscription, etc.
│   ├── views.py                    # API Views for Auth, Jobs, Voice AI, Billing, Analytics
│   ├── serializers.py              # DRF Model & Validation Serializers
│   ├── tasks.py                    # Celery Async Tasks & Beat Crons
│   ├── urls.py                     # All REST API Endpoint Definitions
│   ├── permissions.py              # Custom RBAC Permission Classes
│   ├── middleware.py               # Subscription & Security Middlewares
│   ├── services/                   # Business Services (Billing, Recommendations)
│   └── utils/                      # Core Engines (ATS, Voice Bridge, NLP, Encryption)
├── zecpath_backend/                # Project Settings & Root Routing
│   ├── settings.py                 # Django, JWT, Celery, Cache & Throttle Settings
│   ├── celery.py                   # Celery Instance Configuration
│   ├── urls.py                     # Root URL Router & Swagger Docs
│   └── wsgi.py                     # WSGI Application Handler
├── docs/                           # Architectural & Deployment Documentation
├── scripts/                        # Maintenance & Operational Scripts
├── manage.py                       # Django CLI Manager
├── requirements.txt                # Python Dependencies
└── HANDOVER.md                     # Deployment & Maintenance Runbook
```

---

## 🔌 API Reference & Key Endpoints

### 🔐 Authentication & Profiles
* `POST /api/auth/signup/` — Candidate & Recruiter registration.
* `POST /api/auth/login/` — Issue JWT token pair (`access` + `refresh`).
* `POST /api/auth/logout/` — Invalidate token & add to Redis blacklist.
* `GET/PUT /api/profile/candidate/` — Manage candidate details & skills.

### 💼 Jobs & Applications
* `GET /api/jobs/public/` — Browse public job listings.
* `POST /api/employer/jobs/create/` — Publish new job requisition.
* `POST /api/jobs/apply/` — Submit application with resume.
* `GET /api/candidate/dashboard/applied-jobs/` — Track submitted applications.

### 🤖 AI Screening & ATS
* `POST /api/candidate/resume/parse-async/` — Trigger background NLP resume parser.
* `POST /api/employer/jobs/<id>/async-auto-screen/` — Trigger batch ATS screening on applicants.
* `POST /api/voice/trigger-call/` — Launch automated AI voice interview session.
* `POST /api/testing/ai-questions/<id>/evaluate/` — Score candidate answer using Gemini AI.

### 🗓️ Scheduling & Reminders
* `GET /api/scheduling/slots/available/` — List open interview slots.
* `POST /api/scheduling/book/` — Book an interview slot.
* `POST /api/scheduling/<id>/reschedule/` — Change interview time.

### 💳 SaaS Monetization & Gateways
* `GET /api/billing/plans/` — List subscription plans.
* `POST /api/billing/subscribe/` — Subscribe/Upgrade user plan.
* `POST /api/payments/create-order/` — Initialize Stripe/Razorpay payment order.
* `POST /api/payments/webhook/` — Handle gateway payment webhooks.

### 📈 Recruiter Analytics & Executive Reports
* `GET /api/recruiter/analytics/funnel/` — View application conversion funnel.
* `GET /api/recruiter/premium/jobs/<id>/ranking-report/` — Ranked candidate composite report.
* `GET /api/recruiter/applications/<id>/report-summary/` — Download full candidate scorecard.

---

## ⚙️ Environment Variables

Create a `.env` file in the root directory and configure the required environment variables:

```ini
# Django Core
SECRET_KEY=your-production-secret-key
DEBUG=False
ALLOWED_HOSTS=127.0.0.1,localhost,api.zecpath.com

# Database (PostgreSQL)
DB_ENGINE=django.db.backends.postgresql
DB_NAME=zecpath_db
DB_USER=zecpath_user
DB_PASSWORD=your_secure_password
DB_HOST=localhost
DB_PORT=5432

# Redis (Caching & Celery Broker)
REDIS_URL=redis://127.0.0.1:6379/0

# AI / Google Gemini
GEMINI_API_KEY=your_gemini_api_key

# Payment Gateways
STRIPE_PUBLIC_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
RAZORPAY_KEY_ID=rzp_test_...
RAZORPAY_KEY_SECRET=your_razorpay_secret

# Security & Cloud Storage
FERNET_ENCRYPTION_KEY=your_base64_fernet_key
AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret
AWS_STORAGE_BUCKET_NAME=zecpath-resumes
AWS_S3_REGION_NAME=us-east-1
```

---

## 🚀 Local Installation & Setup

### 1. Clone & Setup Virtual Environment
```bash
git clone https://github.com/its-rajkumarpadmanabhan/Zecpath-AI-Job-Portal-Automated-Hiring-Assistant.git
cd Zecpath-AI-Job-Portal-Automated-Hiring-Assistant

python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Apply Migrations & Static Files
```bash
python manage.py migrate
python manage.py collectstatic --noinput
```

### 4. Run Development Server
```bash
python manage.py runserver
```

Explore the interactive Swagger UI at: **`http://localhost:8000/api/docs/swagger/`**

---

## ⏱️ Background Workers & Celery Tasks

Start Celery workers to handle async processing (resume parsing, ATS scoring, emails):

```bash
# Terminal 1: Celery Worker
celery -A zecpath_backend worker -l info --pool=threads

# Terminal 2: Celery Beat (Periodic Cron Scheduler)
celery -A zecpath_backend beat -l info
```

---

## 🔒 Security & Compliance

* **Token Revocation**: Refresh tokens are revoked and blacklisted upon rotation or logout.
* **Rate Limits**: Protects against credential stuffing (`auth_strict: 5/min`) and AI abuse (`ai_abuse: 5/min`).
* **Encrypted Storage**: Sensitive candidate contact information is stored with Fernet symmetric encryption.
* **Audit Trail**: Every significant administrative, application, and security status change is logged to `SystemAuditTrail` and `SecurityFailureLog`.

---

## 📄 License

This project is licensed under the **MIT License**.
