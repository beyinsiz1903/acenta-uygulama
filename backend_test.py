#!/usr/bin/env python3
"""
PMS BOOKINGS BACKEND FLOW TESTING
Test PMS Bookings backend akışını test et - BookingsTab/VirtualizedBookingList veri yapısı doğrulaması

OBJECTIVE: /api/pms/bookings ve BookingsTab/VirtualizedBookingList'in dayandığı veri yapısının stabil olduğunu,
hata vermediğini ve performans hedeflerini karşıladığını doğrulamak.

TARGET ENDPOINTS:
1. GET /api/pms/bookings (default parametrelerle)
2. GET /api/pms/bookings?limit=100
3. GET /api/pms/bookings?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD (7 günlük periyot)
4. GET /api/folio/booking/{booking_id} (varsa)
5. GET /api/payments/booking/{booking_id} (varsa)

EXPECTED RESULTS:
- Tüm çağrılar HTTP 200 dönmeli, 500/ValidationError olmamalı
- Booking nesnelerinde gerekli alanlar: id, guest_id, room_id, status, total_amount, check_in, check_out
- Mümkünse guest_name ve room_number (veya UI'nin bunları başka yerden çekebileceği net olsun)
- Response süreleri kabaca raporlanacak (ortalama ms seviyesinde)
"""

import asyncio
import aiohttp
import json
import sys
import os
from datetime import datetime, timezone, timedelta, date
from typing import Dict, List, Any, Optional
import uuid

# Configuration
BACKEND_URL = "https://tab-checker.preview.emergentagent.com/api"
TEST_EMAIL = "demo@hotel.com"
TEST_PASSWORD = "demo123"

class PMSBookingsTester:
    def __init__(self):
        self.session = None
        self.auth_token = None
        self.tenant_id = None
        self.user_id = None
        self.test_results = []
        self.created_test_data = {
            'guests': [],
            'bookings': [],
            'rooms': [],
            'folios': []
        }

    async def setup_session(self):
        """Initialize HTTP session"""
        self.session = aiohttp.ClientSession()

    async def cleanup_session(self):
        """Cleanup HTTP session"""
        if self.session:
            await self.session.close()

    async def authenticate(self):
        """Authenticate and get token"""
        try:
            login_data = {
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD
            }
            
            async with self.session.post(f"{BACKEND_URL}/auth/login", json=login_data) as response:
                if response.status == 200:
                    data = await response.json()
                    self.auth_token = data["access_token"]
                    self.tenant_id = data["user"]["tenant_id"]
                    self.user_id = data["user"]["id"]
                    print(f"✅ Authentication successful - User: {data['user']['name']}, Tenant: {self.tenant_id}")
                    return True
                else:
                    print(f"❌ Authentication failed: {response.status}")
                    return False
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            return False

    def get_headers(self):
        """Get authorization headers"""
        return {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json"
        }

    async def create_test_data(self):
        """Create test data for PMS Bookings testing"""
        print("\n🔧 Creating test data for PMS Bookings testing...")
        
        try:
            # Create test guest for bookings
            guest_data = {
                "name": "Mehmet Özkan",
                "email": "mehmet.ozkan@example.com",
                "phone": "+90-555-987-6543",
                "id_number": "98765432109",
                "nationality": "TR",
                "vip_status": False
            }
            
            async with self.session.post(f"{BACKEND_URL}/pms/guests", 
                                       json=guest_data, 
                                       headers=self.get_headers()) as response:
                if response.status == 200:
                    guest = await response.json()
                    guest_id = guest["id"]
                    self.created_test_data['guests'].append(guest_id)
                    print(f"✅ Test guest created: {guest_id}")
                else:
                    print(f"⚠️ Guest creation failed: {response.status}")
                    return False

            # Get available room for booking
            async with self.session.get(f"{BACKEND_URL}/pms/rooms", 
                                      headers=self.get_headers()) as response:
                if response.status == 200:
                    rooms = await response.json()
                    if rooms:
                        room_id = rooms[0]["id"]
                        self.created_test_data['rooms'].append(room_id)
                        print(f"✅ Using room: {room_id}")
                    else:
                        print("⚠️ No rooms available")
                        return False
                else:
                    print(f"⚠️ Failed to get rooms: {response.status}")
                    return False

            # Create multiple test bookings for comprehensive testing
            booking_dates = [
                # Past booking
                {
                    "check_in": (datetime.now(timezone.utc) - timedelta(days=5)).isoformat(),
                    "check_out": (datetime.now(timezone.utc) - timedelta(days=3)).isoformat(),
                    "status": "checked_out"
                },
                # Current booking
                {
                    "check_in": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
                    "check_out": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
                    "status": "checked_in"
                },
                # Future booking
                {
                    "check_in": (datetime.now(timezone.utc) + timedelta(days=3)).isoformat(),
                    "check_out": (datetime.now(timezone.utc) + timedelta(days=5)).isoformat(),
                    "status": "confirmed"
                }
            ]
            
            for i, booking_info in enumerate(booking_dates):
                booking_data = {
                    "guest_id": guest_id,
                    "room_id": room_id,
                    "check_in": booking_info["check_in"],
                    "check_out": booking_info["check_out"],
                    "adults": 2,
                    "children": 0,
                    "children_ages": [],
                    "guests_count": 2,
                    "total_amount": 250.0 + (i * 50),  # Different amounts
                    "special_requests": f"Test booking {i+1} - BookingsTab test"
                }
                
                async with self.session.post(f"{BACKEND_URL}/pms/bookings", 
                                           json=booking_data, 
                                           headers=self.get_headers()) as response:
                    if response.status == 200:
                        booking = await response.json()
                        booking_id = booking["id"]
                        self.created_test_data['bookings'].append(booking_id)
                        print(f"✅ Test booking {i+1} created: {booking_id}")
                    else:
                        print(f"⚠️ Booking {i+1} creation failed: {response.status}")

            print(f"✅ Test data creation completed - {len(self.created_test_data['bookings'])} bookings created")
            return True
            
        except Exception as e:
            print(f"❌ Error creating test data: {e}")
            return False

    # ============= PMS BOOKINGS BACKEND TESTS =============

    async def test_pms_bookings_default_endpoint(self):
        """Test GET /api/pms/bookings (default parametrelerle)"""
        print("\n📅 Testing PMS Bookings Endpoint (Default Parameters)...")
        print("🎯 OBJECTIVE: BookingsTab/VirtualizedBookingList veri yapısı doğrulaması")
        
        test_cases = [
            {
                "name": "Get all bookings - default parameters",
                "params": {},
                "expected_status": 200,
                "required_fields": ["id", "guest_id", "room_id", "status", "total_amount", "check_in", "check_out"],
                "optional_fields": ["guest_name", "room_number"],
                "expected_response_type": "list"
            }
        ]
        
        passed = 0
        total = len(test_cases)
        response_times = []
        
        for test_case in test_cases:
            try:
                url = f"{BACKEND_URL}/pms/bookings"
                if test_case["params"]:
                    params = "&".join([f"{k}={v}" for k, v in test_case["params"].items()])
                    url += f"?{params}"
                
                start_time = datetime.now()
                async with self.session.get(url, headers=self.get_headers()) as response:
                    end_time = datetime.now()
                    response_time = (end_time - start_time).total_seconds() * 1000
                    response_times.append(response_time)
                    
                    if response.status == test_case["expected_status"]:
                        data = await response.json()
                        
                        # Verify response is a list
                        if isinstance(data, list):
                            if data:  # If bookings exist, check structure
                                booking = data[0]
                                missing_fields = [field for field in test_case["required_fields"] if field not in booking]
                                optional_present = [field for field in test_case["optional_fields"] if field in booking]
                                
                                if not missing_fields:
                                    print(f"  ✅ {test_case['name']}: PASSED ({response_time:.1f}ms)")
                                    print(f"      📊 Sample booking: ID={booking.get('id', 'N/A')[:8]}...")
                                    print(f"      📊 Status: {booking.get('status', 'N/A')}, Amount: {booking.get('total_amount', 'N/A')}")
                                    print(f"      📊 Required fields: ✅ All present")
                                    print(f"      📊 Optional fields present: {optional_present}")
                                    print(f"      📊 Total bookings returned: {len(data)}")
                                    passed += 1
                                else:
                                    print(f"  ❌ {test_case['name']}: Missing required fields {missing_fields}")
                            else:
                                print(f"  ✅ {test_case['name']}: PASSED - No bookings found ({response_time:.1f}ms)")
                                passed += 1
                        else:
                            print(f"  ❌ {test_case['name']}: Expected list response, got {type(data)}")
                    else:
                        error_text = await response.text()
                        print(f"  ❌ {test_case['name']}: Expected {test_case['expected_status']}, got {response.status}")
                        if response.status == 500:
                            print(f"      🔍 500 Error Details: {error_text[:300]}...")
                        
            except Exception as e:
                print(f"  ❌ {test_case['name']}: Error {e}")
        
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        print(f"      ⏱️ Average Response Time: {avg_response_time:.1f}ms")
        
        self.test_results.append({
            "endpoint": "GET /api/pms/bookings (default)",
            "passed": passed, "total": total, "success_rate": f"{passed/total*100:.1f}%",
            "avg_response_time": f"{avg_response_time:.1f}ms"
        })

    async def test_pms_bookings_with_limit(self):
        """Test GET /api/pms/bookings?limit=100"""
        print("\n📊 Testing PMS Bookings Endpoint with Limit Parameter...")
        
        test_cases = [
            {
                "name": "Get bookings with limit=100",
                "params": {"limit": 100},
                "expected_status": 200,
                "required_fields": ["id", "guest_id", "room_id", "status", "total_amount", "check_in", "check_out"],
                "optional_fields": ["guest_name", "room_number"]
            },
            {
                "name": "Get bookings with limit=50",
                "params": {"limit": 50},
                "expected_status": 200,
                "required_fields": ["id", "guest_id", "room_id", "status", "total_amount", "check_in", "check_out"],
                "optional_fields": ["guest_name", "room_number"]
            }
        ]
        
        passed = 0
        total = len(test_cases)
        response_times = []
        
        for test_case in test_cases:
            try:
                url = f"{BACKEND_URL}/pms/bookings"
                if test_case["params"]:
                    params = "&".join([f"{k}={v}" for k, v in test_case["params"].items()])
                    url += f"?{params}"
                
                start_time = datetime.now()
                async with self.session.get(url, headers=self.get_headers()) as response:
                    end_time = datetime.now()
                    response_time = (end_time - start_time).total_seconds() * 1000
                    response_times.append(response_time)
                    
                    if response.status == test_case["expected_status"]:
                        data = await response.json()
                        
                        if isinstance(data, list):
                            limit = test_case["params"]["limit"]
                            actual_count = len(data)
                            
                            if data:  # If bookings exist, check structure
                                booking = data[0]
                                missing_fields = [field for field in test_case["required_fields"] if field not in booking]
                                optional_present = [field for field in test_case["optional_fields"] if field in booking]
                                
                                if not missing_fields:
                                    print(f"  ✅ {test_case['name']}: PASSED ({response_time:.1f}ms)")
                                    print(f"      📊 Requested limit: {limit}, Returned: {actual_count}")
                                    print(f"      📊 Pagination working: {'✅' if actual_count <= limit else '❌'}")
                                    print(f"      📊 Optional fields present: {optional_present}")
                                    passed += 1
                                else:
                                    print(f"  ❌ {test_case['name']}: Missing required fields {missing_fields}")
                            else:
                                print(f"  ✅ {test_case['name']}: PASSED - No bookings found ({response_time:.1f}ms)")
                                passed += 1
                        else:
                            print(f"  ❌ {test_case['name']}: Expected list response, got {type(data)}")
                    else:
                        error_text = await response.text()
                        print(f"  ❌ {test_case['name']}: Expected {test_case['expected_status']}, got {response.status}")
                        if response.status == 500:
                            print(f"      🔍 500 Error Details: {error_text[:300]}...")
                        
            except Exception as e:
                print(f"  ❌ {test_case['name']}: Error {e}")
        
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        print(f"      ⏱️ Average Response Time: {avg_response_time:.1f}ms")
        
        self.test_results.append({
            "endpoint": "GET /api/pms/bookings?limit=X",
            "passed": passed, "total": total, "success_rate": f"{passed/total*100:.1f}%",
            "avg_response_time": f"{avg_response_time:.1f}ms"
        })

    async def test_pms_bookings_with_date_range(self):
        """Test GET /api/pms/bookings?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD (7 günlük periyot)"""
        print("\n📅 Testing PMS Bookings Endpoint with Date Range (7-day period)...")
        
        # Calculate 7-day period
        today = datetime.now(timezone.utc).date()
        start_date = today - timedelta(days=3)  # 3 days ago
        end_date = today + timedelta(days=4)    # 4 days from now (total 7 days)
        
        test_cases = [
            {
                "name": "Get bookings for 7-day period",
                "params": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat()
                },
                "expected_status": 200,
                "required_fields": ["id", "guest_id", "room_id", "status", "total_amount", "check_in", "check_out"],
                "optional_fields": ["guest_name", "room_number"]
            },
            {
                "name": "Get bookings for 7-day period with limit",
                "params": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "limit": 100
                },
                "expected_status": 200,
                "required_fields": ["id", "guest_id", "room_id", "status", "total_amount", "check_in", "check_out"],
                "optional_fields": ["guest_name", "room_number"]
            }
        ]
        
        passed = 0
        total = len(test_cases)
        response_times = []
        
        for test_case in test_cases:
            try:
                url = f"{BACKEND_URL}/pms/bookings"
                if test_case["params"]:
                    params = "&".join([f"{k}={v}" for k, v in test_case["params"].items()])
                    url += f"?{params}"
                
                start_time = datetime.now()
                async with self.session.get(url, headers=self.get_headers()) as response:
                    end_time = datetime.now()
                    response_time = (end_time - start_time).total_seconds() * 1000
                    response_times.append(response_time)
                    
                    if response.status == test_case["expected_status"]:
                        data = await response.json()
                        
                        if isinstance(data, list):
                            if data:  # If bookings exist, check structure
                                booking = data[0]
                                missing_fields = [field for field in test_case["required_fields"] if field not in booking]
                                optional_present = [field for field in test_case["optional_fields"] if field in booking]
                                
                                if not missing_fields:
                                    print(f"  ✅ {test_case['name']}: PASSED ({response_time:.1f}ms)")
                                    print(f"      📊 Date range: {start_date} to {end_date} (7 days)")
                                    print(f"      📊 Bookings found: {len(data)}")
                                    print(f"      📊 Sample booking dates: {booking.get('check_in', 'N/A')[:10]} - {booking.get('check_out', 'N/A')[:10]}")
                                    print(f"      📊 Optional fields present: {optional_present}")
                                    passed += 1
                                else:
                                    print(f"  ❌ {test_case['name']}: Missing required fields {missing_fields}")
                            else:
                                print(f"  ✅ {test_case['name']}: PASSED - No bookings in date range ({response_time:.1f}ms)")
                                print(f"      📊 Date range: {start_date} to {end_date} (7 days)")
                                passed += 1
                        else:
                            print(f"  ❌ {test_case['name']}: Expected list response, got {type(data)}")
                    else:
                        error_text = await response.text()
                        print(f"  ❌ {test_case['name']}: Expected {test_case['expected_status']}, got {response.status}")
                        if response.status == 500:
                            print(f"      🔍 500 Error Details: {error_text[:300]}...")
                        
            except Exception as e:
                print(f"  ❌ {test_case['name']}: Error {e}")
        
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        print(f"      ⏱️ Average Response Time: {avg_response_time:.1f}ms")
        
        self.test_results.append({
            "endpoint": "GET /api/pms/bookings?start_date&end_date",
            "passed": passed, "total": total, "success_rate": f"{passed/total*100:.1f}%",
            "avg_response_time": f"{avg_response_time:.1f}ms"
        })

    async def test_pms_guests_endpoint(self):
        """Test GET /api/pms/guests - Guest list"""
        print("\n👥 Testing PMS Guests Endpoint...")
        
        test_cases = [
            {
                "name": "Get all guests - verify structure",
                "params": {},
                "expected_status": 200,
                "required_fields": ["id", "name", "email", "phone"]
            },
            {
                "name": "Get guests with pagination",
                "params": {"limit": 50},
                "expected_status": 200,
                "required_fields": ["id", "name", "email", "phone"]
            }
        ]
        
        passed = 0
        total = len(test_cases)
        
        for test_case in test_cases:
            try:
                url = f"{BACKEND_URL}/pms/guests"
                if test_case["params"]:
                    params = "&".join([f"{k}={v}" for k, v in test_case["params"].items()])
                    url += f"?{params}"
                
                start_time = datetime.now()
                async with self.session.get(url, headers=self.get_headers()) as response:
                    end_time = datetime.now()
                    response_time = (end_time - start_time).total_seconds() * 1000
                    
                    if response.status == test_case["expected_status"]:
                        data = await response.json()
                        
                        if isinstance(data, list):
                            if data:  # If guests exist, check structure
                                guest = data[0]
                                missing_fields = [field for field in test_case["required_fields"] if field not in guest]
                                if not missing_fields:
                                    print(f"  ✅ {test_case['name']}: PASSED ({response_time:.1f}ms)")
                                    print(f"      📊 Sample guest: {guest.get('name', 'N/A')} - {guest.get('email', 'N/A')}")
                                    passed += 1
                                else:
                                    print(f"  ❌ {test_case['name']}: Missing required fields {missing_fields}")
                            else:
                                print(f"  ✅ {test_case['name']}: PASSED - No guests found ({response_time:.1f}ms)")
                                passed += 1
                        else:
                            print(f"  ❌ {test_case['name']}: Expected list response, got {type(data)}")
                    else:
                        error_text = await response.text()
                        print(f"  ❌ {test_case['name']}: Expected {test_case['expected_status']}, got {response.status}")
                        if response.status == 500:
                            print(f"      🔍 500 Error Details: {error_text[:300]}...")
                        
            except Exception as e:
                print(f"  ❌ {test_case['name']}: Error {e}")
        
        self.test_results.append({
            "endpoint": "GET /api/pms/guests",
            "passed": passed, "total": total, "success_rate": f"{passed/total*100:.1f}%"
        })

    async def test_room_status_update_endpoint(self):
        """Test PATCH /api/pms/rooms/{room_id} - Room status update (bulk update function)"""
        print("\n🔄 Testing Room Status Update Endpoint (Bulk Update Function)...")
        
        # Get a room ID for testing
        room_id = None
        if self.created_test_data['rooms']:
            room_id = self.created_test_data['rooms'][0]
        else:
            # Try to get a room from the rooms endpoint
            try:
                async with self.session.get(f"{BACKEND_URL}/pms/rooms", headers=self.get_headers()) as response:
                    if response.status == 200:
                        rooms = await response.json()
                        if rooms:
                            room_id = rooms[0]["id"]
            except:
                pass
        
        if not room_id:
            print("  ⚠️ No room available for testing status update")
            self.test_results.append({
                "endpoint": "PATCH /api/pms/rooms/{room_id}",
                "passed": 0, "total": 1, "success_rate": "0.0%"
            })
            return
        
        test_cases = [
            {
                "name": "Update room status to cleaning",
                "room_id": room_id,
                "data": {"status": "cleaning"},
                "expected_status": 200
            },
            {
                "name": "Update room status to available",
                "room_id": room_id,
                "data": {"status": "available"},
                "expected_status": 200
            },
            {
                "name": "Update room status to maintenance",
                "room_id": room_id,
                "data": {"status": "maintenance", "notes": "Scheduled maintenance"},
                "expected_status": 200
            }
        ]
        
        passed = 0
        total = len(test_cases)
        
        for test_case in test_cases:
            try:
                url = f"{BACKEND_URL}/pms/rooms/{test_case['room_id']}"
                
                start_time = datetime.now()
                async with self.session.put(url, json=test_case["data"], headers=self.get_headers()) as response:
                    end_time = datetime.now()
                    response_time = (end_time - start_time).total_seconds() * 1000
                    
                    if response.status == test_case["expected_status"]:
                        data = await response.json()
                        print(f"  ✅ {test_case['name']}: PASSED ({response_time:.1f}ms)")
                        if "status" in data:
                            print(f"      📊 Room status updated to: {data.get('status', 'N/A')}")
                        passed += 1
                    else:
                        error_text = await response.text()
                        print(f"  ❌ {test_case['name']}: Expected {test_case['expected_status']}, got {response.status}")
                        if response.status == 500:
                            print(f"      🔍 500 Error Details: {error_text[:300]}...")
                        
            except Exception as e:
                print(f"  ❌ {test_case['name']}: Error {e}")
        
        self.test_results.append({
            "endpoint": "PUT /api/pms/rooms/{room_id}",
            "passed": passed, "total": total, "success_rate": f"{passed/total*100:.1f}%"
        })

    async def test_quick_checkout_endpoint(self):
        """Test POST /api/frontdesk/checkout/{booking_id} - Quick checkout button"""
        print("\n🚪 Testing Quick Checkout Endpoint...")
        
        # Get a booking ID for testing
        booking_id = None
        if self.created_test_data['bookings']:
            booking_id = self.created_test_data['bookings'][0]
        else:
            # Try to get a booking from the bookings endpoint
            try:
                async with self.session.get(f"{BACKEND_URL}/pms/bookings", headers=self.get_headers()) as response:
                    if response.status == 200:
                        bookings = await response.json()
                        if bookings:
                            booking_id = bookings[0]["id"]
            except:
                pass
        
        if not booking_id:
            print("  ⚠️ No booking available for testing checkout")
            self.test_results.append({
                "endpoint": "POST /api/frontdesk/checkout/{booking_id}",
                "passed": 0, "total": 1, "success_rate": "0.0%"
            })
            return
        
        test_cases = [
            {
                "name": "Quick checkout with payment",
                "booking_id": booking_id,
                "data": {
                    "payment_method": "card",
                    "payment_amount": 300.0,
                    "notes": "Quick checkout from Rooms TAB"
                },
                "expected_status": [200, 400, 404]  # 200 if successful, 400 if already checked out, 404 if not found
            }
        ]
        
        passed = 0
        total = len(test_cases)
        
        for test_case in test_cases:
            try:
                url = f"{BACKEND_URL}/frontdesk/checkout/{test_case['booking_id']}"
                
                start_time = datetime.now()
                async with self.session.post(url, json=test_case["data"], headers=self.get_headers()) as response:
                    end_time = datetime.now()
                    response_time = (end_time - start_time).total_seconds() * 1000
                    
                    if response.status in test_case["expected_status"]:
                        if response.status == 200:
                            data = await response.json()
                            print(f"  ✅ {test_case['name']}: PASSED - Checkout successful ({response_time:.1f}ms)")
                        else:
                            print(f"  ✅ {test_case['name']}: PASSED - Expected status {response.status} ({response_time:.1f}ms)")
                        passed += 1
                    else:
                        error_text = await response.text()
                        print(f"  ❌ {test_case['name']}: Expected {test_case['expected_status']}, got {response.status}")
                        if response.status == 500:
                            print(f"      🔍 500 Error Details: {error_text[:300]}...")
                        
            except Exception as e:
                print(f"  ❌ {test_case['name']}: Error {e}")
        
        self.test_results.append({
            "endpoint": "POST /api/frontdesk/checkout/{booking_id}",
            "passed": passed, "total": total, "success_rate": f"{passed/total*100:.1f}%"
        })

    async def test_quick_folio_endpoint(self):
        """Test GET /api/folio/booking/{booking_id} - Quick folio button"""
        print("\n📄 Testing Quick Folio Endpoint...")
        
        # Get a booking ID for testing
        booking_id = None
        if self.created_test_data['bookings']:
            booking_id = self.created_test_data['bookings'][0]
        else:
            # Try to get a booking from the bookings endpoint
            try:
                async with self.session.get(f"{BACKEND_URL}/pms/bookings", headers=self.get_headers()) as response:
                    if response.status == 200:
                        bookings = await response.json()
                        if bookings:
                            booking_id = bookings[0]["id"]
            except:
                pass
        
        if not booking_id:
            print("  ⚠️ No booking available for testing folio")
            self.test_results.append({
                "endpoint": "GET /api/folio/booking/{booking_id}",
                "passed": 0, "total": 1, "success_rate": "0.0%"
            })
            return
        
        test_cases = [
            {
                "name": "Get folio for booking",
                "booking_id": booking_id,
                "expected_status": [200, 404],  # 200 if folio exists, 404 if not found
                "expected_fields": ["id", "booking_id", "folio_number", "balance"]
            }
        ]
        
        passed = 0
        total = len(test_cases)
        
        for test_case in test_cases:
            try:
                url = f"{BACKEND_URL}/folio/booking/{test_case['booking_id']}"
                
                start_time = datetime.now()
                async with self.session.get(url, headers=self.get_headers()) as response:
                    end_time = datetime.now()
                    response_time = (end_time - start_time).total_seconds() * 1000
                    
                    if response.status in test_case["expected_status"]:
                        if response.status == 200:
                            data = await response.json()
                            # Handle both single folio and list of folios
                            if isinstance(data, list) and data:
                                folio = data[0]  # Take first folio
                                missing_fields = [field for field in test_case["expected_fields"] if field not in folio]
                                if not missing_fields:
                                    print(f"  ✅ {test_case['name']}: PASSED - Folio found ({response_time:.1f}ms)")
                                    print(f"      📊 Folio: {folio.get('folio_number', 'N/A')} - Balance: {folio.get('balance', 'N/A')}")
                                    passed += 1
                                else:
                                    print(f"  ❌ {test_case['name']}: Missing required fields {missing_fields}")
                            elif isinstance(data, dict):
                                missing_fields = [field for field in test_case["expected_fields"] if field not in data]
                                if not missing_fields:
                                    print(f"  ✅ {test_case['name']}: PASSED - Folio found ({response_time:.1f}ms)")
                                    print(f"      📊 Folio: {data.get('folio_number', 'N/A')} - Balance: {data.get('balance', 'N/A')}")
                                    passed += 1
                                else:
                                    print(f"  ❌ {test_case['name']}: Missing required fields {missing_fields}")
                            else:
                                print(f"  ✅ {test_case['name']}: PASSED - Empty folio list ({response_time:.1f}ms)")
                                passed += 1
                        else:  # 404
                            print(f"  ✅ {test_case['name']}: PASSED - No folio found (expected) ({response_time:.1f}ms)")
                            passed += 1
                    else:
                        error_text = await response.text()
                        print(f"  ❌ {test_case['name']}: Expected {test_case['expected_status']}, got {response.status}")
                        if response.status == 500:
                            print(f"      🔍 500 Error Details: {error_text[:300]}...")
                        
            except Exception as e:
                print(f"  ❌ {test_case['name']}: Error {e}")
        
        self.test_results.append({
            "endpoint": "GET /api/folio/booking/{booking_id}",
            "passed": passed, "total": total, "success_rate": f"{passed/total*100:.1f}%"
        })

    # ============= MAIN TEST EXECUTION =============

    async def run_all_tests(self):
        """Run comprehensive PMS Rooms backend testing"""
        print("🚀 PMS ROOMS BACKEND FLOW TESTING")
        print("Testing 7 ENDPOINTS for Rooms TAB compatibility")
        print("Focus: Verify HTTP 500 / ResponseValidationError (tenant_id) is fixed")
        print("=" * 80)
        
        # Setup
        await self.setup_session()
        
        if not await self.authenticate():
            print("❌ Authentication failed. Cannot proceed with tests.")
            return
        
        # Create test data
        if not await self.create_test_data():
            print("⚠️ Test data creation failed. Some tests may not work properly.")
        
        # Run all PMS Rooms tests
        print("\n" + "="*50)
        print("🏨 PMS ROOMS BACKEND ENDPOINT TESTING")
        print("="*50)
        
        await self.test_pms_rooms_endpoint()
        await self.test_pms_room_blocks_endpoint()
        await self.test_pms_bookings_endpoint()
        await self.test_pms_guests_endpoint()
        await self.test_room_status_update_endpoint()
        await self.test_quick_checkout_endpoint()
        await self.test_quick_folio_endpoint()
        
        # Cleanup
        await self.cleanup_session()
        
        # Print results
        self.print_test_summary()

    def print_test_summary(self):
        """Print comprehensive test summary"""
        print("\n" + "=" * 80)
        print("📊 PMS ROOMS BACKEND FLOW TEST RESULTS")
        print("=" * 80)
        
        total_passed = 0
        total_tests = 0
        
        print("\n🏨 ENDPOINT TEST RESULTS:")
        print("-" * 60)
        
        for result in self.test_results:
            endpoint = result["endpoint"]
            passed = result["passed"]
            total = result["total"]
            success_rate = result["success_rate"]
            
            status = "✅" if passed == total else "❌" if passed == 0 else "⚠️"
            print(f"{status} {endpoint}: {success_rate}")
            
            total_passed += passed
            total_tests += total
        
        print("\n" + "=" * 80)
        overall_success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
        print(f"📈 OVERALL SUCCESS RATE: {total_passed}/{total_tests} ({overall_success_rate:.1f}%)")
        
        if overall_success_rate >= 90:
            print("🎉 EXCELLENT: PMS Rooms backend ready for production!")
        elif overall_success_rate >= 75:
            print("✅ GOOD: Most endpoints working, minor issues remain")
        elif overall_success_rate >= 50:
            print("⚠️ PARTIAL: Some endpoints working, significant issues remain")
        else:
            print("❌ CRITICAL: Major backend issues, needs immediate attention")
        
        print("\n🔍 KEY VERIFICATION POINTS:")
        print("• GET /api/pms/rooms: Required fields for Rooms TAB (id, room_number, room_type, floor, base_price, status)")
        print("• No HTTP 500 / ResponseValidationError with tenant_id missing")
        print("• All supporting endpoints return proper data structures")
        print("• Room status update (bulk function) working")
        print("• Quick checkout and folio buttons functional")
        
        print("\n" + "=" * 80)

async def main():
    """Main test execution"""
    tester = PMSRoomsTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())
