"""Cache warm-up strategy — Pre-load frequently accessed data into Redis on startup.

Runs during application lifespan startup to ensure the most commonly
accessed endpoints have warm caches from the first request.

Configuration:
  CACHE_WARMUP_ENABLED = true|false  (default: true)

Strategy:
  1. Load all active tenants/orgs
  2. For each tenant, pre-cache:
     - Tenant features (5 min TTL)
     - CMS navigation pages (10 min TTL)
     - Active campaigns (5 min TTL)
  3. Pre-cache global data:
     - System health baseline
"""
from __future__ import annotations

import logging
import os
from typing import Any

from app.db import get_db
from app.services.redis_cache import redis_set

logger = logging.getLogger("cache_warmup")


def _is_enabled() -> bool:
    return os.environ.get("CACHE_WARMUP_ENABLED", "true").lower() in ("1", "true", "yes", "on")


async def run_cache_warmup() -> dict[str, Any]:
    """Execute cache warm-up. Returns summary stats."""
    if not _is_enabled():
        logger.info("Cache warm-up disabled via CACHE_WARMUP_ENABLED=false")
        return {"status": "disabled"}

    logger.info("Starting cache warm-up...")
    stats = {"tenants": 0, "features": 0, "cms_nav": 0, "campaigns": 0, "errors": 0}

    try:
        db = await get_db()

        # 1. Discover active tenants
        tenant_cursor = db.tenants.find(
            {"status": {"$in": ["active", "trial", None]}},
            {"_id": 1, "tenant_key": 1, "organization_id": 1},
        ).limit(100)
        tenants = await tenant_cursor.to_list(length=100)
        stats["tenants"] = len(tenants)
        logger.info("Warm-up: found %d active tenants", len(tenants))

        for tenant in tenants:
            tenant_id = str(tenant.get("_id", ""))
            org_id = tenant.get("organization_id") or tenant_id

            # 2a. Tenant features
            try:
                from app.services.feature_service import feature_service
                features, source = await feature_service.get_effective_features(tenant_id)
                plan = await feature_service.get_plan(tenant_id)
                add_ons = await feature_service.get_add_ons(tenant_id)
                cache_data = {
                    "tenant_id": tenant_id,
                    "plan": plan,
                    "add_ons": add_ons,
                    "features": features,
                    "source": source,
                }
                await redis_set(f"tenant_feat:{tenant_id}", cache_data, ttl_seconds=300)
                stats["features"] += 1
            except Exception as e:
                logger.debug("Warm-up features error for tenant %s: %s", tenant_id, e)
                stats["errors"] += 1

            # 2b. CMS navigation pages
            try:
                cursor = db.cms_pages.find(
                    {"organization_id": org_id, "published": True},
                    {"_id": 1, "slug": 1, "title": 1},
                ).sort("created_at", -1)
                docs = await cursor.to_list(length=200)
                items = [
                    {"id": str(d.get("_id")), "slug": d.get("slug", ""), "title": d.get("title", "")}
                    for d in docs
                ]
                await redis_set(f"cms_nav:{org_id}", {"items": items}, ttl_seconds=600)
                stats["cms_nav"] += 1
            except Exception as e:
                logger.debug("Warm-up CMS nav error for org %s: %s", org_id, e)
                stats["errors"] += 1

            # 2c. Active campaigns
            try:
                cursor = db.campaigns.find(
                    {"organization_id": org_id, "active": True},
                ).sort("created_at", -1).limit(20)
                docs = await cursor.to_list(length=20)
                items = [
                    {
                        "id": str(d.get("_id")),
                        "slug": d.get("slug", ""),
                        "name": d.get("name", ""),
                        "description": d.get("description", ""),
                        "channels": d.get("channels", []),
                    }
                    for d in docs
                ]
                await redis_set(f"pub_camps_list:{org_id}", {"items": items}, ttl_seconds=300)
                stats["campaigns"] += 1
            except Exception as e:
                logger.debug("Warm-up campaigns error for org %s: %s", org_id, e)
                stats["errors"] += 1

            # 2d. Active agencies list (admin dropdowns, B2B portal)
            try:
                cursor = db.agencies.find(
                    {"organization_id": org_id, "$or": [{"active": True}, {"is_active": True}]},
                    {"_id": 1, "name": 1, "contact_email": 1},
                ).sort("name", 1).limit(200)
                docs = await cursor.to_list(length=200)
                items = [
                    {"id": str(d.get("_id")), "name": d.get("name", ""), "contact_email": d.get("contact_email", "")}
                    for d in docs
                ]
                await redis_set(f"agencies_active:{org_id}", {"items": items}, ttl_seconds=300)
                stats["agencies"] = stats.get("agencies", 0) + 1
            except Exception as e:
                logger.debug("Warm-up agencies error for org %s: %s", org_id, e)
                stats["errors"] += 1

            # 2e. Hotels list (used across admin, agency portals)
            try:
                cursor = db.hotels.find(
                    {"organization_id": org_id, "active": {"$ne": False}},
                    {"_id": 1, "name": 1, "city": 1, "country": 1},
                ).sort("name", 1).limit(500)
                docs = await cursor.to_list(length=500)
                items = [
                    {"id": str(d.get("_id")), "name": d.get("name", ""), "city": d.get("city", ""), "country": d.get("country", "")}
                    for d in docs
                ]
                await redis_set(f"hotels_active:{org_id}", {"items": items}, ttl_seconds=300)
                stats["hotels"] = stats.get("hotels", 0) + 1
            except Exception as e:
                logger.debug("Warm-up hotels error for org %s: %s", org_id, e)
                stats["errors"] += 1

            # 2f. FX rates (critical for pricing)
            try:
                cursor = db.fx_rates.find(
                    {"organization_id": org_id},
                    {"_id": 0, "base": 1, "quote": 1, "rate": 1, "as_of": 1},
                ).limit(50)
                docs = await cursor.to_list(length=50)
                items = [
                    {"base": d.get("base"), "quote": d.get("quote"), "rate": d.get("rate"), "as_of": str(d.get("as_of", ""))}
                    for d in docs
                ]
                await redis_set(f"fx_rates:{org_id}", {"items": items}, ttl_seconds=600)
                stats["fx_rates"] = stats.get("fx_rates", 0) + 1
            except Exception as e:
                logger.debug("Warm-up FX rates error for org %s: %s", org_id, e)
                stats["errors"] += 1

            # 2g. Active pricing rules (frequently accessed)
            try:
                cursor = db.pricing_rules.find(
                    {"organization_id": org_id, "status": "active"},
                    {"_id": 1, "priority": 1, "scope": 1, "action": 1, "validity": 1},
                ).sort("priority", -1).limit(100)
                docs = await cursor.to_list(length=100)
                items = [
                    {
                        "id": str(d.get("_id")),
                        "priority": d.get("priority"),
                        "scope": d.get("scope", {}),
                        "action": d.get("action", {}),
                        "validity": d.get("validity", {}),
                    }
                    for d in docs
                ]
                await redis_set(f"pricing_rules_active:{org_id}", {"items": items}, ttl_seconds=300)
                stats["pricing_rules"] = stats.get("pricing_rules", 0) + 1
            except Exception as e:
                logger.debug("Warm-up pricing rules error for org %s: %s", org_id, e)
                stats["errors"] += 1

            # 2h. Product counts by type (dashboard widgets)
            try:
                pipeline = [
                    {"$match": {"organization_id": org_id}},
                    {"$group": {"_id": "$type", "count": {"$sum": 1}}},
                ]
                agg = await db.products.aggregate(pipeline).to_list(length=20)
                product_counts = {r["_id"]: r["count"] for r in agg if r.get("_id")}
                total = sum(product_counts.values())
                await redis_set(f"product_counts:{org_id}", {"total": total, "by_type": product_counts}, ttl_seconds=300)
                stats["product_counts"] = stats.get("product_counts", 0) + 1
            except Exception as e:
                logger.debug("Warm-up product counts error for org %s: %s", org_id, e)
                stats["errors"] += 1

            # 2i. Reservation summary (dashboard stats)
            try:
                pipeline = [
                    {"$match": {"organization_id": org_id}},
                    {"$group": {"_id": "$status", "count": {"$sum": 1}}},
                ]
                agg = await db.reservations.aggregate(pipeline).to_list(length=20)
                res_summary = {r["_id"]: r["count"] for r in agg if r.get("_id")}
                total = sum(res_summary.values())
                await redis_set(f"reservation_summary:{org_id}", {"total": total, "by_status": res_summary}, ttl_seconds=300)
                stats["reservation_summary"] = stats.get("reservation_summary", 0) + 1
            except Exception as e:
                logger.debug("Warm-up reservation summary error for org %s: %s", org_id, e)
                stats["errors"] += 1

            # 2j. Agency module settings (for dynamic sidebar)
            try:
                cursor = db.agencies.find(
                    {"organization_id": org_id},
                    {"_id": 1, "name": 1, "allowed_modules": 1},
                ).limit(200)
                docs = await cursor.to_list(length=200)
                items = [
                    {"id": str(d.get("_id")), "name": d.get("name", ""), "allowed_modules": d.get("allowed_modules", [])}
                    for d in docs
                ]
                await redis_set(f"agency_modules:{org_id}", {"items": items}, ttl_seconds=300)
                stats["agency_modules"] = stats.get("agency_modules", 0) + 1
            except Exception as e:
                logger.debug("Warm-up agency modules error for org %s: %s", org_id, e)
                stats["errors"] += 1

            # 2k. Onboarding state (first-load redirect)
            try:
                onboarding = await db.activation_checklist.find_one({"tenant_id": tenant_id})
                if onboarding:
                    await redis_set(f"onboarding:{tenant_id}", {
                        "completed": bool(onboarding.get("completed_at") or onboarding.get("completed")),
                    }, ttl_seconds=600)
                stats["onboarding"] = stats.get("onboarding", 0) + 1
            except Exception as e:
                logger.debug("Warm-up onboarding error for tenant %s: %s", tenant_id, e)
                stats["errors"] += 1

        logger.info(
            "Cache warm-up complete: %d tenants, %d features, %d cms_nav, %d campaigns, "
            "%d agencies, %d hotels, %d fx_rates, %d pricing_rules, "
            "%d product_counts, %d reservation_summary, %d agency_modules, %d onboarding, %d errors",
            stats["tenants"], stats["features"], stats["cms_nav"],
            stats["campaigns"], stats.get("agencies", 0), stats.get("hotels", 0),
            stats.get("fx_rates", 0), stats.get("pricing_rules", 0),
            stats.get("product_counts", 0), stats.get("reservation_summary", 0),
            stats.get("agency_modules", 0), stats.get("onboarding", 0),
            stats["errors"],
        )
        stats["status"] = "completed"

    except Exception as e:
        logger.error("Cache warm-up failed: %s", e)
        stats["status"] = "error"
        stats["error_message"] = str(e)

    return stats
