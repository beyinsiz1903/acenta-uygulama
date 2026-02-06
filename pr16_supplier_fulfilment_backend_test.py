#!/usr/bin/env python3
"""
PR-16 Supplier Fulfilment v1 Backend Validation

This test suite validates the new POST /api/b2b/bookings/{booking_id}/confirm endpoint
for supplier fulfilment functionality as requested in the Turkish specification.

Test Scenarios:
1. Happy path: Complete marketplace booking flow with confirmation
2. Missing supplier mapping scenario
3. Tenant mismatch scenario  
4. Idempotent confirm scenario

All tests use the marketplace booking infrastructure from PR-10 + PR-15.
"""

import requests
import json
import uuid
import asyncio
import subprocess
import sys
from datetime import datetime, timedelta, date
from pymongo import MongoClient
import os
from typing import Dict, Any, Optional
from decimal import Decimal
from bson import ObjectId, Decimal128
import bcrypt

# Configuration - Use production URL from frontend/.env
BASE_URL = "https://billing-dashboard-v5.preview.emergentagent.com"

def get_mongo_client():
    """Get MongoDB client for direct database access"""
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017/test_database")
    return MongoClient(mongo_url)

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

def create_agency_admin_user_and_login(org_id: str, email: str, password: str = "testpass123") -> str:
    """Create an agency_admin user in the database and login via API to get token"""
    mongo_client = get_mongo_client()
    db = mongo_client.get_default_database()
    
    # Create user document with password hash
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
    
    # Insert or update user
    db.users.replace_one({"email": email}, user_doc, upsert=True)
    
    mongo_client.close()
    
    # Login via API to get real JWT token
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": email, "password": password},
    )
    
    if r.status_code != 200:
        raise Exception(f"Login failed for {email}: {r.status_code} - {r.text}")
    
    data = r.json()
    return data["access_token"]

def setup_marketplace_infrastructure(org_suffix: str) -> Dict[str, Any]:
    """Setup complete marketplace infrastructure: org, tenants, user, listing, access"""
    print(f"   📋 Setting up marketplace infrastructure (suffix: {org_suffix})...")
    
    # Create unique identifiers
    unique_id = uuid.uuid4().hex[:8]
    org_id = f"org_pr16_test_{org_suffix}_{unique_id}"
    seller_tenant_id = f"seller_tenant_{unique_id}"
    buyer_tenant_id = f"buyer_tenant_{unique_id}"
    
    mongo_client = get_mongo_client()
    db = mongo_client.get_default_database()
    
    # Clean up any existing test data
    db.organizations.delete_many({"_id": {"$regex": f"^org_pr16_test_{org_suffix}"}})
    db.tenants.delete_many({"organization_id": {"$regex": f"^org_pr16_test_{org_suffix}"}})
    db.marketplace_listings.delete_many({"organization_id": {"$regex": f"^org_pr16_test_{org_suffix}"}})
    db.marketplace_access.delete_many({"organization_id": {"$regex": f"^org_pr16_test_{org_suffix}"}})
    db.pricing_rules.delete_many({"organization_id": {"$regex": f"^org_pr16_test_{org_suffix}"}})
    
    now = datetime.utcnow()
    
    # 1. Create organization
    org_doc = {
        "_id": org_id,
        "name": f"PR-16 Test Org {org_suffix}",
        "slug": f"pr16-test-{org_suffix}-{unique_id}",
        "created_at": now,
        "updated_at": now,
        "settings": {"currency": "TRY"},
        "plan": "core_small_hotel",
        "features": {"partner_api": True},
    }
    db.organizations.replace_one({"_id": org_id}, org_doc, upsert=True)
    
    # 2. Create seller tenant
    seller_tenant_doc = {
        "_id": seller_tenant_id,
        "organization_id": org_id,
        "tenant_key": f"seller-tenant-{unique_id}",
        "name": f"Seller Tenant {unique_id}",
        "type": "seller",
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    db.tenants.replace_one({"_id": seller_tenant_id}, seller_tenant_doc, upsert=True)
    
    # 3. Create buyer tenant
    buyer_tenant_doc = {
        "_id": buyer_tenant_id,
        "organization_id": org_id,
        "tenant_key": f"buyer-tenant-{unique_id}",
        "name": f"Buyer Tenant {unique_id}",
        "type": "buyer",
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    db.tenants.replace_one({"_id": buyer_tenant_id}, buyer_tenant_doc, upsert=True)
    
    # 4. Create pricing rule for buyer tenant (TRY markup)
    pricing_rule_doc = {
        "organization_id": org_id,
        "tenant_id": buyer_tenant_id,
        "supplier": "marketplace",
        "rule_type": "markup_pct",
        "value": Decimal128("15.00"),  # 15% markup
        "priority": 100,
        "valid_from": now - timedelta(days=1),
        "valid_to": now + timedelta(days=365),
        "stackable": True,
        "created_at": now,
        "updated_at": now,
    }
    db.pricing_rules.insert_one(pricing_rule_doc)
    
    # 5. Create marketplace listing with supplier metadata
    listing_id = ObjectId()
    listing_doc = {
        "_id": listing_id,
        "organization_id": org_id,
        "tenant_id": seller_tenant_id,
        "title": f"Test Hotel Listing {unique_id}",
        "description": "Test hotel for PR-16 supplier fulfilment",
        "category": "hotel",
        "currency": "TRY",
        "base_price": Decimal128("100.00"),
        "status": "published",
        "supplier": {
            "name": "mock_supplier_v1",
            "external_ref": f"MOCK-HOTEL-{unique_id}",
            "payload": {"hotel_id": f"MOCK-HOTEL-{unique_id}"}
        },
        "created_at": now,
        "updated_at": now,
    }
    db.marketplace_listings.replace_one({"_id": listing_id}, listing_doc, upsert=True)
    
    # 6. Create marketplace access (seller->buyer)
    access_doc = {
        "organization_id": org_id,
        "seller_tenant_id": seller_tenant_id,
        "buyer_tenant_id": buyer_tenant_id,
        "created_at": now,
    }
    db.marketplace_access.replace_one(
        {
            "organization_id": org_id,
            "seller_tenant_id": seller_tenant_id,
            "buyer_tenant_id": buyer_tenant_id,
        },
        access_doc,
        upsert=True
    )
    
    mongo_client.close()
    
    print(f"   ✅ Created org: {org_id}")
    print(f"   ✅ Created seller tenant: {seller_tenant_id}")
    print(f"   ✅ Created buyer tenant: {buyer_tenant_id}")
    print(f"   ✅ Created marketplace listing: {listing_id}")
    print(f"   ✅ Created marketplace access and pricing rule")
    
    return {
        "org_id": org_id,
        "seller_tenant_id": seller_tenant_id,
        "buyer_tenant_id": buyer_tenant_id,
        "buyer_tenant_key": f"buyer-tenant-{unique_id}",
        "listing_id": str(listing_id),
        "unique_id": unique_id,
    }

def resolve_supplier_mapping(listing_id: str, token: str) -> Dict[str, Any]:
    """Resolve supplier mapping for a listing"""
    print(f"   🔗 Resolving supplier mapping for listing {listing_id}...")
    
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.post(f"{BASE_URL}/api/marketplace/listings/{listing_id}/resolve-supplier", headers=headers)
    
    assert r.status_code == 200, f"Supplier mapping resolution failed: {r.status_code} - {r.text}"
    
    data = r.json()
    print(f"   ✅ Supplier mapping resolved: {data}")
    return data

def create_draft_booking(infrastructure: Dict[str, Any], token: str) -> str:
    """Create a draft booking using marketplace flow"""
    print(f"   📝 Creating draft booking via marketplace flow...")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-Key": infrastructure["buyer_tenant_key"],
        "Idempotency-Key": f"pr16-test-{infrastructure['unique_id']}"
    }
    
    payload = {
        "source": "marketplace",
        "listing_id": infrastructure["listing_id"],
        "customer": {
            "full_name": "Test Customer PR-16",
            "email": f"test-customer-{infrastructure['unique_id']}@example.com",
            "phone": "+905550000000"
        },
        "travellers": [
            {"first_name": "Test", "last_name": "Traveller"}
        ]
    }
    
    r = requests.post(f"{BASE_URL}/api/b2b/bookings", json=payload, headers=headers)
    
    assert r.status_code == 201, f"Draft booking creation failed: {r.status_code} - {r.text}"
    
    data = r.json()
    booking_id = data["booking_id"]
    
    print(f"   ✅ Created draft booking: {booking_id}")
    return booking_id

def cleanup_test_data(org_ids: list):
    """Clean up test data after testing"""
    try:
        mongo_client = get_mongo_client()
        db = mongo_client.get_default_database()
        
        for org_id in org_ids:
            # Clean up all collections for this org
            collections_to_clean = [
                "organizations", "users", "bookings", "audit_logs", "booking_events",
                "tenants", "marketplace_listings", "marketplace_access", "pricing_rules"
            ]
            
            for collection_name in collections_to_clean:
                collection = getattr(db, collection_name)
                result = collection.delete_many({"organization_id": org_id})
                if result.deleted_count > 0:
                    print(f"   🧹 Cleaned {result.deleted_count} documents from {collection_name}")
        
        mongo_client.close()
        print(f"   ✅ Cleanup completed for {len(org_ids)} organizations")
        
    except Exception as e:
        print(f"   ⚠️  Failed to cleanup test data: {e}")

def verify_booking_confirmed_in_db(booking_id: str, org_id: str) -> Dict[str, Any]:
    """Verify booking is confirmed in database with proper supplier_booking_id"""
    mongo_client = get_mongo_client()
    db = mongo_client.get_default_database()
    
    try:
        oid = ObjectId(booking_id)
    except Exception:
        raise Exception(f"Invalid booking_id: {booking_id}")
    
    booking = db.bookings.find_one({"_id": oid, "organization_id": org_id})
    if not booking:
        raise Exception(f"Booking not found: {booking_id}")
    
    # Check booking_events for BOOKING_CONFIRMED
    event = db.booking_events.find_one({
        "organization_id": org_id,
        "booking_id": booking_id,
        "event": "BOOKING_CONFIRMED"
    })
    
    # Check audit_logs for B2B_BOOKING_CONFIRMED
    audit = db.audit_logs.find_one({
        "organization_id": org_id,
        "action": "B2B_BOOKING_CONFIRMED",
        "target.id": booking_id
    })
    
    mongo_client.close()
    
    return {
        "booking": booking,
        "event": event,
        "audit": audit
    }

def test_happy_path_marketplace_booking_confirmation():
    """Test 1: Happy path - Complete marketplace booking flow with confirmation"""
    print("\n" + "=" * 80)
    print("TEST 1: HAPPY PATH - MARKETPLACE BOOKING CONFIRMATION")
    print("Testing complete marketplace booking flow with supplier fulfilment")
    print("=" * 80 + "\n")
    
    # Setup marketplace infrastructure
    infrastructure = setup_marketplace_infrastructure("happy")
    org_id = infrastructure["org_id"]
    
    try:
        # 1. Create agency_admin user and get JWT token
        print("1️⃣  Creating agency_admin user and logging in...")
        email = f"agency_admin_{infrastructure['unique_id']}@test.com"
        token = create_agency_admin_user_and_login(org_id, email)
        print(f"   ✅ Created agency_admin user: {email}")
        
        # 2. Resolve supplier mapping for listing
        mapping = resolve_supplier_mapping(infrastructure["listing_id"], token)
        assert mapping["status"] == "resolved", f"Mapping should be resolved, got {mapping['status']}"
        assert mapping["supplier"] == "mock_supplier_v1", f"Supplier should be mock_supplier_v1, got {mapping['supplier']}"
        
        # 3. Create draft booking via marketplace flow
        booking_id = create_draft_booking(infrastructure, token)
        
        # 4. Confirm the booking
        print("4️⃣  Confirming the booking...")
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Tenant-Key": infrastructure["buyer_tenant_key"]
        }
        
        r = requests.post(f"{BASE_URL}/api/b2b/bookings/{booking_id}/confirm", headers=headers)
        
        print(f"   📋 Response status: {r.status_code}")
        print(f"   📋 Response body: {r.text}")
        
        # 5. Assert HTTP 200
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        
        # 6. Assert response structure
        data = r.json()
        print(f"   📋 Parsed response: {json.dumps(data, indent=2)}")
        
        assert "booking_id" in data, "Response should contain 'booking_id' field"
        assert data["booking_id"] == booking_id, f"booking_id should match: expected {booking_id}, got {data['booking_id']}"
        
        assert "state" in data, "Response should contain 'state' field"
        assert data["state"] == "confirmed", f"state should be 'confirmed', got {data['state']}"
        
        # 7. Verify database state
        print("7️⃣  Verifying database state...")
        db_state = verify_booking_confirmed_in_db(booking_id, org_id)
        
        booking = db_state["booking"]
        assert booking["status"] == "CONFIRMED", f"Booking status should be CONFIRMED, got {booking.get('status')}"
        
        # Check supplier_booking_id is set
        offer_ref = booking.get("offer_ref", {})
        supplier_booking_id = offer_ref.get("supplier_booking_id")
        assert supplier_booking_id is not None, "supplier_booking_id should be set"
        assert supplier_booking_id.startswith("MOCK-BKG-"), f"supplier_booking_id should start with MOCK-BKG-, got {supplier_booking_id}"
        
        # Check booking event
        event = db_state["event"]
        assert event is not None, "BOOKING_CONFIRMED event should exist"
        assert event["event"] == "BOOKING_CONFIRMED", f"Event should be BOOKING_CONFIRMED, got {event['event']}"
        
        # Check audit log
        audit = db_state["audit"]
        assert audit is not None, "B2B_BOOKING_CONFIRMED audit log should exist"
        assert audit["action"] == "B2B_BOOKING_CONFIRMED", f"Audit action should be B2B_BOOKING_CONFIRMED, got {audit['action']}"
        
        meta = audit.get("meta", {})
        assert meta.get("source") == "supplier_fulfilment", f"Audit meta.source should be supplier_fulfilment, got {meta.get('source')}"
        assert meta.get("supplier") == "mock_supplier_v1", f"Audit meta.supplier should be mock_supplier_v1, got {meta.get('supplier')}"
        assert meta.get("supplier_offer_id") is not None, "Audit meta.supplier_offer_id should be set"
        assert meta.get("attempt_id") is not None, "Audit meta.attempt_id should be set"
        
        print(f"   ✅ All database verifications passed")
        print(f"   ✅ Supplier booking ID: {supplier_booking_id}")
        
        return booking_id, org_id
        
    except Exception as e:
        cleanup_test_data([org_id])
        raise e
    
    print(f"\n✅ TEST 1 COMPLETED: Happy path marketplace booking confirmation successful")

def test_missing_supplier_mapping():
    """Test 2: Missing supplier mapping scenario"""
    print("\n" + "=" * 80)
    print("TEST 2: MISSING SUPPLIER MAPPING SCENARIO")
    print("Testing booking confirmation with missing supplier mapping")
    print("=" * 80 + "\n")
    
    # Setup basic infrastructure
    infrastructure = setup_marketplace_infrastructure("missing")
    org_id = infrastructure["org_id"]
    
    try:
        # 1. Create agency_admin user
        print("1️⃣  Creating agency_admin user and logging in...")
        email = f"agency_admin_{infrastructure['unique_id']}@test.com"
        token = create_agency_admin_user_and_login(org_id, email)
        
        # 2. Manually create a draft booking without proper supplier mapping
        print("2️⃣  Creating draft booking with missing supplier mapping...")
        
        mongo_client = get_mongo_client()
        db = mongo_client.get_default_database()
        
        now = datetime.utcnow()
        booking_doc = {
            "organization_id": org_id,
            "state": "draft",
            "status": "PENDING",
            "source": "b2b_marketplace",
            "currency": "TRY",
            "amount": 115.0,
            "customer_email": f"test-{infrastructure['unique_id']}@example.com",
            "customer_name": "Test Customer",
            "offer_ref": {
                "source": "marketplace",
                "listing_id": infrastructure["listing_id"],
                "buyer_tenant_id": infrastructure["buyer_tenant_id"],
                "seller_tenant_id": infrastructure["seller_tenant_id"],
                # Missing supplier and supplier_offer_id fields
            },
            "created_at": now,
            "updated_at": now,
        }
        
        result = db.bookings.insert_one(booking_doc)
        booking_id = str(result.inserted_id)
        
        mongo_client.close()
        
        print(f"   ✅ Created draft booking with missing mapping: {booking_id}")
        
        # 3. Try to confirm the booking
        print("3️⃣  Attempting to confirm booking with missing supplier mapping...")
        
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Tenant-Key": infrastructure["buyer_tenant_key"]
        }
        
        r = requests.post(f"{BASE_URL}/api/b2b/bookings/{booking_id}/confirm", headers=headers)
        
        print(f"   📋 Response status: {r.status_code}")
        print(f"   📋 Response body: {r.text}")
        
        # 4. Assert HTTP 422
        assert r.status_code == 422, f"Expected 422, got {r.status_code}: {r.text}"
        
        # 5. Assert error structure
        data = r.json()
        print(f"   📋 Parsed error response: {json.dumps(data, indent=2)}")
        
        assert "error" in data, "Response should contain 'error' field"
        error = data["error"]
        
        assert "code" in error, "Error should contain 'code' field"
        assert error["code"] == "INVALID_SUPPLIER_MAPPING", f"Error code should be INVALID_SUPPLIER_MAPPING, got {error['code']}"
        
        assert "details" in error, "Error should contain 'details' field"
        details = error["details"]
        
        assert "reason" in details, "Error details should contain 'reason' field"
        reason = details["reason"]
        assert reason in ["missing_supplier", "missing_supplier_offer_id", "unsupported_supplier"], f"Reason should be one of expected values, got {reason}"
        
        print(f"   ✅ Missing supplier mapping correctly rejected with reason: {reason}")
        
    finally:
        cleanup_test_data([org_id])
    
    print(f"\n✅ TEST 2 COMPLETED: Missing supplier mapping scenario successful")

def test_tenant_mismatch():
    """Test 3: Tenant mismatch scenario"""
    print("\n" + "=" * 80)
    print("TEST 3: TENANT MISMATCH SCENARIO")
    print("Testing booking confirmation with wrong tenant context")
    print("=" * 80 + "\n")
    
    # Setup infrastructure
    infrastructure = setup_marketplace_infrastructure("mismatch")
    org_id = infrastructure["org_id"]
    
    try:
        # 1. Create agency_admin user
        print("1️⃣  Creating agency_admin user and logging in...")
        email = f"agency_admin_{infrastructure['unique_id']}@test.com"
        token = create_agency_admin_user_and_login(org_id, email)
        
        # 2. Create a second buyer tenant for mismatch test
        print("2️⃣  Creating second buyer tenant for mismatch test...")
        
        mongo_client = get_mongo_client()
        db = mongo_client.get_default_database()
        
        different_tenant_id = f"different_tenant_{infrastructure['unique_id']}"
        different_tenant_key = f"different-tenant-{infrastructure['unique_id']}"
        
        tenant_doc = {
            "_id": different_tenant_id,
            "organization_id": org_id,
            "tenant_key": different_tenant_key,
            "name": f"Different Tenant {infrastructure['unique_id']}",
            "type": "buyer",
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        db.tenants.insert_one(tenant_doc)
        
        # 3. Create draft booking with original buyer tenant
        now = datetime.utcnow()
        booking_doc = {
            "organization_id": org_id,
            "state": "draft",
            "status": "PENDING",
            "source": "b2b_marketplace",
            "currency": "TRY",
            "amount": 115.0,
            "customer_email": f"test-{infrastructure['unique_id']}@example.com",
            "customer_name": "Test Customer",
            "offer_ref": {
                "source": "marketplace",
                "listing_id": infrastructure["listing_id"],
                "buyer_tenant_id": infrastructure["buyer_tenant_id"],  # Original buyer tenant
                "seller_tenant_id": infrastructure["seller_tenant_id"],
                "supplier": "mock_supplier_v1",
                "supplier_offer_id": f"MOCK-OFFER-{infrastructure['unique_id']}",
            },
            "created_at": now,
            "updated_at": now,
        }
        
        result = db.bookings.insert_one(booking_doc)
        booking_id = str(result.inserted_id)
        
        mongo_client.close()
        
        print(f"   ✅ Created draft booking: {booking_id}")
        print(f"   ✅ Booking buyer_tenant_id: {infrastructure['buyer_tenant_id']}")
        print(f"   ✅ Different tenant key: {different_tenant_key}")
        
        # 4. Try to confirm with different tenant key
        print("4️⃣  Attempting to confirm with different tenant context...")
        
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Tenant-Key": different_tenant_key  # Different tenant!
        }
        
        r = requests.post(f"{BASE_URL}/api/b2b/bookings/{booking_id}/confirm", headers=headers)
        
        print(f"   📋 Response status: {r.status_code}")
        print(f"   📋 Response body: {r.text}")
        
        # 5. Assert HTTP 422
        assert r.status_code == 422, f"Expected 422, got {r.status_code}: {r.text}"
        
        # 6. Assert error structure
        data = r.json()
        print(f"   📋 Parsed error response: {json.dumps(data, indent=2)}")
        
        assert "error" in data, "Response should contain 'error' field"
        error = data["error"]
        
        assert "code" in error, "Error should contain 'code' field"
        assert error["code"] == "BOOKING_NOT_CONFIRMABLE", f"Error code should be BOOKING_NOT_CONFIRMABLE, got {error['code']}"
        
        assert "details" in error, "Error should contain 'details' field"
        details = error["details"]
        
        assert "reason" in details, "Error details should contain 'reason' field"
        assert details["reason"] == "invalid_state", f"Reason should be invalid_state, got {details['reason']}"
        
        print(f"   ✅ Tenant mismatch correctly rejected")
        
    finally:
        cleanup_test_data([org_id])
    
    print(f"\n✅ TEST 3 COMPLETED: Tenant mismatch scenario successful")

def test_idempotent_confirm():
    """Test 4: Idempotent confirm scenario"""
    print("\n" + "=" * 80)
    print("TEST 4: IDEMPOTENT CONFIRM SCENARIO")
    print("Testing repeated confirmation calls are idempotent")
    print("=" * 80 + "\n")
    
    # Setup infrastructure
    infrastructure = setup_marketplace_infrastructure("idempotent")
    org_id = infrastructure["org_id"]
    
    try:
        # 1. Create agency_admin user
        print("1️⃣  Creating agency_admin user and logging in...")
        email = f"agency_admin_{infrastructure['unique_id']}@test.com"
        token = create_agency_admin_user_and_login(org_id, email)
        
        # 2. Create a booking that's already CONFIRMED
        print("2️⃣  Creating pre-confirmed booking...")
        
        mongo_client = get_mongo_client()
        db = mongo_client.get_default_database()
        
        now = datetime.utcnow()
        booking_doc = {
            "organization_id": org_id,
            "state": "draft",  # State can remain draft
            "status": "CONFIRMED",  # But projection is CONFIRMED
            "source": "b2b_marketplace",
            "currency": "TRY",
            "amount": 115.0,
            "customer_email": f"test-{infrastructure['unique_id']}@example.com",
            "customer_name": "Test Customer",
            "offer_ref": {
                "source": "marketplace",
                "listing_id": infrastructure["listing_id"],
                "buyer_tenant_id": infrastructure["buyer_tenant_id"],
                "seller_tenant_id": infrastructure["seller_tenant_id"],
                "supplier": "mock_supplier_v1",
                "supplier_offer_id": f"MOCK-OFFER-{infrastructure['unique_id']}",
                "supplier_booking_id": f"MOCK-BKG-{infrastructure['unique_id']}",
            },
            "created_at": now,
            "updated_at": now,
        }
        
        result = db.bookings.insert_one(booking_doc)
        booking_id = str(result.inserted_id)
        
        mongo_client.close()
        
        print(f"   ✅ Created pre-confirmed booking: {booking_id}")
        
        # 3. First confirm call
        print("3️⃣  Making first confirm call...")
        
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Tenant-Key": infrastructure["buyer_tenant_key"]
        }
        
        r1 = requests.post(f"{BASE_URL}/api/b2b/bookings/{booking_id}/confirm", headers=headers)
        
        print(f"   📋 First call status: {r1.status_code}")
        print(f"   📋 First call body: {r1.text}")
        
        # 4. Assert first call returns 200
        assert r1.status_code == 200, f"Expected 200, got {r1.status_code}: {r1.text}"
        
        data1 = r1.json()
        assert data1["booking_id"] == booking_id, f"booking_id should match"
        assert data1["state"] == "confirmed", f"state should be confirmed"
        
        # 5. Second confirm call (should be idempotent)
        print("5️⃣  Making second confirm call (idempotent)...")
        
        r2 = requests.post(f"{BASE_URL}/api/b2b/bookings/{booking_id}/confirm", headers=headers)
        
        print(f"   📋 Second call status: {r2.status_code}")
        print(f"   📋 Second call body: {r2.text}")
        
        # 6. Assert second call also returns 200
        assert r2.status_code == 200, f"Expected 200, got {r2.status_code}: {r2.text}"
        
        data2 = r2.json()
        assert data2["booking_id"] == booking_id, f"booking_id should match"
        assert data2["state"] == "confirmed", f"state should be confirmed"
        
        # 7. Verify only one event and audit log exist
        print("7️⃣  Verifying idempotent behavior in database...")
        
        mongo_client = get_mongo_client()
        db = mongo_client.get_default_database()
        
        # Count BOOKING_CONFIRMED events
        event_count = db.booking_events.count_documents({
            "organization_id": org_id,
            "booking_id": booking_id,
            "event": "BOOKING_CONFIRMED"
        })
        
        # Count B2B_BOOKING_CONFIRMED audit logs
        audit_count = db.audit_logs.count_documents({
            "organization_id": org_id,
            "action": "B2B_BOOKING_CONFIRMED",
            "target.id": booking_id
        })
        
        mongo_client.close()
        
        print(f"   📋 BOOKING_CONFIRMED events: {event_count}")
        print(f"   📋 B2B_BOOKING_CONFIRMED audit logs: {audit_count}")
        
        # Should have exactly 1 of each (idempotent)
        assert event_count == 1, f"Should have exactly 1 BOOKING_CONFIRMED event, got {event_count}"
        assert audit_count == 1, f"Should have exactly 1 B2B_BOOKING_CONFIRMED audit log, got {audit_count}"
        
        print(f"   ✅ Idempotent behavior verified - no duplicate events/audits")
        
    finally:
        cleanup_test_data([org_id])
    
    print(f"\n✅ TEST 4 COMPLETED: Idempotent confirm scenario successful")

def run_all_tests():
    """Run all PR-16 supplier fulfilment tests"""
    print("\n" + "🚀" * 80)
    print("PR-16 SUPPLIER FULFILMENT V1 BACKEND VALIDATION")
    print("Testing POST /api/b2b/bookings/{booking_id}/confirm endpoint")
    print("🚀" * 80)
    
    test_functions = [
        test_happy_path_marketplace_booking_confirmation,
        test_missing_supplier_mapping,
        test_tenant_mismatch,
        test_idempotent_confirm,
    ]
    
    passed_tests = 0
    failed_tests = 0
    
    for test_func in test_functions:
        try:
            test_func()
            passed_tests += 1
        except Exception as e:
            print(f"\n❌ TEST FAILED: {test_func.__name__}")
            print(f"   Error: {e}")
            failed_tests += 1
    
    print("\n" + "🏁" * 80)
    print("TEST SUMMARY")
    print("🏁" * 80)
    print(f"✅ Passed: {passed_tests}")
    print(f"❌ Failed: {failed_tests}")
    print(f"📊 Total: {passed_tests + failed_tests}")
    
    if failed_tests == 0:
        print("\n🎉 ALL TESTS PASSED! PR-16 supplier fulfilment v1 validation complete.")
    else:
        print(f"\n⚠️  {failed_tests} test(s) failed. Please review the errors above.")
    
    print("\n📋 TESTED SCENARIOS:")
    print("✅ Happy path: Complete marketplace booking flow with confirmation")
    print("✅ Missing supplier mapping: Proper error handling for incomplete mappings")
    print("✅ Tenant mismatch: Proper validation of tenant context")
    print("✅ Idempotent confirm: Repeated calls don't create duplicates")
    
    return failed_tests == 0

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)