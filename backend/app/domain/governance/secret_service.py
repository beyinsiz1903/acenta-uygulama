"""Enterprise Governance — Secret Management Service (Part 4).

Secure secret storage with rotation tracking, access logging,
and Vault/AWS Secrets Manager design patterns.
"""
from __future__ import annotations

import base64
import hashlib
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger("governance.secrets")

# In production, this would come from Vault or KMS
_ENCRYPTION_KEY = os.environ.get("GOV_SECRET_ENCRYPTION_KEY", "")


def _mask_value(value: str) -> str:
    """Mask secret value for display."""
    if len(value) <= 4:
        return "****"
    return value[:2] + "*" * (len(value) - 4) + value[-2:]


def _encrypt_value(value: str) -> str:
    """Encrypt secret value (production: use Vault/KMS)."""
    encoded = base64.b64encode(value.encode()).decode()
    return f"enc:{encoded}"


def _decrypt_value(encrypted: str) -> str:
    """Decrypt secret value."""
    if encrypted.startswith("enc:"):
        return base64.b64decode(encrypted[4:]).decode()
    return encrypted


async def store_secret(
    db: Any,
    org_id: str,
    *,
    name: str,
    value: str,
    secret_type: str,
    description: str = "",
    actor_email: str,
    rotation_days: int = 90,
) -> dict:
    """Store a new secret or rotate an existing one."""
    now = datetime.now(timezone.utc)
    existing = await db.gov_secrets.find_one(
        {"name": name, "organization_id": org_id}
    )

    encrypted_value = _encrypt_value(value)
    value_hash = hashlib.sha256(value.encode()).hexdigest()[:16]

    if existing:
        # Rotation: archive old version
        version = (existing.get("version", 0)) + 1
        await db.gov_secret_history.insert_one({
            "_id": str(uuid.uuid4()),
            "secret_name": name,
            "organization_id": org_id,
            "version": existing.get("version", 0),
            "value_hash": existing.get("value_hash", ""),
            "rotated_at": now,
            "rotated_by": actor_email,
        })
        await db.gov_secrets.update_one(
            {"_id": existing["_id"]},
            {"$set": {
                "encrypted_value": encrypted_value,
                "value_hash": value_hash,
                "version": version,
                "last_rotated_at": now,
                "last_rotated_by": actor_email,
                "updated_at": now,
            }},
        )
        return {
            "name": name,
            "version": version,
            "action": "rotated",
            "timestamp": now.isoformat(),
        }

    doc = {
        "_id": str(uuid.uuid4()),
        "name": name,
        "organization_id": org_id,
        "secret_type": secret_type,
        "description": description,
        "encrypted_value": encrypted_value,
        "value_hash": value_hash,
        "version": 1,
        "rotation_days": rotation_days,
        "last_rotated_at": now,
        "last_rotated_by": actor_email,
        "created_at": now,
        "created_by": actor_email,
        "updated_at": now,
        "is_active": True,
    }
    await db.gov_secrets.insert_one(doc)
    return {
        "name": name,
        "version": 1,
        "action": "created",
        "timestamp": now.isoformat(),
    }


async def list_secrets(db: Any, org_id: str) -> list[dict]:
    """List all secrets (values masked)."""
    docs = await db.gov_secrets.find(
        {"organization_id": org_id, "is_active": True},
        {"_id": 0, "encrypted_value": 0},
    ).sort("name", 1).to_list(200)
    return docs


async def get_secret_value(
    db: Any, org_id: str, name: str, actor_email: str,
) -> Optional[dict]:
    """Retrieve a secret value (with access logging)."""
    doc = await db.gov_secrets.find_one(
        {"name": name, "organization_id": org_id, "is_active": True}
    )
    if not doc:
        return None

    # Log access
    await db.gov_secret_access_log.insert_one({
        "_id": str(uuid.uuid4()),
        "secret_name": name,
        "organization_id": org_id,
        "accessed_by": actor_email,
        "accessed_at": datetime.now(timezone.utc),
    })

    decrypted = _decrypt_value(doc["encrypted_value"])
    return {
        "name": name,
        "value": decrypted,
        "version": doc.get("version", 1),
        "secret_type": doc.get("secret_type", ""),
    }


async def delete_secret(
    db: Any, org_id: str, name: str, actor_email: str,
) -> dict:
    """Soft-delete a secret."""
    now = datetime.now(timezone.utc)
    result = await db.gov_secrets.update_one(
        {"name": name, "organization_id": org_id},
        {"$set": {"is_active": False, "deleted_at": now, "deleted_by": actor_email}},
    )
    return {
        "name": name,
        "deleted": result.modified_count > 0,
        "timestamp": now.isoformat(),
    }


async def check_rotation_status(db: Any, org_id: str) -> list[dict]:
    """Check which secrets need rotation."""
    from datetime import timedelta
    now = datetime.now(timezone.utc)
    docs = await db.gov_secrets.find(
        {"organization_id": org_id, "is_active": True},
        {"_id": 0, "encrypted_value": 0},
    ).to_list(200)

    results = []
    for doc in docs:
        rotation_days = doc.get("rotation_days", 90)
        last_rotated = doc.get("last_rotated_at", doc.get("created_at", now))
        if last_rotated.tzinfo is None:
            last_rotated = last_rotated.replace(tzinfo=timezone.utc)
        days_since = (now - last_rotated).days
        needs_rotation = days_since >= rotation_days

        results.append({
            "name": doc["name"],
            "secret_type": doc.get("secret_type", ""),
            "days_since_rotation": days_since,
            "rotation_policy_days": rotation_days,
            "needs_rotation": needs_rotation,
            "status": "overdue" if needs_rotation else "ok",
        })

    return sorted(results, key=lambda x: x["days_since_rotation"], reverse=True)
