#!/usr/bin/env python3
"""
Fix seed data customer types to match API schema
"""

import asyncio
import sys

# Add backend to path for imports
sys.path.append('/app/backend')
from app.db import get_db


async def fix_customer_types():
    """Fix customer types from 'person' to 'individual'"""
    db = await get_db()
    
    # Update seed customers to use 'individual' instead of 'person'
    result = await db.customers.update_many(
        {"id": {"$in": ["cust_seed_linked", "cust_seed_unlinked"]}, "type": "person"},
        {"$set": {"type": "individual"}}
    )
    
    print(f"Updated {result.modified_count} customers from 'person' to 'individual'")
    
    # Verify the fix
    linked_customer = await db.customers.find_one({"id": "cust_seed_linked"})
    unlinked_customer = await db.customers.find_one({"id": "cust_seed_unlinked"})
    
    if linked_customer:
        print(f"cust_seed_linked type: {linked_customer.get('type')}")
    if unlinked_customer:
        print(f"cust_seed_unlinked type: {unlinked_customer.get('type')}")


async def main():
    await fix_customer_types()


if __name__ == "__main__":
    asyncio.run(main())