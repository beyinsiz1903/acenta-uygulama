"""MongoDB $jsonSchema validation for critical collections.

Enforces data integrity at the database level for the most important
collections. This prevents malformed documents from being inserted.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("schema_validation")

# ============================================================================
# Schema Definitions for Top 10 Critical Collections
# ============================================================================

USERS_SCHEMA = {
    "bsonType": "object",
    "required": ["email", "password_hash", "roles", "organization_id"],
    "properties": {
        "email": {"bsonType": "string", "description": "User email address"},
        "password_hash": {"bsonType": "string", "description": "Bcrypt hash"},
        "roles": {"bsonType": "array", "items": {"bsonType": "string"}},
        "organization_id": {"bsonType": "string"},
        "name": {"bsonType": "string"},
        "is_active": {"bsonType": "bool"},
    },
}

ORGANIZATIONS_SCHEMA = {
    "bsonType": "object",
    "required": ["name", "slug"],
    "properties": {
        "name": {"bsonType": "string"},
        "slug": {"bsonType": "string"},
        "settings": {"bsonType": "object"},
    },
}

TENANTS_SCHEMA = {
    "bsonType": "object",
    "required": ["organization_id", "name", "status"],
    "properties": {
        "organization_id": {"bsonType": "string"},
        "name": {"bsonType": "string"},
        "slug": {"bsonType": "string"},
        "status": {"bsonType": "string", "enum": ["active", "suspended", "inactive", "trialing", "cancelled"]},
        "is_active": {"bsonType": "bool"},
    },
}

BOOKINGS_SCHEMA = {
    "bsonType": "object",
    "required": ["organization_id", "status"],
    "properties": {
        "organization_id": {"bsonType": "string"},
        "agency_id": {"bsonType": "string"},
        "status": {
            "bsonType": "string",
            "enum": ["DRAFT", "QUOTED", "PENDING", "CONFIRMED", "CANCELLED", "COMPLETED", "EXPIRED", "AMENDMENT_PENDING"],
        },
        "channel_id": {"bsonType": "string"},
        "total_amount": {"bsonType": ["double", "int", "decimal"]},
        "currency": {"bsonType": "string"},
    },
}

AGENCIES_SCHEMA = {
    "bsonType": "object",
    "required": ["organization_id", "name"],
    "properties": {
        "organization_id": {"bsonType": "string"},
        "name": {"bsonType": "string"},
        "settings": {"bsonType": "object"},
    },
}

PRODUCTS_SCHEMA = {
    "bsonType": "object",
    "required": ["organization_id", "type", "status"],
    "properties": {
        "organization_id": {"bsonType": "string"},
        "type": {"bsonType": "string", "enum": ["hotel", "tour", "transfer", "activity"]},
        "status": {"bsonType": "string", "enum": ["active", "inactive", "draft", "archived"]},
        "name": {"bsonType": "object"},
    },
}

MEMBERSHIPS_SCHEMA = {
    "bsonType": "object",
    "required": ["user_id", "tenant_id", "role", "status"],
    "properties": {
        "user_id": {"bsonType": "string"},
        "tenant_id": {"bsonType": "string"},
        "role": {"bsonType": "string"},
        "status": {"bsonType": "string", "enum": ["active", "suspended", "revoked"]},
    },
}

RESERVATIONS_SCHEMA = {
    "bsonType": "object",
    "required": ["organization_id"],
    "properties": {
        "organization_id": {"bsonType": "string"},
        "hotel_id": {"bsonType": "string"},
        "guest_name": {"bsonType": "string"},
        "status": {"bsonType": "string"},
    },
}

FINANCE_ACCOUNTS_SCHEMA = {
    "bsonType": "object",
    "required": ["organization_id", "type", "currency"],
    "properties": {
        "organization_id": {"bsonType": "string"},
        "type": {"bsonType": "string", "enum": ["agency", "platform", "supplier", "escrow"]},
        "currency": {"bsonType": "string"},
        "status": {"bsonType": "string", "enum": ["active", "frozen", "closed"]},
    },
}

AUDIT_LOG_SCHEMA = {
    "bsonType": "object",
    "required": ["action", "actor_id", "timestamp"],
    "properties": {
        "action": {"bsonType": "string"},
        "actor_id": {"bsonType": "string"},
        "timestamp": {"bsonType": "date"},
        "tenant_id": {"bsonType": "string"},
        "resource_type": {"bsonType": "string"},
    },
}


# Collection name -> schema mapping
SCHEMA_MAP: dict[str, dict[str, Any]] = {
    "users": USERS_SCHEMA,
    "organizations": ORGANIZATIONS_SCHEMA,
    "tenants": TENANTS_SCHEMA,
    "bookings": BOOKINGS_SCHEMA,
    "agencies": AGENCIES_SCHEMA,
    "products": PRODUCTS_SCHEMA,
    "memberships": MEMBERSHIPS_SCHEMA,
    "reservations": RESERVATIONS_SCHEMA,
    "finance_accounts": FINANCE_ACCOUNTS_SCHEMA,
    "audit_log": AUDIT_LOG_SCHEMA,
}


async def apply_schema_validation(db, *, strict: bool = False) -> dict[str, str]:
    """Apply $jsonSchema validation to critical collections.

    Args:
        db: AsyncIOMotorDatabase instance
        strict: If True, use 'error' validation action (rejects invalid inserts).
                If False, use 'warn' (logs but allows).

    Returns:
        Dict mapping collection name -> result status
    """
    validation_action = "error" if strict else "warn"
    results: dict[str, str] = {}

    for collection_name, schema in SCHEMA_MAP.items():
        try:
            # Check if collection exists
            existing_collections = await db.list_collection_names()
            if collection_name not in existing_collections:
                # Create collection with validation
                await db.create_collection(
                    collection_name,
                    validator={"$jsonSchema": schema},
                    validationLevel="moderate",
                    validationAction=validation_action,
                )
                results[collection_name] = "created_with_validation"
                logger.info("Created collection '%s' with schema validation", collection_name)
            else:
                # Apply validation to existing collection
                await db.command({
                    "collMod": collection_name,
                    "validator": {"$jsonSchema": schema},
                    "validationLevel": "moderate",
                    "validationAction": validation_action,
                })
                results[collection_name] = "validation_applied"
                logger.info("Applied schema validation to '%s'", collection_name)
        except Exception as exc:
            results[collection_name] = f"error: {str(exc)[:100]}"
            logger.warning("Failed to apply schema validation to '%s': %s", collection_name, exc)

    return results
