#!/usr/bin/env python3
"""
Paraşüt Push V1 Backend API Comprehensive Test
==============================================

This test creates a real booking in the database and then tests the Paraşüt Push V1 APIs:
1) Login with admin@acenta.test / admin123 (get JWT token)
2) Create a test booking in the database
3) POST /api/admin/finance/parasut/push-invoice-v1 with {"booking_id": "<booking_id>"}
4) Test idempotency by calling POST again at least 2 times
5) GET /api/admin/finance/parasut/pushes?booking_id=<booking_id>&limit=50
6) Test validation with deliberately broken booking_id (expect 422 INVALID_BOOKING_ID)
"""

import asyncio
import json
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import httpx
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient


class ParasutPushComprehensiveTester:
    def __init__(self, base_url: str, mongo_url: str):
        self.base_url = base_url.rstrip('/')
        self.client = httpx.AsyncClient(timeout=30.0)
        self.mongo_client = AsyncIOMotorClient(mongo_url)
        self.db = self.mongo_client.get_default_database()
        self.token: Optional[str] = None
        self.headers: Dict[str, str] = {}
        self.org_id: Optional[str] = None
        
    async def close(self):
        await self.client.aclose()
        self.mongo_client.close()
        
    def log(self, message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")
        
    async def login(self, email: str, password: str) -> bool:
        """Step 1: Login and get JWT token"""
        self.log("🔐 Step 1: Admin Login")
        
        login_data = {
            "email": email,
            "password": password
        }
        
        try:
            response = await self.client.post(
                f"{self.base_url}/api/auth/login",
                json=login_data
            )
            
            self.log(f"Login Response Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                if self.token:
                    self.headers = {"Authorization": f"Bearer {self.token}"}
                    user_info = data.get("user", {})
                    self.org_id = user_info.get("organization_id", "N/A")
                    role = user_info.get("role", "N/A")
                    self.log(f"✅ Login successful - Role: {role}, Org ID: {self.org_id}")
                    return True
                else:
                    self.log("❌ Login failed - No access token in response")
                    return False
            else:
                self.log(f"❌ Login failed - Status: {response.status_code}")
                if response.status_code != 500:
                    self.log(f"Response: {response.text}")
                return False
                
        except Exception as e:
            self.log(f"❌ Login error: {str(e)}")
            return False
            
    async def create_test_booking(self) -> Optional[str]:
        """Create a test booking directly in the database"""
        self.log("📝 Creating test booking in database...")
        
        try:
            booking_id = ObjectId()
            now = datetime.now(timezone.utc)
            
            # Create a comprehensive test booking document
            booking_doc = {
                "_id": booking_id,
                "id": str(booking_id),
                "organization_id": self.org_id,
                "code": f"PARASUT-TEST-{booking_id}",
                "booking_code": f"PARASUT-TEST-{booking_id}",
                "status": "confirmed",
                "created_at": now,
                "updated_at": now,
                "confirmed_at": now,
                
                # Guest information
                "guest": {
                    "full_name": "Ahmet Parasüt Test",
                    "name": "Ahmet Parasüt Test",
                    "email": "ahmet.parasut@test.com",
                    "phone": "+90 555 987 6543"
                },
                "guest_email": "ahmet.parasut@test.com",
                
                # Booking amounts
                "amount_total_cents": 15000,  # 150.00 EUR
                "currency": "EUR",
                "amounts": {
                    "sell": 150.0,
                    "net": 150.0,
                    "currency": "EUR",
                    "breakdown": {
                        "base": 150.0,
                        "markup_amount": 0.0,
                        "discount_amount": 0.0
                    }
                },
                
                # Product information
                "product_id": str(ObjectId()),
                "product_type": "hotel",
                "product_name": "Test Hotel Parasüt",
                
                # Dates
                "date_from": "2026-02-01",
                "date_to": "2026-02-02",
                "check_in": "2026-02-01",
                "check_out": "2026-02-02",
                
                # Occupancy
                "pax": {
                    "adults": 2,
                    "children": 0
                },
                "rooms": 1,
                
                # Channel information
                "channel": "public",
                "source": "public_checkout",
                
                # Payment status
                "payment_status": "paid",
                "paid_at": now
            }
            
            # Insert the booking
            result = await self.db.bookings.insert_one(booking_doc)
            
            if result.inserted_id:
                self.log(f"✅ Test booking created successfully: {booking_id}")
                self.log(f"   Booking Code: PARASUT-TEST-{booking_id}")
                self.log(f"   Amount: 150.00 EUR")
                self.log(f"   Guest: Ahmet Parasüt Test")
                return str(booking_id)
            else:
                self.log("❌ Failed to create test booking")
                return None
                
        except Exception as e:
            self.log(f"❌ Error creating test booking: {str(e)}")
            return None
            
    async def test_push_invoice_v1(self, booking_id: str) -> Dict[str, Any]:
        """Step 2: Test POST /api/admin/finance/parasut/push-invoice-v1"""
        self.log("🚀 Step 2: Testing Paraşüt Push Invoice V1")
        
        payload = {"booking_id": booking_id}
        
        try:
            response = await self.client.post(
                f"{self.base_url}/api/admin/finance/parasut/push-invoice-v1",
                json=payload,
                headers=self.headers
            )
            
            self.log(f"Push Invoice Response Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                status = data.get("status")
                log_id = data.get("log_id")
                parasut_contact_id = data.get("parasut_contact_id")
                parasut_invoice_id = data.get("parasut_invoice_id")
                reason = data.get("reason")
                
                self.log(f"✅ Push successful - Status: {status}")
                self.log(f"   Log ID: {log_id}")
                if parasut_contact_id:
                    self.log(f"   Paraşüt Contact ID: {parasut_contact_id}")
                if parasut_invoice_id:
                    self.log(f"   Paraşüt Invoice ID: {parasut_invoice_id}")
                if reason:
                    self.log(f"   Reason: {reason}")
                    
                # Verify response schema compliance
                required_fields = ["status", "log_id"]
                missing_fields = [field for field in required_fields if data.get(field) is None]
                if missing_fields:
                    self.log(f"   ⚠️ Missing required fields: {missing_fields}")
                else:
                    self.log(f"   ✅ Response schema compliant")
                    
                # Verify status is one of expected values
                if status in ["success", "skipped", "failed"]:
                    self.log(f"   ✅ Status value valid: {status}")
                else:
                    self.log(f"   ❌ Invalid status value: {status}")
                    
                return data
            else:
                self.log(f"❌ Push failed - Status: {response.status_code}")
                self.log(f"Response: {response.text}")
                return {}
                
        except Exception as e:
            self.log(f"❌ Push error: {str(e)}")
            return {}
            
    async def test_idempotency(self, booking_id: str, original_result: Dict[str, Any]):
        """Step 3: Test idempotency by calling POST again multiple times"""
        self.log("🔄 Step 3: Testing Idempotency (2 additional calls)")
        
        payload = {"booking_id": booking_id}
        
        for attempt in range(2):
            self.log(f"   Idempotency test #{attempt + 1}")
            
            try:
                response = await self.client.post(
                    f"{self.base_url}/api/admin/finance/parasut/push-invoice-v1",
                    json=payload,
                    headers=self.headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    status = data.get("status")
                    log_id = data.get("log_id")
                    
                    self.log(f"   ✅ Call #{attempt + 1} - Status: {status}, Log ID: {log_id}")
                    
                    # Check idempotency behavior
                    if original_result:
                        original_log_id = original_result.get("log_id")
                        original_status = original_result.get("status")
                        
                        if log_id == original_log_id:
                            self.log(f"   ✅ Idempotency verified - Same log ID: {log_id}")
                        else:
                            self.log(f"   ⚠️ Different log ID - Original: {original_log_id}, New: {log_id}")
                            
                        # For successful pushes, subsequent calls should return "skipped"
                        if original_status == "success" and status == "skipped":
                            self.log(f"   ✅ Idempotency behavior correct - Success → Skipped")
                        elif status == original_status:
                            self.log(f"   ✅ Consistent status: {status}")
                        else:
                            self.log(f"   ⚠️ Status changed - Original: {original_status}, New: {status}")
                else:
                    self.log(f"   ❌ Call #{attempt + 1} failed - Status: {response.status_code}")
                    
            except Exception as e:
                self.log(f"   ❌ Call #{attempt + 1} error: {str(e)}")
                
    async def test_list_pushes(self, booking_id: str):
        """Step 4: Test GET /api/admin/finance/parasut/pushes"""
        self.log("📋 Step 4: Testing List Paraşüt Pushes")
        
        try:
            response = await self.client.get(
                f"{self.base_url}/api/admin/finance/parasut/pushes?booking_id={booking_id}&limit=50",
                headers=self.headers
            )
            
            self.log(f"List Pushes Response Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                items = data.get("items", [])
                
                self.log(f"✅ List successful - Found {len(items)} log entries")
                
                for i, item in enumerate(items):
                    item_id = item.get("id")
                    item_booking_id = item.get("booking_id")
                    push_type = item.get("push_type")
                    status = item.get("status")
                    attempt_count = item.get("attempt_count")
                    last_error = item.get("last_error")
                    created_at = item.get("created_at")
                    updated_at = item.get("updated_at")
                    parasut_contact_id = item.get("parasut_contact_id")
                    parasut_invoice_id = item.get("parasut_invoice_id")
                    
                    self.log(f"   Entry #{i + 1}:")
                    self.log(f"     ID: {item_id}")
                    self.log(f"     Booking ID: {item_booking_id}")
                    self.log(f"     Push Type: {push_type}")
                    self.log(f"     Status: {status}")
                    self.log(f"     Attempt Count: {attempt_count}")
                    if last_error:
                        self.log(f"     Last Error: {last_error}")
                    if parasut_contact_id:
                        self.log(f"     Paraşüt Contact ID: {parasut_contact_id}")
                    if parasut_invoice_id:
                        self.log(f"     Paraşüt Invoice ID: {parasut_invoice_id}")
                    self.log(f"     Created: {created_at}")
                    self.log(f"     Updated: {updated_at}")
                    
                    # Verify required fields are present (ParasutPushLogListResponse schema)
                    required_fields = ["id", "booking_id", "push_type", "status", "attempt_count", "created_at", "updated_at"]
                    missing_fields = [field for field in required_fields if item.get(field) is None]
                    if missing_fields:
                        self.log(f"     ⚠️ Missing required fields: {missing_fields}")
                    else:
                        self.log(f"     ✅ All required fields present")
                        
                    # Verify status is valid
                    if status in ["pending", "success", "failed"]:
                        self.log(f"     ✅ Status value valid: {status}")
                    else:
                        self.log(f"     ❌ Invalid status value: {status}")
                        
            else:
                self.log(f"❌ List failed - Status: {response.status_code}")
                self.log(f"Response: {response.text}")
                
        except Exception as e:
            self.log(f"❌ List error: {str(e)}")
            
    async def test_invalid_booking_id(self):
        """Step 5: Test validation with invalid booking_id (expect 422 INVALID_BOOKING_ID)"""
        self.log("🚫 Step 5: Testing Invalid Booking ID Validation")
        
        invalid_booking_ids = [
            "invalid-booking-id",
            "12345",
            "",
            "not-an-objectid",
            "abc123def456"
        ]
        
        for invalid_id in invalid_booking_ids:
            self.log(f"   Testing invalid ID: '{invalid_id}'")
            
            payload = {"booking_id": invalid_id}
            
            try:
                response = await self.client.post(
                    f"{self.base_url}/api/admin/finance/parasut/push-invoice-v1",
                    json=payload,
                    headers=self.headers
                )
                
                if response.status_code == 422:
                    response_text = response.text
                    if "INVALID_BOOKING_ID" in response_text:
                        self.log(f"   ✅ Validation working - 422 INVALID_BOOKING_ID returned")
                    else:
                        self.log(f"   ⚠️ 422 returned but message unexpected: {response_text}")
                else:
                    self.log(f"   ❌ Expected 422, got {response.status_code}: {response.text}")
                    
            except Exception as e:
                self.log(f"   ❌ Validation test error: {str(e)}")
                
    async def cleanup_test_booking(self, booking_id: str):
        """Clean up the test booking from database"""
        try:
            result = await self.db.bookings.delete_one({"_id": ObjectId(booking_id)})
            if result.deleted_count > 0:
                self.log(f"🧹 Test booking {booking_id} cleaned up")
            else:
                self.log(f"⚠️ Test booking {booking_id} not found for cleanup")
        except Exception as e:
            self.log(f"⚠️ Cleanup error: {str(e)}")
                
    async def run_full_test(self):
        """Run the complete test suite"""
        self.log("🎯 Starting Paraşüt Push V1 Backend API Comprehensive Test")
        self.log("=" * 70)
        
        booking_id = None
        
        try:
            # Step 1: Login
            login_success = await self.login("admin@acenta.test", "admin123")
            if not login_success:
                self.log("❌ Test aborted - Login failed")
                return False
                
            # Step 2: Create test booking
            booking_id = await self.create_test_booking()
            if not booking_id:
                self.log("❌ Test aborted - Could not create test booking")
                return False
                
            # Step 3: Test push invoice
            original_result = await self.test_push_invoice_v1(booking_id)
            if not original_result:
                self.log("❌ Test aborted - Push invoice failed")
                return False
                
            # Step 4: Test idempotency
            await self.test_idempotency(booking_id, original_result)
            
            # Step 5: Test list pushes
            await self.test_list_pushes(booking_id)
            
            # Step 6: Test validation
            await self.test_invalid_booking_id()
            
            self.log("=" * 70)
            self.log("🎉 Paraşüt Push V1 Backend API Comprehensive Test Complete")
            return True
            
        except Exception as e:
            self.log(f"❌ Test suite error: {str(e)}")
            return False
        finally:
            # Cleanup
            if booking_id:
                await self.cleanup_test_booking(booking_id)


async def main():
    """Main test runner"""
    # Configuration
    backend_url = "https://parasut-push.preview.emergentagent.com"
    mongo_url = "mongodb://localhost:27017/syroce_dev"
    
    print(f"🚀 Paraşüt Push V1 Backend API Comprehensive Test")
    print(f"Backend URL: {backend_url}")
    print(f"MongoDB URL: {mongo_url}")
    print()
    
    tester = ParasutPushComprehensiveTester(backend_url, mongo_url)
    
    try:
        success = await tester.run_full_test()
        return 0 if success else 1
    finally:
        await tester.close()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)