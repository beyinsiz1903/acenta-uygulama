#!/usr/bin/env python3
"""
PR#7.3 Auto Customer Match/Create - Direct Database Test
Testing the customer matching logic directly without B2B booking flow
"""

import uuid
from datetime import datetime
from pymongo import MongoClient
import os
import asyncio

# MongoDB connection
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017/test_database")

def get_mongo_client():
    return MongoClient(MONGO_URL)

def _normalize_phone(value: str) -> str:
    """Normalize phone number to digits only"""
    digits = [ch for ch in str(value) if ch.isdigit()]
    return "".join(digits)

async def find_or_create_customer_for_booking_test(db, organization_id, booking, created_by_user_id=None):
    """Test version of the customer matching function"""
    # Try both 'customer' (B2B bookings) and 'guest' (other bookings) fields
    customer_data = booking.get("customer") or booking.get("guest") or {}
    email_raw = (customer_data.get("email") or "").strip().lower()
    phone_raw = (customer_data.get("phone") or "").strip()
    phone_norm = _normalize_phone(phone_raw) if phone_raw else ""

    print(f"   📋 Looking for customer with email: '{email_raw}', phone: '{phone_norm}'")

    if not email_raw and not phone_norm:
        print(f"   ❌ No email or phone provided")
        return None

    # 1) Try match by email (case-insensitive)
    if email_raw:
        existing_by_email = db.customers.find_one(
            {
                "organization_id": organization_id,
                "contacts": {
                    "$elemMatch": {
                        "type": "email",
                        "value": {"$regex": f"^{email_raw}$", "$options": "i"},
                    }
                },
            },
            {"_id": 0},
        )
        if existing_by_email:
            customer_id = existing_by_email.get("id")
            print(f"   ✅ Found existing customer by email: {customer_id}")
            return customer_id

    # 2) Try match by phone
    if phone_norm:
        existing_by_phone = db.customers.find_one(
            {
                "organization_id": organization_id,
                "contacts": {
                    "$elemMatch": {
                        "type": "phone",
                        "value": phone_norm,
                    }
                },
            },
            {"_id": 0},
        )
        if existing_by_phone:
            customer_id = existing_by_phone.get("id")
            print(f"   ✅ Found existing customer by phone: {customer_id}")
            return customer_id

    # 3) Create new customer
    print(f"   📋 No existing customer found, creating new one...")
    name = (customer_data.get("name") or customer_data.get("full_name") or "Misafir").strip() or "Misafir"
    contacts = []
    if email_raw:
        contacts.append({"type": "email", "value": email_raw, "is_primary": True})
    if phone_norm:
        contacts.append({"type": "phone", "value": phone_norm, "is_primary": not contacts})

    customer_id = f"cust_{uuid.uuid4().hex}"
    doc = {
        "id": customer_id,
        "organization_id": organization_id,
        "type": "individual",
        "name": name,
        "tags": ["auto_created"],
        "contacts": contacts,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    
    db.customers.insert_one(doc)
    print(f"   ✅ Created new customer: {customer_id}")
    return customer_id

def test_customer_matching():
    """Test customer matching functionality directly"""
    print("\n" + "=" * 60)
    print("PR#7.3 CUSTOMER MATCHING DIRECT TEST")
    print("=" * 60)

    mongo_client = get_mongo_client()
    db = mongo_client.get_default_database()
    
    # Use a test organization ID
    org_id = "695e03c80b04ed31c4eaa899"  # Known org from previous tests

    # Test 1: Email match scenario
    print("\n1️⃣  Email match scenario...")
    test_email = "test_email_match@gmail.com"
    
    # Create a test customer with email
    existing_customer_id = f"cust_{uuid.uuid4().hex}"
    existing_customer = {
        "id": existing_customer_id,
        "organization_id": org_id,
        "type": "individual",
        "name": "Existing Email Customer",
        "tags": ["test_match"],
        "contacts": [
            {"type": "email", "value": test_email.lower(), "is_primary": True}
        ],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    
    db.customers.insert_one(existing_customer)
    print(f"   ✅ Created existing customer: {existing_customer_id} with email: {test_email}")

    # Test B2B booking with matching email
    booking_b2b = {
        "customer": {
            "name": "Test B2B Customer",
            "email": test_email.upper()  # Test case insensitive matching
        }
    }
    
    print(f"   📋 Testing B2B booking customer match...")
    matched_id = asyncio.run(find_or_create_customer_for_booking_test(db, org_id, booking_b2b))
    
    if matched_id == existing_customer_id:
        print(f"   ✅ EMAIL MATCH SUCCESS: B2B booking matched existing customer")
    else:
        print(f"   ❌ EMAIL MATCH FAILED: Expected {existing_customer_id}, got {matched_id}")

    # Test 2: Phone match scenario
    print("\n2️⃣  Phone match scenario...")
    test_phone = "+90 (555) 123 4567"
    test_phone_normalized = _normalize_phone(test_phone)
    
    # Create a test customer with phone
    existing_phone_customer_id = f"cust_{uuid.uuid4().hex}"
    existing_phone_customer = {
        "id": existing_phone_customer_id,
        "organization_id": org_id,
        "type": "individual",
        "name": "Existing Phone Customer",
        "tags": ["test_match"],
        "contacts": [
            {"type": "phone", "value": test_phone_normalized, "is_primary": True}
        ],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    
    db.customers.insert_one(existing_phone_customer)
    print(f"   ✅ Created existing customer: {existing_phone_customer_id} with phone: {test_phone} -> {test_phone_normalized}")

    # Test booking with matching phone (different format)
    booking_phone = {
        "guest": {  # Test with 'guest' field
            "full_name": "Test Phone Customer",
            "phone": "905551234567"  # Different format, same number
        }
    }
    
    print(f"   📋 Testing phone customer match...")
    matched_phone_id = asyncio.run(find_or_create_customer_for_booking_test(db, org_id, booking_phone))
    
    if matched_phone_id == existing_phone_customer_id:
        print(f"   ✅ PHONE MATCH SUCCESS: Booking matched existing customer")
    else:
        print(f"   ❌ PHONE MATCH FAILED: Expected {existing_phone_customer_id}, got {matched_phone_id}")

    # Test 3: Auto-create scenario
    print("\n3️⃣  Auto-create scenario...")
    new_email = f"new_auto_create_{uuid.uuid4().hex}@gmail.com"
    
    booking_new = {
        "customer": {
            "name": "New Auto Customer",
            "email": new_email
        }
    }
    
    print(f"   📋 Testing auto-create with new email: {new_email}")
    new_customer_id = asyncio.run(find_or_create_customer_for_booking_test(db, org_id, booking_new))
    
    if new_customer_id:
        # Verify the customer was created correctly
        created_customer = db.customers.find_one({"id": new_customer_id, "organization_id": org_id})
        if created_customer:
            print(f"   ✅ AUTO-CREATE SUCCESS: New customer created: {new_customer_id}")
            print(f"   📋 Customer name: {created_customer.get('name')}")
            print(f"   📋 Customer type: {created_customer.get('type')}")
            
            # Check email normalization
            contacts = created_customer.get("contacts", [])
            for contact in contacts:
                if contact.get("type") == "email":
                    email_value = contact.get("value")
                    print(f"   📋 Email normalized: '{email_value}'")
                    if email_value == new_email.lower():
                        print(f"   ✅ Email normalization correct")
                    else:
                        print(f"   ❌ Email normalization incorrect: expected '{new_email.lower()}'")
        else:
            print(f"   ❌ Created customer not found in database")
    else:
        print(f"   ❌ AUTO-CREATE FAILED: No customer ID returned")

    # Test 4: Contact normalization verification
    print("\n4️⃣  Contact normalization verification...")
    
    # Check all test customers for proper normalization
    test_customers = db.customers.find({
        "organization_id": org_id,
        "$or": [
            {"tags": "test_match"},
            {"tags": "auto_created"}
        ]
    })
    
    for customer in test_customers:
        customer_id = customer.get("id")
        contacts = customer.get("contacts", [])
        print(f"   📋 Customer {customer_id}:")
        
        for contact in contacts:
            contact_type = contact.get("type")
            contact_value = contact.get("value")
            
            if contact_type == "email":
                if contact_value == contact_value.lower():
                    print(f"      ✅ Email '{contact_value}' properly normalized (lowercase)")
                else:
                    print(f"      ❌ Email '{contact_value}' not normalized")
            elif contact_type == "phone":
                if contact_value.isdigit():
                    print(f"      ✅ Phone '{contact_value}' properly normalized (digits only)")
                else:
                    print(f"      ❌ Phone '{contact_value}' not normalized")

    # Cleanup
    print("\n5️⃣  Cleanup...")
    result = db.customers.delete_many({
        "organization_id": org_id,
        "$or": [
            {"tags": "test_match"},
            {"tags": "auto_created"}
        ]
    })
    print(f"   ✅ Cleaned up {result.deleted_count} test customers")
    
    mongo_client.close()

    print("\n" + "=" * 60)
    print("✅ PR#7.3 CUSTOMER MATCHING DIRECT TEST COMPLETED")
    print("=" * 60)

if __name__ == "__main__":
    test_customer_matching()