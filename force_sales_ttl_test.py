#!/usr/bin/env python3
"""
Force Sales Override TTL & Reason Feature Test
Tests the newly added TTL and reason functionality for force_sales_open
"""
import requests
import sys
import time
from datetime import datetime, timedelta

class ForceSalesOverrideTTLTester:
    def __init__(self, base_url="https://hardening-e1-e4.preview.emergentagent.com"):
        self.base_url = base_url
        self.admin_token = None
        self.agency_token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.failed_tests = []
        
        # Store IDs for testing
        self.hotel_id = None
        self.stop_sell_id = None
        self.allocation_id = None

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
                response = requests.get(url, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=10)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=10)
            elif method == 'PATCH':
                response = requests.patch(url, json=data, headers=headers, timeout=10)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=10)
            else:
                raise ValueError(f"Unsupported method: {method}")

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                self.log(f"✅ PASSED - Status: {response.status_code}")
                try:
                    if 'application/json' in response.headers.get('content-type', ''):
                        return True, response.json()
                    else:
                        return True, response.text
                except:
                    return True, response.text if hasattr(response, 'text') else {}
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
        """1) Test super admin login"""
        self.log("\n=== 1) ADMIN LOGIN & HOTEL LIST ===")
        success, response = self.run_test(
            "Super Admin Login (admin@acenta.test)",
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

    def test_get_hotel_id(self):
        """Get a hotel_id from /api/admin/hotels list"""
        self.log("\n--- Get Hotel ID from Admin Hotels List ---")
        
        success, response = self.run_test(
            "GET /api/admin/hotels",
            "GET",
            "api/admin/hotels",
            200,
            token=self.admin_token
        )
        
        if success and isinstance(response, list) and len(response) > 0:
            hotel = response[0]
            self.hotel_id = hotel.get('id')
            hotel_name = hotel.get('name', 'Unknown')
            force_sales_open = hotel.get('force_sales_open', False)
            
            self.log(f"✅ Found hotel: {hotel_name} (ID: {self.hotel_id})")
            self.log(f"   Current force_sales_open: {force_sales_open}")
            return True
        else:
            self.log(f"❌ No hotels found in admin list")
            return False

    def test_force_sales_override_with_ttl_and_reason(self):
        """2) Test enabling force_sales_open with TTL and reason"""
        self.log("\n=== 2) ENABLE FORCE SALES OVERRIDE WITH TTL & REASON ===")
        
        if not self.hotel_id:
            self.log("❌ No hotel_id available")
            return False
        
        override_data = {
            "force_sales_open": True,
            "ttl_hours": 1,
            "reason": "Test override"
        }
        
        success, response = self.run_test(
            f"PATCH /api/admin/hotels/{self.hotel_id}/force-sales (Enable with TTL & Reason)",
            "PATCH",
            f"api/admin/hotels/{self.hotel_id}/force-sales",
            200,
            data=override_data,
            token=self.admin_token
        )
        
        if success:
            # Verify response contains expected fields
            force_sales_open = response.get('force_sales_open')
            expires_at = response.get('force_sales_open_expires_at')
            reason = response.get('force_sales_open_reason')
            
            if force_sales_open is True:
                self.log(f"✅ force_sales_open set to: {force_sales_open}")
            else:
                self.log(f"❌ force_sales_open not set correctly: {force_sales_open}")
                return False
                
            if expires_at:
                self.log(f"✅ force_sales_open_expires_at populated: {expires_at}")
                # Verify it's approximately 1 hour from now
                try:
                    expires_dt = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                    now_dt = datetime.now(expires_dt.tzinfo)
                    time_diff = expires_dt - now_dt
                    if 50 <= time_diff.total_seconds() / 60 <= 70:  # 50-70 minutes (allowing some variance)
                        self.log(f"✅ TTL correctly set to ~1 hour: {time_diff.total_seconds()/60:.1f} minutes")
                    else:
                        self.log(f"❌ TTL not correctly set: {time_diff.total_seconds()/60:.1f} minutes")
                        return False
                except Exception as e:
                    self.log(f"❌ Error parsing expires_at: {e}")
                    return False
            else:
                self.log(f"❌ force_sales_open_expires_at not populated")
                return False
                
            if reason == "Test override":
                self.log(f"✅ force_sales_open_reason set correctly: {reason}")
            else:
                self.log(f"❌ force_sales_open_reason not set correctly: {reason}")
                return False
                
            return True
        return False

    def test_audit_log_verification(self):
        """Verify audit log contains force_sales_override action with meta fields"""
        self.log("\n--- Verify Audit Log Entry with Meta Fields ---")
        
        success, response = self.run_test(
            "GET /api/audit/logs (Check for force_sales_override with meta)",
            "GET",
            "api/audit/logs?action=hotel.force_sales_override&limit=5",
            200,
            token=self.admin_token
        )
        
        if success:
            items = response if isinstance(response, list) else response.get('items', [])
            if items:
                latest_audit = items[0]  # Most recent
                action = latest_audit.get('action')
                target_type = latest_audit.get('target_type')
                target_id = latest_audit.get('target_id')
                meta = latest_audit.get('meta', {})
                
                if action == "hotel.force_sales_override":
                    self.log(f"✅ Found audit log with action: {action}")
                else:
                    self.log(f"❌ Wrong action in audit log: {action}")
                    return False
                    
                if target_type == "hotel" and target_id == self.hotel_id:
                    self.log(f"✅ Correct target_type and target_id: {target_type}, {target_id}")
                else:
                    self.log(f"⚠️  Target info: {target_type}, {target_id} (expected: hotel, {self.hotel_id})")
                
                # Check meta fields
                expected_meta_fields = ['force_sales_open', 'ttl_hours', 'expires_at', 'reason']
                all_fields_present = True
                for field in expected_meta_fields:
                    if field in meta:
                        self.log(f"✅ Meta field '{field}' present: {meta[field]}")
                    else:
                        self.log(f"❌ Meta field '{field}' missing from audit log")
                        all_fields_present = False
                
                return all_fields_present
            else:
                self.log(f"❌ No audit log entries found for force_sales_override")
                return False
        return False

    def test_agency_login(self):
        """Test agency login for search testing"""
        self.log("\n=== 3) AGENCY SEARCH WITH OVERRIDE ACTIVE ===")
        success, response = self.run_test(
            "Agency Login (agency1@demo.test)",
            "POST",
            "api/auth/login",
            200,
            data={"email": "agency1@demo.test", "password": "agency123"},
            headers_override={'Content-Type': 'application/json'}
        )
        if success and 'access_token' in response:
            self.agency_token = response['access_token']
            user = response.get('user', {})
            agency_id = user.get('agency_id')
            
            if agency_id:
                self.log(f"✅ Agency login successful - agency_id: {agency_id}")
                return True
            else:
                self.log(f"❌ Missing agency_id")
                return False
        return False

    def setup_stop_sell_and_allocation(self):
        """Setup stop-sell and allocation rules to test override bypass"""
        self.log("\n--- Setup Stop-sell and Allocation for Override Test ---")
        
        # First login as hotel admin to create stop-sell and allocation
        success, response = self.run_test(
            "Hotel Admin Login (hoteladmin@acenta.test)",
            "POST",
            "api/auth/login",
            200,
            data={"email": "hoteladmin@acenta.test", "password": "admin123"},
            headers_override={'Content-Type': 'application/json'}
        )
        
        if not success or 'access_token' not in response:
            self.log("❌ Hotel admin login failed")
            return False
            
        hotel_token = response['access_token']
        
        # Create stop-sell for deluxe rooms
        stop_sell_data = {
            "room_type": "deluxe",
            "start_date": "2026-03-10",
            "end_date": "2026-03-12",
            "reason": "Test stop-sell for override",
            "is_active": True
        }
        
        success, response = self.run_test(
            "Create Stop-sell for Override Test",
            "POST",
            "api/hotel/stop-sell",
            200,
            data=stop_sell_data,
            token=hotel_token
        )
        
        if success:
            self.stop_sell_id = response.get('id')
            self.log(f"✅ Stop-sell created: {self.stop_sell_id}")
        else:
            self.log("❌ Failed to create stop-sell")
            return False
        
        # Create allocation for standard rooms
        allocation_data = {
            "room_type": "standard",
            "start_date": "2026-03-01",
            "end_date": "2026-03-31",
            "allotment": 1,  # Very restrictive
            "is_active": True,
            "channel": "agency_extranet"
        }
        
        success, response = self.run_test(
            "Create Allocation for Override Test",
            "POST",
            "api/hotel/allocations",
            200,
            data=allocation_data,
            token=hotel_token
        )
        
        if success:
            self.allocation_id = response.get('id')
            self.log(f"✅ Allocation created: {self.allocation_id}")
            return True
        else:
            self.log("❌ Failed to create allocation")
            return False

    def test_search_with_override_active(self):
        """Test that stop-sell/allocation rules are bypassed when override is active"""
        self.log("\n--- Search with Override Active (Should Bypass Rules) ---")
        
        if not self.setup_stop_sell_and_allocation():
            return False
        
        search_data = {
            "hotel_id": self.hotel_id,
            "check_in": "2026-03-10",
            "check_out": "2026-03-12",
            "occupancy": {"adults": 2, "children": 0}
        }
        
        success, response = self.run_test(
            "Agency Search with Override Active",
            "POST",
            "api/agency/search",
            200,
            data=search_data,
            token=self.agency_token
        )
        
        if success:
            rooms = response.get('rooms', [])
            
            # Check if deluxe rooms are available (should bypass stop-sell)
            deluxe_available = False
            standard_available = False
            
            for room in rooms:
                room_type_id = room.get('room_type_id', '')
                inventory_left = room.get('inventory_left', 0)
                
                if 'deluxe' in room_type_id.lower() and inventory_left > 0:
                    deluxe_available = True
                    self.log(f"✅ Deluxe rooms available despite stop-sell (override working): {inventory_left}")
                
                if 'standard' in room_type_id.lower() and inventory_left > 1:  # Should be more than allocation limit
                    standard_available = True
                    self.log(f"✅ Standard rooms available despite allocation limit (override working): {inventory_left}")
            
            if deluxe_available and standard_available:
                self.log(f"✅ Override successfully bypassed both stop-sell and allocation rules")
                return True
            else:
                self.log(f"❌ Override not working - deluxe: {deluxe_available}, standard: {standard_available}")
                return False
        return False

    def test_ttl_expiry_simulation(self):
        """4) Test TTL expiry simulation and self-healing behavior"""
        self.log("\n=== 4) TTL EXPIRY & SELF-HEAL TEST ===")
        
        # Since we can't wait for actual TTL expiry, we'll test the disable functionality
        # and verify that rules are re-applied
        self.log("--- Testing Rule Re-application After Override Disable ---")
        
        # Disable override
        disable_data = {"force_sales_open": False}
        
        success, response = self.run_test(
            f"Disable Force Sales Override",
            "PATCH",
            f"api/admin/hotels/{self.hotel_id}/force-sales",
            200,
            data=disable_data,
            token=self.admin_token
        )
        
        if success:
            force_sales_open = response.get('force_sales_open')
            expires_at = response.get('force_sales_open_expires_at')
            reason = response.get('force_sales_open_reason')
            
            if force_sales_open is False:
                self.log(f"✅ force_sales_open disabled: {force_sales_open}")
            else:
                self.log(f"❌ force_sales_open not disabled: {force_sales_open}")
                return False
                
            if expires_at is None:
                self.log(f"✅ force_sales_open_expires_at cleared: {expires_at}")
            else:
                self.log(f"❌ force_sales_open_expires_at not cleared: {expires_at}")
                return False
                
            if reason is None:
                self.log(f"✅ force_sales_open_reason cleared: {reason}")
            else:
                self.log(f"❌ force_sales_open_reason not cleared: {reason}")
                return False
        else:
            return False
        
        # Now test that rules are re-applied
        search_data = {
            "hotel_id": self.hotel_id,
            "check_in": "2026-03-10",
            "check_out": "2026-03-12",
            "occupancy": {"adults": 2, "children": 0}
        }
        
        success, response = self.run_test(
            "Agency Search After Override Disabled (Rules Should Apply)",
            "POST",
            "api/agency/search",
            200,
            data=search_data,
            token=self.agency_token
        )
        
        if success:
            rooms = response.get('rooms', [])
            
            # Check that deluxe rooms are now blocked by stop-sell
            deluxe_blocked = True
            standard_limited = True
            
            for room in rooms:
                room_type_id = room.get('room_type_id', '')
                inventory_left = room.get('inventory_left', 0)
                
                if 'deluxe' in room_type_id.lower() and inventory_left > 0:
                    deluxe_blocked = False
                    self.log(f"❌ Deluxe rooms still available (stop-sell not working): {inventory_left}")
                
                if 'standard' in room_type_id.lower() and inventory_left > 1:
                    standard_limited = False
                    self.log(f"❌ Standard rooms not limited by allocation: {inventory_left}")
            
            if deluxe_blocked:
                self.log(f"✅ Stop-sell rules re-applied: deluxe rooms blocked")
            if standard_limited:
                self.log(f"✅ Allocation rules re-applied: standard rooms limited")
                
            return deluxe_blocked and standard_limited
        return False

    def test_override_false_with_null_fields(self):
        """5) Test PATCH with force_sales_open=false results in null reason/expires_at"""
        self.log("\n=== 5) OVERRIDE FALSE WITH NULL FIELDS TEST ===")
        
        # First enable override again
        override_data = {
            "force_sales_open": True,
            "ttl_hours": 2,
            "reason": "Another test override"
        }
        
        success, response = self.run_test(
            f"Enable Override Again",
            "PATCH",
            f"api/admin/hotels/{self.hotel_id}/force-sales",
            200,
            data=override_data,
            token=self.admin_token
        )
        
        if not success:
            return False
        
        # Now disable it and verify fields are null
        disable_data = {"force_sales_open": False}
        
        success, response = self.run_test(
            f"Disable Override and Check Null Fields",
            "PATCH",
            f"api/admin/hotels/{self.hotel_id}/force-sales",
            200,
            data=disable_data,
            token=self.admin_token
        )
        
        if success:
            force_sales_open = response.get('force_sales_open')
            expires_at = response.get('force_sales_open_expires_at')
            reason = response.get('force_sales_open_reason')
            
            success_checks = []
            
            if force_sales_open is False:
                self.log(f"✅ force_sales_open=false: {force_sales_open}")
                success_checks.append(True)
            else:
                self.log(f"❌ force_sales_open not false: {force_sales_open}")
                success_checks.append(False)
                
            if expires_at is None:
                self.log(f"✅ expires_at is null: {expires_at}")
                success_checks.append(True)
            else:
                self.log(f"❌ expires_at not null: {expires_at}")
                success_checks.append(False)
                
            if reason is None:
                self.log(f"✅ reason is null: {reason}")
                success_checks.append(True)
            else:
                self.log(f"❌ reason not null: {reason}")
                success_checks.append(False)
                
            return all(success_checks)
        return False

    def test_admin_endpoints_smoke_test(self):
        """6) Smoke test other admin endpoints to ensure they're not affected"""
        self.log("\n=== 6) ADMIN ENDPOINTS SMOKE TEST ===")
        
        # Test agencies endpoint
        success, response = self.run_test(
            "GET /api/admin/agencies (Smoke Test)",
            "GET",
            "api/admin/agencies",
            200,
            token=self.admin_token
        )
        
        if success:
            self.log(f"✅ Agencies endpoint working: {len(response)} agencies")
        else:
            return False
        
        # Test agency-hotel-links endpoint
        success, response = self.run_test(
            "GET /api/admin/agency-hotel-links (Smoke Test)",
            "GET",
            "api/admin/agency-hotel-links",
            200,
            token=self.admin_token
        )
        
        if success:
            self.log(f"✅ Agency-hotel-links endpoint working: {len(response)} links")
        else:
            return False
        
        # Test availability calculation is not affected
        search_data = {
            "hotel_id": self.hotel_id,
            "check_in": "2026-04-10",  # Different dates to avoid existing rules
            "check_out": "2026-04-12",
            "occupancy": {"adults": 2, "children": 0}
        }
        
        success, response = self.run_test(
            "Agency Search (Different Dates - Availability Calculation Test)",
            "POST",
            "api/agency/search",
            200,
            data=search_data,
            token=self.agency_token
        )
        
        if success:
            rooms = response.get('rooms', [])
            if rooms:
                self.log(f"✅ Availability calculation working: {len(rooms)} room types found")
                return True
            else:
                self.log(f"⚠️  No rooms found (may be normal)")
                return True
        return False

    def print_summary(self):
        """Print test summary"""
        self.log("\n" + "="*60)
        self.log("FORCE SALES OVERRIDE TTL & REASON TEST SUMMARY")
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

    def run_force_sales_ttl_tests(self):
        """Run all force sales override TTL & reason tests"""
        self.log("🚀 Starting Force Sales Override TTL & Reason Tests")
        self.log(f"Base URL: {self.base_url}")
        
        # 1) Admin login and get hotel ID
        if not self.test_admin_login():
            self.log("❌ Admin login failed - stopping tests")
            self.print_summary()
            return 1

        if not self.test_get_hotel_id():
            self.log("❌ Failed to get hotel ID - stopping tests")
            self.print_summary()
            return 1

        # 2) Enable force sales override with TTL and reason
        if not self.test_force_sales_override_with_ttl_and_reason():
            self.log("❌ Failed to enable force sales override with TTL & reason")
        
        # 3) Verify audit log
        self.test_audit_log_verification()
        
        # 4) Agency login for search tests
        if not self.test_agency_login():
            self.log("❌ Agency login failed - skipping search tests")
        else:
            # 5) Test search with override active (bypass rules)
            self.test_search_with_override_active()
        
        # 6) Test TTL expiry simulation and rule re-application
        self.test_ttl_expiry_simulation()
        
        # 7) Test override=false with null fields
        self.test_override_false_with_null_fields()
        
        # 8) Smoke test other endpoints
        self.test_admin_endpoints_smoke_test()

        # Summary
        self.print_summary()

        return 0 if self.tests_failed == 0 else 1


if __name__ == "__main__":
    tester = ForceSalesOverrideTTLTester()
    exit_code = tester.run_force_sales_ttl_tests()
    sys.exit(exit_code)