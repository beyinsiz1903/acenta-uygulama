# SYROCE FRONTEND ARCHITECTURE — Analysis & Redesign Blueprint

**Date:** February 2026
**Scope:** Full frontend codebase audit + enterprise-grade architecture proposal
**Benchmark:** Stripe Dashboard, Shopify Admin, Linear, Vercel Console

---

## TABLE OF CONTENTS

1. [STEP 1 — Full Repository Analysis](#step-1--full-repository-analysis)
2. [STEP 2 — Frontend Architecture Redesign](#step-2--frontend-architecture-redesign)
3. [STEP 3 — Design System Creation](#step-3--design-system-creation)
4. [STEP 4 — Component Governance](#step-4--component-governance)
5. [STEP 5 — UX Standardization](#step-5--ux-standardization)
6. [STEP 6 — Data Fetching Architecture](#step-6--data-fetching-architecture)
7. [STEP 7 — Performance Optimization](#step-7--performance-optimization)
8. [STEP 8 — Enterprise UX Features](#step-8--enterprise-ux-features)
9. [STEP 9 — Multi-Tenant UX](#step-9--multi-tenant-ux)
10. [STEP 10 — Frontend Roadmap](#step-10--frontend-roadmap)

---

# STEP 1 — FULL REPOSITORY ANALYSIS

## 1.1 Current Folder Structure

```
/app/frontend/src/
├── api/                    # 3 files — partial API layer (marketLaunch, operations, scalability)
├── b2b/                    # 4 files — B2B portal (layout, auth guard, login, 3 pages)
├── components/             # 108 files — flat + 7 subdirs (admin, b2b, landing, marketing, ops, settings, usage, ui/)
│   ├── ui/                 # 48 shadcn/radix primitives (button, card, dialog, table, etc.)
│   ├── admin/              # 2 files
│   ├── b2b/                # 1 file (PricingPreviewDialog — 925 lines!)
│   ├── landing/            # 2 files
│   ├── marketing/          # 4 files
│   ├── ops/                # 1 file
│   ├── settings/           # settings components
│   └── usage/              # usage components
├── config/                 # 3 files — feature catalog, plans, menu config
├── contexts/               # 3 files — Feature, I18n, ProductMode
├── hooks/                  # 6 files — useAuth, useDashboard, useReservations, useSeo, useTours, use-toast
├── layouts/                # 4 files — Admin, Agency, Hotel, HotelSettlements
├── lib/                    # 38 files — everything (api, auth, billing, crm, format, roles, navigation, etc.)
├── nav/                    # 3 files — adminNav, agencyNav, hotelNav
├── pages/                  # 193 files — flat + 8 subdirs
│   ├── admin/              # 35 files (largest: PlatformHardeningPage 1912 lines)
│   ├── agency/             # 1 file (UnifiedSearchPage 1257 lines)
│   ├── crm/                # 6 files
│   ├── marketplace/        # 1 file
│   ├── ops/                # 2 files
│   ├── partners/           # 7 files
│   ├── public/             # 10 files
│   └── storefront/         # 3 files
├── theme/                  # 1 file — useTheme.js
├── utils/                  # 7 files — formatters, booking status, copy text, etc.
├── App.js                  # 598 lines — all routes defined here
├── index.css               # 162 lines — CSS variables, Tailwind base
└── index.js                # Entry point
```

### Key Metrics

| Metric | Count |
|--------|-------|
| Total source lines | **101,864** |
| Page components | **193** |
| Shared components | **108** |
| Hooks | **6** |
| Context providers | **3** |
| API layer files | **3** (partial) |
| Lib utility files | **38** |
| Files > 500 lines | **29** |
| Files > 1000 lines | **12** |
| Largest file | **2,150 lines** (AdminFinanceRefundsPage) |

---

## 1.2 Page Architecture

### Routing

All 193+ routes are defined in a single `App.js` (598 lines) with 4 top-level route groups:

| Route Group | Auth Guard | Layout | Count |
|-------------|-----------|--------|-------|
| `/app/admin/*` | `RequireAuth(super_admin, admin)` | `AppShell > AdminLayout` | ~85 routes |
| `/app/*` | `RequireAuth(multi-role)` | `AppShell` | ~45 routes |
| `/app/agency/*` | `RequireAuth(agency_*)` | `AppShell > AgencyLayout` | ~18 routes |
| `/app/hotel/*` | `RequireAuth(hotel_*)` | `AppShell > HotelLayout` | ~6 routes |
| `/b2b/*` | `B2BAuthGuard` | `B2BLayout` | 3 routes |
| Public | None | None | ~25 routes |

**Issue:** App.js is a monolithic route file. Every new page requires modifying this single file. No route-level code ownership. No typed route definitions.

### Layout Hierarchy

```
BrowserRouter
└── Suspense (PageLoader)
    └── Routes
        ├── PublicHomePage (no shell)
        ├── LoginPage (no shell)
        ├── RequireAuth + AppShell
        │   ├── AdminLayout → Admin pages
        │   ├── AgencyLayout → Agency pages
        │   ├── HotelLayout → Hotel pages
        │   └── Core pages (Dashboard, CRM, etc.)
        ├── B2BAuthGuard + B2BLayout → B2B pages
        └── NotFoundPage
```

---

## 1.3 Component Hierarchy

### Shared Component Analysis

| Component | Usage Count | Purpose |
|-----------|------------|---------|
| `PageHeader` | 25 pages | Page title + breadcrumbs |
| `StatCard` | 47 instances | KPI cards |
| `EmptyState` | 76 instances | Empty data views |
| `ErrorState/ErrorCard` | 40 instances | Error displays |
| `Skeleton` | 47 instances | Loading placeholders |
| Shadcn UI primitives | Throughout | Base design system |

### Problems

1. **God Components:** 12 files exceed 1000 lines. `PlatformHardeningPage` is 1912 lines. These contain embedded sub-components, inline API calls, local state machines, and UI all in one file.
2. **No DataTable abstraction:** Tables are hand-built in every page — `<Table>` + manual pagination + manual sorting + manual filtering. Estimated 50+ pages build their own tables.
3. **Drawer/Dialog inconsistency:** `BookingDetailDrawer` (1414 lines), `OpsGuestCaseDrawer` (954 lines) are monolithic. No standard drawer pattern.
4. **No standardized form pattern:** Forms mix react-hook-form and manual useState. No form builder or validation pattern.

---

## 1.4 State Management Patterns

| Pattern | Usage | Location |
|---------|-------|----------|
| Local `useState` + `useEffect` (fetch in effect) | **536 direct API calls in pages** | Throughout all pages |
| TanStack Query (`useQuery/useMutation`) | **9 instances in pages, 22 in hooks** | Only 6 hooks use it |
| Context API | 3 providers | Feature, I18n, ProductMode |
| URL state (search params) | Partial | Dashboard, some list pages |
| localStorage | Session, sidebar collapse, filters | Scattered |

### Critical Issue: TanStack Query Underutilization

TanStack Query is installed and configured but used in only **~5% of data fetching**. The remaining 95% uses raw `useEffect + useState + api.get()` patterns:

```jsx
// CURRENT PATTERN (95% of pages):
const [data, setData] = useState([]);
const [loading, setLoading] = useState(true);
const [error, setError] = useState(null);

useEffect(() => {
  const load = async () => {
    try {
      const res = await api.get("/some/endpoint");
      setData(res.data);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  };
  load();
}, []);
```

This means: no caching, no background refetch, no stale-while-revalidate, no optimistic updates, no deduplication, no shared cache between pages.

---

## 1.5 API Integration Patterns

### Current API Layer

```
lib/api.js          → axios instance + interceptors (415 lines, monolithic)
lib/crm.js          → CRM-specific API helpers
lib/billing.js      → Billing API helpers
lib/settlements.js  → Settlement API helpers
lib/partnerGraph.js → Partner API helpers
api/marketLaunch.js → Market launch helpers
api/operations.js   → Operations helpers
api/scalability.js  → Scalability helpers
```

### Issues

1. **No centralized API layer**: API calls are scattered across 193+ page files (536 direct `api.get/post` calls in pages)
2. **Inconsistent response handling**: Some pages unwrap `res.data`, others use the full response
3. **No typed API contracts**: No TypeScript, no Zod validation of API responses
4. **Two separate API directories** (`/api/` and `/lib/`) with no clear boundary
5. **Error messages hardcoded in Turkish** in `api.js`

---

## 1.6 UX Inconsistencies

| Area | Issue |
|------|-------|
| **Loading states** | 947 loading references but no unified skeleton pattern. Some pages show spinners, others show skeletons, others show nothing |
| **Empty states** | 78 instances, but each page hand-crafts its own empty state text and icon |
| **Error handling** | 1531 error references but no global error boundary. Each page catches and displays errors differently |
| **Tables** | 2626 table references across pages. No DataTable component. Each builds its own sorting, filtering, pagination |
| **Modals/Dialogs** | 706 modal references. No standard modal sizes, no standard form-in-dialog pattern |
| **Page headers** | Only 25 of 193 pages use the shared `PageHeader` component |
| **Navigation** | 1038-line `appNavigation.js` defines all nav structure. Complex mode/role/feature filtering logic |

---

## 1.7 Design System Gaps

### What Exists (Shadcn/UI — 48 primitives)

Accordion, AlertDialog, Alert, Avatar, Badge, Breadcrumb, Button, Calendar, Card, Carousel, Checkbox, Collapsible, Command, ContextMenu, Dialog, Drawer, DropdownMenu, Form, HoverCard, Input, InputOTP, Label, Menubar, NavigationMenu, Pagination, Popover, Progress, RadioGroup, Resizable, ScrollArea, Select, Separator, Sheet, Skeleton, Slider, Sonner, Switch, Table, Tabs, Textarea, Toast, Toaster, ToggleGroup, Toggle, Tooltip

### What's Missing (Enterprise Gaps)

| Missing | Impact |
|---------|--------|
| **DataTable** | Every page rebuilds table logic (sorting, filtering, pagination, row selection, column visibility) |
| **PageShell** | Standard page layout wrapper (header + content + sidebar) |
| **FormBuilder** | Standard form layout with validation, sections, conditional fields |
| **StatCard variants** | Different stat card types (trend, comparison, sparkline) |
| **FilterBar** | Reusable filter/search bar for list pages |
| **ConfirmDialog** | Standard confirmation dialog |
| **StatusBadge** | Semantic status indicators (booking status, payment status) |
| **Timeline** | Activity/audit timeline component |
| **EmptyState variants** | Search empty, data empty, error empty, onboarding empty |
| **CommandMenu** | Global command palette (cmdk is installed but unused beyond basic) |

---

## 1.8 Reusable vs Duplicated Components

### Reusable (Good)
- `PageHeader` — used in 25 pages
- `StatCard` — used in 47 instances
- `EmptyState` — used in 76 instances
- `ThemeToggle`, `ThemeProvider`
- `RequireAuth`
- All Shadcn UI primitives

### Duplicated (Bad)
- **Table patterns**: 50+ pages build their own table with sorting/pagination
- **CRUD patterns**: Every admin page reimplements list + create + edit + delete
- **API loading pattern**: `useState(loading) + useEffect(fetch)` repeated 536 times
- **Filter bars**: Multiple pages build their own filter UI
- **Drawer content**: Large drawers with embedded forms repeated per domain
- **Status color mapping**: Booking status → color mapping duplicated in 10+ files

---

## 1.9 Performance Bottlenecks

| Issue | Impact | Severity |
|-------|--------|----------|
| **No route-based code splitting for admin sub-routes** | All admin pages in one chunk | HIGH |
| **100K+ lines in single SPA** | Large initial parse time | HIGH |
| **No virtualized tables** | Pages with 1000+ rows (bookings, users) render all rows | HIGH |
| **No memoization strategy** | Components re-render on every parent state change | MEDIUM |
| **Inline style objects** | 73 inline `style={{}}` create new objects every render | LOW |
| **No React.memo on list items** | Table rows, sidebar items re-render unnecessarily | MEDIUM |
| **No image optimization** | No lazy loading, no next-gen formats | MEDIUM |
| **No bundle analyzer** | Unknown bundle composition | MEDIUM |

---

## 1.10 Technical Debt Areas

| Area | Debt | Priority |
|------|------|----------|
| **Monolithic App.js** | 598 lines, all routes in one file | P0 |
| **God Pages** | 12 files over 1000 lines, 29 over 500 lines | P0 |
| **No TypeScript** | Entire codebase is JavaScript, no type safety | P1 |
| **TanStack Query unused** | Installed but only 5% adoption | P1 |
| **No DataTable** | 50+ hand-built tables | P1 |
| **Inconsistent API layer** | Direct api calls in 536 places in pages | P1 |
| **Duplicate nav configs** | `appNavigation.js` (1038 lines) + `/nav/` directory + `/config/menuConfig.js` | P2 |
| **No form standard** | Mix of react-hook-form and manual state | P2 |
| **CSS variable mismatch** | `design_guidelines.json` defines colors that differ from `index.css` | P2 |
| **Dead code** | Multiple test pages, duplicate routes | P3 |

---

# STEP 2 — FRONTEND ARCHITECTURE REDESIGN

## 2.1 Target Architecture: Domain-Driven Frontend

```
/src
├── app/                          # Application shell & routing
│   ├── App.tsx                   # Root component (minimal: providers + router)
│   ├── router.tsx                # Centralized route definitions
│   ├── providers.tsx             # All provider wrappers (Query, Theme, I18n, Feature, etc.)
│   └── layouts/                  # Shell layouts
│       ├── AppShell.tsx          # Authenticated shell (sidebar + topbar + main)
│       ├── AdminLayout.tsx       # Admin sub-layout
│       ├── AgencyLayout.tsx      # Agency sub-layout
│       ├── HotelLayout.tsx       # Hotel sub-layout
│       ├── B2BLayout.tsx         # B2B portal layout
│       └── PublicLayout.tsx      # Public/marketing layout
│
├── design-system/                # Syroce Design System (SDS)
│   ├── primitives/               # Atomic UI components (Shadcn + custom)
│   │   ├── Button.tsx
│   │   ├── Input.tsx
│   │   ├── Select.tsx
│   │   ├── Dialog.tsx
│   │   ├── Table.tsx
│   │   └── ...
│   ├── patterns/                 # Composed UI patterns
│   │   ├── DataTable.tsx         # Sortable, filterable, paginated table
│   │   ├── PageShell.tsx         # Standard page wrapper (header + content)
│   │   ├── FormSection.tsx       # Form layout with sections
│   │   ├── FilterBar.tsx         # Reusable search + filter bar
│   │   ├── StatCard.tsx          # KPI cards with variants
│   │   ├── StatusBadge.tsx       # Semantic status indicator
│   │   ├── EmptyState.tsx        # Empty state with variants
│   │   ├── ConfirmDialog.tsx     # Standard confirmation pattern
│   │   ├── DetailDrawer.tsx      # Standard detail drawer pattern
│   │   └── Timeline.tsx          # Activity/audit timeline
│   └── tokens/                   # Design tokens
│       ├── colors.css            # CSS custom properties
│       ├── typography.css        # Font scales
│       └── spacing.css           # Spacing scale
│
├── features/                     # Domain modules (DDD bounded contexts)
│   ├── auth/                     # Authentication
│   │   ├── api.ts                # Auth API layer
│   │   ├── hooks.ts              # useLogin, useLogout, useCurrentUser
│   │   ├── components/           # LoginForm, RequireAuth, etc.
│   │   └── pages/                # LoginPage, ResetPasswordPage
│   │
│   ├── dashboard/                # Dashboard & KPIs
│   │   ├── api.ts
│   │   ├── hooks.ts
│   │   ├── components/
│   │   └── pages/
│   │
│   ├── bookings/                 # Booking/Reservation management
│   │   ├── api.ts
│   │   ├── hooks.ts
│   │   ├── components/
│   │   │   ├── BookingDetailDrawer.tsx
│   │   │   ├── BookingStatusBadge.tsx
│   │   │   └── BookingTable.tsx
│   │   └── pages/
│   │       ├── ReservationsPage.tsx
│   │       ├── BookingNewPage.tsx
│   │       └── BookingConfirmedPage.tsx
│   │
│   ├── inventory/                # Inventory & Supplier management
│   │   ├── api.ts
│   │   ├── hooks.ts
│   │   ├── components/
│   │   └── pages/
│   │       ├── InventoryPage.tsx
│   │       ├── InventorySyncDashboardPage.tsx
│   │       └── SupplierCredentialsPage.tsx
│   │
│   ├── finance/                  # Finance, settlements, refunds
│   │   ├── api.ts
│   │   ├── hooks.ts
│   │   ├── components/
│   │   └── pages/
│   │
│   ├── crm/                      # Customer relationship management
│   │   ├── api.ts
│   │   ├── hooks.ts
│   │   ├── components/
│   │   └── pages/
│   │
│   ├── b2b/                      # B2B portal
│   │   ├── api.ts
│   │   ├── hooks.ts
│   │   ├── components/
│   │   └── pages/
│   │
│   ├── operations/               # Ops tasks, guest cases, incidents
│   │   ├── api.ts
│   │   ├── hooks.ts
│   │   ├── components/
│   │   └── pages/
│   │
│   ├── admin/                    # Admin-only features
│   │   ├── api.ts
│   │   ├── hooks.ts
│   │   ├── components/
│   │   └── pages/
│   │
│   ├── analytics/                # Reporting & analytics
│   │   ├── api.ts
│   │   ├── hooks.ts
│   │   └── pages/
│   │
│   ├── governance/               # Audit logs, approvals, policies
│   │   ├── api.ts
│   │   ├── hooks.ts
│   │   └── pages/
│   │
│   └── storefront/               # Public booking & storefront
│       ├── api.ts
│       ├── hooks.ts
│       └── pages/
│
├── shared/                       # Cross-cutting shared utilities
│   ├── api/                      # Base API client & interceptors
│   │   ├── client.ts             # Axios instance + interceptors
│   │   └── types.ts              # Shared API types
│   ├── hooks/                    # Cross-domain hooks
│   │   ├── useDebounce.ts
│   │   ├── usePagination.ts
│   │   └── useLocalStorage.ts
│   ├── contexts/                 # Global contexts
│   │   ├── FeatureContext.tsx
│   │   ├── I18nContext.tsx
│   │   └── ProductModeContext.tsx
│   ├── config/                   # Feature flags, nav config
│   │   ├── navigation.ts
│   │   └── featureFlags.ts
│   ├── lib/                      # Pure utility functions
│   │   ├── format.ts
│   │   ├── date.ts
│   │   ├── roles.ts
│   │   └── validation.ts
│   └── types/                    # Shared TypeScript types
│       ├── booking.ts
│       ├── user.ts
│       └── supplier.ts
│
└── styles/                       # Global styles
    └── globals.css               # Tailwind directives + CSS variables
```

### Why Each Layer Exists

| Layer | Purpose | Rule |
|-------|---------|------|
| `app/` | Application bootstrapping, routing, layouts | Only wiring — no business logic |
| `design-system/` | Visual components, independent of business logic | Zero business imports. Can be extracted to a package |
| `features/` | Domain-specific modules (bounded contexts) | Each feature owns its API, hooks, components, pages. Features can import from `design-system/` and `shared/`, but NOT from other features |
| `shared/` | Cross-cutting concerns | Only pure utilities and configurations. No UI components |
| `styles/` | Global CSS | Tailwind config + CSS variables only |

### Dependency Rules (Critical)

```
features/X  →  design-system/  ✅
features/X  →  shared/         ✅
features/X  →  features/Y      ❌  (Cross-feature communication via shared events or URL)
design-system/ → shared/lib    ✅
design-system/ → features/     ❌
shared/     →  features/       ❌
```

---

# STEP 3 — DESIGN SYSTEM CREATION

## 3.1 Syroce Design System (SDS) — Token Foundation

### Color Tokens

```css
/* /src/styles/globals.css */

:root {
  /* --- Semantic Colors (Light) --- */
  --sds-bg:            210 20% 99%;
  --sds-fg:            222 47% 11%;
  --sds-surface:       0 0% 100%;
  --sds-surface-raised: 210 40% 98%;
  --sds-muted:         210 40% 96%;
  --sds-muted-fg:      215 16% 47%;
  --sds-border:        214 32% 91%;
  --sds-border-strong: 214 20% 80%;

  /* --- Brand --- */
  --sds-primary:       221 83% 53%;
  --sds-primary-fg:    210 40% 98%;
  --sds-accent:        199 89% 48%;
  --sds-accent-fg:     210 40% 98%;

  /* --- Semantic States --- */
  --sds-success:       151 55% 32%;
  --sds-success-muted: 151 40% 95%;
  --sds-warning:       35 92% 45%;
  --sds-warning-muted: 35 70% 93%;
  --sds-danger:        0 84% 60%;
  --sds-danger-muted:  0 60% 95%;
  --sds-info:          199 89% 48%;
  --sds-info-muted:    199 60% 95%;

  /* --- Spacing Scale (4px base) --- */
  --sds-space-1:  0.25rem;   /* 4px */
  --sds-space-2:  0.5rem;    /* 8px */
  --sds-space-3:  0.75rem;   /* 12px */
  --sds-space-4:  1rem;      /* 16px */
  --sds-space-5:  1.25rem;   /* 20px */
  --sds-space-6:  1.5rem;    /* 24px */
  --sds-space-8:  2rem;      /* 32px */
  --sds-space-10: 2.5rem;    /* 40px */
  --sds-space-12: 3rem;      /* 48px */
  --sds-space-16: 4rem;      /* 64px */

  /* --- Radius --- */
  --sds-radius-sm: 0.375rem;  /* 6px */
  --sds-radius-md: 0.5rem;    /* 8px */
  --sds-radius-lg: 0.75rem;   /* 12px */
  --sds-radius-xl: 1rem;      /* 16px */
  --sds-radius-full: 9999px;
}

.dark {
  --sds-bg:            224 30% 6%;
  --sds-fg:            210 40% 98%;
  --sds-surface:       224 28% 9%;
  --sds-surface-raised: 224 25% 12%;
  --sds-muted:         223 22% 14%;
  --sds-muted-fg:      220 12% 70%;
  --sds-border:        223 20% 18%;
  --sds-border-strong: 223 16% 28%;
}
```

### Typography Scale

```
Font Pairing:
  Headings: Manrope (600-800)
  Body:     Inter (400-600)
  Mono:     Roboto Mono (400-500)

Scale:
  Display:   text-4xl (36px) / leading-tight / tracking-tight / font-bold
  H1:        text-2xl (24px) / leading-tight / tracking-tight / font-bold
  H2:        text-xl (20px) / leading-snug / font-semibold
  H3:        text-lg (18px) / leading-snug / font-semibold
  H4:        text-base (16px) / font-semibold
  Body:      text-sm (14px) / leading-relaxed / font-normal
  Caption:   text-xs (12px) / font-medium
  Micro:     text-2xs (10px) / font-medium / uppercase / tracking-wider
```

## 3.2 Core Primitives — Implementation Specs

### Button

```tsx
// design-system/primitives/Button.tsx
import { cva, type VariantProps } from "class-variance-authority"

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg text-sm font-medium transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default:     "bg-primary text-primary-foreground shadow hover:bg-primary/90 active:scale-[0.98]",
        destructive: "bg-destructive text-destructive-foreground shadow-sm hover:bg-destructive/90",
        outline:     "border border-input bg-background shadow-sm hover:bg-accent hover:text-accent-foreground",
        secondary:   "bg-secondary text-secondary-foreground shadow-sm hover:bg-secondary/80",
        ghost:       "hover:bg-accent hover:text-accent-foreground",
        link:        "text-primary underline-offset-4 hover:underline",
      },
      size: {
        xs:      "h-7 px-2 text-xs rounded-md",
        sm:      "h-8 px-3 text-xs",
        default: "h-9 px-4",
        lg:      "h-10 px-6",
        xl:      "h-11 px-8 text-base",
        icon:    "h-9 w-9",
        "icon-sm": "h-7 w-7",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

// Props: variant, size, asChild, loading, disabled
// Loading state: shows spinner + disables interaction
// Accessibility: proper aria-disabled, aria-busy when loading
```

### DataTable (Most Critical Missing Component)

```tsx
// design-system/patterns/DataTable.tsx
interface DataTableProps<T> {
  data: T[]
  columns: ColumnDef<T>[]
  loading?: boolean
  emptyState?: React.ReactNode
  // Pagination
  pageSize?: number
  totalCount?: number
  page?: number
  onPageChange?: (page: number) => void
  // Sorting
  sortable?: boolean
  defaultSort?: { column: string; direction: "asc" | "desc" }
  onSortChange?: (sort: SortState) => void
  // Filtering
  searchable?: boolean
  searchPlaceholder?: string
  onSearchChange?: (query: string) => void
  filters?: FilterDef[]
  // Selection
  selectable?: boolean
  onSelectionChange?: (rows: T[]) => void
  // Actions
  bulkActions?: BulkAction[]
  rowActions?: (row: T) => React.ReactNode
  // Export
  exportable?: boolean
  onExport?: (format: "csv" | "xlsx") => void
}

// Implementation:
// - Uses @tanstack/react-table internally
// - Renders Shadcn <Table> primitives
// - Loading: skeleton rows
// - Empty: configurable EmptyState
// - Pagination: bottom bar with page size selector
// - Responsive: horizontal scroll on mobile, priority column hiding
```

### PageShell (Standard Page Wrapper)

```tsx
// design-system/patterns/PageShell.tsx
interface PageShellProps {
  title: string
  description?: string
  breadcrumbs?: Breadcrumb[]
  actions?: React.ReactNode         // Top-right action buttons
  tabs?: TabDef[]                    // Page-level tabs
  children: React.ReactNode
  loading?: boolean                  // Shows skeleton for entire page
  className?: string
}

// Implementation:
// - Consistent page header with title, description, breadcrumbs
// - Action buttons area (Create, Export, etc.)
// - Optional tab bar below header
// - Consistent spacing and max-width
// - Loading state shows title skeleton + content skeleton
```

### FilterBar

```tsx
// design-system/patterns/FilterBar.tsx
interface FilterBarProps {
  search?: {
    placeholder: string
    value: string
    onChange: (value: string) => void
  }
  filters?: FilterDef[]
  activeFilterCount?: number
  onReset?: () => void
  actions?: React.ReactNode           // Additional toolbar actions
}

// Implementation:
// - Search input with debounce
// - Filter dropdowns (select, date range, multi-select)
// - Active filter chips with remove
// - Reset all button
// - Responsive: collapses to filter sheet on mobile
```

### StatusBadge

```tsx
// design-system/patterns/StatusBadge.tsx
const STATUS_VARIANTS = {
  // Booking
  pending:    { color: "warning",  label: "Beklemede",   dot: true },
  confirmed:  { color: "info",     label: "Onaylandı",   dot: true },
  paid:       { color: "success",  label: "Ödendi",      dot: true },
  cancelled:  { color: "danger",   label: "İptal",       dot: true },
  // System
  healthy:    { color: "success",  label: "Sağlıklı",    dot: true },
  degraded:   { color: "warning",  label: "Bozulmuş",    dot: true },
  down:       { color: "danger",   label: "Çökmüş",      dot: true },
  // Generic
  active:     { color: "success" },
  inactive:   { color: "muted" },
  draft:      { color: "muted" },
}

// Props: status (keyof STATUS_VARIANTS), size: "sm" | "md", showDot?: boolean
```

### EmptyState Variants

```tsx
// design-system/patterns/EmptyState.tsx
interface EmptyStateProps {
  variant?: "default" | "search" | "error" | "no-permission" | "onboarding"
  icon?: LucideIcon
  title: string
  description?: string
  action?: {
    label: string
    onClick: () => void
    variant?: ButtonVariant
  }
  secondaryAction?: { label: string; onClick: () => void }
}
```

### ConfirmDialog

```tsx
// design-system/patterns/ConfirmDialog.tsx
interface ConfirmDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  title: string
  description: string
  variant?: "default" | "destructive"
  confirmLabel?: string
  cancelLabel?: string
  onConfirm: () => void | Promise<void>
  loading?: boolean
}
```

### Timeline

```tsx
// design-system/patterns/Timeline.tsx
interface TimelineEvent {
  id: string
  timestamp: Date
  title: string
  description?: string
  user?: { name: string; avatar?: string }
  type: "created" | "updated" | "status_change" | "comment" | "system"
  metadata?: Record<string, string>
}

interface TimelineProps {
  events: TimelineEvent[]
  loading?: boolean
  emptyText?: string
}
```

---

# STEP 4 — COMPONENT GOVERNANCE

## 4.1 Decision Framework: When to Create What

```
┌─────────────────────────────────────────────────────────────┐
│                  Component Decision Tree                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Is it used in 3+ features?                                 │
│  ├── YES → design-system/patterns/                          │
│  └── NO                                                     │
│      ├── Is it a UI primitive (no business logic)?          │
│      │   ├── YES → design-system/primitives/                │
│      │   └── NO                                             │
│      │       ├── Is it used in 2+ pages of SAME feature?   │
│      │       │   ├── YES → features/X/components/           │
│      │       │   └── NO  → Inline in the page file         │
│      │       └───────────────────────────────────────────── │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 4.2 Naming Conventions

| Type | Convention | Example |
|------|-----------|---------|
| Design system primitive | `PascalCase.tsx` | `Button.tsx`, `Input.tsx` |
| Design system pattern | `PascalCase.tsx` | `DataTable.tsx`, `PageShell.tsx` |
| Feature component | `FeaturePascalCase.tsx` | `BookingStatusBadge.tsx` |
| Feature page | `PascalCasePage.tsx` | `ReservationsPage.tsx` |
| API layer | `camelCase.ts` | `bookings.api.ts` |
| Hook | `usePascalCase.ts` | `useBookings.ts` |
| Utility | `camelCase.ts` | `formatCurrency.ts` |
| Type definition | `PascalCase.types.ts` | `Booking.types.ts` |

## 4.3 Folder Structure Rules

```
features/bookings/
├── api.ts               # All API calls for this feature
├── hooks.ts             # All TanStack Query hooks for this feature
├── types.ts             # TypeScript interfaces
├── components/          # Feature-local components
│   ├── BookingTable.tsx  # Uses design-system DataTable
│   ├── BookingForm.tsx
│   └── BookingStatusBadge.tsx
└── pages/               # Route-level components (lazy loaded)
    ├── ReservationsPage.tsx
    ├── BookingNewPage.tsx
    └── BookingDetailPage.tsx
```

## 4.4 Anti-Duplication Rules

1. **If a component file exceeds 300 lines**, it MUST be split into sub-components
2. **If a pattern is copy-pasted 3+ times**, it MUST be extracted to `design-system/patterns/`
3. **If an API call is made from 2+ pages**, it MUST be moved to `features/X/api.ts`
4. **If a `useState` + `useEffect` fetch pattern appears**, replace with TanStack Query hook in `features/X/hooks.ts`
5. **No inline style objects** — use Tailwind classes or CSS variables exclusively

---

# STEP 5 — UX STANDARDIZATION

## 5.1 Dashboard Layout Pattern

```
┌──────────────────────────────────────────────────────────────────┐
│ PageShell: title="Dashboard" actions=[DateRangePicker, Export]   │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │ KPI Card │ │ KPI Card │ │ KPI Card │ │ KPI Card │           │
│  │ Gelir    │ │ Rez.     │ │ Müşteri  │ │ Trend    │           │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
│                                                                  │
│  ┌─────────────────────────────┐ ┌───────────────────────────┐  │
│  │ Chart: Revenue Trend        │ │ Chart: Booking Funnel     │  │
│  │ (ResponsiveContainer)       │ │ (ResponsiveContainer)     │  │
│  └─────────────────────────────┘ └───────────────────────────┘  │
│                                                                  │
│  ┌─────────────────────────────┐ ┌───────────────────────────┐  │
│  │ Widget: Recent Bookings     │ │ Widget: Pending Tasks     │  │
│  │ (Compact DataTable)         │ │ (Task List)               │  │
│  └─────────────────────────────┘ └───────────────────────────┘  │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

## 5.2 CRUD Page Pattern (List → Create → Edit → Detail)

### List Page

```
┌──────────────────────────────────────────────────────────────────┐
│ PageShell: title="Rezervasyonlar" actions=[+ Yeni Rezervasyon]   │
├──────────────────────────────────────────────────────────────────┤
│ FilterBar: [Search] [Status ▼] [Date Range] [Agency ▼] [Reset] │
├──────────────────────────────────────────────────────────────────┤
│ DataTable:                                                       │
│ ☐ │ Ref    │ Müşteri      │ Otel        │ Tarih  │ Tutar │ ...│
│ ☐ │ #1234  │ Ali Demir    │ Kaya Palace │ 12 Mar │ ₺4.5K │ ...│
│ ☐ │ #1235  │ Ayşe Yılmaz  │ Blue Sky    │ 13 Mar │ ₺2.1K │ ...│
│   │        │              │             │        │       │     │
│ ← 1 2 3 ... 12 →                    Toplam: 248 │ 20/sayfa ▼ │
└──────────────────────────────────────────────────────────────────┘
```

### Create/Edit: Dialog for simple, Full Page for complex

```
Simple (< 5 fields): Dialog/Sheet
Complex (> 5 fields, multi-step): Full page with FormSection components

Every form:
  - zod validation schema
  - react-hook-form controller
  - Loading state on submit button
  - Error messages below fields
  - Cancel navigates back
  - Success toast + redirect
```

## 5.3 Table Interaction Standards

| Feature | Standard |
|---------|----------|
| Sort | Click column header. Arrow indicator. Server-side for > 100 rows |
| Filter | FilterBar above table. Active filters as chips |
| Search | Debounced (300ms). Searches across display columns |
| Pagination | Bottom bar. Page size: [10, 20, 50]. Show total count |
| Selection | Checkbox column. Bulk actions bar appears on selection |
| Row click | Navigate to detail or open drawer. Cursor pointer |
| Actions | Three-dot menu (DropdownMenu) per row |
| Empty | EmptyState component in table body |
| Loading | Skeleton rows (match column widths) |
| Export | CSV/Excel button in page actions |

## 5.4 Modal/Dialog Standards

| Size | Width | Use Case |
|------|-------|----------|
| `sm` | 400px | Confirmation, single input |
| `md` | 500px | Simple form (3-5 fields) |
| `lg` | 640px | Complex form, detail view |
| `xl` | 800px | Multi-section form, comparison |
| `full` | Sheet | Long forms, complex workflows |

Rules:
- Close on Escape key
- Close on backdrop click (except when dirty form)
- Focus trap within modal
- Loading overlay on submit
- Destructive actions: red variant confirm button

## 5.5 Error Handling UX

```
┌─────────────────────────────────────────────────────┐
│ Level 1: Field-level (inline validation)             │
│ → Red border + error text below field                │
│                                                      │
│ Level 2: Form-level (API error)                      │
│ → Alert banner above form                            │
│                                                      │
│ Level 3: Page-level (data fetch error)               │
│ → ErrorState component with retry button             │
│                                                      │
│ Level 4: Global (network error, 500)                 │
│ → Sonner toast with correlation ID + retry           │
│                                                      │
│ Level 5: Critical (auth expired)                     │
│ → Redirect to login with session_expired             │
└─────────────────────────────────────────────────────┘
```

## 5.6 Loading Skeleton Standards

- **Page load:** Full page skeleton (PageShell skeleton + content skeletons)
- **Table load:** Skeleton rows matching column count and approximate widths
- **Card load:** Skeleton matching card layout (icon + text + value)
- **Chart load:** Skeleton rectangle with rounded corners
- **Drawer load:** Skeleton for header + sections

---

# STEP 6 — DATA FETCHING ARCHITECTURE

## 6.1 TanStack Query Adoption Plan

### Query Key Strategy

```ts
// shared/api/queryKeys.ts

export const queryKeys = {
  // Namespace by feature
  bookings: {
    all:     ["bookings"] as const,
    lists:   () => [...queryKeys.bookings.all, "list"] as const,
    list:    (filters: BookingFilters) => [...queryKeys.bookings.lists(), filters] as const,
    details: () => [...queryKeys.bookings.all, "detail"] as const,
    detail:  (id: string) => [...queryKeys.bookings.details(), id] as const,
  },
  inventory: {
    all:     ["inventory"] as const,
    sync:    () => [...queryKeys.inventory.all, "sync"] as const,
    health:  () => [...queryKeys.inventory.all, "health"] as const,
    kpi:     () => [...queryKeys.inventory.all, "kpi"] as const,
  },
  crm: {
    all:       ["crm"] as const,
    customers: () => [...queryKeys.crm.all, "customers"] as const,
    customer:  (id: string) => [...queryKeys.crm.customers(), id] as const,
  },
  // ... per feature
}
```

### API Layer Pattern

```ts
// features/bookings/api.ts

import { api } from "@/shared/api/client"

export const bookingsApi = {
  list: async (filters: BookingFilters) => {
    const { data } = await api.get("/reservations", { params: filters })
    return data as BookingListResponse
  },

  detail: async (id: string) => {
    const { data } = await api.get(`/reservations/${id}`)
    return data as BookingDetail
  },

  create: async (payload: CreateBookingPayload) => {
    const { data } = await api.post("/reservations", payload)
    return data as BookingDetail
  },

  update: async (id: string, payload: Partial<BookingDetail>) => {
    const { data } = await api.put(`/reservations/${id}`, payload)
    return data as BookingDetail
  },

  cancel: async (id: string, reason: string) => {
    const { data } = await api.post(`/reservations/${id}/cancel`, { reason })
    return data
  },
}
```

### Hook Pattern

```ts
// features/bookings/hooks.ts

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { bookingsApi } from "./api"
import { queryKeys } from "@/shared/api/queryKeys"

export function useBookings(filters: BookingFilters) {
  return useQuery({
    queryKey: queryKeys.bookings.list(filters),
    queryFn: () => bookingsApi.list(filters),
    staleTime: 30_000,
  })
}

export function useBookingDetail(id: string) {
  return useQuery({
    queryKey: queryKeys.bookings.detail(id),
    queryFn: () => bookingsApi.detail(id),
    enabled: !!id,
  })
}

export function useCreateBooking() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: bookingsApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.bookings.lists() })
    },
  })
}

export function useCancelBooking() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) =>
      bookingsApi.cancel(id, reason),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.bookings.detail(id) })
      queryClient.invalidateQueries({ queryKey: queryKeys.bookings.lists() })
    },
  })
}
```

### Error Handling

```ts
// shared/api/client.ts

// Global error handler in QueryClient config
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: (failureCount, error) => {
        if (error?.response?.status === 401) return false
        if (error?.response?.status === 404) return false
        return failureCount < 2
      },
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: 0,
      onError: (error) => {
        // Global mutation error toast
        const message = apiErrorMessage(error)
        toast.error(message)
      },
    },
  },
})
```

### Optimistic Updates (Example: Status change)

```ts
export function useUpdateBookingStatus() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, status }) => bookingsApi.updateStatus(id, status),
    onMutate: async ({ id, status }) => {
      await queryClient.cancelQueries({ queryKey: queryKeys.bookings.detail(id) })
      const previous = queryClient.getQueryData(queryKeys.bookings.detail(id))
      queryClient.setQueryData(queryKeys.bookings.detail(id), (old) => ({
        ...old,
        status,
      }))
      return { previous }
    },
    onError: (_, { id }, context) => {
      queryClient.setQueryData(queryKeys.bookings.detail(id), context.previous)
    },
    onSettled: (_, __, { id }) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.bookings.detail(id) })
    },
  })
}
```

---

# STEP 7 — PERFORMANCE OPTIMIZATION

## 7.1 Code Splitting Strategy

### Current State
- Top-level pages are lazy-loaded (good)
- Admin sub-routes all loaded in one chunk (bad)
- No chunk naming strategy

### Proposed

```tsx
// Route-based splitting with named chunks
const ReservationsPage = lazy(() =>
  import(/* webpackChunkName: "bookings" */ "@/features/bookings/pages/ReservationsPage")
)

// Feature-based grouping
// Chunk: bookings (~50KB) — all booking pages
// Chunk: finance (~40KB) — all finance pages
// Chunk: admin (~60KB) — admin-only pages
// Chunk: crm (~30KB) — CRM pages
// Chunk: analytics (~35KB) — charts + analytics
```

## 7.2 Virtualized Tables

```tsx
// For tables with 100+ rows, use @tanstack/react-virtual
import { useVirtualizer } from "@tanstack/react-virtual"

// DataTable internally switches to virtual mode when:
// - rowCount > 100
// - OR virtual prop is explicitly true
```

## 7.3 Memoization Strategy

| What | How | When |
|------|-----|------|
| Table rows | `React.memo` | Always |
| Chart components | `React.memo` + `useMemo` for data | When data > 50 points |
| Sidebar nav items | `React.memo` | Always |
| Filter bar | `useMemo` for filter options | When options > 20 |
| Computed stats | `useMemo` | When source data > 100 items |

## 7.4 Bundle Size Targets

| Chunk | Target | Current Estimate |
|-------|--------|-----------------|
| Initial (framework + shell) | < 150KB gzipped | ~200KB (needs reduction) |
| Per-feature chunk | < 50KB gzipped | ~30-80KB (varies) |
| Design system | < 30KB gzipped | N/A (new) |
| Total loaded for typical session | < 400KB gzipped | ~500KB+ |

## 7.5 Quick Wins

1. **Remove unused Recharts imports** — Import only needed chart types
2. **Tree-shake lucide-react** — Already tree-shakeable, verify no barrel imports
3. **Lazy-load framer-motion** — Only needed on specific pages
4. **Add `React.memo` to DataTable rows** — Prevents re-render on scroll
5. **Debounce search inputs** — Reduce API calls and re-renders

---

# STEP 8 — ENTERPRISE UX FEATURES

## 8.1 Command Palette (Priority: HIGH)

```
Trigger: Cmd+K / Ctrl+K

Features:
├── Quick navigation to any page
├── Search bookings by reference number
├── Search customers by name
├── Quick actions: "Create Booking", "Export Report"
├── Recent pages
└── Settings shortcuts

Implementation: cmdk library (already installed)
```

## 8.2 Global Search

```
Location: Top bar, always visible

Features:
├── Unified search across: Bookings, Customers, Hotels, Invoices
├── Categorized results (grouped by type)
├── Recent searches
├── Keyboard navigation
└── Debounced API call (300ms)

API: GET /api/search?q=<query>&types=booking,customer,hotel&limit=10
```

## 8.3 Keyboard Shortcuts

```
Global:
  Cmd+K          → Command palette
  Cmd+/          → Keyboard shortcuts help
  Cmd+Shift+N    → New booking
  Cmd+Shift+S    → Search
  Escape         → Close modal/drawer

Table:
  j/k            → Navigate rows
  Enter          → Open detail
  x              → Toggle selection
  Cmd+A          → Select all

Navigation:
  g then d       → Dashboard
  g then r       → Reservations
  g then c       → Customers
  g then f       → Finance
```

## 8.4 Activity Timeline

```
Every entity (Booking, Customer, Hotel) gets a Timeline tab showing:
├── Created: "Ali Demir tarafından oluşturuldu" — 12 Mar 14:30
├── Status Change: "pending → confirmed" — 12 Mar 15:00
├── Payment: "₺4,500 ödeme alındı" — 12 Mar 15:05
├── Note: "Müşteri erken check-in istedi" — 12 Mar 16:00
├── System: "Otomatik hatırlatma gönderildi" — 13 Mar 09:00
└── Updated: "Check-out tarihi değiştirildi" — 14 Mar 11:00
```

## 8.5 Real-time Notifications

```
Architecture:
├── SSE (Server-Sent Events) for real-time updates
├── Notification bell with unread count
├── Notification drawer with categories:
│   ├── Bookings (new, status change, cancellation)
│   ├── Finance (payment received, refund processed)
│   ├── System (sync complete, error alert)
│   └── Approvals (pending approval request)
├── Browser notification permission (optional)
└── Sound notification for critical alerts
```

## 8.6 User Presence Indicators

```
Show who is currently viewing the same entity:
├── BookingDetailPage: "Ayşe Y. bu sayfayı görüntülüyor"
├── Customer edit: "2 kişi bu kaydı düzenliyor"
└── Visual: Avatar stack in page header

Implementation: WebSocket or SSE-based presence tracking
```

---

# STEP 9 — MULTI-TENANT UX

## 9.1 Tenant Switcher

```
Location: Top bar, next to brand logo

UI:
┌────────────────────────────┐
│ [Logo] Syroce Travel  ▼   │
├────────────────────────────┤
│ ✓ Syroce Travel (Admin)   │
│   Blue Sky Hotels          │
│   Palmiye Turizm           │
├────────────────────────────┤
│ + Yeni Organizasyon Ekle   │
└────────────────────────────┘

Features:
├── Quick switch without logout
├── Visual indicator of current tenant
├── Role display per tenant
└── Tenant-specific branding (logo, color)
```

## 9.2 Role-Based UI

```
Permission-aware component:

<Authorize permission="bookings.create">
  <Button>Yeni Rezervasyon</Button>
</Authorize>

<Authorize role={["admin", "super_admin"]}>
  <AdminPanel />
</Authorize>

Implementation:
├── usePermissions() hook
├── <Authorize> wrapper component
├── Navigation items auto-hidden
├── API error 403 → redirect to unauthorized page
└── Backend enforces same permissions (defense in depth)
```

## 9.3 Permission-Aware Navigation

```
Current: Complex filtering in AppShell (350+ lines of nav logic)
Proposed: Declarative permission model in route/nav definition

// navigation.ts
{
  key: "finance-settlements",
  label: "Mutabakatlar",
  path: "/app/admin/finance/settlements",
  icon: Wallet,
  permissions: ["finance.settlements.view"],
  roles: ["admin", "super_admin", "accounting"],
  minMode: "pro",
}

// NavRenderer automatically:
// 1. Filters by role
// 2. Filters by permission
// 3. Filters by product mode
// 4. Filters by feature flag
// 5. Hides entire sections if all items filtered
```

## 9.4 Organization Settings UI

```
/app/settings/organization
├── General: Name, Logo, Primary Color
├── Team: User management, role assignment
├── Billing: Plan, usage, invoices
├── Integrations: Connected services
├── Security: 2FA enforcement, session policies
└── Data: Export, import, retention policies
```

---

# STEP 10 — FRONTEND ROADMAP

## Phase 1 — Architecture Cleanup (2-3 weeks)

**Goal:** Clean foundation without breaking anything

| Task | Effort | Impact |
|------|--------|--------|
| Split `App.js` routes into domain route files | 2d | Maintainability |
| Create `features/` directory structure (empty shells) | 1d | Organization |
| Move API calls from pages to `features/X/api.ts` (top 10 pages) | 3d | Consistency |
| Create TanStack Query hooks for top 10 most-used endpoints | 3d | Performance, UX |
| Split 5 largest god pages into sub-components (> 1000 lines) | 3d | Maintainability |
| Consolidate duplicate nav configs (`appNavigation.js`, `/nav/`, `/config/`) | 1d | Simplification |

**Estimated:** 13 dev-days

## Phase 2 — Design System (2-3 weeks)

**Goal:** Reusable component library

| Task | Effort | Impact |
|------|--------|--------|
| Build `DataTable` pattern component (sort, filter, paginate, select) | 3d | Eliminates 50+ duplicate implementations |
| Build `PageShell` pattern component | 1d | Consistent page layout |
| Build `FilterBar` pattern component | 1d | Consistent filtering |
| Build `StatusBadge` component | 0.5d | Consistent status display |
| Build `EmptyState` variants | 0.5d | Consistent empty views |
| Build `ConfirmDialog` pattern | 0.5d | Consistent confirmations |
| Build `Timeline` component | 1d | Activity tracking UI |
| Standardize design tokens (update `index.css`) | 1d | Visual consistency |
| Migrate top 10 list pages to `DataTable` | 3d | Proof of concept |
| Document design system in Storybook (optional) | 2d | Developer experience |

**Estimated:** 13 dev-days

## Phase 3 — UX Standardization (2-3 weeks)

**Goal:** Consistent user experience across all pages

| Task | Effort | Impact |
|------|--------|--------|
| Migrate remaining list pages to `DataTable` | 5d | Consistency |
| Migrate all pages to `PageShell` | 3d | Consistent layout |
| Standardize all CRUD flows (create → edit → delete) | 3d | UX quality |
| Implement error boundary with correlation ID display | 1d | Debuggability |
| Standardize loading states (skeleton per page type) | 2d | Perceived performance |

**Estimated:** 14 dev-days

## Phase 4 — Performance (1-2 weeks)

**Goal:** Fast, responsive application

| Task | Effort | Impact |
|------|--------|--------|
| Implement route-based code splitting with named chunks | 2d | Initial load time |
| Add virtualized tables for large datasets | 2d | Scroll performance |
| Add `React.memo` to key components (table rows, nav items) | 1d | Render performance |
| Bundle analysis + tree-shaking audit | 1d | Bundle size |
| Lazy-load heavy libraries (recharts, framer-motion) | 1d | Initial load |

**Estimated:** 7 dev-days

## Phase 5 — Enterprise UX (3-4 weeks)

**Goal:** World-class SaaS polish

| Task | Effort | Impact |
|------|--------|--------|
| Command palette (Cmd+K) with navigation + search | 3d | Power user UX |
| Global search with unified results | 3d | Discoverability |
| Keyboard shortcuts framework | 2d | Power user UX |
| Activity timeline on entity pages | 3d | Audit visibility |
| Notification system (SSE + drawer) | 5d | Real-time awareness |
| Tenant switcher in top bar | 2d | Multi-tenant UX |
| Permission-aware navigation refactor | 2d | Security UX |

**Estimated:** 20 dev-days

---

## Total Effort Summary

| Phase | Duration | Dev-Days | Priority |
|-------|----------|----------|----------|
| Phase 1: Architecture Cleanup | 2-3 weeks | 13 | P0 |
| Phase 2: Design System | 2-3 weeks | 13 | P0 |
| Phase 3: UX Standardization | 2-3 weeks | 14 | P1 |
| Phase 4: Performance | 1-2 weeks | 7 | P1 |
| Phase 5: Enterprise UX | 3-4 weeks | 20 | P2 |
| **TOTAL** | **10-15 weeks** | **67 dev-days** | — |

---

## Implementation Strategy

### Migration Approach: Strangler Fig Pattern

Do NOT rewrite everything at once. Instead:

1. **Build new patterns alongside existing code** (DataTable, PageShell, API hooks)
2. **Migrate one page at a time** to new patterns (start with highest-traffic pages)
3. **Delete old patterns** only when all consumers are migrated
4. **Feature-flag new implementations** when needed

### Migration Priority Order (by user impact)

1. `DashboardPage` — First thing users see
2. `ReservationsPage` — Most-used CRUD page
3. `AdminAgenciesPage` — Admin core workflow
4. `CrmCustomersPage` — CRM core workflow
5. `AdminFinanceRefundsPage` — Largest god page (2150 lines)
6. `InventorySyncDashboardPage` — Supplier monitoring
7. `B2BPortalPage` — B2B partner experience
8. `AgencyHotelsPage` — Agency workflow
9. Remaining admin pages
10. Public/storefront pages

### TypeScript Migration (Parallel Track)

Recommend migrating to TypeScript incrementally:
1. Start with `shared/types/` — define all interfaces
2. Rename files `.js → .ts/.tsx` one feature at a time
3. `design-system/` should be TypeScript from day one
4. Use `strict: false` initially, tighten over time

---

## Quality Benchmarks: What 10/10 Looks Like

| Metric | Current | Target |
|--------|---------|--------|
| Largest file | 2,150 lines | < 300 lines |
| God pages (> 500 lines) | 29 | 0 |
| TanStack Query adoption | 5% | 100% |
| Direct API calls in pages | 536 | 0 |
| Design system coverage | 30% | 95% |
| DataTable pages with standard pattern | 0 | 50+ |
| Loading skeleton coverage | 24% (47/193 pages) | 100% |
| Lighthouse Performance | ~65 | > 90 |
| Bundle gzipped | ~500KB+ | < 400KB |
| TypeScript coverage | 0% | 100% (long-term) |
| Code splitting chunks | 1 large | 10+ feature chunks |
| data-testid coverage | 2032 elements | All interactive elements |

---

*This document serves as the north star for Syroce's frontend transformation from a functional MVP to an enterprise-grade SaaS platform comparable to Stripe Dashboard, Shopify Admin, and Linear.*
