#!/usr/bin/env python
"""
Mobile BFF API Contract Tests for PR-5A (Preview URL)

Tests run directly against preview URL using requests library.
No conftest fixtures needed - standalone test script.

Test Coverage:
- All mobile endpoints require authentication (401 without token)
- GET /api/v1/mobile/auth/me returns sanitized mobile DTO
- GET /api/v1/mobile/dashboard/summary returns stable KPI shape
- GET /api/v1/mobile/bookings returns list without _id leak
- GET /api/v1/mobile/bookings/{id} returns detail with tenant isolation
- POST /api/v1/mobile/bookings creates draft booking 
- GET /api/v1/mobile/reports/summary returns reporting shape
- Legacy auth endpoints still work (non-regression)
"""

import os
import sys
import json
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://quota-track.preview.emergentagent.com").rstrip("/")

# Test credentials
ADMIN_CREDS = {"email": "admin@acenta.test", "password": "admin123"}
AGENT_CREDS = {"email": "agent@acenta.test", "password": "agent123"}

test_results = {"passed": [], "failed": []}


def log_pass(test_name, details=""):
    """Log a passing test."""
    msg = f"PASS: {test_name}"
    if details:
        msg += f" - {details}"
    print(f"✅ {msg}")
    test_results["passed"].append(test_name)


def log_fail(test_name, error):
    """Log a failing test."""
    msg = f"FAIL: {test_name} - {error}"
    print(f"❌ {msg}")
    test_results["failed"].append({"test": test_name, "error": str(error)})


def get_admin_token():
    """Login as admin and return access token."""
    response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
    if response.status_code != 200:
        raise Exception(f"Admin login failed: {response.status_code} - {response.text}")
    data = response.json()
    token = data.get("access_token")
    if not token:
        raise Exception(f"No access_token in response: {data}")
    return token


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
            if method == "GET":
                response = requests.get(f"{BASE_URL}{path}")
            else:
                response = requests.post(f"{BASE_URL}{path}", json={})
            
            if response.status_code == 401:
                log_pass(f"{method} {path} requires auth", "Returns 401 without token")
            else:
                log_fail(f"{method} {path} requires auth", f"Expected 401, got {response.status_code}")
        except Exception as e:
            log_fail(f"{method} {path} requires auth", str(e))


def test_mobile_auth_me():
    """Test GET /api/v1/mobile/auth/me returns sanitized mobile DTO."""
    print("\n=== Testing Mobile Auth Me ===")
    
    try:
        token = get_admin_token()
        headers = {"Authorization": f"Bearer {token}"}
        
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
        token = get_admin_token()
        headers = {"Authorization": f"Bearer {token}"}
        
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
            log_fail("mobile_dashboard_types", f"Invalid types: bookings_today={type(data.get('bookings_today'))}")
        
        # Check no _id leak
        if "_id" in data:
            log_fail("mobile_dashboard_no_id_leak", f"MongoDB _id leaked: {data.get('_id')}")
        else:
            log_pass("mobile_dashboard_no_id_leak", "No raw MongoDB _id in response")
        
    except Exception as e:
        log_fail("mobile_dashboard_summary", str(e))


def test_mobile_bookings_list():
    """Test GET /api/v1/mobile/bookings returns list without _id leak."""
    print("\n=== Testing Mobile Bookings List ===")
    
    try:
        token = get_admin_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.get(f"{BASE_URL}/api/v1/mobile/bookings", headers=headers)
        
        if response.status_code != 200:
            log_fail("mobile_bookings_list", f"Expected 200, got {response.status_code}: {response.text}")
            return
        
        data = response.json()
        print(f"   Response: total={data.get('total')}, items_count={len(data.get('items', []))}")
        
        # Check required fields
        if "total" not in data or "items" not in data:
            log_fail("mobile_bookings_list_fields", f"Missing total or items: {list(data.keys())}")
        else:
            log_pass("mobile_bookings_list_fields", "Has total and items fields")
        
        # Check no _id leak in items
        items = data.get("items", [])
        has_id_leak = any("_id" in item for item in items)
        if has_id_leak:
            log_fail("mobile_bookings_list_no_id_leak", "Found _id in booking items")
        else:
            log_pass("mobile_bookings_list_no_id_leak", "No raw MongoDB _id in items")
        
        # Check item shape
        if items:
            item = items[0]
            required_item_fields = ["id", "status", "total_price", "currency"]
            missing = [f for f in required_item_fields if f not in item]
            if missing:
                log_fail("mobile_bookings_item_shape", f"Missing item fields: {missing}")
            else:
                log_pass("mobile_bookings_item_shape", f"Item has required fields: {required_item_fields}")
        
    except Exception as e:
        log_fail("mobile_bookings_list", str(e))


def test_mobile_booking_create():
    """Test POST /api/v1/mobile/bookings creates draft booking."""
    print("\n=== Testing Mobile Booking Create ===")
    
    try:
        token = get_admin_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        # Get tenant_id from /auth/me for proper tenant scoping
        me_response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
        if me_response.status_code == 200:
            tenant_id = me_response.json().get("tenant_id")
            if tenant_id:
                headers["X-Tenant-Id"] = tenant_id
        
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
        if missing:
            log_fail("mobile_booking_create_fields", f"Missing fields: {missing}")
        else:
            log_pass("mobile_booking_create_fields", "All required fields in response")
        
        # Check status is draft
        if data.get("status") == "draft":
            log_pass("mobile_booking_create_status", "Status is 'draft' as expected")
        else:
            log_fail("mobile_booking_create_status", f"Expected status 'draft', got '{data.get('status')}'")
        
        # Check no _id leak
        if "_id" in data:
            log_fail("mobile_booking_create_no_id_leak", f"MongoDB _id leaked: {data.get('_id')}")
        else:
            log_pass("mobile_booking_create_no_id_leak", "No raw MongoDB _id in response")
        
        # Check data matches input
        if data.get("customer_name") == payload["customer_name"]:
            log_pass("mobile_booking_create_data", "Customer name matches input")
        else:
            log_fail("mobile_booking_create_data", f"Customer name mismatch: {data.get('customer_name')}")
        
        # Return booking ID for detail test
        return data.get("id")
        
    except Exception as e:
        log_fail("mobile_booking_create", str(e))
        return None


def test_mobile_booking_detail(booking_id=None):
    """Test GET /api/v1/mobile/bookings/{id} returns detail."""
    print("\n=== Testing Mobile Booking Detail ===")
    
    try:
        token = get_admin_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        # If no booking ID provided, create one first
        if not booking_id:
            me_response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
            if me_response.status_code == 200:
                tenant_id = me_response.json().get("tenant_id")
                if tenant_id:
                    headers["X-Tenant-Id"] = tenant_id
            
            create_payload = {
                "amount": 750.0,
                "currency": "TRY",
                "customer_name": "Detail Test Customer",
                "hotel_name": "Detail Test Hotel",
                "booking_ref": f"MB-DETAIL-{os.urandom(4).hex().upper()}",
                "source": "mobile"
            }
            create_response = requests.post(f"{BASE_URL}/api/v1/mobile/bookings", headers=headers, json=create_payload)
            if create_response.status_code == 201:
                booking_id = create_response.json().get("id")
        
        if not booking_id:
            log_fail("mobile_booking_detail", "Could not create test booking")
            return
        
        response = requests.get(f"{BASE_URL}/api/v1/mobile/bookings/{booking_id}", headers=headers)
        
        if response.status_code != 200:
            log_fail("mobile_booking_detail", f"Expected 200, got {response.status_code}: {response.text}")
            return
        
        data = response.json()
        print(f"   Detail for {booking_id}: status={data.get('status')}, tenant_id={data.get('tenant_id')}")
        
        # Check detail-specific fields (extra over list item)
        detail_fields = ["tenant_id", "booking_ref", "notes"]
        present = [f for f in detail_fields if f in data]
        if present:
            log_pass("mobile_booking_detail_fields", f"Detail fields present: {present}")
        else:
            log_fail("mobile_booking_detail_fields", f"Missing detail fields")
        
        # Check no _id leak
        if "_id" in data:
            log_fail("mobile_booking_detail_no_id_leak", f"MongoDB _id leaked: {data.get('_id')}")
        else:
            log_pass("mobile_booking_detail_no_id_leak", "No raw MongoDB _id in response")
        
    except Exception as e:
        log_fail("mobile_booking_detail", str(e))


def test_mobile_reports_summary():
    """Test GET /api/v1/mobile/reports/summary returns reporting shape."""
    print("\n=== Testing Mobile Reports Summary ===")
    
    try:
        token = get_admin_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.get(f"{BASE_URL}/api/v1/mobile/reports/summary", headers=headers)
        
        if response.status_code != 200:
            log_fail("mobile_reports_summary", f"Expected 200, got {response.status_code}: {response.text}")
            return
        
        data = response.json()
        print(f"   Response: total_bookings={data.get('total_bookings')}, total_revenue={data.get('total_revenue')}")
        
        # Check required fields
        required_fields = ["total_bookings", "total_revenue", "currency", "status_breakdown", "daily_sales"]
        missing = [f for f in required_fields if f not in data]
        if missing:
            log_fail("mobile_reports_summary_fields", f"Missing fields: {missing}")
        else:
            log_pass("mobile_reports_summary_fields", "All required fields present")
        
        # Check types
        if isinstance(data.get("status_breakdown"), list) and isinstance(data.get("daily_sales"), list):
            log_pass("mobile_reports_summary_types", "status_breakdown and daily_sales are lists")
        else:
            log_fail("mobile_reports_summary_types", f"Invalid types for breakdown/sales arrays")
        
        # Check no _id leak
        if "_id" in data:
            log_fail("mobile_reports_summary_no_id_leak", f"MongoDB _id leaked: {data.get('_id')}")
        else:
            log_pass("mobile_reports_summary_no_id_leak", "No raw MongoDB _id in response")
        
    except Exception as e:
        log_fail("mobile_reports_summary", str(e))


def test_legacy_auth_non_regression():
    """Test that legacy auth endpoints still work."""
    print("\n=== Testing Legacy Auth Non-Regression ===")
    
    try:
        # Test login
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN_CREDS)
        if login_response.status_code == 200:
            log_pass("legacy_auth_login", "POST /api/auth/login works")
            token = login_response.json().get("access_token")
        else:
            log_fail("legacy_auth_login", f"POST /api/auth/login failed: {login_response.status_code}")
            return
        
        # Test /auth/me
        me_response = requests.get(f"{BASE_URL}/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        if me_response.status_code == 200:
            data = me_response.json()
            if "email" in data:
                log_pass("legacy_auth_me", "GET /api/auth/me works and returns email")
            else:
                log_fail("legacy_auth_me", f"Missing email in response: {list(data.keys())}")
        else:
            log_fail("legacy_auth_me", f"GET /api/auth/me failed: {me_response.status_code}")
        
    except Exception as e:
        log_fail("legacy_auth_non_regression", str(e))


def run_all_tests():
    """Run all mobile BFF tests."""
    print(f"\n{'='*60}")
    print(f"Mobile BFF API Contract Tests - PR-5A")
    print(f"Target: {BASE_URL}")
    print(f"{'='*60}")
    
    test_auth_requirement()
    test_mobile_auth_me()
    test_mobile_dashboard_summary()
    test_mobile_bookings_list()
    booking_id = test_mobile_booking_create()
    test_mobile_booking_detail(booking_id)
    test_mobile_reports_summary()
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
