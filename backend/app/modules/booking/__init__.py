"""Booking domain module — unified state machine, command-based transitions.

Owner: Booking Domain
Boundary: All booking lifecycle — search, create, state transitions, outcomes,
          vouchers, matching, cancellation reasons, and unified booking orchestration.

Routers consolidated here (Phase 2, Dalga 2):
  - modules/booking/router.py         → Booking commands (state machine)
  - modules/booking/migration_router.py→ Booking migration admin
  - routers/bookings.py               → Legacy booking CRUD
  - routers/booking_outcomes.py        → Booking outcome resolution
  - routers/unified_booking_router.py  → Supplier-backed unified booking
  - routers/cancel_reasons.py         → Cancellation reason codes
  - routers/vouchers.py               → Voucher generation & delivery
  - routers/voucher.py                → Voucher view & PDF
  - routers/matches.py                → Booking match admin
  - routers/match_alerts.py           → Match alert management
  - routers/match_unblock.py          → Match unblock operations
"""
from fastapi import APIRouter

from app.config import API_PREFIX

# --- Core booking (domain module) ---
from app.modules.booking.router import router as booking_commands_router
from app.modules.booking.migration_router import router as booking_migration_router

# --- Legacy booking CRUD & outcomes ---
from app.routers.bookings import router as bookings_legacy_router
from app.routers.booking_outcomes import router as booking_outcomes_router

# --- Unified booking orchestration ---
from app.routers.unified_booking_router import router as unified_booking_router

# --- Supporting: cancel reasons, vouchers ---
from app.routers.cancel_reasons import router as cancel_reasons_router
from app.routers.vouchers import router as vouchers_router
from app.routers.voucher import router as voucher_router

# --- Matching ---
from app.routers.matches import router as matches_router
from app.routers.match_alerts import router as match_alerts_router
from app.routers.match_unblock import router as match_unblock_router

domain_router = APIRouter()

# Core booking commands & migration (prefix: /bookings, /admin/booking-migration → needs /api)
domain_router.include_router(booking_commands_router, prefix=API_PREFIX)
domain_router.include_router(booking_migration_router, prefix=API_PREFIX)

# Legacy booking CRUD (prefix: /bookings → needs /api)
domain_router.include_router(bookings_legacy_router, prefix=API_PREFIX)
domain_router.include_router(booking_outcomes_router, prefix=API_PREFIX)

# Unified booking (prefix built-in: /api/unified-booking)
domain_router.include_router(unified_booking_router)

# Cancel reasons (prefix built-in: /api/reference)
domain_router.include_router(cancel_reasons_router)

# Vouchers (no prefix → needs /api, voucher has built-in /api/voucher)
domain_router.include_router(vouchers_router, prefix=API_PREFIX)
domain_router.include_router(voucher_router)

# Matching (prefix built-in: /api/admin/matches, /api/admin/match-alerts)
domain_router.include_router(matches_router)
domain_router.include_router(match_alerts_router)
domain_router.include_router(match_unblock_router)
