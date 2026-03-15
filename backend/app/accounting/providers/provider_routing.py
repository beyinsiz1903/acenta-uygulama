"""Provider Routing & Credential Management Service (MEGA PROMPT #34).

Handles:
  - Tenant -> Provider mapping (one tenant = one active provider)
  - Credential CRUD with encryption
  - Connection testing
  - Provider health tracking

DB Collection: accounting_provider_configs
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

from app.accounting.credential_encryption import (
    decrypt_credentials,
    encrypt_credentials,
    mask_credentials,
)
from app.accounting.providers.capability_matrix import (
    get_capability,
    list_all_providers,
)
from app.accounting.providers.provider_registry import get_provider
from app.db import get_db
from app.utils import now_utc, serialize_doc

logger = logging.getLogger("accounting.provider_routing")

COL = "accounting_provider_configs"


async def set_tenant_provider(
    tenant_id: str,
    provider_code: str,
    credentials: dict[str, Any],
    updated_by: str = "",
) -> dict[str, Any]:
    """Configure (upsert) the accounting provider for a tenant.

    One tenant = one active accounting provider.
    Credentials are encrypted at rest.
    """
    cap = get_capability(provider_code)
    if not cap:
        return {"error": f"Bilinmeyen provider: {provider_code}"}

    db = await get_db()
    now = now_utc()
    encrypted = encrypt_credentials(credentials)

    doc = {
        "tenant_id": tenant_id,
        "provider_code": provider_code,
        "provider_name": cap.name,
        "encrypted_credentials": encrypted,
        "credential_fields": list(credentials.keys()),
        "status": "configured",
        "last_test_at": None,
        "last_test_result": None,
        "rotated_at": None,
        "updated_by": updated_by,
        "updated_at": now,
        "health": {
            "total_requests": 0,
            "total_failures": 0,
            "avg_latency_ms": 0,
            "last_error": None,
            "last_success_at": None,
        },
    }

    existing = await db[COL].find_one({"tenant_id": tenant_id})
    if existing:
        # Deactivate current, replace with new provider
        await db[COL].update_one(
            {"_id": existing["_id"]},
            {"$set": doc},
        )
        doc["config_id"] = existing.get("config_id", f"APC-{uuid.uuid4().hex[:8].upper()}")
        doc["created_at"] = existing.get("created_at", now)
    else:
        doc["config_id"] = f"APC-{uuid.uuid4().hex[:8].upper()}"
        doc["created_at"] = now
        await db[COL].insert_one(doc)

    return _safe_doc(doc)


async def get_tenant_provider(tenant_id: str) -> dict[str, Any] | None:
    """Get the active accounting provider config for a tenant (without credentials)."""
    db = await get_db()
    doc = await db[COL].find_one({"tenant_id": tenant_id})
    if not doc:
        return None
    safe = _safe_doc(doc)
    try:
        creds = decrypt_credentials(doc["encrypted_credentials"])
        safe["masked_credentials"] = mask_credentials(creds)
    except Exception:
        safe["masked_credentials"] = {}
    return safe


async def get_tenant_credentials(tenant_id: str) -> tuple[str | None, dict[str, Any]]:
    """Get provider code and decrypted credentials for a tenant.

    Returns (provider_code, credentials) or (None, {}) if not configured.
    Used internally by the sync engine.
    """
    db = await get_db()
    doc = await db[COL].find_one({"tenant_id": tenant_id})
    if not doc:
        return None, {}
    try:
        creds = decrypt_credentials(doc["encrypted_credentials"])
        return doc["provider_code"], creds
    except Exception:
        return doc["provider_code"], {}


async def delete_tenant_provider(tenant_id: str) -> bool:
    """Remove accounting provider config for a tenant."""
    db = await get_db()
    result = await db[COL].delete_one({"tenant_id": tenant_id})
    return result.deleted_count > 0


async def test_provider_connection(tenant_id: str) -> dict[str, Any]:
    """Test the configured provider connection for a tenant."""
    db = await get_db()
    doc = await db[COL].find_one({"tenant_id": tenant_id})
    if not doc:
        return {"success": False, "error_message": "Provider yapilandirmasi bulunamadi"}

    provider_code = doc["provider_code"]
    provider = get_provider(provider_code)
    if not provider:
        return {"success": False, "error_message": f"Provider bulunamadi: {provider_code}"}

    try:
        creds = decrypt_credentials(doc["encrypted_credentials"])
    except Exception:
        return {"success": False, "error_message": "Kimlik bilgileri cozulemedi"}

    result = await provider.test_connection(creds)

    now = now_utc()
    update: dict[str, Any] = {
        "last_test_at": now,
        "last_test_result": result.status,
        "updated_at": now,
    }
    if result.success:
        update["status"] = "active"
    else:
        update["status"] = "error"

    await db[COL].update_one({"_id": doc["_id"]}, {"$set": update})

    return result.to_dict()


async def record_provider_request(
    tenant_id: str, success: bool, latency_ms: float, error: str | None = None,
) -> None:
    """Track provider health metrics after each request."""
    db = await get_db()
    now = now_utc()

    inc_fields: dict[str, int] = {"health.total_requests": 1}
    if not success:
        inc_fields["health.total_failures"] = 1

    set_fields: dict[str, Any] = {"updated_at": now}
    if success:
        set_fields["health.last_success_at"] = now
    if error:
        set_fields["health.last_error"] = error

    await db[COL].update_one(
        {"tenant_id": tenant_id},
        {
            "$inc": inc_fields,
            "$set": set_fields,
        },
    )


async def rotate_credentials(
    tenant_id: str,
    new_credentials: dict[str, Any],
    rotated_by: str = "",
) -> dict[str, Any]:
    """Rotate provider credentials for a tenant."""
    db = await get_db()
    doc = await db[COL].find_one({"tenant_id": tenant_id})
    if not doc:
        return {"error": "Provider yapilandirmasi bulunamadi"}

    now = now_utc()
    encrypted = encrypt_credentials(new_credentials)
    await db[COL].update_one(
        {"_id": doc["_id"]},
        {"$set": {
            "encrypted_credentials": encrypted,
            "credential_fields": list(new_credentials.keys()),
            "rotated_at": now,
            "updated_by": rotated_by,
            "updated_at": now,
            "status": "configured",
            "last_test_at": None,
            "last_test_result": None,
        }},
    )

    updated = await db[COL].find_one({"_id": doc["_id"]})
    return _safe_doc(updated)


async def get_provider_health_summary() -> list[dict[str, Any]]:
    """Get health summary for all configured tenant providers (admin view)."""
    db = await get_db()
    cursor = db[COL].find({}, {"_id": 0, "encrypted_credentials": 0})
    docs = await cursor.to_list(length=500)
    results = []
    for doc in docs:
        health = doc.get("health", {})
        total = health.get("total_requests", 0)
        failures = health.get("total_failures", 0)
        success_rate = ((total - failures) / total * 100) if total > 0 else 0
        results.append({
            "tenant_id": doc.get("tenant_id"),
            "provider_code": doc.get("provider_code"),
            "provider_name": doc.get("provider_name"),
            "status": doc.get("status"),
            "last_test_at": str(doc["last_test_at"]) if doc.get("last_test_at") else None,
            "last_test_result": doc.get("last_test_result"),
            "total_requests": total,
            "total_failures": failures,
            "success_rate": round(success_rate, 1),
            "last_error": health.get("last_error"),
            "last_success_at": str(health["last_success_at"]) if health.get("last_success_at") else None,
            "updated_at": str(doc["updated_at"]) if doc.get("updated_at") else None,
        })
    return results


def _safe_doc(doc: dict[str, Any]) -> dict[str, Any]:
    safe = serialize_doc(doc)
    safe.pop("encrypted_credentials", None)
    return safe
