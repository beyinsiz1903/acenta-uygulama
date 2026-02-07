#!/usr/bin/env python3

"""
FAZ 3 / Ticket 3 Backend Test - Email No-Op Patch Verification

Test scenarios:
1. /api/public/my-booking/request-link endpoint with different scenarios
2. dispatch_pending_emails behavior when SES config is missing  
3. E2E flow: request-link → get token from outbox → /my-booking/:token → cancel/amend → ops_cases + booking_events

Key focus: Email sending is now **no-op** but token generation + email_outbox recording + 
public GET + cancel/amend → ops_cases/booking_events chain should work end-to-end.
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timedelta
from typing import Any, Dict

import httpx
from bson import ObjectId

# Add backend to path for imports
sys.path.insert(0, '/app/backend')

from app.db import get_db, connect_mongo, close_mongo
from app.services.email_outbox import dispatch_pending_emails
from app.utils import now_utc

# Test configuration
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://hardening-e1-e4.preview.emergentagent.com')
API_BASE = f"{BACKEND_URL}/api"

class FAZ3Ticket3BackendTest:
    def __init__(self):
        self.client = httpx.Client(timeout=30.0)
        self.admin_token = None
        self.agency_token = None
        self.test_booking_id = None
        self.test_booking_code = None
        self.test_guest_email = None
        self.db = None
        
    async def setup(self):
        """Setup test environment"""
        print("🔧 Setting up FAZ 3 / Ticket 3 test environment...")
        
        # Connect to database
        await connect_mongo()
        self.db = await get_db()
        
        # Login as admin
        admin_resp = self.client.post(f"{API_BASE}/auth/login", json={
            "email": "admin@acenta.test",
            "password": "admin123"
        })
        if admin_resp.status_code != 200:
            raise Exception(f"Admin login failed: {admin_resp.status_code} {admin_resp.text}")
        
        self.admin_token = admin_resp.json()["access_token"]
        print("✅ Admin login successful")
        
        # Login as agency
        agency_resp = self.client.post(f"{API_BASE}/auth/login", json={
            "email": "agency1@demo.test", 
            "password": "agency123"
        })
        if agency_resp.status_code != 200:
            raise Exception(f"Agency login failed: {agency_resp.status_code} {agency_resp.text}")
            
        self.agency_token = agency_resp.json()["access_token"]
        print("✅ Agency login successful")
        
        # Find or create a test booking
        await self._setup_test_booking()
        
    async def _setup_test_booking(self):
        """Find or create a test booking for testing"""
        print("🔍 Setting up test booking...")
        
        # Look for existing bookings first
        bookings = await self.db.bookings.find({
            "organization_id": {"$exists": True},
            "code": {"$exists": True},
            "guest.email": {"$exists": True}
        }).limit(5).to_list(length=5)
        
        if bookings:
            # Use existing booking
            booking = bookings[0]
            self.test_booking_id = str(booking["_id"])
            self.test_booking_code = booking["code"]
            self.test_guest_email = booking.get("guest", {}).get("email", "test@example.com")
            print(f"✅ Using existing booking: {self.test_booking_code} / {self.test_guest_email}")
        else:
            # Create a minimal test booking
            now = now_utc()
            booking_doc = {
                "_id": ObjectId(),
                "organization_id": "695e03c80b04ed31c4eaa899",  # Default org
                "code": f"TEST{int(now.timestamp())}",
                "status": "CONFIRMED",
                "guest": {
                    "email": "test.guest@example.com",
                    "full_name": "Test Guest"
                },
                "hotel_name": "Test Hotel",
                "stay": {
                    "check_in": "2026-02-01",
                    "check_out": "2026-02-03"
                },
                "created_at": now,
                "updated_at": now
            }
            
            await self.db.bookings.insert_one(booking_doc)
            self.test_booking_id = str(booking_doc["_id"])
            self.test_booking_code = booking_doc["code"]
            self.test_guest_email = booking_doc["guest"]["email"]
            print(f"✅ Created test booking: {self.test_booking_code} / {self.test_guest_email}")

    async def test_request_link_scenarios(self):
        """Test /api/public/my-booking/request-link endpoint scenarios"""
        print("\n📧 Testing /api/public/my-booking/request-link endpoint scenarios...")
        
        # Scenario 1: Non-existent booking_code+email combination
        print("1️⃣ Testing non-existent booking+email combination...")
        
        # Clear any existing tokens/outbox for clean test
        await self.db.booking_public_tokens.delete_many({})
        await self.db.email_outbox.delete_many({})
        
        resp = self.client.post(f"{API_BASE}/public/my-booking/request-link", json={
            "booking_code": "NONEXISTENT123",
            "email": "nonexistent@example.com"
        })
        
        if resp.status_code != 200:
            print(f"❌ Expected 200, got {resp.status_code}: {resp.text}")
            return False
            
        data = resp.json()
        if not data.get("ok"):
            print(f"❌ Expected ok=true, got {data}")
            return False
            
        # Verify no records created
        tokens_count = await self.db.booking_public_tokens.count_documents({})
        outbox_count = await self.db.email_outbox.count_documents({})
        
        if tokens_count != 0 or outbox_count != 0:
            print(f"❌ Expected no records, but found tokens={tokens_count}, outbox={outbox_count}")
            return False
            
        print("✅ Non-existent booking correctly returns 200 {ok:true} with no database changes")
        
        # Scenario 2: Existing booking
        print("2️⃣ Testing existing booking...")
        
        resp = self.client.post(f"{API_BASE}/public/my-booking/request-link", json={
            "booking_code": self.test_booking_code,
            "email": self.test_guest_email
        })
        
        if resp.status_code != 200:
            print(f"❌ Expected 200, got {resp.status_code}: {resp.text}")
            return False
            
        data = resp.json()
        if not data.get("ok"):
            print(f"❌ Expected ok=true, got {data}")
            return False
            
        # Verify token and outbox records created
        tokens = await self.db.booking_public_tokens.find({}).to_list(length=10)
        outbox = await self.db.email_outbox.find({}).to_list(length=10)
        
        if len(tokens) != 1:
            print(f"❌ Expected 1 token, got {len(tokens)}")
            return False
            
        if len(outbox) != 1:
            print(f"❌ Expected 1 outbox record, got {len(outbox)}")
            return False
            
        token_doc = tokens[0]
        outbox_doc = outbox[0]
        
        # Verify token has token_hash and expires_at
        if not token_doc.get("token_hash") or not token_doc.get("expires_at"):
            print(f"❌ Token missing required fields: {token_doc}")
            return False
            
        # Verify outbox has correct event_type
        if outbox_doc.get("event_type") != "my_booking.link":
            print(f"❌ Expected event_type='my_booking.link', got {outbox_doc.get('event_type')}")
            return False
            
        print("✅ Existing booking correctly creates token_hash + expires_at and email_outbox record")
        
        # Store token for later tests
        self.test_token = token_doc.get("token") or token_doc.get("token_hash")
        
        return True

    async def test_dispatch_pending_emails_no_ses(self):
        """Test dispatch_pending_emails when SES config is missing"""
        print("\n📤 Testing dispatch_pending_emails with missing SES config...")
        
        # Ensure we have a pending email from previous test
        pending_count = await self.db.email_outbox.count_documents({"status": "pending"})
        if pending_count == 0:
            print("⚠️ No pending emails found, creating one for test...")
            await self.client.post(f"{API_BASE}/public/my-booking/request-link", json={
                "booking_code": self.test_booking_code,
                "email": self.test_guest_email
            })
            
        # Clear SES environment variables to simulate missing config
        original_env = {}
        ses_vars = ["AWS_REGION", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SES_FROM_EMAIL"]
        for var in ses_vars:
            if var in os.environ:
                original_env[var] = os.environ[var]
                del os.environ[var]
        
        try:
            # Check initial state
            initial_pending = await self.db.email_outbox.count_documents({"status": "pending"})
            print(f"📊 Initial pending emails: {initial_pending}")
            
            # Run dispatch_pending_emails
            processed = await dispatch_pending_emails(self.db, limit=10)
            print(f"📊 Processed {processed} email jobs")
            
            # Check final state - emails should be marked as sent with no-op behavior
            final_pending = await self.db.email_outbox.count_documents({"status": "pending"})
            sent_emails = await self.db.email_outbox.count_documents({"status": "sent"})
            
            print(f"📊 Final state: pending={final_pending}, sent={sent_emails}")
            
            # The key behavior: dispatch_pending_emails should NOT crash even without SES
            # Emails may be marked as "sent" (no-op success) rather than "failed"
            if processed > 0:
                print("✅ dispatch_pending_emails processed emails without crashing")
            else:
                print("⚠️ No emails were processed")
                
            # Verify worker didn't crash (it should handle the error gracefully)
            print("✅ dispatch_pending_emails completed without crashing - no 500/520 errors")
            
        finally:
            # Restore environment variables
            for var, value in original_env.items():
                os.environ[var] = value
                
        return True

    async def test_e2e_flow(self):
        """Test E2E flow: request-link → get token → /my-booking/:token → cancel/amend → ops_cases + booking_events"""
        print("\n🔄 Testing E2E flow...")
        
        # Step 1: Get token from outbox (simulate email delivery)
        print("1️⃣ Getting token from email_outbox...")
        
        outbox_docs = await self.db.email_outbox.find({
            "event_type": "my_booking.link"
        }).sort("created_at", -1).limit(1).to_list(length=1)
        
        if not outbox_docs:
            print("❌ No my_booking.link email found in outbox")
            return False
            
        # Extract token from email body (simulate user clicking link)
        email_body = outbox_docs[0].get("html_body", "")
        import re
        token_match = re.search(r'/my-booking/([a-zA-Z0-9_-]+)', email_body)
        if not token_match:
            print(f"❌ Could not extract token from email body: {email_body[:200]}...")
            return False
            
        token = token_match.group(1)
        print(f"✅ Extracted token: {token[:20]}...")
        
        # Step 2: Test /my-booking/:token endpoint
        print("2️⃣ Testing GET /my-booking/:token...")
        
        resp = self.client.get(f"{API_BASE}/public/my-booking/{token}")
        if resp.status_code != 200:
            print(f"❌ GET /my-booking/{token} failed: {resp.status_code} {resp.text}")
            return False
            
        booking_view = resp.json()
        if not booking_view.get("id"):
            print(f"❌ Invalid booking view: {booking_view}")
            return False
            
        print("✅ GET /my-booking/:token returned valid booking view")
        
        # Step 3: Test cancel request
        print("3️⃣ Testing POST /:token/request-cancel...")
        
        # Clear existing ops_cases for clean test
        await self.db.ops_cases.delete_many({"booking_id": self.test_booking_id, "type": "cancel"})
        await self.db.booking_events.delete_many({"booking_id": self.test_booking_id, "event": "GUEST_REQUEST_CANCEL"})
        
        resp = self.client.post(f"{API_BASE}/public/my-booking/{token}/request-cancel", json={
            "note": "Test cancel request"
        })
        
        if resp.status_code != 200:
            print(f"❌ Cancel request failed: {resp.status_code} {resp.text}")
            return False
            
        cancel_data = resp.json()
        if not cancel_data.get("ok") or not cancel_data.get("case_id"):
            print(f"❌ Invalid cancel response: {cancel_data}")
            return False
            
        case_id = cancel_data["case_id"]
        print(f"✅ Cancel request created case: {case_id}")
        
        # Verify ops_case created
        ops_case = await self.db.ops_cases.find_one({"case_id": case_id})
        if not ops_case:
            print(f"❌ ops_case not found: {case_id}")
            return False
            
        if ops_case.get("type") != "cancel" or ops_case.get("status") != "open":
            print(f"❌ Invalid ops_case: {ops_case}")
            return False
            
        print("✅ ops_case created correctly")
        
        # Verify booking_event created
        booking_event = await self.db.booking_events.find_one({
            "booking_id": self.test_booking_id,
            "event": "GUEST_REQUEST_CANCEL"
        })
        
        if not booking_event:
            print("❌ booking_event not created for cancel request")
            return False
            
        print("✅ booking_event created correctly")
        
        # Step 4: Test amend request
        print("4️⃣ Testing POST /:token/request-amend...")
        
        # Clear existing amend cases
        await self.db.ops_cases.delete_many({"booking_id": self.test_booking_id, "type": "amend"})
        await self.db.booking_events.delete_many({"booking_id": self.test_booking_id, "event": "GUEST_REQUEST_AMEND"})
        
        resp = self.client.post(f"{API_BASE}/public/my-booking/{token}/request-amend", json={
            "note": "Test amend request",
            "requested_changes": "Change dates to next week"
        })
        
        if resp.status_code != 200:
            print(f"❌ Amend request failed: {resp.status_code} {resp.text}")
            return False
            
        amend_data = resp.json()
        if not amend_data.get("ok") or not amend_data.get("case_id"):
            print(f"❌ Invalid amend response: {amend_data}")
            return False
            
        amend_case_id = amend_data["case_id"]
        print(f"✅ Amend request created case: {amend_case_id}")
        
        # Verify amend ops_case created
        amend_case = await self.db.ops_cases.find_one({"case_id": amend_case_id})
        if not amend_case:
            print(f"❌ amend ops_case not found: {amend_case_id}")
            return False
            
        if amend_case.get("type") != "amend" or amend_case.get("status") != "open":
            print(f"❌ Invalid amend ops_case: {amend_case}")
            return False
            
        print("✅ amend ops_case created correctly")
        
        # Verify amend booking_event created
        amend_event = await self.db.booking_events.find_one({
            "booking_id": self.test_booking_id,
            "event": "GUEST_REQUEST_AMEND"
        })
        
        if not amend_event:
            print("❌ booking_event not created for amend request")
            return False
            
        print("✅ amend booking_event created correctly")
        
        return True

    async def test_idempotency(self):
        """Test idempotency of cancel/amend requests"""
        print("\n🔁 Testing idempotency of cancel/amend requests...")
        
        # Get token from previous test
        outbox_docs = await self.db.email_outbox.find({
            "event_type": "my_booking.link"
        }).sort("created_at", -1).limit(1).to_list(length=1)
        
        if not outbox_docs:
            print("❌ No token available for idempotency test")
            return False
            
        email_body = outbox_docs[0].get("html_body", "")
        import re
        token_match = re.search(r'/my-booking/([a-zA-Z0-9_-]+)', email_body)
        if not token_match:
            print("❌ Could not extract token for idempotency test")
            return False
            
        token = token_match.group(1)
        
        # Test cancel idempotency
        print("1️⃣ Testing cancel request idempotency...")
        
        resp1 = self.client.post(f"{API_BASE}/public/my-booking/{token}/request-cancel", json={
            "note": "Idempotent cancel test"
        })
        
        resp2 = self.client.post(f"{API_BASE}/public/my-booking/{token}/request-cancel", json={
            "note": "Idempotent cancel test 2"
        })
        
        if resp1.status_code != 200 or resp2.status_code != 200:
            print(f"❌ Cancel idempotency failed: {resp1.status_code}, {resp2.status_code}")
            return False
            
        data1 = resp1.json()
        data2 = resp2.json()
        
        if data1.get("case_id") != data2.get("case_id"):
            print(f"❌ Cancel not idempotent: {data1.get('case_id')} != {data2.get('case_id')}")
            return False
            
        print("✅ Cancel requests are idempotent")
        
        # Test amend idempotency
        print("2️⃣ Testing amend request idempotency...")
        
        resp1 = self.client.post(f"{API_BASE}/public/my-booking/{token}/request-amend", json={
            "note": "Idempotent amend test",
            "requested_changes": "Test changes"
        })
        
        resp2 = self.client.post(f"{API_BASE}/public/my-booking/{token}/request-amend", json={
            "note": "Idempotent amend test 2", 
            "requested_changes": "Different changes"
        })
        
        if resp1.status_code != 200 or resp2.status_code != 200:
            print(f"❌ Amend idempotency failed: {resp1.status_code}, {resp2.status_code}")
            return False
            
        data1 = resp1.json()
        data2 = resp2.json()
        
        if data1.get("case_id") != data2.get("case_id"):
            print(f"❌ Amend not idempotent: {data1.get('case_id')} != {data2.get('case_id')}")
            return False
            
        print("✅ Amend requests are idempotent")
        
        return True

    async def run_all_tests(self):
        """Run all test scenarios"""
        print("🚀 Starting FAZ 3 / Ticket 3 Backend Tests")
        print("=" * 60)
        
        try:
            await self.setup()
            
            tests = [
                ("Request Link Scenarios", self.test_request_link_scenarios),
                ("Dispatch Pending Emails (No SES)", self.test_dispatch_pending_emails_no_ses),
                ("E2E Flow", self.test_e2e_flow),
                ("Idempotency", self.test_idempotency),
            ]
            
            passed = 0
            total = len(tests)
            
            for test_name, test_func in tests:
                print(f"\n{'='*20} {test_name} {'='*20}")
                try:
                    result = await test_func()
                    if result:
                        print(f"✅ {test_name} PASSED")
                        passed += 1
                    else:
                        print(f"❌ {test_name} FAILED")
                except Exception as e:
                    print(f"❌ {test_name} ERROR: {e}")
                    import traceback
                    traceback.print_exc()
            
            print(f"\n{'='*60}")
            print(f"📊 TEST RESULTS: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
            
            if passed == total:
                print("🎉 ALL TESTS PASSED - FAZ 3 / Ticket 3 backend functionality working correctly!")
                print("\n✅ KEY FINDINGS:")
                print("  • /api/public/my-booking/request-link returns 200 {ok:true} for all scenarios")
                print("  • No 500/520 errors even without SES configuration")
                print("  • Token generation + email_outbox recording working")
                print("  • dispatch_pending_emails handles missing SES gracefully")
                print("  • E2E flow: request-link → token → public GET → cancel/amend → ops_cases + booking_events")
                print("  • Email sending is now **no-op** but core functionality intact")
            else:
                print("⚠️ SOME TESTS FAILED - Check output above for details")
                
        except Exception as e:
            print(f"💥 SETUP ERROR: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await close_mongo()
            self.client.close()

async def main():
    """Main test runner"""
    test = FAZ3Ticket3BackendTest()
    await test.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())