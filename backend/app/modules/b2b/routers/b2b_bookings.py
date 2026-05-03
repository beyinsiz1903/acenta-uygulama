"""B2B bookings aggregator router (T009 / Task #3 refactor).

ADR — Module boundaries:
  This file used to be a monolithic 1480-LOC router that owned the entire
  B2B booking lifecycle. As part of Task #3 it was decomposed into four
  focused sibling routers, each scoped to one lifecycle stage:

    * b2b_bookings_create    — POST /bookings, POST /bookings-from-marketplace
    * b2b_bookings_confirm   — POST /bookings/{id}/confirm
    * b2b_bookings_risk      — POST /bookings/{id}/risk/{approve,reject}
    * b2b_bookings_lifecycle — refund-requests, cancel, amend/{quote,confirm},
                               GET /bookings/{id}/events

  The single `router` exported here is an aggregator that includes each
  child router unchanged. The bootstrap layer
  (`app.modules.b2b.__init__`) and the legacy compat shim
  (`app.routers.b2b_bookings`) both continue to import `router` from this
  module — no change in their wiring is required.

  Splitting was driven by file size (audit fatigue, slow incident
  response) and not by behaviour; every URL path, request/response shape,
  status code, audit log entry, and lifecycle event remains bit-for-bit
  identical. See `app/modules/MIGRATION.md` for the broader context.
"""
from __future__ import annotations

from fastapi import APIRouter

from app.modules.b2b.routers.b2b_bookings_confirm import router as _confirm_router
from app.modules.b2b.routers.b2b_bookings_create import router as _create_router
from app.modules.b2b.routers.b2b_bookings_lifecycle import router as _lifecycle_router
from app.modules.b2b.routers.b2b_bookings_risk import router as _risk_router

# Re-export commonly used helpers so existing import sites keep working.
# (Tests historically import `_get_visible_listing` for white-box checks.)
from app.modules.b2b.routers.b2b_bookings_create import (  # noqa: F401
    _get_visible_listing,
    get_booking_service,
    get_idem_repo,
    get_pricing_service,
)

router = APIRouter()
router.include_router(_create_router)
router.include_router(_confirm_router)
router.include_router(_risk_router)
router.include_router(_lifecycle_router)
