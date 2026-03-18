# Router Domain Manifest

## Architecture: Domain-Based Router Registry
**Status**: Phase 1 Complete — Domain aggregates created, registry reorganized.

### Registry Files
| File | Purpose |
|------|---------|
| `app/bootstrap/domain_router_registry.py` | **ACTIVE** — Domain-organized router registration |
| `app/bootstrap/router_registry.py` | **DEPRECATED** — Old flat registry (kept as reference) |

### Domain Modules (Phase 1 — Aggregate Routers)

| # | Domain | Module | Routers Consolidated | Status |
|---|--------|--------|---------------------|--------|
| 1 | **Booking** | `modules/booking/` | 2 (state machine + migration) | NEW — Unified state machine |
| 2 | **Auth** | `modules/auth/` | 3 (auth, password_reset, 2fa) | Aggregate |
| 3 | **Identity** | `modules/identity/` | 19 (agencies, RBAC, tenants, settings) | Aggregate |
| 4 | **B2B** | `modules/b2b/` | 20 (network, marketplace, exchange) | Aggregate |
| 5 | **Supplier** | `modules/supplier/` | 4 (adapters, health, ops) | Aggregate |
| 6 | **Finance** | `modules/finance/` | 25 (billing, payments, settlements) | Aggregate |
| 7 | **CRM** | `modules/crm/` | 10 (customers, deals, activities) | Aggregate |
| 8 | **Operations** | `modules/operations/` | 4 (cases, tasks, incidents) | Aggregate |
| 9 | **Enterprise** | `modules/enterprise/` | 6 (audit, approvals, governance) | Aggregate |
| 10 | **System** | `modules/system/` | 22 (health, infra, cache, monitoring) | Aggregate |
| — | Remaining | `domain_router_registry.py` | ~119 (admin, inventory, public, etc.) | Organized sections |

### Metrics
- **Before**: 234 router files, 1 flat registry, no domain boundaries
- **After Phase 1**: 10 domain modules + organized remaining sections
  - 115 routers consolidated into 10 domain aggregates
  - 119 routers in organized sections (Phase 2 candidates)
  - Registry reduced from 537 lines of imports to clear domain sections

### Phase 2 Candidates (Next Consolidation)
1. **Admin** (~25 routers) → `modules/admin/`
2. **Inventory** (~16 routers) → `modules/inventory/`
3. **Public/Storefront** (~13 routers) → `modules/public/`
4. **Marketplace/Pricing** (~11 routers) → `modules/marketplace/`
5. **Reports** (~4 routers) → `modules/reports/`

### Phase 3 (True Consolidation)
Merge individual router files into domain-level files:
- `modules/crm/router.py` replaces 10 separate files
- `modules/b2b/router.py` replaces 20 separate files
- etc.
