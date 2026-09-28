# Zecpath AI Platform: Comprehensive Architecture & Flow Specifications

## 1. System Topology Overview
- **Edge Routing / DNS**: Cloudflare / AWS Route 53 with SSL termination.
- **Reverse Proxy**: Nginx 1.24 handling `/static/`, `/media/` (or proxying to S3 pre-signed redirects), and forwarding `/api/` to Gunicorn Unix sockets.
- **Application Server**: Django 5.x / DRF with SimpleJWT, Celery 5.x, Gunicorn (3 workers, Gevent/sync mode).
- **Persistence & Caching**: PostgreSQL 16 with composite B-tree indices and connection reuse (`CONN_MAX_AGE=600`), Redis 7 for Celery brokerage and 5-minute DRF view caching.
- **External Interfaces**: AWS S3 (private buckets), Twilio Voice / WebSockets, OpenAI / Whisper APIs, Stripe / Razorpay Webhooks.

## 2. End-to-End Operational Workflows
### A. Candidate Acquisition & Automated Screening
1. Candidate creates profile via `POST /api/auth/signup/` (role: `candidate`).
2. Candidate uploads resume to `POST /api/storage/resumes/presigned-upload/`.
3. S3 triggers an asynchronous Celery task:
   - Text parsing via Apache Tika/pdfplumber.
   - Skill extraction and cosine similarity ATS matching against job requirements.
4. ATS score stored in `core_application.match_score`.

### B. AI Voice Interview Pipeline
1. Candidate triggers session at `POST /api/voice/trigger-call/`.
2. Backend establishes audio session with Twilio/WebSockets.
3. Transcribed answers sent to LLM evaluation service.
4. Composite score calculated: ATS Match (50%) + AI Screening (50%).

### C. SaaS Monetization & Webhooks
1. Recruiter orders plan via `POST /api/payments/create-order/`.
2. Signature verified through `POST /api/payments/verify/` using HMAC SHA256.
3. Asynchronous webhook listener updates `UserSubscription` to `active` within a `transaction.atomic()` block.
