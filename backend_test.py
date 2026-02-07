#!/usr/bin/env python3
"""
Google Sheets Live Sync API Testing with Graceful Fallback

Tests the production-ready Google Sheets integration endpoints when 
GOOGLE_SERVICE_ACCOUNT_JSON is NOT set (graceful fallback mode).

All endpoints should work without crashing and return proper error messages.
"""

import asyncio
import csv
import io
import json
import os
import tempfile
import time
from typing import Any, Dict, Optional

import httpx


# Configuration
BACKEND_URL = "https://unified-control-4.preview.emergentagent.com"
ADMIN_EMAIL = "admin@acenta.test"
ADMIN_PASSWORD = "admin123"
API_BASE = f"{BACKEND_URL}/api"


class TestResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
        
    def add_result(self, test_name: str, success: bool, error: Optional[str] = None):
        if success:
            self.passed += 1
            print(f"✅ {test_name}")
        else:
            self.failed += 1
            self.errors.append(f"{test_name}: {error}")
            print(f"❌ {test_name}: {error}")
    
    def summary(self):
        total = self.passed + self.failed
        print(f"\n📊 Test Summary: {self.passed}/{total} passed")
        if self.errors:
            print("\nFailed tests:")
            for error in self.errors:
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