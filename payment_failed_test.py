#!/usr/bin/env python3

import asyncio
import httpx
from datetime import date, timedelta

async def test_payment_failed_standardization():
    """Test the PAYMENT_FAILED error standardization for public checkout"""
    
    base_url = "https://resflow-polish.preview.emergentagent.com"
    
    async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
        
        print("=== Testing PAYMENT_FAILED Standardization ===")
        
        # Test the existing provider_unavailable behavior first
        # This should return 502 with PAYMENT_FAILED error code
        checkout_payload = {
            "org": "test_org_payment_failed",
            "quote_id": "qt_nonexistent_test_123",  # Non-existent quote to trigger error
            "guest": {
                "full_name": "Test Payment Failed Guest",
                "email": "test@example.com",
                "phone": "+905001112233",
            },
            "payment": {"method": "stripe"},
            "idempotency_key": "test-payment-failed-1",
        }
        
        try:
            print("Testing checkout with non-existent quote (should trigger PAYMENT_FAILED)...")
            resp = await client.post("/api/public/checkout", json=checkout_payload)
            print(f"Status Code: {resp.status_code}")
            print(f"Response: {resp.text}")
            
            if resp.status_code == 502:
                data = resp.json()
                error = data.get("error", {})
                print(f"✅ Correct status code: 502")
                print(f"Error code: {error.get('code')}")
                print(f"Error message: {error.get('message')}")
                
                details = error.get("details", {})
                correlation_id = details.get("correlation_id")
                print(f"Correlation ID: {correlation_id}")
                
                if error.get("code") == "PAYMENT_FAILED":
                    print("✅ PAYMENT_FAILED error code confirmed")
                else:
                    print(f"❌ Expected PAYMENT_FAILED, got: {error.get('code')}")
                    
                if correlation_id and isinstance(correlation_id, str) and correlation_id.strip():
                    print("✅ Non-empty correlation_id confirmed")
                else:
                    print(f"❌ Invalid correlation_id: {correlation_id}")
                    
            elif resp.status_code == 404:
                data = resp.json()
                error = data.get("error", {})
                print(f"Got 404 with error code: {error.get('code')}")
                if error.get("code") == "QUOTE_NOT_FOUND":
                    print("✅ This is expected for non-existent quote")
                    
            else:
                print(f"❌ Unexpected status code: {resp.status_code}")
                
        except Exception as e:
            print(f"Error during test: {e}")
            
        print("\n=== Testing Provider Unavailable Scenario ===")
        
        # Test with a real quote but expect provider unavailable
        # First try to create a quote
        quote_payload = {
            "org": "test_org_provider_unavailable", 
            "product_id": "test_product_123",
            "date_from": date.today().isoformat(),
            "date_to": (date.today() + timedelta(days=1)).isoformat(),
            "pax": {"adults": 1, "children": 0},
            "rooms": 1,
            "currency": "EUR",
        }
        
        try:
            print("Attempting to create quote...")
            quote_resp = await client.post("/api/public/quote", json=quote_payload)
            print(f"Quote Status: {quote_resp.status_code}")
            
            if quote_resp.status_code == 200:
                quote_data = quote_resp.json()
                quote_id = quote_data.get("quote_id")
                
                # Now test checkout with this quote
                checkout_payload_real = {
                    "org": "test_org_provider_unavailable",
                    "quote_id": quote_id,
                    "guest": {
                        "full_name": "Provider Unavailable Guest",
                        "email": "provunav@example.com",
                        "phone": "+905009998877",
                    },
                    "payment": {"method": "stripe"},
                    "idempotency_key": "test-prov-unav-1",
                }
                
                checkout_resp = await client.post("/api/public/checkout", json=checkout_payload_real)
                print(f"Checkout Status: {checkout_resp.status_code}")
                print(f"Checkout Response: {checkout_resp.text}")
                
                if checkout_resp.status_code == 200:
                    data = checkout_resp.json()
                    if data.get("ok") is False and data.get("reason") == "provider_unavailable":
                        print("✅ Provider unavailable scenario working correctly (200 + ok=false)")
                    else:
                        print(f"❌ Unexpected response structure: {data}")
                elif checkout_resp.status_code == 502:
                    data = checkout_resp.json()
                    error = data.get("error", {})
                    if error.get("code") == "PAYMENT_FAILED":
                        print("✅ PAYMENT_FAILED standardization working correctly (502)")
                    else:
                        print(f"❌ Unexpected error code: {error.get('code')}")
                        
            else:
                print(f"Quote creation failed: {quote_resp.text}")
                
        except Exception as e:
            print(f"Error during provider unavailable test: {e}")

if __name__ == "__main__":
    asyncio.run(test_payment_failed_standardization())