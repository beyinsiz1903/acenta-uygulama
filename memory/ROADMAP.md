# Syroce — ROADMAP

## P0 — In Progress: Frontend Architecture Refactoring
- [x] Phase 1: Route Splitting (App.js 598→189 lines, 6 domain modules)
- [x] Phase 2: Design System (DataTable, PageShell, FilterBar, StatusBadge, ConfirmDialog, Timeline, EmptyState)
- [ ] Phase 3: UX Standardization (migrate pages to new patterns, god page splitting)
- [ ] Phase 4: Performance (code splitting, virtualization, memoization)
- [ ] Phase 5: Enterprise UX (Cmd+K, global search, shortcuts, timeline)

## P1 — Near-Term
- [ ] Migrate top 10 pages to DataTable + PageShell + FilterBar
- [ ] Split 5 god pages (>1000 LOC) into sub-components
- [ ] TanStack Query adoption for remaining pages (currently 5%)
- [ ] Real Ratehawk Sandbox Validation (CTO provides credentials)

## P2 — Medium-Term
- [ ] Paximum Sandbox & Reliability Engine
- [ ] TypeScript migration (incremental, start with design-system/)
- [ ] Bundle analysis + tree-shaking audit
- [ ] Search Caching & Optimization
- [ ] Agency Behavior Personalization

## P3 — Backlog
- [ ] Command palette (Cmd+K) using cmdk
- [ ] Global search with unified results
- [ ] Keyboard shortcuts framework
- [ ] Activity timeline on entity pages
- [ ] Notification system (SSE + drawer)
- [ ] Tenant switcher in top bar
- [ ] Permission-aware navigation refactor
- [ ] SaaS Pricing Model infrastructure
- [ ] Prometheus / Grafana metrics export

## Completed
- [x] Core Platform (Auth, Multi-tenancy, RBAC)
- [x] Production Hardening (Security, Reliability, Monitoring)
- [x] Multi-Tenant Supplier Integration
- [x] Supplier Adapter Pattern + Aggregator
- [x] Unified Booking & Fallback Layer
- [x] Commercial Booking Experience Layer
- [x] Smart Search & Supplier Intelligence Layer
- [x] Revenue & Supplier Optimization Engine
- [x] Frontend Architecture Phase 1 (Route Splitting)
- [x] Frontend Architecture Phase 2 (Design System)
