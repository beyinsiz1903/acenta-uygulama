#!/usr/bin/env python3
"""Clean up test pricing rules before running tests"""

import asyncio
from app.db import connect_mongo, get_db, close_mongo

async def clean_test_rules():
    await connect_mongo()
    db = await get_db()
    
    # Find organization
    org = await db.organizations.find_one({})
    if not org:
        print("No organization found")
        return
        
    org_id = org.get("id") or str(org.get("_id"))
    print(f"Organization ID: {org_id}")
    
    # Delete all test rules
    result1 = await db.pricing_rules.delete_many({"organization_id": org_id, "notes": "test_p1_2"})
    result2 = await db.pricing_rules.delete_many({"organization_id": org_id, "notes": "test_p1_2_range"})
    
    print(f"Deleted {result1.deleted_count} rules with notes 'test_p1_2'")
    print(f"Deleted {result2.deleted_count} rules with notes 'test_p1_2_range'")
    
    # Show remaining active rules
    remaining = await db.pricing_rules.find({"organization_id": org_id, "status": "active"}).to_list(length=100)
    print(f"Remaining active rules: {len(remaining)}")
    for rule in remaining:
        print(f"  - Priority: {rule.get('priority')}, Scope: {rule.get('scope')}, Action: {rule.get('action')}, Notes: {rule.get('notes')}")
    
    await close_mongo()

if __name__ == "__main__":
    asyncio.run(clean_test_rules())