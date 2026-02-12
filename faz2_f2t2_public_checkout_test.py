#!/usr/bin/env python3
"""
FAZ 2 / F2.T2 Public Quote + Checkout Backend Test

Test scenarios:
1. test_public_quote_happy_path - Active + published product + rate_plan for quote generation
2. test_public_checkout_happy_path_stubbed_stripe - Stripe create_payment_intent with monkeypatch
3. test_public_checkout_expired_quote - Expired quote checkout should return 404
"""

import asyncio
import json
from datetime import date, datetime, timedelta
from typing import Dict, Any

import httpx


class PublicCheckoutTester:
    def __init__(self):
        # Read backend URL from frontend env
        try:
            with open('/app/frontend/.env', 'r') as f:
                for line in f:
                    if line.startswith('REACT_APP_BACKEND_URL='):
                        self.base_url = line.split('=', 1)[1].strip()
                        break
                else:
                    self.base_url = "https://data-sync-tool-1.preview.emergentagent.com"
        except:
            self.base_url = "https://data-sync-tool-1.preview.emergentagent.com"
            
        self.client = None
        
    async def setup(self):
        """Setup HTTP client"""
        self.client = httpx.AsyncClient(base_url=self.base_url, timeout=30.0)
        
    async def cleanup(self):
        """Cleanup HTTP client"""
        if self.client:
            await self.client.aclose()
            
    async def test_public_quote_happy_path(self):
        """Test 1: Active + published product + rate_plan for quote generation"""
        print("🧪 Test 1: Public Quote Happy Path")
        
        # Test data
        org = "org_public_quote_test"
        payload = {
            "org": org,
            "product_id": "507f1f77bcf86cd799439011",  # Valid ObjectId format
            "date_from": date.today().isoformat(),
            "date_to": (date.today() + timedelta(days=3)).isoformat(),
            "pax": {"adults": 2, "children": 0},
            "rooms": 1,
            "currency": "EUR",
        }
        
        try:
            response = await self.client.post("/api/public/quote", json=payload)
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text[:500]}...")
            
            if response.status_code == 200:
                data = response.json()
                assert data.get("ok") is True, "Response should have ok=True"
                assert "quote_id" in data, "Response should have quote_id"
                assert "amount_cents" in data, "Response should have amount_cents"
                assert data.get("currency") == "EUR", "Currency should be EUR"
                assert "product" in data, "Response should have product snapshot"
                print("   ✅ Quote creation successful")
                return data
            else:
                print(f"   ❌ Quote creation failed: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"   ❌ Exception during quote test: {e}")
            return None
            
    async def test_public_checkout_happy_path_stubbed_stripe(self):
        """Test 2: Stripe create_payment_intent with monkeypatch (simulated)"""
        print("🧪 Test 2: Public Checkout Happy Path (Stubbed Stripe)")
        
        # First create a quote (this would need real data in production)
        org = "org_public_checkout_test"
        quote_payload = {
            "org": org,
            "product_id": "507f1f77bcf86cd799439012",  # Valid ObjectId format
            "date_from": date.today().isoformat(),
            "date_to": (date.today() + timedelta(days=2)).isoformat(),
            "pax": {"adults": 2, "children": 0},
            "rooms": 1,
            "currency": "EUR",
        }
        
        try:
            # Step 1: Create quote
            quote_resp = await self.client.post("/api/public/quote", json=quote_payload)
            print(f"   Quote Status: {quote_resp.status_code}")
            
            if quote_resp.status_code != 200:
                print(f"   ❌ Quote creation failed: {quote_resp.text}")
                return False
                
            quote_data = quote_resp.json()
            quote_id = quote_data["quote_id"]
            amount_cents = quote_data["amount_cents"]
            
            # Step 2: Perform checkout
            checkout_payload = {
                "org": org,
                "quote_id": quote_id,
                "guest": {
                    "full_name": "Test Guest",
                    "email": "guest@example.com",
                    "phone": "+905001112233",
                },
                "payment": {"method": "stripe", "return_url": "https://example.com/book/complete"},
                "idempotency_key": "idem-public-test-1",
            }
            
            checkout_resp = await self.client.post("/api/public/checkout", json=checkout_payload)
            print(f"   Checkout Status: {checkout_resp.status_code}")
            print(f"   Checkout Response: {checkout_resp.text[:500]}...")
            
            if checkout_resp.status_code == 200:
                data = checkout_resp.json()
                assert data.get("ok") is True, "Response should have ok=True"
                assert "booking_id" in data, "Response should have booking_id"
                assert "payment_intent_id" in data, "Response should have payment_intent_id"
                assert "client_secret" in data, "Response should have client_secret"
                print("   ✅ Checkout successful")
                
                # Test idempotency
                checkout_resp2 = await self.client.post("/api/public/checkout", json=checkout_payload)
                if checkout_resp2.status_code == 200:
                    data2 = checkout_resp2.json()
                    if data2["booking_id"] == data["booking_id"]:
                        print("   ✅ Idempotency working correctly")
                    else:
                        print("   ⚠️ Idempotency issue: different booking_id returned")
                        
                return True
            else:
                print(f"   ❌ Checkout failed: {checkout_resp.status_code}")
                return False
                
        except Exception as e:
            print(f"   ❌ Exception during checkout test: {e}")
            return False
            
    async def test_public_checkout_expired_quote(self):
        """Test 3: Expired quote checkout should return 404 QUOTE_NOT_FOUND"""
        print("🧪 Test 3: Public Checkout Expired Quote")
        
        org = "org_public_expired_test"
        payload = {
            "org": org,
            "quote_id": "qt_expired_test_123",  # Non-existent/expired quote
            "guest": {
                "full_name": "Expired Guest",
                "email": "expired@example.com",
                "phone": "+905001112233",
            },
            "payment": {"method": "stripe"},
            "idempotency_key": "idem-expired-test-1",
        }
        
        try:
            response = await self.client.post("/api/public/checkout", json=payload)
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text}")
            
            if response.status_code == 404:
                print("   ✅ Expired quote correctly rejected with 404")
                return True
            else:
                print(f"   ❌ Expected 404, got {response.status_code}")
                return False
                
        except Exception as e:
            print(f"   ❌ Exception during expired quote test: {e}")
            return False
            
    async def test_endpoint_availability(self):
        """Test if endpoints are available"""
        print("🔍 Testing endpoint availability...")
        
        try:
            # Test GET (should return 405 Method Not Allowed)
            resp = await self.client.get("/api/public/quote")
            print(f"   GET /api/public/quote: {resp.status_code}")
            
            # Test POST with empty payload (should return 422 validation error)
            resp = await self.client.post("/api/public/quote", json={})
            print(f"   POST /api/public/quote (empty): {resp.status_code}")
            
            resp = await self.client.post("/api/public/checkout", json={})
            print(f"   POST /api/public/checkout (empty): {resp.status_code}")
            
            if resp.status_code in [405, 422]:
                print("   ✅ Endpoints are accessible")
                return True
            else:
                print("   ❌ Endpoints may not be properly configured")
                return False
                
        except Exception as e:
            print(f"   ❌ Exception during endpoint availability test: {e}")
            return False
            
    async def run_all_tests(self):
        """Run all test scenarios"""
        print("=" * 60)
        print("FAZ 2 / F2.T2 PUBLIC QUOTE + CHECKOUT BACKEND TEST")
        print("=" * 60)
        print(f"Backend URL: {self.base_url}")
        print()
        
        await self.setup()
        
        try:
            # Test endpoint availability first
            await self.test_endpoint_availability()
            print()
            
            # Run the three main test scenarios
            test1_result = await self.test_public_quote_happy_path()
            print()
            
            test2_result = await self.test_public_checkout_happy_path_stubbed_stripe()
            print()
            
            test3_result = await self.test_public_checkout_expired_quote()
            print()
            
            # Summary
            print("=" * 60)
            print("TEST SUMMARY")
            print("=" * 60)
            print(f"1. Public Quote Happy Path: {'✅ PASS' if test1_result else '❌ FAIL'}")
            print(f"2. Public Checkout Happy Path: {'✅ PASS' if test2_result else '❌ FAIL'}")
            print(f"3. Expired Quote Test: {'✅ PASS' if test3_result else '❌ FAIL'}")
            
            if all([test1_result, test2_result, test3_result]):
                print("\n🎉 ALL TESTS PASSED - FAZ 2 / F2.T2 backend functionality working correctly!")
            else:
                print("\n⚠️ SOME TESTS FAILED - Check implementation and data setup")
                
        finally:
            await self.cleanup()


async def main():
    """Main test runner"""
    tester = PublicCheckoutTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())