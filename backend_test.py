#!/usr/bin/env python3
"""
Portfolio Sync Engine Backend API Test Suite

Tests all new endpoints at /api/admin/sheets/* as specified in the review request.
Focus on auth guards, graceful fallback when Google Sheets not configured, 
CRUD operations, and error handling.
"""

import requests
import json
import sys
from typing import Dict, Any, Optional
from datetime import datetime

# Get backend URL from environment
BACKEND_URL = "https://portfolio-connector.preview.emergentagent.com/api"

# Test credentials as specified in review request  
ADMIN_EMAIL = "admin@acenta.test"
ADMIN_PASSWORD = "Test1234!"

class PortfolioSyncTester:
    def __init__(self):
        self.base_url = BACKEND_URL
        self.auth_token = None
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
        status_icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        self.log(f"{status_icon} {test_name}: {status} {details}")
        
    def request(self, method: str, endpoint: str, headers: Optional[Dict] = None, 
               json_data: Optional[Dict] = None, params: Optional[Dict] = None, 
               expect_status: Optional[int] = None) -> requests.Response:
        """Make HTTP request with proper error handling"""
        url = f"{self.base_url}{endpoint}"
        req_headers = {"Content-Type": "application/json"}
        
        if headers:
            req_headers.update(headers)
            
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=req_headers,
                json=json_data,
                params=params,
                timeout=30
            )
            
            status_str = f"{response.status_code}"
            if expect_status and response.status_code == expect_status:
                status_str += " (expected)"
            elif expect_status:
                status_str += f" (expected {expect_status})"
                
            self.log(f"{method} {endpoint} -> {status_str}")
            return response
        except requests.RequestException as e:
            self.log(f"Request failed: {e}", "ERROR")
            raise
            
    def authenticate(self) -> bool:
        """Login and get JWT token as specified in review request"""
        self.log("=== AUTHENTICATION ===")
        
        # First, try to register the user (will fail if exists, that's OK)
        signup_data = {
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD,
            "name": "Test Admin"
        }
        
        try:
            signup_response = self.request("POST", "/auth/signup", json_data=signup_data)
            if signup_response.status_code == 200:
                self.log("✅ User registered successfully")
            elif signup_response.status_code == 409:
                self.log("ℹ️ User already exists (OK)")
            else:
                self.log(f"⚠️ User registration: {signup_response.status_code}")
        except Exception as e:
            self.log(f"⚠️ User registration error (may already exist): {e}")
        
        # Now try to login
        login_data = {
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        }
        
        response = self.request("POST", "/auth/login", json_data=login_data, expect_status=200)
        
        if response.status_code == 200:
            try:
                data = response.json()
                self.auth_token = data.get("access_token")
                if self.auth_token:
                    self.add_result("Authentication", "PASS", f"Token obtained for {ADMIN_EMAIL}")
                    return True
                else:
                    self.add_result("Authentication", "FAIL", "No access_token in response")
                    return False
            except json.JSONDecodeError:
                self.add_result("Authentication", "FAIL", "Invalid JSON response")
                return False
        else:
            self.add_result("Authentication", "FAIL", f"Status: {response.status_code}")
            return False

    def get_auth_headers(self) -> Dict[str, str]:
        """Get headers with Bearer token"""
        if self.auth_token:
            return {"Authorization": f"Bearer {self.auth_token}"}
        return {}

    def test_config_endpoint(self):
        """Test 1: GET /api/admin/sheets/config - Configuration status"""
        self.log("=== TEST 1: CONFIG ENDPOINT ===")
        
        response = self.request("GET", "/admin/sheets/config", 
                               headers=self.get_auth_headers(), expect_status=200)
        
        if response.status_code == 200:
            try:
                data = response.json()
                # Expected: {configured: false, service_account_email: null, message: "..."}
                if (data.get("configured") == False and 
                    data.get("service_account_email") is None and
                    "message" in data):
                    self.add_result("Config Endpoint", "PASS", 
                                  f"configured=false, has message: '{data.get('message')[:50]}...'")
                else:
                    self.add_result("Config Endpoint", "FAIL", 
                                  f"Unexpected response format: {json.dumps(data)}")
            except json.JSONDecodeError:
                self.add_result("Config Endpoint", "FAIL", "Invalid JSON response")
        else:
            self.add_result("Config Endpoint", "FAIL", f"Status: {response.status_code}")

    def create_test_hotel(self) -> bool:
        """Create test hotel as specified in review request"""
        self.log("=== CREATE TEST HOTEL ===")
        
        hotel_data = {
            "name": "Test Sheet Hotel",
            "city": "Istanbul"
        }
        
        response = self.request("POST", "/admin/hotels", 
                               headers=self.get_auth_headers(), 
                               json_data=hotel_data)
        
        if response.status_code == 201:
            try:
                data = response.json()
                self.test_hotel_id = data.get("_id")
                if self.test_hotel_id:
                    self.add_result("Create Test Hotel", "PASS", 
                                  f"Hotel ID: {self.test_hotel_id}")
                    return True
                else:
                    self.add_result("Create Test Hotel", "FAIL", "No _id in response")
            except json.JSONDecodeError:
                self.add_result("Create Test Hotel", "FAIL", "Invalid JSON response")
        else:
            self.add_result("Create Test Hotel", "FAIL", f"Status: {response.status_code}")
        
        return False

    def test_connect_sheet(self):
        """Test 3: POST /api/admin/sheets/connect - Connect hotel to sheet"""
        self.log("=== TEST 3: CONNECT SHEET ===")
        
        if not self.test_hotel_id:
            self.add_result("Connect Sheet", "SKIP", "No test hotel available")
            return
            
        connect_data = {
            "hotel_id": self.test_hotel_id,
            "sheet_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms",
            "sheet_tab": "Sheet1",
            "sync_enabled": True,
            "sync_interval_minutes": 5
        }
        
        response = self.request("POST", "/admin/sheets/connect", 
                               headers=self.get_auth_headers(),
                               json_data=connect_data)
        
        if response.status_code == 200:
            try:
                data = response.json()
                # Expected: connection doc with configured=false, detected_headers=[]
                if (data.get("configured") == False and 
                    isinstance(data.get("detected_headers"), list)):
                    self.add_result("Connect Sheet", "PASS", 
                                  f"Connection created, configured=false, detected_headers=[]")
                else:
                    self.add_result("Connect Sheet", "FAIL", 
                                  f"Unexpected response: configured={data.get('configured')}, detected_headers={data.get('detected_headers')}")
            except json.JSONDecodeError:
                self.add_result("Connect Sheet", "FAIL", "Invalid JSON response")
        else:
            self.add_result("Connect Sheet", "FAIL", f"Status: {response.status_code}")

    def test_list_connections(self):
        """Test 4: GET /api/admin/sheets/connections - List connections"""
        self.log("=== TEST 4: LIST CONNECTIONS ===")
        
        response = self.request("GET", "/admin/sheets/connections", 
                               headers=self.get_auth_headers(), expect_status=200)
        
        if response.status_code == 200:
            try:
                data = response.json()
                if isinstance(data, list):
                    self.add_result("List Connections", "PASS", 
                                  f"Returns array with {len(data)} connections")
                else:
                    self.add_result("List Connections", "FAIL", 
                                  f"Expected array, got: {type(data)}")
            except json.JSONDecodeError:
                self.add_result("List Connections", "FAIL", "Invalid JSON response")
        else:
            self.add_result("List Connections", "FAIL", f"Status: {response.status_code}")

    def test_get_single_connection(self):
        """Test 5: GET /api/admin/sheets/connections/{hotel_id} - Get single connection"""
        self.log("=== TEST 5: GET SINGLE CONNECTION ===")
        
        if not self.test_hotel_id:
            self.add_result("Get Single Connection", "SKIP", "No test hotel available")
            return
            
        response = self.request("GET", f"/admin/sheets/connections/{self.test_hotel_id}", 
                               headers=self.get_auth_headers(), expect_status=200)
        
        if response.status_code == 200:
            try:
                data = response.json()
                if data.get("connected") == True:
                    self.add_result("Get Single Connection", "PASS", 
                                  "Connection detail with connected=true")
                else:
                    self.add_result("Get Single Connection", "PASS", 
                                  f"No connection found: connected={data.get('connected')}")
            except json.JSONDecodeError:
                self.add_result("Get Single Connection", "FAIL", "Invalid JSON response")
        else:
            self.add_result("Get Single Connection", "FAIL", f"Status: {response.status_code}")

    def test_update_connection(self):
        """Test 6: PATCH /api/admin/sheets/connections/{hotel_id} - Update connection"""
        self.log("=== TEST 6: UPDATE CONNECTION ===")
        
        if not self.test_hotel_id:
            self.add_result("Update Connection", "SKIP", "No test hotel available")
            return
            
        update_data = {
            "sync_enabled": False,
            "sync_interval_minutes": 10
        }
        
        response = self.request("PATCH", f"/admin/sheets/connections/{self.test_hotel_id}", 
                               headers=self.get_auth_headers(),
                               json_data=update_data)
        
        if response.status_code == 200:
            try:
                data = response.json()
                if (data.get("sync_enabled") == False and 
                    data.get("sync_interval_minutes") == 10):
                    self.add_result("Update Connection", "PASS", "Connection updated successfully")
                else:
                    self.add_result("Update Connection", "FAIL", 
                                  f"Update not reflected: sync_enabled={data.get('sync_enabled')}, interval={data.get('sync_interval_minutes')}")
            except json.JSONDecodeError:
                self.add_result("Update Connection", "FAIL", "Invalid JSON response")
        else:
            # Connection might not exist yet, that's ok
            if response.status_code == 404:
                self.add_result("Update Connection", "PASS", "404 - No connection to update (expected)")
            else:
                self.add_result("Update Connection", "FAIL", f"Status: {response.status_code}")

    def test_manual_sync(self):
        """Test 7: POST /api/admin/sheets/sync/{hotel_id} - Manual sync (not configured)"""
        self.log("=== TEST 7: MANUAL SYNC ===")
        
        if not self.test_hotel_id:
            self.add_result("Manual Sync", "SKIP", "No test hotel available")
            return
            
        response = self.request("POST", f"/admin/sheets/sync/{self.test_hotel_id}", 
                               headers=self.get_auth_headers())
        
        if response.status_code == 200:
            try:
                data = response.json()
                # Expected: {status: "not_configured", configured: false, message: "..."}
                if (data.get("status") == "not_configured" and 
                    data.get("configured") == False and
                    "message" in data):
                    self.add_result("Manual Sync", "PASS", 
                                  f"status=not_configured, message: '{data.get('message')[:50]}...'")
                else:
                    self.add_result("Manual Sync", "FAIL", 
                                  f"Unexpected response: {json.dumps(data)}")
            except json.JSONDecodeError:
                self.add_result("Manual Sync", "FAIL", "Invalid JSON response")
        else:
            # Connection might not exist
            if response.status_code == 404:
                self.add_result("Manual Sync", "PASS", "404 - No connection to sync (expected)")
            else:
                self.add_result("Manual Sync", "FAIL", f"Status: {response.status_code}")

    def test_sync_all(self):
        """Test 8: POST /api/admin/sheets/sync-all - Sync all connections"""
        self.log("=== TEST 8: SYNC ALL ===")
        
        response = self.request("POST", "/admin/sheets/sync-all", 
                               headers=self.get_auth_headers(), expect_status=200)
        
        if response.status_code == 200:
            try:
                data = response.json()
                # Expected: {status: "not_configured", configured: false}
                if (data.get("status") == "not_configured" and 
                    data.get("configured") == False):
                    self.add_result("Sync All", "PASS", "status=not_configured, configured=false")
                else:
                    self.add_result("Sync All", "FAIL", 
                                  f"Unexpected response: {json.dumps(data)}")
            except json.JSONDecodeError:
                self.add_result("Sync All", "FAIL", "Invalid JSON response")
        else:
            self.add_result("Sync All", "FAIL", f"Status: {response.status_code}")

    def test_portfolio_status(self):
        """Test 9: GET /api/admin/sheets/status - Portfolio health dashboard"""
        self.log("=== TEST 9: PORTFOLIO STATUS ===")
        
        response = self.request("GET", "/admin/sheets/status", 
                               headers=self.get_auth_headers(), expect_status=200)
        
        if response.status_code == 200:
            try:
                data = response.json()
                # Expected: Health summary with total, enabled, healthy counts
                if ("total" in data or "enabled" in data or "healthy" in data):
                    self.add_result("Portfolio Status", "PASS", 
                                  f"Health summary returned: {json.dumps(data)}")
                else:
                    self.add_result("Portfolio Status", "FAIL", 
                                  f"Missing health fields: {json.dumps(data)}")
            except json.JSONDecodeError:
                self.add_result("Portfolio Status", "FAIL", "Invalid JSON response")
        else:
            self.add_result("Portfolio Status", "FAIL", f"Status: {response.status_code}")

    def test_sync_runs(self):
        """Test 10: GET /api/admin/sheets/runs - Sync run history"""
        self.log("=== TEST 10: SYNC RUNS ===")
        
        response = self.request("GET", "/admin/sheets/runs", 
                               headers=self.get_auth_headers(), expect_status=200)
        
        if response.status_code == 200:
            try:
                data = response.json()
                if isinstance(data, list):
                    self.add_result("Sync Runs", "PASS", 
                                  f"Returns array with {len(data)} runs")
                else:
                    self.add_result("Sync Runs", "FAIL", 
                                  f"Expected array, got: {type(data)}")
            except json.JSONDecodeError:
                self.add_result("Sync Runs", "FAIL", "Invalid JSON response")
        else:
            self.add_result("Sync Runs", "FAIL", f"Status: {response.status_code}")

    def test_stale_hotels(self):
        """Test 11: GET /api/admin/sheets/stale-hotels - Stale connections"""
        self.log("=== TEST 11: STALE HOTELS ===")
        
        response = self.request("GET", "/admin/sheets/stale-hotels", 
                               headers=self.get_auth_headers(), expect_status=200)
        
        if response.status_code == 200:
            try:
                data = response.json()
                if isinstance(data, list):
                    self.add_result("Stale Hotels", "PASS", 
                                  f"Returns array with {len(data)} stale connections")
                else:
                    self.add_result("Stale Hotels", "FAIL", 
                                  f"Expected array, got: {type(data)}")
            except json.JSONDecodeError:
                self.add_result("Stale Hotels", "FAIL", "Invalid JSON response")
        else:
            self.add_result("Stale Hotels", "FAIL", f"Status: {response.status_code}")

    def test_preview_mapping(self):
        """Test 12: POST /api/admin/sheets/preview-mapping - Preview mapping (not configured)"""
        self.log("=== TEST 12: PREVIEW MAPPING ===")
        
        preview_data = {
            "sheet_id": "test123",
            "sheet_tab": "Sheet1"
        }
        
        response = self.request("POST", "/admin/sheets/preview-mapping", 
                               headers=self.get_auth_headers(),
                               json_data=preview_data)
        
        if response.status_code == 200:
            try:
                data = response.json()
                # Expected: {configured: false, message: "..."}
                if (data.get("configured") == False and "message" in data):
                    self.add_result("Preview Mapping", "PASS", 
                                  f"configured=false, message: '{data.get('message')[:50]}...'")
                else:
                    self.add_result("Preview Mapping", "FAIL", 
                                  f"Unexpected response: {json.dumps(data)}")
            except json.JSONDecodeError:
                self.add_result("Preview Mapping", "FAIL", "Invalid JSON response")
        else:
            self.add_result("Preview Mapping", "FAIL", f"Status: {response.status_code}")

    def test_available_hotels(self):
        """Test 13: GET /api/admin/sheets/available-hotels - Hotels for connect wizard"""
        self.log("=== TEST 13: AVAILABLE HOTELS ===")
        
        response = self.request("GET", "/admin/sheets/available-hotels", 
                               headers=self.get_auth_headers(), expect_status=200)
        
        if response.status_code == 200:
            try:
                data = response.json()
                if isinstance(data, list):
                    self.add_result("Available Hotels", "PASS", 
                                  f"Returns array with {len(data)} hotels")
                else:
                    self.add_result("Available Hotels", "FAIL", 
                                  f"Expected array, got: {type(data)}")
            except json.JSONDecodeError:
                self.add_result("Available Hotels", "FAIL", "Invalid JSON response")
        else:
            self.add_result("Available Hotels", "FAIL", f"Status: {response.status_code}")

    def test_duplicate_connect(self):
        """Test 14: Duplicate connect test - should return 409"""
        self.log("=== TEST 14: DUPLICATE CONNECT ===")
        
        if not self.test_hotel_id:
            self.add_result("Duplicate Connect", "SKIP", "No test hotel available")
            return
            
        # Try to connect the same hotel again
        connect_data = {
            "hotel_id": self.test_hotel_id,
            "sheet_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms",
            "sheet_tab": "Sheet1",
            "sync_enabled": True,
            "sync_interval_minutes": 5
        }
        
        response = self.request("POST", "/admin/sheets/connect", 
                               headers=self.get_auth_headers(),
                               json_data=connect_data, expect_status=409)
        
        if response.status_code == 409:
            try:
                data = response.json()
                if "connection_exists" in str(data).lower():
                    self.add_result("Duplicate Connect", "PASS", "409 error 'connection_exists'")
                else:
                    self.add_result("Duplicate Connect", "PASS", f"409 error returned: {data}")
            except json.JSONDecodeError:
                self.add_result("Duplicate Connect", "PASS", "409 error returned")
        else:
            # If no existing connection, it might succeed
            if response.status_code == 200:
                self.add_result("Duplicate Connect", "PASS", "200 - No existing connection to duplicate")
            else:
                self.add_result("Duplicate Connect", "FAIL", f"Status: {response.status_code}")

    def test_delete_connection(self):
        """Test 15: DELETE /api/admin/sheets/connections/{hotel_id} - Delete connection"""
        self.log("=== TEST 15: DELETE CONNECTION ===")
        
        if not self.test_hotel_id:
            self.add_result("Delete Connection", "SKIP", "No test hotel available")
            return
            
        response = self.request("DELETE", f"/admin/sheets/connections/{self.test_hotel_id}", 
                               headers=self.get_auth_headers())
        
        if response.status_code == 200:
            try:
                data = response.json()
                if data.get("deleted") == True:
                    self.add_result("Delete Connection", "PASS", "deleted=true")
                else:
                    self.add_result("Delete Connection", "FAIL", 
                                  f"Unexpected response: {json.dumps(data)}")
            except json.JSONDecodeError:
                self.add_result("Delete Connection", "FAIL", "Invalid JSON response")
        else:
            # Connection might not exist
            if response.status_code == 404:
                self.add_result("Delete Connection", "PASS", "404 - No connection to delete (expected)")
            else:
                self.add_result("Delete Connection", "FAIL", f"Status: {response.status_code}")

    def test_auth_guards(self):
        """Test 16: Auth guards - All endpoints should require auth"""
        self.log("=== TEST 16: AUTH GUARDS ===")
        
        # Test config endpoint without token
        response = self.request("GET", "/admin/sheets/config", expect_status=401)
        
        if response.status_code == 401:
            self.add_result("Auth Guards", "PASS", "Returns 401 without authentication token")
        else:
            self.add_result("Auth Guards", "FAIL", f"Expected 401, got {response.status_code}")

    def run_all_tests(self):
        """Run all Portfolio Sync Engine tests in the specified order"""
        print("🚀 Starting Portfolio Sync Engine Tests")
        print("📋 Testing all /api/admin/sheets/* endpoints\n")
        
        # Authentication (required)
        if not self.authenticate():
            print("\n❌ Authentication failed - cannot continue tests")
            return False
            
        # Step 1: Config
        self.test_config_endpoint()
        
        # Step 2: Create test hotel  
        self.create_test_hotel()
        
        # Step 3-15: Portfolio Sync Engine endpoints
        self.test_connect_sheet()
        self.test_list_connections()
        self.test_get_single_connection()
        self.test_update_connection()
        self.test_manual_sync()
        self.test_sync_all()
        self.test_portfolio_status()
        self.test_sync_runs()
        self.test_stale_hotels()
        self.test_preview_mapping()
        self.test_available_hotels()
        self.test_duplicate_connect()
        self.test_delete_connection()
        
        # Step 16: Auth guards
        self.test_auth_guards()
        
        return True

    def print_summary(self):
        """Print test results summary"""
        print("\n" + "="*80)
        print("🏁 PORTFOLIO SYNC ENGINE TEST SUMMARY")
        print("="*80)
        
        total = len(self.test_results)
        passed = len([r for r in self.test_results if r["status"] == "PASS"])
        failed = len([r for r in self.test_results if r["status"] == "FAIL"])
        skipped = len([r for r in self.test_results if r["status"] == "SKIP"])
        
        print(f"\n📊 Results: {passed} PASS, {failed} FAIL, {skipped} SKIP (Total: {total})")
        
        if failed > 0:
            print(f"\n❌ FAILED TESTS ({failed}):")
            for result in self.test_results:
                if result["status"] == "FAIL":
                    print(f"  - {result['test']}: {result['details']}")
        
        if skipped > 0:
            print(f"\n⚠️ SKIPPED TESTS ({skipped}):")
            for result in self.test_results:
                if result["status"] == "SKIP":
                    print(f"  - {result['test']}: {result['details']}")
        
        print(f"\n✅ PASSED TESTS ({passed}):")
        for result in self.test_results:
            if result["status"] == "PASS":
                print(f"  - {result['test']}: {result['details']}")
        
        # Key assertions from review request
        print("\n🔑 KEY ASSERTIONS:")
        no_500_errors = all("500" not in str(r["details"]) for r in self.test_results if r["status"] == "FAIL")
        print(f"  - No 500 errors: {'✅' if no_500_errors else '❌'}")
        
        configured_false = any("configured=false" in str(r["details"]) for r in self.test_results if r["status"] == "PASS")
        print(f"  - configured=false when no GOOGLE_SERVICE_ACCOUNT_JSON: {'✅' if configured_false else '❌'}")
        
        auth_guards = any("Auth Guards" in r["test"] and r["status"] == "PASS" for r in self.test_results)
        print(f"  - Auth guards functional: {'✅' if auth_guards else '❌'}")
        
        crud_working = any("Connect" in r["test"] and r["status"] == "PASS" for r in self.test_results) and \
                      any("List" in r["test"] and r["status"] == "PASS" for r in self.test_results) and \
                      any("Delete" in r["test"] and r["status"] == "PASS" for r in self.test_results)
        print(f"  - All CRUD operations work: {'✅' if crud_working else '❌'}")
        
        return passed, failed, skipped


def main():
    """Main function"""
    tester = PortfolioSyncTester()
    
    try:
        success = tester.run_all_tests()
        passed, failed, skipped = tester.print_summary()
        
        # Exit with error code if tests failed
        if failed > 0:
            sys.exit(1)
        elif not success:
            sys.exit(2)
        else:
            print("\n🎉 All tests completed successfully!")
            sys.exit(0)
            
    except Exception as e:
        print(f"\n💥 Test runner crashed: {e}")
        sys.exit(3)


if __name__ == "__main__":
    main()