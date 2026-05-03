"""Compat shim package — original split routers moved to canonical paths.

Old → New mapping:
  app.routers.inventory.sync_router        → app.modules.inventory.routers.sync
  app.routers.inventory.booking_router     → app.modules.inventory.routers.booking_flow
  app.routers.inventory.diagnostics_router → app.modules.inventory.routers.diagnostics
  app.routers.inventory.onboarding_router  → app.modules.inventory.routers.onboarding

The four sibling files (sync_router.py, booking_router.py, diagnostics_router.py,
onboarding_router.py) are themselves compat shims pointing at the new locations.
This `__init__` re-exports the same attribute names that legacy callers used
(`from app.routers.inventory import sync_router, booking_router, ...`).
"""
from app.modules.inventory.routers.sync import router as sync_router
from app.modules.inventory.routers.booking_flow import router as booking_router
from app.modules.inventory.routers.diagnostics import (
    router as diagnostics_router,
    e2e_demo_router,
)
from app.modules.inventory.routers.onboarding import router as onboarding_router

__all__ = [
    "sync_router",
    "booking_router",
    "diagnostics_router",
    "e2e_demo_router",
    "onboarding_router",
]
