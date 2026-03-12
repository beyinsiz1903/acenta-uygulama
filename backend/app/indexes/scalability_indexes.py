"""Scalability indexes — performance-critical indexes for high-scale operations.

Targets:
  - Event queries (domain_events)
  - Rate limit cleanup
  - Job queue efficiency
  - Booking search optimization
  - Settlement runs
  - Supplier accrual queries

Applied during app startup alongside existing indexes.
"""
from __future__ import annotations

import logging

logger = logging.getLogger("indexes.scalability")


async def ensure_scalability_indexes(db) -> dict:
    """Create all scalability-phase indexes. Returns stats."""
    created = []
    errors = []

    index_specs = [
        # Event Bus: fast event queries
        ("domain_events", [("event_type", 1), ("organization_id", 1), ("created_at", -1)], "idx_events_type_org_time"),
        ("domain_events", [("correlation_id", 1)], "idx_events_correlation"),
        ("domain_events", [("processed", 1), ("created_at", 1)], "idx_events_unprocessed"),

        # Rate limits: TTL cleanup + fast lookups
        ("rate_limits", [("key", 1), ("created_at", -1)], "idx_rl_key_time"),
        ("rate_limits", [("expires_at", 1)], "idx_rl_expires_ttl"),

        # Jobs: efficient claim queries
        ("jobs", [("status", 1), ("next_run_at", 1), ("locked_at", 1)], "idx_jobs_claimable"),
        ("jobs", [("organization_id", 1), ("type", 1), ("status", 1)], "idx_jobs_org_type_status"),

        # Bookings: search optimization
        ("bookings", [("organization_id", 1), ("status", 1), ("created_at", -1)], "idx_bookings_org_status_time"),
        ("bookings", [("organization_id", 1), ("agency_id", 1), ("status", 1)], "idx_bookings_org_agency_status"),
        ("bookings", [("hotel_id", 1), ("check_in", 1)], "idx_bookings_hotel_checkin"),

        # Reservations: PMS operational queries
        ("reservations", [("organization_id", 1), ("hotel_id", 1), ("status", 1)], "idx_res_org_hotel_status"),
        ("reservations", [("check_in", 1), ("check_out", 1)], "idx_res_checkin_checkout"),

        # Finance: ledger queries
        ("ledger_postings", [("organization_id", 1), ("account_id", 1), ("occurred_at", -1)], "idx_ledger_org_acct_time"),
        ("ledger_postings", [("source_type", 1), ("source_id", 1)], "idx_ledger_source"),

        # Settlement: run queries
        ("settlement_runs", [("organization_id", 1), ("status", 1), ("created_at", -1)], "idx_settlement_org_status_time"),

        # Supplier accruals
        ("supplier_accruals", [("organization_id", 1), ("supplier_id", 1), ("status", 1)], "idx_accruals_org_supplier"),

        # Usage metrics: time-series
        ("usage_daily", [("tenant_id", 1), ("metric", 1), ("day", -1)], "idx_usage_tenant_metric_day"),

        # Audit log: compliance queries
        ("audit_log", [("organization_id", 1), ("action", 1), ("created_at", -1)], "idx_audit_org_action_time"),
        ("audit_log", [("entity_type", 1), ("entity_id", 1)], "idx_audit_entity"),

        # App cache: TTL cleanup
        ("app_cache", [("expires_at", 1)], "idx_cache_expires_ttl"),

        # Products: catalog search
        ("products", [("organization_id", 1), ("type", 1), ("status", 1)], "idx_products_org_type_status"),
        ("products", [("supplier_id", 1), ("status", 1)], "idx_products_supplier_status"),
    ]

    for collection, keys, name in index_specs:
        try:
            await db[collection].create_index(keys, name=name, background=True)
            created.append(name)
        except Exception as e:
            errors.append({"index": name, "error": str(e)})

    # Create TTL index for rate_limits (auto-cleanup)
    try:
        await db.rate_limits.create_index(
            "expires_at",
            name="idx_rl_ttl",
            expireAfterSeconds=0,
            background=True,
        )
        created.append("idx_rl_ttl")
    except Exception as e:
        errors.append({"index": "idx_rl_ttl", "error": str(e)})

    # Create TTL index for app_cache
    try:
        await db.app_cache.create_index(
            "expires_at",
            name="idx_cache_ttl",
            expireAfterSeconds=0,
            background=True,
        )
        created.append("idx_cache_ttl")
    except Exception as e:
        errors.append({"index": "idx_cache_ttl", "error": str(e)})

    # Create TTL index for domain_events (30 day retention)
    try:
        await db.domain_events.create_index(
            "created_at",
            name="idx_events_ttl_30d",
            expireAfterSeconds=30 * 24 * 3600,
            background=True,
        )
        created.append("idx_events_ttl_30d")
    except Exception as e:
        errors.append({"index": "idx_events_ttl_30d", "error": str(e)})

    result = {
        "total_indexes": len(index_specs) + 3,
        "created": len(created),
        "errors": len(errors),
        "error_details": errors if errors else None,
    }
    logger.info("Scalability indexes: %d created, %d errors", len(created), len(errors))
    return result
