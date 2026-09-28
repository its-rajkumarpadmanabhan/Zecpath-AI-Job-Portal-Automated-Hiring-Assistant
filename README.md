# Zecpath AI Recruitment Platform (Backend Engine)

Production-grade, asynchronous AI recruitment platform built with Django REST Framework, Celery, PostgreSQL, and AWS S3.

## Core Capabilities
- **Automated Resume Parsing**: Text extraction and ATS cosine similarity matching.
- **Voice AI Interviewing**: Real-time evaluation pipeline scoring candidate technical skills.
- **SaaS Monetization**: Multi-tier subscription models with Stripe/Razorpay webhook automation.
- **Hardened Security**: Short-lived JWTs (15 min) with token rotation, Redis blacklisting, and role-based permissions.

## Documentation & API Exploration
- **Interactive Swagger UI**: `http://localhost:8000/api/docs/swagger/`
- **Redoc Interface**: `http://localhost:8000/api/docs/redoc/`
