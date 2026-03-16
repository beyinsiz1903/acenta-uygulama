"""Centralized cache invalidation for all domain write operations.

Each function invalidates both Redis L1 and MongoDB L2 caches
for a specific domain. Called from write endpoints (POST/PUT/PATCH/DELETE).

Usage:
    from app.services.cache_invalidation import invalidate_products
    await invalidate_products(org_id)
"""
from __future__ import annotations

import logging

from app.services.redis_cache import redis_invalidate_pattern
from app.services.mongo_cache_service import cache_invalidate_pattern as mongo_invalidate
from app.services import cache_metrics as cm

logger = logging.getLogger("cache_invalidation")


async def _inv_app_cache(prefix: str) -> int:
    """Also clear the B3 app_cache collection (cache_service.py stores there)."""
    try:
        from app.db import get_db
        db = await get_db()
        result = await db.app_cache.delete_many({"key": {"$regex": f"^{prefix}"}})
        return result.deleted_count
    except Exception:
        return 0


async def _inv(prefix: str, scope: str = "") -> int:
    """Invalidate both Redis + MongoDB for a prefix. Returns total cleared."""
    try:
        r_count = await redis_invalidate_pattern(prefix, scope)
        m_count = await mongo_invalidate(f"{prefix}")
        a_count = await _inv_app_cache(prefix)
        total = r_count + m_count + a_count
        if total > 0:
            logger.debug("Invalidated %s:%s -> %d keys", prefix, scope, total)
            cm.invalidation_ok(f"{prefix}:{scope}", total)
        return total
    except Exception as e:
        logger.warning("Invalidation error %s:%s -> %s", prefix, scope, e)
        cm.invalidation_fail(f"{prefix}:{scope}", str(e))
        return 0


# ─── Domain-Specific Invalidation ─────────────────────────────

async def invalidate_products(org_id: str) -> None:
    """Invalidate product list + related public search caches."""
    await _inv("products", org_id)
    await _inv("pub_search", org_id)
    await _inv("dash_popular", org_id)


async def invalidate_hotels(org_id: str) -> None:
    """Invalidate hotel list + search caches."""
    await _inv("hotel_list", org_id)
    await _inv("search", org_id)
    await _inv("b2b_htl_srch", org_id)
    await _inv("agency_hotels", org_id)


async def invalidate_tours(org_id: str) -> None:
    """Invalidate tour list + detail + public caches."""
    await _inv("pub_tours", org_id)
    await _inv("tour_detail", org_id)
    await _inv("pub_search", org_id)


async def invalidate_crm_customers(org_id: str) -> None:
    """Invalidate CRM customer list cache."""
    await _inv("crm_cust", org_id)


async def invalidate_crm_deals(org_id: str) -> None:
    """Invalidate CRM deals list cache."""
    await _inv("crm_deals", org_id)


async def invalidate_pricing_rules(org_id: str) -> None:
    """Invalidate pricing rules + related search caches."""
    await _inv("pricing_rules", org_id)
    await _inv("pub_search", org_id)
    await _inv("b2b_htl_srch", org_id)


async def invalidate_cms_pages(org_id: str) -> None:
    """Invalidate CMS page + navigation caches."""
    await _inv("cms_page", org_id)
    await _inv("cms_nav", org_id)


async def invalidate_campaigns(org_id: str) -> None:
    """Invalidate campaign caches."""
    await _inv("pub_camp", org_id)
    await _inv("pub_camps_list", org_id)


async def invalidate_tenant_features(tenant_id: str) -> None:
    """Invalidate tenant features + quota caches."""
    await _inv("tenant_feat", tenant_id)
    await _inv("tenant_quota", tenant_id)
    await _inv("tenant_usage_summary", tenant_id)
    await _inv(f"tenant_feat:{tenant_id}")
    await _inv(f"tenant_quota:{tenant_id}")
    await _inv(f"tenant_usage_summary:{tenant_id}")


async def invalidate_b2b_announcements(org_id: str) -> None:
    """Invalidate B2B announcement caches."""
    await _inv("b2b_ann", org_id)


async def invalidate_b2b_listings(tenant_id: str) -> None:
    """Invalidate B2B exchange listing caches."""
    await _inv("b2b_my_list", tenant_id)


async def invalidate_b2b_bookings(org_id: str, agency_id: str = "") -> None:
    """Invalidate B2B booking list cache."""
    await _inv("b2b_bkgs", org_id)


async def invalidate_dashboard(org_id: str) -> None:
    """Invalidate all dashboard caches."""
    await _inv("dash_kpi", org_id)
    await _inv("dash_weekly", org_id)
    await _inv("dash_popular", org_id)


async def invalidate_storefront(tenant_id: str) -> None:
    """Invalidate storefront health/branding cache."""
    await _inv("sf_health", tenant_id)


async def invalidate_all_for_org(org_id: str) -> None:
    """Nuclear option: invalidate ALL caches for an organization."""
    await invalidate_products(org_id)
    await invalidate_hotels(org_id)
    await invalidate_tours(org_id)
    await invalidate_crm_customers(org_id)
    await invalidate_crm_deals(org_id)
    await invalidate_pricing_rules(org_id)
    await invalidate_cms_pages(org_id)
    await invalidate_campaigns(org_id)
    await invalidate_dashboard(org_id)
    await invalidate_b2b_announcements(org_id)
    logger.info("Full cache invalidation for org %s", org_id)



# ─── Supplier Sync Invalidation ───────────────────────────────

async def invalidate_supplier_sync(supplier: str, org_id: str = "") -> int:
    """Invalidate all cached inventory for a supplier after sync completes.

    Called after supplier sync job finishes to ensure stale
    inventory/prices are purged. Also clears pricing engine cache.
    """
    total = 0
    total += await _inv(f"inv:{supplier}")
    total += await _inv(f"inv_city:{supplier}")
    total += await _inv(f"supplier_cache:{org_id}:{supplier}" if org_id else "supplier_cache")
    total += await _inv("search", org_id)
    total += await _inv("b2b_htl_srch", org_id)
    total += await _inv("pricing_rules", org_id)

    # Invalidate pricing engine in-memory cache for this supplier
    try:
        from app.services.pricing_distribution_engine import pricing_cache
        pricing_cleared = pricing_cache.invalidate_by_supplier(supplier)
        total += pricing_cleared
        logger.info("Post-sync pricing cache invalidation for %s: %d entries cleared", supplier, pricing_cleared)
    except Exception as e:
        logger.warning("Failed to invalidate pricing cache for %s: %s", supplier, e)

    logger.info("Post-sync invalidation for %s: %d keys cleared", supplier, total)
    return total


async def invalidate_booking_lifecycle(org_id: str, booking_id: str = "") -> int:
    """Invalidate caches affected by booking creation, update, or cancellation.

    Ensures:
    - Availability caches refreshed
    - Dashboard stats updated
    - Booking status not stale
    """
    total = 0
    total += await _inv("booking_status", org_id)
    total += await _inv("availability", org_id)
    total += await _inv("dash_kpi", org_id)
    total += await _inv("dash_weekly", org_id)
    total += await _inv("reservation_summary", org_id)
    total += await _inv("b2b_bkgs", org_id)
    if booking_id:
        total += await _inv(f"booking:{booking_id}")
    logger.info("Post-booking invalidation for org=%s booking=%s: %d keys", org_id, booking_id, total)
    return total


async def invalidate_price_change(org_id: str, supplier: str = "") -> int:
    """Invalidate caches when price data changes.

    Ensures stale rates are never served after a price update.
    """
    total = 0
    total += await _inv("search", org_id)
    total += await _inv("price_revalidation", org_id)
    total += await _inv("b2b_htl_srch", org_id)
    if supplier:
        total += await _inv(f"supplier_cache:{org_id}:{supplier}")
        # Invalidate pricing engine in-memory cache for this supplier
        try:
            from app.services.pricing_distribution_engine import pricing_cache
            pricing_cleared = pricing_cache.invalidate_by_supplier(supplier)
            total += pricing_cleared
        except Exception as e:
            logger.warning("Failed to invalidate pricing cache for %s: %s", supplier, e)
    logger.info("Price change invalidation for org=%s supplier=%s: %d keys", org_id, supplier, total)
    return total
