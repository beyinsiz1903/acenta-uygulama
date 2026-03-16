"""Order Service — Core CRUD and aggregation for OMS.

Manages order creation, reading, updating, number generation,
and demo data seeding.
"""
from __future__ import annotations

import uuid
import random
from datetime import datetime, timezone, timedelta
from typing import Optional

from app.db import get_db
from app.services.order_event_service import append_event
from app.services.order_mapping_service import map_booking_to_order_item


# ── Order Number Generation ──

async def generate_order_number() -> str:
    """Generate a human-friendly order number: ORD-XXXXXX."""
    db = await get_db()
    # Get next sequence value
    result = await db.counters.find_one_and_update(
        {"_id": "order_number"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True,
    )
    seq = result["seq"]
    return f"ORD-{seq:06d}"


# ── Create Order ──

async def create_order(
    tenant_id: str = "",
    agency_id: str = "",
    customer_id: str = "",
    channel: str = "B2B",
    currency: str = "EUR",
    source: str = "manual",
    items: Optional[list[dict]] = None,
    pricing_trace_id: str = "",
    metadata: Optional[dict] = None,
    actor_name: str = "system",
    org_id: str = "default_org",
) -> dict:
    """Create a new order with optional items."""
    db = await get_db()
    now = datetime.now(timezone.utc).isoformat()
    order_id = f"ord_{uuid.uuid4().hex[:12]}"
    order_number = await generate_order_number()

    order = {
        "order_id": order_id,
        "order_number": order_number,
        "tenant_id": tenant_id,
        "agency_id": agency_id,
        "customer_id": customer_id,
        "status": "draft",
        "status_reason": "",
        "status_updated_at": now,
        "currency": currency,
        "total_sell_amount": 0,
        "total_supplier_amount": 0,
        "total_margin_amount": 0,
        "channel": channel,
        "source": source,
        "supplier_summary": {},
        "created_at": now,
        "updated_at": now,
        "created_by": actor_name,
        "updated_by": actor_name,
        "pricing_trace_id": pricing_trace_id,
        "booking_reference_count": 0,
        "settlement_status": "not_settled",
        "metadata": metadata or {},
        "org_id": org_id,
    }
    await db.orders.insert_one(order)
    order.pop("_id", None)

    # Record creation event
    await append_event(
        order_id=order_id,
        event_type="order_created",
        actor_type="user",
        actor_id=actor_name,
        actor_name=actor_name,
        after_state={"status": "draft", "order_number": order_number, "channel": channel},
        payload={"customer_id": customer_id, "agency_id": agency_id},
        org_id=org_id,
    )

    # Create items if provided
    created_items = []
    if items:
        for item_data in items:
            item = await map_booking_to_order_item(
                order_id=order_id,
                item_type=item_data.get("item_type", "hotel"),
                supplier_code=item_data.get("supplier_code", ""),
                supplier_booking_id=item_data.get("supplier_booking_id", ""),
                product_reference=item_data.get("product_reference", ""),
                product_name=item_data.get("product_name", ""),
                check_in=item_data.get("check_in", ""),
                check_out=item_data.get("check_out", ""),
                passenger_summary=item_data.get("passenger_summary"),
                room_summary=item_data.get("room_summary"),
                sell_amount=item_data.get("sell_amount", 0),
                supplier_amount=item_data.get("supplier_amount", 0),
                margin_amount=item_data.get("margin_amount", 0),
                currency=currency,
                pricing_trace_id=item_data.get("pricing_trace_id", pricing_trace_id),
                booking_trace_id=item_data.get("booking_trace_id", ""),
                metadata=item_data.get("metadata"),
                actor_name=actor_name,
                org_id=org_id,
            )
            created_items.append(item)

    # Re-read order to get updated totals
    final_order = await db.orders.find_one({"order_id": order_id}, {"_id": 0})
    final_order["items"] = created_items
    return final_order


# ── Read Orders ──

async def get_orders(
    org_id: str = "default_org",
    skip: int = 0,
    limit: int = 50,
    status: Optional[str] = None,
    channel: Optional[str] = None,
    agency_id: Optional[str] = None,
) -> dict:
    """List orders with pagination and filters."""
    db = await get_db()
    query: dict = {"org_id": org_id}
    if status:
        query["status"] = status
    if channel:
        query["channel"] = channel
    if agency_id:
        query["agency_id"] = agency_id

    total = await db.orders.count_documents(query)
    cursor = (
        db.orders.find(query, {"_id": 0})
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
    )
    orders = await cursor.to_list(length=limit)
    return {"orders": orders, "total": total, "skip": skip, "limit": limit}


async def get_order_by_id(order_id: str) -> Optional[dict]:
    """Get a single order with its items and financial summary."""
    db = await get_db()
    order = await db.orders.find_one({"order_id": order_id}, {"_id": 0})
    if not order:
        return None

    items = await db.order_items.find(
        {"order_id": order_id}, {"_id": 0}
    ).sort("created_at", 1).to_list(length=100)

    order["items"] = items
    order["financial_summary"] = {
        "sell_total": order.get("total_sell_amount", 0),
        "supplier_total": order.get("total_supplier_amount", 0),
        "margin_total": order.get("total_margin_amount", 0),
        "currency": order.get("currency", "EUR"),
        "settlement_status": order.get("settlement_status", "not_settled"),
        "item_count": len(items),
    }
    return order


# ── Update Order ──

async def update_order(
    order_id: str,
    updates: dict,
    actor_name: str = "system",
) -> Optional[dict]:
    """Update non-status fields of an order (PATCH)."""
    db = await get_db()
    order = await db.orders.find_one({"order_id": order_id})
    if not order:
        return None

    # Prevent status updates through this method
    forbidden = {"status", "status_reason", "status_updated_at", "order_id", "order_number", "created_at", "created_by", "_id", "org_id"}
    safe_updates = {k: v for k, v in updates.items() if k not in forbidden}

    if not safe_updates:
        order.pop("_id", None)
        return order

    now = datetime.now(timezone.utc).isoformat()
    safe_updates["updated_at"] = now
    safe_updates["updated_by"] = actor_name

    await db.orders.update_one({"order_id": order_id}, {"$set": safe_updates})
    updated = await db.orders.find_one({"order_id": order_id}, {"_id": 0})
    return updated


# ── Order Items ──

async def get_order_items(order_id: str) -> list[dict]:
    db = await get_db()
    return await db.order_items.find(
        {"order_id": order_id}, {"_id": 0}
    ).sort("created_at", 1).to_list(length=100)


async def get_order_item(order_id: str, item_id: str) -> Optional[dict]:
    db = await get_db()
    return await db.order_items.find_one(
        {"order_id": order_id, "item_id": item_id}, {"_id": 0}
    )


async def update_order_item(
    order_id: str,
    item_id: str,
    updates: dict,
    actor_name: str = "system",
) -> Optional[dict]:
    db = await get_db()
    item = await db.order_items.find_one({"order_id": order_id, "item_id": item_id})
    if not item:
        return None

    forbidden = {"item_id", "order_id", "created_at", "_id", "org_id"}
    safe_updates = {k: v for k, v in updates.items() if k not in forbidden}
    now = datetime.now(timezone.utc).isoformat()
    safe_updates["updated_at"] = now

    await db.order_items.update_one({"item_id": item_id}, {"$set": safe_updates})

    # Recalculate totals if amounts changed
    if any(k in safe_updates for k in ("sell_amount", "supplier_amount", "margin_amount")):
        from app.services.order_mapping_service import _recalculate_order_totals
        await _recalculate_order_totals(order_id)

    return await db.order_items.find_one({"item_id": item_id}, {"_id": 0})


# ── Financial Summary ──

async def get_financial_summary(order_id: str) -> Optional[dict]:
    db = await get_db()
    order = await db.orders.find_one({"order_id": order_id}, {"_id": 0})
    if not order:
        return None
    return {
        "order_id": order_id,
        "sell_total": order.get("total_sell_amount", 0),
        "supplier_total": order.get("total_supplier_amount", 0),
        "margin_total": order.get("total_margin_amount", 0),
        "currency": order.get("currency", "EUR"),
        "settlement_status": order.get("settlement_status", "not_settled"),
    }


# ── Seed Demo Data ──

async def seed_demo_orders(org_id: str = "default_org") -> dict:
    """Seed realistic demo orders for development/testing."""
    db = await get_db()

    # Check if already seeded
    existing = await db.orders.count_documents({"org_id": org_id})
    if existing > 0:
        return {"message": "Demo orders already exist", "count": existing}

    hotels = [
        ("Antalya Luxury Resort", "ratehawk", "htl_001"),
        ("Istanbul Grand Palace", "ratehawk", "htl_002"),
        ("Bodrum Bay Hotel", "paximum", "htl_003"),
        ("Cappadocia Cave Suites", "ratehawk", "htl_004"),
        ("Izmir Seaside Hotel", "hotelbeds", "htl_005"),
    ]

    agencies = ["agency_alpha", "agency_beta", "agency_gamma"]
    customers = ["cust_mehmet", "cust_ayse", "cust_ali", "cust_fatma", "cust_emre"]
    channels = ["B2B", "B2C", "Corporate"]

    statuses_to_create = [
        ("draft", None),
        ("pending_confirmation", None),
        ("confirmed", None),
        ("confirmed", None),
        ("confirmed", None),
        ("cancel_requested", "Customer requested change"),
        ("cancelled", "Customer cancelled"),
        ("closed", "Completed successfully"),
    ]

    created_orders = []
    for i, (target_status, reason) in enumerate(statuses_to_create):
        hotel = hotels[i % len(hotels)]
        agency = agencies[i % len(agencies)]
        customer = customers[i % len(customers)]
        channel = channels[i % len(channels)]

        base_price = random.randint(500, 3000)
        margin_pct = random.uniform(0.08, 0.20)
        supplier_price = round(base_price * (1 - margin_pct))
        margin = base_price - supplier_price

        days_ago = random.randint(1, 30)
        check_in_offset = random.randint(10, 60)
        nights = random.randint(2, 7)

        order = await create_order(
            tenant_id="t_demo",
            agency_id=agency,
            customer_id=customer,
            channel=channel,
            currency="EUR",
            source="demo_seed",
            pricing_trace_id=f"prc_{uuid.uuid4().hex[:8]}",
            items=[{
                "item_type": "hotel",
                "supplier_code": hotel[1],
                "supplier_booking_id": f"sbk_{uuid.uuid4().hex[:8]}" if target_status not in ("draft",) else "",
                "product_reference": hotel[2],
                "product_name": hotel[0],
                "check_in": (datetime.now(timezone.utc) + timedelta(days=check_in_offset)).strftime("%Y-%m-%d"),
                "check_out": (datetime.now(timezone.utc) + timedelta(days=check_in_offset + nights)).strftime("%Y-%m-%d"),
                "passenger_summary": {"adults": random.randint(1, 3), "children": random.randint(0, 2)},
                "room_summary": {"rooms": 1, "room_type": random.choice(["Standard", "Deluxe", "Suite"])},
                "sell_amount": base_price,
                "supplier_amount": supplier_price,
                "margin_amount": margin,
            }],
            actor_name="demo_seeder",
            org_id=org_id,
        )

        # Backdate created_at
        past_date = (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()
        await db.orders.update_one(
            {"order_id": order["order_id"]},
            {"$set": {"created_at": past_date}},
        )

        # Progress through status transitions
        oid = order["order_id"]
        from app.services.order_transition_service import transition_order_status

        if target_status in ("pending_confirmation", "confirmed", "cancel_requested", "cancelled", "closed"):
            await transition_order_status(oid, "pending_confirmation", actor_name="demo_seeder", org_id=org_id)
        if target_status in ("confirmed", "cancel_requested", "cancelled", "closed"):
            await transition_order_status(oid, "confirmed", actor_name="demo_seeder", reason="Supplier confirmed", org_id=org_id)
        if target_status in ("cancel_requested", "cancelled"):
            await transition_order_status(oid, "cancel_requested", actor_name="demo_seeder", reason=reason or "", org_id=org_id)
        if target_status == "cancelled":
            await transition_order_status(oid, "cancelled", actor_name="demo_seeder", reason=reason or "", org_id=org_id)
        if target_status == "closed":
            await transition_order_status(oid, "closed", actor_name="demo_seeder", reason=reason or "", org_id=org_id)

        created_orders.append(order["order_id"])

    return {"message": f"Seeded {len(created_orders)} demo orders", "order_ids": created_orders}
