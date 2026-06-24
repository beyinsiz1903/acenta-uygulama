---
name: Idempotent write retry safety
description: When it is safe to auto-retry a failed outbound HTTP request to an external system.
---

# Auto-retry only when the operation is idempotent

A transient failure that happens AFTER a request is sent — read timeout, network
error mid-flight, or a 5xx — is **ambiguous**: the write may or may not have been
applied. Replaying it can double-apply.

**Rule:** auto-retry such ambiguous failures ONLY when the request is idempotent:
- a `GET`, or
- a write carrying a stable `Idempotency-Key` the server dedups on.

For any keyless `POST/PUT/PATCH/DELETE`, **fail closed** — raise immediately
instead of retrying.

**Why:** the original architect review flagged a keyless write being retried as a
HIGH double-apply risk. Folio charge / webhook register / cancel / delete had no
idempotency key, so a blind retry could apply them twice.

**How to apply:**
- Compute `retry_safe = (method == "GET") or bool(idempotency_key)` and gate the
  timeout/network/5xx retry branches on it.
- `429` is the exception — it means rejected (rate limit) or in-flight
  (idempotent dedupe), i.e. NOT applied — so honour `Retry-After` and retry the
  SAME request regardless of method.
- Permanent business statuses `{400,401,402,403,404,409,422}` never retry (a
  retry just replays the same error).
- For `POST /reservations`, resolve a STABLE key: caller-supplied valid UUID wins;
  else map a `client_request_id` to a persisted key; else generate + echo it back.
  Reject a caller-supplied key that is not a valid UUID with 422 (don't silently
  replace it — that breaks the caller's retry determinism).
