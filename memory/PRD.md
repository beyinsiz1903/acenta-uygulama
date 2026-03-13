# Syroce — Travel SaaS Platform PRD

## Original Problem Statement
Enterprise multi-tenant travel B2B SaaS platform for agencies. Includes search, booking, pricing, payments, supplier integrations, and ops management.

## Architecture
- **Frontend:** React + Tailwind + Shadcn/UI
- **Backend:** FastAPI + MongoDB + Redis + Celery
- **Suppliers:** RateHawk (hotel), TBO (hotel+flight+tour), Paximum (hotel+transfer+activity), WWTatil (tour)

## Core Requirements
- Multi-tenant agency management
- Search, booking, voucher pipelines
- Supplier integrations with failover
- Production readiness with monitoring
- Multi-tenant supplier credentials (per-agency)
- Real supplier API adapters
- Supplier Aggregator for unified search

## Completed Features

### Phase 1-2: Core Platform (DONE)
- Authentication, multi-tenancy, RBAC
- Hotel/flight search and booking
- Pricing, payments, CRM, Admin dashboards

### Phase 3: Production Hardening (DONE)
- Security, reliability, DLQ, monitoring, 15+ tabs

### Celery Worker Infrastructure (DONE - 9.88/10)
### Supplier Activation (DONE - 9.88/10)
### Stress Testing (DONE - 10.0/10)
### Production Pilot Launch (DONE - 10.0/10)

### Multi-Tenant Supplier Integration (DONE)
- **Supplier Credentials Service:** AES-256 encrypted per-agency credential storage
- **Connection Testing:** Real HTTP calls to supplier APIs with latency measurement
- **Frontend:** Supplier Settings tab with 4 supplier cards
- **Multi-tenant model:** Each agency manages their own supplier credentials

### Supplier Adapter Pattern + Aggregator (DONE - 13 Mar 2026)
- **Base Adapter:** Abstract interface (authenticate, search_hotels, search_tours, search_flights, search_transfers, search_activities, create_booking, cancel_booking)
- **RateHawk Adapter:** Hotel supplier with Basic auth (key_id:api_key)
- **TBO Adapter:** Multi-product (hotel, flight, tour) with token auth
- **Paximum Adapter:** Multi-product (hotel, transfer, activity) with token auth
- **WWTatil Adapter:** Tour supplier with token auth (24h validity), full booking flow
- **Supplier Aggregator:** Fan-out parallel search across all connected suppliers, price sorting, capability matrix
- **Capability Matrix UI:** Table showing supplier vs product type coverage, product coverage badges
- **Test report:** 31/31 backend tests passed (iteration_80)

## Supplier Capability Matrix

| Supplier | Hotel | Flight | Tour | Transfer | Activity |
|----------|-------|--------|------|----------|----------|
| RateHawk | Yes   | -      | -    | -        | -        |
| TBO      | Yes   | Yes    | Yes  | -        | -        |
| Paximum  | Yes   | -      | -    | Yes      | Yes      |
| WWTatil  | -     | -      | Yes  | -        | -        |

## Key APIs

### Supplier Credentials APIs
- `GET /api/supplier-credentials/supported` — List supported suppliers
- `GET /api/supplier-credentials/my` — Get agency's credentials (masked)
- `POST /api/supplier-credentials/save` — Save credentials (encrypted)
- `DELETE /api/supplier-credentials/{supplier}` — Delete credentials
- `POST /api/supplier-credentials/test/{supplier}` — Test connection

### Supplier Aggregator APIs
- `POST /api/supplier-aggregator/search` — Unified search across all connected suppliers
- `GET /api/supplier-aggregator/capabilities` — Supplier capability matrix
- `GET /api/supplier-aggregator/coverage` — Product type coverage

### WWTatil Direct APIs
- `POST /api/supplier-credentials/wwtatil/tours` — Get tours
- `POST /api/supplier-credentials/wwtatil/search` — Search tours
- `POST /api/supplier-credentials/wwtatil/basket/add` — Add basket item
- `POST /api/supplier-credentials/wwtatil/booking/create` — Create booking

## DB Schema

### supplier_credentials collection
```
{
  organization_id: str,       // Agency ID (tenant)
  supplier: str,              // "ratehawk" | "tbo" | "paximum" | "wwtatil"
  status: str,                // "saved" | "connected" | "auth_failed"
  enc_base_url: str,          // AES encrypted
  enc_key_id: str,            // RateHawk
  enc_api_key: str,           // RateHawk
  enc_username: str,          // TBO, Paximum, WWTatil
  enc_password: str,          // TBO, Paximum, WWTatil
  enc_client_id: str,         // TBO (optional)
  enc_agency_code: str,       // Paximum
  enc_application_secret_key: str, // WWTatil
  enc_agency_id: str,         // WWTatil
  connected_at: str,
  last_tested: str
}
```

### supplier_tokens collection
```
{
  organization_id: str,
  supplier: str,
  token: str,
  obtained_at: str,
  expires_hours: int
}
```

## Remaining Backlog

### P0 — Immediate
- Activate real supplier connections with live API credentials
- Connect unified search aggregator to platform booking flow

### P1 — Next
- Complete remaining 10-part activation flow (shadow traffic, limited booking, monitoring)
- Connect real booking flow through supplier adapters
- Implement supplier fallback logic (if one fails, try next)

### P2 — Future
- Real Prometheus/Grafana integration
- Full customer onboarding workflow
- Dedicated cross-tenant security testing
- Supplier rate comparison dashboard
- Booking reconciliation across suppliers

## Test Credentials
- Super Admin: agent@acenta.test / agent123
- Agency Admin: agency1@demo.test / agency123
