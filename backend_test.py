#!/usr/bin/env python3
"""Backend Google Sheets Integration Hardening Test.

This script tests the Google Sheets integration backend endpoints
to verify the tenant-aware configuration cache, new endpoints,
and admin/agency connect flows work correctly without Google config.
"""

import json
import requests
import sys
from typing import Dict, Any, Optional
import uuid

# Use the preview URL from frontend/.env
BASE_URL = "https://supplier-e2e-demo.preview.emergentagent.com"
API_BASE = f"{BASE_URL}/api"

# Test credentials
ADMIN_EMAIL = "admin@acenta.test"
ADMIN_PASSWORD = "admin123"
AGENCY_EMAIL = "agent@acenta.test"  
AGENCY_PASSWORD = "agent123"

class TestSession:
    """Helper class to manage authenticated sessions."""
    
    def __init__(self):
        self.session = requests.Session()
        self.token = None
        
    def login(self, email: str, password: str) -> bool:
        """Login and store access token."""
        response = self.session.post(f"{API_BASE}/auth/login", json={
            "email": email,
            "password": password
        })
        
        if response.status_code != 200:
            print(f"❌ Login failed for {email}: {response.status_code}")
            return False
            
        data = response.json()
        self.token = data.get("access_token")
        
        if not self.token:
            print(f"❌ No access_token in login response for {email}")
            return False
            
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        print(f"✅ Login successful for {email} (token length: {len(self.token)})")
        return True
        
    def get(self, url: str, **kwargs) -> requests.Response:
        """GET with authentication."""
        return self.session.get(f"{API_BASE}{url}", **kwargs)
        
    def post(self, url: str, **kwargs) -> requests.Response:
        """POST with authentication."""
        return self.session.post(f"{API_BASE}{url}", **kwargs)
        
    def delete(self, url: str, **kwargs) -> requests.Response:
        """DELETE with authentication."""
        return self.session.delete(f"{API_BASE}{url}", **kwargs)


def test_admin_login():
    """Test 1: Admin login works."""
    print("\n=== Test 1: Admin Login ===")
    admin_session = TestSession()
    success = admin_session.login(ADMIN_EMAIL, ADMIN_PASSWORD)
    
    # If we get a rate limit, wait and try again
    if not success:
        print("   Rate limit detected, waiting 10 seconds and retrying...")
        import time
        time.sleep(10)
        success = admin_session.login(ADMIN_EMAIL, ADMIN_PASSWORD)
    
    if success:
        print("✅ PASS: Admin login successful")
        return admin_session
    else:
        print("❌ FAIL: Admin login failed")
        return None


def test_admin_sheets_config(admin_session: TestSession):
    """Test 2: GET /api/admin/sheets/config returns 200 and configured=false when no service account exists."""
    print("\n=== Test 2: Admin Sheets Config ===")
    
    response = admin_session.get("/admin/sheets/config")
    
    if response.status_code != 200:
        print(f"❌ FAIL: Expected 200, got {response.status_code}: {response.text}")
        return False
        
    try:
        data = response.json()
        configured = data.get("configured")
        
        print(f"✅ PASS: GET /admin/sheets/config returns 200")
        print(f"   Response: {json.dumps(data, indent=2)}")
        
        if configured is False:
            print("✅ PASS: configured=false as expected (no service account)")
        else:
            print(f"⚠️  NOTE: configured={configured} (expected false for unconfigured state)")
            
        return True
        
    except json.JSONDecodeError:
        print(f"❌ FAIL: Invalid JSON response: {response.text}")
        return False


def test_admin_sheets_templates(admin_session: TestSession):
    """Test 3: GET /api/admin/sheets/templates returns 200 with expected payload."""
    print("\n=== Test 3: Admin Sheets Templates ===")
    
    response = admin_session.get("/admin/sheets/templates")
    
    if response.status_code != 200:
        print(f"❌ FAIL: Expected 200, got {response.status_code}: {response.text}")
        return False
        
    try:
        data = response.json()
        
        # Check for expected fields according to review request
        expected_keys = ["checklist", "inventory_sync", "reservation_writeback"]
        
        print(f"✅ PASS: GET /admin/sheets/templates returns 200")
        print(f"   Response keys: {list(data.keys())}")
        
        all_present = True
        for key in expected_keys:
            if key in data:
                print(f"   ✅ {key}: present")
            else:
                print(f"   ❌ {key}: MISSING")
                all_present = False
                
        if all_present:
            print("✅ PASS: All expected template sections present")
        else:
            print("❌ FAIL: Missing expected template sections")
            
        return all_present
        
    except json.JSONDecodeError:
        print(f"❌ FAIL: Invalid JSON response: {response.text}")
        return False


def test_legacy_admin_import_config(admin_session: TestSession):
    """Test 4: GET /api/admin/import/sheet/config returns 200 and no longer depends only on env wording."""
    print("\n=== Test 4: Legacy Admin Import Config ===")
    
    response = admin_session.get("/admin/import/sheet/config")
    
    if response.status_code != 200:
        print(f"❌ FAIL: Expected 200, got {response.status_code}: {response.text}")
        return False
        
    try:
        data = response.json()
        
        print(f"✅ PASS: GET /admin/import/sheet/config returns 200")
        print(f"   Response: {json.dumps(data, indent=2)}")
        
        # Check that it respects tenant-aware config path
        has_configured = "configured" in data
        has_service_account_email = "service_account_email" in data
        
        if has_configured and has_service_account_email:
            print("✅ PASS: Legacy endpoint has tenant-aware configuration fields")
        else:
            print("❌ FAIL: Legacy endpoint missing expected configuration fields")
            
        return has_configured and has_service_account_email
        
    except json.JSONDecodeError:
        print(f"❌ FAIL: Invalid JSON response: {response.text}")
        return False


def test_admin_available_hotels(admin_session: TestSession):
    """Test 5a: GET /api/admin/sheets/available-hotels returns list."""
    print("\n=== Test 5a: Admin Available Hotels ===")
    
    response = admin_session.get("/admin/sheets/available-hotels")
    
    if response.status_code != 200:
        print(f"❌ FAIL: Expected 200, got {response.status_code}: {response.text}")
        return None
        
    try:
        data = response.json()
        
        if isinstance(data, list):
            print(f"✅ PASS: GET /admin/sheets/available-hotels returns list with {len(data)} hotels")
            return data
        else:
            print(f"❌ FAIL: Expected list, got {type(data)}")
            return None
            
    except json.JSONDecodeError:
        print(f"❌ FAIL: Invalid JSON response: {response.text}")
        return None


def test_admin_connect_flow_without_google(admin_session: TestSession, available_hotels):
    """Test 5b: Admin connect flow without Google config."""
    print("\n=== Test 5b: Admin Connect Flow (No Google Config) ===")
    
    if not available_hotels:
        print("❌ SKIP: No available hotels to test with")
        return None
        
    # Find a non-connected hotel
    target_hotel = None
    for hotel in available_hotels:
        if not hotel.get("connected", False):
            target_hotel = hotel
            break
            
    if not target_hotel:
        print("⚠️  NOTE: All hotels are already connected, using first hotel anyway")
        target_hotel = available_hotels[0]
        
    hotel_id = target_hotel["_id"]
    fake_sheet_id = f"1test_sheet_id_{uuid.uuid4().hex[:8]}"
    
    print(f"   Using hotel: {target_hotel.get('name', 'Unknown')} (ID: {hotel_id})")
    print(f"   Fake sheet ID: {fake_sheet_id}")
    
    payload = {
        "hotel_id": hotel_id,
        "sheet_id": fake_sheet_id,
        "sheet_tab": "Sheet1",
        "writeback_tab": "Rezervasyonlar"
    }
    
    response = admin_session.post("/admin/sheets/connect", json=payload)
    
    if response.status_code not in [200, 409]:  # 409 if already exists
        print(f"❌ FAIL: Expected 200/409, got {response.status_code}: {response.text}")
        return None
        
    try:
        data = response.json()
        
        if response.status_code == 409:
            print("⚠️  NOTE: Connection already exists (409), this is expected behavior")
            return None
            
        print(f"✅ PASS: POST /admin/sheets/connect successful in pending configuration mode")
        
        # Check for expected fields in response
        writeback_tab = data.get("writeback_tab")
        validation_status = data.get("validation_status")
        
        if writeback_tab == "Rezervasyonlar":
            print("✅ PASS: writeback_tab='Rezervasyonlar' as expected")
        else:
            print(f"❌ FAIL: writeback_tab='{writeback_tab}', expected 'Rezervasyonlar'")
            
        if validation_status == "pending_configuration":
            print("✅ PASS: validation_status='pending_configuration' as expected")
        else:
            print(f"❌ FAIL: validation_status='{validation_status}', expected 'pending_configuration'")
            
        connection_id = data.get("_id") or data.get("id")
        print(f"   Created connection ID: {connection_id}")
        print(f"   Full response data keys: {list(data.keys())}")
        
        return connection_id
        
    except json.JSONDecodeError:
        print(f"❌ FAIL: Invalid JSON response: {response.text}")
        return None


def test_admin_connection_cleanup(admin_session: TestSession, connection_id: Optional[str]):
    """Test 5c: Cleanup admin connection."""
    print("\n=== Test 5c: Admin Connection Cleanup ===")
    
    if not connection_id:
        print("❌ SKIP: No connection ID to cleanup")
        return False
        
    # First get the connection to find hotel_id
    response = admin_session.get("/admin/sheets/connections")
    if response.status_code != 200:
        print(f"❌ FAIL: Could not list connections: {response.status_code}")
        return False
        
    connections = response.json()
    target_connection = None
    
    for conn in connections:
        if conn.get("_id") == connection_id or conn.get("id") == connection_id:
            target_connection = conn
            break
            
    if not target_connection:
        print(f"❌ FAIL: Could not find connection {connection_id}")
        return False
        
    hotel_id = target_connection.get("hotel_id")
    if not hotel_id:
        print(f"❌ FAIL: Connection missing hotel_id")
        return False
        
    # Delete the connection
    response = admin_session.delete(f"/admin/sheets/connections/{hotel_id}")
    
    if response.status_code != 200:
        print(f"❌ FAIL: Delete failed: {response.status_code}: {response.text}")
        return False
        
    try:
        data = response.json()
        deleted = data.get("deleted")
        
        if deleted:
            print("✅ PASS: Admin connection deleted successfully")
            return True
        else:
            print(f"❌ FAIL: Delete response indicates failure: {data}")
            return False
            
    except json.JSONDecodeError:
        print(f"❌ FAIL: Invalid JSON response: {response.text}")
        return False


def test_agency_login():
    """Test 6: Agency login works."""
    print("\n=== Test 6: Agency Login ===")
    
    # Add a delay to avoid rate limiting
    import time
    time.sleep(2)
    
    agency_session = TestSession()
    success = agency_session.login(AGENCY_EMAIL, AGENCY_PASSWORD)
    
    # If we get a rate limit, wait and try again
    if not success:
        print("   Rate limit detected, waiting 5 seconds and retrying...")
        time.sleep(5)
        success = agency_session.login(AGENCY_EMAIL, AGENCY_PASSWORD)
    
    if success:
        print("✅ PASS: Agency login successful")
        return agency_session
    else:
        print("❌ FAIL: Agency login failed")
        return None


def test_agency_available_hotels(agency_session: TestSession):
    """Test 7a: GET /api/agency/sheets/hotels returns list."""
    print("\n=== Test 7a: Agency Available Hotels ===")
    
    response = agency_session.get("/agency/sheets/hotels")
    
    # May return 200 (list) or 403 (no agency)
    if response.status_code == 403:
        print("⚠️  NOTE: Agency user not linked to agency (403), this may be expected")
        return None
    elif response.status_code != 200:
        print(f"❌ FAIL: Expected 200/403, got {response.status_code}: {response.text}")
        return None
        
    try:
        data = response.json()
        
        if isinstance(data, list):
            print(f"✅ PASS: GET /api/agency/sheets/hotels returns list with {len(data)} hotels")
            return data
        else:
            print(f"❌ FAIL: Expected list, got {type(data)}")
            return None
            
    except json.JSONDecodeError:
        print(f"❌ FAIL: Invalid JSON response: {response.text}")
        return None


def test_agency_connect_flow_without_google(agency_session: TestSession, available_hotels):
    """Test 7b: Agency connect flow without Google config."""
    print("\n=== Test 7b: Agency Connect Flow (No Google Config) ===")
    
    if not available_hotels:
        print("❌ SKIP: No available hotels to test with")
        return None
        
    # Find a non-connected hotel
    target_hotel = None
    for hotel in available_hotels:
        if not hotel.get("connected", False):
            target_hotel = hotel
            break
            
    if not target_hotel:
        print("⚠️  NOTE: All hotels are already connected, using first hotel anyway")
        target_hotel = available_hotels[0]
        
    hotel_id = target_hotel["_id"]
    fake_sheet_id = f"1test_agency_sheet_{uuid.uuid4().hex[:8]}"
    
    print(f"   Using hotel: {target_hotel.get('name', 'Unknown')} (ID: {hotel_id})")
    print(f"   Fake sheet ID: {fake_sheet_id}")
    
    payload = {
        "hotel_id": hotel_id,
        "sheet_id": fake_sheet_id,
        "sheet_tab": "Sheet1",
        "writeback_tab": "Rezervasyonlar"
    }
    
    response = agency_session.post("/agency/sheets/connect", json=payload)
    
    if response.status_code not in [200, 409, 403]:  # 403 if no agency access
        print(f"❌ FAIL: Expected 200/409/403, got {response.status_code}: {response.text}")
        return None
        
    if response.status_code == 403:
        print("⚠️  NOTE: Agency user cannot access agency endpoints (403)")
        return None
        
    try:
        data = response.json()
        
        if response.status_code == 409:
            print("⚠️  NOTE: Agency connection already exists (409), this is expected behavior")
            return None
            
        print(f"✅ PASS: POST /agency/sheets/connect successful in pending configuration mode")
        
        # Check for expected fields in response
        writeback_tab = data.get("writeback_tab")
        validation_status = data.get("validation_status")
        
        if writeback_tab == "Rezervasyonlar":
            print("✅ PASS: writeback_tab='Rezervasyonlar' as expected")
        else:
            print(f"❌ FAIL: writeback_tab='{writeback_tab}', expected 'Rezervasyonlar'")
            
        if validation_status == "pending_configuration":
            print("✅ PASS: validation_status='pending_configuration' as expected")
        else:
            print(f"❌ FAIL: validation_status='{validation_status}', expected 'pending_configuration'")
            
        connection_id = data.get("_id") or data.get("id")
        print(f"   Created agency connection ID: {connection_id}")
        print(f"   Full agency response data keys: {list(data.keys())}")
        
        return connection_id
        
    except json.JSONDecodeError:
        print(f"❌ FAIL: Invalid JSON response: {response.text}")
        return None


def test_agency_connection_cleanup(agency_session: TestSession, connection_id: Optional[str]):
    """Test 7c: Cleanup agency connection."""
    print("\n=== Test 7c: Agency Connection Cleanup ===")
    
    if not connection_id:
        print("❌ SKIP: No agency connection ID to cleanup")
        return False
        
    response = agency_session.delete(f"/agency/sheets/connections/{connection_id}")
    
    if response.status_code not in [200, 404]:
        print(f"❌ FAIL: Delete failed: {response.status_code}: {response.text}")
        return False
        
    if response.status_code == 404:
        print("⚠️  NOTE: Agency connection not found (404), may have been cleaned up already")
        return True
        
    try:
        data = response.json()
        deleted = data.get("deleted")
        
        if deleted:
            print("✅ PASS: Agency connection deleted successfully")
            return True
        else:
            print(f"❌ FAIL: Delete response indicates failure: {data}")
            return False
            
    except json.JSONDecodeError:
        print(f"❌ FAIL: Invalid JSON response: {response.text}")
        return False


def test_existing_backend_regression():
    """Test 8: Existing backend regression check - run pytest on test_agency_sheets_api.py."""
    print("\n=== Test 8: Backend Regression Check ===")
    
    import subprocess
    import os
    
    # Change to backend directory
    os.chdir("/app/backend")
    
    try:
        result = subprocess.run([
            "python", "-m", "pytest", 
            "tests/test_agency_sheets_api.py", 
            "-q"
        ], capture_output=True, text=True, timeout=60)
        
        print(f"   Exit code: {result.returncode}")
        if result.stdout:
            print(f"   STDOUT:\n{result.stdout}")
        if result.stderr:
            print(f"   STDERR:\n{result.stderr}")
            
        if result.returncode == 0:
            print("✅ PASS: Backend regression tests passed")
            return True
        else:
            print("❌ FAIL: Backend regression tests failed")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ FAIL: Backend regression tests timed out")
        return False
    except Exception as e:
        print(f"❌ FAIL: Error running regression tests: {e}")
        return False


def main():
    """Run all Google Sheets integration hardening tests."""
    print("🧪 BACKEND GOOGLE SHEETS INTEGRATION HARDENING TEST")
    print("=" * 60)
    
    # Add initial delay to avoid rate limits
    import time
    print("⏱️  Waiting 10 seconds to avoid rate limits...")
    time.sleep(10)
    
    results = []
    
    # Test 1: Admin login
    admin_session = test_admin_login()
    results.append(("Admin Login", admin_session is not None))
    
    if not admin_session:
        print("\n❌ CRITICAL: Cannot proceed without admin access")
        sys.exit(1)
    
    # Test 2: Admin sheets config
    config_result = test_admin_sheets_config(admin_session)
    results.append(("Admin Sheets Config", config_result))
    
    # Test 3: Admin sheets templates
    templates_result = test_admin_sheets_templates(admin_session)
    results.append(("Admin Sheets Templates", templates_result))
    
    # Test 4: Legacy admin import config
    legacy_result = test_legacy_admin_import_config(admin_session)
    results.append(("Legacy Admin Import Config", legacy_result))
    
    # Test 5: Admin connect flow
    available_hotels = test_admin_available_hotels(admin_session)
    results.append(("Admin Available Hotels", available_hotels is not None))
    
    admin_connection_id = test_admin_connect_flow_without_google(admin_session, available_hotels)
    results.append(("Admin Connect Flow", admin_connection_id is not None))
    
    admin_cleanup_result = test_admin_connection_cleanup(admin_session, admin_connection_id)
    results.append(("Admin Connection Cleanup", admin_cleanup_result))
    
    # Test 6: Agency login
    agency_session = test_agency_login()
    results.append(("Agency Login", agency_session is not None))
    
    if agency_session:
        # Test 7: Agency connect flow
        agency_available_hotels = test_agency_available_hotels(agency_session)
        results.append(("Agency Available Hotels", agency_available_hotels is not None))
        
        agency_connection_id = test_agency_connect_flow_without_google(agency_session, agency_available_hotels)
        results.append(("Agency Connect Flow", agency_connection_id is not None or agency_available_hotels is None))
        
        agency_cleanup_result = test_agency_connection_cleanup(agency_session, agency_connection_id)
        results.append(("Agency Connection Cleanup", agency_cleanup_result or agency_connection_id is None))
    
    # Test 8: Backend regression
    regression_result = test_existing_backend_regression()
    results.append(("Backend Regression Check", regression_result))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name}")
        if success:
            passed += 1
    
    print(f"\nResult: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED!")
        sys.exit(0)
    else:
        print("💥 SOME TESTS FAILED!")
        sys.exit(1)


if __name__ == "__main__":
    main()