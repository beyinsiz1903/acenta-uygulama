# Travel Distribution SaaS — PRD

## Product Vision
B2B otel dağıtım platformu: acentalar, tedarikçiler ve operasyon ekipleri için.

## Core Architecture
- **Backend**: FastAPI + MongoDB (Motor async)
- **Frontend**: React + Shadcn/UI
- **Multi-tenant**: Organization-based isolation (HARDENED)
- **Suppliers**: Paximum (active), Hotelbeds/Juniper (planned)

## Domain Modules (Modular Monolith)

### Active Modules
| Module | Path | Status |
|--------|------|--------|
| **Tenant** | `modules/tenant/` | Production-ready (isolation hardening) |
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

### Tenant Isolation (Canonical)
**Enforcement layer**: `app/modules/tenant/`

Key components:
- `TenantScopedRepository`: base class for all tenant-aware data access
- `TenantContext`: FastAPI dependency for extracting tenant info
- `TenantGuard`: enforcement layer + violation audit logging
- Admin bypass whitelist for global collections
- Exception handlers for security boundary violations (403)

Guarantees:
- Every query on tenant-scoped collections includes `organization_id` filter
- Cross-tenant access attempts raise `TenantFilterBypassAttempt` (logged as CRITICAL)
- Aggregate pipelines enforce `$match: {organization_id}` as first stage
- Insert operations auto-stamp `organization_id`
- Legacy `include_legacy_without_tenant=True` deprecated (defaults to False)
- 32 collections classified (tenant-scoped vs global)
- `organization_id` indexes on all tenant-scoped collections

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
- 11 domain modules (including tenant)
- ~119 remaining routers in organized sections
- See `ROUTER_DOMAIN_MANIFEST.md` for details

## Key API Endpoints

### Tenant Isolation Admin Endpoints (NEW)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/admin/tenant-isolation/health` | Health score + collection audit |
| GET | `/api/admin/tenant-isolation/violations` | Violation log viewer |
| POST | `/api/admin/tenant-isolation/ensure-indexes` | Create org_id indexes |
| GET | `/api/admin/tenant-isolation/orphaned-documents` | Find orphaned docs |
| GET | `/api/admin/tenant-isolation/scope-summary` | Coverage per collection |

### Booking Command Endpoints
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/bookings/{id}/quote` | Create quote |
| POST | `/api/bookings/{id}/confirm` | Confirm booking |
| POST | `/api/bookings/{id}/cancel` | Cancel booking |
| POST | `/api/bookings/{id}/complete` | Complete booking |
| GET | `/api/bookings/{id}/history` | Transition history |
| GET | `/api/bookings-statuses/transitions` | Transition matrix |

### Orphan Migration Admin Endpoints (NEW)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/admin/orphan-migration/status` | Migration summary + health score |
| GET | `/api/admin/orphan-migration/audit-log` | Audit trail with evidence chains |
| GET | `/api/admin/orphan-migration/quarantine` | Quarantined orders (filter by reviewed/strategy) |
| POST | `/api/admin/orphan-migration/review` | Approve/reject quarantined order |
| POST | `/api/admin/orphan-migration/analyze` | Re-run dry-run analysis |
| POST | `/api/admin/orphan-migration/rollback` | Rollback a migration batch |

### Existing Endpoints
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/login` | Login |
| GET | `/api/auth/me` | Current user |
| GET | `/api/health` | Health check |

## Test Credentials
- **Super Admin**: agent@acenta.test / agent123
- **Agency Admin**: agency1@demo.test / agency123

## Completed Milestones
1. Paximum Supplier Integration
2. Strategic Analysis & Growth Plan
3. **Unified Booking State Machine** (P0 #1)
4. **Router Domain Consolidation Phase 1** (P0 #2)
5. **Tenant Isolation Hardening** (P0 #3)
6. **Orphan Order Organization Recovery** (P1 — Data Integrity)

## Active Roadmap

### P0 — In Progress
- [x] Booking State Machine Unification
- [x] Router Consolidation Phase 1 (domain aggregates)
- [x] Tenant Isolation Hardening
- [x] Orphan Order Organization Recovery (data integrity)
- [ ] Async Queue (Celery + Redis + Outbox Consumer)

### P1 — Next
- [ ] Event-Driven Core (outbox consumer workers)
- [ ] Transactional Outbox Pattern (full implementation)
- [ ] API Response Standardization
- [ ] Router Consolidation Phase 2 (admin, inventory, public)

### P2 — Backlog
- [ ] Cache Strategy (L0/L1/L2)
- [ ] API Versioning (/api/v1/)
- [ ] Webhook System
- [ ] New Supplier Adapters (Hotelbeds, Juniper)
- [ ] Frontend persona-based separation

### Deferred (Out of Scope)
- WebPOS, Storefront, Tour Management, Campaign Engine, CMS, AI Assistant
