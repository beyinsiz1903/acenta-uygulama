#!/usr/bin/env python3
"""
Admin B2B Pricing Preview Backend Test

Tests the new Admin B2B Pricing Preview endpoint:
POST /api/admin/b2b/pricing/preview

Test scenarios:
1. Auth & basic contract
2. Validation behavior  
3. Response shape resilience
4. Error handling
"""

import asyncio
import json
import os
import sys
from datetime import date, timedelta
from typing import Any, Dict

import aiohttp
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient

# Configuration
BACKEND_URL = "https://bayiportal-2.preview.emergentagent.com"
ADMIN_EMAIL = "admin@acenta.test"
ADMIN_PASSWORD = "admin123"

class TestResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
        
    def success(self, message: str):
        print(f"✅ {message}")
        self.passed += 1
        
    def failure(self, message: str):
        print(f"❌ {message}")
        self.failed += 1
        self.errors.append(message)
        
    def info(self, message: str):
        print(f"ℹ️  {message}")

async def get_admin_token() -> str:
    """Login as admin and get JWT token"""
    async with aiohttp.ClientSession() as session:
        login_payload = {
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        }
        
        async with session.post(f"{BACKEND_URL}/api/auth/login", json=login_payload) as resp:
            if resp.status != 200:
                raise Exception(f"Admin login failed: {resp.status} - {await resp.text()}")
            
            data = await resp.json()
            return data["access_token"]

async def setup_test_data() -> Dict[str, Any]:
    """Create test product and partner if they don't exist"""
    mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
    client = AsyncIOMotorClient(mongo_url)
    db = client.acenta_db
    
    # Use admin's organization
    org_id = "org_ops_close_idem"
    
    # Find or create test product
    product = await db.products.find_one({"organization_id": org_id})
    if not product:
        product_id = ObjectId()
        await db.products.insert_one({
            "_id": product_id,
            "organization_id": org_id,
            "title": "Test Hotel Product",
            "type": "hotel",
            "base_price": 100.0,
            "currency": "EUR",
            "created_at": "2025-01-01T00:00:00Z"
        })
        product = {"_id": product_id}
    
    # Find or create test partner
    partner = await db.partner_profiles.find_one({"organization_id": org_id})
    if not partner:
        partner_id = ObjectId()
        await db.partner_profiles.insert_one({
            "_id": partner_id,
            "organization_id": org_id,
            "name": "Test Partner",
            "type": "hotel_supplier",
            "created_at": "2025-01-01T00:00:00Z"
        })
        partner = {"_id": partner_id}
    
    client.close()
    
    return {
        "organization_id": org_id,
        "product_id": str(product["_id"]),
        "partner_id": str(partner["_id"])
    }

async def test_auth_and_basic_contract(token: str, test_data: Dict[str, Any], result: TestResult):
    """Test 1: Auth & basic contract"""
    result.info("Testing Auth & Basic Contract...")
    
    # Prepare realistic payload
    checkin = date.today() + timedelta(days=30)
    checkout = checkin + timedelta(days=2)
    
    payload = {
        "partner_id": test_data["partner_id"],
        "product_id": test_data["product_id"],
        "checkin": checkin.isoformat(),
        "checkout": checkout.isoformat(),
        "occupancy": {
            "adults": 2,
            "children": 0,
            "rooms": 1
        },
        "currency": "EUR"
    }
    
    headers = {"Authorization": f"Bearer {token}"}
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BACKEND_URL}/api/admin/b2b/pricing/preview",
            json=payload,
            headers=headers
        ) as resp:
            status = resp.status
            response_text = await resp.text()
            
            result.info(f"Request: POST /api/admin/b2b/pricing/preview")
            result.info(f"Payload: {json.dumps(payload, indent=2)}")
            result.info(f"Response Status: {status}")
            result.info(f"Response: {response_text}")
            
            if status == 200:
                try:
                    data = json.loads(response_text)
                    result.success("✅ Status 200 received")
                    result.success("✅ JSON response parsed successfully")
                    
                    # Check required fields
                    required_fields = ["partner_id", "product_id", "currency", "checkin", "checkout", "occupancy", "breakdown"]
                    for field in required_fields:
                        if field in data:
                            result.success(f"✅ Required field '{field}' present")
                        else:
                            result.failure(f"❌ Required field '{field}' missing")
                    
                    # Check breakdown structure
                    if "breakdown" in data:
                        breakdown_fields = ["nights", "base_price", "markup_percent", "final_sell_price"]
                        for field in breakdown_fields:
                            if field in data["breakdown"]:
                                result.success(f"✅ Breakdown field '{field}' present")
                            else:
                                result.failure(f"❌ Breakdown field '{field}' missing")
                    
                    # Check no MongoDB _id leakage
                    response_str = json.dumps(data)
                    if "_id" not in response_str:
                        result.success("✅ No MongoDB _id leakage detected")
                    else:
                        result.failure("❌ MongoDB _id found in response")
                    
                    return data
                    
                except json.JSONDecodeError:
                    result.failure("❌ Invalid JSON response")
                    return None
            else:
                result.failure(f"❌ Expected status 200, got {status}: {response_text}")
                return None

async def test_validation_behavior(token: str, test_data: Dict[str, Any], result: TestResult):
    """Test 2: Validation behavior"""
    result.info("Testing Validation Behavior...")
    
    headers = {"Authorization": f"Bearer {token}"}
    checkin = date.today() + timedelta(days=30)
    checkout = checkin + timedelta(days=2)
    
    # Test missing product_id
    payload_missing_product = {
        "partner_id": test_data["partner_id"],
        "checkin": checkin.isoformat(),
        "checkout": checkout.isoformat(),
        "occupancy": {
            "adults": 2,
            "children": 0,
            "rooms": 1
        }
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BACKEND_URL}/api/admin/b2b/pricing/preview",
            json=payload_missing_product,
            headers=headers
        ) as resp:
            status = resp.status
            response_text = await resp.text()
            
            result.info(f"Missing product_id test - Status: {status}")
            result.info(f"Response: {response_text}")
            
            if status in [400, 422]:
                result.success("✅ Missing product_id returns 400/422 validation error")
            else:
                result.failure(f"❌ Expected 400/422 for missing product_id, got {status}")
    
    # Test invalid nights (0 nights)
    payload_invalid_nights = {
        "partner_id": test_data["partner_id"],
        "product_id": test_data["product_id"],
        "checkin": checkin.isoformat(),
        "checkout": checkin.isoformat(),  # Same date = 0 nights
        "occupancy": {
            "adults": 2,
            "children": 0,
            "rooms": 1
        }
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BACKEND_URL}/api/admin/b2b/pricing/preview",
            json=payload_invalid_nights,
            headers=headers
        ) as resp:
            status = resp.status
            response_text = await resp.text()
            
            result.info(f"Invalid nights test - Status: {status}")
            result.info(f"Response: {response_text}")
            
            if status in [400, 422]:
                result.success("✅ Invalid nights (0) returns 400/422 validation error")
            else:
                result.failure(f"❌ Expected 400/422 for invalid nights, got {status}")

async def test_response_shape_resilience(token: str, test_data: Dict[str, Any], result: TestResult):
    """Test 3: Response shape resilience for frontend"""
    result.info("Testing Response Shape Resilience...")
    
    checkin = date.today() + timedelta(days=30)
    checkout = checkin + timedelta(days=2)
    
    payload = {
        "partner_id": test_data["partner_id"],
        "product_id": test_data["product_id"],
        "checkin": checkin.isoformat(),
        "checkout": checkout.isoformat(),
        "occupancy": {
            "adults": 2,
            "children": 0,
            "rooms": 1
        },
        "currency": "EUR"
    }
    
    headers = {"Authorization": f"Bearer {token}"}
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BACKEND_URL}/api/admin/b2b/pricing/preview",
            json=payload,
            headers=headers
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                
                result.info("=== SAMPLE RESPONSE BODY ===")
                result.info(json.dumps(data, indent=2, default=str))
                result.info("=== END SAMPLE RESPONSE ===")
                
                # Check for expected optional keys
                optional_keys = ["currency", "breakdown", "rule_hits", "notes"]
                for key in optional_keys:
                    if key in data:
                        result.success(f"✅ Optional key '{key}' present")
                    else:
                        result.info(f"ℹ️  Optional key '{key}' not present (acceptable)")
                
                # Check JSON serializability
                try:
                    json.dumps(data, default=str)
                    result.success("✅ Response is JSON-serializable")
                except Exception as e:
                    result.failure(f"❌ Response not JSON-serializable: {e}")
                
                # Check no MongoDB _id leakage (detailed check)
                def check_no_id_recursive(obj, path=""):
                    if isinstance(obj, dict):
                        for k, v in obj.items():
                            if k == "_id":
                                result.failure(f"❌ MongoDB _id found at {path}.{k}")
                                return False
                            if not check_no_id_recursive(v, f"{path}.{k}"):
                                return False
                    elif isinstance(obj, list):
                        for i, item in enumerate(obj):
                            if not check_no_id_recursive(item, f"{path}[{i}]"):
                                return False
                    return True
                
                if check_no_id_recursive(data):
                    result.success("✅ No MongoDB _id fields found in response")
                
            else:
                result.failure(f"❌ Could not get valid response for shape testing: {resp.status}")

async def test_error_handling(token: str, test_data: Dict[str, Any], result: TestResult):
    """Test 4: Error handling"""
    result.info("Testing Error Handling...")
    
    headers = {"Authorization": f"Bearer {token}"}
    checkin = date.today() + timedelta(days=30)
    checkout = checkin + timedelta(days=2)
    
    # Test with non-existent product_id
    payload_bad_product = {
        "partner_id": test_data["partner_id"],
        "product_id": "000000000000000000000000",  # Non-existent ObjectId
        "checkin": checkin.isoformat(),
        "checkout": checkout.isoformat(),
        "occupancy": {
            "adults": 2,
            "children": 0,
            "rooms": 1
        }
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BACKEND_URL}/api/admin/b2b/pricing/preview",
            json=payload_bad_product,
            headers=headers
        ) as resp:
            status = resp.status
            response_text = await resp.text()
            
            result.info(f"Non-existent product test - Status: {status}")
            result.info(f"Response: {response_text}")
            
            if status == 404:
                try:
                    data = json.loads(response_text)
                    if "error" in data and "message" in data["error"]:
                        result.success("✅ 404 error with proper error structure")
                    else:
                        result.failure("❌ 404 error but missing proper error structure")
                except:
                    result.failure("❌ 404 error but response not valid JSON")
            elif status >= 400 and status < 500:
                result.success(f"✅ Controlled 4xx error ({status}) for non-existent product")
            else:
                result.failure(f"❌ Expected 4xx error for non-existent product, got {status}")
    
    # Test with non-existent partner_id
    payload_bad_partner = {
        "partner_id": "000000000000000000000000",  # Non-existent ObjectId
        "product_id": test_data["product_id"],
        "checkin": checkin.isoformat(),
        "checkout": checkout.isoformat(),
        "occupancy": {
            "adults": 2,
            "children": 0,
            "rooms": 1
        }
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{BACKEND_URL}/api/admin/b2b/pricing/preview",
            json=payload_bad_partner,
            headers=headers
        ) as resp:
            status = resp.status
            response_text = await resp.text()
            
            result.info(f"Non-existent partner test - Status: {status}")
            result.info(f"Response: {response_text}")
            
            if status == 404:
                try:
                    data = json.loads(response_text)
                    if "error" in data and "message" in data["error"]:
                        result.success("✅ 404 error with proper error structure")
                    else:
                        result.failure("❌ 404 error but missing proper error structure")
                except:
                    result.failure("❌ 404 error but response not valid JSON")
            elif status >= 400 and status < 500:
                result.success(f"✅ Controlled 4xx error ({status}) for non-existent partner")
            else:
                result.failure(f"❌ Expected 4xx error for non-existent partner, got {status}")

async def main():
    """Main test execution"""
    print("🚀 Starting Admin B2B Pricing Preview Backend Test")
    print(f"Backend URL: {BACKEND_URL}")
    print(f"Admin User: {ADMIN_EMAIL}")
    print("=" * 60)
    
    result = TestResult()
    
    try:
        # Setup
        result.info("Setting up test data...")
        test_data = await setup_test_data()
        result.info(f"Test data: {test_data}")
        
        result.info("Getting admin token...")
        token = await get_admin_token()
        result.success("✅ Admin authentication successful")
        
        # Run tests
        await test_auth_and_basic_contract(token, test_data, result)
        await test_validation_behavior(token, test_data, result)
        await test_response_shape_resilience(token, test_data, result)
        await test_error_handling(token, test_data, result)
        
    except Exception as e:
        result.failure(f"Test setup failed: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    print(f"✅ Passed: {result.passed}")
    print(f"❌ Failed: {result.failed}")
    print(f"📈 Success Rate: {result.passed / (result.passed + result.failed) * 100:.1f}%" if (result.passed + result.failed) > 0 else "No tests run")
    
    if result.errors:
        print("\n🚨 FAILURES:")
        for error in result.errors:
            print(f"  - {error}")
    
    if result.failed == 0:
        print("\n🎉 ALL TESTS PASSED!")
        sys.exit(0)
    else:
        print(f"\n⚠️  {result.failed} TEST(S) FAILED")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())