# Finance Features Plan (Agentis Parity)

## 1) Objectives
- Achieve Agentis parity for finance flows end-to-end in one version (backend + frontend)
- P0: Settlements, Commission calculation, Voucher
- P1: Self-billing PDF (informational), Payment status tracking, Booking financial summary
- P2: Allotment/Release (soft, no financial impact), Agency reports (date-filtered KPIs)
- P3: Hotel financial dashboard (aggregate KPIs)
- Constraints: TRY currency, NO VAT for v1, hotel-level single commission%, commission snapshot at booking creation, manual payment_status (unpaid/partially_paid/paid)

## 2) Scope & Rules (Authoritative)
- Pricing model: Gross price from hotel; agency earns commission on gross; no markup
- Commission configuration: agency-hotel single %; stored in agency_hotel_financials
- Snapshot rule: commission% and amounts written at booking creation to financial_snapshot; later changes don’t alter past bookings
- Voucher (v1): applied at booking creation; affects gross before snapshot; later edits not allowed (keeps scope simple)
- Self-billing PDF: informational only, “Bu belge bilgi amaçlıdır, resmi fatura yerine geçmez.” note included
- Payment tracking: manual; booking-level status only (unpaid/partially_paid/paid)
- Allotment/Release: soft only; no financial coupling in v1

## 3) Phase 1 — Core POC (Decision)
- Complexity level: 2 (internal logic + existing auth) → POC NOT REQUIRED
- Quick sanity validations (no separate script):
  1) Compute commission snapshot at booking creation using stored commission% and voucher discount
  2) Ensure snapshot stays immutable after commission% changes
  3) Generate informational self-billing PDF for a booking
  4) Update payment_status and reflect in summaries
  5) Aggregate settlement totals by date range and booking IDs
- Phase 1 User Stories:
  - As an agency_admin, I want booking creation to store a financial_snapshot with gross/commission/net.
  - As a hotel_admin, I want a settlement calculation to include only bookings within a selected date range.
  - As an agency_admin, I want an informational PDF for a booking showing commission/net amounts.
  - As a finance user, I want voucher to reduce gross before commission is calculated at creation.
  - As an operator, I want to manually mark a booking’s payment_status and see it reflected in totals.

## 4) Phase 2 — Main App Development (All features)
### 4.1 Backend Implementation (FastAPI + Mongo)
- Collections/Models (extend if already exist):
  - agency_hotel_financials: {agency_id, hotel_id, commission_percent}
  - bookings: add financial_snapshot {currency:"TRY", gross_total, commission_percent, commission_amount, net_to_hotel, voucher: {code, type, value}, created_at}
  - vouchers: {code, type:"percent"|"amount", value, status:"active"|"inactive", valid_from, valid_to, usage_limit, used_count, created_by}
  - settlements: {agency_id, hotel_id, period_start, period_end, booking_ids, totals:{gross, commission, net, paid, unpaid}, status:"open"|"finalized", created_at}
  - payments (embedded under booking): {records:[{amount, note, at}], payment_status}
- Endpoints (/api prefix):
  - Commission config: GET/POST /api/agency/commission-config (by agency_id+hotel_id)
  - Booking create/update: on create compute financial_snapshot; block post-create voucher edits
  - Booking finance: GET /api/bookings/{id}/financial-summary; PATCH /api/bookings/{id}/payment-status
  - Vouchers: CRUD + POST /api/vouchers/validate-apply (at creation)
  - Settlements: POST /api/settlements/preview, POST /api/settlements/finalize, GET /api/settlements/{id}
  - Self-billing PDF: GET /api/self-billing/{booking_id}/pdf (ReportLab)
  - Agency Reports: GET /api/reports/agency/summary?date_from&date_to
  - Hotel Dashboard: GET /api/hotel/dashboard/financial?date_from&date_to
  - Allotment/Release (soft): minimal GET/POST to store non-financial notes/states
- Business rules & validations:
  - Snapshot immutability; commission% resolved from agency_hotel_financials at creation
  - Voucher validation (active, date window, usage limit)
  - Payment_status ENUM guard
- PDF generation:
  - Use reportlab (pure Python) to avoid system deps; simple header, totals, disclaimer text
- Serialization helpers:
  - Ensure ObjectId/datetime safe JSON (serialize_doc)

### 4.2 Frontend Implementation (React + shadcn/ui)
- Booking Detail: Financial Summary card (Brüt, Komisyon %, Komisyon Tutarı, Otele Net, Ödeme Durumu); action: Update payment_status; Generate Self-billing PDF
- Booking Creation: Voucher code entry; on validate-apply shows discounted gross before confirm
- Settlements (Agency + Hotel): 
  - Filter by agency/hotel + date range; preview list of bookings with totals; finalize and store
  - Export/print-friendly view
- Voucher Management: CRUD grid (status badges, validity, usage)
- Agency Reports: KPIs (Toplam rezervasyon, Toplam brüt satış, Toplam komisyon, Paid/Unpaid) with month and custom range filters
- Hotel Financial Dashboard: KPIs (Toplam rezervasyon, Toplam brüt satış, Acenta kırılımı, Paid/Unpaid)
- All pages include loading/error states and data-testid on interactive elements
- Routes: use existing shells (AgencyLayout/HotelLayout) and pages under /app/agency and /app/hotel

### 4.3 Testing (testing_agent_v3)
- Backend tests: commission snapshot, voucher validation, payment_status transitions, settlement preview/finalize, reports/dashboard aggregates, PDF endpoint 200 + non-empty bytes
- Frontend tests: 
  - Booking Detail shows Financial Summary; payment_status update persists
  - Voucher apply during creation updates preview totals
  - Settlements preview totals match backend; finalize persists
  - Agency report KPIs match dataset; filters work
  - Hotel dashboard KPIs load; acenta breakdown visible
- Skip camera/drag features by design

### 4.4 Phase 2 User Stories
- As an agency_admin, I can configure commission% per hotel and see it used when creating bookings.
- As a booking agent, I can apply a voucher during booking creation and see updated gross before confirmation.
- As a finance user, I can preview a settlement for a period and finalize it, storing booking references and totals.
- As a hotel_admin, I can see a financial dashboard with paid/unpaid breakdown and acenta-based totals.
- As an operator, I can download an informational self-billing PDF from the booking page.
- As an agency_admin, I can mark payment_status and watch totals adjust in reports/settlements.
- As a manager, I can view agency reports with month/custom-date filters showing core KPIs.

## 5) Phase 3 — Hardening & Enhancements (post-MVP)
- Voucher post-create amendments via adjustments (keep original snapshot; add delta lines)
- More filters/exports (CSV) for reports and settlements
- Role-based fine-grained permissions on finance endpoints
- Performance: pre-aggregated collections for dashboards
- Future P2+: room-rateplan-level commissions, overdue/refunds, multi-currency, VAT
- Phase 3 User Stories:
  - As finance, I can export CSVs for settlements and report KPIs.
  - As admin, I can audit changes to payment_status and settlements.
  - As manager, I can schedule monthly auto-generated PDFs for settlements.
  - As ops, I can see performance improved on large date ranges via cached aggregates.
  - As admin, I can edit voucher usage limits safely with audit log.

## 6) Implementation Steps (Execution Plan)
1) Backend: add models + endpoints; integrate snapshot on booking creation; add PDF generation (reportlab)
2) Frontend: implement Finance Summary card, Voucher in creation, Settlements UI, Reports, Hotel Dashboard
3) Lint (Python/JS), restart if deps change (reportlab), verify logs
4) Call design_agent for UI polish and apply
5) End-to-end tests via testing_agent_v3; fix issues; re-test

## 7) Next Actions
- Proceed directly to Phase 2 build (POC not required)
- Install backend dep: reportlab
- Request design guidelines via design_agent; then bulk implement BE/FE
- Run testing_agent_v3 with defined scenarios; iterate until green

## 8) Success Criteria
- P0/P1/P2/P3 features implemented and usable via UI with consistent backend
- Booking creation persists immutable financial_snapshot; voucher applied at creation only
- Self-billing PDF endpoint returns a valid file with disclaimer
- Payment_status transitions persist and affect aggregates
- Settlements preview/finalize work; totals accurate for selected date range
- Agency reports and Hotel dashboard show correct KPIs with filters
- All interactive elements have data-testid; /api prefix respected; no env hardcoding
