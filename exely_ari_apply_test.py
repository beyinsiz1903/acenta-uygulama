#!/usr/bin/env python3
"""
Exely ARI Apply endpoint smoke test for Acenta Master
Tests the complete flow: setup connector + mappings + dry_run + idempotency + non-dry-run
"""
import requests
import sys
import uuid
from datetime import datetime, timedelta

class ExelyAriApplyTester:
    def __init__(self, base_url="http://localhost:8001"):
        self.base_url = base_url
        self.super_admin_token = None
        self.hotel_admin_token = None
        self.connector_id = None
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
        self.log("\n=== A) SETUP - SUPER ADMIN ===")
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

    def test_setup_hotel_package(self):
        """Get hotels list and make first hotel a package"""
        self.log("\n--- Setup Hotel Package ---")
        
        # Get hotels list
        success, response = self.run_test(
            "Get Admin Hotels List",
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
        hotel_id = hotel.get('id')
        self.log(f"✅ Using hotel: {hotel.get('hotel_name')} (ID: {hotel_id})")
        
        # Make hotel a package
        success, response = self.run_test(
            "Make Hotel Package",
            "POST",
            f"api/admin/hotels/{hotel_id}/package",
            200,
            token=self.super_admin_token
        )
        
        if success:
            self.log(f"✅ Hotel {hotel_id} made into package")
            return True
        return False

    def test_hotel_admin_login(self):
        """Test hotel admin login"""
        self.log("\n=== B) SETUP - HOTEL ADMIN ===")
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

    def test_cleanup_existing_connectors(self):
        """Delete all existing channel connectors"""
        self.log("\n--- Cleanup Existing Connectors ---")
        
        # Get existing connectors
        success, response = self.run_test(
            "List Existing Connectors",
            "GET",
            "api/channels/connectors",
            200,
            token=self.hotel_admin_token
        )
        
        if not success:
            return False
            
        connectors = response.get('items', []) if isinstance(response, dict) else []
        
        if not connectors:
            self.log("✅ No existing connectors to cleanup")
            return True
            
        # Delete each connector
        for connector in connectors:
            connector_id = connector.get('_id')
            success, response = self.run_test(
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

    def test_create_exely_connector(self):
        """Create a new Exely connector"""
        self.log("\n--- Create Exely Connector ---")
        
        connector_data = {
            "provider": "exely",
            "display_name": "Exely",
            "credentials": {"api_key": "dummy-key"},
            "capabilities": ["ARI_read", "ARI_write"],
            "settings": {"base_url": "https://example.invalid", "ari_path": "/ari"}
        }
        
        success, response = self.run_test(
            "Create Exely Connector",
            "POST",
            "api/channels/connectors",
            200,
            data=connector_data,
            token=self.hotel_admin_token
        )
        
        if success and response.get('_id'):
            self.connector_id = response['_id']
            self.log(f"✅ Exely connector created with ID: {self.connector_id}")
            return True
        return False

    def test_create_mappings(self):
        """Create basic room_type and rate_plan mappings"""
        self.log("\n--- Create Mappings ---")
        
        if not self.connector_id:
            self.log("❌ No connector ID available for mappings")
            return False
            
        mappings_data = {
            "room_type_mappings": [
                {
                    "pms_room_type_id": "dummy_room",
                    "channel_room_type_id": "CH-ROOM-1",
                    "channel_room_name": "STD",
                    "active": True
                }
            ],
            "rate_plan_mappings": [
                {
                    "pms_rate_plan_id": "dummy_rate",
                    "channel_rate_plan_id": "CH-RATE-1",
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
            self.log(f"✅ Mappings created for connector {self.connector_id}")
            return True
        return False

    def test_ari_apply_dry_run(self):
        """Test Exely ARI Apply with dry_run=1"""
        self.log("\n=== C) EXELY ARI APPLY - DRY RUN ===")
        
        if not self.connector_id:
            self.log("❌ No connector ID available for ARI apply")
            return False
            
        ari_data = {
            "from_date": "2026-03-10",
            "to_date": "2026-03-12",
            "mode": "rates_and_availability"
        }
        
        success, response = self.run_test(
            "ARI Apply Dry Run",
            "POST",
            f"api/channels/connectors/{self.connector_id}/ari/apply?dry_run=1",
            200,
            data=ari_data,
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
                
        # Verify summary fields
        summary = response.get('summary', {})
        expected_summary_fields = ['from_date', 'to_date', 'mode', 'dry_run']
        for field in expected_summary_fields:
            if field not in summary:
                self.log(f"❌ Missing summary field: {field}")
                return False
                
        # Verify summary values
        if summary.get('from_date') != "2026-03-10":
            self.log(f"❌ Wrong from_date: {summary.get('from_date')}")
            return False
            
        if summary.get('to_date') != "2026-03-12":
            self.log(f"❌ Wrong to_date: {summary.get('to_date')}")
            return False
            
        if summary.get('mode') != "rates_and_availability":
            self.log(f"❌ Wrong mode: {summary.get('mode')}")
            return False
            
        if not summary.get('dry_run'):
            self.log(f"❌ Wrong dry_run flag: {summary.get('dry_run')}")
            return False
            
        run_id = response.get('run_id')
        status = response.get('status')
        ok = response.get('ok')
        
        self.log(f"✅ ARI Apply dry run completed - ok: {ok}, status: {status}, run_id: {run_id}")
        
        # Store run_id for idempotency test
        self.first_run_id = run_id
        self.first_response = response
        
        # Note: Since this is a mocked Exely endpoint, we expect either:
        # - ok=false, status="failed", error.code="PROVIDER_UNAVAILABLE" or "TIMEOUT"
        # - But the channel_sync_runs record should still be created
        
        if not ok and status == "failed":
            error = response.get('error', {})
            error_code = error.get('code')
            if error_code in ['PROVIDER_UNAVAILABLE', 'TIMEOUT']:
                self.log(f"✅ Expected error for mocked endpoint: {error_code}")
            else:
                self.log(f"⚠️  Unexpected error code: {error_code}")
        
        return True

    def test_idempotency_check(self):
        """Test idempotency by calling the same dry_run again"""
        self.log("\n=== D) IDEMPOTENCY VERIFICATION ===")
        
        if not self.connector_id or not hasattr(self, 'first_run_id'):
            self.log("❌ No connector ID or first run ID available for idempotency test")
            return False
            
        # Call the exact same endpoint with same parameters
        ari_data = {
            "from_date": "2026-03-10",
            "to_date": "2026-03-12",
            "mode": "rates_and_availability"
        }
        
        success, response = self.run_test(
            "ARI Apply Dry Run (Idempotency Check)",
            "POST",
            f"api/channels/connectors/{self.connector_id}/ari/apply?dry_run=1",
            200,
            data=ari_data,
            token=self.hotel_admin_token
        )
        
        if not success:
            return False
            
        # Verify same run_id is returned
        second_run_id = response.get('run_id')
        if second_run_id != self.first_run_id:
            self.log(f"❌ Idempotency failed - different run_id: {second_run_id} vs {self.first_run_id}")
            return False
            
        # Verify same summary and diff are returned
        first_summary = self.first_response.get('summary', {})
        second_summary = response.get('summary', {})
        
        if first_summary != second_summary:
            self.log(f"❌ Idempotency failed - different summary")
            return False
            
        first_diff = self.first_response.get('diff', {})
        second_diff = response.get('diff', {})
        
        if first_diff != second_diff:
            self.log(f"❌ Idempotency failed - different diff")
            return False
            
        self.log(f"✅ Idempotency working - same run_id returned: {second_run_id}")
        return True

    def test_non_dry_run(self):
        """Test non-dry-run if fetch_ari works"""
        self.log("\n=== E) NON-DRY-RUN TEST (if applicable) ===")
        
        if not self.connector_id:
            self.log("❌ No connector ID available for non-dry-run test")
            return False
            
        # Use different dates to avoid idempotency conflict
        ari_data = {
            "from_date": "2026-03-15",
            "to_date": "2026-03-17",
            "mode": "rates_and_availability"
        }
        
        success, response = self.run_test(
            "ARI Apply Non-Dry-Run",
            "POST",
            f"api/channels/connectors/{self.connector_id}/ari/apply?dry_run=0",
            200,
            data=ari_data,
            token=self.hotel_admin_token
        )
        
        if not success:
            return False
            
        # Verify response structure
        ok = response.get('ok')
        status = response.get('status')
        run_id = response.get('run_id')
        
        self.log(f"✅ Non-dry-run completed - ok: {ok}, status: {status}, run_id: {run_id}")
        
        # For mocked endpoint, we expect similar behavior as dry-run
        # The key difference would be that if it succeeded, it would write to PMS collections
        # But since it's mocked, we expect PROVIDER_UNAVAILABLE or similar
        
        if not ok and status == "failed":
            error = response.get('error', {})
            error_code = error.get('code')
            if error_code in ['PROVIDER_UNAVAILABLE', 'TIMEOUT']:
                self.log(f"✅ Expected error for mocked endpoint: {error_code}")
            else:
                self.log(f"⚠️  Unexpected error code: {error_code}")
        elif ok and status in ["success", "partial"]:
            self.log(f"✅ Unexpected success - PMS data should be written to collections")
            # In a real scenario, we would verify pms_daily_rates and pms_daily_availability collections
        
        return True

    def print_summary(self):
        """Print test summary"""
        self.log("\n" + "="*60)
        self.log("EXELY ARI APPLY ENDPOINT TEST SUMMARY")
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
        """Run all Exely ARI Apply tests in sequence"""
        self.log("🚀 Starting Exely ARI Apply Endpoint Backend Smoke Tests")
        self.log(f"Base URL: {self.base_url}")
        
        # A) Setup - Super Admin
        if not self.test_super_admin_login():
            self.log("❌ Super admin login failed - stopping tests")
            self.print_summary()
            return 1
            
        if not self.test_setup_hotel_package():
            self.log("❌ Hotel package setup failed - continuing anyway")
        
        # B) Setup - Hotel Admin
        if not self.test_hotel_admin_login():
            self.log("❌ Hotel admin login failed - stopping tests")
            self.print_summary()
            return 1
            
        if not self.test_cleanup_existing_connectors():
            self.log("❌ Connector cleanup failed - continuing anyway")
        
        if not self.test_create_exely_connector():
            self.log("❌ Exely connector creation failed - stopping tests")
            self.print_summary()
            return 1
            
        if not self.test_create_mappings():
            self.log("❌ Mappings creation failed - stopping tests")
            self.print_summary()
            return 1
        
        # C) ARI Apply Tests
        if not self.test_ari_apply_dry_run():
            self.log("❌ ARI Apply dry run failed")
        
        if not self.test_idempotency_check():
            self.log("❌ Idempotency check failed")
        
        if not self.test_non_dry_run():
            self.log("❌ Non-dry-run test failed")
        
        # Summary
        self.print_summary()
        
        return 0 if self.tests_failed == 0 else 1


if __name__ == "__main__":
    tester = ExelyAriApplyTester()
    exit_code = tester.run_all_tests()
    sys.exit(exit_code)