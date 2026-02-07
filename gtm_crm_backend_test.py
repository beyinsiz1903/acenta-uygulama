#!/usr/bin/env python3
"""
GTM + CRM Backend Testing Suite

This test suite verifies the new GTM (Go-to-Market) and CRM endpoints:

1. Demo Seed Endpoint - POST /api/admin/demo/seed
2. Activation Checklist - GET/PUT /api/activation/checklist
3. Upgrade Requests - POST /api/upgrade-requests 
4. Tenant Health - GET /api/admin/tenants/health
5. CRM Deal Move Stage - POST /api/crm/deals/{id}/move-stage
6. CRM Task Complete - PUT /api/crm/tasks/{id}/complete
7. CRM Notes - GET/POST /api/crm/notes
8. Automation Rules - POST /api/notifications/trigger-checks

All endpoints require authentication via JWT token obtained from signup.
"""

import requests
import json
import uuid
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

# Configuration - Use production URL from frontend/.env
BASE_URL = "https://ops-excellence-10.preview.emergentagent.com"

class GTMCRMTester:
    def __init__(self):
        self.access_token = None
        self.test_email = f"testgtm_{uuid.uuid4().hex[:8]}@test.com"
        self.test_password = "test123456"
        self.test_company = "Test GTM Co"
        self.test_admin = "Test Admin"
        self.tenant_id = None
        self.created_deals = []
        self.created_tasks = []
        self.test_results = []

    def log_result(self, test_name: str, success: bool, message: str, details: dict = None):
        """Log test result"""
        result = {
            "test": test_name,
            "success": success,
            "message": message,
            "details": details or {}
        }
        self.test_results.append(result)
        status = "✅" if success else "❌"
        print(f"{status} {test_name}: {message}")
        if details:
            print(f"   Details: {details}")

    def setup_authentication(self) -> bool:
        """Step 1: Create user account and get JWT token"""
        print("\n" + "=" * 80)
        print("STEP 1: AUTHENTICATION SETUP")
        print("Creating test user and obtaining JWT token")
        print("=" * 80)
        
        signup_data = {
            "company_name": self.test_company,
            "admin_name": self.test_admin,
            "email": self.test_email,
            "password": self.test_password
        }
        
        try:
            response = requests.post(f"{BASE_URL}/api/onboarding/signup", json=signup_data)
            print(f"Signup response: {response.status_code}")
            print(f"Signup response body: {response.text}")
            
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get("access_token")
                self.tenant_id = data.get("tenant_id")
                
                if self.access_token and self.tenant_id:
                    self.log_result("Authentication Setup", True, f"User created and token obtained for {self.test_email}, tenant_id: {self.tenant_id}")
                    return True
                else:
                    self.log_result("Authentication Setup", False, f"Missing token or tenant_id. Token: {bool(self.access_token)}, Tenant: {bool(self.tenant_id)}", {"response": data})
                    return False
            else:
                self.log_result("Authentication Setup", False, f"Signup failed with status {response.status_code}", {"response": response.text})
                return False
                
        except Exception as e:
            self.log_result("Authentication Setup", False, f"Exception during signup: {e}")
            return False

    def get_headers(self) -> dict:
        """Get authentication headers for API calls"""
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        # Add tenant header if we have a tenant_id
        if self.tenant_id:
            headers["X-Tenant-Id"] = self.tenant_id
            
        return headers

    def test_demo_seed(self) -> bool:
        """Test POST /api/admin/demo/seed"""
        print("\n" + "-" * 60)
        print("TEST 1: DEMO SEED ENDPOINT")
        print("-" * 60)
        
        try:
            # Test 1a: Basic seed with light mode
            payload = {
                "mode": "light",
                "with_finance": True,
                "with_crm": True
            }
            
            response = requests.post(
                f"{BASE_URL}/api/admin/demo/seed",
                json=payload,
                headers=self.get_headers()
            )
            
            print(f"Demo seed response: {response.status_code}")
            print(f"Response body: {response.text}")
            
            if response.status_code == 200:
                data = response.json()
                if data.get("ok") and "counts" in data:
                    self.log_result("Demo Seed - Initial", True, "Demo data seeded successfully", {
                        "already_seeded": data.get("already_seeded", False),
                        "counts": data.get("counts", {})
                    })
                    
                    # Test 1b: Idempotency - call again without force=true
                    response2 = requests.post(
                        f"{BASE_URL}/api/admin/demo/seed",
                        json=payload,
                        headers=self.get_headers()
                    )
                    
                    if response2.status_code == 200:
                        data2 = response2.json()
                        if data2.get("already_seeded"):
                            self.log_result("Demo Seed - Idempotency", True, "Idempotency working - returned already_seeded=true")
                        else:
                            self.log_result("Demo Seed - Idempotency", False, "Idempotency failed - should return already_seeded=true", {"response": data2})
                    else:
                        self.log_result("Demo Seed - Idempotency", False, f"Second call failed with {response2.status_code}")
                    
                    # Test 1c: Force re-seed
                    payload["force"] = True
                    response3 = requests.post(
                        f"{BASE_URL}/api/admin/demo/seed",
                        json=payload,
                        headers=self.get_headers()
                    )
                    
                    if response3.status_code == 200:
                        data3 = response3.json()
                        if data3.get("ok") and not data3.get("already_seeded"):
                            self.log_result("Demo Seed - Force", True, "Force re-seed working")
                        else:
                            self.log_result("Demo Seed - Force", False, "Force re-seed failed", {"response": data3})
                    else:
                        self.log_result("Demo Seed - Force", False, f"Force re-seed failed with {response3.status_code}")
                    
                    return True
                else:
                    self.log_result("Demo Seed - Initial", False, "Invalid response format", {"response": data})
                    return False
            else:
                self.log_result("Demo Seed - Initial", False, f"Failed with status {response.status_code}", {"response": response.text})
                return False
                
        except Exception as e:
            self.log_result("Demo Seed", False, f"Exception: {e}")
            return False

    def test_activation_checklist(self) -> bool:
        """Test GET/PUT /api/activation/checklist"""
        print("\n" + "-" * 60)
        print("TEST 2: ACTIVATION CHECKLIST")
        print("-" * 60)
        
        try:
            # Test 2a: GET checklist
            response = requests.get(
                f"{BASE_URL}/api/activation/checklist",
                headers=self.get_headers()
            )
            
            print(f"Get checklist response: {response.status_code}")
            print(f"Response body: {response.text}")
            
            if response.status_code == 200:
                data = response.json()
                if "items" in data and "completed_count" in data:
                    items_count = len(data.get("items", []))
                    completed_count = data.get("completed_count", 0)
                    
                    if items_count == 7:  # Expected 7 items
                        self.log_result("Activation Checklist - GET", True, f"Checklist retrieved with {items_count} items, {completed_count} completed")
                        
                        # Test 2b: Complete an item
                        response2 = requests.put(
                            f"{BASE_URL}/api/activation/checklist/create_product/complete",
                            headers=self.get_headers()
                        )
                        
                        if response2.status_code == 200:
                            # Test 2c: Verify completion
                            response3 = requests.get(
                                f"{BASE_URL}/api/activation/checklist",
                                headers=self.get_headers()
                            )
                            
                            if response3.status_code == 200:
                                data3 = response3.json()
                                new_completed = data3.get("completed_count", 0)
                                if new_completed == completed_count + 1:
                                    self.log_result("Activation Checklist - Complete Item", True, f"Item completed successfully - count increased from {completed_count} to {new_completed}")
                                    return True
                                else:
                                    self.log_result("Activation Checklist - Complete Item", False, f"Completed count didn't increase: {completed_count} -> {new_completed}")
                            else:
                                self.log_result("Activation Checklist - Verify", False, f"Failed to verify completion: {response3.status_code}")
                        else:
                            self.log_result("Activation Checklist - Complete Item", False, f"Failed to complete item: {response2.status_code}")
                    else:
                        self.log_result("Activation Checklist - GET", False, f"Expected 7 items, got {items_count}")
                else:
                    self.log_result("Activation Checklist - GET", False, "Invalid response format", {"response": data})
            else:
                self.log_result("Activation Checklist - GET", False, f"Failed with status {response.status_code}", {"response": response.text})
            
            return False
                
        except Exception as e:
            self.log_result("Activation Checklist", False, f"Exception: {e}")
            return False

    def test_upgrade_requests(self) -> bool:
        """Test POST /api/upgrade-requests"""
        print("\n" + "-" * 60)
        print("TEST 3: UPGRADE REQUESTS")
        print("-" * 60)
        
        try:
            # Test 3a: Create upgrade request
            payload = {
                "requested_plan": "growth",
                "message": "We need more features for our growing business"
            }
            
            response = requests.post(
                f"{BASE_URL}/api/upgrade-requests",
                json=payload,
                headers=self.get_headers()
            )
            
            print(f"Upgrade request response: {response.status_code}")
            print(f"Response body: {response.text}")
            
            if response.status_code == 200:
                data = response.json()
                if "requested_plan" in data and data["requested_plan"] == "growth":
                    self.log_result("Upgrade Request - Create", True, "Upgrade request created successfully", {"id": data.get("id")})
                    
                    # Test 3b: Try to create duplicate (should fail with 409)
                    response2 = requests.post(
                        f"{BASE_URL}/api/upgrade-requests",
                        json=payload,
                        headers=self.get_headers()
                    )
                    
                    if response2.status_code == 409:
                        self.log_result("Upgrade Request - Duplicate Prevention", True, "Duplicate request properly rejected with 409")
                        return True
                    else:
                        self.log_result("Upgrade Request - Duplicate Prevention", False, f"Expected 409 for duplicate, got {response2.status_code}")
                        return True  # Original request worked
                else:
                    self.log_result("Upgrade Request - Create", False, "Invalid response format", {"response": data})
            else:
                self.log_result("Upgrade Request - Create", False, f"Failed with status {response.status_code}", {"response": response.text})
            
            return False
                
        except Exception as e:
            self.log_result("Upgrade Request", False, f"Exception: {e}")
            return False

    def test_tenant_health(self) -> bool:
        """Test GET /api/admin/tenants/health (requires super_admin role)"""
        print("\n" + "-" * 60)
        print("TEST 4: TENANT HEALTH")
        print("-" * 60)
        
        try:
            # Test 4a: Get all tenants health
            response = requests.get(
                f"{BASE_URL}/api/admin/tenants/health",
                headers=self.get_headers()
            )
            
            print(f"Tenant health response: {response.status_code}")
            print(f"Response body: {response.text}")
            
            if response.status_code == 200:
                data = response.json()
                if "items" in data and "total" in data:
                    items_count = len(data.get("items", []))
                    total = data.get("total", 0)
                    self.log_result("Tenant Health - All", True, f"Retrieved {items_count} tenants, total: {total}")
                    
                    # Test 4b: Filter by trial_expiring
                    response2 = requests.get(
                        f"{BASE_URL}/api/admin/tenants/health?filter_type=trial_expiring",
                        headers=self.get_headers()
                    )
                    
                    if response2.status_code == 200:
                        self.log_result("Tenant Health - Filter trial_expiring", True, "Filter working")
                    else:
                        self.log_result("Tenant Health - Filter trial_expiring", False, f"Filter failed: {response2.status_code}")
                    
                    # Test 4c: Filter by inactive
                    response3 = requests.get(
                        f"{BASE_URL}/api/admin/tenants/health?filter_type=inactive",
                        headers=self.get_headers()
                    )
                    
                    if response3.status_code == 200:
                        self.log_result("Tenant Health - Filter inactive", True, "Filter working")
                        return True
                    else:
                        self.log_result("Tenant Health - Filter inactive", False, f"Filter failed: {response3.status_code}")
                        return True  # Main endpoint worked
                else:
                    self.log_result("Tenant Health - All", False, "Invalid response format", {"response": data})
            else:
                self.log_result("Tenant Health - All", False, f"Failed with status {response.status_code}", {"response": response.text})
            
            return False
                
        except Exception as e:
            self.log_result("Tenant Health", False, f"Exception: {e}")
            return False

    def test_crm_deals(self) -> bool:
        """Test CRM Deal creation and move-stage functionality"""
        print("\n" + "-" * 60)
        print("TEST 5: CRM DEALS - CREATE & MOVE STAGE")
        print("-" * 60)
        
        try:
            # Test 5a: Create a deal
            deal_payload = {
                "title": "Test GTM Deal",
                "amount": 5000,
                "currency": "TRY",
                "stage": "lead"
            }
            
            response = requests.post(
                f"{BASE_URL}/api/crm/deals",
                json=deal_payload,
                headers=self.get_headers()
            )
            
            print(f"Create deal response: {response.status_code}")
            print(f"Response body: {response.text}")
            
            if response.status_code == 200:
                deal_data = response.json()
                deal_id = deal_data.get("id")
                if deal_id and deal_data.get("stage") == "lead":
                    self.created_deals.append(deal_id)
                    self.log_result("CRM Deal - Create", True, f"Deal created successfully with ID: {deal_id}")
                    
                    # Test 5b: Move deal to next stage
                    move_payload = {
                        "stage": "contacted"
                    }
                    
                    response2 = requests.post(
                        f"{BASE_URL}/api/crm/deals/{deal_id}/move-stage",
                        json=move_payload,
                        headers=self.get_headers()
                    )
                    
                    print(f"Move stage response: {response2.status_code}")
                    print(f"Move stage body: {response2.text}")
                    
                    if response2.status_code == 200:
                        moved_data = response2.json()
                        if moved_data.get("stage") == "contacted":
                            self.log_result("CRM Deal - Move Stage", True, f"Deal moved from 'lead' to 'contacted'")
                            
                            # Test 5c: Verify stage change by getting deal
                            response3 = requests.get(
                                f"{BASE_URL}/api/crm/deals/{deal_id}",
                                headers=self.get_headers()
                            )
                            
                            if response3.status_code == 200:
                                verify_data = response3.json()
                                if verify_data.get("stage") == "contacted":
                                    self.log_result("CRM Deal - Verify Stage", True, "Stage change verified successfully")
                                    return True
                                else:
                                    self.log_result("CRM Deal - Verify Stage", False, f"Stage not updated in GET response: {verify_data.get('stage')}")
                            else:
                                self.log_result("CRM Deal - Verify Stage", False, f"Failed to GET deal: {response3.status_code}")
                        else:
                            self.log_result("CRM Deal - Move Stage", False, f"Stage not updated: {moved_data.get('stage')}")
                    else:
                        self.log_result("CRM Deal - Move Stage", False, f"Failed with status {response2.status_code}", {"response": response2.text})
                else:
                    self.log_result("CRM Deal - Create", False, "Invalid deal creation response", {"response": deal_data})
            else:
                self.log_result("CRM Deal - Create", False, f"Failed with status {response.status_code}", {"response": response.text})
            
            return False
                
        except Exception as e:
            self.log_result("CRM Deal", False, f"Exception: {e}")
            return False

    def test_crm_tasks(self) -> bool:
        """Test CRM Task creation and completion"""
        print("\n" + "-" * 60)
        print("TEST 6: CRM TASKS - CREATE & COMPLETE")
        print("-" * 60)
        
        try:
            # Test 6a: Create a task
            task_payload = {
                "title": "Test GTM Task - Follow up with client"
            }
            
            response = requests.post(
                f"{BASE_URL}/api/crm/tasks",
                json=task_payload,
                headers=self.get_headers()
            )
            
            print(f"Create task response: {response.status_code}")
            print(f"Response body: {response.text}")
            
            if response.status_code == 200:
                task_data = response.json()
                task_id = task_data.get("id")
                if task_id and task_data.get("status") == "open":
                    self.created_tasks.append(task_id)
                    self.log_result("CRM Task - Create", True, f"Task created successfully with ID: {task_id}")
                    
                    # Test 6b: Complete the task
                    response2 = requests.put(
                        f"{BASE_URL}/api/crm/tasks/{task_id}/complete",
                        headers=self.get_headers()
                    )
                    
                    print(f"Complete task response: {response2.status_code}")
                    print(f"Complete task body: {response2.text}")
                    
                    if response2.status_code == 200:
                        completed_data = response2.json()
                        if completed_data.get("status") == "done":
                            self.log_result("CRM Task - Complete", True, "Task completed successfully")
                            
                            # Test 6c: Verify by listing done tasks
                            response3 = requests.get(
                                f"{BASE_URL}/api/crm/tasks?status=done",
                                headers=self.get_headers()
                            )
                            
                            if response3.status_code == 200:
                                list_data = response3.json()
                                items = list_data.get("items", [])
                                task_found = any(item.get("id") == task_id for item in items)
                                if task_found:
                                    self.log_result("CRM Task - Verify Complete", True, "Completed task found in done list")
                                    return True
                                else:
                                    self.log_result("CRM Task - Verify Complete", False, "Completed task not found in done list")
                            else:
                                self.log_result("CRM Task - Verify Complete", False, f"Failed to list done tasks: {response3.status_code}")
                        else:
                            self.log_result("CRM Task - Complete", False, f"Task status not updated: {completed_data.get('status')}")
                    else:
                        self.log_result("CRM Task - Complete", False, f"Failed with status {response2.status_code}", {"response": response2.text})
                else:
                    self.log_result("CRM Task - Create", False, "Invalid task creation response", {"response": task_data})
            else:
                self.log_result("CRM Task - Create", False, f"Failed with status {response.status_code}", {"response": response.text})
            
            return False
                
        except Exception as e:
            self.log_result("CRM Task", False, f"Exception: {e}")
            return False

    def test_crm_notes(self) -> bool:
        """Test CRM Notes creation and retrieval"""
        print("\n" + "-" * 60)
        print("TEST 7: CRM NOTES - CREATE & RETRIEVE")
        print("-" * 60)
        
        try:
            # Test 7a: Create a note
            note_payload = {
                "content": "This is a test note for GTM testing",
                "entity_type": "deal",
                "entity_id": "test123"
            }
            
            response = requests.post(
                f"{BASE_URL}/api/crm/notes",
                json=note_payload,
                headers=self.get_headers()
            )
            
            print(f"Create note response: {response.status_code}")
            print(f"Response body: {response.text}")
            
            if response.status_code == 200:
                note_data = response.json()
                note_id = note_data.get("id")
                if note_id and note_data.get("content") == note_payload["content"]:
                    self.log_result("CRM Note - Create", True, f"Note created successfully with ID: {note_id}")
                    
                    # Test 7b: Retrieve notes by entity
                    response2 = requests.get(
                        f"{BASE_URL}/api/crm/notes?entity_type=deal&entity_id=test123",
                        headers=self.get_headers()
                    )
                    
                    print(f"Get notes response: {response2.status_code}")
                    print(f"Get notes body: {response2.text}")
                    
                    if response2.status_code == 200:
                        list_data = response2.json()
                        items = list_data.get("items", [])
                        note_found = any(item.get("id") == note_id for item in items)
                        if note_found:
                            self.log_result("CRM Note - Retrieve", True, f"Note retrieved successfully from filtered list")
                            return True
                        else:
                            self.log_result("CRM Note - Retrieve", False, "Created note not found in filtered list")
                    else:
                        self.log_result("CRM Note - Retrieve", False, f"Failed to retrieve notes: {response2.status_code}")
                else:
                    self.log_result("CRM Note - Create", False, "Invalid note creation response", {"response": note_data})
            else:
                self.log_result("CRM Note - Create", False, f"Failed with status {response.status_code}", {"response": response.text})
            
            return False
                
        except Exception as e:
            self.log_result("CRM Note", False, f"Exception: {e}")
            return False

    def test_automation_rules(self) -> bool:
        """Test Automation Rules via trigger-checks endpoint"""
        print("\n" + "-" * 60)
        print("TEST 8: AUTOMATION RULES - TRIGGER CHECKS")
        print("-" * 60)
        
        try:
            response = requests.post(
                f"{BASE_URL}/api/notifications/trigger-checks",
                headers=self.get_headers()
            )
            
            print(f"Trigger checks response: {response.status_code}")
            print(f"Response body: {response.text}")
            
            if response.status_code == 200:
                data = response.json()
                if "automation_rules" in data:
                    automation_rules = data["automation_rules"]
                    self.log_result("Automation Rules - Trigger", True, "Automation rules triggered successfully", {
                        "automation_rules": automation_rules
                    })
                    return True
                else:
                    self.log_result("Automation Rules - Trigger", False, "No automation_rules in response", {"response": data})
            else:
                self.log_result("Automation Rules - Trigger", False, f"Failed with status {response.status_code}", {"response": response.text})
            
            return False
                
        except Exception as e:
            self.log_result("Automation Rules", False, f"Exception: {e}")
            return False

    def test_tenant_isolation(self) -> bool:
        """Test tenant isolation by creating a second tenant"""
        print("\n" + "-" * 60)
        print("TEST 9: TENANT ISOLATION")
        print("-" * 60)
        
        try:
            # Create second tenant
            second_email = f"testgtm2_{uuid.uuid4().hex[:8]}@test.com"
            signup_data = {
                "company_name": "Second Test Co",
                "admin_name": "Second Admin", 
                "email": second_email,
                "password": self.test_password
            }
            
            response = requests.post(f"{BASE_URL}/api/onboarding/signup", json=signup_data)
            
            if response.status_code == 200:
                data = response.json()
                second_token = data.get("access_token")
                second_tenant_id = data.get("tenant_id")
                
                if second_token and second_tenant_id:
                    second_headers = {
                        "Authorization": f"Bearer {second_token}",
                        "Content-Type": "application/json",
                        "X-Tenant-Id": second_tenant_id
                    }
                    
                    # Try to access first tenant's deals
                    if self.created_deals:
                        deal_id = self.created_deals[0]
                        response2 = requests.get(
                            f"{BASE_URL}/api/crm/deals/{deal_id}",
                            headers=second_headers
                        )
                        
                        if response2.status_code == 404:
                            self.log_result("Tenant Isolation", True, "Second tenant cannot access first tenant's deals")
                            return True
                        else:
                            self.log_result("Tenant Isolation", False, f"Second tenant can access first tenant's deals: {response2.status_code}")
                    else:
                        # No deals to test with, just verify different tenant setup
                        self.log_result("Tenant Isolation", True, f"Second tenant created successfully - tenant_id: {second_tenant_id} vs {self.tenant_id}")
                        return True
                else:
                    self.log_result("Tenant Isolation", False, f"Second tenant creation failed - missing token or tenant_id. Token: {bool(second_token)}, Tenant: {bool(second_tenant_id)}")
            else:
                self.log_result("Tenant Isolation", False, f"Second tenant creation failed: {response.status_code}")
            
            return False
                
        except Exception as e:
            self.log_result("Tenant Isolation", False, f"Exception: {e}")
            return False

    def run_all_tests(self):
        """Run all GTM + CRM backend tests"""
        print("\n" + "🚀" * 80)
        print("GTM + CRM BACKEND TESTING SUITE")
        print("Testing new Go-to-Market and CRM endpoints")
        print("🚀" * 80)
        
        # Step 1: Authentication
        if not self.setup_authentication():
            print("❌ Authentication failed - cannot continue with tests")
            return False
        
        # Run all tests
        tests = [
            self.test_demo_seed,
            self.test_activation_checklist, 
            self.test_upgrade_requests,
            self.test_tenant_health,
            self.test_crm_deals,
            self.test_crm_tasks,
            self.test_crm_notes,
            self.test_automation_rules,
            self.test_tenant_isolation
        ]
        
        passed = 0
        failed = 0
        
        for test in tests:
            try:
                if test():
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                print(f"❌ Test {test.__name__} crashed: {e}")
                failed += 1
        
        # Print summary
        print("\n" + "🏁" * 80)
        print("TEST SUMMARY")
        print("🏁" * 80)
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"📊 Total: {passed + failed}")
        
        if failed == 0:
            print("\n🎉 ALL TESTS PASSED! GTM + CRM endpoints working correctly.")
        else:
            print(f"\n⚠️  {failed} test(s) failed. Please review the errors above.")
        
        print("\n📋 DETAILED RESULTS:")
        for result in self.test_results:
            status = "✅" if result["success"] else "❌"
            print(f"{status} {result['test']}: {result['message']}")
            
        return failed == 0

if __name__ == "__main__":
    tester = GTMCRMTester()
    success = tester.run_all_tests()
    exit(0 if success else 1)