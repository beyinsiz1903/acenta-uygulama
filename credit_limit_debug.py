#!/usr/bin/env python3
"""
Focused test for credit limit guard functionality
"""

import requests
import json
import uuid
from datetime import datetime, timedelta
from pymongo import MongoClient
import os
from bson import ObjectId, Decimal128
import bcrypt

BASE_URL = "https://conversational-ai-5.preview.emergentagent.com"

def get_mongo_client():
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017/test_database")
    return MongoClient(mongo_url)

def create_agency_admin_user_and_login(org_id: str, email: str, password: str = "testpass123") -> str:
    mongo_client = get_mongo_client()
    db = mongo_client.get_default_database()
    
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    user_doc = {
        "email": email,
        "password_hash": password_hash,
        "roles": ["agency_admin"],
        "organization_id": org_id,
        "is_active": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    
    db.users.replace_one({"email": email}, user_doc, upsert=True)
    mongo_client.close()
    
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": email, "password": password},
    )
    
    if r.status_code != 200:
        raise Exception(f"Login failed for {email}: {r.status_code} - {r.text}")
    
    data = r.json()
    return data["access_token"]

def setup_test_org_and_infrastructure():
    """Setup test organization and infrastructure"""
    unique_id = uuid.uuid4().hex[:8]
    org_id = f"org_credit_test_{unique_id}"
    
    mongo_client = get_mongo_client()
    db = mongo_client.get_default_database()
    
    now = datetime.utcnow()
    
    # Create organization
    org_doc = {
        "_id": org_id,
        "name": f"Credit Test Org {unique_id}",
        "slug": f"credit-test-{unique_id}",
        "created_at": now,
        "updated_at": now,
        "settings": {"currency": "TRY"},
        "plan": "core_small_hotel",
        "features": {"partner_api": True},
    }
    db.organizations.replace_one({"_id": org_id}, org_doc, upsert=True)
    
    # Create credit profile with low limit
    credit_profile_doc = {
        "organization_id": org_id,
        "name": "Standard",
        "credit_limit": 50.0,  # Very low limit
        "currency": "TRY",
        "created_at": now,
        "updated_at": now,
    }
    db.credit_profiles.replace_one(
        {"organization_id": org_id, "name": "Standard"},
        credit_profile_doc,
        upsert=True
    )
    
    # Create buyer tenant
    buyer_tenant_id = f"tenant_buyer_{unique_id}"
    buyer_tenant_doc = {
        "_id": buyer_tenant_id,
        "organization_id": org_id,
        "tenant_key": f"buyer-tenant-{unique_id}",
        "name": "Buyer Tenant",
        "type": "buyer",
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    db.tenants.replace_one({"_id": buyer_tenant_id}, buyer_tenant_doc, upsert=True)
    
    # Create high amount booking
    booking_id = ObjectId()
    booking_doc = {
        "_id": booking_id,
        "organization_id": org_id,
        "state": "draft",
        "status": "PENDING",
        "source": "b2b_marketplace",
        "currency": "TRY",
        "amount": 25000.0,  # Much higher than 50.0 limit
        "customer_email": "test@example.com",
        "customer_name": "Test Customer",
        "customer_phone": "+905550000000",
        "offer_ref": {
            "source": "marketplace",
            "buyer_tenant_id": buyer_tenant_id,
            "supplier": "mock_supplier_v1",
            "supplier_offer_id": "MOCK-IST-001",
        },
        "pricing": {
            "base_amount": "25000.00",
            "final_amount": "25000.00",
            "commission_amount": "0.00",
            "margin_amount": "0.00",
            "currency": "TRY",
            "applied_rules": [],
            "calculated_at": now,
        },
        "created_at": now,
        "updated_at": now,
    }
    
    db.bookings.insert_one(booking_doc)
    mongo_client.close()
    
    return org_id, str(booking_id), f"buyer-tenant-{unique_id}"

def test_credit_limit():
    print("Testing credit limit guard...")
    
    # Setup
    org_id, booking_id, buyer_tenant_key = setup_test_org_and_infrastructure()
    
    # Create user and login
    email = f"agency_admin_{uuid.uuid4().hex[:8]}@test.com"
    token = create_agency_admin_user_and_login(org_id, email)
    
    # Try to confirm booking
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-Key": buyer_tenant_key
    }
    
    print(f"Confirming booking {booking_id} with credit limit 50.0 and amount 25000.0...")
    
    r = requests.post(
        f"{BASE_URL}/api/b2b/bookings/{booking_id}/confirm",
        headers=headers
    )
    
    print(f"Response: {r.status_code} - {r.text}")
    
    # Check database state
    mongo_client = get_mongo_client()
    db = mongo_client.get_default_database()
    
    # Check credit profile
    credit_profile = db.credit_profiles.find_one({"organization_id": org_id, "name": "Standard"})
    print(f"Credit profile: {credit_profile}")
    
    # Check booking
    booking = db.bookings.find_one({"_id": ObjectId(booking_id)})
    print(f"Booking amount: {booking.get('amount')}")
    print(f"Booking status: {booking.get('status')}")
    
    # Check existing bookings with state 'booked'
    booked_bookings = list(db.bookings.find({"organization_id": org_id, "state": "booked"}))
    print(f"Existing booked bookings: {len(booked_bookings)}")
    
    mongo_client.close()
    
    # Cleanup
    mongo_client = get_mongo_client()
    db = mongo_client.get_default_database()
    db.organizations.delete_one({"_id": org_id})
    db.users.delete_many({"organization_id": org_id})
    db.bookings.delete_many({"organization_id": org_id})
    db.tenants.delete_many({"organization_id": org_id})
    db.credit_profiles.delete_many({"organization_id": org_id})
    mongo_client.close()

if __name__ == "__main__":
    test_credit_limit()