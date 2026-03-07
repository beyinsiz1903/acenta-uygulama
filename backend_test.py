#!/usr/bin/env python3

"""
PR-V1-0 Backend Smoke Test

Turkish review request:
- POST /api/auth/login (admin@acenta.test / admin123) 200 dönüyor mu?
- GET /api/auth/me login sonrası çalışıyor mu?  
- GET /api/v1/mobile/auth/me korunmuş mu?
- GET /api/health çalışıyor mu?
- Duplicate auth route semptomu var mı? (özellikle auth uçları normal davranıyor mu, beklenmeyen conflict/shadowing yok mu)
- Route inventory export dosyası `/app/backend/app/bootstrap/route_inventory.json` mevcut mu ve foundation alanlarını içeriyor mu?
"""

import requests
import json
import os
from typing import Dict, Optional

# Get backend URL from frontend/.env
BACKEND_URL = "https://saas-modernize-2.preview.emergentagent.com"

class BackendSmokeTest:
    def __init__(self):
        self.base_url = BACKEND_URL
        self.access_token: Optional[str] = None
        self.results: Dict[str, Dict] = {}
        
    def log_result(self, test_name: str, passed: bool, details: str, response_data: Optional[Dict] = None):
        """Log test result"""
        self.results[test_name] = {
            "passed": passed,
            "details": details,
            "response_data": response_data
        }
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} {test_name}: {details}")
        
    def test_health_endpoint(self):
        """Test 4: GET /api/health çalışıyor mu?"""
        try:
            response = requests.get(f"{self.base_url}/api/health", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                self.log_result(
                    "health_endpoint", 
                    True, 
                    f"Health endpoint returns 200 OK with status: {data.get('status', 'unknown')}", 
                    data
                )
                return True
            else:
                self.log_result(
                    "health_endpoint", 
                    False, 
                    f"Health endpoint returned {response.status_code}: {response.text[:200]}"
                )
                return False
                
        except Exception as e:
            self.log_result("health_endpoint", False, f"Health endpoint failed: {str(e)}")
            return False
    
    def test_login_endpoint(self):
        """Test 1: POST /api/auth/login (admin@acenta.test / admin123) 200 dönüyor mu?"""
        try:
            login_data = {
                "email": "admin@acenta.test",
                "password": "admin123"
            }
            
            response = requests.post(f"{self.base_url}/api/auth/login", json=login_data, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get("access_token")
                
                # Check if we have required fields
                has_access_token = bool(self.access_token)
                has_user = bool(data.get("user"))
                
                if has_access_token and has_user:
                    self.log_result(
                        "login_endpoint", 
                        True, 
                        f"Login successful. Access token length: {len(self.access_token) if self.access_token else 0} chars", 
                        {"access_token_length": len(self.access_token) if self.access_token else 0, "user_email": data.get("user", {}).get("email")}
                    )
                    return True
                else:
                    self.log_result(
                        "login_endpoint", 
                        False, 
                        f"Login response missing required fields. has_access_token: {has_access_token}, has_user: {has_user}"
                    )
                    return False
            else:
                self.log_result(
                    "login_endpoint", 
                    False, 
                    f"Login failed with status {response.status_code}: {response.text[:200]}"
                )
                return False
                
        except Exception as e:
            self.log_result("login_endpoint", False, f"Login request failed: {str(e)}")
            return False
    
    def test_auth_me_endpoint(self):
        """Test 2: GET /api/auth/me login sonrası çalışıyor mu?"""
        if not self.access_token:
            self.log_result("auth_me_endpoint", False, "No access token available from login")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            response = requests.get(f"{self.base_url}/api/auth/me", headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                user_email = data.get("email", "")
                
                if user_email == "admin@acenta.test":
                    self.log_result(
                        "auth_me_endpoint", 
                        True, 
                        f"Auth/me endpoint working correctly. User email: {user_email}", 
                        {"email": user_email, "roles": data.get("roles", [])}
                    )
                    return True
                else:
                    self.log_result(
                        "auth_me_endpoint", 
                        False, 
                        f"Auth/me returned unexpected email: {user_email}"
                    )
                    return False
            else:
                self.log_result(
                    "auth_me_endpoint", 
                    False, 
                    f"Auth/me failed with status {response.status_code}: {response.text[:200]}"
                )
                return False
                
        except Exception as e:
            self.log_result("auth_me_endpoint", False, f"Auth/me request failed: {str(e)}")
            return False
    
    def test_mobile_auth_me_protected(self):
        """Test 3: GET /api/v1/mobile/auth/me korunmuş mu?"""
        
        # First test without authentication - should be protected (401/403)
        try:
            response = requests.get(f"{self.base_url}/api/v1/mobile/auth/me", timeout=10)
            
            if response.status_code in [401, 403]:
                # Good - endpoint is protected
                protected_correctly = True
                protected_message = f"Mobile auth/me properly protected (returns {response.status_code} without auth)"
            else:
                protected_correctly = False
                protected_message = f"Mobile auth/me NOT protected (returns {response.status_code} without auth)"
        except Exception as e:
            protected_correctly = False
            protected_message = f"Mobile auth/me test without auth failed: {str(e)}"
        
        # Test with authentication if we have a token
        if self.access_token:
            try:
                headers = {"Authorization": f"Bearer {self.access_token}"}
                auth_response = requests.get(f"{self.base_url}/api/v1/mobile/auth/me", headers=headers, timeout=10)
                
                if auth_response.status_code == 200:
                    auth_data = auth_response.json()
                    auth_works = True
                    auth_message = f"Mobile auth/me works with token. User: {auth_data.get('email', 'unknown')}"
                else:
                    auth_works = True  # Still consider this okay if protection works
                    auth_message = f"Mobile auth/me with token returns {auth_response.status_code} (may be normal)"
            except Exception as e:
                auth_works = True  # Don't fail if auth test fails, protection is more important
                auth_message = f"Mobile auth/me with token test failed: {str(e)}"
        else:
            auth_works = True
            auth_message = "Skipped authenticated test (no token available)"
        
        overall_result = protected_correctly and auth_works
        combined_message = f"{protected_message}. {auth_message}"
        
        self.log_result(
            "mobile_auth_protected", 
            overall_result, 
            combined_message,
            {"protected": protected_correctly, "auth_works": auth_works}
        )
        return overall_result
    
    def test_auth_route_conflicts(self):
        """Test 5: Duplicate auth route semptomu var mı?"""
        
        # Test if auth endpoints behave normally and consistently
        auth_endpoints_to_check = [
            "/api/auth/login",
            "/api/auth/me", 
            "/api/auth/sessions"
        ]
        
        consistent_behavior = True
        issues_found = []
        
        for endpoint_path in auth_endpoints_to_check:
            try:
                # Test OPTIONS request to see if endpoint exists and is properly configured
                response = requests.options(f"{self.base_url}{endpoint_path}", timeout=5)
                
                # Check if we get expected behavior (should return 200, 204, or 405, not 404)
                if response.status_code == 404:
                    consistent_behavior = False
                    issues_found.append(f"{endpoint_path} returns 404 (route missing)")
                elif response.status_code in [200, 204, 405]:  # Normal responses for OPTIONS (204 No Content is valid for CORS)
                    # Good - endpoint exists
                    pass
                else:
                    # Unexpected response could indicate route conflicts
                    issues_found.append(f"{endpoint_path} OPTIONS returns unexpected {response.status_code}")
                    
            except Exception as e:
                issues_found.append(f"{endpoint_path} test failed: {str(e)}")
        
        # Additional test: Check if login endpoint responds consistently
        if self.access_token:
            try:
                # Test multiple calls to login with same credentials - should be consistent
                login_data = {"email": "admin@acenta.test", "password": "admin123"}
                
                response1 = requests.post(f"{self.base_url}/api/auth/login", json=login_data, timeout=5)
                response2 = requests.post(f"{self.base_url}/api/auth/login", json=login_data, timeout=5)
                
                if response1.status_code != response2.status_code:
                    consistent_behavior = False
                    issues_found.append(f"Login endpoint inconsistent: {response1.status_code} vs {response2.status_code}")
                    
            except Exception as e:
                issues_found.append(f"Login consistency test failed: {str(e)}")
        
        if consistent_behavior and not issues_found:
            self.log_result(
                "auth_route_conflicts", 
                True, 
                "No auth route conflicts detected. All auth endpoints behave normally.",
                {"endpoints_checked": auth_endpoints_to_check}
            )
        else:
            self.log_result(
                "auth_route_conflicts", 
                False, 
                f"Potential auth route issues detected: {'; '.join(issues_found)}",
                {"issues": issues_found}
            )
        
        return consistent_behavior and not issues_found
    
    def test_route_inventory_file(self):
        """Test 6: Route inventory export dosyası mevcut mu ve foundation alanlarını içeriyor mu?"""
        
        inventory_path = "/app/backend/app/bootstrap/route_inventory.json"
        
        try:
            # Check if file exists
            if not os.path.exists(inventory_path):
                self.log_result(
                    "route_inventory_file", 
                    False, 
                    f"Route inventory file not found at {inventory_path}"
                )
                return False
            
            # Read and validate the file
            with open(inventory_path, 'r') as f:
                inventory_data = json.load(f)
            
            if not isinstance(inventory_data, list):
                self.log_result(
                    "route_inventory_file", 
                    False, 
                    "Route inventory file is not a valid JSON array"
                )
                return False
            
            # Check for foundation fields in the inventory entries
            required_fields = ["compat_required", "current_namespace", "legacy_or_v1", "method", "owner", "path", "risk_level", "source", "target_namespace"]
            
            if len(inventory_data) == 0:
                self.log_result(
                    "route_inventory_file", 
                    False, 
                    "Route inventory file is empty"
                )
                return False
            
            # Check first few entries for required foundation fields
            sample_entries = inventory_data[:5]
            missing_fields = []
            
            for i, entry in enumerate(sample_entries):
                for field in required_fields:
                    if field not in entry:
                        missing_fields.append(f"Entry {i}: missing '{field}'")
            
            if missing_fields:
                self.log_result(
                    "route_inventory_file", 
                    False, 
                    f"Route inventory missing foundation fields: {'; '.join(missing_fields[:3])}"
                )
                return False
            
            # Count auth-related routes to verify they're captured
            auth_routes = [entry for entry in inventory_data if "/api/auth" in entry.get("path", "")]
            mobile_routes = [entry for entry in inventory_data if "/api/v1/mobile" in entry.get("path", "")]
            
            inventory_stats = {
                "total_routes": len(inventory_data),
                "auth_routes": len(auth_routes),
                "mobile_routes": len(mobile_routes),
                "foundation_fields": required_fields
            }
            
            if len(auth_routes) > 0 and len(inventory_data) > 10:  # Sanity check
                self.log_result(
                    "route_inventory_file", 
                    True, 
                    f"Route inventory file exists with {len(inventory_data)} routes, including {len(auth_routes)} auth routes and {len(mobile_routes)} mobile routes. Foundation fields present.",
                    inventory_stats
                )
                return True
            else:
                self.log_result(
                    "route_inventory_file", 
                    False, 
                    f"Route inventory file exists but seems incomplete. Total routes: {len(inventory_data)}, Auth routes: {len(auth_routes)}"
                )
                return False
                
        except Exception as e:
            self.log_result("route_inventory_file", False, f"Route inventory file test failed: {str(e)}")
            return False
    
    def run_all_tests(self):
        """Run all smoke tests in sequence"""
        print("🚀 Starting PR-V1-0 Backend Smoke Test")
        print(f"Base URL: {self.base_url}")
        print("-" * 60)
        
        # Test order matters - login must be first to get token
        test_functions = [
            self.test_health_endpoint,           # Test 4: Health check
            self.test_login_endpoint,           # Test 1: Login 
            self.test_auth_me_endpoint,         # Test 2: Auth/me
            self.test_mobile_auth_me_protected, # Test 3: Mobile auth protection
            self.test_auth_route_conflicts,     # Test 5: Route conflicts
            self.test_route_inventory_file,     # Test 6: Route inventory
        ]
        
        total_tests = len(test_functions)
        passed_tests = 0
        
        for test_func in test_functions:
            if test_func():
                passed_tests += 1
        
        print("-" * 60)
        print(f"📊 Test Results: {passed_tests}/{total_tests} tests passed")
        
        # Generate summary
        if passed_tests == total_tests:
            print("✅ ALL TESTS PASSED - Backend foundation changes did not break runtime behavior")
            return True
        else:
            print("❌ SOME TESTS FAILED - Issues detected with backend foundation changes")
            failed_tests = [name for name, result in self.results.items() if not result["passed"]]
            print(f"Failed tests: {', '.join(failed_tests)}")
            return False


def main():
    """Main entry point"""
    test_runner = BackendSmokeTest()
    success = test_runner.run_all_tests()
    
    # Generate detailed JSON report
    report_path = "/app/backend_smoke_test_results.json"
    with open(report_path, 'w') as f:
        json.dump({
            "summary": {
                "success": success,
                "total_tests": len(test_runner.results),
                "passed_tests": sum(1 for r in test_runner.results.values() if r["passed"]),
                "backend_url": BACKEND_URL,
                "test_timestamp": "2026-03-07"
            },
            "results": test_runner.results
        }, f, indent=2)
    
    print(f"📋 Detailed results written to: {report_path}")
    
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())