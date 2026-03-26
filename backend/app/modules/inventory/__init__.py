"""Inventory domain — stock, availability, PMS, sheets, hotel management, search.

Owner: Inventory Domain
Boundary: All inventory lifecycle — hotel/room management, availability,
          reservations, PMS integration, sheets, iCal sync, catalog, tours.

Phase 2, Dalga 4 consolidation.
"""
from fastapi import APIRouter

from app.config import API_PREFIX

# --- Core inventory ---
from app.modules.inventory.routers.inventory_shares import router as inventory_shares_router
from app.modules.inventory.routers.inventory_snapshots_api import router as inventory_snapshots_api_router
from app.modules.inventory.routers.products import router as products_router
from app.modules.inventory.routers.hotel import router as agency_hotels_router
from app.modules.inventory.routers.hotel_integrations import router as hotel_integrations_router
from app.modules.inventory.routers.rateplans import router as rateplans_router
from app.modules.inventory.routers.search import router as search_router
from app.modules.inventory.routers.reservations import router as reservations_router

# --- Agency operations ---
from app.modules.inventory.routers.agency_availability import router as agency_availability_router
from app.modules.inventory.routers.agency_reservations import router as agency_reservations_router
from app.modules.inventory.routers.agency_pms import router as agency_pms_router
from app.modules.inventory.routers.agency_pms_accounting import router as agency_pms_accounting_router
from app.modules.inventory.routers.agency_sheets import router as agency_sheets_router
from app.modules.inventory.routers.agency_writeback import router as agency_writeback_router
from app.modules.inventory.routers.agency_booking import router as agency_booking_router

# --- Admin inventory ---
from app.modules.inventory.routers.admin_hotels import router as admin_hotels_router
from app.modules.inventory.routers.admin_ical import router as admin_ical_router
from app.modules.inventory.routers.admin_sheets import router as admin_sheets_router
from app.modules.inventory.routers.admin_catalog import router as admin_catalog_router
from app.modules.inventory.routers.admin_tours import router as admin_tours_router

# --- Inventory sub-package (sync, booking, diagnostics, onboarding) ---
from app.routers.inventory import (
    sync_router as inv_sync_router,
    booking_router as inv_booking_router,
    diagnostics_router as inv_diagnostics_router,
    e2e_demo_router as inv_e2e_demo_router,
    onboarding_router as inv_onboarding_router,
)

domain_router = APIRouter()

# Core inventory (various prefix patterns)
domain_router.include_router(inventory_shares_router)         # /api/inventory-shares (built-in)
domain_router.include_router(inventory_snapshots_api_router)  # /api/inventory (built-in)
domain_router.include_router(products_router, prefix=API_PREFIX)  # /products → /api/products
domain_router.include_router(agency_hotels_router)            # /api/hotel (built-in)
domain_router.include_router(hotel_integrations_router)       # /api/hotel/integrations (built-in)
domain_router.include_router(rateplans_router)                # /api/rateplans (built-in)
domain_router.include_router(search_router, prefix=API_PREFIX)  # no prefix → /api/search
domain_router.include_router(reservations_router, prefix=API_PREFIX)  # /reservations → /api/reservations

# Agency operations (all /api/agency/* built-in)
domain_router.include_router(agency_availability_router)
domain_router.include_router(agency_reservations_router)
domain_router.include_router(agency_pms_router)
domain_router.include_router(agency_pms_accounting_router)
domain_router.include_router(agency_sheets_router)
domain_router.include_router(agency_writeback_router)
domain_router.include_router(agency_booking_router)

# Admin inventory (all /api/admin/* built-in)
domain_router.include_router(admin_hotels_router)
domain_router.include_router(admin_ical_router)
domain_router.include_router(admin_sheets_router)
domain_router.include_router(admin_catalog_router)
domain_router.include_router(admin_tours_router)

# Inventory sub-package
domain_router.include_router(inv_sync_router)
domain_router.include_router(inv_booking_router)
domain_router.include_router(inv_diagnostics_router)
domain_router.include_router(inv_e2e_demo_router)
domain_router.include_router(inv_onboarding_router)
