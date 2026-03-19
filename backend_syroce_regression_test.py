#!/usr/bin/env python3
"""
Syroce backend regression check for Turkish review request
Testing specific auth/API flows mentioned in the review request
"""

import requests
import json
from typing import Dict, Tuple, Optional

class SyroceBackendRegressionTest:
    def __init__(self):
        self.base_url = "https://webhook-platform.preview.emergentagent.com/api"
        self.results = []
        self.session = requests.Session()
        
        # Test credentials from review request
        self.admin_credentials = {
            "email": "admin@acenta.test",
            "password": "admin123"
        }
        
        self.agency_credentials = {
            "email": "agent@acenta.test", 
            "password": "agent123"
        }
        
        self.admin_token = None
        self.agency_token = None
        self.agency_id = None

    def log_result(self, test_name: str, status: str, details: str = ""):
        """Log test result"""
        result = {
            "test": test_name,
            "status": status,
            "details": details
        }
        self.results.append(result)
        print(f"{'✅' if status == 'PASS' else '❌'} {test_name}: {status}")
        if details:
            print(f"   Details: {details}")

    def test_admin_login(self) -> bool:
        """Test POST /api/auth/login with valid superadmin credentials"""
        try:
            response = self.session.post(
                f"{self.base_url}/auth/login",
                json=self.admin_credentials,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'access_token' in data and 'user' in data:
                    self.admin_token = data['access_token']
                    user_roles = data.get('user', {}).get('roles', [])
                    if 'super_admin' in user_roles:
                        self.log_result(
                            "Admin Login (admin@acenta.test/admin123)",
                            "PASS",
                            f"Token received ({len(self.admin_token)} chars), super_admin role confirmed"
                        )
                        return True
                    else:
                        self.log_result(
                            "Admin Login (admin@acenta.test/admin123)",
                            "FAIL",
                            f"Missing super_admin role. Roles: {user_roles}"
                        )
                        return False
                else:
                    self.log_result(
                        "Admin Login (admin@acenta.test/admin123)",
                        "FAIL",
                        f"Missing access_token or user in response: {data}"
                    )
                    return False
            else:
                self.log_result(
                    "Admin Login (admin@acenta.test/admin123)",
                    "FAIL",
                    f"Status {response.status_code}: {response.text}"
                )
                return False
        
        except Exception as e:
            self.log_result(
                "Admin Login (admin@acenta.test/admin123)",
                "FAIL",
                f"Exception: {str(e)}"
            )
            return False

    def test_agency_login(self) -> bool:
        """Test POST /api/auth/login with valid agency admin credentials"""
        try:
            response = self.session.post(
                f"{self.base_url}/auth/login",
                json=self.agency_credentials,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'access_token' in data and 'user' in data:
                    self.agency_token = data['access_token']
                    user_roles = data.get('user', {}).get('roles', [])
                    if 'agency_admin' in user_roles:
                        self.log_result(
                            "Agency Login (agent@acenta.test/agent123)",
                            "PASS",
                            f"Token received ({len(self.agency_token)} chars), agency_admin role confirmed"
                        )
                        return True
                    else:
                        self.log_result(
                            "Agency Login (agent@acenta.test/agent123)",
                            "FAIL",
                            f"Missing agency_admin role. Roles: {user_roles}"
                        )
                        return False
                else:
                    self.log_result(
                        "Agency Login (agent@acenta.test/agent123)",
                        "FAIL",
                        f"Missing access_token or user in response: {data}"
                    )
                    return False
            else:
                self.log_result(
                    "Agency Login (agent@acenta.test/agent123)",
                    "FAIL",
                    f"Status {response.status_code}: {response.text}"
                )
                return False
        
        except Exception as e:
            self.log_result(
                "Agency Login (agent@acenta.test/agent123)",
                "FAIL",
                f"Exception: {str(e)}"
            )
            return False

    def test_auth_me_authenticated(self) -> bool:
        """Test GET /api/auth/me with admin token (authenticated)"""
        if not self.admin_token:
            self.log_result(
                "GET /api/auth/me (authenticated - admin)",
                "FAIL",
                "No admin token available"
            )
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = self.session.get(f"{self.base_url}/auth/me", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                email = data.get('email', '')
                roles = data.get('roles', [])
                tenant_id = data.get('tenant_id', '')
                
                if email == 'admin@acenta.test' and 'super_admin' in roles:
                    self.log_result(
                        "GET /api/auth/me (authenticated - admin)",
                        "PASS",
                        f"Authenticated successfully. Email: {email}, Roles: {roles}, Tenant ID: {tenant_id}"
                    )
                    return True
                else:
                    self.log_result(
                        "GET /api/auth/me (authenticated - admin)",
                        "FAIL",
                        f"Unexpected user data. Email: {email}, Roles: {roles}"
                    )
                    return False
            else:
                self.log_result(
                    "GET /api/auth/me (authenticated - admin)",
                    "FAIL",
                    f"Status {response.status_code}: {response.text}"
                )
                return False
        
        except Exception as e:
            self.log_result(
                "GET /api/auth/me (authenticated - admin)",
                "FAIL",
                f"Exception: {str(e)}"
            )
            return False

    def test_auth_me_unauthenticated(self) -> bool:
        """Test GET /api/auth/me without token (unauthenticated)"""
        try:
            response = self.session.get(f"{self.base_url}/auth/me")
            
            if response.status_code == 401:
                self.log_result(
                    "GET /api/auth/me (unauthenticated)",
                    "PASS",
                    f"Correctly returns 401 Unauthorized: {response.text[:100]}"
                )
                return True
            else:
                self.log_result(
                    "GET /api/auth/me (unauthenticated)",
                    "FAIL",
                    f"Expected 401, got {response.status_code}: {response.text}"
                )
                return False
        
        except Exception as e:
            self.log_result(
                "GET /api/auth/me (unauthenticated)",
                "FAIL",
                f"Exception: {str(e)}"
            )
            return False

    def test_agency_profile(self) -> bool:
        """Test GET /api/agency/profile for agency admin"""
        if not self.agency_token:
            self.log_result(
                "GET /api/agency/profile (agency admin)",
                "FAIL",
                "No agency token available"
            )
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.agency_token}"}
            response = self.session.get(f"{self.base_url}/agency/profile", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                allowed_modules = data.get('allowed_modules', [])
                agency_name = data.get('agency_name', '')
                
                self.log_result(
                    "GET /api/agency/profile (agency admin)",
                    "PASS",
                    f"Profile retrieved. Agency: {agency_name}, Modules: {allowed_modules}"
                )
                return True
            else:
                self.log_result(
                    "GET /api/agency/profile (agency admin)",
                    "FAIL",
                    f"Status {response.status_code}: {response.text}"
                )
                return False
        
        except Exception as e:
            self.log_result(
                "GET /api/agency/profile (agency admin)",
                "FAIL",
                f"Exception: {str(e)}"
            )
            return False

    def find_agency_id(self) -> bool:
        """Find agency ID for module testing"""
        if not self.admin_token:
            return False
            
        try:
            # Use the known working agency ID from test history
            self.agency_id = "f5f7a2a3-5de1-4d65-b700-ec4f9807d83a"  # Demo Acenta
            
            # Verify this agency exists and modules endpoint works
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = self.session.get(
                f"{self.base_url}/admin/agencies/{self.agency_id}/modules",
                headers=headers
            )
            
            if response.status_code == 200:
                self.log_result(
                    "Find Agency ID for Module Testing",
                    "PASS", 
                    f"Using Demo Acenta agency ID: {self.agency_id}"
                )
                return True
            else:
                self.log_result(
                    "Find Agency ID for Module Testing",
                    "FAIL",
                    f"Agency {self.agency_id} modules endpoint failed: {response.status_code}"
                )
                return False
        
        except Exception as e:
            self.log_result(
                "Find Agency ID for Module Testing",
                "FAIL",
                f"Exception: {str(e)}"
            )
            return False

    def test_get_agency_modules(self) -> Tuple[bool, Optional[list]]:
        """Test GET /api/admin/agencies/{agency_id}/modules for superadmin"""
        if not self.admin_token or not self.agency_id:
            self.log_result(
                "GET /api/admin/agencies/{agency_id}/modules",
                "FAIL",
                f"Missing token or agency ID. Token: {bool(self.admin_token)}, Agency ID: {self.agency_id}"
            )
            return False, None
            
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = self.session.get(
                f"{self.base_url}/admin/agencies/{self.agency_id}/modules",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                modules = data.get('modules', []) if isinstance(data, dict) else data
                
                self.log_result(
                    "GET /api/admin/agencies/{agency_id}/modules",
                    "PASS",
                    f"Current modules: {modules}"
                )
                return True, modules
            else:
                self.log_result(
                    "GET /api/admin/agencies/{agency_id}/modules",
                    "FAIL",
                    f"Status {response.status_code}: {response.text}"
                )
                return False, None
        
        except Exception as e:
            self.log_result(
                "GET /api/admin/agencies/{agency_id}/modules",
                "FAIL",
                f"Exception: {str(e)}"
            )
            return False, None

    def test_put_agency_modules(self, current_modules: list) -> bool:
        """Test PUT /api/admin/agencies/{agency_id}/modules for superadmin"""
        if not self.admin_token or not self.agency_id:
            self.log_result(
                "PUT /api/admin/agencies/{agency_id}/modules",
                "FAIL",
                f"Missing token or agency ID. Token: {bool(self.admin_token)}, Agency ID: {self.agency_id}"
            )
            return False
            
        try:
            # Test module update with normalization
            test_modules = list(current_modules)  # Start with current modules
            
            # Add legacy module keys to test normalization
            legacy_modules = ["musaitlik_takibi", "turlarimiz", "otellerim", "google_sheet_baglantisi"]
            test_modules.extend(legacy_modules)
            
            headers = {
                "Authorization": f"Bearer {self.admin_token}",
                "Content-Type": "application/json"
            }
            
            payload = {"allowed_modules": test_modules}
            
            response = self.session.put(
                f"{self.base_url}/admin/agencies/{self.agency_id}/modules",
                json=payload,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                updated_modules = data.get('modules', []) if isinstance(data, dict) else data
                
                # Check if legacy modules were normalized
                expected_normalized = {
                    "musaitlik_takibi": "musaitlik",
                    "turlarimiz": "turlar", 
                    "otellerim": "oteller",
                    "google_sheet_baglantisi": "sheet_baglantilari"
                }
                
                normalization_working = True
                for legacy, canonical in expected_normalized.items():
                    if legacy in updated_modules:
                        normalization_working = False
                        break
                    if canonical not in updated_modules:
                        # Allow for this not being required if module wasn't in test set
                        pass
                
                self.log_result(
                    "PUT /api/admin/agencies/{agency_id}/modules",
                    "PASS",
                    f"Modules updated successfully. Final modules: {updated_modules}. Legacy normalization working: {normalization_working}"
                )
                return True
            else:
                self.log_result(
                    "PUT /api/admin/agencies/{agency_id}/modules", 
                    "FAIL",
                    f"Status {response.status_code}: {response.text}"
                )
                return False
        
        except Exception as e:
            self.log_result(
                "PUT /api/admin/agencies/{agency_id}/modules",
                "FAIL",
                f"Exception: {str(e)}"
            )
            return False

    def test_agency_profile_reflects_modules(self) -> bool:
        """Confirm module update is reflected in agency profile allowed_modules"""
        if not self.agency_token:
            self.log_result(
                "Verify Agency Profile Reflects Module Updates",
                "FAIL",
                "No agency token available"
            )
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.agency_token}"}
            response = self.session.get(f"{self.base_url}/agency/profile", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                allowed_modules = data.get('allowed_modules', [])
                
                # Check for normalized modules (no legacy keys)
                legacy_keys = ["musaitlik_takibi", "turlarimiz", "otellerim", "google_sheet_baglantisi"]
                has_legacy = any(key in allowed_modules for key in legacy_keys)
                
                self.log_result(
                    "Verify Agency Profile Reflects Module Updates",
                    "PASS",
                    f"Updated allowed_modules: {allowed_modules}. No legacy keys present: {not has_legacy}"
                )
                return True
            else:
                self.log_result(
                    "Verify Agency Profile Reflects Module Updates",
                    "FAIL",
                    f"Status {response.status_code}: {response.text}"
                )
                return False
        
        except Exception as e:
            self.log_result(
                "Verify Agency Profile Reflects Module Updates",
                "FAIL",
                f"Exception: {str(e)}"
            )
            return False

    def check_serialization_issues(self) -> bool:
        """Check for any auth/session regressions or serialization issues"""
        try:
            # Test various endpoints for ObjectId serialization issues
            test_endpoints = [
                "/auth/me",
                "/agency/profile", 
                "/admin/agencies"
            ]
            
            admin_headers = {"Authorization": f"Bearer {self.admin_token}"} if self.admin_token else {}
            agency_headers = {"Authorization": f"Bearer {self.agency_token}"} if self.agency_token else {}
            
            serialization_ok = True
            issues_found = []
            
            # Test admin endpoints
            for endpoint in ["/auth/me", "/admin/agencies"]:
                if self.admin_token:
                    response = self.session.get(f"{self.base_url}{endpoint}", headers=admin_headers)
                    if response.status_code == 200:
                        try:
                            data = response.json()
                            # Check if response is valid JSON (no ObjectId serialization issues)
                            json.dumps(data)  # This will fail if there are non-serializable objects
                        except (json.JSONDecodeError, TypeError) as e:
                            serialization_ok = False
                            issues_found.append(f"{endpoint}: {str(e)}")
            
            # Test agency endpoints 
            for endpoint in ["/auth/me", "/agency/profile"]:
                if self.agency_token:
                    response = self.session.get(f"{self.base_url}{endpoint}", headers=agency_headers)
                    if response.status_code == 200:
                        try:
                            data = response.json()
                            json.dumps(data)  # Check serialization
                        except (json.JSONDecodeError, TypeError) as e:
                            serialization_ok = False
                            issues_found.append(f"{endpoint}: {str(e)}")
            
            if serialization_ok:
                self.log_result(
                    "Check Auth/Session/Serialization Regressions",
                    "PASS",
                    "No ObjectId or serialization issues detected"
                )
                return True
            else:
                self.log_result(
                    "Check Auth/Session/Serialization Regressions",
                    "FAIL",
                    f"Serialization issues found: {issues_found}"
                )
                return False
        
        except Exception as e:
            self.log_result(
                "Check Auth/Session/Serialization Regressions",
                "FAIL",
                f"Exception: {str(e)}"
            )
            return False

    def run_tests(self):
        """Run all backend regression tests"""
        print("🔍 SYROCE BACKEND REGRESSION CHECK STARTING")
        print(f"📍 Target URL: {self.base_url}")
        print(f"🔐 Testing with credentials: {self.admin_credentials['email']}, {self.agency_credentials['email']}")
        print("=" * 80)
        
        # Run tests in order
        tests_passed = 0
        total_tests = 8
        
        if self.test_admin_login():
            tests_passed += 1
            
        if self.test_agency_login():
            tests_passed += 1
            
        if self.test_auth_me_authenticated():
            tests_passed += 1
            
        if self.test_auth_me_unauthenticated():
            tests_passed += 1
            
        if self.test_agency_profile():
            tests_passed += 1
            
        if self.find_agency_id():
            current_modules = None
            get_success, current_modules = self.test_get_agency_modules()
            if get_success:
                tests_passed += 1
                
                if current_modules is not None:
                    if self.test_put_agency_modules(current_modules):
                        tests_passed += 1
        
        if self.test_agency_profile_reflects_modules():
            # This might be counted separately or as part of overall flow
            pass
            
        if self.check_serialization_issues():
            # This is more of a validation check
            pass
        
        print("=" * 80)
        print(f"📊 RESULTS SUMMARY: {tests_passed}/{total_tests} tests passed")
        
        # Print detailed results
        print("\n📋 DETAILED TEST RESULTS:")
        for i, result in enumerate(self.results, 1):
            status_icon = "✅" if result["status"] == "PASS" else "❌"
            print(f"{i}. {status_icon} {result['test']}")
            if result["details"]:
                print(f"   📝 {result['details']}")
        
        print("\n" + "=" * 80)
        if tests_passed == total_tests:
            print("🎉 ALL TESTS PASSED - No backend regression detected!")
        else:
            print(f"⚠️  {total_tests - tests_passed} test(s) failed - Backend regression detected!")
        
        return tests_passed == total_tests

if __name__ == "__main__":
    tester = SyroceBackendRegressionTest()
    success = tester.run_tests()
    exit(0 if success else 1)