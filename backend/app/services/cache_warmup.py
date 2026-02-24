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

        logger.info(
            "Cache warm-up complete: %d tenants, %d features, %d cms_nav, %d campaigns, %d errors",
            stats["tenants"], stats["features"], stats["cms_nav"],
            stats["campaigns"], stats["errors"],
        )
        stats["status"] = "completed"

    except Exception as e:
        logger.error("Cache warm-up failed: %s", e)
        stats["status"] = "error"
        stats["error_message"] = str(e)

    return stats
