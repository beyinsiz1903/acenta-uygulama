#!/usr/bin/env python3
"""
FAZ 2 / F2.FE.T3 Public booking summary endpoint ve complete sayfası entegrasyonunu test et.

Backend test for public booking summary API endpoints.
"""

import json
import requests
import sys
from datetime import datetime

# Use the production backend URL from frontend .env
BACKEND_URL = "https://bookingsuite-7.preview.emergentagent.com"

def test_public_booking_summary_happy_path():
    """Test GET /api/public/bookings/by-code/PB-TEST123?org=org_public_summary"""
    print("🧪 Testing public booking summary happy path...")
    
    url = f"{BACKEND_URL}/api/public/bookings/by-code/PB-TEST123"
    params = {"org": "org_public_summary"}
    
    try:
        response = requests.get(url, params=params, timeout=10)
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   Response: {json.dumps(data, indent=2)}")
            
            # Verify response structure
            assert data["ok"] is True, "Response should have ok=true"
            
            booking = data["booking"]
            assert booking["booking_code"] == "PB-TEST123", "Booking code should match"
            
            # Verify price structure
            assert "price" in booking, "Booking should have price field"
            assert "amount_cents" in booking["price"], "Price should have amount_cents"
            assert "currency" in booking["price"], "Price should have currency"
            assert booking["price"]["currency"] == "EUR", "Currency should be EUR"
            
            # Verify PII protection - guest fields should NOT be present
            assert "guest" not in booking, "Guest PII should not be present"
            assert "email" not in booking, "Email PII should not be present"
            assert "phone" not in booking, "Phone PII should not be present"
            assert "full_name" not in booking, "Full name PII should not be present"
            
            # Verify required fields are present
            required_fields = ["booking_code", "status", "price", "pax", "product"]
            for field in required_fields:
                assert field in booking, f"Required field '{field}' should be present"
            
            print("   ✅ Happy path test PASSED")
            print(f"   ✅ PII protection verified - no guest fields in response")
            print(f"   ✅ Price: {booking['price']['amount_cents']} cents {booking['price']['currency']}")
            return True
            
        else:
            print(f"   ❌ Expected 200, got {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def test_public_booking_summary_not_found():
    """Test GET /api/public/bookings/by-code/NONEXISTENT?org=org_public_summary"""
    print("🧪 Testing public booking summary not found...")
    
    url = f"{BACKEND_URL}/api/public/bookings/by-code/NONEXISTENT"
    params = {"org": "org_public_summary"}
    
    try:
        response = requests.get(url, params=params, timeout=10)
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 404:
            data = response.json()
            print(f"   Response: {json.dumps(data, indent=2)}")
            
            # Verify error response
            assert data["detail"] == "NOT_FOUND", "Should return NOT_FOUND error"
            
            print("   ✅ Not found test PASSED")
            return True
            
        else:
            print(f"   ❌ Expected 404, got {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def test_public_booking_summary_different_org():
    """Test with different org parameter to verify tenant isolation"""
    print("🧪 Testing public booking summary with different org...")
    
    url = f"{BACKEND_URL}/api/public/bookings/by-code/PB-TEST123"
    params = {"org": "different_org"}
    
    try:
        response = requests.get(url, params=params, timeout=10)
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 404:
            data = response.json()
            print(f"   Response: {json.dumps(data, indent=2)}")
            
            # Verify error response
            assert data["detail"] == "NOT_FOUND", "Should return NOT_FOUND for different org"
            
            print("   ✅ Tenant isolation test PASSED")
            return True
            
        else:
            print(f"   ❌ Expected 404, got {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def main():
    """Run all backend tests"""
    print("🚀 Starting FAZ 2 / F2.FE.T3 Public Booking Summary Backend Tests")
    print(f"🌐 Backend URL: {BACKEND_URL}")
    print("=" * 80)
    
    tests = [
        test_public_booking_summary_happy_path,
        test_public_booking_summary_not_found,
        test_public_booking_summary_different_org,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
            print()
        except Exception as e:
            print(f"   ❌ Test failed with exception: {e}")
            print()
    
    print("=" * 80)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All backend tests PASSED!")
        return 0
    else:
        print("❌ Some backend tests FAILED!")
        return 1

if __name__ == "__main__":
    sys.exit(main())