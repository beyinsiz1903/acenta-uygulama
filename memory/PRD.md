# Travel Distribution SaaS — PRD

## Product Vision
B2B otel dağıtım platformu: acentalar, tedarikçiler ve operasyon ekipleri için.

## Core Architecture
- **Backend**: FastAPI + MongoDB (Motor async)
- **Frontend**: React + Shadcn/UI
- **Multi-tenant**: Organization-based isolation
- **Suppliers**: Paximum (active), Hotelbeds/Juniper (planned)

## Domain Modules (NEW — Modular Monolith)

### Active Modules
| Module | Path | Status |
|--------|------|--------|
| **Booking** | `modules/booking/` | Production-ready (unified state machine) |
| **Auth** | `modules/auth/` | Domain aggregate |
| **Identity** | `modules/identity/` | Domain aggregate |
| **B2B** | `modules/b2b/` | Domain aggregate |
| **Supplier** | `modules/supplier/` | Domain aggregate |
| **Finance** | `modules/finance/` | Domain aggregate |
| **CRM** | `modules/crm/` | Domain aggregate |
| **Operations** | `modules/operations/` | Domain aggregate |
| **Enterprise** | `modules/enterprise/` | Domain aggregate |
| **System** | `modules/system/` | Domain aggregate |

### Booking State Machine (Canonical)
**Single source of truth**: `app/modules/booking/models.py`

States: DRAFT → QUOTED → OPTIONED → CONFIRMED → COMPLETED → CANCELLED → REFUNDED

Separate tracks:
- `fulfillment_status`: NONE, TICKETED, VOUCHERED, BOTH
- `payment_status`: UNPAID, PARTIAL, PAID, REFUND_PENDING, REFUNDED

Key features:
- Command-based transitions (not direct status set)
- Optimistic locking (version field)
- Full history tracking (booking_history collection)
- Event outbox (outbox_events collection)
- Policy validation layer
- Legacy state migration

### Router Architecture
**Registry**: `app/bootstrap/domain_router_registry.py`
- 10 domain aggregates consolidating 115+ routers
- ~119 remaining routers in organized sections
- See `ROUTER_DOMAIN_MANIFEST.md` for details

## Key API Endpoints

### Booking Command Endpoints (NEW)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/bookings/{id}/quote` | Create quote |
| POST | `/api/bookings/{id}/option` | Place option |
| POST | `/api/bookings/{id}/confirm` | Confirm booking |
| POST | `/api/bookings/{id}/cancel` | Cancel booking |
| POST | `/api/bookings/{id}/complete` | Complete booking |
| POST | `/api/bookings/{id}/mark-ticketed` | Mark as ticketed |
| POST | `/api/bookings/{id}/mark-vouchered` | Mark as vouchered |
| POST | `/api/bookings/{id}/mark-refunded` | Mark as refunded |
| GET | `/api/bookings/{id}/history` | Transition history |
| GET | `/api/bookings/{id}/status` | Status summary |
| GET | `/api/bookings-statuses/transitions` | Transition matrix |

### Migration Endpoints
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/admin/booking-migration/run` | Run migration |
| GET | `/api/admin/booking-migration/status` | Migration status |

### Existing Endpoints
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/login` | Login |
| GET | `/api/auth/me` | Current user |
| GET | `/api/health` | Health check |
| POST | `/api/suppliers/paximum/search` | Hotel search |
| POST | `/api/suppliers/paximum/book` | Book hotel |

## Test Credentials
- **Super Admin**: agent@acenta.test / agent123
- **Agency Admin**: agency1@demo.test / agency123

## Completed Milestones
1. Paximum Supplier Integration
2. Strategic Analysis & Growth Plan
3. **Unified Booking State Machine** (P0 #1)
4. **Router Domain Consolidation Phase 1** (P0 #2)

## Active Roadmap

### P0 — In Progress
- [x] Booking State Machine Unification
- [x] Router Consolidation Phase 1 (domain aggregates)
- [ ] Unified Domain Boundaries (interface-based communication)
- [ ] Async Queue (Celery + Redis)
- [ ] Tenant Isolation Hardening

### P1 — Next
- [ ] Event-Driven Core (outbox consumer workers)
- [ ] Transactional Outbox Pattern (full implementation)
- [ ] API Response Standardization
- [ ] Router Consolidation Phase 2 (admin, inventory, public)
- [ ] Router Consolidation Phase 3 (merge files per domain)

### P2 — Backlog
- [ ] Cache Strategy (L0/L1/L2)
- [ ] API Versioning (/api/v1/)
- [ ] Webhook System
- [ ] New Supplier Adapters (Hotelbeds, Juniper)
- [ ] Frontend persona-based separation

### Deferred (Out of Scope)
- WebPOS, Storefront, Tour Management, Campaign Engine, CMS, AI Assistant
