#!/usr/bin/env python
"""
Mobile BFF API Contract Tests for PR-5A (Preview URL)

Optimized version: Reuses auth token to avoid rate limiting.
"""

import os
import sys
import json
import time
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://api-versioning-hub.preview.emergentagent.com").rstrip("/")

# Test credentials
ADMIN_CREDS = {"email": "admin@acenta.test", "password": "admin123"}

test_results = {"passed": [], "failed": []}

# Global token cache
_cached_token = None
_cached_tenant_id = None


def log_pass(test_name, details=""):
    msg = f"PASS: {test_name}"
    if details:
        msg += f" - {details}"
    print(f"✅ {msg}")
    test_results["passed"].append(test_name)


def log_fail(test_name, error):
    msg = f"FAIL: {test_name} - {error}"
    print(f"❌ {msg}")
    test_results["failed"].append({"test": test_name, "error": str(error)})


def get_admin_auth():
    """Login as admin and return (token, tenant_id). Caches result."""
    global _cached_token, _cached_tenant_id
    
    if _cached_token:
        return _cached_token, _cached_tenant_id
    
    response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
    if response.status_code != 200:
        raise Exception(f"Admin login failed: {response.status_code} - {response.text}")
    
    data = response.json()
    _cached_token = data.get("access_token")
    if not _cached_token:
        raise Exception(f"No access_token in response: {data}")
    
    # Get tenant_id from /auth/me
    time.sleep(0.5)  # Small delay between requests
    me_response = requests.get(f"{BASE_URL}/api/auth/me", headers={"Authorization": f"Bearer {_cached_token}"})
    if me_response.status_code == 200:
        _cached_tenant_id = me_response.json().get("tenant_id")
    
    return _cached_token, _cached_tenant_id


def get_headers():
    """Get headers with cached token."""
    token, tenant_id = get_admin_auth()
    headers = {"Authorization": f"Bearer {token}"}
    if tenant_id:
        headers["X-Tenant-Id"] = tenant_id
    return headers


def test_auth_requirement():
    """Test that all mobile endpoints require authentication."""
    print("\n=== Testing Authentication Requirements ===")
    
    endpoints = [
        ("/api/v1/mobile/auth/me", "GET"),
        ("/api/v1/mobile/dashboard/summary", "GET"),
        ("/api/v1/mobile/bookings", "GET"),
        ("/api/v1/mobile/reports/summary", "GET"),
    ]
    
    for path, method in endpoints:
        try:
            response = requests.get(f"{BASE_URL}{path}")
            if response.status_code == 401:
                log_pass(f"{method} {path} requires auth", "Returns 401 without token")
            else:
                log_fail(f"{method} {path} requires auth", f"Expected 401, got {response.status_code}")
            time.sleep(0.2)
        except Exception as e:
            log_fail(f"{method} {path} requires auth", str(e))


def test_mobile_auth_me():
    """Test GET /api/v1/mobile/auth/me returns sanitized mobile DTO."""
    print("\n=== Testing Mobile Auth Me ===")
    
    try:
        headers = get_headers()
        response = requests.get(f"{BASE_URL}/api/v1/mobile/auth/me", headers=headers)
        
        if response.status_code != 200:
            log_fail("mobile_auth_me", f"Expected 200, got {response.status_code}: {response.text}")
            return
        
        data = response.json()
        print(f"   Response: {json.dumps(data, indent=2)[:500]}")
        
        # Check required fields
        required_fields = ["id", "email", "roles", "organization_id", "tenant_id", "allowed_tenant_ids"]
        missing = [f for f in required_fields if f not in data]
        if missing:
            log_fail("mobile_auth_me_fields", f"Missing fields: {missing}")
        else:
            log_pass("mobile_auth_me_fields", "All required fields present")
        
        # Check no _id leak
        if "_id" in data:
            log_fail("mobile_auth_me_no_id_leak", f"MongoDB _id leaked: {data.get('_id')}")
        else:
            log_pass("mobile_auth_me_no_id_leak", "No raw MongoDB _id in response")
        
        # Check no sensitive fields
        sensitive = ["password_hash", "totp_secret"]
        leaked = [f for f in sensitive if f in data]
        if leaked:
            log_fail("mobile_auth_me_sensitive", f"Sensitive fields leaked: {leaked}")
        else:
            log_pass("mobile_auth_me_sensitive", "No sensitive fields leaked")
        
    except Exception as e:
        log_fail("mobile_auth_me", str(e))


def test_mobile_dashboard_summary():
    """Test GET /api/v1/mobile/dashboard/summary returns stable shape."""
    print("\n=== Testing Mobile Dashboard Summary ===")
    
    try:
        headers = get_headers()
        response = requests.get(f"{BASE_URL}/api/v1/mobile/dashboard/summary", headers=headers)
        
        if response.status_code != 200:
            log_fail("mobile_dashboard_summary", f"Expected 200, got {response.status_code}: {response.text}")
            return
        
        data = response.json()
        print(f"   Response: {json.dumps(data, indent=2)}")
        
        # Check required fields
        required_fields = ["bookings_today", "bookings_month", "revenue_month", "currency"]
        missing = [f for f in required_fields if f not in data]
        if missing:
            log_fail("mobile_dashboard_fields", f"Missing fields: {missing}")
        else:
            log_pass("mobile_dashboard_fields", "All required fields present")
        
        # Check types
        if isinstance(data.get("bookings_today"), int) and isinstance(data.get("bookings_month"), int):
            log_pass("mobile_dashboard_types", "Booking counts are integers")
        else:
            log_fail("mobile_dashboard_types", f"Invalid types")
        
        # Check no _id leak
        if "_id" not in data:
            log_pass("mobile_dashboard_no_id_leak", "No raw MongoDB _id in response")
        else:
            log_fail("mobile_dashboard_no_id_leak", f"MongoDB _id leaked")
        
    except Exception as e:
        log_fail("mobile_dashboard_summary", str(e))


def test_mobile_bookings_list():
    """Test GET /api/v1/mobile/bookings returns list without _id leak."""
    print("\n=== Testing Mobile Bookings List ===")
    
    try:
        headers = get_headers()
        response = requests.get(f"{BASE_URL}/api/v1/mobile/bookings", headers=headers)
        
        if response.status_code != 200:
            log_fail("mobile_bookings_list", f"Expected 200, got {response.status_code}: {response.text}")
            return
        
        data = response.json()
        print(f"   Response: total={data.get('total')}, items_count={len(data.get('items', []))}")
        
        # Check required fields
        if "total" in data and "items" in data:
            log_pass("mobile_bookings_list_fields", "Has total and items fields")
        else:
            log_fail("mobile_bookings_list_fields", f"Missing total or items")
        
        # Check no _id leak in items
        items = data.get("items", [])
        has_id_leak = any("_id" in item for item in items)
        if not has_id_leak:
            log_pass("mobile_bookings_list_no_id_leak", "No raw MongoDB _id in items")
        else:
            log_fail("mobile_bookings_list_no_id_leak", "Found _id in booking items")
        
        # Check item shape
        if items:
            item = items[0]
            required_item_fields = ["id", "status", "total_price", "currency"]
            missing = [f for f in required_item_fields if f not in item]
            if not missing:
                log_pass("mobile_bookings_item_shape", f"Item has required fields")
            else:
                log_fail("mobile_bookings_item_shape", f"Missing item fields: {missing}")
        
    except Exception as e:
        log_fail("mobile_bookings_list", str(e))


def test_mobile_booking_create_and_detail():
    """Test POST /api/v1/mobile/bookings and GET detail."""
    print("\n=== Testing Mobile Booking Create & Detail ===")
    
    try:
        headers = get_headers()
        
        payload = {
            "amount": 1250.00,
            "currency": "TRY",
            "customer_name": "Mobile BFF Test Customer",
            "hotel_name": "Mobile BFF Test Hotel",
            "booking_ref": f"MB-TEST-{os.urandom(4).hex().upper()}",
            "check_in": "2026-03-20",
            "check_out": "2026-03-23",
            "notes": "Created via mobile BFF test",
            "source": "mobile"
        }
        
        response = requests.post(f"{BASE_URL}/api/v1/mobile/bookings", headers=headers, json=payload)
        
        if response.status_code != 201:
            log_fail("mobile_booking_create", f"Expected 201, got {response.status_code}: {response.text}")
            return
        
        data = response.json()
        print(f"   Created booking: id={data.get('id')}, status={data.get('status')}")
        
        # Check required fields
        required_fields = ["id", "status", "total_price", "customer_name", "hotel_name"]
        missing = [f for f in required_fields if f not in data]
        if not missing:
            log_pass("mobile_booking_create_fields", "All required fields in response")
        else:
            log_fail("mobile_booking_create_fields", f"Missing fields: {missing}")
        
        # Check status is draft
        if data.get("status") == "draft":
            log_pass("mobile_booking_create_status", "Status is 'draft' as expected")
        else:
            log_fail("mobile_booking_create_status", f"Expected status 'draft', got '{data.get('status')}'")
        
        # Check no _id leak
        if "_id" not in data:
            log_pass("mobile_booking_create_no_id_leak", "No raw MongoDB _id in response")
        else:
            log_fail("mobile_booking_create_no_id_leak", f"MongoDB _id leaked")
        
        # Test GET detail
        time.sleep(0.3)
        booking_id = data.get("id")
        detail_response = requests.get(f"{BASE_URL}/api/v1/mobile/bookings/{booking_id}", headers=headers)
        
        if detail_response.status_code == 200:
            detail_data = detail_response.json()
            if detail_data.get("id") == booking_id:
                log_pass("mobile_booking_detail", f"GET detail for {booking_id} works")
            else:
                log_fail("mobile_booking_detail", f"ID mismatch in detail")
            
            # Check detail-specific fields
            if "tenant_id" in detail_data and "booking_ref" in detail_data:
                log_pass("mobile_booking_detail_fields", "Detail has tenant_id and booking_ref")
            else:
                log_fail("mobile_booking_detail_fields", "Missing detail fields")
            
            # Check no _id leak
            if "_id" not in detail_data:
                log_pass("mobile_booking_detail_no_id_leak", "No raw MongoDB _id")
            else:
                log_fail("mobile_booking_detail_no_id_leak", "MongoDB _id leaked in detail")
        else:
            log_fail("mobile_booking_detail", f"Expected 200, got {detail_response.status_code}")
        
    except Exception as e:
        log_fail("mobile_booking_create_and_detail", str(e))


def test_mobile_reports_summary():
    """Test GET /api/v1/mobile/reports/summary returns reporting shape."""
    print("\n=== Testing Mobile Reports Summary ===")
    
    try:
        headers = get_headers()
        response = requests.get(f"{BASE_URL}/api/v1/mobile/reports/summary", headers=headers)
        
        if response.status_code != 200:
            log_fail("mobile_reports_summary", f"Expected 200, got {response.status_code}: {response.text}")
            return
        
        data = response.json()
        print(f"   Response: total_bookings={data.get('total_bookings')}, total_revenue={data.get('total_revenue')}")
        
        # Check required fields
        required_fields = ["total_bookings", "total_revenue", "currency", "status_breakdown", "daily_sales"]
        missing = [f for f in required_fields if f not in data]
        if not missing:
            log_pass("mobile_reports_summary_fields", "All required fields present")
        else:
            log_fail("mobile_reports_summary_fields", f"Missing fields: {missing}")
        
        # Check types
        if isinstance(data.get("status_breakdown"), list) and isinstance(data.get("daily_sales"), list):
            log_pass("mobile_reports_summary_types", "status_breakdown and daily_sales are lists")
        else:
            log_fail("mobile_reports_summary_types", f"Invalid types")
        
        # Check no _id leak
        if "_id" not in data:
            log_pass("mobile_reports_summary_no_id_leak", "No raw MongoDB _id in response")
        else:
            log_fail("mobile_reports_summary_no_id_leak", "MongoDB _id leaked")
        
    except Exception as e:
        log_fail("mobile_reports_summary", str(e))


def test_legacy_auth_non_regression():
    """Test that legacy auth endpoints still work."""
    print("\n=== Testing Legacy Auth Non-Regression ===")
    
    try:
        # Use cached token - just verify it exists and was obtained via /api/auth/login
        token, tenant_id = get_admin_auth()
        if token:
            log_pass("legacy_auth_login", "POST /api/auth/login works (token obtained)")
        else:
            log_fail("legacy_auth_login", "No token from login")
        
        # Test /auth/me (non-mobile version)
        response = requests.get(f"{BASE_URL}/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        if response.status_code == 200:
            data = response.json()
            if "email" in data:
                log_pass("legacy_auth_me", "GET /api/auth/me works and returns email")
            else:
                log_fail("legacy_auth_me", f"Missing email in response")
        else:
            log_fail("legacy_auth_me", f"GET /api/auth/me failed: {response.status_code}")
        
    except Exception as e:
        log_fail("legacy_auth_non_regression", str(e))


def run_all_tests():
    """Run all mobile BFF tests."""
    print(f"\n{'='*60}")
    print(f"Mobile BFF API Contract Tests - PR-5A")
    print(f"Target: {BASE_URL}")
    print(f"{'='*60}")
    
    test_auth_requirement()
    time.sleep(0.5)
    
    test_mobile_auth_me()
    time.sleep(0.3)
    
    test_mobile_dashboard_summary()
    time.sleep(0.3)
    
    test_mobile_bookings_list()
    time.sleep(0.3)
    
    test_mobile_booking_create_and_detail()
    time.sleep(0.3)
    
    test_mobile_reports_summary()
    time.sleep(0.3)
    
    test_legacy_auth_non_regression()
    
    # Summary
    print(f"\n{'='*60}")
    print(f"TEST SUMMARY")
    print(f"{'='*60}")
    print(f"Passed: {len(test_results['passed'])}")
    print(f"Failed: {len(test_results['failed'])}")
    
    if test_results["failed"]:
        print(f"\nFailed tests:")
        for failure in test_results["failed"]:
            print(f"  - {failure['test']}: {failure['error'][:100]}")
    
    return len(test_results["failed"]) == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
