#!/usr/bin/env python3
"""
Fix admin user organization to match seeded data
"""

import asyncio
import sys

# Add backend to path for imports
sys.path.append('/app/backend')
from app.db import get_db


async def fix_admin_user_org():
    """Update admin user to be in the same org as seeded data"""
    db = await get_db()
    
    # Check current admin user
    admin_user = await db.users.find_one({"email": "admin@acenta.test"})
    if not admin_user:
        print("Admin user not found")
        return
    
    current_org = admin_user.get('organization_id')
    print(f"Current admin org: {current_org}")
    
    # Check if seed data exists in current org
    seed_customers = await db.customers.count_documents({
        "organization_id": current_org,
        "id": {"$in": ["cust_seed_linked", "cust_seed_unlinked"]}
    })
    
    print(f"Seed customers in current org: {seed_customers}")
    
    if seed_customers == 2:
        print("✅ Admin user is already in the correct organization with seed data")
        return
    
    # Find where the seed data actually is
    seed_customer = await db.customers.find_one({"id": "cust_seed_linked"})
    if not seed_customer:
        print("❌ Seed data not found anywhere")
        return
    
    seed_org = seed_customer.get('organization_id')
    print(f"Seed data is in organization: {seed_org}")
    
    # Update admin user to be in the seed organization
    result = await db.users.update_one(
        {"email": "admin@acenta.test"},
        {"$set": {"organization_id": seed_org}}
    )
    
    if result.modified_count > 0:
        print(f"✅ Updated admin user to organization: {seed_org}")
    else:
        print("❌ Failed to update admin user organization")


async def main():
    await fix_admin_user_org()


if __name__ == "__main__":
    asyncio.run(main())