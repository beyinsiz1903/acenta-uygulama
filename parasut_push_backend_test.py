#!/usr/bin/env python3
"""
Paraşüt Push V1 Backend API Smoke Test
=====================================

Test suite for Paraşüt Push V1 backend APIs as requested:
1) Login with admin@acenta.test / admin123 (get JWT token)
2) Find or create a test booking_id
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


class ParasutPushTester:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.client = httpx.AsyncClient(timeout=30.0)
        self.token: Optional[str] = None
        self.headers: Dict[str, str] = {}
        
    async def close(self):
        await self.client.aclose()
        
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
                    org_id = user_info.get("organization_id", "N/A")
                    role = user_info.get("role", "N/A")
                    self.log(f"✅ Login successful - Role: {role}, Org ID: {org_id}")
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
            
    async def find_or_create_booking(self) -> Optional[str]:
        """Find existing booking or create test booking for testing"""
        self.log("📋 Finding existing booking for testing...")
        
        try:
            # Try to get existing bookings
            response = await self.client.get(
                f"{self.base_url}/api/ops/bookings?limit=5",
                headers=self.headers
            )
            
            if response.status_code == 200:
                data = response.json()
                bookings = data.get("items", [])
                if bookings:
                    booking_id = bookings[0].get("id") or bookings[0].get("_id")
                    if booking_id:
                        self.log(f"✅ Found existing booking: {booking_id}")
                        return str(booking_id)
                        
            self.log("📝 No existing bookings found, creating test booking...")
            
            # Create a test booking document directly (simplified approach)
            test_booking_id = str(ObjectId())
            self.log(f"✅ Using test booking ID: {test_booking_id}")
            return test_booking_id
            
        except Exception as e:
            self.log(f"⚠️ Error finding bookings: {str(e)}")
            # Fallback to a test ObjectId
            test_booking_id = str(ObjectId())
            self.log(f"✅ Using fallback test booking ID: {test_booking_id}")
            return test_booking_id
            
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
                        if log_id == original_log_id:
                            self.log(f"   ✅ Idempotency verified - Same log ID: {log_id}")
                        else:
                            self.log(f"   ⚠️ Different log ID - Original: {original_log_id}, New: {log_id}")
                            
                        if status == "skipped":
                            self.log(f"   ✅ Idempotency behavior correct - Status: skipped")
                        elif status == original_result.get("status"):
                            self.log(f"   ✅ Consistent status: {status}")
                        else:
                            self.log(f"   ⚠️ Status changed - Original: {original_result.get('status')}, New: {status}")
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
                    
                    self.log(f"   Entry #{i + 1}:")
                    self.log(f"     ID: {item_id}")
                    self.log(f"     Booking ID: {item_booking_id}")
                    self.log(f"     Push Type: {push_type}")
                    self.log(f"     Status: {status}")
                    self.log(f"     Attempt Count: {attempt_count}")
                    if last_error:
                        self.log(f"     Last Error: {last_error}")
                    self.log(f"     Created: {created_at}")
                    self.log(f"     Updated: {updated_at}")
                    
                    # Verify required fields are present
                    required_fields = ["id", "booking_id", "push_type", "status", "attempt_count", "created_at", "updated_at"]
                    missing_fields = [field for field in required_fields if item.get(field) is None]
                    if missing_fields:
                        self.log(f"     ⚠️ Missing fields: {missing_fields}")
                    else:
                        self.log(f"     ✅ All required fields present")
                        
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
            "not-an-objectid"
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
                
    async def run_full_test(self):
        """Run the complete test suite"""
        self.log("🎯 Starting Paraşüt Push V1 Backend API Smoke Test")
        self.log("=" * 60)
        
        try:
            # Step 1: Login
            login_success = await self.login("admin@acenta.test", "admin123")
            if not login_success:
                self.log("❌ Test aborted - Login failed")
                return False
                
            # Step 2: Find or create booking
            booking_id = await self.find_or_create_booking()
            if not booking_id:
                self.log("❌ Test aborted - Could not get booking ID")
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
            
            self.log("=" * 60)
            self.log("🎉 Paraşüt Push V1 Backend API Smoke Test Complete")
            return True
            
        except Exception as e:
            self.log(f"❌ Test suite error: {str(e)}")
            return False


async def main():
    """Main test runner"""
    # Get backend URL from environment
    backend_url = "https://b2b-dashboard-3.preview.emergentagent.com"
    
    print(f"🚀 Paraşüt Push V1 Backend API Smoke Test")
    print(f"Backend URL: {backend_url}")
    print()
    
    tester = ParasutPushTester(backend_url)
    
    try:
        success = await tester.run_full_test()
        return 0 if success else 1
    finally:
        await tester.close()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)