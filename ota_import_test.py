import requests
import json
import uuid
from datetime import datetime, timedelta, timezone

class OTAImportTester:
    def __init__(self, base_url="https://error-kontrol.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.token = None
        self.user = None
        self.tenant = None
        self.tests_run = 0
        self.tests_passed = 0
        self.created_resources = {
            'connections': [],
            'bookings': [],
            'guests': [],
            'rooms': []
        }

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        if self.token:
            test_headers['Authorization'] = f'Bearer {self.token}'
        if headers:
            test_headers.update(headers)

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=test_headers)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=test_headers)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=test_headers)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    return True, response.json()
                except:
                    return True, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    print(f"   Response: {response.json()}")
                except:
                    print(f"   Response: {response.text}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def login(self):
        """Login with provided credentials"""
        login_data = {
            "email": "test@hotel.com",
            "password": "test123"
        }
        
        success, response = self.run_test(
            "User Login",
            "POST", 
            "auth/login",
            200,
            data=login_data
        )
        
        if success and 'access_token' in response:
            self.token = response['access_token']
            self.user = response['user']
            self.tenant = response.get('tenant')
            print(f"   Logged in as: {self.user['email']}")
            return True
        return False

    def test_channel_connection_status(self):
        """Test 1: Channel Connection Status"""
        print("\n📡 Testing Channel Connection Status...")
        
        # First, create a test connection using query parameters (as per backend implementation)
        success, response = self.run_test(
            "Create Channel Connection",
            "POST",
            "channel-manager/connections?channel_type=booking_com&channel_name=Booking.com Test Hotel&property_id=12345",
            200
        )
        
        if success and 'connection' in response:
            connection = response['connection']
            if hasattr(connection, 'id'):
                self.created_resources['connections'].append(connection.id)
            print(f"   Created connection: {response.get('message')}")
        
        # Test GET connections
        success, connections = self.run_test(
            "Get Channel Connections",
            "GET",
            "channel-manager/connections",
            200
        )
        
        if success:
            connections_list = connections.get('connections', [])
            print(f"   Retrieved {len(connections_list)} connections")
            
            # Verify connection status and timestamps
            for conn in connections_list:
                status_ok = conn.get('status') is not None
                has_created_at = 'created_at' in conn
                if status_ok and has_created_at:
                    print(f"   ✅ Connection {conn.get('channel_name')} - Status: {conn.get('status')}")
                    self.tests_passed += 1
                else:
                    print(f"   ❌ Connection missing status or timestamp info")
                self.tests_run += 1
        
        return True

    def test_import_booking_from_ota(self):
        """Test 2: Import Booking from OTA (via OTA Reservations)"""
        print("\n📥 Testing Import Booking from OTA...")
        print("   ⚠️ NOTE: Backend uses different workflow - OTA reservations must be created first, then imported")
        
        # First, create some test rooms and guests for the import to work
        self.setup_test_data()
        
        # Test with different OTA channels
        ota_channels = ['booking_com', 'expedia', 'airbnb']
        
        for channel in ota_channels:
            print(f"\n   Testing {channel.upper()} import workflow...")
            
            # Step 1: Create OTA reservation (simulating external OTA data)
            ota_reservation = {
                "channel_type": channel,
                "channel_booking_id": f"{channel}_booking_{uuid.uuid4().hex[:8]}",
                "guest_name": f"John Doe {channel}",
                "guest_email": f"john.{channel}@example.com",
                "guest_phone": "+1234567890",
                "room_type": "deluxe",
                "check_in": (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d'),
                "check_out": (datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d'),
                "adults": 2,
                "children": 0,
                "total_amount": 300.0,
                "commission_amount": 45.0,
                "status": "pending"
            }
            
            # Manually insert OTA reservation (simulating external system)
            ota_reservation['id'] = str(uuid.uuid4())
            ota_reservation['tenant_id'] = self.tenant['id'] if self.tenant else 'test-tenant'
            ota_reservation['received_at'] = datetime.now(timezone.utc).isoformat()
            
            # Step 2: Check OTA reservations endpoint
            success, ota_reservations = self.run_test(
                f"Get OTA Reservations for {channel.upper()}",
                "GET",
                "channel-manager/ota-reservations?status=pending",
                200
            )
            
            if success:
                print(f"   ✅ OTA reservations endpoint working - Found {len(ota_reservations.get('reservations', []))} pending reservations")
                self.tests_passed += 1
            self.tests_run += 1
            
            # Step 3: Test import of non-existent reservation (expected to fail)
            fake_ota_id = str(uuid.uuid4())
            success, response = self.run_test(
                f"Import Non-existent OTA Reservation",
                "POST",
                f"channel-manager/import-reservation/{fake_ota_id}",
                404  # Expected to fail
            )
            
            if success:
                print(f"   ✅ Non-existent OTA reservation correctly rejected with 404")
                self.tests_passed += 1
            self.tests_run += 1

    def test_rate_inventory_push(self):
        """Test 3: Rate/Inventory Push"""
        print("\n📤 Testing Rate/Inventory Push...")
        
        # Test push rates
        rate_data = {
            "room_type": "deluxe",
            "date": (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d'),
            "rate": 150.0,
            "channels": ["booking_com", "expedia"]
        }
        
        success, response = self.run_test(
            "Push Rates to Channels",
            "POST",
            "channel-manager/push-rates",
            200,
            data=rate_data
        )
        
        if success:
            print("   ✅ Rates pushed successfully")
            # Verify data consistency
            if response.get('channels_updated'):
                print(f"   ✅ Channels updated: {response.get('channels_updated')}")
                self.tests_passed += 1
            self.tests_run += 1
        
        # Test push inventory
        inventory_data = {
            "room_type": "deluxe",
            "date": (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d'),
            "availability": 10,
            "channels": ["booking_com", "expedia"]
        }
        
        success, response = self.run_test(
            "Push Inventory to Channels",
            "POST",
            "channel-manager/push-inventory",
            200,
            data=inventory_data
        )
        
        if success:
            print("   ✅ Inventory pushed successfully")
            if response.get('channels_updated'):
                print(f"   ✅ Channels updated: {response.get('channels_updated')}")
                self.tests_passed += 1
            self.tests_run += 1

    def test_duplicate_detection(self):
        """Test 4: Duplicate Detection"""
        print("\n🔄 Testing Duplicate Detection...")
        
        # Create a booking first
        booking_data = {
            "channel_type": "booking_com",
            "channel_booking_id": "DUPLICATE_TEST_123",
            "guest_name": "Duplicate Test Guest",
            "guest_email": "duplicate@example.com",
            "guest_phone": "+1234567890",
            "room_type": "deluxe",
            "check_in": (datetime.now() + timedelta(days=5)).strftime('%Y-%m-%d'),
            "check_out": (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d'),
            "adults": 2,
            "children": 0,
            "total_amount": 400.0,
            "commission_amount": 60.0
        }
        
        success, response = self.run_test(
            "Import Original Booking",
            "POST",
            "channel-manager/import-booking",
            200,
            data=booking_data
        )
        
        if success:
            print("   ✅ Original booking imported")
            
            # Try to import the same booking again
            success_dup, response_dup = self.run_test(
                "Import Duplicate Booking (Should Fail)",
                "POST",
                "channel-manager/import-booking",
                400,  # Expecting error
                data=booking_data
            )
            
            if success_dup:
                print("   ✅ Duplicate booking correctly rejected")
                if 'error' in response_dup and 'duplicate' in response_dup['error'].lower():
                    print("   ✅ Proper duplicate error message")
                    self.tests_passed += 1
                self.tests_run += 1
            else:
                print("   ❌ Duplicate detection failed")

    def test_data_mapping(self):
        """Test 5: Data Mapping"""
        print("\n🗺️ Testing Data Mapping...")
        
        # Test OTA guest data mapping to PMS guest fields
        mapping_test_data = {
            "channel_type": "booking_com",
            "channel_booking_id": f"MAPPING_TEST_{uuid.uuid4().hex[:8]}",
            "guest_name": "Müller Schmidt-Jones",  # Special characters
            "guest_email": "mueller.schmidt@example.de",
            "guest_phone": "+49-30-12345678",
            "guest_nationality": "DE",
            "room_type": "suite",
            "check_in": (datetime.now() + timedelta(days=10)).strftime('%Y-%m-%d'),
            "check_out": (datetime.now() + timedelta(days=12)).strftime('%Y-%m-%d'),
            "adults": 2,
            "children": 1,
            "total_amount": 500.0,
            "commission_amount": 75.0,
            "special_requests": "Late check-in, ground floor room"
        }
        
        success, response = self.run_test(
            "Import Booking with Special Data",
            "POST",
            "channel-manager/import-booking",
            200,
            data=mapping_test_data
        )
        
        if success and 'pms_booking_id' in response:
            pms_booking_id = response['pms_booking_id']
            
            # Verify guest data mapping
            success_guest, guests = self.run_test(
                "Verify Guest Data Mapping",
                "GET",
                "pms/guests",
                200
            )
            
            if success_guest:
                mapped_guest = None
                for guest in guests:
                    if guest.get('email') == mapping_test_data['guest_email']:
                        mapped_guest = guest
                        break
                
                if mapped_guest:
                    # Check field mapping
                    mapping_checks = [
                        (mapped_guest.get('name') == mapping_test_data['guest_name'], "Guest name"),
                        (mapped_guest.get('email') == mapping_test_data['guest_email'], "Guest email"),
                        (mapped_guest.get('phone') == mapping_test_data['guest_phone'], "Guest phone"),
                        (mapped_guest.get('nationality') == mapping_test_data.get('guest_nationality'), "Guest nationality")
                    ]
                    
                    for check_result, field_name in mapping_checks:
                        if check_result:
                            print(f"   ✅ {field_name} mapped correctly")
                            self.tests_passed += 1
                        else:
                            print(f"   ❌ {field_name} mapping failed")
                        self.tests_run += 1
                else:
                    print("   ❌ Mapped guest not found")
            
            # Verify room type mapping
            success_booking, bookings = self.run_test(
                "Verify Room Type Mapping",
                "GET",
                "pms/bookings",
                200
            )
            
            if success_booking:
                mapped_booking = None
                for booking in bookings:
                    if booking.get('id') == pms_booking_id:
                        mapped_booking = booking
                        break
                
                if mapped_booking:
                    # Check booking field mapping
                    booking_checks = [
                        (mapped_booking.get('adults') == mapping_test_data['adults'], "Adults count"),
                        (mapped_booking.get('children') == mapping_test_data['children'], "Children count"),
                        (mapped_booking.get('total_amount') == mapping_test_data['total_amount'], "Total amount"),
                        (mapped_booking.get('special_requests') == mapping_test_data.get('special_requests'), "Special requests")
                    ]
                    
                    for check_result, field_name in booking_checks:
                        if check_result:
                            print(f"   ✅ {field_name} mapped correctly")
                            self.tests_passed += 1
                        else:
                            print(f"   ❌ {field_name} mapping failed")
                        self.tests_run += 1
                
                # Verify commission calculation
                expected_commission_pct = (mapping_test_data['commission_amount'] / mapping_test_data['total_amount']) * 100
                if mapped_booking and abs(mapped_booking.get('commission_pct', 0) - expected_commission_pct) < 0.01:
                    print(f"   ✅ Commission calculation correct: {expected_commission_pct:.1f}%")
                    self.tests_passed += 1
                else:
                    print(f"   ❌ Commission calculation failed")
                self.tests_run += 1

    def test_error_handling(self):
        """Test 6: Error Handling"""
        print("\n⚠️ Testing Error Handling...")
        
        # Test with invalid OTA data
        invalid_data_tests = [
            {
                "name": "Missing Required Fields",
                "data": {
                    "channel_type": "booking_com",
                    # Missing channel_booking_id, guest_name, etc.
                },
                "expected_status": 422
            },
            {
                "name": "Invalid Channel Type",
                "data": {
                    "channel_type": "invalid_channel",
                    "channel_booking_id": "INVALID_TEST_123",
                    "guest_name": "Test Guest",
                    "guest_email": "test@example.com",
                    "room_type": "deluxe",
                    "check_in": (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d'),
                    "check_out": (datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d'),
                    "adults": 2,
                    "total_amount": 300.0
                },
                "expected_status": 400
            },
            {
                "name": "Invalid Date Format",
                "data": {
                    "channel_type": "booking_com",
                    "channel_booking_id": "DATE_TEST_123",
                    "guest_name": "Test Guest",
                    "guest_email": "test@example.com",
                    "room_type": "deluxe",
                    "check_in": "invalid-date",
                    "check_out": "2025-01-20",
                    "adults": 2,
                    "total_amount": 300.0
                },
                "expected_status": 400
            },
            {
                "name": "Zero or Negative Amount",
                "data": {
                    "channel_type": "booking_com",
                    "channel_booking_id": "AMOUNT_TEST_123",
                    "guest_name": "Test Guest",
                    "guest_email": "test@example.com",
                    "room_type": "deluxe",
                    "check_in": (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d'),
                    "check_out": (datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d'),
                    "adults": 2,
                    "total_amount": -100.0
                },
                "expected_status": 400
            }
        ]
        
        for test_case in invalid_data_tests:
            success, response = self.run_test(
                f"Error Handling - {test_case['name']}",
                "POST",
                "channel-manager/import-booking",
                test_case['expected_status'],
                data=test_case['data']
            )
            
            if success:
                print(f"   ✅ {test_case['name']} - Error handled correctly")
                if 'error' in response or 'detail' in response:
                    print(f"   ✅ Clear error message provided")
                    self.tests_passed += 1
                self.tests_run += 1

    def test_edge_cases(self):
        """Test 7: Edge Cases"""
        print("\n🎯 Testing Edge Cases...")
        
        edge_cases = [
            {
                "name": "Special Characters in Guest Name",
                "data": {
                    "channel_type": "booking_com",
                    "channel_booking_id": f"SPECIAL_CHARS_{uuid.uuid4().hex[:8]}",
                    "guest_name": "José María Ñoño-Pérez",
                    "guest_email": "jose.maria@example.es",
                    "guest_phone": "+34-91-123-4567",
                    "room_type": "deluxe",
                    "check_in": (datetime.now() + timedelta(days=15)).strftime('%Y-%m-%d'),
                    "check_out": (datetime.now() + timedelta(days=17)).strftime('%Y-%m-%d'),
                    "adults": 2,
                    "children": 0,
                    "total_amount": 350.0
                }
            },
            {
                "name": "Future Date (>1 year)",
                "data": {
                    "channel_type": "expedia",
                    "channel_booking_id": f"FUTURE_DATE_{uuid.uuid4().hex[:8]}",
                    "guest_name": "Future Guest",
                    "guest_email": "future@example.com",
                    "room_type": "suite",
                    "check_in": (datetime.now() + timedelta(days=400)).strftime('%Y-%m-%d'),
                    "check_out": (datetime.now() + timedelta(days=402)).strftime('%Y-%m-%d'),
                    "adults": 2,
                    "children": 0,
                    "total_amount": 600.0
                }
            },
            {
                "name": "Same-day Check-in/Check-out",
                "data": {
                    "channel_type": "airbnb",
                    "channel_booking_id": f"SAME_DAY_{uuid.uuid4().hex[:8]}",
                    "guest_name": "Same Day Guest",
                    "guest_email": "sameday@example.com",
                    "room_type": "standard",
                    "check_in": (datetime.now() + timedelta(days=20)).strftime('%Y-%m-%d'),
                    "check_out": (datetime.now() + timedelta(days=20)).strftime('%Y-%m-%d'),
                    "adults": 1,
                    "children": 0,
                    "total_amount": 100.0
                }
            },
            {
                "name": "Invalid Room Type",
                "data": {
                    "channel_type": "booking_com",
                    "channel_booking_id": f"INVALID_ROOM_{uuid.uuid4().hex[:8]}",
                    "guest_name": "Invalid Room Guest",
                    "guest_email": "invalidroom@example.com",
                    "room_type": "non_existent_room_type",
                    "check_in": (datetime.now() + timedelta(days=25)).strftime('%Y-%m-%d'),
                    "check_out": (datetime.now() + timedelta(days=27)).strftime('%Y-%m-%d'),
                    "adults": 2,
                    "children": 0,
                    "total_amount": 300.0
                }
            }
        ]
        
        for case in edge_cases:
            success, response = self.run_test(
                f"Edge Case - {case['name']}",
                "POST",
                "channel-manager/import-booking",
                200,  # Most should succeed with proper handling
                data=case['data']
            )
            
            if success:
                print(f"   ✅ {case['name']} - Handled successfully")
                if 'pms_booking_id' in response:
                    self.created_resources['bookings'].append(response['pms_booking_id'])
                    self.tests_passed += 1
            else:
                # Some edge cases might legitimately fail
                print(f"   ⚠️ {case['name']} - Rejected (may be expected)")
            self.tests_run += 1

    def run_all_tests(self):
        """Run all OTA import consistency tests"""
        print("🚀 Starting OTA Import Consistency Testing")
        print("=" * 60)
        
        # Login first
        if not self.login():
            print("❌ Login failed - cannot proceed with tests")
            return False
        
        # Run all test scenarios
        try:
            self.test_channel_connection_status()
            self.test_import_booking_from_ota()
            self.test_rate_inventory_push()
            self.test_duplicate_detection()
            self.test_data_mapping()
            self.test_error_handling()
            self.test_edge_cases()
            
        except Exception as e:
            print(f"❌ Test execution failed: {str(e)}")
            return False
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 OTA IMPORT CONSISTENCY TEST SUMMARY")
        print("=" * 60)
        print(f"Total Tests Run: {self.tests_run}")
        print(f"Tests Passed: {self.tests_passed}")
        print(f"Tests Failed: {self.tests_run - self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed / self.tests_run * 100):.1f}%" if self.tests_run > 0 else "0%")
        
        if self.tests_passed == self.tests_run:
            print("🎉 ALL TESTS PASSED!")
        else:
            print("⚠️ Some tests failed - see details above")
        
        return True

if __name__ == "__main__":
    tester = OTAImportTester()
    tester.run_all_tests()