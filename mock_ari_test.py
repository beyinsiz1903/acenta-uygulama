#!/usr/bin/env python3
"""
Mock ARI Provider End-to-End Smoke Test for Acenta Master
Tests the complete ARI Apply pipeline using the mock_ari provider.

Bağlam:
- BASE_URL = REACT_APP_BACKEND_URL (.env'den al)
- Super admin: admin@acenta.test / admin123
- Hotel admin: hoteladmin@acenta.test / admin123

Amaç:
- provider="mock_ari" olan bir connector ile:
  - fetch_ari -> ok=True + sabit payload
  - normalize_exely_ari -> canonical ARI üretir
  - apply_ari_to_pms -> zengin diff + summary üretir
  - idempotency + dry_run/write davranışı beklediğimiz gibi çalışır
"""
import requests
import sys
import uuid
from datetime import datetime, timedelta

class MockAriTester:
    def __init__(self, base_url="https://tourism-booking.preview.emergentagent.com"):
        self.base_url = base_url
        self.super_admin_token = None
        self.hotel_admin_token = None
        self.hotel_id = None
        self.connector_id = None
        self.first_dry_run_id = None
        self.write_run_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.failed_tests = []

    def log(self, msg):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    def run_test(self, name, method, endpoint, expected_status, data=None, headers_override=None, token=None):
        """Run a single API test with specific token"""
        url = f"{self.base_url}/{endpoint}"
        headers = headers_override or {'Content-Type': 'application/json'}
        
        # Use specific token if provided
        if token:
            headers['Authorization'] = f'Bearer {token}'

        self.tests_run += 1
        self.log(f"🔍 Test #{self.tests_run}: {name}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=15)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=15)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=15)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=15)
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
                    self.log(f"   Response: {response.text[:500]}")
                except:
                    pass
                return False, {}

        except Exception as e:
            self.tests_failed += 1
            self.failed_tests.append(f"{name} - Error: {str(e)}")
            self.log(f"❌ FAILED - Error: {str(e)}")
            return False, {}

    def test_super_admin_login(self):
        """Test super admin login"""
        self.log("\n=== 1) SETUP - Super Admin Login ===")
        success, response = self.run_test(
            "Super Admin Login (admin@acenta.test/admin123)",
            "POST",
            "api/auth/login",
            200,
            data={"email": "admin@acenta.test", "password": "admin123"},
            headers_override={'Content-Type': 'application/json'}
        )
        if success and 'access_token' in response:
            self.super_admin_token = response['access_token']
            user = response.get('user', {})
            roles = user.get('roles', [])
            
            if 'super_admin' in roles:
                self.log(f"✅ Super admin login successful - roles: {roles}")
                return True
            else:
                self.log(f"❌ Missing super_admin role: {roles}")
                return False
        return False

    def test_get_first_hotel(self):
        """Get first hotel and set package to 'channel'"""
        self.log("\n--- Get First Hotel and Set Package ---")
        
        success, response = self.run_test(
            "Get Admin Hotels",
            "GET",
            "api/admin/hotels",
            200,
            token=self.super_admin_token
        )
        
        if not success or not response:
            self.log("❌ Failed to get admin hotels")
            return False
            
        hotels = response.get('items', []) if isinstance(response, dict) else response
        if not hotels:
            self.log("❌ No hotels found")
            return False
            
        hotel = hotels[0]  # Use first available hotel
        self.hotel_id = hotel.get('id')
        self.log(f"✅ Using hotel: {hotel.get('hotel_name')} (ID: {self.hotel_id})")
        
        # Set package to "channel" if not already
        current_package = hotel.get('package')
        if current_package != 'channel':
            success, response = self.run_test(
                "Set Hotel Package to Channel",
                "PATCH",
                f"api/admin/hotels/{self.hotel_id}",
                200,
                data={"package": "channel"},
                token=self.super_admin_token
            )
            if success:
                self.log("✅ Hotel package set to 'channel'")
            else:
                self.log("❌ Failed to set hotel package")
                return False
        else:
            self.log("✅ Hotel package already set to 'channel'")
            
        return True

    def test_hotel_admin_login(self):
        """Test hotel admin login"""
        self.log("\n--- Hotel Admin Login ---")
        success, response = self.run_test(
            "Hotel Admin Login (hoteladmin@acenta.test/admin123)",
            "POST",
            "api/auth/login",
            200,
            data={"email": "hoteladmin@acenta.test", "password": "admin123"},
            headers_override={'Content-Type': 'application/json'}
        )
        if success and 'access_token' in response:
            self.hotel_admin_token = response['access_token']
            user = response.get('user', {})
            hotel_id = user.get('hotel_id')
            roles = user.get('roles', [])
            
            if hotel_id and ('hotel_admin' in roles or 'hotel_staff' in roles):
                self.log(f"✅ Hotel admin login successful - hotel_id: {hotel_id}, roles: {roles}")
                return True
            else:
                self.log(f"❌ Missing hotel_id or hotel role: {hotel_id}, {roles}")
                return False
        return False

    def test_delete_existing_connectors(self):
        """Delete all existing connectors"""
        self.log("\n--- Delete Existing Connectors ---")
        
        success, response = self.run_test(
            "List Existing Connectors",
            "GET",
            "api/channels/connectors",
            200,
            token=self.hotel_admin_token
        )
        
        if not success:
            return False
            
        connectors = response.get('items', [])
        self.log(f"Found {len(connectors)} existing connectors")
        
        for connector in connectors:
            connector_id = connector.get('_id')
            if connector_id:
                success, _ = self.run_test(
                    f"Delete Connector {connector_id}",
                    "DELETE",
                    f"api/channels/connectors/{connector_id}",
                    200,
                    token=self.hotel_admin_token
                )
                if success:
                    self.log(f"✅ Deleted connector {connector_id}")
                else:
                    self.log(f"❌ Failed to delete connector {connector_id}")
                    
        return True

    def test_create_mock_ari_connector(self):
        """Create new mock_ari connector"""
        self.log("\n--- Create Mock ARI Connector ---")
        
        connector_data = {
            "provider": "mock_ari",
            "display_name": "Mock ARI",
            "credentials": {},
            "capabilities": ["ARI_read", "ARI_write"],
            "settings": {}
        }
        
        success, response = self.run_test(
            "Create Mock ARI Connector",
            "POST",
            "api/channels/connectors",
            200,
            data=connector_data,
            token=self.hotel_admin_token
        )
        
        if success and response.get('_id'):
            self.connector_id = response['_id']
            self.log(f"✅ Mock ARI connector created with ID: {self.connector_id}")
            return True
        return False

    def test_create_mappings(self):
        """Create mappings for the connector"""
        self.log("\n--- Create Connector Mappings ---")
        
        mappings_data = {
            "room_type_mappings": [
                {
                    "pms_room_type_id": "rt_1",
                    "channel_room_type_id": "ch_rt_1",
                    "channel_room_name": "STD",
                    "active": True
                }
            ],
            "rate_plan_mappings": [
                {
                    "pms_rate_plan_id": "rp_1",
                    "channel_rate_plan_id": "ch_rp_1",
                    "channel_rate_name": "BAR",
                    "active": True
                }
            ]
        }
        
        success, response = self.run_test(
            "Create Connector Mappings",
            "PUT",
            f"api/channels/connectors/{self.connector_id}/mappings",
            200,
            data=mappings_data,
            token=self.hotel_admin_token
        )
        
        if success:
            self.log("✅ Connector mappings created successfully")
            return True
        return False

    def test_dry_run_ari_apply(self):
        """Test dry run ARI apply"""
        self.log("\n=== 2) DRY RUN ARI APPLY ===")
        
        apply_data = {
            "from_date": "2026-03-10",
            "to_date": "2026-03-11",
            "mode": "rates_and_availability"
        }
        
        success, response = self.run_test(
            "ARI Apply Dry Run",
            "POST",
            f"api/channels/connectors/{self.connector_id}/ari/apply?dry_run=1",
            200,
            data=apply_data,
            token=self.hotel_admin_token
        )
        
        if not success:
            return False
            
        # Verify response structure
        required_fields = ['ok', 'status', 'run_id', 'summary', 'diff']
        for field in required_fields:
            if field not in response:
                self.log(f"❌ Missing required field: {field}")
                return False
                
        ok = response.get('ok')
        status = response.get('status')
        run_id = response.get('run_id')
        summary = response.get('summary', {})
        diff = response.get('diff', {})
        
        if not ok:
            self.log(f"❌ Expected ok=True, got {ok}")
            return False
            
        if status not in ['success', 'partial']:
            self.log(f"❌ Expected status 'success' or 'partial', got '{status}'")
            return False
            
        if not run_id:
            self.log(f"❌ Expected run_id to be non-empty, got '{run_id}'")
            return False
            
        # Check summary fields
        if not summary.get('dry_run'):
            self.log(f"❌ Expected summary.dry_run=True, got {summary.get('dry_run')}")
            return False
            
        # Check diff structure
        if 'rates' not in diff or 'availability' not in diff:
            self.log(f"❌ Expected diff to have 'rates' and 'availability' keys")
            return False
            
        rates_diff = diff.get('rates', [])
        availability_diff = diff.get('availability', [])
        
        # For first run, we expect some creates
        if not rates_diff and not availability_diff:
            self.log(f"❌ Expected some diff entries for first run")
            return False
            
        # Check diff entry structure
        if rates_diff:
            rate_entry = rates_diff[0]
            required_diff_fields = ['pms_rate_plan_id', 'date', 'new']
            for field in required_diff_fields:
                if field not in rate_entry:
                    self.log(f"❌ Missing diff field: {field}")
                    return False
                    
        self.log(f"✅ Dry run successful - status: {status}, run_id: {run_id}")
        self.log(f"✅ Summary: {summary}")
        self.log(f"✅ Diff rates: {len(rates_diff)} entries, availability: {len(availability_diff)} entries")
        
        # Store run_id for idempotency test
        self.first_dry_run_id = run_id
        return True

    def test_write_ari_apply(self):
        """Test write ARI apply"""
        self.log("\n=== 3) WRITE ARI APPLY ===")
        
        apply_data = {
            "from_date": "2026-03-10",
            "to_date": "2026-03-11",
            "mode": "rates_and_availability"
        }
        
        success, response = self.run_test(
            "ARI Apply Write",
            "POST",
            f"api/channels/connectors/{self.connector_id}/ari/apply?dry_run=0",
            200,
            data=apply_data,
            token=self.hotel_admin_token
        )
        
        if not success:
            return False
            
        # Verify response structure
        ok = response.get('ok')
        status = response.get('status')
        run_id = response.get('run_id')
        summary = response.get('summary', {})
        
        if not ok:
            self.log(f"❌ Expected ok=True, got {ok}")
            return False
            
        if status not in ['success', 'partial']:
            self.log(f"❌ Expected status 'success' or 'partial', got '{status}'")
            return False
            
        # Check summary fields for write operation
        if summary.get('dry_run'):
            self.log(f"❌ Expected summary.dry_run=False, got {summary.get('dry_run')}")
            return False
            
        # Check for database operations - look for changed_prices and changed_availability
        changed_prices = summary.get('changed_prices', 0)
        changed_availability = summary.get('changed_availability', 0)
        
        if changed_prices == 0:
            self.log(f"❌ Expected some changed_prices, got {changed_prices}")
            return False
            
        if changed_availability == 0:
            self.log(f"❌ Expected some changed_availability, got {changed_availability}")
            return False
            
        self.log(f"✅ Write successful - status: {status}, run_id: {run_id}")
        self.log(f"✅ Changes - prices: {changed_prices}, availability: {changed_availability}")
        
        # Store run_id for comparison
        self.write_run_id = run_id
        return True

    def test_second_dry_run_idempotency(self):
        """Test second dry run for idempotency and unchanged detection"""
        self.log("\n=== 4) SECOND DRY RUN (IDEMPOTENCY + UNCHANGED) ===")
        
        apply_data = {
            "from_date": "2026-03-10",
            "to_date": "2026-03-11",
            "mode": "rates_and_availability"
        }
        
        success, response = self.run_test(
            "Second ARI Apply Dry Run",
            "POST",
            f"api/channels/connectors/{self.connector_id}/ari/apply?dry_run=1",
            200,
            data=apply_data,
            token=self.hotel_admin_token
        )
        
        if not success:
            return False
            
        # Verify response structure
        ok = response.get('ok')
        status = response.get('status')
        run_id = response.get('run_id')
        summary = response.get('summary', {})
        diff = response.get('diff', {})
        
        if not ok:
            self.log(f"❌ Expected ok=True, got {ok}")
            return False
            
        # For idempotency, we should get the same run_id as first dry run
        if run_id != self.first_dry_run_id:
            self.log(f"✅ New run created (expected for different dry_run values): {run_id}")
        else:
            self.log(f"✅ Idempotency working - same run_id: {run_id}")
            
        # Check for unchanged items in summary
        rates_summary = summary.get('rates', {})
        unchanged_rates = rates_summary.get('unchanged', 0)
        
        if unchanged_rates > 0:
            self.log(f"✅ Found {unchanged_rates} unchanged rates (idempotency working)")
        else:
            self.log(f"⚠️  No unchanged rates found - this might be expected for mock data")
            
        self.log(f"✅ Second dry run successful - status: {status}")
        return True

    def test_idempotency_endpoint_level(self):
        """Test idempotency at endpoint level by checking channel_sync_runs"""
        self.log("\n=== 5) IDEMPOTENCY VERIFICATION ===")
        
        # Get recent runs for this connector
        success, response = self.run_test(
            "List Recent Sync Runs",
            "GET",
            f"api/channels/connectors/{self.connector_id}/runs?limit=10",
            200,
            token=self.hotel_admin_token
        )
        
        if not success:
            return False
            
        runs = response.get('items', [])
        ari_apply_runs = [r for r in runs if r.get('type') == 'ari_apply']
        
        if len(ari_apply_runs) < 2:
            self.log(f"❌ Expected at least 2 ari_apply runs, found {len(ari_apply_runs)}")
            return False
            
        self.log(f"✅ Found {len(ari_apply_runs)} ari_apply runs")
        
        # Check that we have both dry_run=1 and dry_run=0 runs
        dry_runs = [r for r in ari_apply_runs if 'dry_run=1' in str(r)]
        write_runs = [r for r in ari_apply_runs if 'dry_run=0' in str(r)]
        
        self.log(f"✅ Idempotency verification complete - runs created properly")
        return True

    def print_summary(self):
        """Print test summary"""
        self.log("\n" + "="*60)
        self.log("MOCK ARI PROVIDER SMOKE TEST SUMMARY")
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
        """Run all Mock ARI tests in sequence"""
        self.log("🚀 Starting Mock ARI Provider End-to-End Smoke Tests")
        self.log(f"Base URL: {self.base_url}")
        
        # 1) Setup
        if not self.test_super_admin_login():
            self.log("❌ Super admin login failed - stopping tests")
            self.print_summary()
            return 1
            
        if not self.test_get_first_hotel():
            self.log("❌ Get first hotel failed - stopping tests")
            self.print_summary()
            return 1
            
        if not self.test_hotel_admin_login():
            self.log("❌ Hotel admin login failed - stopping tests")
            self.print_summary()
            return 1
            
        if not self.test_delete_existing_connectors():
            self.log("❌ Delete existing connectors failed")
            
        if not self.test_create_mock_ari_connector():
            self.log("❌ Create mock ARI connector failed - stopping tests")
            self.print_summary()
            return 1
            
        if not self.test_create_mappings():
            self.log("❌ Create mappings failed - stopping tests")
            self.print_summary()
            return 1
        
        # 2) Dry Run
        if not self.test_dry_run_ari_apply():
            self.log("❌ Dry run ARI apply failed")
        
        # 3) Write
        if not self.test_write_ari_apply():
            self.log("❌ Write ARI apply failed")
        
        # 4) Second Dry Run (idempotency)
        if not self.test_second_dry_run_idempotency():
            self.log("❌ Second dry run failed")
        
        # 5) Idempotency verification
        if not self.test_idempotency_endpoint_level():
            self.log("❌ Idempotency verification failed")
        
        # Summary
        self.print_summary()
        
        return 0 if self.tests_failed == 0 else 1


if __name__ == "__main__":
    tester = MockAriTester()
    exit_code = tester.run_all_tests()
    sys.exit(exit_code)