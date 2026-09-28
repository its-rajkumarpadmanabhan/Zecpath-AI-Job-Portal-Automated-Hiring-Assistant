# Senior Django & Backend Engineering Technical Reference

## 1. Django ORM Internals & Query Optimization
- **`select_related` vs `prefetch_related`**:
  - `select_related`: Performs SQL `INNER JOIN` / `LEFT OUTER JOIN` in a single query. Applicable to single-valued relationships (`ForeignKey`, `OneToOneField`).
  - `prefetch_related`: Performs multi-step queries (Parent query followed by `IN (ids)` lookup) and merges them in Python memory. Ideal for `ManyToManyField` and reverse foreign relations.
- **Solving the N+1 Problem**: Always evaluate querysets using `.select_related()` on related entity tables and `.only()` or `.defer()` to restrict column payload size.
- **Concurrency & Race Conditions**: Enforce `select_for_update()` inside `transaction.atomic()` blocks to acquire row-level locks (e.g., subscription upgrades, concurrent interview slot bookings).

## 2. Architectural Middleware vs Signals
- **Middleware**: Executes globally at the boundary of HTTP request/response handling. Preferred for authentication checks, global rate-limiting, and request correlation IDs.
- **Signals**: Asynchronous event dispatchers on model changes (`post_save`, `pre_delete`). Recommended for decoupling domain events, but must be kept light to avoid hidden cascade bugs.

## 3. JWT Security & Stateless Token Invalidation
- Standard stateless JWTs cannot be revoked prior to expiration.
- Production solution: Short access token TTLs (15 min) combined with rotating refresh tokens (7 days). Store blacklisted refresh token IDs in a Redis cache with TTL matching the remaining lifespan.
