# Syroce — Travel ERP Platform — PRD

## Product Overview
Syroce is a production-grade Turkish travel ERP platform that manages the full lifecycle of travel agency operations: supplier management, booking engine, pricing engine, revenue/growth engine, invoice/e-document engine, accounting sync, financial operations, and multi-provider accounting architecture.

## Current Platform Layers
1. **Supplier Ecosystem** (Score: 10/10)
2. **Booking Engine** (Score: 9.9/10)
3. **Revenue Engine** (Score: 9.8/10)
4. **Invoice Engine** (Score: 9.8/10)
5. **E-Document Layer** (Score: 9.7/10)
6. **Accounting Sync Layer** (Score: 9.6/10)
7. **Accounting Automation Layer** (Score: 9.7/10)
8. **Reconciliation & Finance Ops Layer** (Score: 9.8/10) — MEGA PROMPT #33
9. **Multi Accounting Provider Architecture** (Score: NEW) — MEGA PROMPT #34

## Core Requirements

### Authentication
- JWT-based auth with role-based access control
- Roles: super_admin, admin, finance_admin, agency_admin

### Multi Accounting Provider Architecture (MEGA PROMPT #34) - IMPLEMENTED
- **Base Provider Contract**: Abstract class with 7 methods (test_connection, create_customer, get_customer, create_invoice, cancel_invoice, get_invoice_status, download_invoice_pdf)
- **Normalized Response**: ProviderResponse with success, external_ref, status, error_code, error_message, raw_payload
- **4 Provider Adapters**:
  - Luca (ACTIVE): Full implementation with simulation fallback
  - Logo (STUB): Contract + capability matrix defined
  - Parasut (STUB): Contract + capability matrix defined
  - Mikro (STUB): Contract + capability matrix defined
- **Capability Matrix**: Per-provider feature support (customer_management, invoice_creation, invoice_cancel, status_polling, pdf_download, webhook_support, rate_limit)
- **Provider Routing**: Tenant-level provider selection (one tenant = one active provider)
- **Credential Management**: AES-256-GCM encrypted storage, rotation, validation, masking
- **Provider Health Monitoring**: Per-request tracking (latency, error rate, success rate), aggregated metrics (1h/24h)
- **Failover Strategy**: retry → queue → manual intervention (NOT cross-provider failover)
- **Admin Frontend**: Provider selection cards, credential form, test connection, health dashboard

### Reconciliation & Finance Operations Layer (MEGA PROMPT #33) - IMPLEMENTED
- Reconciliation Engine: Booking vs Invoice vs Accounting comparison
- Finance Operations Queue: Priority-based manual intervention with RBAC
- Financial Alerts: Automated alerts for high fail rate, mismatches, aging

### Accounting Automation Layer (MEGA PROMPT #32) - IMPLEMENTED
- Customer matching with VKN/TCKN/email/phone + match_confidence scores
- Accounting sync queue with retry backoff
- Auto-sync rule engine
- Background scheduler (APScheduler)

## Technical Architecture

### Backend
- FastAPI + MongoDB + Redis
- APScheduler for background jobs
- AES-256-GCM credential encryption
- Collection prefix for tenant isolation

### Frontend
- React + Shadcn UI
- Page routing via React Router
- Admin pages: Dashboard, Accounting, Accounting Providers, Finance Ops, E-Fatura, Settings

### Key Collections (MEGA PROMPT #34)
- `accounting_provider_configs` - Tenant→provider mapping with encrypted credentials and health metrics
- `accounting_provider_health_events` - Per-request health events for analytics

### Key API Endpoints (MEGA PROMPT #34)
- `GET /api/accounting/providers/catalog` - List all providers with capabilities
- `GET /api/accounting/providers/catalog/active` - List active providers only
- `GET /api/accounting/providers/catalog/{code}` - Provider detail
- `POST /api/accounting/providers/config` - Configure tenant provider
- `GET /api/accounting/providers/config` - Get current tenant config
- `DELETE /api/accounting/providers/config` - Remove provider config
- `POST /api/accounting/providers/test-connection` - Test provider connection
- `POST /api/accounting/providers/rotate-credentials` - Rotate credentials
- `GET /api/accounting/providers/health` - Health dashboard with metrics

## What's Mocked
- **LucaProvider**: Simulation mode when real Luca API is unreachable
- **Logo/Parasut/Mikro**: Stub providers returning ERR_UNSUPPORTED
- **Redis**: Running (was FATAL, now fixed)

## Credentials
- Super Admin: admin@acenta.test / admin123
- Agency Admin: agency1@demo.test / agency123

## Upcoming Tasks (P1 — MEGA PROMPT #35+)
- Pilot agency integration with real traffic
- Real supplier API credentials (activate Logo/Parasut/Mikro adapters)
- Automated correction workflows for reconciliation mismatches
- Accounting anomaly detection

## Future Tasks (P2+)
- Full financial analytics dashboard
- Tax reporting module
- Payment/refund tracking integration
- CI/CD pipeline stability improvements
- APScheduler → Celery Beat migration
- Multi-provider fallback (e.g., Luca → Logo when needed)

## Redis Status
- **Fixed**: Redis installed and running on port 6379
- Used by: customer matching cache, rate limiting, search caching, sync queue
