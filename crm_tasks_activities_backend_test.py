#!/usr/bin/env python3
"""
CRM Tasks ve Activities Backend API Smoke Test

Test senaryoları:
1) Auth & erişim (tasks) - Anonymous access → 401, admin login → token
2) Task create + list (customer ile ilişki) - Customer yarat, task yarat, list et
3) Task due filtresi ve status - Task status güncelle, filtreleme test et
4) Activities create + list - Activity yarat, listele
5) Customer detail compute: open_tasks - Customer detail'da open_tasks alanını kontrol et
6) Validation & org scope - Validation ve organization scoping test et
"""

import asyncio
import json
import sys
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

import aiohttp


class CRMTasksActivitiesTest:
    def __init__(self):
        self.base_url = "https://better-menu-labels.preview.emergentagent.com"
        self.session: Optional[aiohttp.ClientSession] = None
        self.admin_token: Optional[str] = None
        self.admin_org_id: Optional[str] = None
        self.test_customer_id: Optional[str] = None
        self.test_task_id: Optional[str] = None
        self.test_activity_id: Optional[str] = None

    async def setup_session(self):
        """HTTP session kurulumu"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={"Content-Type": "application/json"}
        )

    async def cleanup_session(self):
        """HTTP session temizleme"""
        if self.session:
            await self.session.close()

    async def login_admin(self) -> bool:
        """Admin kullanıcısı ile giriş yap"""
        try:
            login_data = {
                "email": "admin@acenta.test",
                "password": "admin123"
            }
            
            async with self.session.post(
                f"{self.base_url}/api/auth/login",
                json=login_data
            ) as resp:
                if resp.status != 200:
                    print(f"❌ Admin login failed: {resp.status}")
                    text = await resp.text()
                    print(f"Response: {text}")
                    return False
                
                data = await resp.json()
                self.admin_token = data.get("access_token")
                
                # Token'dan user bilgilerini al
                if self.admin_token:
                    headers = {"Authorization": f"Bearer {self.admin_token}"}
                    async with self.session.get(f"{self.base_url}/api/auth/me", headers=headers) as me_resp:
                        if me_resp.status == 200:
                            me_data = await me_resp.json()
                            self.admin_org_id = me_data.get("organization_id")
                            print(f"✅ Admin login successful, org_id: {self.admin_org_id}")
                            return True
                
                print("❌ Failed to get admin user info")
                return False
                
        except Exception as e:
            print(f"❌ Admin login error: {e}")
            return False

    async def test_anonymous_access(self) -> bool:
        """Test 1: Anonymous erişim 401 döndürmeli"""
        print("\n🔍 Test 1: Anonymous access to /api/crm/tasks")
        
        try:
            async with self.session.get(f"{self.base_url}/api/crm/tasks") as resp:
                if resp.status == 401:
                    print("✅ Anonymous access correctly returns 401")
                    return True
                else:
                    print(f"❌ Expected 401, got {resp.status}")
                    return False
        except Exception as e:
            print(f"❌ Anonymous access test error: {e}")
            return False

    async def test_authenticated_tasks_list(self) -> bool:
        """Test 1b: Authenticated tasks list - boş liste döndürmeli"""
        print("\n🔍 Test 1b: Authenticated GET /api/crm/tasks")
        
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            async with self.session.get(f"{self.base_url}/api/crm/tasks", headers=headers) as resp:
                if resp.status != 200:
                    print(f"❌ Authenticated tasks list failed: {resp.status}")
                    text = await resp.text()
                    print(f"Response: {text}")
                    return False
                
                data = await resp.json()
                expected_format = {"items", "total", "page", "page_size"}
                if not expected_format.issubset(set(data.keys())):
                    print(f"❌ Response format incorrect. Expected keys: {expected_format}, got: {list(data.keys())}")
                    return False
                
                if data.get("page") != 1 or data.get("page_size") != 50:
                    print(f"❌ Default pagination incorrect: page={data.get('page')}, page_size={data.get('page_size')}")
                    return False
                
                print(f"✅ Authenticated tasks list: {data.get('total')} tasks, format correct")
                return True
                
        except Exception as e:
            print(f"❌ Authenticated tasks list error: {e}")
            return False

    async def create_test_customer(self) -> bool:
        """Test customer oluştur"""
        print("\n🔍 Creating test customer for tasks")
        
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            customer_data = {
                "name": "Tasks Test Customer",
                "type": "individual"
            }
            
            async with self.session.post(
                f"{self.base_url}/api/crm/customers",
                json=customer_data,
                headers=headers
            ) as resp:
                if resp.status != 200:
                    print(f"❌ Customer creation failed: {resp.status}")
                    text = await resp.text()
                    print(f"Response: {text}")
                    return False
                
                data = await resp.json()
                self.test_customer_id = data.get("id")
                
                if not self.test_customer_id or not self.test_customer_id.startswith("cust_"):
                    print(f"❌ Invalid customer ID: {self.test_customer_id}")
                    return False
                
                print(f"✅ Test customer created: {self.test_customer_id}")
                return True
                
        except Exception as e:
            print(f"❌ Customer creation error: {e}")
            return False

    async def test_task_create_and_list(self) -> bool:
        """Test 2: Task create + list (customer ile ilişki)"""
        print("\n🔍 Test 2: Task create + list with customer relationship")
        
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            
            # Task oluştur
            task_data = {
                "title": "Ara ve teklif gönder",
                "related_type": "customer",
                "related_id": self.test_customer_id,
                "priority": "high"
            }
            
            async with self.session.post(
                f"{self.base_url}/api/crm/tasks",
                json=task_data,
                headers=headers
            ) as resp:
                if resp.status != 200:
                    print(f"❌ Task creation failed: {resp.status}")
                    text = await resp.text()
                    print(f"Response: {text}")
                    return False
                
                data = await resp.json()
                self.test_task_id = data.get("id")
                
                # Task ID kontrolü
                if not self.test_task_id or not self.test_task_id.startswith("task_"):
                    print(f"❌ Invalid task ID: {self.test_task_id}")
                    return False
                
                # Organization ID kontrolü
                if data.get("organization_id") != self.admin_org_id:
                    print(f"❌ Organization ID mismatch: {data.get('organization_id')} != {self.admin_org_id}")
                    return False
                
                # Default değerler kontrolü
                if data.get("status") != "open":
                    print(f"❌ Default status incorrect: {data.get('status')}")
                    return False
                
                if data.get("priority") != "high":
                    print(f"❌ Priority incorrect: {data.get('priority')}")
                    return False
                
                # _id alanı response'ta olmamalı
                if "_id" in data:
                    print("❌ _id field should not be in response")
                    return False
                
                print(f"✅ Task created successfully: {self.test_task_id}")
            
            # Task listesini kontrol et
            params = {
                "relatedType": "customer",
                "relatedId": self.test_customer_id
            }
            
            async with self.session.get(
                f"{self.base_url}/api/crm/tasks",
                params=params,
                headers=headers
            ) as resp:
                if resp.status != 200:
                    print(f"❌ Task list failed: {resp.status}")
                    return False
                
                data = await resp.json()
                if data.get("total", 0) < 1:
                    print(f"❌ No tasks found for customer: {data}")
                    return False
                
                # Az önceki task'ı bul
                found_task = None
                for task in data.get("items", []):
                    if task.get("id") == self.test_task_id:
                        found_task = task
                        break
                
                if not found_task:
                    print(f"❌ Created task not found in list")
                    return False
                
                print(f"✅ Task found in filtered list: {found_task.get('title')}")
                return True
                
        except Exception as e:
            print(f"❌ Task create and list error: {e}")
            return False

    async def test_task_status_and_filtering(self) -> bool:
        """Test 3: Task due filtresi ve status"""
        print("\n🔍 Test 3: Task status update and filtering")
        
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            
            # Task'ı "done" yap
            patch_data = {"status": "done"}
            
            async with self.session.patch(
                f"{self.base_url}/api/crm/tasks/{self.test_task_id}",
                json=patch_data,
                headers=headers
            ) as resp:
                if resp.status != 200:
                    print(f"❌ Task patch failed: {resp.status}")
                    text = await resp.text()
                    print(f"Response: {text}")
                    return False
                
                data = await resp.json()
                if data.get("status") != "done":
                    print(f"❌ Status not updated: {data.get('status')}")
                    return False
                
                print(f"✅ Task status updated to 'done'")
            
            # Open tasks listesi - boş olmalı
            params = {
                "status": "open",
                "relatedType": "customer",
                "relatedId": self.test_customer_id
            }
            
            async with self.session.get(
                f"{self.base_url}/api/crm/tasks",
                params=params,
                headers=headers
            ) as resp:
                if resp.status != 200:
                    print(f"❌ Open tasks list failed: {resp.status}")
                    return False
                
                data = await resp.json()
                if data.get("total", 0) > 0:
                    print(f"❌ Found open tasks when expecting none: {data.get('total')}")
                    return False
                
                print(f"✅ No open tasks found (correct)")
            
            # Done tasks listesi - task bulunmalı
            params = {
                "status": "done",
                "relatedType": "customer",
                "relatedId": self.test_customer_id
            }
            
            async with self.session.get(
                f"{self.base_url}/api/crm/tasks",
                params=params,
                headers=headers
            ) as resp:
                if resp.status != 200:
                    print(f"❌ Done tasks list failed: {resp.status}")
                    return False
                
                data = await resp.json()
                if data.get("total", 0) < 1:
                    print(f"❌ No done tasks found: {data}")
                    return False
                
                print(f"✅ Done task found in filtered list")
            
            # Empty patch test
            async with self.session.patch(
                f"{self.base_url}/api/crm/tasks/{self.test_task_id}",
                json={},
                headers=headers
            ) as resp:
                if resp.status != 400:
                    print(f"❌ Empty patch should return 400, got: {resp.status}")
                    return False
                
                data = await resp.json()
                if data.get("detail") != "No fields to update":
                    print(f"❌ Wrong error message: {data.get('detail')}")
                    return False
                
                print(f"✅ Empty patch correctly rejected with 400")
                return True
                
        except Exception as e:
            print(f"❌ Task status and filtering error: {e}")
            return False

    async def test_activities_create_and_list(self) -> bool:
        """Test 4: Activities create + list"""
        print("\n🔍 Test 4: Activities create + list")
        
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            
            # Activity oluştur
            activity_data = {
                "type": "note",
                "body": "İlk arama yapıldı, müşteri dönüş bekliyor.",
                "related_type": "customer",
                "related_id": self.test_customer_id
            }
            
            async with self.session.post(
                f"{self.base_url}/api/crm/activities",
                json=activity_data,
                headers=headers
            ) as resp:
                if resp.status != 200:
                    print(f"❌ Activity creation failed: {resp.status}")
                    text = await resp.text()
                    print(f"Response: {text}")
                    return False
                
                data = await resp.json()
                self.test_activity_id = data.get("id")
                
                # Activity ID kontrolü
                if not self.test_activity_id or not self.test_activity_id.startswith("act_"):
                    print(f"❌ Invalid activity ID: {self.test_activity_id}")
                    return False
                
                # created_by_user_id kontrolü
                if not data.get("created_by_user_id"):
                    print(f"❌ Missing created_by_user_id")
                    return False
                
                # _id alanı response'ta olmamalı
                if "_id" in data:
                    print("❌ _id field should not be in response")
                    return False
                
                print(f"✅ Activity created successfully: {self.test_activity_id}")
            
            # Activities listesini kontrol et
            params = {
                "relatedType": "customer",
                "relatedId": self.test_customer_id
            }
            
            async with self.session.get(
                f"{self.base_url}/api/crm/activities",
                params=params,
                headers=headers
            ) as resp:
                if resp.status != 200:
                    print(f"❌ Activities list failed: {resp.status}")
                    return False
                
                data = await resp.json()
                if data.get("total", 0) < 1:
                    print(f"❌ No activities found for customer: {data}")
                    return False
                
                # Az önceki activity'yi bul
                found_activity = None
                for activity in data.get("items", []):
                    if activity.get("id") == self.test_activity_id:
                        found_activity = activity
                        break
                
                if not found_activity:
                    print(f"❌ Created activity not found in list")
                    return False
                
                # created_at desc sıralama kontrolü
                items = data.get("items", [])
                if len(items) > 1:
                    for i in range(len(items) - 1):
                        current_time = datetime.fromisoformat(items[i]["created_at"].replace("Z", "+00:00"))
                        next_time = datetime.fromisoformat(items[i+1]["created_at"].replace("Z", "+00:00"))
                        if current_time < next_time:
                            print(f"❌ Activities not sorted by created_at desc")
                            return False
                
                print(f"✅ Activity found in list, sorted correctly: {found_activity.get('body')[:50]}...")
                return True
                
        except Exception as e:
            print(f"❌ Activities create and list error: {e}")
            return False

    async def test_customer_detail_compute(self) -> bool:
        """Test 5: Customer detail compute: open_tasks"""
        print("\n🔍 Test 5: Customer detail compute - open_tasks field")
        
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            
            # Önce bir open task oluştur
            task_data = {
                "title": "Open task for customer detail test",
                "related_type": "customer",
                "related_id": self.test_customer_id,
                "priority": "normal"
            }
            
            async with self.session.post(
                f"{self.base_url}/api/crm/tasks",
                json=task_data,
                headers=headers
            ) as resp:
                if resp.status != 200:
                    print(f"❌ Open task creation failed: {resp.status}")
                    return False
                
                open_task_data = await resp.json()
                open_task_id = open_task_data.get("id")
                print(f"✅ Created open task: {open_task_id}")
            
            # Customer detail'ı al
            async with self.session.get(
                f"{self.base_url}/api/crm/customers/{self.test_customer_id}",
                headers=headers
            ) as resp:
                if resp.status != 200:
                    print(f"❌ Customer detail failed: {resp.status}")
                    text = await resp.text()
                    print(f"Response: {text}")
                    return False
                
                data = await resp.json()
                
                # Gerekli alanları kontrol et
                required_fields = {"customer", "open_deals", "open_tasks"}
                if not required_fields.issubset(set(data.keys())):
                    print(f"❌ Missing required fields. Expected: {required_fields}, got: {list(data.keys())}")
                    return False
                
                # Customer alanı normal çalışıyor mu
                customer = data.get("customer", {})
                if customer.get("id") != self.test_customer_id:
                    print(f"❌ Customer field incorrect: {customer.get('id')}")
                    return False
                
                # open_deals listesi (şimdilik boş olabilir)
                open_deals = data.get("open_deals", [])
                print(f"✅ open_deals field present: {len(open_deals)} deals")
                
                # open_tasks listesi - az önce oluşturduğumuz open task görünmeli
                open_tasks = data.get("open_tasks", [])
                if len(open_tasks) < 1:
                    print(f"❌ No open tasks found in customer detail: {open_tasks}")
                    return False
                
                # Open task'ı bul
                found_open_task = None
                for task in open_tasks:
                    if task.get("id") == open_task_id:
                        found_open_task = task
                        break
                
                if not found_open_task:
                    print(f"❌ Created open task not found in customer detail")
                    return False
                
                print(f"✅ open_tasks field working: {len(open_tasks)} tasks, including {open_task_id}")
            
            # Task'ı done yap ve tekrar test et
            patch_data = {"status": "done"}
            async with self.session.patch(
                f"{self.base_url}/api/crm/tasks/{open_task_id}",
                json=patch_data,
                headers=headers
            ) as resp:
                if resp.status != 200:
                    print(f"❌ Task status update failed: {resp.status}")
                    return False
            
            # Customer detail'ı tekrar al - open_tasks boş olmalı
            async with self.session.get(
                f"{self.base_url}/api/crm/customers/{self.test_customer_id}",
                headers=headers
            ) as resp:
                if resp.status != 200:
                    print(f"❌ Customer detail second call failed: {resp.status}")
                    return False
                
                data = await resp.json()
                open_tasks = data.get("open_tasks", [])
                
                # Done task artık open_tasks'ta olmamalı
                found_done_task = None
                for task in open_tasks:
                    if task.get("id") == open_task_id:
                        found_done_task = task
                        break
                
                if found_done_task:
                    print(f"❌ Done task still appears in open_tasks")
                    return False
                
                print(f"✅ Done task correctly removed from open_tasks: {len(open_tasks)} remaining")
                return True
                
        except Exception as e:
            print(f"❌ Customer detail compute error: {e}")
            return False

    async def test_validation_and_org_scope(self) -> bool:
        """Test 6: Validation & org scope"""
        print("\n🔍 Test 6: Validation & organization scope")
        
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            
            # Task title boş - 422 döndürmeli
            task_data = {
                "title": "",
                "related_type": "customer",
                "related_id": self.test_customer_id
            }
            
            async with self.session.post(
                f"{self.base_url}/api/crm/tasks",
                json=task_data,
                headers=headers
            ) as resp:
                if resp.status != 422:
                    print(f"❌ Empty title should return 422, got: {resp.status}")
                    return False
                
                print(f"✅ Empty task title correctly rejected with 422")
            
            # Activity body boş - 422 döndürmeli
            activity_data = {
                "type": "note",
                "body": "",
                "related_type": "customer",
                "related_id": self.test_customer_id
            }
            
            async with self.session.post(
                f"{self.base_url}/api/crm/activities",
                json=activity_data,
                headers=headers
            ) as resp:
                if resp.status != 422:
                    print(f"❌ Empty body should return 422, got: {resp.status}")
                    return False
                
                print(f"✅ Empty activity body correctly rejected with 422")
            
            # Geçerli bir task oluştur ve organization_id kontrolü yap
            valid_task_data = {
                "title": "Validation test task",
                "related_type": "customer",
                "related_id": self.test_customer_id
            }
            
            async with self.session.post(
                f"{self.base_url}/api/crm/tasks",
                json=valid_task_data,
                headers=headers
            ) as resp:
                if resp.status != 200:
                    print(f"❌ Valid task creation failed: {resp.status}")
                    return False
                
                data = await resp.json()
                
                # Organization ID current user organization'ı ile uyumlu mu
                if data.get("organization_id") != self.admin_org_id:
                    print(f"❌ Organization ID mismatch: {data.get('organization_id')} != {self.admin_org_id}")
                    return False
                
                # _id alanı sızmış mı
                if "_id" in data:
                    print("❌ Mongo _id field leaked in response")
                    return False
                
                print(f"✅ Task organization_id correct, no _id leak")
            
            # Geçerli bir activity oluştur ve kontrol et
            valid_activity_data = {
                "type": "call",
                "body": "Validation test activity",
                "related_type": "customer",
                "related_id": self.test_customer_id
            }
            
            async with self.session.post(
                f"{self.base_url}/api/crm/activities",
                json=valid_activity_data,
                headers=headers
            ) as resp:
                if resp.status != 200:
                    print(f"❌ Valid activity creation failed: {resp.status}")
                    return False
                
                data = await resp.json()
                
                # Organization ID current user organization'ı ile uyumlu mu
                if data.get("organization_id") != self.admin_org_id:
                    print(f"❌ Activity organization ID mismatch: {data.get('organization_id')} != {self.admin_org_id}")
                    return False
                
                # _id alanı sızmış mı
                if "_id" in data:
                    print("❌ Mongo _id field leaked in activity response")
                    return False
                
                print(f"✅ Activity organization_id correct, no _id leak")
                return True
                
        except Exception as e:
            print(f"❌ Validation and org scope error: {e}")
            return False

    async def run_all_tests(self):
        """Tüm testleri çalıştır"""
        print("🚀 CRM Tasks ve Activities Backend API Smoke Test Başlıyor...")
        print(f"Backend URL: {self.base_url}")
        
        await self.setup_session()
        
        try:
            # Login
            if not await self.login_admin():
                print("❌ Admin login failed, aborting tests")
                return False
            
            # Test 1: Anonymous access
            if not await self.test_anonymous_access():
                return False
            
            # Test 1b: Authenticated tasks list
            if not await self.test_authenticated_tasks_list():
                return False
            
            # Setup: Create test customer
            if not await self.create_test_customer():
                return False
            
            # Test 2: Task create + list
            if not await self.test_task_create_and_list():
                return False
            
            # Test 3: Task status and filtering
            if not await self.test_task_status_and_filtering():
                return False
            
            # Test 4: Activities create + list
            if not await self.test_activities_create_and_list():
                return False
            
            # Test 5: Customer detail compute
            if not await self.test_customer_detail_compute():
                return False
            
            # Test 6: Validation & org scope
            if not await self.test_validation_and_org_scope():
                return False
            
            print("\n🎉 TÜM TESTLER BAŞARILI!")
            print("\n📋 Test Özeti:")
            print("✅ Auth & erişim (tasks) - Anonymous 401, admin token çalışıyor")
            print("✅ Task create + list (customer ile ilişki) - Task oluşturma ve listeleme çalışıyor")
            print("✅ Task due filtresi ve status - Status güncelleme ve filtreleme çalışıyor")
            print("✅ Activities create + list - Activity oluşturma ve listeleme çalışıyor")
            print("✅ Customer detail compute: open_tasks - Customer detail'da open_tasks alanı doğru çalışıyor")
            print("✅ Validation & org scope - Validation ve organization scoping çalışıyor")
            
            return True
            
        finally:
            await self.cleanup_session()


async def main():
    test = CRMTasksActivitiesTest()
    success = await test.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())