from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorDatabase


async def ensure_tenant_indexes(db: AsyncIOMotorDatabase) -> None:
    """Ensure indexes for tenants and tenant_domains collections.

    - tenants.tenant_key unique
    - tenants.organization_id regular index
    - tenants.primary_domain regular index
    - tenants.subdomain regular index (for subdomain routing)
    - tenant_domains.domain unique
    - tenant_domains.tenant_id regular index
    """

    await db.tenants.create_index("tenant_key", unique=True)
    await db.tenants.create_index("organization_id")
    await db.tenants.create_index("primary_domain")
    await db.tenants.create_index("subdomain")

    await db.tenant_domains.create_index("domain", unique=True)
    await db.tenant_domains.create_index("tenant_id")
