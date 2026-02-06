#!/usr/bin/env python3
"""
PR-10 Backend Validation: B2B Marketplace Booking Create Flow Testing

This test validates the new B2B marketplace booking create flow with:
1. Happy path (marketplace source)
2. Access denied scenarios (no marketplace_access)
3. Missing tenant context scenarios
4. Legacy quote flow regression check

Tests the POST /api/b2b/bookings endpoint with source="marketplace" branching.
"""

import asyncio
import json
import jwt
import httpx
from datetime import datetime, timedelta
from decimal import Decimal
from bson import ObjectId, Decimal128
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Dict, Any
import os
import uuid

# Configuration
BACKEND_URL = "https://tenant-features.preview.emergentagent.com"
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DATABASE_NAME = os.environ.get("DB_NAME", "test_database")

# JWT Secret (from backend auth module)
JWT_SECRET = os.environ.get("JWT_SECRET", "dev_jwt_secret_change_me")

class B2BMarketplaceBookingTester:
    def __init__(self):
        self.client = None
        self.db = None
        self.mongo_client = None
        self.test_data = {}
        
    async def setup(self):
        """Initialize database connection and HTTP client."""
        self.mongo_client = AsyncIOMotorClient(MONGO_URL)
        self.db = self.mongo_client[DATABASE_NAME]
        self.client = httpx.AsyncClient(timeout=30.0)
        
    async def cleanup(self):
        """Clean up connections and test data."""
        if self.client:
            await self.client.aclose()
        if self.mongo_client:
            # Clean up test data
            for collection_name, ids in self.test_data.items():
                if ids:
                    collection = getattr(self.db, collection_name)
                    await collection.delete_many({"_id": {"$in": ids}})
            self.mongo_client.close()
    
    def generate_jwt_token(self, email: str, org_id: str) -> str:
        """Generate JWT token for authentication."""
        payload = {
            "sub": email,
            "org": org_id,
            "exp": datetime.utcnow() + timedelta(hours=1)
        }
        return jwt.encode(payload, JWT_SECRET, algorithm="HS256")
    
    async def create_test_org_and_tenants(self) -> Dict[str, str]:
        """Create test organization, seller tenant, and buyer tenant."""
        now = datetime.utcnow()
        
        # Create organization
        org_doc = {
            "name": f"B2B Test Org {uuid.uuid4().hex[:8]}",
            "slug": f"b2b_test_org_{uuid.uuid4().hex[:8]}",
            "created_at": now,
            "updated_at": now
        }
        org_result = await self.db.organizations.insert_one(org_doc)
        org_id = str(org_result.inserted_id)
        self.test_data.setdefault("organizations", []).append(org_result.inserted_id)
        
        # Create seller tenant
        seller_tenant_key = f"seller-{uuid.uuid4().hex[:8]}"
        seller_doc = {
            "tenant_key": seller_tenant_key,
            "organization_id": org_id,
            "brand_name": f"Seller B2B {uuid.uuid4().hex[:8]}",
            "primary_domain": f"{seller_tenant_key}.example.com",
            "subdomain": seller_tenant_key,
            "theme_config": {},
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
        seller_result = await self.db.tenants.insert_one(seller_doc)
        seller_tenant_id = str(seller_result.inserted_id)
        self.test_data.setdefault("tenants", []).append(seller_result.inserted_id)
        
        # Create buyer tenant
        buyer_tenant_key = f"buyer-{uuid.uuid4().hex[:8]}"
        buyer_doc = {
            "tenant_key": buyer_tenant_key,
            "organization_id": org_id,
            "brand_name": f"Buyer B2B {uuid.uuid4().hex[:8]}",
            "primary_domain": f"{buyer_tenant_key}.example.com",
            "subdomain": buyer_tenant_key,
            "theme_config": {},
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
        buyer_result = await self.db.tenants.insert_one(buyer_doc)
        buyer_tenant_id = str(buyer_result.inserted_id)
        self.test_data.setdefault("tenants", []).append(buyer_result.inserted_id)
        
        return {
            "org_id": org_id,
            "seller_tenant_id": seller_tenant_id,
            "seller_tenant_key": seller_tenant_key,
            "buyer_tenant_id": buyer_tenant_id,
            "buyer_tenant_key": buyer_tenant_key,
        }
    
    async def create_test_user(self, org_id: str, email: str) -> str:
        """Create test user with admin role."""
        now = datetime.utcnow()
        user_doc = {
            "organization_id": org_id,
            "email": email,
            "roles": ["admin"],
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
        user_result = await self.db.users.insert_one(user_doc)
        self.test_data.setdefault("users", []).append(user_result.inserted_id)
        return str(user_result.inserted_id)
    
    async def create_pricing_rule(self, org_id: str, buyer_tenant_id: str) -> str:
        """Create TRY markup_pct pricing rule for buyer tenant."""
        now = datetime.utcnow()
        rule_doc = {
            "organization_id": org_id,
            "tenant_id": buyer_tenant_id,
            "rule_type": "markup_pct",
            "value": Decimal128("15.00"),  # 15% markup
            "priority": 10,
            "stackable": True,
            "valid_from": now - timedelta(minutes=5),
            "valid_to": now + timedelta(days=30),
            "created_at": now,
            "updated_at": now,
        }
        rule_result = await self.db.pricing_rules.insert_one(rule_doc)
        self.test_data.setdefault("pricing_rules", []).append(rule_result.inserted_id)
        return str(rule_result.inserted_id)
    
    async def create_marketplace_listing(self, org_id: str, seller_tenant_id: str) -> str:
        """Create published marketplace listing."""
        now = datetime.utcnow()
        listing_doc = {
            "organization_id": org_id,
            "tenant_id": seller_tenant_id,
            "status": "published",
            "title": f"B2B Test Hotel Listing {uuid.uuid4().hex[:8]}",
            "currency": "TRY",
            "base_price": Decimal128("100.00"),
            "tags": ["b2b", "test"],
            "created_at": now,
            "updated_at": now,
        }
        listing_result = await self.db.marketplace_listings.insert_one(listing_doc)
        self.test_data.setdefault("marketplace_listings", []).append(listing_result.inserted_id)
        return str(listing_result.inserted_id)
    
    async def create_marketplace_access(self, org_id: str, seller_tenant_id: str, buyer_tenant_id: str) -> str:
        """Create marketplace access record (seller->buyer)."""
        now = datetime.utcnow()
        access_doc = {
            "organization_id": org_id,
            "seller_tenant_id": seller_tenant_id,
            "buyer_tenant_id": buyer_tenant_id,
            "created_at": now,
        }
        access_result = await self.db.marketplace_access.insert_one(access_doc)
        self.test_data.setdefault("marketplace_access", []).append(access_result.inserted_id)
        return str(access_result.inserted_id)
    
    async def test_happy_path_marketplace_booking(self) -> Dict[str, Any]:
        """Test 1: Happy path marketplace booking creation."""
        print("🧪 Testing Happy Path (marketplace source)...")
        
        # Setup test data
        setup = await self.create_test_org_and_tenants()
        org_id = setup["org_id"]
        seller_tenant_id = setup["seller_tenant_id"]
        buyer_tenant_id = setup["buyer_tenant_id"]
        buyer_tenant_key = setup["buyer_tenant_key"]
        
        # Create user
        email = f"b2b_admin_{uuid.uuid4().hex[:8]}@example.com"
        await self.create_test_user(org_id, email)
        
        # Create pricing rule
        await self.create_pricing_rule(org_id, buyer_tenant_id)
        
        # Create marketplace listing
        listing_id = await self.create_marketplace_listing(org_id, seller_tenant_id)
        
        # Create marketplace access
        await self.create_marketplace_access(org_id, seller_tenant_id, buyer_tenant_id)
        
        # Generate JWT token
        token = self.generate_jwt_token(email, org_id)
        
        # Prepare request
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Tenant-Key": buyer_tenant_key,
            "Idempotency-Key": f"mkp-test-{uuid.uuid4().hex[:8]}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "source": "marketplace",
            "listing_id": listing_id,
            "customer": {
                "full_name": "B2B Customer",
                "email": "b2b-customer@example.com",
                "phone": "+900000000000"
            },
            "travellers": [
                {"first_name": "Test", "last_name": "User"}
            ]
        }
        
        # Make HTTP request
        response = await self.client.post(
            f"{BACKEND_URL}/api/b2b/bookings",
            json=payload,
            headers=headers
        )
        
        result = {
            "test_name": "Happy Path Marketplace Booking",
            "status_code": response.status_code,
            "success": response.status_code == 201,
            "response_body": response.json() if response.status_code in [200, 201] else response.text,
            "expected_status": 201,
            "setup_data": setup
        }
        
        if response.status_code == 201:
            data = response.json()
            booking_id = data.get("booking_id")
            
            # Verify response structure
            result["response_validation"] = {
                "has_booking_id": bool(booking_id),
                "state_is_draft": data.get("state") == "draft"
            }
            
            if booking_id:
                # DB validation
                booking_doc = await self.db.bookings.find_one({"_id": ObjectId(booking_id)})
                if booking_doc:
                    self.test_data.setdefault("bookings", []).append(ObjectId(booking_id))
                    
                    result["db_validation"] = {
                        "booking_found": True,
                        "state": booking_doc.get("state"),
                        "source": booking_doc.get("source"),
                        "offer_ref_source": booking_doc.get("offer_ref", {}).get("source"),
                        "offer_ref_listing_id": booking_doc.get("offer_ref", {}).get("listing_id"),
                        "offer_ref_buyer_tenant_id": booking_doc.get("offer_ref", {}).get("buyer_tenant_id"),
                        "offer_ref_seller_tenant_id": booking_doc.get("offer_ref", {}).get("seller_tenant_id"),
                        "pricing_currency": booking_doc.get("pricing", {}).get("currency"),
                        "pricing_base_amount": booking_doc.get("pricing", {}).get("base_amount"),
                        "pricing_final_amount": booking_doc.get("pricing", {}).get("final_amount"),
                        "pricing_applied_rules": booking_doc.get("pricing", {}).get("applied_rules", []),
                    }
                    
                    # Check if markup was applied
                    base_amount = booking_doc.get("pricing", {}).get("base_amount")
                    final_amount = booking_doc.get("pricing", {}).get("final_amount")
                    if base_amount and final_amount:
                        result["db_validation"]["markup_applied"] = base_amount != final_amount
                    
                    # Check applied rules
                    applied_rules = booking_doc.get("pricing", {}).get("applied_rules", [])
                    result["db_validation"]["has_markup_pct_rule"] = any(
                        rule.get("rule_type") == "markup_pct" for rule in applied_rules
                    )
                
                # Check audit logs
                audit_count = await self.db.audit_logs.count_documents({
                    "organization_id": org_id,
                    "action": "PRICING_RULE_APPLIED",
                    "target.id": booking_id
                })
                result["audit_validation"] = {
                    "pricing_rule_applied_count": audit_count
                }
        
        return result
    
    async def test_access_denied_scenario(self) -> Dict[str, Any]:
        """Test 2: Access denied scenario (no marketplace_access)."""
        print("🧪 Testing Access Denied Scenario...")
        
        # Setup test data (without marketplace_access)
        setup = await self.create_test_org_and_tenants()
        org_id = setup["org_id"]
        seller_tenant_id = setup["seller_tenant_id"]
        buyer_tenant_key = setup["buyer_tenant_key"]
        
        # Create user
        email = f"b2b_admin_{uuid.uuid4().hex[:8]}@example.com"
        await self.create_test_user(org_id, email)
        
        # Create marketplace listing (but NO marketplace_access)
        listing_id = await self.create_marketplace_listing(org_id, seller_tenant_id)
        
        # Generate JWT token
        token = self.generate_jwt_token(email, org_id)
        
        # Prepare request
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Tenant-Key": buyer_tenant_key,
            "Idempotency-Key": f"mkp-test-{uuid.uuid4().hex[:8]}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "source": "marketplace",
            "listing_id": listing_id,
            "customer": {
                "full_name": "B2B Customer",
                "email": "b2b-customer@example.com",
                "phone": "+900000000000"
            },
            "travellers": [
                {"first_name": "Test", "last_name": "User"}
            ]
        }
        
        # Make HTTP request
        response = await self.client.post(
            f"{BACKEND_URL}/api/b2b/bookings",
            json=payload,
            headers=headers
        )
        
        result = {
            "test_name": "Access Denied Scenario",
            "status_code": response.status_code,
            "success": response.status_code == 403,
            "response_body": response.json() if response.status_code in [400, 403, 422] else response.text,
            "expected_status": 403,
            "setup_data": setup
        }
        
        if response.status_code == 403:
            data = response.json()
            error_message = data.get("error", {}).get("message")
            result["error_validation"] = {
                "error_message": error_message,
                "is_marketplace_access_forbidden": error_message == "MARKETPLACE_ACCESS_FORBIDDEN"
            }
        
        return result
    
    async def test_missing_tenant_context(self) -> Dict[str, Any]:
        """Test 3: Missing tenant context scenario (no X-Tenant-Key)."""
        print("🧪 Testing Missing Tenant Context Scenario...")
        
        # Setup test data
        setup = await self.create_test_org_and_tenants()
        org_id = setup["org_id"]
        seller_tenant_id = setup["seller_tenant_id"]
        buyer_tenant_id = setup["buyer_tenant_id"]
        
        # Create user
        email = f"b2b_admin_{uuid.uuid4().hex[:8]}@example.com"
        await self.create_test_user(org_id, email)
        
        # Create marketplace listing and access
        listing_id = await self.create_marketplace_listing(org_id, seller_tenant_id)
        await self.create_marketplace_access(org_id, seller_tenant_id, buyer_tenant_id)
        
        # Generate JWT token
        token = self.generate_jwt_token(email, org_id)
        
        # Prepare request (WITHOUT X-Tenant-Key)
        headers = {
            "Authorization": f"Bearer {token}",
            # "X-Tenant-Key": buyer_tenant_key,  # Intentionally omitted
            "Idempotency-Key": f"mkp-test-{uuid.uuid4().hex[:8]}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "source": "marketplace",
            "listing_id": listing_id,
            "customer": {
                "full_name": "B2B Customer",
                "email": "b2b-customer@example.com",
                "phone": "+900000000000"
            },
            "travellers": [
                {"first_name": "Test", "last_name": "User"}
            ]
        }
        
        # Make HTTP request
        response = await self.client.post(
            f"{BACKEND_URL}/api/b2b/bookings",
            json=payload,
            headers=headers
        )
        
        result = {
            "test_name": "Missing Tenant Context Scenario",
            "status_code": response.status_code,
            "success": response.status_code == 403,
            "response_body": response.json() if response.status_code in [400, 403, 422] else response.text,
            "expected_status": 403,
            "setup_data": setup
        }
        
        if response.status_code == 403:
            data = response.json()
            error_message = data.get("error", {}).get("message")
            result["error_validation"] = {
                "error_message": error_message,
                "is_tenant_context_required": error_message == "TENANT_CONTEXT_REQUIRED"
            }
        
        return result
    
    async def test_legacy_quote_flow_regression(self) -> Dict[str, Any]:
        """Test 4: Legacy quote flow regression check (source absent/"quote")."""
        print("🧪 Testing Legacy Quote Flow Regression...")
        
        # Setup test data
        setup = await self.create_test_org_and_tenants()
        org_id = setup["org_id"]
        
        # Create user
        email = f"b2b_admin_{uuid.uuid4().hex[:8]}@example.com"
        await self.create_test_user(org_id, email)
        
        # Generate JWT token
        token = self.generate_jwt_token(email, org_id)
        
        # Prepare request (legacy quote flow - no source or source="quote")
        headers = {
            "Authorization": f"Bearer {token}",
            "Idempotency-Key": f"legacy-test-{uuid.uuid4().hex[:8]}",
            "Content-Type": "application/json"
        }
        
        payload = {
            # No source field (should default to quote flow)
            "quote_id": "non-existent-quote-id",  # This will fail but should hit quote flow
            "customer": {
                "name": "Legacy Customer",
                "email": "legacy-customer@example.com"
            },
            "travellers": [
                {"first_name": "Test", "last_name": "User"}
            ]
        }
        
        # Make HTTP request
        response = await self.client.post(
            f"{BACKEND_URL}/api/b2b/bookings",
            json=payload,
            headers=headers
        )
        
        result = {
            "test_name": "Legacy Quote Flow Regression",
            "status_code": response.status_code,
            "success": response.status_code in [400, 403, 422],  # Should fail but not crash
            "response_body": response.json() if response.status_code in [400, 403, 422] else response.text,
            "expected_status": "4xx (not 500)",
            "setup_data": setup
        }
        
        # The important thing is that it doesn't crash (500) and follows the quote flow
        if response.status_code < 500:
            result["regression_check"] = "Legacy quote flow path accessible (no 500 error)"
        
        return result
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all PR-10 B2B marketplace booking tests."""
        print("🚀 Starting PR-10 B2B Marketplace Booking Create Flow Tests")
        print(f"Backend URL: {BACKEND_URL}")
        
        await self.setup()
        
        try:
            results = {}
            
            # Test 1: Happy path
            results["happy_path"] = await self.test_happy_path_marketplace_booking()
            
            # Test 2: Access denied
            results["access_denied"] = await self.test_access_denied_scenario()
            
            # Test 3: Missing tenant context
            results["missing_tenant_context"] = await self.test_missing_tenant_context()
            
            # Test 4: Legacy quote flow regression
            results["legacy_regression"] = await self.test_legacy_quote_flow_regression()
            
            # Summary
            total_tests = len(results)
            passed_tests = sum(1 for r in results.values() if r["success"])
            
            results["summary"] = {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": total_tests - passed_tests,
                "success_rate": f"{(passed_tests/total_tests)*100:.1f}%"
            }
            
            return results
            
        finally:
            await self.cleanup()


async def main():
    """Main test runner."""
    tester = B2BMarketplaceBookingTester()
    results = await tester.run_all_tests()
    
    print("\n" + "="*80)
    print("PR-10 B2B MARKETPLACE BOOKING CREATE FLOW TEST RESULTS")
    print("="*80)
    
    for test_name, result in results.items():
        if test_name == "summary":
            continue
            
        status = "✅ PASS" if result["success"] else "❌ FAIL"
        print(f"\n{status} {result['test_name']}")
        print(f"   Expected: HTTP {result['expected_status']}")
        print(f"   Actual: HTTP {result['status_code']}")
        
        if result["success"]:
            if "db_validation" in result:
                db_val = result["db_validation"]
                print(f"   ✓ Booking state: {db_val.get('state')}")
                print(f"   ✓ Source: {db_val.get('source')}")
                print(f"   ✓ Offer ref source: {db_val.get('offer_ref_source')}")
                print(f"   ✓ Currency: {db_val.get('pricing_currency')}")
                print(f"   ✓ Base amount: {db_val.get('pricing_base_amount')}")
                print(f"   ✓ Final amount: {db_val.get('pricing_final_amount')}")
                print(f"   ✓ Markup applied: {db_val.get('markup_applied')}")
                print(f"   ✓ Has markup_pct rule: {db_val.get('has_markup_pct_rule')}")
            
            if "audit_validation" in result:
                audit_val = result["audit_validation"]
                print(f"   ✓ Pricing audit logs: {audit_val.get('pricing_rule_applied_count')}")
            
            if "error_validation" in result:
                error_val = result["error_validation"]
                print(f"   ✓ Error message: {error_val.get('error_message')}")
            
            if "regression_check" in result:
                print(f"   ✓ {result['regression_check']}")
        else:
            print(f"   ❌ Response: {result.get('response_body', 'No response body')}")
    
    # Summary
    summary = results.get("summary", {})
    print(f"\n{'='*80}")
    print(f"SUMMARY: {summary.get('passed_tests', 0)}/{summary.get('total_tests', 0)} tests passed ({summary.get('success_rate', '0%')})")
    
    if summary.get("failed_tests", 0) > 0:
        print("❌ Some tests failed. Check the details above.")
        return 1
    else:
        print("✅ All tests passed!")
        return 0


if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code)