#!/usr/bin/env python3
"""
PR#7.3 Auto Customer Match/Create - Integration Test with Seed Data
Testing with existing seed data and real B2B booking flow
"""

import requests
import json
import uuid
from datetime import datetime
from pymongo import MongoClient
import os

# Configuration
BASE_URL = "https://bayi-platform.preview.emergentagent.com"

def get_mongo_client():
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017/test_database")
    return MongoClient(mongo_url)

def login_admin():
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": "admin@acenta.test", "password": "admin123"})
    assert r.status_code == 200, f"Admin login failed: {r.text}"
    data = r.json()
    return data["access_token"], data["user"]["organization_id"]

def login_agency():
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
        "name": "Test Auto Match Customer",
        "tags": ["test_auto_match"],
        "contacts": [{"type": "email", "value": email.strip().lower(), "is_primary": True}],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    
    db.customers.insert_one(doc)
    print(f"   ✅ Created test customer: {customer_id} with email: {email}")
    return customer_id

def find_existing_quote(mongo_client, org_id, agency_id):
    """Find an existing quote for testing"""
    db = mongo_client.get_default_database()
    
    # Look for existing quotes
    quote = db.quotes.find_one({
        "organization_id": org_id,
        "agency_id": agency_id,
        "expires_at": {"$gt": datetime.utcnow()}
    })
    
    if quote:
        quote_id = str(quote["_id"])
        print(f"   ✅ Found existing quote: {quote_id}")
        return quote_id
    
    print(f"   ⚠️  No existing valid quotes found")
    return None

def test_integration_with_seed_data():
    """Test auto customer match with real B2B booking flow"""
    print("\n" + "=" * 60)
    print("PR#7.3 INTEGRATION TEST WITH SEED DATA")
    print("=" * 60)

    # Login
    print("\n1️⃣  Authentication...")
    admin_token, admin_org_id = login_admin()
    agency_token, agency_org_id, agency_id = login_agency()
    
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    agency_headers = {"Authorization": f"Bearer {agency_token}"}
    
    print(f"   ✅ Admin org: {admin_org_id}")
    print(f"   ✅ Agency org: {agency_org_id}, agency: {agency_id}")

    org_id = agency_org_id
    mongo_client = get_mongo_client()

    # Test 1: Check existing bookings to understand the structure
    print("\n2️⃣  Examining existing bookings...")
    
    r = requests.get(f"{BASE_URL}/api/api/b2b/bookings?limit=5", headers=agency_headers)
    print(f"   📋 Existing bookings response: {r.status_code}")
    
    if r.status_code == 200:
        bookings_data = r.json()
        items = bookings_data.get("items", [])
        print(f"   📋 Found {len(items)} existing bookings")
        
        for item in items:
            booking_id = item.get("booking_id")
            print(f"   📋 Booking: {booking_id}")
    else:
        print(f"   ❌ Failed to get bookings: {r.text}")

    # Test 2: Check existing quotes
    print("\n3️⃣  Looking for existing quotes...")
    existing_quote_id = find_existing_quote(mongo_client, org_id, agency_id)

    # Test 3: Email match scenario with existing customer
    print("\n4️⃣  Email match scenario...")
    test_email = "test_integration_match@gmail.com"
    existing_customer_id = create_test_customer_with_email(mongo_client, org_id, test_email)

    # If we have a quote, try to create a booking
    if existing_quote_id:
        print(f"   📋 Testing booking creation with existing quote: {existing_quote_id}")
        
        booking_payload = {
            "quote_id": existing_quote_id,
            "customer": {"name": "Test Integration Customer", "email": test_email},
            "travellers": [{"first_name": "John", "last_name": "Doe"}]
        }
        
        agency_headers["Idempotency-Key"] = f"test_integration_{uuid.uuid4().hex}"
        
        r = requests.post(f"{BASE_URL}/api/api/b2b/bookings", json=booking_payload, headers=agency_headers)
        print(f"   📋 Booking creation response: {r.status_code}")
        
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
                    # Check the linked customer
                    linked_customer = db.customers.find_one({"id": customer_id_in_booking})
                    if linked_customer:
                        print(f"   📋 Linked customer: {linked_customer.get('name')}")
                        print(f"   📋 Linked customer contacts: {linked_customer.get('contacts')}")
                else:
                    print(f"   ❌ NO CUSTOMER LINKING: customer_id not set")
                    
                # Test CRM customer detail
                print(f"\n5️⃣  Testing CRM customer detail...")
                if customer_id_in_booking:
                    r = requests.get(f"{BASE_URL}/api/crm/customers/{customer_id_in_booking}", headers=admin_headers)
                    print(f"   📋 Customer detail response: {r.status_code}")
                    
                    if r.status_code == 200:
                        customer_detail = r.json()
                        recent_bookings = customer_detail.get("recent_bookings", [])
                        print(f"   ✅ Customer detail retrieved")
                        print(f"   📋 Recent bookings count: {len(recent_bookings)}")
                        
                        # Check if our booking is in recent_bookings
                        booking_found = False
                        for booking in recent_bookings:
                            if booking.get("booking_id") == booking_id:
                                booking_found = True
                                print(f"   ✅ Test booking found in recent_bookings")
                                break
                        
                        if not booking_found:
                            print(f"   ⚠️  Test booking not found in recent_bookings")
                    else:
                        print(f"   ❌ Customer detail failed: {r.text}")
                
                # Test Ops booking detail
                print(f"\n6️⃣  Testing Ops booking detail...")
                r = requests.get(f"{BASE_URL}/api/ops/bookings/{booking_id}", headers=admin_headers)
                print(f"   📋 Ops booking detail response: {r.status_code}")
                
                if r.status_code == 200:
                    booking_detail = r.json()
                    customer_id_ops = booking_detail.get("customer_id")
                    print(f"   ✅ Ops booking detail retrieved")
                    print(f"   📋 customer_id in ops view: {customer_id_ops}")
                    
                    if customer_id_ops:
                        print(f"   ✅ customer_id correctly set in ops booking detail")
                    else:
                        print(f"   ❌ customer_id not set in ops view")
                else:
                    print(f"   ❌ Ops booking detail failed: {r.text}")
            else:
                print(f"   ❌ Booking not found in database")
        else:
            print(f"   ❌ Booking creation failed: {r.text}")
    else:
        print(f"   ⚠️  No existing quote available for testing")
        print(f"   📋 Skipping booking creation test")

    # Test 4: Auto-create scenario (if we have a quote)
    if existing_quote_id:
        print("\n7️⃣  Auto-create scenario...")
        new_email = f"new_integration_{uuid.uuid4().hex}@gmail.com"
        
        booking_payload_new = {
            "quote_id": existing_quote_id,
            "customer": {"name": "New Integration Customer", "email": new_email},
            "travellers": [{"first_name": "Jane", "last_name": "Smith"}]
        }
        
        agency_headers["Idempotency-Key"] = f"test_new_integration_{uuid.uuid4().hex}"
        
        r = requests.post(f"{BASE_URL}/api/api/b2b/bookings", json=booking_payload_new, headers=agency_headers)
        print(f"   📋 New booking creation response: {r.status_code}")
        
        if r.status_code == 200:
            booking_data = r.json()
            booking_id_new = booking_data.get("booking_id")
            print(f"   ✅ New booking created: {booking_id_new}")
            
            # Check if new customer was created
            db = mongo_client.get_default_database()
            booking_doc = db.bookings.find_one({"_id": ObjectId(booking_id_new)})
            
            if booking_doc:
                customer_id_new = booking_doc.get("customer_id")
                print(f"   📋 customer_id in new booking: {customer_id_new}")
                
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
                        print(f"   ❌ New customer not found in database")
                else:
                    print(f"   ❌ customer_id not set in new booking")
        else:
            print(f"   ❌ New booking creation failed: {r.text}")

    # Cleanup
    print("\n8️⃣  Cleanup...")
    db = mongo_client.get_default_database()
    result = db.customers.delete_many({"organization_id": org_id, "tags": "test_auto_match"})
    print(f"   ✅ Cleaned up {result.deleted_count} test customers")
    
    mongo_client.close()

    print("\n" + "=" * 60)
    print("✅ PR#7.3 INTEGRATION TEST COMPLETED")
    print("=" * 60)

if __name__ == "__main__":
    test_integration_with_seed_data()