# Syroce — Next Generation Agency Operating System

## Project Overview

Syroce is a multi-tenant SaaS platform for travel agencies, managing tours, hotels, flights, bookings, finance, CRM, and B2B operations.

## Architecture

### Frontend
- **Framework**: React 19 with Create React App (CRA) via CRACO
- **UI**: Shadcn/UI (Radix UI), Tailwind CSS
- **State**: TanStack Query (React Query)
- **Routing**: React Router DOM v6
- **Port**: 5000

### Backend
- **Framework**: FastAPI (Python 3.12)
- **Database**: MongoDB (motor async driver)
- **Cache/Queue**: Redis + Celery
- **Auth**: JWT + Session-based with 2FA
- **Port**: 8000

## Project Structure

```
/
├── backend/          # FastAPI backend
│   ├── app/
│   │   ├── bootstrap/    # App startup & lifecycle
│   │   ├── modules/      # Domain modules (auth, booking, finance, etc.)
│   │   ├── domain/       # Core business logic & state machines
│   │   ├── infrastructure/ # Redis, event bus, rate limiters
│   │   ├── repositories/ # Data access layer
│   │   └── services/     # Business services
│   ├── requirements.txt
│   └── server.py         # Entry point
├── frontend/         # React frontend
│   ├── src/
│   │   ├── features/     # Feature-specific components
│   │   ├── components/   # Shared UI components
│   │   ├── pages/        # Top-level pages
│   │   ├── lib/          # API client, auth, utilities
│   │   └── config/       # Feature flags & menus
│   └── craco.config.js   # CRACO webpack config
├── start_backend.sh  # Backend startup script (MongoDB + Redis + FastAPI)
└── Makefile          # Quality gate commands
```

## Workflows

- **Start Backend**: Runs `bash start_backend.sh` — starts MongoDB, Redis, then FastAPI on port 8000
- **Start application**: Runs `cd frontend && PORT=5000 BROWSER=none yarn start` — CRA dev server on port 5000

## Environment Variables

| Variable | Description |
|----------|-------------|
| `MONGO_URL` | MongoDB connection URL (default: `mongodb://localhost:27017`) |
| `DB_NAME` | MongoDB database name (default: `syroce_dev`) |
| `REDIS_URL` | Redis connection URL (default: `redis://localhost:6379/0`) |
| `JWT_SECRET` | JWT signing secret (auto-generated) |
| `ENV` | Environment: `dev`, `staging`, `production` |

## Development Setup

The frontend dev server proxies `/api` requests to the backend at `localhost:8000`.

MongoDB and Redis are started automatically by the `start_backend.sh` script using system-installed packages.

## Key Notes

- MongoDB data is stored at `/tmp/mongodb-data` (ephemeral)
- The app is Turkish-language (UI strings are in Turkish)
- Multi-tenant: every request requires an `X-Tenant-Id` header
- Auth uses HTTP-only cookies (no localStorage tokens)
- CRM customer documents require an explicit `id` field (separate from MongoDB `_id`); the `list_customers` query uses `{"_id": 0}` projection
- Trial and demo seed services (`trial_seed_service.py`, `demo_seed_service.py`) must include `"id"` in customer documents to match the `CustomerOut` Pydantic schema
- Emergent AI platform dependencies have been fully removed (scripts, visual-edits plugin, proxy URLs, CORS allowlists, LLM key references)
- AI assistant uses `LLM_API_KEY` environment variable (not the old Emergent key)
- Stripe connects directly to `api.stripe.com` (no proxy)

## Phase 3 Modules (New)

All new routers live in `backend/app/modules/operations/routers/` and are registered via the operations domain router in `backend/app/modules/operations/__init__.py`. The Customer Portal is registered directly in `domain_router_registry.py` to avoid circular imports in the public module.

| Module | Backend Router | Frontend Page | API Prefix |
|--------|---------------|---------------|------------|
| Transfer Management | `admin_transfers.py` | `pages/admin/Transfers.jsx` | `/api/admin/transfers` |
| Guide Management | `admin_guides.py` | `pages/admin/Guides.jsx` | `/api/admin/guides` |
| Vehicle/Fleet Management | `admin_vehicles.py` | `pages/admin/Vehicles.jsx` | `/api/admin/vehicles` |
| Flight Management | `admin_flights.py` | `pages/admin/Flights.jsx` | `/api/admin/flights` |
| Visa Tracking | `admin_visa.py` | `pages/admin/Visa.jsx` | `/api/admin/visa` |
| Insurance Management | `admin_insurance.py` | `pages/admin/Insurance.jsx` | `/api/admin/insurance` |
| Calendar | `calendar.py` | `pages/admin/Calendar.jsx` | `/api/calendar` |
| Email Templates | `admin_email_templates.py` | `pages/admin/EmailTemplates.jsx` | `/api/admin/email-templates` |
| Customer Self-Service Portal | `customer_portal.py` | `pages/admin/CustomerPortal.jsx` | `/api/portal` |
| Admin Portal Mgmt | `admin_portal_management.py` | (integrated in CustomerPortal) | `/api/admin/support-tickets`, `/api/admin/cancel-requests`, `/api/admin/portal-stats` |
| Villa Management | `admin_villas.py` (inventory) | `pages/admin/AdminVillasPage.jsx` | `/api/admin/villas` |
| Activity Management | `admin_activities.py` (operations) | `pages/admin/AdminActivitiesPage.jsx` | `/api/admin/activities` |
| Payment Gateways | `payment_gateways.py` (finance) | `pages/admin/AdminPaymentGatewaysPage.jsx` | `/api/admin/payment-gateways` |

New MongoDB collections: `transfers`, `guides`, `vehicles`, `flights`, `visa_applications`, `insurance_policies`, `email_templates`, `portal_sessions`, `support_tickets`, `cancel_requests`, `vehicle_maintenance`, `villas`, `activities`, `payment_gateways`, `payment_transactions`

### Supplier Integrations (XML/REST)

| Supplier | Adapter File | Status |
|----------|-------------|--------|
| Paximum | `backend/app/suppliers/adapters/paximum_adapter.py` | Full implementation (Hotel + Transfer + Activity) |
| HotelsPro | `backend/app/suppliers/adapters/hotelspro_adapter.py` | Full implementation (Hotel, JSON + XML modes) |

### Turkish Payment Gateways

| Provider | File | Capabilities |
|----------|------|-------------|
| İyzico | `backend/app/billing/iyzico_provider.py` | Checkout form, 3D Secure, Refund, Cancel, Sub-merchant, Subscriptions |
| PayTR | `backend/app/billing/paytr_provider.py` | iFrame token, Callback verification, Customer management |
| Stripe | `backend/app/billing/stripe_provider.py` | Full implementation (existing) |

Gateway configuration admin: `/api/admin/payment-gateways` — multi-provider setup with test/live modes, credential management, and payment initiation

### Error Handling Standard

All routers use `AppError` from `app.errors` (not `JSONResponse`). The `AppError` class provides:
- Consistent error format: `{"error": {"code": "...", "message": "...", "details": {...}}}`
- Helper functions: `not_found_error()`, `validation_error()`, `conflict_error()`, `business_error()`
- Status validation on PATCH/status updates with allowed status lists
- Pydantic `BaseModel` for all create/update payloads (no raw `Dict[str, Any]`)

### Audit Logging

All Phase 3 routers include `_audit()` helper that writes to audit_logs on create/update/delete/assign operations. Audit failures are logged via `logger.exception()` (never silently swallowed with `except: pass`).

### Bulk Operations

Bulk status update endpoints added:
- `POST /api/admin/transfers/bulk-status`
- `POST /api/admin/flights/bulk-status`
- `POST /api/admin/visa/bulk-status`

### Security

- Customer Portal login requires `organization_id` parameter upfront (prevents cross-tenant lookup)
- All portal endpoints enforce `organization_id` from session (no fallback/optional behavior)
- Flight passenger add uses atomic MongoDB update with `available_seats: {$gt: 0}` filter (race-condition safe)
- Vehicle creation checks for duplicate plate numbers

### Organization Module Management

Per-organization module toggle system allowing each agency to enable/disable specific product modules:

| Component | Path | Description |
|-----------|------|-------------|
| Module Registry | `backend/app/constants/org_modules.py` | 6 groups, 28 modules with labels/descriptions |
| Backend API | `backend/app/modules/identity/routers/org_modules.py` | GET/PUT/DELETE `/api/admin/org-modules` |
| Frontend Page | `frontend/src/pages/admin/AdminOrgModulesPage.jsx` | Toggle UI with search, group select, save |
| Nav Integration | `frontend/src/components/AppShell.jsx` | `moduleKey` on nav items; `isOrgModuleEnabled` filter |

- **Core modules** (dashboard, users, settings) are always visible
- All nav items tagged with `moduleKey` property matching backend module keys
- Disabling a module hides it from sidebar AND blocks route access (redirect to `/app`)
- Changes broadcast via `org-modules-updated` CustomEvent for instant UI refresh
- MongoDB collection: `organization_modules`
- No restrictions = all modules visible (default behavior)

### Cross-Module Integrations (Phase 3 Gaps Fixed)

- **Customer Portal**: Admin support ticket listing/management + cancel request approve/reject + portal stats dashboard
- **Transfer → Vehicle/Guide**: Assign-vehicle and assign-guide buttons with dropdown selectors in Transfer page
- **Transfer → Booking**: `booking_id` field in transfer creation form
- **Visa/Insurance → CRM**: Searchable customer dropdown fetching from `/crm/customers` instead of plain text ID input; sidebar visibility enabled
- **Flight → Passengers**: Passenger list modal with add/remove capability on each flight; atomic seat management
- **Guide → Calendar/Rating**: Calendar modal showing guide assignments + star rating modal with existence validation
- **Vehicle → Maintenance**: Pydantic-validated maintenance form; vehicle km auto-update on maintenance; calendar modal
- **Calendar → Detail/Create**: Click event to see detail modal; click day for quick-create shortcuts to Transfer/Flight/Visa/Insurance
- **Email Templates → Outbox**: `email_template_resolver.py` service resolves templates by `trigger_key` with variable substitution; wired into `enqueue_booking_email` with fallback to hardcoded HTML
- **Insurance → Renew**: Policy renewal endpoint creates new policy linked to previous one
- **Search**: All list endpoints support `search` query parameter for name/number text search

## P0–P3 Audit Hardening (2026-05-03)

Defense-in-depth pass on multi-tenant boundary + production hygiene.

### Security / Tenancy
- **Defensive `organization_id` filters** added at 5 lookup sites (orchestrator, b2c_post_payment, approval_service, advanced_reports_service) plus call-site wiring in `stripe_handlers` (passes `organization_id` from Stripe metadata) and `enterprise_approvals` router (now calls `get_approval` tenant-scoped).
- **`backup_service.delete_backup`** explicitly documented as platform-wide (super_admin scope).
- **Tour image static mount** (`/api/uploads/tours`) confirmed and documented as **intentionally public** — referenced by storefront/SEO/OG. Filenames are random UUIDs, upload endpoint is admin-auth gated, image-only, 10MB cap, extension allowlist, directory listing disabled.

### Production hygiene
- **Test routes gated**: `AgencyBookingTestPage`, `SimpleBookingTest` mounted only when `IS_DEV` (NODE_ENV !== "production").
- **`console.log/debug` stripped** from 7 production agency pages (search/booking/hotel flows).
- **ESLint `no-console` rule** added (allows warn/error/info).
- **`market_launch_service` support channels** read from env (`SYROCE_SUPPORT_EMAIL`, `SYROCE_SUPPORT_WHATSAPP`) — no `XXX` placeholders.
- **`alert()` → sonner toast**: 54 alert sites across 29 admin/marketplace/CRM pages migrated to non-blocking sonner toasts (`toast.success` / `toast.error` / `toast()`), preserving existing `<Toaster richColors closeButton />` mount in `App.js`.

### FX
- **`b2b_hotels_search`** now uses `FXService.get_rate` (per-currency cache inside the loop, graceful 1:1 fallback on lookup failure).

### Per-tenant rate limiting (T007)
Built on the existing Redis token-bucket infra (`app/infrastructure/rate_limiter.py` + `app/middleware/rate_limit_middleware.py`):
- New tier `tenant_global`: 600 req/min baseline per tenant (basic plan).
- **Plan multiplier matrix** (`PLAN_MULTIPLIERS`): free 0.5×, basic 1.0×, starter 2.0×, pro 5.0×, business 10.0×, enterprise 25.0×. Override any plan at runtime via `SYROCE_RATE_PLAN_MULT_<PLAN>` env (e.g. `SYROCE_RATE_PLAN_MULT_PRO=12.5`).
- **Plan scaling is restricted to `tenant_*` tiers only** — IP/auth/public-checkout tiers stay constant so an enterprise tenant can't brute-force `/auth/login` by burning their own quota.
- Middleware now performs a per-tenant check after the per-IP global check, keyed on `request.state.tenant_org_id` (set by `TenantResolutionMiddleware`). Anonymous traffic remains IP-rate-limited only.
- **Plan lookup** uses a 60s in-process TTL cache (`_PLAN_CACHE`, max 4096 entries with cheap eviction) — coalesces repeat requests per org down to ~1 DB hit per minute. DB failures are swallowed (defensive: rate-limit middleware must not 500 the request); unknown plans default to basic (1.0×).
- **Fail-mode semantics fixed**: `check_rate_limit()` now raises `RateLimiterUnavailable` only when Redis itself is unreachable (connection/timeout/refused). Logic-level errors fail-open at source. The middleware's Mongo fallback is reached *only* on real outages — previously it was dead code because the function swallowed all exceptions.
- **Per-IP × per-tenant interaction caveat**: each request is checked against BOTH `api_global` (200/min/IP) AND `tenant_global` (per-tenant, plan-scaled). For tenants behind a single shared egress IP (NAT'd offices), the per-IP cap dominates regardless of plan tier — documented inline. To benefit from higher plan multipliers, traffic must originate from multiple IPs or `api_global` capacity must be raised.
- **Tests**: 13 DB-free unit tests in `tests/unit/test_rate_limiter_per_tenant.py` covering plan multiplier resolution, env override, case-insensitivity, tier-scaling math, plan-cache TTL coalescing, DB-failure graceful fallback, Redis-outage `RateLimiterUnavailable` raise, and Redis-disabled fail-open. New `tests/unit/conftest.py` keeps unit tests isolated from the heavyweight DB-touching autouse fixtures in the parent harness (workaround for the Atlas 500-collection blocker).

### Stripe service helper extraction (T009 partial)
- **Extracted 17 pure helpers + `PLAN_ORDER` + `REAL_*` prefix constants** from `backend/app/services/stripe_checkout_service.py` into a new sibling module `backend/app/services/stripe_checkout_helpers.py` (194 LOC). These functions had zero dependency on `StripeCheckoutService` class state, no DB access, no I/O beyond `os.environ` reads — perfect candidates for isolation.
- **Original file shrank**: 1644 → 1539 lines (~6%). Not a full refactor of T009's giant service, but a low-risk, testable first slice.
- **Back-compat preserved**: `stripe_checkout_service.py` re-imports every extracted symbol at module scope, so legacy import sites continue to work unchanged. Critical example: `app/modules/finance/routers/billing_webhooks.py:12` still does `from app.services.stripe_checkout_service import _iso_from_unix, stripe_checkout_service`.
- **25 DB-free unit tests** in `tests/unit/test_stripe_checkout_helpers.py` covering every extracted helper, parametrized cases for `_iso_from_unix`/`_plan_change_mode`/`_coerce_minor_amount`, Turkish locale formatting in `_format_try_minor`, freshness logic in `_should_refresh_subscription_snapshot`, and a back-compat meta-test asserting the re-export from the service module still resolves. Architect: PASS, no HIGH/CRITICAL.

### Self-service tenant export UI (T008)
- **VERIFIED ALREADY COMPLETE** prior to this audit task. Inventory:
  - **Backend**: `POST /api/admin/tenant/export` (`backend/app/modules/identity/routers/enterprise_export.py`) — admin-gated, in-memory ZIP build, exports 8 collections (`customers`, `crm_deals`, `crm_tasks`, `reservations`, `payments`, `products`, `crm_notes`, `crm_activities`) with `_metadata.json`, includes quota enforcement (`UsageMetric.EXPORT_GENERATED`) and usage tracking with correlation IDs.
  - **Frontend**: `AdminTenantExportPage` at `/app/admin/tenant-export`, lazy-loaded in `adminRoutes.jsx`, registered in `admin.navigation.js` (search-visible, direct-access). Provides download UX with loading state, success badge, 429 rate-limit detection, and Turkish copy.
  - **Companion** (out of T008 scope but relevant): `backend/app/modules/identity/routers/gdpr.py` provides per-user GDPR export/delete/consent endpoints (`/api/gdpr/export-my-data`, `/api/gdpr/delete-my-data`, etc.) — no frontend UI yet but backend is fully implemented; would be a future "Privacy Center" UI sprint.

### Stub page polish (T013)
- **NotFoundPage rewritten** — was a 22-line minimal stub. Now: (1) shows large "404" hero, (2) auth-aware destination (logged-in → `/app`, guests → `/login`), (3) "Geri dön" button uses `navigate(-1)` with empty-history fallback, (4) surfaces the unknown `location.pathname` so users can spot typos, (5) extra deep-link to `/app` for authed users.
- **OnboardingWizard reviewed** — was *not* a stub: 240-line real, multi-step wizard with `/onboarding/state` integration. Audit's "stub" label was inaccurate. No changes needed.

### Lazy router loading (T012)
- **Already complete prior to this audit task** — confirmed via inventory: all 6 route files (`coreRoutes`, `agencyRoutes`, `adminRoutes`, `b2bRoutes`, `hotelRoutes`, `publicRoutes`) use `React.lazy()` exclusively for page components. Total ~234 lazy-loaded page chunks across the router, zero eager `import … from "../pages/…"` statements at the route layer. No further work required.

### Test hygiene (T011)
- **Placeholder skipped test removed**: `tests/test_booking_payments_service.py::test_cas_update_amounts_conflict_raises` was an unconditional `@pytest.mark.skip` with `pass` body. Replaced with a real, DB-free test that stubs the `booking_payments` collection so `find_one_and_update` always returns `None`, asserting `AppError(409, "payment_concurrency_conflict")` is raised after exactly 2 CAS retries.
- **Conftest harness fix**: `tests/conftest.py` truncates `test_db` / `seeded_test_db` database names to fit Atlas's 38-byte DB-name limit (was 45 chars → caused `Database name too long` errors).
- **Module-level env-conditional skips kept** (`test_billing_lifecycle_iteration32.py`, `test_ratehawk_booking_flow_p0_iter116.py`, etc.) — these use the canonical `pytest.skip(..., allow_module_level=True)` pattern when `REACT_APP_BACKEND_URL` is unset for live HTTP integration tests.

### Known infra blocker — pytest DB tests
The shared Atlas free-tier cluster (`syroce.no04m9w.mongodb.net`) is at **500/500 collections** entirely from production-like databases (`syroce-acente`, `syroce-pms`, `syroce-sadakat`, etc.). Any pytest run that touches the DB currently errors with `cannot create a new collection -- already using 500 collections of 500`. Most autouse fixtures in `tests/conftest.py` create a per-test DB, so this affects nearly all backend tests including the new T011 test (whose code is logically correct in isolation). Resolution requires either:
1. Upgrading the Atlas cluster tier, **or**
2. Pointing `MONGO_URL` at a local Mongo instance for test runs.

### Deferred (future sprints)
T005 system/ split, T006 huge page splits, T007 per-tenant rate limit, T008 self-service export UI, T009 stripe/b2b refactors, T012 lazy router loading, T013 stub page polish. See `.local/session_plan.md`.
