# Syroce — Travel SaaS Platform PRD

## Original Problem Statement
Enterprise multi-tenant travel B2B SaaS platform for agencies. Includes search, booking, pricing, payments, supplier integrations, and ops management.

## Architecture
- **Frontend:** React + Tailwind + Shadcn/UI
- **Backend:** FastAPI + MongoDB + Redis + Celery
- **Suppliers:** RateHawk (hotel), TBO (hotel+flight+tour), Paximum (hotel+transfer+activity), WWTatil (tour)
- **Booking Core:** Orchestrator + State Machine + Failover Engine + Registry

## Completed Features

### Phase 1-2: Core Platform (DONE)
- Authentication, multi-tenancy, RBAC
- Hotel/flight search and booking
- Pricing, payments, CRM, Admin dashboards

### Phase 3: Production Hardening (DONE)
- Security, reliability, DLQ, monitoring, 15+ tabs

### Multi-Tenant Supplier Integration (DONE)
- AES-256 encrypted per-agency credential storage
- Connection testing, 4 supplier cards UI

### Supplier Adapter Pattern + Aggregator (DONE - 13 Mar 2026)
- Base Adapter interface, 4 real adapters, Aggregator, Capability Matrix

### Unified Booking & Fallback Layer (DONE - 13 Mar 2026)
- **Real Adapter Bridge:** 4 bridges wrapping HTTP adapters in canonical contract interface
  - RealRateHawkBridge, RealTBOBridge, RealPaximumBridge, RealWWTatilBridge
  - Each implements: search, confirm_booking, cancel_booking (wwtatil also create_hold)
- **Registry Integration:** 9 adapters registered (4 real + 5 mock), capability metadata, product type routing
- **Unified Search:** Fan-out search via contract interface (hotel→3, tour→2, flight→1, transfer→1, activity→1)
- **Price Revalidation:** Drift thresholds (<2% silent, 2-5% warn, 5-10% approval, >10% abort)
- **Booking Execution:** Full orchestration with fallback chain execution
- **Fallback Chains:** ratehawk→[tbo,paximum], tbo→[ratehawk,paximum], paximum→[ratehawk,tbo], wwtatil→[tbo]
- **Reconciliation:** Price/status mismatch detection, aggregated summaries
- **Audit & Observability:** In-memory metrics + MongoDB audit trail (booking_audit_log)
- **Capability Metadata:** supports_hold, supports_direct_confirm, supports_cancel per supplier
- **Test report:** 32/32 tests passed (iteration_81)

## Supplier Capability Matrix

| Supplier | Hotel | Flight | Tour | Transfer | Activity | Hold | Cancel |
|----------|-------|--------|------|----------|----------|------|--------|
| RateHawk | Yes   | -      | -    | -        | -        | No   | Yes    |
| TBO      | Yes   | Yes    | Yes  | -        | -        | No   | Yes    |
| Paximum  | Yes   | -      | -    | Yes      | Yes      | No   | Yes    |
| WWTatil  | -     | -      | Yes  | -        | -        | Yes  | Yes    |

## Key API Endpoints

### Unified Booking APIs
- `POST /api/unified-booking/search` — Fan-out search across real suppliers
- `POST /api/unified-booking/revalidate` — Pre-booking price/availability check
- `POST /api/unified-booking/book` — Execute booking with fallback chain
- `GET /api/unified-booking/registry` — Registered adapters and capabilities
- `GET /api/unified-booking/metrics` — Booking execution metrics
- `GET /api/unified-booking/audit` — Organization audit trail
- `GET /api/unified-booking/audit/{booking_id}` — Booking-specific audit
- `GET /api/unified-booking/reconciliation/{booking_id}` — Reconciliation check
- `GET /api/unified-booking/reconciliation-mismatches` — Mismatched bookings

### Supplier Credential APIs
- `GET /api/supplier-credentials/supported`
- `GET /api/supplier-credentials/my`
- `POST /api/supplier-credentials/save`
- `DELETE /api/supplier-credentials/{supplier}`
- `POST /api/supplier-credentials/test/{supplier}`

### Supplier Aggregator APIs
- `POST /api/supplier-aggregator/search`
- `GET /api/supplier-aggregator/capabilities`
- `GET /api/supplier-aggregator/coverage`

## DB Collections (New)
- `price_revalidations` — Pre-booking price checks
- `booking_reconciliation` — Internal vs supplier state tracking
- `booking_audit_log` — Audit trail events
- `unified_bookings` — Bookings created via unified flow
- `supplier_tokens` — Cached supplier auth tokens

## Remaining Backlog

### P0
- Activate real supplier connections with live API credentials
- End-to-end booking test with a real supplier

### P1
- Frontend unified booking flow UI (search → select → book)
- Booking reconciliation dashboard
- Shadow traffic activation
- Scheduled reconciliation jobs

### P2
- Real Prometheus/Grafana metrics
- Supplier rate comparison dashboard
- Full customer onboarding workflow
- Cross-tenant security testing

## Test Credentials
- Super Admin: agent@acenta.test / agent123
- Agency Admin: agency1@demo.test / agency123
