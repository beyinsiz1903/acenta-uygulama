from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorDatabase


async def ensure_storefront_indexes(db: AsyncIOMotorDatabase) -> None:
    """Ensure indexes for storefront customers and sessions.

    - storefront_customers: (tenant_id, email) unique, tenant_id index
    - storefront_sessions: search_id unique, expires_at TTL
    """

    await db.storefront_customers.create_index(
        [("tenant_id", 1), ("email", 1)], unique=True
    )
    await db.storefront_customers.create_index("tenant_id")

    await db.storefront_sessions.create_index("search_id", unique=True)
    # TTL index: documents expire when expires_at < now
    await db.storefront_sessions.create_index("expires_at", expireAfterSeconds=0)
