# Production Incident Postmortem & RCA

## Incident Identifier: INC-20260928-GATEWAY-DOWN
- **Severity**: P1 (Critical - SaaS Revenue Processing Failure)
- **Time to Detect**: 3 minutes | **Time to Mitigate**: 11 minutes
- **Impact**: 14 subscription checkout transactions failed; users were not upgraded upon card charge.

## Timeline of Events
- **14:02 UTC**: Third-party payment gateway changed webhook payload structure.
- **14:04 UTC**: Django webhook endpoint raised unhandled `KeyError` on `event['payload']['payment']['entity']`.
- **14:07 UTC**: Celery retry queues filled up; Nginx returned HTTP 502 to gateway delivery nodes.
- **14:10 UTC**: On-call engineer executed rollback to stable release and enabled fallback JSON parsing.
- **14:15 UTC**: Re-queued failed transactions via administrative replay endpoint.

## Remediation & Preventive Measures
1. All webhook listeners wrapped with defensive `.get()` methods and fallback schema validators.
2. Unhandled webhook exceptions trigger persistent `PaymentTransaction(status='failed')` records for manual audit rather than raising a 500 error.
3. Added dead-letter queues (DLQ) in Redis for failed Celery tasks.
