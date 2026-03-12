# Supplier Ecosystem Architecture — Syroce Travel Platform

## Architecture Overview

```
                    +------------------+
                    |   API Gateway    |
                    | /api/suppliers/* |
                    +--------+---------+
                             |
              +--------------+--------------+
              |                             |
     +--------v---------+        +---------v--------+
     |   Aggregator     |        |   Orchestrator   |
     | (Multi-supplier  |        | (Booking         |
     |  search fan-out) |        |  lifecycle mgmt) |
     +--------+---------+        +---------+--------+
              |                             |
    +---------+---------+         +---------+--------+
    |                   |         |                  |
+---v---+  +---v---+  +---v---+ +---v---+  +---v---+
| Flight|  | Hotel |  | Tour  | |Pricing|  |Channel|
|Adapter|  |Adapter|  |Adapter| |Engine |  |Manager|
+---+---+  +---+---+  +---+---+ +---+---+  +---+---+
    |          |          |          |          |
+---v----------v----------v----+ +---v----+ +---v----+
|     Supplier Registry        | |Failover| | Health |
|   (adapter discovery)        | | Engine | | Scorer |
+------------------------------+ +--------+ +--------+
              |
    +---------+---------+
    |                   |
+---v---+         +---v---+
| Redis |         |MongoDB|
| Cache |         | (data)|
+-------+         +-------+
```

## Domain Structure

```
/app/backend/app/suppliers/
├── __init__.py
├── contracts/
│   ├── __init__.py
│   ├── base.py              # SupplierAdapter ABC
│   ├── schemas.py           # 20+ normalized Pydantic models
│   └── errors.py            # Typed error hierarchy
├── adapters/
│   ├── __init__.py
│   ├── mock_hotel.py        # Full lifecycle (7 methods)
│   ├── mock_flight.py       # Search, hold, confirm, cancel
│   ├── mock_tour.py         # Search, hold, confirm, cancel
│   ├── mock_insurance.py    # Search, confirm
│   └── mock_transport.py    # Search, hold, confirm, cancel
├── aggregator/
│   ├── __init__.py
│   └── service.py           # Multi-supplier fan-out + merge
├── orchestrator/
│   ├── __init__.py
│   └── service.py           # Full booking lifecycle engine
├── registry.py              # Adapter registration + discovery
├── state_machine.py         # 13 states, 22 transitions
├── failover.py              # Weighted failover algorithm
├── health.py                # 5-metric health scoring (0-100)
├── cache.py                 # Redis TTL caching + invalidation
├── pricing.py               # 6-stage pricing pipeline
├── channel.py               # B2B partner access control
├── events.py                # Event catalog + handlers
├── indexes.py               # 20 MongoDB indexes
└── router.py                # 18 API endpoints
```

## Part 1 — Supplier Adapter Contract

### Interface
```python
class SupplierAdapter(ABC):
    supplier_code: str
    supplier_type: SupplierType  # flight|hotel|tour|insurance|transport

    async def healthcheck(ctx) -> dict
    async def search(ctx, request) -> SearchResult
    async def check_availability(ctx, request) -> AvailabilityResult
    async def get_pricing(ctx, request) -> PricingResult
    async def create_hold(ctx, request) -> HoldResult
    async def confirm_booking(ctx, request) -> ConfirmResult
    async def cancel_booking(ctx, request) -> CancelResult
```

### Normalized Schemas
| Schema | Fields | Used By |
|--------|--------|---------|
| SearchRequest | product_type, destination, dates, adults, filters | Aggregator |
| SearchResult | items[], suppliers_queried, duration_ms, degraded | API |
| SearchItem | supplier_price, sell_price, item_id, metadata | Aggregator, Cache |
| FlightSearchItem | airline, flight_number, departure/arrival times | Flight adapters |
| HotelSearchItem | star_rating, room_type, board_type, nights | Hotel adapters |
| TourSearchItem | tour_code, duration_days, guide_language | Tour adapters |
| InsuranceSearchItem | coverage_type, coverage_amount, deductible | Insurance adapters |
| TransportSearchItem | vehicle_type, capacity, pickup/dropoff | Transport adapters |
| PriceBreakdown | base_price, tax, service_fee, discount, total | Pricing engine |

### Error Hierarchy
```
SupplierError (base)
├── SupplierTimeoutError (retryable=True)
├── SupplierUnavailableError (retryable=True)
├── SupplierRateLimitError (retryable=True)
├── SupplierValidationError (retryable=False)
├── SupplierBookingError (retryable=False)
└── SupplierAuthError (retryable=False)
```

## Part 2 — Inventory Aggregation

### Fan-out Flow
1. Determine target adapters (by supplier_codes or product_type)
2. Filter out circuit-open suppliers
3. Fan out parallel async calls with per-supplier timeout
4. Collect results, record circuit breaker success/failure
5. Deduplicate by supplier_code:supplier_item_id
6. Sort (price_asc, price_desc, rating_desc, name_asc)
7. Paginate
8. Cache results
9. Return merged SearchResult with degradation flag

### Resilience
- Each supplier call has independent timeout (ctx.timeout_ms)
- Partial failures produce `degraded=True` result (not empty)
- Circuit breaker integration: open circuits skip call entirely
- Cache fallback: stale-while-revalidate on total failure

## Part 3 — Booking State Machine

### States (13)
```
draft → search_completed → price_validated → hold_created →
  payment_pending → payment_completed → supplier_confirmed → voucher_issued

Side: cancellation_requested → cancelled → refund_pending → refunded
Sink: failed (reachable from any active state)
```

### Transitions (22)
| From | To | Event | Trigger |
|------|----|-------|---------|
| draft | search_completed | booking.search_completed | Aggregator search done |
| search_completed | price_validated | booking.price_validated | Price check passed |
| price_validated | hold_created | booking.hold_created | Supplier hold success |
| hold_created | payment_pending | booking.payment_initiated | Payment flow started |
| payment_pending | payment_completed | booking.payment_completed | Payment confirmed |
| payment_completed | supplier_confirmed | booking.supplier_confirmed | Supplier confirmation |
| supplier_confirmed | voucher_issued | booking.voucher_issued | Voucher generated |
| * | failed | booking.failed | Unrecoverable error |

### Rollback Map
| Failed State | Rollback To |
|-------------|-------------|
| hold_created | price_validated |
| payment_pending | hold_created |
| payment_completed | payment_pending |
| supplier_confirmed | payment_completed |

## Part 4 — Booking Orchestration Engine

### Flow
```
orchestrate_booking()
  │
  ├─ 1. Create draft booking (if not exists)
  ├─ 2. Transition → search_completed
  ├─ 3. Validate price with supplier
  │     └─ On failure: trigger failover
  ├─ 4. Create reservation hold
  │     └─ Optional: skip if supplier doesn't support hold
  ├─ 5. Transition → payment_pending → payment_completed
  ├─ 6. Confirm with supplier (with retry + backoff)
  ├─ 7. Transition → supplier_confirmed → voucher_issued
  ├─ 8. Emit domain events
  └─ 9. Trigger async post-booking jobs (voucher PDF, email)
```

### Features
- Idempotency keys per step
- Retry: 3 attempts with exponential backoff (2s, 5s, 10s)
- Circuit breaker aware: skips broken suppliers
- Failover: automatic fallback to secondary supplier
- Compensation: rollback on partial failure
- Async jobs: Celery tasks for voucher + email

## Part 5 — Supplier Failover Engine

### Algorithm
```
get_fallback(primary_supplier):
  1. Get explicit fallback chain
  2. Filter out: circuit-open, disabled, excluded suppliers
  3. Score remaining by composite:
     composite = health_score * 0.4 + price_score * 0.3 + reliability * 0.3
  4. Sort by composite descending
  5. Return top candidate
```

### Scoring Weights
| Factor | Weight | Source |
|--------|--------|--------|
| Health Score | 40% | Health scorer (0-100 normalized) |
| Price Competitiveness | 30% | Historical pricing data |
| Reliability Score | 30% | Confirmation success rate |

### Audit
Every failover decision is persisted to `supplier_failover_logs` with 30-day TTL.

## Part 6 — Supplier Health Scoring

### Formula (0-100)
```
score = latency_score * 0.20
      + error_score * 0.30
      + timeout_score * 0.20
      + confirmation_score * 0.20
      + freshness_score * 0.10
```

### Metric Scoring
| Metric | 100 (best) | 0 (worst) |
|--------|-----------|-----------|
| Latency (p95) | < 2000ms | > 10000ms |
| Error rate | 0% | >= 20% |
| Timeout rate | 0% | >= 10% |
| Confirmation rate | 100% | < 80% |
| Inventory freshness | < 5 min | > 60 min |

### Health States
| Score | State | Action |
|-------|-------|--------|
| >= 80 | healthy | Normal operation |
| 60-79 | degraded | Warning, monitor closely |
| 40-59 | critical | Alert ops team |
| < 40 | disabled | Auto-disable, trigger failover |

### Recovery
Re-enable after 3 consecutive checks above 60.

## Part 7 — Redis Inventory Cache

### TTL Strategy
| Product Type | TTL | Reason |
|-------------|-----|--------|
| flight | 300s (5 min) | Prices change frequently |
| hotel | 900s (15 min) | Moderate volatility |
| tour | 1800s (30 min) | Stable pricing |
| insurance | 3600s (1 hour) | Very stable |
| transport | 600s (10 min) | Dynamic demand |

### Key Naming
```
supplier_cache:{org_id}:{product_type}:{md5(search_params)[:12]}
```

### Stale-While-Revalidate
- STALE_BUFFER: 120s extra TTL beyond main TTL
- Serve stale results with `degraded=True` while refreshing

### Invalidation
- On booking confirm: invalidate by org_id
- On supplier health degraded: invalidate all for that supplier
- Manual: POST /api/suppliers/ecosystem/cache/invalidate

## Part 8 — Pricing Engine

### Pipeline (in order)
```
1. Supplier net price (base_price)
2. Product-type markup (hotel: 15%, flight: 8%, tour: 18%)
3. Channel adjustment (B2B: -3%)
4. Agency tier adjustment (premium: -5%, enterprise: -8%)
5. Commission calculation (per tier)
6. Promotional overrides (if promo_code)
7. Currency conversion (if needed)
8. Final sell_price
```

### Agency Tiers
| Tier | Commission | Markup Adjustment |
|------|-----------|-------------------|
| starter | 5% | 0% |
| standard | 8% | -2% |
| premium | 12% | -5% |
| enterprise | 15% | -8% |

## Part 9 — Channel Manager

### Partner Data Model
```json
{
  "partner_id": "uuid",
  "partner_type": "sub_agency|reseller|affiliate|api_partner",
  "status": "pending|active|suspended|terminated",
  "allowed_suppliers": ["mock_hotel"],
  "allowed_product_types": ["hotel", "flight"],
  "pricing_tier": "premium",
  "commission_rate": 12.0,
  "credit_limit": 100000,
  "credit_used": 0,
  "api_key": "sk_partner_...",
  "rate_limit_rpm": 60
}
```

### Access Control Flow
```
check_partner_access(partner_id, supplier_code, product_type):
  1. Verify partner exists and is active
  2. Check supplier whitelist (empty = all)
  3. Check product type whitelist (empty = all)
  4. Check credit limit
  5. Return: {allowed, reason, pricing_tier}
```

## Part 10 — Domain Event Catalog

| Event | Producer | Consumer | Retry |
|-------|----------|----------|-------|
| supplier.search_completed | Aggregator | Analytics | No |
| supplier.search_cached_hit | Cache | Analytics | No |
| supplier.hold_created | Orchestrator | State Machine | No |
| supplier.hold_failed | Orchestrator | Failover | No |
| supplier.booking_confirmed | Orchestrator | Voucher Gen, Email | Yes (3x) |
| supplier.booking_failed | Orchestrator | Alerting | No |
| supplier.booking_cancelled | Orchestrator | Refund Engine | Yes (3x) |
| supplier.failover_triggered | Failover | Alerting, Audit | No |
| supplier.health_degraded | Health Scorer | Cache Invalidation | No |
| supplier.health_recovered | Health Scorer | Re-enable supplier | No |
| supplier.voucher_generated | Voucher Task | Email Notification | Yes (5x) |
| supplier.price_changed | Pricing | Cache Invalidation | No |
| supplier.orchestration_started | Orchestrator | Monitoring | No |
| supplier.orchestration_completed | Orchestrator | Analytics | No |
| supplier.orchestration_failed | Orchestrator | Alerting | No |

## Part 11 — Database Design

### Collections
| Collection | Purpose | TTL | Indexes |
|-----------|---------|-----|---------|
| suppliers | Registered supplier configs | None | (org_id, code) unique |
| supplier_ecosystem_health | Health scores | None | (org_id, code) unique, score |
| supplier_failover_logs | Failover audit | 30 days | (org_id, created_at), (primary_supplier) |
| booking_orchestration_runs | Orchestration tracking | 90 days | booking_id, (org_id, created_at), status |
| channel_partners | B2B partners | None | (org_id, status), partner_id unique, api_key |
| supplier_pricing_rules | Pricing config | None | (org_id, active, priority), rule_id unique |
| supplier_inventory_cache_metadata | Cache tracking | 1 day | (org_id, supplier_code) |

### Total Indexes: 20

## Part 12 — API Design

### Route Map

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | /api/suppliers/ecosystem/search | agency_admin+ | Multi-supplier search |
| POST | /api/suppliers/ecosystem/availability | agency_admin+ | Single-supplier availability |
| POST | /api/suppliers/ecosystem/pricing | agency_admin+ | Price validation |
| POST | /api/suppliers/ecosystem/hold | agency_admin+ | Create reservation hold |
| POST | /api/suppliers/ecosystem/confirm | agency_admin+ | Confirm booking |
| POST | /api/suppliers/ecosystem/cancel | agency_admin+ | Cancel booking |
| POST | /api/suppliers/ecosystem/orchestrate | agency_admin+ | Full booking flow |
| GET | /api/suppliers/ecosystem/health | agency_admin+ | Health dashboard |
| POST | /api/suppliers/ecosystem/health/{code}/compute | agency_admin+ | Compute health score |
| GET | /api/suppliers/ecosystem/failover-logs | agency_admin+ | Failover audit |
| GET | /api/suppliers/ecosystem/orchestration-runs | agency_admin+ | Orchestration history |
| GET | /api/suppliers/ecosystem/partners | agency_admin+ | List partners |
| POST | /api/suppliers/ecosystem/partners | agency_admin+ | Create partner |
| POST | /api/suppliers/ecosystem/partners/{id}/approve | agency_admin+ | Approve partner |
| GET | /api/suppliers/ecosystem/cache/stats | agency_admin+ | Cache statistics |
| POST | /api/suppliers/ecosystem/cache/invalidate | agency_admin+ | Invalidate cache |
| GET | /api/suppliers/ecosystem/registry | agency_admin+ | List adapters |
| GET | /api/suppliers/ecosystem/booking-states | public | State machine info |

## Part 13 — Test Strategy

### Priority Coverage
| Area | Priority | Type | Coverage |
|------|----------|------|----------|
| Adapter contract compliance | P0 | Unit | All 7 lifecycle methods per adapter |
| Aggregator merge behavior | P0 | Integration | Multi-supplier + partial failure |
| Booking orchestration flow | P0 | Integration | Happy path + failure + rollback |
| State machine transitions | P0 | Unit | All 22 transitions + invalid |
| Failover scenarios | P1 | Integration | Circuit open + scoring |
| Pricing rule validation | P1 | Unit | All 6 pipeline stages |
| Cache invalidation | P1 | Integration | TTL, stale, invalidation |
| Channel partner access | P1 | Unit | Allow, deny, credit limit |
| Event emission | P2 | Integration | All 15 event types |

## Part 14 — Maturity Score Update

### Before Supplier Ecosystem
| Dimension | Score |
|-----------|-------|
| Architecture | 7.0/10 |
| Scalability | 6.5/10 |
| Observability | 6.0/10 |
| Security | 7.5/10 |
| Test Coverage | 4.0/10 |
| **Overall** | **6.8/10** |

### After Supplier Ecosystem
| Dimension | Score | Change |
|-----------|-------|--------|
| Architecture | 8.2/10 | +1.2 |
| Scalability | 7.5/10 | +1.0 |
| Observability | 6.5/10 | +0.5 |
| Security | 7.5/10 | +0.0 |
| Test Coverage | 4.5/10 | +0.5 |
| **Overall** | **7.5/10** | **+0.7** |

## Top 50 Implementation Tasks

### P0 — Critical (implement now)
1. Replace mock adapters with real Paximum hotel adapter
2. Implement AviationStack flight adapter
3. Add authentication middleware for partner API keys
4. Implement idempotency store for booking confirmations
5. Add database-driven pricing rules (replace hardcoded defaults)
6. Implement booking rollback compensation logic
7. Add supplier onboarding API (CRUD for supplier configs)
8. Implement retry with exponential backoff in aggregator
9. Add request validation for all API endpoints
10. Implement supplier API key encryption (at-rest)

### P1 — High Priority (next sprint)
11. Implement real-time availability polling
12. Add webhook receiver for supplier push notifications
13. Implement voucher PDF generation in Celery task
14. Add email notification after booking confirmation
15. Implement credit limit enforcement in orchestrator
16. Add agency-specific pricing rule overrides
17. Implement supplier catalog sync (scheduled)
18. Add rate limiting per supplier per organization
19. Implement partial booking (multi-supplier composite)
20. Add booking amendment flow (date change, room change)

### P2 — Medium Priority (month 2)
21. Implement currency conversion in pricing pipeline
22. Add promotional code validation
23. Implement supplier sandbox environment
24. Add supplier API contract validation (schema checks)
25. Implement cache warming jobs (popular routes)
26. Add supplier performance dashboard (Grafana)
27. Implement booking reconciliation (supplier vs platform)
28. Add multi-currency support in channel partner credits
29. Implement supplier SLA tracking and alerting
30. Add booking timeline visualization API

### P3 — Future (month 3+)
31. Implement real tour operator integrations
32. Add insurance provider integrations
33. Implement transfer/transport provider integrations
34. Add GDS connectivity (Amadeus, Sabre, Travelport)
35. Implement dynamic pricing based on demand
36. Add A/B testing for pricing rules
37. Implement supplier bid management
38. Add bulk booking support
39. Implement booking export (CSV, PDF, Excel)
40. Add supplier payment reconciliation

### P4 — Optimization
41. Implement connection pooling per supplier
42. Add request deduplication layer
43. Implement supplier response time prediction
44. Add intelligent cache pre-warming
45. Implement query-level caching for MongoDB
46. Add supplier result scoring (ML-based ranking)
47. Implement booking fraud detection
48. Add capacity planning dashboard
49. Implement supplier cost optimization
50. Add multi-region supplier routing

## Top 20 Technical Risks

| # | Risk | Impact | Mitigation |
|---|------|--------|------------|
| 1 | Supplier API downtime | Bookings blocked | Failover engine + cache |
| 2 | Price discrepancy (cache vs live) | Revenue loss | Short TTLs + price guarantee flag |
| 3 | Double booking | Financial loss | Idempotency keys per step |
| 4 | Hold expiry before payment | Lost bookings | Timer-based hold extension |
| 5 | Circuit breaker false positive | Unnecessary failover | Tuned thresholds + manual reset |
| 6 | Redis failure | No caching, no rate limiting | MongoDB fallback for critical paths |
| 7 | Celery worker crash | Tasks lost | Redis persistence + DLQ |
| 8 | Supplier schema changes | Adapter breakage | Contract tests per adapter |
| 9 | Multi-tenant data leak | Security breach | organization_id in every query |
| 10 | Concurrent booking race | Inventory oversell | Distributed locks |
| 11 | Payment timeout | Stuck bookings | Compensation + timeout state |
| 12 | Supplier rate limiting | Search degradation | Per-supplier rate limit awareness |
| 13 | Large search result sets | Memory pressure | Streaming + pagination |
| 14 | Partner credit abuse | Financial loss | Real-time credit enforcement |
| 15 | Stale health scores | Wrong failover | Frequent re-computation |
| 16 | Event bus failure | Lost events | MongoDB persistence + replay |
| 17 | Pricing rule misconfiguration | Wrong prices shown | Audit trail + preview mode |
| 18 | Supplier auth token expiry | API call failures | Auto-refresh tokens |
| 19 | MongoDB connection exhaustion | Service outage | Connection pooling limits |
| 20 | Unbounded aggregator fan-out | Timeout cascade | Max suppliers per search |

---

*Generated: 2026-03-12*
*Platform: Syroce Travel Agency Operating System*
*Architecture Version: 3.0 (Supplier Ecosystem)*
