#!/usr/bin/env python3
"""
Syroce Backend Critical Regression Validation
Turkish Review Request: Auth, RBAC, Public endpoints validation
Base URL: https://syroce-preview-1.preview.emergentagent.com
"""

import requests
import json
import sys
from typing import Dict, Any, Optional

# Base configuration
BASE_URL = "https://syroce-preview-1.preview.emergentagent.com"
API_BASE = f"{BASE_URL}/api"

# Test credentials from Turkish review request
ADMIN_CREDENTIALS = {
    "email": "admin@acenta.test",
    "password": "admin123"
}

AGENCY_CREDENTIALS = {
    "email": "agent@acenta.test", 
    "password": "agent123"
}

class BackendTester:
    def __init__(self):
        self.admin_token = None
        self.agency_token = None
        self.admin_cookies = None
        self.agency_cookies = None
        self.results = []
        
    def log_result(self, test_name: str, status: str, details: Dict[str, Any]):
        """Log test result with structured data"""
        result = {
            "test": test_name,
            "status": status,  # PASS, FAIL, SKIP
            "details": details
        }
        self.results.append(result)
        status_symbol = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{status_symbol} {test_name}: {status}")
        if status == "FAIL":
            print(f"   Error: {details.get('error', 'Unknown error')}")
            
    def make_request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Make HTTP request with error handling"""
        try:
            response = requests.request(method, url, timeout=15, **kwargs)
            return response
        except Exception as e:
            raise Exception(f"Request failed: {str(e)}")
    
    def test_admin_login(self) -> bool:
        """Test 1: Admin login (admin@acenta.test/admin123)"""
        try:
            url = f"{API_BASE}/auth/login"
            headers = {"Content-Type": "application/json"}
            
            response = self.make_request("POST", url, json=ADMIN_CREDENTIALS, headers=headers)
            
            if response.status_code != 200:
                self.log_result("Admin Login", "FAIL", {
                    "error": f"HTTP {response.status_code}",
                    "response": response.text[:500]
                })
                return False
                
            data = response.json()
            
            # Check for access token
            if "access_token" not in data:
                self.log_result("Admin Login", "FAIL", {
                    "error": "No access_token in response",
                    "response_keys": list(data.keys())
                })
                return False
                
            # Check for super_admin role
            user_roles = data.get("user", {}).get("roles", [])
            if "super_admin" not in user_roles:
                self.log_result("Admin Login", "FAIL", {
                    "error": f"Expected super_admin role, got: {user_roles}",
                    "user_data": data.get("user", {})
                })
                return False
                
            self.admin_token = data["access_token"]
            
            self.log_result("Admin Login", "PASS", {
                "token_length": len(self.admin_token),
                "roles": user_roles,
                "user_email": data.get("user", {}).get("email")
            })
            return True
            
        except Exception as e:
            self.log_result("Admin Login", "FAIL", {"error": str(e)})
            return False
    
    def test_agency_login(self) -> bool:
        """Test 2: Agency login (agent@acenta.test/agent123)"""
        try:
            url = f"{API_BASE}/auth/login"
            headers = {"Content-Type": "application/json"}
            
            response = self.make_request("POST", url, json=AGENCY_CREDENTIALS, headers=headers)
            
            if response.status_code != 200:
                self.log_result("Agency Login", "FAIL", {
                    "error": f"HTTP {response.status_code}",
                    "response": response.text[:500]
                })
                return False
                
            data = response.json()
            
            # Check for access token
            if "access_token" not in data:
                self.log_result("Agency Login", "FAIL", {
                    "error": "No access_token in response",
                    "response_keys": list(data.keys())
                })
                return False
                
            # Check for agency_admin role
            user_roles = data.get("user", {}).get("roles", [])
            if "agency_admin" not in user_roles:
                self.log_result("Agency Login", "FAIL", {
                    "error": f"Expected agency_admin role, got: {user_roles}",
                    "user_data": data.get("user", {})
                })
                return False
                
            self.agency_token = data["access_token"]
            
            self.log_result("Agency Login", "PASS", {
                "token_length": len(self.agency_token),
                "roles": user_roles,
                "user_email": data.get("user", {}).get("email")
            })
            return True
            
        except Exception as e:
            self.log_result("Agency Login", "FAIL", {"error": str(e)})
            return False
    
    def test_admin_auth_me(self) -> bool:
        """Test 3: GET /api/auth/me with admin token"""
        if not self.admin_token:
            self.log_result("Admin Auth/Me", "SKIP", {"error": "No admin token available"})
            return False
            
        try:
            url = f"{API_BASE}/auth/me"
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            
            response = self.make_request("GET", url, headers=headers)
            
            if response.status_code != 200:
                self.log_result("Admin Auth/Me", "FAIL", {
                    "error": f"HTTP {response.status_code}",
                    "response": response.text[:500]
                })
                return False
                
            data = response.json()
            
            # Check for super_admin role
            user_roles = data.get("roles", [])
            if "super_admin" not in user_roles:
                self.log_result("Admin Auth/Me", "FAIL", {
                    "error": f"Expected super_admin role, got: {user_roles}",
                    "user_data": data
                })
                return False
                
            # Check for tenant_id
            if not data.get("tenant_id"):
                self.log_result("Admin Auth/Me", "FAIL", {
                    "error": "No tenant_id in response",
                    "user_data": data
                })
                return False
                
            self.log_result("Admin Auth/Me", "PASS", {
                "roles": user_roles,
                "email": data.get("email"),
                "tenant_id": data.get("tenant_id"),
                "organization_id": data.get("organization_id")
            })
            return True
            
        except Exception as e:
            self.log_result("Admin Auth/Me", "FAIL", {"error": str(e)})
            return False
    
    def test_agency_auth_me(self) -> bool:
        """Test 4: GET /api/auth/me with agency token"""
        if not self.agency_token:
            self.log_result("Agency Auth/Me", "SKIP", {"error": "No agency token available"})
            return False
            
        try:
            url = f"{API_BASE}/auth/me"
            headers = {"Authorization": f"Bearer {self.agency_token}"}
            
            response = self.make_request("GET", url, headers=headers)
            
            if response.status_code != 200:
                self.log_result("Agency Auth/Me", "FAIL", {
                    "error": f"HTTP {response.status_code}",
                    "response": response.text[:500]
                })
                return False
                
            data = response.json()
            
            # Check for agency_admin role
            user_roles = data.get("roles", [])
            if "agency_admin" not in user_roles:
                self.log_result("Agency Auth/Me", "FAIL", {
                    "error": f"Expected agency_admin role, got: {user_roles}",
                    "user_data": data
                })
                return False
                
            # Check for tenant_id
            if not data.get("tenant_id"):
                self.log_result("Agency Auth/Me", "FAIL", {
                    "error": "No tenant_id in response",
                    "user_data": data
                })
                return False
                
            self.log_result("Agency Auth/Me", "PASS", {
                "roles": user_roles,
                "email": data.get("email"),
                "tenant_id": data.get("tenant_id"),
                "organization_id": data.get("organization_id")
            })
            return True
            
        except Exception as e:
            self.log_result("Agency Auth/Me", "FAIL", {"error": str(e)})
            return False
    
    def test_public_theme(self) -> bool:
        """Test 5: GET /api/public/theme (public endpoint)"""
        try:
            url = f"{API_BASE}/public/theme"
            
            response = self.make_request("GET", url)
            
            if response.status_code != 200:
                self.log_result("Public Theme", "FAIL", {
                    "error": f"HTTP {response.status_code}",
                    "response": response.text[:500]
                })
                return False
                
            data = response.json()
            
            # Check for expected theme structure
            required_keys = ["brand", "colors", "typography"]
            missing_keys = [key for key in required_keys if key not in data]
            
            if missing_keys:
                self.log_result("Public Theme", "FAIL", {
                    "error": f"Missing required keys: {missing_keys}",
                    "response_keys": list(data.keys())
                })
                return False
                
            self.log_result("Public Theme", "PASS", {
                "company_name": data.get("brand", {}).get("company_name"),
                "primary_color": data.get("colors", {}).get("primary"),
                "response_size": len(json.dumps(data))
            })
            return True
            
        except Exception as e:
            self.log_result("Public Theme", "FAIL", {"error": str(e)})
            return False
    
    def test_onboarding_plans(self) -> bool:
        """Test 6: GET /api/onboarding/plans (supporting endpoint)"""
        try:
            url = f"{API_BASE}/onboarding/plans"
            
            response = self.make_request("GET", url)
            
            if response.status_code != 200:
                self.log_result("Onboarding Plans", "FAIL", {
                    "error": f"HTTP {response.status_code}",
                    "response": response.text[:500]
                })
                return False
                
            data = response.json()
            
            # Check for plans structure
            if "plans" not in data:
                self.log_result("Onboarding Plans", "FAIL", {
                    "error": "No 'plans' key in response",
                    "response_keys": list(data.keys())
                })
                return False
                
            plans = data["plans"]
            if not isinstance(plans, list):
                self.log_result("Onboarding Plans", "FAIL", {
                    "error": f"Plans is not a list, got: {type(plans)}",
                    "plans_value": plans
                })
                return False
                
            self.log_result("Onboarding Plans", "PASS", {
                "plans_count": len(plans),
                "response_size": len(json.dumps(data))
            })
            return True
            
        except Exception as e:
            self.log_result("Onboarding Plans", "FAIL", {"error": str(e)})
            return False
    
    def test_admin_endpoint_access(self) -> bool:
        """Test 7: Admin endpoint access with admin token"""
        if not self.admin_token:
            self.log_result("Admin Endpoint Access", "SKIP", {"error": "No admin token available"})
            return False
            
        try:
            # Try a lightweight admin endpoint
            url = f"{API_BASE}/admin/agencies"
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            
            response = self.make_request("GET", url, headers=headers)
            
            if response.status_code != 200:
                self.log_result("Admin Endpoint Access", "FAIL", {
                    "error": f"HTTP {response.status_code}",
                    "response": response.text[:500],
                    "endpoint": "/admin/agencies"
                })
                return False
                
            data = response.json()
            
            self.log_result("Admin Endpoint Access", "PASS", {
                "endpoint": "/admin/agencies",
                "response_type": type(data).__name__,
                "response_size": len(json.dumps(data)) if isinstance(data, (dict, list)) else len(str(data))
            })
            return True
            
        except Exception as e:
            self.log_result("Admin Endpoint Access", "FAIL", {"error": str(e)})
            return False
    
    def test_agency_context_endpoint(self) -> bool:
        """Test 8: Agency context endpoint with agency token"""
        if not self.agency_token:
            self.log_result("Agency Context Endpoint", "SKIP", {"error": "No agency token available"})
            return False
            
        try:
            # Try agency profile or reports endpoint
            url = f"{API_BASE}/agency/profile"
            headers = {"Authorization": f"Bearer {self.agency_token}"}
            
            response = self.make_request("GET", url, headers=headers)
            
            # Agency profile might return 404 if not set up, that's acceptable
            if response.status_code in [200, 404]:
                self.log_result("Agency Context Endpoint", "PASS", {
                    "endpoint": "/agency/profile",
                    "status_code": response.status_code,
                    "response_size": len(response.text)
                })
                return True
            else:
                self.log_result("Agency Context Endpoint", "FAIL", {
                    "error": f"HTTP {response.status_code}",
                    "response": response.text[:500],
                    "endpoint": "/agency/profile"
                })
                return False
            
        except Exception as e:
            self.log_result("Agency Context Endpoint", "FAIL", {"error": str(e)})
            return False
    
    def run_all_tests(self):
        """Run all regression tests"""
        print("=== SYROCE BACKEND CRITICAL REGRESSION VALIDATION ===")
        print(f"Base URL: {BASE_URL}")
        print(f"API Base: {API_BASE}")
        print()
        
        # Auth tests (critical)
        print("--- AUTH TESTS ---")
        admin_login_ok = self.test_admin_login()
        agency_login_ok = self.test_agency_login()
        admin_me_ok = self.test_admin_auth_me()
        agency_me_ok = self.test_agency_auth_me()
        
        # Public/supporting endpoints
        print("\n--- PUBLIC/SUPPORTING ENDPOINTS ---")
        public_theme_ok = self.test_public_theme()
        onboarding_plans_ok = self.test_onboarding_plans()
        
        # Role-based access tests
        print("\n--- ROLE-BASED ACCESS TESTS ---")
        admin_access_ok = self.test_admin_endpoint_access()
        agency_context_ok = self.test_agency_context_endpoint()
        
        # Summary
        print(f"\n=== TEST SUMMARY ===")
        total_tests = len(self.results)
        passed_tests = len([r for r in self.results if r["status"] == "PASS"])
        failed_tests = len([r for r in self.results if r["status"] == "FAIL"])
        skipped_tests = len([r for r in self.results if r["status"] == "SKIP"])
        
        print(f"Total: {total_tests}, Passed: {passed_tests}, Failed: {failed_tests}, Skipped: {skipped_tests}")
        
        # Critical failures analysis
        critical_failures = []
        if not admin_login_ok:
            critical_failures.append("Admin login failed")
        if not agency_login_ok:
            critical_failures.append("Agency login failed")
        if not admin_me_ok:
            critical_failures.append("Admin auth/me failed")  
        if not agency_me_ok:
            critical_failures.append("Agency auth/me failed")
            
        if critical_failures:
            print(f"\n❌ CRITICAL FAILURES DETECTED:")
            for failure in critical_failures:
                print(f"   - {failure}")
            return False
        else:
            print(f"\n✅ ALL CRITICAL TESTS PASSED")
            if failed_tests > 0:
                print(f"⚠️  {failed_tests} non-critical tests failed")
            return True

def main():
    tester = BackendTester()
    success = tester.run_all_tests()
    
    # Write detailed results to file for analysis
    results_file = "/app/backend_test_results.json"
    with open(results_file, "w") as f:
        json.dump({
            "timestamp": str(datetime.now().isoformat()),
            "base_url": BASE_URL,
            "total_tests": len(tester.results),
            "results": tester.results
        }, f, indent=2)
    
    print(f"\nDetailed results written to: {results_file}")
    
    # Exit code for CI/automation
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    from datetime import datetime
    main()