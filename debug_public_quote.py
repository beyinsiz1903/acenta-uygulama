#!/usr/bin/env python3
"""
Debug version of the public checkout test to see what's happening
"""

import asyncio
import sys
from pathlib import Path
from datetime import date, timedelta
import uuid
from motor.motor_asyncio import AsyncIOMotorClient
import os

# Add backend to path
ROOT_DIR = Path(__file__).resolve().parent / "backend"
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from server import app
import httpx
from httpx import ASGITransport
from app.db import get_db
from app.utils import now_utc

async def debug_public_quote_test():
    """Debug version of test_public_quote_happy_path"""
    
    # Create a test database like pytest does
    MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    client = AsyncIOMotorClient(MONGO_URL)
    db_name = f"agentis_test_{uuid.uuid4().hex}"
    test_db = client[db_name]
    
    # Override the get_db dependency like pytest does
    async def override_get_db():
        yield test_db
    
    app.dependency_overrides[get_db] = override_get_db
    
    try:
        print(f"Test database: {test_db}")
        
        # Clean up collections
        await test_db.products.delete_many({})
        await test_db.product_versions.delete_many({})
        await test_db.rate_plans.delete_many({})
        await test_db.public_quotes.delete_many({})
        
        org = "org_public_quote"
        now = now_utc()
        
        # Create test data
        prod = {
            "organization_id": org,
            "type": "hotel",
            "code": "HTL-Q1",
            "name": {"tr": "Quote Oteli"},
            "name_search": "quote oteli",
            "status": "active",
            "default_currency": "EUR",
            "location": {"city": "Izmir", "country": "TR"},
            "created_at": now,
            "updated_at": now,
        }
        res = await test_db.products.insert_one(prod)
        pid = res.inserted_id
        print(f"Created product with ID: {pid}")
        
        await test_db.product_versions.insert_one(
            {
                "organization_id": org,
                "product_id": pid,
                "version": 1,
                "status": "published",
                "content": {"description": {"tr": "Test"}},
            }
        )
        print("Created product version")
        
        await test_db.rate_plans.insert_one(
            {
                "organization_id": org,
                "product_id": pid,
                "code": "RP-Q1",
                "currency": "EUR",
                "base_net_price": 100.0,
                "status": "active",
            }
        )
        print("Created rate plan")
        
        # Prepare payload
        payload = {
            "org": org,
            "product_id": str(pid),
            "date_from": date.today().isoformat(),
            "date_to": (date.today() + timedelta(days=3)).isoformat(),
            "pax": {"adults": 2, "children": 0},
            "rooms": 1,
            "currency": "EUR",
        }
        print(f"Payload: {payload}")
        
        # Test with ASGI transport (like pytest does)
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test", timeout=30.0) as client:
            
            # Make the request
            resp = await client.post("/api/public/quote", json=payload)
            print(f"Response status: {resp.status_code}")
            print(f"Response text: {resp.text}")
            
            if resp.status_code == 200:
                data = resp.json()
                print(f"Success! Quote ID: {data.get('quote_id')}")
                print(f"Amount: {data.get('amount_cents')} {data.get('currency')}")
            else:
                print("Failed!")
                
    finally:
        # Clean up
        app.dependency_overrides.clear()
        await client.drop_database(db_name)
        client.close()

if __name__ == "__main__":
    asyncio.run(debug_public_quote_test())