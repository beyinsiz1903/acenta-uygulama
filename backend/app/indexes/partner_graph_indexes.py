from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorDatabase


async def ensure_partner_graph_indexes(db: AsyncIOMotorDatabase) -> None:
    # partner_relationships: unique per seller/buyer pair
    await db.partner_relationships.create_index(
        [("seller_tenant_id", 1), ("buyer_tenant_id", 1)], unique=True
    )

    # inventory_shares
    await db.inventory_shares.create_index([("seller_tenant_id", 1), ("buyer_tenant_id", 1)])
    await db.inventory_shares.create_index([("seller_tenant_id", 1), ("product_id", 1)])
    await db.inventory_shares.create_index([("seller_tenant_id", 1), ("tag", 1)])

    # commission_rules
    await db.commission_rules.create_index([("seller_tenant_id", 1)])
    await db.commission_rules.create_index([("seller_tenant_id", 1), ("buyer_tenant_id", 1)])

    # settlement_ledger
    await db.settlement_ledger.create_index("booking_id", unique=True)
    await db.settlement_ledger.create_index("seller_tenant_id")
    await db.settlement_ledger.create_index("buyer_tenant_id")
    await db.settlement_ledger.create_index("status")
