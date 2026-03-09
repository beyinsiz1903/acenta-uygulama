from __future__ import annotations

from datetime import datetime, timezone
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


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def _money(value: Any) -> float:
    amount = round(_safe_float(value, default=0.0), 2)
    return 0.0 if abs(amount) < 0.005 else amount


def _booking_month(doc: dict[str, Any]) -> str | None:
    stay = doc.get("stay") or {}
    check_in = stay.get("check_in") or doc.get("check_in_date") or doc.get("check_in") or doc.get("start_date")
    if not check_in:
        return None
    return str(check_in)[:7]


def _booking_status(doc: dict[str, Any]) -> str:
    status = str(doc.get("status") or doc.get("state") or "draft").strip().lower()
    if status == "booked":
        return "confirmed"
    if status == "canceled":
        return "cancelled"
    if status == "paid":
        return "completed"
    return status or "draft"


def _sort_created_at(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.timestamp()
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return 0.0
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
        except Exception:
            return 0.0
    return 0.0


def _derive_booking_financial_entry(
    doc: dict[str, Any],
    *,
    month: str,
    hotel_name_map: dict[str, str],
    agency_link_map: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    status = _booking_status(doc)
    if status in {"draft", "quoted", "pending"}:
        return None

    hotel_id = str(doc.get("hotel_id") or "")
    if not hotel_id:
        return None

    rate_snapshot = doc.get("rate_snapshot") or {}
    price = rate_snapshot.get("price") or {}

    gross_amount = (
        _safe_float(doc.get("gross_amount"), default=0.0)
        or _safe_float(price.get("total"), default=0.0)
        or _safe_float(doc.get("amount"), default=0.0)
        or _safe_float((doc.get("amounts") or {}).get("sell"), default=0.0)
        or _safe_float(doc.get("total_price"), default=0.0)
    )
    commission_amount = _safe_float(doc.get("commission_amount"), default=0.0)
    if commission_amount == 0.0 and gross_amount > 0:
        link = agency_link_map.get(hotel_id) or {}
        commission_type = str(link.get("commission_type") or "percent").strip().lower()
        commission_value = _safe_float(link.get("commission_value"), default=0.0)
        if commission_type == "percent":
            commission_amount = round(gross_amount * commission_value / 100.0, 2)
        elif commission_type in {"fixed", "fixed_per_booking"}:
            commission_amount = round(commission_value, 2)

    net_amount = _safe_float(doc.get("net_amount"), default=round(gross_amount - commission_amount, 2))

    if status == "cancelled":
        gross_amount = -abs(gross_amount)
        commission_amount = -abs(commission_amount)
        net_amount = -abs(net_amount)

    settlement_status = "settled" if status in {"completed", "paid", "settled", "closed"} else "open"
    created_at = doc.get("confirmed_at") or doc.get("submitted_at") or doc.get("created_at") or datetime.now(timezone.utc)

    return {
        "_id": f"derived:{doc.get('_id')}",
        "booking_id": str(doc.get("_id") or ""),
        "organization_id": doc.get("organization_id"),
        "agency_id": str(doc.get("agency_id") or ""),
        "hotel_id": hotel_id,
        "hotel_name": doc.get("hotel_name") or hotel_name_map.get(hotel_id) or "-",
        "type": "reversal" if status == "cancelled" else "booking",
        "month": month,
        "currency": doc.get("currency") or price.get("currency") or "TRY",
        "gross_amount": _money(gross_amount),
        "commission_amount": _money(commission_amount),
        "net_amount": _money(net_amount),
        "source_status": status,
        "settlement_status": settlement_status,
        "created_at": created_at,
        "updated_at": created_at,
        "derived_from_booking": True,
    }


async def _load_agency_settlement_entries(
    db,
    *,
    user: dict[str, Any],
    month: str,
    status: Optional[str],
    hotel_id: Optional[str],
) -> list[dict[str, Any]]:
    q = _settlement_query_base(user, month, status)
    q["agency_id"] = user["agency_id"]
    if hotel_id:
        q["hotel_id"] = hotel_id

    entries = await db.booking_financial_entries.find(q).sort("created_at", -1).to_list(5000)
    booking_ids_with_entries = {str(entry.get("booking_id")) for entry in entries if entry.get("booking_id")}

    booking_query: dict[str, Any] = {
        "organization_id": user["organization_id"],
        "agency_id": user["agency_id"],
    }
    if hotel_id:
        booking_query["hotel_id"] = hotel_id

    bookings = await db.bookings.find(booking_query).sort("created_at", -1).to_list(5000)

    hotel_ids = list(
        {
            str(item.get("hotel_id"))
            for item in [*entries, *bookings]
            if item.get("hotel_id")
        }
    )
    hotel_map: dict[str, str] = {}
    if hotel_ids:
        hotels = await db.hotels.find(
            {"organization_id": user["organization_id"], "_id": {"$in": hotel_ids}},
            {"_id": 1, "name": 1},
        ).to_list(len(hotel_ids))
        hotel_map = {str(hotel.get("_id")): hotel.get("name") or "-" for hotel in hotels}

    links = await db.agency_hotel_links.find(
        {"organization_id": user["organization_id"], "agency_id": user["agency_id"], "active": True}
    ).to_list(2000)
    agency_link_map = {str(link.get("hotel_id")): link for link in links if link.get("hotel_id")}

    derived_entries: list[dict[str, Any]] = []
    for booking in bookings:
        booking_id_value = str(booking.get("_id") or "")
        if not booking_id_value or booking_id_value in booking_ids_with_entries:
            continue
        if _booking_month(booking) != month:
            continue

        derived_entry = _derive_booking_financial_entry(
            booking,
            month=month,
            hotel_name_map=hotel_map,
            agency_link_map=agency_link_map,
        )
        if not derived_entry:
            continue
        if status and derived_entry.get("settlement_status") != status:
            continue
        derived_entries.append(derived_entry)

    combined = [*entries, *derived_entries]
    combined.sort(key=lambda item: _sort_created_at(item.get("created_at")), reverse=True)

    enriched_entries: list[dict[str, Any]] = []
    for entry in combined:
        enriched = dict(entry)
        hid = str(enriched.get("hotel_id") or "")
        if hid and not enriched.get("hotel_name"):
            enriched["hotel_name"] = hotel_map.get(hid) or "-"
        enriched_entries.append(enriched)
    return enriched_entries


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
    entries = await _load_agency_settlement_entries(
        db,
        user=user,
        month=month,
        status=status,
        hotel_id=hotel_id,
    )

    totals: dict[str, dict[str, Any]] = {}
    for e in entries:
        hid = str(e.get("hotel_id") or "")
        if not hid:
            continue
        row = totals.setdefault(
            hid,
            {
                "hotel_id": hid,
                "hotel_name": e.get("hotel_name") or "-",
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

from fastapi import Query as _StatementQuery

from app.errors import AppError
from app.services.settlement_statement_service import SettlementStatementService

# Safety cap for statement size (Phase 2.1-B)
MAX_ITEMS = 500


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
        except Exception:
            raise AppError(
                status_code=400,
                code="invalid_cursor",
                message="Invalid cursor.",
                details=None,
            )

    # Fetch items with cursor + counterparty filter
    items = await svc.fetch_items(
        ctx.tenant_id or "",
        perspective,
        month_start,
        month_end,
        statuses or None,
        counterparty_tenant_id,
        # Always fetch up to MAX_ITEMS + 1 to evaluate guard & cursor independently of per-page limit
        MAX_ITEMS,
        cursor_dict,
    )

    # Guardrail: too many items in a single statement
    if len(items) > MAX_ITEMS:
        raise AppError(
            status_code=400,
            code="statement_too_large",
            message="Statement has too many items.",
            details={"max_items": MAX_ITEMS},
        )

    # Compute totals on the current result set
    per_curr, overall = svc.compute_totals(items)

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

    # Counterparty aggregation based on full (un-sliced) result set for this page
    counterparties = svc.compute_counterparties(items, perspective)

    # Cursor-based pagination: encode next_cursor from the (limit+1)th item, if present
    next_cursor = None
    if len(items) > limit:
        from base64 import b64encode
        import json

        last = items[limit - 1]
        payload = {
            "created_at": last.get("created_at"),
            "booking_id": last.get("booking_id"),
        }
        next_cursor = b64encode(json.dumps(payload, default=str).encode("utf-8")).decode("utf-8")

    # Response items for this page
    response_items: list[dict[str, _Any]] = []
    for it in items[:limit]:
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
        "page": {"limit": limit, "next_cursor": next_cursor},
    }
