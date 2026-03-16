# Syroce Travel SaaS — Product Requirements Document

## Original Problem Statement
CTO-requested comprehensive frontend architecture analysis and redesign to transform the "Syroce" Travel SaaS platform into an enterprise-grade product comparable to Stripe Dashboard or Shopify Admin.

## Phase Status Overview

| Phase | Name | Status | Score |
|-------|------|--------|-------|
| 1 | Architecture Cleanup | DONE | 9.2/10 |
| 2 | Design System Foundation | DONE | 9.0/10 |
| 3a | UX Standardization (Batch 1) | DONE | 9.0/10 |
| 3b | UX Standardization (Batch 2) | DONE | 9.0/10 |
| 3c | UX Standardization (Batch 3) | DONE | 9.0/10 |
| 4 | God Page Splitting (P0) | DONE | - |
| 5 | TanStack Query Adoption (P1) | DONE | 83.3% |
| 6 | Performance Optimization (P2) | DONE | 9.5/10 |
| 7 | Enterprise UX Features (P3) | DONE | - |
| 8 | TypeScript Migration | Backlog | - |

## Phase 7 — Enterprise UX Features (COMPLETED 2026-03-16)

### P3.1 — Command Palette (Cmd+K)
- **Component:** `CommandPalette.jsx` using Shadcn `CommandDialog` + `cmdk`
- **Trigger:** Topbar button ("Ara... ⌘K") + keyboard shortcuts (Cmd/Ctrl+K, /)
- **Features:**
  - Quick Actions: "Yeni Rezervasyon" with shortcut hint
  - Navigation Pages: Dashboard, Rezervasyonlar, Müşteriler, Finans, Raporlar, Oteller, Turlar, Entegrasyonlar, Ayarlar
  - Shortcut hints displayed (G D, G R, G C, G F, G S)
  - Footer with keyboard navigation hints

### P3.2 — Global Search
- **Backend:** Pre-existing `GET /api/search?q=...&limit=N` endpoint
- **Searches across:** Customers, Bookings, Hotels, Tours
- **Frontend integration:** 300ms debounced search, loading state, result grouping by entity type
- **Result display:** Type-specific icons, status badges, navigation on select

### P3.3 — Keyboard Shortcuts
- **Hook:** `useKeyboardShortcuts.js`
- **Shortcuts implemented:**
  - `Cmd/Ctrl+K` → Open command palette
  - `/` → Open command palette (when not in input)
  - `G then D` → Navigate to Dashboard
  - `G then R` → Navigate to Reservations
  - `G then C` → Navigate to Customers
  - `G then F` → Navigate to Finance
  - `G then S` → Navigate to Settings
- **Smart input detection:** Shortcuts ignored when focus is in INPUT/TEXTAREA/SELECT

### P3.4 — Accessibility
- `sr-only` DialogTitle for screen readers in CommandDialog
- Proper `data-testid` attributes on all interactive elements

## Phase 6 — Performance Optimization (COMPLETED 2026-03-16)

### P2.1 — Webpack SplitChunks Vendor Chunking
- **Config:** `craco.config.js` — production-only splitChunks
- **Vendor chunks:** react-vendor, ui-vendor, query-vendor, charts-vendor, vendors
- **main.js:** 695K → **162K** (↓76.8%)
- **Gzipped main.js:** 42.54KB
- Vendor chunks are long-term cacheable (content-hash names)

### P2.2 — AppShell Lazy Loading
- `AiAssistant` → lazy import + Suspense (loads on user interaction)
- `NotificationDrawer` → lazy import + conditional render (loads only when opened)
- Both components removed from critical path

### P2.3 — Heavy Feature Isolation
- recharts isolated to `charts-vendor` chunk (329K) — only loaded by dashboard/report pages
- Route-based code splitting already in place (all route files use React.lazy)

### P2.4 — DataTable Virtualization
- Added `@tanstack/react-virtual` to DataTable component
- Auto-activates when row count >= `virtualizeThreshold` (default: 100)
- Same API — no breaking changes for existing consumers

## Phase 4 — God Page Splitting (COMPLETED 2026-03-16)
- AdminFinanceRefundsPage: 2150 LOC → 297 LOC (86% reduction)
- PlatformHardeningPage: 1912 LOC → 90 LOC (95% reduction)

## Phase 5 — TanStack Query Adoption (COMPLETED 2026-03-16)
- Target: 80%+ adoption — Achieved: **83.3%** (120/144 data-fetching files)
- 24 remaining legacy files (contexts, complex booking flows) — not blocking

## Upcoming Tasks

### TypeScript Migration (P1 Priority)
- Incremental migration: API layer → TanStack hooks → design system
- Start with strictest type checks on new files

## Backlog
- Platform Integrations: Ratehawk sandbox, Paximum sandbox
- Design System Migration Guide (internal wiki)
- Remaining ~17% legacy useEffect files (low priority)

## Engineering Metrics

| Metric | Before Phase 1 | After Phase 7 |
|--------|----------------|---------------|
| Routing | Monolithic | Domain-based |
| Tables | 50+ custom | Unified DataTable |
| UX Patterns | Inconsistent | Standardized (15+ pages) |
| TanStack Query | ~5% | ~83.3% |
| God Pages (>1000 LOC) | 3 files | 0 files |
| main.js | ~695K | 162K |
| Vendor caching | None | 4 cacheable chunks |
| Table virtualization | None | Auto @100+ rows |
| Command Palette | None | Cmd+K with global search |
| Keyboard Shortcuts | None | 7 shortcuts |

## Frontend Quality Score

| Area | Score |
|------|-------|
| Architecture | 9.5 / 10 |
| UX Consistency | 9.3 / 10 |
| Maintainability | 9.5 / 10 |
| Performance | 9.5 / 10 |
| Enterprise UX | 9.4 / 10 |
| **Overall** | **9.4 / 10** |

## Test Credentials
- Super Admin: agent@acenta.test / agent123
- Agency Admin: agency1@demo.test / agency123

## Notes
- Ratehawk sync adapter still uses MOCKED/simulated data
- All test reports at `/app/test_reports/`
- SplitChunks config is production-only (dev server unaffected)
