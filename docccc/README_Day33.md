# Day 33 – AI Call Trigger & Eligibility Engine

## Objective
To automate **who gets AI calls and when** using configurable business rules, calling time-window validation, retry policies, Celery task scheduling, and REST API status tracking endpoints.

---

## Tasks & Scope Implemented

### 1. Eligibility Rules Engine (`core/utils/ai_call_engine.py`)
- **ATS Score Threshold Validation**: Enforces candidate ATS score threshold (default: $\ge 75.0\%$).
- **Job Status Validation**: Enforces that job status must be `'active'`.
- **Candidate Availability Validation**: Verifies candidate user `is_active=True` and profile `is_deleted=False`.
- Diagnostic reason reporting returning `(is_eligible, reason)`.

### 2. Trigger Logic & Calling Hours Scheduling
- **Time-Window Validation (`09:00 - 18:00`)**: Enforces permitted candidate calling hours (`9:00 AM` to `6:00 PM`).
- **Automatic Schedule Shift**: Calls triggered outside calling hours automatically shift forward to `09:00 AM` of the current day (if before 9 AM) or `09:00 AM` next morning (if after 6 PM).
- **Event-Based Auto-Triggers**: Automated trigger on application auto-shortlist status transition.

### 3. Scheduler Integration & Retry Policies (`core/tasks.py`)
- **Retry Policies**: Max retry count enforcement (`MAX_RETRY_COUNT = 3`), retry count incrementing, and failure note logging.
- **Celery Task Execution**: `execute_ai_call_task` updates timestamps (`completed_at`, `updated_at`) and handles state transitions.
- **State Machine Transitions**: `queued` $\rightarrow$ `in_progress` $\rightarrow$ `completed` / `failed` / `cancelled`.

### 4. Status Tracking & REST API Endpoints
- `POST /api/aicalls/trigger/`: Manually or programmatically trigger an AI screening call.
- `GET /api/aicalls/<id>/`: Retrieve detailed status and tracking metrics of a specific call.
- `GET /api/aicalls/`: List AI calls with role-based filtering and status query params (`?status=queued`, `?job_id=X`).
- `GET /api/employer/jobs/<job_id>/ai-calls/`: Employer dashboard view of screening calls for a specific job post.
- `POST /api/aicalls/<id>/retry/`: Re-queue a failed or cancelled call.
- `POST /api/aicalls/<id>/cancel/`: Cancel a queued call with reason notes.

---

## Key Verification Highlights

1. **Automatic Execution & Completion**:
   - Status updated from `"queued"` $\rightarrow$ `"completed"`.
   - Completion timestamp set: `completed_at: "2026-08-18T12:44:29Z"`.

2. **State Protection Rules**:
   - Attempting to cancel a completed call correctly returns: `"error": "Cannot cancel a completed call"`.
   - Prevents accidental cancellation of already finished candidate calls.

---

## Summary of Day 33 Complete Verification

| Requirement | Test Result |
| :--- | :--- |
| **1. Eligibility Rules Engine** | ✅ Validated (ATS Score 88.5% $\ge$ 75%, Job active, Candidate active) |
| **2. Time-Window & Scheduling** | ✅ Validated (Scheduled within 09:00 - 18:00 window) |
| **3. Execution & Status Tracking** | ✅ Validated (`GET /api/aicalls/18/` returned `completed` status) |
| **4. State Protection & Retry Rules** | ✅ Validated (`cancel` endpoint blocked cancellation on finished call) |

---

## How to Test Day 33

### Run Real-World Data Seeding:
```bash
python manage.py seed_real_world_data
```

### Run Day 33 Verification Suite:
```bash
python test_day33.py
```

### Run Core Unit Tests:
```bash
python manage.py test core
```
