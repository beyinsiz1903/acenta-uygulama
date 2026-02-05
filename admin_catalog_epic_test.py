#!/usr/bin/env python3
"""
A-epic Admin Catalog Backend Test
Tests cancellation policies, room types, rate plans, and version management
"""
import requests
import sys
import uuid
from datetime import datetime

class AdminCatalogEpicTester:
    def __init__(self, base_url="https://travelpartner-2.preview.emergentagent.com"):
        self.base_url = base_url
        self.admin_token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.failed_tests = []
        
        # Store data for testing
        self.product_id = None
        self.cancellation_policy_id = None
        self.room_type_id = None
        self.rate_plan_id = None

    def log(self, msg):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    def run_test(self, name, method, endpoint, expected_status, data=None, headers_override=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        headers = headers_override or {'Content-Type': 'application/json'}
        if self.admin_token and not headers_override:
            headers['Authorization'] = f'Bearer {self.admin_token}'

        self.tests_run += 1
        self.log(f"🔍 Test #{self.tests_run}: {name}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=10)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=10)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=10)
            else:
                raise ValueError(f"Unsupported method: {method}")

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                self.log(f"✅ PASSED - Status: {response.status_code}")
                try:
                    return True, response.json() if response.content else {}
                except:
                    return True, {}
            else:
                self.tests_failed += 1
                self.failed_tests.append(f"{name} - Expected {expected_status}, got {response.status_code}")
                self.log(f"❌ FAILED - Expected {expected_status}, got {response.status_code}")
                try:
                    self.log(f"   Response: {response.text[:200]}")
                except:
                    pass
                return False, {}

        except Exception as e:
            self.tests_failed += 1
            self.failed_tests.append(f"{name} - Error: {str(e)}")
            self.log(f"❌ FAILED - Error: {str(e)}")
            return False, {}

    def test_admin_login(self):
        """Test admin login"""
        self.log("\n=== AUTHENTICATION ===")
        success, response = self.run_test(
            "Admin Login (admin@acenta.test/admin123)",
            "POST",
            "api/auth/login",
            200,
            data={"email": "admin@acenta.test", "password": "admin123"},
            headers_override={'Content-Type': 'application/json'}
        )
        if success and 'access_token' in response:
            self.admin_token = response['access_token']
            user = response.get('user', {})
            roles = user.get('roles', [])
            
            if 'admin' in roles or 'super_admin' in roles:
                self.log(f"✅ Admin login successful - roles: {roles}")
                return True
            else:
                self.log(f"❌ Missing admin/super_admin role: {roles}")
                return False
        return False

    def test_setup_product(self):
        """Setup a product for testing"""
        self.log("\n=== SETUP PRODUCT FOR TESTING ===")
        
        # First check if we have any existing products
        success, response = self.run_test(
            "List existing products",
            "GET",
            "api/admin/catalog/products?limit=50",
            200
        )
        
        if success and response.get('items'):
            # Use existing product
            self.product_id = response['items'][0]['product_id']
            self.log(f"✅ Using existing product: {self.product_id}")
            return True
        else:
            # Create a new product
            product_data = {
                "type": "hotel",
                "code": "test_hotel_001",
                "name": {"tr": "Test Otel", "en": "Test Hotel"},
                "default_currency": "eur",
                "status": "active"
            }
            success, response = self.run_test(
                "Create test product",
                "POST",
                "api/admin/catalog/products",
                200,
                data=product_data
            )
            
            if success and response.get('product_id'):
                self.product_id = response['product_id']
                self.log(f"✅ Created test product: {self.product_id}")
                return True
            else:
                self.log("❌ Failed to create test product")
                return False

    def test_cancellation_policies(self):
        """1) Cancellation policies test"""
        self.log("\n=== 1) CANCELLATION POLICIES TEST ===")
        
        # Create cancellation policy with unique code
        import time
        unique_suffix = int(time.time())
        policy_data = {
            "code": f"pol_flex14_{unique_suffix}",
            "name": "Flexible 14d",
            "rules": [
                {"days_before": 14, "penalty_type": "none"},
                {"days_before": 0, "penalty_type": "nights", "nights": 1}
            ]
        }
        
        success, response = self.run_test(
            "POST /api/admin/catalog/cancellation-policies",
            "POST",
            "api/admin/catalog/cancellation-policies",
            200,
            data=policy_data
        )
        
        if success:
            # Verify response structure
            required_fields = ['cancellation_policy_id', 'code', 'name', 'rules']
            if all(field in response for field in required_fields):
                self.cancellation_policy_id = response['cancellation_policy_id']
                self.log(f"✅ Policy created successfully:")
                self.log(f"   - cancellation_policy_id: {self.cancellation_policy_id}")
                self.log(f"   - code: {response['code']}")
                self.log(f"   - name: {response['name']}")
                self.log(f"   - rules: {len(response['rules'])} rules")
                
                # Verify rules structure
                rules = response['rules']
                if len(rules) == 2:
                    rule1, rule2 = rules
                    if (rule1.get('days_before') == 14 and rule1.get('penalty_type') == 'none' and
                        rule2.get('days_before') == 0 and rule2.get('penalty_type') == 'nights' and rule2.get('nights') == 1):
                        self.log(f"✅ Rules structure verified correctly")
                    else:
                        self.log(f"❌ Rules structure incorrect: {rules}")
                        return False
                else:
                    self.log(f"❌ Expected 2 rules, got {len(rules)}")
                    return False
            else:
                missing = [f for f in required_fields if f not in response]
                self.log(f"❌ Missing required fields: {missing}")
                return False
        else:
            return False
        
        # List cancellation policies
        success, response = self.run_test(
            "GET /api/admin/catalog/cancellation-policies?limit=200",
            "GET",
            "api/admin/catalog/cancellation-policies?limit=200",
            200
        )
        
        if success:
            # Find our policy in the list
            found_policy = None
            for policy in response:
                if policy.get('cancellation_policy_id') == self.cancellation_policy_id:
                    found_policy = policy
                    break
            
            if found_policy:
                self.log(f"✅ Policy found in list:")
                self.log(f"   - code: {found_policy['code']}")
                self.log(f"   - name: {found_policy['name']}")
                return True
            else:
                self.log(f"❌ Created policy not found in list")
                return False
        else:
            return False

    def test_room_types(self):
        """2) Room types test"""
        self.log("\n=== 2) ROOM TYPES TEST ===")
        
        if not self.product_id:
            self.log("❌ No product_id available for room types test")
            return False
        
        # Create room type with unique code
        import time
        unique_suffix = int(time.time())
        room_type_data = {
            "product_id": self.product_id,
            "code": f"dlx_{unique_suffix}",
            "name": {"tr": "Deluxe Oda", "en": "Deluxe Room"},
            "max_occupancy": 3,
            "attributes": {"view": "sea"}
        }
        
        success, response = self.run_test(
            "POST /api/admin/catalog/room-types",
            "POST",
            "api/admin/catalog/room-types",
            200,
            data=room_type_data
        )
        
        if success:
            # Verify response structure
            required_fields = ['room_type_id', 'product_id', 'code', 'name', 'max_occupancy', 'attributes']
            if all(field in response for field in required_fields):
                self.room_type_id = response['room_type_id']
                self.log(f"✅ Room type created successfully:")
                self.log(f"   - room_type_id: {self.room_type_id}")
                self.log(f"   - product_id: {response['product_id']}")
                self.log(f"   - code: {response['code']}")
                self.log(f"   - name: {response['name']}")
                self.log(f"   - max_occupancy: {response['max_occupancy']}")
                self.log(f"   - attributes: {response['attributes']}")
                
                # Verify values
                if (response['product_id'] == self.product_id and
                    response['code'].startswith('DLX_') and  # Should be uppercase with suffix
                    response['max_occupancy'] == 3 and
                    response['attributes'].get('view') == 'sea'):
                    self.log(f"✅ Room type values verified correctly")
                else:
                    self.log(f"❌ Room type values incorrect")
                    return False
            else:
                missing = [f for f in required_fields if f not in response]
                self.log(f"❌ Missing required fields: {missing}")
                return False
        else:
            return False
        
        # List room types for this product
        success, response = self.run_test(
            f"GET /api/admin/catalog/room-types?product_id={self.product_id}",
            "GET",
            f"api/admin/catalog/room-types?product_id={self.product_id}",
            200
        )
        
        if success:
            # Find our room type in the list
            found_room_type = None
            for room_type in response:
                if room_type.get('room_type_id') == self.room_type_id:
                    found_room_type = room_type
                    break
            
            if found_room_type:
                self.log(f"✅ Room type found in list:")
                self.log(f"   - code: {found_room_type['code']}")
                self.log(f"   - name: {found_room_type['name']}")
            else:
                self.log(f"❌ Created room type not found in list")
                return False
        else:
            return False
        
        # Test duplicate code validation
        success, response = self.run_test(
            "POST /api/admin/catalog/room-types (duplicate code)",
            "POST",
            "api/admin/catalog/room-types",
            409,
            data=room_type_data
        )
        
        if success:
            # Check error details
            if 'duplicate_code' in str(response).lower():
                self.log(f"✅ Duplicate code validation working correctly")
                return True
            else:
                self.log(f"❌ Expected duplicate_code error, got: {response}")
                return False
        else:
            return False

    def test_rate_plans(self):
        """3) Rate plans test"""
        self.log("\n=== 3) RATE PLANS TEST ===")
        
        if not self.product_id or not self.cancellation_policy_id:
            self.log("❌ Missing product_id or cancellation_policy_id for rate plans test")
            return False
        
        # Create rate plan with unique code
        import time
        unique_suffix = int(time.time())
        rate_plan_data = {
            "product_id": self.product_id,
            "code": f"bb_flex14_{unique_suffix}",
            "name": {"tr": "Oda+Kahvaltı Flex", "en": "BB Flex"},
            "board": "BB",
            "cancellation_policy_id": self.cancellation_policy_id,
            "payment_type": "postpay",
            "min_stay": 1,
            "max_stay": 14
        }
        
        success, response = self.run_test(
            "POST /api/admin/catalog/rate-plans",
            "POST",
            "api/admin/catalog/rate-plans",
            200,
            data=rate_plan_data
        )
        
        if success:
            # Verify response structure
            required_fields = ['rate_plan_id', 'product_id', 'code', 'name', 'board', 'cancellation_policy_id', 'payment_type', 'min_stay', 'max_stay']
            if all(field in response for field in required_fields):
                self.rate_plan_id = response['rate_plan_id']
                self.log(f"✅ Rate plan created successfully:")
                self.log(f"   - rate_plan_id: {self.rate_plan_id}")
                self.log(f"   - product_id: {response['product_id']}")
                self.log(f"   - code: {response['code']}")
                self.log(f"   - name: {response['name']}")
                self.log(f"   - board: {response['board']}")
                self.log(f"   - cancellation_policy_id: {response['cancellation_policy_id']}")
                self.log(f"   - payment_type: {response['payment_type']}")
                self.log(f"   - min_stay: {response['min_stay']}")
                self.log(f"   - max_stay: {response['max_stay']}")
                
                # Verify values
                if (response['product_id'] == self.product_id and
                    response['code'].startswith('BB_FLEX14_') and  # Should be uppercase with suffix
                    response['board'] == 'BB' and
                    response['cancellation_policy_id'] == self.cancellation_policy_id and
                    response['payment_type'] == 'postpay' and
                    response['min_stay'] == 1 and
                    response['max_stay'] == 14):
                    self.log(f"✅ Rate plan values verified correctly")
                else:
                    self.log(f"❌ Rate plan values incorrect")
                    return False
            else:
                missing = [f for f in required_fields if f not in response]
                self.log(f"❌ Missing required fields: {missing}")
                return False
        else:
            return False
        
        # List rate plans for this product
        success, response = self.run_test(
            f"GET /api/admin/catalog/rate-plans?product_id={self.product_id}",
            "GET",
            f"api/admin/catalog/rate-plans?product_id={self.product_id}",
            200
        )
        
        if success:
            # Find our rate plan in the list
            found_rate_plan = None
            for rate_plan in response:
                if rate_plan.get('rate_plan_id') == self.rate_plan_id:
                    found_rate_plan = rate_plan
                    break
            
            if found_rate_plan:
                self.log(f"✅ Rate plan found in list:")
                self.log(f"   - code: {found_rate_plan['code']}")
                self.log(f"   - name: {found_rate_plan['name']}")
            else:
                self.log(f"❌ Created rate plan not found in list")
                return False
        else:
            return False
        
        # Test duplicate code validation
        success, response = self.run_test(
            "POST /api/admin/catalog/rate-plans (duplicate code)",
            "POST",
            "api/admin/catalog/rate-plans",
            409,
            data=rate_plan_data
        )
        
        if success:
            # Check error details
            if 'duplicate_code' in str(response).lower():
                self.log(f"✅ Duplicate code validation working correctly")
                return True
            else:
                self.log(f"❌ Expected duplicate_code error, got: {response}")
                return False
        else:
            return False

    def test_version_create_and_publish(self):
        """4) Version create/publish with referential integrity"""
        self.log("\n=== 4) VERSION CREATE/PUBLISH WITH REFERENTIAL INTEGRITY ===")
        
        if not self.product_id or not self.room_type_id or not self.rate_plan_id:
            self.log("❌ Missing required IDs for version test")
            return False
        
        # Create version with room_type_ids and rate_plan_ids
        version_data = {
            "content": {
                "description": {"tr": "V1", "en": "V1"},
                "room_type_ids": [self.room_type_id],
                "rate_plan_ids": [self.rate_plan_id]
            }
        }
        
        success, response = self.run_test(
            f"POST /api/admin/catalog/products/{self.product_id}/versions",
            "POST",
            f"api/admin/catalog/products/{self.product_id}/versions",
            200,
            data=version_data
        )
        
        if success:
            version_id = response.get('version_id')
            version_number = response.get('version')
            if version_id and version_number >= 1 and response.get('status') == 'draft':
                self.log(f"✅ Version {version_number} created as draft:")
                self.log(f"   - version_id: {version_id}")
                self.log(f"   - version: {response['version']}")
                self.log(f"   - status: {response['status']}")
            else:
                self.log(f"❌ Version creation response incorrect: {response}")
                return False
        else:
            return False
        
        # List versions to verify
        success, response = self.run_test(
            f"GET /api/admin/catalog/products/{self.product_id}/versions",
            "GET",
            f"api/admin/catalog/products/{self.product_id}/versions",
            200
        )
        
        if success:
            versions = response.get('items', [])
            if len(versions) >= 1:
                # Find our version
                our_version = None
                for v in versions:
                    if v.get('version_id') == version_id:
                        our_version = v
                        break
                
                if our_version and our_version.get('status') == 'draft':
                    self.log(f"✅ Version found in list with correct status")
                else:
                    self.log(f"❌ Version status incorrect in list: {our_version}")
                    return False
            else:
                self.log(f"❌ No versions found in list")
                return False
        else:
            return False
        
        # Check if product is active before publishing
        success, response = self.run_test(
            f"GET /api/admin/catalog/products?limit=50",
            "GET",
            "api/admin/catalog/products?limit=50",
            200
        )
        
        product_status = None
        if success:
            for item in response.get('items', []):
                if item.get('product_id') == self.product_id:
                    product_status = item.get('status')
                    break
        
        if product_status != 'active':
            # Test publish with inactive product (should fail)
            success, response = self.run_test(
                f"POST /api/admin/catalog/products/{self.product_id}/versions/{version_id}/publish (inactive product)",
                "POST",
                f"api/admin/catalog/products/{self.product_id}/versions/{version_id}/publish",
                409
            )
            
            if success and 'product_not_active' in str(response).lower():
                self.log(f"✅ Publish correctly blocked for inactive product")
                
                # Activate product
                success, response = self.run_test(
                    f"PUT /api/admin/catalog/products/{self.product_id} (activate)",
                    "PUT",
                    f"api/admin/catalog/products/{self.product_id}",
                    200,
                    data={"status": "active"}
                )
                
                if not success:
                    self.log(f"❌ Failed to activate product")
                    return False
            else:
                self.log(f"❌ Expected product_not_active error, got: {response}")
                return False
        
        # Now publish the version
        success, response = self.run_test(
            f"POST /api/admin/catalog/products/{self.product_id}/versions/{version_id}/publish",
            "POST",
            f"api/admin/catalog/products/{self.product_id}/versions/{version_id}/publish",
            200
        )
        
        if success:
            if response.get('status') == 'published':
                self.log(f"✅ Version published successfully:")
                self.log(f"   - status: {response['status']}")
                self.log(f"   - published_version: {response.get('published_version')}")
                return True
            else:
                self.log(f"❌ Publish response incorrect: {response}")
                return False
        else:
            return False

    def print_summary(self):
        """Print test summary"""
        self.log("\n" + "="*60)
        self.log("A-EPIC ADMIN CATALOG BACKEND TEST SUMMARY")
        self.log("="*60)
        self.log(f"Total Tests: {self.tests_run}")
        self.log(f"✅ Passed: {self.tests_passed}")
        self.log(f"❌ Failed: {self.tests_failed}")
        self.log(f"Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        
        if self.failed_tests:
            self.log("\n❌ FAILED TESTS:")
            for i, test in enumerate(self.failed_tests, 1):
                self.log(f"  {i}. {test}")
        
        self.log("="*60)

    def run_admin_catalog_epic_tests(self):
        """Run all A-epic admin catalog tests"""
        self.log("🚀 Starting A-epic Admin Catalog Backend Tests")
        self.log(f"Base URL: {self.base_url}")
        
        # Authentication
        if not self.test_admin_login():
            self.log("❌ Admin login failed - stopping tests")
            self.print_summary()
            return 1

        # Setup product for testing
        if not self.test_setup_product():
            self.log("❌ Product setup failed - stopping tests")
            self.print_summary()
            return 1

        # 1) Cancellation policies
        if not self.test_cancellation_policies():
            self.log("❌ Cancellation policies test failed")

        # 2) Room types
        if not self.test_room_types():
            self.log("❌ Room types test failed")

        # 3) Rate plans
        if not self.test_rate_plans():
            self.log("❌ Rate plans test failed")

        # 4) Version create/publish with referential integrity
        if not self.test_version_create_and_publish():
            self.log("❌ Version create/publish test failed")

        # Summary
        self.print_summary()

        return 0 if self.tests_failed == 0 else 1


if __name__ == "__main__":
    tester = AdminCatalogEpicTester()
    exit_code = tester.run_admin_catalog_epic_tests()
    sys.exit(exit_code)