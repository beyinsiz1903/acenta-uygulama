# Acenta Master — Plan (Agentis+)

Problem Summary
- Build an Agentis-like (and more capable) travel agency automation + online reservation + B2B (sub‑agency) platform.
- Tech: React + shadcn/ui, FastAPI, MongoDB. All backend routes prefixed with /api. JWT auth. Single-tenant now, multi-tenant ready (organization_id on all data).
- Syroce PMS integration deferred for later; architecture must allow easy plug-in.

POC Decision (Level Assessment)
- Level 2 (CRUD + JWT). No external integrations in v1 → POC step is skipped. Go straight to Phase 2 (Main App) with strong incremental testing.

Phases
- Phase 1: Core POC (Isolation) — SKIPPED (no ext. integration in v1). Do quick smoke checks for auth and CRUD during development.
- Phase 2: Main App Development — deliver full admin panel + minimal public booking + B2B portal subset; comprehensive testing via testing agent.

1) Objectives
- End-to-end booking workflow: Product → Price/Inventory → Reservation → Manual Payment Record → Voucher (printable).
- CRM + Lead→Quote→Sale pipeline.
- B2B (sub‑agency) minimal flow: agent login, discount/commission group, create reservation.
- Reports: basic sales and reservation summaries.
- Settings: firm profile, users/roles, org-level config. Multi-tenant ready via organization_id.

2) Implementation Steps (Phase 2)
A. Backend (FastAPI + MongoDB)
- Foundation
  - JWT auth (/api/auth/login). Seed admin user (email admin@acenta.test / pass admin123). Role model: admin, sales, ops, accounting, b2b_agent.
  - Mongo helpers: serialize_doc for ObjectId/datetime; pagination; audit fields (created_at, updated_at, created_by, organization_id).
  - Error model & consistent responses. All endpoints under /api.
- Data Model (collections)
  - organizations: {name, settings}
  - users: {email, password_hash, roles, organization_id}
  - customers: {name, email, phone, notes, organization_id}
  - products: {type: tour|activity|accommodation|transfer, title, description, media[], attributes{}, organization_id}
  - rate_plans: {product_id, name, seasons[], actions[], currency, taxes, organization_id}
  - inventory: {product_id, date, capacity_total, capacity_available, price, extras[], restrictions{}, organization_id}
  - reservations: {pnr, product_id, date(s), pax, customer_id, price_breakdown, status, voucher_no, b2b_agent_id?, payments[], documents[], organization_id}
  - quotes: {lead_id?, items[], total, status, converted_reservation_id?, organization_id}
  - leads: {source, customer_ref, notes, status, organization_id}
  - payments: {reservation_id, method, amount, currency, status, reference, organization_id}
  - agencies: {name, commission_group_id, discount_group_id, organization_id}
  - agents: {agency_id, user_id, organization_id}
  - discount_groups: {name, rules[], organization_id}
  - commission_groups: {name, percent, rules?, organization_id}
- Endpoints (CRUD + actions)
  - /api/auth: POST /login
  - /api/customers: CRUD
  - /api/products: CRUD; filter by type
  - /api/rateplans: CRUD; link to product
  - /api/inventory: CRUD; bulk upsert by date range
  - /api/reservations: CRUD; POST /reserve (validate inventory, price calc), POST /:id/confirm, POST /:id/cancel, GET /:id/voucher
  - /api/leads, /api/quotes: CRUD; POST /quotes/:id/convert → reservation
  - /api/payments: POST manual payment record; mark paid/failed; link to reservation
  - /api/b2b: agencies, agents, discount/commission groups; POST /b2b/book
  - /api/reports: GET sales-summary (by day, by channel), GET reservations-summary (status counts)
  - /api/settings: firm profile; users (admin‑only)
- Business Rules (v1)
  - Reservation creates and consumes inventory atomically; idempotency key for create.
  - Price = rate plan base + season/actions; allow simple flat discount for B2B.
  - Voucher number generator (e.g., ACN-YYYYMM-XXXX). Printable HTML.
  - Manual payment only (record method/ref). Future: payment gateway plug-in.
  - All queries scoped by organization_id.

B. Frontend (React + shadcn/ui)
- App shell: Login → Dashboard (KPIs: today reservations, revenue, availability alerts).
- Core pages (all with data-testid):
  - Products: list/create/edit; type-specific fields minimal (dates, capacity source).
  - Pricing: rate plans + seasons + actions.
  - Inventory/Calendar: per product date grid (capacity, price, restrictions); quick edit.
  - Reservations: list, create (select product/date/pax), detail (status, payments, voucher).
  - CRM: customers CRUD; Leads board (kanban) → Quote builder → Convert to reservation.
  - B2B: Agent login (separate route), product list with discount, create reservation.
  - Reports: Sales summary charts/tables; export CSV basic.
  - Settings: firm profile, users/roles.
- Public booking (optional minimal): /book/:productId → date picker from inventory → create reservation (status=pending).
- API client uses REACT_APP_BACKEND_URL + /api; auth bearer from login; loading/error states; optimistic UI where safe.

C. Quality & Ops
- Add data-testid to all interactive elements.
- Logging: backend structured logs; frontend error boundaries for API failures.
- Seed script: ensure admin user & sample org exist at startup if empty.

User Stories (Phase 2)
1) As an admin, I can log in and see today’s reservations and revenue on the dashboard.
2) As a product manager, I can create a tour product and attach rate plans with seasonal pricing.
3) As an ops user, I can set inventory for a date range and mark close-to-arrival on specific dates.
4) As a sales user, I can create a reservation that decrements availability and generates a voucher.
5) As accounting, I can record a manual payment with a reference and mark it paid.
6) As a CRM user, I can turn a lead into a quote and convert that quote into a reservation.
7) As a B2B agent, I can log in, see my net prices/discount, and place a reservation.
8) As an admin, I can define a commission group for an agency and see commission amounts on reservations.
9) As a manager, I can view a sales summary report by day and export it.
10) As an admin, I can invite a new user, assign roles, and they can access permitted modules only.
11) As a user, I can print/download a voucher from a reservation detail page.
12) As a user, I can cancel a reservation and inventory returns to availability.

Testing Plan (Phase 2)
- Use testing_agent_v3 (both backend + frontend) to verify:
  1) Auth: invalid vs valid login; token usage on protected routes.
  2) Product→RatePlan→Inventory→Reservation end-to-end; inventory decrement; duplicate-create idempotency.
  3) Lead→Quote→Convert flow produces a reservation and closes the quote.
  4) Payment record creation updates reservation balance; status transitions.
  5) B2B agent login and discounted booking; commission visible to admin.
  6) Reports endpoints return non-empty aggregated data after bookings.
  7) Settings role gating (non-admin blocked from user management).
- Skip camera/drag/drop/audio. Validate UI via data-testid selectors. Fix all reported issues before sign-off.

3) Next Actions
- Generate UI design guidelines via design_agent (shadcn/ui theme, layout, components).
- Implement backend models + auth + core CRUD (products, rateplans, inventory, reservations) first.
- Implement frontend pages for the same in parallel; wire API; ensure /api prefix and env vars used.
- Add B2B basics (agencies/agents, discount/commission) and minimal agent portal.
- Add CRM (customers, leads), quotes, and conversion.
- Add reports and voucher print view.
- Run testing agent E2E; iterate until green.

4) Success Criteria
- End-to-end booking with inventory + pricing works reliably; voucher printable; manual payment recorded.
- Lead→Quote→Reservation flow works; B2B agent can book with discount/commission recorded.
- All API routes under /api; env vars used (MONGO_URL, REACT_APP_BACKEND_URL); backend bound to 0.0.0.0:8001.
- No red screen errors; no unhandled 5xx in logs; all interactive elements have data-testid.
- Testing agent scenarios pass; data persists in Mongo; role gating enforced; organization_id present on all data.

Notes for Future (Post‑v1)
- Plug-in Syroce PMS integration (rates/availability/reservations sync) with polling/webhooks + idempotency.
- Payment provider integration (iyzico/stripe) and e‑Fatura (Paraşüt) via dedicated playbooks + POC.
- Multi-tenant UI (org switcher), theming, advanced reports/BI, media uploads, PDFs.
