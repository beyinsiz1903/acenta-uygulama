#!/usr/bin/env python3
"""
Backend test for PR-UM2 reservation.created instrumentation validation.

This script tests the usage metering for newly created reservations
as requested in the review request for multi-tenant travel SaaS.
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import aiohttp

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Base URL from environment
BASE_URL = "https://escape-excel.preview.emergentagent.com"

# Demo credentials from review request
DEMO_EMAIL = "admin@demo-travel.demo.test"
DEMO_PASSWORD = "Demotrav!9831"

class BackendTester:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = None
        self.auth_token = None
        self.tenant_id = None
        self.organization_id = None
        self.user_info = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            connector=aiohttp.TCPConnector(ssl=False)
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def login(self, email: str, password: str) -> bool:
        """Login and store authentication token and user info."""
        try:
            async with self.session.post(
                f"{self.base_url}/api/auth/login",
                json={"email": email, "password": password}
            ) as resp:
                if resp.status != 200:
                    logger.error(f"Login failed: {resp.status} - {await resp.text()}")
                    return False
                
                data = await resp.json()
                self.auth_token = data.get("access_token")
                self.tenant_id = data.get("tenant_id")
                
                if not self.auth_token:
                    logger.error("No access token received from login")
                    return False
                
                logger.info(f"Login successful - Token length: {len(self.auth_token)} chars")
                logger.info(f"Tenant ID: {self.tenant_id}")
                return True
                
        except Exception as e:
            logger.error(f"Login error: {e}")
            return False

    async def get_user_info(self) -> Optional[Dict[str, Any]]:
        """Get current user information."""
        if not self.auth_token:
            return None
            
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            async with self.session.get(f"{self.base_url}/api/auth/me", headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.user_info = data
                    self.organization_id = data.get("organization_id")
                    logger.info(f"User: {data.get('email')} - Org: {self.organization_id}")
                    return data
                else:
                    logger.error(f"Failed to get user info: {resp.status}")
                    return None
        except Exception as e:
            logger.error(f"Get user info error: {e}")
            return None

    async def get_usage_summary(self) -> Optional[Dict[str, Any]]:
        """Get usage summary for tenant."""
        if not self.auth_token or not self.tenant_id:
            return None
            
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            url = f"{self.base_url}/api/admin/billing/tenants/{self.tenant_id}/usage"
            async with self.session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    logger.error(f"Failed to get usage summary: {resp.status} - {await resp.text()}")
                    return None
        except Exception as e:
            logger.error(f"Get usage summary error: {e}")
            return None

    async def create_reservation(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a reservation through the canonical route."""
        if not self.auth_token:
            return None
            
        try:
            headers = {
                "Authorization": f"Bearer {self.auth_token}",
                "Content-Type": "application/json"
            }
            async with self.session.post(
                f"{self.base_url}/api/reservations/reserve", 
                json=payload, 
                headers=headers
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    logger.error(f"Failed to create reservation: {resp.status} - {await resp.text()}")
                    return None
        except Exception as e:
            logger.error(f"Create reservation error: {e}")
            return None

    async def b2b_book(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a B2B booking."""
        if not self.auth_token:
            return None
            
        try:
            headers = {
                "Authorization": f"Bearer {self.auth_token}",
                "Content-Type": "application/json"
            }
            async with self.session.post(
                f"{self.base_url}/api/b2b/book", 
                json=payload, 
                headers=headers
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    logger.error(f"Failed to create B2B booking: {resp.status} - {await resp.text()}")
                    return None
        except Exception as e:
            logger.error(f"B2B book error: {e}")
            return None

    async def reserve_tour(self, tour_id: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a tour reservation."""
        if not self.auth_token:
            return None
            
        try:
            headers = {
                "Authorization": f"Bearer {self.auth_token}",
                "Content-Type": "application/json"
            }
            url = f"{self.base_url}/api/tours/{tour_id}/reserve"
            async with self.session.post(url, json=payload, headers=headers) as resp:
                if resp.status == 201:
                    return await resp.json()
                else:
                    logger.error(f"Failed to reserve tour: {resp.status} - {await resp.text()}")
                    return None
        except Exception as e:
            logger.error(f"Reserve tour error: {e}")
            return None

    async def confirm_reservation(self, reservation_id: str) -> Optional[Dict[str, Any]]:
        """Confirm a reservation."""
        if not self.auth_token:
            return None
            
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            url = f"{self.base_url}/api/reservations/{reservation_id}/confirm"
            async with self.session.post(url, headers=headers) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    logger.error(f"Failed to confirm reservation: {resp.status} - {await resp.text()}")
                    return None
        except Exception as e:
            logger.error(f"Confirm reservation error: {e}")
            return None

    async def cancel_reservation(self, reservation_id: str) -> Optional[Dict[str, Any]]:
        """Cancel a reservation."""
        if not self.auth_token:
            return None
            
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            url = f"{self.base_url}/api/reservations/{reservation_id}/cancel"
            async with self.session.post(url, headers=headers) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    logger.error(f"Failed to cancel reservation: {resp.status} - {await resp.text()}")
                    return None
        except Exception as e:
            logger.error(f"Cancel reservation error: {e}")
            return None

    async def get_available_products(self) -> list:
        """Get available products for testing."""
        if not self.auth_token:
            return []
            
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            async with self.session.get(f"{self.base_url}/api/products", headers=headers) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    logger.warning(f"Could not get products: {resp.status}")
                    return []
        except Exception as e:
            logger.warning(f"Get products error: {e}")
            return []

    async def get_available_customers(self) -> list:
        """Get available customers for testing."""
        if not self.auth_token:
            return []
            
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            async with self.session.get(f"{self.base_url}/api/customers", headers=headers) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    logger.warning(f"Could not get customers: {resp.status}")
                    return []
        except Exception as e:
            logger.warning(f"Get customers error: {e}")
            return []

    async def get_available_tours(self) -> list:
        """Get available tours for testing."""
        if not self.auth_token:
            return []
            
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}"}
            async with self.session.get(f"{self.base_url}/api/tours", headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("items", [])
                else:
                    logger.warning(f"Could not get tours: {resp.status}")
                    return []
        except Exception as e:
            logger.warning(f"Get tours error: {e}")
            return []


async def test_pr_um2_reservation_created_instrumentation():
    """Main test function for PR-UM2 reservation.created instrumentation."""
    
    print("\n" + "="*80)
    print("BACKEND TEST: PR-UM2 Reservation.Created Usage Metering Validation")
    print("="*80)
    
    test_results = []
    
    async with BackendTester(BASE_URL) as tester:
        
        # Test 1: Login with demo credentials
        print("\n1. ✅ Testing login with demo credentials...")
        login_success = await tester.login(DEMO_EMAIL, DEMO_PASSWORD)
        if not login_success:
            print("❌ Login failed - Cannot proceed with tests")
            return False
        
        user_info = await tester.get_user_info()
        if not user_info:
            print("❌ Could not get user info - Cannot proceed")
            return False
        
        test_results.append(("Login with demo credentials", True))
        print(f"✅ Login successful - User: {user_info.get('email')}")
        print(f"   Org ID: {tester.organization_id}")
        print(f"   Tenant ID: {tester.tenant_id}")
        
        # Test 2: Get initial usage counts
        print("\n2. ✅ Getting initial usage baseline...")
        initial_usage = await tester.get_usage_summary()
        if not initial_usage:
            print("❌ Could not get initial usage summary")
            return False
            
        initial_reservation_count = initial_usage.get("metrics", {}).get("reservation.created", {}).get("used", 0)
        print(f"✅ Initial reservation.created count: {initial_reservation_count}")
        test_results.append(("Get initial usage baseline", True))
        
        # Get test data
        products = await tester.get_available_products()
        customers = await tester.get_available_customers()
        tours = await tester.get_available_tours()
        
        if not products:
            print("⚠️  No products available - will skip product-based tests")
        if not customers:
            print("⚠️  No customers available - will skip customer-based tests")
        if not tours:
            print("⚠️  No tours available - will skip tour reservation tests")
        
        # Test 3: Test canonical reservation creation
        if products and customers:
            print("\n3. ✅ Testing canonical reservation creation...")
            timestamp = datetime.now(timezone.utc).isoformat()
            idempotency_key = f"pr-um2-test-{timestamp}"
            
            reservation_payload = {
                "idempotency_key": idempotency_key,
                "product_id": products[0]["id"],
                "customer_id": customers[0]["id"],
                "start_date": "2026-05-01",
                "pax": 2,
                "channel": "direct"
            }
            
            reservation = await tester.create_reservation(reservation_payload)
            if reservation:
                print(f"✅ Reservation created - ID: {reservation.get('id')}")
                test_results.append(("Canonical reservation creation", True))
                
                # Check usage increment
                new_usage = await tester.get_usage_summary()
                if new_usage:
                    new_count = new_usage.get("metrics", {}).get("reservation.created", {}).get("used", 0)
                    if new_count == initial_reservation_count + 1:
                        print(f"✅ Usage incremented correctly: {initial_reservation_count} → {new_count}")
                        test_results.append(("Usage incremented on reservation create", True))
                    else:
                        print(f"❌ Usage increment incorrect: expected {initial_reservation_count + 1}, got {new_count}")
                        test_results.append(("Usage incremented on reservation create", False))
            else:
                print("❌ Failed to create reservation")
                test_results.append(("Canonical reservation creation", False))
        else:
            print("⏭️  Skipping canonical reservation test - missing test data")
            test_results.append(("Canonical reservation creation", "SKIPPED"))
        
        # Test 4: Test idempotency behavior
        if products and customers:
            print("\n4. ✅ Testing idempotency behavior...")
            idempotency_key = f"pr-um2-idempotent-{datetime.now(timezone.utc).isoformat()}"
            
            # Get usage before idempotent requests
            before_idempotent = await tester.get_usage_summary()
            before_count = before_idempotent.get("metrics", {}).get("reservation.created", {}).get("used", 0) if before_idempotent else 0
            
            reservation_payload = {
                "idempotency_key": idempotency_key,
                "product_id": products[0]["id"],
                "customer_id": customers[0]["id"],
                "start_date": "2026-05-02",
                "pax": 1,
                "channel": "direct"
            }
            
            # First request
            first_reservation = await tester.create_reservation(reservation_payload)
            # Second request with same idempotency key
            second_reservation = await tester.create_reservation(reservation_payload)
            
            if first_reservation and second_reservation:
                if first_reservation.get("id") == second_reservation.get("id"):
                    print(f"✅ Idempotency working - Same reservation ID returned")
                    
                    # Check usage didn't double-count
                    after_usage = await tester.get_usage_summary()
                    if after_usage:
                        after_count = after_usage.get("metrics", {}).get("reservation.created", {}).get("used", 0)
                        if after_count == before_count + 1:
                            print(f"✅ No duplicate usage counting: {before_count} → {after_count}")
                            test_results.append(("Idempotency prevents duplicate usage", True))
                        else:
                            print(f"❌ Duplicate usage detected: {before_count} → {after_count}")
                            test_results.append(("Idempotency prevents duplicate usage", False))
                    
                    test_results.append(("Idempotency behavior", True))
                else:
                    print(f"❌ Idempotency failed - Different IDs: {first_reservation.get('id')} vs {second_reservation.get('id')}")
                    test_results.append(("Idempotency behavior", False))
            else:
                print("❌ Failed to test idempotency")
                test_results.append(("Idempotency behavior", False))
        else:
            print("⏭️  Skipping idempotency test - missing test data")
            test_results.append(("Idempotency behavior", "SKIPPED"))
        
        # Test 5: Test status changes don't increment usage
        if products and customers:
            print("\n5. ✅ Testing status changes don't increment usage...")
            
            # Create a reservation first
            test_reservation_payload = {
                "idempotency_key": f"pr-um2-status-test-{datetime.now(timezone.utc).isoformat()}",
                "product_id": products[0]["id"],
                "customer_id": customers[0]["id"],
                "start_date": "2026-05-03",
                "pax": 1,
                "channel": "direct"
            }
            
            test_reservation = await tester.create_reservation(test_reservation_payload)
            if test_reservation:
                # Get usage count after creation
                after_create_usage = await tester.get_usage_summary()
                after_create_count = after_create_usage.get("metrics", {}).get("reservation.created", {}).get("used", 0) if after_create_usage else 0
                
                # Confirm the reservation
                reservation_id = test_reservation.get("id")
                confirmed = await tester.confirm_reservation(reservation_id)
                
                if confirmed:
                    print(f"✅ Reservation confirmed - Status: {confirmed.get('status')}")
                    
                    # Check usage didn't increment on confirm
                    after_confirm_usage = await tester.get_usage_summary()
                    after_confirm_count = after_confirm_usage.get("metrics", {}).get("reservation.created", {}).get("used", 0) if after_confirm_usage else 0
                    
                    if after_confirm_count == after_create_count:
                        print(f"✅ Confirm didn't increment usage: {after_create_count} (unchanged)")
                        
                        # Cancel the reservation
                        cancelled = await tester.cancel_reservation(reservation_id)
                        if cancelled:
                            print(f"✅ Reservation cancelled - Status: {cancelled.get('status')}")
                            
                            # Check usage didn't increment on cancel
                            after_cancel_usage = await tester.get_usage_summary()
                            after_cancel_count = after_cancel_usage.get("metrics", {}).get("reservation.created", {}).get("used", 0) if after_cancel_usage else 0
                            
                            if after_cancel_count == after_create_count:
                                print(f"✅ Cancel didn't increment usage: {after_create_count} (unchanged)")
                                test_results.append(("Status changes don't increment usage", True))
                            else:
                                print(f"❌ Cancel incorrectly incremented usage: {after_create_count} → {after_cancel_count}")
                                test_results.append(("Status changes don't increment usage", False))
                        else:
                            print("❌ Failed to cancel reservation")
                            test_results.append(("Status changes don't increment usage", False))
                    else:
                        print(f"❌ Confirm incorrectly incremented usage: {after_create_count} → {after_confirm_count}")
                        test_results.append(("Status changes don't increment usage", False))
                else:
                    print("❌ Failed to confirm reservation")
                    test_results.append(("Status changes don't increment usage", False))
            else:
                print("❌ Failed to create test reservation for status changes")
                test_results.append(("Status changes don't increment usage", False))
        else:
            print("⏭️  Skipping status change test - missing test data")
            test_results.append(("Status changes don't increment usage", "SKIPPED"))
        
        # Test 6: Test tour reservation path
        if tours:
            print("\n6. ✅ Testing tour reservation path...")
            
            # Get usage before tour reservation
            before_tour_usage = await tester.get_usage_summary()
            before_tour_count = before_tour_usage.get("metrics", {}).get("reservation.created", {}).get("used", 0) if before_tour_usage else 0
            
            tour_id = tours[0]["id"]
            tour_payload = {
                "travel_date": "2026-05-10",
                "adults": 2,
                "children": 1,
                "guest_name": "Tour Test Guest",
                "guest_email": "tour.test@example.test",
                "guest_phone": "+90 555 123 4567",
                "notes": "PR-UM2 tour reservation test"
            }
            
            tour_reservation = await tester.reserve_tour(tour_id, tour_payload)
            if tour_reservation:
                print(f"✅ Tour reservation created - Code: {tour_reservation.get('reservation_code')}")
                
                # Check usage increment for tour reservation
                after_tour_usage = await tester.get_usage_summary()
                if after_tour_usage:
                    after_tour_count = after_tour_usage.get("metrics", {}).get("reservation.created", {}).get("used", 0)
                    if after_tour_count == before_tour_count + 1:
                        print(f"✅ Tour reservation usage incremented correctly: {before_tour_count} → {after_tour_count}")
                        test_results.append(("Tour reservation usage tracking", True))
                    else:
                        print(f"❌ Tour reservation usage increment incorrect: expected {before_tour_count + 1}, got {after_tour_count}")
                        test_results.append(("Tour reservation usage tracking", False))
            else:
                print("❌ Failed to create tour reservation")
                test_results.append(("Tour reservation usage tracking", False))
        else:
            print("⏭️  Skipping tour reservation test - no tours available")
            test_results.append(("Tour reservation usage tracking", "SKIPPED"))
        
        # Test 7: Final usage endpoint validation
        print("\n7. ✅ Final usage endpoint validation...")
        final_usage = await tester.get_usage_summary()
        if final_usage:
            final_count = final_usage.get("metrics", {}).get("reservation.created", {}).get("used", 0)
            billing_period = final_usage.get("billing_period")
            totals_source = final_usage.get("totals_source")
            
            print(f"✅ Final usage endpoint working")
            print(f"   Billing period: {billing_period}")
            print(f"   Totals source: {totals_source}")
            print(f"   Final reservation.created count: {final_count}")
            print(f"   Total increment from tests: {final_count - initial_reservation_count}")
            
            # Validate response structure
            required_fields = ["billing_period", "metrics", "totals_source"]
            all_fields_present = all(field in final_usage for field in required_fields)
            
            if all_fields_present and "reservation.created" in final_usage.get("metrics", {}):
                test_results.append(("Usage endpoint structure validation", True))
                print("✅ Usage endpoint response structure is correct")
            else:
                test_results.append(("Usage endpoint structure validation", False))
                print("❌ Usage endpoint response structure is incorrect")
        else:
            print("❌ Final usage endpoint validation failed")
            test_results.append(("Usage endpoint structure validation", False))
    
    # Print final results
    print("\n" + "="*80)
    print("PR-UM2 TEST RESULTS SUMMARY")
    print("="*80)
    
    passed = sum(1 for _, result in test_results if result is True)
    failed = sum(1 for _, result in test_results if result is False)
    skipped = sum(1 for _, result in test_results if result == "SKIPPED")
    
    for test_name, result in test_results:
        if result is True:
            print(f"✅ {test_name}")
        elif result is False:
            print(f"❌ {test_name}")
        else:
            print(f"⏭️  {test_name} - {result}")
    
    print(f"\nTotal Tests: {len(test_results)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Skipped: {skipped}")
    
    success_rate = (passed / (passed + failed)) * 100 if (passed + failed) > 0 else 0
    print(f"Success Rate: {success_rate:.1f}%")
    
    print("\n" + "="*80)
    
    return failed == 0


if __name__ == "__main__":
    try:
        success = asyncio.run(test_pr_um2_reservation_created_instrumentation())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)