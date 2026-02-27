"""Consolidated seed indexes — extracted from seed.py + server.py inline blocks.

All collection indexes gathered here with defensive _safe_create pattern
for production MongoDB where the user may lack createIndex permission.

Called once at application startup via server.py lifespan.
"""
from __future__ import annotations

import logging

from pymongo.errors import OperationFailure

logger = logging.getLogger("acenta-master.indexes")


async def _safe_create(collection, *args, **kwargs):
    """Create index, swallowing permission/conflict errors."""
    try:
        await collection.create_index(*args, **kwargs)
    except OperationFailure as e:
        msg = str(e).lower()
        if any(k in msg for k in (
            "indexoptionsconflict", "indexkeyspecsconflict",
            "already exists", "unauthorized", "not authorized",
        )):
            logger.debug("Skipping index for %s: %s", collection.name, msg[:120])
            return
        raise
    except Exception as e:
        logger.debug("Index creation skipped for %s: %s", collection.name, str(e)[:120])


async def ensure_seed_indexes(db) -> None:
    """Create all indexes (seed + portfolio + enterprise + GTM)."""

    # ══════════════════════════════════════════════════════════
    # CORE COLLECTIONS (from seed.py)
    # ══════════════════════════════════════════════════════════
    await _safe_create(db.organizations, "slug", unique=True)
    await _safe_create(db.users, [("organization_id", 1), ("email", 1)], unique=True)
    await _safe_create(db.customers, [("organization_id", 1), ("email", 1)])
    await _safe_create(db.products, [("organization_id", 1), ("type", 1)])
    await _safe_create(db.rate_plans, [("organization_id", 1), ("product_id", 1)])
    await _safe_create(db.inventory, [("organization_id", 1), ("product_id", 1), ("date", 1)], unique=True)
    await _safe_create(db.reservations, [("organization_id", 1), ("pnr", 1)], unique=True)
    await _safe_create(db.reservations, [("organization_id", 1), ("idempotency_key", 1)], unique=True, sparse=True)
    await _safe_create(db.payments, [("organization_id", 1), ("reservation_id", 1)])
    await _safe_create(db.leads, [("organization_id", 1), ("status", 1), ("sort_index", -1)])
    await _safe_create(db.quotes, [("organization_id", 1), ("status", 1)])

    # ── Agencies / Hotels / Links ─────────────────────────────
    await _safe_create(db.agencies, [("organization_id", 1), ("name", 1)])
    await _safe_create(db.hotels, [("organization_id", 1), ("name", 1)])
    await _safe_create(db.agency_hotel_links, [("organization_id", 1), ("agency_id", 1), ("hotel_id", 1)], unique=True)

    # ── PMS / Source-based ────────────────────────────────────
    await _safe_create(db.rate_plans, [("organization_id", 1), ("source", 1)])
    await _safe_create(db.rate_periods, [("organization_id", 1), ("source", 1)])
    await _safe_create(db.inventory, [("organization_id", 1), ("source", 1)])
    await _safe_create(db.stop_sell_rules, [("organization_id", 1), ("source", 1)])
    await _safe_create(db.channel_allocations, [("organization_id", 1), ("source", 1)])

    # ── Audit logs ────────────────────────────────────────────
    await _safe_create(db.audit_logs, [("organization_id", 1), ("created_at", -1)])
    await _safe_create(db.audit_logs, [("organization_id", 1), ("target.type", 1), ("target.id", 1), ("created_at", -1)])

    # ── Booking events ────────────────────────────────────────
    await _safe_create(db.booking_events, [("organization_id", 1), ("delivered", 1), ("created_at", 1)])
    await _safe_create(db.booking_events, [("organization_id", 1), ("entity_id", 1), ("event_type", 1)])
    await _safe_create(db.booking_events, [("booking_id", 1), ("event_type", 1), ("payload.actor_email", 1)])

    # ── PMS mock ──────────────────────────────────────────────
    await _safe_create(db.pms_idempotency, [("organization_id", 1), ("idempotency_key", 1)], unique=True)
    await _safe_create(db.pms_bookings, [("organization_id", 1), ("hotel_id", 1), ("created_at", -1)])

    # ── Search cache (TTL) ────────────────────────────────────
    await _safe_create(db.search_cache, [("expires_at", 1)], expireAfterSeconds=0)
    await _safe_create(db.search_cache, [("organization_id", 1), ("agency_id", 1), ("created_at", -1)])

    # ── Vouchers (TTL) ────────────────────────────────────────
    await _safe_create(db.vouchers, [("expires_at", 1)], expireAfterSeconds=0)
    await _safe_create(db.vouchers, [("organization_id", 1), ("booking_id", 1)])
    await _safe_create(db.vouchers, [("token", 1)], unique=True)

    # ── Email outbox ──────────────────────────────────────────
    await _safe_create(db.email_outbox, [("status", 1), ("next_retry_at", 1)])
    await _safe_create(db.email_outbox, [("organization_id", 1), ("booking_id", 1)])

    # ── Hotel integrations ────────────────────────────────────
    await _safe_create(db.hotel_integrations, [("organization_id", 1), ("hotel_id", 1), ("kind", 1)], unique=True)
    await _safe_create(db.hotel_integrations, [("status", 1), ("provider", 1)])
    await _safe_create(db.hotel_integrations, [("organization_id", 1), ("kind", 1), ("updated_at", -1)])

    # ── Booking drafts (TTL) ──────────────────────────────────
    await _safe_create(db.booking_drafts, [("expires_at", 1)], expireAfterSeconds=0)
    await _safe_create(db.booking_drafts, [("organization_id", 1), ("created_at", -1)])
    await _safe_create(db.booking_drafts, [("submitted_booking_id", 1)])

    # ── Bookings ──────────────────────────────────────────────
    await _safe_create(db.bookings, [("organization_id", 1), ("status", 1), ("submitted_at", -1)])
    await _safe_create(db.bookings, [("agency_id", 1), ("status", 1), ("submitted_at", -1)])
    await _safe_create(db.bookings, [("hotel_id", 1), ("status", 1), ("submitted_at", -1)])
    await _safe_create(db.bookings, [("approval_deadline_at", 1)])
    await _safe_create(db.bookings, [("organization_id", 1), ("agency_id", 1), ("hotel_id", 1), ("status", 1), ("created_at", -1)])

    # ── Integration sync outbox ───────────────────────────────
    await _safe_create(db.integration_sync_outbox, [("status", 1), ("next_retry_at", 1)])
    await _safe_create(db.integration_sync_outbox, [("organization_id", 1), ("hotel_id", 1), ("kind", 1), ("created_at", -1)])

    # ── Booking financial entries ─────────────────────────────
    await _safe_create(db.booking_financial_entries, [("organization_id", 1), ("hotel_id", 1), ("month", 1), ("settlement_status", 1)])
    await _safe_create(db.booking_financial_entries, [("organization_id", 1), ("agency_id", 1), ("month", 1), ("settlement_status", 1)])
    await _safe_create(db.booking_financial_entries, [("organization_id", 1), ("booking_id", 1), ("type", 1)])

    # ── Match actions ─────────────────────────────────────────
    await _safe_create(db.match_actions, [("organization_id", 1), ("match_id", 1)], unique=True)
    await _safe_create(db.match_actions, [("organization_id", 1), ("status", 1), ("updated_at", -1)])

    # ── Action policies ───────────────────────────────────────
    await _safe_create(db.action_policies, [("organization_id", 1)], unique=True)

    # ── Pricing rules ─────────────────────────────────────────
    await _safe_create(db.pricing_rules, [("organization_id", 1), ("status", 1), ("priority", -1)])
    await _safe_create(db.pricing_rules, [("organization_id", 1), ("status", 1), ("scope.agency_id", 1), ("scope.product_id", 1), ("scope.product_type", 1)])
    await _safe_create(db.pricing_rules, [("organization_id", 1), ("validity.from", 1), ("validity.to", 1)])

    # ── Approval tasks ────────────────────────────────────────
    await _safe_create(db.approval_tasks, [("organization_id", 1), ("status", 1), ("requested_at", -1)])
    await _safe_create(db.approval_tasks, [("organization_id", 1), ("task_type", 1), ("status", 1)])
    await _safe_create(db.approval_tasks, [("organization_id", 1), ("target.match_id", 1)])

    # ── Risk snapshots ────────────────────────────────────────
    await _safe_create(db.risk_snapshots, [("organization_id", 1), ("snapshot_key", 1), ("generated_at", -1)])

    # ── Match alert policies & deliveries ─────────────────────
    await _safe_create(db.match_alert_policies, [("organization_id", 1)], unique=True)
    try:
        indexes = await db.match_alert_deliveries.index_information()
        for name, info in indexes.items():
            keys = info.get("key") or []
            if keys == [("organization_id", 1), ("match_id", 1), ("fingerprint", 1)]:
                await db.match_alert_deliveries.drop_index(name)
    except Exception:
        pass
    await _safe_create(db.match_alert_deliveries, [("organization_id", 1), ("match_id", 1), ("fingerprint", 1), ("channel", 1)], unique=True)
    await _safe_create(db.match_alert_deliveries, [("organization_id", 1), ("sent_at", -1)])

    # ── Booking outcomes ──────────────────────────────────────
    await _safe_create(db.booking_outcomes, [("organization_id", 1), ("booking_id", 1)], unique=True)
    await _safe_create(db.booking_outcomes, [("organization_id", 1), ("agency_id", 1), ("hotel_id", 1), ("checkin_date", -1)])

    # ── Risk profiles ─────────────────────────────────────────
    await _safe_create(db.risk_profiles, [("organization_id", 1)], unique=True)

    # ── Export policies & runs ────────────────────────────────
    await _safe_create(db.export_policies, [("organization_id", 1), ("key", 1)], unique=True)
    await _safe_create(db.export_runs, [("organization_id", 1), ("policy_key", 1), ("generated_at", -1)])
    await _safe_create(db.export_runs, [("organization_id", 1), ("download.token", 1)], unique=True, sparse=True)

    # ══════════════════════════════════════════════════════════
    # GTM + CRM (from server.py)
    # ══════════════════════════════════════════════════════════
    await _safe_create(db.demo_seed_runs, "tenant_id", unique=True)
    await _safe_create(db.rule_runs, [("tenant_id", 1), ("rule_key", 1), ("date", 1)], unique=True)
    await _safe_create(db.crm_deals, [("organization_id", 1), ("stage", 1)])
    await _safe_create(db.crm_deals, [("organization_id", 1), ("owner_user_id", 1)])
    await _safe_create(db.crm_tasks, [("organization_id", 1), ("owner_user_id", 1), ("status", 1)])
    await _safe_create(db.crm_tasks, [("organization_id", 1), ("due_date", 1)])
    await _safe_create(db.crm_notes, [("organization_id", 1), ("entity_type", 1), ("entity_id", 1)])
    await _safe_create(db.activation_checklist, "tenant_id", unique=True)
    await _safe_create(db.upgrade_requests, [("tenant_id", 1), ("status", 1)])

    # ══════════════════════════════════════════════════════════
    # IMPORT / SHEETS (from server.py)
    # ══════════════════════════════════════════════════════════
    await _safe_create(db.import_jobs, [("organization_id", 1), ("created_at", -1)])
    await _safe_create(db.import_errors, "job_id")
    await _safe_create(db.sheet_connections, [("organization_id", 1), ("status", 1)])
    await _safe_create(db.sheet_sync_runs, [("sheet_connection_id", 1), ("started_at", -1)])
    await _safe_create(db.sheet_row_fingerprints, [("tenant_id", 1), ("sheet_connection_id", 1), ("row_key", 1)], unique=True)
    await _safe_create(db.sheet_sync_locks, "tenant_id", unique=True)

    # ══════════════════════════════════════════════════════════
    # PORTFOLIO SYNC ENGINE (from server.py)
    # ══════════════════════════════════════════════════════════
    await _safe_create(db.hotel_portfolio_sources, [("tenant_id", 1), ("hotel_id", 1)], unique=True)
    await _safe_create(db.hotel_portfolio_sources, [("tenant_id", 1), ("sync_enabled", 1)])
    await _safe_create(db.hotel_portfolio_sources, [("tenant_id", 1), ("last_sync_at", 1)])
    await _safe_create(db.sheet_sync_runs, [("tenant_id", 1), ("hotel_id", 1), ("started_at", -1)])
    await _safe_create(db.sheet_sync_runs, [("tenant_id", 1), ("status", 1), ("started_at", -1)])
    await _safe_create(db.sheet_row_fingerprints, [("tenant_id", 1), ("hotel_id", 1), ("row_key", 1)], unique=True)
    await _safe_create(db.sheet_sync_locks, "lock_key", unique=True)
    await _safe_create(db.sheet_sync_locks, "expires_at", expireAfterSeconds=0)
    await _safe_create(db.hotel_inventory_snapshots, [("tenant_id", 1), ("hotel_id", 1), ("date", 1), ("room_type", 1)])
    await _safe_create(db.sheet_writeback_queue, [("tenant_id", 1), ("status", 1), ("created_at", 1)])
    await _safe_create(db.sheet_writeback_queue, [("tenant_id", 1), ("hotel_id", 1)])
    await _safe_create(db.sheet_writeback_markers, [("tenant_id", 1), ("source_id", 1), ("event_type", 1)], unique=True)
    await _safe_create(db.sheet_change_log, [("tenant_id", 1), ("hotel_id", 1), ("created_at", -1)])
    await _safe_create(db.sheet_change_log, "created_at", expireAfterSeconds=2592000)

    # ══════════════════════════════════════════════════════════
    # ENTERPRISE (from server.py)
    # ══════════════════════════════════════════════════════════
    await _safe_create(db.audit_logs_chain, [("tenant_id", 1), ("created_at", 1)])
    await _safe_create(db.audit_logs_chain, [("tenant_id", 1), ("_id", 1)])
    await _safe_create(db.approval_requests, [("organization_id", 1), ("status", 1)])
    await _safe_create(db.approval_requests, [("tenant_id", 1), ("status", 1)])
    await _safe_create(db.user_2fa, "user_id", unique=True)
    await _safe_create(db.rate_limits, "expires_at", expireAfterSeconds=0)
    await _safe_create(db.rate_limits, [("key", 1), ("created_at", 1)])
    await _safe_create(db.permissions, [("code", 1), ("organization_id", 1)], unique=True)
    await _safe_create(db.role_permissions, [("role", 1), ("organization_id", 1)], unique=True)
    await _safe_create(db.report_schedules, [("organization_id", 1)])
    await _safe_create(db.report_schedules, [("is_active", 1), ("next_run", 1)])

    # E-Fatura
    await _safe_create(db.efatura_invoices, [("tenant_id", 1), ("invoice_id", 1)], unique=True)
    await _safe_create(db.efatura_invoices, [("tenant_id", 1), ("status", 1)])
    await _safe_create(db.efatura_invoices, [("tenant_id", 1), ("source_type", 1), ("source_id", 1)])
    await _safe_create(db.efatura_invoices, [("idempotency_key", 1), ("tenant_id", 1)])
    await _safe_create(db.efatura_events, [("tenant_id", 1), ("invoice_id", 1), ("created_at", 1)])

    # SMS / Tickets
    await _safe_create(db.sms_logs, [("organization_id", 1), ("created_at", -1)])
    await _safe_create(db.tickets, [("tenant_id", 1), ("ticket_code", 1)], unique=True)
    await _safe_create(db.tickets, [("tenant_id", 1), ("reservation_id", 1)])
    await _safe_create(db.tickets, [("organization_id", 1), ("status", 1)])

    # Operational Excellence (O1-O5)
    await _safe_create(db.system_backups, [("created_at", -1)])
    await _safe_create(db.system_errors, [("signature", 1)], unique=True)
    await _safe_create(db.system_errors, [("last_seen", -1)])
    await _safe_create(db.system_errors, [("severity", 1)])
    await _safe_create(db.system_uptime, [("timestamp", -1)])
    await _safe_create(db.system_incidents, [("created_at", -1)])
    await _safe_create(db.system_incidents, [("severity", 1)])
    await _safe_create(db.request_logs, "timestamp", expireAfterSeconds=86400)
    await _safe_create(db.request_logs, [("timestamp", -1)])
    await _safe_create(db.request_logs, [("status_code", 1), ("timestamp", 1)])

    # Performance indexes (B2)
    try:
        from app.indexes.perf_indexes import ensure_perf_indexes
        await ensure_perf_indexes(db)
    except Exception:
        pass

    logger.info("All seed indexes ensured (defensive mode)")
