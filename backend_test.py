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
BACKEND_URL = "https://portfolio-connector.preview.emergentagent.com/api"
TEST_USER_EMAIL = "admin@example.com"
TEST_USER_PASSWORD = "password123"

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
                print(f"  - {error}")


class GoogleSheetsLiveSyncTester:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.results = TestResults()
        self.auth_token: Optional[str] = None
        self.connection_id: Optional[str] = None
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
        
    async def authenticate(self):
        """Login as admin and get JWT token."""
        try:
            response = await self.client.post(
                f"{API_BASE}/auth/login",
                json={
                    "email": ADMIN_EMAIL,
                    "password": ADMIN_PASSWORD
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data.get("access_token")
                self.results.add_result("Authentication", True)
                return True
            else:
                self.results.add_result("Authentication", False, f"Status {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.results.add_result("Authentication", False, str(e))
            return False
    
    def get_headers(self):
        """Get headers with auth token."""
        if not self.auth_token:
            return {}
        return {"Authorization": f"Bearer {self.auth_token}"}
    
    async def test_sheet_config(self):
        """Test GET /api/admin/import/sheet/config - should show not configured."""
        try:
            response = await self.client.get(
                f"{API_BASE}/admin/import/sheet/config",
                headers=self.get_headers()
            )
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ["configured", "service_account_email", "message"]
                missing = [f for f in required_fields if f not in data]
                
                if missing:
                    self.results.add_result("Sheet Config", False, f"Missing fields: {missing}")
                elif data["configured"] != False:
                    self.results.add_result("Sheet Config", False, f"Expected configured=false, got {data['configured']}")
                elif data["service_account_email"] is not None:
                    self.results.add_result("Sheet Config", False, f"Expected service_account_email=null, got {data['service_account_email']}")
                elif not data.get("message"):
                    self.results.add_result("Sheet Config", False, "Expected error message when not configured")
                else:
                    self.results.add_result("Sheet Config", True)
                    return data
            else:
                self.results.add_result("Sheet Config", False, f"Status {response.status_code}: {response.text}")
                
        except Exception as e:
            self.results.add_result("Sheet Config", False, str(e))
        
        return None
    
    async def test_sheet_connect(self):
        """Test POST /api/admin/import/sheet/connect - should save gracefully."""
        try:
            test_data = {
                "sheet_id": "test_sheet_123",
                "worksheet_name": "Hotels",
                "column_mapping": {
                    "Otel Adı": "name",
                    "Şehir": "city"
                },
                "sync_enabled": True
            }
            
            response = await self.client.post(
                f"{API_BASE}/admin/import/sheet/connect",
                headers=self.get_headers(),
                json=test_data
            )
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ["id", "sheet_id", "worksheet_name", "configured", "detected_headers"]
                missing = [f for f in required_fields if f not in data]
                
                if missing:
                    self.results.add_result("Sheet Connect", False, f"Missing fields: {missing}")
                elif data["configured"] != False:
                    self.results.add_result("Sheet Connect", False, f"Expected configured=false, got {data['configured']}")
                elif data["detected_headers"] != []:
                    self.results.add_result("Sheet Connect", False, f"Expected empty detected_headers, got {data['detected_headers']}")
                elif data["sheet_id"] != test_data["sheet_id"]:
                    self.results.add_result("Sheet Connect", False, f"Sheet ID mismatch")
                else:
                    self.connection_id = data["id"]
                    self.results.add_result("Sheet Connect", True)
                    return data
            else:
                self.results.add_result("Sheet Connect", False, f"Status {response.status_code}: {response.text}")
                
        except Exception as e:
            self.results.add_result("Sheet Connect", False, str(e))
        
        return None
    
    async def test_sheet_sync(self):
        """Test POST /api/admin/import/sheet/sync - should return not_configured gracefully."""
        try:
            response = await self.client.post(
                f"{API_BASE}/admin/import/sheet/sync",
                headers=self.get_headers(),
                json={}
            )
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ["status", "message", "configured"]
                missing = [f for f in required_fields if f not in data]
                
                if missing:
                    self.results.add_result("Sheet Sync", False, f"Missing fields: {missing}")
                elif data["status"] != "not_configured":
                    self.results.add_result("Sheet Sync", False, f"Expected status='not_configured', got '{data['status']}'")
                elif data["configured"] != False:
                    self.results.add_result("Sheet Sync", False, f"Expected configured=false, got {data['configured']}")
                elif not data.get("message"):
                    self.results.add_result("Sheet Sync", False, "Expected error message when not configured")
                else:
                    self.results.add_result("Sheet Sync", True)
                    return data
            else:
                self.results.add_result("Sheet Sync", False, f"Status {response.status_code}: {response.text}")
                
        except Exception as e:
            self.results.add_result("Sheet Sync", False, str(e))
        
        return None
    
    async def test_sheet_connection(self):
        """Test GET /api/admin/import/sheet/connection - should return connection details."""
        try:
            response = await self.client.get(
                f"{API_BASE}/admin/import/sheet/connection",
                headers=self.get_headers()
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if not data.get("connected"):
                    # No connection exists yet - this is fine
                    if data.get("connected") == False:
                        self.results.add_result("Sheet Connection", True, "No connection exists (expected)")
                        return {"connected": False}
                    else:
                        self.results.add_result("Sheet Connection", False, "Invalid response format")
                else:
                    # Connection exists - verify format
                    required_fields = ["connected", "configured", "service_account_email"]
                    missing = [f for f in required_fields if f not in data]
                    
                    if missing:
                        self.results.add_result("Sheet Connection", False, f"Missing fields: {missing}")
                    elif data["configured"] != False:
                        self.results.add_result("Sheet Connection", False, f"Expected configured=false, got {data['configured']}")
                    else:
                        self.results.add_result("Sheet Connection", True)
                        return data
            else:
                self.results.add_result("Sheet Connection", False, f"Status {response.status_code}: {response.text}")
                
        except Exception as e:
            self.results.add_result("Sheet Connection", False, str(e))
        
        return None
    
    async def test_sheet_status(self):
        """Test GET /api/admin/import/sheet/status - should return sync status."""
        try:
            response = await self.client.get(
                f"{API_BASE}/admin/import/sheet/status",
                headers=self.get_headers()
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if not data.get("connected"):
                    # No connection exists yet
                    if data.get("connected") == False:
                        self.results.add_result("Sheet Status", True, "No connection exists (expected)")
                        return {"connected": False}
                    else:
                        self.results.add_result("Sheet Status", False, "Invalid response format")
                else:
                    # Connection exists - verify status format
                    required_fields = ["connected", "configured", "recent_runs"]
                    missing = [f for f in required_fields if f not in data]
                    
                    if missing:
                        self.results.add_result("Sheet Status", False, f"Missing fields: {missing}")
                    elif data["configured"] != False:
                        self.results.add_result("Sheet Status", False, f"Expected configured=false, got {data['configured']}")
                    elif not isinstance(data["recent_runs"], list):
                        self.results.add_result("Sheet Status", False, "recent_runs should be a list")
                    else:
                        self.results.add_result("Sheet Status", True)
                        return data
            else:
                self.results.add_result("Sheet Status", False, f"Status {response.status_code}: {response.text}")
                
        except Exception as e:
            self.results.add_result("Sheet Status", False, str(e))
        
        return None
    
    async def test_sheet_connections_list(self):
        """Test GET /api/admin/import/sheet/connections - should list all connections."""
        try:
            response = await self.client.get(
                f"{API_BASE}/admin/import/sheet/connections",
                headers=self.get_headers()
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if isinstance(data, list):
                    self.results.add_result("Sheet Connections List", True)
                    return data
                else:
                    self.results.add_result("Sheet Connections List", False, "Response should be a list")
            else:
                self.results.add_result("Sheet Connections List", False, f"Status {response.status_code}: {response.text}")
                
        except Exception as e:
            self.results.add_result("Sheet Connections List", False, str(e))
        
        return None
    
    async def test_excel_import_still_works(self):
        """Test that Excel import still works (regression test)."""
        try:
            # Create test CSV
            timestamp = str(int(time.time()))
            test_csv = f"name,city,country\nSheets Test Hotel,Istanbul,TR"
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
                f.write(test_csv)
                temp_path = f.name
            
            # Upload
            with open(temp_path, 'rb') as f:
                files = {"file": ("test_sheets.csv", f, "text/csv")}
                response = await self.client.post(
                    f"{API_BASE}/admin/import/hotels/upload",
                    headers=self.get_headers(),
                    files=files
                )
            
            os.unlink(temp_path)
            
            if response.status_code == 200:
                data = response.json()
                job_id = data["job_id"]
                
                # Validate
                response = await self.client.post(
                    f"{API_BASE}/admin/import/hotels/validate",
                    headers=self.get_headers(),
                    json={
                        "job_id": job_id,
                        "mapping": {"0": "name", "1": "city", "2": "country"}
                    }
                )
                
                if response.status_code == 200:
                    self.results.add_result("Excel Import Still Works", True)
                    return True
                else:
                    self.results.add_result("Excel Import Still Works", False, f"Validation failed: {response.status_code}")
            else:
                self.results.add_result("Excel Import Still Works", False, f"Upload failed: {response.status_code}")
                
        except Exception as e:
            self.results.add_result("Excel Import Still Works", False, str(e))
        
        return False
    
    async def test_auth_guards(self):
        """Test that sheet endpoints require admin authentication."""
        sheet_endpoints = [
            ("GET", "/admin/import/sheet/config"),
            ("POST", "/admin/import/sheet/connect"),
            ("POST", "/admin/import/sheet/sync"),
            ("GET", "/admin/import/sheet/connection"),
            ("GET", "/admin/import/sheet/status"),
            ("GET", "/admin/import/sheet/connections"),
        ]
        
        for method, endpoint in sheet_endpoints:
            try:
                if method == "GET":
                    response = await self.client.get(f"{API_BASE}{endpoint}")
                else:
                    response = await self.client.post(f"{API_BASE}{endpoint}", json={})
                
                if response.status_code == 401:
                    self.results.add_result(f"Auth Guard - {method} {endpoint}", True)
                else:
                    self.results.add_result(f"Auth Guard - {method} {endpoint}", False, f"Expected 401, got {response.status_code}")
            except Exception as e:
                self.results.add_result(f"Auth Guard - {method} {endpoint}", False, str(e))
    
    async def test_graceful_error_handling(self):
        """Test graceful error handling scenarios."""
        
        # Test connect with invalid body
        try:
            response = await self.client.post(
                f"{API_BASE}/admin/import/sheet/connect",
                headers=self.get_headers(),
                json={"invalid": "body"}
            )
            
            if response.status_code in [400, 422]:  # Should return validation error
                self.results.add_result("Connect Invalid Body", True)
            else:
                self.results.add_result("Connect Invalid Body", False, f"Expected 400/422, got {response.status_code}")
        except Exception as e:
            self.results.add_result("Connect Invalid Body", False, str(e))
        
        # Test sync without any connection (should return 404)
        try:
            # First clear any existing connections by creating a fresh login
            response = await self.client.post(
                f"{API_BASE}/admin/import/sheet/sync",
                headers=self.get_headers(),
                json={}
            )
            
            # It should either work (if connection exists) or fail gracefully
            if response.status_code in [200, 404]:
                self.results.add_result("Sync Without Connection", True)
            else:
                self.results.add_result("Sync Without Connection", False, f"Expected 200/404, got {response.status_code}")
        except Exception as e:
            self.results.add_result("Sync Without Connection", False, str(e))
    
    async def run_all_tests(self):
        """Run all Google Sheets Live Sync tests."""
        print("🚀 Starting Google Sheets Live Sync Tests (Graceful Fallback Mode)\n")
        print("📋 Testing endpoints when GOOGLE_SERVICE_ACCOUNT_JSON is NOT set\n")
        
        # Core functionality tests
        if not await self.authenticate():
            return self.results
        
        # Main endpoints
        await self.test_sheet_config()
        await self.test_sheet_connect()  # This creates a connection
        await self.test_sheet_sync()
        await self.test_sheet_connection()
        await self.test_sheet_status()
        await self.test_sheet_connections_list()
        
        # Regression test
        await self.test_excel_import_still_works()
        
        # Security tests
        await self.test_auth_guards()
        
        # Error handling tests
        await self.test_graceful_error_handling()
        
        return self.results


async def main():
    """Run the complete test suite."""
    async with GoogleSheetsLiveSyncTester() as tester:
        results = await tester.run_all_tests()
        results.summary()


if __name__ == "__main__":
    asyncio.run(main())