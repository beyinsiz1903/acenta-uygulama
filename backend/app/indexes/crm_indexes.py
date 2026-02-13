from __future__ import annotations

from pymongo import ASCENDING, DESCENDING


async def ensure_crm_indexes(db):
    """Ensure indexes for CRM-related collections (customers, deals, tasks, activities).

    Called from seed/startup alongside other index initializers.
    """

    import logging

    logger = logging.getLogger(__name__)

    async def _safe_create(collection, keys, **kwargs):
        name = kwargs.get("name")
        try:
            await collection.create_index(keys, **kwargs)
        except Exception as exc:
            logger.warning("Failed to ensure index %s on %s: %s", name, collection.name, exc)

    # customers
    await _safe_create(
        db.customers,
        [("organization_id", ASCENDING), ("name", ASCENDING)],
        name="crm_customers_by_org_name",
    )

    await _safe_create(
        db.customers,
        [("organization_id", ASCENDING), ("tags", ASCENDING)],
        name="crm_customers_by_org_tags",
    )

    # Unique-ish index for contact values per org and type (email/phone).
    # NOTE: partialFilterExpression with $ne is not supported in all MongoDB versions.
    # Using $exists only as a safer alternative.
    await _safe_create(
        db.customers,
        [
            ("organization_id", ASCENDING),
            ("contacts.type", ASCENDING),
            ("contacts.value", ASCENDING),
        ],
        name="crm_customers_by_org_contact",
        partialFilterExpression={"contacts": {"$exists": True}},
    )

    # future CRM collections (deals, tasks, activities) - prepared for next PRs
    await _safe_create(
        db.crm_deals,
        [("organization_id", ASCENDING), ("status", ASCENDING), ("stage", ASCENDING), ("owner_user_id", ASCENDING)],
        name="crm_deals_by_org_status_stage_owner",
    )

    await _safe_create(
        db.crm_deals,
        [("organization_id", ASCENDING), ("customer_id", ASCENDING), ("status", ASCENDING), ("updated_at", DESCENDING)],
        name="crm_deals_by_org_customer_status_updated",
    )

    await _safe_create(
        db.crm_tasks,
        [
            ("organization_id", ASCENDING),
            ("owner_user_id", ASCENDING),
            ("status", ASCENDING),
            ("due_date", ASCENDING),
        ],
        name="crm_tasks_by_org_owner_status_due",
    )

    await _safe_create(
        db.crm_tasks,
        [
            ("organization_id", ASCENDING),
            ("related_type", ASCENDING),
            ("related_id", ASCENDING),
            ("status", ASCENDING),
        ],
        name="crm_tasks_by_org_related_status",
    )

    await _safe_create(
        db.crm_activities,
        [
            ("organization_id", ASCENDING),
            ("related_type", ASCENDING),
            ("related_id", ASCENDING),
            ("created_at", DESCENDING),
        ],
        name="crm_activities_by_org_related_created",
    )

    # crm_events collection for audit logging
    await _safe_create(
        db.crm_events,
        [("organization_id", ASCENDING), ("created_at", DESCENDING)],
        name="crm_events_by_org_created",
    )

    await _safe_create(
        db.crm_events,
        [
            ("organization_id", ASCENDING),
            ("entity_type", ASCENDING),
            ("entity_id", ASCENDING),
            ("created_at", DESCENDING),
        ],
        name="crm_events_by_org_entity_created",
    )
