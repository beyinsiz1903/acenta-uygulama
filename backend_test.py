#!/usr/bin/env python3
"""
Syroce Backend Catalog Module API Test
Tests the new catalog module's backend APIs as requested in the review
"""
import requests
import sys
import uuid
from datetime import datetime, timedelta, date

class SyroceCatalogTester:
    def __init__(self, base_url="https://agencyriskmgmt.preview.emergentagent.com"):
        self.base_url = base_url
        self.agency_admin_token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.failed_tests = []
        
        # Store created IDs for testing
        self.created_product_id = None
        self.created_variant_id = None
        self.created_booking_id = None

    def log(self, msg):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    def run_test(self, name, method, endpoint, expected_status, data=None, headers_override=None, token=None):
        """Run a single API test with specific token"""
        url = f"{self.base_url}/{endpoint}"
        headers = headers_override or {'Content-Type': 'application/json'}
        
        # Use specific token if provided
        if token:
            headers['Authorization'] = f'Bearer {token}'

        self.tests_run += 1
        self.log(f"🔍 Test #{self.tests_run}: {name}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=15)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=15)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=15)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=15)
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
                    self.log(f"   Response: {response.text[:500]}")
                except:
                    pass
                return False, {}

        except Exception as e:
            self.tests_failed += 1
            self.failed_tests.append(f"{name} - Error: {str(e)}")
            self.log(f"❌ FAILED - Error: {str(e)}")
            return False, {}

    def test_health_endpoint(self):
        """Test 1) HEALTH - GET /api/health → 200 + { ok:true, service:"acenta-master" }"""
        self.log("\n=== 1) HEALTH CHECK ===")
        success, response = self.run_test(
            "GET /api/health",
            "GET",
            "api/health",
            200
        )
        if success:
            ok = response.get('ok')
            service = response.get('service')
            if ok is True and service == "acenta-master":
                self.log(f"✅ Health check successful - ok: {ok}, service: {service}")
                return True
            else:
                self.log(f"❌ Invalid health response - ok: {ok}, service: {service}")
                return False
        return False

    def test_agency_login(self):
        """Test 2) LOGIN (agency1) - POST /api/auth/login { email:"agency1@demo.test", password:"agency123" }"""
        self.log("\n=== 2) AGENCY LOGIN ===")
        success, response = self.run_test(
            "Agency Login (agency1@demo.test/agency123)",
            "POST",
            "api/auth/login",
            200,
            data={"email": "agency1@demo.test", "password": "agency123"},
            headers_override={'Content-Type': 'application/json'}
        )
        if success and 'access_token' in response:
            self.agency_admin_token = response['access_token']
            user = response.get('user', {})
            agency_id = user.get('agency_id')
            roles = user.get('roles', [])
            
            if agency_id and ('agency_admin' in roles or 'agency_agent' in roles):
                self.log(f"✅ Agency login successful - agency_id: {agency_id}, roles: {roles}")
                self.log(f"✅ Access token obtained for subsequent requests")
                return True
            else:
                self.log(f"❌ Missing agency_id or agency role: {agency_id}, {roles}")
                return False
        return False

    def test_catalog_product_create(self):
        """Test 3a) CATALOG PRODUCT CREATE - POST /api/agency/catalog/products"""
        self.log("\n=== 3a) CATALOG PRODUCT CREATE ===")
        
        product_data = {
            "type": "tour",
            "title": "Test Katalog Turu",
            "description": "Bu bir test katalog turudur. Sapanca bölgesinde günübirlik tur.",
            "location": {
                "city": "Sapanca",
                "country": "TR"
            },
            "base_currency": "TRY",
            "images": []
        }
        
        success, response = self.run_test(
            "POST /api/agency/catalog/products",
            "POST",
            "api/agency/catalog/products",
            200,
            data=product_data,
            token=self.agency_admin_token
        )
        
        if success:
            # Check response structure
            product_id = response.get('id')
            product_type = response.get('type')
            title = response.get('title')
            
            if product_id and product_type == 'tour' and title == 'Test Katalog Turu':
                self.created_product_id = product_id
                self.log(f"✅ Product created successfully:")
                self.log(f"   - ID: {product_id}")
                self.log(f"   - Type: {product_type}")
                self.log(f"   - Title: {title}")
                self.log(f"   - Location: {response.get('location')}")
                self.log(f"   - Currency: {response.get('base_currency')}")
                return True
            else:
                self.log(f"❌ Invalid product creation response - id: {product_id}, type: {product_type}, title: {title}")
                return False
        return False

    def test_catalog_product_list(self):
        """Test 3b) CATALOG PRODUCT LIST - GET /api/agency/catalog/products"""
        self.log("\n=== 3b) CATALOG PRODUCT LIST ===")
        
        success, response = self.run_test(
            "GET /api/agency/catalog/products",
            "GET",
            "api/agency/catalog/products",
            200,
            token=self.agency_admin_token
        )
        
        if success:
            if isinstance(response, dict) and 'items' in response:
                items = response['items']
                self.log(f"✅ Product list retrieved - found {len(items)} products")
                
                # Check if our created product is in the list
                if self.created_product_id:
                    found_product = None
                    for item in items:
                        if item.get('id') == self.created_product_id:
                            found_product = item
                            break
                    
                    if found_product:
                        self.log(f"✅ Created product found in list:")
                        self.log(f"   - ID: {found_product.get('id')}")
                        self.log(f"   - Title: {found_product.get('title')}")
                        self.log(f"   - Type: {found_product.get('type')}")
                        return True
                    else:
                        self.log(f"❌ Created product {self.created_product_id} not found in list")
                        return False
                else:
                    self.log(f"✅ Product list working (no specific product to verify)")
                    return True
            else:
                self.log(f"❌ Expected dict with 'items' key, got: {type(response)}")
                return False
        return False

    def test_catalog_variant_create(self):
        """Test 4a) CATALOG VARIANT CREATE - POST /api/agency/catalog/variants"""
        self.log("\n=== 4a) CATALOG VARIANT CREATE ===")
        
        if not self.created_product_id:
            self.log("❌ No product ID available for variant creation")
            return False
        
        variant_data = {
            "product_id": self.created_product_id,
            "name": "Standart",
            "price": 1000,
            "currency": "TRY",
            "rules": {
                "min_pax": 1,
                "max_pax": 5
            },
            "active": True
        }
        
        success, response = self.run_test(
            "POST /api/agency/catalog/variants",
            "POST",
            "api/agency/catalog/variants",
            200,
            data=variant_data,
            token=self.agency_admin_token
        )
        
        if success:
            # Check response structure
            variant_id = response.get('id')
            name = response.get('name')
            price = response.get('price')
            currency = response.get('currency')
            rules = response.get('rules', {})
            
            if variant_id and name == 'Standart' and price == 1000:
                self.created_variant_id = variant_id
                self.log(f"✅ Variant created successfully:")
                self.log(f"   - ID: {variant_id}")
                self.log(f"   - Name: {name}")
                self.log(f"   - Price: {price} {currency}")
                self.log(f"   - Rules: min_pax={rules.get('min_pax')}, max_pax={rules.get('max_pax')}")
                return True
            else:
                self.log(f"❌ Invalid variant creation response - id: {variant_id}, name: {name}, price: {price}")
                return False
        return False

    def test_catalog_variant_list(self):
        """Test 4b) CATALOG VARIANT LIST - GET /api/agency/catalog/products/{product_id}/variants"""
        self.log("\n=== 4b) CATALOG VARIANT LIST ===")
        
        if not self.created_product_id:
            self.log("❌ No product ID available for variant listing")
            return False
        
        success, response = self.run_test(
            f"GET /api/agency/catalog/products/{self.created_product_id}/variants",
            "GET",
            f"api/agency/catalog/products/{self.created_product_id}/variants",
            200,
            token=self.agency_admin_token
        )
        
        if success:
            if isinstance(response, dict) and 'items' in response:
                items = response['items']
                self.log(f"✅ Variant list retrieved - found {len(items)} variants")
                
                # Check if our created variant is in the list
                if self.created_variant_id:
                    found_variant = None
                    for item in items:
                        if item.get('id') == self.created_variant_id:
                            found_variant = item
                            break
                    
                    if found_variant:
                        self.log(f"✅ Created variant found in list:")
                        self.log(f"   - ID: {found_variant.get('id')}")
                        self.log(f"   - Name: {found_variant.get('name')}")
                        self.log(f"   - Price: {found_variant.get('price')} {found_variant.get('currency')}")
                        return True
                    else:
                        self.log(f"❌ Created variant {self.created_variant_id} not found in list")
                        return False
                else:
                    self.log(f"✅ Variant list working (no specific variant to verify)")
                    return True
            else:
                self.log(f"❌ Expected dict with 'items' key, got: {type(response)}")
                return False
        return False

    def test_catalog_booking_create(self):
        """Test 5a) CATALOG BOOKING CREATE - POST /api/agency/catalog/bookings"""
        self.log("\n=== 5a) CATALOG BOOKING CREATE ===")
        
        if not self.created_product_id or not self.created_variant_id:
            self.log("❌ No product/variant ID available for booking creation")
            return False
        
        booking_data = {
            "product_id": self.created_product_id,
            "variant_id": self.created_variant_id,
            "guest": {
                "full_name": "API Guest",
                "phone": "05550000000",
                "email": "apiguest@example.com"
            },
            "dates": {
                "start": "2026-01-10",
                "end": None
            },
            "pax": 2,
            "commission_rate": 0.1
        }
        
        success, response = self.run_test(
            "POST /api/agency/catalog/bookings",
            "POST",
            "api/agency/catalog/bookings",
            200,
            data=booking_data,
            token=self.agency_admin_token
        )
        
        if success:
            # Check response structure
            booking_id = response.get('id')
            status = response.get('status')
            pricing = response.get('pricing', {})
            guest = response.get('guest', {})
            
            if booking_id and status == 'new' and pricing:
                self.created_booking_id = booking_id
                self.log(f"✅ Booking created successfully:")
                self.log(f"   - ID: {booking_id}")
                self.log(f"   - Status: {status}")
                self.log(f"   - Guest: {guest.get('full_name')} ({guest.get('phone')})")
                self.log(f"   - Pricing: subtotal={pricing.get('subtotal')}, commission={pricing.get('commission_amount')}, total={pricing.get('total')}")
                return True
            else:
                self.log(f"❌ Invalid booking creation response - id: {booking_id}, status: {status}")
                return False
        return False

    def test_catalog_booking_detail(self):
        """Test 5b) CATALOG BOOKING DETAIL - GET /api/agency/catalog/bookings/{id}"""
        self.log("\n=== 5b) CATALOG BOOKING DETAIL ===")
        
        if not self.created_booking_id:
            self.log("❌ No booking ID available for detail test")
            return False
        
        success, response = self.run_test(
            f"GET /api/agency/catalog/bookings/{self.created_booking_id}",
            "GET",
            f"api/agency/catalog/bookings/{self.created_booking_id}",
            200,
            token=self.agency_admin_token
        )
        
        if success:
            # Check response structure
            booking_id = response.get('id')
            status = response.get('status')
            internal_notes = response.get('internal_notes', [])
            pricing = response.get('pricing', {})
            
            if booking_id == self.created_booking_id and status and isinstance(internal_notes, list):
                self.log(f"✅ Booking detail retrieved successfully:")
                self.log(f"   - ID: {booking_id}")
                self.log(f"   - Status: {status}")
                self.log(f"   - Internal notes count: {len(internal_notes)}")
                self.log(f"   - Pricing: {pricing}")
                return True
            else:
                self.log(f"❌ Invalid booking detail response")
                return False
        return False

    def test_catalog_booking_add_note(self):
        """Test 5c) CATALOG BOOKING ADD NOTE - POST /api/agency/catalog/bookings/{id}/internal-notes"""
        self.log("\n=== 5c) CATALOG BOOKING ADD NOTE ===")
        
        if not self.created_booking_id:
            self.log("❌ No booking ID available for note test")
            return False
        
        note_data = {
            "text": "API test notu - Bu rezervasyon API testi sırasında oluşturulmuştur."
        }
        
        success, response = self.run_test(
            f"POST /api/agency/catalog/bookings/{self.created_booking_id}/internal-notes",
            "POST",
            f"api/agency/catalog/bookings/{self.created_booking_id}/internal-notes",
            200,
            data=note_data,
            token=self.agency_admin_token
        )
        
        if success:
            ok = response.get('ok')
            if ok is True:
                self.log(f"✅ Internal note added successfully: ok={ok}")
                return True
            else:
                self.log(f"❌ Invalid add note response: ok={ok}")
                return False
        return False

    def test_catalog_booking_verify_note(self):
        """Test 5d) CATALOG BOOKING VERIFY NOTE - GET /api/agency/catalog/bookings/{id} (verify note exists)"""
        self.log("\n=== 5d) CATALOG BOOKING VERIFY NOTE ===")
        
        if not self.created_booking_id:
            self.log("❌ No booking ID available for note verification")
            return False
        
        success, response = self.run_test(
            f"GET /api/agency/catalog/bookings/{self.created_booking_id} (verify note)",
            "GET",
            f"api/agency/catalog/bookings/{self.created_booking_id}",
            200,
            token=self.agency_admin_token
        )
        
        if success:
            internal_notes = response.get('internal_notes', [])
            
            if len(internal_notes) > 0:
                # Check the structure of the latest note
                latest_note = internal_notes[-1]  # Should be the one we just added
                
                text = latest_note.get('text', '')
                created_at = latest_note.get('created_at')
                actor = latest_note.get('actor', {})
                
                if 'API test notu' in text and created_at and actor:
                    self.log(f"✅ Internal note verified in detail response:")
                    self.log(f"   - Text: {text[:50]}...")
                    self.log(f"   - Created at: {created_at}")
                    self.log(f"   - Actor: {actor.get('name')} ({actor.get('role')})")
                    return True
                else:
                    self.log(f"❌ Note structure incomplete - text: {text[:30]}, created_at: {created_at}, actor: {actor}")
                    return False
            else:
                self.log(f"❌ No internal notes found after adding note")
                return False
        return False

    def print_summary(self):
        """Print test summary"""
        self.log("\n" + "="*60)
        self.log("SYROCE CATALOG MODULE BACKEND TEST SUMMARY")
        self.log("="*60)
        self.log(f"Total Tests: {self.tests_run}")
        self.log(f"✅ Passed: {self.tests_passed}")
        self.log(f"❌ Failed: {self.tests_failed}")
        self.log(f"Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        
        if self.failed_tests:
            self.log("\n❌ FAILED TESTS:")
            for i, test in enumerate(self.failed_tests, 1):
                self.log(f"  {i}. {test}")
        
        # Show created entities
        if self.created_product_id or self.created_variant_id or self.created_booking_id:
            self.log("\n📋 CREATED ENTITIES:")
            if self.created_product_id:
                self.log(f"  - Product ID: {self.created_product_id}")
            if self.created_variant_id:
                self.log(f"  - Variant ID: {self.created_variant_id}")
            if self.created_booking_id:
                self.log(f"  - Booking ID: {self.created_booking_id}")
        
        self.log("="*60)

    def run_all_tests(self):
        """Run all Syroce Catalog backend tests in sequence"""
        self.log("🚀 Starting Syroce Catalog Module Backend Tests")
        self.log(f"Base URL: {self.base_url}")
        
        # 1) Health check
        if not self.test_health_endpoint():
            self.log("❌ Health check failed - stopping tests")
            self.print_summary()
            return 1
        
        # 2) Agency login
        if not self.test_agency_login():
            self.log("❌ Agency login failed - stopping tests")
            self.print_summary()
            return 1
        
        # 3) Catalog Product Create + List
        self.test_catalog_product_create()
        self.test_catalog_product_list()
        
        # 4) Catalog Variant Create + List
        self.test_catalog_variant_create()
        self.test_catalog_variant_list()
        
        # 5) Catalog Booking Create + Detail + Note
        self.test_catalog_booking_create()
        self.test_catalog_booking_detail()
        self.test_catalog_booking_add_note()
        self.test_catalog_booking_verify_note()
        
        # Summary
        self.print_summary()
        
        return 0 if self.tests_failed == 0 else 1


if __name__ == "__main__":
    tester = SyroceCatalogTester()
    exit_code = tester.run_all_tests()
    sys.exit(exit_code)