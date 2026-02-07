"""B2 - Comprehensive Index Migration.

Ensures all performance-critical indexes exist. Idempotent.
"""
from __future__ import annotations

import logging

logger = logging.getLogger("perf_indexes")


async def ensure_perf_indexes(db) -> dict[str, list[str]]:
    """Create all performance-critical indexes."""
    created = []
    skipped = []
    errors = []

    index_specs = [
        # B1: Perf samples (TTL 7 days)
        ("perf_samples", [("timestamp", -1)], {"expireAfterSeconds": 604800}),
        ("perf_samples", [("path", 1), ("method", 1), ("timestamp", 1)], {}),
        # B3: App cache (TTL via expires_at)
        ("app_cache", [("key", 1), ("tenant_id", 1)], {"unique": True}),
        ("app_cache", [("expires_at", 1)], {"expireAfterSeconds": 0}),
        # B2: CRM
        ("crm_deals", [("organization_id", 1), ("updated_at", -1)], {}),
        ("crm_notes", [("organization_id", 1), ("entity_type", 1), ("entity_id", 1), ("created_at", -1)], {}),
        # B2: Reservations / Ops
        ("reservations", [("organization_id", 1), ("status", 1), ("start_date", 1)], {}),
        ("reservations", [("organization_id", 1), ("created_at", -1)], {}),
        ("ops_cases", [("organization_id", 1), ("status", 1), ("created_at", -1)], {}),
        # B2: Billing
        ("billing_subscriptions", [("tenant_id", 1), ("status", 1)], {}),
        # B2: Audit supplement
        ("audit_logs_chain", [("tenant_id", 1), ("action", 1), ("created_at", -1)], {}),
        # B2: Bookings
        ("bookings", [("organization_id", 1), ("status", 1), ("created_at", -1)], {}),
        ("bookings", [("organization_id", 1), ("customer_id", 1)], {}),
        # B2: Products
        ("products", [("organization_id", 1), ("status", 1)], {}),
        # B2: Invoices
        ("efatura_invoices", [("tenant_id", 1), ("created_at", -1)], {}),
        # B2: Tickets
        ("tickets", [("organization_id", 1), ("created_at", -1)], {}),
        # Ops excellence supplement
        ("system_errors", [("severity", 1), ("last_seen", -1)], {}),
        ("system_incidents", [("severity", 1), ("end_time", 1)], {}),
    ]

    for collection_name, keys, options in index_specs:
        try:
            collection = db[collection_name]
            await collection.create_index(keys, **options)
            created.append(f"{collection_name}: {keys}")
        except Exception as e:
            err_str = str(e)
            if "already exists" in err_str.lower() or "IndexOptionsConflict" in err_str:
                skipped.append(f"{collection_name}: {keys}")
            else:
                errors.append(f"{collection_name}: {keys} -> {err_str[:100]}")
                logger.warning("Index creation failed: %s %s", collection_name, err_str[:200])

    logger.info("Perf indexes: %d created, %d skipped, %d errors", len(created), len(skipped), len(errors))
    return {"created": created, "skipped": skipped, "errors": errors}
