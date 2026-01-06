from __future__ import annotations

from pymongo import ASCENDING, DESCENDING


async def ensure_catalog_indexes(db):
    # products - make unique index partial to allow null codes from existing seed data
    await db.products.create_index(
        [("organization_id", ASCENDING), ("code", ASCENDING)],
        unique=True,
        name="uniq_product_code_per_org",
        partialFilterExpression={"code": {"$ne": None}}
    )
    await db.products.create_index(
        [("organization_id", ASCENDING), ("type", ASCENDING), ("status", ASCENDING), ("created_at", DESCENDING)],
        name="products_list",
    )
    await db.products.create_index(
        [("organization_id", ASCENDING), ("name_search", ASCENDING)],
        name="products_name_search",
    )

    # product_versions
    await db.product_versions.create_index(
        [("organization_id", ASCENDING), ("product_id", ASCENDING), ("version", DESCENDING)],
        name="pver_by_product_version",
    )
    await db.product_versions.create_index(
        [("organization_id", ASCENDING), ("product_id", ASCENDING), ("status", ASCENDING)],
        name="pver_by_product_status",
    )
    await db.product_versions.create_index(
        [("organization_id", ASCENDING), ("product_id", ASCENDING), ("published_at", DESCENDING)],
        name="pver_published_at",
    )

    # room_types
    await db.room_types.create_index(
        [("organization_id", ASCENDING), ("product_id", ASCENDING), ("code", ASCENDING)],
        unique=True,
        name="uniq_roomtype_code_per_product",
    )

    # rate_plans
    await db.rate_plans.create_index(
        [("organization_id", ASCENDING), ("product_id", ASCENDING), ("code", ASCENDING)],
        unique=True,
        name="uniq_rateplan_code_per_product",
    )

    # cancellation_policies
    await db.cancellation_policies.create_index(
        [("organization_id", ASCENDING), ("code", ASCENDING)],
        unique=True,
        name="uniq_cancel_policy_code_per_org",
    )

    # audit_logs (extra entity-centric index)
    await db.audit_logs.create_index(
        [
            ("organization_id", ASCENDING),
            ("target.type", ASCENDING),
            ("target.id", ASCENDING),
            ("created_at", DESCENDING),
        ],
        name="audit_by_entity",
    )
