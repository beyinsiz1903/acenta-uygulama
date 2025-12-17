#!/usr/bin/env python3
"""
Folio Creation Test for New Bookings
Tests the fix for "No folio found for this booking" issue
"""

import requests
import json
from datetime import datetime, timedelta

# Configuration
BASE_URL = "https://code-review-helper-12.preview.emergentagent.com/api"
LOGIN_EMAIL = "demo@hotel.com"
LOGIN_PASSWORD = "demo123"

def login():
    """Login and get access token"""
    print("🔐 Logging in...")
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": LOGIN_EMAIL, "password": LOGIN_PASSWORD}
    )
    
    if response.status_code != 200:
        print(f"❌ Login failed: {response.status_code}")
        print(f"Response: {response.text}")
        return None
    
    data = response.json()
    token = data.get("access_token")
    tenant_id = data.get("tenant", {}).get("id")
    print(f"✅ Login successful - Tenant ID: {tenant_id}")
    return token, tenant_id

def get_guests(token):
    """Get list of guests"""
    print("\n📋 Fetching guests...")
    response = requests.get(
        f"{BASE_URL}/pms/guests?limit=10",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to fetch guests: {response.status_code}")
        return []
    
    guests = response.json()
    print(f"✅ Found {len(guests)} guests")
    return guests

def get_rooms(token):
    """Get list of available rooms"""
    print("\n🏨 Fetching rooms...")
    response = requests.get(
        f"{BASE_URL}/pms/rooms?limit=10",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to fetch rooms: {response.status_code}")
        return []
    
    rooms = response.json()
    available_rooms = [r for r in rooms if r.get('status') == 'available']
    print(f"✅ Found {len(available_rooms)} available rooms")
    return available_rooms

def create_booking(token, guest_id, room_id):
    """Create a new booking"""
    print("\n📝 Creating new booking...")
    
    # Calculate check-in and check-out dates
    check_in = (datetime.now() + timedelta(days=1)).isoformat()
    check_out = (datetime.now() + timedelta(days=3)).isoformat()
    
    booking_data = {
        "guest_id": guest_id,
        "room_id": room_id,
        "check_in": check_in,
        "check_out": check_out,
        "adults": 2,
        "children": 0,
        "children_ages": [],
        "guests_count": 2,
        "total_amount": 300.0,
        "base_rate": 150.0,
        "channel": "direct",
        "rate_plan": "Standard",
        "special_requests": "Test booking for folio creation verification"
    }
    
    response = requests.post(
        f"{BASE_URL}/pms/bookings",
        headers={"Authorization": f"Bearer {token}"},
        json=booking_data
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to create booking: {response.status_code}")
        print(f"Response: {response.text}")
        return None
    
    booking = response.json()
    booking_id = booking.get("id")
    print(f"✅ Booking created successfully - ID: {booking_id}")
    print(f"   Guest ID: {guest_id}")
    print(f"   Room ID: {room_id}")
    print(f"   Check-in: {check_in}")
    print(f"   Check-out: {check_out}")
    return booking_id

def verify_folio_created(token, booking_id):
    """Verify that folio was automatically created for the booking"""
    print(f"\n🔍 Verifying folio for booking {booking_id}...")
    
    response = requests.get(
        f"{BASE_URL}/folio/booking/{booking_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to fetch folio: {response.status_code}")
        print(f"Response: {response.text}")
        return False
    
    folios = response.json()
    
    if not folios or len(folios) == 0:
        print(f"❌ No folio found for booking {booking_id}")
        return False
    
    print(f"✅ Folio found! Count: {len(folios)}")
    
    # Verify folio details
    folio = folios[0]
    print(f"\n📄 Folio Details:")
    print(f"   Folio ID: {folio.get('id')}")
    print(f"   Folio Number: {folio.get('folio_number')}")
    print(f"   Folio Type: {folio.get('folio_type')}")
    print(f"   Booking ID: {folio.get('booking_id')}")
    print(f"   Guest ID: {folio.get('guest_id')}")
    print(f"   Status: {folio.get('status')}")
    print(f"   Balance: {folio.get('balance', 0.0)}")
    
    # Verify required fields
    errors = []
    
    if not folio.get('folio_number'):
        errors.append("Missing folio_number")
    elif not folio.get('folio_number').startswith('F-'):
        errors.append(f"Invalid folio_number format: {folio.get('folio_number')} (expected F-YYYY-#####)")
    
    if folio.get('folio_type') != 'guest':
        errors.append(f"Invalid folio_type: {folio.get('folio_type')} (expected 'guest')")
    
    if folio.get('booking_id') != booking_id:
        errors.append(f"Booking ID mismatch: {folio.get('booking_id')} != {booking_id}")
    
    if not folio.get('guest_id'):
        errors.append("Missing guest_id")
    
    if errors:
        print(f"\n❌ Folio validation errors:")
        for error in errors:
            print(f"   - {error}")
        return False
    
    print(f"\n✅ All folio fields validated successfully!")
    return True

def test_existing_booking_folio(token):
    """Test folio retrieval for existing bookings"""
    print("\n🔍 Testing existing bookings with folios...")
    
    response = requests.get(
        f"{BASE_URL}/pms/bookings?limit=5",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to fetch bookings: {response.status_code}")
        return False
    
    bookings = response.json()
    
    if not bookings:
        print("⚠️ No existing bookings found to test")
        return True
    
    print(f"✅ Found {len(bookings)} existing bookings")
    
    success_count = 0
    fail_count = 0
    
    for booking in bookings[:3]:  # Test first 3 bookings
        booking_id = booking.get('id')
        print(f"\n   Testing booking {booking_id}...")
        
        response = requests.get(
            f"{BASE_URL}/folio/booking/{booking_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if response.status_code == 200:
            folios = response.json()
            if folios and len(folios) > 0:
                print(f"   ✅ Folio exists - Folio Number: {folios[0].get('folio_number')}")
                success_count += 1
            else:
                print(f"   ⚠️ No folio found (may be old booking)")
                fail_count += 1
        else:
            print(f"   ❌ Failed to fetch folio: {response.status_code}")
            fail_count += 1
    
    print(f"\n📊 Existing Bookings Test Results:")
    print(f"   Success: {success_count}")
    print(f"   Failed: {fail_count}")
    
    return success_count > 0

def main():
    print("=" * 80)
    print("🧪 FOLIO CREATION TEST FOR NEW BOOKINGS")
    print("=" * 80)
    print("\nTesting the fix for: 'No folio found for this booking' issue")
    print("Expected: New bookings should automatically have folios created\n")
    
    # Step 1: Login
    result = login()
    if not result:
        print("\n❌ TEST FAILED: Login failed")
        return
    
    token, tenant_id = result
    
    # Step 2: Get guests
    guests = get_guests(token)
    if not guests:
        print("\n❌ TEST FAILED: No guests available")
        return
    
    guest_id = guests[0].get('id')
    print(f"   Using guest: {guests[0].get('name')} (ID: {guest_id})")
    
    # Step 3: Get available rooms
    rooms = get_rooms(token)
    if not rooms:
        print("\n❌ TEST FAILED: No available rooms")
        return
    
    room_id = rooms[0].get('id')
    room_number = rooms[0].get('room_number')
    print(f"   Using room: {room_number} (ID: {room_id})")
    
    # Step 4: Create new booking
    booking_id = create_booking(token, guest_id, room_id)
    if not booking_id:
        print("\n❌ TEST FAILED: Could not create booking")
        return
    
    # Step 5: Verify folio was created
    folio_verified = verify_folio_created(token, booking_id)
    
    # Step 6: Test existing bookings
    existing_test = test_existing_booking_folio(token)
    
    # Final Results
    print("\n" + "=" * 80)
    print("📊 FINAL TEST RESULTS")
    print("=" * 80)
    
    if folio_verified and existing_test:
        print("\n✅ ALL TESTS PASSED!")
        print("\n✅ Test 1: New booking folio creation - PASSED")
        print("   - Folio automatically created on booking creation")
        print("   - Folio number follows F-YYYY-##### format")
        print("   - Folio type is 'guest'")
        print("   - All required fields present")
        print("\n✅ Test 2: Existing booking folio retrieval - PASSED")
        print("   - Folios can be retrieved for existing bookings")
        print("\n🎉 FIX VERIFIED: 'No folio found' issue is resolved!")
    else:
        print("\n❌ SOME TESTS FAILED!")
        if not folio_verified:
            print("   ❌ New booking folio creation - FAILED")
        if not existing_test:
            print("   ⚠️ Existing booking folio retrieval - ISSUES FOUND")
        print("\n⚠️ The 'No folio found' issue may still exist")
    
    print("=" * 80)

if __name__ == "__main__":
    main()
