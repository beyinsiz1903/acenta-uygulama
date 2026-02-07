#!/usr/bin/env python3
"""
Zero Migration Friction Engine - Hotel Import API Testing

Tests all the import endpoints with comprehensive scenarios including:
- CSV upload and processing
- Column mapping and validation 
- Bulk execution and job tracking
- Template export
- Google Sheets integration (MOCKED)
- Error handling and edge cases
- Authentication requirements
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

# Test data
TEST_CSV_CONTENT = """Otel Adı,Şehir,Ülke,Açıklama,Fiyat,Yıldız
Import Hotel 1,İstanbul,TR,Test hotel,1500,5
Import Hotel 2,Antalya,TR,Beach hotel,2000,4
Import Hotel 3,Bodrum,TR,Marina view,3000,5
Import Hotel 4,,TR,Missing city,,3
Import Hotel 5,İzmir,TR,Good hotel,abc,4"""

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


class HotelImportTester:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.results = TestResults()
        self.auth_token: Optional[str] = None
        self.job_id: Optional[str] = None
        
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
    
    async def test_upload_csv(self):
        """Test CSV upload endpoint."""
        try:
            # Create temporary CSV file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
                f.write(TEST_CSV_CONTENT)
                temp_path = f.name
            
            # Upload file
            with open(temp_path, 'rb') as f:
                files = {"file": ("test_import.csv", f, "text/csv")}
                response = await self.client.post(
                    f"{API_BASE}/admin/import/hotels/upload",
                    headers=self.get_headers(),
                    files=files
                )
            
            os.unlink(temp_path)  # Clean up
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ["job_id", "filename", "total_rows", "headers", "preview", "available_fields"]
                missing = [f for f in required_fields if f not in data]
                
                if missing:
                    self.results.add_result("CSV Upload", False, f"Missing fields: {missing}")
                elif data["total_rows"] != 5:
                    self.results.add_result("CSV Upload", False, f"Expected 5 rows, got {data['total_rows']}")
                else:
                    self.job_id = data["job_id"]
                    self.results.add_result("CSV Upload", True)
                    return data
            else:
                self.results.add_result("CSV Upload", False, f"Status {response.status_code}: {response.text}")
                
        except Exception as e:
            self.results.add_result("CSV Upload", False, str(e))
        
        return None
    
    async def test_validate_mapping(self):
        """Test validation with column mapping."""
        if not self.job_id:
            self.results.add_result("Validation with Mapping", False, "No job_id from upload")
            return None
            
        try:
            mapping = {
                "0": "name",
                "1": "city", 
                "2": "country",
                "3": "description",
                "4": "price",
                "5": "stars"
            }
            
            response = await self.client.post(
                f"{API_BASE}/admin/import/hotels/validate",
                headers=self.get_headers(),
                json={
                    "job_id": self.job_id,
                    "mapping": mapping
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ["job_id", "total_rows", "valid_count", "error_count"]
                missing = [f for f in required_fields if f not in data]
                
                if missing:
                    self.results.add_result("Validation with Mapping", False, f"Missing fields: {missing}")
                elif data["valid_count"] != 3:
                    self.results.add_result("Validation with Mapping", False, f"Expected 3 valid rows, got {data['valid_count']}")
                elif data["error_count"] < 2:
                    self.results.add_result("Validation with Mapping", False, f"Expected >= 2 errors, got {data['error_count']}")
                else:
                    self.results.add_result("Validation with Mapping", True)
                    return data
            else:
                self.results.add_result("Validation with Mapping", False, f"Status {response.status_code}: {response.text}")
                
        except Exception as e:
            self.results.add_result("Validation with Mapping", False, str(e))
        
        return None
    
    async def test_execute_import(self):
        """Test executing the import."""
        if not self.job_id:
            self.results.add_result("Execute Import", False, "No job_id from upload")
            return None
            
        try:
            response = await self.client.post(
                f"{API_BASE}/admin/import/hotels/execute",
                headers=self.get_headers(),
                json={"job_id": self.job_id}
            )
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ["job_id", "status", "message"]
                missing = [f for f in required_fields if f not in data]
                
                if missing:
                    self.results.add_result("Execute Import", False, f"Missing fields: {missing}")
                elif data["status"] != "processing":
                    self.results.add_result("Execute Import", False, f"Expected status 'processing', got '{data['status']}'")
                else:
                    self.results.add_result("Execute Import", True)
                    return data
            else:
                self.results.add_result("Execute Import", False, f"Status {response.status_code}: {response.text}")
                
        except Exception as e:
            self.results.add_result("Execute Import", False, str(e))
        
        return None
    
    async def test_list_jobs(self):
        """Test listing import jobs."""
        try:
            response = await self.client.get(
                f"{API_BASE}/admin/import/jobs",
                headers=self.get_headers()
            )
            
            if response.status_code == 200:
                jobs = response.json()
                if isinstance(jobs, list):
                    self.results.add_result("List Import Jobs", True)
                    return jobs
                else:
                    self.results.add_result("List Import Jobs", False, "Response is not a list")
            else:
                self.results.add_result("List Import Jobs", False, f"Status {response.status_code}: {response.text}")
                
        except Exception as e:
            self.results.add_result("List Import Jobs", False, str(e))
        
        return None
    
    async def test_get_job_detail(self):
        """Test getting job detail with errors."""
        if not self.job_id:
            self.results.add_result("Get Job Detail", False, "No job_id from upload")
            return None
            
        try:
            # Wait for job to complete
            await asyncio.sleep(3)
            
            response = await self.client.get(
                f"{API_BASE}/admin/import/jobs/{self.job_id}",
                headers=self.get_headers()
            )
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ["_id", "status", "success_count", "error_count"]
                missing = [f for f in required_fields if f not in data]
                
                if missing:
                    self.results.add_result("Get Job Detail", False, f"Missing fields: {missing}")
                elif "errors" not in data:
                    self.results.add_result("Get Job Detail", False, "Missing errors array")
                else:
                    self.results.add_result("Get Job Detail", True)
                    return data
            else:
                self.results.add_result("Get Job Detail", False, f"Status {response.status_code}: {response.text}")
                
        except Exception as e:
            self.results.add_result("Get Job Detail", False, str(e))
        
        return None
    
    async def test_export_template(self):
        """Test downloading XLSX template."""
        try:
            response = await self.client.get(
                f"{API_BASE}/admin/import/export-template",
                headers=self.get_headers()
            )
            
            if response.status_code == 200:
                content_type = response.headers.get("content-type", "")
                content_disposition = response.headers.get("content-disposition", "")
                
                if "spreadsheet" in content_type and "attachment" in content_disposition:
                    self.results.add_result("Export XLSX Template", True)
                    return True
                else:
                    self.results.add_result("Export XLSX Template", False, f"Wrong content type or disposition")
            else:
                self.results.add_result("Export XLSX Template", False, f"Status {response.status_code}: {response.text}")
                
        except Exception as e:
            self.results.add_result("Export XLSX Template", False, str(e))
        
        return False
    
    async def test_sheet_connect(self):
        """Test Google Sheet connection (MOCKED)."""
        try:
            response = await self.client.post(
                f"{API_BASE}/admin/import/sheet/connect",
                headers=self.get_headers(),
                json={
                    "sheet_id": "test123",
                    "worksheet_name": "Sheet1",
                    "sync_enabled": False
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ["_id", "sheet_id", "worksheet_name", "status"]
                missing = [f for f in required_fields if f not in data]
                
                if missing:
                    self.results.add_result("Sheet Connect (MOCKED)", False, f"Missing fields: {missing}")
                else:
                    self.results.add_result("Sheet Connect (MOCKED)", True)
                    return data
            else:
                self.results.add_result("Sheet Connect (MOCKED)", False, f"Status {response.status_code}: {response.text}")
                
        except Exception as e:
            self.results.add_result("Sheet Connect (MOCKED)", False, str(e))
        
        return None
    
    async def test_sheet_sync(self):
        """Test Google Sheet sync (MOCKED)."""
        try:
            response = await self.client.post(
                f"{API_BASE}/admin/import/sheet/sync",
                headers=self.get_headers(),
                json={}
            )
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ["status", "message", "sheet_id", "last_sync_at"]
                missing = [f for f in required_fields if f not in data]
                
                if missing:
                    self.results.add_result("Sheet Sync (MOCKED)", False, f"Missing fields: {missing}")
                elif data["status"] != "synced":
                    self.results.add_result("Sheet Sync (MOCKED)", False, f"Expected status 'synced', got '{data['status']}'")
                else:
                    self.results.add_result("Sheet Sync (MOCKED)", True)
                    return data
            else:
                self.results.add_result("Sheet Sync (MOCKED)", False, f"Status {response.status_code}: {response.text}")
                
        except Exception as e:
            self.results.add_result("Sheet Sync (MOCKED)", False, str(e))
        
        return None
    
    async def test_list_sheet_connections(self):
        """Test listing sheet connections."""
        try:
            response = await self.client.get(
                f"{API_BASE}/admin/import/sheet/connections",
                headers=self.get_headers()
            )
            
            if response.status_code == 200:
                connections = response.json()
                if isinstance(connections, list) and len(connections) >= 1:
                    self.results.add_result("List Sheet Connections", True)
                    return connections
                else:
                    self.results.add_result("List Sheet Connections", False, f"Expected list with >= 1 connection, got {len(connections) if isinstance(connections, list) else 'not list'}")
            else:
                self.results.add_result("List Sheet Connections", False, f"Status {response.status_code}: {response.text}")
                
        except Exception as e:
            self.results.add_result("List Sheet Connections", False, str(e))
        
        return None
    
    async def test_validation_errors(self):
        """Test various validation scenarios."""
        
        # Test upload without file
        try:
            response = await self.client.post(
                f"{API_BASE}/admin/import/hotels/upload",
                headers=self.get_headers()
            )
            if response.status_code in [400, 422]:  # Should return error
                self.results.add_result("Upload Without File", True)
            else:
                self.results.add_result("Upload Without File", False, f"Expected 400/422, got {response.status_code}")
        except Exception as e:
            self.results.add_result("Upload Without File", False, str(e))
        
        # Test upload with invalid format
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write("Invalid content")
                temp_path = f.name
            
            with open(temp_path, 'rb') as f:
                files = {"file": ("test.txt", f, "text/plain")}
                response = await self.client.post(
                    f"{API_BASE}/admin/import/hotels/upload",
                    headers=self.get_headers(),
                    files=files
                )
            
            os.unlink(temp_path)
            
            if response.status_code == 400:
                self.results.add_result("Upload Invalid Format", True)
            else:
                self.results.add_result("Upload Invalid Format", False, f"Expected 400, got {response.status_code}")
        except Exception as e:
            self.results.add_result("Upload Invalid Format", False, str(e))
        
        # Test validate with invalid job_id
        try:
            response = await self.client.post(
                f"{API_BASE}/admin/import/hotels/validate",
                headers=self.get_headers(),
                json={
                    "job_id": "invalid-job-id",
                    "mapping": {"0": "name"}
                }
            )
            if response.status_code == 404:
                self.results.add_result("Validate Invalid Job ID", True)
            else:
                self.results.add_result("Validate Invalid Job ID", False, f"Expected 404, got {response.status_code}")
        except Exception as e:
            self.results.add_result("Validate Invalid Job ID", False, str(e))
        
        # Test execute with invalid job_id
        try:
            response = await self.client.post(
                f"{API_BASE}/admin/import/hotels/execute",
                headers=self.get_headers(),
                json={"job_id": "invalid-job-id"}
            )
            if response.status_code == 404:
                self.results.add_result("Execute Invalid Job ID", True)
            else:
                self.results.add_result("Execute Invalid Job ID", False, f"Expected 404, got {response.status_code}")
        except Exception as e:
            self.results.add_result("Execute Invalid Job ID", False, str(e))
    
    async def test_authentication_required(self):
        """Test that admin endpoints require authentication."""
        endpoints = [
            ("GET", "/admin/import/jobs"),
            ("POST", "/admin/import/hotels/upload"),
            ("GET", "/admin/import/export-template"),
            ("POST", "/admin/import/sheet/connect"),
            ("POST", "/admin/import/sheet/sync"),
            ("GET", "/admin/import/sheet/connections"),
        ]
        
        for method, endpoint in endpoints:
            try:
                if method == "GET":
                    response = await self.client.get(f"{API_BASE}{endpoint}")
                else:
                    response = await self.client.post(f"{API_BASE}{endpoint}", json={})
                    
                if response.status_code == 401:
                    self.results.add_result(f"Auth Required - {method} {endpoint}", True)
                else:
                    self.results.add_result(f"Auth Required - {method} {endpoint}", False, f"Expected 401, got {response.status_code}")
            except Exception as e:
                self.results.add_result(f"Auth Required - {method} {endpoint}", False, str(e))
    
    async def test_duplicate_detection(self):
        """Test duplicate hotel detection."""
        # First, upload and process the same hotels again
        try:
            # Create CSV with same hotel names
            duplicate_csv = """Otel Adı,Şehir,Ülke,Açıklama,Fiyat,Yıldız
Import Hotel 1,İstanbul,TR,Duplicate test,1600,5
Import Hotel 2,Ankara,TR,Another duplicate,1800,4"""
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
                f.write(duplicate_csv)
                temp_path = f.name
            
            # Upload
            with open(temp_path, 'rb') as f:
                files = {"file": ("duplicate_test.csv", f, "text/csv")}
                response = await self.client.post(
                    f"{API_BASE}/admin/import/hotels/upload",
                    headers=self.get_headers(),
                    files=files
                )
            
            os.unlink(temp_path)
            
            if response.status_code == 200:
                data = response.json()
                job_id = data["job_id"]
                
                # Validate - should detect duplicates
                mapping = {"0": "name", "1": "city", "2": "country", "3": "description", "4": "price", "5": "stars"}
                response = await self.client.post(
                    f"{API_BASE}/admin/import/hotels/validate",
                    headers=self.get_headers(),
                    json={"job_id": job_id, "mapping": mapping}
                )
                
                if response.status_code == 200:
                    validation_data = response.json()
                    if validation_data["error_count"] >= 2:  # Should detect duplicates
                        self.results.add_result("Duplicate Detection", True)
                    else:
                        self.results.add_result("Duplicate Detection", False, f"Expected >= 2 duplicate errors, got {validation_data['error_count']}")
                else:
                    self.results.add_result("Duplicate Detection", False, f"Validation failed: {response.status_code}")
            else:
                self.results.add_result("Duplicate Detection", False, f"Upload failed: {response.status_code}")
                
        except Exception as e:
            self.results.add_result("Duplicate Detection", False, str(e))
    
    async def run_all_tests(self):
        """Run all test scenarios."""
        print("🚀 Starting Zero Migration Friction Engine - Hotel Import API Tests\n")
        
        # Core functionality tests
        if not await self.authenticate():
            return self.results
        
        upload_result = await self.test_upload_csv()
        if upload_result:
            await self.test_validate_mapping()
            await self.test_execute_import()
            await self.test_get_job_detail()
        
        await self.test_list_jobs()
        await self.test_export_template()
        
        # Google Sheets (MOCKED) tests
        await self.test_sheet_connect()
        await self.test_sheet_sync()
        await self.test_list_sheet_connections()
        
        # Validation and error handling tests
        await self.test_validation_errors()
        await self.test_authentication_required()
        await self.test_duplicate_detection()
        
        return self.results


async def main():
    """Run the complete test suite."""
    async with HotelImportTester() as tester:
        results = await tester.run_all_tests()
        results.summary()


if __name__ == "__main__":
    asyncio.run(main())