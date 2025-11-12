import requests
import sys
import json
from datetime import datetime, timedelta

class RoomOpsAPITester:
    def __init__(self, base_url="https://tax-plus-helper.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.token = None
        self.user = None
        self.tenant = None
        self.tests_run = 0
        self.tests_passed = 0
        self.created_resources = {
            'rooms': [],
            'guests': [],
            'bookings': [],
            'invoices': [],
            'loyalty_programs': [],
            'orders': []
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

    def test_registration(self):
        """Test tenant registration"""
        timestamp = datetime.now().strftime('%H%M%S')
        registration_data = {
            "property_name": f"Test Hotel {timestamp}",
            "email": f"test{timestamp}@example.com",
            "password": "TestPass123!",
            "name": f"Test Manager {timestamp}",
            "phone": "+1234567890",
            "address": "123 Test Street, Test City"
        }
        
        success, response = self.run_test(
            "Tenant Registration",
            "POST",
            "auth/register",
            200,
            data=registration_data
        )
        
        if success and 'access_token' in response:
            self.token = response['access_token']
            self.user = response['user']
            self.tenant = response['tenant']
            print(f"   Registered tenant: {self.tenant['property_name']}")
            return True
        return False

    def test_login(self):
        """Test user login"""
        if not self.user:
            return False
            
        login_data = {
            "email": self.user['email'],
            "password": "TestPass123!"
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
            return True
        return False

    def test_auth_me(self):
        """Test get current user"""
        success, response = self.run_test(
            "Get Current User",
            "GET",
            "auth/me",
            200
        )
        return success

    def test_pms_module(self):
        """Test PMS (Property Management System) endpoints"""
        print("\n📋 Testing PMS Module...")
        
        # Test create room
        room_data = {
            "tenant_id": "dummy",  # Will be overwritten by backend
            "room_number": "101",
            "room_type": "deluxe",
            "floor": 1,
            "capacity": 2,
            "base_price": 150.00,
            "amenities": ["wifi", "tv", "minibar"]
        }
        
        success, response = self.run_test(
            "Create Room",
            "POST",
            "pms/rooms",
            200,
            data=room_data
        )
        
        if success and 'id' in response:
            self.created_resources['rooms'].append(response['id'])
        
        # Test get rooms
        success, rooms = self.run_test(
            "Get Rooms",
            "GET",
            "pms/rooms",
            200
        )
        
        # Test create guest
        guest_data = {
            "tenant_id": "dummy",  # Will be overwritten by backend
            "name": "John Doe",
            "email": "john.doe@example.com",
            "phone": "+1234567890",
            "id_number": "ID123456789",
            "address": "456 Guest Street"
        }
        
        success, response = self.run_test(
            "Create Guest",
            "POST",
            "pms/guests",
            200,
            data=guest_data
        )
        
        if success and 'id' in response:
            self.created_resources['guests'].append(response['id'])
            guest_id = response['id']
        
        # Test get guests
        success, guests = self.run_test(
            "Get Guests",
            "GET",
            "pms/guests",
            200
        )
        
        # Test create booking (if we have room and guest)
        if self.created_resources['rooms'] and self.created_resources['guests']:
            booking_data = {
                "tenant_id": "dummy",  # Will be overwritten by backend
                "guest_id": self.created_resources['guests'][0],
                "room_id": self.created_resources['rooms'][0],
                "check_in": (datetime.now() + timedelta(days=1)).isoformat(),
                "check_out": (datetime.now() + timedelta(days=3)).isoformat(),
                "guests_count": 2,
                "total_amount": 300.00,
                "channel": "direct"
            }
            
            success, response = self.run_test(
                "Create Booking",
                "POST",
                "pms/bookings",
                200,
                data=booking_data
            )
            
            if success and 'id' in response:
                self.created_resources['bookings'].append(response['id'])
        
        # Test get bookings
        success, bookings = self.run_test(
            "Get Bookings",
            "GET",
            "pms/bookings",
            200
        )
        
        # Test PMS dashboard
        success, dashboard = self.run_test(
            "PMS Dashboard",
            "GET",
            "pms/dashboard",
            200
        )
        
        return True

    def test_invoice_module(self):
        """Test Invoice Service endpoints"""
        print("\n💰 Testing Invoice Module...")
        
        # Test create invoice
        invoice_data = {
            "tenant_id": "dummy",  # Will be overwritten by backend
            "invoice_number": "dummy",  # Will be generated by backend
            "customer_name": "Test Customer",
            "customer_email": "customer@example.com",
            "items": [
                {
                    "description": "Room Charge",
                    "quantity": 2,
                    "unit_price": 150.00,
                    "total": 300.00
                }
            ],
            "subtotal": 300.00,
            "tax": 30.00,
            "total": 330.00,
            "due_date": (datetime.now() + timedelta(days=30)).isoformat()
        }
        
        success, response = self.run_test(
            "Create Invoice",
            "POST",
            "invoices",
            200,
            data=invoice_data
        )
        
        if success and 'id' in response:
            self.created_resources['invoices'].append(response['id'])
            invoice_id = response['id']
        
        # Test get invoices
        success, invoices = self.run_test(
            "Get Invoices",
            "GET",
            "invoices",
            200
        )
        
        # Test update invoice status
        if self.created_resources['invoices']:
            success, response = self.run_test(
                "Update Invoice Status",
                "PUT",
                f"invoices/{self.created_resources['invoices'][0]}",
                200,
                data={"status": "sent"}
            )
        
        # Test invoice stats
        success, stats = self.run_test(
            "Invoice Stats",
            "GET",
            "invoices/stats",
            200
        )
        
        return True

    def test_rms_module(self):
        """Test RMS (Revenue Management System) endpoints"""
        print("\n📈 Testing RMS Module...")
        
        # Test get price suggestions
        success, suggestions = self.run_test(
            "Get Price Suggestions",
            "GET",
            "rms/suggestions",
            200
        )
        
        # Test create price analysis
        analysis_data = {
            "tenant_id": "dummy",  # Will be overwritten by backend
            "room_type": "deluxe",
            "date": datetime.now().isoformat(),
            "current_price": 150.00,
            "suggested_price": 165.00,
            "occupancy_rate": 75.0,
            "demand_score": 0.8,
            "competitor_avg": 160.00
        }
        
        success, response = self.run_test(
            "Create Price Analysis",
            "POST",
            "rms/analysis",
            200,
            data=analysis_data
        )
        
        # Test get price analysis
        success, analysis = self.run_test(
            "Get Price Analysis",
            "GET",
            "rms/analysis",
            200
        )
        
        return True

    def test_loyalty_module(self):
        """Test Loyalty Service endpoints"""
        print("\n🏆 Testing Loyalty Module...")
        
        # Test create loyalty program (need guest first)
        if self.created_resources['guests']:
            program_data = {
                "tenant_id": "dummy",  # Will be overwritten by backend
                "guest_id": self.created_resources['guests'][0],
                "tier": "bronze",
                "points": 100,
                "lifetime_points": 100
            }
            
            success, response = self.run_test(
                "Create Loyalty Program",
                "POST",
                "loyalty/programs",
                200,
                data=program_data
            )
            
            if success and 'id' in response:
                self.created_resources['loyalty_programs'].append(response['id'])
        
        # Test get loyalty programs
        success, programs = self.run_test(
            "Get Loyalty Programs",
            "GET",
            "loyalty/programs",
            200
        )
        
        # Test create loyalty transaction
        if self.created_resources['guests']:
            transaction_data = {
                "tenant_id": "dummy",  # Will be overwritten by backend
                "guest_id": self.created_resources['guests'][0],
                "points": 50,
                "transaction_type": "earned",
                "description": "Stay bonus points"
            }
            
            success, response = self.run_test(
                "Create Loyalty Transaction",
                "POST",
                "loyalty/transactions",
                200,
                data=transaction_data
            )
        
        # Test get guest loyalty info
        if self.created_resources['guests']:
            success, loyalty_info = self.run_test(
                "Get Guest Loyalty",
                "GET",
                f"loyalty/guest/{self.created_resources['guests'][0]}",
                200
            )
        
        return True

    def test_marketplace_module(self):
        """Test Marketplace Service endpoints"""
        print("\n🛒 Testing Marketplace Module...")
        
        # Test get products
        success, products = self.run_test(
            "Get Products",
            "GET",
            "marketplace/products",
            200
        )
        
        # Test create order
        order_data = {
            "tenant_id": "dummy",  # Will be overwritten by backend
            "items": [
                {
                    "product_id": "sample-product-1",
                    "name": "Test Product",
                    "quantity": 2,
                    "price": 25.99,
                    "total": 51.98
                }
            ],
            "total_amount": 51.98,
            "delivery_address": self.tenant['address'] if self.tenant else "123 Test Street"
        }
        
        success, response = self.run_test(
            "Create Order",
            "POST",
            "marketplace/orders",
            200,
            data=order_data
        )
        
        if success and 'id' in response:
            self.created_resources['orders'].append(response['id'])
        
        # Test get orders
        success, orders = self.run_test(
            "Get Orders",
            "GET",
            "marketplace/orders",
            200
        )
        
        return True

    def test_multi_tenant_isolation(self):
        """Test that tenant isolation works properly"""
        print("\n🔒 Testing Multi-Tenant Isolation...")
        
        # Create a second tenant
        timestamp = datetime.now().strftime('%H%M%S') + "2"
        registration_data = {
            "property_name": f"Test Hotel 2 {timestamp}",
            "email": f"test2{timestamp}@example.com",
            "password": "TestPass123!",
            "name": f"Test Manager 2 {timestamp}",
            "phone": "+1234567891",
            "address": "456 Test Street, Test City"
        }
        
        success, response = self.run_test(
            "Register Second Tenant",
            "POST",
            "auth/register",
            200,
            data=registration_data
        )
        
        if success and 'access_token' in response:
            # Store original token
            original_token = self.token
            original_user = self.user
            
            # Switch to second tenant
            self.token = response['access_token']
            second_user = response['user']
            
            # Try to access first tenant's data (should be empty)
            success, rooms = self.run_test(
                "Tenant 2 - Get Rooms (Should be Empty)",
                "GET",
                "pms/rooms",
                200
            )
            
            if success and len(rooms) == 0:
                print("✅ Tenant isolation working - Second tenant sees no rooms from first tenant")
                self.tests_passed += 1
            else:
                print("❌ Tenant isolation failed - Second tenant can see first tenant's data")
            
            self.tests_run += 1
            
            # Restore original token
            self.token = original_token
            self.user = original_user
            
            return True
        
        return False

def main():
    print("🏨 Starting RoomOps Platform API Testing...")
    print("=" * 60)
    
    tester = RoomOpsAPITester()
    
    # Test authentication flow
    if not tester.test_registration():
        print("❌ Registration failed, stopping tests")
        return 1
    
    if not tester.test_login():
        print("❌ Login failed, stopping tests")
        return 1
    
    if not tester.test_auth_me():
        print("❌ Auth verification failed, stopping tests")
        return 1
    
    # Test all modules
    tester.test_pms_module()
    tester.test_invoice_module()
    tester.test_rms_module()
    tester.test_loyalty_module()
    tester.test_marketplace_module()
    
    # Test multi-tenant isolation
    tester.test_multi_tenant_isolation()
    
    # Print final results
    print("\n" + "=" * 60)
    print(f"📊 Final Results: {tester.tests_passed}/{tester.tests_run} tests passed")
    print(f"🎯 Success Rate: {(tester.tests_passed/tester.tests_run*100):.1f}%")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All tests passed!")
        return 0
    else:
        print("⚠️  Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())