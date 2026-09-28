# Professional Portfolio & Technical Resume Highlights

## Technical Summary
**Backend Engineer | Python, Django, DRF, Celery, PostgreSQL, AWS, Docker**

## Project Showcase: Zecpath AI Automated Recruitment SaaS
- Architected and deployed an automated recruitment platform backend handling resume parsing, AI voice interview evaluations, and SaaS subscription billing.
- Designed an asynchronous ATS pipeline using Celery and Redis, reducing candidate profile processing time from 12s to 1.8s.
- Built a real-time voice interview evaluation pipeline with WebSockets and LLMs, scoring candidates across communication clarity, technical accuracy, and role fit.
- Implemented multi-tier SaaS billing with Stripe and Razorpay, including HMAC SHA256 webhook signature verification and zero-downtime subscription state transitions.
- Optimized PostgreSQL queries via composite B-tree indices (`idx_app_job_status`, `idx_job_employer_status`), reducing candidate ranking endpoint latency by 95%.
- Established CI/CD deployment pipelines using GitHub Actions, Gunicorn systemd daemons, Nginx reverse proxies, and AWS S3 private document vaults.
