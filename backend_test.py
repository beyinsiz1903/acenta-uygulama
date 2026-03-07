#!/usr/bin/env python3
"""
PR-V1-1 Backend Validation Test Suite

This test suite validates the low-risk /api/v1 rollout for PR-V1-1 as requested.
Tests both legacy + v1 parity for specific routes and route inventory functionality.

Scope:
1. Legacy + v1 parity for low-risk routes
2. Confirm legacy paths still work unchanged  
3. Confirm route inventory snapshot exists
4. Confirm diff CLI works

Admin credentials: admin@acenta.test / admin123
"""

import json
import subprocess
import tempfile
from pathlib import Path
import requests
import sys
import os

# Get base URL from environment
BACKEND_URL = "https://saas-modernize-2.preview.emergentagent.com"
ADMIN_CREDENTIALS = {
    "email": "admin@acenta.test", 
    "password": "admin123"
}

class PRV1ValidationTests:
    def __init__(self):
        self.base_url = BACKEND_URL
        self.admin_token = None
        self.test_results = []

    def log_result(self, test_name, passed, details=""):
        """Log test result"""
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
        if details:
            print(f"  Details: {details}")
        self.test_results.append({
            "test": test_name,
            "passed": passed,
            "details": details
        })

    def get_admin_token(self):
        """Get admin authentication token"""
        try:
            response = requests.post(
                f"{self.base_url}/api/auth/login",
                json=ADMIN_CREDENTIALS,
                timeout=30
            )
            if response.status_code == 200:
                data = response.json()
                self.admin_token = data.get("access_token")
                self.log_result("Admin Authentication", True, f"Token length: {len(self.admin_token) if self.admin_token else 0}")
                return True
            else:
                self.log_result("Admin Authentication", False, f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log_result("Admin Authentication", False, str(e))
            return False

    def test_route_parity(self, legacy_path, v1_path, method="GET", needs_auth=False):
        """Test parity between legacy and v1 routes"""
        headers = {}
        if needs_auth and self.admin_token:
            headers["Authorization"] = f"Bearer {self.admin_token}"

        try:
            # Test legacy route
            if method == "GET":
                legacy_response = requests.get(f"{self.base_url}{legacy_path}", headers=headers, timeout=30)
            else:
                self.log_result(f"Route Parity {legacy_path} <-> {v1_path}", False, "Only GET method supported in this test")
                return False

            # Test v1 route  
            if method == "GET":
                v1_response = requests.get(f"{self.base_url}{v1_path}", headers=headers, timeout=30)
            else:
                v1_response = None

            # Check if both return same status
            if legacy_response.status_code == v1_response.status_code:
                # For successful responses, compare basic structure
                if legacy_response.status_code == 200:
                    try:
                        legacy_json = legacy_response.json()
                        v1_json = v1_response.json()
                        # Basic structure comparison - they should have similar keys
                        legacy_keys = set(legacy_json.keys()) if isinstance(legacy_json, dict) else set()
                        v1_keys = set(v1_json.keys()) if isinstance(v1_json, dict) else set()
                        
                        if legacy_keys == v1_keys or (isinstance(legacy_json, list) and isinstance(v1_json, list)):
                            self.log_result(f"Route Parity {legacy_path} <-> {v1_path}", True, 
                                          f"Both return {legacy_response.status_code}, similar structure")
                            return True
                        else:
                            self.log_result(f"Route Parity {legacy_path} <-> {v1_path}", False, 
                                          f"Different response structure: {legacy_keys} vs {v1_keys}")
                            return False
                    except:
                        # If not JSON, compare content length
                        if len(legacy_response.content) > 0 and len(v1_response.content) > 0:
                            self.log_result(f"Route Parity {legacy_path} <-> {v1_path}", True,
                                          f"Both return {legacy_response.status_code}, non-empty responses")
                            return True
                        else:
                            self.log_result(f"Route Parity {legacy_path} <-> {v1_path}", False,
                                          "Empty responses or parse error")
                            return False
                else:
                    # Both failed with same status, that's still parity
                    self.log_result(f"Route Parity {legacy_path} <-> {v1_path}", True,
                                  f"Both return {legacy_response.status_code}")
                    return True
            else:
                self.log_result(f"Route Parity {legacy_path} <-> {v1_path}", False,
                              f"Different status codes: {legacy_response.status_code} vs {v1_response.status_code}")
                return False

        except Exception as e:
            self.log_result(f"Route Parity {legacy_path} <-> {v1_path}", False, str(e))
            return False

    def test_legacy_routes_unchanged(self):
        """Test that legacy routes still work as expected"""
        test_routes = [
            ("/api/health", False),
            ("/api/system/ping", False), 
            ("/api/public/theme", False),
            (f"/api/public/cms/pages?org=org_demo", False),
            (f"/api/public/campaigns?org=org_demo", False),
            ("/api/system/health-dashboard", True),
            ("/api/admin/theme", True),
        ]
        
        passed_count = 0
        total_count = len(test_routes)
        
        for route, needs_auth in test_routes:
            try:
                headers = {}
                if needs_auth and self.admin_token:
                    headers["Authorization"] = f"Bearer {self.admin_token}"
                
                response = requests.get(f"{self.base_url}{route}", headers=headers, timeout=30)
                
                if response.status_code in [200, 401, 403]:  # Expected statuses
                    self.log_result(f"Legacy Route {route}", True, f"Status: {response.status_code}")
                    passed_count += 1
                else:
                    self.log_result(f"Legacy Route {route}", False, f"Unexpected status: {response.status_code}")
                    
            except Exception as e:
                self.log_result(f"Legacy Route {route}", False, str(e))
        
        return passed_count == total_count

    def test_low_risk_v1_parity(self):
        """Test low-risk v1 route aliases work correctly"""
        if not self.admin_token:
            self.log_result("V1 Route Parity Tests", False, "No admin token available")
            return False

        # Routes from review request  
        parity_tests = [
            ("/api/health", "/api/v1/health", False),
            ("/api/system/ping", "/api/v1/system/ping", False),
            ("/api/system/health-dashboard", "/api/v1/system/health-dashboard", True),
            ("/api/public/theme", "/api/v1/public/theme", False),
            ("/api/admin/theme", "/api/v1/admin/theme", True),
            ("/api/public/cms/pages?org=org_demo", "/api/v1/public/cms/pages?org=org_demo", False),
            ("/api/public/campaigns?org=org_demo", "/api/v1/public/campaigns?org=org_demo", False),
        ]
        
        passed_count = 0
        for legacy_path, v1_path, needs_auth in parity_tests:
            if self.test_route_parity(legacy_path, v1_path, "GET", needs_auth):
                passed_count += 1
                
        total_count = len(parity_tests)
        self.log_result("Overall V1 Parity Tests", passed_count == total_count, 
                       f"{passed_count}/{total_count} parity tests passed")
        return passed_count == total_count

    def test_route_inventory_exists(self):
        """Test that route inventory snapshot exists and contains v1 aliases"""
        try:
            inventory_path = Path("/app/backend/app/bootstrap/route_inventory.json")
            
            if not inventory_path.exists():
                self.log_result("Route Inventory File Exists", False, "File not found")
                return False
                
            self.log_result("Route Inventory File Exists", True, str(inventory_path))
            
            # Load and validate content
            with open(inventory_path) as f:
                inventory = json.load(f)
            
            if not isinstance(inventory, list) or len(inventory) == 0:
                self.log_result("Route Inventory Content Valid", False, "Invalid or empty inventory")
                return False
                
            # Count v1 routes
            v1_routes = [route for route in inventory if route.get("legacy_or_v1") == "v1"]
            legacy_routes = [route for route in inventory if route.get("legacy_or_v1") == "legacy"]
            
            self.log_result("Route Inventory Content Valid", True, 
                          f"Total routes: {len(inventory)}, V1 routes: {len(v1_routes)}, Legacy routes: {len(legacy_routes)}")
            
            # Check for required fields
            required_fields = ["compat_required", "current_namespace", "legacy_or_v1", "method", 
                             "owner", "path", "risk_level", "source", "target_namespace"]
            
            sample_route = inventory[0]
            missing_fields = [field for field in required_fields if field not in sample_route]
            
            if missing_fields:
                self.log_result("Route Inventory Fields Complete", False, f"Missing fields: {missing_fields}")
                return False
            else:
                self.log_result("Route Inventory Fields Complete", True, "All required fields present")
                
            # Check if v1 aliases exist for low-risk routes
            v1_paths = {route["path"] for route in v1_routes}
            expected_v1_paths = ["/api/v1/health", "/api/v1/system/ping", "/api/v1/system/health-dashboard",
                               "/api/v1/public/theme", "/api/v1/admin/theme", "/api/v1/public/cms/pages",
                               "/api/v1/public/campaigns"]
            
            found_paths = [path for path in expected_v1_paths if path in v1_paths]
            
            self.log_result("V1 Aliases in Inventory", len(found_paths) > 0, 
                          f"Found {len(found_paths)} expected v1 aliases: {found_paths}")
            
            return True
            
        except Exception as e:
            self.log_result("Route Inventory Validation", False, str(e))
            return False

    def test_diff_cli_functionality(self):
        """Test route inventory diff CLI tool"""
        try:
            # Create a synthetic previous inventory by filtering out v1 entries
            current_inventory_path = Path("/app/backend/app/bootstrap/route_inventory.json")
            
            if not current_inventory_path.exists():
                self.log_result("Diff CLI Test", False, "Current inventory file not found")
                return False
                
            with open(current_inventory_path) as f:
                current_inventory = json.load(f)
            
            # Create previous inventory without v1 routes
            previous_inventory = [route for route in current_inventory if not route["path"].startswith("/api/v1/")]
            
            # Write to temp file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
                json.dump(previous_inventory, temp_file, indent=2)
                temp_path = temp_file.name
            
            try:
                # Test diff CLI with text format
                result = subprocess.run([
                    "python", "/app/backend/scripts/diff_route_inventory.py",
                    temp_path, str(current_inventory_path),
                    "--format", "text"
                ], capture_output=True, text=True, cwd="/app/backend", timeout=30)
                
                if result.returncode == 0:
                    output = result.stdout
                    
                    # Check if output contains expected information
                    if "added_route_count:" in output and "new_v1_route_count:" in output:
                        self.log_result("Diff CLI Text Format", True, "Output contains expected metrics")
                        
                        # Extract some numbers for validation
                        lines = output.split('\n')
                        added_count = None
                        v1_count = None
                        
                        for line in lines:
                            if "added_route_count:" in line:
                                added_count = line.split(':')[1].strip()
                            elif "new_v1_route_count:" in line:
                                v1_count = line.split(':')[1].strip()
                        
                        self.log_result("Diff CLI Metrics", True, 
                                      f"Added routes: {added_count}, New V1 routes: {v1_count}")
                    else:
                        self.log_result("Diff CLI Text Format", False, "Missing expected metrics in output")
                        return False
                else:
                    self.log_result("Diff CLI Text Format", False, f"Exit code: {result.returncode}, Error: {result.stderr}")
                    return False
                
                # Test JSON format
                result_json = subprocess.run([
                    "python", "/app/backend/scripts/diff_route_inventory.py", 
                    temp_path, str(current_inventory_path),
                    "--format", "json"
                ], capture_output=True, text=True, cwd="/app/backend", timeout=30)
                
                if result_json.returncode == 0:
                    try:
                        diff_data = json.loads(result_json.stdout)
                        if "summary" in diff_data and "added_paths" in diff_data:
                            self.log_result("Diff CLI JSON Format", True, "Valid JSON output with expected structure")
                            return True
                        else:
                            self.log_result("Diff CLI JSON Format", False, "JSON missing expected structure")
                            return False
                    except json.JSONDecodeError as e:
                        self.log_result("Diff CLI JSON Format", False, f"Invalid JSON: {e}")
                        return False
                else:
                    self.log_result("Diff CLI JSON Format", False, f"Exit code: {result_json.returncode}")
                    return False
                    
            finally:
                # Cleanup temp file
                os.unlink(temp_path)
                
        except Exception as e:
            self.log_result("Diff CLI Test", False, str(e))
            return False

    def run_all_tests(self):
        """Run all PR-V1-1 validation tests"""
        print("=== PR-V1-1 Backend Validation Test Suite ===")
        print(f"Testing against: {self.base_url}")
        print()
        
        # Step 1: Get admin authentication
        if not self.get_admin_token():
            print("❌ CRITICAL: Cannot proceed without admin authentication")
            return False
        
        print()
        
        # Step 2: Test legacy routes still work unchanged
        print("--- Testing Legacy Routes Unchanged ---")
        legacy_passed = self.test_legacy_routes_unchanged()
        print()
        
        # Step 3: Test legacy + v1 parity for low-risk routes
        print("--- Testing Legacy + V1 Parity ---")
        parity_passed = self.test_low_risk_v1_parity()
        print()
        
        # Step 4: Test route inventory snapshot exists
        print("--- Testing Route Inventory Snapshot ---")
        inventory_passed = self.test_route_inventory_exists()
        print()
        
        # Step 5: Test diff CLI functionality
        print("--- Testing Diff CLI Functionality ---")
        diff_passed = self.test_diff_cli_functionality()
        print()
        
        # Summary
        total_tests = len(self.test_results)
        passed_tests = len([t for t in self.test_results if t["passed"]])
        
        print("=== PR-V1-1 TEST SUMMARY ===")
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        print()
        
        if passed_tests == total_tests:
            print("✅ ALL TESTS PASSED - PR-V1-1 low-risk /api/v1 rollout validated successfully")
            return True
        else:
            print("❌ SOME TESTS FAILED - Review failures above")
            
            # Show failed tests
            failed_tests = [t for t in self.test_results if not t["passed"]]
            if failed_tests:
                print("\nFailed Tests:")
                for test in failed_tests:
                    print(f"  - {test['test']}: {test['details']}")
                    
            return False

if __name__ == "__main__":
    tester = PRV1ValidationTests()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)