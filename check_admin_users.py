#!/usr/bin/env python3
"""
Check all admin users and fix organization mismatch
"""

import asyncio
import sys

# Add backend to path for imports
sys.path.append('/app/backend')
from app.db import get_db


async def check_all_admin_users():
    """Check all users with admin email and fix organization"""
    db = await get_db()
    
    # Find all users with admin email
    admin_users = await db.users.find({"email": "admin@acenta.test"}).to_list(length=10)
    print(f"Found {len(admin_users)} admin users:")
    
    for i, user in enumerate(admin_users):
        user_id = user.get('id') or user.get('_id')
        org_id = user.get('organization_id')
        print(f"  {i+1}. ID: {user_id}, Org: {org_id}")
    
    # Find where seed data is
    seed_customer = await db.customers.find_one({"id": "cust_seed_linked"})
    if not seed_customer:
        print("❌ Seed data not found")
        return
    
    seed_org = seed_customer.get('organization_id')
    print(f"\nSeed data is in organization: {seed_org}")
    
    # Update ALL admin users to be in seed organization
    result = await db.users.update_many(
        {"email": "admin@acenta.test"},
        {"$set": {"organization_id": seed_org}}
    )
    
    print(f"Updated {result.modified_count} admin users to organization: {seed_org}")
    
    # Verify the update
    admin_users_after = await db.users.find({"email": "admin@acenta.test"}).to_list(length=10)
    print(f"\nAfter update:")
    for i, user in enumerate(admin_users_after):
        user_id = user.get('id') or user.get('_id')
        org_id = user.get('organization_id')
        print(f"  {i+1}. ID: {user_id}, Org: {org_id}")


async def main():
    await check_all_admin_users()


if __name__ == "__main__":
    asyncio.run(main())