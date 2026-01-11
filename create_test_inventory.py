#!/usr/bin/env python3
"""
Create test inventory for FAZ 5 testing
"""

import asyncio
import sys
from datetime import datetime, date
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

from bson import ObjectId
from app.db import connect_mongo, get_db

async def create_test_inventory():
    """Create inventory for test dates"""
    
    # Connect to database
    await connect_mongo()
    db = await get_db()
    
    # Organization and product info
    org_id = "695e03c80b04ed31c4eaa899"  # From agency login
    product_id = ObjectId("695eae3c4a23404286091033")  # From search results
    
    # Test dates
    test_dates = ["2026-01-15", "2026-01-16", "2026-01-17"]
    
    for test_date in test_dates:
        # Check if inventory already exists
        existing = await db.inventory.find_one({
            "organization_id": org_id,
            "product_id": product_id,
            "date": test_date
        })
        
        if existing:
            print(f"📋 Inventory already exists for {test_date}")
            continue
        
        # Create inventory
        inventory_doc = {
            "organization_id": org_id,
            "product_id": product_id,
            "date": test_date,
            "capacity_available": 10,
            "price": 100.0,
            "restrictions": {
                "closed": False,
                "min_stay": 1,
                "max_stay": 30
            },
            "created_at": datetime.utcnow()
        }
        
        result = await db.inventory.insert_one(inventory_doc)
        print(f"✅ Inventory created for {test_date}: {result.inserted_id}")
    
    print(f"✅ Test inventory setup complete")

if __name__ == "__main__":
    asyncio.run(create_test_inventory())