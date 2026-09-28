# Mock Technical Interview Evaluation & Scorecard

## 1. Technical Round (Django & Architecture)
- **Q1: How do you prevent race conditions during concurrent subscription checkout?**
  - *Answer*: Wrap the verification logic in `transaction.atomic()` and lock the `UserSubscription` row using `.select_for_update()`.
  - *Score*: 5/5
- **Q2: Why use Celery for resume extraction instead of standard Django view execution?**
  - *Answer*: PDF text extraction and NLP vectorization take 1–3 seconds per document. Running them synchronously blocks Gunicorn worker threads and causes HTTP 504 gateway timeouts. Celery delegates this to a Redis task queue, allowing the HTTP API to respond immediately with a tracking ID.
  - *Score*: 5/5

## 2. System Design Round (High-Scale ATS)
- Candidate demonstrated understanding of pre-signed S3 upload links, message broker task decoupling, read-replica database routing, and Redis caching.
- *Score*: 4.8/5

## 3. Overall Performance Rating: GRADE A (Production Ready)
- **Strengths**: Strong understanding of ORM internals, webhook security, and database indexing.
- **Next Steps**: Continue practicing distributed cache invalidation strategies.
