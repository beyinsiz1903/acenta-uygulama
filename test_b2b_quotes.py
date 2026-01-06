#!/usr/bin/env python3
"""
B2B Quotes Endpoint Test using FastAPI TestClient
Tests the POST /api/b2b/quotes endpoint with various scenarios
"""

import sys
import os
import asyncio
from datetime import datetime, date, timedelta
from fastapi.testclient import TestClient

# Add backend directory to path
sys.path.insert(0, '/app/backend')

from server import app

class B2BQuotesTestClient:
    def __init__(self):
        self.client = TestClient(app)
        self.agency_token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.failed_tests = []
        
        # Test data
        self.organization_id = "demo"
        self.agency_id = None
        self.product_id = None
        self.channel_id = "web"

    def log(self, msg):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    def run_test(self, name, expected_status, test_func):
        """Run a single test"""
        self.tests_run += 1
        self.log(f"🔍 Test #{self.tests_run}: {name}")
        
        try:
            success, response = test_func()
            
            if success and response.status_code == expected_status:
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

    def test_agency_login(self):
        """Test agency admin login"""
        self.log("\n=== AUTHENTICATION ===")
        
        def login_test():
            response = self.client.post(
                "/api/auth/login",
                json={"email": "agency1@demo.test", "password": "agency123"}
            )
            return True, response
        
        success, response_data = self.run_test(
            "Agency Admin Login (agency1@demo.test/agency123)",
            200,
            login_test
        )
        
        if success and 'access_token' in response_data:
            self.agency_token = response_data['access_token']
            user = response_data.get('user', {})
            roles = user.get('roles', [])
            self.agency_id = user.get('agency_id')
            
            if 'agency_admin' in roles and self.agency_id:
                self.log(f"✅ Agency login successful - roles: {roles}, agency_id: {self.agency_id}")
                return True
            else:
                self.log(f"❌ Missing agency_admin role or agency_id: roles={roles}, agency_id={self.agency_id}")
                return False
        return False

    def setup_test_data(self):
        """Setup test data - find existing product and create inventory"""
        self.log("\n=== SETUP TEST DATA ===")
        
        # Use a known product ID from demo data
        self.product_id = "demo_product_1"  # Use demo product
        self.log(f"✅ Using demo product: {self.product_id}")

        # Create inventory for testing
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        day_after = (date.today() + timedelta(days=2)).isoformat()
        
        # Create available inventory
        def create_inventory_available():
            response = self.client.post(
                "/api/inventory/upsert",
                json={
                    "product_id": self.product_id,
                    "date": tomorrow,
                    "capacity_total": 10,
                    "capacity_available": 5,
                    "price": 150.0,
                    "restrictions": {"closed": False}
                },
                headers={"Authorization": f"Bearer {self.agency_token}"}
            )
            return True, response
        
        success, _ = self.run_test(
            "Create Available Inventory",
            200,
            create_inventory_available
        )
        
        # Create unavailable inventory (capacity_available=0)
        def create_inventory_unavailable():
            response = self.client.post(
                "/api/inventory/upsert",
                json={
                    "product_id": self.product_id,
                    "date": day_after,
                    "capacity_total": 10,
                    "capacity_available": 0,
                    "price": 150.0,
                    "restrictions": {"closed": False}
                },
                headers={"Authorization": f"Bearer {self.agency_token}"}
            )
            return True, response
        
        success2, _ = self.run_test(
            "Create Unavailable Inventory (capacity=0)",
            200,
            create_inventory_unavailable
        )
        
        return success and success2

    def test_scenario_1_validation_errors(self):
        """Test 422 Validation - missing channel_id or empty items"""
        self.log("\n=== SCENARIO 1: 422 VALIDATION ERRORS ===")
        
        # Test 1.1: Missing channel_id
        def test_missing_channel_id():
            response = self.client.post(
                "/api/b2b/quotes",
                json={
                    "items": [{
                        "product_id": self.product_id,
                        "room_type_id": "standard",
                        "rate_plan_id": "base",
                        "check_in": (date.today() + timedelta(days=1)).isoformat(),
                        "check_out": (date.today() + timedelta(days=2)).isoformat(),
                        "occupancy": 2
                    }]
                },
                headers={"Authorization": f"Bearer {self.agency_token}"}
            )
            return True, response
        
        success1, response_data1 = self.run_test(
            "Missing channel_id (expect 422)",
            422,
            test_missing_channel_id
        )
        
        if success1:
            error = response_data1.get('error', {})
            if error.get('code') == 'validation_error':
                self.log(f"✅ Correct validation error for missing channel_id")
            else:
                self.log(f"❌ Expected validation_error, got: {error}")
        
        # Test 1.2: Empty items array
        def test_empty_items():
            response = self.client.post(
                "/api/b2b/quotes",
                json={
                    "channel_id": self.channel_id,
                    "items": []
                },
                headers={"Authorization": f"Bearer {self.agency_token}"}
            )
            return True, response
        
        success2, response_data2 = self.run_test(
            "Empty items array (expect 422)",
            422,
            test_empty_items
        )
        
        if success2:
            error = response_data2.get('error', {})
            if error.get('code') == 'validation_error':
                self.log(f"✅ Correct validation error for empty items")
            else:
                self.log(f"❌ Expected validation_error, got: {error}")
        
        return success1 and success2

    def test_scenario_2_product_not_available(self):
        """Test 409 product_not_available - invalid product_id or status!=active"""
        self.log("\n=== SCENARIO 2: 409 PRODUCT_NOT_AVAILABLE ===")
        
        # Test 2.1: Invalid product_id
        def test_invalid_product_id():
            response = self.client.post(
                "/api/b2b/quotes",
                json={
                    "channel_id": self.channel_id,
                    "items": [{
                        "product_id": "invalid_product_id_12345",
                        "room_type_id": "standard",
                        "rate_plan_id": "base",
                        "check_in": (date.today() + timedelta(days=1)).isoformat(),
                        "check_out": (date.today() + timedelta(days=2)).isoformat(),
                        "occupancy": 2
                    }]
                },
                headers={"Authorization": f"Bearer {self.agency_token}"}
            )
            return True, response
        
        success, response_data = self.run_test(
            "Invalid product_id (expect 409)",
            409,
            test_invalid_product_id
        )
        
        if success:
            error = response_data.get('error', {})
            if error.get('code') == 'product_not_available':
                self.log(f"✅ Correct error code: product_not_available")
                self.log(f"   Error message: {error.get('message')}")
                self.log(f"   Error details: {error.get('details')}")
                return True
            else:
                self.log(f"❌ Expected product_not_available, got: {error.get('code')}")
                return False
        
        return False

    def test_scenario_3_unavailable(self):
        """Test 409 unavailable - capacity_available=0 or restrictions.closed=true"""
        self.log("\n=== SCENARIO 3: 409 UNAVAILABLE ===")
        
        # Test 3.1: capacity_available=0
        def test_capacity_zero():
            response = self.client.post(
                "/api/b2b/quotes",
                json={
                    "channel_id": self.channel_id,
                    "items": [{
                        "product_id": self.product_id,
                        "room_type_id": "standard",
                        "rate_plan_id": "base",
                        "check_in": (date.today() + timedelta(days=2)).isoformat(),  # day_after with capacity=0
                        "check_out": (date.today() + timedelta(days=3)).isoformat(),
                        "occupancy": 2
                    }]
                },
                headers={"Authorization": f"Bearer {self.agency_token}"}
            )
            return True, response
        
        success, response_data = self.run_test(
            "Capacity available = 0 (expect 409)",
            409,
            test_capacity_zero
        )
        
        if success:
            error = response_data.get('error', {})
            if error.get('code') == 'unavailable':
                self.log(f"✅ Correct error code: unavailable")
                self.log(f"   Error message: {error.get('message')}")
                self.log(f"   Error details: {error.get('details')}")
                return True
            else:
                self.log(f"❌ Expected unavailable, got: {error.get('code')}")
                return False
        
        return False

    def test_scenario_4_happy_path(self):
        """Test Happy path - valid request with proper demo data"""
        self.log("\n=== SCENARIO 4: HAPPY PATH ===")
        
        def test_valid_quote():
            response = self.client.post(
                "/api/b2b/quotes",
                json={
                    "channel_id": self.channel_id,
                    "items": [{
                        "product_id": self.product_id,
                        "room_type_id": "standard",
                        "rate_plan_id": "base",
                        "check_in": (date.today() + timedelta(days=1)).isoformat(),  # tomorrow with capacity=5
                        "check_out": (date.today() + timedelta(days=2)).isoformat(),
                        "occupancy": 2
                    }],
                    "client_context": {"test": "happy_path"}
                },
                headers={"Authorization": f"Bearer {self.agency_token}"}
            )
            return True, response
        
        success, response_data = self.run_test(
            "Valid Quote Request (expect 200)",
            200,
            test_valid_quote
        )
        
        if success:
            # Verify response structure
            required_fields = ['quote_id', 'expires_at', 'offers']
            missing_fields = [field for field in required_fields if field not in response_data]
            
            if missing_fields:
                self.log(f"❌ Missing required fields: {missing_fields}")
                return False
            
            quote_id = response_data.get('quote_id')
            expires_at = response_data.get('expires_at')
            offers = response_data.get('offers', [])
            
            # Verify quote_id is string
            if not isinstance(quote_id, str) or not quote_id:
                self.log(f"❌ quote_id should be non-empty string, got: {quote_id}")
                return False
            
            # Verify expires_at is ISO datetime
            try:
                datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                self.log(f"✅ expires_at is valid ISO datetime: {expires_at}")
            except:
                self.log(f"❌ expires_at is not valid ISO datetime: {expires_at}")
                return False
            
            # Verify offers structure
            if len(offers) != 1:
                self.log(f"❌ Expected 1 offer, got {len(offers)}")
                return False
            
            offer = offers[0]
            if 'trace' not in offer:
                self.log(f"❌ Missing trace field in offer")
                return False
            
            trace = offer['trace']
            if 'applied_rules' not in trace:
                self.log(f"❌ Missing applied_rules in trace")
                return False
            
            applied_rules = trace['applied_rules']
            if not isinstance(applied_rules, list):
                self.log(f"❌ applied_rules should be list, got: {type(applied_rules)}")
                return False
            
            self.log(f"✅ Happy path successful:")
            self.log(f"   - quote_id: {quote_id}")
            self.log(f"   - expires_at: {expires_at}")
            self.log(f"   - offers count: {len(offers)}")
            self.log(f"   - offer currency: {offer.get('currency')}")
            self.log(f"   - offer net: {offer.get('net')}")
            self.log(f"   - offer sell: {offer.get('sell')}")
            self.log(f"   - trace.applied_rules: {applied_rules} (length: {len(applied_rules)})")
            
            return True
        
        return False

    def print_summary(self):
        """Print test summary"""
        self.log("\n" + "="*60)
        self.log("B2B QUOTES ENDPOINT TEST SUMMARY")
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

    def run_all_tests(self):
        """Run all B2B quotes tests"""
        self.log("🚀 Starting B2B Quotes Endpoint Tests (FastAPI TestClient)")
        self.log("Testing POST /api/b2b/quotes with various scenarios")
        
        # Authentication
        if not self.test_agency_login():
            self.log("❌ Agency login failed - stopping tests")
            self.print_summary()
            return 1

        # Setup test data
        if not self.setup_test_data():
            self.log("❌ Test data setup failed - stopping tests")
            self.print_summary()
            return 1

        # Test scenarios
        self.test_scenario_1_validation_errors()
        self.test_scenario_2_product_not_available()
        self.test_scenario_3_unavailable()
        self.test_scenario_4_happy_path()

        # Summary
        self.print_summary()

        return 0 if self.tests_failed == 0 else 1


if __name__ == "__main__":
    tester = B2BQuotesTestClient()
    exit_code = tester.run_all_tests()
    sys.exit(exit_code)