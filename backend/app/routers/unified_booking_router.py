"""Unified Booking Router — real supplier-backed search, revalidation, and booking.

Exposes the full unified booking lifecycle:
  1. /search — aggregated search across real suppliers
  2. /revalidate — price/availability check before booking
  3. /book — execute booking with fallback
  4. /reconciliation — check booking reconciliation status
  5. /audit — booking audit trail
  6. /registry — registered adapters and capabilities
  7. /metrics — booking execution metrics
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Body, HTTPException

from app.db import get_db
from app.auth import require_roles

router = APIRouter(prefix="/api/unified-booking", tags=["unified_booking"])


def _parse_date(v: str | None) -> date | None:
    if not v:
        return None
    try:
        return date.fromisoformat(v)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# 1. Unified Search
# ---------------------------------------------------------------------------

@router.post("/search")
async def unified_search(
    payload: dict = Body(...),
    current_user=Depends(require_roles(["admin", "super_admin", "agency_admin"])),
    db=Depends(get_db),
) -> dict[str, Any]:
    """Search across all registered real suppliers using the contract interface.

    Body:
      product_type: hotel | tour | flight | transfer | activity
      destination: str
      check_in: date str (YYYY-MM-DD)
      check_out: date str (YYYY-MM-DD)
      adults: int (default 2)
      children: int (default 0)
      currency: str (default TRY)
      suppliers: optional list of specific supplier codes
    """
    from app.suppliers.registry import supplier_registry
    from app.suppliers.contracts.schemas import SearchRequest, SupplierContext, SupplierProductType
    from app.suppliers import booking_audit
    import asyncio
    import time

    org_id = current_user.get("organization_id", current_user.get("org_id", ""))
    product_type = payload.get("product_type", "hotel")
    request_id = str(uuid.uuid4())

    ctx = SupplierContext(
        request_id=request_id,
        organization_id=org_id,
        currency=payload.get("currency", "TRY"),
        timeout_ms=int(payload.get("timeout_ms", 15000)),
    )

    try:
        spt = SupplierProductType(product_type)
    except ValueError:
        raise HTTPException(400, f"Invalid product_type: {product_type}")

    search_req = SearchRequest(
        product_type=spt,
        destination=payload.get("destination", ""),
        origin=payload.get("origin", ""),
        check_in=_parse_date(payload.get("check_in")),
        check_out=_parse_date(payload.get("check_out")),
        departure_date=_parse_date(payload.get("departure_date") or payload.get("check_in")),
        return_date=_parse_date(payload.get("return_date") or payload.get("check_out")),
        adults=payload.get("adults", 2),
        children=payload.get("children", 0),
    )

    # Find eligible real adapters
    target_suppliers = payload.get("suppliers")
    adapters = supplier_registry.get_by_product_type(product_type)
    real_adapters = [a for a in adapters if not a.supplier_code.startswith("mock_")]
    if target_suppliers:
        real_adapters = [a for a in real_adapters if a.supplier_code in target_suppliers]

    # Inject db into real bridges
    for a in real_adapters:
        if hasattr(a, "db"):
            a.db = db

    if not real_adapters:
        return {
            "request_id": request_id,
            "product_type": product_type,
            "items": [],
            "total": 0,
            "suppliers_queried": [],
            "message": f"No real suppliers registered for '{product_type}'",
        }

    # Fan-out parallel search
    start = time.monotonic()

    async def _search_one(adapter):
        try:
            result = await adapter.search(ctx, search_req)
            booking_audit.record_latency(adapter.supplier_code, result.search_duration_ms if result.search_duration_ms else 0)
            return {"supplier": adapter.supplier_code, "result": result, "error": None}
        except Exception as e:
            return {"supplier": adapter.supplier_code, "result": None, "error": str(e)}

    results = await asyncio.gather(*[_search_one(a) for a in real_adapters], return_exceptions=True)

    all_items = []
    suppliers_queried = []
    suppliers_failed = []
    for r in results:
        if isinstance(r, Exception):
            continue
        suppliers_queried.append(r["supplier"])
        if r["result"]:
            for item in r["result"].items:
                all_items.append(item.model_dump() if hasattr(item, "model_dump") else item.dict())
        if r["error"]:
            suppliers_failed.append({"supplier": r["supplier"], "error": r["error"]})

    # Sort by supplier_price ascending
    all_items.sort(key=lambda x: float(x.get("supplier_price", 0) or 0))
    total_ms = round((time.monotonic() - start) * 1000, 1)

    await booking_audit.log_booking_event(db, "unified_search", org_id, ",".join(suppliers_queried), details={
        "product_type": product_type, "destination": payload.get("destination"),
        "total_items": len(all_items), "total_ms": total_ms,
    })

    # Track search analytics
    from app.suppliers.search_analytics import track_search
    await track_search(
        db, org_id, product_type, payload.get("destination", ""),
        payload.get("check_in"), payload.get("check_out"),
        payload.get("adults", 2), payload.get("children", 0),
        len(all_items), suppliers_queried, total_ms,
    )

    return {
        "request_id": request_id,
        "product_type": product_type,
        "items": all_items,
        "total": len(all_items),
        "suppliers_queried": suppliers_queried,
        "suppliers_failed": suppliers_failed,
        "search_duration_ms": total_ms,
        "organization_id": org_id,
    }


# ---------------------------------------------------------------------------
# 2. Price Revalidation
# ---------------------------------------------------------------------------

@router.post("/revalidate")
async def revalidate_price_endpoint(
    payload: dict = Body(...),
    current_user=Depends(require_roles(["admin", "super_admin", "agency_admin"])),
    db=Depends(get_db),
) -> dict[str, Any]:
    """Pre-booking price and availability check.

    Body:
      supplier_code: str
      supplier_item_id: str
      original_price: float
      currency: str (default TRY)
      product_type: str (default hotel)
    """
    from app.suppliers.price_revalidation import revalidate_price
    from app.suppliers import booking_audit

    org_id = current_user.get("organization_id", current_user.get("org_id", ""))
    result = await revalidate_price(
        db, org_id,
        supplier_code=payload["supplier_code"],
        supplier_item_id=payload["supplier_item_id"],
        original_price=payload["original_price"],
        currency=payload.get("currency", "TRY"),
        product_type=payload.get("product_type", "hotel"),
    )

    booking_audit.inc("revalidation_total")
    if result.price_drift_pct != 0:
        booking_audit.inc("price_drift_total")
    if not result.can_proceed:
        booking_audit.inc("revalidation_abort_total")

    await booking_audit.log_booking_event(db, "price_revalidation", org_id, payload["supplier_code"], details={
        "valid": result.valid, "drift_pct": result.price_drift_pct, "can_proceed": result.can_proceed,
    })

    return result.model_dump() if hasattr(result, "model_dump") else result.dict()


# ---------------------------------------------------------------------------
# 3. Execute Booking
# ---------------------------------------------------------------------------

@router.post("/book")
async def execute_booking(
    payload: dict = Body(...),
    current_user=Depends(require_roles(["admin", "super_admin", "agency_admin"])),
    db=Depends(get_db),
) -> dict[str, Any]:
    """Execute a unified booking through the orchestrator.

    Body:
      supplier_code: str
      supplier_item_id: str
      product_type: str
      travellers: list[{first_name, last_name, ...}]
      contact: {email, phone}
      billing: {company_name, tax_id, ...} (optional)
      expected_price: float
      currency: str
      special_requests: str (optional)
    """
    from app.suppliers.registry import supplier_registry
    from app.suppliers.contracts.schemas import (
        ConfirmRequest, SupplierContext,
    )
    from app.suppliers.price_revalidation import revalidate_price
    from app.suppliers.failover import failover_engine
    from app.suppliers.booking_reconciliation import create_reconciliation_record
    from app.suppliers import booking_audit
    import time

    org_id = current_user.get("organization_id", current_user.get("org_id", ""))
    supplier_code = payload["supplier_code"]
    idempotency_key = payload.get("idempotency_key", str(uuid.uuid4()))
    internal_booking_id = str(uuid.uuid4())
    start = time.monotonic()

    booking_audit.inc("booking_attempts_total")
    await booking_audit.log_booking_event(db, "booking_attempt", org_id, supplier_code, internal_booking_id, {
        "supplier_item_id": payload.get("supplier_item_id"),
        "expected_price": payload.get("expected_price"),
    })

    ctx = SupplierContext(
        request_id=idempotency_key,
        organization_id=org_id,
        currency=payload.get("currency", "TRY"),
    )

    # Step 1: Price revalidation guard
    expected_price = payload.get("expected_price", 0)
    if expected_price > 0:
        reval = await revalidate_price(
            db, org_id, supplier_code,
            payload.get("supplier_item_id", ""),
            expected_price,
            payload.get("currency", "TRY"),
            payload.get("product_type", "hotel"),
        )
        if not reval.can_proceed:
            booking_audit.inc("booking_failure_total")
            await booking_audit.log_booking_event(db, "booking_aborted_price", org_id, supplier_code, internal_booking_id, {
                "reason": reval.abort_reason, "drift_pct": reval.price_drift_pct,
            })
            return {
                "status": "aborted",
                "reason": reval.abort_reason,
                "revalidation": reval.model_dump() if hasattr(reval, "model_dump") else reval.dict(),
                "internal_booking_id": internal_booking_id,
            }

    # Step 2: Attempt booking on primary supplier
    confirm_req = ConfirmRequest(
        supplier_code=supplier_code,
        hold_id=payload.get("supplier_item_id", ""),
        idempotency_key=idempotency_key,
        payment_reference=str(payload.get("expected_price", "")),
    )

    result = None
    used_supplier = supplier_code
    fallback_used = False

    try:
        adapter = supplier_registry.get(supplier_code)
        if hasattr(adapter, "db"):
            adapter.db = db
        result = await adapter.confirm_booking(ctx, confirm_req)
    except Exception as primary_error:
        # Step 3: Fallback
        await booking_audit.log_booking_event(db, "booking_primary_failed", org_id, supplier_code, internal_booking_id, {
            "error": str(primary_error),
        })
        booking_audit.inc("fallback_trigger_total")

        fallback_chain = failover_engine.get_fallback_chain(supplier_code)
        for fb_code in fallback_chain:
            try:
                fb_adapter = supplier_registry.get(fb_code)
                if hasattr(fb_adapter, "db"):
                    fb_adapter.db = db
                fb_confirm = ConfirmRequest(
                    supplier_code=fb_code,
                    hold_id=payload.get("supplier_item_id", ""),
                    idempotency_key=idempotency_key,
                    payment_reference=str(payload.get("expected_price", "")),
                )
                result = await fb_adapter.confirm_booking(ctx, fb_confirm)
                used_supplier = fb_code
                fallback_used = True
                await booking_audit.log_booking_event(db, "fallback_success", org_id, fb_code, internal_booking_id, {
                    "original_supplier": supplier_code,
                })
                break
            except Exception as fb_err:
                await booking_audit.log_booking_event(db, "fallback_failed", org_id, fb_code, internal_booking_id, {
                    "error": str(fb_err),
                })
                continue

    duration_ms = round((time.monotonic() - start) * 1000, 1)
    booking_audit.record_latency(used_supplier, duration_ms)

    if result and result.status == "confirmed":
        booking_audit.inc("booking_success_total")

        # Create reconciliation record
        confirmed_price = float(result.supplier_metadata.get("price", expected_price)) if result.supplier_metadata else expected_price
        await create_reconciliation_record(
            db, internal_booking_id, used_supplier,
            result.supplier_booking_id, expected_price, confirmed_price,
            payload.get("currency", "TRY"), "confirmed",
        )

        # Persist booking
        booking_doc = {
            "internal_booking_id": internal_booking_id,
            "supplier_code": used_supplier,
            "supplier_booking_id": result.supplier_booking_id,
            "product_type": payload.get("product_type", "hotel"),
            "status": "confirmed",
            "organization_id": org_id,
            "travellers": payload.get("travellers", []),
            "contact": payload.get("contact", {}),
            "billing": payload.get("billing", {}),
            "booked_price": expected_price,
            "confirmed_price": confirmed_price,
            "currency": payload.get("currency", "TRY"),
            "fallback_used": fallback_used,
            "original_supplier": supplier_code if fallback_used else None,
            "confirmation_code": result.confirmation_code,
            "idempotency_key": idempotency_key,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "duration_ms": duration_ms,
        }
        await db["unified_bookings"].insert_one(booking_doc)
        booking_doc.pop("_id", None)

        await booking_audit.log_booking_event(db, "booking_confirmed", org_id, used_supplier, internal_booking_id, {
            "supplier_booking_id": result.supplier_booking_id, "duration_ms": duration_ms, "fallback_used": fallback_used,
        })

        # Track booking confirm analytics
        from app.suppliers.search_analytics import track_booking_confirm
        await track_booking_confirm(db, org_id, used_supplier, payload.get("product_type", "hotel"), confirmed_price, fallback_used)

        return {
            "status": "confirmed",
            "internal_booking_id": internal_booking_id,
            "supplier_code": used_supplier,
            "supplier_booking_id": result.supplier_booking_id,
            "confirmation_code": result.confirmation_code,
            "booked_price": expected_price,
            "confirmed_price": confirmed_price,
            "currency": payload.get("currency", "TRY"),
            "fallback_used": fallback_used,
            "original_supplier": supplier_code if fallback_used else None,
            "duration_ms": duration_ms,
        }
    else:
        booking_audit.inc("booking_failure_total")
        await booking_audit.log_booking_event(db, "booking_failed", org_id, supplier_code, internal_booking_id, {
            "attempted_suppliers": [supplier_code] + (failover_engine.get_fallback_chain(supplier_code) if not result else []),
        })
        return {
            "status": "failed",
            "internal_booking_id": internal_booking_id,
            "error": "All suppliers failed to confirm booking",
            "duration_ms": duration_ms,
        }


# ---------------------------------------------------------------------------
# 4. Reconciliation
# ---------------------------------------------------------------------------

@router.get("/reconciliation/{booking_id}")
async def get_reconciliation(
    booking_id: str,
    current_user=Depends(require_roles(["admin", "super_admin", "agency_admin"])),
    db=Depends(get_db),
) -> dict[str, Any]:
    from app.suppliers.booking_reconciliation import check_reconciliation
    return await check_reconciliation(db, booking_id)


@router.get("/reconciliation-mismatches")
async def get_mismatches(
    current_user=Depends(require_roles(["admin", "super_admin", "agency_admin"])),
    db=Depends(get_db),
) -> dict[str, Any]:
    from app.suppliers.booking_reconciliation import get_mismatched_bookings, get_reconciliation_summary
    mismatches = await get_mismatched_bookings(db)
    summary = await get_reconciliation_summary(db)
    return {"mismatches": mismatches, "summary": summary}


# ---------------------------------------------------------------------------
# 5. Audit
# ---------------------------------------------------------------------------

@router.get("/audit/{booking_id}")
async def get_booking_audit(
    booking_id: str,
    current_user=Depends(require_roles(["admin", "super_admin", "agency_admin"])),
    db=Depends(get_db),
) -> dict[str, Any]:
    from app.suppliers.booking_audit import get_audit_trail
    trail = await get_audit_trail(db, booking_id=booking_id)
    return {"booking_id": booking_id, "events": trail}


@router.get("/audit")
async def get_org_audit(
    current_user=Depends(require_roles(["admin", "super_admin", "agency_admin"])),
    db=Depends(get_db),
) -> dict[str, Any]:
    from app.suppliers.booking_audit import get_audit_trail
    org_id = current_user.get("organization_id", current_user.get("org_id", ""))
    trail = await get_audit_trail(db, organization_id=org_id, limit=200)
    return {"organization_id": org_id, "events": trail}


# ---------------------------------------------------------------------------
# 6. Registry & Capabilities
# ---------------------------------------------------------------------------

@router.get("/registry")
async def get_registry_info(
    current_user=Depends(require_roles(["admin", "super_admin"])),
) -> dict[str, Any]:
    from app.suppliers.registry import supplier_registry
    all_adapters = supplier_registry.get_all()
    real = [a for a in all_adapters if not a.supplier_code.startswith("mock_")]
    mock = [a for a in all_adapters if a.supplier_code.startswith("mock_")]
    return {
        "total_registered": len(all_adapters),
        "real_adapters": [a.get_info() for a in real],
        "mock_adapters": [a.get_info() for a in mock],
        "capabilities": supplier_registry.get_capabilities(),
        "fallback_chains": _get_fallback_chains(),
    }


def _get_fallback_chains() -> dict:
    from app.suppliers.failover import failover_engine
    chains = {}
    for code in ["ratehawk", "tbo", "paximum", "wwtatil"]:
        chains[code] = failover_engine.get_fallback_chain(code)
    return chains


# ---------------------------------------------------------------------------
# 7. Metrics
# ---------------------------------------------------------------------------

@router.get("/metrics")
async def get_booking_metrics(
    current_user=Depends(require_roles(["admin", "super_admin", "agency_admin"])),
) -> dict[str, Any]:
    from app.suppliers.booking_audit import get_metrics
    return get_metrics()
