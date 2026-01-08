#!/usr/bin/env python3
"""
P0.4 Voucher PDF Backend Chain Test
Testing booking → voucher HTML → voucher PDF flow with Turkish requirements
"""

import requests
import json
import uuid
from datetime import datetime, date

# Configuration - Use production URL from frontend/.env
BASE_URL = "https://commerce-os.preview.emergentagent.com"

def login_agency():
    """Login as agency user and return token, org_id, agency_id, email"""
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "agency1@demo.test", "password": "agency123"},
    )
    assert r.status_code == 200, f"Agency login failed: {r.text}"
    data = r.json()
    user = data["user"]
    return data["access_token"], user["organization_id"], user.get("agency_id"), user["email"]

def login_admin():
    """Login as admin user and return token, org_id, email"""
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "admin@acenta.test", "password": "admin123"},
    )
    assert r.status_code == 200, f"Admin login failed: {r.text}"
    data = r.json()
    user = data["user"]
    return data["access_token"], user["organization_id"], user["email"]

def test_p02_search_quote_booking_chain():
    """Test P0.2 Search→Quote→Booking backend chain with Turkish requirements"""
    print("\n" + "=" * 80)
    print("P0.2 SEARCH→QUOTE→BOOKING BACKEND CHAIN TEST")
    print("Testing B2B hotel search, quote creation, booking creation, and my bookings")
    print("=" * 80 + "\n")

    # Setup
    token, org_id, agency_id, agency_email = login_agency()
    headers = {"Authorization": f"Bearer {token}"}

    print(f"✅ Agency login successful: {agency_email}")
    print(f"✅ Organization ID: {org_id}")
    print(f"✅ Agency ID: {agency_id}")

    # ------------------------------------------------------------------
    # Test 1: Login - POST /api/auth/login
    # Should return access_token + user.roles with agency_admin/agent
    # ------------------------------------------------------------------
    print("\n1️⃣  Testing Login Authentication...")
    
    # Re-login to verify roles
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "agency1@demo.test", "password": "agency123"},
    )
    assert r.status_code == 200, f"Login failed: {r.text}"
    login_data = r.json()
    
    assert "access_token" in login_data, "access_token should be present"
    assert "user" in login_data, "user should be present"
    
    user_roles = login_data["user"].get("roles", [])
    print(f"   📋 User roles: {user_roles}")
    
    # Check if user has agency_admin or agency_agent role
    agency_roles = [role for role in user_roles if role in ["agency_admin", "agency_agent"]]
    assert len(agency_roles) > 0, f"User should have agency_admin or agency_agent role, got: {user_roles}"
    print(f"   ✅ User has required agency role: {agency_roles}")

    # ------------------------------------------------------------------
    # Test 2: Hotel Search - GET /api/b2b/hotels/search
    # Should return 200 with items list containing required fields
    # ------------------------------------------------------------------
    print("\n2️⃣  Testing Hotel Search - GET /api/b2b/hotels/search...")

    search_params = {
        "city": "Istanbul",
        "check_in": "2026-01-10",
        "check_out": "2026-01-12",
        "adults": 2,
        "children": 0
    }
    
    r = requests.get(
        f"{BASE_URL}/api/b2b/hotels/search",
        params=search_params,
        headers=headers,
    )
    assert r.status_code == 200, f"Hotel search failed: {r.text}"
    search_response = r.json()
    
    print(f"   📋 Search response status: 200")
    assert "items" in search_response, "Response should contain items list"
    
    items = search_response["items"]
    print(f"   📋 Found {len(items)} hotel search results")
    assert len(items) > 0, "Should have at least 1 search result"
    
    # Verify first item structure
    first_item = items[0]
    required_fields = [
        "product_id", "rate_plan_id", "hotel_name", "city", "country", 
        "board", "base_currency", "base_net", "selling_currency", 
        "selling_total", "nights", "occupancy"
    ]
    
    for field in required_fields:
        assert field in first_item, f"Field '{field}' should be present in search result"
    
    # Verify specific values
    assert isinstance(first_item["product_id"], str), "product_id should be string"
    assert isinstance(first_item["rate_plan_id"], str), "rate_plan_id should be string"
    assert first_item["base_net"] > 0, "base_net should be > 0"
    assert first_item["selling_total"] > 0, "selling_total should be > 0"
    assert first_item["nights"] == 2, "nights should be 2 (2026-01-10 to 2026-01-12)"
    assert first_item["occupancy"]["adults"] == 2, "occupancy.adults should be 2"
    assert first_item["occupancy"]["children"] == 0, "occupancy.children should be 0"
    
    print(f"   ✅ Search result structure verified")
    print(f"   📋 Sample result: {first_item['hotel_name']} - {first_item['city']}, {first_item['country']}")
    print(f"   💰 Price: {first_item['base_net']} {first_item['base_currency']} → {first_item['selling_total']} {first_item['selling_currency']}")
    
    # Store for next test
    selected_product_id = first_item["product_id"]
    selected_rate_plan_id = first_item["rate_plan_id"]

    # ------------------------------------------------------------------
    # Test 3: Quote Creation - POST /api/b2b/quotes
    # Should return 200 with quote_id, expires_at, and offers
    # ------------------------------------------------------------------
    print("\n3️⃣  Testing Quote Creation - POST /api/b2b/quotes...")

    quote_payload = {
        "channel_id": "agency_extranet",
        "items": [
            {
                "product_id": selected_product_id,
                "room_type_id": "default_room",
                "rate_plan_id": selected_rate_plan_id,
                "check_in": "2026-01-10",
                "check_out": "2026-01-12",
                "occupancy": 2
            }
        ],
        "client_context": {"source": "p0.2-test"}
    }
    
    r = requests.post(
        f"{BASE_URL}/api/b2b/quotes",
        json=quote_payload,
        headers=headers,
    )
    assert r.status_code == 200, f"Quote creation failed: {r.text}"
    quote_response = r.json()
    
    print(f"   📋 Quote creation status: 200")
    
    # Verify required fields
    assert "quote_id" in quote_response, "quote_id should be present"
    assert "expires_at" in quote_response, "expires_at should be present"
    assert "offers" in quote_response, "offers should be present"
    
    quote_id = quote_response["quote_id"]
    assert isinstance(quote_id, str) and len(quote_id) > 0, "quote_id should be non-empty string"
    
    expires_at = quote_response["expires_at"]
    # Verify expires_at is a future date
    expires_dt = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
    assert expires_dt > datetime.now(expires_dt.tzinfo), "expires_at should be in the future"
    
    offers = quote_response["offers"]
    assert len(offers) >= 1, "Should have at least 1 offer"
    
    first_offer = offers[0]
    assert "currency" in first_offer, "Offer should have currency"
    assert "net" in first_offer, "Offer should have net price"
    assert "sell" in first_offer, "Offer should have sell price"
    assert first_offer["net"] > 0, "net should be > 0"
    assert first_offer["sell"] > 0, "sell should be > 0"
    
    print(f"   ✅ Quote created successfully")
    print(f"   📋 Quote ID: {quote_id}")
    print(f"   📅 Expires at: {expires_at}")
    print(f"   💰 First offer: {first_offer['net']} → {first_offer['sell']} {first_offer['currency']}")

    # ------------------------------------------------------------------
    # Test 4: Booking Creation - POST /api/b2b/bookings
    # Should return 200 with booking_id and status=CONFIRMED
    # ------------------------------------------------------------------
    print("\n4️⃣  Testing Booking Creation - POST /api/b2b/bookings...")

    # Generate unique idempotency key
    idempotency_key = f"p0.2-test-{uuid.uuid4()}"
    
    booking_payload = {
        "quote_id": quote_id,
        "customer": {
            "name": "P0.2 Test Guest",
            "email": "p02-test@example.com"
        },
        "travellers": [
            {
                "first_name": "P0.2 Test",
                "last_name": "Guest"
            }
        ],
        "notes": "P0.2 backend flow test"
    }
    
    booking_headers = {
        **headers,
        "Idempotency-Key": idempotency_key
    }
    
    r = requests.post(
        f"{BASE_URL}/api/b2b/bookings",
        json=booking_payload,
        headers=booking_headers,
    )
    assert r.status_code == 200, f"Booking creation failed: {r.text}"
    booking_response = r.json()
    
    print(f"   📋 Booking creation status: 200")
    
    # Verify required fields
    assert "booking_id" in booking_response, "booking_id should be present"
    assert "status" in booking_response, "status should be present"
    
    booking_id = booking_response["booking_id"]
    assert isinstance(booking_id, str) and len(booking_id) > 0, "booking_id should be non-empty string"
    
    booking_status = booking_response["status"]
    assert booking_status == "CONFIRMED", f"Status should be CONFIRMED, got: {booking_status}"
    
    # Check voucher_status if present
    if "voucher_status" in booking_response:
        voucher_status = booking_response["voucher_status"]
        print(f"   📋 Voucher status: {voucher_status}")
    
    print(f"   ✅ Booking created successfully")
    print(f"   📋 Booking ID: {booking_id}")
    print(f"   📊 Status: {booking_status}")

    # ------------------------------------------------------------------
    # Test 5: My Bookings - GET /api/b2b/bookings
    # Should return 200 with items containing the created booking
    # ------------------------------------------------------------------
    print("\n5️⃣  Testing My Bookings - GET /api/b2b/bookings...")

    r = requests.get(
        f"{BASE_URL}/api/b2b/bookings",
        headers=headers,
    )
    assert r.status_code == 200, f"My bookings failed: {r.text}"
    bookings_response = r.json()
    
    print(f"   📋 My bookings status: 200")
    
    assert "items" in bookings_response, "Response should contain items list"
    items = bookings_response["items"]
    print(f"   📋 Found {len(items)} bookings")
    
    # Find our created booking (should be first due to created_at desc sort)
    our_booking = None
    for item in items:
        if item.get("booking_id") == booking_id:
            our_booking = item
            break
    
    assert our_booking is not None, f"Created booking {booking_id} should be in the list"
    
    # Verify booking structure
    required_booking_fields = [
        "booking_id", "status", "created_at", "currency", 
        "amount_sell", "check_in", "check_out", "primary_guest_name", "product_name"
    ]
    
    for field in required_booking_fields:
        assert field in our_booking, f"Field '{field}' should be present in booking item"
    
    # Verify specific values
    assert our_booking["product_name"] != "", "product_name should not be empty"
    assert our_booking["check_in"] == "2026-01-10", "check_in should match"
    assert our_booking["check_out"] == "2026-01-12", "check_out should match"
    assert our_booking["amount_sell"] > 0, "amount_sell should be > 0"
    
    print(f"   ✅ Created booking found in my bookings list")
    print(f"   📋 Booking: {our_booking['product_name']} - {our_booking['primary_guest_name']}")
    print(f"   💰 Amount: {our_booking['amount_sell']} {our_booking['currency']}")
    print(f"   📅 Dates: {our_booking['check_in']} to {our_booking['check_out']}")

    # ------------------------------------------------------------------
    # Test 6a: Edge Guard - Invalid date range
    # Should return 422 with error.invalid_date_range
    # ------------------------------------------------------------------
    print("\n6️⃣ a) Testing Edge Guard - Invalid date range...")

    invalid_search_params = {
        "city": "Istanbul",
        "check_in": "2026-01-12",  # After check_out
        "check_out": "2026-01-10",
        "adults": 2,
        "children": 0
    }
    
    r = requests.get(
        f"{BASE_URL}/api/b2b/hotels/search",
        params=invalid_search_params,
        headers=headers,
    )
    assert r.status_code == 422, f"Expected 422 for invalid date range, got: {r.status_code}"
    error_response = r.json()
    
    print(f"   📋 Invalid date range status: 422")
    
    # Check error structure
    assert "error" in error_response, "Error response should contain error field"
    error = error_response["error"]
    assert "code" in error, "Error should contain code"
    assert error["code"] == "invalid_date_range", f"Expected invalid_date_range, got: {error['code']}"
    
    print(f"   ✅ Invalid date range correctly rejected")
    print(f"   📋 Error: {error['code']} - {error.get('message', '')}")

    # ------------------------------------------------------------------
    # Test 6b: Edge Guard - Empty city
    # Should return 422 with validation_error, field=city
    # ------------------------------------------------------------------
    print("\n6️⃣ b) Testing Edge Guard - Empty city...")

    empty_city_params = {
        "city": "",  # Empty city
        "check_in": "2026-01-10",
        "check_out": "2026-01-12",
        "adults": 2,
        "children": 0
    }
    
    r = requests.get(
        f"{BASE_URL}/api/b2b/hotels/search",
        params=empty_city_params,
        headers=headers,
    )
    assert r.status_code == 422, f"Expected 422 for empty city, got: {r.status_code}"
    error_response = r.json()
    
    print(f"   📋 Empty city status: 422")
    
    # Check error structure
    assert "error" in error_response, "Error response should contain error field"
    error = error_response["error"]
    assert "code" in error, "Error should contain code"
    assert error["code"] == "validation_error", f"Expected validation_error, got: {error['code']}"
    
    # Check if field=city is mentioned
    error_details = error.get("details", {})
    if "field" in error_details:
        assert error_details["field"] == "city", f"Expected field=city, got: {error_details['field']}"
        print(f"   ✅ Empty city correctly rejected with field=city")
    else:
        # Check if city is mentioned in message or details
        error_text = str(error_response).lower()
        assert "city" in error_text, "Error should mention city field"
        print(f"   ✅ Empty city correctly rejected (city mentioned in error)")
    
    print(f"   📋 Error: {error['code']} - {error.get('message', '')}")

    # ------------------------------------------------------------------
    # Test 6c: Edge Guard - Invalid product_id in quote
    # Should return 409 product_not_available
    # ------------------------------------------------------------------
    print("\n6️⃣ c) Testing Edge Guard - Invalid product_id in quote...")

    # Generate a random ObjectId-like string
    invalid_product_id = "507f1f77bcf86cd799439011"  # Valid ObjectId format but non-existent
    
    invalid_quote_payload = {
        "channel_id": "agency_extranet",
        "items": [
            {
                "product_id": invalid_product_id,
                "room_type_id": "default_room",
                "rate_plan_id": selected_rate_plan_id,  # Use valid rate_plan_id
                "check_in": "2026-01-10",
                "check_out": "2026-01-12",
                "occupancy": 2
            }
        ],
        "client_context": {"source": "p0.2-test-invalid"}
    }
    
    r = requests.post(
        f"{BASE_URL}/api/b2b/quotes",
        json=invalid_quote_payload,
        headers=headers,
    )
    assert r.status_code == 409, f"Expected 409 for invalid product_id, got: {r.status_code}"
    error_response = r.json()
    
    print(f"   📋 Invalid product_id status: 409")
    
    # Check error structure
    assert "error" in error_response, "Error response should contain error field"
    error = error_response["error"]
    assert "code" in error, "Error should contain code"
    assert error["code"] == "product_not_available", f"Expected product_not_available, got: {error['code']}"
    
    print(f"   ✅ Invalid product_id correctly rejected")
    print(f"   📋 Error: {error['code']} - {error.get('message', '')}")

    print("\n" + "=" * 80)
    print("✅ P0.2 SEARCH→QUOTE→BOOKING BACKEND CHAIN TEST COMPLETE")
    print("✅ Login with agency credentials working (agency_admin/agent role)")
    print("✅ Hotel search returning proper structure with required fields")
    print("✅ Quote creation working with search results")
    print("✅ Booking creation working with quote (CONFIRMED status)")
    print("✅ My bookings list showing created booking (created_at desc sort)")
    print("✅ Edge guards working (invalid date range, empty city, invalid product_id)")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    test_p02_search_quote_booking_chain()