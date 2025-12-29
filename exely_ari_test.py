#!/usr/bin/env python3
"""
Exely ARI Read Backend Test for Acenta Master
Tests the GET /api/channels/connectors/{id}/ari endpoint with success and CONFIG_ERROR scenarios
"""
import requests
import sys
import uuid
from datetime import datetime

class ExelyAriTester:
    def __init__(self, base_url="http://localhost:8001"):
        self.base_url = base_url
        self.admin_token = None
        self.hotel_token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.failed_tests = []
        
        # Store created IDs for testing
        self.hotel_id = None
        self.connector_id = None

    def log(self, msg):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    def run_test(self, name, method, endpoint, expected_status, data=None, headers_override=None, token=None, params=None):
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
                response = requests.get(url, headers=headers, params=params, timeout=15)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=15)
            elif method == 'PATCH':
                response = requests.patch(url, json=data, headers=headers, timeout=15)
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

    def test_admin_login(self):
        """Test super admin login"""
        self.log("\n=== 1) SETUP: ADMIN LOGIN ===")
        success, response = self.run_test(
            "Super Admin Login (admin@acenta.test/admin123)",
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
            
            if 'super_admin' in roles:
                self.log(f"✅ Super admin login successful - roles: {roles}")
                return True
            else:
                self.log(f"❌ Missing super_admin role: {roles}")
                return False
        return False

    def test_hotel_package_setup(self):
        """Ensure at least one hotel has package=channel"""
        self.log("\n=== 2) SETUP: HOTEL PACKAGE=CHANNEL ===")
        # First get list of hotels
        success, response = self.run_test(
            "Get Hotels List",
            "GET",
            "api/admin/hotels",
            200,
            token=self.admin_token
        )
        
        if not success or not response:
            self.log("❌ No hotels found")
            return False
            
        hotels = response  # Response is directly a list
        self.log(f"Found {len(hotels)} hotels")
        
        # Find first hotel and set package=channel
        hotel = hotels[0]
        self.hotel_id = hotel['id']
        
        success, response = self.run_test(
            f"Set Hotel Package to Channel (hotel_id: {self.hotel_id})",
            "PATCH",
            f"api/admin/hotels/{self.hotel_id}/package",
            200,
            data={"package": "channel"},
            token=self.admin_token
        )
        
        if success:
            self.log(f"✅ Hotel {self.hotel_id} package set to channel")
            return True
        return False

    def test_hotel_login(self):
        """Test hotel admin login"""
        self.log("\n=== 3) SETUP: HOTEL LOGIN ===")
        success, response = self.run_test(
            "Hotel Admin Login (hoteladmin@acenta.test/admin123)",
            "POST",
            "api/auth/login",
            200,
            data={"email": "hoteladmin@acenta.test", "password": "admin123"},
            headers_override={'Content-Type': 'application/json'}
        )
        if success and 'access_token' in response:
            self.hotel_token = response['access_token']
            user = response.get('user', {})
            hotel_id = user.get('hotel_id')
            roles = user.get('roles', [])
            
            if hotel_id and 'hotel_admin' in roles:
                self.log(f"✅ Hotel admin login successful - hotel_id: {hotel_id}, roles: {roles}")
                return True
            else:
                self.log(f"❌ Missing hotel_id or hotel_admin role: {hotel_id}, {roles}")
                return False
        return False

    def cleanup_existing_connectors(self):
        """Clean up any existing connectors to ensure clean test state"""
        self.log("\n=== 4) SETUP: CLEANUP EXISTING CONNECTORS ===")
        success, response = self.run_test(
            "Get Existing Connectors",
            "GET",
            "api/channels/connectors",
            200,
            token=self.hotel_token
        )
        
        if success and response.get('items'):
            connectors = response['items']
            self.log(f"Found {len(connectors)} existing connectors to clean up")
            for connector in connectors:
                connector_id = connector['_id']
                success, _ = self.run_test(
                    f"Delete Existing Connector {connector_id}",
                    "DELETE",
                    f"api/channels/connectors/{connector_id}",
                    200,
                    token=self.hotel_token
                )
                if success:
                    self.log(f"✅ Deleted connector {connector_id}")
                else:
                    self.log(f"⚠️ Could not delete connector {connector_id}")
        else:
            self.log("✅ No existing connectors to clean up")
        return True

    def test_create_exely_connector(self):
        """Create Exely connector with proper configuration"""
        self.log("\n=== 5) CREATE EXELY CONNECTOR ===")
        
        # Create Exely connector with proper settings
        success, response = self.run_test(
            "Create Exely Connector",
            "POST",
            "api/channels/connectors",
            200,
            data={
                "provider": "exely",
                "display_name": "Exely",
                "credentials": {"api_key": "dummy-key"},
                "capabilities": ["ARI_read"],
                "settings": {
                    "base_url": "https://example.invalid",
                    "ari_path": "/ari"
                }
            },
            token=self.hotel_token
        )
        
        if not success:
            return False
            
        self.connector_id = response.get('_id')
        self.log(f"✅ Created Exely connector: {self.connector_id}")
        
        # Verify connector was created with correct settings
        if response.get('provider') != 'exely':
            self.log(f"❌ Expected provider 'exely', got: {response.get('provider')}")
            return False
            
        if 'ARI_read' not in response.get('capabilities', []):
            self.log(f"❌ Expected ARI_read capability, got: {response.get('capabilities')}")
            return False
            
        return True

    def test_ari_success_path(self):
        """Test ARI endpoint with proper configuration (mocked success)"""
        self.log("\n=== 6) ARI ENDPOINT: SUCCESS PATH (MOCKED) ===")
        
        if not self.connector_id:
            self.log("❌ No connector available for ARI test")
            return False
        
        # Test ARI endpoint - this will likely return PROVIDER_UNAVAILABLE since it's mocked
        # but we want to verify the response structure
        success, response = self.run_test(
            "GET ARI Data (Success Path)",
            "GET",
            f"api/channels/connectors/{self.connector_id}/ari",
            200,
            params={
                "from_date": "2026-03-10T00:00:00",
                "to_date": "2026-03-12T00:00:00"
            },
            token=self.hotel_token
        )
        
        if not success:
            self.log("❌ ARI endpoint call failed")
            return False
        
        # Verify response structure
        required_fields = ['ok', 'code', 'message', 'run_id', 'data']
        for field in required_fields:
            if field not in response:
                self.log(f"❌ Missing required field '{field}' in response")
                return False
        
        self.log(f"✅ ARI response structure valid: ok={response.get('ok')}, code={response.get('code')}")
        
        # Verify channel_sync_runs entry was created
        success, runs_response = self.run_test(
            "Check ARI Sync Runs",
            "GET",
            f"api/channels/connectors/{self.connector_id}/runs",
            200,
            params={"limit": 5},
            token=self.hotel_token
        )
        
        if success and runs_response.get('items'):
            runs = runs_response['items']
            ari_runs = [run for run in runs if run.get('type') == 'ari_read']
            if ari_runs:
                self.log(f"✅ Found {len(ari_runs)} ARI sync run(s)")
                return True
            else:
                self.log(f"❌ No ARI sync runs found, available types: {[run.get('type') for run in runs]}")
                return False
        else:
            self.log("❌ No sync runs found")
            return False

    def test_ari_config_error_path(self):
        """Test ARI endpoint with CONFIG_ERROR (empty base_url)"""
        self.log("\n=== 7) ARI ENDPOINT: CONFIG_ERROR PATH ===")
        
        if not self.connector_id:
            self.log("❌ No connector available for CONFIG_ERROR test")
            return False
        
        # Update connector to have empty base_url
        success, response = self.run_test(
            "Update Connector - Empty base_url",
            "PATCH",
            f"api/channels/connectors/{self.connector_id}",
            200,
            data={"settings": {"base_url": ""}},
            token=self.hotel_token
        )
        
        if not success:
            self.log("❌ Failed to update connector settings")
            return False
        
        self.log("✅ Updated connector with empty base_url")
        
        # Test ARI endpoint - should return CONFIG_ERROR
        success, response = self.run_test(
            "GET ARI Data (CONFIG_ERROR Path)",
            "GET",
            f"api/channels/connectors/{self.connector_id}/ari",
            200,
            params={
                "from_date": "2026-03-10T00:00:00",
                "to_date": "2026-03-12T00:00:00"
            },
            token=self.hotel_token
        )
        
        if not success:
            self.log("❌ ARI endpoint call failed")
            return False
        
        # Verify CONFIG_ERROR response
        if response.get('ok') != False:
            self.log(f"❌ Expected ok=false, got: {response.get('ok')}")
            return False
        
        code = response.get('code', '').upper()
        if code != 'CONFIG_ERROR':
            self.log(f"❌ Expected code='CONFIG_ERROR', got: '{code}'")
            return False
        
        message = response.get('message', '')
        if 'base_url tanımlı değil' not in message:
            self.log(f"❌ Expected message to contain 'base_url tanımlı değil', got: '{message}'")
            return False
        
        self.log(f"✅ CONFIG_ERROR response correct: ok={response.get('ok')}, code={code}")
        
        # Verify another channel_sync_runs entry was created
        success, runs_response = self.run_test(
            "Check CONFIG_ERROR Sync Runs",
            "GET",
            f"api/channels/connectors/{self.connector_id}/runs",
            200,
            params={"limit": 5},
            token=self.hotel_token
        )
        
        if success and runs_response.get('items'):
            runs = runs_response['items']
            ari_runs = [run for run in runs if run.get('type') == 'ari_read']
            if len(ari_runs) >= 2:
                self.log(f"✅ Found {len(ari_runs)} ARI sync runs (including CONFIG_ERROR)")
                return True
            else:
                self.log(f"❌ Expected at least 2 ARI sync runs, found: {len(ari_runs)}")
                return False
        else:
            self.log("❌ No sync runs found")
            return False

    def run_all_tests(self):
        """Run all test scenarios"""
        self.log("🚀 Starting Exely ARI Read Backend Test")
        self.log("=" * 80)
        self.log(f"Base URL: {self.base_url}")
        
        # Test sequence
        tests = [
            ("Admin Login", self.test_admin_login),
            ("Hotel Package Setup", self.test_hotel_package_setup),
            ("Hotel Login", self.test_hotel_login),
            ("Cleanup Connectors", self.cleanup_existing_connectors),
            ("Create Exely Connector", self.test_create_exely_connector),
            ("ARI Success Path", self.test_ari_success_path),
            ("ARI CONFIG_ERROR Path", self.test_ari_config_error_path),
        ]
        
        for test_name, test_func in tests:
            try:
                if not test_func():
                    self.log(f"❌ {test_name} failed - stopping test suite")
                    break
            except Exception as e:
                self.log(f"❌ {test_name} crashed: {str(e)}")
                self.tests_failed += 1
                self.failed_tests.append(f"{test_name} - Crashed: {str(e)}")
                break
        
        # Final summary
        self.log("\n" + "=" * 80)
        self.log("📊 EXELY ARI READ TEST SUMMARY")
        self.log("=" * 80)
        self.log(f"Total Tests: {self.tests_run}")
        self.log(f"✅ Passed: {self.tests_passed}")
        self.log(f"❌ Failed: {self.tests_failed}")
        
        if self.tests_failed > 0:
            self.log("\n🚨 FAILED TESTS:")
            for failed in self.failed_tests:
                self.log(f"   • {failed}")
        
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        self.log(f"\n📈 Success Rate: {success_rate:.1f}%")
        
        if self.tests_failed == 0:
            self.log("🎉 ALL TESTS PASSED! Exely ARI Read functionality is working correctly.")
            return True
        else:
            self.log("💥 SOME TESTS FAILED! Exely ARI Read needs attention.")
            return False

if __name__ == "__main__":
    # Use the local backend URL
    base_url = "http://localhost:8001"
    
    tester = ExelyAriTester(base_url)
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)