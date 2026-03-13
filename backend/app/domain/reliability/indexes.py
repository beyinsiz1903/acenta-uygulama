"""Integration Reliability — MongoDB Indexes."""
from __future__ import annotations

import logging

from pymongo import ASCENDING, DESCENDING, IndexModel

logger = logging.getLogger("reliability.indexes")


async def ensure_reliability_indexes(db) -> None:
    """Create all integration reliability MongoDB indexes."""
    try:
        # rel_resilience_events — P1
        await db.rel_resilience_events.create_indexes([
            IndexModel([("organization_id", ASCENDING), ("supplier_code", ASCENDING), ("timestamp", DESCENDING)]),
            IndexModel([("organization_id", ASCENDING), ("outcome", ASCENDING), ("timestamp", DESCENDING)]),
            IndexModel([("timestamp", ASCENDING)], expireAfterSeconds=30 * 24 * 3600),  # 30 day TTL
        ])

        # rel_resilience_config — P1
        await db.rel_resilience_config.create_indexes([
            IndexModel([("organization_id", ASCENDING)], unique=True),
        ])

        # rel_sandbox_config — P2
        await db.rel_sandbox_config.create_indexes([
            IndexModel([("organization_id", ASCENDING)], unique=True),
        ])

        # rel_sandbox_log — P2
        await db.rel_sandbox_log.create_indexes([
            IndexModel([("organization_id", ASCENDING), ("supplier_code", ASCENDING), ("timestamp", DESCENDING)]),
            IndexModel([("timestamp", ASCENDING)], expireAfterSeconds=7 * 24 * 3600),  # 7 day TTL
        ])

        # rel_dead_letter_queue — P3
        await db.rel_dead_letter_queue.create_indexes([
            IndexModel([("organization_id", ASCENDING), ("category", ASCENDING), ("status", ASCENDING)]),
            IndexModel([("organization_id", ASCENDING), ("entry_id", ASCENDING)], unique=True),
            IndexModel([("organization_id", ASCENDING), ("supplier_code", ASCENDING), ("status", ASCENDING)]),
        ])

        # rel_retry_config — P3
        await db.rel_retry_config.create_indexes([
            IndexModel([("organization_id", ASCENDING)], unique=True),
        ])

        # rel_idempotency_store — P4
        await db.rel_idempotency_store.create_indexes([
            IndexModel([("organization_id", ASCENDING), ("idempotency_key", ASCENDING), ("operation", ASCENDING)], unique=True),
            IndexModel([("created_at", ASCENDING)], expireAfterSeconds=24 * 3600),  # 24h TTL
        ])

        # rel_request_dedup — P4
        await db.rel_request_dedup.create_indexes([
            IndexModel([("organization_id", ASCENDING), ("request_hash", ASCENDING)]),
            IndexModel([("created_at", ASCENDING)], expireAfterSeconds=60),  # 60s TTL
        ])

        # rel_api_versions — P5
        await db.rel_api_versions.create_indexes([
            IndexModel([("organization_id", ASCENDING), ("supplier_code", ASCENDING)], unique=True),
        ])

        # rel_version_history — P5
        await db.rel_version_history.create_indexes([
            IndexModel([("organization_id", ASCENDING), ("supplier_code", ASCENDING), ("timestamp", DESCENDING)]),
        ])

        # rel_contract_schemas — P6
        await db.rel_contract_schemas.create_indexes([
            IndexModel([("organization_id", ASCENDING), ("supplier_code", ASCENDING), ("method", ASCENDING)], unique=True),
        ])

        # rel_contract_violations — P6
        await db.rel_contract_violations.create_indexes([
            IndexModel([("organization_id", ASCENDING), ("supplier_code", ASCENDING), ("timestamp", DESCENDING)]),
            IndexModel([("timestamp", ASCENDING)], expireAfterSeconds=90 * 24 * 3600),  # 90 day TTL
        ])

        # rel_metrics — P7
        await db.rel_metrics.create_indexes([
            IndexModel([("organization_id", ASCENDING), ("supplier_code", ASCENDING), ("metric_type", ASCENDING), ("timestamp", DESCENDING)]),
            IndexModel([("organization_id", ASCENDING), ("timestamp", DESCENDING)]),
            IndexModel([("timestamp", ASCENDING)], expireAfterSeconds=30 * 24 * 3600),  # 30 day TTL
        ])

        # rel_incidents — P8
        await db.rel_incidents.create_indexes([
            IndexModel([("organization_id", ASCENDING), ("status", ASCENDING), ("created_at", DESCENDING)]),
            IndexModel([("organization_id", ASCENDING), ("supplier_code", ASCENDING), ("created_at", DESCENDING)]),
            IndexModel([("organization_id", ASCENDING), ("incident_id", ASCENDING)], unique=True),
            IndexModel([("organization_id", ASCENDING), ("severity", ASCENDING)]),
        ])

        # rel_supplier_status — P8/P9
        await db.rel_supplier_status.create_indexes([
            IndexModel([("organization_id", ASCENDING), ("supplier_code", ASCENDING)], unique=True),
        ])

        logger.info("Integration reliability indexes created successfully")
    except Exception as exc:
        logger.warning("Reliability indexes setup: %s", exc)
