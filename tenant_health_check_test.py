#!/usr/bin/env python3
"""
Tenant-Aware Endpoints Health Check Test

This test suite verifies the tenant-aware endpoints after tenant header fix
as requested in the review:

1) GET /api/partner-graph/inbox
2) GET /api/partner-graph/notifications/summary  
3) GET /api/reports/sales-summary?days=7
4) GET /api/reports/reservations-summary
5) GET /api/admin/agencies/
6) GET /api/public/theme (no auth, no tenant header)

For each endpoint, verify:
- HTTP status is 200
- Response is well-formed JSON, matching expected schema
- Use super admin user (admin@acenta.test / admin123) 
- Use X-Tenant-Id=tenant_partner_test_a_14beaf25
"""

import requests
import json
from typing import Dict, Any

# Configuration - Use production URL from frontend/.env
BASE_URL = "https://booking-platform-48.preview.emergentagent.com"
TENANT_ID = "tenant_partner_test_a_14beaf25"

def login_super_admin():
    """Login as super admin and return token"""
    print("🔐 Logging in as super admin...")
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "admin@acenta.test", "password": "admin123"},
    )
    
    print(f"   📋 Login response: {r.status_code}")
    if r.status_code != 200:
        print(f"   ❌ Login failed: {r.text}")
        return None
        
    data = r.json()
    token = data["access_token"]
    print(f"   ✅ Login successful, token obtained")
    return token

def test_endpoint(endpoint: str, expected_keys: list, use_auth: bool = True, use_tenant: bool = True, query_params: str = ""):
    """Test a single endpoint and verify response structure"""
    
    # Get auth token if needed
    token = None
    if use_auth:
        token = login_super_admin()
        if not token:
            return False, "Failed to get auth token"
    
    # Build headers
    headers = {}
    if use_auth:
        headers["Authorization"] = f"Bearer {token}"
    if use_tenant:
        headers["X-Tenant-Id"] = TENANT_ID
    
    # Build URL
    url = f"{BASE_URL}{endpoint}"
    if query_params:
        url += f"?{query_params}"
    
    print(f"\n🔍 Testing: {endpoint}")
    print(f"   📋 URL: {url}")
    print(f"   📋 Headers: {list(headers.keys())}")
    
    try:
        # Make request
        r = requests.get(url, headers=headers, timeout=30)
        
        print(f"   📋 Response status: {r.status_code}")
        
        # Check status code
        if r.status_code != 200:
            print(f"   ❌ Expected 200, got {r.status_code}")
            print(f"   📋 Response body: {r.text}")
            return False, f"HTTP {r.status_code}: {r.text}"
        
        # Check if response is JSON
        try:
            data = r.json()
        except json.JSONDecodeError as e:
            print(f"   ❌ Response is not valid JSON: {e}")
            print(f"   📋 Response body: {r.text}")
            return False, f"Invalid JSON: {e}"
        
        print(f"   📋 Response keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
        
        # Check expected keys
        if expected_keys:
            missing_keys = []
            if isinstance(data, dict):
                for key in expected_keys:
                    if key not in data:
                        missing_keys.append(key)
            else:
                missing_keys = expected_keys  # If not dict, all keys are missing
            
            if missing_keys:
                print(f"   ❌ Missing expected keys: {missing_keys}")
                print(f"   📋 Full response: {json.dumps(data, indent=2)}")
                return False, f"Missing keys: {missing_keys}"
        
        print(f"   ✅ Endpoint working correctly")
        print(f"   📋 Sample response: {json.dumps(data, indent=2)[:500]}...")
        
        return True, "Success"
        
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Request failed: {e}")
        return False, f"Request error: {e}"

def run_health_check():
    """Run health check on all tenant-aware endpoints"""
    
    print("\n" + "🏥" * 80)
    print("TENANT-AWARE ENDPOINTS HEALTH CHECK")
    print("Testing endpoints after tenant header fix")
    print("🏥" * 80)
    
    # Define endpoints to test
    endpoints = [
        {
            "endpoint": "/api/partner-graph/inbox",
            "expected_keys": ["tenant_id", "invites_received", "invites_sent", "active_partners"],
            "use_auth": True,
            "use_tenant": True,
            "query_params": ""
        },
        {
            "endpoint": "/api/partner-graph/notifications/summary", 
            "expected_keys": ["tenant_id", "counts"],
            "use_auth": True,
            "use_tenant": True,
            "query_params": ""
        },
        {
            "endpoint": "/api/reports/sales-summary",
            "expected_keys": [],  # Expect array response
            "use_auth": True,
            "use_tenant": True,
            "query_params": "days=7"
        },
        {
            "endpoint": "/api/reports/reservations-summary",
            "expected_keys": [],  # Expect array response
            "use_auth": True,
            "use_tenant": True,
            "query_params": ""
        },
        {
            "endpoint": "/api/admin/agencies/",
            "expected_keys": [],  # Expect array response
            "use_auth": True,
            "use_tenant": True,
            "query_params": ""
        },
        {
            "endpoint": "/api/public/theme",
            "expected_keys": ["brand", "colors"],
            "use_auth": False,
            "use_tenant": False,
            "query_params": ""
        }
    ]
    
    results = []
    
    for endpoint_config in endpoints:
        success, message = test_endpoint(
            endpoint_config["endpoint"],
            endpoint_config["expected_keys"],
            endpoint_config["use_auth"],
            endpoint_config["use_tenant"],
            endpoint_config["query_params"]
        )
        
        results.append({
            "endpoint": endpoint_config["endpoint"],
            "success": success,
            "message": message
        })
    
    # Print summary
    print("\n" + "📊" * 80)
    print("HEALTH CHECK SUMMARY")
    print("📊" * 80)
    
    passed = 0
    failed = 0
    
    for result in results:
        if result["success"]:
            print(f"✅ {result['endpoint']} - OK")
            passed += 1
        else:
            print(f"❌ {result['endpoint']} - FAILED: {result['message']}")
            failed += 1
    
    print(f"\n📈 Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("\n🎉 ALL ENDPOINTS HEALTHY! Tenant-aware endpoints working correctly.")
    else:
        print(f"\n⚠️  {failed} endpoint(s) failed. See details above.")
    
    # Print failing endpoints for easy reference
    if failed > 0:
        print("\n🔍 FAILING ENDPOINTS:")
        for result in results:
            if not result["success"]:
                print(f"   ❌ {result['endpoint']}: {result['message']}")
    
    return failed == 0

if __name__ == "__main__":
    success = run_health_check()
    exit(0 if success else 1)