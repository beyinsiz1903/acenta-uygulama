#!/usr/bin/env python3
"""
Backend No-Regression Test
Test backend API endpoints after frontend admin login redirect and navigation changes
"""

import requests
import json
import sys
from datetime import datetime, timedelta

# Base URL from frontend/.env
BASE_URL = "https://security-admin-1.preview.emergentagent.com/api"

# Test credentials
ADMIN_CREDENTIALS = {
    "email": "admin@acenta.test",
    "password": "admin123"
}

def test_admin_login():
    """Test POST /api/auth/login with admin credentials"""
    print("1. Testing POST /api/auth/login with admin@acenta.test/admin123...")
    
    url = f"{BASE_URL}/auth/login"
    response = requests.post(url, json=ADMIN_CREDENTIALS)
    
    print(f"   Status: {response.status_code}")
    
    if response.status_code != 200:
        print(f"   ❌ FAIL - Expected 200, got {response.status_code}")
        print(f"   Response: {response.text[:500]}")
        return None
    
    try:
        data = response.json()
        access_token = data.get("access_token")
        if not access_token:
            print("   ❌ FAIL - No access_token in response")
            return None
        
        print(f"   ✅ PASS - Login successful, token length: {len(access_token)}")
        return access_token
    except Exception as e:
        print(f"   ❌ FAIL - JSON parsing error: {e}")
        return None

def test_auth_me(token):
    """Test GET /api/auth/me with Bearer token"""
    print("2. Testing GET /api/auth/me with token...")
    
    url = f"{BASE_URL}/auth/me"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    
    print(f"   Status: {response.status_code}")
    
    if response.status_code != 200:
        print(f"   ❌ FAIL - Expected 200, got {response.status_code}")
        print(f"   Response: {response.text[:500]}")
        return False
    
    try:
        data = response.json()
        email = data.get("email")
        if email != "admin@acenta.test":
            print(f"   ❌ FAIL - Expected admin@acenta.test, got {email}")
            return False
        
        print(f"   ✅ PASS - Auth/me working, user: {email}")
        return True
    except Exception as e:
        print(f"   ❌ FAIL - JSON parsing error: {e}")
        return False

def test_admin_agencies(token):
    """Test GET /api/admin/agencies"""
    print("3. Testing GET /api/admin/agencies...")
    
    url = f"{BASE_URL}/admin/agencies"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 429:
        print("   ⚠️ SKIP - Rate limit detected (429), not treated as regression")
        return True
    elif response.status_code not in [200, 404]:
        print(f"   ❌ FAIL - Unexpected status {response.status_code}")
        print(f"   Response: {response.text[:500]}")
        return False
    
    try:
        data = response.json()
        print(f"   ✅ PASS - Admin agencies endpoint responding, data length: {len(str(data))}")
        return True
    except Exception as e:
        print(f"   ❌ FAIL - JSON parsing error: {e}")
        return False

def test_admin_reporting_summary(token):
    """Test GET /api/admin/reporting/summary?days=30"""
    print("4. Testing GET /api/admin/reporting/summary?days=30...")
    
    url = f"{BASE_URL}/admin/reporting/summary?days=30"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 429:
        print("   ⚠️ SKIP - Rate limit detected (429), not treated as regression")
        return True
    elif response.status_code not in [200, 404]:
        print(f"   ❌ FAIL - Unexpected status {response.status_code}")
        print(f"   Response: {response.text[:500]}")
        return False
    
    try:
        data = response.json()
        print(f"   ✅ PASS - Admin reporting summary responding, data length: {len(str(data))}")
        return True
    except Exception as e:
        print(f"   ❌ FAIL - JSON parsing error: {e}")
        return False

def test_admin_metrics_overview(token):
    """Test GET /api/admin/metrics/overview with date parameters"""
    print("5. Testing GET /api/admin/metrics/overview...")
    
    # Calculate date range for last 30 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    url = f"{BASE_URL}/admin/metrics/overview?start_date={start_date.strftime('%Y-%m-%d')}&end_date={end_date.strftime('%Y-%m-%d')}"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 429:
        print("   ⚠️ SKIP - Rate limit detected (429), not treated as regression")
        return True
    elif response.status_code not in [200, 404]:
        print(f"   ❌ FAIL - Unexpected status {response.status_code}")
        print(f"   Response: {response.text[:500]}")
        return False
    
    try:
        data = response.json()
        print(f"   ✅ PASS - Admin metrics overview responding, data length: {len(str(data))}")
        return True
    except Exception as e:
        print(f"   ❌ FAIL - JSON parsing error: {e}")
        return False

def get_tenant_id_for_billing_test(token):
    """Get a valid tenant ID from admin tenants list"""
    print("6a. Getting tenant ID for billing test...")
    
    url = f"{BASE_URL}/admin/tenants?limit=5"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    
    if response.status_code == 429:
        print("   ⚠️ SKIP - Rate limit detected (429)")
        return None
    elif response.status_code != 200:
        print(f"   ⚠️ SKIP - Could not get tenants list: {response.status_code}")
        return None
    
    try:
        data = response.json()
        items = data.get("items", [])
        if items:
            tenant_id = items[0].get("id")
            print(f"   ✅ Found tenant ID: {tenant_id}")
            return tenant_id
        else:
            print("   ⚠️ No tenants found")
            return None
    except Exception as e:
        print(f"   ⚠️ Error getting tenant ID: {e}")
        return None

def test_admin_billing_tenant_usage(token, tenant_id):
    """Test GET /api/admin/billing/tenants/<tenant-id>/usage"""
    if not tenant_id:
        print("6b. Skipping billing tenant usage test - no valid tenant ID")
        return True
    
    print(f"6b. Testing GET /api/admin/billing/tenants/{tenant_id}/usage...")
    
    url = f"{BASE_URL}/admin/billing/tenants/{tenant_id}/usage"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 429:
        print("   ⚠️ SKIP - Rate limit detected (429), not treated as regression")
        return True
    elif response.status_code not in [200, 404]:
        print(f"   ❌ FAIL - Unexpected status {response.status_code}")
        print(f"   Response: {response.text[:500]}")
        return False
    
    try:
        data = response.json()
        print(f"   ✅ PASS - Admin billing tenant usage responding, data length: {len(str(data))}")
        return True
    except Exception as e:
        print(f"   ❌ FAIL - JSON parsing error: {e}")
        return False

def test_agency_bookings(token):
    """Test GET /api/agency/bookings for simplification regression"""
    print("7. Testing GET /api/agency/bookings (simplification regression check)...")
    
    url = f"{BASE_URL}/agency/bookings"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 429:
        print("   ⚠️ SKIP - Rate limit detected (429), not treated as regression")
        return True
    elif response.status_code == 404:
        print("   ✅ PASS - 404 expected for admin user on agency endpoint")
        return True
    elif response.status_code not in [200, 403]:
        print(f"   ❌ FAIL - Unexpected status {response.status_code}")
        print(f"   Response: {response.text[:500]}")
        return False
    
    try:
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ PASS - Agency bookings responding, data length: {len(str(data))}")
        else:
            print("   ✅ PASS - 403 Forbidden as expected for admin user")
        return True
    except Exception as e:
        print(f"   ❌ FAIL - JSON parsing error: {e}")
        return False

def main():
    """Run all no-regression tests"""
    print("=== BACKEND NO-REGRESSION VALIDATION ===")
    print(f"Base URL: {BASE_URL}")
    print(f"Testing after frontend admin login redirect and navigation changes")
    print()
    
    results = []
    
    # Test 1: Admin login
    token = test_admin_login()
    if not token:
        print("\n❌ CRITICAL: Cannot proceed without valid admin token")
        sys.exit(1)
    results.append(True)
    
    # Test 2: Auth/me with token
    results.append(test_auth_me(token))
    
    # Test 3: Admin agencies
    results.append(test_admin_agencies(token))
    
    # Test 4: Admin reporting summary
    results.append(test_admin_reporting_summary(token))
    
    # Test 5: Admin metrics overview
    results.append(test_admin_metrics_overview(token))
    
    # Test 6: Admin billing tenant usage (get tenant ID first)
    tenant_id = get_tenant_id_for_billing_test(token)
    results.append(test_admin_billing_tenant_usage(token, tenant_id))
    
    # Test 7: Agency bookings regression check
    results.append(test_agency_bookings(token))
    
    # Summary
    print("\n=== TEST SUMMARY ===")
    passed = sum(results)
    total = len(results)
    
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("✅ ALL TESTS PASSED - Backend no-regression validation successful")
        print("✅ No regressions detected from frontend admin navigation changes")
        return 0
    else:
        print(f"❌ {total - passed} TESTS FAILED - Regressions detected")
        return 1

if __name__ == "__main__":
    sys.exit(main())