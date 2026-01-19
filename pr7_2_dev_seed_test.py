#!/usr/bin/env python3
"""
PR#7.2 Dev Seed Backend Test
Test script to verify dev_seed.py created all expected data in MongoDB collections.
"""

import asyncio
import os
import sys
from typing import Any, Dict, List, Optional

import requests
from motor.motor_asyncio import AsyncIOMotorClient

# Add backend to path for imports
sys.path.append('/app/backend')
from app.db import get_db


class DevSeedTester:
    def __init__(self):
        self.backend_url = "https://finspine.preview.emergentagent.com/api"
        self.db = None
        self.org_id = "695e03c80b04ed31c4eaa899"  # Admin user's organization (moved seed data here)
        self.test_results = {
            "customers": {"passed": 0, "failed": 0, "details": []},
            "bookings": {"passed": 0, "failed": 0, "details": []},
            "crm_deals": {"passed": 0, "failed": 0, "details": []},
            "crm_tasks": {"passed": 0, "failed": 0, "details": []},
            "api_tests": {"passed": 0, "failed": 0, "details": []},
        }

    async def setup_db(self):
        """Initialize database connection"""
        try:
            self.db = await get_db()
            print(f"✅ Connected to MongoDB database: {self.db.name}")
            return True
        except Exception as e:
            print(f"❌ Failed to connect to database: {e}")
            return False

    async def test_customers_collection(self):
        """Test customers collection for seeded data"""
        print("\n🔍 Testing customers collection...")
        
        try:
            # Check for cust_seed_linked
            linked_customer = await self.db.customers.find_one({
                "organization_id": self.org_id,
                "id": "cust_seed_linked"
            })
            
            if linked_customer:
                print("✅ Found cust_seed_linked customer")
                print(f"   Name: {linked_customer.get('name')}")
                print(f"   Type: {linked_customer.get('type')}")
                print(f"   Tags: {linked_customer.get('tags')}")
                print(f"   Contacts: {len(linked_customer.get('contacts', []))} contacts")
                self.test_results["customers"]["passed"] += 1
                self.test_results["customers"]["details"].append("✅ cust_seed_linked found with correct data")
            else:
                print("❌ cust_seed_linked customer NOT found")
                self.test_results["customers"]["failed"] += 1
                self.test_results["customers"]["details"].append("❌ cust_seed_linked customer missing")

            # Check for cust_seed_unlinked
            unlinked_customer = await self.db.customers.find_one({
                "organization_id": self.org_id,
                "id": "cust_seed_unlinked"
            })
            
            if unlinked_customer:
                print("✅ Found cust_seed_unlinked customer")
                print(f"   Name: {unlinked_customer.get('name')}")
                print(f"   Type: {unlinked_customer.get('type')}")
                print(f"   Tags: {unlinked_customer.get('tags')}")
                print(f"   Contacts: {len(unlinked_customer.get('contacts', []))} contacts")
                self.test_results["customers"]["passed"] += 1
                self.test_results["customers"]["details"].append("✅ cust_seed_unlinked found with correct data")
            else:
                print("❌ cust_seed_unlinked customer NOT found")
                self.test_results["customers"]["failed"] += 1
                self.test_results["customers"]["details"].append("❌ cust_seed_unlinked customer missing")

            # Count total customers for this org
            total_customers = await self.db.customers.count_documents({"organization_id": self.org_id})
            print(f"📊 Total customers in organization: {total_customers}")

        except Exception as e:
            print(f"❌ Error testing customers collection: {e}")
            self.test_results["customers"]["failed"] += 1
            self.test_results["customers"]["details"].append(f"❌ Error: {e}")

    async def test_bookings_collection(self):
        """Test bookings collection for seeded data"""
        print("\n🔍 Testing bookings collection...")
        
        try:
            # Check for BKG-SEED-LINKED (should have customer_id)
            linked_booking = await self.db.bookings.find_one({
                "organization_id": self.org_id,
                "booking_id": "BKG-SEED-LINKED"
            })
            
            if linked_booking:
                customer_id = linked_booking.get("customer_id")
                print("✅ Found BKG-SEED-LINKED booking")
                print(f"   Customer ID: {customer_id}")
                print(f"   Status: {linked_booking.get('status')}")
                print(f"   Currency: {linked_booking.get('currency')}")
                print(f"   Amount: {linked_booking.get('amounts', {}).get('sell')}")
                
                if customer_id == "cust_seed_linked":
                    print("✅ BKG-SEED-LINKED correctly linked to cust_seed_linked")
                    self.test_results["bookings"]["passed"] += 1
                    self.test_results["bookings"]["details"].append("✅ BKG-SEED-LINKED found with correct customer_id")
                else:
                    print(f"❌ BKG-SEED-LINKED has wrong customer_id: {customer_id}")
                    self.test_results["bookings"]["failed"] += 1
                    self.test_results["bookings"]["details"].append(f"❌ BKG-SEED-LINKED has wrong customer_id: {customer_id}")
            else:
                print("❌ BKG-SEED-LINKED booking NOT found")
                self.test_results["bookings"]["failed"] += 1
                self.test_results["bookings"]["details"].append("❌ BKG-SEED-LINKED booking missing")

            # Check for BKG-SEED-UNLINKED (should NOT have customer_id)
            unlinked_booking = await self.db.bookings.find_one({
                "organization_id": self.org_id,
                "booking_id": "BKG-SEED-UNLINKED"
            })
            
            if unlinked_booking:
                customer_id = unlinked_booking.get("customer_id")
                print("✅ Found BKG-SEED-UNLINKED booking")
                print(f"   Customer ID: {customer_id}")
                print(f"   Status: {unlinked_booking.get('status')}")
                print(f"   Currency: {unlinked_booking.get('currency')}")
                print(f"   Amount: {unlinked_booking.get('amounts', {}).get('sell')}")
                
                if customer_id is None:
                    print("✅ BKG-SEED-UNLINKED correctly has no customer_id (None)")
                    self.test_results["bookings"]["passed"] += 1
                    self.test_results["bookings"]["details"].append("✅ BKG-SEED-UNLINKED found with no customer_id (correct)")
                else:
                    print(f"❌ BKG-SEED-UNLINKED should have no customer_id but has: {customer_id}")
                    self.test_results["bookings"]["failed"] += 1
                    self.test_results["bookings"]["details"].append(f"❌ BKG-SEED-UNLINKED has customer_id when it shouldn't: {customer_id}")
            else:
                print("❌ BKG-SEED-UNLINKED booking NOT found")
                self.test_results["bookings"]["failed"] += 1
                self.test_results["bookings"]["details"].append("❌ BKG-SEED-UNLINKED booking missing")

            # Count total bookings for this org
            total_bookings = await self.db.bookings.count_documents({"organization_id": self.org_id})
            print(f"📊 Total bookings in organization: {total_bookings}")

        except Exception as e:
            print(f"❌ Error testing bookings collection: {e}")
            self.test_results["bookings"]["failed"] += 1
            self.test_results["bookings"]["details"].append(f"❌ Error: {e}")

    async def test_crm_deals_collection(self):
        """Test crm_deals collection for seeded data"""
        print("\n🔍 Testing crm_deals collection...")
        
        try:
            # Check for deal_seed_1
            deal = await self.db.crm_deals.find_one({
                "organization_id": self.org_id,
                "id": "deal_seed_1"
            })
            
            if deal:
                customer_id = deal.get("customer_id")
                print("✅ Found deal_seed_1")
                print(f"   Title: {deal.get('title')}")
                print(f"   Customer ID: {customer_id}")
                print(f"   Stage: {deal.get('stage')}")
                print(f"   Status: {deal.get('status')}")
                print(f"   Amount: {deal.get('amount')} {deal.get('currency')}")
                print(f"   Owner: {deal.get('owner_user_id')}")
                
                if customer_id == "cust_seed_linked":
                    print("✅ deal_seed_1 correctly linked to cust_seed_linked")
                    self.test_results["crm_deals"]["passed"] += 1
                    self.test_results["crm_deals"]["details"].append("✅ deal_seed_1 found with correct customer_id")
                else:
                    print(f"❌ deal_seed_1 has wrong customer_id: {customer_id}")
                    self.test_results["crm_deals"]["failed"] += 1
                    self.test_results["crm_deals"]["details"].append(f"❌ deal_seed_1 has wrong customer_id: {customer_id}")
            else:
                print("❌ deal_seed_1 NOT found")
                self.test_results["crm_deals"]["failed"] += 1
                self.test_results["crm_deals"]["details"].append("❌ deal_seed_1 missing")

            # Count total deals for this org
            total_deals = await self.db.crm_deals.count_documents({"organization_id": self.org_id})
            print(f"📊 Total deals in organization: {total_deals}")

        except Exception as e:
            print(f"❌ Error testing crm_deals collection: {e}")
            self.test_results["crm_deals"]["failed"] += 1
            self.test_results["crm_deals"]["details"].append(f"❌ Error: {e}")

    async def test_crm_tasks_collection(self):
        """Test crm_tasks collection for seeded data"""
        print("\n🔍 Testing crm_tasks collection...")
        
        try:
            # Check for task_seed_1
            task = await self.db.crm_tasks.find_one({
                "organization_id": self.org_id,
                "id": "task_seed_1"
            })
            
            if task:
                related_id = task.get("related_id")
                print("✅ Found task_seed_1")
                print(f"   Title: {task.get('title')}")
                print(f"   Related ID: {related_id}")
                print(f"   Related Type: {task.get('related_type')}")
                print(f"   Status: {task.get('status')}")
                print(f"   Priority: {task.get('priority')}")
                print(f"   Owner: {task.get('owner_user_id')}")
                
                if related_id == "cust_seed_linked":
                    print("✅ task_seed_1 correctly linked to cust_seed_linked")
                    self.test_results["crm_tasks"]["passed"] += 1
                    self.test_results["crm_tasks"]["details"].append("✅ task_seed_1 found with correct related_id")
                else:
                    print(f"❌ task_seed_1 has wrong related_id: {related_id}")
                    self.test_results["crm_tasks"]["failed"] += 1
                    self.test_results["crm_tasks"]["details"].append(f"❌ task_seed_1 has wrong related_id: {related_id}")
            else:
                print("❌ task_seed_1 NOT found")
                self.test_results["crm_tasks"]["failed"] += 1
                self.test_results["crm_tasks"]["details"].append("❌ task_seed_1 missing")

            # Count total tasks for this org
            total_tasks = await self.db.crm_tasks.count_documents({"organization_id": self.org_id})
            print(f"📊 Total tasks in organization: {total_tasks}")

        except Exception as e:
            print(f"❌ Error testing crm_tasks collection: {e}")
            self.test_results["crm_tasks"]["failed"] += 1
            self.test_results["crm_tasks"]["details"].append(f"❌ Error: {e}")

    def get_auth_token(self):
        """Try to get authentication token"""
        try:
            login_data = {
                "email": "admin@acenta.test",
                "password": "admin123"
            }
            
            response = requests.post(f"{self.backend_url}/auth/login", json=login_data, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                token = data.get("access_token")
                if token:
                    print("✅ Successfully obtained auth token")
                    return token
                else:
                    print("❌ Login response missing access_token")
                    return None
            else:
                print(f"❌ Login failed with status {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Error during login: {e}")
            return None

    def test_api_endpoints(self):
        """Test HTTP API endpoints for seeded data"""
        print("\n🔍 Testing HTTP API endpoints...")
        
        token = self.get_auth_token()
        if not token:
            print("❌ Cannot test APIs without authentication token")
            self.test_results["api_tests"]["failed"] += 1
            self.test_results["api_tests"]["details"].append("❌ Authentication failed - cannot test APIs")
            return

        headers = {"Authorization": f"Bearer {token}"}

        try:
            # Test 1: GET /api/crm/customers?search=seed
            print("\n📡 Testing GET /api/crm/customers?search=seed")
            response = requests.get(f"{self.backend_url}/crm/customers?search=seed", headers=headers, timeout=10)
            
            if response.status_code == 200:
                customers = response.json()
                customer_count = len(customers) if isinstance(customers, list) else customers.get('total', 0)
                print(f"✅ API returned {customer_count} customers with 'seed' search")
                
                if customer_count >= 2:
                    print("✅ Found expected 2+ seed customers via API")
                    self.test_results["api_tests"]["passed"] += 1
                    self.test_results["api_tests"]["details"].append("✅ GET /api/crm/customers?search=seed returned 2+ customers")
                else:
                    print(f"❌ Expected 2+ customers, got {customer_count}")
                    self.test_results["api_tests"]["failed"] += 1
                    self.test_results["api_tests"]["details"].append(f"❌ GET /api/crm/customers?search=seed returned {customer_count} customers, expected 2+")
            else:
                print(f"❌ API call failed with status {response.status_code}: {response.text}")
                self.test_results["api_tests"]["failed"] += 1
                self.test_results["api_tests"]["details"].append(f"❌ GET /api/crm/customers?search=seed failed: {response.status_code}")

            # Test 2: GET /api/api/ops/bookings?page_size=5 (note: double API prefix due to router configuration)
            print("\n📡 Testing GET /api/api/ops/bookings?page_size=5")
            response = requests.get(f"{self.backend_url}/api/ops/bookings?page_size=5", headers=headers, timeout=10)
            
            if response.status_code == 200:
                bookings_data = response.json()
                bookings = bookings_data if isinstance(bookings_data, list) else bookings_data.get('items', [])
                booking_ids = [b.get('booking_id') for b in bookings if isinstance(b, dict)]
                
                print(f"✅ API returned {len(bookings)} bookings")
                print(f"   Booking IDs: {booking_ids}")
                
                found_linked = "BKG-SEED-LINKED" in booking_ids
                found_unlinked = "BKG-SEED-UNLINKED" in booking_ids
                
                if found_linked and found_unlinked:
                    print("✅ Found both BKG-SEED-LINKED and BKG-SEED-UNLINKED via API")
                    self.test_results["api_tests"]["passed"] += 1
                    self.test_results["api_tests"]["details"].append("✅ GET /api/api/ops/bookings found both seed bookings")
                else:
                    print(f"❌ Missing seed bookings - Linked: {found_linked}, Unlinked: {found_unlinked}")
                    self.test_results["api_tests"]["failed"] += 1
                    self.test_results["api_tests"]["details"].append(f"❌ GET /api/api/ops/bookings missing seed bookings - Linked: {found_linked}, Unlinked: {found_unlinked}")
            else:
                print(f"❌ API call failed with status {response.status_code}: {response.text}")
                self.test_results["api_tests"]["failed"] += 1
                self.test_results["api_tests"]["details"].append(f"❌ GET /api/api/ops/bookings failed: {response.status_code}")

            # Test 3: GET /api/crm/customers/cust_seed_linked
            print("\n📡 Testing GET /api/crm/customers/cust_seed_linked")
            response = requests.get(f"{self.backend_url}/crm/customers/cust_seed_linked", headers=headers, timeout=10)
            
            if response.status_code == 200:
                customer_detail = response.json()
                print("✅ Successfully retrieved cust_seed_linked details")
                
                recent_bookings = customer_detail.get("recent_bookings", [])
                open_deals = customer_detail.get("open_deals", [])
                open_tasks = customer_detail.get("open_tasks", [])
                
                print(f"   Recent bookings: {len(recent_bookings)}")
                print(f"   Open deals: {len(open_deals)}")
                print(f"   Open tasks: {len(open_tasks)}")
                
                # Check if BKG-SEED-LINKED is in recent_bookings
                booking_ids_in_recent = [b.get('booking_id') for b in recent_bookings if isinstance(b, dict)]
                has_linked_booking = "BKG-SEED-LINKED" in booking_ids_in_recent
                
                # Check if seed deal and task are present
                deal_ids = [d.get('id') for d in open_deals if isinstance(d, dict)]
                task_ids = [t.get('id') for t in open_tasks if isinstance(t, dict)]
                
                has_seed_deal = "deal_seed_1" in deal_ids
                has_seed_task = "task_seed_1" in task_ids
                
                success_count = sum([has_linked_booking, has_seed_deal, has_seed_task])
                
                if success_count == 3:
                    print("✅ Customer detail contains all expected seed data")
                    self.test_results["api_tests"]["passed"] += 1
                    self.test_results["api_tests"]["details"].append("✅ GET /api/crm/customers/cust_seed_linked contains all seed data")
                else:
                    print(f"❌ Customer detail missing some seed data - Booking: {has_linked_booking}, Deal: {has_seed_deal}, Task: {has_seed_task}")
                    self.test_results["api_tests"]["failed"] += 1
                    self.test_results["api_tests"]["details"].append(f"❌ Customer detail missing seed data - Booking: {has_linked_booking}, Deal: {has_seed_deal}, Task: {has_seed_task}")
            else:
                print(f"❌ API call failed with status {response.status_code}: {response.text}")
                self.test_results["api_tests"]["failed"] += 1
                self.test_results["api_tests"]["details"].append(f"❌ GET /api/crm/customers/cust_seed_linked failed: {response.status_code}")

        except Exception as e:
            print(f"❌ Error during API testing: {e}")
            self.test_results["api_tests"]["failed"] += 1
            self.test_results["api_tests"]["details"].append(f"❌ API testing error: {e}")

    def print_summary(self):
        """Print comprehensive test summary"""
        print("\n" + "="*80)
        print("📋 PR#7.2 DEV SEED TEST SUMMARY")
        print("="*80)
        
        total_passed = 0
        total_failed = 0
        
        for category, results in self.test_results.items():
            passed = results["passed"]
            failed = results["failed"]
            total_passed += passed
            total_failed += failed
            
            status = "✅ PASS" if failed == 0 else "❌ FAIL" if passed == 0 else "⚠️ PARTIAL"
            print(f"\n{category.upper().replace('_', ' ')}: {status}")
            print(f"  Passed: {passed}, Failed: {failed}")
            
            for detail in results["details"]:
                print(f"  {detail}")
        
        print(f"\n🎯 OVERALL RESULTS:")
        print(f"   Total Passed: {total_passed}")
        print(f"   Total Failed: {total_failed}")
        
        if total_failed == 0:
            print("✅ ALL TESTS PASSED - Dev seed data verified successfully!")
        elif total_passed > 0:
            print("⚠️ PARTIAL SUCCESS - Some tests failed, review details above")
        else:
            print("❌ ALL TESTS FAILED - Dev seed data not found or corrupted")
        
        print("="*80)

    async def run_all_tests(self):
        """Run all tests in sequence"""
        print("🚀 Starting PR#7.2 Dev Seed Backend Test")
        print(f"🎯 Testing organization: {self.org_id}")
        
        # Setup database connection
        if not await self.setup_db():
            return
        
        # Run database tests
        await self.test_customers_collection()
        await self.test_bookings_collection()
        await self.test_crm_deals_collection()
        await self.test_crm_tasks_collection()
        
        # Run API tests
        self.test_api_endpoints()
        
        # Print summary
        self.print_summary()


async def main():
    """Main test execution"""
    tester = DevSeedTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())