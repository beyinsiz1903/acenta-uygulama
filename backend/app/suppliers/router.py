"""Supplier Ecosystem API Router.

Namespace: /api/suppliers/ecosystem/*

Endpoints:
  - Search: multi-supplier search
  - Availability: single-supplier availability check
  - Pricing: price validation
  - Hold: create reservation hold
  - Confirm: confirm booking with supplier
  - Cancel: cancel booking
  - Health: supplier health dashboard
  - Failover: failover audit log
  - Orchestration: run full booking flow
  - Partners: channel partner management
  - Cache: cache management
  - Registry: adapter registry info
"""
from __future__ import annotations

import uuid
import logging
from datetime import date
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field

from app.db import get_db
from app.auth import require_roles

logger = logging.getLogger("routers.supplier_ecosystem")

router = APIRouter(prefix="/api/suppliers/ecosystem", tags=["supplier_ecosystem"])


# ---------------------------------------------------------------------------
# Request/Response models (API-layer, thin wrappers around domain schemas)
# ---------------------------------------------------------------------------

class SearchBody(BaseModel):
    product_type: str = "hotel"
    destination: Optional[str] = None
    origin: Optional[str] = None
    check_in: Optional[date] = None
    check_out: Optional[date] = None
    departure_date: Optional[date] = None
    return_date: Optional[date] = None
    adults: int = 1
    children: int = 0
    rooms: int = 1
    supplier_codes: List[str] = Field(default_factory=list)
    sort_by: str = "price_asc"
    page: int = 1
    page_size: int = 20


class HoldBody(BaseModel):
    supplier_code: str
    supplier_item_id: str
    product_type: str = "hotel"
    guests: List[Dict[str, Any]] = Field(default_factory=list)
    contact: Dict[str, Any] = Field(default_factory=dict)
    special_requests: Optional[str] = None


class ConfirmBody(BaseModel):
    supplier_code: str
    hold_id: str
    payment_reference: Optional[str] = None


class CancelBody(BaseModel):
    supplier_code: str
    supplier_booking_id: str
    reason: Optional[str] = None


class OrchestrateBody(BaseModel):
    booking_id: str
    supplier_code: str
    supplier_item_id: str
    product_type: str = "hotel"
    guests: List[Dict[str, Any]] = Field(default_factory=list)
    contact: Dict[str, Any] = Field(default_factory=dict)
    payment_reference: Optional[str] = None
    special_requests: Optional[str] = None


class PartnerCreateBody(BaseModel):
    name: str
    partner_type: str = "sub_agency"
    contact_email: Optional[str] = None
    allowed_suppliers: List[str] = Field(default_factory=list)
    allowed_product_types: List[str] = Field(default_factory=list)
    pricing_tier: str = "standard"
    commission_rate: float = 8.0
    credit_limit: float = 0
    credit_currency: str = "TRY"


# ---------------------------------------------------------------------------
# Helper to build SupplierContext from request
# ---------------------------------------------------------------------------

def _build_ctx(request: Request):
    from app.suppliers.contracts.schemas import SupplierContext as SupCtx
    user = getattr(request.state, "user", {}) or {}
    return SupCtx(
        request_id=str(uuid.uuid4()),
        organization_id=user.get("organization_id", ""),
        tenant_id=user.get("tenant_id"),
        user_id=user.get("user_id") or user.get("email", ""),
        channel="direct",
        currency="TRY",
    )


# ============================================================================
# SEARCH
# ============================================================================

@router.post("/search", summary="Multi-supplier search")
async def supplier_search(
    body: SearchBody,
    request: Request,
    user=Depends(require_roles(["agency_admin", "admin", "super_admin", "agent"])),
):
    """Fan out search to multiple suppliers, aggregate and return results."""
    from app.suppliers.contracts.schemas import SearchRequest, SupplierProductType
    from app.suppliers.aggregator.service import aggregate_search

    ctx = _build_ctx(request)
    db = await get_db()

    search_req = SearchRequest(
        supplier_codes=body.supplier_codes,
        product_type=SupplierProductType(body.product_type),
        destination=body.destination,
        origin=body.origin,
        check_in=body.check_in,
        check_out=body.check_out,
        departure_date=body.departure_date,
        return_date=body.return_date,
        adults=body.adults,
        children=body.children,
        rooms=body.rooms,
        sort_by=body.sort_by,
        page=body.page,
        page_size=body.page_size,
    )

    # Try cache first
    from app.suppliers.cache import get_cached_results
    cached = await get_cached_results(ctx, search_req)
    if cached and not cached.degraded:
        return cached.model_dump(mode="json")

    result = await aggregate_search(ctx, search_req, db=db)
    return result.model_dump(mode="json")


# ============================================================================
# AVAILABILITY
# ============================================================================

@router.post("/availability", summary="Check single-supplier availability")
async def check_availability(
    supplier_code: str = Query(...),
    supplier_item_id: str = Query(...),
    product_type: str = Query("hotel"),
    check_in: Optional[date] = Query(None),
    check_out: Optional[date] = Query(None),
    adults: int = Query(1),
    request: Request = None,
    user=Depends(require_roles(["agency_admin", "admin", "super_admin", "agent"])),
):
    from app.suppliers.contracts.schemas import AvailabilityRequest, SupplierProductType
    from app.suppliers.registry import supplier_registry

    ctx = _build_ctx(request)
    adapter = supplier_registry.get(supplier_code)

    avail_req = AvailabilityRequest(
        supplier_code=supplier_code,
        supplier_item_id=supplier_item_id,
        product_type=SupplierProductType(product_type),
        check_in=check_in,
        check_out=check_out,
        adults=adults,
    )
    result = await adapter.check_availability(ctx, avail_req)
    return result.model_dump(mode="json")


# ============================================================================
# PRICING
# ============================================================================

@router.post("/pricing", summary="Validate supplier pricing")
async def validate_pricing(
    supplier_code: str = Query(...),
    supplier_item_id: str = Query(...),
    product_type: str = Query("hotel"),
    check_in: Optional[date] = Query(None),
    check_out: Optional[date] = Query(None),
    request: Request = None,
    user=Depends(require_roles(["agency_admin", "admin", "super_admin", "agent"])),
):
    from app.suppliers.contracts.schemas import PricingRequest, SupplierProductType
    from app.suppliers.registry import supplier_registry
    from app.suppliers.pricing import compute_sell_price

    ctx = _build_ctx(request)
    adapter = supplier_registry.get(supplier_code)

    pricing_req = PricingRequest(
        supplier_code=supplier_code,
        supplier_item_id=supplier_item_id,
        product_type=SupplierProductType(product_type),
        check_in=check_in,
        check_out=check_out,
    )
    result = await adapter.get_pricing(ctx, pricing_req)

    # Apply pricing engine
    if result.supplier_price:
        result.sell_price = compute_sell_price(
            result.supplier_price,
            product_type=product_type,
            supplier_code=supplier_code,
        )

    return result.model_dump(mode="json")


# ============================================================================
# HOLD
# ============================================================================

@router.post("/hold", summary="Create reservation hold")
async def create_hold(
    body: HoldBody,
    request: Request,
    user=Depends(require_roles(["agency_admin", "admin", "super_admin", "agent"])),
):
    from app.suppliers.contracts.schemas import HoldRequest, SupplierProductType
    from app.suppliers.registry import supplier_registry

    ctx = _build_ctx(request)
    adapter = supplier_registry.get(body.supplier_code)

    hold_req = HoldRequest(
        supplier_code=body.supplier_code,
        supplier_item_id=body.supplier_item_id,
        product_type=SupplierProductType(body.product_type),
        guests=body.guests,
        contact=body.contact,
        special_requests=body.special_requests,
    )
    result = await adapter.create_hold(ctx, hold_req)
    return result.model_dump(mode="json")


# ============================================================================
# CONFIRM
# ============================================================================

@router.post("/confirm", summary="Confirm booking with supplier")
async def confirm_booking(
    body: ConfirmBody,
    request: Request,
    user=Depends(require_roles(["agency_admin", "admin", "super_admin", "agent"])),
):
    from app.suppliers.contracts.schemas import ConfirmRequest
    from app.suppliers.registry import supplier_registry

    ctx = _build_ctx(request)
    adapter = supplier_registry.get(body.supplier_code)

    confirm_req = ConfirmRequest(
        supplier_code=body.supplier_code,
        hold_id=body.hold_id,
        payment_reference=body.payment_reference,
        idempotency_key=str(uuid.uuid4()),
    )
    result = await adapter.confirm_booking(ctx, confirm_req)
    return result.model_dump(mode="json")


# ============================================================================
# CANCEL
# ============================================================================

@router.post("/cancel", summary="Cancel booking with supplier")
async def cancel_booking(
    body: CancelBody,
    request: Request,
    user=Depends(require_roles(["agency_admin", "admin", "super_admin", "agent"])),
):
    from app.suppliers.contracts.schemas import CancelRequest
    from app.suppliers.registry import supplier_registry

    ctx = _build_ctx(request)
    adapter = supplier_registry.get(body.supplier_code)

    cancel_req = CancelRequest(
        supplier_code=body.supplier_code,
        supplier_booking_id=body.supplier_booking_id,
        reason=body.reason,
        idempotency_key=str(uuid.uuid4()),
    )
    result = await adapter.cancel_booking(ctx, cancel_req)
    return result.model_dump(mode="json")


# ============================================================================
# ORCHESTRATION — full booking flow
# ============================================================================

@router.post("/orchestrate", summary="Execute full booking orchestration")
async def orchestrate_booking_endpoint(
    body: OrchestrateBody,
    request: Request,
    user=Depends(require_roles(["agency_admin", "admin", "super_admin", "agent"])),
):
    from app.suppliers.orchestrator.service import orchestrate_booking

    ctx = _build_ctx(request)
    db = await get_db()

    result = await orchestrate_booking(
        db, ctx,
        booking_id=body.booking_id,
        supplier_code=body.supplier_code,
        supplier_item_id=body.supplier_item_id,
        product_type=body.product_type,
        guests=body.guests,
        contact=body.contact,
        payment_reference=body.payment_reference,
        special_requests=body.special_requests,
    )
    return result


# ============================================================================
# HEALTH — supplier health dashboard
# ============================================================================

@router.get("/health", summary="Supplier health dashboard")
async def supplier_health_dashboard(
    request: Request,
    user=Depends(require_roles(["agency_admin", "admin", "super_admin"])),
):
    ctx = _build_ctx(request)
    db = await get_db()

    from app.suppliers.registry import supplier_registry
    adapters = supplier_registry.get_all()

    health_data = []
    for adapter in adapters:
        doc = await db.supplier_ecosystem_health.find_one(
            {"organization_id": ctx.organization_id, "supplier_code": adapter.supplier_code},
            {"_id": 0},
        )
        health_data.append({
            "supplier_code": adapter.supplier_code,
            "supplier_type": adapter.supplier_type.value,
            "display_name": adapter.display_name,
            "health": doc or {"state": "unknown", "score": None},
        })

    return {"suppliers": health_data, "total": len(health_data)}


# ============================================================================
# HEALTH SCORING — trigger health score computation
# ============================================================================

@router.post("/health/{supplier_code}/compute", summary="Compute supplier health score")
async def compute_supplier_health(
    supplier_code: str,
    request: Request,
    user=Depends(require_roles(["agency_admin", "admin", "super_admin"])),
):
    ctx = _build_ctx(request)
    db = await get_db()

    from app.suppliers.health import compute_and_store_health
    score = await compute_and_store_health(db, ctx.organization_id, supplier_code)

    return {
        "supplier_code": score.supplier_code,
        "score": score.score,
        "state": score.state,
        "breakdown": {
            "latency": score.latency_score,
            "error": score.error_score,
            "timeout": score.timeout_score,
            "confirmation": score.confirmation_score,
            "freshness": score.freshness_score,
        },
    }


# ============================================================================
# FAILOVER AUDIT
# ============================================================================

@router.get("/failover-logs", summary="View failover audit log")
async def failover_audit_log(
    request: Request,
    limit: int = Query(20, le=100),
    user=Depends(require_roles(["agency_admin", "admin", "super_admin"])),
):
    ctx = _build_ctx(request)
    db = await get_db()

    cursor = db.supplier_failover_logs.find(
        {"organization_id": ctx.organization_id},
        {"_id": 0},
    ).sort("created_at", -1).limit(limit)

    logs = await cursor.to_list(length=limit)
    return {"logs": logs, "total": len(logs)}


# ============================================================================
# ORCHESTRATION RUNS
# ============================================================================

@router.get("/orchestration-runs", summary="List orchestration runs")
async def list_orchestration_runs(
    request: Request,
    booking_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(20, le=100),
    user=Depends(require_roles(["agency_admin", "admin", "super_admin"])),
):
    ctx = _build_ctx(request)
    db = await get_db()

    query: Dict[str, Any] = {"organization_id": ctx.organization_id}
    if booking_id:
        query["booking_id"] = booking_id
    if status:
        query["status"] = status

    cursor = db.booking_orchestration_runs.find(query, {"_id": 0}).sort("created_at", -1).limit(limit)
    runs = await cursor.to_list(length=limit)
    return {"runs": runs, "total": len(runs)}


# ============================================================================
# CHANNEL PARTNERS
# ============================================================================

@router.get("/partners", summary="List distribution partners")
async def list_partners_endpoint(
    request: Request,
    status: Optional[str] = Query(None),
    partner_type: Optional[str] = Query(None),
    user=Depends(require_roles(["agency_admin", "admin", "super_admin"])),
):
    ctx = _build_ctx(request)
    db = await get_db()

    from app.suppliers.channel import list_partners
    partners = await list_partners(db, ctx.organization_id, status=status, partner_type=partner_type)
    return {"partners": partners, "total": len(partners)}


@router.post("/partners", summary="Create distribution partner", status_code=201)
async def create_partner_endpoint(
    body: PartnerCreateBody,
    request: Request,
    user=Depends(require_roles(["agency_admin", "admin", "super_admin"])),
):
    ctx = _build_ctx(request)
    db = await get_db()

    from app.suppliers.channel import create_partner
    result = await create_partner(db, ctx.organization_id, body.model_dump())
    return result


@router.post("/partners/{partner_id}/approve", summary="Approve partner")
async def approve_partner_endpoint(
    partner_id: str,
    request: Request,
    user=Depends(require_roles(["agency_admin", "admin", "super_admin"])),
):
    ctx = _build_ctx(request)
    db = await get_db()

    from app.suppliers.channel import approve_partner
    result = await approve_partner(db, ctx.organization_id, partner_id, ctx.user_id)
    return result


# ============================================================================
# CACHE MANAGEMENT
# ============================================================================

@router.get("/cache/stats", summary="Cache statistics")
async def cache_stats(
    request: Request,
    user=Depends(require_roles(["agency_admin", "admin", "super_admin"])),
):
    ctx = _build_ctx(request)
    from app.suppliers.cache import get_cache_stats
    return await get_cache_stats(ctx.organization_id)


@router.post("/cache/invalidate", summary="Invalidate supplier cache")
async def invalidate_cache(
    request: Request,
    product_type: Optional[str] = Query(None),
    user=Depends(require_roles(["agency_admin", "admin", "super_admin"])),
):
    ctx = _build_ctx(request)
    from app.suppliers.cache import invalidate_supplier_cache
    count = await invalidate_supplier_cache(ctx.organization_id, product_type)
    return {"invalidated_keys": count}


# ============================================================================
# REGISTRY INFO
# ============================================================================

@router.get("/registry", summary="List registered supplier adapters")
async def list_registry(
    request: Request,
    user=Depends(require_roles(["agency_admin", "admin", "super_admin"])),
):
    from app.suppliers.registry import supplier_registry
    adapters = supplier_registry.get_all()
    return {
        "adapters": [a.get_info() for a in adapters],
        "total": len(adapters),
    }


# ============================================================================
# STATE MACHINE INFO
# ============================================================================

@router.get("/booking-states", summary="Get booking state machine info")
async def booking_states_info():
    from app.suppliers.state_machine import BookingState, TRANSITIONS, get_allowed_transitions

    states = []
    for state in BookingState:
        states.append({
            "state": state.value,
            "allowed_transitions": [s.value for s in get_allowed_transitions(state)],
        })

    return {
        "states": states,
        "total_states": len(BookingState),
        "total_transitions": len(TRANSITIONS),
    }
