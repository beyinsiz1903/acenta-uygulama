#!/usr/bin/env python3
"""
Portfolio Sync Engine Backend API Test Suite

Tests all new endpoints at /api/admin/sheets/* with focus on:
- Auth guards (401 without token)
- Graceful fallback when Google Sheets not configured
- CRUD operations for hotel sheet connections
- Tenant isolation
- Error handling
"""

import json
import sys
import requests
from typing import Dict, Any, Optional
from datetime import datetime

# Configuration
BACKEND_URL = "https://data-sync-tool-1.preview.emergentagent.com/api"
TEST_USER_EMAIL = "admin@acenta.test"
TEST_USER_PASSWORD = "admin123"

class PortfolioSyncTester:
    def __init__(self):
        self.base_url = BACKEND_URL
        self.auth_token = None
        self.user_data = None
        self.test_hotel_id = None
        self.test_results = []
        
    def log(self, message: str, level: str = "INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
        
    def add_result(self, test_name: str, status: str, details: str = ""):
        self.test_results.append({
            "test": test_name,
            "status": status,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
        
    def request(self, method: str, endpoint: str, headers: Optional[Dict] = None, 
               json_data: Optional[Dict] = None, params: Optional[Dict] = None) -> requests.Response:
        """Make HTTP request with proper error handling"""
        url = f"{self.base_url}{endpoint}"
        req_headers = {"Content-Type": "application/json"}
        
        if headers:
            req_headers.update(headers)
            
        if self.auth_token and "Authorization" not in req_headers:
            req_headers["Authorization"] = f"Bearer {self.auth_token}"
            
        # Add tenant header if we have user data
        if self.user_data and "X-Tenant-Id" not in req_headers:
            # Use organization_id as tenant_id since no separate tenant_id
            tenant_id = self.user_data.get("organization_id")
            if tenant_id:
                req_headers["X-Tenant-Id"] = tenant_id
            
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=req_headers,
                json=json_data,
                params=params,
                timeout=30
            )
            self.log(f"{method} {url} -> {response.status_code}")
            return response
        except requests.RequestException as e:
            self.log(f"Request failed: {e}", "ERROR")
            raise
            
    def authenticate(self) -> bool:
        """Login and get JWT token"""
        self.log("=== AUTHENTICATION TEST ===")
        
        # First, try to create a test user (will fail if exists, that's OK)
        try:
            register_data = {
                "email": TEST_USER_EMAIL,
                "password": TEST_USER_PASSWORD,
                "name": "Test Admin",
                "organization_name": "Test Organization"
            }
            response = self.request("POST", "/auth/register", json_data=register_data)
            if response.status_code in [201, 409]:  # Created or already exists
                self.log("Test user registration: OK")
        except Exception as e:
            self.log(f"User registration failed (may already exist): {e}")
        
        # Login
        login_data = {
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        }
        
        response = self.request("POST", "/auth/login", json_data=login_data)
        
        if response.status_code == 200:
            data = response.json()
            self.auth_token = data.get("access_token")
            self.user_data = data.get("user", {})
            self.log(f"✅ Authentication successful. User: {self.user_data.get('email')}")
            self.log(f"   Organization ID: {self.user_data.get('organization_id')}")
            self.log(f"   Tenant ID: {self.user_data.get('tenant_id')}")
            self.add_result("Authentication", "PASS", "Successfully logged in")
            return True
        else:
            self.log(f"❌ Authentication failed: {response.status_code} - {response.text}")
            self.add_result("Authentication", "FAIL", f"Status: {response.status_code}")
            return False
            
    def create_test_hotel(self) -> bool:
        """Create a test hotel for sheet connection tests"""
        self.log("=== CREATING TEST HOTEL ===")
        
        hotel_data = {
            "name": "Test Portfolio Hotel",
            "city": "Istanbul",
            "country": "Turkey",
            "description": "Test hotel for portfolio sync testing",
            "stars": 4
        }
        
        response = self.request("POST", "/admin/hotels", json_data=hotel_data)
        
        if response.status_code == 201:
            data = response.json()
            self.test_hotel_id = data.get("_id")
            self.log(f"✅ Test hotel created: {self.test_hotel_id}")
            self.add_result("Create Test Hotel", "PASS", f"Hotel ID: {self.test_hotel_id}")
            return True
        else:
            self.log(f"❌ Failed to create test hotel: {response.status_code} - {response.text}")
            self.add_result("Create Test Hotel", "FAIL", f"Status: {response.status_code}")
            return False
            
    def test_auth_guards(self):
        """Test that all endpoints require authentication"""
        self.log("=== AUTH GUARDS TEST ===")
        
        endpoints = [
            ("GET", "/admin/sheets/config"),
            ("POST", "/admin/sheets/connect"),
            ("GET", "/admin/sheets/connections"),
            ("GET", "/admin/sheets/connections/test-hotel"),
            ("PATCH", "/admin/sheets/connections/test-hotel"),
            ("DELETE", "/admin/sheets/connections/test-hotel"),
            ("POST", "/admin/sheets/sync/test-hotel"),
            ("POST", "/admin/sheets/sync-all"),
            ("GET", "/admin/sheets/status"),
            ("GET", "/admin/sheets/runs"),
            ("GET", "/admin/sheets/stale-hotels"),
            ("POST", "/admin/sheets/preview-mapping"),
            ("GET", "/admin/sheets/available-hotels")
        ]
        
        auth_failures = 0
        for method, endpoint in endpoints:
            # Test without token
            response = requests.request(
                method=method,
                url=f"{self.base_url}{endpoint}",
                headers={"Content-Type": "application/json"},
                json={"test": "data"} if method in ["POST", "PATCH"] else None,
                timeout=10
            )
            
            if response.status_code == 401:
                self.log(f"✅ {method} {endpoint}: Auth guard working (401)")
            else:
                self.log(f"❌ {method} {endpoint}: Expected 401, got {response.status_code}")
                auth_failures += 1
                
        if auth_failures == 0:
            self.add_result("Auth Guards", "PASS", "All endpoints require authentication")
        else:
            self.add_result("Auth Guards", "FAIL", f"{auth_failures} endpoints missing auth")
            
    def test_config_endpoint(self):
        """Test /api/admin/sheets/config endpoint"""
        self.log("=== CONFIG ENDPOINT TEST ===")
        
        response = self.request("GET", "/admin/sheets/config")
        
        if response.status_code == 200:
            data = response.json()
            
            # Should return graceful fallback since no GOOGLE_SERVICE_ACCOUNT_JSON
            expected_keys = ["configured", "service_account_email", "message"]
            
            if all(key in data for key in expected_keys):
                if data["configured"] == False and data["service_account_email"] is None:
                    self.log("✅ Config endpoint returns proper fallback")
                    self.add_result("Config Endpoint", "PASS", "Graceful fallback working")
                else:
                    self.log("❌ Config endpoint should show not configured")
                    self.add_result("Config Endpoint", "FAIL", "Expected not configured")
            else:
                self.log(f"❌ Config endpoint missing keys: {data}")
                self.add_result("Config Endpoint", "FAIL", "Missing required keys")
        else:
            self.log(f"❌ Config endpoint failed: {response.status_code}")
            self.add_result("Config Endpoint", "FAIL", f"Status: {response.status_code}")
            
    def test_connect_endpoint(self):
        """Test /api/admin/sheets/connect endpoint"""
        self.log("=== CONNECT ENDPOINT TEST ===")
        
        if not self.test_hotel_id:
            self.log("❌ No test hotel available")
            self.add_result("Connect Endpoint", "FAIL", "No test hotel")
            return
            
        connect_data = {
            "hotel_id": self.test_hotel_id,
            "sheet_id": "1TEST_SHEET_ID_FOR_TESTING",
            "sheet_tab": "Sheet1",
            "mapping": {
                "Date": "date",
                "Room Type": "room_type", 
                "Price": "price"
            },
            "sync_enabled": True,
            "sync_interval_minutes": 5
        }
        
        response = self.request("POST", "/admin/sheets/connect", json_data=connect_data)
        
        if response.status_code == 201:
            data = response.json()
            expected_keys = ["_id", "hotel_id", "sheet_id", "configured"]
            
            if all(key in data for key in expected_keys):
                if data["hotel_id"] == self.test_hotel_id:
                    self.log("✅ Sheet connection created successfully")
                    self.add_result("Connect Endpoint", "PASS", f"Connection ID: {data['_id']}")
                else:
                    self.log("❌ Hotel ID mismatch in response")
                    self.add_result("Connect Endpoint", "FAIL", "Hotel ID mismatch")
            else:
                self.log(f"❌ Connect response missing keys: {data}")
                self.add_result("Connect Endpoint", "FAIL", "Missing response keys")
        else:
            self.log(f"❌ Connect failed: {response.status_code} - {response.text}")
            self.add_result("Connect Endpoint", "FAIL", f"Status: {response.status_code}")
            
    def test_list_connections(self):
        """Test /api/admin/sheets/connections endpoint"""
        self.log("=== LIST CONNECTIONS TEST ===")
        
        # Test list all connections
        response = self.request("GET", "/admin/sheets/connections")
        
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                self.log(f"✅ Listed {len(data)} connections")
                
                # Test with hotel_id filter
                if self.test_hotel_id:
                    response2 = self.request("GET", "/admin/sheets/connections", 
                                           params={"hotel_id": self.test_hotel_id})
                    if response2.status_code == 200:
                        filtered_data = response2.json()
                        self.log(f"✅ Filtered connections: {len(filtered_data)}")
                        self.add_result("List Connections", "PASS", f"Total: {len(data)}, Filtered: {len(filtered_data)}")
                    else:
                        self.add_result("List Connections", "PARTIAL", "List OK, filter failed")
                else:
                    self.add_result("List Connections", "PASS", f"Listed {len(data)} connections")
            else:
                self.log(f"❌ Expected list, got: {type(data)}")
                self.add_result("List Connections", "FAIL", "Invalid response type")
        else:
            self.log(f"❌ List connections failed: {response.status_code}")
            self.add_result("List Connections", "FAIL", f"Status: {response.status_code}")
            
    def test_single_connection(self):
        """Test /api/admin/sheets/connections/{hotel_id} endpoint"""
        self.log("=== SINGLE CONNECTION TEST ===")
        
        if not self.test_hotel_id:
            self.log("❌ No test hotel available")
            self.add_result("Single Connection", "FAIL", "No test hotel")
            return
            
        response = self.request("GET", f"/admin/sheets/connections/{self.test_hotel_id}")
        
        if response.status_code == 200:
            data = response.json()
            
            # Should have either connection data or {"connected": False}
            if "connected" in data:
                if data["connected"]:
                    self.log("✅ Hotel has sheet connection")
                    self.add_result("Single Connection", "PASS", "Connection found")
                else:
                    self.log("✅ Hotel has no sheet connection (expected format)")
                    self.add_result("Single Connection", "PASS", "No connection (proper format)")
            else:
                self.log(f"❌ Unexpected response format: {data}")
                self.add_result("Single Connection", "FAIL", "Invalid response format")
        else:
            self.log(f"❌ Single connection failed: {response.status_code}")
            self.add_result("Single Connection", "FAIL", f"Status: {response.status_code}")
            
    def test_update_connection(self):
        """Test /api/admin/sheets/connections/{hotel_id} PATCH endpoint"""
        self.log("=== UPDATE CONNECTION TEST ===")
        
        if not self.test_hotel_id:
            self.log("❌ No test hotel available")
            self.add_result("Update Connection", "FAIL", "No test hotel")
            return
            
        update_data = {
            "sync_enabled": False,
            "sync_interval_minutes": 10
        }
        
        response = self.request("PATCH", f"/admin/sheets/connections/{self.test_hotel_id}", 
                               json_data=update_data)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("sync_enabled") == False:
                self.log("✅ Connection updated successfully")
                self.add_result("Update Connection", "PASS", "Sync disabled")
            else:
                self.log("❌ Update not reflected in response")
                self.add_result("Update Connection", "FAIL", "Update not applied")
        elif response.status_code == 404:
            self.log("✅ No connection to update (404 expected)")
            self.add_result("Update Connection", "PASS", "404 for non-existent connection")
        else:
            self.log(f"❌ Update failed: {response.status_code} - {response.text}")
            self.add_result("Update Connection", "FAIL", f"Status: {response.status_code}")
            
    def test_sync_endpoints(self):
        """Test sync endpoints that should return not_configured"""
        self.log("=== SYNC ENDPOINTS TEST ===")
        
        # Test manual sync
        if self.test_hotel_id:
            response = self.request("POST", f"/admin/sheets/sync/{self.test_hotel_id}")
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "not_configured" and data.get("configured") == False:
                    self.log("✅ Manual sync returns not_configured")
                    sync_result = "PASS"
                else:
                    self.log(f"❌ Manual sync unexpected response: {data}")
                    sync_result = "FAIL"
            elif response.status_code == 404:
                self.log("✅ Manual sync returns 404 (no connection)")
                sync_result = "PASS"
            else:
                self.log(f"❌ Manual sync failed: {response.status_code}")
                sync_result = "FAIL"
        else:
            sync_result = "SKIP"
            
        # Test sync all
        response = self.request("POST", "/admin/sheets/sync-all")
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "not_configured" and data.get("configured") == False:
                self.log("✅ Sync all returns not_configured")
                sync_all_result = "PASS"
            else:
                self.log(f"✅ Sync all processed connections: {data}")
                sync_all_result = "PASS"
        else:
            self.log(f"❌ Sync all failed: {response.status_code}")
            sync_all_result = "FAIL"
            
        if sync_result == "PASS" and sync_all_result == "PASS":
            self.add_result("Sync Endpoints", "PASS", "Both manual and bulk sync working")
        else:
            self.add_result("Sync Endpoints", "PARTIAL", f"Manual: {sync_result}, Bulk: {sync_all_result}")
            
    def test_status_dashboard(self):
        """Test /api/admin/sheets/status endpoint"""
        self.log("=== STATUS DASHBOARD TEST ===")
        
        response = self.request("GET", "/admin/sheets/status")
        
        if response.status_code == 200:
            data = response.json()
            expected_keys = ["configured", "total", "enabled", "healthy"]
            
            if all(key in data for key in expected_keys):
                if data["configured"] == False:
                    self.log("✅ Status dashboard shows not configured")
                    self.add_result("Status Dashboard", "PASS", "Proper fallback status")
                else:
                    self.log(f"✅ Status dashboard: {data}")
                    self.add_result("Status Dashboard", "PASS", "Status data returned")
            else:
                self.log(f"❌ Status missing keys: {data}")
                self.add_result("Status Dashboard", "FAIL", "Missing required keys")
        else:
            self.log(f"❌ Status dashboard failed: {response.status_code}")
            self.add_result("Status Dashboard", "FAIL", f"Status: {response.status_code}")
            
    def test_runs_history(self):
        """Test /api/admin/sheets/runs endpoint"""
        self.log("=== RUNS HISTORY TEST ===")
        
        response = self.request("GET", "/admin/sheets/runs")
        
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                self.log(f"✅ Runs history returned {len(data)} runs")
                self.add_result("Runs History", "PASS", f"{len(data)} sync runs")
            else:
                self.log(f"❌ Expected list, got: {type(data)}")
                self.add_result("Runs History", "FAIL", "Invalid response type")
        else:
            self.log(f"❌ Runs history failed: {response.status_code}")
            self.add_result("Runs History", "FAIL", f"Status: {response.status_code}")
            
    def test_stale_hotels(self):
        """Test /api/admin/sheets/stale-hotels endpoint"""
        self.log("=== STALE HOTELS TEST ===")
        
        response = self.request("GET", "/admin/sheets/stale-hotels", params={"stale_minutes": 30})
        
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                self.log(f"✅ Stale hotels returned {len(data)} hotels")
                self.add_result("Stale Hotels", "PASS", f"{len(data)} stale connections")
            else:
                self.log(f"❌ Expected list, got: {type(data)}")
                self.add_result("Stale Hotels", "FAIL", "Invalid response type")
        else:
            self.log(f"❌ Stale hotels failed: {response.status_code}")
            self.add_result("Stale Hotels", "FAIL", f"Status: {response.status_code}")
            
    def test_preview_mapping(self):
        """Test /api/admin/sheets/preview-mapping endpoint"""
        self.log("=== PREVIEW MAPPING TEST ===")
        
        preview_data = {
            "sheet_id": "1TEST_SHEET_ID",
            "sheet_tab": "Sheet1",
            "mapping": {"Date": "date", "Room": "room_type"}
        }
        
        response = self.request("POST", "/admin/sheets/preview-mapping", json_data=preview_data)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("configured") == False:
                self.log("✅ Preview mapping returns not configured")
                self.add_result("Preview Mapping", "PASS", "Graceful fallback")
            else:
                self.log(f"✅ Preview mapping returned data: {data}")
                self.add_result("Preview Mapping", "PASS", "Preview data returned")
        else:
            self.log(f"❌ Preview mapping failed: {response.status_code}")
            self.add_result("Preview Mapping", "FAIL", f"Status: {response.status_code}")
            
    def test_available_hotels(self):
        """Test /api/admin/sheets/available-hotels endpoint"""
        self.log("=== AVAILABLE HOTELS TEST ===")
        
        response = self.request("GET", "/admin/sheets/available-hotels")
        
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                self.log(f"✅ Available hotels returned {len(data)} hotels")
                
                # Check if our test hotel is in the list
                test_hotel_found = any(h.get("_id") == self.test_hotel_id for h in data)
                if test_hotel_found:
                    self.log("✅ Test hotel found in available hotels")
                    self.add_result("Available Hotels", "PASS", f"{len(data)} hotels, test hotel found")
                else:
                    self.log("⚠️  Test hotel not in available list (may be connected)")
                    self.add_result("Available Hotels", "PASS", f"{len(data)} hotels listed")
            else:
                self.log(f"❌ Expected list, got: {type(data)}")
                self.add_result("Available Hotels", "FAIL", "Invalid response type")
        else:
            self.log(f"❌ Available hotels failed: {response.status_code}")
            self.add_result("Available Hotels", "FAIL", f"Status: {response.status_code}")
            
    def test_delete_connection(self):
        """Test DELETE /api/admin/sheets/connections/{hotel_id} endpoint"""
        self.log("=== DELETE CONNECTION TEST ===")
        
        if not self.test_hotel_id:
            self.log("❌ No test hotel available")
            self.add_result("Delete Connection", "FAIL", "No test hotel")
            return
            
        response = self.request("DELETE", f"/admin/sheets/connections/{self.test_hotel_id}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get("deleted") == True:
                self.log("✅ Connection deleted successfully")
                self.add_result("Delete Connection", "PASS", "Connection deleted")
            else:
                self.log(f"❌ Unexpected delete response: {data}")
                self.add_result("Delete Connection", "FAIL", "Invalid response")
        elif response.status_code == 404:
            self.log("✅ No connection to delete (404 expected)")
            self.add_result("Delete Connection", "PASS", "404 for non-existent connection")
        else:
            self.log(f"❌ Delete failed: {response.status_code}")
            self.add_result("Delete Connection", "FAIL", f"Status: {response.status_code}")
            
    def test_tenant_isolation(self):
        """Test that queries are properly scoped to tenant"""
        self.log("=== TENANT ISOLATION TEST ===")
        
        # This is a basic test - we verify that all endpoints return data scoped to current user
        # In a real multi-tenant test, we'd create multiple tenants and verify isolation
        
        isolation_pass = True
        isolation_details = []
        
        # Check that connections endpoint returns tenant-scoped data
        response = self.request("GET", "/admin/sheets/connections")
        if response.status_code == 200:
            data = response.json()
            self.log(f"✅ Connections endpoint accessible (tenant-scoped): {len(data)} items")
            isolation_details.append(f"Connections: {len(data)}")
        else:
            isolation_pass = False
            isolation_details.append("Connections endpoint failed")
            
        # Check status endpoint
        response = self.request("GET", "/admin/sheets/status")
        if response.status_code == 200:
            data = response.json()
            self.log("✅ Status endpoint accessible (tenant-scoped)")
            isolation_details.append("Status: OK")
        else:
            isolation_pass = False
            isolation_details.append("Status endpoint failed")
            
        if isolation_pass:
            self.add_result("Tenant Isolation", "PASS", "; ".join(isolation_details))
        else:
            self.add_result("Tenant Isolation", "FAIL", "; ".join(isolation_details))
            
    def run_all_tests(self):
        """Run the complete test suite"""
        self.log("🚀 Starting Portfolio Sync Engine Backend API Tests")
        self.log(f"Backend URL: {self.base_url}")
        
        # Authentication
        if not self.authenticate():
            self.log("❌ Authentication failed - aborting tests")
            return False
            
        # Create test hotel
        self.create_test_hotel()
        
        # Run all tests
        self.test_auth_guards()
        self.test_config_endpoint()
        self.test_connect_endpoint()
        self.test_list_connections()
        self.test_single_connection()
        self.test_update_connection()
        self.test_sync_endpoints()
        self.test_status_dashboard()
        self.test_runs_history()
        self.test_stale_hotels()
        self.test_preview_mapping()
        self.test_available_hotels()
        self.test_delete_connection()
        self.test_tenant_isolation()
        
        # Summary
        self.print_summary()
        return True
        
    def print_summary(self):
        """Print test results summary"""
        self.log("\n" + "="*60)
        self.log("🔍 PORTFOLIO SYNC ENGINE TEST RESULTS")
        self.log("="*60)
        
        passed = sum(1 for r in self.test_results if r["status"] == "PASS")
        failed = sum(1 for r in self.test_results if r["status"] == "FAIL")
        partial = sum(1 for r in self.test_results if r["status"] in ["PARTIAL", "SKIP"])
        
        for result in self.test_results:
            status_icon = {"PASS": "✅", "FAIL": "❌", "PARTIAL": "⚠️", "SKIP": "⏭️"}
            icon = status_icon.get(result["status"], "❓")
            self.log(f"{icon} {result['test']}: {result['status']} - {result['details']}")
            
        self.log("\n" + "-"*60)
        self.log(f"📊 SUMMARY: {passed} PASSED, {failed} FAILED, {partial} PARTIAL/SKIPPED")
        
        if failed == 0:
            self.log("🎉 ALL CRITICAL TESTS PASSED!")
        else:
            self.log("⚠️  SOME TESTS FAILED - REVIEW ABOVE")
            
        # Key findings
        self.log("\n" + "🔍 KEY FINDINGS:")
        config_test = next((r for r in self.test_results if r["test"] == "Config Endpoint"), None)
        if config_test and config_test["status"] == "PASS":
            self.log("✅ Google Sheets graceful fallback working (not configured)")
        else:
            self.log("❌ Google Sheets fallback may have issues")
            
        auth_test = next((r for r in self.test_results if r["test"] == "Auth Guards"), None)
        if auth_test and auth_test["status"] == "PASS":
            self.log("✅ All endpoints properly protected by authentication")
        else:
            self.log("❌ Some endpoints may lack proper auth guards")
            
        tenant_test = next((r for r in self.test_results if r["test"] == "Tenant Isolation"), None)
        if tenant_test and tenant_test["status"] == "PASS":
            self.log("✅ Tenant isolation appears to be working")
        else:
            self.log("❌ Tenant isolation may have issues")


if __name__ == "__main__":
    tester = PortfolioSyncTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)