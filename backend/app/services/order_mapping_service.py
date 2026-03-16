"""Order Mapping Service — Booking to Order mapping.

Maps supplier bookings to order items and links supplier booking IDs.
Phase 1 supports hotel bookings only.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from app.db import get_db
from app.services.order_event_service import append_event


async def map_booking_to_order_item(
    order_id: str,
    item_type: str = "hotel",
    supplier_code: str = "",
    supplier_booking_id: str = "",
    product_reference: str = "",
    product_name: str = "",
    check_in: str = "",
    check_out: str = "",
    passenger_summary: Optional[dict] = None,
    room_summary: Optional[dict] = None,
    sell_amount: float = 0,
    supplier_amount: float = 0,
    margin_amount: float = 0,
    currency: str = "EUR",
    pricing_trace_id: str = "",
    booking_trace_id: str = "",
    metadata: Optional[dict] = None,
    actor_name: str = "system",
    org_id: str = "",
) -> dict:
    """Create an order_item from a booking and link it to an order."""
    db = await get_db()
    now = datetime.now(timezone.utc).isoformat()

    item_id = f"oi_{uuid.uuid4().hex[:12]}"
    order_item = {
        "item_id": item_id,
        "order_id": order_id,
        "item_type": item_type,
        "item_status": "pending",
        "item_status_reason": "",
        "supplier_code": supplier_code,
        "supplier_booking_id": supplier_booking_id,
        "supplier_booking_status": "not_started" if not supplier_booking_id else "pending",
        "product_reference": product_reference,
        "product_name": product_name,
        "check_in": check_in,
        "check_out": check_out,
        "passenger_summary": passenger_summary or {},
        "room_summary": room_summary or {},
        "sell_amount": sell_amount,
        "supplier_amount": supplier_amount,
        "margin_amount": margin_amount,
        "currency": currency,
        "pricing_trace_id": pricing_trace_id,
        "booking_trace_id": booking_trace_id,
        "created_at": now,
        "updated_at": now,
        "metadata": metadata or {},
        "org_id": org_id,
    }
    await db.order_items.insert_one(order_item)
    order_item.pop("_id", None)

    # Update order totals
    await _recalculate_order_totals(order_id)

    # Record event
    await append_event(
        order_id=order_id,
        event_type="order_item_added",
        actor_type="system",
        actor_id=actor_name,
        actor_name=actor_name,
        after_state={"item_id": item_id, "item_type": item_type, "product_name": product_name},
        payload={"sell_amount": sell_amount, "supplier_code": supplier_code},
        order_item_id=item_id,
        org_id=org_id,
    )

    return order_item


async def link_supplier_booking(
    order_id: str,
    item_id: str,
    supplier_booking_id: str,
    supplier_booking_status: str = "pending",
    actor_name: str = "system",
    org_id: str = "",
) -> dict:
    """Link a supplier booking ID to an existing order item."""
    db = await get_db()
    now = datetime.now(timezone.utc).isoformat()

    result = await db.order_items.find_one(
        {"order_id": order_id, "item_id": item_id}
    )
    if not result:
        return {"success": False, "error": "Order item not found"}

    old_booking_id = result.get("supplier_booking_id", "")
    await db.order_items.update_one(
        {"item_id": item_id},
        {"$set": {
            "supplier_booking_id": supplier_booking_id,
            "supplier_booking_status": supplier_booking_status,
            "updated_at": now,
        }},
    )

    await append_event(
        order_id=order_id,
        event_type="supplier_booking_linked",
        actor_type="system",
        actor_id=actor_name,
        actor_name=actor_name,
        before_state={"supplier_booking_id": old_booking_id},
        after_state={"supplier_booking_id": supplier_booking_id, "supplier_booking_status": supplier_booking_status},
        order_item_id=item_id,
        org_id=org_id,
    )

    return {"success": True, "item_id": item_id, "supplier_booking_id": supplier_booking_id}


async def _recalculate_order_totals(order_id: str) -> None:
    """Recalculate order financial totals from items."""
    db = await get_db()
    items = await db.order_items.find(
        {"order_id": order_id}, {"_id": 0}
    ).to_list(length=100)

    total_sell = sum(i.get("sell_amount", 0) for i in items)
    total_supplier = sum(i.get("supplier_amount", 0) for i in items)
    total_margin = sum(i.get("margin_amount", 0) for i in items)

    now = datetime.now(timezone.utc).isoformat()
    await db.orders.update_one(
        {"order_id": order_id},
        {"$set": {
            "total_sell_amount": total_sell,
            "total_supplier_amount": total_supplier,
            "total_margin_amount": total_margin,
            "booking_reference_count": len(items),
            "updated_at": now,
        }},
    )
