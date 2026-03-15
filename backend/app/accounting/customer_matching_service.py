"""Customer Matching Service for Accounting Sync.

Manages customer (cari hesap) matching between Syroce and accounting providers.
Matching order: VKN -> TCKN -> email -> phone -> manual selection.

DB Collection: accounting_customers

Key rule: same tenant + same VKN cannot create duplicate cari.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

from app.db import get_db
from app.utils import now_utc, serialize_doc

logger = logging.getLogger("accounting.customer_matching")

COL = "accounting_customers"

MATCH_VKN = "vkn"
MATCH_TCKN = "tckn"
MATCH_EMAIL = "email"
MATCH_PHONE = "phone"
MATCH_MANUAL = "manual"

MATCH_ORDER = [MATCH_VKN, MATCH_TCKN, MATCH_EMAIL, MATCH_PHONE]

# Match confidence scores per CTO directive
MATCH_CONFIDENCE = {
    MATCH_VKN: 1.0,
    MATCH_TCKN: 0.95,
    MATCH_EMAIL: 0.8,
    MATCH_PHONE: 0.6,
    MATCH_MANUAL: 1.0,
    "auto": 0.7,
}


async def _try_cache_get(tenant_id: str, vkn: str) -> dict | None:
    """Try to get customer from Redis cache. Returns None if unavailable."""
    try:
        from app.infrastructure.redis_client import get_async_redis
        r = await get_async_redis()
        if r:
            import json
            key = f"customer_match:{tenant_id}:{vkn}"
            cached = await r.get(key)
            if cached:
                return json.loads(cached)
    except Exception:
        pass
    return None


async def _try_cache_set(tenant_id: str, vkn: str, data: dict) -> None:
    """Try to cache customer match result. Silent on failure."""
    try:
        from app.infrastructure.redis_client import get_async_redis
        r = await get_async_redis()
        if r:
            import json
            key = f"customer_match:{tenant_id}:{vkn}"
            await r.setex(key, 3600, json.dumps(data, default=str))
    except Exception:
        pass


async def match_customer(
    tenant_id: str,
    provider: str,
    customer_data: dict[str, Any],
) -> dict[str, Any] | None:
    """Try to match a customer in accounting_customers using the match order.

    Returns the matched customer doc or None.
    """
    db = await get_db()
    vkn = customer_data.get("tax_id") or customer_data.get("vkn") or ""
    tckn = customer_data.get("id_number") or customer_data.get("tckn") or ""
    email = customer_data.get("email") or ""
    phone = customer_data.get("phone") or ""

    # Try Redis cache first (VKN-based)
    if vkn:
        cached = await _try_cache_get(tenant_id, vkn)
        if cached:
            return cached

    base_q = {"tenant_id": tenant_id, "provider": provider}

    # Match order: VKN -> TCKN -> email -> phone
    match_attempts = [
        (MATCH_VKN, "vkn", vkn),
        (MATCH_TCKN, "tckn", tckn),
        (MATCH_EMAIL, "email", email),
        (MATCH_PHONE, "phone", phone),
    ]

    for method, field, value in match_attempts:
        if not value:
            continue
        doc = await db[COL].find_one({**base_q, field: value})
        if doc:
            result = serialize_doc(doc)
            result["match_method"] = method
            result["match_confidence"] = MATCH_CONFIDENCE.get(method, 0.5)
            if vkn:
                await _try_cache_set(tenant_id, vkn, result)
            return result

    return None


async def create_customer(
    tenant_id: str,
    provider: str,
    customer_data: dict[str, Any],
    match_method: str = "auto",
    external_customer_id: str = "",
) -> dict[str, Any]:
    """Create a new accounting customer. Enforces VKN uniqueness per tenant."""
    db = await get_db()

    vkn = customer_data.get("tax_id") or customer_data.get("vkn") or ""
    tckn = customer_data.get("id_number") or customer_data.get("tckn") or ""

    # Enforce VKN uniqueness per tenant
    if vkn:
        existing = await db[COL].find_one({
            "tenant_id": tenant_id,
            "provider": provider,
            "vkn": vkn,
        })
        if existing:
            return {
                "error": "duplicate_vkn",
                "message": f"Bu VKN ({vkn}) ile zaten bir cari hesap mevcut",
                "existing": serialize_doc(existing),
            }

    now = now_utc()
    customer_id = f"CUST-{uuid.uuid4().hex[:8].upper()}"

    doc = {
        "customer_id": customer_id,
        "tenant_id": tenant_id,
        "provider": provider,
        "external_customer_id": external_customer_id,
        "name": customer_data.get("name", ""),
        "vkn": vkn,
        "tckn": tckn,
        "email": customer_data.get("email", ""),
        "phone": customer_data.get("phone", ""),
        "tax_office": customer_data.get("tax_office", ""),
        "address": customer_data.get("address", ""),
        "city": customer_data.get("city", ""),
        "country": customer_data.get("country", "TR"),
        "match_method": match_method,
        "match_confidence": MATCH_CONFIDENCE.get(match_method, 0.5),
        "created_at": now,
        "updated_at": now,
    }

    await db[COL].insert_one(doc)

    # Cache the new customer
    if vkn:
        await _try_cache_set(tenant_id, vkn, serialize_doc(doc))

    return serialize_doc(doc)


async def get_or_create_customer(
    tenant_id: str,
    provider: str,
    customer_data: dict[str, Any],
) -> dict[str, Any]:
    """Match first, create if missing. Used during sync flow."""
    matched = await match_customer(tenant_id, provider, customer_data)
    if matched:
        return {**matched, "action": "matched"}

    # Try to create via accounting provider
    from app.accounting.integrators.registry import get_accounting_integrator
    from app.accounting.tenant_integrator_service import get_integrator_credentials

    integrator = get_accounting_integrator(provider)
    creds = await get_integrator_credentials(tenant_id, provider) or {}

    external_ref = ""
    if integrator:
        try:
            result = await integrator.create_customer(customer_data, creds)
            if result.success:
                external_ref = result.external_ref
        except Exception as e:
            logger.warning("Customer creation in %s failed: %s", provider, e)

    # Determine match method
    vkn = customer_data.get("tax_id") or customer_data.get("vkn") or ""
    tckn = customer_data.get("id_number") or customer_data.get("tckn") or ""
    if vkn:
        method = MATCH_VKN
    elif tckn:
        method = MATCH_TCKN
    elif customer_data.get("email"):
        method = MATCH_EMAIL
    else:
        method = "auto"

    created = await create_customer(
        tenant_id=tenant_id,
        provider=provider,
        customer_data=customer_data,
        match_method=method,
        external_customer_id=external_ref,
    )

    if "error" in created:
        # Duplicate VKN - return the existing one
        return {**created.get("existing", created), "action": "existing"}

    return {**created, "action": "created"}


async def list_customers(
    tenant_id: str,
    provider: str | None = None,
    search: str | None = None,
    limit: int = 50,
    skip: int = 0,
) -> dict[str, Any]:
    """List accounting customers with optional filters."""
    db = await get_db()
    q: dict[str, Any] = {"tenant_id": tenant_id}
    if provider:
        q["provider"] = provider
    if search:
        q["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"vkn": {"$regex": search, "$options": "i"}},
            {"tckn": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}},
        ]

    total = await db[COL].count_documents(q)
    cursor = db[COL].find(q).sort("updated_at", -1).skip(skip).limit(limit)
    docs = await cursor.to_list(length=limit)
    return {
        "items": [serialize_doc(d) for d in docs],
        "total": total,
        "limit": limit,
        "skip": skip,
    }


async def update_customer(
    tenant_id: str,
    customer_id: str,
    update_data: dict[str, Any],
) -> dict[str, Any] | None:
    """Update an accounting customer (manual override)."""
    db = await get_db()
    doc = await db[COL].find_one({
        "tenant_id": tenant_id,
        "customer_id": customer_id,
    })
    if not doc:
        return None

    allowed_fields = {"name", "vkn", "tckn", "email", "phone", "tax_office",
                      "address", "city", "country", "external_customer_id", "match_method"}
    update = {k: v for k, v in update_data.items() if k in allowed_fields}
    update["updated_at"] = now_utc()
    update["match_method"] = MATCH_MANUAL

    await db[COL].update_one({"_id": doc["_id"]}, {"$set": update})
    updated = await db[COL].find_one({"_id": doc["_id"]})
    return serialize_doc(updated)


async def get_customer_match_stats(tenant_id: str) -> dict[str, Any]:
    """Get customer matching statistics for dashboard."""
    db = await get_db()
    q = {"tenant_id": tenant_id}
    total = await db[COL].count_documents(q)
    by_method = {}
    for method in [MATCH_VKN, MATCH_TCKN, MATCH_EMAIL, MATCH_PHONE, MATCH_MANUAL, "auto"]:
        by_method[method] = await db[COL].count_documents({**q, "match_method": method})

    unmatched = await db[COL].count_documents({
        **q, "external_customer_id": {"$in": [None, ""]},
    })

    return {
        "total_customers": total,
        "by_match_method": by_method,
        "unmatched_count": unmatched,
    }
