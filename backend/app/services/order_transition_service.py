"""Order Transition Service — State machine & guarded transitions.

Enforces the order status state machine. All status changes MUST go
through this service. Direct DB updates to order status are forbidden.

Three separate status domains:
  - Order status
  - Supplier booking status
  - Financial settlement status
"""
from __future__ import annotations


from app.db import get_db
from app.services.order_event_service import append_event


# ── Order Status Enum ──
ORDER_STATUSES = {
    "draft",
    "pending_confirmation",
    "confirmed",
    "cancel_requested",
    "cancelled",
    "closed",
}

# ── Allowed Transitions ──
ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"pending_confirmation", "confirmed"},
    "pending_confirmation": {"confirmed", "cancel_requested", "cancelled"},
    "confirmed": {"cancel_requested", "cancelled", "closed"},
    "cancel_requested": {"cancelled"},
    "cancelled": {"closed"},
    "closed": set(),
}

# ── Supplier Booking Status Enum ──
SUPPLIER_BOOKING_STATUSES = {
    "not_started",
    "pending",
    "confirmed",
    "failed",
    "cancel_requested",
    "cancelled",
}

# ── Financial Settlement Status Enum ──
SETTLEMENT_STATUSES = {
    "not_settled",
    "partially_settled",
    "settled",
    "reversed",
}


def is_transition_allowed(current: str, target: str) -> bool:
    """Check if transition from current to target status is allowed."""
    return target in ALLOWED_TRANSITIONS.get(current, set())


async def transition_order_status(
    order_id: str,
    target_status: str,
    actor_type: str = "system",
    actor_id: str = "system",
    actor_name: str = "system",
    reason: str = "",
    org_id: str = "",
) -> dict:
    """Perform a guarded status transition on an order."""
    db = await get_db()

    order = await db.orders.find_one({"order_id": order_id})
    if not order:
        return {"success": False, "error": "Order not found"}

    current_status = order.get("status", "draft")
    if not is_transition_allowed(current_status, target_status):
        return {
            "success": False,
            "error": f"Transition from '{current_status}' to '{target_status}' is not allowed",
            "current_status": current_status,
            "allowed_transitions": list(ALLOWED_TRANSITIONS.get(current_status, set())),
        }

    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    current_version = order.get("version", 1)

    await db.orders.update_one(
        {"order_id": order_id},
        {"$set": {
            "status": target_status,
            "status_reason": reason,
            "status_updated_at": now,
            "updated_at": now,
            "updated_by": actor_name,
            "version": current_version + 1,
        }},
    )

    # Determine event type
    event_type_map = {
        "pending_confirmation": "order_status_changed",
        "confirmed": "order_confirmed",
        "cancel_requested": "order_cancel_requested",
        "cancelled": "order_cancelled",
        "closed": "order_closed",
    }
    event_type = event_type_map.get(target_status, "order_status_changed")

    await append_event(
        order_id=order_id,
        event_type=event_type,
        actor_type=actor_type,
        actor_id=actor_id,
        actor_name=actor_name,
        before_state={"status": current_status},
        after_state={"status": target_status},
        payload={"reason": reason} if reason else {},
        org_id=org_id or order.get("org_id", ""),
    )

    # Phase 2: Trigger financial linkage on status transitions
    try:
        from app.services.oms.order_financial_linkage_service import (
            post_order_to_ledger,
            reverse_order_ledger,
        )
        if target_status == "confirmed":
            await post_order_to_ledger(order_id, actor_name=actor_name)
        elif target_status == "cancelled":
            await reverse_order_ledger(order_id, actor_name=actor_name)
    except Exception:
        pass  # Financial linkage errors should not block status transitions

    return {
        "success": True,
        "order_id": order_id,
        "previous_status": current_status,
        "new_status": target_status,
    }


async def confirm_order(
    order_id: str, actor_name: str = "system", reason: str = "", org_id: str = ""
) -> dict:
    return await transition_order_status(
        order_id, "confirmed", "user", actor_name, actor_name, reason, org_id
    )


async def request_cancel(
    order_id: str, actor_name: str = "system", reason: str = "", org_id: str = ""
) -> dict:
    return await transition_order_status(
        order_id, "cancel_requested", "user", actor_name, actor_name, reason, org_id
    )


async def cancel_order(
    order_id: str, actor_name: str = "system", reason: str = "", org_id: str = ""
) -> dict:
    return await transition_order_status(
        order_id, "cancelled", "user", actor_name, actor_name, reason, org_id
    )


async def close_order(
    order_id: str, actor_name: str = "system", reason: str = "", org_id: str = ""
) -> dict:
    return await transition_order_status(
        order_id, "closed", "user", actor_name, actor_name, reason, org_id
    )
