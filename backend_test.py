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

    def test_accounting_invoice_with_taxes(self):
        """Test Accounting Invoice creation with additional tax functionality"""
        print("\n🧾 Testing Accounting Invoice with Additional Taxes...")
        
        # Test 1: Invoice with 10% VAT Rate
        print("\n📋 Test 1: Invoice with 10% VAT Rate")
        invoice_data_10_vat = {
            "invoice_type": "sales",
            "customer_name": "ABC Corporation",
            "customer_email": "abc@corporation.com",
            "items": [
                {
                    "description": "Premium Room Service",
                    "quantity": 1,
                    "unit_price": 100.0,
                    "vat_rate": 10.0,
                    "vat_amount": 10.0,
                    "total": 110.0,
                    "additional_taxes": []
                }
            ],
            "due_date": "2025-12-31",
            "notes": "Test invoice with 10% VAT"
        }
        
        success, response = self.run_test(
            "Create Invoice with 10% VAT",
            "POST",
            "accounting/invoices",
            200,
            data=invoice_data_10_vat
        )
        
        if success:
            # Verify calculations
            expected_subtotal = 100.0
            expected_total_vat = 10.0
            expected_total = 110.0
            
            if (response.get('subtotal') == expected_subtotal and 
                response.get('total_vat') == expected_total_vat and 
                response.get('total') == expected_total):
                print("✅ 10% VAT calculation verified")
                self.tests_passed += 1
            else:
                print(f"❌ 10% VAT calculation failed - Expected: subtotal={expected_subtotal}, vat={expected_total_vat}, total={expected_total}")
                print(f"   Got: subtotal={response.get('subtotal')}, vat={response.get('total_vat')}, total={response.get('total')}")
            self.tests_run += 1
        
        # Test 2: Invoice with ÖTV (Special Consumption Tax) - Percentage
        print("\n📋 Test 2: Invoice with ÖTV (Percentage)")
        invoice_data_otv_percent = {
            "invoice_type": "sales",
            "customer_name": "XYZ Hotel",
            "customer_email": "xyz@hotel.com",
            "items": [
                {
                    "description": "Luxury Beverage Package",
                    "quantity": 2,
                    "unit_price": 50.0,
                    "vat_rate": 18.0,
                    "vat_amount": 18.0,
                    "total": 118.0,
                    "additional_taxes": [
                        {
                            "tax_type": "otv",
                            "tax_name": "ÖTV (Special Consumption Tax)",
                            "rate": 5.0,
                            "is_percentage": True,
                            "calculated_amount": 5.0
                        }
                    ]
                }
            ],
            "due_date": "2025-12-31",
            "notes": "Test invoice with ÖTV percentage"
        }
        
        success, response = self.run_test(
            "Create Invoice with ÖTV (Percentage)",
            "POST",
            "accounting/invoices",
            200,
            data=invoice_data_otv_percent
        )
        
        if success:
            # Verify calculations: subtotal=100, vat=18, otv=5% of 100=5, total=123
            expected_subtotal = 100.0
            expected_total_vat = 18.0
            expected_additional_taxes = 5.0
            expected_total = 123.0
            
            if (response.get('subtotal') == expected_subtotal and 
                response.get('total_vat') == expected_total_vat and 
                response.get('total_additional_taxes') == expected_additional_taxes and
                response.get('total') == expected_total):
                print("✅ ÖTV percentage calculation verified")
                self.tests_passed += 1
            else:
                print(f"❌ ÖTV percentage calculation failed")
                print(f"   Expected: subtotal={expected_subtotal}, vat={expected_total_vat}, additional_taxes={expected_additional_taxes}, total={expected_total}")
                print(f"   Got: subtotal={response.get('subtotal')}, vat={response.get('total_vat')}, additional_taxes={response.get('total_additional_taxes')}, total={response.get('total')}")
            self.tests_run += 1
        
        # Test 3: Invoice with ÖTV (Fixed Amount)
        print("\n📋 Test 3: Invoice with ÖTV (Fixed Amount)")
        invoice_data_otv_fixed = {
            "invoice_type": "sales",
            "customer_name": "DEF Resort",
            "customer_email": "def@resort.com",
            "items": [
                {
                    "description": "Tobacco Products",
                    "quantity": 1,
                    "unit_price": 80.0,
                    "vat_rate": 18.0,
                    "vat_amount": 14.4,
                    "total": 94.4,
                    "additional_taxes": [
                        {
                            "tax_type": "otv",
                            "tax_name": "ÖTV (Fixed Amount)",
                            "amount": 10.0,
                            "is_percentage": False,
                            "calculated_amount": 10.0
                        }
                    ]
                }
            ],
            "due_date": "2025-12-31",
            "notes": "Test invoice with ÖTV fixed amount"
        }
        
        success, response = self.run_test(
            "Create Invoice with ÖTV (Fixed Amount)",
            "POST",
            "accounting/invoices",
            200,
            data=invoice_data_otv_fixed
        )
        
        if success:
            # Verify calculations: subtotal=80, vat=14.4, otv=10, total=104.4
            expected_subtotal = 80.0
            expected_total_vat = 14.4
            expected_additional_taxes = 10.0
            expected_total = 104.4
            
            if (response.get('subtotal') == expected_subtotal and 
                response.get('total_vat') == expected_total_vat and 
                response.get('total_additional_taxes') == expected_additional_taxes and
                response.get('total') == expected_total):
                print("✅ ÖTV fixed amount calculation verified")
                self.tests_passed += 1
            else:
                print(f"❌ ÖTV fixed amount calculation failed")
                print(f"   Expected: subtotal={expected_subtotal}, vat={expected_total_vat}, additional_taxes={expected_additional_taxes}, total={expected_total}")
                print(f"   Got: subtotal={response.get('subtotal')}, vat={response.get('total_vat')}, additional_taxes={response.get('total_additional_taxes')}, total={response.get('total')}")
            self.tests_run += 1
        
        # Test 4: Invoice with Withholding Tax (Tevkifat) - 7/10
        print("\n📋 Test 4: Invoice with Withholding Tax (7/10)")
        invoice_data_withholding = {
            "invoice_type": "sales",
            "customer_name": "GHI Construction",
            "customer_email": "ghi@construction.com",
            "items": [
                {
                    "description": "Construction Services",
                    "quantity": 1,
                    "unit_price": 100.0,
                    "vat_rate": 18.0,
                    "vat_amount": 18.0,
                    "total": 118.0,
                    "additional_taxes": [
                        {
                            "tax_type": "withholding",
                            "tax_name": "Tevkifat (7/10)",
                            "withholding_rate": "7/10",
                            "is_percentage": True,
                            "calculated_amount": 12.6
                        }
                    ]
                }
            ],
            "due_date": "2025-12-31",
            "notes": "Test invoice with withholding tax 7/10"
        }
        
        success, response = self.run_test(
            "Create Invoice with Withholding Tax (7/10)",
            "POST",
            "accounting/invoices",
            200,
            data=invoice_data_withholding
        )
        
        if success:
            # Verify calculations: subtotal=100, vat=18, withholding=70% of 18=12.6, total=100+18-12.6=105.4
            expected_subtotal = 100.0
            expected_total_vat = 18.0
            expected_vat_withholding = 12.6
            expected_total = 105.4
            
            if (response.get('subtotal') == expected_subtotal and 
                response.get('total_vat') == expected_total_vat and 
                response.get('vat_withholding') == expected_vat_withholding and
                response.get('total') == expected_total):
                print("✅ Withholding tax (7/10) calculation verified")
                self.tests_passed += 1
            else:
                print(f"❌ Withholding tax (7/10) calculation failed")
                print(f"   Expected: subtotal={expected_subtotal}, vat={expected_total_vat}, withholding={expected_vat_withholding}, total={expected_total}")
                print(f"   Got: subtotal={response.get('subtotal')}, vat={response.get('total_vat')}, withholding={response.get('vat_withholding')}, total={response.get('total')}")
            self.tests_run += 1
        
        # Test 5: Invoice with Accommodation Tax
        print("\n📋 Test 5: Invoice with Accommodation Tax")
        invoice_data_accommodation = {
            "invoice_type": "sales",
            "customer_name": "JKL Tourism",
            "customer_email": "jkl@tourism.com",
            "items": [
                {
                    "description": "Hotel Accommodation",
                    "quantity": 3,
                    "unit_price": 120.0,
                    "vat_rate": 8.0,
                    "vat_amount": 28.8,
                    "total": 388.8,
                    "additional_taxes": [
                        {
                            "tax_type": "accommodation",
                            "tax_name": "Konaklama Vergisi",
                            "rate": 2.0,
                            "is_percentage": True,
                            "calculated_amount": 7.2
                        }
                    ]
                }
            ],
            "due_date": "2025-12-31",
            "notes": "Test invoice with accommodation tax"
        }
        
        success, response = self.run_test(
            "Create Invoice with Accommodation Tax",
            "POST",
            "accounting/invoices",
            200,
            data=invoice_data_accommodation
        )
        
        if success:
            # Verify calculations: subtotal=360, vat=28.8, accommodation=2% of 360=7.2, total=396
            expected_subtotal = 360.0
            expected_total_vat = 28.8
            expected_additional_taxes = 7.2
            expected_total = 396.0
            
            if (response.get('subtotal') == expected_subtotal and 
                response.get('total_vat') == expected_total_vat and 
                response.get('total_additional_taxes') == expected_additional_taxes and
                response.get('total') == expected_total):
                print("✅ Accommodation tax calculation verified")
                self.tests_passed += 1
            else:
                print(f"❌ Accommodation tax calculation failed")
                print(f"   Expected: subtotal={expected_subtotal}, vat={expected_total_vat}, additional_taxes={expected_additional_taxes}, total={expected_total}")
                print(f"   Got: subtotal={response.get('subtotal')}, vat={response.get('total_vat')}, additional_taxes={response.get('total_additional_taxes')}, total={response.get('total')}")
            self.tests_run += 1
        
        # Test 6: Complex Invoice with Multiple Taxes
        print("\n📋 Test 6: Complex Invoice with Multiple Taxes")
        invoice_data_complex = {
            "invoice_type": "sales",
            "customer_name": "MNO Enterprise",
            "customer_email": "mno@enterprise.com",
            "items": [
                {
                    "description": "Premium Service Package",
                    "quantity": 1,
                    "unit_price": 200.0,
                    "vat_rate": 18.0,
                    "vat_amount": 36.0,
                    "total": 236.0,
                    "additional_taxes": [
                        {
                            "tax_type": "otv",
                            "tax_name": "ÖTV",
                            "rate": 3.0,
                            "is_percentage": True,
                            "calculated_amount": 6.0
                        },
                        {
                            "tax_type": "withholding",
                            "tax_name": "Tevkifat (9/10)",
                            "withholding_rate": "9/10",
                            "is_percentage": True,
                            "calculated_amount": 32.4
                        }
                    ]
                },
                {
                    "description": "Additional Services",
                    "quantity": 2,
                    "unit_price": 50.0,
                    "vat_rate": 10.0,
                    "vat_amount": 10.0,
                    "total": 110.0,
                    "additional_taxes": [
                        {
                            "tax_type": "accommodation",
                            "tax_name": "Konaklama Vergisi",
                            "rate": 1.5,
                            "is_percentage": True,
                            "calculated_amount": 1.5
                        }
                    ]
                }
            ],
            "due_date": "2025-12-31",
            "notes": "Test invoice with multiple complex taxes"
        }
        
        success, response = self.run_test(
            "Create Invoice with Multiple Taxes",
            "POST",
            "accounting/invoices",
            200,
            data=invoice_data_complex
        )
        
        if success:
            # Verify calculations:
            # Item 1: subtotal=200, vat=36, otv=6, withholding=90% of 36=32.4
            # Item 2: subtotal=100, vat=10, accommodation=1.5% of 100=1.5
            # Total: subtotal=300, vat=46, additional_taxes=7.5, withholding=32.4, total=321.1
            expected_subtotal = 300.0
            expected_total_vat = 46.0
            expected_additional_taxes = 7.5
            expected_vat_withholding = 32.4
            expected_total = 321.1
            
            if (response.get('subtotal') == expected_subtotal and 
                response.get('total_vat') == expected_total_vat and 
                response.get('total_additional_taxes') == expected_additional_taxes and
                response.get('vat_withholding') == expected_vat_withholding and
                abs(response.get('total', 0) - expected_total) < 0.01):  # Allow small floating point differences
                print("✅ Multiple taxes calculation verified")
                self.tests_passed += 1
            else:
                print(f"❌ Multiple taxes calculation failed")
                print(f"   Expected: subtotal={expected_subtotal}, vat={expected_total_vat}, additional_taxes={expected_additional_taxes}, withholding={expected_vat_withholding}, total={expected_total}")
                print(f"   Got: subtotal={response.get('subtotal')}, vat={response.get('total_vat')}, additional_taxes={response.get('total_additional_taxes')}, withholding={response.get('vat_withholding')}, total={response.get('total')}")
            self.tests_run += 1
        
        # Test 7: Different Withholding Rates
        print("\n📋 Test 7: Different Withholding Rates (9/10, 5/10, 3/10)")
        withholding_rates = [
            {"rate": "9/10", "expected_percent": 90},
            {"rate": "5/10", "expected_percent": 50},
            {"rate": "3/10", "expected_percent": 30}
        ]
        
        for rate_test in withholding_rates:
            rate = rate_test["rate"]
            expected_percent = rate_test["expected_percent"]
            
            invoice_data_rate = {
                "invoice_type": "sales",
                "customer_name": f"Test Company {rate}",
                "customer_email": f"test{rate.replace('/', '')}@company.com",
                "items": [
                    {
                        "description": f"Service with {rate} withholding",
                        "quantity": 1,
                        "unit_price": 100.0,
                        "vat_rate": 18.0,
                        "vat_amount": 18.0,
                        "total": 118.0,
                        "additional_taxes": [
                            {
                                "tax_type": "withholding",
                                "tax_name": f"Tevkifat ({rate})",
                                "withholding_rate": rate,
                                "is_percentage": True,
                                "calculated_amount": 18.0 * (expected_percent / 100)
                            }
                        ]
                    }
                ],
                "due_date": "2025-12-31",
                "notes": f"Test invoice with withholding tax {rate}"
            }
            
            success, response = self.run_test(
                f"Create Invoice with Withholding Tax ({rate})",
                "POST",
                "accounting/invoices",
                200,
                data=invoice_data_rate
            )
            
            if success:
                expected_withholding = 18.0 * (expected_percent / 100)
                expected_total = 100.0 + 18.0 - expected_withholding
                
                if (abs(response.get('vat_withholding', 0) - expected_withholding) < 0.01 and
                    abs(response.get('total', 0) - expected_total) < 0.01):
                    print(f"✅ Withholding tax ({rate}) calculation verified")
                    self.tests_passed += 1
                else:
                    print(f"❌ Withholding tax ({rate}) calculation failed")
                    print(f"   Expected: withholding={expected_withholding}, total={expected_total}")
                    print(f"   Got: withholding={response.get('vat_withholding')}, total={response.get('total')}")
                self.tests_run += 1
        
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