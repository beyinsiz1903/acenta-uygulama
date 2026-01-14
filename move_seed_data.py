#!/usr/bin/env python3
"""
Move seed data to the admin user's organization for testing
"""

import asyncio
import sys

# Add backend to path for imports
sys.path.append('/app/backend')
from app.db import get_db


async def move_seed_data_to_admin_org():
    """Move seed data to the admin user's organization"""
    db = await get_db()
    
    # Find the admin user that's being used (the one in org 695e03c80b04ed31c4eaa899)
    admin_user = await db.users.find_one({"id": "696552a9f1cc0f5606f137e3"})
    if not admin_user:
        print("❌ Admin user not found")
        return
    
    admin_org = admin_user.get('organization_id')
    print(f"Admin user organization: {admin_org}")
    
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
    await move_seed_data_to_admin_org()


if __name__ == "__main__":
    asyncio.run(main())