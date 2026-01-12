#!/usr/bin/env python3
"""
Click-to-Pay API Test Script
Tests the Click-to-Pay functionality as requested by the user.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

import httpx
from httpx import ASGITransport
from server import app
from app.db import get_db
from app.utils import now_utc
from app.auth import hash_password
from bson import ObjectId


class ClickToPayTester:
    def __init__(self):
        self.client = None
        self.db = None
        
    async def setup(self):
        """Setup test environment"""
        # Override get_db to use test database
        from app.db import connect_mongo
        await connect_mongo()
        self.db = await get_db()
        
        # Create HTTP client
        transport = ASGITransport(app=app)
        self.client = httpx.AsyncClient(transport=transport, base_url="http://test", timeout=30.0)
        
    async def cleanup(self):
        """Cleanup test environment"""
        if self.client:
            await self.client.aclose()
            
    async def setup_test_data(self):
        """Setup test data for Click-to-Pay tests"""
        print("🔧 Setting up test data...")
        
        # Clean up any existing test data
        await self.db.bookings.delete_many({"_id": {"$regex": "^BKG-CLICK-"}})
        await self.db.booking_payments.delete_many({"booking_id": {"$regex": "^BKG-CLICK-"}})
        await self.db.click_to_pay_links.delete_many({"booking_id": {"$regex": "^BKG-CLICK-"}})
        
        # Ensure default organization exists (required by auth system)
        default_org = await self.db.organizations.find_one({"slug": "default"})
        if not default_org:
            org_doc = {
                "name": "Varsayılan Acenta",
                "slug": "default",
                "created_at": now_utc(),
                "updated_at": now_utc(),
                "settings": {"currency": "TRY"},
            }
            result = await self.db.organizations.insert_one(org_doc)
            self.default_org_id = str(result.inserted_id)
        else:
            self.default_org_id = str(default_org["_id"])
            
        # Ensure admin user exists in default org
        admin = await self.db.users.find_one({"organization_id": self.default_org_id, "email": "admin@acenta.test"})
        if not admin:
            await self.db.users.insert_one({
                "organization_id": self.default_org_id,
                "email": "admin@acenta.test",
                "name": "Admin",
                "password_hash": hash_password("admin123"),
                "roles": ["super_admin"],
                "created_at": now_utc(),
                "updated_at": now_utc(),
                "is_active": True,
            })
            
        # Generate test booking IDs
        self.booking_id_1 = str(ObjectId())
        self.booking_id_2 = str(ObjectId())
        self.booking_id_3 = str(ObjectId())
        self.booking_id_expired = str(ObjectId())
            
        print("✅ Test data setup complete")
        
    async def test_happy_path_stubbed_stripe(self):
        """Test 1: Happy path with stubbed Stripe"""
        print("\n🧪 Test 1: Happy path with stubbed Stripe")
        
        org_id = self.default_org_id
        booking_id = "BKG-CLICK-1"
        now = now_utc()
        
        # Create test booking
        await self.db.bookings.insert_one({
            "_id": booking_id,
            "organization_id": org_id,
            "agency_id": "agency_ctp",
            "currency": "EUR",
            "amounts": {"sell": 123.45},
            "status": "CONFIRMED",
            "created_at": now,
            "updated_at": now,
        })
        
        # Ensure no existing payments
        await self.db.booking_payments.delete_many({"organization_id": org_id, "booking_id": booking_id})
        
        # Login as admin
        login_resp = await self.client.post(
            "/api/auth/login",
            json={"email": "admin@acenta.test", "password": "admin123"},
        )
        
        if login_resp.status_code != 200:
            print(f"❌ Login failed: {login_resp.status_code} - {login_resp.text}")
            return False
            
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test ops endpoint to create link
        resp = await self.client.post(
            "/api/ops/payments/click-to-pay/",
            json={"booking_id": booking_id},
            headers=headers,
        )
        
        print(f"   POST /api/ops/payments/click-to-pay/ -> {resp.status_code}")
        
        if resp.status_code != 200:
            print(f"❌ Click-to-pay creation failed: {resp.status_code} - {resp.text}")
            return False
            
        body = resp.json()
        
        # Verify response structure
        if not body.get("ok"):
            print(f"❌ Response ok=false: {body}")
            return False
            
        if not body.get("url", "").startswith("/pay/"):
            print(f"❌ Invalid URL format: {body.get('url')}")
            return False
            
        if body.get("amount_cents", 0) <= 0:
            print(f"❌ Invalid amount_cents: {body.get('amount_cents')}")
            return False
            
        if body.get("currency", "").upper() != "EUR":
            print(f"❌ Invalid currency: {body.get('currency')}")
            return False
            
        # Verify link persisted in database
        link_doc = await self.db.click_to_pay_links.find_one({"organization_id": org_id, "booking_id": booking_id})
        if not link_doc:
            print("❌ Click-to-pay link not found in database")
            return False
            
        # Test public endpoint
        token_part = body["url"].split("/pay/")[-1]
        public_resp = await self.client.get(f"/api/public/pay/{token_part}")
        
        print(f"   GET /api/public/pay/{token_part} -> {public_resp.status_code}")
        
        if public_resp.status_code != 200:
            print(f"❌ Public pay endpoint failed: {public_resp.status_code} - {public_resp.text}")
            return False
            
        pdata = public_resp.json()
        
        if not pdata.get("ok"):
            print(f"❌ Public response ok=false: {pdata}")
            return False
            
        print("✅ Happy path test passed")
        return True
        
    async def test_nothing_to_collect(self):
        """Test 2: Nothing to collect scenario"""
        print("\n🧪 Test 2: Nothing to collect")
        
        org_id = self.default_org_id
        booking_id = "BKG-CLICK-2"
        now = now_utc()
        
        # Create test booking
        await self.db.bookings.insert_one({
            "_id": booking_id,
            "organization_id": org_id,
            "agency_id": "agency_ctp2",
            "currency": "EUR",
            "amounts": {"sell": 100.0},
            "status": "CONFIRMED",
            "created_at": now,
            "updated_at": now,
        })
        
        # Create fully paid booking_payments
        await self.db.booking_payments.insert_one({
            "organization_id": org_id,
            "booking_id": booking_id,
            "currency": "EUR",
            "amount_total": 10_000,
            "amount_paid": 10_000,
            "amount_refunded": 0,
            "status": "PAID",
        })
        
        # Login as admin
        login_resp = await self.client.post(
            "/api/auth/login",
            json={"email": "admin@acenta.test", "password": "admin123"},
        )
        
        if login_resp.status_code != 200:
            print(f"❌ Login failed: {login_resp.status_code} - {login_resp.text}")
            return False
            
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test ops endpoint
        resp = await self.client.post(
            "/api/ops/payments/click-to-pay/",
            json={"booking_id": booking_id},
            headers=headers,
        )
        
        print(f"   POST /api/ops/payments/click-to-pay/ -> {resp.status_code}")
        
        if resp.status_code != 200:
            print(f"❌ Request failed: {resp.status_code} - {resp.text}")
            return False
            
        body = resp.json()
        
        if body.get("ok") is not False:
            print(f"❌ Expected ok=false, got: {body}")
            return False
            
        if body.get("reason") != "nothing_to_collect":
            print(f"❌ Expected reason=nothing_to_collect, got: {body.get('reason')}")
            return False
            
        if body.get("url") is not None:
            print(f"❌ Expected url=null, got: {body.get('url')}")
            return False
            
        print("✅ Nothing to collect test passed")
        return True
        
    async def test_wrong_org_ownership(self):
        """Test 3: Wrong organization ownership"""
        print("\n🧪 Test 3: Wrong organization ownership")
        
        booking_id = "BKG-CLICK-3"
        now = now_utc()
        
        # Create booking in a different org (simulate cross-org access)
        # Since auth is hardcoded to default org, we'll create booking in different org
        # but user will be from default org - this should result in 404
        different_org_id = "different_org_id"
        await self.db.bookings.insert_one({
            "_id": booking_id,
            "organization_id": different_org_id,
            "agency_id": "agency_A",
            "currency": "EUR",
            "amounts": {"sell": 50.0},
            "status": "CONFIRMED",
            "created_at": now,
            "updated_at": now,
        })
        
        # Login as admin from default org
        login_resp = await self.client.post(
            "/api/auth/login",
            json={"email": "admin@acenta.test", "password": "admin123"},
        )
        
        if login_resp.status_code != 200:
            print(f"❌ Login failed: {login_resp.status_code} - {login_resp.text}")
            return False
            
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test ops endpoint (should fail with 404)
        resp = await self.client.post(
            "/api/ops/payments/click-to-pay/",
            json={"booking_id": booking_id},
            headers=headers,
        )
        
        print(f"   POST /api/ops/payments/click-to-pay/ -> {resp.status_code}")
        
        if resp.status_code != 404:
            print(f"❌ Expected 404, got: {resp.status_code} - {resp.text}")
            return False
            
        print("✅ Wrong org ownership test passed")
        return True
        
    async def test_invalid_and_expired_tokens(self):
        """Test 4: Invalid and expired tokens"""
        print("\n🧪 Test 4: Invalid and expired tokens")
        
        # Test invalid token
        resp = await self.client.get("/api/public/pay/invalid-token-123")
        print(f"   GET /api/public/pay/invalid-token-123 -> {resp.status_code}")
        
        if resp.status_code != 404:
            print(f"❌ Expected 404 for invalid token, got: {resp.status_code}")
            return False
            
        body = resp.json()
        if body.get("error") != "NOT_FOUND":
            print(f"❌ Expected error=NOT_FOUND, got: {body}")
            return False
            
        # Test expired token
        from app.services.click_to_pay import _hash_token
        now = now_utc()
        raw_token = "expired-token-456"
        token_hash = _hash_token(raw_token)
        
        await self.db.click_to_pay_links.insert_one({
            "token_hash": token_hash,
            "expires_at": now.replace(year=now.year - 1),  # clearly in the past
            "organization_id": self.default_org_id,
            "booking_id": "BKG-EXPIRED",
            "payment_intent_id": "pi_expired",
            "amount_cents": 1000,
            "currency": "eur",
            "status": "active",
            "telemetry": {"access_count": 0},
            "created_at": now,
        })
        
        resp2 = await self.client.get(f"/api/public/pay/{raw_token}")
        print(f"   GET /api/public/pay/{raw_token} -> {resp2.status_code}")
        
        if resp2.status_code != 404:
            print(f"❌ Expected 404 for expired token, got: {resp2.status_code}")
            return False
            
        body2 = resp2.json()
        if body2.get("error") != "NOT_FOUND":
            print(f"❌ Expected error=NOT_FOUND for expired token, got: {body2}")
            return False
            
        print("✅ Invalid and expired tokens test passed")
        return True
        
    async def run_all_tests(self):
        """Run all Click-to-Pay tests"""
        print("🚀 Starting Click-to-Pay API Tests")
        
        try:
            await self.setup()
            await self.setup_test_data()
            
            tests = [
                self.test_happy_path_stubbed_stripe,
                self.test_nothing_to_collect,
                self.test_wrong_org_ownership,
                self.test_invalid_and_expired_tokens,
            ]
            
            passed = 0
            total = len(tests)
            
            for test in tests:
                try:
                    result = await test()
                    if result:
                        passed += 1
                except Exception as e:
                    print(f"❌ Test failed with exception: {e}")
                    import traceback
                    traceback.print_exc()
                    
            print(f"\n📊 Test Results: {passed}/{total} tests passed")
            
            if passed == total:
                print("🎉 All Click-to-Pay tests passed!")
                return True
            else:
                print("❌ Some tests failed")
                return False
                
        finally:
            await self.cleanup()


async def main():
    """Main test runner"""
    tester = ClickToPayTester()
    success = await tester.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)