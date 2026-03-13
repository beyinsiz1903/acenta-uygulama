# Syroce — Travel SaaS Platform PRD

## Original Problem Statement
Enterprise multi-tenant travel B2B SaaS platform for agencies. Includes search, booking, pricing, payments, supplier integrations, and ops management.

## Architecture
- **Frontend:** React + Tailwind + Shadcn/UI
- **Backend:** FastAPI + MongoDB + Redis + Celery
- **Suppliers:** WWTatil (tour), Paximum (hotel), AviationStack (flight)

## Core Requirements
- Multi-tenant agency management
- Search, booking, voucher pipelines
- Supplier integrations with failover
- Production readiness with monitoring
- Multi-tenant supplier credentials (per-agency)
- Real supplier API adapters

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
- **WWTatil Tour API Adapter:** Full production-grade adapter
  - Auth: `/api/Auth/get-token-async` (24h token, per-agency cache)
  - Tour Catalog: `getall-tour-async`, `search-tour-async`
  - Basket: `add-basket-item-async`, `get-basket-by-id-async`, delete operations
  - Booking: `create-succeeded-booking-async`, notes, cancellation
  - Post-Sale: tour change, period change, service add/delete/cancel
- **Connection Testing:** Real HTTP calls to supplier APIs with latency measurement
- **Frontend:** Supplier Settings tab with 3 supplier cards (WWTatil, Paximum, AviationStack)
- **Multi-tenant model:** Each agency manages their own supplier credentials

## Key APIs

### Supplier Credentials APIs
- `GET /api/supplier-credentials/supported` — List supported suppliers
- `GET /api/supplier-credentials/my` — Get agency's credentials (masked)
- `POST /api/supplier-credentials/save` — Save credentials (encrypted)
- `DELETE /api/supplier-credentials/{supplier}` — Delete credentials
- `POST /api/supplier-credentials/test/{supplier}` — Test connection
- `POST /api/supplier-credentials/wwtatil/tours` — Get tours via wwtatil
- `POST /api/supplier-credentials/wwtatil/search` — Search tours via wwtatil
- `POST /api/supplier-credentials/wwtatil/basket/add` — Add basket item
- `POST /api/supplier-credentials/wwtatil/booking/create` — Create booking

## DB Schema

### supplier_credentials collection
```
{
  organization_id: str,       // Agency ID (tenant)
  supplier: str,              // "wwtatil" | "paximum" | "aviationstack"
  status: str,                // "saved" | "connected" | "auth_failed"
  enc_base_url: str,          // AES encrypted
  enc_application_secret_key: str,
  enc_username: str,
  enc_password: str,
  enc_agency_id: str,
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

### P1 — Next
- Complete remaining 10-part activation flow (shadow traffic, limited booking, monitoring, etc.)
- Connect real booking flow through wwtatil adapter

### P2 — Future
- Real Prometheus/Grafana integration
- Full customer onboarding workflow
- Dedicated cross-tenant security testing

## Test Credentials
- Super Admin: agent@acenta.test / agent123
- Agency Admin: agency1@demo.test / agency123
