#!/usr/bin/env python3
"""
Channel Hub Provider Adapter Backend Smoke Test for Acenta Master
Tests the new provider adapter-based test_connection flow with all scenarios
"""
import requests
import sys
import uuid
from datetime import datetime

class ChannelHubTester:
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
        self.exely_connector_no_key_id = None
        self.exely_connector_with_key_id = None
        self.expedia_connector_id = None

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
        self.log("\n=== 1) SETUP: ENSURE HOTEL HAS PACKAGE=CHANNEL ===")
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
                
                # Clean up any existing connectors before starting tests
                self.cleanup_existing_connectors()
                return True
            else:
                self.log(f"❌ Missing hotel_id or hotel_admin role: {hotel_id}, {roles}")
                return False
        return False

    def cleanup_existing_connectors(self):
        """Clean up any existing connectors to ensure clean test state"""
        self.log("🧹 Cleaning up existing connectors...")
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

    def test_exely_auth_failed(self):
        """Test Exely connector with missing/empty api_key (AUTH_FAILED path)"""
        self.log("\n=== 2) EXELY CONNECTOR: AUTH_FAILED PATH ===")
        
        # Create Exely connector with missing api_key
        success, response = self.run_test(
            "Create Exely Connector (No API Key)",
            "POST",
            "api/channels/connectors",
            200,
            data={
                "provider": "exely",
                "display_name": "Exely No Key",
                "credentials": {}
            },
            token=self.hotel_token
        )
        
        if not success:
            return False
            
        self.exely_connector_no_key_id = response.get('_id')
        self.log(f"✅ Created Exely connector without key: {self.exely_connector_no_key_id}")
        
        # Test connection - should fail with AUTH_FAILED
        success, response = self.run_test(
            "Test Exely Connection (No API Key) - Expect 400 AUTH_FAILED",
            "POST",
            f"api/channels/connectors/{self.exely_connector_no_key_id}/test",
            400,
            token=self.hotel_token
        )
        
        if success:
            # Check error detail
            if response.get('detail', {}).get('code') == 'AUTH_FAILED':
                self.log("✅ Correct AUTH_FAILED error returned")
            else:
                self.log(f"❌ Expected AUTH_FAILED, got: {response}")
                return False
        else:
            return False
            
        # Verify channel_sync_runs entry
        success, response = self.run_test(
            "Check Sync Runs for AUTH_FAILED",
            "GET",
            f"api/channels/connectors/{self.exely_connector_no_key_id}/runs",
            200,
            token=self.hotel_token
        )
        
        if success and response.get('items'):
            run = response['items'][0]
            if run.get('status') == 'failed':
                self.log("✅ Sync run marked as failed")
            else:
                self.log(f"❌ Expected failed status, got: {run.get('status')}")
                return False
        else:
            self.log("❌ No sync runs found")
            return False
            
        # Verify connector status updated
        success, response = self.run_test(
            "Check Connector Status After AUTH_FAILED",
            "GET",
            f"api/channels/connectors/{self.exely_connector_no_key_id}",
            200,
            token=self.hotel_token
        )
        
        if success:
            if response.get('status') == 'error' and response.get('last_error', {}).get('code') == 'AUTH_FAILED':
                self.log("✅ Connector status updated to error with AUTH_FAILED")
                return True
            else:
                self.log(f"❌ Expected error status with AUTH_FAILED, got: {response.get('status')}, {response.get('last_error')}")
                return False
        return False

    def test_exely_success(self):
        """Test Exely connector with valid api_key (success path)"""
        self.log("\n=== 3) EXELY CONNECTOR: SUCCESS PATH ===")
        
        # Delete the previous Exely connector first (due to unique constraint)
        if self.exely_connector_no_key_id:
            success, response = self.run_test(
                "Delete Previous Exely Connector",
                "DELETE",
                f"api/channels/connectors/{self.exely_connector_no_key_id}",
                200,
                token=self.hotel_token
            )
            if success:
                self.log("✅ Previous Exely connector deleted")
            else:
                self.log("⚠️ Could not delete previous connector, continuing...")
        
        # Create Exely connector with api_key
        success, response = self.run_test(
            "Create Exely Connector (With API Key)",
            "POST",
            "api/channels/connectors",
            200,
            data={
                "provider": "exely",
                "display_name": "Exely With Key",
                "credentials": {"api_key": "demo_key_123"}
            },
            token=self.hotel_token
        )
        
        if not success:
            return False
            
        self.exely_connector_with_key_id = response.get('_id')
        self.log(f"✅ Created Exely connector with key: {self.exely_connector_with_key_id}")
        
        # Test connection - should succeed
        success, response = self.run_test(
            "Test Exely Connection (With API Key) - Expect 200 Success",
            "POST",
            f"api/channels/connectors/{self.exely_connector_with_key_id}/test",
            200,
            token=self.hotel_token
        )
        
        if success:
            # Check response structure
            if response.get('status') == 'success' and response.get('run_id'):
                self.log(f"✅ Success response with run_id: {response.get('run_id')}")
            else:
                self.log(f"❌ Expected success response, got: {response}")
                return False
        else:
            return False
            
        # Verify channel_sync_runs entry
        success, response = self.run_test(
            "Check Sync Runs for Success",
            "GET",
            f"api/channels/connectors/{self.exely_connector_with_key_id}/runs",
            200,
            token=self.hotel_token
        )
        
        if success and response.get('items'):
            run = response['items'][0]
            if run.get('status') == 'success':
                self.log("✅ Sync run marked as success")
            else:
                self.log(f"❌ Expected success status, got: {run.get('status')}")
                return False
        else:
            self.log("❌ No sync runs found")
            return False
            
        # Verify connector status updated
        success, response = self.run_test(
            "Check Connector Status After Success",
            "GET",
            f"api/channels/connectors/{self.exely_connector_with_key_id}",
            200,
            token=self.hotel_token
        )
        
        if success:
            if (response.get('status') == 'connected' and 
                response.get('last_success_at') and 
                response.get('last_error') is None):
                self.log("✅ Connector status updated to connected with last_success_at")
                return True
            else:
                self.log(f"❌ Expected connected status, got: {response.get('status')}, last_error: {response.get('last_error')}")
                return False
        return False

    def test_not_implemented_provider(self):
        """Test non-implemented provider (e.g. expedia) - NOT_IMPLEMENTED path"""
        self.log("\n=== 4) NON-IMPLEMENTED PROVIDER (EXPEDIA) ===")
        
        # Create Expedia connector
        success, response = self.run_test(
            "Create Expedia Connector",
            "POST",
            "api/channels/connectors",
            200,
            data={
                "provider": "expedia",
                "display_name": "Expedia Test",
                "credentials": {"username": "test", "password": "test"}
            },
            token=self.hotel_token
        )
        
        if not success:
            return False
            
        self.expedia_connector_id = response.get('_id')
        self.log(f"✅ Created Expedia connector: {self.expedia_connector_id}")
        
        # Test connection - should fail with NOT_IMPLEMENTED
        success, response = self.run_test(
            "Test Expedia Connection - Expect 501 NOT_IMPLEMENTED",
            "POST",
            f"api/channels/connectors/{self.expedia_connector_id}/test",
            501,
            token=self.hotel_token
        )
        
        if success:
            # Check error detail
            if response.get('detail', {}).get('code') == 'NOT_IMPLEMENTED':
                self.log("✅ Correct NOT_IMPLEMENTED error returned")
            else:
                self.log(f"❌ Expected NOT_IMPLEMENTED, got: {response}")
                return False
        else:
            return False
            
        # Verify channel_sync_runs entry
        success, response = self.run_test(
            "Check Sync Runs for NOT_IMPLEMENTED",
            "GET",
            f"api/channels/connectors/{self.expedia_connector_id}/runs",
            200,
            token=self.hotel_token
        )
        
        if success and response.get('items'):
            run = response['items'][0]
            if run.get('status') == 'failed':
                self.log("✅ Sync run marked as failed")
            else:
                self.log(f"❌ Expected failed status, got: {run.get('status')}")
                return False
        else:
            self.log("❌ No sync runs found")
            return False
            
        # Verify connector status updated
        success, response = self.run_test(
            "Check Connector Status After NOT_IMPLEMENTED",
            "GET",
            f"api/channels/connectors/{self.expedia_connector_id}",
            200,
            token=self.hotel_token
        )
        
        if success:
            if response.get('status') == 'error' and response.get('last_error', {}).get('code') == 'NOT_IMPLEMENTED':
                self.log("✅ Connector status updated to error with NOT_IMPLEMENTED")
                return True
            else:
                self.log(f"❌ Expected error status with NOT_IMPLEMENTED, got: {response.get('status')}, {response.get('last_error')}")
                return False
        return False

    def test_guard_enforcement(self):
        """Test that guard is still enforced when package=basic"""
        self.log("\n=== 5) GUARD ENFORCEMENT (PACKAGE=BASIC) ===")
        
        # Change hotel package back to basic
        success, response = self.run_test(
            f"Set Hotel Package to Basic (hotel_id: {self.hotel_id})",
            "PATCH",
            f"api/admin/hotels/{self.hotel_id}/package",
            200,
            data={"package": "basic"},
            token=self.admin_token
        )
        
        if not success:
            return False
            
        self.log("✅ Hotel package set to basic")
        
        # Try to access connectors list - should fail with 403
        success, response = self.run_test(
            "Try to Access Connectors with Basic Package - Expect 403",
            "GET",
            "api/channels/connectors",
            403,
            token=self.hotel_token
        )
        
        if success:
            if response.get('detail', {}).get('code') == 'FEATURE_NOT_AVAILABLE':
                self.log("✅ Correct FEATURE_NOT_AVAILABLE error returned")
            else:
                self.log(f"❌ Expected FEATURE_NOT_AVAILABLE, got: {response}")
                return False
        else:
            return False
            
        # Try to test connection - should also fail with 403
        success, response = self.run_test(
            "Try to Test Connection with Basic Package - Expect 403",
            "POST",
            f"api/channels/connectors/{self.exely_connector_with_key_id}/test",
            403,
            token=self.hotel_token
        )
        
        if success:
            if response.get('detail', {}).get('code') == 'FEATURE_NOT_AVAILABLE':
                self.log("✅ Correct FEATURE_NOT_AVAILABLE error returned for test connection")
                return True
            else:
                self.log(f"❌ Expected FEATURE_NOT_AVAILABLE, got: {response}")
                return False
        return False

    def run_all_tests(self):
        """Run all test scenarios"""
        self.log("🚀 Starting Channel Hub Provider Adapter Backend Smoke Test")
        self.log("=" * 80)
        
        # Test sequence
        tests = [
            ("Admin Login", self.test_admin_login),
            ("Hotel Package Setup", self.test_hotel_package_setup),
            ("Hotel Login", self.test_hotel_login),
            ("Exely AUTH_FAILED", self.test_exely_auth_failed),
            ("Exely Success", self.test_exely_success),
            ("Not Implemented Provider", self.test_not_implemented_provider),
            ("Guard Enforcement", self.test_guard_enforcement),
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
        self.log("📊 CHANNEL HUB PROVIDER ADAPTER TEST SUMMARY")
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
            self.log("🎉 ALL TESTS PASSED! Channel Hub provider adapter functionality is working correctly.")
            return True
        else:
            self.log("💥 SOME TESTS FAILED! Channel Hub provider adapter needs attention.")
            return False

if __name__ == "__main__":
    # Use localhost:8001 as default since we're testing backend directly
    base_url = "http://localhost:8001"
    
    tester = ChannelHubTester(base_url)
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)