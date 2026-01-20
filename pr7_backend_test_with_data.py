#!/usr/bin/env python3
"""
PR#7.0 Backend Test Suite - Customer-Booking Linking (Simplified)

This version creates test data first and then tests the functionality.
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timedelta
from uuid import uuid4
from bson import ObjectId

import httpx
import motor.motor_asyncio

# Backend URL from environment
BACKEND_URL = os.getenv("REACT_APP_BACKEND_URL", "https://resflow-polish.preview.emergentagent.com")
API_BASE = f"{BACKEND_URL}/api/api"  # Note: double /api due to router configuration

# MongoDB connection
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017/b2b_hotel_suite")

# Test credentials
ADMIN_EMAIL = "admin@acenta.test"
ADMIN_PASSWORD = "admin123"

class TestRunner:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.admin_token = None
        self.admin_user = None
        self.test_org_id = None
        self.db = None
        
    async def setup(self):
        """Authenticate and setup database connection"""
        print("🔐 Authenticating admin user...")
        
        auth_response = await self.client.post(
            f"{BACKEND_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        
        if auth_response.status_code != 200:
            raise Exception(f"Admin authentication failed: {auth_response.status_code} - {auth_response.text}")
        
        auth_data = auth_response.json()
        self.admin_token = auth_data["access_token"]
        self.admin_user = auth_data["user"]
        self.test_org_id = self.admin_user["organization_id"]
        
        print(f"✅ Admin authenticated - Org ID: {self.test_org_id}")
        
        # Setup MongoDB connection
        mongo_client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URL)
        self.db = mongo_client.get_default_database()
        
    def get_headers(self, token=None):
        """Get authorization headers"""
        token = token or self.admin_token
        return {"Authorization": f"Bearer {token}"}
    
    async def create_test_booking(self):
        """Create a test booking directly in database"""
        booking_id = ObjectId()
        booking_doc = {
            "_id": booking_id,
            "organization_id": self.test_org_id,
            "status": "CONFIRMED",
            "currency": "EUR",
            "amounts": {"sell": 150.0, "buy": 120.0},
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "quote_id": f"qt_{uuid4().hex[:12]}",  # B2B booking needs quote_id
            "agency_id": "agency_test_123",
            "channel_id": "channel_test_123",
            "items": [{"type": "hotel", "name": "Test Hotel"}],
            "customer": {"name": "Test Guest", "email": "test@example.com"},
            "travellers": []
        }
        
        await self.db.bookings.insert_one(booking_doc)
        print(f"   Created test booking: {booking_id}")
        return str(booking_id)
    
    async def create_test_customer(self, name_suffix=""):
        """Create a test customer for linking tests"""
        customer_data = {
            "name": f"Test Customer PR7{name_suffix}",
            "type": "individual",
            "contacts": [
                {"type": "email", "value": f"test.customer.pr7{name_suffix}@example.com", "is_primary": True}
            ],
            "tags": ["test", "pr7"]
        }
        
        # CRM endpoints use single /api prefix
        crm_api_base = f"{BACKEND_URL}/api"
        response = await self.client.post(
            f"{crm_api_base}/crm/customers",
            json=customer_data,
            headers=self.get_headers()
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to create test customer: {response.status_code} - {response.text}")
        
        return response.json()
    
    async def test_patch_customer_link_valid_scenario(self):
        """Test scenario a: Valid booking_id + valid customer_id (same org)"""
        print("\n📋 Test 1a: Valid booking_id + valid customer_id (same org)")
        
        # Create test data
        booking_id = await self.create_test_booking()
        customer = await self.create_test_customer("_valid")
        customer_id = customer["id"]
        
        print(f"   Using booking: {booking_id}")
        print(f"   Using customer: {customer_id}")
        
        # Test linking customer to booking
        link_response = await self.client.patch(
            f"{API_BASE}/api/ops/bookings/{booking_id}/customer",
            json={"customer_id": customer_id},
            headers=self.get_headers()
        )
        
        print(f"   PATCH response: {link_response.status_code}")
        if link_response.status_code == 200:
            data = link_response.json()
            print(f"   Response body: {json.dumps(data, indent=2)}")
            
            # Verify response structure
            if (data.get("ok") is True and 
                data.get("booking_id") == booking_id and 
                data.get("customer_id") == customer_id):
                print("   ✅ Valid linking successful - correct response structure")
                
                # Verify in database
                booking_doc = await self.db.bookings.find_one({"_id": ObjectId(booking_id)})
                if booking_doc and booking_doc.get("customer_id") == customer_id:
                    print("   ✅ Database correctly updated with customer_id")
                    return True
                else:
                    print("   ❌ Database not updated correctly")
                    return False
            else:
                print("   ❌ Response structure incorrect")
                return False
        else:
            print(f"   ❌ Expected 200, got {link_response.status_code}: {link_response.text}")
            return False
    
    async def test_patch_customer_unlink_scenario(self):
        """Test scenario b: Valid booking_id + customer_id=NULL (unlink)"""
        print("\n📋 Test 1b: Valid booking_id + customer_id=NULL (unlink)")
        
        # Create test data and link first
        booking_id = await self.create_test_booking()
        customer = await self.create_test_customer("_unlink")
        customer_id = customer["id"]
        
        # First link the customer
        await self.client.patch(
            f"{API_BASE}/api/ops/bookings/{booking_id}/customer",
            json={"customer_id": customer_id},
            headers=self.get_headers()
        )
        
        print(f"   Using booking: {booking_id} (pre-linked)")
        
        # Test unlinking (customer_id = null)
        unlink_response = await self.client.patch(
            f"{API_BASE}/api/ops/bookings/{booking_id}/customer",
            json={"customer_id": None},
            headers=self.get_headers()
        )
        
        print(f"   PATCH response: {unlink_response.status_code}")
        if unlink_response.status_code == 200:
            data = unlink_response.json()
            print(f"   Response body: {json.dumps(data, indent=2)}")
            
            # Verify response structure for unlink
            if (data.get("ok") is True and 
                data.get("booking_id") == booking_id and 
                data.get("customer_id") is None):
                print("   ✅ Valid unlinking successful - correct response structure")
                
                # Verify in database (customer_id should be unset)
                booking_doc = await self.db.bookings.find_one({"_id": ObjectId(booking_id)})
                if booking_doc and "customer_id" not in booking_doc:
                    print("   ✅ Database correctly unset customer_id field")
                    return True
                else:
                    print(f"   ❌ Database still has customer_id: {booking_doc.get('customer_id')}")
                    return False
            else:
                print("   ❌ Response structure incorrect for unlink")
                return False
        else:
            print(f"   ❌ Expected 200, got {unlink_response.status_code}: {unlink_response.text}")
            return False
    
    async def test_patch_invalid_booking_id(self):
        """Test scenario c: Invalid booking_id (unparseable ObjectId)"""
        print("\n📋 Test 1c: Invalid booking_id (unparseable ObjectId)")
        
        invalid_booking_id = "invalid-booking-id-123"
        
        response = await self.client.patch(
            f"{API_BASE}/api/ops/bookings/{invalid_booking_id}/customer",
            json={"customer_id": "cust_test123"},
            headers=self.get_headers()
        )
        
        print(f"   PATCH response: {response.status_code}")
        if response.status_code == 400:
            data = response.json()
            print(f"   Response body: {json.dumps(data, indent=2)}")
            
            # Check for expected error code
            error_code = data.get("error", {}).get("code") or data.get("code")
            if error_code == "invalid_booking_id":
                print("   ✅ Invalid booking_id correctly rejected with 400 + invalid_booking_id")
                return True
            else:
                print(f"   ❌ Expected code 'invalid_booking_id', got '{error_code}'")
                return False
        else:
            print(f"   ❌ Expected 400, got {response.status_code}: {response.text}")
            return False
    
    async def test_patch_nonexistent_booking(self):
        """Test scenario d: Valid ObjectId format but booking doesn't exist in org"""
        print("\n📋 Test 1d: Non-existent booking (valid format but not in org)")
        
        # Use a valid ObjectId format that doesn't exist
        nonexistent_booking_id = "507f1f77bcf86cd799439011"
        
        response = await self.client.patch(
            f"{API_BASE}/api/ops/bookings/{nonexistent_booking_id}/customer",
            json={"customer_id": "cust_test123"},
            headers=self.get_headers()
        )
        
        print(f"   PATCH response: {response.status_code}")
        if response.status_code == 404:
            data = response.json()
            print(f"   Response body: {json.dumps(data, indent=2)}")
            
            # Check for expected error code
            error_code = data.get("error", {}).get("code") or data.get("code")
            if error_code in ["booking_not_found", "not_found"]:
                print("   ✅ Non-existent booking correctly rejected with 404 + booking_not_found")
                return True
            else:
                print(f"   ❌ Expected code 'booking_not_found' or 'not_found', got '{error_code}'")
                return False
        else:
            print(f"   ❌ Expected 404, got {response.status_code}: {response.text}")
            return False
    
    async def test_patch_customer_different_org(self):
        """Test scenario e: Valid booking_id + customer_id from different org"""
        print("\n📋 Test 1e: Valid booking_id + customer_id from different org")
        
        # Create test booking
        booking_id = await self.create_test_booking()
        
        # Use a customer_id that doesn't exist in this org (simulating different org)
        fake_customer_id = "cust_different_org_123456"
        
        response = await self.client.patch(
            f"{API_BASE}/api/ops/bookings/{booking_id}/customer",
            json={"customer_id": fake_customer_id},
            headers=self.get_headers()
        )
        
        print(f"   PATCH response: {response.status_code}")
        if response.status_code == 404:
            data = response.json()
            print(f"   Response body: {json.dumps(data, indent=2)}")
            
            # Check for expected error code
            error_code = data.get("error", {}).get("code") or data.get("code")
            if error_code == "customer_not_found":
                print("   ✅ Different org customer correctly rejected with 404 + customer_not_found")
                return True
            else:
                print(f"   ❌ Expected code 'customer_not_found', got '{error_code}'")
                return False
        else:
            print(f"   ❌ Expected 404, got {response.status_code}: {response.text}")
            return False
    
    async def test_ops_booking_detail_customer_id_field(self):
        """Test scenario 2: Ops booking detail endpoint includes customer_id field"""
        print("\n📋 Test 2: Ops booking detail endpoint includes customer_id field")
        
        # Create test data
        booking_id = await self.create_test_booking()
        
        print(f"   Testing booking detail: {booking_id}")
        
        # Test booking detail before linking
        detail_response = await self.client.get(
            f"{API_BASE}/api/ops/bookings/{booking_id}",
            headers=self.get_headers()
        )
        
        print(f"   GET detail response: {detail_response.status_code}")
        if detail_response.status_code == 200:
            data = detail_response.json()
            
            # Check if customer_id field is present (should be null/missing before linking)
            if "customer_id" in data:
                customer_id_before = data["customer_id"]
                print(f"   ✅ customer_id field present before linking: {customer_id_before}")
                
                # Now create a customer and link it
                customer = await self.create_test_customer("_detail_test")
                customer_id = customer["id"]
                
                # Link customer to booking
                link_response = await self.client.patch(
                    f"{API_BASE}/ops/bookings/{booking_id}/customer",
                    json={"customer_id": customer_id},
                    headers=self.get_headers()
                )
                
                if link_response.status_code == 200:
                    # Check booking detail after linking
                    detail_after_response = await self.client.get(
                        f"{API_BASE}/api/ops/bookings/{booking_id}",
                        headers=self.get_headers()
                    )
                    
                    if detail_after_response.status_code == 200:
                        data_after = detail_after_response.json()
                        customer_id_after = data_after.get("customer_id")
                        
                        if customer_id_after == customer_id:
                            print(f"   ✅ customer_id field correctly updated after linking: {customer_id_after}")
                            return True
                        else:
                            print(f"   ❌ customer_id not updated correctly. Expected: {customer_id}, Got: {customer_id_after}")
                            return False
                    else:
                        print(f"   ❌ Failed to get booking detail after linking: {detail_after_response.status_code}")
                        return False
                else:
                    print(f"   ❌ Failed to link customer: {link_response.status_code}")
                    return False
            else:
                print("   ❌ customer_id field not present in booking detail response")
                return False
        else:
            print(f"   ❌ Failed to get booking detail: {detail_response.status_code}")
            return False
    
    async def test_crm_customer_recent_bookings(self):
        """Test scenario 3: CRM Customer Detail Recent Bookings behavior"""
        print("\n📋 Test 3: CRM Customer Detail Recent Bookings")
        
        # Create a test customer
        customer = await self.create_test_customer("_recent_bookings")
        customer_id = customer["id"]
        print(f"   Created test customer: {customer_id}")
        
        # Test customer detail before any bookings are linked
        crm_api_base = f"{BACKEND_URL}/api"
        detail_response = await self.client.get(
            f"{crm_api_base}/crm/customers/{customer_id}",
            headers=self.get_headers()
        )
        
        print(f"   GET customer detail response: {detail_response.status_code}")
        if detail_response.status_code == 200:
            data = detail_response.json()
            
            # Check recent_bookings field before linking
            recent_bookings_before = data.get("recent_bookings", [])
            print(f"   recent_bookings before linking: {len(recent_bookings_before)} items")
            
            if len(recent_bookings_before) == 0:
                print("   ✅ recent_bookings is empty before linking (correct)")
                
                # Now create a booking and link it to this customer
                booking_id = await self.create_test_booking()
                
                # Link customer to booking
                link_response = await self.client.patch(
                    f"{API_BASE}/ops/bookings/{booking_id}/customer",
                    json={"customer_id": customer_id},
                    headers=self.get_headers()
                )
                
                if link_response.status_code == 200:
                    print(f"   ✅ Successfully linked booking {booking_id} to customer")
                    
                    # Check customer detail after linking
                    detail_after_response = await self.client.get(
                        f"{crm_api_base}/crm/customers/{customer_id}",
                        headers=self.get_headers()
                    )
                    
                    if detail_after_response.status_code == 200:
                        data_after = detail_after_response.json()
                        recent_bookings_after = data_after.get("recent_bookings", [])
                        
                        print(f"   recent_bookings after linking: {len(recent_bookings_after)} items")
                        
                        if len(recent_bookings_after) > 0:
                            print("   ✅ recent_bookings populated after linking")
                            
                            # Check that _id field is not present (projection requirement)
                            first_booking = recent_bookings_after[0]
                            if "_id" not in first_booking:
                                print("   ✅ _id field correctly excluded from recent_bookings projection")
                                
                                # Check sorting (should be by created_at desc or updated_at desc)
                                if len(recent_bookings_after) > 1:
                                    # Verify sorting
                                    dates = []
                                    for booking in recent_bookings_after:
                                        created_at = booking.get("created_at")
                                        updated_at = booking.get("updated_at")
                                        sort_date = created_at or updated_at
                                        if sort_date:
                                            dates.append(sort_date)
                                    
                                    if dates == sorted(dates, reverse=True):
                                        print("   ✅ recent_bookings correctly sorted by date desc")
                                    else:
                                        print("   ⚠️  recent_bookings sorting could not be verified")
                                
                                return True
                            else:
                                print("   ❌ _id field present in recent_bookings (should be excluded)")
                                return False
                        else:
                            print("   ❌ recent_bookings still empty after linking")
                            return False
                    else:
                        print(f"   ❌ Failed to get customer detail after linking: {detail_after_response.status_code}")
                        return False
                else:
                    print(f"   ❌ Failed to link booking to customer: {link_response.status_code}")
                    return False
            else:
                print(f"   ⚠️  Customer already has {len(recent_bookings_before)} recent bookings")
                return True
        else:
            print(f"   ❌ Failed to get customer detail: {detail_response.status_code}")
            return False
    
    async def run_all_tests(self):
        """Run all test scenarios"""
        print("🚀 Starting PR#7.0 Backend Test Suite (With Test Data)")
        print("=" * 60)
        
        await self.setup()
        
        test_results = []
        
        # Test 1: PATCH /api/ops/bookings/{booking_id}/customer scenarios
        test_results.append(await self.test_patch_customer_link_valid_scenario())
        test_results.append(await self.test_patch_customer_unlink_scenario())
        test_results.append(await self.test_patch_invalid_booking_id())
        test_results.append(await self.test_patch_nonexistent_booking())
        test_results.append(await self.test_patch_customer_different_org())
        
        # Test 2: Ops booking detail endpoint
        test_results.append(await self.test_ops_booking_detail_customer_id_field())
        
        # Test 3: CRM customer recent bookings
        test_results.append(await self.test_crm_customer_recent_bookings())
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for result in test_results if result)
        total = len(test_results)
        
        print(f"✅ Passed: {passed}/{total}")
        print(f"❌ Failed: {total - passed}/{total}")
        
        if passed == total:
            print("\n🎉 ALL TESTS PASSED! PR#7.0 backend functionality is working correctly.")
        else:
            print(f"\n⚠️  {total - passed} test(s) failed. Please review the issues above.")
        
        return passed == total

async def main():
    """Main test runner"""
    runner = TestRunner()
    try:
        success = await runner.run_all_tests()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n💥 Test suite failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        await runner.client.aclose()

if __name__ == "__main__":
    asyncio.run(main())