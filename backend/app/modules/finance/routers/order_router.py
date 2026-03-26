"""Order Router — OMS Phase 1 & 2 API endpoints.

All order CRUD, status transitions, items, events, financial summary,
ledger linkage, and settlement linkage.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional

from app.services.order_service import (
    create_order,
    get_orders,
    get_order_by_id,
    update_order,
    get_order_items,
    get_order_item,
    update_order_item,
    seed_demo_orders,
    search_orders,
    VersionConflictError,
)
from app.services.order_transition_service import (
    confirm_order,
    request_cancel,
    cancel_order,
    close_order,
)
from app.services.order_event_service import get_order_events, get_order_timeline
from app.services.order_mapping_service import (
    map_booking_to_order_item,
    link_supplier_booking,
)
from app.services.oms.order_financial_linkage_service import (
    build_order_financial_summary,
    post_order_to_ledger,
    attach_settlement_run,
    mark_order_settled,
)
from app.services.oms.order_ledger_query_service import (
    get_order_ledger_entries,
    get_order_posting_totals,
    get_order_ledger_postings,
)
from app.services.oms.order_settlement_query_service import (
    get_order_settlements,
    get_order_settlement_status,
)


router = APIRouter(prefix="/api/orders", tags=["OMS - Orders"])


# ── Pydantic Models ──

class OrderItemCreate(BaseModel):
    item_type: str = "hotel"
    supplier_code: str = ""
    supplier_booking_id: str = ""
    product_reference: str = ""
    product_name: str = ""
    check_in: str = ""
    check_out: str = ""
    passenger_summary: Optional[dict] = None
    room_summary: Optional[dict] = None
    sell_amount: float = 0
    supplier_amount: float = 0
    margin_amount: float = 0
    pricing_trace_id: str = ""
    booking_trace_id: str = ""
    metadata: Optional[dict] = None


class OrderCreate(BaseModel):
    tenant_id: str = ""
    agency_id: str = ""
    customer_id: str = ""
    channel: str = "B2B"
    currency: str = "EUR"
    source: str = "manual"
    pricing_trace_id: str = ""
    metadata: Optional[dict] = None
    items: list[OrderItemCreate] = Field(default_factory=list)


class OrderUpdate(BaseModel):
    customer_id: Optional[str] = None
    agency_id: Optional[str] = None
    channel: Optional[str] = None
    metadata: Optional[dict] = None
    version: Optional[int] = None  # For optimistic locking


class StatusAction(BaseModel):
    actor: str = "admin"
    reason: str = ""


class LinkSupplierBooking(BaseModel):
    supplier_booking_id: str
    supplier_booking_status: str = "pending"
    actor: str = "system"


# ── Order CRUD ──

@router.post("")
async def api_create_order(body: OrderCreate):
    order = await create_order(
        tenant_id=body.tenant_id,
        agency_id=body.agency_id,
        customer_id=body.customer_id,
        channel=body.channel,
        currency=body.currency,
        source=body.source,
        items=[item.model_dump() for item in body.items],
        pricing_trace_id=body.pricing_trace_id,
        metadata=body.metadata,
        actor_name="api",
    )
    return order


@router.get("")
async def api_list_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status: Optional[str] = None,
    channel: Optional[str] = None,
    agency_id: Optional[str] = None,
):
    return await get_orders(skip=skip, limit=limit, status=status, channel=channel, agency_id=agency_id)


@router.get("/search")
async def api_search_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status: Optional[str] = None,
    channel: Optional[str] = None,
    agency_id: Optional[str] = None,
    customer_id: Optional[str] = None,
    supplier_code: Optional[str] = None,
    order_number: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    settlement_status: Optional[str] = None,
    q: Optional[str] = None,
):
    return await search_orders(
        skip=skip,
        limit=limit,
        status=status,
        channel=channel,
        agency_id=agency_id,
        customer_id=customer_id,
        supplier_code=supplier_code,
        order_number=order_number,
        date_from=date_from,
        date_to=date_to,
        settlement_status=settlement_status,
        q=q,
    )


@router.get("/{order_id}")
async def api_get_order(order_id: str):
    order = await get_order_by_id(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.patch("/{order_id}")
async def api_update_order(order_id: str, body: OrderUpdate):
    updates = body.model_dump(exclude_none=True)
    expected_version = updates.pop("version", None)
    try:
        result = await update_order(order_id, updates, expected_version=expected_version)
    except VersionConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    if not result:
        raise HTTPException(status_code=404, detail="Order not found")
    return result


# ── Status Transitions (explicit command endpoints) ──

@router.post("/{order_id}/confirm")
async def api_confirm_order(order_id: str, body: StatusAction):
    result = await confirm_order(order_id, actor_name=body.actor, reason=body.reason)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Transition failed"))
    return result


@router.post("/{order_id}/request-cancel")
async def api_request_cancel(order_id: str, body: StatusAction):
    result = await request_cancel(order_id, actor_name=body.actor, reason=body.reason)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Transition failed"))
    return result


@router.post("/{order_id}/cancel")
async def api_cancel_order(order_id: str, body: StatusAction):
    result = await cancel_order(order_id, actor_name=body.actor, reason=body.reason)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Transition failed"))
    return result


@router.post("/{order_id}/close")
async def api_close_order(order_id: str, body: StatusAction):
    result = await close_order(order_id, actor_name=body.actor, reason=body.reason)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Transition failed"))
    return result


# ── Order Items ──

@router.post("/{order_id}/items")
async def api_add_item(order_id: str, body: OrderItemCreate):
    order = await get_order_by_id(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    item = await map_booking_to_order_item(
        order_id=order_id,
        item_type=body.item_type,
        supplier_code=body.supplier_code,
        supplier_booking_id=body.supplier_booking_id,
        product_reference=body.product_reference,
        product_name=body.product_name,
        check_in=body.check_in,
        check_out=body.check_out,
        passenger_summary=body.passenger_summary,
        room_summary=body.room_summary,
        sell_amount=body.sell_amount,
        supplier_amount=body.supplier_amount,
        margin_amount=body.margin_amount,
        currency=order.get("currency", "EUR"),
        pricing_trace_id=body.pricing_trace_id,
        booking_trace_id=body.booking_trace_id,
        metadata=body.metadata,
        org_id=order.get("org_id", "default_org"),
    )
    return item


@router.get("/{order_id}/items")
async def api_list_items(order_id: str):
    return await get_order_items(order_id)


@router.get("/{order_id}/items/{item_id}")
async def api_get_item(order_id: str, item_id: str):
    item = await get_order_item(order_id, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Order item not found")
    return item


@router.patch("/{order_id}/items/{item_id}")
async def api_update_item(order_id: str, item_id: str, body: dict):
    result = await update_order_item(order_id, item_id, body)
    if not result:
        raise HTTPException(status_code=404, detail="Order item not found")
    return result


# ── Link Supplier Booking ──

@router.post("/{order_id}/items/{item_id}/link-supplier")
async def api_link_supplier(order_id: str, item_id: str, body: LinkSupplierBooking):
    result = await link_supplier_booking(
        order_id=order_id,
        item_id=item_id,
        supplier_booking_id=body.supplier_booking_id,
        supplier_booking_status=body.supplier_booking_status,
        actor_name=body.actor,
    )
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Link failed"))
    return result


# ── Events / Timeline ──

@router.get("/{order_id}/events")
async def api_get_events(order_id: str, limit: int = Query(100, ge=1, le=500)):
    return await get_order_events(order_id, limit=limit)


@router.get("/{order_id}/timeline")
async def api_get_timeline(order_id: str, limit: int = Query(50, ge=1, le=200)):
    return await get_order_timeline(order_id, limit=limit)


# ── Financial Summary (Phase 2: Enhanced) ──

@router.get("/{order_id}/financial-summary")
async def api_financial_summary(order_id: str):
    """Get the full financial summary for an order (Phase 2 enhanced)."""
    summary = await build_order_financial_summary(order_id)
    if summary.get("error"):
        raise HTTPException(status_code=404, detail=summary["error"])
    return summary


@router.post("/{order_id}/financial-summary/rebuild")
async def api_rebuild_financial_summary(order_id: str):
    """Rebuild financial summary from scratch (ops/debug)."""
    summary = await build_order_financial_summary(order_id)
    if summary.get("error"):
        raise HTTPException(status_code=404, detail=summary["error"])
    return {"message": "Summary rebuilt", "summary": summary}


# ── Ledger Linkage (Phase 2) ──

@router.get("/{order_id}/ledger-entries")
async def api_order_ledger_entries(order_id: str):
    """Get all ledger entries linked to this order."""
    entries = await get_order_ledger_entries(order_id)
    totals = await get_order_posting_totals(order_id)
    return {"entries": entries, "totals": totals}


@router.get("/{order_id}/ledger-postings")
async def api_order_ledger_postings(order_id: str):
    """Get all ledger posting documents for this order."""
    return await get_order_ledger_postings(order_id)


@router.post("/{order_id}/post-to-ledger")
async def api_post_to_ledger(order_id: str, body: StatusAction):
    """Manually post an order to the ledger."""
    result = await post_order_to_ledger(order_id, actor_name=body.actor)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Posting failed"))
    return result


# ── Settlement Linkage (Phase 2) ──

@router.get("/{order_id}/settlements")
async def api_order_settlements(order_id: str):
    """Get all settlement runs linked to this order."""
    runs = await get_order_settlements(order_id)
    status = await get_order_settlement_status(order_id)
    return {"runs": runs, "status": status}


class AttachSettlement(BaseModel):
    run_id: str
    actor: str = "system"


@router.post("/{order_id}/settlements/link")
async def api_link_settlement(order_id: str, body: AttachSettlement):
    """Link a settlement run to this order."""
    result = await attach_settlement_run(order_id, body.run_id, actor_name=body.actor)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Link failed"))
    return result


@router.post("/{order_id}/mark-settled")
async def api_mark_settled(order_id: str, body: StatusAction):
    """Mark an order as fully settled."""
    result = await mark_order_settled(order_id, actor_name=body.actor)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed"))
    return result


# ── Seed Demo Data ──

@router.post("/seed")
async def api_seed_demo():
    return await seed_demo_orders()
