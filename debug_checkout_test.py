#!/usr/bin/env python3

import asyncio
import httpx
from datetime import date, timedelta

async def test_checkout_responses():
    """Debug the actual responses from checkout endpoints"""
    
    async with httpx.AsyncClient(base_url="https://hotel-marketplace-1.preview.emergentagent.com") as client:
        
        # Test 1: Create a quote first
        quote_payload = {
            "org": "org_debug_test",
            "product_id": "676b2e107a63a8c8fe88b751",  # Use a test product ID
            "date_from": date.today().isoformat(),
            "date_to": (date.today() + timedelta(days=1)).isoformat(),
            "pax": {"adults": 1, "children": 0},
            "rooms": 1,
            "currency": "EUR",
        }
        
        print("=== Testing Quote Creation ===")
        try:
            quote_resp = await client.post("/api/public/quote", json=quote_payload)
            print(f"Quote Status: {quote_resp.status_code}")
            print(f"Quote Response: {quote_resp.text}")
            
            if quote_resp.status_code == 200:
                quote_data = quote_resp.json()
                quote_id = quote_data.get("quote_id")
                
                if quote_id:
                    # Test 2: Try checkout with the quote
                    checkout_payload = {
                        "org": "org_debug_test",
                        "quote_id": quote_id,
                        "guest": {
                            "full_name": "Debug Test Guest",
                            "email": "debug@example.com",
                            "phone": "+905001112233",
                        },
                        "payment": {"method": "stripe"},
                        "idempotency_key": "debug-test-1",
                    }
                    
                    print("\n=== Testing Checkout ===")
                    checkout_resp = await client.post("/api/public/checkout", json=checkout_payload)
                    print(f"Checkout Status: {checkout_resp.status_code}")
                    print(f"Checkout Response: {checkout_resp.text}")
                    
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_checkout_responses())