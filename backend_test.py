#!/usr/bin/env python3
"""
Backend API Testing for GTM Readiness Pack and CRM Pipeline Deepening
Tests all 8 API groups as specified in the review request
"""

import asyncio
import json
import time
import requests
from datetime import datetime


class GTMBackendTester:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.auth_token = None
        self.user_id = None
        self.org_id = None
        self.tenant_id = None
        
    def log(self, message: str, level: str = "INFO"):
        """Log test messages with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
        
    def signup_new_user(self) -> bool:
        """Sign up a new user and get JWT token"""
        try:
            # Create unique email with timestamp
            timestamp = str(int(time.time()))
            email = f"testgtm_{timestamp}@test.com"
            
            self.log(f"Signing up new user: {email}")
            
            response = self.session.post(f"{self.base_url}/api/onboarding/signup", json={
                "email": email,
                "password": "TestPassword123!",
                "admin_name": "GTM Test User",
                "company_name": f"GTM Test Org {timestamp}",
                "plan": "startup"
            })
            
            if response.status_code in [200, 201]:
                data = response.json()
                self.auth_token = data.get("access_token")
                self.user_id = data.get("user_id") 
                self.org_id = data.get("org_id")
                self.tenant_id = data.get("tenant_id")
                
                # Set auth header for subsequent requests
                self.session.headers.update({
                    'Authorization': f'Bearer {self.auth_token}',
                    'X-Tenant-Id': self.tenant_id
                })
                
                self.log(f"✅ User signup successful: user_id={self.user_id}, org_id={self.org_id}, tenant_id={self.tenant_id}")
                return True
            else:
                self.log(f"❌ User signup failed: {response.status_code} - {response.text}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ User signup error: {str(e)}", "ERROR")
            return False

    def test_demo_seed(self) -> dict:
        """Test Group 1: Demo Seed API"""
        results = {"group": "Demo Seed", "tests": []}
        
        try:
            self.log("🧪 Testing Demo Seed POST /api/admin/demo/seed")
            
            # Test 1: Initial seed request
            response = self.session.post(f"{self.base_url}/api/admin/demo/seed", json={
                "mode": "light",
                "with_finance": True,
                "with_crm": True
            })
            
            test_result = {
                "name": "Initial demo seed",
                "status": "pass" if response.status_code == 200 else "fail",
                "details": f"Status: {response.status_code}"
            }
            
            if response.status_code == 200:
                data = response.json()
                if data.get("ok") and "counts" in data and not data.get("already_seeded"):
                    counts = data["counts"]
                    expected_keys = ["products", "customers", "reservations", "payments", "deals", "tasks"]
                    if all(key in counts for key in expected_keys):
                        test_result["details"] += f" ✅ Counts: {counts}"
                    else:
                        test_result["status"] = "fail"
                        test_result["details"] += f" ❌ Missing counts: {counts}"
                else:
                    test_result["status"] = "fail" 
                    test_result["details"] += f" ❌ Invalid response: {data}"
            else:
                test_result["details"] += f" ❌ Response: {response.text}"
                
            results["tests"].append(test_result)
            
            # Test 2: Idempotency check (without force)
            response2 = self.session.post(f"{self.base_url}/api/admin/demo/seed", json={
                "mode": "light",
                "with_finance": True,
                "with_crm": True
            })
            
            test_result2 = {
                "name": "Idempotency check",
                "status": "pass" if response2.status_code == 200 else "fail",
                "details": f"Status: {response2.status_code}"
            }
            
            if response2.status_code == 200:
                data2 = response2.json()
                if data2.get("already_seeded"):
                    test_result2["details"] += " ✅ Already seeded returned correctly"
                else:
                    test_result2["status"] = "fail"
                    test_result2["details"] += f" ❌ Expected already_seeded=true: {data2}"
            else:
                test_result2["details"] += f" ❌ Response: {response2.text}"
                
            results["tests"].append(test_result2)
            
            # Test 3: Force re-seed
            response3 = self.session.post(f"{self.base_url}/api/admin/demo/seed", json={
                "mode": "light",
                "with_finance": True,
                "with_crm": True,
                "force": True
            })
            
            test_result3 = {
                "name": "Force re-seed",
                "status": "pass" if response3.status_code == 200 else "fail",
                "details": f"Status: {response3.status_code}"
            }
            
            if response3.status_code == 200:
                data3 = response3.json()
                if data3.get("ok") and not data3.get("already_seeded"):
                    test_result3["details"] += " ✅ Force re-seed successful"
                else:
                    test_result3["status"] = "fail"
                    test_result3["details"] += f" ❌ Force failed: {data3}"
            else:
                test_result3["details"] += f" ❌ Response: {response3.text}"
                
            results["tests"].append(test_result3)
            
        except Exception as e:
            results["tests"].append({
                "name": "Demo seed test exception",
                "status": "fail",
                "details": f"Exception: {str(e)}"
            })
            
        return results

    def test_activation_checklist(self) -> dict:
        """Test Group 2: Activation Checklist API"""
        results = {"group": "Activation Checklist", "tests": []}
        
        try:
            self.log("🧪 Testing Activation Checklist GET/PUT /api/activation/checklist")
            
            # Test 1: GET checklist (auto-creates if not exists)
            response = self.session.get(f"{self.base_url}/api/activation/checklist")
            
            test_result = {
                "name": "GET activation checklist",
                "status": "pass" if response.status_code == 200 else "fail",
                "details": f"Status: {response.status_code}"
            }
            
            if response.status_code == 200:
                data = response.json()
                if "items" in data and len(data["items"]) == 7:
                    test_result["details"] += f" ✅ 7 checklist items: {data['completed_count']}/{data['total']}"
                else:
                    test_result["status"] = "fail"
                    test_result["details"] += f" ❌ Invalid checklist: {data}"
            else:
                test_result["details"] += f" ❌ Response: {response.text}"
                
            results["tests"].append(test_result)
            
            # Test 2: PUT complete item
            response2 = self.session.put(f"{self.base_url}/api/activation/checklist/create_product/complete")
            
            test_result2 = {
                "name": "Complete checklist item",
                "status": "pass" if response2.status_code == 200 else "fail",
                "details": f"Status: {response2.status_code}"
            }
            
            if response2.status_code == 200:
                data2 = response2.json()
                if data2.get("ok") and not data2.get("already_completed"):
                    test_result2["details"] += " ✅ Item completed successfully"
                else:
                    test_result2["details"] += f" ℹ️ Already completed: {data2}"
            else:
                test_result2["details"] += f" ❌ Response: {response2.text}"
                
            results["tests"].append(test_result2)
            
            # Test 3: GET again to verify completion
            response3 = self.session.get(f"{self.base_url}/api/activation/checklist")
            
            test_result3 = {
                "name": "Verify checklist completion",
                "status": "pass" if response3.status_code == 200 else "fail",
                "details": f"Status: {response3.status_code}"
            }
            
            if response3.status_code == 200:
                data3 = response3.json()
                if data3.get("completed_count", 0) > 0:
                    test_result3["details"] += f" ✅ Completed count increased: {data3['completed_count']}/{data3['total']}"
                else:
                    test_result3["status"] = "fail"
                    test_result3["details"] += f" ❌ No completion progress: {data3}"
            else:
                test_result3["details"] += f" ❌ Response: {response3.text}"
                
            results["tests"].append(test_result3)
            
        except Exception as e:
            results["tests"].append({
                "name": "Activation checklist exception",
                "status": "fail", 
                "details": f"Exception: {str(e)}"
            })
            
        return results

    def test_upgrade_requests(self) -> dict:
        """Test Group 3: Upgrade Requests API"""
        results = {"group": "Upgrade Requests", "tests": []}
        
        try:
            self.log("🧪 Testing Upgrade Requests POST /api/upgrade-requests")
            
            # Test 1: Create upgrade request
            response = self.session.post(f"{self.base_url}/api/upgrade-requests", json={
                "requested_plan": "growth"
            })
            
            test_result = {
                "name": "Create upgrade request",
                "status": "pass" if response.status_code == 200 else "fail",
                "details": f"Status: {response.status_code}"
            }
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "pending" and data.get("requested_plan") == "growth":
                    test_result["details"] += f" ✅ Request created: {data.get('id')}"
                else:
                    test_result["status"] = "fail"
                    test_result["details"] += f" ❌ Invalid response: {data}"
            else:
                test_result["details"] += f" ❌ Response: {response.text}"
                
            results["tests"].append(test_result)
            
            # Test 2: Try creating another (should get 409)
            response2 = self.session.post(f"{self.base_url}/api/upgrade-requests", json={
                "requested_plan": "enterprise"
            })
            
            test_result2 = {
                "name": "Duplicate request check",
                "status": "pass" if response2.status_code == 409 else "fail",
                "details": f"Status: {response2.status_code}"
            }
            
            if response2.status_code == 409:
                test_result2["details"] += " ✅ Correctly rejected duplicate request"
            else:
                test_result2["details"] += f" ❌ Should be 409, got: {response2.text}"
                
            results["tests"].append(test_result2)
            
            # Test 3: GET upgrade requests list
            response3 = self.session.get(f"{self.base_url}/api/upgrade-requests")
            
            test_result3 = {
                "name": "List upgrade requests",
                "status": "pass" if response3.status_code == 200 else "fail",
                "details": f"Status: {response3.status_code}"
            }
            
            if response3.status_code == 200:
                data3 = response3.json()
                if "items" in data3 and len(data3["items"]) > 0:
                    test_result3["details"] += f" ✅ Found {len(data3['items'])} requests"
                else:
                    test_result3["status"] = "fail"
                    test_result3["details"] += f" ❌ No requests found: {data3}"
            else:
                test_result3["details"] += f" ❌ Response: {response3.text}"
                
            results["tests"].append(test_result3)
            
        except Exception as e:
            results["tests"].append({
                "name": "Upgrade requests exception",
                "status": "fail",
                "details": f"Exception: {str(e)}"
            })
            
        return results

    def test_tenant_health(self) -> dict:
        """Test Group 4: Tenant Health API"""
        results = {"group": "Tenant Health", "tests": []}
        
        try:
            self.log("🧪 Testing Tenant Health GET /api/admin/tenants/health")
            
            # Test 1: GET tenant health (no filter)
            response = self.session.get(f"{self.base_url}/api/admin/tenants/health")
            
            test_result = {
                "name": "GET tenant health",
                "status": "pass" if response.status_code in [200, 403] else "fail",
                "details": f"Status: {response.status_code}"
            }
            
            if response.status_code == 200:
                data = response.json()
                if "items" in data and isinstance(data["items"], list):
                    test_result["details"] += f" ✅ Health data returned: {len(data['items'])} tenants"
                else:
                    test_result["status"] = "fail"
                    test_result["details"] += f" ❌ Invalid response: {data}"
            elif response.status_code == 403:
                test_result["status"] = "pass"  # Expected for non-super-admin
                test_result["details"] += " ℹ️ Access denied (expected for non-super-admin)"
            else:
                test_result["details"] += f" ❌ Response: {response.text}"
                
            results["tests"].append(test_result)
            
            # Test 2: GET with filter_type=trial_expiring
            response2 = self.session.get(f"{self.base_url}/api/admin/tenants/health?filter_type=trial_expiring")
            
            test_result2 = {
                "name": "Filter trial_expiring",
                "status": "pass" if response2.status_code in [200, 403] else "fail",
                "details": f"Status: {response2.status_code}"
            }
            
            if response2.status_code == 200:
                data2 = response2.json()
                test_result2["details"] += f" ✅ Trial expiring filter works"
            elif response2.status_code == 403:
                test_result2["details"] += " ℹ️ Access denied (expected)"
            else:
                test_result2["details"] += f" ❌ Response: {response2.text}"
                
            results["tests"].append(test_result2)
            
            # Test 3: GET with filter_type=inactive
            response3 = self.session.get(f"{self.base_url}/api/admin/tenants/health?filter_type=inactive")
            
            test_result3 = {
                "name": "Filter inactive",
                "status": "pass" if response3.status_code in [200, 403] else "fail",
                "details": f"Status: {response3.status_code}"
            }
            
            if response3.status_code == 200:
                test_result3["details"] += " ✅ Inactive filter works"
            elif response3.status_code == 403:
                test_result3["details"] += " ℹ️ Access denied (expected)"
            else:
                test_result3["details"] += f" ❌ Response: {response3.text}"
                
            results["tests"].append(test_result3)
            
        except Exception as e:
            results["tests"].append({
                "name": "Tenant health exception",
                "status": "fail",
                "details": f"Exception: {str(e)}"
            })
            
        return results

    def test_crm_deal_crud_and_move_stage(self) -> dict:
        """Test Group 5: CRM Deal CRUD + Move-Stage"""
        results = {"group": "CRM Deal CRUD + Move-Stage", "tests": []}
        deal_id = None
        
        try:
            self.log("🧪 Testing CRM Deal CRUD + Move-Stage")
            
            # Test 1: Create deal
            response = self.session.post(f"{self.base_url}/api/crm/deals", json={
                "title": "Test Deal API",
                "amount": 5000,
                "currency": "TRY", 
                "stage": "lead"
            })
            
            test_result = {
                "name": "Create CRM deal",
                "status": "pass" if response.status_code == 200 else "fail",
                "details": f"Status: {response.status_code}"
            }
            
            if response.status_code == 200:
                data = response.json()
                deal_id = data.get("id")
                if deal_id and data.get("stage") == "lead":
                    test_result["details"] += f" ✅ Deal created: {deal_id}"
                else:
                    test_result["status"] = "fail"
                    test_result["details"] += f" ❌ Invalid deal data: {data}"
            else:
                test_result["details"] += f" ❌ Response: {response.text}"
                
            results["tests"].append(test_result)
            
            # Test 2: GET deals list 
            response2 = self.session.get(f"{self.base_url}/api/crm/deals")
            
            test_result2 = {
                "name": "List CRM deals",
                "status": "pass" if response2.status_code == 200 else "fail",
                "details": f"Status: {response2.status_code}"
            }
            
            if response2.status_code == 200:
                data2 = response2.json()
                if "items" in data2 and len(data2["items"]) > 0:
                    test_result2["details"] += f" ✅ Found {len(data2['items'])} deals"
                else:
                    test_result2["details"] += f" ℹ️ No deals found: {data2}"
            else:
                test_result2["details"] += f" ❌ Response: {response2.text}"
                
            results["tests"].append(test_result2)
            
            if deal_id:
                # Test 3: Move stage to "contacted"
                response3 = self.session.post(f"{self.base_url}/api/crm/deals/{deal_id}/move-stage", json={
                    "stage": "contacted"
                })
                
                test_result3 = {
                    "name": "Move stage to contacted",
                    "status": "pass" if response3.status_code == 200 else "fail",
                    "details": f"Status: {response3.status_code}"
                }
                
                if response3.status_code == 200:
                    data3 = response3.json()
                    if data3.get("stage") == "contacted":
                        test_result3["details"] += " ✅ Stage moved to contacted"
                    else:
                        test_result3["status"] = "fail"
                        test_result3["details"] += f" ❌ Stage not updated: {data3}"
                else:
                    test_result3["details"] += f" ❌ Response: {response3.text}"
                    
                results["tests"].append(test_result3)
                
                # Test 4: Move stage to "proposal"
                response4 = self.session.post(f"{self.base_url}/api/crm/deals/{deal_id}/move-stage", json={
                    "stage": "proposal"
                })
                
                test_result4 = {
                    "name": "Move stage to proposal",
                    "status": "pass" if response4.status_code == 200 else "fail",
                    "details": f"Status: {response4.status_code}"
                }
                
                if response4.status_code == 200:
                    data4 = response4.json()
                    if data4.get("stage") == "proposal":
                        test_result4["details"] += " ✅ Stage moved to proposal"
                    else:
                        test_result4["status"] = "fail"
                        test_result4["details"] += f" ❌ Stage not updated: {data4}"
                else:
                    test_result4["details"] += f" ❌ Response: {response4.text}"
                    
                results["tests"].append(test_result4)
                
                # Test 5: Move stage to "won" (should also change status)
                response5 = self.session.post(f"{self.base_url}/api/crm/deals/{deal_id}/move-stage", json={
                    "stage": "won"
                })
                
                test_result5 = {
                    "name": "Move stage to won (status change)",
                    "status": "pass" if response5.status_code == 200 else "fail",
                    "details": f"Status: {response5.status_code}"
                }
                
                if response5.status_code == 200:
                    data5 = response5.json()
                    if data5.get("stage") == "won" and data5.get("status") == "won":
                        test_result5["details"] += " ✅ Stage and status moved to won"
                    else:
                        test_result5["status"] = "fail"
                        test_result5["details"] += f" ❌ Stage/Status not updated: {data5}"
                else:
                    test_result5["details"] += f" ❌ Response: {response5.text}"
                    
                results["tests"].append(test_result5)
            
        except Exception as e:
            results["tests"].append({
                "name": "CRM deal exception",
                "status": "fail",
                "details": f"Exception: {str(e)}"
            })
            
        return results

    def test_crm_task_complete(self) -> dict:
        """Test Group 6: CRM Task Complete"""
        results = {"group": "CRM Task Complete", "tests": []}
        task_id = None
        
        try:
            self.log("🧪 Testing CRM Task Complete")
            
            # Test 1: Create task
            response = self.session.post(f"{self.base_url}/api/crm/tasks", json={
                "title": "Test Task API"
            })
            
            test_result = {
                "name": "Create CRM task",
                "status": "pass" if response.status_code == 200 else "fail",
                "details": f"Status: {response.status_code}"
            }
            
            if response.status_code == 200:
                data = response.json()
                task_id = data.get("id")
                if task_id and data.get("status") == "open":
                    test_result["details"] += f" ✅ Task created: {task_id}"
                else:
                    test_result["status"] = "fail"
                    test_result["details"] += f" ❌ Invalid task data: {data}"
            else:
                test_result["details"] += f" ❌ Response: {response.text}"
                
            results["tests"].append(test_result)
            
            if task_id:
                # Test 2: Complete task
                response2 = self.session.put(f"{self.base_url}/api/crm/tasks/{task_id}/complete")
                
                test_result2 = {
                    "name": "Complete CRM task",
                    "status": "pass" if response2.status_code == 200 else "fail",
                    "details": f"Status: {response2.status_code}"
                }
                
                if response2.status_code == 200:
                    data2 = response2.json()
                    if data2.get("status") == "done":
                        test_result2["details"] += " ✅ Task completed successfully"
                    else:
                        test_result2["status"] = "fail"
                        test_result2["details"] += f" ❌ Task not completed: {data2}"
                else:
                    test_result2["details"] += f" ❌ Response: {response2.text}"
                    
                results["tests"].append(test_result2)
            
        except Exception as e:
            results["tests"].append({
                "name": "CRM task exception",
                "status": "fail",
                "details": f"Exception: {str(e)}"
            })
            
        return results

    def test_crm_notes(self) -> dict:
        """Test Group 7: CRM Notes"""
        results = {"group": "CRM Notes", "tests": []}
        
        try:
            self.log("🧪 Testing CRM Notes")
            
            # Test 1: Create note
            response = self.session.post(f"{self.base_url}/api/crm/notes", json={
                "content": "Test note API content",
                "entity_type": "deal",
                "entity_id": "test-123"
            })
            
            test_result = {
                "name": "Create CRM note", 
                "status": "pass" if response.status_code == 200 else "fail",
                "details": f"Status: {response.status_code}"
            }
            
            if response.status_code == 200:
                data = response.json()
                if data.get("entity_type") == "deal" and data.get("entity_id") == "test-123":
                    test_result["details"] += f" ✅ Note created: {data.get('id')}"
                else:
                    test_result["status"] = "fail"
                    test_result["details"] += f" ❌ Invalid note data: {data}"
            else:
                test_result["details"] += f" ❌ Response: {response.text}"
                
            results["tests"].append(test_result)
            
            # Test 2: GET notes with filters
            response2 = self.session.get(f"{self.base_url}/api/crm/notes?entity_type=deal&entity_id=test-123")
            
            test_result2 = {
                "name": "Get filtered CRM notes",
                "status": "pass" if response2.status_code == 200 else "fail",
                "details": f"Status: {response2.status_code}"
            }
            
            if response2.status_code == 200:
                data2 = response2.json()
                if "items" in data2 and len(data2["items"]) > 0:
                    test_result2["details"] += f" ✅ Found {len(data2['items'])} notes"
                else:
                    test_result2["details"] += f" ℹ️ No notes found: {data2}"
            else:
                test_result2["details"] += f" ❌ Response: {response2.text}"
                
            results["tests"].append(test_result2)
            
        except Exception as e:
            results["tests"].append({
                "name": "CRM notes exception",
                "status": "fail",
                "details": f"Exception: {str(e)}"
            })
            
        return results

    def test_automation_rules(self) -> dict:
        """Test Group 8: Automation Rules (via trigger-checks)"""
        results = {"group": "Automation Rules", "tests": []}
        
        try:
            self.log("🧪 Testing Automation Rules via /api/notifications/trigger-checks")
            
            # Test 1: Trigger notification checks (includes automation rules)
            response = self.session.post(f"{self.base_url}/api/notifications/trigger-checks")
            
            test_result = {
                "name": "Trigger automation rules",
                "status": "pass" if response.status_code == 200 else "fail",
                "details": f"Status: {response.status_code}"
            }
            
            if response.status_code == 200:
                data = response.json()
                if "automation_rules" in data:
                    test_result["details"] += f" ✅ Automation rules executed: {data['automation_rules']}"
                else:
                    test_result["status"] = "fail"
                    test_result["details"] += f" ❌ No automation_rules key: {data}"
            else:
                test_result["details"] += f" ❌ Response: {response.text}"
                
            results["tests"].append(test_result)
            
        except Exception as e:
            results["tests"].append({
                "name": "Automation rules exception",
                "status": "fail",
                "details": f"Exception: {str(e)}"
            })
            
        return results

    def test_tenant_isolation(self) -> dict:
        """Test tenant isolation by signing up a second user"""
        results = {"group": "Tenant Isolation", "tests": []}
        
        try:
            self.log("🧪 Testing Tenant Isolation")
            
            # Save current session
            original_token = self.auth_token
            original_session = self.session.headers.copy()
            
            # Create second user
            timestamp2 = str(int(time.time()) + 1)
            email2 = f"testgtm2_{timestamp2}@test.com"
            
            response = self.session.post(f"{self.base_url}/api/onboarding/signup", json={
                "email": email2,
                "password": "TestPassword123!",
                "admin_name": "GTM Test User 2",
                "company_name": f"GTM Test Org 2 {timestamp2}",
                "plan": "startup"
            })
            
            test_result = {
                "name": "Second user signup",
                "status": "pass" if response.status_code in [200, 201] else "fail",
                "details": f"Status: {response.status_code}"
            }
            
            if response.status_code in [200, 201]:
                data = response.json()
                second_token = data.get("access_token")
                
                # Update session with second user's token
                self.session.headers.update({
                    'Authorization': f'Bearer {second_token}',
                    'X-Tenant-Id': data.get("tenant_id", "")
                })
                
                # Test that second user can't see first user's data
                deals_response = self.session.get(f"{self.base_url}/api/crm/deals")
                
                if deals_response.status_code == 200:
                    deals_data = deals_response.json()
                    if len(deals_data.get("items", [])) == 0:
                        test_result["details"] += " ✅ Tenant isolation works - no cross-tenant data"
                    else:
                        test_result["status"] = "fail"
                        test_result["details"] += f" ❌ Saw other tenant's data: {len(deals_data['items'])} deals"
                else:
                    test_result["details"] += f" ⚠️ Could not test isolation - deals API failed"
            else:
                test_result["details"] += f" ❌ Second user signup failed: {response.text}"
            
            # Restore original session
            self.session.headers.update(original_session)
            self.auth_token = original_token
            
            results["tests"].append(test_result)
            
        except Exception as e:
            results["tests"].append({
                "name": "Tenant isolation exception",
                "status": "fail",
                "details": f"Exception: {str(e)}"
            })
            
        return results

    def run_all_tests(self) -> dict:
        """Run all backend API tests"""
        self.log("🚀 Starting GTM Backend API Testing")
        
        if not self.signup_new_user():
            return {"error": "Failed to create test user"}
        
        all_results = []
        
        # Run all test groups
        test_groups = [
            self.test_demo_seed,
            self.test_activation_checklist, 
            self.test_upgrade_requests,
            self.test_tenant_health,
            self.test_crm_deal_crud_and_move_stage,
            self.test_crm_task_complete,
            self.test_crm_notes,
            self.test_automation_rules,
            self.test_tenant_isolation,
        ]
        
        for test_group in test_groups:
            try:
                result = test_group()
                all_results.append(result)
            except Exception as e:
                all_results.append({
                    "group": test_group.__name__,
                    "tests": [{
                        "name": "Test group exception",
                        "status": "fail",
                        "details": f"Exception: {str(e)}"
                    }]
                })
        
        return {
            "summary": self.generate_summary(all_results),
            "details": all_results
        }

    def generate_summary(self, results: list) -> dict:
        """Generate test summary"""
        total_tests = 0
        passed_tests = 0
        failed_tests = 0
        
        for group in results:
            for test in group.get("tests", []):
                total_tests += 1
                if test["status"] == "pass":
                    passed_tests += 1
                else:
                    failed_tests += 1
        
        return {
            "total_groups": len(results),
            "total_tests": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
            "success_rate": f"{(passed_tests/total_tests)*100:.1f}%" if total_tests > 0 else "0%"
        }


def main():
    """Main test execution"""
    # Get backend URL from environment 
    backend_url = "https://hardening-e1-e4.preview.emergentagent.com"
    
    print(f"🎯 Testing backend at: {backend_url}")
    
    tester = GTMBackendTester(backend_url)
    results = tester.run_all_tests()
    
    print("\n" + "="*80)
    print("📊 TEST RESULTS SUMMARY")
    print("="*80)
    
    if "error" in results:
        print(f"❌ Test execution failed: {results['error']}")
        return
    
    summary = results["summary"]
    print(f"📋 Total Groups: {summary['total_groups']}")
    print(f"📋 Total Tests: {summary['total_tests']}")
    print(f"✅ Passed: {summary['passed']}")
    print(f"❌ Failed: {summary['failed']}")
    print(f"📈 Success Rate: {summary['success_rate']}")
    
    print(f"\n📝 DETAILED RESULTS:")
    print("-" * 80)
    
    for group in results["details"]:
        group_name = group["group"]
        tests = group["tests"]
        group_passed = sum(1 for t in tests if t["status"] == "pass")
        group_total = len(tests)
        
        status_icon = "✅" if group_passed == group_total else "❌"
        print(f"{status_icon} {group_name} ({group_passed}/{group_total})")
        
        for test in tests:
            test_icon = "  ✅" if test["status"] == "pass" else "  ❌"
            print(f"{test_icon} {test['name']}: {test['details']}")
        print()

    # Return overall status
    return summary["failed"] == 0


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)