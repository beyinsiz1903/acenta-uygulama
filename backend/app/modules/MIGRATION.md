# `app.routers` → `app.modules.<domain>.routers` Migration

This document tracks the relocation of router files from the flat
`app/routers/` directory into the per-domain module layout under
`app/modules/<domain>/routers/`.

## Status (Task #1, 2026-05-03)

The migration was already ~95% complete before this task. The active
boot path is `app.bootstrap.domain_router_registry.register_routers`
(wired into `app.bootstrap.api_app`), which composes 16 domain modules
plus a small set of cross-cutting utilities.

This task closed out the remaining 9 real router files (the rest of
`app/routers/*.py` had previously become re-export shims) and brought
the inventory subpackage `app/routers/inventory/*` under the canonical
module layout.

## Verified

- Active registry: `app.bootstrap.domain_router_registry` (api_app:16,171)
- Legacy `app.bootstrap.router_registry` is **not** mounted at boot
- Total registered route count is **identical pre- vs post-refactor**:
  1598 routes, MD5 hash `6c041c9f44dd487f836e62d7642448a2`
- All 14 historical absolute import paths still resolve via shims
- `ruff check` passes, `/api/health` returns 200

## Closed in this task — old → new

| Old path | New path | Domain |
|---|---|---|
| `app.routers.agency` | `app.modules.inventory.routers.agency_hotels` | inventory |
| `app.routers.admin_orphan_migration` | `app.modules.enterprise.routers.admin_orphan_migration` | enterprise |
| `app.routers.admin_outbox` | `app.modules.operations.routers.admin_outbox` | operations |
| `app.routers.webhooks` | `app.modules.system.routers.webhooks` | system |
| `app.routers.admin_webhooks` | `app.modules.system.routers.admin_webhooks` | system |
| `app.routers.inventory.sync_router` | `app.modules.inventory.routers.sync` | inventory |
| `app.routers.inventory.booking_router` | `app.modules.inventory.routers.booking_flow` | inventory |
| `app.routers.inventory.diagnostics_router` | `app.modules.inventory.routers.diagnostics` | inventory |
| `app.routers.inventory.onboarding_router` | `app.modules.inventory.routers.onboarding` | inventory |

Each old location now contains a one-line `importlib`-based shim that
re-mounts the canonical module into `sys.modules[__name__]`, mirroring
the long-standing pattern at `app/routers/b2b_bookings.py`. The
`app/routers/inventory/__init__.py` package re-exports the four
sub-routers under their original attribute names so legacy
`from app.routers.inventory import sync_router, booking_router, ...`
imports keep working unchanged.

## Pre-existing migrations (already complete before this task)

The remaining 254 files in `app/routers/` were already shims pointing
at canonical `app.modules.*.routers.*` locations; the 16 domain modules
already composed every router under their domain via a `domain_router`
APIRouter. Cross-cutting utilities (orphan migration, outbox, webhooks)
remained in the registry as one-off `include_router` calls but their
sources have now been moved into appropriate domain modules.

## Boundary rationale

- **inventory** owns hotel/room/availability/PMS/sheets/iCal/sync,
  including the supplier-onboarding wizard and inventory-diagnostics
  endpoints (originally under `app/routers/inventory/`). The agency
  hotel listing logic (`agency.py`) belongs here too — its single
  router builds agency-facing hotel rows joined with sales status.
- **enterprise** owns governance/audit/approvals/admin tooling. The
  orphan-migration admin console is a cross-domain admin tool that
  fits the enterprise governance theme.
- **operations** owns ops cases/tasks/incidents and the outbox-consumer
  monitoring (admin_outbox), which is an ops-control surface.
- **system** owns infra/health/cache/monitoring; the cross-tenant
  webhook subscription system and its admin counterpart fit here as
  platform-level infrastructure.

## Future cleanup (out of scope for this task)

- Once a release cycle has elapsed without external imports of the
  legacy `app.routers.*` paths, the shim files can be deleted in bulk
  and the legacy `app.bootstrap.router_registry` module retired. This
  is intentionally deferred — many test files and untracked scripts
  still import by the old absolute path.
