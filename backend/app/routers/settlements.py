from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Response

from app.auth import get_current_user, require_roles
from app.db import get_db
from app.utils import serialize_doc, to_csv

hotel_router = APIRouter(prefix="/api/hotel", tags=["hotel-settlements"])
agency_router = APIRouter(prefix="/api/agency", tags=["agency-settlements"])


def _validate_month(month: str) -> str:
    # Expected YYYY-MM
    if not month or len(month) != 7 or month[4] != "-":
        raise HTTPException(status_code=422, detail="INVALID_MONTH")
    yyyy, mm = month.split("-")
    if not (yyyy.isdigit() and mm.isdigit()):
        raise HTTPException(status_code=422, detail="INVALID_MONTH")
    if not (1 <= int(mm) <= 12):
        raise HTTPException(status_code=422, detail="INVALID_MONTH")
    return month


def _settlement_query_base(user: dict[str, Any], month: str, status: Optional[str]) -> dict[str, Any]:
    q: dict[str, Any] = {
        "organization_id": user["organization_id"],
        "month": month,
    }
    if status:
        if status not in {"open", "settled"}:
            raise HTTPException(status_code=422, detail="INVALID_STATUS")
        q["settlement_status"] = status
    return q


@hotel_router.get(
    "/settlements",
    dependencies=[Depends(require_roles(["hotel_admin", "hotel_staff"]))],
)
async def hotel_settlements(
    month: str,
    status: Optional[str] = None,
    agency_id: Optional[str] = None,
    export: Optional[str] = None,
    user=Depends(get_current_user),
):
    db = await get_db()
    if not user.get("hotel_id"):
        raise HTTPException(status_code=403, detail="NOT_LINKED_TO_HOTEL")

    month = _validate_month(month)
    q = _settlement_query_base(user, month, status)
    q["hotel_id"] = user["hotel_id"]
    if agency_id:
        q["agency_id"] = agency_id

    entries = await db.booking_financial_entries.find(q).sort("created_at", -1).to_list(5000)

    # totals by agency
    agency_ids = list({e.get("agency_id") for e in entries if e.get("agency_id")})
    agency_map: dict[str, str] = {}
    if agency_ids:
        agencies = await db.agencies.find({"organization_id": user["organization_id"], "_id": {"$in": agency_ids}}).to_list(200)
        agency_map = {str(a["_id"]): a.get("name") or "-" for a in agencies}

    totals: dict[str, dict[str, Any]] = {}
    for e in entries:
        aid = str(e.get("agency_id") or "")
        if not aid:
            continue
        row = totals.setdefault(
            aid,
            {
                "agency_id": aid,
                "agency_name": agency_map.get(aid, "-"),
                "currency": e.get("currency") or "TRY",
                "gross_total": 0.0,
                "commission_total": 0.0,
                "net_total": 0.0,
                "count": 0,
            },
        )
        row["gross_total"] = round(float(row["gross_total"]) + float(e.get("gross_amount") or 0), 2)
        row["commission_total"] = round(float(row["commission_total"]) + float(e.get("commission_amount") or 0), 2)
        row["net_total"] = round(float(row["net_total"]) + float(e.get("net_amount") or 0), 2)
        row["count"] += 1

    totals_list = sorted(totals.values(), key=lambda r: r["net_total"], reverse=True)

    if export == "csv":
        csv_str = to_csv(
            totals_list,
            [
                "agency_id",
                "agency_name",
                "currency",
                "gross_total",
                "commission_total",
                "net_total",
                "count",
            ],
        )
        return Response(content=csv_str, media_type="text/csv")

    return {
        "month": month,
        "status": status or "all",
        "hotel_id": str(user["hotel_id"]),
        "totals": totals_list,
        "entries": [serialize_doc(e) for e in entries[:200]],
    }


@agency_router.get(
    "/settlements",
    dependencies=[Depends(require_roles(["agency_admin", "agency_agent"]))],
)
async def agency_settlements(
    month: str,
    status: Optional[str] = None,
    hotel_id: Optional[str] = None,
    export: Optional[str] = None,
    user=Depends(get_current_user),
):
    db = await get_db()
    if not user.get("agency_id"):
        raise HTTPException(status_code=403, detail="NOT_LINKED_TO_AGENCY")

    month = _validate_month(month)
    q = _settlement_query_base(user, month, status)
    q["agency_id"] = user["agency_id"]
    if hotel_id:
        q["hotel_id"] = hotel_id

    entries = await db.booking_financial_entries.find(q).sort("created_at", -1).to_list(5000)

    # totals by hotel
    hotel_ids = list({e.get("hotel_id") for e in entries if e.get("hotel_id")})
    hotel_map: dict[str, str] = {}
    if hotel_ids:
        hotels = await db.hotels.find({"organization_id": user["organization_id"], "_id": {"$in": hotel_ids}}).to_list(200)
        hotel_map = {str(h["_id"]): h.get("name") or "-" for h in hotels}

    totals: dict[str, dict[str, Any]] = {}
    for e in entries:
        hid = str(e.get("hotel_id") or "")
        if not hid:
            continue
        row = totals.setdefault(
            hid,
            {
                "hotel_id": hid,
                "hotel_name": hotel_map.get(hid, "-"),
                "currency": e.get("currency") or "TRY",
                "gross_total": 0.0,
                "commission_total": 0.0,
                "net_total": 0.0,
                "count": 0,
            },
        )
        row["gross_total"] = round(float(row["gross_total"]) + float(e.get("gross_amount") or 0), 2)
        row["commission_total"] = round(float(row["commission_total"]) + float(e.get("commission_amount") or 0), 2)
        row["net_total"] = round(float(row["net_total"]) + float(e.get("net_amount") or 0), 2)
        row["count"] += 1

    totals_list = sorted(totals.values(), key=lambda r: r["gross_total"], reverse=True)

    if export == "csv":
        csv_str = to_csv(
            totals_list,
            [
                "hotel_id",
                "hotel_name",
                "currency",
                "gross_total",
                "commission_total",
                "net_total",
                "count",
            ],
        )
        return Response(content=csv_str, media_type="text/csv")

    return {
        "month": month,
        "status": status or "all",
        "agency_id": str(user["agency_id"]),
        "totals": totals_list,
        "entries": [serialize_doc(e) for e in entries[:200]],
    }



# Phase 2.0.1: B2B Network Settlements listing over settlement_ledger
from typing import Dict as _Dict, Any as _Any, Optional as _Opt

from fastapi import Depends as _Depends, APIRouter as _APIRouter, Query as _Query

from app.auth import get_current_user as _get_current_user
from app.db import get_db as _get_db
from app.request_context import get_request_context as _get_request_context, RequestContext as _RequestContext, require_permission as _require_permission
from app.services.settlement_service import SettlementService as _SettlementService

network_settlements_router = _APIRouter(prefix="/api/settlements", tags=["network-settlements"])


@network_settlements_router.get("")
async def list_network_settlements(  # type: ignore[no-untyped-def]
    perspective: str = _Query("seller", pattern="^(seller|buyer)$"),
    status: _Opt[str] = _Query(None),
    user: _Dict[str, _Any] = _Depends(_get_current_user),
):
    ctx: _RequestContext = _get_request_context(required=True)  # type: ignore[assignment]

    # RBAC
    @_require_permission("settlements.view")
    async def _noop() -> None:  # type: ignore[no-untyped-def]
        return None

    await _noop()

    db = await _get_db()
    service = _SettlementService(db)

    items = await service.list_settlements(ctx.tenant_id or "", perspective)
    if status:
        items = [s for s in items if s.get("status") == status]

    return {"items": items}



# Phase 2.1-B: Monthly settlement statement over settlement_ledger
from datetime import datetime

from fastapi import Query as _StatementQuery

from app.errors import AppError
from app.services.settlement_statement_service import SettlementStatementService


@network_settlements_router.get("/statement")
async def get_settlement_statement(  # type: ignore[no-untyped-def]
    month: str = _StatementQuery(...),
    perspective: str = _StatementQuery("seller"),
    status: _Opt[str] = _StatementQuery(None),
    counterparty_tenant_id: _Opt[str] = _StatementQuery(None),
    limit: int = _StatementQuery(100, ge=1, le=200),
    cursor: _Opt[str] = _StatementQuery(None),
    user: _Dict[str, _Any] = _Depends(_get_current_user),
):
    ctx: _RequestContext = _get_request_context(required=True)  # type: ignore[assignment]

    # RBAC
    @_require_permission("settlements.view")
    async def _guard() -> None:  # type: ignore[no-untyped-def]
        return None

    await _guard()

    # Validate perspective
    if perspective not in {"seller", "buyer"}:
        raise AppError(
            status_code=400,
            code="invalid_perspective",
            message="perspective must be 'seller' or 'buyer'",
            details={"perspective": perspective},
        )

    # Validate month format YYYY-MM
    try:
        parts = month.split("-")
        if len(parts) != 2:
            raise ValueError
        year = int(parts[0])
        mon = int(parts[1])
        if not (1 <= mon <= 12):
            raise ValueError
    except Exception:
        raise AppError(
            status_code=400,
            code="invalid_month",
            message="Invalid month format, expected YYYY-MM",
            details={"month": month},
        )

    from calendar import monthrange
    from datetime import timezone as _tz

    month_start = datetime(year, mon, 1, 0, 0, 0, tzinfo=_tz.utc)
    if mon == 12:
        month_end = datetime(year + 1, 1, 1, 0, 0, 0, tzinfo=_tz.utc)
    else:
        month_end = datetime(year, mon + 1, 1, 0, 0, 0, tzinfo=_tz.utc)

    statuses: _Opt[list[str]] = None
    if status:
        parts = [s.strip() for s in status.split(",") if s.strip()]
        allowed = {"open", "approved", "paid", "void"}
        if any(s not in allowed for s in parts):
            raise AppError(
                status_code=400,
                code="invalid_status",
                message="Invalid status filter",
                details={"allowed": sorted(allowed)},
            )
        statuses = parts

    if counterparty_tenant_id and counterparty_tenant_id == ctx.tenant_id:
        raise AppError(
            status_code=400,
            code="invalid_counterparty",
            message="counterparty_tenant_id cannot be the same as tenant_id",
            details={"tenant_id": ctx.tenant_id},
        )

    db = await _get_db()
    svc = SettlementStatementService(db)

    # Decode cursor if provided
    cursor_dict = None
    if cursor:
        import json
        from base64 import b64decode

        try:
            raw = b64decode(cursor).decode("utf-8")
            cursor_dict = json.loads(raw)
            # created_at is ISO string stored as-is in DB, we use it directly in comparison
        except Exception:
            raise AppError(
                status_code=400,
                code="invalid_cursor",
                message="Invalid cursor.",
                details=None,
            )

    items = await svc.fetch_items(
        ctx.tenant_id or "",
        perspective,
        month_start,
        month_end,
        statuses or None,
        counterparty_tenant_id,
        limit,
        cursor_dict,
    )

    per_curr, overall = svc.compute_totals(items[:limit])

    currency_breakdown = [
        {
            "currency": cur,
            "gross_total": totals.gross_total,
            "commission_total": totals.commission_total,
            "net_total": totals.net_total,
            "count": totals.count,
        }
        for cur, totals in per_curr.items()
    ]

    # Sort currency list for stability
    currency_breakdown.sort(key=lambda x: x["currency"])

    counterparties = svc.compute_counterparties(items, perspective)

    # Slice items to MAX_ITEMS; ensure consistent shape
    response_items: list[dict[str, _Any]] = []
    for it in items[:MAX_ITEMS]:
        response_items.append(
            {
                "settlement_id": it["settlement_id"],
                "booking_id": it.get("booking_id"),
                "seller_tenant_id": it.get("seller_tenant_id"),
                "buyer_tenant_id": it.get("buyer_tenant_id"),
                "relationship_id": it.get("relationship_id"),
                "commission_rule_id": it.get("commission_rule_id"),
                "gross_amount": it.get("gross_amount"),
                "commission_amount": it.get("commission_amount"),
                "net_amount": it.get("net_amount"),
                "currency": it.get("currency"),
                "status": it.get("status"),
                "created_at": it.get("created_at").isoformat() if it.get("created_at") else None,
            }
        )

    return {
        "tenant_id": ctx.tenant_id,
        "perspective": perspective,
        "month": month,
        "currency_breakdown": currency_breakdown,
        "totals": {
            "count": overall.count,
            "gross_total": overall.gross_total,
            "commission_total": overall.commission_total,
            "net_total": overall.net_total,
        },
        "counterparties": counterparties,
        "items": response_items,
    }
