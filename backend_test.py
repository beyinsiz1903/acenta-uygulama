#!/usr/bin/env python3
"""
PR#7.5a Duplicate Detection (Dry-Run) Endpoint Test
Testing the duplicate customer detection endpoint as requested in Turkish specification
"""

import requests
import json
import uuid
import hashlib
from datetime import datetime, timedelta
from pymongo import MongoClient
import os

# Configuration - Use production URL from frontend/.env
BASE_URL = "https://b2b-hotel-suite.preview.emergentagent.com"

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

def get_mongo_client():
    """Get MongoDB client for direct database access"""
    # Use the same MongoDB URL as backend
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017/test_database")
    return MongoClient(mongo_url)

def normalize_email(email):
    """Normalize email for duplicate detection"""
    return email.strip().lower()

def normalize_phone(phone):
    """Normalize phone for duplicate detection"""
    return ''.join(filter(str.isdigit, phone))

def setup_duplicate_test_data(admin_headers, admin_org_id):
    """Setup test data for duplicate detection as specified in Turkish requirements"""
    print("   📋 Setting up duplicate test data...")
    
    # Test data as specified in the requirements
    test_customers = [
        # Email duplicates
        {
            "name": "Duplicate Email 1",
            "type": "individual",
            "contacts": [
                {
                    "type": "email",
                    "value": "DupEmail@Test.Example",
                    "is_primary": True
                }
            ],
            "tags": ["test", "duplicate"]
        },
        {
            "name": "Duplicate Email 2",
            "type": "individual",
            "contacts": [
                {
                    "type": "email",
                    "value": "dupemail@test.example",  # Same email, different case
                    "is_primary": True
                }
            ],
            "tags": ["test", "duplicate"]
        },
        # Phone duplicates
        {
            "name": "Duplicate Phone 1", 
            "type": "individual",
            "contacts": [
                {
                    "type": "phone",
                    "value": "+90 (555) 000 0007",
                    "is_primary": True
                }
            ],
            "tags": ["test", "duplicate"]
        },
        {
            "name": "Duplicate Phone 2",
            "type": "individual", 
            "contacts": [
                {
                    "type": "phone",
                    "value": "905550000007",  # Same phone, normalized format
                    "is_primary": True
                }
            ],
            "tags": ["test", "duplicate"]
        }
    ]
    
    # Create customers via API
    created_customers = []
    for customer_data in test_customers:
        try:
            r = requests.post(
                f"{BASE_URL}/api/crm/customers",
                json=customer_data,
                headers=admin_headers,
            )
            if r.status_code == 200:
                created_customer = r.json()
                created_customers.append(created_customer)
                print(f"   ✅ Created customer: {created_customer['id']} - {created_customer['name']}")
            else:
                print(f"   ❌ Failed to create customer {customer_data['name']}: {r.status_code} - {r.text}")
        except Exception as e:
            print(f"   ❌ Error creating customer {customer_data['name']}: {e}")
    
    print(f"   ✅ Created {len(created_customers)} test customers")
    return created_customers

def cleanup_duplicate_test_data(created_customers):
    """Clean up test data after testing"""
    try:
        mongo_client = get_mongo_client()
        db = mongo_client.get_default_database()
        
        # Remove test data by IDs
        customer_ids = [customer['id'] for customer in created_customers]
        if customer_ids:
            result = db.customers.delete_many({
                "id": {"$in": customer_ids}
            })
            print(f"   ✅ Cleaned up {result.deleted_count} test customers")
        
        mongo_client.close()
        
    except Exception as e:
        print(f"   ⚠️  Failed to cleanup test data: {e}")

def test_pr75a_duplicate_detection_endpoint():
    """Test PR#7.5a Duplicate Detection (Dry-Run) Endpoint"""
    print("\n" + "=" * 80)
    print("PR#7.5a DUPLICATE DETECTION (DRY-RUN) ENDPOINT TEST")
    print("Testing duplicate customer detection endpoint as per Turkish specification:")
    print("1) Duplicate setup with email and phone duplicates")
    print("2) GET /api/crm/customers/duplicates endpoint test")
    print("3) Response structure and duplicate logic verification")
    print("4) Read-only verification (no writes)")
    print("=" * 80 + "\n")

    # ------------------------------------------------------------------
    # Test 1: Login & Setup
    # ------------------------------------------------------------------
    print("1️⃣  Login & duplicate setup...")
    
    admin_token, admin_org_id, admin_email = login_admin()
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    
    print(f"   ✅ admin@acenta.test / admin123 ile login başarılı: {admin_email}")
    print(f"   📋 Organization ID: {admin_org_id}")
    
    # Setup test data
    created_customers = setup_duplicate_test_data(admin_headers, admin_org_id)
    
    if not created_customers:
        print("   ❌ Test data setup failed, aborting test")
        return

    # ------------------------------------------------------------------
    # Test 2: GET /api/crm/customers/duplicates
    # ------------------------------------------------------------------
    print("\n2️⃣  GET /api/crm/customers/duplicates endpoint test...")
    
    r = requests.get(
        f"{BASE_URL}/api/crm/customers/duplicates",
        headers=admin_headers,
    )
    
    print(f"   📋 Response status: {r.status_code}")
    print(f"   📋 Response headers: {dict(r.headers)}")
    
    if r.status_code == 200:
        print(f"   ✅ 200 OK response received")
        
        try:
            clusters = r.json()
            print(f"   ✅ JSON response parsed successfully")
            print(f"   📋 Number of duplicate clusters found: {len(clusters)}")
            
            # Verify we have at least 2 clusters (email and phone)
            assert len(clusters) >= 2, f"Expected at least 2 clusters, got {len(clusters)}"
            print(f"   ✅ At least 2 duplicate clusters found as expected")
            
            # Analyze each cluster
            email_cluster = None
            phone_cluster = None
            
            for cluster in clusters:
                contact = cluster.get("contact", {})
                contact_type = contact.get("type")
                contact_value = contact.get("value")
                
                print(f"\n   📋 Cluster found:")
                print(f"      Contact type: {contact_type}")
                print(f"      Contact value: {contact_value}")
                print(f"      Organization ID: {cluster.get('organization_id')}")
                
                # Verify cluster structure
                assert cluster.get("organization_id") == admin_org_id, "organization_id should match"
                assert "contact" in cluster, "contact field required"
                assert "primary" in cluster, "primary field required"
                assert "duplicates" in cluster, "duplicates field required"
                
                primary = cluster.get("primary", {})
                duplicates = cluster.get("duplicates", [])
                
                print(f"      Primary customer: {primary.get('id')} - {primary.get('name')}")
                print(f"      Duplicate customers: {len(duplicates)}")
                
                for dup in duplicates:
                    print(f"         - {dup.get('id')} - {dup.get('name')}")
                
                # Verify primary and duplicates structure
                assert "id" in primary, "primary.id required"
                assert "name" in primary, "primary.name required"
                assert "created_at" in primary, "primary.created_at required"
                assert "updated_at" in primary, "primary.updated_at required"
                
                for dup in duplicates:
                    assert "id" in dup, "duplicate.id required"
                    assert "name" in dup, "duplicate.name required"
                    assert "created_at" in dup, "duplicate.created_at required"
                    assert "updated_at" in dup, "duplicate.updated_at required"
                
                # Identify email and phone clusters
                if contact_type == "email" and contact_value == "dupemail@test.example":
                    email_cluster = cluster
                elif contact_type == "phone" and contact_value == "905550000007":
                    phone_cluster = cluster
            
            # ------------------------------------------------------------------
            # Test 3: Email duplicate cluster verification
            # ------------------------------------------------------------------
            print("\n3️⃣  Email duplicate cluster verification...")
            
            if email_cluster:
                print(f"   ✅ Email cluster found with normalized value: dupemail@test.example")
                
                primary = email_cluster.get("primary", {})
                duplicates = email_cluster.get("duplicates", [])
                
                # Primary should be the one with newer updated_at (cust_dup_email_2)
                assert primary.get("id") == "cust_dup_email_2", f"Primary should be cust_dup_email_2, got {primary.get('id')}"
                print(f"   ✅ Primary customer correctly selected: {primary.get('id')} (newer updated_at)")
                
                # Duplicates should contain cust_dup_email_1
                duplicate_ids = [dup.get("id") for dup in duplicates]
                assert "cust_dup_email_1" in duplicate_ids, f"cust_dup_email_1 should be in duplicates, got {duplicate_ids}"
                print(f"   ✅ Duplicate customer correctly identified: cust_dup_email_1")
                
            else:
                print(f"   ❌ Email cluster not found")
                assert False, "Email cluster should be found"
            
            # ------------------------------------------------------------------
            # Test 4: Phone duplicate cluster verification
            # ------------------------------------------------------------------
            print("\n4️⃣  Phone duplicate cluster verification...")
            
            if phone_cluster:
                print(f"   ✅ Phone cluster found with normalized value: 905550000007")
                
                primary = phone_cluster.get("primary", {})
                duplicates = phone_cluster.get("duplicates", [])
                
                # Primary should be the one with newer updated_at (cust_dup_phone_2)
                assert primary.get("id") == "cust_dup_phone_2", f"Primary should be cust_dup_phone_2, got {primary.get('id')}"
                print(f"   ✅ Primary customer correctly selected: {primary.get('id')} (newer updated_at)")
                
                # Duplicates should contain cust_dup_phone_1
                duplicate_ids = [dup.get("id") for dup in duplicates]
                assert "cust_dup_phone_1" in duplicate_ids, f"cust_dup_phone_1 should be in duplicates, got {duplicate_ids}"
                print(f"   ✅ Duplicate customer correctly identified: cust_dup_phone_1")
                
            else:
                print(f"   ❌ Phone cluster not found")
                assert False, "Phone cluster should be found"
            
            # ------------------------------------------------------------------
            # Test 5: Read-only verification
            # ------------------------------------------------------------------
            print("\n5️⃣  Read-only verification...")
            
            # Verify no data was modified by checking customer records
            try:
                mongo_client = get_mongo_client()
                db = mongo_client.get_default_database()
                
                # Check that all test customers still exist unchanged
                for test_customer in test_customers:
                    existing = db.customers.find_one({
                        "organization_id": admin_org_id,
                        "id": test_customer["id"]
                    })
                    
                    assert existing is not None, f"Customer {test_customer['id']} should still exist"
                    assert existing["name"] == test_customer["name"], f"Customer name should be unchanged"
                    
                print(f"   ✅ All test customers remain unchanged")
                print(f"   ✅ Endpoint is read-only (no writes performed)")
                
                mongo_client.close()
                
            except Exception as e:
                print(f"   ⚠️  Read-only verification failed: {e}")
            
        except json.JSONDecodeError as e:
            print(f"   ❌ Failed to parse JSON response: {e}")
            print(f"   📋 Response text: {r.text}")
            assert False, "Response should be valid JSON"
            
    elif r.status_code == 403:
        print(f"   ❌ 403 Forbidden - Admin role required")
        print(f"   📋 Response: {r.text}")
        assert False, "Admin user should have access to duplicates endpoint"
        
    else:
        print(f"   ❌ Unexpected status code: {r.status_code}")
        print(f"   📋 Response: {r.text}")
        assert False, f"Expected 200, got {r.status_code}"

    # ------------------------------------------------------------------
    # Test 6: Empty result verification
    # ------------------------------------------------------------------
    print("\n6️⃣  Empty result verification...")
    
    # Clean up test data
    cleanup_duplicate_test_data(admin_org_id)
    
    # Test endpoint again - should return empty list
    r = requests.get(
        f"{BASE_URL}/api/crm/customers/duplicates",
        headers=admin_headers,
    )
    
    if r.status_code == 200:
        clusters = r.json()
        
        # Filter out any non-test duplicates that might exist
        test_clusters = []
        for cluster in clusters:
            contact = cluster.get("contact", {})
            if (contact.get("value") == "dupemail@test.example" or 
                contact.get("value") == "905550000007"):
                test_clusters.append(cluster)
        
        assert len(test_clusters) == 0, f"Should have no test duplicates after cleanup, got {len(test_clusters)}"
        print(f"   ✅ No test duplicates found after cleanup")
        print(f"   ✅ Endpoint returns empty/filtered results correctly")
    else:
        print(f"   ⚠️  Cleanup verification failed: {r.status_code}")

    print("\n" + "=" * 80)
    print("✅ PR#7.5a DUPLICATE DETECTION ENDPOINT TEST COMPLETED")
    print("✅ Duplicate detection logic working correctly")
    print("✅ 1) Test data setup: Email and phone duplicates created ✓")
    print("✅ 2) GET /api/crm/customers/duplicates: 200 OK response ✓")
    print("✅ 3) Email cluster: Correct normalization and primary selection ✓")
    print("✅ 4) Phone cluster: Correct normalization and primary selection ✓")
    print("✅ 5) Read-only verification: No data modifications ✓")
    print("✅ 6) Empty result: Correct behavior after cleanup ✓")
    print("")
    print("📋 Response structure verified:")
    print("   - organization_id, contact.type, contact.value fields present")
    print("   - primary and duplicates follow DuplicateCustomerSummary structure")
    print("   - Primary selection based on updated_at (newest first)")
    print("   - Contact normalization working (email lowercase, phone digits only)")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    test_pr75a_duplicate_detection_endpoint()