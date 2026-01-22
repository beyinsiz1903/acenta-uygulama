#!/usr/bin/env python3
"""
CRM Customers Backend API Smoke Test
Test the newly added CRM Customers backend API endpoints.

Context:
- Stack: FastAPI + MongoDB
- Auth: JWT bearer, existing login endpoint `/api/auth/login` (email: `admin@acenta.test`, password: `admin123`)
- New router: `/api/crm/customers` (list/create/detail/patch)
- Org scope: `organization_id` from token filters DB records by `organization_id` field

Test Requirements:
1) Auth & access controls
2) Create + list
3) Detail endpoint
4) Patch endpoint  
5) Input validation & search
"""

import requests
import json
import sys
from typing import Dict, Any, Optional

# Backend URL from frontend/.env
BASE_URL = "https://acenta-network.preview.emergentagent.com"
API_BASE = f"{BASE_URL}/api"

class CRMCustomersTest:
    def __init__(self):
        self.token: Optional[str] = None
        self.organization_id: Optional[str] = None
        self.created_customer_id: Optional[str] = None
        
    def log(self, message: str):
        print(f"[CRM-TEST] {message}")
        
    def login_admin(self) -> bool:
        """Login as admin user and get JWT token"""
        self.log("🔐 Logging in as admin user...")
        
        login_data = {
            "email": "admin@acenta.test",
            "password": "admin123"
        }
        
        try:
            response = requests.post(f"{API_BASE}/auth/login", json=login_data)
            self.log(f"Login response: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                self.organization_id = data.get("organization_id")
                self.log(f"✅ Login successful - Token: {self.token[:20]}...")
                self.log(f"✅ Organization ID: {self.organization_id}")
                return True
            else:
                self.log(f"❌ Login failed: {response.text}")
                return False
                
        except Exception as e:
            self.log(f"❌ Login error: {e}")
            return False
    
    def get_headers(self) -> Dict[str, str]:
        """Get headers with JWT token"""
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def test_anonymous_access(self) -> bool:
        """Test 1: Anonymous request should return 401"""
        self.log("🧪 Test 1: Anonymous access control...")
        
        try:
            response = requests.get(f"{API_BASE}/crm/customers")
            self.log(f"Anonymous GET /api/crm/customers: {response.status_code}")
            
            if response.status_code == 401:
                self.log("✅ Anonymous request correctly rejected with 401")
                return True
            else:
                self.log(f"❌ Expected 401, got {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log(f"❌ Anonymous access test error: {e}")
            return False
    
    def test_authenticated_list_empty(self) -> bool:
        """Test 2: Authenticated list request should return proper structure"""
        self.log("🧪 Test 2: Authenticated list (empty)...")
        
        try:
            response = requests.get(f"{API_BASE}/crm/customers", headers=self.get_headers())
            self.log(f"Authenticated GET /api/crm/customers: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                self.log(f"Response structure: {json.dumps(data, indent=2)}")
                
                # Check response structure
                required_fields = ["items", "total", "page", "page_size"]
                if all(field in data for field in required_fields):
                    self.log("✅ Response has correct structure")
                    self.log(f"✅ Items: {len(data['items'])}, Total: {data['total']}, Page: {data['page']}, Page size: {data['page_size']}")
                    return True
                else:
                    self.log(f"❌ Missing required fields in response: {data}")
                    return False
            else:
                self.log(f"❌ Expected 200, got {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log(f"❌ Authenticated list test error: {e}")
            return False
    
    def test_create_customer(self) -> bool:
        """Test 3: Create customer with proper data"""
        self.log("🧪 Test 3: Create customer...")
        
        customer_data = {
            "name": "ACME Travel",
            "type": "corporate",
            "tags": ["vip", "istanbul"],
            "contacts": [
                {"type": "email", "value": "ops@acmetravel.test", "is_primary": True},
                {"type": "phone", "value": "+90 555 000 00 00", "is_primary": False}
            ]
        }
        
        try:
            response = requests.post(f"{API_BASE}/crm/customers", 
                                   json=customer_data, 
                                   headers=self.get_headers())
            self.log(f"POST /api/crm/customers: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                self.log(f"Created customer: {json.dumps(data, indent=2)}")
                
                # Check response fields
                checks = [
                    ("id starts with cust_", data.get("id", "").startswith("cust_")),
                    ("organization_id present", bool(data.get("organization_id"))),
                    ("name matches", data.get("name") == "ACME Travel"),
                    ("type matches", data.get("type") == "corporate"),
                    ("tags match", data.get("tags") == ["vip", "istanbul"]),
                    ("contacts match", len(data.get("contacts", [])) == 2),
                    ("no _id field", "_id" not in data)
                ]
                
                all_passed = True
                for check_name, check_result in checks:
                    if check_result:
                        self.log(f"✅ {check_name}")
                    else:
                        self.log(f"❌ {check_name}")
                        all_passed = False
                
                if all_passed:
                    self.created_customer_id = data.get("id")
                    self.log(f"✅ Customer created successfully with ID: {self.created_customer_id}")
                    return True
                else:
                    return False
            else:
                self.log(f"❌ Expected 200, got {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log(f"❌ Create customer test error: {e}")
            return False
    
    def test_list_with_search(self) -> bool:
        """Test 4: List customers with search"""
        self.log("🧪 Test 4: List customers with search...")
        
        try:
            response = requests.get(f"{API_BASE}/crm/customers?search=ACME", 
                                  headers=self.get_headers())
            self.log(f"GET /api/crm/customers?search=ACME: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                self.log(f"Search results: {json.dumps(data, indent=2)}")
                
                checks = [
                    ("items is list", isinstance(data.get("items"), list)),
                    ("total >= 1", data.get("total", 0) >= 1),
                    ("page field present", "page" in data),
                    ("page_size field present", "page_size" in data)
                ]
                
                # Check if ACME Travel is in results
                items = data.get("items", [])
                acme_found = any(item.get("name") == "ACME Travel" for item in items)
                checks.append(("ACME Travel found", acme_found))
                
                all_passed = True
                for check_name, check_result in checks:
                    if check_result:
                        self.log(f"✅ {check_name}")
                    else:
                        self.log(f"❌ {check_name}")
                        all_passed = False
                
                return all_passed
            else:
                self.log(f"❌ Expected 200, got {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log(f"❌ List with search test error: {e}")
            return False
    
    def test_customer_detail(self) -> bool:
        """Test 5: Get customer detail"""
        self.log("🧪 Test 5: Get customer detail...")
        
        if not self.created_customer_id:
            self.log("❌ No customer ID available for detail test")
            return False
        
        try:
            response = requests.get(f"{API_BASE}/crm/customers/{self.created_customer_id}", 
                                  headers=self.get_headers())
            self.log(f"GET /api/crm/customers/{self.created_customer_id}: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                self.log(f"Customer detail: {json.dumps(data, indent=2)}")
                
                checks = [
                    ("customer field present", "customer" in data),
                    ("recent_bookings is list", isinstance(data.get("recent_bookings"), list)),
                    ("open_deals is list", isinstance(data.get("open_deals"), list)),
                    ("open_tasks is list", isinstance(data.get("open_tasks"), list))
                ]
                
                # Check customer data
                customer = data.get("customer", {})
                if customer:
                    checks.extend([
                        ("customer id matches", customer.get("id") == self.created_customer_id),
                        ("customer name present", bool(customer.get("name"))),
                        ("customer contacts present", isinstance(customer.get("contacts"), list)),
                        ("customer tags present", isinstance(customer.get("tags"), list))
                    ])
                
                # Check that lists are empty (backend doesn't populate them yet)
                checks.extend([
                    ("recent_bookings empty", len(data.get("recent_bookings", [])) == 0),
                    ("open_deals empty", len(data.get("open_deals", [])) == 0),
                    ("open_tasks empty", len(data.get("open_tasks", [])) == 0)
                ])
                
                all_passed = True
                for check_name, check_result in checks:
                    if check_result:
                        self.log(f"✅ {check_name}")
                    else:
                        self.log(f"❌ {check_name}")
                        all_passed = False
                
                return all_passed
            else:
                self.log(f"❌ Expected 200, got {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log(f"❌ Customer detail test error: {e}")
            return False
    
    def test_patch_customer(self) -> bool:
        """Test 6: Patch customer"""
        self.log("🧪 Test 6: Patch customer...")
        
        if not self.created_customer_id:
            self.log("❌ No customer ID available for patch test")
            return False
        
        patch_data = {
            "tags": ["vip", "istanbul", "priority"],
            "assigned_user_id": "some-user-id"
        }
        
        try:
            response = requests.patch(f"{API_BASE}/crm/customers/{self.created_customer_id}", 
                                    json=patch_data,
                                    headers=self.get_headers())
            self.log(f"PATCH /api/crm/customers/{self.created_customer_id}: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                self.log(f"Patched customer: {json.dumps(data, indent=2)}")
                
                checks = [
                    ("tags updated", data.get("tags") == ["vip", "istanbul", "priority"]),
                    ("assigned_user_id updated", data.get("assigned_user_id") == "some-user-id"),
                    ("no _id field", "_id" not in data),
                    ("id unchanged", data.get("id") == self.created_customer_id)
                ]
                
                all_passed = True
                for check_name, check_result in checks:
                    if check_result:
                        self.log(f"✅ {check_name}")
                    else:
                        self.log(f"❌ {check_name}")
                        all_passed = False
                
                return all_passed
            else:
                self.log(f"❌ Expected 200, got {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log(f"❌ Patch customer test error: {e}")
            return False
    
    def test_input_validation(self) -> bool:
        """Test 7: Input validation"""
        self.log("🧪 Test 7: Input validation...")
        
        # Test short name
        invalid_data = {
            "name": "A",  # Too short (min_length=2)
            "type": "individual"
        }
        
        try:
            response = requests.post(f"{API_BASE}/crm/customers", 
                                   json=invalid_data, 
                                   headers=self.get_headers())
            self.log(f"POST with short name: {response.status_code}")
            
            if response.status_code == 422:
                self.log("✅ Short name correctly rejected with 422")
                return True
            else:
                self.log(f"❌ Expected 422, got {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log(f"❌ Input validation test error: {e}")
            return False
    
    def test_search_variations(self) -> bool:
        """Test 8: Search variations"""
        self.log("🧪 Test 8: Search variations...")
        
        # Create additional customers for search testing
        customers_to_create = [
            {
                "name": "Istanbul Tours Ltd",
                "type": "corporate",
                "tags": ["vip"],
                "contacts": [{"type": "email", "value": "info@istanbultours.test", "is_primary": True}]
            },
            {
                "name": "Ankara Travel Agency",
                "type": "corporate", 
                "tags": ["priority"],
                "contacts": [{"type": "phone", "value": "+90 312 555 0000", "is_primary": True}]
            }
        ]
        
        created_ids = []
        for customer_data in customers_to_create:
            try:
                response = requests.post(f"{API_BASE}/crm/customers", 
                                       json=customer_data, 
                                       headers=self.get_headers())
                if response.status_code == 200:
                    data = response.json()
                    created_ids.append(data.get("id"))
                    self.log(f"✅ Created test customer: {customer_data['name']}")
                else:
                    self.log(f"⚠️ Failed to create test customer: {response.status_code}")
            except Exception as e:
                self.log(f"⚠️ Error creating test customer: {e}")
        
        # Test email search
        try:
            response = requests.get(f"{API_BASE}/crm/customers?search=@acmetravel.test", 
                                  headers=self.get_headers())
            self.log(f"Email search (@acmetravel.test): {response.status_code}")
            
            email_search_ok = False
            if response.status_code == 200:
                data = response.json()
                items = data.get("items", [])
                # Should find ACME Travel by email
                acme_found = any(item.get("name") == "ACME Travel" for item in items)
                if acme_found:
                    self.log("✅ Email search working - found ACME Travel")
                    email_search_ok = True
                else:
                    self.log("❌ Email search not working - ACME Travel not found")
            else:
                self.log(f"❌ Email search failed: {response.status_code}")
        except Exception as e:
            self.log(f"❌ Email search error: {e}")
        
        # Test tag filter
        try:
            response = requests.get(f"{API_BASE}/crm/customers?tag=vip", 
                                  headers=self.get_headers())
            self.log(f"Tag filter (vip): {response.status_code}")
            
            tag_search_ok = False
            if response.status_code == 200:
                data = response.json()
                items = data.get("items", [])
                # Should find customers with vip tag
                vip_customers = [item for item in items if "vip" in item.get("tags", [])]
                if len(vip_customers) >= 1:
                    self.log(f"✅ Tag filter working - found {len(vip_customers)} VIP customers")
                    tag_search_ok = True
                else:
                    self.log("❌ Tag filter not working - no VIP customers found")
            else:
                self.log(f"❌ Tag filter failed: {response.status_code}")
        except Exception as e:
            self.log(f"❌ Tag filter error: {e}")
        
        return email_search_ok and tag_search_ok
    
    def run_all_tests(self) -> bool:
        """Run all CRM customers tests"""
        self.log("🚀 Starting CRM Customers Backend API Smoke Test")
        self.log(f"Backend URL: {BASE_URL}")
        
        # Login first
        if not self.login_admin():
            self.log("❌ Cannot proceed without authentication")
            return False
        
        tests = [
            ("Anonymous Access Control", self.test_anonymous_access),
            ("Authenticated List (Empty)", self.test_authenticated_list_empty),
            ("Create Customer", self.test_create_customer),
            ("List with Search", self.test_list_with_search),
            ("Customer Detail", self.test_customer_detail),
            ("Patch Customer", self.test_patch_customer),
            ("Input Validation", self.test_input_validation),
            ("Search Variations", self.test_search_variations)
        ]
        
        results = []
        for test_name, test_func in tests:
            self.log(f"\n{'='*60}")
            try:
                result = test_func()
                results.append((test_name, result))
                status = "✅ PASS" if result else "❌ FAIL"
                self.log(f"{status}: {test_name}")
            except Exception as e:
                self.log(f"❌ ERROR in {test_name}: {e}")
                results.append((test_name, False))
        
        # Summary
        self.log(f"\n{'='*60}")
        self.log("📊 TEST SUMMARY")
        self.log(f"{'='*60}")
        
        passed = sum(1 for _, result in results if result)
        total = len(results)
        
        for test_name, result in results:
            status = "✅ PASS" if result else "❌ FAIL"
            self.log(f"{status}: {test_name}")
        
        self.log(f"\n🎯 Results: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
        
        if passed == total:
            self.log("🎉 All tests passed! CRM Customers API is working correctly.")
            return True
        else:
            self.log(f"⚠️ {total-passed} test(s) failed. Please check the issues above.")
            return False

def main():
    """Main test runner"""
    tester = CRMCustomersTest()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()