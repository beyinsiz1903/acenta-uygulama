# CHANGELOG — Syroce Platform

## [2026-03-26] Phase 4: Platform Maturation Program

### Faz A: CI Quality Gates & Scope Audit
- Created unified Makefile with quality gate commands
- Upgraded CI pipeline to 9 stages including architecture guard, scope audit, docs freshness
- Added coverage threshold script with kademeli enforcement (Overall ≥20%, Critical ≥30%)
- Created `tests/test_scope_audit.py` with 7 automated audit tests
- Created Quality Gates documentation at `docs/QUALITY_GATES.md`

### Faz B: Physical Router Migration
- Migrated 230 router files from `app/routers/` to `app/modules/{domain}/routers/`
- Created backward-compatible shim files using importlib module aliasing
- Updated all 16 domain module `__init__.py` imports to local paths
- Preserved 1443 routes post-migration (verified via boot test)
- Migration script: `scripts/migrate_routers.py` (with --dry-run and --verify modes)

### Faz C: Event-Driven Core + Cache Strategy
- Defined 20 domain events in `app/infrastructure/event_contracts.py`
- Created event-cache invalidation bridge (`event_cache_bridge.py`)
- Registered bridge at app startup in `api_app.py`
- Standardized all 4 dashboard endpoint TTLs via centralized `cache_ttl_config.py`
- Added `cache_delete` function to `cache_service.py` for L2 invalidation
- Created `tests/test_event_cache.py` with 8 tests (all passing)

### Faz D: Live Architecture Documentation
- Created auto-generation script `scripts/generate_arch_docs.py`
- Generated 5 architecture documents in `docs/generated/`:
  - DOMAIN_OWNERSHIP.md, ROUTER_MAP.md, EVENT_CATALOG.md, CACHE_SURFACES.md, NAVIGATION_INDEX.md
- Integrated docs freshness check into CI pipeline
- Added `make docs-generate` and `make docs-check` commands

### Bug Fixes
- Fixed missing `Request`, `write_audit_log`, `audit_snapshot` imports in `admin_b2b_marketplace.py`
- Fixed missing `datetime`, `BackgroundTasks`, `Request`, `send_email_ses`, `EmailSendError` imports in `voucher.py`
- Added docstring to `mobile` module `__init__.py`

### Files Changed/Created
- `/app/Makefile` (new)
- `/app/.github/workflows/ci.yml` (updated — 9 stages)
- `/app/docs/QUALITY_GATES.md` (new)
- `/app/docs/generated/*.md` (5 new auto-generated docs)
- `/app/backend/scripts/check_coverage_threshold.py` (new)
- `/app/backend/scripts/migrate_routers.py` (new)
- `/app/backend/scripts/generate_arch_docs.py` (new)
- `/app/backend/tests/test_scope_audit.py` (new — 7 tests)
- `/app/backend/tests/test_event_cache.py` (new — 8 tests)
- `/app/backend/app/infrastructure/event_contracts.py` (new — 20 events)
- `/app/backend/app/infrastructure/event_cache_bridge.py` (new)
- `/app/backend/app/bootstrap/api_app.py` (updated — bridge registration)
- `/app/backend/app/services/cache_service.py` (updated — cache_delete)
- `/app/backend/app/modules/*/routers/*.py` (230 files migrated)
- `/app/backend/app/modules/*/__init__.py` (16 updated imports)
- `/app/backend/app/routers/*.py` (230 shim files)
- Dashboard TTL standardization: `dashboard_admin.py`, `dashboard_agency.py`, `dashboard_hotel.py`, `dashboard_b2b.py`

---

## [2026-03-24] Phase 3 Sprint 4: Hotel & B2B Dashboards + Cmd+K
- Hotel Dashboard backend + frontend
- B2B Dashboard backend + frontend
- Cmd+K persona-based search enrichment
- Frontend hooks: useHotelDashboard, useB2BDashboard

## [2026-03-22] Phase 3 Sprint 3: Admin Dashboard
- Admin dashboard API + UI

## [2026-03-20] Phase 3 Sprint 2: Agency Dashboard
- Agency dashboard API + UI

## [2026-03-18] Phase 3 Sprint 1: Persona-Based Navigation
- Dynamic persona resolution
- Module-specific navigation configs

## [2026-03-15] Phase 2: Router & Domain Ownership Cleanup
- 160+ routers consolidated
- Architecture guard test
- Domain ownership manifest

## [2026-03-10] Phase 1: Foundation
- PRD/README reset
- Module maps
- Commercial packaging matrix
