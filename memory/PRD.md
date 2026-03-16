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
| 6 | Performance Optimization (P2) | Planned | - |
| 7 | Enterprise UX Features (P3) | Planned | - |
| 8 | TypeScript Migration | Backlog | - |

## Phase 4 — God Page Splitting (COMPLETED 2026-03-16)

### AdminFinanceRefundsPage
- **Before:** 2150 LOC monolithic file
- **After:** 297 LOC slim orchestrator
- **Reduction:** 86%
- **Components extracted:** 8

Structure:
```
features/refunds/
  api.js                              - API layer (all refund ops)
  hooks.js                            - TanStack Query hooks
  utils.js                            - CSV export, helpers
  components/
    RefundBadges.jsx                  - Status/priority badges
    RefundQueueList.jsx               - Queue list with filters
    RefundDetailPanel.jsx             - Full detail view
    RefundDialogs.jsx                 - Approve/Reject/MarkPaid dialogs
    RefundDocuments.jsx               - Document management + PDF preview
    RefundTasks.jsx                   - Task management
    MiniRefundHistory.jsx             - Booking refund history
    BulkOperationsCard.jsx            - Bulk operations
    FilterPresetsBar.jsx              - Filter presets
```

### PlatformHardeningPage
- **Before:** 1912 LOC monolithic file
- **After:** 90 LOC slim orchestrator
- **Reduction:** 95%
- **Tab groups extracted:** 5 files

Structure:
```
features/platform-hardening/
  api.js                              - useHardeningApi + API calls
  helpers.js                          - Shared badge/status helpers
  components/
    ScoreGauge.jsx                    - Reusable gauge component
    OverviewExecutionTabs.jsx         - Overview, Execution, Certification
    InfrastructureTabs.jsx            - Traffic, Workers (with 10 sub-tabs)
    MonitoringTabs.jsx                - Observability, Performance, Tenant, Secrets
    OperationsTabs.jsx                - Playbooks, Scaling, DR, Checklist
    ActivationTabs.jsx                - 8 go-live/activation tabs
```

## Upcoming Tasks

### P1 — TanStack Query Adoption (COMPLETED 2026-03-16)
- Target: 80%+ adoption — Achieved: **83.3%** (120/144 data-fetching files)
- ~108 files migrated across pages, components, and contexts
- Patterns: useQuery for data fetching, useMutation for mutations, useQueryClient for cache invalidation
- 24 remaining legacy files (contexts, complex booking flows) — not blocking
- Regression tested: All migrated pages verified working (test_reports/iteration_111.json)

### P2 — Performance (Phase 6)
- Route-based code splitting
- Virtualized tables (large datasets)
- Bundle size reduction

### P3 — Enterprise UX (Phase 7)
- Cmd+K command palette
- Global search
- Keyboard shortcuts
- Activity timeline

## Backlog
- TypeScript Migration (API → hooks → design system)
- Platform Integrations (Ratehawk sandbox, Paximum sandbox)
- Design System Migration Guide (internal wiki)

## Engineering Metrics

| Metric | Before Phase 1 | After Phase 4 |
|--------|----------------|---------------|
| Routing | Monolithic | Domain-based |
| Tables | 50+ custom | Unified DataTable |
| UX Patterns | Inconsistent | Standardized (15+ pages) |
| TanStack Query | ~5% | ~83.3% |
| God Pages (>1000 LOC) | 3 files | 0 files |

## Test Credentials
- Super Admin: agent@acenta.test / agent123
- Agency Admin: agency1@demo.test / agency123

## Notes
- Ratehawk sync adapter still uses MOCKED/simulated data
- All test reports at `/app/test_reports/`
