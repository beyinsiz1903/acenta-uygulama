#!/usr/bin/env python3
"""
Focused test for reservation creation flow with demo seed data
Based on the specific test scenario in the review request
"""
import requests
import sys
from datetime import datetime, timedelta

class ReservationFlowTester:
    def __init__(self, base_url="https://b2b-dashboard-3.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.failed_tests = []
        
        # Store IDs for the flow
        self.product_id = None
        self.customer_id = None
        self.reservation_id = None

    def log(self, msg):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    def run_test(self, name, method, endpoint, expected_status, data=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'

        self.tests_run += 1
        self.log(f"🔍 Test #{self.tests_run}: {name}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=10)
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
                    self.log(f"   Response: {response.text[:300]}")
                except:
                    pass
                return False, {}

        except Exception as e:
            self.tests_failed += 1
            self.failed_tests.append(f"{name} - Error: {str(e)}")
            self.log(f"❌ FAILED - Error: {str(e)}")
            return False, {}

    def test_1_health(self):
        """1) /api/health OK"""
        self.log("\n=== 1. HEALTH CHECK ===")
        success, response = self.run_test(
            "Health Check",
            "GET",
            "api/health",
            200
        )
        if success and response.get('ok'):
            self.log("✅ Database connection OK")
            return True
        else:
            self.log("❌ Health check failed or database not OK")
            return False

    def test_2_login(self):
        """2) admin@acenta.test / admin123 ile login"""
        self.log("\n=== 2. AUTHENTICATION ===")
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
        else:
            self.log("❌ Login failed or no access token received")
            return False

    def test_3_products(self):
        """3) /api/products GET en az 1 ürün dönüyor mu? (demo ürün varsa)"""
        self.log("\n=== 3. PRODUCTS CHECK ===")
        success, response = self.run_test(
            "List Products",
            "GET",
            "api/products",
            200
        )
        if success and isinstance(response, list) and len(response) > 0:
            self.product_id = response[0]['id']
            self.log(f"✅ Found {len(response)} products, using product_id: {self.product_id}")
            self.log(f"   Product: {response[0].get('title', 'N/A')}")
            return True
        else:
            self.log("❌ No products found or invalid response")
            return False

    def test_4_customers(self):
        """4) /api/customers GET en az 1 müşteri dönüyor mu? (demo müşteri varsa)"""
        self.log("\n=== 4. CUSTOMERS CHECK ===")
        success, response = self.run_test(
            "List Customers",
            "GET",
            "api/customers",
            200
        )
        if success and isinstance(response, list) and len(response) > 0:
            self.customer_id = response[0]['id']
            self.log(f"✅ Found {len(response)} customers, using customer_id: {self.customer_id}")
            self.log(f"   Customer: {response[0].get('name', 'N/A')}")
            return True
        else:
            self.log("❌ No customers found or invalid response")
            return False

    def test_5_inventory(self):
        """5) /api/inventory endpoint'ini kullanarak en az birkaç gün kaydı var mı kontrol et"""
        self.log("\n=== 5. INVENTORY CHECK ===")
        
        if not self.product_id:
            self.log("❌ Cannot test inventory - no product_id")
            return False

        # Check inventory for next few days
        today = datetime.now().date()
        start_date = (today + timedelta(days=1)).strftime("%Y-%m-%d")
        end_date = (today + timedelta(days=5)).strftime("%Y-%m-%d")
        
        success, response = self.run_test(
            "List Inventory",
            "GET",
            f"api/inventory?product_id={self.product_id}&start={start_date}&end={end_date}",
            200
        )
        if success and isinstance(response, list) and len(response) > 0:
            self.log(f"✅ Found {len(response)} inventory records for dates {start_date} to {end_date}")
            for inv in response[:3]:  # Show first 3 records
                self.log(f"   Date: {inv.get('date')}, Available: {inv.get('capacity_available')}, Price: {inv.get('price')}")
            return True
        else:
            self.log("❌ No inventory records found")
            return False

    def test_6_create_reservation(self):
        """6) /api/reservations/reserve ile rezervasyon oluştur"""
        self.log("\n=== 6. CREATE RESERVATION ===")
        
        if not self.product_id or not self.customer_id:
            self.log("❌ Cannot create reservation - missing product_id or customer_id")
            return False

        # Create reservation for tomorrow and day after
        today = datetime.now().date()
        start_date = (today + timedelta(days=1)).strftime("%Y-%m-%d")
        end_date = (today + timedelta(days=2)).strftime("%Y-%m-%d")
        
        reservation_data = {
            "idempotency_key": f"test-{datetime.now().timestamp()}",
            "product_id": self.product_id,
            "customer_id": self.customer_id,
            "start_date": start_date,
            "end_date": end_date,
            "pax": 2,
            "channel": "direct"
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
            self.log(f"✅ Reservation created with ID: {self.reservation_id}")
            self.log(f"   PNR: {response.get('pnr')}")
            self.log(f"   Status: {response.get('status')}")
            self.log(f"   Total Price: {response.get('total_price')} {response.get('currency')}")
            return True
        else:
            self.log("❌ Reservation creation failed or no ID returned")
            return False

    def test_7_list_reservations(self):
        """7) /api/reservations listesinde rezervasyon görünüyor mu?"""
        self.log("\n=== 7. LIST RESERVATIONS ===")
        
        success, response = self.run_test(
            "List Reservations",
            "GET",
            "api/reservations",
            200
        )
        if success and isinstance(response, list):
            self.log(f"✅ Found {len(response)} reservations")
            
            # Check if our reservation is in the list
            if self.reservation_id:
                found = any(res.get('id') == self.reservation_id for res in response)
                if found:
                    self.log(f"✅ Our reservation {self.reservation_id} is in the list")
                    return True
                else:
                    self.log(f"❌ Our reservation {self.reservation_id} NOT found in the list")
                    return False
            else:
                # If we don't have a reservation_id, just check if list works
                return True
        else:
            self.log("❌ Failed to get reservations list")
            return False

    def test_8_reservation_detail(self):
        """8) /api/reservations/{id} detay endpoint'i çalışıyor mu ve due_amount hesaplanıyor mu?"""
        self.log("\n=== 8. RESERVATION DETAIL ===")
        
        if not self.reservation_id:
            self.log("❌ Cannot test reservation detail - no reservation_id")
            return False

        success, response = self.run_test(
            "Get Reservation Detail",
            "GET",
            f"api/reservations/{self.reservation_id}",
            200
        )
        if success:
            total_price = response.get('total_price', 0)
            paid_amount = response.get('paid_amount', 0)
            due_amount = response.get('due_amount', 0)
            
            self.log(f"✅ Reservation detail retrieved successfully")
            self.log(f"   Total Price: {total_price}")
            self.log(f"   Paid Amount: {paid_amount}")
            self.log(f"   Due Amount: {due_amount}")
            
            # Check if due_amount is calculated correctly
            expected_due = float(total_price) - float(paid_amount)
            if abs(float(due_amount) - expected_due) < 0.01:  # Allow small floating point differences
                self.log(f"✅ Due amount calculation is correct")
                return True
            else:
                self.log(f"❌ Due amount calculation incorrect. Expected: {expected_due}, Got: {due_amount}")
                return False
        else:
            self.log("❌ Failed to get reservation detail")
            return False

    def print_summary(self):
        """Print test summary"""
        self.log("\n" + "="*60)
        self.log("RESERVATION FLOW TEST SUMMARY")
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

    def run_reservation_flow_tests(self):
        """Run the specific reservation flow tests"""
        self.log("🚀 Starting Reservation Flow Tests")
        self.log(f"Base URL: {self.base_url}")
        
        # Run tests in sequence - each depends on the previous
        tests = [
            self.test_1_health,
            self.test_2_login,
            self.test_3_products,
            self.test_4_customers,
            self.test_5_inventory,
            self.test_6_create_reservation,
            self.test_7_list_reservations,
            self.test_8_reservation_detail
        ]
        
        for test_func in tests:
            if not test_func():
                self.log(f"❌ Critical test failed: {test_func.__name__}")
                break
        
        self.print_summary()
        return 0 if self.tests_failed == 0 else 1


def main():
    tester = ReservationFlowTester()
    exit_code = tester.run_reservation_flow_tests()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()