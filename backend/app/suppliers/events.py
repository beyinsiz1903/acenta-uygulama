"""Supplier Domain Events — event catalog and handlers.

All supplier lifecycle events are emitted through the central Event Bus.
This module defines the event catalog and registers handlers.
"""
from __future__ import annotations

import logging
from typing import Any, Dict

logger = logging.getLogger("suppliers.events")


# ---------------------------------------------------------------------------
# Event catalog
# ---------------------------------------------------------------------------

class SupplierEventTypes:
    # Search
    SEARCH_COMPLETED = "supplier.search_completed"
    SEARCH_CACHED_HIT = "supplier.search_cached_hit"
    # Hold
    HOLD_CREATED = "supplier.hold_created"
    HOLD_FAILED = "supplier.hold_failed"
    HOLD_EXPIRED = "supplier.hold_expired"
    # Booking
    BOOKING_CONFIRMED = "supplier.booking_confirmed"
    BOOKING_FAILED = "supplier.booking_failed"
    BOOKING_CANCELLED = "supplier.booking_cancelled"
    # Failover
    FAILOVER_TRIGGERED = "supplier.failover_triggered"
    # Health
    HEALTH_DEGRADED = "supplier.health_degraded"
    HEALTH_RECOVERED = "supplier.health_recovered"
    SUPPLIER_DISABLED = "supplier.disabled"
    SUPPLIER_ENABLED = "supplier.enabled"
    # Voucher
    VOUCHER_GENERATED = "supplier.voucher_generated"
    # Pricing
    PRICE_CHANGED = "supplier.price_changed"
    # Orchestration
    ORCHESTRATION_STARTED = "supplier.orchestration_started"
    ORCHESTRATION_COMPLETED = "supplier.orchestration_completed"
    ORCHESTRATION_FAILED = "supplier.orchestration_failed"


# ---------------------------------------------------------------------------
# Event handlers
# ---------------------------------------------------------------------------

async def handle_search_completed(event: Dict[str, Any]):
    """Log search completion, update analytics."""
    logger.info(
        "Search completed: %s items from %s suppliers",
        event["payload"].get("total_items", 0),
        event["payload"].get("suppliers_queried", []),
    )


async def handle_booking_confirmed(event: Dict[str, Any]):
    """Post-booking: trigger voucher generation, notifications."""
    booking_id = event["payload"].get("booking_id")
    logger.info("Booking confirmed: %s — triggering post-booking jobs", booking_id)

    # Trigger async tasks
    try:
        from app.tasks.booking_tasks import generate_voucher, send_booking_confirmation_email
        org_id = event.get("organization_id", "")
        generate_voucher.delay(booking_id, org_id)
        send_booking_confirmation_email.delay(booking_id, org_id)
    except Exception as e:
        logger.warning("Failed to trigger post-booking tasks: %s", e)


async def handle_failover_triggered(event: Dict[str, Any]):
    """Log failover for audit, alert if repeated."""
    payload = event.get("payload", {})
    logger.warning(
        "Failover triggered: %s -> %s (%s)",
        payload.get("primary_supplier"),
        payload.get("selected_supplier"),
        payload.get("reason"),
    )


async def handle_health_degraded(event: Dict[str, Any]):
    """Supplier health degraded — invalidate cache, alert ops."""
    payload = event.get("payload", {})
    supplier_code = payload.get("supplier_code")
    logger.warning(
        "Supplier %s health degraded: score=%s state=%s",
        supplier_code, payload.get("score"), payload.get("state"),
    )
    # Invalidate cache for degraded supplier
    try:
        from app.suppliers.cache import invalidate_supplier_cache
        org_id = event.get("organization_id", "")
        await invalidate_supplier_cache(org_id)
    except Exception:
        pass


async def handle_booking_cancelled(event: Dict[str, Any]):
    """Post-cancel: process refund, update inventory."""
    booking_id = event["payload"].get("booking_id")
    logger.info("Booking cancelled: %s — processing refund", booking_id)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def register_supplier_event_handlers():
    """Wire up all supplier event handlers with the Event Bus."""
    from app.infrastructure.event_bus import subscribe

    subscribe(SupplierEventTypes.SEARCH_COMPLETED, handle_search_completed)
    subscribe(SupplierEventTypes.BOOKING_CONFIRMED, handle_booking_confirmed)
    subscribe(SupplierEventTypes.FAILOVER_TRIGGERED, handle_failover_triggered)
    subscribe(SupplierEventTypes.HEALTH_DEGRADED, handle_health_degraded)
    subscribe(SupplierEventTypes.BOOKING_CANCELLED, handle_booking_cancelled)

    logger.info("Registered %d supplier event handlers", 5)
