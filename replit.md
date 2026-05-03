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

### FX
- **`b2b_hotels_search`** now uses `FXService.get_rate` (per-currency cache inside the loop, graceful 1:1 fallback on lookup failure).

### Deferred (future sprints)
T004 alert→toast, T005 system/ split, T006 huge page splits, T007 per-tenant rate limit, T008 self-service export UI, T009 stripe/b2b refactors, T011 skipped tests, T012 lazy router loading, T013 stub page polish. See `.local/session_plan.md`.
