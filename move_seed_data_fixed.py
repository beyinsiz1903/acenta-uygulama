#!/usr/bin/env python3
"""
Find the correct admin user and move seed data
"""

import asyncio
import sys

# Add backend to path for imports
sys.path.append('/app/backend')
from app.db import get_db


async def find_and_move_seed_data():
    """Find the correct admin user and move seed data"""
    db = await get_db()
    
    # Find admin user in org 695e03c80b04ed31c4eaa899 (from JWT token)
    target_org = "695e03c80b04ed31c4eaa899"
    admin_user = await db.users.find_one({"email": "admin@acenta.test", "organization_id": target_org})
    
    if not admin_user:
        print(f"❌ Admin user not found in organization {target_org}")
        # List all admin users
        all_admins = await db.users.find({"email": "admin@acenta.test"}).to_list(length=10)
        print("Available admin users:")
        for admin in all_admins:
            user_id = admin.get('id') or admin.get('_id')
            org_id = admin.get('organization_id')
            print(f"  ID: {user_id}, Org: {org_id}")
        return
    
    admin_org = admin_user.get('organization_id')
    print(f"Found admin user in organization: {admin_org}")
    
    # Check current seed data location
    seed_customer = await db.customers.find_one({"id": "cust_seed_linked"})
    if not seed_customer:
        print("❌ Seed data not found")
        return
    
    current_seed_org = seed_customer.get('organization_id')
    print(f"Current seed data organization: {current_seed_org}")
    
    if admin_org == current_seed_org:
        print("✅ Seed data is already in admin's organization")
        return
    
    print(f"Moving seed data from {current_seed_org} to {admin_org}...")
    
    # Update customers
    customers_result = await db.customers.update_many(
        {"organization_id": current_seed_org, "id": {"$in": ["cust_seed_linked", "cust_seed_unlinked"]}},
        {"$set": {"organization_id": admin_org}}
    )
    print(f"Updated {customers_result.modified_count} customers")
    
    # Update bookings
    bookings_result = await db.bookings.update_many(
        {"organization_id": current_seed_org, "booking_id": {"$in": ["BKG-SEED-LINKED", "BKG-SEED-UNLINKED"]}},
        {"$set": {"organization_id": admin_org}}
    )
    print(f"Updated {bookings_result.modified_count} bookings")
    
    # Update deals
    deals_result = await db.crm_deals.update_many(
        {"organization_id": current_seed_org, "id": "deal_seed_1"},
        {"$set": {"organization_id": admin_org}}
    )
    print(f"Updated {deals_result.modified_count} deals")
    
    # Update tasks
    tasks_result = await db.crm_tasks.update_many(
        {"organization_id": current_seed_org, "id": "task_seed_1"},
        {"$set": {"organization_id": admin_org}}
    )
    print(f"Updated {tasks_result.modified_count} tasks")
    
    print("✅ Seed data moved successfully")


async def main():
    await find_and_move_seed_data()


if __name__ == "__main__":
    asyncio.run(main())