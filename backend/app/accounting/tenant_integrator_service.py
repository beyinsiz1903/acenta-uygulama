"""Tenant Integrator Credential Service (Faz 2).

Manages per-tenant e-document integrator credentials.
Credentials are encrypted at rest with AES-256-GCM.

DB Collection: tenant_integrators
"""
from __future__ import annotations

import uuid
from typing import Any

from app.accounting.credential_encryption import (
    decrypt_credentials,
    encrypt_credentials,
    mask_credentials,
)
from app.accounting.integrators.registry import get_integrator
from app.db import get_db
from app.utils import now_utc, serialize_doc

COL = "tenant_integrators"


async def save_integrator_credentials(
    tenant_id: str,
    provider: str,
    credentials: dict[str, Any],
    saved_by: str = "",
) -> dict[str, Any]:
    """Save (upsert) integrator credentials for a tenant.

    Credentials are encrypted before storage.
    """
    db = await get_db()

    encrypted = encrypt_credentials(credentials)
    now = now_utc()

    doc = {
        "tenant_id": tenant_id,
        "provider": provider,
        "encrypted_credentials": encrypted,
        "credential_fields": list(credentials.keys()),
        "status": "configured",
        "last_test": None,
        "last_test_result": None,
        "saved_by": saved_by,
        "updated_at": now,
    }

    existing = await db[COL].find_one({"tenant_id": tenant_id, "provider": provider})
    if existing:
        await db[COL].update_one(
            {"_id": existing["_id"]},
            {"$set": doc},
        )
        doc["_id"] = existing["_id"]
        doc["created_at"] = existing.get("created_at", now)
    else:
        doc["integrator_id"] = f"INT-{uuid.uuid4().hex[:8].upper()}"
        doc["created_at"] = now
        await db[COL].insert_one(doc)

    return _safe_doc(doc)


async def get_integrator_credentials(tenant_id: str, provider: str) -> dict[str, Any] | None:
    """Get decrypted integrator credentials for a tenant."""
    db = await get_db()
    doc = await db[COL].find_one({"tenant_id": tenant_id, "provider": provider})
    if not doc:
        return None
    try:
        creds = decrypt_credentials(doc["encrypted_credentials"])
        return creds
    except Exception:
        return None


async def list_integrator_configs(tenant_id: str) -> list[dict[str, Any]]:
    """List all configured integrators for a tenant (masked credentials)."""
    db = await get_db()
    cursor = db[COL].find({"tenant_id": tenant_id})
    docs = await cursor.to_list(length=20)
    result = []
    for doc in docs:
        safe = _safe_doc(doc)
        try:
            creds = decrypt_credentials(doc["encrypted_credentials"])
            safe["masked_credentials"] = mask_credentials(creds)
        except Exception:
            safe["masked_credentials"] = {}
        result.append(safe)
    return result


async def delete_integrator_credentials(tenant_id: str, provider: str) -> bool:
    """Delete integrator credentials for a tenant."""
    db = await get_db()
    result = await db[COL].delete_one({"tenant_id": tenant_id, "provider": provider})
    return result.deleted_count > 0


async def test_integrator_connection(
    tenant_id: str, provider: str,
) -> dict[str, Any]:
    """Test integrator connection with stored credentials."""
    creds = await get_integrator_credentials(tenant_id, provider)
    if not creds:
        return {"success": False, "message": "Entegrator kimlik bilgileri bulunamadi"}

    integrator = get_integrator(provider)
    if not integrator:
        return {"success": False, "message": f"Desteklenmeyen entegrator: {provider}"}

    result = await integrator.test_connection(creds)

    # Update last test result
    db = await get_db()
    now = now_utc()
    await db[COL].update_one(
        {"tenant_id": tenant_id, "provider": provider},
        {"$set": {
            "last_test": now,
            "last_test_result": result.status,
            "status": "active" if result.success else "error",
            "updated_at": now,
        }},
    )

    return result.to_dict()


async def has_active_integrator(tenant_id: str) -> bool:
    """Check if tenant has any configured integrator."""
    db = await get_db()
    count = await db[COL].count_documents({"tenant_id": tenant_id})
    return count > 0


def _safe_doc(doc: dict[str, Any]) -> dict[str, Any]:
    """Return a safe version of the document (no encrypted data)."""
    safe = serialize_doc(doc)
    safe.pop("encrypted_credentials", None)
    return safe
