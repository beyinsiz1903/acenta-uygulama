#!/usr/bin/env python3
"""
PR#7.3 Auto Customer Match/Create for B2B bookings - Focused Test
Testing the core functionality with simplified approach
"""

import requests
import json
import uuid
from datetime import datetime
from pymongo import MongoClient
import os

# Configuration
BASE_URL = "https://billing-dashboard-v5.preview.emergentagent.com"

def get_mongo_client():
    """Get MongoDB client for direct database access"""
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017/test_database")
    return MongoClient(mongo_url)

def login_admin():
    """Login as admin user"""
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": "admin@acenta.test", "password": "admin123"})
    assert r.status_code == 200, f"Admin login failed: {r.text}"
    data = r.json()
    return data["access_token"], data["user"]["organization_id"]

def login_agency():
    """Login as agency user"""
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": "agency1@demo.test", "password": "agency123"})
    assert r.status_code == 200, f"Agency login failed: {r.text}"
    data = r.json()
    user = data["user"]
    return data["access_token"], user["organization_id"], user["agency_id"]

def create_test_customer_with_email(mongo_client, org_id, email):
    """Create a test customer with email contact"""
    db = mongo_client.get_default_database()
    customer_id = f"cust_{uuid.uuid4().hex}"
    
    doc = {
        "id": customer_id,
        "organization_id": org_id,
        "type": "individual",
        "name": "Test Email Customer",
        "tags": ["test_auto_match"],
        "contacts": [{"type": "email", "value": email.strip().lower(), "is_primary": True}],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    
    db.customers.insert_one(doc)
    print(f"   ✅ Created test customer: {customer_id} with email: {email}")
    return customer_id

def test_auto_customer_match():
    """Test auto customer match functionality"""
    print("\n" + "=" * 60)
    print("PR#7.3 AUTO CUSTOMER MATCH/CREATE TEST")
    print("=" * 60)

    # Login
    print("\n1️⃣  Authentication...")
    admin_token, admin_org_id = login_admin()
    agency_token, agency_org_id, agency_id = login_agency()
    
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    agency_headers = {"Authorization": f"Bearer {agency_token}", "Idempotency-Key": f"test_{uuid.uuid4().hex}"}
    
    print(f"   ✅ Admin org: {admin_org_id}")
    print(f"   ✅ Agency org: {agency_org_id}, agency: {agency_id}")

    # Use agency org for consistency
    org_id = agency_org_id
    mongo_client = get_mongo_client()

    # Test 1: Email match scenario
    print("\n2️⃣  Email match scenario...")
    test_email = "test_auto_match@gmail.com"
    existing_customer_id = create_test_customer_with_email(mongo_client, org_id, test_email)

    # Check current B2B booking implementation
    print("\n3️⃣  Testing B2B booking creation...")
    
    # First, let's check if we can create a simple quote
    from datetime import date
    quote_payload = {
        "channel_id": "test_channel",
        "items": [{
            "product_id": "test_hotel_123",
            "room_type_id": "standard", 
            "rate_plan_id": "flexible",
            "check_in": "2026-01-15",
            "check_out": "2026-01-17",
            "occupancy": 2
        }]
    }
    
    print(f"   📋 Creating B2B quote...")
    r = requests.post(f"{BASE_URL}/api/api/b2b/quotes", json=quote_payload, headers=agency_headers)
    print(f"   📋 Quote response: {r.status_code}")
    
    if r.status_code == 200:
        quote_data = r.json()
        quote_id = quote_data.get("quote_id")
        print(f"   ✅ Quote created: {quote_id}")
    else:
        print(f"   ⚠️  Quote creation failed: {r.text}")
        quote_id = "mock_quote_for_testing"

    # Test booking creation with email match
    booking_payload = {
        "quote_id": quote_id,
        "customer": {"name": "Test Customer", "email": test_email},
        "travellers": [{"first_name": "John", "last_name": "Doe"}]
    }
    
    agency_headers["Idempotency-Key"] = f"test_email_{uuid.uuid4().hex}"
    
    print(f"   📋 Creating B2B booking with email: {test_email}")
    r = requests.post(f"{BASE_URL}/api/api/b2b/bookings", json=booking_payload, headers=agency_headers)
    print(f"   📋 Booking response: {r.status_code}")
    
    if r.status_code == 200:
        booking_data = r.json()
        booking_id = booking_data.get("booking_id")
        print(f"   ✅ Booking created: {booking_id}")
        
        # Check if customer_id was set correctly
        db = mongo_client.get_default_database()
        from bson import ObjectId
        booking_doc = db.bookings.find_one({"_id": ObjectId(booking_id)})
        
        if booking_doc:
            customer_id_in_booking = booking_doc.get("customer_id")
            print(f"   📋 customer_id in booking: {customer_id_in_booking}")
            
            if customer_id_in_booking == existing_customer_id:
                print(f"   ✅ EMAIL MATCH SUCCESS: Existing customer linked correctly")
            elif customer_id_in_booking:
                print(f"   ❌ EMAIL MATCH FAILED: Different customer linked")
                # Check if a new customer was created
                new_customer = db.customers.find_one({"id": customer_id_in_booking})
                if new_customer:
                    print(f"   📋 New customer created instead: {new_customer.get('name')}")
            else:
                print(f"   ❌ NO CUSTOMER LINKING: customer_id not set")
        else:
            print(f"   ❌ Booking not found in database")
            
    else:
        print(f"   ❌ Booking creation failed: {r.text}")

    # Test 2: Auto-create scenario
    print("\n4️⃣  Auto-create scenario...")
    new_email = f"new_customer_{uuid.uuid4().hex}@gmail.com"
    
    booking_payload_new = {
        "quote_id": quote_id,
        "customer": {"name": "New Auto Customer", "email": new_email},
        "travellers": [{"first_name": "Jane", "last_name": "Smith"}]
    }
    
    agency_headers["Idempotency-Key"] = f"test_new_{uuid.uuid4().hex}"
    
    print(f"   📋 Creating B2B booking with new email: {new_email}")
    r = requests.post(f"{BASE_URL}/api/api/b2b/bookings", json=booking_payload_new, headers=agency_headers)
    print(f"   📋 Booking response: {r.status_code}")
    
    if r.status_code == 200:
        booking_data = r.json()
        booking_id_new = booking_data.get("booking_id")
        print(f"   ✅ Booking created: {booking_id_new}")
        
        # Check if new customer was created
        db = mongo_client.get_default_database()
        booking_doc = db.bookings.find_one({"_id": ObjectId(booking_id_new)})
        
        if booking_doc:
            customer_id_new = booking_doc.get("customer_id")
            print(f"   📋 customer_id in booking: {customer_id_new}")
            
            if customer_id_new:
                new_customer = db.customers.find_one({"id": customer_id_new})
                if new_customer:
                    print(f"   ✅ AUTO-CREATE SUCCESS: New customer created")
                    print(f"   📋 Customer name: {new_customer.get('name')}")
                    print(f"   📋 Customer type: {new_customer.get('type')}")
                    
                    # Check email normalization
                    contacts = new_customer.get("contacts", [])
                    for contact in contacts:
                        if contact.get("type") == "email":
                            email_value = contact.get("value")
                            print(f"   📋 Email normalized: {email_value}")
                            if email_value == new_email.strip().lower():
                                print(f"   ✅ Email normalization correct")
                            else:
                                print(f"   ❌ Email normalization incorrect")
                else:
                    print(f"   ❌ Customer not found in database")
            else:
                print(f"   ❌ customer_id not set in booking")
    else:
        print(f"   ❌ Booking creation failed: {r.text}")

    # Test 3: CRM Customer Detail verification
    print("\n5️⃣  CRM Customer Detail verification...")
    if existing_customer_id:
        r = requests.get(f"{BASE_URL}/api/crm/customers/{existing_customer_id}", headers=admin_headers)
        print(f"   📋 Customer detail response: {r.status_code}")
        
        if r.status_code == 200:
            customer_detail = r.json()
            recent_bookings = customer_detail.get("recent_bookings", [])
            print(f"   ✅ Customer detail retrieved")
            print(f"   📋 Recent bookings count: {len(recent_bookings)}")
        else:
            print(f"   ❌ Customer detail failed: {r.text}")

    # Cleanup
    print("\n6️⃣  Cleanup...")
    db = mongo_client.get_default_database()
    result = db.customers.delete_many({"organization_id": org_id, "tags": "test_auto_match"})
    print(f"   ✅ Cleaned up {result.deleted_count} test customers")
    
    mongo_client.close()

    print("\n" + "=" * 60)
    print("✅ PR#7.3 AUTO CUSTOMER MATCH TEST COMPLETED")
    print("=" * 60)

if __name__ == "__main__":
    test_auto_customer_match()