#!/usr/bin/env python3
"""
Focused test for Lead Kanban drag-drop functionality
Tests sort_index persistence and status updates
"""
import requests
import sys
import uuid
from datetime import datetime

class LeadKanbanTester:
    def __init__(self, base_url="https://booking-platform-48.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.failed_tests = []
        
        # Store created IDs for testing
        self.customer_id = None
        self.lead_ids = []

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
            elif method == 'PATCH':
                response = requests.patch(url, json=data, headers=headers, timeout=10)
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
            self.log("❌ Health check failed")
            return False

    def test_login(self):
        """Test login with seeded admin"""
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
            self.log("❌ Login failed")
            return False

    def test_create_customer(self):
        """Test customer creation or use existing"""
        self.log("\n=== 3. CUSTOMER SETUP ===")
        
        # First try to list existing customers
        success, response = self.run_test(
            "List existing customers",
            "GET",
            "api/customers",
            200
        )
        
        if success and len(response) > 0:
            self.customer_id = response[0]['id']
            self.log(f"✅ Using existing customer: {self.customer_id}")
            return True
        
        # Create new customer if none exist
        customer_data = {
            "name": f"Kanban Test Customer {uuid.uuid4().hex[:8]}",
            "email": f"kanban{uuid.uuid4().hex[:8]}@test.com",
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
            return True
        else:
            self.log("❌ Customer creation failed")
            return False

    def test_create_leads(self):
        """Test creating 2-3 leads with different sources/notes"""
        self.log("\n=== 4. CREATE LEADS ===")
        
        if not self.customer_id:
            self.log("❌ No customer_id available")
            return False

        leads_data = [
            {
                "customer_id": self.customer_id,
                "source": "website",
                "status": "new",
                "notes": "İlk lead - website'den geldi"
            },
            {
                "customer_id": self.customer_id,
                "source": "phone",
                "status": "new", 
                "notes": "İkinci lead - telefon araması"
            },
            {
                "customer_id": self.customer_id,
                "source": "referral",
                "status": "new",
                "notes": "Üçüncü lead - referans"
            }
        ]

        for i, lead_data in enumerate(leads_data, 1):
            success, response = self.run_test(
                f"Create Lead {i}",
                "POST",
                "api/leads",
                200,
                data=lead_data
            )
            if success and response.get('id'):
                lead_id = response['id']
                sort_index = response.get('sort_index')
                self.lead_ids.append(lead_id)
                self.log(f"✅ Lead {i} created - ID: {lead_id}, sort_index: {sort_index}")
                
                # Verify sort_index was auto-set
                if sort_index is None:
                    self.log(f"⚠️  Lead {i} missing sort_index in response")
                    return False
            else:
                self.log(f"❌ Lead {i} creation failed")
                return False

        return len(self.lead_ids) == 3

    def test_leads_list_sorting(self):
        """Test /api/leads list has proper sort_index desc ordering"""
        self.log("\n=== 5. VERIFY LEADS SORTING ===")
        
        success, response = self.run_test(
            "List all leads",
            "GET",
            "api/leads",
            200
        )
        
        if not success:
            self.log("❌ Failed to list leads")
            return False

        if len(response) < 3:
            self.log(f"⚠️  Expected at least 3 leads, got {len(response)}")
            return False

        # Check sort_index descending order
        sort_indices = [lead.get('sort_index') for lead in response if lead.get('sort_index') is not None]
        
        if len(sort_indices) < 2:
            self.log("⚠️  Not enough leads with sort_index to verify sorting")
            return False

        is_sorted_desc = all(sort_indices[i] >= sort_indices[i+1] for i in range(len(sort_indices)-1))
        
        if is_sorted_desc:
            self.log(f"✅ Leads properly sorted by sort_index desc: {sort_indices[:3]}")
            return True
        else:
            self.log(f"❌ Leads NOT sorted by sort_index desc: {sort_indices[:3]}")
            return False

    def test_status_and_sort_update(self):
        """Test moving a lead to different status with sort_index update"""
        self.log("\n=== 6. STATUS + SORT_INDEX UPDATE ===")
        
        if not self.lead_ids:
            self.log("❌ No lead_ids available")
            return False

        # Use the first lead for testing
        lead_id = self.lead_ids[0]
        
        # Update status from 'new' to 'contacted' with high sort_index
        patch_data = {
            "status": "contacted",
            "sort_index": 999999.0  # High value to ensure it appears at top
        }
        
        success, response = self.run_test(
            "Update lead status and sort_index",
            "PATCH",
            f"api/leads/{lead_id}/status",
            200,
            data=patch_data
        )
        
        if not success:
            self.log("❌ Failed to update lead status")
            return False

        # Verify both status and sort_index were updated
        updated_status = response.get('status')
        updated_sort_index = response.get('sort_index')
        
        if updated_status != 'contacted':
            self.log(f"❌ Status not updated correctly: expected 'contacted', got '{updated_status}'")
            return False
            
        if updated_sort_index != 999999.0:
            self.log(f"❌ sort_index not updated correctly: expected 999999.0, got {updated_sort_index}")
            return False

        self.log(f"✅ Lead updated - Status: {updated_status}, sort_index: {updated_sort_index}")
        return True

    def test_contacted_leads_sorting(self):
        """Test that updated lead appears at top in contacted status"""
        self.log("\n=== 7. VERIFY CONTACTED LEADS SORTING ===")
        
        success, response = self.run_test(
            "List contacted leads",
            "GET",
            "api/leads?status=contacted",
            200
        )
        
        if not success:
            self.log("❌ Failed to list contacted leads")
            return False

        if len(response) == 0:
            self.log("❌ No contacted leads found")
            return False

        # Check if our updated lead is at the top
        first_lead = response[0]
        first_lead_id = first_lead.get('id')
        first_lead_sort_index = first_lead.get('sort_index')
        
        if first_lead_id == self.lead_ids[0]:  # Our updated lead
            self.log(f"✅ Updated lead is at top of contacted list - sort_index: {first_lead_sort_index}")
            return True
        else:
            self.log(f"❌ Updated lead not at top. First lead ID: {first_lead_id}, expected: {self.lead_ids[0]}")
            return False

    def print_summary(self):
        """Print test summary"""
        self.log("\n" + "="*60)
        self.log("LEAD KANBAN TEST SUMMARY")
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

    def run_kanban_tests(self):
        """Run focused Kanban tests"""
        self.log("🚀 Starting Lead Kanban Drag-Drop Tests")
        self.log(f"Base URL: {self.base_url}")
        
        # Run tests in sequence
        if not self.test_health():
            self.log("❌ Health check failed - stopping tests")
            self.print_summary()
            return 1

        if not self.test_login():
            self.log("❌ Login failed - stopping tests")
            self.print_summary()
            return 1

        if not self.test_create_customer():
            self.log("❌ Customer setup failed - stopping tests")
            self.print_summary()
            return 1

        if not self.test_create_leads():
            self.log("❌ Lead creation failed - stopping tests")
            self.print_summary()
            return 1

        self.test_leads_list_sorting()
        self.test_status_and_sort_update()
        self.test_contacted_leads_sorting()

        # Summary
        self.print_summary()

        return 0 if self.tests_failed == 0 else 1


def main():
    tester = LeadKanbanTester()
    exit_code = tester.run_kanban_tests()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()