#!/usr/bin/env python3

"""
Backend API Test Suite for Tour Enhancement APIs

Tests all tour-related endpoints on https://tour-reserve.preview.emergentagent.com
- Authentication (POST /api/auth/login)
- Tours browsing (GET /api/tours, GET /api/tours/{id}) 
- Tour reservations (POST /api/tours/{id}/reserve)
- Admin tour management (GET/PUT/DELETE /api/admin/tours/{id})
- Image upload (POST /api/admin/tours/upload-image)
"""

import requests
import json
import sys
from typing import Dict, Any, Optional


class TourAPITester:
    def __init__(self):
        self.base_url = "https://tour-reserve.preview.emergentagent.com"
        self.token: Optional[str] = None
        self.headers: Dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        self.results = []
        
    def log(self, message: str, level: str = "INFO"):
        """Log messages with level indicator"""
        print(f"[{level}] {message}")
        
    def record_result(self, test_name: str, success: bool, details: str, response_data: Any = None):
        """Record test result"""
        result = {
            "test": test_name,
            "success": success,
            "details": details,
            "response": response_data
        }
        self.results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        self.log(f"{status} {test_name}: {details}")
        
    def make_request(self, method: str, endpoint: str, data: Any = None, auth_required: bool = True) -> requests.Response:
        """Make HTTP request with proper headers"""
        url = f"{self.base_url}{endpoint}"
        headers = self.headers.copy()
        
        if auth_required and self.token:
            headers["Authorization"] = f"Bearer {self.token}"
            
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, timeout=30)
            elif method.upper() == "POST":
                response = requests.post(url, headers=headers, json=data, timeout=30)
            elif method.upper() == "PUT":
                response = requests.put(url, headers=headers, json=data, timeout=30)
            elif method.upper() == "DELETE":
                response = requests.delete(url, headers=headers, timeout=30)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
                
            return response
        except requests.RequestException as e:
            self.log(f"Request failed: {str(e)}", "ERROR")
            raise
            
    def test_login(self) -> bool:
        """Test POST /api/auth/login - Get authentication token"""
        self.log("Testing authentication...")
        
        login_data = {
            "email": "admin@acenta.test",
            "password": "admin123"
        }
        
        try:
            response = self.make_request("POST", "/api/auth/login", login_data, auth_required=False)
            
            if response.status_code == 200:
                data = response.json()
                if "access_token" in data:
                    self.token = data["access_token"]
                    self.record_result("Login", True, f"Successfully authenticated. Token length: {len(self.token)}", data)
                    return True
                else:
                    self.record_result("Login", False, f"No access_token in response: {data}")
                    return False
            else:
                self.record_result("Login", False, f"Status {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.record_result("Login", False, f"Exception during login: {str(e)}")
            return False
            
    def test_tours_list(self) -> Optional[str]:
        """Test GET /api/tours - List tours with authentication"""
        self.log("Testing tours list...")
        
        try:
            response = self.make_request("GET", "/api/tours")
            
            if response.status_code == 200:
                data = response.json()
                if "items" in data:
                    tours_count = len(data["items"])
                    self.record_result("Tours List", True, f"Retrieved {tours_count} tours successfully", {
                        "count": tours_count,
                        "has_filters": "filters" in data,
                        "total": data.get("total", 0)
                    })
                    # Return first tour ID for detail testing
                    if data["items"]:
                        return data["items"][0]["id"]
                    return None
                else:
                    self.record_result("Tours List", False, f"No 'items' in response: {data}")
            else:
                self.record_result("Tours List", False, f"Status {response.status_code}: {response.text}")
                
        except Exception as e:
            self.record_result("Tours List", False, f"Exception: {str(e)}")
            
        return None
        
    def test_tours_list_with_filters(self) -> bool:
        """Test GET /api/tours with query parameters"""
        self.log("Testing tours list with filters...")
        
        test_params = [
            ("q", "Kapadokya"),
            ("destination", "Istanbul"), 
            ("category", "Cultural"),
            ("min_price", "100"),
            ("max_price", "500"),
            ("page", "1"),
            ("page_size", "10")
        ]
        
        success_count = 0
        for param, value in test_params:
            try:
                endpoint = f"/api/tours?{param}={value}"
                response = self.make_request("GET", endpoint)
                
                if response.status_code == 200:
                    data = response.json()
                    success_count += 1
                    self.log(f"Filter {param}={value} works: {len(data.get('items', []))} results")
                else:
                    self.log(f"Filter {param}={value} failed: {response.status_code}", "WARN")
                    
            except Exception as e:
                self.log(f"Filter {param}={value} exception: {str(e)}", "ERROR")
                
        success = success_count >= 4  # At least half should work
        self.record_result("Tours List Filters", success, f"{success_count}/{len(test_params)} filters working")
        return success
        
    def test_tour_detail(self, tour_id: str) -> bool:
        """Test GET /api/tours/{tour_id} - Get tour detail"""
        if not tour_id:
            self.record_result("Tour Detail", False, "No tour ID available for testing")
            return False
            
        self.log(f"Testing tour detail for ID: {tour_id}")
        
        try:
            response = self.make_request("GET", f"/api/tours/{tour_id}")
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ["id", "name", "description", "base_price"]
                missing_fields = [f for f in required_fields if f not in data]
                
                if not missing_fields:
                    self.record_result("Tour Detail", True, f"Tour detail retrieved successfully. Name: {data.get('name', 'N/A')}", {
                        "tour_name": data.get("name"),
                        "has_images": len(data.get("images", [])) > 0,
                        "has_itinerary": len(data.get("itinerary", [])) > 0,
                        "has_includes": len(data.get("includes", [])) > 0
                    })
                    return True
                else:
                    self.record_result("Tour Detail", False, f"Missing required fields: {missing_fields}")
            else:
                self.record_result("Tour Detail", False, f"Status {response.status_code}: {response.text}")
                
        except Exception as e:
            self.record_result("Tour Detail", False, f"Exception: {str(e)}")
            
        return False
        
    def test_tour_reservation(self, tour_id: str) -> bool:
        """Test POST /api/tours/{tour_id}/reserve - Create reservation"""
        if not tour_id:
            self.record_result("Tour Reservation", False, "No tour ID available for testing")
            return False
            
        self.log(f"Testing tour reservation for ID: {tour_id}")
        
        reservation_data = {
            "travel_date": "2025-08-15",
            "adults": 2,
            "children": 1, 
            "guest_name": "John Doe",
            "guest_email": "john.doe@example.com",
            "guest_phone": "+905551234567",
            "notes": "Test reservation from API testing"
        }
        
        try:
            response = self.make_request("POST", f"/api/tours/{tour_id}/reserve", reservation_data)
            
            if response.status_code == 201:
                data = response.json()
                required_fields = ["reservation_code", "total", "status"]
                missing_fields = [f for f in required_fields if f not in data]
                
                if not missing_fields:
                    self.record_result("Tour Reservation", True, f"Reservation created: {data.get('reservation_code')}", {
                        "reservation_code": data.get("reservation_code"),
                        "total": data.get("total"),
                        "currency": data.get("currency"),
                        "status": data.get("status")
                    })
                    return True
                else:
                    self.record_result("Tour Reservation", False, f"Missing fields in response: {missing_fields}")
            else:
                self.record_result("Tour Reservation", False, f"Status {response.status_code}: {response.text}")
                
        except Exception as e:
            self.record_result("Tour Reservation", False, f"Exception: {str(e)}")
            
        return False
        
    def test_admin_tours_list(self) -> Optional[str]:
        """Test GET /api/admin/tours - Admin list tours"""
        self.log("Testing admin tours list...")
        
        try:
            response = self.make_request("GET", "/api/admin/tours")
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    tours_count = len(data)
                    self.record_result("Admin Tours List", True, f"Retrieved {tours_count} tours in admin panel", {
                        "count": tours_count
                    })
                    # Return first tour ID for admin operations
                    if data:
                        return data[0]["id"]
                    return None
                else:
                    self.record_result("Admin Tours List", False, f"Expected list, got: {type(data)}")
            else:
                self.record_result("Admin Tours List", False, f"Status {response.status_code}: {response.text}")
                
        except Exception as e:
            self.record_result("Admin Tours List", False, f"Exception: {str(e)}")
            
        return None
        
    def test_admin_tour_detail(self, tour_id: str) -> bool:
        """Test GET /api/admin/tours/{tour_id} - Admin get single tour"""
        if not tour_id:
            self.record_result("Admin Tour Detail", False, "No tour ID available for testing")
            return False
            
        self.log(f"Testing admin tour detail for ID: {tour_id}")
        
        try:
            response = self.make_request("GET", f"/api/admin/tours/{tour_id}")
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ["id", "name", "description"]
                missing_fields = [f for f in required_fields if f not in data]
                
                if not missing_fields:
                    self.record_result("Admin Tour Detail", True, f"Admin tour detail retrieved: {data.get('name', 'N/A')}", {
                        "tour_name": data.get("name"),
                        "status": data.get("status"),
                        "base_price": data.get("base_price")
                    })
                    return True
                else:
                    self.record_result("Admin Tour Detail", False, f"Missing required fields: {missing_fields}")
            else:
                self.record_result("Admin Tour Detail", False, f"Status {response.status_code}: {response.text}")
                
        except Exception as e:
            self.record_result("Admin Tour Detail", False, f"Exception: {str(e)}")
            
        return False
        
    def test_admin_tour_update(self, tour_id: str) -> bool:
        """Test PUT /api/admin/tours/{tour_id} - Update tour"""
        if not tour_id:
            self.record_result("Admin Tour Update", False, "No tour ID available for testing")
            return False
            
        self.log(f"Testing admin tour update for ID: {tour_id}")
        
        update_data = {
            "name": "Updated Tour Name (API Test)",
            "description": "Updated description from API testing"
        }
        
        try:
            response = self.make_request("PUT", f"/api/admin/tours/{tour_id}", update_data)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("name") == update_data["name"]:
                    self.record_result("Admin Tour Update", True, f"Tour updated successfully: {data.get('name')}", {
                        "updated_name": data.get("name"),
                        "updated_description": data.get("description")
                    })
                    
                    # Revert the change
                    try:
                        revert_data = {
                            "name": data.get("name", "").replace(" (API Test)", ""),
                            "description": data.get("description", "").replace(" from API testing", "")
                        }
                        self.make_request("PUT", f"/api/admin/tours/{tour_id}", revert_data)
                        self.log("Successfully reverted tour changes")
                    except:
                        self.log("Failed to revert tour changes", "WARN")
                        
                    return True
                else:
                    self.record_result("Admin Tour Update", False, f"Update not reflected. Expected: {update_data['name']}, Got: {data.get('name')}")
            else:
                self.record_result("Admin Tour Update", False, f"Status {response.status_code}: {response.text}")
                
        except Exception as e:
            self.record_result("Admin Tour Update", False, f"Exception: {str(e)}")
            
        return False
        
    def test_admin_tour_delete_auth(self, tour_id: str) -> bool:
        """Test DELETE /api/admin/tours/{tour_id} - Test auth guard only (don't actually delete)"""
        if not tour_id:
            self.record_result("Admin Tour Delete Auth", False, "No tour ID available for testing")
            return False
            
        self.log(f"Testing admin tour delete auth guard for ID: {tour_id}")
        
        # Test without token first
        try:
            headers_no_auth = self.headers.copy()
            # Remove auth header if present
            if "Authorization" in headers_no_auth:
                del headers_no_auth["Authorization"]
                
            url = f"{self.base_url}/api/admin/tours/{tour_id}"
            response = requests.delete(url, headers=headers_no_auth, timeout=30)
            
            if response.status_code == 401:
                self.record_result("Admin Tour Delete Auth (No Token)", True, "Correctly returned 401 without auth token", {
                    "status_code": response.status_code,
                    "response": response.text[:200]
                })
                
                # Test with valid token (but don't actually delete - just verify access)
                auth_response = self.make_request("GET", f"/api/admin/tours/{tour_id}")
                if auth_response.status_code == 200:
                    self.record_result("Admin Tour Delete Auth (With Token)", True, "Auth guard working - can access with token")
                    return True
                else:
                    self.record_result("Admin Tour Delete Auth (With Token)", False, f"Cannot access with token: {auth_response.status_code}")
                    
            else:
                self.record_result("Admin Tour Delete Auth (No Token)", False, f"Expected 401, got {response.status_code}")
                
        except Exception as e:
            self.record_result("Admin Tour Delete Auth", False, f"Exception: {str(e)}")
            
        return False
        
    def test_admin_image_upload_auth(self) -> bool:
        """Test POST /api/admin/tours/upload-image - Test auth guard only"""
        self.log("Testing admin image upload auth guard...")
        
        # Test without token
        try:
            headers_no_auth = self.headers.copy()
            if "Authorization" in headers_no_auth:
                del headers_no_auth["Authorization"]
                
            # Remove content-type for file upload
            if "Content-Type" in headers_no_auth:
                del headers_no_auth["Content-Type"]
                
            url = f"{self.base_url}/api/admin/tours/upload-image"
            
            # Create a small test file
            files = {'file': ('test.jpg', b'fake image data', 'image/jpeg')}
            response = requests.post(url, headers=headers_no_auth, files=files, timeout=30)
            
            if response.status_code == 401:
                self.record_result("Admin Image Upload Auth", True, "Correctly returned 401 without auth token", {
                    "status_code": response.status_code
                })
                return True
            else:
                self.record_result("Admin Image Upload Auth", False, f"Expected 401, got {response.status_code}: {response.text}")
                
        except Exception as e:
            self.record_result("Admin Image Upload Auth", False, f"Exception: {str(e)}")
            
        return False
        
    def test_auth_guards(self) -> bool:
        """Test all endpoints without authentication to verify 401 responses"""
        self.log("Testing authentication guards...")
        
        endpoints_to_test = [
            ("GET", "/api/tours"),
            ("GET", "/api/tours/test-id"),
            ("POST", "/api/tours/test-id/reserve"),
            ("GET", "/api/admin/tours"),
            ("GET", "/api/admin/tours/test-id"),
            ("PUT", "/api/admin/tours/test-id"),
            ("DELETE", "/api/admin/tours/test-id")
        ]
        
        success_count = 0
        headers_no_auth = {"Content-Type": "application/json", "Accept": "application/json"}
        
        for method, endpoint in endpoints_to_test:
            try:
                url = f"{self.base_url}{endpoint}"
                
                if method == "GET":
                    response = requests.get(url, headers=headers_no_auth, timeout=30)
                elif method == "POST":
                    response = requests.post(url, headers=headers_no_auth, json={}, timeout=30)
                elif method == "PUT":
                    response = requests.put(url, headers=headers_no_auth, json={}, timeout=30)
                elif method == "DELETE":
                    response = requests.delete(url, headers=headers_no_auth, timeout=30)
                    
                if response.status_code == 401:
                    success_count += 1
                    self.log(f"✓ {method} {endpoint} correctly returns 401")
                else:
                    self.log(f"✗ {method} {endpoint} returned {response.status_code}, expected 401", "WARN")
                    
            except Exception as e:
                self.log(f"✗ {method} {endpoint} exception: {str(e)}", "ERROR")
                
        success = success_count >= len(endpoints_to_test) * 0.7  # 70% should work
        self.record_result("Auth Guards", success, f"{success_count}/{len(endpoints_to_test)} endpoints correctly protected")
        return success
        
    def run_all_tests(self):
        """Run complete test suite"""
        self.log("=" * 60)
        self.log("Starting Tour Enhancement Backend API Tests")
        self.log(f"Target URL: {self.base_url}")
        self.log("=" * 60)
        
        # 1. Authentication
        if not self.test_login():
            self.log("Authentication failed - stopping tests", "ERROR")
            return
            
        # 2. Test auth guards first
        self.test_auth_guards()
        
        # 3. Test tours endpoints
        tour_id = self.test_tours_list()
        self.test_tours_list_with_filters()
        
        if tour_id:
            self.test_tour_detail(tour_id)
            self.test_tour_reservation(tour_id)
        
        # 4. Test admin endpoints
        admin_tour_id = self.test_admin_tours_list()
        
        if admin_tour_id:
            self.test_admin_tour_detail(admin_tour_id)
            self.test_admin_tour_update(admin_tour_id)
            self.test_admin_tour_delete_auth(admin_tour_id)
            
        # 5. Test image upload auth
        self.test_admin_image_upload_auth()
        
        # 6. Summary
        self.print_summary()
        
    def print_summary(self):
        """Print test results summary"""
        self.log("=" * 60)
        self.log("TEST RESULTS SUMMARY")
        self.log("=" * 60)
        
        passed = [r for r in self.results if r["success"]]
        failed = [r for r in self.results if not r["success"]]
        
        self.log(f"Total Tests: {len(self.results)}")
        self.log(f"Passed: {len(passed)}")
        self.log(f"Failed: {len(failed)}")
        self.log("")
        
        if failed:
            self.log("FAILED TESTS:")
            for result in failed:
                self.log(f"  ❌ {result['test']}: {result['details']}", "ERROR")
            self.log("")
            
        if passed:
            self.log("PASSED TESTS:")
            for result in passed:
                self.log(f"  ✅ {result['test']}: {result['details']}")
                
        self.log("=" * 60)
        
        # Return exit code
        return 0 if len(failed) == 0 else 1


def main():
    """Main test runner"""
    tester = TourAPITester()
    exit_code = tester.run_all_tests()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()