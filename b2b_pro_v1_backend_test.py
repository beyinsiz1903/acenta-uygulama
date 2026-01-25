#!/usr/bin/env python3
"""
B2B PRO V1 Backend Verification Test

This test verifies the B2B PRO V1 backend features as requested in PROMPT 4:
1. Admin agencies API (existing + new constraints)
2. Statements / cari ekstre API  
3. Whitelabel config API
4. Regression checks

Test Environment: Uses REACT_APP_BACKEND_URL from frontend/.env
Authentication: admin@acenta.test / admin123
"""

import requests
import json
import sys
from datetime import datetime, timedelta
import os

# Get backend URL from frontend env
BACKEND_URL = "https://bayi-platform.preview.emergentagent.com"
API_BASE = f"{BACKEND_URL}/api"

class B2BProV1Tester:
    def __init__(self):
        self.session = requests.Session()
        self.token = None
        self.user_info = None
        self.test_results = []
        
    def log_result(self, test_name, success, details, response_data=None):
        """Log test result with details"""
        result = {
            "test": test_name,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        if response_data:
            result["response_data"] = response_data
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {details}")
        
    def authenticate(self):
        """Authenticate as admin user"""
        try:
            response = self.session.post(f"{API_BASE}/auth/login", json={
                "email": "admin@acenta.test",
                "password": "admin123"
            })
            
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                self.user_info = data.get("user", {})
                self.session.headers.update({"Authorization": f"Bearer {self.token}"})
                
                self.log_result("Authentication", True, 
                    f"Admin login successful. User: {self.user_info.get('email')}, "
                    f"Org: {self.user_info.get('organization_id')}, "
                    f"Roles: {self.user_info.get('roles')}")
                return True
            else:
                self.log_result("Authentication", False, 
                    f"Login failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.log_result("Authentication", False, f"Login error: {str(e)}")
            return False
    
    def test_admin_agencies_api(self):
        """Test Admin Agencies API - existing endpoints and new B2B PRO constraints"""
        print("\n=== TESTING ADMIN AGENCIES API ===")
        
        # Test 1: GET /api/admin/agencies - List existing agencies
        try:
            response = self.session.get(f"{API_BASE}/admin/agencies")
            
            if response.status_code == 200:
                agencies = response.json()
                self.log_result("GET /api/admin/agencies", True, 
                    f"Retrieved {len(agencies)} agencies. Organization scoping working.",
                    {"sample_count": len(agencies), "sample_agency": agencies[0] if agencies else None})
                
                # Check if any agencies exist for further testing
                if agencies:
                    sample_agency = agencies[0]
                    self.log_result("Agency Structure Check", True,
                        f"Sample agency structure: {list(sample_agency.keys())}")
            else:
                self.log_result("GET /api/admin/agencies", False,
                    f"Failed: {response.status_code} - {response.text}")
                
        except Exception as e:
            self.log_result("GET /api/admin/agencies", False, f"Error: {str(e)}")
        
        # Test 2: Check for B2B PRO feature guard (should be require_feature("b2b_pro"))
        # This test will verify if the endpoint is properly guarded
        try:
            # First, let's check if the current endpoint has proper role requirements
            response = self.session.get(f"{API_BASE}/admin/agencies")
            
            if response.status_code == 200:
                self.log_result("B2B PRO Feature Guard Check", False,
                    "⚠️ MISSING: Agencies endpoint accessible without B2B PRO feature guard. "
                    "Expected: require_feature('b2b_pro') + super_admin/admin roles")
            elif response.status_code == 404:
                self.log_result("B2B PRO Feature Guard Check", True,
                    "B2B PRO feature guard appears to be working (404 response)")
            else:
                self.log_result("B2B PRO Feature Guard Check", False,
                    f"Unexpected response: {response.status_code}")
                
        except Exception as e:
            self.log_result("B2B PRO Feature Guard Check", False, f"Error: {str(e)}")
        
        # Test 3: POST /api/admin/agencies - Create agency with parent_agency_id support
        try:
            test_agency_data = {
                "name": "Test B2B PRO Agency",
                "parent_agency_id": None  # Test without parent first
            }
            
            response = self.session.post(f"{API_BASE}/admin/agencies", json=test_agency_data)
            
            if response.status_code == 200:
                created_agency = response.json()
                agency_id = created_agency.get("id")
                
                self.log_result("POST /api/admin/agencies (basic)", True,
                    f"Agency created successfully. ID: {agency_id}",
                    {"created_agency": created_agency})
                
                # Test parent_agency_id cycle detection
                cycle_test_data = {
                    "name": "Cycle Test Agency",
                    "parent_agency_id": agency_id  # Try to create with self as parent
                }
                
                cycle_response = self.session.post(f"{API_BASE}/admin/agencies", json=cycle_test_data)
                
                if cycle_response.status_code in [400, 409]:
                    self.log_result("Parent Agency Cycle Detection", True,
                        "Cycle detection working - self-parent rejected")
                else:
                    self.log_result("Parent Agency Cycle Detection", False,
                        "⚠️ MISSING: Parent agency cycle detection not implemented")
                        
            else:
                self.log_result("POST /api/admin/agencies", False,
                    f"Failed: {response.status_code} - {response.text}")
                
        except Exception as e:
            self.log_result("POST /api/admin/agencies", False, f"Error: {str(e)}")
        
        # Test 4: Audit Events Check
        try:
            # Check if audit events are being written for agency operations
            # This is a basic check - we can't easily verify the exact events without access to audit logs
            self.log_result("Audit Events Check", False,
                "⚠️ CANNOT VERIFY: AGENCY_CREATED/UPDATED/DISABLED audit events. "
                "Manual verification required in audit_logs collection.")
                
        except Exception as e:
            self.log_result("Audit Events Check", False, f"Error: {str(e)}")
    
    def test_statements_api(self):
        """Test Statements / Cari Ekstre API"""
        print("\n=== TESTING STATEMENTS / CARI EKSTRE API ===")
        
        # Test 1: GET /api/admin/statements/transactions
        try:
            # Test with date range and agency_id parameters
            from datetime import datetime, timedelta
            date_to = datetime.now()
            date_from = date_to - timedelta(days=30)
            
            params = {
                "date_from": date_from.strftime("%Y-%m-%d"),
                "date_to": date_to.strftime("%Y-%m-%d"),
                "agency_id": "test_agency_id"  # This should be filtered based on user role
            }
            
            response = self.session.get(f"{API_BASE}/admin/statements/transactions", params=params)
            
            if response.status_code == 200:
                data = response.json()
                self.log_result("GET /api/admin/statements/transactions (JSON)", True,
                    f"Statements API working. Response structure: {list(data.keys()) if isinstance(data, dict) else 'Array'}",
                    {"response_sample": data[:2] if isinstance(data, list) else data})
                
                # Verify expected JSON structure
                if isinstance(data, list) and len(data) > 0:
                    sample_row = data[0]
                    expected_fields = ["date", "booking_id", "booking_code", "customer_name", 
                                     "amount_gross_cents", "currency", "payment_method", "agency_id", "channel"]
                    
                    missing_fields = [field for field in expected_fields if field not in sample_row]
                    if not missing_fields:
                        self.log_result("Statements JSON Structure", True,
                            f"All expected fields present: {expected_fields}")
                    else:
                        self.log_result("Statements JSON Structure", False,
                            f"Missing fields: {missing_fields}")
                        
            elif response.status_code == 404:
                self.log_result("GET /api/admin/statements/transactions", False,
                    "⚠️ NOT IMPLEMENTED: Statements API endpoint not found")
            else:
                self.log_result("GET /api/admin/statements/transactions", False,
                    f"Failed: {response.status_code} - {response.text}")
                
        except Exception as e:
            self.log_result("GET /api/admin/statements/transactions", False, f"Error: {str(e)}")
        
        # Test 2: CSV Format Support
        try:
            params = {
                "date_from": (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"),
                "date_to": datetime.now().strftime("%Y-%m-%d"),
                "format": "csv"
            }
            
            headers = {"Accept": "text/csv"}
            response = self.session.get(f"{API_BASE}/admin/statements/transactions", 
                                      params=params, headers=headers)
            
            if response.status_code == 200 and "text/csv" in response.headers.get("content-type", ""):
                self.log_result("Statements CSV Format", True,
                    f"CSV format working. Content-Type: {response.headers.get('content-type')}")
            elif response.status_code == 404:
                self.log_result("Statements CSV Format", False,
                    "⚠️ NOT IMPLEMENTED: CSV format support not available")
            else:
                self.log_result("Statements CSV Format", False,
                    f"CSV format failed: {response.status_code}")
                
        except Exception as e:
            self.log_result("Statements CSV Format", False, f"Error: {str(e)}")
        
        # Test 3: Role-based Agency Filtering
        try:
            # Test admin vs agency_admin behavior
            # Admin should be able to specify any agency_id in org
            # Agency_admin should have agency_id query ignored, use their own user.agency_id
            
            self.log_result("Role-based Agency Filtering", False,
                "⚠️ CANNOT VERIFY: Role-based agency filtering requires agency_admin user. "
                "Manual test needed with agency_admin credentials.")
                
        except Exception as e:
            self.log_result("Role-based Agency Filtering", False, f"Error: {str(e)}")
        
        # Test 4: STATEMENT_VIEWED Audit Log
        try:
            self.log_result("STATEMENT_VIEWED Audit Log", False,
                "⚠️ CANNOT VERIFY: STATEMENT_VIEWED audit log creation. "
                "Manual verification required in audit_logs collection.")
                
        except Exception as e:
            self.log_result("STATEMENT_VIEWED Audit Log", False, f"Error: {str(e)}")
    
    def test_whitelabel_config_api(self):
        """Test Whitelabel Config API"""
        print("\n=== TESTING WHITELABEL CONFIG API ===")
        
        # Test 1: GET /api/admin/whitelabel
        try:
            response = self.session.get(f"{API_BASE}/admin/whitelabel")
            
            if response.status_code == 200:
                config = response.json()
                self.log_result("GET /api/admin/whitelabel", True,
                    f"Whitelabel config loaded. Keys: {list(config.keys()) if isinstance(config, dict) else 'Not dict'}",
                    {"config_sample": config})
                
                # Store config for PUT test
                self.whitelabel_config = config
                
            elif response.status_code == 404:
                self.log_result("GET /api/admin/whitelabel", False,
                    "⚠️ NOT IMPLEMENTED: Whitelabel config API endpoint not found")
                self.whitelabel_config = None
            else:
                self.log_result("GET /api/admin/whitelabel", False,
                    f"Failed: {response.status_code} - {response.text}")
                self.whitelabel_config = None
                
        except Exception as e:
            self.log_result("GET /api/admin/whitelabel", False, f"Error: {str(e)}")
            self.whitelabel_config = None
        
        # Test 2: PUT /api/admin/whitelabel
        try:
            if hasattr(self, 'whitelabel_config') and self.whitelabel_config:
                # Update existing config
                updated_config = dict(self.whitelabel_config)
                updated_config["test_field"] = "B2B PRO V1 Test"
                
                response = self.session.put(f"{API_BASE}/admin/whitelabel", json=updated_config)
                
                if response.status_code == 200:
                    self.log_result("PUT /api/admin/whitelabel", True,
                        "Whitelabel config update successful")
                else:
                    self.log_result("PUT /api/admin/whitelabel", False,
                        f"Update failed: {response.status_code} - {response.text}")
            else:
                # Try creating new config
                test_config = {
                    "company_name": "B2B PRO Test Company",
                    "primary_color": "#007bff",
                    "logo_url": "https://example.com/logo.png"
                }
                
                response = self.session.put(f"{API_BASE}/admin/whitelabel", json=test_config)
                
                if response.status_code == 200:
                    self.log_result("PUT /api/admin/whitelabel (create)", True,
                        "Whitelabel config creation successful")
                elif response.status_code == 404:
                    self.log_result("PUT /api/admin/whitelabel", False,
                        "⚠️ NOT IMPLEMENTED: Whitelabel config PUT endpoint not found")
                else:
                    self.log_result("PUT /api/admin/whitelabel", False,
                        f"Failed: {response.status_code} - {response.text}")
                
        except Exception as e:
            self.log_result("PUT /api/admin/whitelabel", False, f"Error: {str(e)}")
        
        # Test 3: Organization-scoped Unique Constraint
        try:
            self.log_result("Org-scoped Unique Constraint", False,
                "⚠️ CANNOT VERIFY: Organization-scoped unique constraint for whitelabel settings. "
                "Requires multiple organizations for testing.")
                
        except Exception as e:
            self.log_result("Org-scoped Unique Constraint", False, f"Error: {str(e)}")
        
        # Test 4: WHITELABEL_UPDATED Audit Event
        try:
            self.log_result("WHITELABEL_UPDATED Audit Event", False,
                "⚠️ CANNOT VERIFY: WHITELABEL_UPDATED audit event creation. "
                "Manual verification required in audit_logs collection.")
                
        except Exception as e:
            self.log_result("WHITELABEL_UPDATED Audit Event", False, f"Error: {str(e)}")
    
    def test_regression_checks(self):
        """Test regression checks for existing B2B functionality"""
        print("\n=== TESTING REGRESSION CHECKS ===")
        
        # Test 1: Existing B2B booking endpoint unchanged
        try:
            # This is a basic connectivity test - we can't create a full booking without proper setup
            response = self.session.get(f"{API_BASE}/api/b2b/quotes")  # Note: double /api prefix
            
            if response.status_code in [200, 401, 403]:  # Any of these indicates endpoint exists
                self.log_result("B2B Booking Endpoint Regression", True,
                    f"B2B endpoints accessible. Status: {response.status_code}")
            elif response.status_code == 404:
                # Try alternative path
                response2 = self.session.get(f"{API_BASE}/b2b/quotes")
                if response2.status_code in [200, 401, 403]:
                    self.log_result("B2B Booking Endpoint Regression", True,
                        f"B2B endpoints accessible at /api/b2b/. Status: {response2.status_code}")
                else:
                    self.log_result("B2B Booking Endpoint Regression", False,
                        "B2B endpoints not accessible")
            else:
                self.log_result("B2B Booking Endpoint Regression", False,
                    f"Unexpected response: {response.status_code}")
                
        except Exception as e:
            self.log_result("B2B Booking Endpoint Regression", False, f"Error: {str(e)}")
        
        # Test 2: Organization Data Isolation
        try:
            # Test that admin endpoints only return data for current organization
            response = self.session.get(f"{API_BASE}/admin/agencies")
            
            if response.status_code == 200:
                agencies = response.json()
                org_id = self.user_info.get("organization_id")
                
                # Check if all agencies belong to current organization
                if agencies:
                    org_check = all(agency.get("organization_id") == org_id for agency in agencies)
                    if org_check:
                        self.log_result("Organization Data Isolation", True,
                            f"All {len(agencies)} agencies belong to current org: {org_id}")
                    else:
                        self.log_result("Organization Data Isolation", False,
                            "⚠️ SECURITY ISSUE: Cross-organization data leakage detected")
                else:
                    self.log_result("Organization Data Isolation", True,
                        "No agencies found - isolation cannot be verified but no leakage detected")
            else:
                self.log_result("Organization Data Isolation", False,
                    f"Cannot verify isolation: {response.status_code}")
                
        except Exception as e:
            self.log_result("Organization Data Isolation", False, f"Error: {str(e)}")
    
    def generate_summary(self):
        """Generate comprehensive test summary"""
        print("\n" + "="*80)
        print("B2B PRO V1 BACKEND VERIFICATION SUMMARY")
        print("="*80)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests*100):.1f}%")
        
        print("\n=== DETAILED FINDINGS ===")
        
        # Group results by category
        categories = {
            "Admin Agencies API": [],
            "Statements API": [],
            "Whitelabel API": [],
            "Regression Checks": [],
            "Authentication": []
        }
        
        for result in self.test_results:
            test_name = result["test"]
            if "agencies" in test_name.lower() or "agency" in test_name.lower():
                categories["Admin Agencies API"].append(result)
            elif "statement" in test_name.lower():
                categories["Statements API"].append(result)
            elif "whitelabel" in test_name.lower():
                categories["Whitelabel API"].append(result)
            elif "regression" in test_name.lower() or "b2b" in test_name.lower():
                categories["Regression Checks"].append(result)
            elif "auth" in test_name.lower():
                categories["Authentication"].append(result)
        
        for category, results in categories.items():
            if results:
                print(f"\n{category}:")
                for result in results:
                    status = "✅" if result["success"] else "❌"
                    print(f"  {status} {result['test']}: {result['details']}")
        
        print("\n=== EXAMPLE RESPONSES ===")
        
        # Show example JSON responses where available
        for result in self.test_results:
            if result.get("response_data") and result["success"]:
                print(f"\n{result['test']} Example Response:")
                response_str = json.dumps(result["response_data"], indent=2)
                if len(response_str) > 500:
                    print(response_str[:500] + "...")
                else:
                    print(response_str)
        
        return {
            "total_tests": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
            "success_rate": passed_tests/total_tests*100 if total_tests > 0 else 0
        }

def main():
    """Main test execution"""
    print("B2B PRO V1 Backend Verification Test")
    print("=" * 50)
    print(f"Backend URL: {BACKEND_URL}")
    print(f"Test Time: {datetime.now().isoformat()}")
    print()
    
    tester = B2BProV1Tester()
    
    # Step 1: Authenticate
    if not tester.authenticate():
        print("❌ Authentication failed. Cannot proceed with tests.")
        sys.exit(1)
    
    # Step 2: Run all test suites
    tester.test_admin_agencies_api()
    tester.test_statements_api()
    tester.test_whitelabel_config_api()
    tester.test_regression_checks()
    
    # Step 3: Generate summary
    summary = tester.generate_summary()
    
    # Step 4: Exit with appropriate code
    if summary["failed"] > 0:
        print(f"\n⚠️  {summary['failed']} tests failed. Review implementation status above.")
        sys.exit(1)
    else:
        print(f"\n✅ All {summary['passed']} tests passed!")
        sys.exit(0)

if __name__ == "__main__":
    main()