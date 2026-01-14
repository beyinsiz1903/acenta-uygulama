#!/usr/bin/env python3
"""
Focused test for unique index behavior
"""

import asyncio
import sys
from datetime import datetime
from pymongo.errors import DuplicateKeyError

sys.path.append('/app/backend')

from app.db import connect_mongo, get_db
from app.services.crm_customers import create_customer

TEST_ORG_ID = "695e03c80b04ed31c4eaa899"

async def test_unique_constraint():
    await connect_mongo()
    db = await get_db()
    
    test_email = "unique.constraint.test@example.com"
    
    # Clean up any existing test data
    await db.customers.delete_many({
        "organization_id": TEST_ORG_ID,
        "contacts.value": test_email
    })
    
    print("Testing unique constraint behavior...")
    
    # Create first customer
    customer_data_1 = {
        "type": "individual",
        "name": "Unique Test Customer 1",
        "contacts": [
            {"type": "email", "value": test_email, "is_primary": True}
        ]
    }
    
    try:
        customer_1 = await create_customer(db, TEST_ORG_ID, "system", customer_data_1)
        print(f"✅ Created first customer: {customer_1['id']}")
        
        # Check what was actually stored
        stored_customer = await db.customers.find_one({"id": customer_1["id"]})
        print(f"   Stored contacts: {stored_customer['contacts']}")
        
    except Exception as e:
        print(f"❌ Failed to create first customer: {e}")
        return
    
    # Try to create second customer with same email
    customer_data_2 = {
        "type": "individual",
        "name": "Unique Test Customer 2", 
        "contacts": [
            {"type": "email", "value": test_email, "is_primary": True}
        ]
    }
    
    try:
        customer_2 = await create_customer(db, TEST_ORG_ID, "system", customer_data_2)
        print(f"⚠️ Created second customer unexpectedly: {customer_2['id']}")
        
        # Check what was stored
        stored_customer_2 = await db.customers.find_one({"id": customer_2["id"]})
        print(f"   Stored contacts: {stored_customer_2['contacts']}")
        
    except DuplicateKeyError as e:
        print(f"✅ DuplicateKeyError caught as expected: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    
    # Check how many customers exist with this email
    count = await db.customers.count_documents({
        "organization_id": TEST_ORG_ID,
        "contacts.value": test_email
    })
    print(f"Total customers with {test_email}: {count}")
    
    # Try direct MongoDB insert to test index
    print("\nTesting direct MongoDB insert...")
    try:
        await db.customers.insert_one({
            "id": "test_direct_insert",
            "organization_id": TEST_ORG_ID,
            "type": "individual",
            "name": "Direct Insert Test",
            "contacts": [
                {"type": "email", "value": test_email, "is_primary": True}
            ],
            "tags": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        })
        print("⚠️ Direct insert succeeded unexpectedly")
    except DuplicateKeyError as e:
        print(f"✅ Direct insert failed with DuplicateKeyError: {e}")
    except Exception as e:
        print(f"❌ Direct insert failed with unexpected error: {e}")
    
    # Clean up
    await db.customers.delete_many({
        "organization_id": TEST_ORG_ID,
        "contacts.value": test_email
    })
    await db.customers.delete_many({
        "id": "test_direct_insert"
    })

if __name__ == "__main__":
    asyncio.run(test_unique_constraint())