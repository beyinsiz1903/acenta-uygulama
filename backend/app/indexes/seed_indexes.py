"""Consolidated seed indexes — extracted from seed.py.

All collection indexes that were previously scattered inside ensure_seed_data()
are gathered here so they can be called independently from data seeding.

Called once at application startup via server.py lifespan.
"""
from __future__ import annotations

import logging

logger = logging.getLogger("acenta-master.indexes")


async def ensure_seed_indexes(db) -> None:
    """Create all indexes that were previously inside seed.py."""

    # ── Core collections ──────────────────────────────────────
    await db.organizations.create_index("slug", unique=True)
    await db.users.create_index([("organization_id", 1), ("email", 1)], unique=True)
    await db.customers.create_index([("organization_id", 1), ("email", 1)])
    await db.products.create_index([("organization_id", 1), ("type", 1)])
    await db.rate_plans.create_index([("organization_id", 1), ("product_id", 1)])
    await db.inventory.create_index(
        [("organization_id", 1), ("product_id", 1), ("date", 1)], unique=True
    )
    await db.reservations.create_index(
        [("organization_id", 1), ("pnr", 1)], unique=True
    )
    await db.reservations.create_index(
        [("organization_id", 1), ("idempotency_key", 1)], unique=True, sparse=True
    )
    await db.payments.create_index([("organization_id", 1), ("reservation_id", 1)])
    await db.leads.create_index(
        [("organization_id", 1), ("status", 1), ("sort_index", -1)]
    )
    await db.quotes.create_index([("organization_id", 1), ("status", 1)])

    # ── Agencies / Hotels / Links ─────────────────────────────
    await db.agencies.create_index([("organization_id", 1), ("name", 1)])
    await db.hotels.create_index([("organization_id", 1), ("name", 1)])
    await db.agency_hotel_links.create_index(
        [("organization_id", 1), ("agency_id", 1), ("hotel_id", 1)], unique=True
    )

    # ── PMS / Source-based indexes ────────────────────────────
    await db.rate_plans.create_index([("organization_id", 1), ("source", 1)])
    await db.rate_periods.create_index([("organization_id", 1), ("source", 1)])
    await db.inventory.create_index([("organization_id", 1), ("source", 1)])
    await db.stop_sell_rules.create_index([("organization_id", 1), ("source", 1)])
    await db.channel_allocations.create_index([("organization_id", 1), ("source", 1)])

    # ── Audit logs ────────────────────────────────────────────
    await db.audit_logs.create_index(
        [("organization_id", 1), ("created_at", -1)]
    )
    await db.audit_logs.create_index(
        [("organization_id", 1), ("target.type", 1), ("target.id", 1), ("created_at", -1)]
    )

    # ── Booking events ────────────────────────────────────────
    await db.booking_events.create_index(
        [("organization_id", 1), ("delivered", 1), ("created_at", 1)]
    )
    await db.booking_events.create_index(
        [("organization_id", 1), ("entity_id", 1), ("event_type", 1)]
    )
    await db.booking_events.create_index(
        [("booking_id", 1), ("event_type", 1), ("payload.actor_email", 1)]
    )

    # ── PMS mock ──────────────────────────────────────────────
    await db.pms_idempotency.create_index(
        [("organization_id", 1), ("idempotency_key", 1)], unique=True
    )
    await db.pms_bookings.create_index(
        [("organization_id", 1), ("hotel_id", 1), ("created_at", -1)]
    )

    # ── Search cache (TTL) ────────────────────────────────────
    await db.search_cache.create_index([("expires_at", 1)], expireAfterSeconds=0)
    await db.search_cache.create_index(
        [("organization_id", 1), ("agency_id", 1), ("created_at", -1)]
    )

    # ── Vouchers (TTL) ────────────────────────────────────────
    await db.vouchers.create_index([("expires_at", 1)], expireAfterSeconds=0)
    await db.vouchers.create_index([("organization_id", 1), ("booking_id", 1)])
    await db.vouchers.create_index([("token", 1)], unique=True)

    # ── Email outbox ──────────────────────────────────────────
    await db.email_outbox.create_index([("status", 1), ("next_retry_at", 1)])
    await db.email_outbox.create_index([("organization_id", 1), ("booking_id", 1)])

    # ── Hotel integrations ────────────────────────────────────
    await db.hotel_integrations.create_index(
        [("organization_id", 1), ("hotel_id", 1), ("kind", 1)], unique=True
    )
    await db.hotel_integrations.create_index([("status", 1), ("provider", 1)])
    await db.hotel_integrations.create_index(
        [("organization_id", 1), ("kind", 1), ("updated_at", -1)]
    )

    # ── Booking drafts (TTL) ──────────────────────────────────
    await db.booking_drafts.create_index([("expires_at", 1)], expireAfterSeconds=0)
    await db.booking_drafts.create_index([("organization_id", 1), ("created_at", -1)])
    await db.booking_drafts.create_index([("submitted_booking_id", 1)])

    # ── Bookings ──────────────────────────────────────────────
    await db.bookings.create_index(
        [("organization_id", 1), ("status", 1), ("submitted_at", -1)]
    )
    await db.bookings.create_index(
        [("agency_id", 1), ("status", 1), ("submitted_at", -1)]
    )
    await db.bookings.create_index(
        [("hotel_id", 1), ("status", 1), ("submitted_at", -1)]
    )
    await db.bookings.create_index([("approval_deadline_at", 1)])
    await db.bookings.create_index([
        ("organization_id", 1),
        ("agency_id", 1),
        ("hotel_id", 1),
        ("status", 1),
        ("created_at", -1),
    ])

    # ── Integration sync outbox ───────────────────────────────
    await db.integration_sync_outbox.create_index(
        [("status", 1), ("next_retry_at", 1)]
    )
    await db.integration_sync_outbox.create_index([
        ("organization_id", 1), ("hotel_id", 1), ("kind", 1), ("created_at", -1)
    ])

    # ── Booking financial entries ─────────────────────────────
    await db.booking_financial_entries.create_index(
        [("organization_id", 1), ("hotel_id", 1), ("month", 1), ("settlement_status", 1)]
    )
    await db.booking_financial_entries.create_index(
        [("organization_id", 1), ("agency_id", 1), ("month", 1), ("settlement_status", 1)]
    )
    await db.booking_financial_entries.create_index(
        [("organization_id", 1), ("booking_id", 1), ("type", 1)]
    )

    # ── Match actions ─────────────────────────────────────────
    await db.match_actions.create_index(
        [("organization_id", 1), ("match_id", 1)], unique=True
    )
    await db.match_actions.create_index(
        [("organization_id", 1), ("status", 1), ("updated_at", -1)]
    )

    # ── Action policies ───────────────────────────────────────
    await db.action_policies.create_index(
        [("organization_id", 1)], unique=True
    )

    # ── Pricing rules ─────────────────────────────────────────
    await db.pricing_rules.create_index(
        [("organization_id", 1), ("status", 1), ("priority", -1)]
    )
    await db.pricing_rules.create_index([
        ("organization_id", 1),
        ("status", 1),
        ("scope.agency_id", 1),
        ("scope.product_id", 1),
        ("scope.product_type", 1),
    ])
    await db.pricing_rules.create_index(
        [("organization_id", 1), ("validity.from", 1), ("validity.to", 1)]
    )

    # ── Approval tasks ────────────────────────────────────────
    await db.approval_tasks.create_index(
        [("organization_id", 1), ("status", 1), ("requested_at", -1)]
    )
    await db.approval_tasks.create_index(
        [("organization_id", 1), ("task_type", 1), ("status", 1)]
    )
    await db.approval_tasks.create_index(
        [("organization_id", 1), ("target.match_id", 1)]
    )

    # ── Risk snapshots ────────────────────────────────────────
    await db.risk_snapshots.create_index(
        [("organization_id", 1), ("snapshot_key", 1), ("generated_at", -1)]
    )

    # ── Match alert policies & deliveries ─────────────────────
    await db.match_alert_policies.create_index(
        [("organization_id", 1)], unique=True
    )

    # Migrate old unique index to channel-aware version
    try:
        indexes = await db.match_alert_deliveries.index_information()
        for name, info in indexes.items():
            keys = info.get("key") or []
            if keys == [("organization_id", 1), ("match_id", 1), ("fingerprint", 1)]:
                await db.match_alert_deliveries.drop_index(name)
    except Exception:
        pass

    await db.match_alert_deliveries.create_index(
        [("organization_id", 1), ("match_id", 1), ("fingerprint", 1), ("channel", 1)],
        unique=True,
    )
    await db.match_alert_deliveries.create_index(
        [("organization_id", 1), ("sent_at", -1)]
    )

    # ── Booking outcomes ──────────────────────────────────────
    await db.booking_outcomes.create_index(
        [("organization_id", 1), ("booking_id", 1)], unique=True
    )
    await db.booking_outcomes.create_index([
        ("organization_id", 1),
        ("agency_id", 1),
        ("hotel_id", 1),
        ("checkin_date", -1),
    ])

    # ── Risk profiles ─────────────────────────────────────────
    await db.risk_profiles.create_index(
        [("organization_id", 1)], unique=True
    )

    # ── Export policies & runs ────────────────────────────────
    await db.export_policies.create_index(
        [("organization_id", 1), ("key", 1)], unique=True
    )
    await db.export_runs.create_index(
        [("organization_id", 1), ("policy_key", 1), ("generated_at", -1)]
    )
    await db.export_runs.create_index(
        [("organization_id", 1), ("download.token", 1)], unique=True, sparse=True
    )

    logger.info("Seed indexes ensured")
