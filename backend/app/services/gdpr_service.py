"""KVKK/GDPR Compliance Service.

Provides:
- Data export (right to portability)
- Data deletion (right to erasure)
- Data anonymization
- Consent tracking
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from app.db import get_db
from app.utils import now_utc

logger = logging.getLogger("gdpr")


# ----- Consent Tracking -----

async def record_consent(
    user_email: str,
    organization_id: str,
    consent_type: str,
    granted: bool,
    ip_address: str = "",
    user_agent: str = "",
) -> dict[str, Any]:
    """Record a consent decision."""
    db = await get_db()
    now = now_utc()
    doc = {
        "_id": str(uuid.uuid4()),
        "user_email": user_email,
        "organization_id": organization_id,
        "consent_type": consent_type,
        "granted": granted,
        "ip_address": ip_address,
        "user_agent": user_agent[:500] if user_agent else "",
        "recorded_at": now,
    }
    await db.gdpr_consents.insert_one(doc)
    return doc


async def get_user_consents(user_email: str, organization_id: str) -> list[dict[str, Any]]:
    """Get all consent records for a user."""
    db = await get_db()
    docs = await db.gdpr_consents.find(
        {"user_email": user_email, "organization_id": organization_id}
    ).sort("recorded_at", -1).to_list(200)
    return [{k: v for k, v in d.items() if k != "_id"} | {"id": str(d["_id"])} for d in docs]


async def get_latest_consent(
    user_email: str, organization_id: str, consent_type: str
) -> Optional[dict[str, Any]]:
    """Get most recent consent record of a specific type."""
    db = await get_db()
    doc = await db.gdpr_consents.find_one(
        {"user_email": user_email, "organization_id": organization_id, "consent_type": consent_type},
        sort=[("recorded_at", -1)],
    )
    if doc:
        return {k: v for k, v in doc.items() if k != "_id"} | {"id": str(doc["_id"])}
    return None


# ----- Data Export -----

async def export_user_data(user_email: str, organization_id: str) -> dict[str, Any]:
    """Export all user data for GDPR portability."""
    db = await get_db()

    # Collect data from all relevant collections
    user = await db.users.find_one({"email": user_email, "organization_id": organization_id})
    user_data = None
    if user:
        user_data = {
            "email": user.get("email"),
            "name": user.get("name"),
            "roles": user.get("roles"),
            "created_at": str(user.get("created_at", "")),
            "last_login_at": str(user.get("last_login_at", "")),
        }

    # Bookings
    bookings = await db.bookings.find(
        {"organization_id": organization_id, "$or": [
            {"guest_email": user_email},
            {"created_by": user_email},
        ]}
    ).to_list(5000)
    bookings_data = []
    for b in bookings:
        bookings_data.append({
            "id": str(b.get("_id", "")),
            "status": b.get("status"),
            "hotel_name": b.get("hotel_name"),
            "stay": b.get("stay"),
            "guest_name": b.get("guest_name"),
            "created_at": str(b.get("created_at", "")),
        })

    # Consent records
    consents = await get_user_consents(user_email, organization_id)

    # Audit logs
    audit_logs = await db.audit_events.find(
        {"organization_id": organization_id, "actor.email": user_email}
    ).sort("created_at", -1).to_list(1000)
    audit_data = [
        {
            "action": a.get("action"),
            "target_type": a.get("target_type"),
            "created_at": str(a.get("created_at", "")),
        }
        for a in audit_logs
    ]

    # Log the export request
    await db.gdpr_requests.insert_one({
        "_id": str(uuid.uuid4()),
        "user_email": user_email,
        "organization_id": organization_id,
        "request_type": "export",
        "status": "completed",
        "created_at": now_utc(),
    })

    return {
        "user": user_data,
        "bookings": bookings_data,
        "consents": consents,
        "audit_logs": audit_data,
        "exported_at": str(now_utc()),
    }


# ----- Data Deletion / Anonymization -----

async def anonymize_user_data(
    user_email: str,
    organization_id: str,
    requested_by: str = "",
) -> dict[str, Any]:
    """Anonymize user data (right to erasure).

    Replaces PII with anonymized placeholders while preserving
    aggregate/statistical data.
    """
    db = await get_db()
    anon_id = str(uuid.uuid4())[:8]
    anon_email = f"anonymized_{anon_id}@deleted.local"
    anon_name = f"Anonymized User {anon_id}"
    now = now_utc()

    results = {"collections_updated": []}

    # Users
    user_result = await db.users.update_one(
        {"email": user_email, "organization_id": organization_id},
        {"$set": {
            "email": anon_email,
            "name": anon_name,
            "password_hash": "DELETED",
            "phone": None,
            "is_active": False,
            "anonymized_at": now,
            "original_email_hash": str(uuid.uuid5(uuid.NAMESPACE_DNS, user_email)),
        }},
    )
    if user_result.modified_count:
        results["collections_updated"].append("users")

    # Bookings - anonymize guest info
    booking_result = await db.bookings.update_many(
        {"organization_id": organization_id, "$or": [
            {"guest_email": user_email},
            {"created_by": user_email},
        ]},
        {"$set": {
            "guest_email": anon_email,
            "guest_name": anon_name,
            "guest_phone": None,
            "anonymized_at": now,
        }},
    )
    if booking_result.modified_count:
        results["collections_updated"].append(f"bookings({booking_result.modified_count})")

    # CRM customers
    crm_result = await db.crm_customers.update_many(
        {"organization_id": organization_id, "email": user_email},
        {"$set": {
            "email": anon_email,
            "name": anon_name,
            "phone": None,
            "anonymized_at": now,
        }},
    )
    if crm_result.modified_count:
        results["collections_updated"].append("crm_customers")

    # Log the deletion request
    await db.gdpr_requests.insert_one({
        "_id": str(uuid.uuid4()),
        "user_email": user_email,
        "organization_id": organization_id,
        "request_type": "anonymize",
        "status": "completed",
        "requested_by": requested_by,
        "anon_email": anon_email,
        "created_at": now,
    })

    results["anonymized_email"] = anon_email
    results["status"] = "completed"
    return results


async def delete_user_data(
    user_email: str,
    organization_id: str,
    requested_by: str = "",
) -> dict[str, Any]:
    """Hard delete user data where legally permissible.

    Note: Some data must be retained for legal/financial compliance.
    Those records are anonymized instead of deleted.
    """
    db = await get_db()
    now = now_utc()
    results = {"deleted": [], "anonymized": []}

    # Hard delete: consents, sessions
    del_consents = await db.gdpr_consents.delete_many(
        {"user_email": user_email, "organization_id": organization_id}
    )
    if del_consents.deleted_count:
        results["deleted"].append(f"consents({del_consents.deleted_count})")

    del_tokens = await db.refresh_tokens.delete_many({"user_email": user_email})
    if del_tokens.deleted_count:
        results["deleted"].append(f"refresh_tokens({del_tokens.deleted_count})")

    # Anonymize: bookings, financial records (must be retained)
    anon_result = await anonymize_user_data(user_email, organization_id, requested_by)
    results["anonymized"] = anon_result.get("collections_updated", [])

    # Deactivate user account
    await db.users.update_one(
        {"email": user_email, "organization_id": organization_id},
        {"$set": {"is_active": False, "deleted_at": now}},
    )

    # Log the request
    await db.gdpr_requests.insert_one({
        "_id": str(uuid.uuid4()),
        "user_email": user_email,
        "organization_id": organization_id,
        "request_type": "delete",
        "status": "completed",
        "requested_by": requested_by,
        "created_at": now,
    })

    results["status"] = "completed"
    return results


async def ensure_gdpr_indexes() -> None:
    db = await get_db()
    try:
        await db.gdpr_consents.create_index([("user_email", 1), ("organization_id", 1)])
        await db.gdpr_consents.create_index([("user_email", 1), ("consent_type", 1)])
        await db.gdpr_requests.create_index([("user_email", 1), ("organization_id", 1)])
        await db.gdpr_requests.create_index("created_at")
    except Exception as e:
        logger.warning("GDPR index creation warning: %s", e)
