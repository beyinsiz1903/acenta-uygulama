#!/usr/bin/env python3

import asyncio
import sys
import os

# Add the backend directory to Python path
sys.path.insert(0, '/app/backend')

from datetime import date, timedelta
import pytest
from app.db import get_db
from app.utils import now_utc

async def test_payment_failed_only():
    """Test only the PAYMENT_FAILED error standardization part"""
    
    # Import test client setup
    from httpx import AsyncClient
    from app.main import app
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Get test database
        from motor.motor_asyncio import AsyncIOMotorClient
        mongo_client = AsyncIOMotorClient("mongodb://localhost:27017")
        db = mongo_client.agentis_test_payment_failed
        
        # Clean up
        await db.products.delete_many({})
        await db.product_versions.delete_many({})
        await db.rate_plans.delete_many({})
        await db.public_quotes.delete_many({})
        await db.public_checkouts.delete_many({})
        await db.bookings.delete_many({})

        org = "org_public_payment_failed"
        now = now_utc()

        # Create a simple product + rate plan
        prod = {
            "organization_id": org,
            "type": "hotel",
            "code": "HTL-PF-1",
            "name": {"tr": "Payment Failed Oteli"},
            "name_search": "payment failed oteli",
            "status": "active",
            "default_currency": "EUR",
            "location": {"city": "Izmir", "country": "TR"},
            "created_at": now,
            "updated_at": now,
        }
        res = await db.products.insert_one(prod)
        pid = res.inserted_id

        await db.product_versions.insert_one(
            {
                "organization_id": org,
                "product_id": pid,
                "version": 1,
                "status": "published",
                "content": {"description": {"tr": "Test"}},
            }
        )

        await db.rate_plans.insert_one(
            {
                "organization_id": org,
                "product_id": pid,
                "code": "RP-PF-1",
                "currency": "EUR",
                "base_net_price": 100.0,
                "status": "active",
            }
        )

        # 1) Create quote
        quote_payload = {
            "org": org,
            "product_id": str(pid),
            "date_from": date.today().isoformat(),
            "date_to": (date.today() + timedelta(days=1)).isoformat(),
            "pax": {"adults": 1, "children": 0},
            "rooms": 1,
            "currency": "EUR",
        }

        quote_resp = await client.post("/api/public/quote", json=quote_payload)
        print(f"Quote response status: {quote_resp.status_code}")
        print(f"Quote response: {quote_resp.text}")
        
        if quote_resp.status_code != 200:
            print("❌ Quote creation failed")
            return
            
        quote_data = quote_resp.json()
        quote_id = quote_data["quote_id"]

        # 2) Mock stripe adapter to fail
        from unittest.mock import patch
        
        async def failing_create_payment_intent(*args, **kwargs):
            raise RuntimeError("stripe down")

        # 3) Test checkout with mocked failure
        checkout_payload = {
            "org": org,
            "quote_id": quote_id,
            "guest": {
                "full_name": "Payment Failed Guest",
                "email": "pf@example.com",
                "phone": "+905001112233",
            },
            "payment": {"method": "stripe"},
            "idempotency_key": "idem-payment-failed-1",
        }

        with patch('app.services.stripe_adapter.create_payment_intent', side_effect=failing_create_payment_intent):
            resp = await client.post("/api/public/checkout", json=checkout_payload)
            print(f"Checkout response status: {resp.status_code}")
            print(f"Checkout response: {resp.text}")
            
            if resp.status_code == 502:
                data = resp.json()
                error = data.get("error", {})
                
                print(f"✅ Correct status code: 502")
                print(f"Error code: {error.get('code')}")
                
                if error.get("code") == "PAYMENT_FAILED":
                    print("✅ PAYMENT_FAILED error code confirmed")
                else:
                    print(f"❌ Expected PAYMENT_FAILED, got: {error.get('code')}")
                    
                details = error.get("details", {})
                correlation_id = details.get("correlation_id")
                
                if correlation_id and isinstance(correlation_id, str) and correlation_id.strip():
                    print("✅ Non-empty correlation_id confirmed")
                else:
                    print(f"❌ Invalid correlation_id: {correlation_id}")
                    
                # Check database state
                booking_count = await db.bookings.count_documents({"organization_id": org})
                print(f"Booking count after failure: {booking_count}")
                
                if booking_count == 0:
                    print("✅ No orphan bookings created")
                else:
                    print(f"❌ Found {booking_count} orphan bookings")
                    
                doc = await db.public_checkouts.find_one({"organization_id": org, "idempotency_key": "idem-payment-failed-1"})
                if doc:
                    print(f"Public checkout record: ok={doc.get('ok')}, reason={doc.get('reason')}")
                    if doc.get("ok") is False and doc.get("reason") == "provider_unavailable":
                        print("✅ Public checkout record correctly marked as failed")
                    else:
                        print("❌ Public checkout record has incorrect state")
                else:
                    print("❌ No public checkout record found")
                    
            else:
                print(f"❌ Expected 502, got {resp.status_code}")
                
        # Clean up
        await mongo_client.close()

if __name__ == "__main__":
    asyncio.run(test_payment_failed_only())