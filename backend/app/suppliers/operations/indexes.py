"""MongoDB indexes for the Operations Layer collections."""
from __future__ import annotations

import logging

logger = logging.getLogger("suppliers.ops.indexes")


async def ensure_operations_indexes(db) -> None:
    """Create indexes for all operations collections."""

    # supplier_debug_logs
    await db.supplier_debug_logs.create_index(
        [("organization_id", 1), ("created_at", -1)]
    )
    await db.supplier_debug_logs.create_index(
        [("organization_id", 1), ("supplier_code", 1), ("created_at", -1)]
    )
    await db.supplier_debug_logs.create_index(
        "created_at", expireAfterSeconds=7 * 86400  # 7 day TTL
    )

    # ops_incidents
    await db.ops_incidents.create_index(
        [("organization_id", 1), ("status", 1), ("created_at", -1)]
    )
    await db.ops_incidents.create_index(
        [("organization_id", 1), ("booking_id", 1)]
    )

    # ops_alerts
    await db.ops_alerts.create_index(
        [("organization_id", 1), ("status", 1), ("created_at", -1)]
    )
    await db.ops_alerts.create_index(
        [("organization_id", 1), ("alert_type", 1)]
    )
    await db.ops_alerts.create_index(
        "created_at", expireAfterSeconds=30 * 86400  # 30 day TTL
    )

    # ops_alert_config
    await db.ops_alert_config.create_index("organization_id", unique=True)

    # ops_audit_log
    await db.ops_audit_log.create_index(
        [("organization_id", 1), ("created_at", -1)]
    )
    await db.ops_audit_log.create_index(
        "created_at", expireAfterSeconds=90 * 86400  # 90 day TTL
    )

    # ops_email_queue
    await db.ops_email_queue.create_index(
        [("status", 1), ("created_at", 1)]
    )
    await db.ops_email_queue.create_index(
        "created_at", expireAfterSeconds=7 * 86400
    )

    # voucher_pipeline
    await db.voucher_pipeline.create_index(
        [("organization_id", 1), ("status", 1)]
    )
    await db.voucher_pipeline.create_index(
        [("organization_id", 1), ("booking_id", 1)]
    )

    logger.info("Operations Layer indexes created")
