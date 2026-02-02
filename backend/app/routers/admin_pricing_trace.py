from __future__ import annotations

from typing import Any

from bson import ObjectId
from fastapi import APIRouter, Depends, Query, Request

from app.auth import require_roles
from app.db import get_db
from app.errors import AppError
from app.schemas_pricing_graph import PricingGraphTraceResponse, PricingGraphStepOut
from app.services.audit import write_audit_log
from app.services.offers.search_session_service import get_search_session
from app.utils import now_utc


router = APIRouter(prefix="/api/admin/pricing/graph", tags=["admin_pricing_graph"])


async def _get_org_id(user: dict[str, Any]) -> str:
    org_id = user.get("organization_id")
    if not org_id:
        raise AppError(403, "ORG_NOT_RESOLVED", "Organization not resolved from user context", {})
    return str(org_id)


def _map_steps(raw_steps: Any) -> list[PricingGraphStepOut]:
    steps_out: list[PricingGraphStepOut] = []
    for s in raw_steps or []:
        try:
            steps_out.append(
                PricingGraphStepOut(
                    level=int(s.get("level", 0)),
                    tenant_id=s.get("tenant_id"),
                    node_type=s.get("node_type") or "seller",
                    rule_id=s.get("rule_id"),
                    markup_pct=float(s.get("markup_pct", 0.0)),
                    base_amount=float(s.get("base_amount", 0.0)),
                    delta_amount=float(s.get("delta_amount", 0.0)),
                    amount_after=float(s.get("amount_after", 0.0)),
                    currency=str(s.get("currency") or ""),
                    notes=list(s.get("notes") or []),
                )
            )
        except Exception:
            # Fail-open: skip malformed step
            continue
    return steps_out


@router.get("/trace/by-booking/{booking_id}", response_model=PricingGraphTraceResponse)
async def get_pricing_trace_by_booking(
    booking_id: str,
    request: Request,
    db=Depends(get_db),
    user: dict[str, Any] = Depends(require_roles(["agency_admin"])),
) -> PricingGraphTraceResponse:
    """Return pricing graph trace snapshot from booking.pricing (read-only).

    - Requires agency_admin role
    - Fails with PRICING_TRACE_NOT_AVAILABLE if booking has no pricing snapshot
    """

    org_id = await _get_org_id(user)

    try:
        oid = ObjectId(booking_id)
    except Exception:
        raise AppError(404, "BOOKING_NOT_FOUND", "Booking not found", {"booking_id": booking_id})

    booking = await db.bookings.find_one({"_id": oid, "organization_id": org_id})
    if not booking:
        raise AppError(404, "BOOKING_NOT_FOUND", "Booking not found", {"booking_id": booking_id})

    pricing = booking.get("pricing") or None
    if not pricing:
        raise AppError(
            404,
            "PRICING_TRACE_NOT_AVAILABLE",
            "Booking has no pricing snapshot.",
            {"booking_id": booking_id},
        )

    offer_ref = booking.get("offer_ref") or {}
    buyer_tenant_id = offer_ref.get("buyer_tenant_id")

    currency = pricing.get("currency") or booking.get("currency")
    base_amount = pricing.get("base_amount")
    final_amount = pricing.get("final_amount") or booking.get("amount")
    applied_pct = pricing.get("applied_markup_pct")

    model_version = pricing.get("model_version")
    graph_path = pricing.get("graph_path") or []
    pricing_rule_ids = pricing.get("pricing_rule_ids") or []
    steps = _map_steps(pricing.get("steps") or [])

    resp = PricingGraphTraceResponse(
        source="booking",
        organization_id=org_id,
        buyer_tenant_id=buyer_tenant_id,
        booking_id=booking_id,
        session_id=None,
        offer_token=None,
        currency=currency,
        base_amount=float(base_amount) if base_amount is not None else None,
        final_amount=float(final_amount) if final_amount is not None else None,
        applied_total_markup_pct=float(applied_pct) if applied_pct is not None else None,
        model_version=model_version,
        graph_path=list(graph_path),
        pricing_rule_ids=list(pricing_rule_ids),
        steps=steps,
        notes=["trace_read_from_booking_snapshot"],
    )

    # Best-effort audit, fail-open on errors
    try:
        actor = {
            "actor_type": "user",
            "email": user.get("email"),
            "roles": user.get("roles") or [],
        }
        await write_audit_log(
            db,
            organization_id=org_id,
            actor=actor,
            request=request,
            action="PRICING_TRACE_VIEWED",
            target_type="booking",
            target_id=booking_id,
            before=None,
            after=None,
            meta={
                "source": "booking",
                "booking_id": booking_id,
                "buyer_tenant_id": buyer_tenant_id,
                "model_version": model_version,
                "steps_count": len(steps),
            },
        )
    except Exception:
        pass

    return resp


@router.get("/trace/by-session", response_model=PricingGraphTraceResponse)
async def get_pricing_trace_by_session_offer(
    session_id: str = Query(...),
    offer_token: str = Query(...),
    request: Request = None,
    db=Depends(get_db),
    user: dict[str, Any] = Depends(require_roles(["agency_admin"])),
) -> PricingGraphTraceResponse:
    """Return pricing graph trace snapshot from search_session.pricing_overlay_index.

    - Requires agency_admin role
    - Reads only persisted overlay snapshot, does NOT recompute pricing
    """

    org_id = await _get_org_id(user)

    session = await get_search_session(db, organization_id=org_id, session_id=session_id)
    if not session:
        raise AppError(404, "SEARCH_SESSION_NOT_FOUND", "Search session not found", {"session_id": session_id})

    overlay_index = session.get("pricing_overlay_index") or {}
    overlay = overlay_index.get(offer_token)
    if not overlay:
        raise AppError(404, "OFFER_TOKEN_NOT_FOUND", "Offer token not found in session", {"offer_token": offer_token})

    buyer_tenant_id = session.get("tenant_id")

    currency = overlay.get("currency")
    final_amount = overlay.get("final_amount")
    applied_pct = overlay.get("applied_markup_pct")
    model_version = overlay.get("model_version")
    graph_path = overlay.get("graph_path") or []
    pricing_rule_ids = overlay.get("pricing_rule_ids") or []

    # Attempt to recover base_amount from canonical offers within the session
    base_amount = None
    offers = session.get("offers") or []
    for o in offers:
        if o.get("offer_token") == offer_token:
            price = o.get("price") or {}
            if price.get("currency") == currency:
                base_amount = price.get("amount")
            break

    notes: list[str] = ["trace_read_from_search_session"]
    if base_amount is None:
        notes.append("base_amount_not_available_in_session")

    resp = PricingGraphTraceResponse(
        source="search_session",
        organization_id=org_id,
        buyer_tenant_id=buyer_tenant_id,
        booking_id=None,
        session_id=str(session.get("_id")),
        offer_token=offer_token,
        currency=currency,
        base_amount=float(base_amount) if base_amount is not None else None,
        final_amount=float(final_amount) if final_amount is not None else None,
        applied_total_markup_pct=float(applied_pct) if applied_pct is not None else None,
        model_version=model_version,
        graph_path=list(graph_path),
        pricing_rule_ids=list(pricing_rule_ids),
        steps=[],  # session overlay does not currently persist full steps
        notes=notes,
    )

    try:
        actor = {
            "actor_type": "user",
            "email": user.get("email"),
            "roles": user.get("roles") or [],
        }
        await write_audit_log(
            db,
            organization_id=org_id,
            actor=actor,
            request=request,
            action="PRICING_TRACE_VIEWED",
            target_type="offer",
            target_id=offer_token,
            before=None,
            after=None,
            meta={
                "source": "search_session",
                "session_id": session_id,
                "offer_token": offer_token,
                "buyer_tenant_id": buyer_tenant_id,
                "model_version": model_version,
                "steps_count": len(resp.steps),
            },
        )
    except Exception:
        pass

    return resp
