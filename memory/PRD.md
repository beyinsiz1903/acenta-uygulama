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

### Preview Supervisor Runtime Attachment (Mar 6, 2026)
- Added preview process-manager wiring at `/etc/supervisor/conf.d/acenta_dedicated_runtimes.conf` so `backend-worker` and `backend-scheduler` now run as dedicated supervisor-managed services alongside the existing API process.
- Hardened runtime launch scripts (`backend/scripts/run_api_runtime.sh`, `run_worker_runtime.sh`, `run_scheduler_runtime.sh`) to use the project virtualenv binaries by default, preventing supervisor from starting worker/scheduler with the wrong Python interpreter.
- Smoke validation passed for supervisor process status, worker/scheduler heartbeat freshness, `/api/health`, `/api/auth/login`, `/api/auth/me`, `/api/v1/mobile/auth/me`, and web admin login redirect.
- Deferred admin optional endpoint errors (`/api/partner-graph/notifications/summary`, `/api/tenant/features`, `/api/tenant/quota-status`) were intentionally left untouched in this scoped runtime task.

### PR-7 Implemented — Web Active Sessions / Active Devices (Mar 6, 2026)
- Added new web route `/app/settings/security` with `frontend/src/pages/SettingsSecurityPage.jsx` to surface session hardening to users without changing backend auth/session business logic.
- Added small session-focused UI modules: `frontend/src/components/settings/SettingsSectionNav.jsx`, `SessionCard.jsx`, `SessionRevokeDialog.jsx`, and helper `frontend/src/lib/sessionSecurity.js` for device/user-agent labeling plus timestamp formatting.
- Screen uses the existing backend contracts only: `GET /api/auth/sessions`, `POST /api/auth/sessions/{session_id}/revoke`, and `GET /api/auth/me` for current session highlighting.
- UX delivered per scope: active sessions list, device/user-agent/IP/created-at/last-active display, current-session badge, safe confirmation modal, single-session revoke, “other all sessions” revoke, loading/error states, and post-action refresh.
- Settings IA updated with a lightweight section nav between security and users; sidebar “Ayarlar” now lands on the new security page while existing `/app/settings` user-management page remains available.
- Found and fixed a frontend-only regression during smoke testing: bulk revoke was initially firing all revoke calls in parallel, which caused partial completion under load. Updated the “other all sessions” action to revoke sequentially for reliable completion while keeping the same backend endpoints.
- Validation passed via frontend/browser smoke: login → `/app/settings/security`, current-session modal cancel, single remote session revoke, bulk revoke of remaining sessions, final counts (`total=1`, `current=1`, `other=0`), plus backend/API session revoke curl verification.

### PR-8 Implemented — Web Auth Compat Cleanup (Mar 6, 2026)
- Removed all frontend `localStorage` auth token and refresh token persistence from the web app. Web auth source of truth is now `httpOnly` cookies + `/api/auth/me` bootstrap.
- Updated `frontend/src/lib/api.js` and `frontend/src/lib/cookieAuthCompat.js` so web requests always use `withCredentials`, never inject bearer tokens from storage, and refresh through cookie-based `/api/auth/refresh` retry logic.
- Updated login-adjacent flows (`LoginPage`, `B2BLoginPage`, `SignupPage`) and legacy token-touching pages (`AdminPilotDashboardPage`, `AgencyBookingConfirmedPage`, `AiAssistant`) to use cookie session behavior instead of reading/storing tokens.
- Validation passed via external curl smoke (`/api/auth/login`, `/api/auth/me`, `/api/auth/logout`), browser smoke on `/login`, testing report `/app/test_reports/iteration_15.json`, plus dedicated frontend/backend sanity agents.

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

### PR-8 Verified — Web Cookie Auth Cleanup (Mar 7, 2026)
- Verified on preview `https://travel-saas-refactor-1.preview.emergentagent.com` with browser smoke, external curl checks, and dedicated frontend automation.
- Admin flow passed: `/login` -> protected area redirect, refresh persistence via `/api/auth/me`, logout redirect, and protected-route guard after logout.
- B2B flow passed: `/b2b/login` -> `/b2b/bookings` redirect, refresh persistence, and authenticated `/api/b2b/me` access.
- Critical security verification passed: no `access_token`, `refresh_token`, or bearer token data persisted in browser `localStorage`; web auth is operating through cookie session transport (`auth_transport: cookie_compat`).
- Remaining auth-adjacent note: B2B logout button selector is less automation-friendly, but no functional auth regression was found.

## `/api/v1` Standardization Plan (Mar 7, 2026)

### Planning Guardrails
- This is a **repo-specific migration plan**, not a greenfield API design.
- Auth/session/tenant behavior must remain unchanged while routes are standardized.
- Existing `mobile` contract at `/api/v1/mobile/*` is the reference point; do **not** churn that contract while the mobile repo is still detached.
- Versioning work must be **namespace-only first**. No entitlement logic, billing semantics, or observability payload redesign should be mixed into the same PRs.
- Before the first implementation PR, `backend/app/bootstrap/router_registry.py` must be cleaned so `auth_router` is not mounted twice. Exact duplicate route registration exists today for `/api/auth/*`.

### 1. Hedef Namespace Yapısı

#### 1.1 Proposed target structure
- **Shared platform / authenticated core**
  - `/api/v1/auth/*`
  - `/api/v1/settings/*`
  - `/api/v1/tenants/*` (only where tenant objects are the resource)
  - `/api/v1/system/*`, `/api/v1/health/*`
- **Web SPA-facing namespaces**
  - `/api/v1/admin/*`
  - `/api/v1/agency/*`
  - `/api/v1/b2b/*`
  - `/api/v1/crm/*`
  - `/api/v1/ops/*`
  - `/api/v1/reports/*`, `/api/v1/dashboard/*`, `/api/v1/notifications/*`
- **Mobile BFF**
  - `/api/v1/mobile/*` (already live; keep as-is)
- **Public / anonymous / storefront**
  - `/api/v1/public/*`
  - `/api/v1/storefront/*`
- **Partner / external API**
  - `/api/v1/partner/*`
- **Integrations / callbacks / machine-to-machine**
  - `/api/v1/webhooks/*`
  - `/api/v1/integrations/*`

#### 1.2 Normalization rules
- Keep `/api` as the ingress root; add version after it: `/api/v1/...`.
- Do **not** move tenant identity into the URL path right now. Keep `X-Tenant-Id` + middleware-driven `RequestContext` as the canonical tenant mechanism.
- Do **not** split auth into separate web/mobile login URLs yet. Web keeps cookie transport via `X-Client-Platform: web`; mobile keeps bearer-style usage.
- Keep public and partner APIs separate from web namespaces even if they reuse the same services.

### 2. Mevcut Router Envanteri

#### 2.1 Current repo reality
- `backend/app/routers/`: **186** router files
- `backend/app/modules/mobile/router.py`: **1** active `/api/v1/*` router module
- Current route style is mixed:
  1. **Prefix already includes `/api/...`**: `auth`, `admin_*`, `agency_*`, `b2b_*`, `public_*`, `partner_v1`, `settings`, `tenant_features`, `reports`, etc.
  2. **Router has bare prefix and composition adds `API_PREFIX`** in `router_registry.py`: `bookings`, `payments`, `products`, `pricing`, `pricing_rules`, `reservations`, `marketplace`, `suppliers`, `search`, `finance`, `web_booking`, `web_catalog`.
  3. **No router prefix; full paths are hardcoded on decorators**: `billing_webhooks.py`, `theme.py`, `upgrade_requests.py` (and similar legacy-style files).
  4. **Already versioned**: `modules/mobile/router.py` mounted at `/api/v1/mobile/*`.

#### 2.2 Current group inventory (high-level)
- **Admin:** ~55 router files (`admin_*` family)
- **Agency:** 7 router files (`agency_*`)
- **B2B:** 12 router files (`b2b_*`)
- **CRM:** 8 router files (`crm_*`)
- **Ops:** 7 router files (`ops_*`)
- **Partner/Public/Web-facing:** public checkout/search/my-booking/storefront/web booking/catalog/partner + onboarding/payment surface
- **Catalog / booking / pricing / reservations core:** products, bookings, pricing, pricing_rules, reservations, marketplace, suppliers, inventory, payments, reports

#### 2.3 Known route-shape irregularities that matter for v1
- `auth_router` is included twice in `backend/app/bootstrap/router_registry.py`, so `/api/auth/*` currently has duplicate route registration.
- `payments.py`, `products.py`, `pricing.py`, `reservations.py`, `marketplace.py`, `search.py`, `finance.py`, `suppliers.py`, `web_booking.py`, `web_catalog.py` rely on registry-time prefix composition instead of fully declaring final paths in the router file.
- `theme.py`, `billing_webhooks.py`, and `upgrade_requests.py` are harder to standardize because they embed full legacy paths directly on decorators.
- Error payloads are mostly standardized globally, but some routers still return legacy/raw shapes or raise raw `HTTPException` strings.

### 3. Low-Risk -> High-Risk Migration Sırası

| Order | Risk | Router groups |
|---|---|---|
| 0 | Low-Med | Versioning foundation, registry cleanup, deprecation headers, route manifest |
| 1 | Low | Health/system/read-only public metadata (`health`, `health_dashboard`, `theme`, public CMS/campaign/theme-like surfaces) |
| 2 | Low-Med | Shared auth-adjacent read surfaces (`settings`, password reset metadata, session reads) |
| 3 | Medium | Agency/B2B read-first surfaces and dashboard/report reads |
| 4 | Medium | Admin read-first surfaces (`admin/agencies`, `admin/all-users`, reports/analytics reads) |
| 5 | Medium-High | Core booking/catalog/pricing write surfaces |
| 6 | High | Public checkout + partner API + payments/webhooks/integrations |
| 7 | High | Legacy hardcoded-path routers + compat removal |

#### Why this order fits this repo
- Low-risk groups are mostly **read-heavy** and have fewer external consumers.
- The most sensitive groups (`auth`, `public checkout`, `partner`, `payments`, `webhooks`) sit behind already-hardening work and should not be mixed with namespace experimentation early.
- `mobile` is already on `/api/v1/mobile/*`, so it should be treated as an anchor, not a migration target.

### 4. Compat Period Süresi ve Kaldırma Kriterleri

#### 4.1 Proposed compat period
- **Minimum:** 45 days **or** 2 production release cycles, whichever is longer.
- During this window, both legacy and v1 endpoints stay live for migrated router groups.

#### 4.2 Removal criteria for legacy paths
Legacy `/api/...` aliases can be removed only when **all** are true:
- Web SPA calls for the migrated group are moved to `/api/v1/...`.
- Mobile BFF is unaffected or explicitly validated.
- Partner/public consumers for that group are inventoried and notified (if applicable).
- Legacy traffic for that group falls below **1% for 14 consecutive days**.
- Smoke suite + targeted pytest for the group are green in preview/staging.
- No open Sev-1 / Sev-2 incidents linked to the migrated namespace.

#### 4.3 Compat behavior during the window
- Legacy routes return the same payloads they return today.
- v1 routes return the standardized error envelope and normalized response conventions.
- Add response headers on legacy aliases:
  - `Deprecation: true`
  - `Sunset: <RFC date>`
  - `Link: <.../api/v1/...>; rel="successor-version"`

### 5. Compat Adapter Planı

#### 5.1 Core principle
- **No business-logic forks.** Versioning should wrap the same services/use-cases, not duplicate domain logic.

#### 5.2 Repo-specific adapter approach
- Introduce `backend/app/api_versions/v1/` (or equivalent) as the composition layer for new v1 routers.
- For each migrated group:
  - keep existing router/service logic untouched initially,
  - expose a **v1 router** that delegates to the same internal handler/service functions,
  - keep the **legacy router** registered until compat exit.
- For prefix-composed routers (`payments`, `products`, `pricing`, `reservations`, `marketplace`, etc.), refactor the router module so handlers can be mounted by composition under both legacy and v1 prefixes.
- For hardcoded-path routers (`theme`, `upgrade_requests`, `billing_webhooks`), extract internal handler functions first, then remount them under versioned prefixes.

#### 5.3 Legacy alias rules
- Legacy route remains the frontend-safe default until the consuming client is switched.
- Alias layer must be **thin**: path remap + deprecation headers only.
- No payload transformation should happen in legacy aliases unless required to preserve backward compatibility.

### 6. Breaking-Change Riski Olan Endpoint’ler

#### Highest-risk endpoints
- `/api/auth/*` — because web cookie auth now depends on these exact routes and `X-Client-Platform: web` behavior.
- `/api/public/quote`, `/api/public/checkout`, `/api/public/my-booking/*` — public funnel + payment + idempotency exposure.
- `/api/partner/*` — external consumers and partner-key auth surface.
- `/api/webhook/stripe-billing` — third-party callback endpoint; should stay stable and likely remain unversioned externally until a later webhook strategy PR.
- `/api/payments`, `/api/reservations`, `/api/bookings`, `/api/pricing*` — central business flows with multiple internal consumers.
- `/api/tenant/*` and admin tenant feature/quota surfaces — tied to entitlement/billing roadmap.

#### Medium-risk endpoints
- `/api/admin/*` write actions
- `/api/agency/*` writeback / sheets / bookings
- `/api/b2b/*` booking and marketplace flows
- `/api/crm/*` and `/api/ops/*` mutation endpoints

#### Lower-risk endpoints
- health/system/read-only metadata
- read-only reports/dashboard endpoints
- theme/public theme endpoints

### 7. Web / Mobile / Partner / Public Ayrımı

#### Web
- Primary consumer: React SPA using `frontend/src/lib/api.js` with base `/api` and cookie auth for web.
- Web v1 target: `/api/v1/auth`, `/api/v1/admin`, `/api/v1/agency`, `/api/v1/b2b`, `/api/v1/crm`, `/api/v1/ops`, `/api/v1/reports`.

#### Mobile
- Primary consumer: future mobile app via existing `/api/v1/mobile/*` BFF.
- Rule: **leave mobile BFF URLs stable** during `/api/v1` rollout. If auth gains `/api/v1/auth/*`, mobile may adopt it later, but `/api/v1/mobile/*` must not change in the same PR.

#### Partner
- Current partner surface is `partner_v1.py` under `/api/partner/*`.
- Target: `/api/v1/partner/*`.
- Partner should have the longest compat window because external consumers are harder to coordinate than web SPA.

#### Public
- Current public surface spans `/api/public/*`, `/web/*`, `/storefront/*`, and payment-adjacent routes.
- Target: consolidate anonymous browser/public flows under `/api/v1/public/*` (and keep `/api/v1/storefront/*` only if storefront remains a distinct public surface).

### 8. Error Envelope ve Response Standardı

#### 8.1 Error envelope for v1
Use the repo’s existing standardized shape everywhere in v1:

```json
{
  "error": {
    "code": "validation_error",
    "message": "İstek doğrulama hatası",
    "details": {
      "path": "/api/v1/...",
      "correlation_id": "..."
    }
  }
}
```

#### 8.2 Response standard for v1 success payloads
- **Single resource:** return the resource directly; do not introduce a global `data` wrapper now.
- **List endpoints:** prefer `{ "items": [...], "total": n, ... }`.
- **Mutation endpoints:** return the created/updated resource or `{ "status": "ok" }` for command-style actions.
- **Delete/command endpoints:** standardize on `{ "status": "ok" }` or `204 No Content`; do not mix both inside the same router family.
- **Pagination keys:** `items`, `total`, optional `page`, `page_size`, `next_cursor`.
- **Correlation:** keep `X-Correlation-Id` header and include `correlation_id` in error details.

#### 8.3 Response-model rule for this repo
- New v1 endpoints should use explicit Pydantic response models where feasible.
- Do not return raw Mongo documents or `ObjectId` values.
- For legacy endpoints, behavior can remain as-is during compat.

### 9. Router Bazlı PR Planı

#### PR-V1-0 — Foundation / Registry / Route Manifest
- Scope:
  - dedupe `auth_router` registration in `router_registry.py`
  - add route inventory script / manifest
  - add deprecation-header helper for legacy aliases
  - define shared v1 registration pattern and file structure
- No client-visible path migration yet

#### PR-V1-1 — System / Health / Public Metadata (low risk)
- Router groups:
  - `health.py`, `health_dashboard.py`, `theme.py`, `public_cms_pages.py`, `public_campaigns.py`
- Target examples:
  - `/api/v1/health/*`
  - `/api/v1/system/*`
  - `/api/v1/public/theme`
  - `/api/v1/public/cms/pages`
  - `/api/v1/public/campaigns`

#### PR-V1-2 — Auth / Session / Settings (controlled)
- Router groups:
  - `auth.py`, `auth_password_reset.py`, `enterprise_2fa.py`, `settings.py`
- Target examples:
  - `/api/v1/auth/login`
  - `/api/v1/auth/me`
  - `/api/v1/auth/refresh`
  - `/api/v1/auth/sessions`
  - `/api/v1/settings/*`
- Must preserve cookie auth behavior exactly

#### PR-V1-3 — Agency + B2B Read-First Migration
- Router groups:
  - `agency_profile.py`, `agency_availability.py`, selected `b2b_*` GET surfaces, `dashboard_enhanced.py`, `reports.py`
- Focus: read paths first; no booking/payment writes yet

#### PR-V1-4 — Admin Read-First Migration
- Router groups:
  - `admin_agencies.py` (GETs), `admin_agency_users.py` (GETs), `admin_tenant_features.py` (GETs), `admin_analytics.py`, `admin_reports.py`, `admin_metrics.py`
- Keep admin write mutations for later PR unless a router is trivially low-risk

#### PR-V1-5 — Core Business Mutation Surfaces
- Router groups:
  - `bookings.py`, `reservations.py`, `payments.py`, `products.py`, `pricing.py`, `pricing_rules.py`, `quotes.py`, `offers.py`, `inventory*.py`, `hotel.py`, `customers.py`
- This is the biggest internal-web surface and should stay strictly repo-internal until stable

#### PR-V1-6 — Public Funnel + Partner API
- Router groups:
  - `public_search.py`, `public_checkout.py`, `public_my_booking.py`, `public_bookings.py`, `partner_v1.py`, `public_partners.py`, `storefront.py`, `web_booking.py`, `web_catalog.py`
- Keep partner/public compat longer than web

#### PR-V1-7 — Integrations / Webhooks / Legacy Hardcoded Paths
- Router groups:
  - `billing_webhooks.py`, `payments_stripe.py`, `admin_integrations.py`, `admin_sheets.py`, `agency_sheets.py`, `agency_writeback.py`, `upgrade_requests.py`, remaining hardcoded-path legacy routers
- Includes webhook/versioning decision and final alias cleanup prep

### 10. Hangi Router Grupları Asla Aynı PR’a Girmemeli
- **Do not mix** `auth*` with `public_checkout` / `partner_v1` in the same PR.
- **Do not mix** `billing_webhooks.py` with `payments.py` / `public_checkout.py` namespace changes.
- **Do not mix** `/api/v1/mobile/*` changes with `bookings.py` / `reports.py` namespace migration in the same PR.
- **Do not mix** admin write routers and agency/B2B write routers in one migration PR.
- **Do not mix** hardcoded-path routers (`theme`, `upgrade_requests`, `billing_webhooks`) with bulk prefix-based alias batches.
- **Do not mix** tenant feature/quota/entitlement routers with generic versioning-only admin cleanup.

### 11. Her PR İçin Risk Matrisi

| PR | Scope | Risk | Primary failure mode | Mitigation |
|---|---|---|---|---|
| PR-V1-0 | registry + manifest | Low-Med | accidental route shadowing | route inventory diff + exact route-count assertions |
| PR-V1-1 | system/public metadata | Low | path mismatch / stale frontend call | legacy alias + preview smoke |
| PR-V1-2 | auth/session/settings | High | login/refresh/logout regressions | keep legacy path default, cookie auth curl + browser smoke |
| PR-V1-3 | agency/b2b reads | Medium | tenant header / role scope drift | tenant-aware preview tests + read-only rollout |
| PR-V1-4 | admin reads | Medium | dashboard/admin data regressions | GET-only first, targeted admin smoke |
| PR-V1-5 | core mutations | High | booking/payment/pricing regressions | no payload redesign, contract tests, staged rollout |
| PR-V1-6 | public + partner | High | external contract break / idempotency issue | longer compat, partner/public dedicated tests |
| PR-V1-7 | webhooks/integrations | High | callback failures / missed events | keep webhook stable until explicit cutover, replay testing |

### 12. Cookie Auth + Mobile BFF + Tenant Binding Etkileri

#### Cookie auth
- `/api/v1/auth/*` must preserve:
  - `X-Client-Platform: web`
  - httpOnly access/refresh cookie setting and clearing
  - `/auth/me` bootstrap semantics used by `frontend/src/hooks/useAuth.js`
- Web SPA should migrate to `/api/v1/auth/*` only after the v1 auth alias is proven in preview.

#### Mobile BFF
- `/api/v1/mobile/*` is already the versioned contract and should remain untouched during early v1 rollout.
- Mobile BFF depends on booking/report service behavior and tenant-aware repositories, so do not couple it to core route churn in the same PR.

#### Tenant binding
- Current tenant model depends on `X-Tenant-Id` + `TenantResolutionMiddleware` + `RequestContext`.
- v1 migration must not introduce tenant path params or alternate tenant resolution rules yet.
- Any v1 alias for agency/admin/b2b routes must preserve current request header and membership validation behavior.

### 13. Rollback Stratejisi

#### Rollback principle
- Rollback should be **route-registration only**, not business-logic rollback.

#### Recommended rollback mechanism
- Keep legacy routes live during compat.
- Gate v1 registration behind explicit rollout flags/modes in composition (example: `legacy-only`, `dual`, `v1-default`).
- If a v1 rollout causes issues:
  1. switch router registry back to `legacy-only`,
  2. leave legacy `/api/...` paths untouched,
  3. investigate v1 alias behavior without reverting auth/session/business logic changes.

#### Repo-specific rollback note
- Because web auth, session model, tenant binding, and mobile BFF are already stabilized, rollback must not revert those earlier PRs. Only the namespace layer should roll back.

### 14. Test / Smoke Planı

#### 14.1 Existing tests to reuse
- Auth/session/tenant:
  - `backend/tests/test_auth_web_cookie_compat.py`
  - `backend/tests/test_auth_session_model.py`
  - `backend/tests/test_auth_tenant_binding.py`
  - `backend/tests/test_auth_jwt_and_org_context.py`
- Mobile:
  - `backend/tests/test_mobile_bff_contracts.py`
  - `backend/tests/test_mobile_bff_preview_api.py`
- Public:
  - `backend/tests/test_public_search_api.py`
  - `backend/tests/test_public_checkout_api.py`
  - `backend/tests/test_public_my_booking_*.py`
- Partner:
  - `backend/tests/test_partner_api_v1.py`
- Tenant/admin:
  - `backend/tests/test_tenant_isolation_admin_agencies.py`
  - `backend/tests/integration/feature_flags/test_tenant_features_endpoint.py`

#### 14.2 Smoke test matrix

| Surface | Legacy path | v1 path | What must be validated |
|---|---|---|---|
| Web auth | `/api/auth/login`, `/me`, `/refresh`, `/logout` | `/api/v1/auth/...` | cookie set/refresh/clear, browser refresh persistence |
| Admin web | `/api/admin/agencies` | `/api/v1/admin/agencies` | same auth, same tenant scope, same status codes |
| Agency web | `/api/agency/profile` | `/api/v1/agency/profile` | allowed modules, tenant header behavior |
| B2B web | `/api/b2b/me`, `/api/b2b/bookings` | `/api/v1/b2b/...` | role guard + redirect safety |
| Mobile BFF | `/api/v1/mobile/...` | same | no regression allowed |
| Public | `/api/public/quote`, `/checkout` | `/api/v1/public/...` | quote creation, idempotency, payment bootstrap |
| Partner | `/api/partner/*` | `/api/v1/partner/*` | API key auth, response parity |
| Billing webhook | `/api/webhook/stripe-billing` | only after explicit decision | signature validation, idempotency, audit side effects |

#### 14.3 Mandatory rollout validation sequence per PR
1. Route inventory diff
2. Targeted pytest for the migrated router group
3. Preview curl parity test: legacy vs v1
4. Browser smoke for affected web flow (if web-facing)
5. Staging smoke before production enablement

### 15. En Sonda Önerilen Rollout Sırası
1. **PR-V1-0** — foundation / registry cleanup / route manifest
2. **PR-V1-1** — low-risk system + public metadata routes
3. **PR-V1-2** — auth/session/settings with dual-route compat
4. **PR-V1-3** — agency + B2B read-first
5. **PR-V1-4** — admin read-first
6. **PR-V1-5** — core booking/catalog/pricing mutations
7. **PR-V1-6** — public funnel + partner API
8. **PR-V1-7** — integrations/webhooks/hardcoded-path cleanup
9. After v1 path stabilization: **staging/prod runtime wiring parity**
10. After mobile repo attachment: **PR-5B mobile secure session adoption**
11. After those are stable: **entitlement projection / billing unification**

### PR-V1-0 Implemented — Foundation / Registry / Route Inventory (Mar 7, 2026)
- Added foundation files under `backend/app/bootstrap/`:
  - `v1_manifest.py` for deterministic route classification metadata (`current_namespace`, `target_namespace`, `owner`, `risk_level`)
  - `compat_headers.py` for shared deprecation/sunset/successor-version header generation
  - `v1_registry.py` as the initial `/api/v1` composition entrypoint
  - `route_inventory.py` for sorted route inventory building and JSON export
- Added helper script `backend/scripts/export_route_inventory.py` that writes deterministic route inventory output to `/app/backend/app/bootstrap/route_inventory.json`.
- Cleaned `backend/app/bootstrap/router_registry.py` so `auth_router` is no longer registered twice. The v1 registry is now mounted through `register_v1_routers(app)` and currently preserves the existing `/api/v1/mobile/*` surface only.
- Generated committed artifact `/app/backend/app/bootstrap/route_inventory.json` with stable ordering and required foundation fields: `path`, `method`, `source`, `current_namespace`, `target_namespace`, `legacy_or_v1`, `compat_required`, `risk_level`, `owner`.
- Added focused tests:
  - `backend/tests/test_api_v1_foundation.py`
  - `backend/tests/test_pr_v1_foundation_acceptance.py`
- Validation passed via:
  - `pytest /app/backend/tests/test_api_v1_foundation.py -q`
  - `pytest /app/backend/tests/test_auth_web_cookie_compat.py -q`
  - `pytest /app/backend/tests/test_pr_v1_foundation_acceptance.py -q`
  - deterministic export script run
  - backend testing agent report `/app/test_reports/iteration_16.json`
  - frontend smoke + frontend automation verifying login still works after registry cleanup

### PR-V1-1 Implemented — Low-Risk System / Public Metadata Rollout (Mar 7, 2026)
- Added low-risk v1 alias registration in `backend/app/bootstrap/v1_aliases.py` and wired it via `backend/app/bootstrap/v1_registry.py`.
- New dual-route coverage now exists for these scoped router groups while preserving legacy paths:
  - `GET /api/health` + `GET /api/v1/health`
  - `GET /api/system/ping` + `GET /api/v1/system/ping`
  - `GET /api/system/health-dashboard` + `GET /api/v1/system/health-dashboard`
  - `GET /api/system/prometheus` + `GET /api/v1/system/prometheus`
  - `GET /api/public/theme` + `GET /api/v1/public/theme`
  - `GET|PUT /api/admin/theme` + `GET|PUT /api/v1/admin/theme`
  - `GET /api/public/cms/pages[/{slug}]` + `GET /api/v1/public/cms/pages[/{slug}]`
  - `GET /api/public/campaigns[/{slug}]` + `GET /api/v1/public/campaigns[/{slug}]`
- Extended `v1_manifest.py` with `derive_target_path()` plus `/api/v1/*` namespace awareness so route inventory classifies both legacy and v1 aliases correctly.
- Added best-effort runtime snapshot export in `backend/app/bootstrap/api_app.py`, so the current `route_inventory.json` is refreshed during app boot without making runtime availability depend on export success.
- Added route inventory diff support:
  - `backend/app/bootstrap/route_inventory_diff.py`
  - `backend/scripts/diff_route_inventory.py` (`text` and `json` output)
- Current inventory snapshot now reports **675** total routes with **17** v1 routes, including **11** newly added PR-V1-1 aliases.
- Added/updated tests:
  - `backend/tests/test_api_v1_low_risk_rollout.py`
  - `backend/tests/test_pr_v1_1_low_risk_rollout_http.py`
- Validation passed via:
  - `pytest /app/backend/tests/test_api_v1_foundation.py /app/backend/tests/test_api_v1_low_risk_rollout.py -q`
  - preview HTTP smoke on legacy + v1 parity for health/system/theme/public CMS/public campaigns/admin theme
  - backend testing agent report `/app/test_reports/iteration_17.json`
  - backend deep validation agent: 23/23 checks passed

### Runtime Parity + CI Route Visibility Added (Mar 7, 2026)
- Added route inventory summary support in `backend/app/bootstrap/route_inventory_summary.py` with deterministic counts and hash fields:
  - `route_count`
  - `v1_count`
  - `legacy_count`
  - `compat_required_count`
  - `inventory_hash`
- Runtime export now writes both of these best-effort artifacts during API boot:
  - `backend/app/bootstrap/route_inventory.json`
  - `backend/app/bootstrap/route_inventory_summary.json`
- Extended `backend/scripts/export_route_inventory.py` so runtime containers and CI can export inventory + summary to custom paths with explicit environment labels.
- Added parity comparison CLI: `backend/scripts/check_route_inventory_parity.py`
  - compares preview/staging/prod summary files
  - reports count/hash parity in `json` or `text`
  - can fail CI via `--fail-on-mismatch`
- Added operational parity playbook: `backend/app/bootstrap/route_inventory_parity.md`
- Updated `backend/app/bootstrap/runtime_ops.md` with route inventory export + parity commands in the deploy smoke checklist.
- CI workflow (`.github/workflows/ci.yml`) now includes a dedicated `route-inventory` job that:
  - exports route inventory + summary artifacts
  - generates parity artifacts
  - resolves a previous baseline inventory
  - generates diff artifacts (`json` + `text`)
  - uploads artifacts for inspection
  - writes a PR step summary and updates/creates a PR comment on pull requests
- Artifact set now includes:
  - `route_inventory.json`
  - `route_inventory_summary.json`
  - `route_inventory_diff.json`
  - `route_inventory_diff.txt`
  - `route_inventory_parity.json`
  - `route_inventory_parity.txt`
  - `route_inventory_pr_summary.md`
- Important scope note: actual staging/prod environments were **not attached in this workspace**, so this work implements the runtime/CI tooling and parity workflow needed for real environment execution, rather than claiming live staging/prod verification already happened.
- Added/updated tests:
  - `backend/tests/test_route_inventory_parity.py`
  - `backend/tests/test_route_inventory_parity_tooling.py`
- Validation passed via:
  - `pytest /app/backend/tests/test_api_v1_foundation.py /app/backend/tests/test_api_v1_low_risk_rollout.py /app/backend/tests/test_route_inventory_parity.py -q`
  - `pytest /app/backend/tests/test_route_inventory_parity_tooling.py -q`
  - local export/parity CLI smoke with preview/staging/prod-labeled summaries (`675 total / 17 v1 / 658 legacy`)
  - YAML parse validation of `.github/workflows/ci.yml`
  - backend testing agent report `/app/test_reports/iteration_18.json`

### PR-V1-2A Implemented — Auth Bootstrap Alias-First Rollout (Mar 7, 2026)
- PR-V1-2 was intentionally split into smaller rollout slices. **PR-V1-2A** covers only the auth bootstrap surface:
  - `POST /api/v1/auth/login`
  - `GET /api/v1/auth/me`
  - `POST /api/v1/auth/refresh`
- Legacy auth routes remain unchanged and still primary for the current web client:
  - `POST /api/auth/login`
  - `GET /api/auth/me`
  - `POST /api/auth/refresh`
- Added scoped auth alias rollout in `backend/app/bootstrap/v1_aliases.py` without taking sessions/revoke/settings into this PR.
- Added legacy compatibility headers for migrated auth bootstrap endpoints in `backend/app/routers/auth.py`:
  - `Deprecation: true`
  - `Link: </api/v1/auth/...>; rel="successor-version"`
- Cookie auth behavior, web bootstrap, bearer fallback, session model, and mobile BFF contract were preserved.
- `route_inventory` state after PR-V1-2A:
  - `route_count = 678`
  - `v1_count = 20`
  - `legacy_count = 658`
  - `legacy_routes_remaining = 658`
  - `namespaces.auth = 17`
- Added/updated tests:
  - `backend/tests/test_api_v1_auth_aliases.py`
  - `backend/tests/test_pr_v1_2a_auth_bootstrap_http.py`
- Validation passed via:
  - `pytest /app/backend/tests/test_api_v1_foundation.py /app/backend/tests/test_api_v1_auth_aliases.py /app/backend/tests/test_auth_web_cookie_compat.py -q`
  - preview smoke for legacy compat headers + v1 login/me/refresh cookie flow + v1 bearer flow
  - backend deep validation: 15/15 passed
  - frontend smoke validation: existing `/login` flow, bootstrap, protected-route redirect, and logout all passed with no regression
- Scope guard confirmed: **not included yet**
  - `/api/v1/auth/sessions`
  - `/api/v1/auth/sessions/{id}/revoke`
  - `/api/v1/auth/revoke-all-sessions`
  - settings namespace work

### PR-V1-2B Implemented — Auth Session Management Alias-First Rollout (Mar 7, 2026)
- Extended the scoped auth rollout in `backend/app/bootstrap/v1_aliases.py` for session management while preserving all legacy routes:
  - `GET /api/v1/auth/sessions`
  - `POST /api/v1/auth/sessions/{id}/revoke`
  - `POST /api/v1/auth/revoke-all-sessions`
- Legacy session endpoints remain active and backward compatible:
  - `GET /api/auth/sessions`
  - `POST /api/auth/sessions/{id}/revoke`
  - `POST /api/auth/revoke-all-sessions`
- Added legacy compatibility headers in `backend/app/routers/auth.py` for session listing and revoke-all flows, and route-template aware successor resolution for dynamic revoke paths.
- Cookie auth behavior stayed intact for web requests using `X-Client-Platform: web`; bearer/session revoke semantics were preserved for current session and bulk revoke behavior.
- Expanded route inventory telemetry in `backend/app/bootstrap/route_inventory_summary.py` with `domain_v1_progress` so auth/admin/public/system/mobile/tenant/finance/misc domains now expose target count, migrated v1 count, remaining count, and migration percent.
- Updated route inventory artifacts after rollout:
  - `route_count = 681`
  - `v1_count = 23`
  - `legacy_count = 658`
  - `legacy_routes_remaining = 658`
  - `domain_v1_progress.auth = 42.86%` (`6 / 14` target auth routes migrated)
  - `route_inventory_diff.json` reports exactly **3** new v1 auth session aliases
- Added/updated tests:
  - `backend/tests/test_auth_session_model.py`
  - `backend/tests/test_route_inventory_parity.py`
  - `backend/tests/test_route_inventory_parity_tooling.py`
  - `backend/tests/test_pr_v1_2a_auth_bootstrap_http.py`
  - `backend/tests/test_pr_v1_2b_session_rollout_http.py`
- Validation passed via:
  - `pytest /app/backend/tests/test_auth_session_model.py /app/backend/tests/test_route_inventory_parity.py /app/backend/tests/test_route_inventory_parity_tooling.py -q`
  - `pytest /app/backend/tests/test_pr_v1_2b_session_rollout_http.py -q`
  - preview curl smoke for legacy/v1 session parity, single-session revoke, revoke-all, and cookie-auth session flows
  - backend deep validation: all requested PR-V1-2B checks passed

### PR-V1-2C Implemented — Settings Namespace Alias-First Rollout (Mar 7, 2026)
- Rolled the existing settings router into `/api/v1/settings/*` using the same alias-first strategy while keeping legacy routes active:
  - `GET /api/v1/settings/users`
  - `POST /api/v1/settings/users`
- Legacy settings endpoints remain active and backward compatible:
  - `GET /api/settings/users`
  - `POST /api/settings/users`
- Added compat headers to legacy settings endpoints in `backend/app/routers/settings.py` so the compat period is explicit without changing behavior:
  - `Deprecation: true`
  - `Link: </api/v1/settings/users>; rel="successor-version"`
- Confirmed cookie auth was not affected: web requests with `X-Client-Platform: web` still resolve `cookie_compat`; Mobile BFF remained unaffected.
- Expanded route inventory telemetry with `migration_velocity` in `backend/app/bootstrap/route_inventory_summary.py`:
  - `routes_migrated_this_pr`
  - `routes_remaining`
  - `estimated_prs_remaining`
- Updated route inventory artifacts after rollout:
  - `route_count = 683`
  - `v1_count = 25`
  - `legacy_count = 658`
  - `legacy_routes_remaining = 658`
  - `migration_velocity.routes_migrated_this_pr = 2`
  - `migration_velocity.estimated_prs_remaining = 11`
  - `domain_v1_progress.system = 31.58%` (`6 / 19` target system/settings routes migrated)
  - `route_inventory_diff.json` reports exactly **2** new v1 settings aliases
- Added/updated tests:
  - `backend/tests/test_route_inventory_parity.py`
  - `backend/tests/test_route_inventory_parity_tooling.py`
  - `backend/tests/test_pr_v1_2c_settings_rollout_http.py`
- Validation passed via:
  - `pytest /app/backend/tests/test_route_inventory_parity.py /app/backend/tests/test_route_inventory_parity_tooling.py /app/backend/tests/test_pr_v1_2c_settings_rollout_http.py -q`
  - preview smoke for legacy/v1 settings parity, v1 create-user behavior, cookie-auth settings listing, and mobile BFF safety
  - backend deep validation: all requested PR-V1-2C checks passed

## Current Priority Backlog
- **P0:** If/when separate real environments exist, run the parity workflow against staging/prod artifacts; for the current single-environment setup this remains N/A but tooling is ready
- **P0:** PR-5B — Mobile Secure Session + Session Bootstrap (requires mobile repo; checklist ready at `backend/app/modules/mobile/pr5b_integration_checklist.md`)
- **P1:** Entitlement projection engine + usage metering hattı
- **P1:** Observability stack
- **P1:** Cleanup PR for non-blocking preview issues: `/api/partner-graph/notifications/summary`, `/api/tenant/features`, `/api/tenant/quota-status`
- **P2:** Optional internal ops PR — `domain_v1_progress` / migration kartını admin dashboard üzerinde görünür yapmak
- **P2:** Broader frontend modular refactor
