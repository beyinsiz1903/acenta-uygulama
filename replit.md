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

| Admin Portal Mgmt | `admin_portal_management.py` | (integrated in CustomerPortal) | `/api/admin/support-tickets`, `/api/admin/cancel-requests` |

New MongoDB collections: `transfers`, `guides`, `vehicles`, `flights`, `visa_applications`, `insurance_policies`, `email_templates`, `portal_sessions`, `support_tickets`, `cancel_requests`

### Cross-Module Integrations (Phase 3 Gaps Fixed)

- **Customer Portal**: Admin support ticket listing/management + cancel request approve/reject endpoints
- **Transfer → Vehicle/Guide**: Assign-vehicle and assign-guide buttons with dropdown selectors in Transfer page
- **Transfer → Booking**: `booking_id` field in transfer creation form
- **Visa/Insurance → CRM**: Searchable customer dropdown fetching from `/crm/customers` instead of plain text ID input
- **Flight → Passengers**: Passenger list modal with add/remove capability on each flight
- **Guide → Calendar/Rating**: Calendar modal showing guide assignments + star rating modal
- **Vehicle → Maintenance**: Maintenance record viewer + add form; calendar modal for vehicle assignments
- **Calendar → Detail/Create**: Click event to see detail modal; click day for quick-create shortcuts to Transfer/Flight/Visa/Insurance
- **Email Templates → Outbox**: `email_template_resolver.py` service resolves templates by `trigger_key` with variable substitution; wired into `enqueue_booking_email` with fallback to hardcoded HTML
