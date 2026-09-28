# Production Debugging Report & Resolution Postmortem

## Issue 1: High Latency on Recruiter Candidate Rankings API
- **Symptom**: `GET /api/recruiter/premium/jobs/<id>/ranking-report/` latency degraded to 4,200 ms with 50+ candidates.
- **Root Cause**: N+1 query problem. Iterating through applications caused individual child queries for `AIInterviewSession` and `candidate` user profiles.
- **Fix**: Replaced dynamic loops with `.select_related('candidate', 'job')` and `.prefetch_related('ai_interview_sessions')`. Enforced database-level B-tree index `idx_app_job_status`.
- **Result**: Query execution time dropped from 4,200 ms to 18 ms.

## Issue 2: Memory Leak in Resume PDF Parser
- **Symptom**: Celery workers consumed 100% host RAM and restarted with OOM (Out Of Memory) errors after processing large PDF files.
- **Root Cause**: `pdfminer` stream handlers maintained unclosed file descriptors and retained parsed image streams in global heap buffers.
- **Fix**: Wrapped stream readers in context managers, forced garbage collection passes after every 50 document extractions, and set Celery `--max-tasks-per-child=100`.
