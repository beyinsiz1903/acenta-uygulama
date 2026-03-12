"""Enterprise Governance — MongoDB Indexes.

Ensures indexes for all governance collections.
"""
from __future__ import annotations

import logging

from pymongo import ASCENDING, DESCENDING, IndexModel

logger = logging.getLogger("governance.indexes")


async def ensure_governance_indexes(db) -> None:
    """Create all governance-related MongoDB indexes."""
    try:
        # gov_roles
        await db.gov_roles.create_indexes([
            IndexModel([("role", ASCENDING), ("organization_id", ASCENDING)], unique=True),
        ])

        # gov_permissions
        await db.gov_permissions.create_indexes([
            IndexModel([("code", ASCENDING), ("organization_id", ASCENDING)], unique=True),
        ])

        # gov_audit_log
        await db.gov_audit_log.create_indexes([
            IndexModel([("organization_id", ASCENDING), ("timestamp", DESCENDING)]),
            IndexModel([("organization_id", ASCENDING), ("actor_email", ASCENDING), ("timestamp", DESCENDING)]),
            IndexModel([("organization_id", ASCENDING), ("category", ASCENDING), ("timestamp", DESCENDING)]),
            IndexModel([("organization_id", ASCENDING), ("action", ASCENDING)]),
            IndexModel([("timestamp", ASCENDING)], expireAfterSeconds=90 * 24 * 3600),  # 90 day TTL
        ])

        # gov_secrets
        await db.gov_secrets.create_indexes([
            IndexModel([("name", ASCENDING), ("organization_id", ASCENDING)], unique=True),
            IndexModel([("organization_id", ASCENDING), ("is_active", ASCENDING)]),
        ])

        # gov_secret_history
        await db.gov_secret_history.create_indexes([
            IndexModel([("secret_name", ASCENDING), ("organization_id", ASCENDING), ("version", ASCENDING)]),
        ])

        # gov_secret_access_log
        await db.gov_secret_access_log.create_indexes([
            IndexModel([("secret_name", ASCENDING), ("organization_id", ASCENDING)]),
            IndexModel([("accessed_at", ASCENDING)], expireAfterSeconds=30 * 24 * 3600),  # 30 day TTL
        ])

        # gov_tenant_violations
        await db.gov_tenant_violations.create_indexes([
            IndexModel([("requesting_org_id", ASCENDING), ("timestamp", DESCENDING)]),
            IndexModel([("timestamp", ASCENDING)], expireAfterSeconds=90 * 24 * 3600),  # 90 day TTL
        ])

        # gov_compliance_log
        await db.gov_compliance_log.create_indexes([
            IndexModel([("organization_id", ASCENDING), ("sequence", DESCENDING)]),
            IndexModel([("organization_id", ASCENDING), ("operation_type", ASCENDING), ("timestamp", DESCENDING)]),
            IndexModel([("organization_id", ASCENDING), ("booking_id", ASCENDING)]),
            IndexModel([("organization_id", ASCENDING), ("timestamp", DESCENDING)]),
        ])

        # gov_data_policies
        await db.gov_data_policies.create_indexes([
            IndexModel([("organization_id", ASCENDING), ("resource", ASCENDING), ("is_active", ASCENDING)]),
            IndexModel([("organization_id", ASCENDING), ("name", ASCENDING)], unique=True),
        ])

        # gov_security_alerts
        await db.gov_security_alerts.create_indexes([
            IndexModel([("organization_id", ASCENDING), ("status", ASCENDING), ("created_at", DESCENDING)]),
            IndexModel([("organization_id", ASCENDING), ("severity", ASCENDING), ("created_at", DESCENDING)]),
            IndexModel([("organization_id", ASCENDING), ("alert_type", ASCENDING)]),
            IndexModel([("created_at", ASCENDING)], expireAfterSeconds=180 * 24 * 3600),  # 180 day TTL
        ])

        logger.info("Governance indexes created successfully")
    except Exception as exc:
        logger.warning("Governance indexes setup: %s", exc)
