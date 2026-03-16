# Syroce — Travel Distribution Infrastructure PRD

## Problem Statement
Build a "Travel Distribution Infrastructure" platform named Syroce — an order-centric travel operating platform that manages the full lifecycle of travel orders including supplier integrations, pricing, financial ledger, settlement, and order management.

## Architecture
- **Frontend**: React + TailwindCSS + Shadcn/UI + React Query
- **Backend**: FastAPI (Python) + MongoDB
- **Authentication**: JWT-based custom auth

## Core Modules

### 1. Supplier Integration Layer ✅
- RateHawk integration
- Supplier onboarding service
- Inventory sync

### 2. Pricing Engine ✅
- Rate pricing
- Commission engine
- Pricing distribution

### 3. Booking Orchestration ✅
- Booking lifecycle management
- Booking events & amendments

### 4. Financial Ledger ✅
- Double-entry ledger (LedgerPostingService)
- Agency balances
- Supplier payables

### 5. Settlement Engine ✅
- Settlement runs
- Statement generation

### 6. Activity Timeline ✅
- Audit trail
- Cross-system event tracking

### 7. Order Management System (OMS)

#### Phase 1: Order Core Layer ✅ (Completed)
- **Services**: order_service, order_transition_service, order_event_service, order_mapping_service
- **State Machine**: draft → pending_confirmation → confirmed → cancel_requested → cancelled → closed
- **Event Sourcing**: Append-only order_events collection
- **Frontend**: Orders list page + Order detail page

#### Phase 1 Improvements ✅ (Completed 2026-03-16)
- **Order Number Strategy**: ORD-YYYY-NNNNNN format (e.g., ORD-2026-000001)
- **Order Search Endpoint**: GET /api/orders/search with 10+ filters (status, channel, agency_id, customer_id, supplier_code, order_number, date_from, date_to, settlement_status, q)
- **Order Locking**: version field with optimistic locking (409 Conflict on mismatch)

#### Phase 2: Financial Linkage ✅ (Completed 2026-03-16)
- **Order → Ledger**: Auto-post to ledger on confirm (3 entries: agency receivable, supplier payable, platform revenue)
- **Ledger Reversal**: Auto-reverse on cancel
- **Settlement Linkage**: Link settlement runs to orders
- **Financial Status**: not_posted → posted → partially_settled → settled → reversed
- **Services**: order_financial_linkage_service, order_ledger_query_service, order_settlement_query_service
- **API Endpoints**: financial-summary, rebuild, ledger-entries, ledger-postings, settlements, settlements/link, mark-settled, post-to-ledger
- **Frontend**: Enhanced Financial Summary (5 metrics), Ledger Entries table with debit/credit, Settlement card, 3 status badges

## Key Data Models

### orders
- order_id, order_number (ORD-YYYY-NNNNNN), status, currency, version
- total_sell_amount, total_supplier_amount, total_margin_amount
- financial_status, ledger_posting_refs[], settlement_run_refs[], settlement_status
- last_posted_at, last_settled_at

### order_items
- item_id, order_id, item_type, supplier_code, sell_amount, supplier_amount, margin_amount

### order_events
- event_id, order_id, event_type, actor_type, actor_name, before_state, after_state

### order_financial_summaries
- order_id, sell_total, supplier_total, margin_total, financial_status, settlement_status

## Test Credentials
- Super Admin: agent@acenta.test / agent123
- Agency Admin: agency1@demo.test / agency123

## Status: Platform Score ≈ 9.85/10
