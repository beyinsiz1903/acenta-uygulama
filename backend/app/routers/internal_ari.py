from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from bson import ObjectId

from app.auth import get_current_user, require_roles, require_hotel_capability
from app.db import get_db
from app.services.channels.ari_apply import apply_ari_to_pms
from app.routers.channels import AriApplyOut
from app.services.internal_ari_simulator import build_internal_canonical_ari

router = APIRouter(prefix="/api/internal-ari", tags=["internal-ari"])


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_hotel_context(user: dict[str, Any]) -> tuple[str, str]:
    org_id = user.get("organization_id")
    hotel_id = user.get("hotel_id")
    if not org_id or not hotel_id:
        raise HTTPException(status_code=403, detail="NOT_LINKED_TO_HOTEL")
    return str(org_id), str(hotel_id)


class DateRule(BaseModel):
    type: str = Field("date_range", pattern="^(weekend|weekday|date_range)$")
    from_date: Optional[str] = Field(default=None, description="YYYY-MM-DD")
    to_date: Optional[str] = Field(default=None, description="YYYY-MM-DD")


class RateRule(BaseModel):
    type: str = Field("percent", pattern="^(percent|absolute)$")
    value: float = 0.0


class AvailabilityRule(BaseModel):
    type: str = Field("delta", pattern="^(set|delta)$")
    value: int = 0


class InternalAriRuleIn(BaseModel):
    scope: str = Field("both", pattern="^(rates|availability|both)$")
    name: str = Field(..., max_length=120)
    active: bool = True

    date_rule: DateRule = Field(default_factory=DateRule)
    rate_rule: Optional[RateRule] = None
    availability_rule: Optional[AvailabilityRule] = None
    stop_sell: Optional[bool] = None


class InternalAriRuleOut(InternalAriRuleIn):
    id: str
    created_at: datetime
    updated_at: datetime


async def _serialize_rule(doc: dict[str, Any]) -> InternalAriRuleOut:
    return InternalAriRuleOut(
        id=str(doc.get("_id")),
        scope=doc.get("scope") or "both",
        name=doc.get("name") or "Internal ARI Rule",
        active=bool(doc.get("active", True)),
        date_rule=DateRule(**(doc.get("date_rule") or {})),
        rate_rule=(RateRule(**doc["rate_rule"]) if doc.get("rate_rule") else None),
        availability_rule=(
            AvailabilityRule(**doc["availability_rule"]) if doc.get("availability_rule") else None
        ),
        stop_sell=doc.get("stop_sell"),
        created_at=doc.get("created_at"),
        updated_at=doc.get("updated_at"),
    )


@router.get(
    "/rules",
    response_model=dict,
    dependencies=[
        Depends(require_roles(["hotel_admin", "hotel_staff"])),
        Depends(require_hotel_capability("channel_hub")),
    ],
)
async def list_internal_ari_rules(user=Depends(get_current_user)) -> dict[str, Any]:
    """List internal ARI rules for current hotel."""

    db = await get_db()
    org_id, hotel_id = _normalize_hotel_context(user)

    cursor = db.internal_ari_rules.find(
        {
            "organization_id": org_id,
            "hotel_id": hotel_id,
        }
    ).sort("created_at", 1)

    items: list[InternalAriRuleOut] = []
    async for doc in cursor:
        items.append(await _serialize_rule(doc))

    return {"items": [item.model_dump() for item in items]}


@router.post(
    "/rules",
    response_model=InternalAriRuleOut,
    dependencies=[
        Depends(require_roles(["hotel_admin"])),
        Depends(require_hotel_capability("channel_hub")),
    ],
)
async def create_internal_ari_rule(
    payload: InternalAriRuleIn,
    user=Depends(get_current_user),
) -> InternalAriRuleOut:
    db = await get_db()
    org_id, hotel_id = _normalize_hotel_context(user)
    now = _utc_now()

    doc: dict[str, Any] = {
        "organization_id": org_id,
        "hotel_id": hotel_id,
        "scope": payload.scope,
        "name": payload.name,
        "active": payload.active,
        "date_rule": payload.date_rule.model_dump(),
        "rate_rule": payload.rate_rule.model_dump() if payload.rate_rule else None,
        "availability_rule": (
            payload.availability_rule.model_dump() if payload.availability_rule else None
        ),
        "stop_sell": payload.stop_sell,
        "created_at": now,
        "updated_at": now,
    }

    ins = await db.internal_ari_rules.insert_one(doc)
    doc["_id"] = ins.inserted_id
    return await _serialize_rule(doc)


@router.put(
    "/rules/{rule_id}",
    response_model=InternalAriRuleOut,
    dependencies=[
        Depends(require_roles(["hotel_admin"])),
        Depends(require_hotel_capability("channel_hub")),
    ],
)
async def update_internal_ari_rule(
    rule_id: str,
    payload: InternalAriRuleIn,
    user=Depends(get_current_user),
) -> InternalAriRuleOut:
    db = await get_db()
    org_id, hotel_id = _normalize_hotel_context(user)

    existing = await db.internal_ari_rules.find_one(
        {
            "_id": ObjectId(rule_id),
            "organization_id": org_id,
            "hotel_id": hotel_id,
        }
    )
    if not existing:
        raise HTTPException(status_code=404, detail="RULE_NOT_FOUND")

    now = _utc_now()
    update_doc: dict[str, Any] = {
        "scope": payload.scope,
        "name": payload.name,
        "active": payload.active,
        "date_rule": payload.date_rule.model_dump(),
        "rate_rule": payload.rate_rule.model_dump() if payload.rate_rule else None,
        "availability_rule": (
            payload.availability_rule.model_dump() if payload.availability_rule else None
        ),
        "stop_sell": payload.stop_sell,
        "updated_at": now,
    }

    await db.internal_ari_rules.update_one(
        {
            "_id": ObjectId(rule_id),
            "organization_id": org_id,
            "hotel_id": hotel_id,
        },
        {"$set": update_doc},
    )

    updated = {**existing, **update_doc}
    return await _serialize_rule(updated)


@router.delete(
    "/rules/{rule_id}",
    response_model=dict,
    dependencies=[
        Depends(require_roles(["hotel_admin"])),
        Depends(require_hotel_capability("channel_hub")),
    ],
)
async def delete_internal_ari_rule(
    rule_id: str,
    user=Depends(get_current_user),
) -> dict[str, Any]:
    """Soft delete: active=False.

    Gerçek silme yerine active=false yapmak, geçmiş ARI apply run'ları ile
    tutarlılığı korur.
    """

    db = await get_db()
    org_id, hotel_id = _normalize_hotel_context(user)

    res = await db.internal_ari_rules.update_one(
        {
            "_id": ObjectId(rule_id),
            "organization_id": org_id,
            "hotel_id": hotel_id,
        },
        {"$set": {"active": False, "updated_at": _utc_now()}},
    )

    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="RULE_NOT_FOUND")

    return {"ok": True}



class InternalAriSimulateIn(BaseModel):
    from_date: date
    to_date: date


@router.post(
    "/simulate",
    response_model=AriApplyOut,
    dependencies=[
        Depends(require_roles(["hotel_admin", "hotel_staff"])),
        Depends(require_hotel_capability("channel_hub")),
    ],
)
async def simulate_internal_ari(
    payload: InternalAriSimulateIn,
    dry_run: int = Query(1, ge=0, le=1),
    user=Depends(get_current_user),
) -> AriApplyOut:
    """Run internal ARI simulation for the current hotel.

    Bu endpoint, dahili ARI kurallarını ve PMS snapshot'larını kullanarak
    canonical ARI üretir ve mevcut apply_ari_to_pms pipeline'ı ile
    (dry_run veya write) uygular.
    """

    db = await get_db()
    org_id, hotel_id = _normalize_hotel_context(user)

    canonical, sim_stats = await build_internal_canonical_ari(
        org_id=org_id,
        hotel_id=hotel_id,
        from_date=payload.from_date,
        to_date=payload.to_date,
    )

    idem_key = (
        f"internal_ari:{hotel_id}:"
        f"{payload.from_date.isoformat()}:{payload.to_date.isoformat()}:"
        f"dry={dry_run}"
    )

    apply_result = await apply_ari_to_pms(
        db=db,
        canonical=canonical,
        org_id=org_id,
        hotel_id=hotel_id,
        connector_id="internal_ari",
        mode="rates_and_availability",
        dry_run=bool(dry_run),
        idempotency_key=idem_key,
    )

    status = apply_result.get("status") or "failed"
    summary = apply_result.get("summary") or {}
    diff = apply_result.get("diff") or {}

    # Internal simulator istatistiklerini summary'ye ekle
    summary.update(
        {
            "internal_rule_count": sim_stats.get("rule_count", 0),
            "internal_parsed_rate_days": sim_stats.get("parsed_rate_days", 0),
            "internal_parsed_availability_days": sim_stats.get("parsed_availability_days", 0),
        }
    )

    # channel_sync_runs içine ayrı bir run kaydı yaz
    now = _utc_now()
    run_doc: dict[str, Any] = {
        "organization_id": org_id,
        "hotel_id": hotel_id,
        "connector_id": "internal_ari",
        "type": "ari_apply",
        "status": status,
        "started_at": now,
        "finished_at": now,
        "duration_ms": 0,
        "summary": summary,
        "diff": diff,
        "error": None if status in ("success", "partial") else {"code": "INTERNAL_ARI_FAILED"},
        "meta": {
            "invoked_by": "internal_simulator",
            "rule_count": sim_stats.get("rule_count", 0),
            "dry_run": bool(dry_run),
        },
        "idempotency_key": idem_key,
    }

    ins = await db.channel_sync_runs.insert_one(run_doc)
    run_id = str(ins.inserted_id)

    ok = status in ("success", "partial")
    return AriApplyOut(
        ok=ok,
        status=status,
        run_id=run_id,
        summary=summary,
        diff=diff,
        error=None if ok else {"code": "INTERNAL_ARI_FAILED"},
    )
