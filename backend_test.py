#!/usr/bin/env python3
"""
Tour Voucher PDF Endpoint Backend Test
Tests the new tour voucher PDF endpoint flow including offline payment preparation and public PDF access
"""
import requests
import sys
import uuid
from datetime import datetime, timedelta, date

class TourVoucherPDFTester:
    def __init__(self, base_url="https://syroce-tours.preview.emergentagent.com"):
        self.base_url = base_url
        self.agency_admin_token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.failed_tests = []
        
        # Store tour and booking request IDs for testing
        self.active_tour_id = None
        self.created_request_id = None
        
        # Store bookings for voucher testing
        self.booking_with_voucher = None
        self.booking_without_voucher = None
        self.new_voucher_id = None

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

    def test_agency_admin_login(self):
        """Test agency admin login with agency1@demo.test / agency123"""
        self.log("\n=== A) AGENCY ADMIN LOGIN ===")
        success, response = self.run_test(
            "Agency Admin Login (agency1@demo.test/agency123)",
            "POST",
            "api/auth/login",
            200,
            data={"email": "agency1@demo.test", "password": "agency123"},
            headers_override={'Content-Type': 'application/json'}
        )
        if success and 'access_token' in response:
            self.agency_admin_token = response['access_token']
            user = response.get('user', {})
            agency_id = user.get('agency_id')
            roles = user.get('roles', [])
            
            if agency_id and ('agency_admin' in roles):
                self.log(f"✅ Agency admin login successful - agency_id: {agency_id}, roles: {roles}")
                return True
            else:
                self.log(f"❌ Missing agency_id or agency_admin role: {agency_id}, {roles}")
                return False
        return False

    def test_get_active_tours(self):
        """Test GET /api/public/tours to find an active tour for booking"""
        self.log("\n=== B) GET ACTIVE TOURS ===")
        
        success, response = self.run_test(
            "GET /api/public/tours",
            "GET",
            "api/public/tours",
            200
        )
        
        if success:
            if isinstance(response, list) and len(response) > 0:
                # Find an active tour, preferably one with agency_id
                for tour in response:
                    if tour.get('status') == 'active' and tour.get('title') == 'Test Tour for Booking':
                        self.active_tour_id = tour.get('id')
                        title = tour.get('title', 'Unknown')
                        self.log(f"✅ Found active tour with agency_id: {title} (ID: {self.active_tour_id})")
                        return True
                
                # Fallback to any active tour
                for tour in response:
                    if tour.get('status') == 'active':
                        self.active_tour_id = tour.get('id')
                        title = tour.get('title', 'Unknown')
                        self.log(f"✅ Found active tour: {title} (ID: {self.active_tour_id})")
                        return True
                
                self.log(f"❌ No active tours found in {len(response)} tours")
                return False
            else:
                self.log(f"❌ Expected list with tours, got: {type(response)} with {len(response) if isinstance(response, list) else 'N/A'} items")
                return False
        return False

    def test_public_tour_booking_creation(self):
        """Test POST /api/public/tours/{tour_id}/book"""
        self.log("\n=== C) PUBLIC TOUR BOOKING CREATION ===")
        
        if not self.active_tour_id:
            self.log("❌ No active tour ID available for booking test")
            return False
        
        booking_data = {
            "full_name": "Test User",
            "phone": "+905551112233",
            "email": "test@example.com",
            "desired_date": "2025-12-30",
            "pax": 2,
            "note": "Testing tour booking request"
        }
        
        success, response = self.run_test(
            f"POST /api/public/tours/{self.active_tour_id}/book",
            "POST",
            f"api/public/tours/{self.active_tour_id}/book",
            200,
            data=booking_data
        )
        
        if success:
            # Check response structure
            ok = response.get('ok')
            request_id = response.get('request_id')
            status = response.get('status')
            
            if ok is True and request_id and status == 'new':
                self.created_request_id = request_id
                self.log(f"✅ Tour booking created successfully: request_id={request_id}, status={status}")
                return True
            else:
                self.log(f"❌ Invalid response structure: ok={ok}, request_id={request_id}, status={status}")
                return False
        return False

    def test_agency_tour_bookings_list(self):
        """Test GET /api/agency/tour-bookings?status=new"""
        self.log("\n=== D) AGENCY TOUR BOOKINGS LIST ===")
        
        success, response = self.run_test(
            "GET /api/agency/tour-bookings?status=new",
            "GET",
            "api/agency/tour-bookings?status=new",
            200,
            token=self.agency_admin_token
        )
        
        if success:
            if isinstance(response, dict) and 'items' in response:
                items = response['items']
                self.log(f"✅ Tour bookings list retrieved - found {len(items)} new requests")
                
                # Check if our created request is in the list
                if self.created_request_id:
                    found_request = None
                    for item in items:
                        if item.get('id') == self.created_request_id:
                            found_request = item
                            break
                    
                    if found_request:
                        # Validate required fields
                        required_fields = ['id', 'tour_title', 'guest', 'desired_date', 'pax', 'status', 'note']
                        missing_fields = []
                        for field in required_fields:
                            if field not in found_request:
                                missing_fields.append(field)
                        
                        if not missing_fields:
                            guest = found_request.get('guest', {})
                            guest_name = guest.get('full_name')
                            guest_phone = guest.get('phone')
                            self.log(f"✅ Created request found with all required fields: guest={guest_name}, phone={guest_phone}")
                        else:
                            self.log(f"❌ Created request missing fields: {missing_fields}")
                            return False
                    else:
                        self.log(f"⚠️  Created request {self.created_request_id} not found in list (might be in different agency)")
                
                return True
            else:
                self.log(f"❌ Expected dict with 'items' key, got: {type(response)}")
                return False
        return False

    def test_tour_booking_status_update(self):
        """Test POST /api/agency/tour-bookings/{id}/set-status"""
        self.log("\n=== E) TOUR BOOKING STATUS UPDATE ===")
        
        if not self.created_request_id:
            self.log("❌ No created request ID available for status update test")
            return False
        
        # Test updating status to approved
        update_data = {"status": "approved"}
        
        success, response = self.run_test(
            f"POST /api/agency/tour-bookings/{self.created_request_id}/set-status",
            "POST",
            f"api/agency/tour-bookings/{self.created_request_id}/set-status",
            200,
            data=update_data,
            token=self.agency_admin_token
        )
        
        if success:
            ok = response.get('ok')
            status = response.get('status')
            
            if ok is True and status == 'approved':
                self.log(f"✅ Status update successful: ok={ok}, status={status}")
                return True
            else:
                self.log(f"❌ Invalid status update response: ok={ok}, status={status}")
                return False
        return False

    def test_tour_booking_status_verification(self):
        """Test GET /api/agency/tour-bookings?status=approved to verify status update"""
        self.log("\n=== F) TOUR BOOKING STATUS VERIFICATION ===")
        
        success, response = self.run_test(
            "GET /api/agency/tour-bookings?status=approved",
            "GET",
            "api/agency/tour-bookings?status=approved",
            200,
            token=self.agency_admin_token
        )
        
        if success:
            if isinstance(response, dict) and 'items' in response:
                items = response['items']
                self.log(f"✅ Approved tour bookings list retrieved - found {len(items)} approved requests")
                
                # Check if our updated request is in the approved list
                if self.created_request_id:
                    found_request = None
                    for item in items:
                        if item.get('id') == self.created_request_id:
                            found_request = item
                            break
                    
                    if found_request and found_request.get('status') == 'approved':
                        self.log(f"✅ Request {self.created_request_id} found in approved list with correct status")
                    else:
                        self.log(f"⚠️  Request {self.created_request_id} not found in approved list or status incorrect")
                
                return True
            else:
                self.log(f"❌ Expected dict with 'items' key, got: {type(response)}")
                return False
        return False

    def test_permission_checks(self):
        """Test permission and validation checks"""
        self.log("\n=== G) PERMISSION & VALIDATION CHECKS ===")
        
        all_passed = True
        
        # Test 1: Missing/invalid token for agency endpoints should return 401
        success, response = self.run_test(
            "GET /api/agency/tour-bookings (no auth - should fail)",
            "GET",
            "api/agency/tour-bookings",
            401,
            token=None
        )
        if not success:
            self.log("❌ Auth test failed - expected 401 for missing token")
            all_passed = False
        
        # Test 2: Invalid status update should return 400
        if self.created_request_id:
            invalid_status_data = {"status": "foo"}
            success, response = self.run_test(
                f"POST /api/agency/tour-bookings/{self.created_request_id}/set-status (invalid status)",
                "POST",
                f"api/agency/tour-bookings/{self.created_request_id}/set-status",
                400,
                data=invalid_status_data,
                token=self.agency_admin_token
            )
            if success:
                # Check if the error detail is correct
                try:
                    if isinstance(response, dict) and response.get('detail') == 'INVALID_STATUS':
                        self.log("✅ Invalid status correctly rejected with INVALID_STATUS")
                    else:
                        self.log(f"⚠️  Invalid status rejected but unexpected detail: {response}")
                except:
                    pass
            else:
                self.log("❌ Invalid status test failed - expected 400")
                all_passed = False
        
        # Test 3: Booking non-existing tour should return 404
        fake_tour_id = "non-existing-tour-id"
        booking_data = {
            "full_name": "Test User",
            "phone": "+905551112233",
            "email": "test@example.com",
            "desired_date": "2025-12-30",
            "pax": 2,
            "note": "Testing with fake tour ID"
        }
        
        success, response = self.run_test(
            f"POST /api/public/tours/{fake_tour_id}/book (non-existing tour)",
            "POST",
            f"api/public/tours/{fake_tour_id}/book",
            404,
            data=booking_data
        )
        if success:
            # Check if the error detail is correct
            try:
                if isinstance(response, dict) and response.get('detail') == 'TOUR_NOT_FOUND':
                    self.log("✅ Non-existing tour correctly rejected with TOUR_NOT_FOUND")
                else:
                    self.log(f"⚠️  Non-existing tour rejected but unexpected detail: {response}")
            except:
                pass
        else:
            self.log("❌ Non-existing tour test failed - expected 404")
            all_passed = False
        
        return all_passed

    def test_tour_booking_detail_endpoint(self):
        """Test GET /api/agency/tour-bookings/{id} - Tour booking detail with internal notes"""
        self.log("\n=== H) TOUR BOOKING DETAIL ENDPOINT (C3) ===")
        
        if not self.created_request_id:
            self.log("❌ No created request ID available for detail test")
            return False
        
        success, response = self.run_test(
            f"GET /api/agency/tour-bookings/{self.created_request_id}",
            "GET",
            f"api/agency/tour-bookings/{self.created_request_id}",
            200,
            token=self.agency_admin_token
        )
        
        if success:
            # Check response structure - should include all fields from list + internal_notes
            required_fields = ['id', 'organization_id', 'agency_id', 'tour_id', 'tour_title', 
                             'guest', 'desired_date', 'pax', 'status', 'note', 'internal_notes']
            missing_fields = []
            for field in required_fields:
                if field not in response:
                    missing_fields.append(field)
            
            if not missing_fields:
                internal_notes = response.get('internal_notes', [])
                self.log(f"✅ Tour booking detail retrieved successfully")
                self.log(f"   - ID: {response.get('id')}")
                self.log(f"   - Tour: {response.get('tour_title')}")
                self.log(f"   - Guest: {response.get('guest', {}).get('full_name')}")
                self.log(f"   - Status: {response.get('status')}")
                self.log(f"   - Internal notes count: {len(internal_notes)}")
                
                # Verify internal_notes is always a list (empty if no notes)
                if isinstance(internal_notes, list):
                    self.log(f"✅ internal_notes field is properly formatted as list")
                    return True
                else:
                    self.log(f"❌ internal_notes should be list, got: {type(internal_notes)}")
                    return False
            else:
                self.log(f"❌ Missing required fields in detail response: {missing_fields}")
                return False
        return False

    def test_add_internal_note_endpoint(self):
        """Test POST /api/agency/tour-bookings/{id}/add-note - Add internal note"""
        self.log("\n=== I) ADD INTERNAL NOTE ENDPOINT (C3) ===")
        
        if not self.created_request_id:
            self.log("❌ No created request ID available for add note test")
            return False
        
        # Test 1: Add valid note
        note_data = {
            "text": "Bu müşteri ile telefon görüşmesi yapıldı. Ödeme detayları konuşuldu."
        }
        
        success, response = self.run_test(
            f"POST /api/agency/tour-bookings/{self.created_request_id}/add-note",
            "POST",
            f"api/agency/tour-bookings/{self.created_request_id}/add-note",
            200,
            data=note_data,
            token=self.agency_admin_token
        )
        
        if success:
            ok = response.get('ok')
            if ok is True:
                self.log(f"✅ Internal note added successfully: ok={ok}")
                return True
            else:
                self.log(f"❌ Invalid add note response: ok={ok}")
                return False
        return False

    def test_verify_internal_note_in_detail(self):
        """Test that added internal note appears in detail endpoint"""
        self.log("\n=== J) VERIFY INTERNAL NOTE IN DETAIL (C3) ===")
        
        if not self.created_request_id:
            self.log("❌ No created request ID available for verification test")
            return False
        
        success, response = self.run_test(
            f"GET /api/agency/tour-bookings/{self.created_request_id} (verify note)",
            "GET",
            f"api/agency/tour-bookings/{self.created_request_id}",
            200,
            token=self.agency_admin_token
        )
        
        if success:
            internal_notes = response.get('internal_notes', [])
            
            if len(internal_notes) > 0:
                # Check the structure of the latest note
                latest_note = internal_notes[-1]  # Should be the one we just added
                
                required_note_fields = ['text', 'created_at', 'actor']
                missing_note_fields = []
                for field in required_note_fields:
                    if field not in latest_note:
                        missing_note_fields.append(field)
                
                if not missing_note_fields:
                    actor = latest_note.get('actor', {})
                    actor_fields = ['user_id', 'name', 'role']
                    missing_actor_fields = []
                    for field in actor_fields:
                        if field not in actor:
                            missing_actor_fields.append(field)
                    
                    if not missing_actor_fields:
                        self.log(f"✅ Internal note verified in detail response:")
                        self.log(f"   - Text: {latest_note.get('text')[:50]}...")
                        self.log(f"   - Created at: {latest_note.get('created_at')}")
                        self.log(f"   - Actor name: {actor.get('name')}")
                        self.log(f"   - Actor role: {actor.get('role')}")
                        return True
                    else:
                        self.log(f"❌ Missing actor fields in note: {missing_actor_fields}")
                        return False
                else:
                    self.log(f"❌ Missing note fields: {missing_note_fields}")
                    return False
            else:
                self.log(f"❌ No internal notes found after adding note")
                return False
        return False

    def test_add_note_validation_errors(self):
        """Test validation errors for add note endpoint"""
        self.log("\n=== K) ADD NOTE VALIDATION ERRORS (C3) ===")
        
        if not self.created_request_id:
            self.log("❌ No created request ID available for validation test")
            return False
        
        all_passed = True
        
        # Test 1: Empty text should return 400 INVALID_NOTE
        empty_note_data = {"text": ""}
        success, response = self.run_test(
            f"POST /api/agency/tour-bookings/{self.created_request_id}/add-note (empty text)",
            "POST",
            f"api/agency/tour-bookings/{self.created_request_id}/add-note",
            400,
            data=empty_note_data,
            token=self.agency_admin_token
        )
        if success:
            try:
                if isinstance(response, dict) and response.get('detail') == 'INVALID_NOTE':
                    self.log("✅ Empty text correctly rejected with INVALID_NOTE")
                else:
                    self.log(f"⚠️  Empty text rejected but unexpected detail: {response}")
            except:
                pass
        else:
            self.log("❌ Empty text validation test failed - expected 400")
            all_passed = False
        
        # Test 2: Single character should return 400 INVALID_NOTE
        short_note_data = {"text": "x"}
        success, response = self.run_test(
            f"POST /api/agency/tour-bookings/{self.created_request_id}/add-note (1 char)",
            "POST",
            f"api/agency/tour-bookings/{self.created_request_id}/add-note",
            400,
            data=short_note_data,
            token=self.agency_admin_token
        )
        if success:
            try:
                if isinstance(response, dict) and response.get('detail') == 'INVALID_NOTE':
                    self.log("✅ Single character correctly rejected with INVALID_NOTE")
                else:
                    self.log(f"⚠️  Single character rejected but unexpected detail: {response}")
            except:
                pass
        else:
            self.log("❌ Single character validation test failed - expected 400")
            all_passed = False
        
        return all_passed

    def test_authorization_checks_c3(self):
        """Test authorization checks for C3 endpoints"""
        self.log("\n=== L) AUTHORIZATION CHECKS C3 ===")
        
        if not self.created_request_id:
            self.log("❌ No created request ID available for auth test")
            return False
        
        all_passed = True
        
        # Test 1: GET detail without JWT should return 401
        success, response = self.run_test(
            f"GET /api/agency/tour-bookings/{self.created_request_id} (no auth)",
            "GET",
            f"api/agency/tour-bookings/{self.created_request_id}",
            401,
            token=None
        )
        if not success:
            self.log("❌ GET detail auth test failed - expected 401 for missing token")
            all_passed = False
        
        # Test 2: POST add-note without JWT should return 401
        note_data = {"text": "Test note"}
        success, response = self.run_test(
            f"POST /api/agency/tour-bookings/{self.created_request_id}/add-note (no auth)",
            "POST",
            f"api/agency/tour-bookings/{self.created_request_id}/add-note",
            401,
            data=note_data,
            token=None
        )
        if not success:
            self.log("❌ POST add-note auth test failed - expected 401 for missing token")
            all_passed = False
        
        # Test 3: Try to access non-existing booking (should return 404)
        fake_request_id = "507f1f77bcf86cd799439011"  # Valid ObjectId format but non-existing
        success, response = self.run_test(
            f"GET /api/agency/tour-bookings/{fake_request_id} (non-existing)",
            "GET",
            f"api/agency/tour-bookings/{fake_request_id}",
            404,
            token=self.agency_admin_token
        )
        if success:
            try:
                if isinstance(response, dict) and response.get('detail') == 'TOUR_BOOKING_REQUEST_NOT_FOUND':
                    self.log("✅ Non-existing booking correctly rejected with TOUR_BOOKING_REQUEST_NOT_FOUND")
                else:
                    self.log(f"⚠️  Non-existing booking rejected but unexpected detail: {response}")
            except:
                pass
        else:
            self.log("❌ Non-existing booking test failed - expected 404")
            all_passed = False
        
        return all_passed

    def print_summary(self):
        """Print test summary"""
        self.log("\n" + "="*60)
        self.log("TOUR VOUCHER PDF BACKEND TEST SUMMARY")
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

    def test_agency_tour_bookings_list_for_voucher(self):
        """Test GET /api/agency/tour-bookings to find bookings for voucher testing"""
        self.log("\n=== VOUCHER TEST: GET TOUR BOOKINGS ===")
        
        success, response = self.run_test(
            "GET /api/agency/tour-bookings (for voucher testing)",
            "GET",
            "api/agency/tour-bookings?limit=50",
            200,
            token=self.agency_admin_token
        )
        
        if success:
            if isinstance(response, dict) and 'items' in response:
                items = response['items']
                self.log(f"✅ Found {len(items)} tour bookings for voucher testing")
                
                # Look for bookings with different payment/voucher states
                booking_with_voucher = None
                booking_without_voucher = None
                
                for item in items:
                    payment = item.get('payment', {})
                    voucher = item.get('voucher', {})
                    status = item.get('status', '').lower()
                    
                    self.log(f"   Booking {item.get('id')}: status={status}, payment_mode={payment.get('mode')}, voucher_id={voucher.get('voucher_id')}")
                    
                    # Check if this booking has payment + voucher already
                    if (payment.get('mode') == 'offline' and 
                        payment.get('reference_code') and 
                        voucher.get('voucher_id') and 
                        voucher.get('pdf_url')):
                        booking_with_voucher = item
                        self.log(f"✅ Found booking with existing voucher: {item.get('id')} (voucher_id: {voucher.get('voucher_id')})")
                    
                    # Check if this booking has payment but no voucher
                    elif (payment.get('mode') == 'offline' and 
                          payment.get('reference_code') and 
                          not voucher.get('voucher_id')):
                        booking_without_voucher = item
                        self.log(f"✅ Found booking with payment but no voucher: {item.get('id')}")
                    
                    # Check if this booking has no payment and status allows payment (new/approved)
                    elif (not payment.get('mode') and status in ['new', 'approved']):
                        if not booking_without_voucher:  # Use this if we don't have a better candidate
                            booking_without_voucher = item
                            self.log(f"✅ Found booking without payment (status={status}): {item.get('id')} (can be used for prepare-offline-payment)")
                
                # Store the bookings for later tests
                self.booking_with_voucher = booking_with_voucher
                self.booking_without_voucher = booking_without_voucher
                
                if booking_with_voucher:
                    self.log(f"✅ Will test existing voucher: {booking_with_voucher.get('id')}")
                else:
                    self.log("⚠️  No booking with existing voucher found")
                    
                if booking_without_voucher:
                    self.log(f"✅ Will test prepare offline payment: {booking_without_voucher.get('id')}")
                else:
                    self.log("⚠️  No suitable booking for prepare offline payment found")
                
                return True
            else:
                self.log(f"❌ Expected dict with 'items' key, got: {type(response)}")
                return False
        return False

    def test_existing_voucher_pdf_access(self):
        """Test GET /api/public/vouchers/{voucher_id}.pdf for existing voucher"""
        self.log("\n=== VOUCHER TEST: EXISTING VOUCHER PDF ACCESS ===")
        
        if not hasattr(self, 'booking_with_voucher') or not self.booking_with_voucher:
            self.log("⚠️  No booking with existing voucher found - skipping test")
            return True  # Not a failure, just no data to test
        
        voucher = self.booking_with_voucher.get('voucher', {})
        voucher_id = voucher.get('voucher_id')
        
        if not voucher_id:
            self.log("❌ Booking has voucher but no voucher_id")
            return False
        
        # Test public PDF access (no auth required)
        url = f"{self.base_url}/api/public/vouchers/{voucher_id}.pdf"
        self.log(f"🔍 Testing PDF access: {url}")
        
        try:
            response = requests.get(url, timeout=15)
            
            if response.status_code == 200:
                content_type = response.headers.get('Content-Type', '')
                content = response.content
                
                # Verify it's actually a PDF
                if content.startswith(b'%PDF'):
                    self.log(f"✅ PDF access successful - Status: 200, Content-Type: {content_type}, Size: {len(content)} bytes")
                    self.log(f"✅ PDF content verified - starts with '%PDF' as expected")
                    self.tests_passed += 1
                    return True
                else:
                    self.log(f"❌ Response is not a valid PDF - starts with: {content[:20]}")
                    self.tests_failed += 1
                    self.failed_tests.append(f"Existing voucher PDF - Invalid PDF content")
                    return False
            else:
                self.log(f"❌ PDF access failed - Status: {response.status_code}")
                self.log(f"   Response: {response.text[:500]}")
                self.tests_failed += 1
                self.failed_tests.append(f"Existing voucher PDF - Expected 200, got {response.status_code}")
                return False
                
        except Exception as e:
            self.log(f"❌ PDF access error: {str(e)}")
            self.tests_failed += 1
            self.failed_tests.append(f"Existing voucher PDF - Error: {str(e)}")
            return False
        finally:
            self.tests_run += 1

    def test_prepare_offline_payment_and_voucher(self):
        """Test POST /api/agency/tour-bookings/{id}/prepare-offline-payment"""
        self.log("\n=== VOUCHER TEST: PREPARE OFFLINE PAYMENT ===")
        
        if not hasattr(self, 'booking_without_voucher') or not self.booking_without_voucher:
            self.log("⚠️  No booking without voucher found - skipping test")
            return True  # Not a failure, just no data to test
        
        booking_id = self.booking_without_voucher.get('id')
        if not booking_id:
            self.log("❌ Booking without voucher has no ID")
            return False
        
        success, response = self.run_test(
            f"POST /api/agency/tour-bookings/{booking_id}/prepare-offline-payment",
            "POST",
            f"api/agency/tour-bookings/{booking_id}/prepare-offline-payment",
            200,
            token=self.agency_admin_token
        )
        
        if success:
            # Verify response structure
            payment = response.get('payment', {})
            voucher = response.get('voucher', {})
            
            required_payment_fields = ['mode', 'status', 'reference_code', 'due_at', 'iban_snapshot']
            required_voucher_fields = ['enabled', 'voucher_id', 'pdf_url']
            
            missing_payment = [f for f in required_payment_fields if f not in payment]
            missing_voucher = [f for f in required_voucher_fields if f not in voucher]
            
            if not missing_payment and not missing_voucher:
                if (payment.get('mode') == 'offline' and 
                    voucher.get('enabled') is True and 
                    voucher.get('voucher_id') and 
                    voucher.get('pdf_url')):
                    
                    self.log(f"✅ Offline payment prepared successfully:")
                    self.log(f"   - Payment mode: {payment.get('mode')}")
                    self.log(f"   - Reference code: {payment.get('reference_code')}")
                    self.log(f"   - Voucher enabled: {voucher.get('enabled')}")
                    self.log(f"   - Voucher ID: {voucher.get('voucher_id')}")
                    self.log(f"   - PDF URL: {voucher.get('pdf_url')}")
                    
                    # Store voucher_id for next test
                    self.new_voucher_id = voucher.get('voucher_id')
                    return True
                else:
                    self.log(f"❌ Invalid payment/voucher values in response")
                    return False
            else:
                self.log(f"❌ Missing fields - Payment: {missing_payment}, Voucher: {missing_voucher}")
                return False
        return False

    def test_new_voucher_pdf_access(self):
        """Test GET /api/public/vouchers/{voucher_id}.pdf for newly created voucher"""
        self.log("\n=== VOUCHER TEST: NEW VOUCHER PDF ACCESS ===")
        
        if not hasattr(self, 'new_voucher_id') or not self.new_voucher_id:
            self.log("⚠️  No new voucher ID available - skipping test")
            return True  # Not a failure, just no data to test
        
        # Test public PDF access (no auth required)
        url = f"{self.base_url}/api/public/vouchers/{self.new_voucher_id}.pdf"
        self.log(f"🔍 Testing new PDF access: {url}")
        
        try:
            response = requests.get(url, timeout=15)
            
            if response.status_code == 200:
                content_type = response.headers.get('Content-Type', '')
                content = response.content
                
                # Verify it's actually a PDF
                if content.startswith(b'%PDF'):
                    self.log(f"✅ New PDF access successful - Status: 200, Content-Type: {content_type}, Size: {len(content)} bytes")
                    self.log(f"✅ New PDF content verified - starts with '%PDF' as expected")
                    self.tests_passed += 1
                    return True
                else:
                    self.log(f"❌ Response is not a valid PDF - starts with: {content[:20]}")
                    self.tests_failed += 1
                    self.failed_tests.append(f"New voucher PDF - Invalid PDF content")
                    return False
            else:
                self.log(f"❌ New PDF access failed - Status: {response.status_code}")
                self.log(f"   Response: {response.text[:500]}")
                self.tests_failed += 1
                self.failed_tests.append(f"New voucher PDF - Expected 200, got {response.status_code}")
                return False
                
        except Exception as e:
            self.log(f"❌ New PDF access error: {str(e)}")
            self.tests_failed += 1
            self.failed_tests.append(f"New voucher PDF - Error: {str(e)}")
            return False
        finally:
            self.tests_run += 1

    def test_voucher_not_found_error(self):
        """Test GET /api/public/vouchers/{non_existent_id}.pdf error handling"""
        self.log("\n=== VOUCHER TEST: VOUCHER NOT FOUND ERROR ===")
        
        fake_voucher_id = "vtr_nonexistent123456789012"
        url = f"{self.base_url}/api/public/vouchers/{fake_voucher_id}.pdf"
        
        try:
            response = requests.get(url, timeout=15)
            
            if response.status_code == 404:
                try:
                    error_data = response.json()
                    detail = error_data.get('detail', {})
                    
                    if detail.get('code') == 'VOUCHER_NOT_FOUND':
                        self.log(f"✅ Voucher not found error handled correctly:")
                        self.log(f"   - Status: 404")
                        self.log(f"   - Error code: {detail.get('code')}")
                        self.log(f"   - Error message: {detail.get('message')}")
                        self.tests_passed += 1
                        return True
                    else:
                        self.log(f"❌ Wrong error code - Expected 'VOUCHER_NOT_FOUND', got: {detail.get('code')}")
                        self.tests_failed += 1
                        self.failed_tests.append(f"Voucher not found - Wrong error code")
                        return False
                except:
                    self.log(f"❌ Invalid JSON response for 404 error")
                    self.tests_failed += 1
                    self.failed_tests.append(f"Voucher not found - Invalid JSON response")
                    return False
            else:
                self.log(f"❌ Wrong status code - Expected 404, got: {response.status_code}")
                self.tests_failed += 1
                self.failed_tests.append(f"Voucher not found - Expected 404, got {response.status_code}")
                return False
                
        except Exception as e:
            self.log(f"❌ Voucher not found test error: {str(e)}")
            self.tests_failed += 1
            self.failed_tests.append(f"Voucher not found - Error: {str(e)}")
            return False
        finally:
            self.tests_run += 1

    def run_all_tests(self):
        """Run all Tour Voucher PDF backend tests in sequence"""
        self.log("🚀 Starting Tour Voucher PDF Backend Tests")
        self.log(f"Base URL: {self.base_url}")
        
        # 1) Agency admin login
        if not self.test_agency_admin_login():
            self.log("❌ Agency admin login failed - stopping tests")
            self.print_summary()
            return 1
        
        # 2) Get tour bookings for voucher testing
        if not self.test_agency_tour_bookings_list_for_voucher():
            self.log("❌ Failed to get tour bookings - stopping tests")
            self.print_summary()
            return 1
        
        # 3) Test existing voucher PDF access (scenario a)
        self.test_existing_voucher_pdf_access()
        
        # 4) Test prepare offline payment for booking without voucher (scenario b)
        self.test_prepare_offline_payment_and_voucher()
        
        # 5) Test new voucher PDF access (scenario b continued)
        self.test_new_voucher_pdf_access()
        
        # 6) Test error handling for non-existent voucher
        self.test_voucher_not_found_error()
        
        # Summary
        self.print_summary()
        
        return 0 if self.tests_failed == 0 else 1


if __name__ == "__main__":
    tester = TourVoucherPDFTester()
    exit_code = tester.run_all_tests()
    sys.exit(exit_code)