# Syroce — Travel ERP Platform — PRD

## Product Overview
Syroce is a production-grade Turkish travel ERP platform that manages the full lifecycle of travel agency operations: supplier management, booking engine, pricing engine, revenue/growth engine, invoice/e-document engine, accounting sync, and financial operations.

## Current Platform Layers
1. **Supplier Ecosystem** (Score: 10/10)
2. **Booking Engine** (Score: 9.9/10)
3. **Revenue Engine** (Score: 9.8/10)
4. **Invoice Engine** (Score: 9.8/10)
5. **E-Document Layer** (Score: 9.7/10)
6. **Accounting Sync Layer** (Score: 9.6/10)
7. **Accounting Automation Layer** (Score: 9.7/10)
8. **Reconciliation & Finance Ops Layer** (Score: NEW — MEGA PROMPT #33)

## Core Requirements

### Authentication
- JWT-based auth with role-based access control
- Roles: super_admin, admin, finance_admin, agency_admin

### Booking Engine
- Multi-supplier booking with pricing, commissions
- Status management: pending → confirmed → completed

### Invoice Engine
- Auto invoice generation from bookings
- E-Invoice (e-Fatura) and E-Archive support
- GIB integration (simulated)

### Accounting Sync Layer (MEGA PROMPT #31)
- Luca accounting provider integration (simulated)
- Sync invoices to accounting system
- Sync logs and status tracking

### Accounting Automation Layer (MEGA PROMPT #32) ✅
- Customer matching with VKN/TCKN/email/phone + match_confidence scores
- Accounting sync queue with retry backoff (5m, 15m, 1h, 6h, 24h)
- Auto-sync rule engine (triggers: invoice_issued, invoice_approved, booking_confirmed, manual_trigger)
- Background scheduler (APScheduler) for queue processing
- Enhanced dashboard with 6 KPIs and 3 tabs

### Reconciliation & Finance Operations Layer (MEGA PROMPT #33) ✅
- **Reconciliation Engine**: Booking vs Invoice vs Accounting comparison
  - Mismatch types: missing_invoice, amount_mismatch, tax_mismatch, missing_sync, sync_amount_mismatch, duplicate_entry, customer_mismatch, status_mismatch
  - Severity: critical, high, medium, low (CTO-defined rules)
  - Source of truth tracking per mismatch
  - Age bucket tracking (0_1h, 1_6h, 6_24h, gt_24h)
- **Scheduler**: Hourly incremental + Daily full reconciliation + Alert check every 30min
- **Finance Operations Queue**: Priority-based manual intervention
  - Resolution states: open, claimed, in_progress, resolved, escalated, ignored
  - RBAC: super_admin/finance_admin full access, agency_admin view + note + request retry/escalation
  - Audit trail on all actions
- **Financial Alerts**: Automated alerts for high fail rate, reconciliation mismatches, aging
  - Severity: critical, warning, info
  - Acknowledge/resolve workflow

## Technical Architecture

### Backend
- FastAPI + MongoDB + Redis (graceful fallback)
- APScheduler for background jobs
- Collection prefix for tenant isolation

### Frontend
- React + Shadcn UI
- Page routing via React Router
- Admin pages: Dashboard, Accounting, Finance Ops, E-Fatura, Settings

### Key Collections (MEGA PROMPT #33)
- `reconciliation_runs` - Run history (incremental/full/manual)
- `reconciliation_items` - Individual mismatch records
- `finance_ops_queue` - Manual intervention queue
- `financial_alerts` - Alert records

### Key API Endpoints (MEGA PROMPT #33)
- `GET /api/reconciliation/summary` - Dashboard summary
- `GET /api/reconciliation/aging` - Aging KPI
- `POST /api/reconciliation/run` - Trigger manual run
- `GET /api/reconciliation/runs` - List runs
- `GET /api/reconciliation/items` - List mismatches
- `GET /api/reconciliation/ops` - List ops queue
- `POST /api/reconciliation/ops/{claim|resolve|escalate|note|retry}` - Queue actions
- `GET /api/reconciliation/alerts` - List alerts
- `POST /api/reconciliation/alerts/{acknowledge|resolve}` - Alert actions

## What's Mocked
- **LucaIntegrator**: Accounting provider returns simulated responses
- **Redis**: FATAL (graceful fallback, cache operations silently fail)

## Credentials
- Super Admin: admin@acenta.test / agent123
- Agency Admin: agency1@demo.test / agency123

## Upcoming Tasks (P1 — MEGA PROMPT #34+)
- Multi-Provider Architecture (Logo, Paraşüt, Mikro adapters)
- Automated correction workflows for reconciliation mismatches
- Accounting anomaly detection (advanced patterns)
- Pilot agency integration with real traffic
- Real supplier API credentials (replace mocked LucaIntegrator)

## Future Tasks (P2+)
- Full financial analytics dashboard
- Tax reporting
- Payment/refund tracking integration
- CI/CD pipeline stability improvements
