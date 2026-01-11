#!/usr/bin/env python3
"""
Create test coupon for FAZ 5 testing
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

from app.db import connect_mongo, get_db

async def create_test_coupon():
    """Create TEST10 coupon for FAZ 5 testing"""
    
    # Connect to database
    await connect_mongo()
    db = await get_db()
    
    # Organization ID for org_demo (from seed data)
    org_id = "org_demo"
    
    # Check if coupon already exists
    existing = await db.coupons.find_one({
        "organization_id": org_id,
        "code": "TEST10"
    })
    
    if existing:
        print(f"✅ TEST10 coupon already exists: {existing['_id']}")
        return str(existing["_id"])
    
    # Create new coupon
    now = datetime.utcnow()
    coupon_doc = {
        "organization_id": org_id,
        "code": "TEST10",
        "discount_type": "PERCENT",
        "value": 10,
        "scope": "B2B",
        "active": True,
        "usage_limit": 10,
        "usage_count": 0,
        "valid_from": now - timedelta(days=1),
        "valid_to": now + timedelta(days=30),
        "min_total": 0.0,
        "currency": "EUR",
        "created_at": now,
        "created_by": "test_script"
    }
    
    result = await db.coupons.insert_one(coupon_doc)
    coupon_id = str(result.inserted_id)
    
    print(f"✅ TEST10 coupon created: {coupon_id}")
    print(f"📋 Organization: {org_id}")
    print(f"📋 Code: TEST10")
    print(f"📋 Discount: 10% (PERCENT)")
    print(f"📋 Scope: B2B")
    print(f"📋 Active: True")
    print(f"📋 Usage: 0/10")
    
    return coupon_id

if __name__ == "__main__":
    asyncio.run(create_test_coupon())