import requests
import sys
import json
from datetime import datetime, timedelta

class RoomOpsAPITester:
    def __init__(self, base_url="https://auto-corp-rates.preview.emergentagent.com"):
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
            'orders': [],
            'companies': []
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

    def test_corporate_booking_features(self):
        """Test comprehensive corporate booking and company management features"""
        print("\n🏢 Testing Corporate Booking Features...")
        
        # Test 1: Create Company
        print("\n📋 Test 1: Create Company")
        company_data = {
            "name": "Hilton Hotels Corp",
            "corporate_code": "HILTON01",
            "tax_number": "1234567890",
            "billing_address": "123 Main St, Istanbul",
            "contact_person": "John Doe",
            "contact_email": "john@hilton.com",
            "contact_phone": "+90-212-555-0123",
            "contracted_rate": "corp_std",
            "default_rate_type": "corporate",
            "default_market_segment": "corporate",
            "default_cancellation_policy": "h48",
            "payment_terms": "Net 30",
            "status": "active"
        }
        
        success, response = self.run_test(
            "Create Company",
            "POST",
            "companies",
            200,
            data=company_data
        )
        
        company_id = None
        if success and 'id' in response:
            company_id = response['id']
            self.created_resources['companies'].append(company_id)
            print(f"   Created company: {response.get('name')} (ID: {company_id})")
        
        # Test 2: Get All Companies
        print("\n📋 Test 2: Get All Companies")
        success, companies = self.run_test(
            "Get All Companies",
            "GET",
            "companies",
            200
        )
        
        if success and len(companies) > 0:
            print(f"   Retrieved {len(companies)} companies")
        
        # Test 3: Search Companies
        print("\n📋 Test 3: Search Companies")
        success, search_results = self.run_test(
            "Search Companies (Hilton)",
            "GET",
            "companies?search=Hilton",
            200
        )
        
        if success and len(search_results) > 0:
            print(f"   Found {len(search_results)} companies matching 'Hilton'")
        
        # Test 4: Get Specific Company
        if company_id:
            print("\n📋 Test 4: Get Specific Company")
            success, company_details = self.run_test(
                "Get Specific Company",
                "GET",
                f"companies/{company_id}",
                200
            )
            
            if success:
                print(f"   Retrieved company: {company_details.get('name')}")
        
        # Test 5: Update Company
        if company_id:
            print("\n📋 Test 5: Update Company")
            update_data = {
                "name": "Hilton Hotels Corp",
                "corporate_code": "HILTON01",
                "tax_number": "1234567890",
                "billing_address": "123 Main St, Istanbul",
                "contact_person": "John Doe",
                "contact_email": "john@hilton.com",
                "contact_phone": "+90-212-555-0123",
                "contracted_rate": "corp_std",
                "default_rate_type": "corporate",
                "default_market_segment": "corporate",
                "default_cancellation_policy": "h48",
                "payment_terms": "Net 45",  # Changed from Net 30
                "status": "active"
            }
            
            success, updated_company = self.run_test(
                "Update Company",
                "PUT",
                f"companies/{company_id}",
                200,
                data=update_data
            )
            
            if success and updated_company.get('payment_terms') == 'Net 45':
                print("   ✅ Company payment terms updated successfully")
                self.tests_passed += 1
            elif success:
                print("   ❌ Company update failed - payment terms not updated")
            self.tests_run += 1
        
        return company_id

    def test_corporate_bookings(self, company_id):
        """Test corporate booking functionality with rate overrides"""
        print("\n📋 Testing Corporate Bookings...")
        
        if not company_id or not self.created_resources['rooms'] or not self.created_resources['guests']:
            print("   ⚠️ Skipping corporate booking tests - missing prerequisites")
            return
        
        # Test 6: Create Booking with Corporate Features
        print("\n📋 Test 6: Create Corporate Booking")
        corporate_booking_data = {
            "guest_id": self.created_resources['guests'][0],
            "room_id": self.created_resources['rooms'][0],
            "check_in": (datetime.now() + timedelta(days=1)).isoformat(),
            "check_out": (datetime.now() + timedelta(days=3)).isoformat(),
            "adults": 2,
            "children": 1,
            "children_ages": [5],
            "guests_count": 3,
            "company_id": company_id,
            "contracted_rate": "corp_std",
            "rate_type": "corporate",
            "market_segment": "corporate",
            "cancellation_policy": "h48",
            "billing_address": "123 Main St, Istanbul",
            "billing_tax_number": "1234567890",
            "billing_contact_person": "John Doe",
            "base_rate": 100.0,
            "total_amount": 100.0,
            "channel": "direct"
        }
        
        success, booking_response = self.run_test(
            "Create Corporate Booking",
            "POST",
            "pms/bookings",
            200,
            data=corporate_booking_data
        )
        
        if success and 'id' in booking_response:
            self.created_resources['bookings'].append(booking_response['id'])
            
            # Verify corporate fields
            if (booking_response.get('adults') == 2 and 
                booking_response.get('children') == 1 and 
                booking_response.get('children_ages') == [5] and
                booking_response.get('company_id') == company_id and
                booking_response.get('contracted_rate') == 'corp_std'):
                print("   ✅ Corporate booking fields verified")
                self.tests_passed += 1
            else:
                print("   ❌ Corporate booking fields verification failed")
            self.tests_run += 1
        
        # Test 7: Create Booking with Rate Override (Automatic Logging)
        print("\n📋 Test 7: Create Booking with Rate Override")
        override_booking_data = {
            "guest_id": self.created_resources['guests'][0],
            "room_id": self.created_resources['rooms'][0],
            "check_in": (datetime.now() + timedelta(days=5)).isoformat(),
            "check_out": (datetime.now() + timedelta(days=7)).isoformat(),
            "adults": 2,
            "children": 0,
            "children_ages": [],
            "guests_count": 2,
            "company_id": company_id,
            "contracted_rate": "corp_std",
            "rate_type": "corporate",
            "market_segment": "corporate",
            "cancellation_policy": "h48",
            "billing_address": "123 Main St, Istanbul",
            "billing_tax_number": "1234567890",
            "billing_contact_person": "John Doe",
            "base_rate": 150.0,  # Base rate
            "total_amount": 120.0,  # Discounted rate
            "override_reason": "VIP customer discount",
            "channel": "direct"
        }
        
        success, override_booking_response = self.run_test(
            "Create Booking with Rate Override",
            "POST",
            "pms/bookings",
            200,
            data=override_booking_data
        )
        
        override_booking_id = None
        if success and 'id' in override_booking_response:
            override_booking_id = override_booking_response['id']
            self.created_resources['bookings'].append(override_booking_id)
            
            # Test 8: Verify Override Log was Created
            print("\n📋 Test 8: Verify Override Log Creation")
            success, override_logs = self.run_test(
                "Get Override Logs",
                "GET",
                f"bookings/{override_booking_id}/override-logs",
                200
            )
            
            if success and len(override_logs) > 0:
                log = override_logs[0]
                if (log.get('base_rate') == 150.0 and 
                    log.get('new_rate') == 120.0 and 
                    log.get('override_reason') == 'VIP customer discount'):
                    print("   ✅ Override log created and verified")
                    self.tests_passed += 1
                else:
                    print("   ❌ Override log data incorrect")
                    print(f"      Expected: base_rate=150.0, new_rate=120.0, reason='VIP customer discount'")
                    print(f"      Got: base_rate={log.get('base_rate')}, new_rate={log.get('new_rate')}, reason='{log.get('override_reason')}'")
            else:
                print("   ❌ Override log not found")
            self.tests_run += 1
            
            # Test 9: Create Manual Rate Override
            print("\n📋 Test 9: Create Manual Rate Override")
            success, manual_override = self.run_test(
                "Create Manual Rate Override",
                "POST",
                f"bookings/{override_booking_id}/override?new_rate=110.0&override_reason=Manager approval",
                200
            )
            
            if success:
                # Verify booking total was updated
                success, updated_booking = self.run_test(
                    "Verify Booking Rate Updated",
                    "GET",
                    f"pms/bookings",
                    200
                )
                
                if success:
                    # Find our booking in the list
                    target_booking = None
                    for booking in updated_booking:
                        if booking.get('id') == override_booking_id:
                            target_booking = booking
                            break
                    
                    if target_booking and target_booking.get('total_amount') == 110.0:
                        print("   ✅ Manual override applied and booking updated")
                        self.tests_passed += 1
                    else:
                        print("   ❌ Manual override failed - booking not updated")
                else:
                    print("   ❌ Could not verify booking update")
                self.tests_run += 1

    def test_edge_cases(self, company_id):
        """Test edge cases for corporate bookings"""
        print("\n📋 Testing Edge Cases...")
        
        if not company_id or not self.created_resources['rooms'] or not self.created_resources['guests']:
            print("   ⚠️ Skipping edge case tests - missing prerequisites")
            return
        
        # Test 10: Edge Case - Children with Ages
        print("\n📋 Test 10: Edge Case - Multiple Children with Ages")
        children_booking_data = {
            "guest_id": self.created_resources['guests'][0],
            "room_id": self.created_resources['rooms'][0],
            "check_in": (datetime.now() + timedelta(days=10)).isoformat(),
            "check_out": (datetime.now() + timedelta(days=12)).isoformat(),
            "adults": 2,
            "children": 3,
            "children_ages": [4, 7, 10],
            "guests_count": 5,
            "company_id": company_id,
            "contracted_rate": "corp_std",
            "rate_type": "corporate",
            "market_segment": "corporate",
            "cancellation_policy": "h48",
            "billing_address": "123 Main St, Istanbul",
            "billing_tax_number": "1234567890",
            "billing_contact_person": "John Doe",
            "base_rate": 200.0,
            "total_amount": 200.0,
            "channel": "direct"
        }
        
        success, children_booking = self.run_test(
            "Create Booking with Multiple Children",
            "POST",
            "pms/bookings",
            200,
            data=children_booking_data
        )
        
        if success and 'id' in children_booking:
            if (children_booking.get('children') == 3 and 
                children_booking.get('children_ages') == [4, 7, 10] and
                children_booking.get('guests_count') == 5):
                print("   ✅ Multiple children booking verified")
                self.tests_passed += 1
            else:
                print("   ❌ Multiple children booking verification failed")
            self.tests_run += 1
        
        # Test 11: Edge Case - No Children
        print("\n📋 Test 11: Edge Case - No Children")
        no_children_booking_data = {
            "guest_id": self.created_resources['guests'][0],
            "room_id": self.created_resources['rooms'][0],
            "check_in": (datetime.now() + timedelta(days=15)).isoformat(),
            "check_out": (datetime.now() + timedelta(days=17)).isoformat(),
            "adults": 2,
            "children": 0,
            "children_ages": [],
            "guests_count": 2,
            "company_id": company_id,
            "contracted_rate": "corp_std",
            "rate_type": "corporate",
            "market_segment": "corporate",
            "cancellation_policy": "h48",
            "billing_address": "123 Main St, Istanbul",
            "billing_tax_number": "1234567890",
            "billing_contact_person": "John Doe",
            "base_rate": 180.0,
            "total_amount": 180.0,
            "channel": "direct"
        }
        
        success, no_children_booking = self.run_test(
            "Create Booking with No Children",
            "POST",
            "pms/bookings",
            200,
            data=no_children_booking_data
        )
        
        if success and 'id' in no_children_booking:
            if (no_children_booking.get('children') == 0 and 
                no_children_booking.get('children_ages') == [] and
                no_children_booking.get('guests_count') == 2):
                print("   ✅ No children booking verified")
                self.tests_passed += 1
            else:
                print("   ❌ No children booking verification failed")
            self.tests_run += 1
        
        # Test 12: Create Company with Pending Status (Quick-create scenario)
        print("\n📋 Test 12: Create Company with Pending Status")
        pending_company_data = {
            "name": "Quick Created Corp",
            "corporate_code": "QUICK01",
            "status": "pending"
        }
        
        success, pending_company = self.run_test(
            "Create Pending Company",
            "POST",
            "companies",
            200,
            data=pending_company_data
        )
        
        if success and 'id' in pending_company:
            if pending_company.get('status') == 'pending':
                print("   ✅ Pending company created successfully")
                self.tests_passed += 1
                self.created_resources['companies'].append(pending_company['id'])
            else:
                print("   ❌ Pending company status incorrect")
        else:
            print("   ❌ Pending company creation failed")
        self.tests_run += 1
        
        # Test 13: Test Enum Values
        print("\n📋 Test 13: Test Enum Values")
        enum_test_data = {
            "name": "Enum Test Corp",
            "corporate_code": "ENUM01",
            "contracted_rate": "corp_pref",  # Different contracted rate
            "default_rate_type": "government",  # Different rate type
            "default_market_segment": "mice",  # Different market segment
            "default_cancellation_policy": "d7",  # Different cancellation policy
            "status": "active"
        }
        
        success, enum_company = self.run_test(
            "Create Company with Different Enum Values",
            "POST",
            "companies",
            200,
            data=enum_test_data
        )
        
        if success and 'id' in enum_company:
            if (enum_company.get('contracted_rate') == 'corp_pref' and
                enum_company.get('default_rate_type') == 'government' and
                enum_company.get('default_market_segment') == 'mice' and
                enum_company.get('default_cancellation_policy') == 'd7'):
                print("   ✅ Enum values verified")
                self.tests_passed += 1
                self.created_resources['companies'].append(enum_company['id'])
            else:
                print("   ❌ Enum values verification failed")
        else:
            print("   ❌ Enum company creation failed")
        self.tests_run += 1

    def test_folio_billing_engine(self):
        """Test comprehensive Folio & Billing Engine functionality"""
        print("\n💰 Testing Folio & Billing Engine...")
        
        # Prerequisites: Create test guest, room, and booking
        test_guest_id = None
        test_room_id = None
        test_booking_id = None
        test_company_id = None
        
        # Create test guest if not exists
        if not self.created_resources['guests']:
            guest_data = {
                "name": "Folio Test Guest",
                "email": "folio.guest@example.com",
                "phone": "+1234567890",
                "id_number": "FOLIO123456",
                "address": "123 Folio Street"
            }
            
            success, response = self.run_test(
                "Create Test Guest for Folio",
                "POST",
                "pms/guests",
                200,
                data=guest_data
            )
            
            if success and 'id' in response:
                test_guest_id = response['id']
                self.created_resources['guests'].append(test_guest_id)
        else:
            test_guest_id = self.created_resources['guests'][0]
        
        # Create test room if not exists
        if not self.created_resources['rooms']:
            room_data = {
                "room_number": "101",
                "room_type": "deluxe",
                "floor": 1,
                "capacity": 2,
                "base_price": 100.00,
                "amenities": ["wifi", "tv", "minibar"]
            }
            
            success, response = self.run_test(
                "Create Test Room for Folio",
                "POST",
                "pms/rooms",
                200,
                data=room_data
            )
            
            if success and 'id' in response:
                test_room_id = response['id']
                self.created_resources['rooms'].append(test_room_id)
        else:
            test_room_id = self.created_resources['rooms'][0]
        
        # Create test company if not exists
        if not self.created_resources['companies']:
            company_data = {
                "name": "Folio Test Company",
                "corporate_code": "FOLIO01",
                "tax_number": "9876543210",
                "billing_address": "456 Company Ave",
                "contact_person": "Jane Smith",
                "contact_email": "jane@foliocompany.com",
                "contact_phone": "+1234567891",
                "status": "active"
            }
            
            success, response = self.run_test(
                "Create Test Company for Folio",
                "POST",
                "companies",
                200,
                data=company_data
            )
            
            if success and 'id' in response:
                test_company_id = response['id']
                self.created_resources['companies'].append(test_company_id)
        else:
            test_company_id = self.created_resources['companies'][0]
        
        # Create test booking
        if test_guest_id and test_room_id:
            booking_data = {
                "guest_id": test_guest_id,
                "room_id": test_room_id,
                "check_in": datetime.now().isoformat(),
                "check_out": (datetime.now() + timedelta(days=1)).isoformat(),
                "adults": 2,
                "children": 0,
                "children_ages": [],
                "guests_count": 2,
                "total_amount": 100.0,
                "channel": "direct"
            }
            
            success, response = self.run_test(
                "Create Test Booking for Folio",
                "POST",
                "pms/bookings",
                200,
                data=booking_data
            )
            
            if success and 'id' in response:
                test_booking_id = response['id']
                self.created_resources['bookings'].append(test_booking_id)
        
        if not (test_guest_id and test_room_id and test_booking_id and test_company_id):
            print("   ⚠️ Skipping folio tests - missing prerequisites")
            return False
        
        # Now run the folio tests
        guest_folio_id = self.test_folio_creation(test_booking_id, test_company_id)
        company_folio_id = None
        
        if guest_folio_id:
            company_folio_id = self.test_company_folio_creation(test_booking_id, test_company_id)
            self.test_charge_posting(guest_folio_id)
            self.test_payment_posting(guest_folio_id)
            self.test_folio_details(guest_folio_id)
            
            if company_folio_id:
                self.test_charge_transfer(guest_folio_id, company_folio_id)
            
            self.test_void_charge(guest_folio_id)
            self.test_booking_folios_list(test_booking_id)
            self.test_folio_closure(guest_folio_id)
            self.test_night_audit()
            self.test_folio_edge_cases(test_booking_id, guest_folio_id)
        
        return True

    def test_folio_creation(self, booking_id, company_id):
        """Test 1: FOLIO CREATION"""
        print("\n📋 Test 1: Folio Creation")
        
        # Create guest folio
        guest_folio_data = {
            "booking_id": booking_id,
            "folio_type": "guest"
        }
        
        success, response = self.run_test(
            "Create Guest Folio",
            "POST",
            "folio/create",
            200,
            data=guest_folio_data
        )
        
        guest_folio_id = None
        if success and 'id' in response:
            guest_folio_id = response['id']
            
            # Verify folio details
            if (response.get('folio_type') == 'guest' and
                response.get('status') == 'open' and
                response.get('balance') == 0.0 and
                'F-' in response.get('folio_number', '')):
                print("   ✅ Guest folio created successfully")
                print(f"      Folio Number: {response.get('folio_number')}")
                self.tests_passed += 1
            else:
                print("   ❌ Guest folio creation verification failed")
        else:
            print("   ❌ Guest folio creation failed")
        self.tests_run += 1
        
        return guest_folio_id

    def test_company_folio_creation(self, booking_id, company_id):
        """Create company folio"""
        company_folio_data = {
            "booking_id": booking_id,
            "folio_type": "company",
            "company_id": company_id
        }
        
        success, response = self.run_test(
            "Create Company Folio",
            "POST",
            "folio/create",
            200,
            data=company_folio_data
        )
        
        company_folio_id = None
        if success and 'id' in response:
            company_folio_id = response['id']
            
            if (response.get('folio_type') == 'company' and
                response.get('company_id') == company_id and
                response.get('status') == 'open' and
                response.get('balance') == 0.0):
                print("   ✅ Company folio created successfully")
                self.tests_passed += 1
            else:
                print("   ❌ Company folio creation verification failed")
        else:
            print("   ❌ Company folio creation failed")
        self.tests_run += 1
        
        return company_folio_id

    def test_charge_posting(self, folio_id):
        """Test 2: CHARGE POSTING"""
        print("\n📋 Test 2: Charge Posting")
        
        # Post room charge
        room_charge_data = {
            "charge_category": "room",
            "description": "Room 101 - Night 1",
            "amount": 100.0,
            "quantity": 1,
            "auto_calculate_tax": False
        }
        
        success, response = self.run_test(
            "Post Room Charge",
            "POST",
            f"folio/{folio_id}/charge",
            200,
            data=room_charge_data
        )
        
        room_charge_id = None
        if success and 'id' in response:
            room_charge_id = response['id']
            if (response.get('charge_category') == 'room' and
                response.get('amount') == 100.0 and
                response.get('total') == 100.0):
                print("   ✅ Room charge posted successfully")
                self.tests_passed += 1
            else:
                print("   ❌ Room charge posting verification failed")
        self.tests_run += 1
        
        # Post food charge
        food_charge_data = {
            "charge_category": "food",
            "description": "Breakfast",
            "amount": 25.0,
            "quantity": 2,
            "auto_calculate_tax": False
        }
        
        success, response = self.run_test(
            "Post Food Charge",
            "POST",
            f"folio/{folio_id}/charge",
            200,
            data=food_charge_data
        )
        
        if success and response.get('amount') == 50.0:  # 25 * 2
            print("   ✅ Food charge posted successfully")
            self.tests_passed += 1
        else:
            print("   ❌ Food charge posting failed")
        self.tests_run += 1
        
        # Post minibar charge
        minibar_charge_data = {
            "charge_category": "minibar",
            "description": "Coca Cola",
            "amount": 5.0,
            "quantity": 3,
            "auto_calculate_tax": False
        }
        
        success, response = self.run_test(
            "Post Minibar Charge",
            "POST",
            f"folio/{folio_id}/charge",
            200,
            data=minibar_charge_data
        )
        
        minibar_charge_id = None
        if success and 'id' in response:
            minibar_charge_id = response['id']
            if response.get('amount') == 15.0:  # 5 * 3
                print("   ✅ Minibar charge posted successfully")
                self.tests_passed += 1
            else:
                print("   ❌ Minibar charge posting failed")
        self.tests_run += 1
        
        return room_charge_id, minibar_charge_id

    def test_payment_posting(self, folio_id):
        """Test 3: PAYMENT POSTING"""
        print("\n📋 Test 3: Payment Posting")
        
        # Post prepayment
        prepayment_data = {
            "amount": 50.0,
            "method": "card",
            "payment_type": "prepayment"
        }
        
        success, response = self.run_test(
            "Post Prepayment",
            "POST",
            f"folio/{folio_id}/payment",
            200,
            data=prepayment_data
        )
        
        if success and response.get('amount') == 50.0 and response.get('payment_type') == 'prepayment':
            print("   ✅ Prepayment posted successfully")
            self.tests_passed += 1
        else:
            print("   ❌ Prepayment posting failed")
        self.tests_run += 1
        
        # Post interim payment
        interim_payment_data = {
            "amount": 100.0,
            "method": "card",
            "payment_type": "interim"
        }
        
        success, response = self.run_test(
            "Post Interim Payment",
            "POST",
            f"folio/{folio_id}/payment",
            200,
            data=interim_payment_data
        )
        
        if success and response.get('amount') == 100.0 and response.get('payment_type') == 'interim':
            print("   ✅ Interim payment posted successfully")
            self.tests_passed += 1
        else:
            print("   ❌ Interim payment posting failed")
        self.tests_run += 1

    def test_folio_details(self, folio_id):
        """Test 4: FOLIO DETAILS"""
        print("\n📋 Test 4: Folio Details")
        
        success, response = self.run_test(
            "Get Folio Details",
            "GET",
            f"folio/{folio_id}",
            200
        )
        
        if success:
            folio = response.get('folio', {})
            charges = response.get('charges', [])
            payments = response.get('payments', [])
            balance = response.get('balance', 0)
            
            # Expected balance: (100 + 50 + 15) - (50 + 100) = 15
            expected_balance = 15.0
            
            if (len(charges) >= 3 and  # At least 3 charges
                len(payments) >= 2 and  # At least 2 payments
                abs(balance - expected_balance) < 0.01):  # Balance matches
                print(f"   ✅ Folio details verified - Balance: {balance}")
                self.tests_passed += 1
            else:
                print(f"   ❌ Folio details verification failed")
                print(f"      Charges: {len(charges)}, Payments: {len(payments)}, Balance: {balance}")
                print(f"      Expected balance: {expected_balance}")
        else:
            print("   ❌ Failed to get folio details")
        self.tests_run += 1

    def test_charge_transfer(self, from_folio_id, to_folio_id):
        """Test 5: CHARGE TRANSFER"""
        print("\n📋 Test 5: Charge Transfer")
        
        # First, get charges from source folio to find room charge
        success, folio_details = self.run_test(
            "Get Source Folio for Transfer",
            "GET",
            f"folio/{from_folio_id}",
            200
        )
        
        room_charge_id = None
        if success:
            charges = folio_details.get('charges', [])
            for charge in charges:
                if charge.get('charge_category') == 'room' and not charge.get('voided'):
                    room_charge_id = charge.get('id')
                    break
        
        if not room_charge_id:
            print("   ⚠️ No room charge found for transfer")
            self.tests_run += 1
            return
        
        # Transfer room charge to company folio
        transfer_data = {
            "operation_type": "transfer",
            "from_folio_id": from_folio_id,
            "to_folio_id": to_folio_id,
            "charge_ids": [room_charge_id],
            "reason": "Company billing"
        }
        
        success, response = self.run_test(
            "Transfer Room Charge",
            "POST",
            "folio/transfer",
            200,
            data=transfer_data
        )
        
        if success and response.get('operation_type') == 'transfer':
            print("   ✅ Charge transfer completed successfully")
            self.tests_passed += 1
        else:
            print("   ❌ Charge transfer failed")
        self.tests_run += 1

    def test_void_charge(self, folio_id):
        """Test 6: VOID CHARGE"""
        print("\n📋 Test 6: Void Charge")
        
        # Get folio details to find minibar charge
        success, folio_details = self.run_test(
            "Get Folio for Void",
            "GET",
            f"folio/{folio_id}",
            200
        )
        
        minibar_charge_id = None
        if success:
            charges = folio_details.get('charges', [])
            for charge in charges:
                if charge.get('charge_category') == 'minibar' and not charge.get('voided'):
                    minibar_charge_id = charge.get('id')
                    break
        
        if not minibar_charge_id:
            print("   ⚠️ No minibar charge found for voiding")
            self.tests_run += 1
            return
        
        # Void the minibar charge
        success, response = self.run_test(
            "Void Minibar Charge",
            "POST",
            f"folio/{folio_id}/void-charge/{minibar_charge_id}?void_reason=Wrong charge",
            200
        )
        
        if success:
            print("   ✅ Charge voided successfully")
            self.tests_passed += 1
        else:
            print("   ❌ Charge void failed")
        self.tests_run += 1

    def test_booking_folios_list(self, booking_id):
        """Test 7: BOOKING FOLIOS LIST"""
        print("\n📋 Test 7: Booking Folios List")
        
        success, response = self.run_test(
            "Get Booking Folios",
            "GET",
            f"folio/booking/{booking_id}",
            200
        )
        
        if success and len(response) >= 1:  # At least guest folio
            print(f"   ✅ Retrieved {len(response)} folios for booking")
            self.tests_passed += 1
        else:
            print("   ❌ Failed to get booking folios")
        self.tests_run += 1

    def test_folio_closure(self, folio_id):
        """Test 8: FOLIO CLOSURE"""
        print("\n📋 Test 8: Folio Closure")
        
        # First try to close with outstanding balance (should fail)
        success, response = self.run_test(
            "Try Close Folio with Balance (Should Fail)",
            "POST",
            f"folio/{folio_id}/close",
            400  # Expecting failure
        )
        
        if not success:  # This is expected
            print("   ✅ Folio closure correctly rejected with outstanding balance")
            self.tests_passed += 1
        else:
            print("   ❌ Folio closure should have failed with outstanding balance")
        self.tests_run += 1
        
        # Add payment to clear balance
        # Get current balance first
        success, folio_details = self.run_test(
            "Get Folio Balance for Closure",
            "GET",
            f"folio/{folio_id}",
            200
        )
        
        if success:
            balance = folio_details.get('balance', 0)
            if balance > 0:
                # Add payment to clear balance
                payment_data = {
                    "amount": balance,
                    "method": "card",
                    "payment_type": "final"
                }
                
                success, payment_response = self.run_test(
                    "Add Final Payment to Clear Balance",
                    "POST",
                    f"folio/{folio_id}/payment",
                    200,
                    data=payment_data
                )
                
                if success:
                    # Now try to close folio (should succeed)
                    success, close_response = self.run_test(
                        "Close Folio After Payment",
                        "POST",
                        f"folio/{folio_id}/close",
                        200
                    )
                    
                    if success:
                        print("   ✅ Folio closed successfully after payment")
                        self.tests_passed += 1
                    else:
                        print("   ❌ Folio closure failed after payment")
                else:
                    print("   ❌ Failed to add final payment")
            else:
                # Balance is already zero or negative, try to close
                success, close_response = self.run_test(
                    "Close Folio (Zero Balance)",
                    "POST",
                    f"folio/{folio_id}/close",
                    200
                )
                
                if success:
                    print("   ✅ Folio closed successfully")
                    self.tests_passed += 1
                else:
                    print("   ❌ Folio closure failed")
        self.tests_run += 1

    def test_night_audit(self):
        """Test 9: NIGHT AUDIT"""
        print("\n📋 Test 9: Night Audit")
        
        # Update booking status to checked_in if needed
        if self.created_resources['bookings']:
            booking_id = self.created_resources['bookings'][0]
            
            # Update booking to checked_in status
            success, update_response = self.run_test(
                "Update Booking to Checked In",
                "POST",
                f"frontdesk/checkin/{booking_id}",
                200
            )
            
            if success:
                print("   ✅ Booking checked in for night audit")
            
            # Run night audit
            success, response = self.run_test(
                "Run Night Audit",
                "POST",
                "night-audit/post-room-charges",
                200
            )
            
            if success:
                charges_posted = response.get('charges_posted', 0)
                bookings_processed = response.get('bookings_processed', 0)
                print(f"   ✅ Night audit completed - {charges_posted} charges posted to {bookings_processed} bookings")
                self.tests_passed += 1
            else:
                print("   ❌ Night audit failed")
        else:
            print("   ⚠️ No bookings available for night audit")
        self.tests_run += 1

    def test_folio_edge_cases(self, booking_id, folio_id):
        """Test 10: EDGE CASES"""
        print("\n📋 Test 10: Edge Cases")
        
        # Try creating folio for non-existent booking
        invalid_folio_data = {
            "booking_id": "non-existent-booking-id",
            "folio_type": "guest"
        }
        
        success, response = self.run_test(
            "Create Folio for Non-existent Booking (Should Fail)",
            "POST",
            "folio/create",
            404,  # Expecting failure
            data=invalid_folio_data
        )
        
        if not success:  # This is expected
            print("   ✅ Correctly rejected folio creation for non-existent booking")
            self.tests_passed += 1
        else:
            print("   ❌ Should have failed creating folio for non-existent booking")
        self.tests_run += 1
        
        # Try posting charge to closed folio (if we have a closed folio)
        # This test might not work if folio isn't actually closed
        charge_data = {
            "charge_category": "other",
            "description": "Test charge to closed folio",
            "amount": 10.0,
            "quantity": 1,
            "auto_calculate_tax": False
        }
        
        success, response = self.run_test(
            "Post Charge to Closed Folio (May Fail)",
            "POST",
            f"folio/{folio_id}/charge",
            404,  # Expecting failure if folio is closed
            data=charge_data
        )
        
        if not success:
            print("   ✅ Correctly rejected charge to closed folio")
            self.tests_passed += 1
        else:
            print("   ⚠️ Charge posted (folio may not be closed)")
        self.tests_run += 1
        
        # Try voiding already voided charge
        # Get folio details to find a voided charge
        success, folio_details = self.run_test(
            "Get Folio for Void Test",
            "GET",
            f"folio/{folio_id}",
            200
        )
        
        voided_charge_id = None
        if success:
            charges = folio_details.get('charges', [])
            for charge in charges:
                if charge.get('voided'):
                    voided_charge_id = charge.get('id')
                    break
        
        if voided_charge_id:
            success, response = self.run_test(
                "Try Void Already Voided Charge (Should Fail)",
                "POST",
                f"folio/{folio_id}/void-charge/{voided_charge_id}?void_reason=Test double void",
                404  # Expecting failure
            )
            
            if not success:
                print("   ✅ Correctly rejected voiding already voided charge")
                self.tests_passed += 1
            else:
                print("   ❌ Should have failed voiding already voided charge")
        else:
            print("   ⚠️ No voided charges found for testing")
        self.tests_run += 1
        
        # Try transferring non-existent charge
        transfer_data = {
            "operation_type": "transfer",
            "from_folio_id": folio_id,
            "to_folio_id": folio_id,  # Same folio for simplicity
            "charge_ids": ["non-existent-charge-id"],
            "reason": "Test transfer of non-existent charge"
        }
        
        success, response = self.run_test(
            "Transfer Non-existent Charge (Should Handle Gracefully)",
            "POST",
            "folio/transfer",
            200,  # Should handle gracefully
            data=transfer_data
        )
        
        if success:
            print("   ✅ Transfer of non-existent charge handled gracefully")
            self.tests_passed += 1
        else:
            print("   ❌ Transfer of non-existent charge not handled properly")
        self.tests_run += 1

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
    
    # Test accounting invoice with additional taxes (NEW FUNCTIONALITY)
    tester.test_accounting_invoice_with_taxes()
    
    # Test corporate booking features (NEW FUNCTIONALITY)
    company_id = tester.test_corporate_booking_features()
    if company_id:
        tester.test_corporate_bookings(company_id)
        tester.test_edge_cases(company_id)
    
    # Test Folio & Billing Engine (NEW FUNCTIONALITY)
    tester.test_folio_billing_engine()
    
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