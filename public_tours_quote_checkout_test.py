#!/usr/bin/env python3
"""
Public Tour Quote & Checkout API Smoke Test

This script tests the new endpoints in /app/backend/app/routers/public_tours.py:
- POST /api/public/tours/quote
- POST /api/public/tours/checkout

Environment assumptions:
- Uses the existing preview backend URL from frontend/.env (REACT_APP_BACKEND_URL)
- Organization id: 695e03c80b04ed31c4eaa899
"""

import asyncio
import json
import os
import sys
from datetime import date, datetime
from typing import Any, Dict, Optional

import aiohttp
from motor.motor_asyncio import AsyncIOMotorClient


# Configuration
BACKEND_URL = "https://b2bportal-3.preview.emergentagent.com"
ORG_ID = "695e03c80b04ed31c4eaa899"
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")


class TestResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
        
    def assert_equal(self, actual, expected, message=""):
        if actual == expected:
            self.passed += 1
            print(f"✅ PASS: {message}")
        else:
            self.failed += 1
            error_msg = f"❌ FAIL: {message} - Expected: {expected}, Got: {actual}"
            print(error_msg)
            self.errors.append(error_msg)
    
    def assert_true(self, condition, message=""):
        if condition:
            self.passed += 1
            print(f"✅ PASS: {message}")
        else:
            self.failed += 1
            error_msg = f"❌ FAIL: {message}"
            print(error_msg)
            self.errors.append(error_msg)
    
    def assert_in(self, item, container, message=""):
        if item in container:
            self.passed += 1
            print(f"✅ PASS: {message}")
        else:
            self.failed += 1
            error_msg = f"❌ FAIL: {message} - {item} not found in {container}"
            print(error_msg)
            self.errors.append(error_msg)
    
    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*60}")
        print(f"TEST SUMMARY: {self.passed}/{total} passed")
        if self.failed > 0:
            print(f"FAILED TESTS: {self.failed}")
            for error in self.errors:
                print(f"  - {error}")
        print(f"{'='*60}")


async def setup_test_data() -> Optional[str]:
    """Insert a minimal tour document and return its _id"""
    print("🔧 Setting up test data...")
    
    try:
        client = AsyncIOMotorClient(MONGO_URL)
        db = client[DB_NAME]
        
        # Check if tour already exists
        existing_tour = await db.tours.find_one({
            "organization_id": ORG_ID,
            "name": "Test Tour Backend"
        })
        
        if existing_tour:
            tour_id = str(existing_tour["_id"])
            print(f"✅ Using existing tour: {tour_id}")
            client.close()
            return tour_id
        
        # Insert new tour
        tour_doc = {
            "organization_id": ORG_ID,
            "name": "Test Tour Backend",
            "destination": "Istanbul",
            "base_price": 120.0,
            "currency": "EUR",
            "status": "active",
            "created_at": datetime.utcnow(),
            "type": "tour"
        }
        
        result = await db.tours.insert_one(tour_doc)
        tour_id = str(result.inserted_id)
        print(f"✅ Created new tour: {tour_id}")
        
        client.close()
        return tour_id
        
    except Exception as e:
        print(f"❌ Failed to setup test data: {e}")
        return None


async def make_request(session: aiohttp.ClientSession, method: str, url: str, 
                      json_data: Optional[Dict] = None, params: Optional[Dict] = None) -> tuple:
    """Make HTTP request and return (status, response_data)"""
    try:
        async with session.request(method, url, json=json_data, params=params) as response:
            try:
                data = await response.json()
            except:
                data = await response.text()
            return response.status, data
    except Exception as e:
        return 0, {"error": str(e)}


def print_request(method: str, url: str, body: Optional[Dict] = None):
    """Print HTTP request details"""
    print(f"\n📤 {method} {url}")
    if body:
        # Print short body for readability
        body_str = json.dumps(body, indent=2)
        if len(body_str) > 200:
            body_str = body_str[:200] + "..."
        print(f"   Body: {body_str}")


def print_response(status: int, data: Any):
    """Print HTTP response details"""
    print(f"📥 Response: {status}")
    if isinstance(data, dict):
        # Print key fields for readability
        key_fields = ["ok", "quote_id", "expires_at", "amount_cents", "currency", 
                     "booking_id", "booking_code", "code", "message"]
        filtered_data = {k: v for k, v in data.items() if k in key_fields}
        if filtered_data:
            print(f"   Key fields: {json.dumps(filtered_data, indent=2)}")
        else:
            print(f"   Data: {json.dumps(data, indent=2)}")
    else:
        print(f"   Data: {data}")


async def test_tour_quote_happy_path(session: aiohttp.ClientSession, tour_id: str, results: TestResults) -> Optional[str]:
    """Test POST /api/public/tours/quote happy path"""
    print("\n" + "="*60)
    print("TEST 1: POST /api/public/tours/quote (Happy Path)")
    print("="*60)
    
    url = f"{BACKEND_URL}/api/public/tours/quote"
    today = date.today().isoformat()
    
    payload = {
        "org": ORG_ID,
        "tour_id": tour_id,
        "date": today,
        "pax": {"adults": 2, "children": 1},
        "currency": "EUR"
    }
    
    print_request("POST", url, payload)
    status, data = await make_request(session, "POST", url, json_data=payload)
    print_response(status, data)
    
    # Assertions
    results.assert_equal(status, 200, "HTTP status should be 200")
    
    if isinstance(data, dict):
        results.assert_equal(data.get("ok"), True, "Response should have ok=true")
        results.assert_true("quote_id" in data, "Response should have quote_id")
        results.assert_true("expires_at" in data, "Response should have expires_at")
        results.assert_true("amount_cents" in data, "Response should have amount_cents")
        results.assert_equal(data.get("currency"), "EUR", "Currency should be EUR")
        results.assert_true("breakdown" in data, "Response should have breakdown")
        results.assert_true("pax" in data, "Response should have pax")
        results.assert_true("date" in data, "Response should have date")
        results.assert_true("tour" in data, "Response should have tour")
        
        # Check amount calculation: (base_price * participants) * 1.1 (10% tax)
        # base_price = 120.0, participants = 2 + 1 = 3
        # expected = (120.0 * 3) * 1.1 = 396.0 EUR = 39600 cents
        expected_amount = int((120.0 * 3) * 1.1 * 100)
        results.assert_equal(data.get("amount_cents"), expected_amount, 
                           f"Amount should be {expected_amount} cents (120 EUR * 3 pax * 1.1 tax)")
        
        if data.get("amount_cents", 0) > 0:
            results.assert_true(True, "Amount cents should be > 0")
        else:
            results.assert_true(False, "Amount cents should be > 0")
        
        return data.get("quote_id")
    
    return None


async def test_tour_quote_validation_errors(session: aiohttp.ClientSession, results: TestResults):
    """Test POST /api/public/tours/quote validation and error paths"""
    print("\n" + "="*60)
    print("TEST 2: POST /api/public/tours/quote (Validation/Error Paths)")
    print("="*60)
    
    url = f"{BACKEND_URL}/api/public/tours/quote"
    today = date.today().isoformat()
    
    # Test 2a: Invalid tour_id (random 24-char hex)
    print("\n--- Test 2a: Invalid tour_id ---")
    invalid_tour_id = "507f1f77bcf86cd799439011"  # Valid ObjectId format but doesn't exist
    payload = {
        "org": ORG_ID,
        "tour_id": invalid_tour_id,
        "date": today,
        "pax": {"adults": 2, "children": 1},
        "currency": "EUR"
    }
    
    print_request("POST", url, payload)
    status, data = await make_request(session, "POST", url, json_data=payload)
    print_response(status, data)
    
    results.assert_equal(status, 404, "Invalid tour_id should return 404")
    if isinstance(data, dict):
        results.assert_equal(data.get("code"), "TOUR_NOT_FOUND", "Should return TOUR_NOT_FOUND code")
    
    # Test 2b: Invalid pax (adults=0)
    print("\n--- Test 2b: Invalid pax (adults=0) ---")
    payload = {
        "org": ORG_ID,
        "tour_id": "507f1f77bcf86cd799439011",  # Doesn't matter, validation should fail first
        "date": today,
        "pax": {"adults": 0, "children": 1},  # Invalid: adults must be >= 1
        "currency": "EUR"
    }
    
    print_request("POST", url, payload)
    status, data = await make_request(session, "POST", url, json_data=payload)
    print_response(status, data)
    
    results.assert_equal(status, 422, "Invalid pax (adults=0) should return 422 from pydantic validation")


async def test_tour_checkout_happy_path(session: aiohttp.ClientSession, quote_id: str, results: TestResults) -> Optional[tuple]:
    """Test POST /api/public/tours/checkout happy path"""
    print("\n" + "="*60)
    print("TEST 3: POST /api/public/tours/checkout (Happy Path)")
    print("="*60)
    
    if not quote_id:
        print("❌ Skipping checkout test - no valid quote_id from previous test")
        return None
    
    url = f"{BACKEND_URL}/api/public/tours/checkout"
    
    payload = {
        "org": ORG_ID,
        "quote_id": quote_id,
        "guest": {
            "full_name": "Test Guest",
            "email": "guest@example.com",
            "phone": "+905551112233"
        }
    }
    
    print_request("POST", url, payload)
    status, data = await make_request(session, "POST", url, json_data=payload)
    print_response(status, data)
    
    # Assertions
    results.assert_equal(status, 200, "HTTP status should be 200")
    
    if isinstance(data, dict):
        results.assert_equal(data.get("ok"), True, "Response should have ok=true")
        results.assert_true("booking_id" in data, "Response should have booking_id")
        results.assert_true("booking_code" in data, "Response should have booking_code")
        
        booking_id = data.get("booking_id")
        booking_code = data.get("booking_code")
        
        if booking_id:
            results.assert_true(len(booking_id) > 0, "booking_id should be non-empty string")
        
        if booking_code:
            results.assert_true(booking_code.startswith("TT-"), "booking_code should start with 'TT-'")
        
        return booking_id, booking_code
    
    return None


async def verify_booking_in_mongo(booking_id: str, quote_id: str, results: TestResults):
    """Verify booking was created correctly in MongoDB"""
    print("\n" + "="*60)
    print("TEST 4: Verify Booking in MongoDB")
    print("="*60)
    
    if not booking_id:
        print("❌ Skipping MongoDB verification - no booking_id")
        return
    
    try:
        from bson import ObjectId
        
        client = AsyncIOMotorClient(MONGO_URL)
        db = client[DB_NAME]
        
        # Find the booking
        booking = await db.bookings.find_one({"_id": ObjectId(booking_id)})
        
        if not booking:
            results.assert_true(False, f"Booking {booking_id} should exist in MongoDB")
            return
        
        print(f"✅ Found booking in MongoDB: {booking_id}")
        
        # Verify booking fields
        results.assert_equal(booking.get("organization_id"), ORG_ID, "Booking should have correct organization_id")
        results.assert_equal(booking.get("source"), "public_tour", "Booking source should be 'public_tour'")
        results.assert_equal(booking.get("product_type"), "tour", "Product type should be 'tour'")
        results.assert_equal(booking.get("currency"), "EUR", "Currency should be 'EUR'")
        
        # Check product title matches tour name
        expected_title = "Test Tour Backend"
        actual_title = booking.get("product_title")
        results.assert_equal(actual_title, expected_title, f"Product title should be '{expected_title}'")
        
        # Check amount matches quote
        expected_amount = int((120.0 * 3) * 1.1 * 100)  # Same calculation as quote
        actual_amount = booking.get("amount_total_cents")
        results.assert_equal(actual_amount, expected_amount, f"Amount should be {expected_amount} cents")
        
        # Check public_quote fields
        public_quote = booking.get("public_quote", {})
        today = date.today().isoformat()
        results.assert_equal(public_quote.get("date_from"), today, f"date_from should be {today}")
        results.assert_equal(public_quote.get("date_to"), today, f"date_to should be {today}")
        
        await client.close()
        
    except Exception as e:
        results.assert_true(False, f"MongoDB verification failed: {e}")


async def test_tour_checkout_error_paths(session: aiohttp.ClientSession, results: TestResults):
    """Test POST /api/public/tours/checkout error paths"""
    print("\n" + "="*60)
    print("TEST 5: POST /api/public/tours/checkout (Error Paths)")
    print("="*60)
    
    url = f"{BACKEND_URL}/api/public/tours/checkout"
    
    # Test 5a: Non-existent quote_id
    print("\n--- Test 5a: Non-existent quote_id ---")
    fake_quote_id = "tq_nonexistent123456"
    payload = {
        "org": ORG_ID,
        "quote_id": fake_quote_id,
        "guest": {
            "full_name": "Test Guest",
            "email": "guest@example.com",
            "phone": "+905551112233"
        }
    }
    
    print_request("POST", url, payload)
    status, data = await make_request(session, "POST", url, json_data=payload)
    print_response(status, data)
    
    results.assert_equal(status, 404, "Non-existent quote_id should return 404")
    if isinstance(data, dict):
        results.assert_equal(data.get("code"), "QUOTE_NOT_FOUND", "Should return QUOTE_NOT_FOUND code")


async def test_expired_quote_scenario(session: aiohttp.ClientSession, tour_id: str, results: TestResults):
    """Test expired quote scenario (optional)"""
    print("\n" + "="*60)
    print("TEST 6: Expired Quote Scenario (Optional)")
    print("="*60)
    
    # This test would require manually updating a quote's expires_at in MongoDB
    # For now, we'll skip this as it's marked optional in the requirements
    print("⚠️  Skipping expired quote test - requires manual MongoDB manipulation")
    print("   To test: Create quote, manually update expires_at to past time, then checkout")


async def main():
    """Main test runner"""
    print("🚀 Starting Public Tour Quote & Checkout API Smoke Test")
    print(f"Backend URL: {BACKEND_URL}")
    print(f"Organization ID: {ORG_ID}")
    
    results = TestResults()
    
    # Setup test data
    tour_id = await setup_test_data()
    if not tour_id:
        print("❌ Failed to setup test data. Exiting.")
        return
    
    print(f"📋 Using TOUR_ID: {tour_id}")
    
    async with aiohttp.ClientSession() as session:
        # Test 1: Quote happy path
        quote_id = await test_tour_quote_happy_path(session, tour_id, results)
        
        # Test 2: Quote validation errors
        await test_tour_quote_validation_errors(session, results)
        
        # Test 3: Checkout happy path
        booking_result = await test_tour_checkout_happy_path(session, quote_id, results)
        
        # Test 4: Verify booking in MongoDB
        if booking_result:
            booking_id, booking_code = booking_result
            print(f"📋 Created BOOKING_ID: {booking_id}")
            print(f"📋 Created BOOKING_CODE: {booking_code}")
            await verify_booking_in_mongo(booking_id, quote_id, results)
        
        # Test 5: Checkout error paths
        await test_tour_checkout_error_paths(session, results)
        
        # Test 6: Expired quote (optional)
        await test_expired_quote_scenario(session, tour_id, results)
    
    # Print final summary
    results.summary()
    
    # Exit with appropriate code
    if results.failed > 0:
        sys.exit(1)
    else:
        print("🎉 All tests passed!")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())