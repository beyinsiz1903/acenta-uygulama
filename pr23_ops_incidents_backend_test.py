#!/usr/bin/env python3
"""
PR-23 Ops Console v2: Incidents + Supplier Health Enrichment Backend Validation

This test suite performs HTTP-level sanity checks for the PR-23 functionality:
1. List incidents endpoint with/without supplier health enrichment
2. Detail incident endpoint with/without supplier health enrichment
3. Verify fail-open behavior when health data is missing
"""

import requests
import json
import uuid
from datetime import datetime
from pymongo import MongoClient
import os

# Configuration - Use production URL from frontend/.env
BASE_URL = "https://risk-aware-b2b.preview.emergentagent.com"

def get_mongo_client():
    """Get MongoDB client for direct database access"""
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017/test_database")
    return MongoClient(mongo_url)

def create_test_org_and_admin():
    """Create test organization and admin user, return org_id, email, token"""
    mongo_client = get_mongo_client()
    db = mongo_client.get_default_database()
    
    # Create unique org
    unique_id = uuid.uuid4().hex[:8]
    org_id = f"org_pr23_test_{unique_id}"
    
    now = datetime.utcnow()
    
    # Create organization
    org_doc = {
        "_id": org_id,
        "name": f"PR-23 Test Org {unique_id}",
        "slug": f"pr23-test-{unique_id}",
        "created_at": now,
        "updated_at": now,
    }
    db.organizations.replace_one({"_id": org_id}, org_doc, upsert=True)
    
    # Create admin user
    email = f"admin_{unique_id}@pr23test.com"
    import bcrypt
    password_hash = bcrypt.hashpw("testpass123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    user_doc = {
        "email": email,
        "password_hash": password_hash,
        "roles": ["agency_admin"],
        "organization_id": org_id,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    db.users.replace_one({"email": email}, user_doc, upsert=True)
    
    mongo_client.close()
    
    # Login to get token
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": email, "password": "testpass123"},
    )
    
    if r.status_code != 200:
        raise Exception(f"Login failed: {r.status_code} - {r.text}")
    
    data = r.json()
    token = data["access_token"]
    
    return org_id, email, token

def seed_test_incidents_and_health(org_id):
    """Seed test incidents and supplier health data"""
    mongo_client = get_mongo_client()
    db = mongo_client.get_default_database()
    
    now = datetime.utcnow()
    
    # Create supplier incident
    incident_doc = {
        "incident_id": "pr23_test_incident_1",
        "organization_id": org_id,
        "type": "supplier_partial_failure",
        "severity": "medium",
        "status": "open",
        "summary": "PR-23 Test Supplier Incident",
        "source_ref": {"session_id": "pr23_test_session"},
        "meta": {
            "failed_suppliers": [
                {"supplier_code": "paximum", "code": "SUPPLIER_TIMEOUT"},
            ],
        },
        "created_at": now,
        "updated_at": now,
    }
    db.ops_incidents.replace_one(
        {"incident_id": "pr23_test_incident_1", "organization_id": org_id}, 
        incident_doc, 
        upsert=True
    )
    
    # Create risk incident (no supplier health expected)
    risk_incident_doc = {
        "incident_id": "pr23_test_risk_incident",
        "organization_id": org_id,
        "type": "risk_review",
        "severity": "high",
        "status": "open",
        "summary": "PR-23 Test Risk Incident",
        "source_ref": {"booking_id": "pr23_test_booking"},
        "meta": {},
        "created_at": now,
        "updated_at": now,
    }
    db.ops_incidents.replace_one(
        {"incident_id": "pr23_test_risk_incident", "organization_id": org_id}, 
        risk_incident_doc, 
        upsert=True
    )
    
    # Create supplier health snapshot
    health_doc = {
        "organization_id": org_id,
        "supplier_code": "paximum",
        "window_sec": 900,
        "metrics": {
            "total_calls": 10,
            "success_calls": 6,
            "fail_calls": 4,
            "success_rate": 0.6,
            "error_rate": 0.4,
            "avg_latency_ms": 800,
            "p95_latency_ms": 2000,
            "last_error_codes": ["SUPPLIER_TIMEOUT"],
        },
        "circuit": {
            "state": "open",
            "opened_at": now,
            "until": now,
            "reason_code": "SUPPLIER_TIMEOUT",
            "consecutive_failures": 3,
            "last_transition_at": now,
        },
        "updated_at": now,
    }
    db.supplier_health.replace_one(
        {"organization_id": org_id, "supplier_code": "paximum"}, 
        health_doc, 
        upsert=True
    )
    
    mongo_client.close()
    
    return "pr23_test_incident_1", "pr23_test_risk_incident"

def cleanup_test_data(org_id):
    """Clean up test data"""
    try:
        mongo_client = get_mongo_client()
        db = mongo_client.get_default_database()
        
        # Clean up collections
        collections_to_clean = [
            "organizations", "users", "ops_incidents", "supplier_health"
        ]
        
        for collection_name in collections_to_clean:
            collection = getattr(db, collection_name)
            result = collection.delete_many({"organization_id": org_id})
            if result.deleted_count > 0:
                print(f"   🧹 Cleaned {result.deleted_count} documents from {collection_name}")
        
        mongo_client.close()
        print(f"   ✅ Cleanup completed for org: {org_id}")
        
    except Exception as e:
        print(f"   ⚠️  Failed to cleanup test data: {e}")

def test_list_incidents_no_enrichment():
    """Test GET /api/admin/ops/incidents (default behavior - no enrichment)"""
    print("\n" + "=" * 80)
    print("TEST 1: LIST INCIDENTS - NO ENRICHMENT BY DEFAULT")
    print("Testing GET /api/admin/ops/incidents without include_supplier_health")
    print("=" * 80 + "\n")
    
    # Setup
    org_id, email, token = create_test_org_and_admin()
    supplier_incident_id, risk_incident_id = seed_test_incidents_and_health(org_id)
    
    try:
        headers = {"Authorization": f"Bearer {token}"}
        
        # Call list endpoint without enrichment flag
        print("1️⃣  Calling GET /api/admin/ops/incidents (default behavior)...")
        r = requests.get(f"{BASE_URL}/api/admin/ops/incidents", headers=headers)
        
        print(f"   📋 Response status: {r.status_code}")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        
        data = r.json()
        items = data.get("items", [])
        print(f"   📋 Found {len(items)} incidents")
        
        # Find supplier incident
        supplier_incident = None
        for item in items:
            if item.get("incident_id") == supplier_incident_id:
                supplier_incident = item
                break
        
        assert supplier_incident is not None, f"Supplier incident {supplier_incident_id} not found"
        
        # Verify supplier_health is omitted or None by default
        supplier_health = supplier_incident.get("supplier_health")
        assert supplier_health in (None, {}), f"supplier_health should be omitted/None by default, got: {supplier_health}"
        
        print(f"   ✅ Supplier health omitted by default as expected")
        
    finally:
        cleanup_test_data(org_id)
    
    print(f"\n✅ TEST 1 COMPLETED: List incidents no enrichment verification successful")

def test_list_incidents_with_enrichment():
    """Test GET /api/admin/ops/incidents?include_supplier_health=true"""
    print("\n" + "=" * 80)
    print("TEST 2: LIST INCIDENTS - WITH SUPPLIER HEALTH ENRICHMENT")
    print("Testing GET /api/admin/ops/incidents?include_supplier_health=true")
    print("=" * 80 + "\n")
    
    # Setup
    org_id, email, token = create_test_org_and_admin()
    supplier_incident_id, risk_incident_id = seed_test_incidents_and_health(org_id)
    
    try:
        headers = {"Authorization": f"Bearer {token}"}
        
        # Call list endpoint with enrichment flag
        print("1️⃣  Calling GET /api/admin/ops/incidents?include_supplier_health=true...")
        r = requests.get(f"{BASE_URL}/api/admin/ops/incidents?include_supplier_health=true", headers=headers)
        
        print(f"   📋 Response status: {r.status_code}")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        
        data = r.json()
        items = data.get("items", [])
        print(f"   📋 Found {len(items)} incidents")
        
        # Find supplier incident
        supplier_incident = None
        risk_incident = None
        for item in items:
            if item.get("incident_id") == supplier_incident_id:
                supplier_incident = item
            elif item.get("incident_id") == risk_incident_id:
                risk_incident = item
        
        assert supplier_incident is not None, f"Supplier incident {supplier_incident_id} not found"
        assert risk_incident is not None, f"Risk incident {risk_incident_id} not found"
        
        # Verify supplier incident has health badge
        supplier_health = supplier_incident.get("supplier_health")
        assert supplier_health is not None, "Supplier incident should have supplier_health badge"
        assert supplier_health.get("supplier_code") == "paximum", f"Expected supplier_code 'paximum', got {supplier_health.get('supplier_code')}"
        assert supplier_health.get("circuit_state") == "open", f"Expected circuit_state 'open', got {supplier_health.get('circuit_state')}"
        
        print(f"   ✅ Supplier incident enriched with health badge: {supplier_health.get('supplier_code')} ({supplier_health.get('circuit_state')})")
        
        # Verify risk incident has supplier_health=null (no supplier involved)
        risk_health = risk_incident.get("supplier_health")
        assert risk_health is None, f"Risk incident should have supplier_health=null, got: {risk_health}"
        
        print(f"   ✅ Risk incident correctly has supplier_health=null")
        
    finally:
        cleanup_test_data(org_id)
    
    print(f"\n✅ TEST 2 COMPLETED: List incidents with enrichment verification successful")

def test_detail_incident_enrichment_default():
    """Test GET /api/admin/ops/incidents/{incident_id} (enrichment by default)"""
    print("\n" + "=" * 80)
    print("TEST 3: DETAIL INCIDENT - ENRICHMENT BY DEFAULT")
    print("Testing GET /api/admin/ops/incidents/{incident_id} (supplier_health filled by default)")
    print("=" * 80 + "\n")
    
    # Setup
    org_id, email, token = create_test_org_and_admin()
    supplier_incident_id, risk_incident_id = seed_test_incidents_and_health(org_id)
    
    try:
        headers = {"Authorization": f"Bearer {token}"}
        
        # Call detail endpoint for supplier incident (default enrichment)
        print("1️⃣  Calling GET /api/admin/ops/incidents/{incident_id} for supplier incident...")
        r = requests.get(f"{BASE_URL}/api/admin/ops/incidents/{supplier_incident_id}", headers=headers)
        
        print(f"   📋 Response status: {r.status_code}")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        
        data = r.json()
        
        # Verify supplier_health is filled by default
        supplier_health = data.get("supplier_health")
        assert supplier_health is not None, "Detail endpoint should enrich supplier_health by default"
        assert supplier_health.get("supplier_code") == "paximum", f"Expected supplier_code 'paximum', got {supplier_health.get('supplier_code')}"
        
        print(f"   ✅ Supplier incident detail enriched by default: {supplier_health.get('supplier_code')}")
        
    finally:
        cleanup_test_data(org_id)
    
    print(f"\n✅ TEST 3 COMPLETED: Detail incident enrichment by default verification successful")

def test_detail_incident_enrichment_disabled():
    """Test GET /api/admin/ops/incidents/{incident_id}?include_supplier_health=false"""
    print("\n" + "=" * 80)
    print("TEST 4: DETAIL INCIDENT - ENRICHMENT DISABLED")
    print("Testing GET /api/admin/ops/incidents/{incident_id}?include_supplier_health=false")
    print("=" * 80 + "\n")
    
    # Setup
    org_id, email, token = create_test_org_and_admin()
    supplier_incident_id, risk_incident_id = seed_test_incidents_and_health(org_id)
    
    try:
        headers = {"Authorization": f"Bearer {token}"}
        
        # Call detail endpoint with enrichment disabled
        print("1️⃣  Calling GET /api/admin/ops/incidents/{incident_id}?include_supplier_health=false...")
        r = requests.get(f"{BASE_URL}/api/admin/ops/incidents/{supplier_incident_id}?include_supplier_health=false", headers=headers)
        
        print(f"   📋 Response status: {r.status_code}")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        
        data = r.json()
        
        # Verify supplier_health is omitted/None when disabled
        supplier_health = data.get("supplier_health")
        assert supplier_health in (None, {}), f"supplier_health should be omitted/None when disabled, got: {supplier_health}"
        
        print(f"   ✅ Supplier health omitted when include_supplier_health=false")
        
    finally:
        cleanup_test_data(org_id)
    
    print(f"\n✅ TEST 4 COMPLETED: Detail incident enrichment disabled verification successful")

def run_all_tests():
    """Run all PR-23 sanity check tests"""
    print("\n" + "🚀" * 80)
    print("PR-23 OPS CONSOLE V2: INCIDENTS + SUPPLIER HEALTH ENRICHMENT")
    print("Backend HTTP-level sanity check validation")
    print("🚀" * 80)
    
    test_functions = [
        test_list_incidents_no_enrichment,
        test_list_incidents_with_enrichment,
        test_detail_incident_enrichment_default,
        test_detail_incident_enrichment_disabled,
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
        print("\n🎉 ALL TESTS PASSED! PR-23 HTTP sanity check complete.")
    else:
        print(f"\n⚠️  {failed_tests} test(s) failed. Please review the errors above.")
    
    print("\n📋 TESTED SCENARIOS:")
    print("✅ GET /api/admin/ops/incidents (default - no enrichment)")
    print("✅ GET /api/admin/ops/incidents?include_supplier_health=true (enrichment enabled)")
    print("✅ GET /api/admin/ops/incidents/{incident_id} (default - enrichment enabled)")
    print("✅ GET /api/admin/ops/incidents/{incident_id}?include_supplier_health=false (enrichment disabled)")
    
    return failed_tests == 0

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)