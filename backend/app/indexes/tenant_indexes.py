from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorDatabase


async def ensure_tenant_indexes(db: AsyncIOMotorDatabase) -> None:
    """Ensure indexes for tenants and related SaaS collections.

    - tenants.tenant_key unique (legacy)
    - tenants.slug unique (SaaS URL slug)
    - tenants.organization_id regular index
    - tenants.primary_domain regular index
    - tenants.subdomain regular index (for subdomain routing)
    - tenant_domains.domain unique
    - tenant_domains.tenant_id regular index
    - memberships (user_id, tenant_id) unique
    - subscriptions.org_id index
    - usage_logs (org_id, metric, ts) index
    """

    # Tenants
    await db.tenants.create_index("tenant_key", unique=True)
    await db.tenants.create_index("slug", unique=True)
    await db.tenants.create_index("organization_id")
    await db.tenants.create_index("primary_domain")
    await db.tenants.create_index("subdomain")

    # Tenant domains
    await db.tenant_domains.create_index("domain", unique=True)
    await db.tenant_domains.create_index("tenant_id")

    # Memberships
    await db.memberships.create_index([("user_id", 1), ("tenant_id", 1)], unique=True)

    # Subscriptions
    await db.subscriptions.create_index("org_id")

    # Usage logs
    await db.usage_logs.create_index([("org_id", 1), ("metric", 1), ("ts", 1)])
