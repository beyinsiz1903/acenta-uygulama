"""Syroce auto-provisioning hook.

When a new SaaS organization is approved, we automatically create a marketplace
agency on the PMS side and store the (encrypted) raw API key in our DB.

Idempotent: if a syroce_agencies record already exists with a syroce_agency_id,
the PMS create call is skipped.

Failures do NOT roll back the user/organization signup — the org just gets a
"failed" sync status with the error message, and the admin panel surfaces a
"Yeniden Senkronize Et" button.
"""
from __future__ import annotations

import asyncio
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from pymongo.errors import DuplicateKeyError

from app.services.syroce import admin as syroce_admin
from app.services.syroce.crypto import encrypt_key
from app.services.syroce.errors import SyroceError

logger = logging.getLogger(__name__)

COLLECTION = "syroce_agencies"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _is_enabled() -> bool:
    """Provisioning hook is best-effort; only runs if base url + admin token are set."""
    return bool(os.environ.get("SYROCE_BASE_URL")) and bool(os.environ.get("SYROCE_MARKETPLACE_ADMIN_TOKEN"))


async def ensure_indexes(db) -> None:
    try:
        await db[COLLECTION].create_index("organization_id", unique=True, name="uniq_org")
        await db[COLLECTION].create_index(
            "syroce_agency_id", unique=True, sparse=True, name="uniq_syroce_agency_id",
        )
    except Exception as e:
        logger.debug("syroce_agencies index ensure: %s", e)


async def get_status(db, organization_id: str) -> Dict[str, Any]:
    doc = await db[COLLECTION].find_one({"organization_id": organization_id})
    if not doc:
        return {"provisioned": False, "key_set": False}
    return {
        "provisioned": True,
        "organization_id": organization_id,
        "syroce_agency_id": doc.get("syroce_agency_id"),
        "syroce_status": doc.get("syroce_status"),
        "name": doc.get("name"),
        "contact_email": doc.get("contact_email"),
        "country": doc.get("country"),
        "default_commission_pct": doc.get("default_commission_pct"),
        "key_set": bool(doc.get("syroce_api_key_encrypted")),
        "syroce_created_at": doc.get("syroce_created_at"),
        "syroce_last_synced_at": doc.get("syroce_last_synced_at"),
        "syroce_sync_error": doc.get("syroce_sync_error"),
    }


async def provision_agency(
    db,
    *,
    organization_id: str,
    name: str,
    contact_email: str,
    contact_phone: str = "",
    country: str = "TR",
    default_commission_pct: float = 10.0,
) -> Dict[str, Any]:
    """Create or refresh an organization's Syroce marketplace agency.

    Idempotent: if a syroce_agency_id already exists for this org, no PMS call
    is made and the existing record is returned (with status: "active").
    """
    await ensure_indexes(db)
    existing = await db[COLLECTION].find_one({"organization_id": organization_id})

    # STRICT idempotency: if a remote syroce_agency_id already exists, NEVER call create again.
    if existing and existing.get("syroce_agency_id"):
        if existing.get("syroce_api_key_encrypted"):
            # Fully provisioned — re-confirm status.
            await db[COLLECTION].update_one(
                {"organization_id": organization_id},
                {"$set": {
                    "syroce_status": "active",
                    "syroce_sync_error": None,
                    "syroce_last_synced_at": _now(),
                    "updated_at": _now(),
                }},
            )
            return await get_status(db, organization_id)
        # Has agency_id but missing key — recover via key regeneration (no duplicate agency).
        logger.info("syroce: existing agency_id without key — recovering via regenerate org=%s", organization_id)
        return await regenerate_key(db, organization_id)

    if not _is_enabled():
        # Save a placeholder so admin can retry once secrets are configured
        await db[COLLECTION].update_one(
            {"organization_id": organization_id},
            {"$set": {
                "organization_id": organization_id,
                "name": name,
                "contact_email": contact_email,
                "contact_phone": contact_phone,
                "country": country,
                "default_commission_pct": default_commission_pct,
                "syroce_status": "not_configured",
                "syroce_sync_error": "SYROCE_BASE_URL veya SYROCE_MARKETPLACE_ADMIN_TOKEN tanımlı değil.",
                "updated_at": _now(),
            }, "$setOnInsert": {
                "id": str(uuid.uuid4()),
                "created_at": _now(),
            }},
            upsert=True,
        )
        return await get_status(db, organization_id)

    # Atomically CLAIM the slot: transition to "provisioning" state. If another
    # caller has already claimed it, abort BEFORE calling PMS to avoid creating
    # a duplicate remote marketplace agency.
    claim_set = {
        "organization_id": organization_id,
        "name": name,
        "contact_email": contact_email,
        "contact_phone": contact_phone,
        "country": country,
        "default_commission_pct": default_commission_pct,
        "syroce_status": "provisioning",
        "syroce_sync_error": None,
        "updated_at": _now(),
    }
    try:
        claim_result = await db[COLLECTION].update_one(
            {
                "organization_id": organization_id,
                "syroce_status": {"$ne": "provisioning"},
                "syroce_agency_id": {"$in": [None, ""]},
            },
            {
                "$set": claim_set,
                "$setOnInsert": {"id": str(uuid.uuid4()), "created_at": _now()},
            },
            upsert=True,
        )
    except DuplicateKeyError:
        raise SyroceError(409, "Bu organizasyon için Syroce sağlama işlemi zaten devam ediyor. Lütfen biraz sonra tekrar deneyin.")
    if claim_result.matched_count == 0 and claim_result.upserted_id is None:
        raise SyroceError(409, "Bu organizasyon için Syroce sağlama işlemi zaten devam ediyor. Lütfen biraz sonra tekrar deneyin.")

    try:
        result = await syroce_admin.create_syroce_agency(
            name=name,
            contact_email=contact_email,
            contact_phone=contact_phone,
            country=country,
            default_commission_pct=default_commission_pct,
        )
    except SyroceError as exc:
        await db[COLLECTION].update_one(
            {"organization_id": organization_id},
            {"$set": {
                "organization_id": organization_id,
                "name": name,
                "contact_email": contact_email,
                "contact_phone": contact_phone,
                "country": country,
                "default_commission_pct": default_commission_pct,
                "syroce_status": "failed",
                "syroce_sync_error": exc.detail,
                "updated_at": _now(),
            }, "$setOnInsert": {
                "id": str(uuid.uuid4()),
                "created_at": _now(),
            }},
            upsert=True,
        )
        # Re-raise so callers (admin endpoint) get a 4xx; the auto-hook should swallow.
        raise

    # Syroce PMS returns: {"agency": {"id": "...", ...}, "api_key": "...", "key_prefix": "...", "warning": "..."}
    # Tolerate both nested and flat shapes for forward-compat.
    agency_obj = result.get("agency") if isinstance(result.get("agency"), dict) else {}
    syroce_agency_id = agency_obj.get("id") or result.get("agency_id") or result.get("id")
    raw_api_key = result.get("api_key")
    if not syroce_agency_id or not raw_api_key:
        raise SyroceError(502, "Syroce admin API beklenen alanları döndürmedi (agency_id / api_key).")

    encrypted = encrypt_key(raw_api_key)

    await db[COLLECTION].update_one(
        {"organization_id": organization_id},
        {"$set": {
            "organization_id": organization_id,
            "name": name,
            "contact_email": contact_email,
            "contact_phone": contact_phone,
            "country": country,
            "default_commission_pct": default_commission_pct,
            "syroce_agency_id": syroce_agency_id,
            "syroce_api_key_encrypted": encrypted,
            "syroce_status": "active",
            "syroce_sync_error": None,
            "syroce_created_at": _now(),
            "syroce_last_synced_at": _now(),
            "updated_at": _now(),
        }, "$setOnInsert": {
            "id": str(uuid.uuid4()),
            "created_at": _now(),
        }},
        upsert=True,
    )
    # NEVER log raw_api_key
    logger.info("syroce: provisioned organization=%s syroce_agency_id=%s", organization_id, syroce_agency_id)
    return await get_status(db, organization_id)


async def regenerate_key(db, organization_id: str) -> Dict[str, Any]:
    doc = await db[COLLECTION].find_one({"organization_id": organization_id})
    if not doc or not doc.get("syroce_agency_id"):
        raise SyroceError(404, "Bu organizasyon için Syroce kaydı bulunamadı.")
    result = await syroce_admin.regenerate_api_key(doc["syroce_agency_id"])
    raw_api_key = result.get("api_key")
    if not raw_api_key:
        raise SyroceError(502, "Syroce admin API yeni api_key döndürmedi.")
    await db[COLLECTION].update_one(
        {"organization_id": organization_id},
        {"$set": {
            "syroce_api_key_encrypted": encrypt_key(raw_api_key),
            "syroce_status": "active",
            "syroce_sync_error": None,
            "syroce_last_synced_at": _now(),
            "updated_at": _now(),
        }},
    )
    logger.info("syroce: key regenerated organization=%s", organization_id)
    return await get_status(db, organization_id)


async def disable_agency(db, organization_id: str) -> Dict[str, Any]:
    doc = await db[COLLECTION].find_one({"organization_id": organization_id})
    if not doc or not doc.get("syroce_agency_id"):
        raise SyroceError(404, "Bu organizasyon için Syroce kaydı bulunamadı.")
    try:
        await syroce_admin.disable_syroce_agency(doc["syroce_agency_id"])
    except SyroceError as exc:
        # 404 from PMS = already gone, treat as success
        if exc.http_status != 404:
            raise
    await db[COLLECTION].update_one(
        {"organization_id": organization_id},
        {"$set": {
            "syroce_status": "disabled",
            "syroce_last_synced_at": _now(),
            "updated_at": _now(),
        }},
    )
    return await get_status(db, organization_id)


async def best_effort_provision(db, *, organization_id: str, name: str, contact_email: str, **kwargs) -> Optional[Dict[str, Any]]:
    """Fire-and-forget hook used by signup flow.

    Never raises — failures are recorded in the syroce_agencies record with
    syroce_status="failed". The signup itself must not roll back.
    """
    try:
        return await provision_agency(
            db,
            organization_id=organization_id,
            name=name,
            contact_email=contact_email,
            **kwargs,
        )
    except SyroceError as exc:
        logger.warning("syroce best-effort provision failed org=%s detail=%s", organization_id, exc.detail)
        return None
    except Exception as exc:
        logger.exception("syroce best-effort provision crashed org=%s err=%s", organization_id, exc)
        return None
