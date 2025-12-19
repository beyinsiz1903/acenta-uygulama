#!/usr/bin/env python3
"""
Comprehensive backend API test for Acenta Master
Tests all endpoints with proper flow
"""
import requests
import sys
import uuid
from datetime import datetime, timedelta

class AcentaAPITester:
    def __init__(self, base_url="https://pms-extranet-app.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.failed_tests = []
        
        # Store created IDs for cleanup and further testing
        self.product_id = None
        self.customer_id = None
        self.reservation_id = None
        self.lead_id = None
        self.quote_id = None
        self.agency_id = None
        self.agent_email = None

    def log(self, msg):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    def run_test(self, name, method, endpoint, expected_status, data=None, headers_override=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        headers = headers_override or {'Content-Type': 'application/json'}
        if self.token and not headers_override:
            headers['Authorization'] = f'Bearer {self.token}'

        self.tests_run += 1
        self.log(f"🔍 Test #{self.tests_run}: {name}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=10)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=10)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=10)
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
        """Test health endpoint"""
        self.log("\n=== HEALTH CHECK ===")
        success, response = self.run_test(
            "Health Check",
            "GET",
            "api/health",
            200
        )
        if success and response.get('ok'):
            self.log("✅ Database connection OK")
        return success

    def test_login(self):
        """Test login with seeded admin"""
        self.log("\n=== AUTHENTICATION ===")
        success, response = self.run_test(
            "Login with admin@acenta.test",
            "POST",
            "api/auth/login",
            200,
            data={"email": "admin@acenta.test", "password": "admin123"}
        )
        if success and 'access_token' in response:
            self.token = response['access_token']
            self.log(f"✅ Token obtained: {self.token[:20]}...")
            return True
        return False

    def test_me(self):
        """Test /me endpoint"""
        success, response = self.run_test(
            "Get current user (/me)",
            "GET",
            "api/auth/me",
            200
        )
        if success:
            self.log(f"✅ User: {response.get('email')}, Roles: {response.get('roles')}")
        return success

    def test_products_crud(self):
        """Test products CRUD operations"""
        self.log("\n=== PRODUCTS CRUD ===")
        
        # Create product
        product_data = {
            "title": f"Test Tour {uuid.uuid4().hex[:8]}",
            "type": "tour",
            "description": "Test tour description",
            "currency": "TRY"
        }
        success, response = self.run_test(
            "Create Product",
            "POST",
            "api/products",
            200,
            data=product_data
        )
        if success and response.get('id'):
            self.product_id = response['id']
            self.log(f"✅ Product created with ID: {self.product_id}")
        else:
            return False

        # List products
        success, response = self.run_test(
            "List Products",
            "GET",
            "api/products",
            200
        )
        if success:
            self.log(f"✅ Found {len(response)} products")

        # Get single product
        success, response = self.run_test(
            "Get Product by ID",
            "GET",
            f"api/products/{self.product_id}",
            200
        )

        # Update product
        product_data['title'] = f"Updated Tour {uuid.uuid4().hex[:8]}"
        success, response = self.run_test(
            "Update Product",
            "PUT",
            f"api/products/{self.product_id}",
            200,
            data=product_data
        )

        return True

    def test_inventory(self):
        """Test inventory management"""
        self.log("\n=== INVENTORY ===")
        
        if not self.product_id:
            self.log("⚠️  Skipping inventory tests - no product_id")
            return False

        # Upsert inventory
        today = datetime.now().strftime("%Y-%m-%d")
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        
        inventory_data = {
            "product_id": self.product_id,
            "date": today,
            "capacity_total": 10,
            "capacity_available": 10,
            "price": 150.0
        }
        success, response = self.run_test(
            "Upsert Inventory",
            "POST",
            "api/inventory/upsert",
            200,
            data=inventory_data
        )

        # List inventory
        success, response = self.run_test(
            "List Inventory",
            "GET",
            f"api/inventory?product_id={self.product_id}&start={today}&end={tomorrow}",
            200
        )
        if success:
            self.log(f"✅ Found {len(response)} inventory records")

        return True

    def test_customers_crud(self):
        """Test customers CRUD operations"""
        self.log("\n=== CUSTOMERS CRUD ===")
        
        # Create customer
        customer_data = {
            "name": f"Test Customer {uuid.uuid4().hex[:8]}",
            "email": f"test{uuid.uuid4().hex[:8]}@example.com",
            "phone": "+905551234567"
        }
        success, response = self.run_test(
            "Create Customer",
            "POST",
            "api/customers",
            200,
            data=customer_data
        )
        if success and response.get('id'):
            self.customer_id = response['id']
            self.log(f"✅ Customer created with ID: {self.customer_id}")
        else:
            return False

        # List customers
        success, response = self.run_test(
            "List Customers",
            "GET",
            "api/customers",
            200
        )
        if success:
            self.log(f"✅ Found {len(response)} customers")

        # Get single customer
        success, response = self.run_test(
            "Get Customer by ID",
            "GET",
            f"api/customers/{self.customer_id}",
            200
        )

        # Update customer
        customer_data['name'] = f"Updated Customer {uuid.uuid4().hex[:8]}"
        success, response = self.run_test(
            "Update Customer",
            "PUT",
            f"api/customers/{self.customer_id}",
            200,
            data=customer_data
        )

        return True

    def test_reservations(self):
        """Test reservation flow"""
        self.log("\n=== RESERVATIONS ===")
        
        if not self.product_id or not self.customer_id:
            self.log("⚠️  Skipping reservation tests - missing product_id or customer_id")
            return False

        # Create reservation (single day tour - end_date should be None)
        today = datetime.now().strftime("%Y-%m-%d")
        reservation_data = {
            "idempotency_key": str(uuid.uuid4()),
            "product_id": self.product_id,
            "customer_id": self.customer_id,
            "start_date": today,
            "end_date": None,
            "pax": 2,
            "channel": "direct",
            "agency_id": None
        }
        success, response = self.run_test(
            "Create Reservation",
            "POST",
            "api/reservations/reserve",
            200,
            data=reservation_data
        )
        if success and response.get('id'):
            self.reservation_id = response['id']
            self.log(f"✅ Reservation created with ID: {self.reservation_id}, PNR: {response.get('pnr')}")
        else:
            return False

        # List reservations
        success, response = self.run_test(
            "List Reservations",
            "GET",
            "api/reservations",
            200
        )
        if success:
            self.log(f"✅ Found {len(response)} reservations")

        # Get single reservation
        success, response = self.run_test(
            "Get Reservation by ID",
            "GET",
            f"api/reservations/{self.reservation_id}",
            200
        )
        if success:
            self.log(f"✅ Reservation details: Total={response.get('total_price')}, Paid={response.get('paid_amount')}, Due={response.get('due_amount')}")

        # Confirm reservation
        success, response = self.run_test(
            "Confirm Reservation",
            "POST",
            f"api/reservations/{self.reservation_id}/confirm",
            200
        )

        return True

    def test_payments(self):
        """Test payment flow"""
        self.log("\n=== PAYMENTS ===")
        
        if not self.reservation_id:
            self.log("⚠️  Skipping payment tests - no reservation_id")
            return False

        # Add payment
        payment_data = {
            "reservation_id": self.reservation_id,
            "amount": 100.0,
            "method": "cash",
            "notes": "Test payment"
        }
        success, response = self.run_test(
            "Add Payment",
            "POST",
            "api/payments",
            200,
            data=payment_data
        )
        if success:
            self.log(f"✅ Payment added: {response.get('amount')} {response.get('method')}")

        # Verify payment reflected in reservation
        success, response = self.run_test(
            "Verify Payment in Reservation",
            "GET",
            f"api/reservations/{self.reservation_id}",
            200
        )
        if success:
            self.log(f"✅ Updated amounts: Paid={response.get('paid_amount')}, Due={response.get('due_amount')}")

        return True

    def test_voucher(self):
        """Test voucher generation"""
        self.log("\n=== VOUCHER ===")
        
        if not self.reservation_id:
            self.log("⚠️  Skipping voucher test - no reservation_id")
            return False

        # Get voucher HTML
        url = f"{self.base_url}/api/reservations/{self.reservation_id}/voucher"
        headers = {'Authorization': f'Bearer {self.token}'}
        
        self.tests_run += 1
        self.log(f"🔍 Test #{self.tests_run}: Get Voucher HTML")
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200 and 'text/html' in response.headers.get('content-type', ''):
                self.tests_passed += 1
                self.log(f"✅ PASSED - Voucher HTML generated ({len(response.text)} bytes)")
                if 'Voucher' in response.text and 'PNR' in response.text:
                    self.log("✅ Voucher contains expected content")
                return True
            else:
                self.tests_failed += 1
                self.failed_tests.append(f"Voucher - Expected 200 HTML, got {response.status_code}")
                self.log(f"❌ FAILED - Status: {response.status_code}")
                return False
        except Exception as e:
            self.tests_failed += 1
            self.failed_tests.append(f"Voucher - Error: {str(e)}")
            self.log(f"❌ FAILED - Error: {str(e)}")
            return False

    def test_crm_leads(self):
        """Test CRM leads"""
        self.log("\n=== CRM - LEADS ===")
        
        if not self.customer_id:
            self.log("⚠️  Skipping lead tests - no customer_id")
            return False

        # Create lead
        lead_data = {
            "customer_id": self.customer_id,
            "source": "website",
            "status": "new",
            "notes": "Test lead"
        }
        success, response = self.run_test(
            "Create Lead",
            "POST",
            "api/leads",
            200,
            data=lead_data
        )
        if success and response.get('id'):
            self.lead_id = response['id']
            self.log(f"✅ Lead created with ID: {self.lead_id}")
        else:
            return False

        # List leads
        success, response = self.run_test(
            "List Leads",
            "GET",
            "api/leads",
            200
        )
        if success:
            self.log(f"✅ Found {len(response)} leads")

        # Update lead
        lead_data['status'] = 'contacted'
        success, response = self.run_test(
            "Update Lead",
            "PUT",
            f"api/leads/{self.lead_id}",
            200,
            data=lead_data
        )

        return True

    def test_crm_quotes(self):
        """Test CRM quotes"""
        self.log("\n=== CRM - QUOTES ===")
        
        if not self.customer_id or not self.product_id:
            self.log("⚠️  Skipping quote tests - missing customer_id or product_id")
            return False

        # Create quote (single day tour - end_date should be None)
        today = datetime.now().strftime("%Y-%m-%d")
        quote_data = {
            "customer_id": self.customer_id,
            "lead_id": self.lead_id,
            "items": [
                {
                    "product_id": self.product_id,
                    "start_date": today,
                    "end_date": None,
                    "pax": 2,
                    "unit_price": 150.0,
                    "total": 300.0
                }
            ],
            "currency": "TRY",
            "status": "draft"
        }
        success, response = self.run_test(
            "Create Quote",
            "POST",
            "api/quotes",
            200,
            data=quote_data
        )
        if success and response.get('id'):
            self.quote_id = response['id']
            self.log(f"✅ Quote created with ID: {self.quote_id}, Total: {response.get('total')}")
        else:
            return False

        # List quotes
        success, response = self.run_test(
            "List Quotes",
            "GET",
            "api/quotes",
            200
        )
        if success:
            self.log(f"✅ Found {len(response)} quotes")

        # Convert quote to reservation
        convert_data = {
            "quote_id": self.quote_id,
            "idempotency_key": str(uuid.uuid4())
        }
        success, response = self.run_test(
            "Convert Quote to Reservation",
            "POST",
            "api/quotes/convert",
            200,
            data=convert_data
        )
        if success:
            self.log(f"✅ Quote converted to reservation: {response.get('pnr')}")

        return True

    def test_b2b_agencies(self):
        """Test B2B agency management"""
        self.log("\n=== B2B - AGENCIES ===")
        
        # Create agency
        agency_data = {
            "name": f"Test Agency {uuid.uuid4().hex[:8]}",
            "contact_name": "Agency Contact",
            "email": f"agency{uuid.uuid4().hex[:8]}@example.com",
            "phone": "+905559876543"
        }
        success, response = self.run_test(
            "Create Agency",
            "POST",
            "api/b2b/agencies",
            200,
            data=agency_data
        )
        if success and response.get('id'):
            self.agency_id = response['id']
            self.log(f"✅ Agency created with ID: {self.agency_id}")
        else:
            return False

        # List agencies
        success, response = self.run_test(
            "List Agencies",
            "GET",
            "api/b2b/agencies",
            200
        )
        if success:
            self.log(f"✅ Found {len(response)} agencies")

        return True

    def test_b2b_agents(self):
        """Test B2B agent creation"""
        self.log("\n=== B2B - AGENTS ===")
        
        if not self.agency_id:
            self.log("⚠️  Skipping agent tests - no agency_id")
            return False

        # Create agent
        self.agent_email = f"agent{uuid.uuid4().hex[:8]}@example.com"
        agent_data = {
            "email": self.agent_email,
            "name": "Test Agent",
            "password": "agent123",
            "roles": ["b2b_agent"],
            "agency_id": self.agency_id
        }
        success, response = self.run_test(
            "Create B2B Agent",
            "POST",
            "api/b2b/agents",
            200,
            data=agent_data
        )
        if success:
            self.log(f"✅ Agent created: {self.agent_email}")

        return True

    def test_b2b_booking(self):
        """Test B2B booking flow"""
        self.log("\n=== B2B - BOOKING ===")
        
        if not self.agent_email or not self.product_id or not self.customer_id:
            self.log("⚠️  Skipping B2B booking - missing agent_email, product_id, or customer_id")
            return False

        # Login as agent
        success, response = self.run_test(
            "Login as B2B Agent",
            "POST",
            "api/auth/login",
            200,
            data={"email": self.agent_email, "password": "agent123"}
        )
        if not success or 'access_token' not in response:
            return False

        agent_token = response['access_token']
        self.log(f"✅ Agent logged in")

        # Create booking as agent (single day tour - end_date should be None)
        today = datetime.now().strftime("%Y-%m-%d")
        booking_data = {
            "idempotency_key": str(uuid.uuid4()),
            "product_id": self.product_id,
            "customer_id": self.customer_id,
            "start_date": today,
            "end_date": None,
            "pax": 1
        }
        
        url = f"{self.base_url}/api/b2b/book"
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {agent_token}'
        }
        
        self.tests_run += 1
        self.log(f"🔍 Test #{self.tests_run}: Create B2B Booking")
        
        try:
            response = requests.post(url, json=booking_data, headers=headers, timeout=10)
            if response.status_code == 200:
                self.tests_passed += 1
                data = response.json()
                self.log(f"✅ PASSED - B2B booking created: {data.get('pnr')}")
                return True
            else:
                self.tests_failed += 1
                self.failed_tests.append(f"B2B Booking - Expected 200, got {response.status_code}")
                self.log(f"❌ FAILED - Status: {response.status_code}")
                return False
        except Exception as e:
            self.tests_failed += 1
            self.failed_tests.append(f"B2B Booking - Error: {str(e)}")
            self.log(f"❌ FAILED - Error: {str(e)}")
            return False

    def test_reports(self):
        """Test reports endpoints"""
        self.log("\n=== REPORTS ===")
        
        # Reservations summary
        success, response = self.run_test(
            "Reservations Summary",
            "GET",
            "api/reports/reservations-summary",
            200
        )
        if success:
            self.log(f"✅ Summary: {response}")

        # Sales summary
        success, response = self.run_test(
            "Sales Summary",
            "GET",
            "api/reports/sales-summary",
            200
        )
        if success:
            self.log(f"✅ Sales data: {len(response)} days")

        # CSV download
        url = f"{self.base_url}/api/reports/sales-summary.csv"
        headers = {'Authorization': f'Bearer {self.token}'}
        
        self.tests_run += 1
        self.log(f"🔍 Test #{self.tests_run}: Download CSV Report")
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200 and 'text/csv' in response.headers.get('content-type', ''):
                self.tests_passed += 1
                self.log(f"✅ PASSED - CSV downloaded ({len(response.text)} bytes)")
                return True
            else:
                self.tests_failed += 1
                self.failed_tests.append(f"CSV Download - Expected 200 CSV, got {response.status_code}")
                self.log(f"❌ FAILED - Status: {response.status_code}")
                return False
        except Exception as e:
            self.tests_failed += 1
            self.failed_tests.append(f"CSV Download - Error: {str(e)}")
            self.log(f"❌ FAILED - Error: {str(e)}")
            return False

    def test_settings_users(self):
        """Test settings/users management"""
        self.log("\n=== SETTINGS - USERS ===")
        
        # List users
        success, response = self.run_test(
            "List Users",
            "GET",
            "api/settings/users",
            200
        )
        if success:
            self.log(f"✅ Found {len(response)} users")

        # Create user
        user_data = {
            "email": f"user{uuid.uuid4().hex[:8]}@example.com",
            "name": "Test User",
            "password": "user123",
            "roles": ["sales"]
        }
        success, response = self.run_test(
            "Create User",
            "POST",
            "api/settings/users",
            200,
            data=user_data
        )
        if success:
            self.log(f"✅ User created: {response.get('email')}")

        return True

    def test_delete_product(self):
        """Test product deletion (cleanup)"""
        self.log("\n=== CLEANUP - DELETE PRODUCT ===")
        
        if not self.product_id:
            self.log("⚠️  No product to delete")
            return True

        success, response = self.run_test(
            "Delete Product",
            "DELETE",
            f"api/products/{self.product_id}",
            200
        )
        if success:
            self.log(f"✅ Product deleted (also deletes related inventory)")

        return True

    def test_delete_customer(self):
        """Test customer deletion (cleanup)"""
        self.log("\n=== CLEANUP - DELETE CUSTOMER ===")
        
        if not self.customer_id:
            self.log("⚠️  No customer to delete")
            return True

        success, response = self.run_test(
            "Delete Customer",
            "DELETE",
            f"api/customers/{self.customer_id}",
            200
        )
        if success:
            self.log(f"✅ Customer deleted")

        return True

    def print_summary(self):
        """Print test summary"""
        self.log("\n" + "="*60)
        self.log("TEST SUMMARY")
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
        """Run all tests in sequence"""
        self.log("🚀 Starting Acenta Master API Tests")
        self.log(f"Base URL: {self.base_url}")
        
        # Health check
        if not self.test_health():
            self.log("❌ Health check failed - stopping tests")
            self.print_summary()
            return 1

        # Authentication
        if not self.test_login():
            self.log("❌ Login failed - stopping tests")
            self.print_summary()
            return 1

        self.test_me()

        # Core features
        self.test_products_crud()
        self.test_inventory()
        self.test_customers_crud()
        self.test_reservations()
        self.test_payments()
        self.test_voucher()

        # CRM
        self.test_crm_leads()
        self.test_crm_quotes()

        # B2B
        self.test_b2b_agencies()
        self.test_b2b_agents()
        self.test_b2b_booking()

        # Reports
        self.test_reports()

        # Settings
        self.test_settings_users()

        # Cleanup
        self.test_delete_product()
        self.test_delete_customer()

        # Summary
        self.print_summary()

        return 0 if self.tests_failed == 0 else 1


class FAZ5HotelExtranetTester:
    def __init__(self, base_url="https://pms-extranet-app.preview.emergentagent.com"):
        self.base_url = base_url
        self.hotel_token = None
        self.agency_token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.failed_tests = []
        
        # Store created IDs for testing
        self.hotel_id = None
        self.stop_sell_id = None
        self.allocation_id = None
        self.booking_ids = []

    def log(self, msg):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    def run_test(self, name, method, endpoint, expected_status, data=None, headers_override=None, token=None):
        """Run a single API test with specific token"""
        url = f"{self.base_url}/{endpoint}"
        headers = headers_override or {'Content-Type': 'application/json'}
        
        # Use specific token if provided, otherwise use hotel_token
        if token:
            headers['Authorization'] = f'Bearer {token}'
        elif self.hotel_token and not headers_override:
            headers['Authorization'] = f'Bearer {self.hotel_token}'

        self.tests_run += 1
        self.log(f"🔍 Test #{self.tests_run}: {name}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=10)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=10)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=10)
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

    def test_hotel_admin_login(self):
        """A1) Test hotel admin login"""
        self.log("\n=== A) AUTH / CONTEXT ===")
        success, response = self.run_test(
            "Hotel Admin Login",
            "POST",
            "api/auth/login",
            200,
            data={"email": "hoteladmin@acenta.test", "password": "admin123"},
            headers_override={'Content-Type': 'application/json'}
        )
        if success and 'access_token' in response:
            self.hotel_token = response['access_token']
            user = response.get('user', {})
            roles = user.get('roles', [])
            hotel_id = user.get('hotel_id')
            
            if 'hotel_admin' in roles:
                self.log(f"✅ User has hotel_admin role: {roles}")
            else:
                self.log(f"❌ Missing hotel_admin role: {roles}")
                return False
                
            if hotel_id:
                self.hotel_id = hotel_id
                self.log(f"✅ Hotel ID populated: {hotel_id}")
            else:
                self.log(f"❌ Hotel ID missing")
                return False
                
            return True
        return False

    def test_hotel_bookings_list(self):
        """B2) Test hotel bookings endpoint"""
        self.log("\n=== B) HOTEL ENDPOINTS ===")
        success, response = self.run_test(
            "Hotel Bookings List",
            "GET",
            "api/hotel/bookings",
            200
        )
        if success:
            self.log(f"✅ Hotel bookings endpoint working (found {len(response)} bookings)")
        return success

    def test_stop_sell_crud(self):
        """B3) Test stop-sell CRUD operations"""
        self.log("\n--- Stop-sell CRUD ---")
        
        # Create stop-sell
        stop_sell_data = {
            "room_type": "deluxe",
            "start_date": "2026-03-10",
            "end_date": "2026-03-12",
            "reason": "bakım",
            "is_active": True
        }
        success, response = self.run_test(
            "Create Stop-sell",
            "POST",
            "api/hotel/stop-sell",
            200,
            data=stop_sell_data
        )
        if success and response.get('id'):
            self.stop_sell_id = response['id']
            self.log(f"✅ Stop-sell created with ID: {self.stop_sell_id}")
        else:
            return False

        # List stop-sell
        success, response = self.run_test(
            "List Stop-sell",
            "GET",
            "api/hotel/stop-sell",
            200
        )
        if success:
            found = any(item.get('id') == self.stop_sell_id for item in response)
            if found:
                self.log(f"✅ Created stop-sell found in list")
            else:
                self.log(f"❌ Created stop-sell not found in list")
                return False

        # Update stop-sell (toggle is_active)
        stop_sell_data['is_active'] = False
        success, response = self.run_test(
            "Update Stop-sell (toggle active)",
            "PUT",
            f"api/hotel/stop-sell/{self.stop_sell_id}",
            200,
            data=stop_sell_data
        )
        if success:
            self.log(f"✅ Stop-sell updated successfully")

        # Delete stop-sell
        success, response = self.run_test(
            "Delete Stop-sell",
            "DELETE",
            f"api/hotel/stop-sell/{self.stop_sell_id}",
            200
        )
        if success:
            self.log(f"✅ Stop-sell deleted successfully")

        return True

    def test_allocation_crud(self):
        """B4) Test allocation CRUD operations"""
        self.log("\n--- Allocation CRUD ---")
        
        # Create allocation
        allocation_data = {
            "room_type": "standard",
            "start_date": "2026-03-01",
            "end_date": "2026-03-31",
            "allotment": 2,
            "is_active": True,
            "channel": "agency_extranet"
        }
        success, response = self.run_test(
            "Create Allocation",
            "POST",
            "api/hotel/allocations",
            200,
            data=allocation_data
        )
        if success and response.get('id'):
            self.allocation_id = response['id']
            self.log(f"✅ Allocation created with ID: {self.allocation_id}")
        else:
            return False

        # List allocations
        success, response = self.run_test(
            "List Allocations",
            "GET",
            "api/hotel/allocations",
            200
        )
        if success:
            found = any(item.get('id') == self.allocation_id for item in response)
            if found:
                self.log(f"✅ Created allocation found in list")
            else:
                self.log(f"❌ Created allocation not found in list")
                return False

        # Update allocation (toggle is_active)
        allocation_data['is_active'] = False
        success, response = self.run_test(
            "Update Allocation (toggle active)",
            "PUT",
            f"api/hotel/allocations/{self.allocation_id}",
            200,
            data=allocation_data
        )
        if success:
            self.log(f"✅ Allocation updated successfully")

        # Delete allocation
        success, response = self.run_test(
            "Delete Allocation",
            "DELETE",
            f"api/hotel/allocations/{self.allocation_id}",
            200
        )
        if success:
            self.log(f"✅ Allocation deleted successfully")

        return True

    def test_agency_login(self):
        """C5) Test agency login"""
        self.log("\n=== C) SEARCH IMPACT (CRITICAL) ===")
        success, response = self.run_test(
            "Agency Login",
            "POST",
            "api/auth/login",
            200,
            data={"email": "agency1@demo.test", "password": "agency123"},
            headers_override={'Content-Type': 'application/json'}
        )
        if success and 'access_token' in response:
            self.agency_token = response['access_token']
            self.log(f"✅ Agency logged in successfully")
            return True
        return False

    def test_search_with_stop_sell_impact(self):
        """C6) Test search with stop-sell impact"""
        self.log("\n--- Search with Stop-sell Impact ---")
        
        # First, create an active stop-sell for deluxe rooms
        stop_sell_data = {
            "room_type": "deluxe",
            "start_date": "2026-03-10",
            "end_date": "2026-03-12",
            "reason": "bakım",
            "is_active": True
        }
        success, response = self.run_test(
            "Create Stop-sell for Search Test",
            "POST",
            "api/hotel/stop-sell",
            200,
            data=stop_sell_data,
            token=self.hotel_token
        )
        if success:
            stop_sell_id = response.get('id')
            self.log(f"✅ Stop-sell created for search test: {stop_sell_id}")
        
        # Now search as agency
        search_data = {
            "hotel_id": self.hotel_id,
            "check_in": "2026-03-10",
            "check_out": "2026-03-12",
            "occupancy": {"adults": 2, "children": 0}
        }
        success, response = self.run_test(
            "Agency Search with Stop-sell Active",
            "POST",
            "api/agency/search",
            200,
            data=search_data,
            token=self.agency_token
        )
        if success:
            rooms = response.get('rooms', [])
            deluxe_found = any(room.get('room_type_id') == 'rt_deluxe' and room.get('inventory_left', 0) > 0 for room in rooms)
            
            if not deluxe_found:
                self.log(f"✅ Stop-sell working: deluxe rooms not available or inventory_left=0")
            else:
                self.log(f"❌ Stop-sell not working: deluxe rooms still available")
                return False
        
        return success

    def test_allocation_impact_and_bookings(self):
        """C7) Test allocation impact and booking flow"""
        self.log("\n--- Allocation Impact & Booking Flow ---")
        
        # Create allocation for standard rooms
        allocation_data = {
            "room_type": "standard",
            "start_date": "2026-03-01",
            "end_date": "2026-03-31",
            "allotment": 2,
            "is_active": True,
            "channel": "agency_extranet"
        }
        success, response = self.run_test(
            "Create Allocation for Search Test",
            "POST",
            "api/hotel/allocations",
            200,
            data=allocation_data,
            token=self.hotel_token
        )
        if success:
            allocation_id = response.get('id')
            self.log(f"✅ Allocation created for search test: {allocation_id}")
        
        # Search to check allocation limit
        search_data = {
            "hotel_id": self.hotel_id,
            "check_in": "2026-03-15",
            "check_out": "2026-03-17",
            "occupancy": {"adults": 2, "children": 0}
        }
        success, response = self.run_test(
            "Agency Search with Allocation Active",
            "POST",
            "api/agency/search",
            200,
            data=search_data,
            token=self.agency_token
        )
        
        search_id = None
        standard_inventory = 0
        if success:
            search_id = response.get('search_id')
            rooms = response.get('rooms', [])
            for room in rooms:
                if room.get('room_type_id') == 'rt_standard':
                    standard_inventory = room.get('inventory_left', 0)
                    break
            
            if standard_inventory <= 2:
                self.log(f"✅ Allocation working: standard inventory_left={standard_inventory} (≤2)")
            else:
                self.log(f"❌ Allocation not working: standard inventory_left={standard_inventory} (>2)")
        
        # Create 2 bookings to exhaust allocation
        if search_id and standard_inventory > 0:
            for i in range(2):
                # Create draft
                draft_data = {
                    "search_id": search_id,
                    "hotel_id": self.hotel_id,
                    "room_type_id": "rt_standard",
                    "rate_plan_id": "rp_base",
                    "guest": {
                        "full_name": f"Test Guest {i+1}",
                        "email": f"guest{i+1}@test.com",
                        "phone": "+905551234567"
                    },
                    "check_in": "2026-03-15",
                    "check_out": "2026-03-17",
                    "nights": 2,
                    "adults": 2,
                    "children": 0
                }
                
                success, response = self.run_test(
                    f"Create Booking Draft {i+1}",
                    "POST",
                    "api/agency/bookings/draft",
                    200,
                    data=draft_data,
                    token=self.agency_token
                )
                
                if success:
                    draft_id = response.get('id')
                    self.log(f"✅ Draft {i+1} created: {draft_id}")
                    
                    # Confirm booking
                    confirm_data = {"draft_id": draft_id}
                    success, response = self.run_test(
                        f"Confirm Booking {i+1}",
                        "POST",
                        "api/agency/bookings/confirm",
                        200,
                        data=confirm_data,
                        token=self.agency_token
                    )
                    
                    if success:
                        booking_id = response.get('id')
                        self.booking_ids.append(booking_id)
                        self.log(f"✅ Booking {i+1} confirmed: {booking_id}")
            
            # Search again to verify inventory is exhausted
            success, response = self.run_test(
                "Agency Search After 2 Bookings",
                "POST",
                "api/agency/search",
                200,
                data=search_data,
                token=self.agency_token
            )
            
            if success:
                rooms = response.get('rooms', [])
                standard_inventory_after = 0
                for room in rooms:
                    if room.get('room_type_id') == 'rt_standard':
                        standard_inventory_after = room.get('inventory_left', 0)
                        break
                
                if standard_inventory_after == 0:
                    self.log(f"✅ Allocation exhausted: standard inventory_left=0 after 2 bookings")
                else:
                    self.log(f"❌ Allocation not exhausted: standard inventory_left={standard_inventory_after}")
        
        return True

    def test_booking_actions(self):
        """D8-11) Test booking actions"""
        self.log("\n=== D) BOOKING ACTIONS ===")
        
        # List hotel bookings
        success, response = self.run_test(
            "Hotel Admin List Bookings",
            "GET",
            "api/hotel/bookings",
            200,
            token=self.hotel_token
        )
        
        if success:
            bookings = response
            self.log(f"✅ Found {len(bookings)} bookings")
            
            if len(bookings) > 0:
                booking_id = bookings[0].get('id')
                if not booking_id and self.booking_ids:
                    booking_id = self.booking_ids[0]
                
                if booking_id:
                    # Add booking note
                    note_data = {"note": "test not"}
                    success, response = self.run_test(
                        "Add Booking Note",
                        "POST",
                        f"api/hotel/bookings/{booking_id}/note",
                        200,
                        data=note_data,
                        token=self.hotel_token
                    )
                    if success:
                        self.log(f"✅ Booking note added successfully")
                    
                    # Add guest note
                    guest_note_data = {"note": "guest note"}
                    success, response = self.run_test(
                        "Add Guest Note",
                        "POST",
                        f"api/hotel/bookings/{booking_id}/guest-note",
                        200,
                        data=guest_note_data,
                        token=self.hotel_token
                    )
                    if success:
                        self.log(f"✅ Guest note added successfully")
                    
                    # Add cancel request
                    cancel_data = {"reason": "misafir iptal istedi"}
                    success, response = self.run_test(
                        "Add Cancel Request",
                        "POST",
                        f"api/hotel/bookings/{booking_id}/cancel-request",
                        200,
                        data=cancel_data,
                        token=self.hotel_token
                    )
                    if success:
                        self.log(f"✅ Cancel request added successfully")
                else:
                    self.log(f"⚠️  No booking ID available for actions test")
            else:
                self.log(f"⚠️  No bookings found for actions test")
        
        return success

    def print_summary(self):
        """Print test summary"""
        self.log("\n" + "="*60)
        self.log("FAZ-5 HOTEL EXTRANET TEST SUMMARY")
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

    def run_faz5_tests(self):
        """Run all FAZ-5 tests in sequence"""
        self.log("🚀 Starting FAZ-5 Hotel Extranet Tests")
        self.log(f"Base URL: {self.base_url}")
        
        # A) Auth / context
        if not self.test_hotel_admin_login():
            self.log("❌ Hotel admin login failed - stopping tests")
            self.print_summary()
            return 1

        # B) Hotel endpoints
        self.test_hotel_bookings_list()
        self.test_stop_sell_crud()
        self.test_allocation_crud()

        # C) Search impact
        if not self.test_agency_login():
            self.log("❌ Agency login failed - stopping search tests")
        else:
            self.test_search_with_stop_sell_impact()
            self.test_allocation_impact_and_bookings()

        # D) Booking actions
        self.test_booking_actions()

        # Summary
        self.print_summary()

        return 0 if self.tests_failed == 0 else 1


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "faz5":
        tester = FAZ5HotelExtranetTester()
        exit_code = tester.run_faz5_tests()
        sys.exit(exit_code)
    else:
        tester = AcentaAPITester()
        exit_code = tester.run_all_tests()
        sys.exit(exit_code)


if __name__ == "__main__":
    main()
