"""MongoDB indexes for the supplier ecosystem domain.

Collections:
  - suppliers: registered supplier configs
  - supplier_ecosystem_health: health scores
  - supplier_failover_logs: failover audit trail
  - booking_orchestration_runs: orchestration tracking
  - supplier_events: domain events (already via event_bus)
  - channel_partners: B2B distribution partners
  - supplier_pricing_rules: pricing configuration
  - supplier_inventory_cache_metadata: cache tracking

All collections are tenant-isolated by organization_id.
"""
from __future__ import annotations

import logging

logger = logging.getLogger("suppliers.indexes")


async def ensure_supplier_ecosystem_indexes(db) -> int:
    """Create all supplier ecosystem indexes. Returns count created."""
    count = 0

    indexes = [
        # --- suppliers ---
        ("suppliers", [("organization_id", 1), ("supplier_code", 1)], {"unique": True}),
        ("suppliers", [("supplier_type", 1)], {}),
        ("suppliers", [("status", 1)], {}),

        # --- supplier_ecosystem_health ---
        ("supplier_ecosystem_health", [("organization_id", 1), ("supplier_code", 1)], {"unique": True}),
        ("supplier_ecosystem_health", [("state", 1)], {}),
        ("supplier_ecosystem_health", [("score", -1)], {}),

        # --- supplier_failover_logs ---
        ("supplier_failover_logs", [("organization_id", 1), ("created_at", -1)], {}),
        ("supplier_failover_logs", [("primary_supplier", 1), ("created_at", -1)], {}),
        ("supplier_failover_logs", [("created_at", 1)], {"expireAfterSeconds": 2592000}),  # 30 day TTL

        # --- booking_orchestration_runs ---
        ("booking_orchestration_runs", [("booking_id", 1)], {}),
        ("booking_orchestration_runs", [("organization_id", 1), ("created_at", -1)], {}),
        ("booking_orchestration_runs", [("status", 1)], {}),
        ("booking_orchestration_runs", [("created_at", 1)], {"expireAfterSeconds": 7776000}),  # 90 day TTL

        # --- channel_partners ---
        ("channel_partners", [("organization_id", 1), ("status", 1)], {}),
        ("channel_partners", [("partner_id", 1)], {"unique": True}),
        ("channel_partners", [("api_key", 1)], {"sparse": True}),

        # --- supplier_pricing_rules ---
        ("supplier_pricing_rules", [("organization_id", 1), ("active", 1), ("priority", 1)], {}),
        ("supplier_pricing_rules", [("rule_id", 1)], {"unique": True}),

        # --- supplier_inventory_cache_metadata ---
        ("supplier_inventory_cache_metadata", [("organization_id", 1), ("supplier_code", 1)], {}),
        ("supplier_inventory_cache_metadata", [("updated_at", 1)], {"expireAfterSeconds": 86400}),  # 1 day TTL
    ]

    for collection_name, keys, options in indexes:
        try:
            await db[collection_name].create_index(keys, **options)
            count += 1
        except Exception as e:
            # Duplicate index is fine
            if "already exists" not in str(e).lower():
                logger.warning("Index creation failed for %s: %s", collection_name, e)

    logger.info("Ensured %d supplier ecosystem indexes", count)
    return count
