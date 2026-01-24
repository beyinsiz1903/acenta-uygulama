#!/usr/bin/env python3
"""
Phase-1 Multi-tenant Backend Test for Acenta Master - FIXED VERSION
Tests multi-tenant omurga (agencies/hotels/agency_hotel_links) + RBAC + visibility rules
"""
import requests
import sys
from datetime import datetime

class MultiTenantTesterFixed:
    def __init__(self, base_url="https://hotel-marketplace-1.preview.emergentagent.com"):
        self.base_url = base_url
        self.super_admin_token = None
        self.agency1_token = None
        self.agency2_token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.failed_tests = []
        
        # Store IDs for visibility tests
        self.agency1_hotel2_link_id = None
        self.agency_a_id = None
        self.hotel2_id = None

    def log(self, msg):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    def run_test(self, name, method, endpoint, expected_status, data=None, token=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = f'Bearer {token}'

        self.tests_run += 1
        self.log(f"🔍 Test #{self.tests_run}: {name}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=10)
            elif method == 'PATCH':
                response = requests.patch(url, json=data, headers=headers, timeout=10)
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

    def test_health(self):
        """Test 1: /api/health OK"""
        self.log("\n=== 1. HEALTH CHECK ===")
        success, response = self.run_test(
            "Health Check",
            "GET",
            "api/health",
            200
        )
        if success and response.get('ok'):
            self.log("✅ Database connection OK")
        return success

    def test_super_admin_login(self):
        """Test 2: SUPER_ADMIN login: admin@acenta.test / admin123"""
        self.log("\n=== 2. SUPER ADMIN LOGIN ===")
        success, response = self.run_test(
            "Super Admin Login",
            "POST",
            "api/auth/login",
            200,
            data={"email": "admin@acenta.test", "password": "admin123"}
        )
        if success and 'access_token' in response:
            self.super_admin_token = response['access_token']
            self.log(f"✅ Super admin token obtained")
            return True
        return False

    def test_super_admin_me(self):
        """Test super admin /me endpoint - roles içinde super_admin var mı?"""
        success, response = self.run_test(
            "Super Admin /me - Check super_admin role",
            "GET",
            "api/auth/me",
            200,
            token=self.super_admin_token
        )
        if success:
            roles = response.get('roles', [])
            if 'super_admin' in roles:
                self.log(f"✅ Super admin role confirmed: {roles}")
                return True
            else:
                self.log(f"❌ super_admin role missing in: {roles}")
                self.failed_tests.append("Super admin role missing")
                return False
        return False

    def test_admin_agencies(self):
        """Test GET /api/admin/agencies -> en az 2 demo agency geliyor mu?"""
        success, response = self.run_test(
            "Admin - List Agencies (min 2 expected)",
            "GET",
            "api/admin/agencies",
            200,
            token=self.super_admin_token
        )
        if success:
            agencies = response if isinstance(response, list) else []
            if len(agencies) >= 2:
                self.log(f"✅ Found {len(agencies)} agencies (≥2 required)")
                for agency in agencies:
                    self.log(f"   - {agency.get('name')} (ID: {agency.get('id')})")
                    if agency.get('name') == 'Demo Acente A':
                        self.agency_a_id = agency.get('id')
                return True
            else:
                self.log(f"❌ Only {len(agencies)} agencies found, need ≥2")
                self.failed_tests.append(f"Only {len(agencies)} agencies found")
                return False
        return False

    def test_admin_hotels(self):
        """Test GET /api/admin/hotels -> en az 3 demo hotel geliyor mu?"""
        success, response = self.run_test(
            "Admin - List Hotels (min 3 expected)",
            "GET",
            "api/admin/hotels",
            200,
            token=self.super_admin_token
        )
        if success:
            hotels = response if isinstance(response, list) else []
            if len(hotels) >= 3:
                self.log(f"✅ Found {len(hotels)} hotels (≥3 required)")
                for hotel in hotels:
                    self.log(f"   - {hotel.get('name')} (ID: {hotel.get('id')})")
                    if hotel.get('name') == 'Demo Hotel 2':
                        self.hotel2_id = hotel.get('id')
                return True
            else:
                self.log(f"❌ Only {len(hotels)} hotels found, need ≥3")
                self.failed_tests.append(f"Only {len(hotels)} hotels found")
                return False
        return False

    def test_admin_agency_hotel_links(self):
        """Test GET /api/admin/agency-hotel-links -> en az 3 link geliyor mu?"""
        success, response = self.run_test(
            "Admin - List Agency-Hotel Links (min 3 expected)",
            "GET",
            "api/admin/agency-hotel-links",
            200,
            token=self.super_admin_token
        )
        if success:
            links = response if isinstance(response, list) else []
            if len(links) >= 3:
                self.log(f"✅ Found {len(links)} agency-hotel links (≥3 required)")
                for link in links:
                    self.log(f"   - Agency: {link.get('agency_id')} -> Hotel: {link.get('hotel_id')} (Active: {link.get('active')})")
                    # Find the specific Agency A -> Hotel 2 link
                    if (link.get('agency_id') == self.agency_a_id and 
                        link.get('hotel_id') == self.hotel2_id and 
                        link.get('active')):
                        self.agency1_hotel2_link_id = link.get('id')
                        self.log(f"   ✅ Found Agency A -> Hotel 2 link: {self.agency1_hotel2_link_id}")
                return True
            else:
                self.log(f"❌ Only {len(links)} links found, need ≥3")
                self.failed_tests.append(f"Only {len(links)} links found")
                return False
        return False

    def test_agency1_login(self):
        """Test 3: AGENCY_ADMIN login: agency1@demo.test / agency123"""
        self.log("\n=== 3. AGENCY1 ADMIN LOGIN ===")
        success, response = self.run_test(
            "Agency1 Admin Login",
            "POST",
            "api/auth/login",
            200,
            data={"email": "agency1@demo.test", "password": "agency123"}
        )
        if success and 'access_token' in response:
            self.agency1_token = response['access_token']
            self.log(f"✅ Agency1 admin token obtained")
            return True
        return False

    def test_agency1_me(self):
        """Test agency1 /me - roles içinde agency_admin var mı ve agency_id var mı?"""
        success, response = self.run_test(
            "Agency1 /me - Check agency_admin role and agency_id",
            "GET",
            "api/auth/me",
            200,
            token=self.agency1_token
        )
        if success:
            roles = response.get('roles', [])
            agency_id = response.get('agency_id')
            
            has_role = 'agency_admin' in roles
            has_agency_id = agency_id is not None
            
            if has_role and has_agency_id:
                self.log(f"✅ Agency admin role and agency_id confirmed: roles={roles}, agency_id={agency_id}")
                return True
            else:
                self.log(f"❌ Missing agency_admin role or agency_id: roles={roles}, agency_id={agency_id}")
                self.failed_tests.append("Agency1 missing role or agency_id")
                return False
        return False

    def test_agency1_hotels_before(self):
        """Test GET /api/agency/hotels -> sadece Demo Hotel 1 & Demo Hotel 2 dönmeli (2 otel)"""
        success, response = self.run_test(
            "Agency1 - List Hotels BEFORE deactivation (expect Demo Hotel 1 & 2)",
            "GET",
            "api/agency/hotels",
            200,
            token=self.agency1_token
        )
        if success:
            hotels = response if isinstance(response, list) else []
            hotel_names = [hotel.get('name') for hotel in hotels]
            
            expected_hotels = ['Demo Hotel 1', 'Demo Hotel 2']
            has_hotel1 = 'Demo Hotel 1' in hotel_names
            has_hotel2 = 'Demo Hotel 2' in hotel_names
            
            self.log(f"   Found hotels: {hotel_names}")
            
            if len(hotels) == 2 and has_hotel1 and has_hotel2:
                self.log(f"✅ Agency1 sees exactly 2 hotels as expected: {hotel_names}")
                return True
            else:
                self.log(f"❌ Agency1 should see Demo Hotel 1 & 2, but got: {hotel_names}")
                self.failed_tests.append(f"Agency1 wrong hotels: {hotel_names}")
                return False
        return False

    def test_agency2_login(self):
        """Test 4: AGENCY_ADMIN login: agency2@demo.test / agency123"""
        self.log("\n=== 4. AGENCY2 ADMIN LOGIN ===")
        success, response = self.run_test(
            "Agency2 Admin Login",
            "POST",
            "api/auth/login",
            200,
            data={"email": "agency2@demo.test", "password": "agency123"}
        )
        if success and 'access_token' in response:
            self.agency2_token = response['access_token']
            self.log(f"✅ Agency2 admin token obtained")
            return True
        return False

    def test_agency2_hotels(self):
        """Test GET /api/agency/hotels -> sadece Demo Hotel 3 dönmeli (1 otel)"""
        success, response = self.run_test(
            "Agency2 - List Hotels (expect Demo Hotel 3 only)",
            "GET",
            "api/agency/hotels",
            200,
            token=self.agency2_token
        )
        if success:
            hotels = response if isinstance(response, list) else []
            hotel_names = [hotel.get('name') for hotel in hotels]
            
            self.log(f"   Found hotels: {hotel_names}")
            
            if len(hotels) == 1 and 'Demo Hotel 3' in hotel_names:
                self.log(f"✅ Agency2 sees exactly Demo Hotel 3 as expected")
                return True
            else:
                self.log(f"❌ Agency2 should see only Demo Hotel 3, but got: {hotel_names}")
                self.failed_tests.append(f"Agency2 wrong hotels: {hotel_names}")
                return False
        return False

    def test_patch_agency_hotel_link(self):
        """Test PATCH /api/admin/agency-hotel-links/{id} active=false - specifically Agency A -> Hotel 2"""
        self.log("\n=== 5. DEACTIVATE AGENCY A -> HOTEL 2 LINK ===")
        if not self.agency1_hotel2_link_id:
            self.log("⚠️  No Agency A -> Hotel 2 link ID available for patch test")
            return False
            
        success, response = self.run_test(
            f"Admin - Deactivate Agency A -> Hotel 2 Link {self.agency1_hotel2_link_id}",
            "PATCH",
            f"api/admin/agency-hotel-links/{self.agency1_hotel2_link_id}",
            200,
            data={"active": False},
            token=self.super_admin_token
        )
        if success:
            if response.get('active') == False:
                self.log(f"✅ Agency A -> Hotel 2 link deactivated successfully")
                return True
            else:
                self.log(f"❌ Link active status not updated: {response.get('active')}")
                return False
        return False

    def test_verify_link_deactivation(self):
        """Verify the specific link was deactivated in the list"""
        success, response = self.run_test(
            "Admin - Verify Agency A -> Hotel 2 Link Deactivation",
            "GET",
            "api/admin/agency-hotel-links",
            200,
            token=self.super_admin_token
        )
        if success:
            links = response if isinstance(response, list) else []
            deactivated_link = next((link for link in links if link.get('id') == self.agency1_hotel2_link_id), None)
            if deactivated_link and deactivated_link.get('active') == False:
                self.log(f"✅ Agency A -> Hotel 2 link deactivation verified in list")
                return True
            else:
                self.log(f"❌ Agency A -> Hotel 2 link deactivation not reflected in list")
                return False
        return False

    def test_visibility_after_deactivation(self):
        """Test 5: Görünürlük testi - agency1 artık deactivated hotel'i görmemeli"""
        self.log("\n=== 6. VISIBILITY TEST AFTER DEACTIVATION ===")
        success, response = self.run_test(
            "Agency1 - Verify Hotel Visibility After Agency A -> Hotel 2 Link Deactivation",
            "GET",
            "api/agency/hotels",
            200,
            token=self.agency1_token
        )
        if success:
            hotels = response if isinstance(response, list) else []
            hotel_names = [hotel.get('name') for hotel in hotels]
            
            self.log(f"   Agency1 hotels after deactivation: {hotel_names}")
            
            # After deactivating Agency A -> Hotel 2 link, agency1 should only see Hotel 1
            if len(hotels) == 1 and 'Demo Hotel 1' in hotel_names and 'Demo Hotel 2' not in hotel_names:
                self.log(f"✅ Visibility rule working - Agency1 now sees only Demo Hotel 1: {hotel_names}")
                return True
            else:
                self.log(f"❌ Visibility rule failed - Agency1 should see only Demo Hotel 1, but got: {hotel_names}")
                self.failed_tests.append(f"Visibility rule failed: {hotel_names}")
                return False
        return False

    def test_security_agency_cannot_access_admin(self):
        """Test security: agency1 user /api/admin/agencies çağırınca 403 dönmeli"""
        self.log("\n=== 7. SECURITY TEST ===")
        success, response = self.run_test(
            "Security - Agency1 cannot access admin endpoints (expect 403)",
            "GET",
            "api/admin/agencies",
            403,  # Expect 403 Forbidden
            token=self.agency1_token
        )
        if success:
            self.log(f"✅ Security working - Agency1 correctly denied admin access")
            return True
        return False

    def print_summary(self):
        """Print test summary"""
        self.log("\n" + "="*60)
        self.log("PHASE-1 MULTI-TENANT TEST SUMMARY (FIXED)")
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
        """Run all multi-tenant tests in sequence"""
        self.log("🚀 Starting Phase-1 Multi-Tenant Tests (FIXED VERSION)")
        self.log(f"Base URL: {self.base_url}")
        
        # Test 1: Health check
        if not self.test_health():
            self.log("❌ Health check failed - stopping tests")
            self.print_summary()
            return 1

        # Test 2: Super admin authentication and admin endpoints
        if not self.test_super_admin_login():
            self.log("❌ Super admin login failed - stopping tests")
            self.print_summary()
            return 1

        self.test_super_admin_me()
        self.test_admin_agencies()
        self.test_admin_hotels()
        self.test_admin_agency_hotel_links()

        # Test 3: Agency1 admin
        if not self.test_agency1_login():
            self.log("❌ Agency1 login failed")
        else:
            self.test_agency1_me()
            self.test_agency1_hotels_before()

        # Test 4: Agency2 admin
        if not self.test_agency2_login():
            self.log("❌ Agency2 login failed")
        else:
            self.test_agency2_hotels()

        # Test 5: Deactivate specific link and test visibility
        self.test_patch_agency_hotel_link()
        self.test_verify_link_deactivation()
        
        if self.agency1_token:
            self.test_visibility_after_deactivation()

        # Security test
        if self.agency1_token:
            self.test_security_agency_cannot_access_admin()

        # Summary
        self.print_summary()

        return 0 if self.tests_failed == 0 else 1


def main():
    tester = MultiTenantTesterFixed()
    exit_code = tester.run_all_tests()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()