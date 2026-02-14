#!/usr/bin/env python3
"""
Enhanced Dashboard API Testing Script
Tests the 5 new dashboard endpoints with authentication
"""
import requests
import json
from datetime import datetime

# Configuration
BASE_URL = "https://booking-platform-48.preview.emergentagent.com"
LOGIN_CREDENTIALS = {
    "email": "demo@acenta.test",
    "password": "Demo12345!x"
}

class DashboardTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.session = requests.Session()
        self.access_token = None
        self.test_results = []

    def log_result(self, test_name, success, message, response_data=None):
        """Log test result"""
        result = {
            "test": test_name,
            "success": success,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "response_data": response_data
        }
        self.test_results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {test_name}: {message}")
        return success

    def authenticate(self):
        """Login and get access token"""
        try:
            print("\n🔐 Authenticating...")
            login_url = f"{self.base_url}/api/auth/login"
            
            response = self.session.post(login_url, json=LOGIN_CREDENTIALS)
            
            if response.status_code == 200:
                data = response.json()
                if "access_token" in data:
                    self.access_token = data["access_token"]
                    self.session.headers.update({"Authorization": f"Bearer {self.access_token}"})
                    return self.log_result("Authentication", True, "Successfully logged in and obtained access token")
                else:
                    return self.log_result("Authentication", False, f"No access_token in response: {data}")
            else:
                return self.log_result("Authentication", False, f"Login failed: {response.status_code} - {response.text}")
        except Exception as e:
            return self.log_result("Authentication", False, f"Login exception: {str(e)}")

    def test_kpi_stats(self):
        """Test GET /api/dashboard/kpi-stats"""
        try:
            print("\n📊 Testing KPI Stats endpoint...")
            url = f"{self.base_url}/api/dashboard/kpi-stats"
            
            # Test without auth
            response_no_auth = requests.get(url)
            if response_no_auth.status_code != 401:
                return self.log_result("KPI Stats - Auth Guard", False, f"Expected 401 but got {response_no_auth.status_code}")
            else:
                print("✅ Auth guard working - returns 401 without token")
            
            # Test with auth
            response = self.session.get(url)
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ["total_sales", "total_reservations", "completed_reservations", "conversion_rate", "online_count", "currency"]
                
                missing_fields = [field for field in required_fields if field not in data]
                if missing_fields:
                    return self.log_result("KPI Stats", False, f"Missing required fields: {missing_fields}", data)
                
                # Validate data types
                if not isinstance(data["total_sales"], (int, float)):
                    return self.log_result("KPI Stats", False, f"total_sales should be numeric, got {type(data['total_sales'])}", data)
                
                if not isinstance(data["total_reservations"], int):
                    return self.log_result("KPI Stats", False, f"total_reservations should be int, got {type(data['total_reservations'])}", data)
                
                if not isinstance(data["completed_reservations"], int):
                    return self.log_result("KPI Stats", False, f"completed_reservations should be int, got {type(data['completed_reservations'])}", data)
                
                if not isinstance(data["conversion_rate"], (int, float)):
                    return self.log_result("KPI Stats", False, f"conversion_rate should be numeric, got {type(data['conversion_rate'])}", data)
                
                if not isinstance(data["online_count"], int):
                    return self.log_result("KPI Stats", False, f"online_count should be int, got {type(data['online_count'])}", data)
                
                if data["currency"] != "TRY":
                    return self.log_result("KPI Stats", False, f"currency should be 'TRY', got '{data['currency']}'", data)
                
                return self.log_result("KPI Stats", True, f"All required fields present and valid", data)
            else:
                return self.log_result("KPI Stats", False, f"Request failed: {response.status_code} - {response.text}")
        
        except Exception as e:
            return self.log_result("KPI Stats", False, f"Exception: {str(e)}")

    def test_reservation_widgets(self):
        """Test GET /api/dashboard/reservation-widgets"""
        try:
            print("\n📋 Testing Reservation Widgets endpoint...")
            url = f"{self.base_url}/api/dashboard/reservation-widgets"
            
            # Test without auth
            response_no_auth = requests.get(url)
            if response_no_auth.status_code != 401:
                return self.log_result("Reservation Widgets - Auth Guard", False, f"Expected 401 but got {response_no_auth.status_code}")
            else:
                print("✅ Auth guard working - returns 401 without token")
            
            # Test with auth
            response = self.session.get(url)
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ["completed", "completed_count", "pending", "pending_count", "abandoned", "abandoned_count"]
                
                missing_fields = [field for field in required_fields if field not in data]
                if missing_fields:
                    return self.log_result("Reservation Widgets", False, f"Missing required fields: {missing_fields}", data)
                
                # Validate arrays
                if not isinstance(data["completed"], list):
                    return self.log_result("Reservation Widgets", False, f"completed should be array, got {type(data['completed'])}", data)
                
                if not isinstance(data["pending"], list):
                    return self.log_result("Reservation Widgets", False, f"pending should be array, got {type(data['pending'])}", data)
                
                if not isinstance(data["abandoned"], list):
                    return self.log_result("Reservation Widgets", False, f"abandoned should be array, got {type(data['abandoned'])}", data)
                
                # Validate counts
                if not isinstance(data["completed_count"], int):
                    return self.log_result("Reservation Widgets", False, f"completed_count should be int, got {type(data['completed_count'])}", data)
                
                if not isinstance(data["pending_count"], int):
                    return self.log_result("Reservation Widgets", False, f"pending_count should be int, got {type(data['pending_count'])}", data)
                
                if not isinstance(data["abandoned_count"], int):
                    return self.log_result("Reservation Widgets", False, f"abandoned_count should be int, got {type(data['abandoned_count'])}", data)
                
                return self.log_result("Reservation Widgets", True, f"All required fields present and valid", data)
            else:
                return self.log_result("Reservation Widgets", False, f"Request failed: {response.status_code} - {response.text}")
        
        except Exception as e:
            return self.log_result("Reservation Widgets", False, f"Exception: {str(e)}")

    def test_weekly_summary(self):
        """Test GET /api/dashboard/weekly-summary"""
        try:
            print("\n📅 Testing Weekly Summary endpoint...")
            url = f"{self.base_url}/api/dashboard/weekly-summary"
            
            # Test without auth
            response_no_auth = requests.get(url)
            if response_no_auth.status_code != 401:
                return self.log_result("Weekly Summary - Auth Guard", False, f"Expected 401 but got {response_no_auth.status_code}")
            else:
                print("✅ Auth guard working - returns 401 without token")
            
            # Test with auth
            response = self.session.get(url)
            
            if response.status_code == 200:
                data = response.json()
                
                if not isinstance(data, list):
                    return self.log_result("Weekly Summary", False, f"Response should be array, got {type(data)}", data)
                
                if len(data) != 7:
                    return self.log_result("Weekly Summary", False, f"Should return exactly 7 days, got {len(data)}", data)
                
                # Check each day has required fields
                required_fields = ["date", "day_name", "full_date", "tours", "reservations", "pax", "payments", "is_today"]
                
                for i, day in enumerate(data):
                    missing_fields = [field for field in required_fields if field not in day]
                    if missing_fields:
                        return self.log_result("Weekly Summary", False, f"Day {i} missing fields: {missing_fields}", data)
                
                # Check that exactly one day has is_today=true
                today_count = sum(1 for day in data if day.get("is_today") is True)
                if today_count != 1:
                    return self.log_result("Weekly Summary", False, f"Exactly one day should have is_today=true, found {today_count}", data)
                
                return self.log_result("Weekly Summary", True, f"7 days returned with all required fields, one marked as today", data)
            else:
                return self.log_result("Weekly Summary", False, f"Request failed: {response.status_code} - {response.text}")
        
        except Exception as e:
            return self.log_result("Weekly Summary", False, f"Exception: {str(e)}")

    def test_popular_products(self):
        """Test GET /api/dashboard/popular-products"""
        try:
            print("\n🏆 Testing Popular Products endpoint...")
            url = f"{self.base_url}/api/dashboard/popular-products"
            
            # Test without auth
            response_no_auth = requests.get(url)
            if response_no_auth.status_code != 401:
                return self.log_result("Popular Products - Auth Guard", False, f"Expected 401 but got {response_no_auth.status_code}")
            else:
                print("✅ Auth guard working - returns 401 without token")
            
            # Test with auth
            response = self.session.get(url)
            
            if response.status_code == 200:
                data = response.json()
                
                if not isinstance(data, list):
                    return self.log_result("Popular Products", False, f"Response should be array, got {type(data)}", data)
                
                # Check each product has required fields
                required_fields = ["product_id", "product_name", "image_url", "reservation_count", "view_count", "total_revenue"]
                
                for i, product in enumerate(data):
                    missing_fields = [field for field in required_fields if field not in product]
                    if missing_fields:
                        return self.log_result("Popular Products", False, f"Product {i} missing fields: {missing_fields}", data)
                    
                    # Validate data types
                    if not isinstance(product["reservation_count"], int):
                        return self.log_result("Popular Products", False, f"Product {i} reservation_count should be int", data)
                    
                    if not isinstance(product["view_count"], int):
                        return self.log_result("Popular Products", False, f"Product {i} view_count should be int", data)
                    
                    if not isinstance(product["total_revenue"], (int, float)):
                        return self.log_result("Popular Products", False, f"Product {i} total_revenue should be numeric", data)
                
                return self.log_result("Popular Products", True, f"Array returned with {len(data)} products, all have required fields", data)
            else:
                return self.log_result("Popular Products", False, f"Request failed: {response.status_code} - {response.text}")
        
        except Exception as e:
            return self.log_result("Popular Products", False, f"Exception: {str(e)}")

    def test_recent_customers(self):
        """Test GET /api/dashboard/recent-customers"""
        try:
            print("\n👥 Testing Recent Customers endpoint...")
            url = f"{self.base_url}/api/dashboard/recent-customers"
            
            # Test without auth
            response_no_auth = requests.get(url)
            if response_no_auth.status_code != 401:
                return self.log_result("Recent Customers - Auth Guard", False, f"Expected 401 but got {response_no_auth.status_code}")
            else:
                print("✅ Auth guard working - returns 401 without token")
            
            # Test with auth
            response = self.session.get(url)
            
            if response.status_code == 200:
                data = response.json()
                
                if not isinstance(data, list):
                    return self.log_result("Recent Customers", False, f"Response should be array, got {type(data)}", data)
                
                # Check each customer has required fields
                required_fields = ["id", "name", "email", "created_at"]
                
                for i, customer in enumerate(data):
                    missing_fields = [field for field in required_fields if field not in customer]
                    if missing_fields:
                        return self.log_result("Recent Customers", False, f"Customer {i} missing fields: {missing_fields}", data)
                
                return self.log_result("Recent Customers", True, f"Array returned with {len(data)} customers, all have required fields", data)
            else:
                return self.log_result("Recent Customers", False, f"Request failed: {response.status_code} - {response.text}")
        
        except Exception as e:
            return self.log_result("Recent Customers", False, f"Exception: {str(e)}")

    def run_all_tests(self):
        """Run all dashboard API tests"""
        print("🚀 Starting Enhanced Dashboard API Tests")
        print("=" * 60)
        
        if not self.authenticate():
            print("\n❌ Authentication failed - cannot proceed with other tests")
            return False
        
        # Run all endpoint tests
        tests = [
            self.test_kpi_stats,
            self.test_reservation_widgets,
            self.test_weekly_summary,
            self.test_popular_products,
            self.test_recent_customers
        ]
        
        passed = 0
        total = len(tests)
        
        for test in tests:
            if test():
                passed += 1
        
        # Print summary
        print("\n" + "=" * 60)
        print(f"📋 TEST SUMMARY: {passed}/{total} tests passed")
        
        for result in self.test_results:
            status = "✅" if result["success"] else "❌"
            print(f"{status} {result['test']}: {result['message']}")
        
        return passed == total

if __name__ == "__main__":
    tester = DashboardTester()
    success = tester.run_all_tests()
    exit(0 if success else 1)