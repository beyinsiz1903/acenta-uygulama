"""KVKK/GDPR Full Compliance Service.

Provides:
- Data export (right to portability) - comprehensive across all collections
- Data deletion (right to erasure)
- Data anonymization
- Consent tracking with KVKK-specific types
- Data retention policy
- Data processing log (veri işleme kaydı)
- Right to be forgotten with processing queue
"""
from __future__ import annotations

import logging
import uuid
from datetime import timedelta
from typing import Any, Optional

from app.db import get_db
from app.utils import now_utc

logger = logging.getLogger("gdpr")

# KVKK consent types
KVKK_CONSENT_TYPES = {
    "acik_riza": "Açık Rıza (Explicit Consent)",
    "marketing": "Pazarlama İzni",
    "analytics": "Analitik / İstatistik",
    "third_party": "Üçüncü Taraf Paylaşım",
    "data_processing": "Veri İşleme",
    "profiling": "Profilleme",
    "international_transfer": "Yurt Dışı Aktarım",
    "cookie_essential": "Zorunlu Çerezler",
    "cookie_analytics": "Analitik Çerezler",
    "cookie_marketing": "Pazarlama Çerezleri",
}

# Data retention periods (in days)
DATA_RETENTION_POLICY = {
    "bookings": 3650,        # 10 years (financial records)
    "payments": 3650,        # 10 years (financial records)
    "invoices": 3650,        # 10 years (tax requirement)
    "audit_events": 2555,    # 7 years (audit trail)
    "gdpr_consents": 1825,   # 5 years (consent proof)
    "gdpr_requests": 1825,   # 5 years
    "users": 365,            # 1 year after deactivation
    "sessions": 90,          # 90 days
    "error_tracking": 90,    # 90 days
    "cache_entries": 1,      # 1 day
}


# ----- Consent Tracking -----

async def record_consent(
    user_email: str,
    organization_id: str,
    consent_type: str,
    granted: bool,
    ip_address: str = "",
    user_agent: str = "",
    legal_basis: str = "",
    version: str = "1.0",
) -> dict[str, Any]:
    """Record a consent decision with KVKK compliance."""
    db = await get_db()
    now = now_utc()
    doc = {
        "_id": str(uuid.uuid4()),
        "user_email": user_email,
        "organization_id": organization_id,
        "consent_type": consent_type,
        "consent_label": KVKK_CONSENT_TYPES.get(consent_type, consent_type),
        "granted": granted,
        "ip_address": ip_address,
        "user_agent": user_agent[:500] if user_agent else "",
        "legal_basis": legal_basis or ("explicit_consent" if granted else "withdrawal"),
        "version": version,
        "recorded_at": now,
        "expires_at": now + timedelta(days=365) if granted else None,
    }
    await db.gdpr_consents.insert_one(doc)

    # Log to data processing registry
    await _log_data_processing(
        db, organization_id, user_email,
        action="consent_recorded",
        details=f"consent_type={consent_type}, granted={granted}",
    )

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


# ----- Data Export (Comprehensive) -----

async def export_user_data(user_email: str, organization_id: str) -> dict[str, Any]:
    """Export all user data for GDPR/KVKK portability (comprehensive)."""
    db = await get_db()

    # Collect data from ALL relevant collections
    user = await db.users.find_one({"email": user_email, "organization_id": organization_id})
    user_data = None
    if user:
        user_data = {
            "email": user.get("email"),
            "name": user.get("name"),
            "roles": user.get("roles"),
            "phone": user.get("phone"),
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
    bookings_data = [
        {
            "id": str(b.get("_id", "")),
            "status": b.get("status"),
            "hotel_name": b.get("hotel_name"),
            "stay": b.get("stay"),
            "guest_name": b.get("guest_name"),
            "amounts": b.get("amounts"),
            "created_at": str(b.get("created_at", "")),
        }
        for b in bookings
    ]

    # Reservations
    reservations = await db.reservations.find(
        {"organization_id": organization_id, "$or": [
            {"customer_email": user_email},
            {"guest_email": user_email},
            {"created_by": user_email},
        ]}
    ).to_list(5000)
    reservations_data = [
        {
            "id": str(r.get("_id", "")),
            "pnr": r.get("pnr"),
            "status": r.get("status"),
            "total_price": r.get("total_price"),
            "currency": r.get("currency"),
            "start_date": r.get("start_date"),
            "end_date": r.get("end_date"),
            "created_at": str(r.get("created_at", "")),
        }
        for r in reservations
    ]

    # Tour reservations
    tour_reservations = await db.tour_reservations.find(
        {"organization_id": organization_id, "guest.email": user_email}
    ).to_list(5000)
    tour_data = [
        {
            "id": str(t.get("_id", "")),
            "reservation_code": t.get("reservation_code"),
            "tour_name": t.get("tour_name"),
            "status": t.get("status"),
            "pricing": t.get("pricing"),
            "guest": t.get("guest"),
            "created_at": str(t.get("created_at", "")),
        }
        for t in tour_reservations
    ]

    # Customers (CRM)
    customers = await db.customers.find(
        {"organization_id": organization_id, "$or": [
            {"email": user_email},
        ]}
    ).to_list(100)
    customers_data = [
        {
            "id": str(c.get("_id", "")),
            "name": c.get("name"),
            "email": c.get("email"),
            "phone": c.get("phone"),
            "tags": c.get("tags"),
            "created_at": str(c.get("created_at", "")),
        }
        for c in customers
    ]

    # CRM customers
    crm_customers = await db.crm_customers.find(
        {"organization_id": organization_id, "email": user_email}
    ).to_list(100)
    crm_data = [
        {
            "id": str(c.get("_id", "")),
            "name": c.get("name"),
            "email": c.get("email"),
            "phone": c.get("phone"),
            "created_at": str(c.get("created_at", "")),
        }
        for c in crm_customers
    ]

    # Payments
    payments = await db.payments.find(
        {"organization_id": organization_id, "$or": [
            {"payer_email": user_email},
            {"created_by": user_email},
        ]}
    ).to_list(5000)
    payments_data = [
        {
            "id": str(p.get("_id", "")),
            "amount": p.get("amount"),
            "currency": p.get("currency"),
            "method": p.get("method"),
            "status": p.get("status"),
            "created_at": str(p.get("created_at", "")),
        }
        for p in payments
    ]

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

    # Sessions
    sessions = await db.refresh_tokens.find(
        {"user_email": user_email}
    ).to_list(100)
    sessions_data = [
        {
            "user_agent": s.get("user_agent", "")[:100],
            "ip_address": s.get("ip_address"),
            "created_at": str(s.get("created_at", "")),
        }
        for s in sessions
    ]

    # Log the export request
    await db.gdpr_requests.insert_one({
        "_id": str(uuid.uuid4()),
        "user_email": user_email,
        "organization_id": organization_id,
        "request_type": "export",
        "status": "completed",
        "collections_exported": [
            "users", "bookings", "reservations", "tour_reservations",
            "customers", "crm_customers", "payments", "consents",
            "audit_events", "sessions",
        ],
        "created_at": now_utc(),
    })

    await _log_data_processing(
        await get_db(), organization_id, user_email,
        action="data_export",
        details="Full KVKK data export completed",
    )

    return {
        "export_format": "KVKK_COMPLIANT_JSON_v2",
        "user": user_data,
        "bookings": bookings_data,
        "reservations": reservations_data,
        "tour_reservations": tour_data,
        "customers": customers_data,
        "crm_customers": crm_data,
        "payments": payments_data,
        "consents": consents,
        "audit_logs": audit_data,
        "sessions": sessions_data,
        "exported_at": str(now_utc()),
        "data_controller": "Organization",
        "legal_basis": "KVKK Madde 11 - Veri taşınabilirliği hakkı",
    }


# ----- Data Anonymization (Comprehensive) -----

async def anonymize_user_data(
    user_email: str,
    organization_id: str,
    requested_by: str = "",
) -> dict[str, Any]:
    """Anonymize user data comprehensively (KVKK right to erasure)."""
    db = await get_db()
    anon_id = str(uuid.uuid4())[:8]
    anon_email = f"anonymized_{anon_id}@deleted.local"
    anon_name = f"Anonim Kullanıcı {anon_id}"
    anon_phone = None
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
            "guest_phone": anon_phone,
            "anonymized_at": now,
        }},
    )
    if booking_result.modified_count:
        results["collections_updated"].append(f"bookings({booking_result.modified_count})")

    # Reservations
    res_result = await db.reservations.update_many(
        {"organization_id": organization_id, "$or": [
            {"customer_email": user_email},
            {"guest_email": user_email},
            {"created_by": user_email},
        ]},
        {"$set": {
            "customer_email": anon_email,
            "guest_email": anon_email,
            "customer_name": anon_name,
            "guest_name": anon_name,
            "customer_phone": anon_phone,
            "guest_phone": anon_phone,
            "anonymized_at": now,
        }},
    )
    if res_result.modified_count:
        results["collections_updated"].append(f"reservations({res_result.modified_count})")

    # Tour reservations
    tour_result = await db.tour_reservations.update_many(
        {"organization_id": organization_id, "guest.email": user_email},
        {"$set": {
            "guest.email": anon_email,
            "guest.full_name": anon_name,
            "guest.phone": anon_phone,
            "anonymized_at": now,
        }},
    )
    if tour_result.modified_count:
        results["collections_updated"].append(f"tour_reservations({tour_result.modified_count})")

    # Customers
    cust_result = await db.customers.update_many(
        {"organization_id": organization_id, "email": user_email},
        {"$set": {
            "email": anon_email,
            "name": anon_name,
            "phone": anon_phone,
            "anonymized_at": now,
        }},
    )
    if cust_result.modified_count:
        results["collections_updated"].append(f"customers({cust_result.modified_count})")

    # CRM customers
    crm_result = await db.crm_customers.update_many(
        {"organization_id": organization_id, "email": user_email},
        {"$set": {
            "email": anon_email,
            "name": anon_name,
            "phone": anon_phone,
            "anonymized_at": now,
        }},
    )
    if crm_result.modified_count:
        results["collections_updated"].append(f"crm_customers({crm_result.modified_count})")

    # Log the request
    await db.gdpr_requests.insert_one({
        "_id": str(uuid.uuid4()),
        "user_email": user_email,
        "organization_id": organization_id,
        "request_type": "anonymize",
        "status": "completed",
        "requested_by": requested_by,
        "anon_email": anon_email,
        "collections_affected": results["collections_updated"],
        "created_at": now,
    })

    await _log_data_processing(
        db, organization_id, user_email,
        action="data_anonymized",
        details=f"Anonymized to {anon_email}, collections: {results['collections_updated']}",
    )

    results["anonymized_email"] = anon_email
    results["status"] = "completed"
    return results


# ----- Data Deletion -----

async def delete_user_data(
    user_email: str,
    organization_id: str,
    requested_by: str = "",
) -> dict[str, Any]:
    """Hard delete user data where legally permissible."""
    db = await get_db()
    now = now_utc()
    results = {"deleted": [], "anonymized": []}

    # Hard delete: consents, sessions, notifications, inbox
    for col_name, query in [
        ("gdpr_consents", {"user_email": user_email, "organization_id": organization_id}),
        ("refresh_tokens", {"user_email": user_email}),
        ("token_blacklist", {"user_email": user_email}),
        ("notifications", {"user_email": user_email, "organization_id": organization_id}),
    ]:
        try:
            result = await db[col_name].delete_many(query)
            if result.deleted_count:
                results["deleted"].append(f"{col_name}({result.deleted_count})")
        except Exception:
            pass

    # Anonymize: bookings, financial records (must be retained by law)
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
        "deleted_collections": results["deleted"],
        "anonymized_collections": results["anonymized"],
        "created_at": now,
    })

    results["status"] = "completed"
    return results


# ----- Data Processing Log (Veri İşleme Kaydı) -----

async def _log_data_processing(
    db, organization_id: str, data_subject: str,
    action: str, details: str = "",
):
    """Log all data processing activities (KVKK Madde 16 requirement)."""
    try:
        await db.kvkk_processing_log.insert_one({
            "_id": str(uuid.uuid4()),
            "organization_id": organization_id,
            "data_subject": data_subject,
            "action": action,
            "details": details,
            "legal_basis": "KVKK Madde 5/6",
            "timestamp": now_utc(),
        })
    except Exception as e:
        logger.warning("KVKK processing log failed: %s", e)


async def get_data_processing_log(
    organization_id: str,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """Get KVKK data processing log."""
    db = await get_db()
    docs = await db.kvkk_processing_log.find(
        {"organization_id": organization_id}
    ).sort("timestamp", -1).to_list(limit)
    return [{k: v for k, v in d.items()} for d in docs]


# ----- Data Retention Policy -----

async def get_retention_policy() -> dict[str, Any]:
    """Get data retention policy."""
    return {
        "policy_version": "2.0",
        "legal_basis": "KVKK Madde 7 - Kişisel verilerin silinmesi, yok edilmesi veya anonim hale getirilmesi",
        "retention_periods": {
            k: {"days": v, "description": _retention_desc(k)}
            for k, v in DATA_RETENTION_POLICY.items()
        },
    }


def _retention_desc(collection: str) -> str:
    descs = {
        "bookings": "Finansal kayıtlar (VUK gereği 10 yıl)",
        "payments": "Ödeme kayıtları (VUK gereği 10 yıl)",
        "invoices": "Fatura kayıtları (VUK gereği 10 yıl)",
        "audit_events": "Denetim izleri (7 yıl)",
        "gdpr_consents": "Açık rıza kanıtları (5 yıl)",
        "gdpr_requests": "KVKK talepleri (5 yıl)",
        "users": "Kullanıcı hesapları (deaktivasyon sonrası 1 yıl)",
        "sessions": "Oturum verileri (90 gün)",
        "error_tracking": "Hata izleme (90 gün)",
        "cache_entries": "Önbellek (1 gün)",
    }
    return descs.get(collection, "")


# ----- Indexes -----

async def ensure_gdpr_indexes() -> None:
    db = await get_db()
    try:
        await db.gdpr_consents.create_index([("user_email", 1), ("organization_id", 1)])
        await db.gdpr_consents.create_index([("user_email", 1), ("consent_type", 1)])
        await db.gdpr_requests.create_index([("user_email", 1), ("organization_id", 1)])
        await db.gdpr_requests.create_index("created_at")
        await db.kvkk_processing_log.create_index([("organization_id", 1), ("timestamp", -1)])
        await db.kvkk_processing_log.create_index("data_subject")
    except Exception as e:
        logger.warning("GDPR/KVKK index creation warning: %s", e)
