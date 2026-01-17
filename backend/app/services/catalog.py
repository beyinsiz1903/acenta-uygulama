from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
import re

from bson import ObjectId
from pymongo import DESCENDING

from app.errors import AppError
from app.services.audit import write_audit_log
from app.utils import now_utc
from app.db import get_db


def _oid(x: str) -> ObjectId:
    try:
        return ObjectId(x)
    except Exception:
        raise AppError(404, "not_found", "Entity not found", {"id": x})



def _slugify(raw: str) -> str:
    """Very small slug helper for SEO.

    - Lowercases
    - Replaces whitespace with '-'
    - Strips characters outside [a-z0-9-]
    """
    text = (raw or "").strip().lower()
    if not text:
        return ""
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"[^a-z0-9-]", "", text)
    return text.strip("-")


def _name_search(name: dict | None) -> str:
    name = name or {}
    tr = name.get("tr") or ""
    en = name.get("en") or ""
    return (tr + " " + en).strip().lower()


def _normalize_code(raw: str) -> str:
    return (raw or "").strip().upper()


async def create_product(db, actor: dict[str, Any], payload: dict) -> dict:
    org_id = actor["organization_id"]
    actor_email = actor.get("email") or ""
    now = now_utc()

    code = _normalize_code(payload["code"])
    if not code:
        raise AppError(422, "validation_error", "Product code is required", {"field": "code"})

    status = payload.get("status", "inactive")
    default_currency = (payload["default_currency"] or "").upper()
    if not default_currency or len(default_currency) != 3:
        raise AppError(422, "validation_error", "Default currency must be 3-letter code", {"field": "default_currency"})

    # Hotel-specific required fields (service-level guard)
    if payload["type"] == "hotel":
        loc = payload.get("location") or {}
        if not loc.get("city") or not loc.get("country"):
            raise AppError(
                422,
                "validation_error",
                "Hotel products require location.city and location.country",
                {"field": "location"},
            )

    doc = {
        "organization_id": org_id,
        "type": payload["type"],
        "code": code,
        "name": payload["name"],
        "name_search": _name_search(payload.get("name")),
        "status": status,
        "default_currency": default_currency,
        "location": payload.get("location"),
        "created_at": now,
        "updated_at": now,
    }

    try:
        res = await db.products.insert_one(doc)
    except Exception:
        raise AppError(409, "duplicate_code", "Product code already exists", {"code": doc["code"]})

    doc["_id"] = res.inserted_id

    # Audit in service (domain-level)
    await write_audit_log(
        db,
        organization_id=org_id,
        actor={"email": actor_email, "roles": actor.get("roles")},
        request=actor.get("request"),
        action="catalog.product.create",
        target_type="product",
        target_id=str(doc["_id"]),
        before=None,
        after={"code": doc["code"], "type": doc["type"], "status": doc["status"]},
    )

    return doc


async def update_product(db, actor: dict[str, Any], product_id: str, patch: dict) -> dict:
    org_id = actor["organization_id"]
    actor_email = actor.get("email") or ""

    pid = _oid(product_id)
    cur = await db.products.find_one({"_id": pid, "organization_id": org_id})
    if not cur:
        raise AppError(404, "not_found", "Product not found", {"product_id": product_id})

    update: Dict[str, Any] = {}
    for k in ["type", "code", "name", "status", "default_currency", "location"]:
        if k in patch and patch[k] is not None:
            update[k] = patch[k]

    if "code" in update:
        update["code"] = _normalize_code(update["code"])
        if not update["code"]:
            raise AppError(422, "validation_error", "Product code is required", {"field": "code"})

    if "default_currency" in update:
        update["default_currency"] = (update["default_currency"] or "").upper()
        if not update["default_currency"] or len(update["default_currency"]) != 3:
            raise AppError(422, "validation_error", "Default currency must be 3-letter code", {"field": "default_currency"})

    if "name" in update:
        update["name_search"] = _name_search(update["name"])

    if not update:
        return cur

    update["updated_at"] = now_utc()

    try:
        await db.products.update_one({"_id": pid, "organization_id": org_id}, {"$set": update})
    except Exception:
        raise AppError(409, "duplicate_code", "Product code already exists", {"code": update.get("code")})

    nxt = await db.products.find_one({"_id": pid, "organization_id": org_id})

    await write_audit_log(
        db,
        organization_id=org_id,
        actor={"email": actor_email, "roles": actor.get("roles")},
        request=actor.get("request"),
        action="catalog.product.update",
        target_type="product",
        target_id=product_id,
        before={
            "code": cur.get("code"),
            "status": cur.get("status"),
            "name": cur.get("name"),
        },
        after={
            "code": nxt.get("code"),
            "status": nxt.get("status"),
            "name": nxt.get("name"),
        },
    )

    return nxt


async def list_products(
    db,
    org_id: str,
    *,
    q: Optional[str],
    type_: Optional[str],
    status: Optional[str],
    limit: int,
    cursor: Optional[str],
):
    filt: Dict[str, Any] = {"organization_id": org_id}
    if type_:
        filt["type"] = type_
    if status:
        filt["status"] = status
    if q:
        filt["name_search"] = {"$regex": q.strip().lower()}
    if cursor:
        try:
            dt = datetime.fromisoformat(cursor.replace("Z", "+00:00"))
        except Exception:
            raise AppError(422, "validation_error", "Invalid cursor", {"cursor": cursor})
        filt["created_at"] = {"$lt": dt}

    cur = db.products.find(filt).sort("created_at", DESCENDING).limit(limit)
    items = await cur.to_list(length=limit)

    product_ids = [it["_id"] for it in items]
    published_map: Dict[str, int] = {}
    if product_ids:
        pv_cur = db.product_versions.find(
            {
                "organization_id": org_id,
                "product_id": {"$in": product_ids},
                "status": "published",
            },
            {"product_id": 1, "version": 1},
        ).sort("published_at", DESCENDING)
        pv_list = await pv_cur.to_list(length=5000)
        for x in pv_list:
            pid = str(x["product_id"])
            if pid not in published_map:
                published_map[pid] = x["version"]

    next_cursor = items[-1]["created_at"].isoformat() + "Z" if len(items) == limit else None
    return items, published_map, next_cursor


async def create_product_version(db, actor: dict[str, Any], product_id: str, payload: dict) -> dict:
    org_id = actor["organization_id"]
    actor_email = actor.get("email") or ""

    pid = _oid(product_id)
    prod = await db.products.find_one({"_id": pid, "organization_id": org_id})
    if not prod:
        raise AppError(404, "not_found", "Product not found", {"product_id": product_id})

    content = payload.get("content") or {}
    room_ids = content.get("room_type_ids") or []
    rate_ids = content.get("rate_plan_ids") or []

    if room_ids:
        oids = [_oid(x) for x in room_ids]
        count = await db.room_types.count_documents(
            {"organization_id": org_id, "product_id": pid, "_id": {"$in": oids}}
        )
        if count != len(oids):
            raise AppError(409, "invalid_reference", "Room type ids invalid for product", {"room_type_ids": room_ids})

    if rate_ids:
        oids = [_oid(x) for x in rate_ids]
        count = await db.rate_plans.count_documents(
            {"organization_id": org_id, "product_id": pid, "_id": {"$in": oids}}
        )
        if count != len(oids):
            raise AppError(409, "invalid_reference", "Rate plan ids invalid for product", {"rate_plan_ids": rate_ids})

    last = await db.product_versions.find_one(
        {"organization_id": org_id, "product_id": pid}, sort=[("version", DESCENDING)]
    )
    next_ver = (last["version"] + 1) if last else 1

    now = now_utc()
    doc = {
        "organization_id": org_id,
        "product_id": pid,
        "version": next_ver,
        "status": "draft",
        "valid_from": payload.get("valid_from"),
        "valid_to": payload.get("valid_to"),
        "content": content,
        "created_at": now,
        "updated_at": now,
        "published_at": None,
        "published_by_email": None,
    }

    res = await db.product_versions.insert_one(doc)
    doc["_id"] = res.inserted_id

    await write_audit_log(
        db,
        organization_id=org_id,
        actor={"email": actor_email, "roles": actor.get("roles")},
        request=actor.get("request"),
        action="catalog.version.create",
        target_type="product_version",
        target_id=str(doc["_id"]),
        before=None,
        after={"product_id": product_id, "version": next_ver, "status": "draft"},
    )

    return doc


async def list_product_versions(db, org_id: str, product_id: str) -> List[dict[str, Any]]:
    pid = _oid(product_id)
    cur = db.product_versions.find({"organization_id": org_id, "product_id": pid}).sort("version", DESCENDING)
    return await cur.to_list(length=500)


async def publish_product_version(db, actor: dict[str, Any], product_id: str, version_id: str) -> dict:
    org_id = actor["organization_id"]
    actor_email = actor.get("email") or ""

    pid = _oid(product_id)
    vid = _oid(version_id)

    ver = await db.product_versions.find_one({"_id": vid, "organization_id": org_id, "product_id": pid})
    if not ver:
        raise AppError(404, "not_found", "Version not found", {"version_id": version_id})

    # Guard: cannot publish archived versions
    if ver["status"] == "archived":
        raise AppError(
            409,
            "invalid_version_state",
            "Archived version cannot be published",
            {"status": ver["status"]},
        )

    # Guard: product must be active to publish
    prod = await db.products.find_one({"_id": pid, "organization_id": org_id})
    if not prod:
        raise AppError(404, "not_found", "Product not found", {"product_id": product_id})
    if prod.get("status") != "active":
        raise AppError(
            409,
            "product_not_active",
            "Product must be active before publishing versions",
            {"status": prod.get("status")},
        )

    # Additional guard for hotel products: must have at least one active rate plan
    if prod.get("type") == "hotel":
        active_rp_count = await db.rate_plans.count_documents(
            {
                "organization_id": org_id,
                "product_id": pid,
                "status": "active",
            }
        )
        if active_rp_count <= 0:
            raise AppError(
                409,
                "product_not_sellable",
                "Product must have at least one active rate plan before publishing",
                {},
            )

    now = now_utc()

    # Old published → archived
    await db.product_versions.update_many(
        {"organization_id": org_id, "product_id": pid, "status": "published"},
        {"$set": {"status": "archived", "updated_at": now}},
    )

    # SEO+ Pack: publish-time slug + meta defaults (non-destructive)
    # Dokunma kuralı: mevcut slug/meta_* alanları doluysa asla overwrite etme.
    name = (prod.get("name") or {})
    title_tr = name.get("tr") or ""
    title_en = name.get("en") or ""

    update_product_fields: Dict[str, Any] = {}

    # Slug: sadece boşsa üret ve org-scope içinde collision kontrolü yap
    existing_slug = (prod.get("slug") or "").strip()
    if not existing_slug:
        base_title = title_tr or title_en or prod.get("code") or str(pid)
        base_slug = _slugify(base_title)
        slug = base_slug or str(pid)

        # Org-scoped slug collision çözümü (-2, -3 ...)
        suffix = 1
        while True:
            other = await db.products.find_one(
                {
                    "organization_id": org_id,
                    "slug": slug,
                    "_id": {"$ne": pid},
                },
                {"_id": 1},
            )
            if not other:
                break
            suffix += 1
            slug = f"{base_slug}-{suffix}"

        update_product_fields["slug"] = slug

    # Meta title/description: sadece boşsa üret
    existing_meta_title = (prod.get("meta_title") or "").strip()
    existing_meta_desc = (prod.get("meta_description") or "").strip()

    # Base title for SEO fallbacks
    base_title = title_tr or title_en or prod.get("code") or "Otel"

    if not existing_meta_title:
        update_product_fields["meta_title"] = f"{base_title} | Syroce"

    if not existing_meta_desc:
        city = ((prod.get("location") or {}).get("city") or "").strip()
        country = ((prod.get("location") or {}).get("country") or "").strip()
        loc_part = ", ".join([x for x in [city, country] if x])
        if loc_part:
            update_product_fields["meta_description"] = f"{base_title} - {loc_part} için otel rezervasyonu."
        else:
            update_product_fields["meta_description"] = f"{base_title} için otel rezervasyonu."

    if update_product_fields:
        update_product_fields["updated_at"] = now
        await db.products.update_one(
            {"_id": pid, "organization_id": org_id},
            {"$set": update_product_fields},
        )

    await db.product_versions.update_one(
        {"_id": vid, "organization_id": org_id, "product_id": pid},
        {
            "$set": {
                "status": "published",
                "published_at": now,
                "published_by_email": actor_email,
                "updated_at": now,
            }
        },
    )

    nxt = await db.product_versions.find_one({"_id": vid, "organization_id": org_id, "product_id": pid})

    await write_audit_log(
        db,
        organization_id=org_id,
        actor={"email": actor_email, "roles": actor.get("roles")},
        request=actor.get("request"),
        action="catalog.version.publish",
        target_type="product_version",
        target_id=version_id,
        before={"status": ver.get("status")},
        after={"status": "published", "published_at": now.isoformat()},
    )

    return nxt
