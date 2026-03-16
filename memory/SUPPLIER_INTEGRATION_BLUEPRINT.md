# Syroce Supplier Integration Blueprint

## Overview

This document defines the standard architecture for integrating external travel suppliers
into the Syroce platform. Every supplier (hotel, flight, tour, transfer, activity, insurance)
follows this contract to ensure consistency, reliability, and production safety.

---

## 1. Adapter Contract

Every supplier is wrapped by an adapter that implements the canonical interface.
The platform never speaks supplier-native — all communication goes through normalized schemas.

### Architecture Layers

```
Frontend (Search UI)
    |
API Router (/api/inventory/*)
    |
Inventory Sync Engine (cache-first search)
    |
Supplier Orchestrator (fan-out, aggregation)
    |
Supplier Bridge (canonical contract → supplier-specific)
    |
Supplier HTTP Adapter (raw API calls with retry/backoff)
    |
External Supplier API (RateHawk, Paximum, TBO, WWTatil)
```

### Contract Interface (contracts/base.py)

| Method | Required | Description |
|--------|----------|-------------|
| `healthcheck(ctx)` | Optional | Lightweight probe (default: ok) |
| `search(ctx, request)` | Required | Search products → SearchResult |
| `check_availability(ctx, request)` | Optional | Real-time availability check |
| `get_pricing(ctx, request)` | Optional | Standalone pricing (if not in search) |
| `create_hold(ctx, request)` | Optional | Hold/reserve before confirm |
| `confirm_booking(ctx, request)` | Required | Confirm and pay |
| `cancel_booking(ctx, request)` | Optional | Cancel a confirmed booking |

---

## 2. Canonical Models (contracts/schemas.py)

All supplier data passes through these normalized models:

| Model | Purpose |
|-------|---------|
| `SupplierContext` | Request metadata: org_id, user_id, currency, timeout |
| `SearchRequest` | Unified search params (destination, dates, guests) |
| `SearchResult` | Aggregated results with supplier attribution |
| `HotelSearchItem` | Hotel-specific result fields |
| `AvailabilityResult` | Real-time avail check response |
| `PricingResult` | Price breakdown with supplier/sell prices |
| `ConfirmResult` | Booking confirmation with supplier ID |
| `CancelResult` | Cancellation status with penalty info |
| `UnifiedBookingRequest` | Full booking payload with travellers |
| `UnifiedBookingResponse` | Full booking response with pricing drift |

---

## 3. Retry Policy

### Exponential Backoff with Jitter

```
Module: app/suppliers/retry.py

base_delay = 1.0s
max_delay  = 30.0s
max_retries = 3
jitter     = +/- 25%

delay(attempt) = min(base_delay * 2^attempt + random_jitter, max_delay)
```

### Retry Decision Matrix

| Error Type | Retryable | Max Retries | Backoff |
|------------|-----------|-------------|---------|
| `SupplierTimeoutError` | Yes | 3 | Exponential |
| `SupplierUnavailableError` | Yes | 3 | Exponential |
| `SupplierRateLimitError` | Yes | 5 | Exponential + longer base |
| `SupplierAuthError` | No | 0 | N/A |
| `SupplierValidationError` | No | 0 | N/A |
| `SupplierBookingError` | No | 0 | N/A |
| HTTP 5xx | Yes | 3 | Exponential |
| HTTP 4xx (not 429) | No | 0 | N/A |
| HTTP 429 | Yes | 5 | Respect Retry-After header |
| Connection Error | Yes | 2 | Exponential |
| DNS/SSL Error | No | 0 | N/A |

---

## 4. Timeout Policy

### Per-Operation Timeout Matrix

| Operation | Default Timeout | Max Timeout | Notes |
|-----------|----------------|-------------|-------|
| `healthcheck` | 5s | 5s | Hard limit |
| `search` | 8s | 15s | Most critical for UX |
| `check_availability` | 5s | 10s | |
| `get_pricing` | 5s | 10s | |
| `create_hold` | 10s | 20s | |
| `confirm_booking` | 15s | 30s | Financial — never timeout too early |
| `cancel_booking` | 10s | 20s | |
| `credential_validation` | 10s | 15s | |
| `inventory_sync` | 60s per region | 120s | Background job |

### Per-Supplier Overrides

| Supplier | Search | Booking | Cancel | Notes |
|----------|--------|---------|--------|-------|
| RateHawk | 8s | 15s | 10s | Fast API |
| Paximum | 12s | 20s | 15s | Slower, XML-based |
| TBO | 10s | 15s | 10s | |
| WWTatil | 15s | 25s | 15s | Basket model = slower |

---

## 5. Rate Limiting

### Per-Supplier Limits

| Supplier | Requests/sec | Requests/min | Burst | Notes |
|----------|-------------|-------------|-------|-------|
| RateHawk | 10 | 300 | 20 | B2B standard |
| Paximum | 5 | 150 | 10 | Agency tier dependent |
| TBO | 8 | 240 | 15 | |
| WWTatil | 3 | 90 | 5 | Conservative |

### Implementation

- Token bucket algorithm per supplier
- Shared counter in Redis for multi-instance
- Graceful degradation: queue excess requests instead of failing
- 429 responses trigger automatic backoff

---

## 6. Error Classification

### Error Categories

| Category | Code | HTTP | Retryable | Action |
|----------|------|------|-----------|--------|
| Timeout | `supplier_timeout` | 504 | Yes | Retry → Failover |
| Unavailable | `supplier_unavailable` | 503 | Yes | Retry → Failover |
| Rate Limited | `supplier_rate_limited` | 429 | Yes | Backoff → Retry |
| Auth Failed | `supplier_auth_error` | 401 | No | Alert → Disable |
| Validation | `supplier_validation` | 422 | No | Log → Return error |
| Booking Error | `supplier_booking_error` | 409 | No | Log → Return error |
| Generic | `supplier_error` | 502 | Configurable | Depends on context |

### Error Flow

```
API Call Failed
    |
    v
Classify Error (retryable?)
    |
    +-- Retryable: attempt < max_retries?
    |       +-- Yes: wait(backoff) → retry
    |       +-- No: failover to next supplier
    |
    +-- Non-retryable: return error immediately
```

---

## 7. Observability Fields

Every supplier API call records:

```json
{
  "trace_id": "uuid",
  "supplier_code": "ratehawk",
  "operation": "search",
  "request_id": "ctx.request_id",
  "organization_id": "ctx.organization_id",
  "started_at": "ISO8601",
  "finished_at": "ISO8601",
  "duration_ms": 245,
  "status": "success|error|timeout",
  "http_status": 200,
  "error_code": null,
  "error_message": null,
  "retryable": false,
  "attempt": 1,
  "cached": false,
  "items_count": 15
}
```

Stored in: `supplier_health_events` collection

---

## 8. Sync Modes

| Mode | Description | Data Source | When |
|------|-------------|------------|------|
| `simulation` | Generated mock data | In-memory templates | No credentials configured |
| `sandbox` | Real API, test environment | Supplier sandbox API | Credentials configured, mode=sandbox |
| `production` | Real API, live data | Supplier production API | Credentials configured, mode=production |
| `disabled` | No sync allowed | N/A | SUPPLIER_SIMULATION_ALLOWED=false & no creds |

### Mode Detection Flow

```
Check supplier_credentials collection
    |
    +-- Credentials found + mode=sandbox → sandbox
    +-- Credentials found + mode=production → production
    +-- No credentials + SUPPLIER_SIMULATION_ALLOWED=true → simulation
    +-- No credentials + SUPPLIER_SIMULATION_ALLOWED=false → disabled
```

---

## 9. Booking Lifecycle

### Full E2E Flow

```
1. SEARCH         → Cached inventory search (Redis/Mongo)
2. DETAIL          → Hotel/product detail from cache
3. REVALIDATION    → Real-time price check with supplier API
4. HOLD (optional) → Reserve the product
5. CONFIRM         → Create booking and charge
6. STATUS CHECK    → Verify confirmation
7. CANCEL          → Cancel if needed
```

### Price Drift Handling

| Drift % | Severity | Action |
|---------|----------|--------|
| <= 2% | normal | Auto-accept |
| 2-5% | warning | Accept with warning |
| 5-10% | high | Require approval |
| > 10% | critical | Block booking, alert ops |

---

## 10. Sync Job Stability

### Guards

- **Duplicate Prevention**: Check for running jobs before starting new sync
- **Stuck Job Detection**: Jobs running > 5 minutes are marked as stuck
- **Idempotency**: Same supplier + same hour = skip if already completed
- **Partial Failure**: Continue syncing other regions if one fails
- **Graceful Degradation**: If supplier is down, serve stale cached data

### Job States

```
pending → running → completed
                  → completed_with_errors
                  → failed
                  → stuck (detected by monitor)
```

---

## 11. Supplier Onboarding Checklist

To add a new supplier:

1. Create HTTP adapter: `app/suppliers/adapters/{name}_adapter.py`
2. Create canonical bridge: add class to `app/suppliers/adapters/real_bridges.py`
3. Register in `app/suppliers/registry.py`
4. Add sync config to `SUPPLIER_SYNC_CONFIG`
5. Add timeout overrides to timeout matrix
6. Add rate limit config
7. Register failover chain
8. Add sandbox validation test
9. Update frontend dashboard supplier list
10. Create integration test

---

## 12. Security

- Credentials stored encrypted in `supplier_credentials` MongoDB collection
- API keys never logged (masked in all outputs)
- Per-org credential isolation (multi-tenant)
- Credential rotation support via update endpoint
- Validation endpoint tests credentials without storing sensitive data in logs

---

## 13. Supported Suppliers

| Supplier | Code | Products | Auth Method | Status |
|----------|------|----------|-------------|--------|
| RateHawk | `ratehawk` | Hotel | Basic (key_id:api_key) | Sandbox Ready |
| Paximum | `paximum` | Hotel, Transfer, Activity | Token (user/pass/agency) | Adapter Ready |
| TBO | `tbo` | Hotel, Flight, Tour | Token (client_id/secret) | Adapter Ready |
| WWTatil | `wwtatil` | Tour | Token (user/pass/agency) | Adapter Ready |

---

*Document Version: 1.0*
*Last Updated: 2026-02-XX*
*Author: Syroce Engineering*
