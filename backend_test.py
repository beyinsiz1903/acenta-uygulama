#!/usr/bin/env python3
"""
Hotel Approval/Reject Workflow Backend Testing

Tests the following scenarios:
1. Login authentication  
2. List tours to get tour_id
3. Create tour reservation (should be 'pending', not 'CONFIRMED')
4. Find and verify new reservation status
5. Test REJECT workflow with reason
6. Test invalid transitions on rejected reservations
7. Test CONFIRM workflow
8. Test invalid double confirm
9. Test cancel from confirmed status
10. Verify status history tracking
"""

import asyncio
import json
import aiohttp
import sys
from datetime import datetime
from typing import Dict, Any, Optional

# Backend URL
BASE_URL = "https://hotel-reject-system.preview.emergentagent.com"
API_BASE = f"{BASE_URL}/api"

class HotelWorkflowTester:
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.access_token: Optional[str] = None
        self.test_results = []
        self.tour_id: Optional[str] = None
        self.first_reservation_id: Optional[str] = None
        self.second_reservation_id: Optional[str] = None
        
    async def setup(self):
        """Setup HTTP session"""
        self.session = aiohttp.ClientSession()
        
    async def cleanup(self):
        """Cleanup resources"""
        if self.session:
            await self.session.close()
            
    def log_result(self, test_name: str, success: bool, details: str):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {details}")
        self.test_results.append({
            'test': test_name,
            'success': success,
            'details': details,
            'timestamp': datetime.now().isoformat()
        })
        
    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers"""
        if not self.access_token:
            return {}
        return {"Authorization": f"Bearer {self.access_token}"}
        
    async def test_login(self):
        """Test 1: POST /api/auth/login"""
        test_name = "Login Authentication"
        try:
            # Try different credentials from test results 
            credentials_to_try = [
                {"email": "admin@acenta.test", "password": "admin123"},
                {"email": "demo@acenta.test", "password": "Demo12345!x"}
            ]
            
            for creds in credentials_to_try:
                payload = creds
            
            
                async with self.session.post(f"{API_BASE}/auth/login", json=payload) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if "access_token" in data:
                            self.access_token = data["access_token"]
                            self.log_result(test_name, True, f"Login successful with {payload['email']}, token obtained")
                            return True
                        else:
                            self.log_result(test_name, False, f"No access_token in response for {payload['email']}: {data}")
                    else:
                        text = await resp.text()
                        print(f"Failed login attempt for {payload['email']}: HTTP {resp.status}: {text}")
                        
            # If all attempts failed
            self.log_result(test_name, False, "All credential combinations failed")
                    
        except Exception as e:
            self.log_result(test_name, False, f"Exception: {str(e)}")
            
        return False
        
    async def test_list_tours(self):
        """Test 2: GET /api/tours - Get tour_id for reservation"""
        test_name = "List Tours"
        try:
            headers = self.get_auth_headers()
            
            async with self.session.get(f"{API_BASE}/tours", headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"Tours API response: {data}")
                    items = data.get("items", [])
                    if len(items) > 0:
                        self.tour_id = items[0]["id"]
                        self.log_result(test_name, True, f"Found {len(items)} tours, using tour_id: {self.tour_id}")
                        return True
                    else:
                        # Let's also try admin endpoint to check for tours
                        async with self.session.get(f"{API_BASE}/admin/tours", headers=headers) as admin_resp:
                            if admin_resp.status == 200:
                                admin_data = await admin_resp.json()
                                print(f"Admin tours API response: {admin_data}")
                                if len(admin_data) > 0:
                                    # Use admin tour data
                                    self.tour_id = admin_data[0]["id"]
                                    self.log_result(test_name, True, f"Found {len(admin_data)} tours via admin endpoint, using tour_id: {self.tour_id}")
                                    return True
                        self.log_result(test_name, False, f"No tours found. Regular: {data}, Admin endpoint also checked.")
                else:
                    text = await resp.text()
                    self.log_result(test_name, False, f"HTTP {resp.status}: {text}")
                    
        except Exception as e:
            self.log_result(test_name, False, f"Exception: {str(e)}")
            
        return False
        
    async def test_create_tour_reservation(self, guest_name: str):
        """Test 3 & 7: POST /api/tours/{tour_id}/reserve - Create reservation"""
        test_name = f"Create Tour Reservation ({guest_name})"
        try:
            if not self.tour_id:
                self.log_result(test_name, False, "No tour_id available")
                return None
                
            headers = self.get_auth_headers()
            payload = {
                "travel_date": "2025-08-15",
                "adults": 2,
                "children": 0,
                "guest_name": guest_name,
                "guest_email": f"{guest_name.lower().replace(' ', '.')}@test.com",
                "guest_phone": "+905551234567"
            }
            
            async with self.session.post(f"{API_BASE}/tours/{self.tour_id}/reserve", 
                                       json=payload, headers=headers) as resp:
                if resp.status == 201:
                    data = await resp.json()
                    reservation_code = data.get("reservation_code")
                    status = data.get("status")
                    
                    if status == "pending":
                        self.log_result(test_name, True, 
                                      f"Reservation created: {reservation_code}, status: {status} (correctly pending)")
                        return reservation_code
                    else:
                        self.log_result(test_name, False, 
                                      f"Reservation created but status is '{status}' instead of 'pending'")
                        return reservation_code
                else:
                    text = await resp.text()
                    self.log_result(test_name, False, f"HTTP {resp.status}: {text}")
                    
        except Exception as e:
            self.log_result(test_name, False, f"Exception: {str(e)}")
            
        return None
        
    async def test_find_reservation_by_pnr(self, reservation_code: str):
        """Test 4: GET /api/reservations - Find reservation by PNR"""
        test_name = f"Find Reservation by PNR ({reservation_code})"
        try:
            headers = self.get_auth_headers()
            
            async with self.session.get(f"{API_BASE}/reservations?q={reservation_code}", 
                                      headers=headers) as resp:
                if resp.status == 200:
                    reservations = await resp.json()
                    if len(reservations) > 0:
                        reservation = reservations[0]
                        reservation_id = reservation.get("id")
                        status = reservation.get("status")
                        pnr = reservation.get("pnr")
                        
                        if pnr == reservation_code and status == "pending":
                            self.log_result(test_name, True, 
                                          f"Found reservation ID: {reservation_id}, status: {status}")
                            return reservation_id
                        else:
                            self.log_result(test_name, False, 
                                          f"Found reservation but PNR: {pnr}, status: {status}")
                            return reservation_id
                    else:
                        self.log_result(test_name, False, "No reservations found")
                else:
                    text = await resp.text()
                    self.log_result(test_name, False, f"HTTP {resp.status}: {text}")
                    
        except Exception as e:
            self.log_result(test_name, False, f"Exception: {str(e)}")
            
        return None
        
    async def test_reject_reservation(self, reservation_id: str):
        """Test 5: POST /api/reservations/{reservation_id}/reject"""
        test_name = "Reject Reservation"
        try:
            headers = self.get_auth_headers()
            payload = {"reason": "Oda müsait değil"}
            
            async with self.session.post(f"{API_BASE}/reservations/{reservation_id}/reject",
                                       json=payload, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    status = data.get("status")
                    rejection_reason = data.get("rejection_reason")
                    rejected_at = data.get("rejected_at")
                    rejected_by = data.get("rejected_by")
                    status_history = data.get("status_history", [])
                    
                    success = True
                    details = []
                    
                    if status != "rejected":
                        success = False
                        details.append(f"Status is '{status}', expected 'rejected'")
                    else:
                        details.append(f"Status: {status}")
                        
                    if rejection_reason != "Oda müsait değil":
                        success = False
                        details.append(f"Rejection reason: '{rejection_reason}', expected 'Oda müsait değil'")
                    else:
                        details.append(f"Rejection reason: {rejection_reason}")
                        
                    if not rejected_at:
                        success = False
                        details.append("Missing rejected_at")
                    else:
                        details.append(f"Rejected at: {rejected_at}")
                        
                    if not rejected_by:
                        success = False
                        details.append("Missing rejected_by")
                    else:
                        details.append(f"Rejected by: {rejected_by}")
                        
                    if len(status_history) == 0:
                        success = False
                        details.append("Missing status_history")
                    else:
                        details.append(f"Status history entries: {len(status_history)}")
                        
                    self.log_result(test_name, success, "; ".join(details))
                    return success
                else:
                    text = await resp.text()
                    self.log_result(test_name, False, f"HTTP {resp.status}: {text}")
                    
        except Exception as e:
            self.log_result(test_name, False, f"Exception: {str(e)}")
            
        return False
        
    async def test_invalid_transition_rejected_to_confirmed(self, reservation_id: str):
        """Test 6: POST /api/reservations/{reservation_id}/confirm on rejected reservation"""
        test_name = "Invalid Transition (Rejected -> Confirmed)"
        try:
            headers = self.get_auth_headers()
            
            async with self.session.post(f"{API_BASE}/reservations/{reservation_id}/confirm",
                                       headers=headers) as resp:
                if resp.status == 409:
                    text = await resp.text()
                    self.log_result(test_name, True, f"Correctly returned 409 error: {text}")
                    return True
                else:
                    text = await resp.text()
                    self.log_result(test_name, False, 
                                  f"Expected 409 error but got HTTP {resp.status}: {text}")
                    
        except Exception as e:
            self.log_result(test_name, False, f"Exception: {str(e)}")
            
        return False
        
    async def test_confirm_reservation(self, reservation_id: str):
        """Test 8: POST /api/reservations/{reservation_id}/confirm"""
        test_name = "Confirm Reservation"
        try:
            headers = self.get_auth_headers()
            
            async with self.session.post(f"{API_BASE}/reservations/{reservation_id}/confirm",
                                       headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    status = data.get("status")
                    confirmed_at = data.get("confirmed_at")
                    confirmed_by = data.get("confirmed_by")
                    status_history = data.get("status_history", [])
                    
                    success = True
                    details = []
                    
                    if status != "confirmed":
                        success = False
                        details.append(f"Status is '{status}', expected 'confirmed'")
                    else:
                        details.append(f"Status: {status}")
                        
                    if not confirmed_at:
                        success = False
                        details.append("Missing confirmed_at")
                    else:
                        details.append(f"Confirmed at: {confirmed_at}")
                        
                    if not confirmed_by:
                        success = False
                        details.append("Missing confirmed_by")
                    else:
                        details.append(f"Confirmed by: {confirmed_by}")
                        
                    if len(status_history) == 0:
                        success = False
                        details.append("Missing status_history")
                    else:
                        details.append(f"Status history entries: {len(status_history)}")
                        
                    self.log_result(test_name, success, "; ".join(details))
                    return success
                else:
                    text = await resp.text()
                    self.log_result(test_name, False, f"HTTP {resp.status}: {text}")
                    
        except Exception as e:
            self.log_result(test_name, False, f"Exception: {str(e)}")
            
        return False
        
    async def test_double_confirm(self, reservation_id: str):
        """Test 9: POST /api/reservations/{reservation_id}/confirm again (should fail)"""
        test_name = "Double Confirm (Invalid Transition)"
        try:
            headers = self.get_auth_headers()
            
            async with self.session.post(f"{API_BASE}/reservations/{reservation_id}/confirm",
                                       headers=headers) as resp:
                if resp.status == 409:
                    text = await resp.text()
                    self.log_result(test_name, True, f"Correctly returned 409 error: {text}")
                    return True
                else:
                    text = await resp.text()
                    self.log_result(test_name, False, 
                                  f"Expected 409 error but got HTTP {resp.status}: {text}")
                    
        except Exception as e:
            self.log_result(test_name, False, f"Exception: {str(e)}")
            
        return False
        
    async def test_cancel_from_confirmed(self, reservation_id: str):
        """Test 10: POST /api/reservations/{reservation_id}/cancel from confirmed"""
        test_name = "Cancel from Confirmed"
        try:
            headers = self.get_auth_headers()
            
            async with self.session.post(f"{API_BASE}/reservations/{reservation_id}/cancel",
                                       headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    status = data.get("status")
                    
                    if status == "cancelled":
                        self.log_result(test_name, True, f"Successfully cancelled reservation, status: {status}")
                        return True
                    else:
                        self.log_result(test_name, False, f"Unexpected status: {status}")
                else:
                    text = await resp.text()
                    self.log_result(test_name, False, f"HTTP {resp.status}: {text}")
                    
        except Exception as e:
            self.log_result(test_name, False, f"Exception: {str(e)}")
            
        return False
        
    async def run_all_tests(self):
        """Run the complete hotel approval/reject workflow test suite"""
        print("🚀 Starting Hotel Approval/Reject Workflow Testing")
        print(f"🌐 Testing against: {BASE_URL}")
        print("=" * 80)
        
        try:
            # Test 1: Login
            if not await self.test_login():
                print("\n❌ Login failed - cannot continue with tests")
                return
                
            # Test 2: List tours
            if not await self.test_list_tours():
                print("\n❌ Could not get tours - cannot continue")
                return
                
            # Test 3: Create first reservation for rejection test
            first_reservation_code = await self.test_create_tour_reservation("Test Reject Guest")
            if not first_reservation_code:
                print("\n❌ Could not create first reservation")
                return
                
            # Test 4: Find first reservation
            self.first_reservation_id = await self.test_find_reservation_by_pnr(first_reservation_code)
            if not self.first_reservation_id:
                print("\n❌ Could not find first reservation")
                return
                
            # Test 5: Test reject workflow
            await self.test_reject_reservation(self.first_reservation_id)
            
            # Test 6: Test invalid transition (rejected -> confirmed)
            await self.test_invalid_transition_rejected_to_confirmed(self.first_reservation_id)
            
            # Test 7: Create second reservation for confirmation test
            second_reservation_code = await self.test_create_tour_reservation("Test Confirm Guest")
            if not second_reservation_code:
                print("\n❌ Could not create second reservation")
                return
                
            # Find second reservation
            self.second_reservation_id = await self.test_find_reservation_by_pnr(second_reservation_code)
            if not self.second_reservation_id:
                print("\n❌ Could not find second reservation")
                return
                
            # Test 8: Test confirm workflow
            if await self.test_confirm_reservation(self.second_reservation_id):
                # Test 9: Test double confirm (invalid)
                await self.test_double_confirm(self.second_reservation_id)
                
                # Test 10: Test cancel from confirmed
                await self.test_cancel_from_confirmed(self.second_reservation_id)
                
        except Exception as e:
            print(f"\n❌ Unexpected error during testing: {str(e)}")
            
        finally:
            await self.print_summary()
            
    async def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 80)
        print("📊 TEST SUMMARY")
        print("=" * 80)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r['success'])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"Success Rate: {passed_tests/total_tests*100:.1f}%" if total_tests > 0 else "N/A")
        
        if failed_tests > 0:
            print("\n🚨 FAILED TESTS:")
            for result in self.test_results:
                if not result['success']:
                    print(f"❌ {result['test']}: {result['details']}")
        
        print("\n📝 DETAILED RESULTS:")
        for result in self.test_results:
            status = "✅ PASS" if result['success'] else "❌ FAIL"
            print(f"{status} {result['test']}: {result['details']}")

async def main():
    """Main test runner"""
    tester = HotelWorkflowTester()
    
    try:
        await tester.setup()
        await tester.run_all_tests()
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    asyncio.run(main())