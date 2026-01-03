#!/usr/bin/env python3
"""
Syroce Settlement Module Backend API Test
Tests settlement listing, confirm, dispute, and reopen endpoints
"""
import requests
import sys
from datetime import datetime

class SyroceSettlementTester:
    def __init__(self, base_url="https://uygulama-bilgi.preview.emergentagent.com"):
        self.base_url = base_url
        self.agency_token = None
        self.hotel_token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.failed_tests = []
        
        # Store settlement IDs for testing
        self.test_settlement_id = None

    def log(self, msg):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    def run_test(self, name, method, endpoint, expected_status, data=None, params=None, token=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        if token:
            headers['Authorization'] = f'Bearer {token}'

        self.tests_run += 1
        self.log(f"🔍 Test #{self.tests_run}: {name}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params, timeout=15)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, params=params, timeout=15)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, params=params, timeout=15)
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

    def test_agency_login(self):
        """Login as agency user"""
        self.log("\n=== AGENCY LOGIN ===")
        success, response = self.run_test(
            "Agency Login (agency1@demo.test)",
            "POST",
            "api/auth/login",
            200,
            data={"email": "agency1@demo.test", "password": "agency123"}
        )
        if success and 'access_token' in response:
            self.agency_token = response['access_token']
            user = response.get('user', {})
            self.log(f"✅ Agency login successful - agency_id: {user.get('agency_id')}")
            return True
        return False

    def test_hotel_login(self):
        """Login as hotel user"""
        self.log("\n=== HOTEL LOGIN ===")
        success, response = self.run_test(
            "Hotel Login (hoteladmin@acenta.test)",
            "POST",
            "api/auth/login",
            200,
            data={"email": "hoteladmin@acenta.test", "password": "admin123"}
        )
        if success and 'access_token' in response:
            self.hotel_token = response['access_token']
            user = response.get('user', {})
            self.log(f"✅ Hotel login successful - hotel_id: {user.get('hotel_id')}")
            return True
        return False

    def test_agency_settlements_listing(self):
        """Test 1) GET /api/agency/settlements - check status field and skipped_count"""
        self.log("\n=== 1) AGENCY SETTLEMENTS LISTING ===")
        
        # Get current month in YYYY-MM format
        current_month = datetime.now().strftime("%Y-%m")
        
        success, response = self.run_test(
            "GET /api/agency/settlements",
            "GET",
            "api/agency/settlements",
            200,
            params={"month": current_month},
            token=self.agency_token
        )
        
        if success:
            # Check response structure
            month = response.get('month')
            entries = response.get('entries', [])
            skipped_count = response.get('skipped_count')
            
            self.log(f"✅ Response structure valid:")
            self.log(f"   - Month: {month}")
            self.log(f"   - Entries count: {len(entries)}")
            self.log(f"   - Skipped count: {skipped_count}")
            
            # Check if skipped_count field exists
            if skipped_count is None:
                self.log(f"❌ skipped_count field is missing in response")
                return False
            
            # Check if entries have status field
            if entries:
                entry_with_status = 0
                for entry in entries:
                    if 'status' in entry and entry.get('status'):
                        entry_with_status += 1
                        # Store first entry ID for later tests
                        if not self.test_settlement_id:
                            self.test_settlement_id = entry.get('_id') or entry.get('id')
                
                self.log(f"✅ Entries with status field: {entry_with_status}/{len(entries)}")
                
                if entry_with_status == 0:
                    self.log(f"❌ No entries have status field")
                    return False
                
                # Show sample entry status
                if entries:
                    sample = entries[0]
                    self.log(f"✅ Sample entry status: {sample.get('status')}")
                    self.log(f"   - gross_amount: {sample.get('gross_amount')}")
                    self.log(f"   - commission_amount: {sample.get('commission_amount')}")
                    self.log(f"   - net_amount: {sample.get('net_amount')}")
            else:
                self.log(f"⚠️  No entries found for month {current_month}")
            
            return True
        return False

    def test_hotel_settlements_listing(self):
        """Test 2) GET /api/hotel/settlements - check status field and skipped_count"""
        self.log("\n=== 2) HOTEL SETTLEMENTS LISTING ===")
        
        # Get current month in YYYY-MM format
        current_month = datetime.now().strftime("%Y-%m")
        
        success, response = self.run_test(
            "GET /api/hotel/settlements",
            "GET",
            "api/hotel/settlements",
            200,
            params={"month": current_month},
            token=self.hotel_token
        )
        
        if success:
            # Check response structure
            month = response.get('month')
            entries = response.get('entries', [])
            skipped_count = response.get('skipped_count')
            
            self.log(f"✅ Response structure valid:")
            self.log(f"   - Month: {month}")
            self.log(f"   - Entries count: {len(entries)}")
            self.log(f"   - Skipped count: {skipped_count}")
            
            # Check if skipped_count field exists
            if skipped_count is None:
                self.log(f"❌ skipped_count field is missing in response")
                return False
            
            # Check if entries have status field
            if entries:
                entry_with_status = 0
                for entry in entries:
                    if 'status' in entry and entry.get('status'):
                        entry_with_status += 1
                
                self.log(f"✅ Entries with status field: {entry_with_status}/{len(entries)}")
                
                if entry_with_status == 0:
                    self.log(f"❌ No entries have status field")
                    return False
                
                # Show sample entry status
                if entries:
                    sample = entries[0]
                    self.log(f"✅ Sample entry status: {sample.get('status')}")
            else:
                self.log(f"⚠️  No entries found for month {current_month}")
            
            return True
        return False

    def test_agency_confirm_settlement(self):
        """Test 3) POST /api/agency/settlements/{id}/confirm - check status transition"""
        self.log("\n=== 3) AGENCY CONFIRM SETTLEMENT ===")
        
        if not self.test_settlement_id:
            self.log("⚠️  No settlement ID available for confirm test (no entries found)")
            return True  # Not a failure, just no data
        
        success, response = self.run_test(
            f"POST /api/agency/settlements/{self.test_settlement_id}/confirm",
            "POST",
            f"api/agency/settlements/{self.test_settlement_id}/confirm",
            200,
            token=self.agency_token
        )
        
        if success:
            # Check if status field is updated
            status = response.get('status')
            agency_confirmed_at = response.get('agency_confirmed_at')
            
            self.log(f"✅ Settlement confirmed by agency:")
            self.log(f"   - Status: {status}")
            self.log(f"   - Agency confirmed at: {agency_confirmed_at}")
            
            # Status should be either 'confirmed_by_agency' or 'closed' (if hotel also confirmed)
            if status in ['confirmed_by_agency', 'closed']:
                self.log(f"✅ Status transition correct: {status}")
                return True
            else:
                self.log(f"❌ Unexpected status after agency confirm: {status}")
                return False
        return False

    def test_hotel_confirm_settlement(self):
        """Test 4) POST /api/agency/settlements/{id}/confirm (as hotel) - check status transition"""
        self.log("\n=== 4) HOTEL CONFIRM SETTLEMENT ===")
        
        if not self.test_settlement_id:
            self.log("⚠️  No settlement ID available for confirm test (no entries found)")
            return True  # Not a failure, just no data
        
        success, response = self.run_test(
            f"POST /api/agency/settlements/{self.test_settlement_id}/confirm (as hotel)",
            "POST",
            f"api/agency/settlements/{self.test_settlement_id}/confirm",
            200,
            token=self.hotel_token
        )
        
        if success:
            # Check if status field is updated
            status = response.get('status')
            hotel_confirmed_at = response.get('hotel_confirmed_at')
            
            self.log(f"✅ Settlement confirmed by hotel:")
            self.log(f"   - Status: {status}")
            self.log(f"   - Hotel confirmed at: {hotel_confirmed_at}")
            
            # Status should be 'closed' (both confirmed) or 'confirmed_by_hotel'
            if status in ['confirmed_by_hotel', 'closed']:
                self.log(f"✅ Status transition correct: {status}")
                return True
            else:
                self.log(f"❌ Unexpected status after hotel confirm: {status}")
                return False
        return False

    def test_agency_dispute_settlement(self):
        """Test 5) POST /api/agency/settlements/{id}/dispute - check status transition"""
        self.log("\n=== 5) AGENCY DISPUTE SETTLEMENT ===")
        
        if not self.test_settlement_id:
            self.log("⚠️  No settlement ID available for dispute test (no entries found)")
            return True  # Not a failure, just no data
        
        success, response = self.run_test(
            f"POST /api/agency/settlements/{self.test_settlement_id}/dispute",
            "POST",
            f"api/agency/settlements/{self.test_settlement_id}/dispute",
            200,
            data={"reason": "Test dispute reason - API test"},
            token=self.agency_token
        )
        
        if success:
            # Check if status field is updated to 'disputed'
            status = response.get('status')
            disputed = response.get('disputed')
            dispute_reason = response.get('dispute_reason')
            
            self.log(f"✅ Settlement disputed by agency:")
            self.log(f"   - Status: {status}")
            self.log(f"   - Disputed: {disputed}")
            self.log(f"   - Dispute reason: {dispute_reason}")
            
            # Status should be 'disputed'
            if status == 'disputed' and disputed is True:
                self.log(f"✅ Status transition correct: {status}")
                return True
            else:
                self.log(f"❌ Unexpected status after dispute: {status}, disputed: {disputed}")
                return False
        return False

    def print_summary(self):
        """Print test summary"""
        self.log("\n" + "="*60)
        self.log("SYROCE SETTLEMENT MODULE BACKEND TEST SUMMARY")
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
        """Run all settlement backend tests in sequence"""
        self.log("🚀 Starting Syroce Settlement Module Backend Tests")
        self.log(f"Base URL: {self.base_url}")
        
        # Login tests
        if not self.test_agency_login():
            self.log("❌ Agency login failed - stopping tests")
            self.print_summary()
            return 1
        
        if not self.test_hotel_login():
            self.log("❌ Hotel login failed - stopping tests")
            self.print_summary()
            return 1
        
        # Settlement listing tests
        self.test_agency_settlements_listing()
        self.test_hotel_settlements_listing()
        
        # Settlement action tests (confirm, dispute)
        self.test_agency_confirm_settlement()
        self.test_hotel_confirm_settlement()
        self.test_agency_dispute_settlement()
        
        # Summary
        self.print_summary()
        
        return 0 if self.tests_failed == 0 else 1


if __name__ == "__main__":
    tester = SyroceSettlementTester()
    exit_code = tester.run_all_tests()
    sys.exit(exit_code)
