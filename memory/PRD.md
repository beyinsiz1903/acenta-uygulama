# PRD - Acenta Master Travel Management Platform

## Original Problem Statement
Full-stack travel management (acenta) application with B2B agency management, hotel portfolio sync via Google Sheets, reservations, CRM, finance, and operations modules.

## Core Architecture
- **Frontend:** React (CRA + Tailwind + shadcn/ui)
- **Backend:** FastAPI (Python)
- **Database:** MongoDB
- **Auth:** JWT-based with role-based access control

## User Roles
- `super_admin` / `admin` - Full platform access
- `agency_admin` / `agency_agent` - B2B agency portal
- `hotel_admin` / `hotel_staff` - Hotel portal

### Deployment Fixes (Feb 27, 2026)
- **Fix:** Removed unused `serialize_doc` import from `agency_profile.py` (Ruff lint CI failure)
- **Fix:** Simplified `_db_name()` in `db.py` — removed dual-source DB name logic (DB_NAME env + MONGO_URL path extraction) that caused `INVALID_DATABASE_NAME` error during MongoDB Atlas migration (name was duplicated with comma)
- **Fix:** Removed comments from `backend/.env` to prevent deployment parser issues

## What's Been Implemented

### Google Sheets Integration (Feb 2026)
- Admin + Agency portal sheet connections
- Manual sync, sync status badges, error details

### Infrastructure (Feb 27, 2026)
- Root cleanup, seed refactoring, orphan org cleanup
- Cache warmup expansion (+agencies, hotels, FX, pricing rules)
- Seed on startup with idempotent data creation

### Per-Agency Module Management (Feb 27, 2026)
- **Backend:** GET/PUT `/api/admin/agencies/{id}/modules` — store allowed_modules per agency
- **Backend:** GET `/api/agency/profile` — agency users fetch their allowed modules
- **Admin UI:** `/app/admin/agency-modules` — checkbox grid to configure tabs per agency

### Branding Restriction (Feb 27, 2026)
- **Backend:** `can_edit_name` flag in whitelabel-settings response (true only for super_admin)
- **Frontend:** company_name input readonly for non-super_admin users

### Super Admin Unified User Management - CRUD Complete (Feb 27, 2026)
- **Backend:** GET `/api/admin/all-users` — all agency users with agency_name
- **Backend:** POST `/api/admin/all-users` — create new agency user with email, name, password, agency_id, role
- **Backend:** PUT `/api/admin/all-users/{user_id}` — update user name, email, role, status, agency_id
- **Backend:** DELETE `/api/admin/all-users/{user_id}` — hard delete user
- **Frontend:** `/app/admin/all-users` — full CRUD with search, filter, role/status management
- **Frontend:** Create user dialog (name, email, password, agency, role fields)
- **Frontend:** Edit user dialog (name, email, agency, role, status fields)
- **Frontend:** Delete user confirmation dialog (hard delete)
- **Sidebar:** "Kullanici Yonetimi" link under YONETIM

### Dynamic Agency Navigation (Feb 27, 2026)
- AppShell fetches `/api/agency/profile` for agency users
- Sidebar items filtered by `allowed_modules` modeKey matching
- Empty allowed_modules = no restriction (all visible)

### DB Index Cleanup (Feb 27, 2026)
- `_safe_create` now uses OperationFailure error codes (85, 86, 13) instead of string matching
- Removed bare `except Exception` that silently swallowed all errors

### Cache Warm-up Expansion (Feb 27, 2026)
- Added: product_counts, reservation_summary, agency_modules, onboarding state
- Total warm-up sources: tenant features, CMS nav, campaigns, agencies, hotels, FX rates, pricing rules, product counts, reservation summaries, agency module settings, onboarding state

## Key Files
- `backend/app/routers/admin_agency_users.py` - Per-agency user CRUD + all_users_router (GET/POST/PUT/DELETE)
- `backend/app/routers/admin_agencies.py` - Agency CRUD + module management
- `backend/app/routers/agency_profile.py` - Agency profile endpoint
- `backend/app/indexes/seed_indexes.py` - Consolidated DB indexes
- `backend/app/services/cache_warmup.py` - Startup cache warm-up
- `frontend/src/pages/AdminAllUsersPage.jsx` - Unified user management UI with CRUD dialogs
- `frontend/src/pages/AdminAgencyModulesPage.jsx` - Module config UI
- `frontend/src/components/AppShell.jsx` - Sidebar with dynamic agency module filtering

## Key API Endpoints
- `GET /api/admin/all-users` - List all agency users across agencies
- `POST /api/admin/all-users` - Create new agency user
- `PUT /api/admin/all-users/{user_id}` - Update agency user
- `DELETE /api/admin/all-users/{user_id}` - Delete agency user
- `GET /api/me/modules` - Agency user's allowed modules

## Credentials
| Portal | Email | Password | Role |
|--------|-------|----------|------|
| Admin | admin@acenta.test | admin123 | Super Admin |
| Agency | agent@acenta.test | agent123 | Agency Admin |

## Backlog
- P2: Apple Watch UI
- P2: Google Sheets sync testing (requires Service Account JSON)

### Bug Fix: React Error #31 - {tr, en} Object Rendering (Feb 28, 2026)
- **Root cause:** `dashboard/popular-products` API returned `product_name` as `{tr: "...", en: "..."}` object from MongoDB. DashboardPage.jsx rendered this directly in a `<p>` tag, crashing the entire React tree.
- **Backend fix:** Added `_str_name()` helper in `dashboard_enhanced.py` to flatten multilingual objects to strings. Applied to all `product_name`, `hotel_name`, `tour_name` fields across `popular-products`, `reservation-widgets`, and abandoned data endpoints.
- **Frontend fix:** Added `safeName()` utility in `formatters.js`. Applied as defense-in-depth across: DashboardPage, AdminAgenciesPage (+ Dialog moved out of TableRow), AdminAllUsersPage, AdminAgencyContractsPage, AdminAgencyModulesPage, AdminAgencyUsersPage, AdminHotelsPage.
- **Status:** FIXED & TESTED — both `/app` (dashboard) and `/app/admin/agencies` verified with zero console errors.

## Enterprise SaaS Audit Update (Mar 6, 2026)

### Scope Completed
- Web/bulut SaaS repository audited against enterprise SaaS requirements: backend architecture, frontend architecture, tenancy, security, API design, billing, observability, database/indexing, testing, DevOps, and scalability.
- Mobile repository cloned and audited after web platform review; cross-platform integration risks identified.
- Smoke verification completed: web login, admin agencies page, dashboard render, and core backend auth/admin/dashboard endpoints.

### Current Architecture Snapshot
- **Backend reality:** very large FastAPI modular monolith with `server.py` as central composition root (~800 lines), 186 router files, 168 service files, 25 repositories, and 119 backend tests.
- **Frontend reality:** CRA + React Router app with a very large route registry in `frontend/src/App.js` (500+ lines), 161 page files, partial TanStack Query adoption, and mostly page-local API calls.
- **Mobile reality:** Expo Router app with a thin FastAPI proxy backend. Mobile backend hardcodes remote web API base and provides hybrid remote+local demo behavior.

### P0 Production Blockers Identified
- `backend/app/auth.py` uses fallback JWT secret (`dev_jwt_secret_change_me`) instead of fail-fast secret loading.
- `backend/app/db.py` and `backend/app/config.py` still allow production-unsafe fallbacks for Mongo/CORS/env-sensitive settings.
- `backend/server.py` is overloaded with router registration, startup jobs, and operational concerns in one file.
- Tenant isolation is inconsistent: middleware resolves tenant context, but many routers still query collections directly.
- Mobile backend (`/tmp/acenta-mobil/backend/server.py`) hardcodes `REMOTE_API = "https://agency.syroce.com"`.
- Mobile frontend calls endpoints such as `/api/bookings` and `/api/reports/summary`, but mobile backend does not implement them.

### P1 Refactor Priorities
- Introduce bounded-context module structure: `core`, `auth`, `tenancy`, `billing`, `bookings`, `crm`, `reports`, `integrations`, `ops`.
- Standardize tenant-aware repositories and remove direct collection access from routers.
- Replace localStorage/web token handling and AsyncStorage/mobile token handling with hardened session/token strategy.
- Move plan/features/quotas to a single canonical entitlement model and remove legacy dual-write drift.
- Split frontend into feature folders with route modules, shared query keys, and standardized form/mutation patterns.

### P2 Strategic Roadmap
- Build 30/60/90 day execution plan around security hardening, tenancy enforcement, platform observability, billing maturity, and mobile/API convergence.
- After platform stabilization, evaluate compact/mobile-first companion experiences and Apple Watch backlog separately.

### PR-1 Implemented (Mar 6, 2026)
- **CI baseline hardened:** removed fake-green `|| true` behavior from backend test and frontend lint jobs in `.github/workflows/ci.yml`. Because the legacy full backend suite is not yet Sprint-1 clean, backend blocking CI was intentionally narrowed to the verified auth/security subset (`test_auth_jwt_and_org_context`, `test_jwt_revocation`, `test_rate_limiting`, `test_security_headers`, `test_stripe_webhook_b2c_side_effects`) instead of silently ignoring failures.
- **Config hardening:** added fail-fast `require_env()` / `MissingRequiredEnv` in `backend/app/config.py`; removed JWT and Mongo fallbacks in `backend/app/auth.py` and `backend/app/db.py`.
- **JWT boot safety:** created `backend/app/security/jwt_config.py` and enforced `require_jwt_secret()` during backend startup from `server.py` so missing `JWT_SECRET` now prevents boot.
- **Webhook hardening:** `backend/app/routers/billing_webhooks.py` now rejects requests when `STRIPE_WEBHOOK_SECRET` is not configured and no longer accepts unsigned fallback payload parsing.
- **Test harness hardening:** updated `backend/tests/conftest.py` and relevant auth/webhook tests so local/CI test environments explicitly provide required env vars.
- **Operational note:** full frontend build still surfaces legacy CRA/ESLint warnings from unrelated pages; blocking frontend lint in CI was narrowed to stable auth/core files (`src/lib/api.js`, `src/hooks/useAuth.js`, `src/components/RequireAuth.jsx`, `src/pages/LoginPage.jsx`, `src/index.js`) to avoid fake-green behavior while keeping PR-1 scope controlled.
- **Smoke result:** backend restart successful; external smoke verified `/api/auth/login`, `/api/auth/me`, `/api/admin/agencies`, and `/api/webhook/stripe-billing` reject behavior (503 without secret). Web login flow and admin agencies page remained stable.

### PR-2 Implemented (Mar 6, 2026)
- **Session model added:** created `backend/app/repositories/session_repository.py` and `backend/app/services/session_service.py`. Login now creates a persistent session record and access tokens issued from `/api/auth/login` include `sid` in addition to `jti`.
- **Access token validation hardened:** `backend/app/auth.py` now checks session state when `sid` is present. Revoked sessions immediately invalidate their access tokens. Legacy tokens without `sid` are still accepted as a temporary compatibility path until frontend auth compat work (PR-4).
- **Refresh rotation hardened:** created `backend/app/services/refresh_token_crypto.py`; refresh tokens are now opaque client tokens with `token_hash` stored server-side, linked to `session_id` + `family_id`. Reuse detection revokes the family and associated session.
- **Revocation fixed:** `/api/auth/logout` now revokes the current session and its refresh tokens; `/api/auth/revoke-all-sessions` now revokes all active sessions plus all refresh tokens for the user. `/api/auth/sessions` and `/api/auth/sessions/{session_id}/revoke` now operate on the new sessions collection.
- **Indexes:** added session indexes in `seed_indexes.py` and startup session index creation in `server.py`. Refresh token unique index was changed to partial-on-string `token_hash` to avoid startup warnings from legacy documents with `null` token hashes.
- **Testing:** added `backend/tests/test_auth_session_model.py` and expanded `test_jwt_revocation.py` for `sid`, session revocation, revoke-all invalidation, and refresh reuse detection. Targeted backend test groups passed.
- **Smoke result:** external verification passed for login, session listing, refresh rotation, reuse rejection (401), revoke-all invalidation, `/api/auth/me`, and `/api/admin/agencies`. Web login/navigation stayed stable, but frontend refresh-token persistence / cookie-based auth migration remains pending future PRs.

### PR-3 Implemented (Mar 6, 2026)
- **Tenant-bound login:** `backend/app/services/login_context_service.py`, `backend/app/repositories/tenant_repository.py`, and `backend/app/repositories/tenant_membership_repository.py` added. `/api/auth/login` now supports explicit `tenant_id` / `tenant_slug` and resolves login through tenant membership or tightly controlled admin fallback. Duplicate-email cross-tenant logins without tenant context are rejected.
- **Middleware hardening:** `backend/app/middleware/tenant_middleware.py` now treats `X-Tenant-Id` as a request hint, not a trust source. Non-super-admin users must have an active membership for the requested tenant. Middleware now records `tenant_source` + `allowed_tenant_ids` in `RequestContext`.
- **Canonical scope direction:** `RequestContext` and `base_repository.py` were updated to carry tenant-aware scope and a new `with_tenant_filter()` guardrail helper. This starts the move toward `tenant_id` as the canonical partition key while preserving a short-lived legacy fallback for documents that do not yet store `tenant_id`.
- **Pilot tenant guardrails:** `admin_agencies.py`, `admin_agency_users.py`, and `tenant_features.py` now apply pilot tenant-safe filters. New agency/user records written by these flows now store `tenant_id`. Reads use a temporary legacy-compatible tenant filter so old documents remain visible during migration.
- **Seed/test data alignment:** `seed.py` and `tests/conftest.py` now create a default tenant plus memberships for seeded admin/agency demo users so tenant-bound login works in preview and isolated test databases.
- **Testing:** added `backend/tests/test_auth_tenant_binding.py` and `backend/tests/test_tenant_isolation_admin_agencies.py`. Targeted test groups for tenant-bound login, session regressions, tenant features, security headers, rate limiting, and webhook security passed.
- **Operational note:** some older legacy tests (e.g. portions of `test_b2b_pro_v1.py`) still encode pre-existing assumptions about `admin` aliasing and raw `detail` response shapes. Those were not expanded into this PR’s blocking gate to keep PR-3 scoped to tenancy/login hardening.
- **Smoke result:** deployed preview verified both `admin@acenta.test` and `agent@acenta.test` login successfully, with stable redirects, tenant id persistence, and no auth/tenant regressions on `/api/auth/me` and `/api/admin/agencies`.

### PR-4 Implemented (Mar 6, 2026)
- **Web auth compat layer:** `frontend/src/lib/authSession.js` and `frontend/src/lib/cookieAuthCompat.js` added. Web auth state now prefers cookie/bootstrap flow while preserving short-term bearer fallback compatibility.
- **Backend cookie compat contract:** `backend/app/routers/auth.py`, `backend/app/auth.py`, and `backend/app/config.py` now support `X-Client-Platform: web` cookie transport. `/api/auth/login` and `/api/auth/refresh` set httpOnly access/refresh cookies for web requests, still return legacy-compatible body tokens, and expose `auth_transport` / `X-Auth-Transport` so web vs legacy/mobile handling is explicit.
- **Session bootstrap direction:** `/api/auth/me` now works with cookie auth (no Authorization header required) and sensitive fields are sanitized before response. `/api/auth/logout` and `/api/auth/revoke-all-sessions` clear auth cookies alongside session revocation.
- **Frontend auth centralization:** `frontend/src/lib/api.js`, `frontend/src/hooks/useAuth.js`, `frontend/src/components/RequireAuth.jsx`, and `frontend/src/pages/LoginPage.jsx` were updated so login, reload bootstrap, refresh fallback, logout, and route protection all flow through the new compat layer instead of localStorage-first assumptions.
- **Testing:** added `backend/tests/test_auth_web_cookie_compat.py`; testing agent also added `backend/tests/test_web_auth_cookie_compat_comprehensive.py`. Targeted pytest for auth/session/tenant/cookie suites passed, preview curl verification passed for login/me/refresh/logout cookie flows, and frontend smoke + dedicated frontend/backend testing agents passed.
- **Scope guard:** this PR is intentionally not a full cookie migration. Legacy bearer path remains available for mobile and short-lived fallback while web source-of-truth shifts toward cookie + bootstrap.

### PR-5A Implemented (Mar 6, 2026)
- **Scope split accepted:** mobile repo was not available in the workspace, so PR-5 was intentionally split into **PR-5A backend Mobile BFF** and future **PR-5B mobile SecureStore/bootstrap** work.
- **Mobile BFF module added:** `backend/app/modules/mobile/` created with `router.py`, `service.py`, `schemas.py`, `__init__.py`, and `mobile_contract.md`.
- **New endpoints:** mounted at `/api/v1/mobile` via `server.py`.
  - `GET /api/v1/mobile/auth/me`
  - `GET /api/v1/mobile/dashboard/summary`
  - `GET /api/v1/mobile/bookings`
  - `GET /api/v1/mobile/bookings/{id}`
  - `POST /api/v1/mobile/bookings`
  - `GET /api/v1/mobile/reports/summary`
- **Thin orchestration rule preserved:** mobile booking creation delegates to existing `booking_service.create_booking_draft()`; mobile layer owns projection/DTO shaping, not business logic.
- **DTO safety:** mobile schemas are separate from web DTOs, sensitive fields are not exposed, and Mongo `_id` is never returned in mobile responses.
- **Tenant guardrails:** mobile reads use request context tenant scoping; booking drafts created through mobile BFF now persist `tenant_id` and mobile-friendly optional metadata via `BookingRepository` updates.
- **Testing:** added `backend/tests/test_mobile_bff_contracts.py`. Testing agent also added preview contract coverage. Internal pytest, external preview API verification, and backend deep testing all passed with no auth regressions.
- **Re-validation on current fork:** `pytest backend/tests/test_mobile_bff_contracts.py -q` re-run passed (`5 passed`), confirming PR-5A contract stability before PR-6 planning.
- **Blocked follow-up:** PR-5B remains pending until mobile repo is attached. That phase will cover SecureStore migration, session bootstrap, refresh persistence, and mobile app adoption of these new endpoints.

### PR-5B Prep Added (Mar 6, 2026)
- Added `backend/app/modules/mobile/pr5b_integration_checklist.md` as a short, implementation-ready handoff for the mobile team.
- Checklist scope intentionally stays narrow: SecureStore migration, session bootstrap, login/refresh/logout behavior, and adoption of `/api/v1/mobile/*` endpoints without proposing a new mobile architecture.
- This prep is intended to let PR-6 proceed immediately while keeping PR-5B integration predictable once the mobile repo is attached.

### PR-6 Implemented (Mar 6, 2026)
- **Runtime composition refactor:** extracted API composition from `server.py` into `backend/app/bootstrap/api_app.py` while keeping `backend/server.py` as a thin compat wrapper so `server:app` continues to work.
- **Controlled bootstrap split:** added `backend/app/bootstrap/router_registry.py`, `middleware_setup.py`, and `runtime_init.py` to isolate router registration, middleware chain, and startup/runtime initialization without changing auth/session/tenant or Mobile BFF business behavior.
- **Dedicated runtime entrypoints:** added `backend/app/bootstrap/worker_app.py` and `scheduler_app.py` for background loops and periodic schedulers. API runtime no longer starts worker/scheduler loops directly.
- **Behavioral guardrail:** auth, session validation, tenant binding, and `/api/v1/mobile/*` contract were preserved; this PR is composition-only refactor, not an auth or tenancy rewrite.
- **Validation:** internal smoke passed for `/health` and `/`; preview login + `/api/auth/me` + `/api/v1/mobile/auth/me` + mobile bookings/reports endpoints passed; targeted pytest passed for `test_mobile_bff_contracts.py`, `test_auth_session_model.py`, and `test_auth_tenant_binding.py`.
- **Operational note:** dedicated worker/scheduler entrypoints were process-start verified, but preview supervisor wiring for these new processes is not part of this PR.

### Mobile Cutover Runbook Added (Mar 6, 2026)
- Added `backend/app/modules/mobile/mobile_cutover_runbook.md` as a short operational handoff covering preconditions, mobile build version, SecureStore migration, endpoint switch, rollout, monitoring, and rollback.
- Runbook is intentionally one-page and follows PR-5A contract + PR-5B migration scope only; it does not introduce a new mobile architecture.

### Runtime Ops + Dedicated Runtime Wiring Added (Mar 6, 2026)
- Added `backend/app/bootstrap/runtime_ops.md` as the short operational source of truth for runtime overview, entrypoints, process responsibilities, local commands, preview/staging/prod run approach, health checks, smoke checklist, rollback, and the `server:app` compat note.
- Added runtime health/ops wiring with `backend/app/bootstrap/runtime_health.py` so dedicated `worker` and `scheduler` runtimes emit heartbeat files and respond gracefully to `SIGTERM` / `SIGINT`.
- Added executable runtime entry scripts: `backend/scripts/run_api_runtime.sh`, `backend/scripts/run_worker_runtime.sh`, `backend/scripts/run_scheduler_runtime.sh`.
- Added `backend/scripts/check_runtime_health.py` for non-HTTP worker/scheduler health verification using heartbeat freshness.
- Strengthened `worker_app.py` and `scheduler_app.py` with explicit runtime component manifests, heartbeat updates, and controlled shutdown behavior.
- Added `backend/tests/test_runtime_wiring.py`; targeted pytest, ingress/auth/mobile curl smoke, temporary worker/scheduler process smoke, and backend deep testing all passed.

### Backend Ruff Cleanup (Mar 6, 2026)
- Cleaned backend lint blockers with scope-limited, behavior-preserving fixes only: unused locals/imports, constant f-strings, truthy assert style, dead unreachable test code, and missing trailing newline in `app/services/session_service.py`.
- `ruff` now passes for `/app/backend`.
- Revalidated with targeted pytest (`test_runtime_wiring.py`, `test_auth_session_model.py`, `test_auth_tenant_binding.py`, `test_mobile_bff_contracts.py`) plus preview curl smoke on `/api/health`, `/api/auth/me`, and `/api/v1/mobile/auth/me`.

### Backend Ruff Cleanup — Full Sweep (Mar 6, 2026)
- Completed the remaining backend-wide Ruff cleanup after CI still reported stale/extra issues beyond the first pass.
- Applied safe auto-fixes plus small manual whitespace/import/export corrections across backend app, scripts, and tests; restored `backend/server.py` compat export via `__all__ = ["app"]` so lint cleanliness did not break `server:app` usage.
- Verified with exact command `ruff check /app/backend --output-format concise` (clean), targeted pytest reruns, and preview auth/mobile smoke.

### Auth Test Harness Compatibility Fix (Mar 6, 2026)
- Fixed CI failure in `backend/tests/test_auth_jwt_and_org_context.py::test_get_current_org_403_when_user_has_no_org` by passing a minimal Starlette `Request` object into the direct `get_current_user(...)` test call.
- This was a test-only compatibility update after auth dependency signature evolution; no application behavior or auth business logic was changed.
- Revalidated with targeted auth pytest (`test_auth_jwt_and_org_context.py`, `test_auth_session_model.py`, `test_auth_tenant_binding.py`) and preview smoke on `/api/health`, `/api/auth/me`, `/api/v1/mobile/auth/me`.

### CI Exit Gate Test Harness Fixes (Mar 6, 2026)
- Updated `backend/tests/test_api_org_isolation_bookings.py` to seed tenant + membership records and send `X-Tenant-Id`, aligning the test with the post-PR-3 tenant hardening rules instead of pre-hardening assumptions.
- Cleaned `backend/tests/test_mobile_bff_preview_api.py` by removing the no-op `pytest.mark.usefixtures()` usage and the non-`None` test return path that produced pytest warnings in CI.
- Added a shared preview admin auth fixture in `test_mobile_bff_preview_api.py` to reduce repeated login churn during preview-facing test execution.
- Validation passed via targeted pytest (`test_api_org_isolation_bookings.py`, `test_mobile_bff_preview_api.py -k requires_auth`), smoke on `/api/health`, `/api/auth/me`, `/api/v1/mobile/auth/me`, and backend deep testing.

### Preview Auth Helper Hardening (Mar 6, 2026)
- Added `backend/tests/preview_auth_helper.py` as a small, isolated preview-external test helper with shared auth cache, short TTL, explicit invalidation, tenant-aware login support, refresh/login fallback, and a local ASGI bootstrap fallback for preview login rate-limit scenarios.
- Migrated preview-facing external HTTP tests to the helper where relevant: `test_mobile_bff_preview_api.py`, `test_admin_all_users_crud.py`, `test_agency_modules_and_branding.py`, `test_admin_all_users_and_agency_nav.py`, and `test_agency_sheets_api.py`.
- Added narrow guards in `backend/tests/conftest.py` so local DB seeding/index fixtures do not create avoidable flakiness for preview-only external HTTP tests.
- Validation passed for: `test_mobile_bff_preview_api.py`, `test_agency_sheets_api.py`, `test_admin_all_users_crud.py`, `test_agency_modules_and_branding.py`, `test_admin_all_users_and_agency_nav.py`, and `test_api_org_isolation_bookings.py`, plus helper smoke against preview `/api/health` and `/api/auth/me`.

## Current Priority Backlog
- **P0:** PR-5B — Mobile Secure Session + Session Bootstrap (requires mobile repo; checklist ready at `backend/app/modules/mobile/pr5b_integration_checklist.md`)
- **P1:** Environment-specific process-manager attachment of the new runtime scripts (`run_api_runtime.sh`, `run_worker_runtime.sh`, `run_scheduler_runtime.sh`) wherever preview/staging/prod infra definitions live
- **P1:** PR-7 — Web Active Devices / Sessions screen
- **P1:** Web auth follow-up cleanup after compat window closes (remove remaining localStorage fallback paths page-by-page)
- **P1:** Cleanup PR for non-blocking preview issues: `/api/partner-graph/notifications/summary`, `/api/tenant/features`, `/api/tenant/quota-status`
- **P1:** API versioning rollout (`/api/v1/*`) and compat adapters
- **P2:** Entitlement/billing unification, observability stack, broader frontend modular refactor
