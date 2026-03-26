# PRD — Syroce: Acenta Bulut Otomasyon Platformu

## Problem Statement
Tur, otel, uçak ve B2B satış yapan acenteler için modüler bir bulut otomasyon platformu. Sistem persona bazlı UI routing, domain-driven backend mimarisi ve çok kiracılı (multi-tenant) yapıda çalışır.

## User Personas
- **Super Admin**: Tüm sistemi yöneten platform admini
- **Agency Admin**: Acenta operasyonlarını yöneten kullanıcı
- **Hotel Manager**: Otel operasyonlarını takip eden kullanıcı
- **B2B Partner**: B2B kanalı üzerinden işlem yapan partner

## Core Architecture
- **Frontend**: React 18 + React Router v6 + Tailwind + Shadcn/UI
- **Backend**: FastAPI + MongoDB + Redis (optional)
- **Auth**: JWT-based, role-based access control
- **Structure**: Domain-Driven Design (DDD) with bounded contexts

## Implemented Phases

### Phase 1 — Foundation (Complete)
- PRD/README reset, module maps, commercial packaging matrix

### Phase 2 — Router & Domain Cleanup (Complete)
- 160+ routers consolidated into domain modules
- Architecture guard + domain ownership manifest

### Phase 3 — Persona-Based UI & Dashboards (Complete)
- Sprint 1: Persona-based navigation
- Sprint 2: Agency dashboard
- Sprint 3: Admin dashboard
- Sprint 4: Hotel & B2B dashboards, Cmd+K enrichment

### Phase 4 — Platform Maturation Program (Complete)
#### Faz A: CI Quality Gates & Scope Audit
- CI pipeline: 9 stages (lint, architecture guard, scope audit, backend tests, coverage, frontend build, contract tests, docs freshness, quality summary)
- Makefile: `make quality`, `make lint`, `make test-guard`, `make docs-check`
- Coverage threshold: Overall ≥20%, Critical ≥30% (kademeli artırılacak)
- Scope audit: 7 test (router ownership, orphan detection, duplicate ownership, registry count, docstring, domain existence, service layer)

#### Faz B: Physical Router Migration
- 230 router files moved from `app/routers/` → `app/modules/{domain}/routers/`
- Backward-compatible shim files at old locations (importlib aliasing)
- Module `__init__.py` imports updated to local paths
- 1443 routes verified post-migration

#### Faz C: Event-Driven Core + Cache Strategy
- 20 domain events defined in `event_contracts.py`
- Event-cache invalidation bridge registered at startup
- Dashboard endpoints use centralized TTL from `cache_ttl_config.py`
- Cache invalidation matrix: event → cache prefix mapping

#### Faz D: Live Architecture Documentation
- Auto-generated docs: DOMAIN_OWNERSHIP, ROUTER_MAP, EVENT_CATALOG, CACHE_SURFACES, NAVIGATION_INDEX
- Freshness check: `python scripts/generate_arch_docs.py --check`
- CI-integrated docs staleness gate

## Key API Endpoints
- `POST /api/auth/login` — Authentication
- `GET /api/dashboard/admin-today` — Admin dashboard
- `GET /api/dashboard/agency-today` — Agency dashboard
- `GET /api/dashboard/hotel-today` — Hotel dashboard
- `GET /api/dashboard/b2b-today` — B2B dashboard
- `GET /api/health` — Health check

## DB Schema (Key Collections)
- `users`: {email, password_hash, active, roles}
- `tenants`: {name, slug}
- `memberships`: Links users to tenants with roles
- `reservations`, `ops_incidents`, `audit_logs`: Dashboard aggregate sources

## 3rd Party Integrations
- Stripe (Payments) — MOCKED in preview
- Redis (Cache L1) — Optional, graceful degradation
- Celery (Background Tasks)

## Test Credentials
- Super Admin: `admin@acenta.test` / `Admin123!@#`
- Agency Admin: `agency1@demo.test` / `Agency123!@#`

## Known Issues
- 4 orphan routers (soft warning, not blocking)
- 14 service-layer FastAPI imports (gradual enforcement)
- React Router v7 future flag warnings (console only)
