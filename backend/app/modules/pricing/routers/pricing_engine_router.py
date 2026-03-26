"""Pricing & Distribution Engine API Router.

Endpoints:
  - POST /api/pricing-engine/simulate        - Price simulation
  - GET  /api/pricing-engine/dashboard       - Dashboard stats
  - CRUD /api/pricing-engine/distribution-rules
  - CRUD /api/pricing-engine/channels
  - CRUD /api/pricing-engine/promotions
  - CRUD /api/pricing-engine/guardrails
"""
from __future__ import annotations

import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.auth import get_current_user
from app.db import get_db
from app.utils import now_utc, serialize_doc
from app.services.activity_timeline_service import record_event
from app.services.config_versioning_service import stamp_create, stamp_update, stamp_delete
from app.services.pricing_distribution_engine import (
    PricingDistributionEngine,
    PricingContext,
    get_pricing_engine_stats,
    pricing_cache,
    warm_cache_for_supplier,
    CHANNELS,
    SEASONS,
)
from app.services.promotion_engine import (
    create_promotion,
    list_promotions,
    delete_promotion,
    toggle_promotion,
    PROMO_TYPES,
)

router = APIRouter(prefix="/api/pricing-engine", tags=["pricing_engine"])


# --- Schemas ---

class SimulateRequest(BaseModel):
    supplier_code: str = "ratehawk"
    supplier_price: float = 100.0
    supplier_currency: str = "EUR"
    destination: str = ""
    channel: str = "b2c"
    agency_id: str = ""
    agency_tier: str = "standard"
    season: str = "mid"
    product_type: str = "hotel"
    nights: int = 1
    sell_currency: str = "EUR"
    promo_code: str = ""


class DistributionRuleCreate(BaseModel):
    name: str
    rule_category: str  # base_markup, agency_tier, commission, tax
    value: float = 0.0
    scope: dict = Field(default_factory=dict)
    priority: int = 0
    active: bool = True
    change_reason: str = ""


class DistributionRuleUpdate(BaseModel):
    name: Optional[str] = None
    value: Optional[float] = None
    scope: Optional[dict] = None
    priority: Optional[int] = None
    active: Optional[bool] = None
    change_reason: str = ""


class ChannelConfigCreate(BaseModel):
    channel: str
    label: str = ""
    adjustment_pct: float = 0.0
    agency_tier: str = ""
    commission_pct: float = 0.0
    active: bool = True
    change_reason: str = ""


class ChannelConfigUpdate(BaseModel):
    label: Optional[str] = None
    adjustment_pct: Optional[float] = None
    agency_tier: Optional[str] = None
    commission_pct: Optional[float] = None
    active: Optional[bool] = None
    change_reason: str = ""


class PromotionCreate(BaseModel):
    name: str
    promo_type: str = "campaign_discount"
    discount_pct: float = 0.0
    fixed_price: Optional[float] = None
    promo_code: str = ""
    scope: dict = Field(default_factory=dict)
    valid_from: Optional[str] = None
    valid_to: Optional[str] = None
    min_days_before: int = 0
    max_uses: int = 0
    change_reason: str = ""


class PromotionUpdate(BaseModel):
    name: Optional[str] = None
    discount_pct: Optional[float] = None
    fixed_price: Optional[float] = None
    promo_code: Optional[str] = None
    scope: Optional[dict] = None
    valid_from: Optional[str] = None
    valid_to: Optional[str] = None
    min_days_before: Optional[int] = None
    max_uses: Optional[int] = None
    active: Optional[bool] = None
    change_reason: str = ""


class GuardrailCreate(BaseModel):
    name: str
    guardrail_type: str  # min_margin_pct, max_discount_pct, channel_floor_price, supplier_max_markup_pct
    value: float = 0.0
    scope: dict = Field(default_factory=dict)
    active: bool = True
    change_reason: str = ""


class GuardrailUpdate(BaseModel):
    name: Optional[str] = None
    guardrail_type: Optional[str] = None
    value: Optional[float] = None
    scope: Optional[dict] = None
    active: Optional[bool] = None
    change_reason: str = ""


# --- Dashboard ---

@router.get("/dashboard")
async def pricing_dashboard(user=Depends(get_current_user)):
    org_id = user["organization_id"]
    stats = await get_pricing_engine_stats(org_id)
    return stats


@router.get("/metadata")
async def pricing_metadata(user=Depends(get_current_user)):
    """Return available channels, seasons, promotion types."""
    return {
        "channels": list(CHANNELS),
        "seasons": list(SEASONS),
        "promotion_types": list(PROMO_TYPES),
        "rule_categories": ["base_markup", "agency_tier", "commission", "tax"],
        "agency_tiers": ["starter", "standard", "premium", "enterprise"],
        "guardrail_types": ["min_margin_pct", "max_discount_pct", "channel_floor_price", "supplier_max_markup_pct"],
    }


# --- Price Simulation ---

@router.post("/simulate")
async def simulate_price(payload: SimulateRequest, user=Depends(get_current_user)):
    org_id = user["organization_id"]
    db = await get_db()
    engine = PricingDistributionEngine(db)

    ctx = PricingContext(
        supplier_code=payload.supplier_code,
        supplier_price=payload.supplier_price,
        supplier_currency=payload.supplier_currency,
        destination=payload.destination,
        channel=payload.channel,
        agency_id=payload.agency_id,
        agency_tier=payload.agency_tier,
        season=payload.season,
        product_type=payload.product_type,
        nights=payload.nights,
        sell_currency=payload.sell_currency,
        promo_code=payload.promo_code,
        organization_id=org_id,
    )

    result = await engine.calculate(ctx)
    # Cache hit returns dict directly, fresh calc returns PricingBreakdown
    if isinstance(result, dict):
        return result
    return result.to_dict()


# --- Distribution Rules CRUD ---

@router.get("/distribution-rules")
async def list_distribution_rules(
    category: Optional[str] = Query(None),
    active_only: bool = Query(False),
    user=Depends(get_current_user),
):
    db = await get_db()
    org_id = user["organization_id"]
    query: dict[str, Any] = {"organization_id": org_id}
    if category:
        query["rule_category"] = category
    if active_only:
        query["active"] = True

    docs = await db.distribution_rules.find(query, {"_id": 0}).sort("priority", -1).to_list(500)
    return [serialize_doc(d) for d in docs]


@router.post("/distribution-rules", status_code=201)
async def create_distribution_rule(payload: DistributionRuleCreate, user=Depends(get_current_user)):
    db = await get_db()
    org_id = user["organization_id"]
    actor = user.get("email", "system")
    now = now_utc()
    rule_id = f"rule_{uuid.uuid4().hex[:8]}"

    doc = {
        "rule_id": rule_id,
        "organization_id": org_id,
        "name": payload.name,
        "rule_category": payload.rule_category,
        "value": payload.value,
        "scope": payload.scope,
        "priority": payload.priority,
        "active": payload.active,
        "created_at": now,
        "updated_at": now,
    }
    await stamp_create(doc, actor)
    await db.distribution_rules.insert_one(doc)
    result = serialize_doc(doc)
    await record_event(
        actor=actor, action="created", entity_type="distribution_rule",
        entity_id=rule_id, org_id=org_id, after=result,
        metadata={"rule_category": payload.rule_category, "change_reason": payload.change_reason},
    )
    return result


@router.patch("/distribution-rules/{rule_id}")
async def update_distribution_rule(rule_id: str, payload: DistributionRuleUpdate, user=Depends(get_current_user)):
    org_id = user["organization_id"]
    actor = user.get("email", "system")
    updates = {k: v for k, v in payload.dict(exclude_unset=True).items() if v is not None and k != "change_reason"}

    result = await stamp_update(
        entity_type="distribution_rule", entity_id=rule_id, org_id=org_id,
        updates=updates, actor=actor, change_reason=payload.change_reason,
    )
    if isinstance(result, dict) and result.get("error"):
        return result
    await record_event(
        actor=actor, action="updated", entity_type="distribution_rule",
        entity_id=rule_id, org_id=org_id, after=result,
        metadata={"change_reason": payload.change_reason},
    )
    return serialize_doc(result)


@router.delete("/distribution-rules/{rule_id}")
async def delete_distribution_rule(rule_id: str, user=Depends(get_current_user)):
    db = await get_db()
    org_id = user["organization_id"]
    actor = user.get("email", "system")
    await stamp_delete("distribution_rule", rule_id, org_id, actor)
    result = await db.distribution_rules.delete_one({"organization_id": org_id, "rule_id": rule_id})
    if result.deleted_count > 0:
        await record_event(
            actor=actor, action="deleted", entity_type="distribution_rule",
            entity_id=rule_id, org_id=org_id,
        )
    return {"ok": result.deleted_count > 0}


# --- Channel Configs CRUD ---

@router.get("/channels")
async def list_channels(user=Depends(get_current_user)):
    db = await get_db()
    org_id = user["organization_id"]
    docs = await db.channel_configs.find({"organization_id": org_id}, {"_id": 0}).to_list(50)
    return [serialize_doc(d) for d in docs]


@router.post("/channels", status_code=201)
async def create_channel(payload: ChannelConfigCreate, user=Depends(get_current_user)):
    db = await get_db()
    org_id = user["organization_id"]
    actor = user.get("email", "system")
    now = now_utc()
    rule_id = f"ch_{uuid.uuid4().hex[:8]}"

    doc = {
        "rule_id": rule_id,
        "organization_id": org_id,
        "channel": payload.channel,
        "label": payload.label or payload.channel.upper(),
        "adjustment_pct": payload.adjustment_pct,
        "agency_tier": payload.agency_tier,
        "commission_pct": payload.commission_pct,
        "active": payload.active,
        "created_at": now,
        "updated_at": now,
    }
    await stamp_create(doc, actor)
    await db.channel_configs.insert_one(doc)
    result = serialize_doc(doc)
    await record_event(
        actor=actor, action="created", entity_type="channel_config",
        entity_id=rule_id, org_id=org_id, after=result,
        metadata={"channel": payload.channel, "change_reason": payload.change_reason},
    )
    return result


@router.patch("/channels/{rule_id}")
async def update_channel(rule_id: str, payload: ChannelConfigUpdate, user=Depends(get_current_user)):
    org_id = user["organization_id"]
    actor = user.get("email", "system")
    updates = {k: v for k, v in payload.dict(exclude_unset=True).items() if v is not None and k != "change_reason"}

    result = await stamp_update(
        entity_type="channel_config", entity_id=rule_id, org_id=org_id,
        updates=updates, actor=actor, change_reason=payload.change_reason,
    )
    if isinstance(result, dict) and result.get("error"):
        return result
    await record_event(
        actor=actor, action="updated", entity_type="channel_config",
        entity_id=rule_id, org_id=org_id, after=result,
        metadata={"change_reason": payload.change_reason},
    )
    return serialize_doc(result)


@router.delete("/channels/{rule_id}")
async def delete_channel(rule_id: str, user=Depends(get_current_user)):
    db = await get_db()
    org_id = user["organization_id"]
    actor = user.get("email", "system")
    await stamp_delete("channel_config", rule_id, org_id, actor)
    result = await db.channel_configs.delete_one({"organization_id": org_id, "rule_id": rule_id})
    if result.deleted_count > 0:
        await record_event(
            actor=actor, action="deleted", entity_type="channel_config",
            entity_id=rule_id, org_id=org_id,
        )
    return {"ok": result.deleted_count > 0}


# --- Promotions CRUD ---

@router.get("/promotions")
async def list_promotions_endpoint(
    active_only: bool = Query(False),
    promo_type: Optional[str] = Query(None),
    user=Depends(get_current_user),
):
    org_id = user["organization_id"]
    return await list_promotions(org_id, active_only=active_only, promo_type=promo_type)


@router.post("/promotions", status_code=201)
async def create_promotion_endpoint(payload: PromotionCreate, user=Depends(get_current_user)):
    org_id = user["organization_id"]
    actor = user.get("email", "")
    result = await create_promotion(
        organization_id=org_id,
        name=payload.name,
        promo_type=payload.promo_type,
        discount_pct=payload.discount_pct,
        fixed_price=payload.fixed_price,
        promo_code=payload.promo_code,
        scope=payload.scope,
        valid_from=payload.valid_from,
        valid_to=payload.valid_to,
        min_days_before=payload.min_days_before,
        max_uses=payload.max_uses,
        created_by=actor,
    )
    await record_event(
        actor=actor, action="created", entity_type="promotion",
        entity_id=result.get("rule_id", ""), org_id=org_id, after=result,
        metadata={"promo_type": payload.promo_type, "change_reason": payload.change_reason},
    )
    return result


@router.patch("/promotions/{rule_id}")
async def update_promotion_endpoint(rule_id: str, payload: PromotionUpdate, user=Depends(get_current_user)):
    org_id = user["organization_id"]
    actor = user.get("email", "system")
    updates = {k: v for k, v in payload.dict(exclude_unset=True).items() if v is not None and k != "change_reason"}

    result = await stamp_update(
        entity_type="promotion", entity_id=rule_id, org_id=org_id,
        updates=updates, actor=actor, change_reason=payload.change_reason,
    )
    if isinstance(result, dict) and result.get("error"):
        return result
    await record_event(
        actor=actor, action="updated", entity_type="promotion",
        entity_id=rule_id, org_id=org_id, after=result,
        metadata={"change_reason": payload.change_reason},
    )
    return result


@router.delete("/promotions/{rule_id}")
async def delete_promotion_endpoint(rule_id: str, user=Depends(get_current_user)):
    org_id = user["organization_id"]
    actor = user.get("email", "system")
    await stamp_delete("promotion", rule_id, org_id, actor)
    ok = await delete_promotion(org_id, rule_id)
    if ok:
        await record_event(
            actor=actor, action="deleted", entity_type="promotion",
            entity_id=rule_id, org_id=org_id,
        )
    return {"ok": ok}


@router.post("/promotions/{rule_id}/toggle")
async def toggle_promotion_endpoint(rule_id: str, active: bool = Query(True), user=Depends(get_current_user)):
    org_id = user["organization_id"]
    actor = user.get("email", "system")
    result = await toggle_promotion(org_id, rule_id, active)
    if not result:
        return {"error": "Promotion not found"}
    await record_event(
        actor=actor, action="updated", entity_type="promotion",
        entity_id=rule_id, org_id=org_id,
        metadata={"toggle_active": active},
    )
    return result


# --- Guardrails CRUD ---

@router.get("/guardrails")
async def list_guardrails(user=Depends(get_current_user)):
    db = await get_db()
    org_id = user["organization_id"]
    docs = await db.pricing_guardrails.find({"organization_id": org_id}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return [serialize_doc(d) for d in docs]


@router.post("/guardrails", status_code=201)
async def create_guardrail(payload: GuardrailCreate, user=Depends(get_current_user)):
    db = await get_db()
    org_id = user["organization_id"]
    actor = user.get("email", "system")
    now = now_utc()
    guardrail_id = f"guard_{uuid.uuid4().hex[:8]}"

    doc = {
        "guardrail_id": guardrail_id,
        "organization_id": org_id,
        "name": payload.name,
        "guardrail_type": payload.guardrail_type,
        "value": payload.value,
        "scope": payload.scope,
        "active": payload.active,
        "created_at": now,
        "updated_at": now,
    }
    await stamp_create(doc, actor)
    await db.pricing_guardrails.insert_one(doc)
    result = serialize_doc(doc)
    await record_event(
        actor=actor, action="created", entity_type="guardrail",
        entity_id=guardrail_id, org_id=org_id, after=result,
        metadata={"guardrail_type": payload.guardrail_type, "change_reason": payload.change_reason},
    )
    return result


@router.patch("/guardrails/{guardrail_id}")
async def update_guardrail(guardrail_id: str, payload: GuardrailUpdate, user=Depends(get_current_user)):
    org_id = user["organization_id"]
    actor = user.get("email", "system")
    updates = {k: v for k, v in payload.dict(exclude_unset=True).items() if v is not None and k != "change_reason"}

    result = await stamp_update(
        entity_type="guardrail", entity_id=guardrail_id, org_id=org_id,
        updates=updates, actor=actor, change_reason=payload.change_reason,
    )
    if isinstance(result, dict) and result.get("error"):
        return result
    await record_event(
        actor=actor, action="updated", entity_type="guardrail",
        entity_id=guardrail_id, org_id=org_id, after=result,
        metadata={"change_reason": payload.change_reason},
    )
    return serialize_doc(result)


@router.delete("/guardrails/{guardrail_id}")
async def delete_guardrail(guardrail_id: str, user=Depends(get_current_user)):
    db = await get_db()
    org_id = user["organization_id"]
    actor = user.get("email", "system")
    await stamp_delete("guardrail", guardrail_id, org_id, actor)
    result = await db.pricing_guardrails.delete_one({"organization_id": org_id, "guardrail_id": guardrail_id})
    if result.deleted_count > 0:
        await record_event(
            actor=actor, action="deleted", entity_type="guardrail",
            entity_id=guardrail_id, org_id=org_id,
        )
    return {"ok": result.deleted_count > 0}


# --- Cache Management ---

@router.get("/cache/stats")
async def cache_stats(user=Depends(get_current_user)):
    return pricing_cache.stats()


@router.get("/cache/telemetry")
async def cache_telemetry(user=Depends(get_current_user)):
    """Extended cache telemetry: per-supplier metrics, latencies, invalidation log."""
    return pricing_cache.telemetry()


@router.post("/cache/clear")
async def cache_clear(user=Depends(get_current_user)):
    pricing_cache.clear()
    return {"ok": True, "message": "Pricing cache temizlendi"}


@router.post("/cache/invalidate/{supplier_code}")
async def cache_invalidate_supplier(supplier_code: str, user=Depends(get_current_user)):
    """Invalidate all pricing cache entries for a specific supplier."""
    cleared = pricing_cache.invalidate_by_supplier(supplier_code)
    return {"ok": True, "supplier": supplier_code, "cleared": cleared}


# --- Cache Alerts ---

@router.get("/cache/alerts")
async def cache_alerts(user=Depends(get_current_user)):
    """Get cache performance alerts (active + history)."""
    return {
        "active_alerts": pricing_cache.get_active_alerts(),
        "alert_history": pricing_cache.get_alerts(20),
        "threshold_pct": pricing_cache.HIT_RATE_ALERT_THRESHOLD,
        "min_requests": pricing_cache.MIN_REQUESTS_FOR_ALERT,
    }


@router.post("/cache/alerts/clear")
async def clear_cache_alerts(user=Depends(get_current_user)):
    """Clear all cache alert history."""
    pricing_cache.clear_alerts()
    return {"ok": True, "message": "Alert gecmisi temizlendi"}


# --- Cache Warming ---

@router.post("/cache/warm/{supplier_code}")
async def warm_cache(supplier_code: str, limit: int = Query(10, ge=1, le=50), user=Depends(get_current_user)):
    """Precompute pricing for popular routes of a supplier."""
    result = await warm_cache_for_supplier(supplier_code, limit=limit)
    return result


@router.get("/cache/popular-routes")
async def get_popular_routes(
    supplier_code: str = Query(""),
    limit: int = Query(10, ge=1, le=50),
    user=Depends(get_current_user),
):
    """Get most frequently queried pricing routes."""
    routes = pricing_cache.get_popular_routes(supplier_code=supplier_code, limit=limit)
    return {"routes": routes, "total_tracked": len(pricing_cache._query_frequency)}


# --- Global Diagnostics ---

@router.get("/cache/diagnostics")
async def cache_diagnostics(user=Depends(get_current_user)):
    """Comprehensive cache diagnostics for scaling decisions."""
    stats = pricing_cache.stats()
    telemetry_data = pricing_cache.telemetry()
    return {
        "global_hit_rate": stats["hit_rate_pct"],
        "total_entries": stats["total_entries"],
        "active_entries": stats["active_entries"],
        "memory_usage_mb": stats["memory_usage_mb"],
        "memory_usage_bytes": stats["memory_usage_bytes"],
        "evictions": stats["evictions"],
        "max_size": stats["max_size"],
        "utilization_pct": round(stats["total_entries"] / max(stats["max_size"], 1) * 100, 1),
        "ttl_seconds": stats["ttl_seconds"],
        "total_requests": telemetry_data["total_requests"],
        "hits": stats["hits"],
        "misses": stats["misses"],
        "avg_hit_latency_ms": telemetry_data["avg_hit_latency_ms"],
        "avg_miss_latency_ms": telemetry_data["avg_miss_latency_ms"],
        "uptime_seconds": telemetry_data["uptime_seconds"],
        "active_alerts": telemetry_data["active_alerts"],
        "warming_status": telemetry_data["warming_status"],
        "supplier_count": len(telemetry_data["supplier_breakdown"]),
    }
