"""Inventory domain routers — split from monolithic inventory_sync_router.py.

Sub-modules:
  sync_router        — Sync engine: trigger, status, jobs, retry, search, stats
  booking_router     — Booking flow: precheck, create, status, cancel, test-matrix
  diagnostics_router — Stability, supplier health/config, E2E certification
  onboarding_router  — Supplier onboarding wizard (6-step)
"""
from app.routers.inventory.sync_router import router as sync_router
from app.routers.inventory.booking_router import router as booking_router
from app.routers.inventory.diagnostics_router import (
    router as diagnostics_router,
    e2e_demo_router,
)
from app.routers.inventory.onboarding_router import router as onboarding_router

__all__ = [
    "sync_router",
    "booking_router",
    "diagnostics_router",
    "e2e_demo_router",
    "onboarding_router",
]
