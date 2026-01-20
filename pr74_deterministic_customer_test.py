#!/usr/bin/env python3
"""
PR#7.4 – Deterministic & duplicate-safe customer match/create test

Test scenarios:
1. Deterministic selection test (email) - create two customers with same email but different updated_at times
2. Deterministic selection test (phone) - similar test with phone numbers and normalization  
3. Unique index + DuplicateKeyError retry test - test the retry logic when duplicate keys are encountered
4. Normalization test - verify email lowercase and phone digit-only normalization
5. Reporting - document which customer IDs were selected and verify normalization
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, Any, List
import httpx
from pymongo.errors import DuplicateKeyError

# Add backend to path
sys.path.append('/app/backend')

from app.db import connect_mongo, get_db
from app.services.crm_customers import find_or_create_customer_for_booking, create_customer, _normalize_phone
from bson import ObjectId

# Test configuration
BACKEND_URL = "https://resflow-polish.preview.emergentagent.com/api"
TEST_ORG_ID = "695e03c80b04ed31c4eaa899"  # Admin organization

class PR74TestResults:
    def __init__(self):
        self.results = {
            "deterministic_email_test": {},
            "deterministic_phone_test": {},
            "duplicate_key_retry_test": {},
            "normalization_test": {},
            "unique_index_verification": {}
        }
        self.summary = []

    def add_result(self, test_name: str, data: Dict[str, Any]):
        self.results[test_name] = data
        
    def add_summary(self, message: str):
        self.summary.append(message)
        print(f"📋 {message}")

async def get_auth_token():
    """Get admin authentication token"""
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{BACKEND_URL}/auth/login", json={
            "email": "admin@acenta.test",
            "password": "admin123"
        })
        if response.status_code == 200:
            return response.json()["access_token"]
        else:
            raise Exception(f"Login failed: {response.status_code} {response.text}")

async def cleanup_test_customers(db, test_results):
    """Clean up test customers created during testing"""
    customer_ids = []
    
    # Collect all customer IDs from test results
    for test_name, test_data in test_results.results.items():
        if "customer_ids" in test_data:
            customer_ids.extend(test_data["customer_ids"])
        if "selected_customer_id" in test_data:
            customer_ids.append(test_data["selected_customer_id"])
    
    # Remove duplicates
    customer_ids = list(set(customer_ids))
    
    if customer_ids:
        result = await db.customers.delete_many({
            "organization_id": TEST_ORG_ID,
            "id": {"$in": customer_ids}
        })
        print(f"🧹 Cleaned up {result.deleted_count} test customers")

async def test_deterministic_email_selection(db, test_results):
    """Test 1: Deterministic selection test (email)"""
    print("\n🔍 Test 1: Deterministic Email Selection")
    
    # Create two customers with same email but different updated_at times
    now = datetime.utcnow()
    older_time = now - timedelta(hours=2)
    newer_time = now - timedelta(minutes=30)
    
    # Customer M1 (older updated_at)
    customer_m1_data = {
        "type": "individual",
        "name": "Test Customer M1",
        "contacts": [
            {"type": "email", "value": "multi@test.example", "is_primary": True}
        ]
    }
    customer_m1 = await create_customer(db, TEST_ORG_ID, "system", customer_m1_data)
    # Manually update the updated_at to be older
    await db.customers.update_one(
        {"organization_id": TEST_ORG_ID, "id": customer_m1["id"]},
        {"$set": {"updated_at": older_time}}
    )
    
    # Customer M2 (newer updated_at)  
    customer_m2_data = {
        "type": "individual", 
        "name": "Test Customer M2",
        "contacts": [
            {"type": "email", "value": "multi@test.example", "is_primary": True}
        ]
    }
    customer_m2 = await create_customer(db, TEST_ORG_ID, "system", customer_m2_data)
    # Manually update the updated_at to be newer
    await db.customers.update_one(
        {"organization_id": TEST_ORG_ID, "id": customer_m2["id"]},
        {"$set": {"updated_at": newer_time}}
    )
    
    # Test multiple calls to find_or_create_customer_for_booking
    booking_data = {
        "customer": {"email": "multi@test.example"}
    }
    
    selected_ids = []
    for i in range(3):
        selected_id = await find_or_create_customer_for_booking(
            db, TEST_ORG_ID, booking=booking_data
        )
        selected_ids.append(selected_id)
        print(f"  Call {i+1}: Selected customer_id = {selected_id}")
    
    # Verify all calls return the same customer (the newer one)
    all_same = all(id == selected_ids[0] for id in selected_ids)
    expected_newer = customer_m2["id"]
    
    test_results.add_result("deterministic_email_test", {
        "customer_m1_id": customer_m1["id"],
        "customer_m2_id": customer_m2["id"], 
        "customer_ids": [customer_m1["id"], customer_m2["id"]],
        "older_updated_at": older_time.isoformat(),
        "newer_updated_at": newer_time.isoformat(),
        "selected_customer_id": selected_ids[0],
        "all_calls_consistent": all_same,
        "selected_newer_customer": selected_ids[0] == expected_newer,
        "selected_ids": selected_ids
    })
    
    if all_same and selected_ids[0] == expected_newer:
        test_results.add_summary("✅ Deterministic email selection: PASS - Always selects most recent customer")
    else:
        test_results.add_summary("❌ Deterministic email selection: FAIL - Inconsistent or wrong selection")
    
    # Now reverse the updated_at times and test again
    print("  🔄 Reversing updated_at times...")
    await db.customers.update_one(
        {"organization_id": TEST_ORG_ID, "id": customer_m1["id"]},
        {"$set": {"updated_at": newer_time}}
    )
    await db.customers.update_one(
        {"organization_id": TEST_ORG_ID, "id": customer_m2["id"]},
        {"$set": {"updated_at": older_time}}
    )
    
    # Test again
    reversed_selected_ids = []
    for i in range(3):
        selected_id = await find_or_create_customer_for_booking(
            db, TEST_ORG_ID, booking=booking_data
        )
        reversed_selected_ids.append(selected_id)
        print(f"  Reversed Call {i+1}: Selected customer_id = {selected_id}")
    
    reversed_all_same = all(id == reversed_selected_ids[0] for id in reversed_selected_ids)
    expected_m1_now = customer_m1["id"]
    
    test_results.results["deterministic_email_test"].update({
        "reversed_selected_customer_id": reversed_selected_ids[0],
        "reversed_all_calls_consistent": reversed_all_same,
        "reversed_selected_m1": reversed_selected_ids[0] == expected_m1_now,
        "reversed_selected_ids": reversed_selected_ids
    })
    
    if reversed_all_same and reversed_selected_ids[0] == expected_m1_now:
        test_results.add_summary("✅ Deterministic email selection (reversed): PASS - Always selects most recent customer")
    else:
        test_results.add_summary("❌ Deterministic email selection (reversed): FAIL - Inconsistent or wrong selection")

async def test_deterministic_phone_selection(db, test_results):
    """Test 2: Deterministic selection test (phone)"""
    print("\n🔍 Test 2: Deterministic Phone Selection")
    
    # Create two customers with same phone but different updated_at times
    now = datetime.utcnow()
    older_time = now - timedelta(hours=1)
    newer_time = now - timedelta(minutes=15)
    
    # Customer M3 (older updated_at) - with formatted phone
    customer_m3_data = {
        "type": "individual",
        "name": "Test Customer M3",
        "contacts": [
            {"type": "phone", "value": "+90 (555) 000 0003", "is_primary": True}
        ]
    }
    customer_m3 = await create_customer(db, TEST_ORG_ID, "system", customer_m3_data)
    await db.customers.update_one(
        {"organization_id": TEST_ORG_ID, "id": customer_m3["id"]},
        {"$set": {"updated_at": older_time}}
    )
    
    # Customer M4 (newer updated_at) - with normalized phone
    customer_m4_data = {
        "type": "individual",
        "name": "Test Customer M4", 
        "contacts": [
            {"type": "phone", "value": "905550000003", "is_primary": True}
        ]
    }
    customer_m4 = await create_customer(db, TEST_ORG_ID, "system", customer_m4_data)
    await db.customers.update_one(
        {"organization_id": TEST_ORG_ID, "id": customer_m4["id"]},
        {"$set": {"updated_at": newer_time}}
    )
    
    # Test with formatted phone number
    booking_data = {
        "customer": {"phone": "+90 (555) 000 0003"}
    }
    
    selected_ids = []
    for i in range(3):
        selected_id = await find_or_create_customer_for_booking(
            db, TEST_ORG_ID, booking=booking_data
        )
        selected_ids.append(selected_id)
        print(f"  Call {i+1}: Selected customer_id = {selected_id}")
    
    # Verify normalization and selection
    normalized_phone = _normalize_phone("+90 (555) 000 0003")
    all_same = all(id == selected_ids[0] for id in selected_ids)
    expected_newer = customer_m4["id"]
    
    test_results.add_result("deterministic_phone_test", {
        "customer_m3_id": customer_m3["id"],
        "customer_m4_id": customer_m4["id"],
        "customer_ids": [customer_m3["id"], customer_m4["id"]],
        "input_phone": "+90 (555) 000 0003",
        "normalized_phone": normalized_phone,
        "older_updated_at": older_time.isoformat(),
        "newer_updated_at": newer_time.isoformat(),
        "selected_customer_id": selected_ids[0],
        "all_calls_consistent": all_same,
        "selected_newer_customer": selected_ids[0] == expected_newer,
        "selected_ids": selected_ids
    })
    
    if all_same and selected_ids[0] == expected_newer:
        test_results.add_summary("✅ Deterministic phone selection: PASS - Always selects most recent customer with normalized phone matching")
    else:
        test_results.add_summary("❌ Deterministic phone selection: FAIL - Inconsistent or wrong selection")

async def test_unique_index_verification(db, test_results):
    """Test 3: Unique index + DuplicateKeyError retry test"""
    print("\n🔍 Test 3: Unique Index & DuplicateKeyError Retry")
    
    # First verify the unique index exists
    indexes = await db.customers.list_indexes().to_list(length=None)
    unique_index_found = False
    for index in indexes:
        if index.get("name") == "crm_customers_by_org_contact_unique":
            unique_index_found = True
            print(f"  ✅ Found unique index: {index['name']}")
            print(f"     Keys: {index['key']}")
            print(f"     Unique: {index.get('unique', False)}")
            break
    
    if not unique_index_found:
        test_results.add_summary("❌ Unique index verification: FAIL - crm_customers_by_org_contact_unique index not found")
        test_results.add_result("unique_index_verification", {
            "index_found": False,
            "error": "crm_customers_by_org_contact_unique index not found"
        })
        return
    
    # Test duplicate key error scenario by trying to create customers with same contact concurrently
    test_email = "duplicate.test@example.com"
    
    # Create first customer normally
    customer_data_1 = {
        "type": "individual",
        "name": "Duplicate Test Customer 1",
        "contacts": [
            {"type": "email", "value": test_email, "is_primary": True}
        ]
    }
    
    try:
        customer_1 = await create_customer(db, TEST_ORG_ID, "system", customer_data_1)
        print(f"  ✅ Created first customer: {customer_1['id']}")
        
        # Try to create second customer with same email - should trigger DuplicateKeyError
        customer_data_2 = {
            "type": "individual", 
            "name": "Duplicate Test Customer 2",
            "contacts": [
                {"type": "email", "value": test_email, "is_primary": True}
            ]
        }
        
        duplicate_error_caught = False
        try:
            customer_2 = await create_customer(db, TEST_ORG_ID, "system", customer_data_2)
            print(f"  ⚠️ Second customer created unexpectedly: {customer_2['id']}")
        except DuplicateKeyError as e:
            duplicate_error_caught = True
            print(f"  ✅ DuplicateKeyError caught as expected: {str(e)}")
        
        # Now test the retry logic in find_or_create_customer_for_booking
        booking_data = {
            "customer": {"email": test_email}
        }
        
        # This should find the existing customer, not create a new one
        found_customer_id = await find_or_create_customer_for_booking(
            db, TEST_ORG_ID, booking=booking_data
        )
        
        # Verify only one customer exists with this email
        customers_with_email = await db.customers.find({
            "organization_id": TEST_ORG_ID,
            "contacts": {
                "$elemMatch": {
                    "type": "email",
                    "value": test_email
                }
            }
        }).to_list(length=None)
        
        test_results.add_result("duplicate_key_retry_test", {
            "test_email": test_email,
            "first_customer_id": customer_1["id"],
            "duplicate_error_caught": duplicate_error_caught,
            "found_customer_id": found_customer_id,
            "customers_count": len(customers_with_email),
            "customer_ids": [customer_1["id"]],
            "retry_logic_working": found_customer_id == customer_1["id"] and len(customers_with_email) == 1
        })
        
        if found_customer_id == customer_1["id"] and len(customers_with_email) == 1:
            test_results.add_summary("✅ DuplicateKeyError retry test: PASS - Retry logic returns existing customer, only one document in DB")
        else:
            test_results.add_summary("❌ DuplicateKeyError retry test: FAIL - Retry logic or uniqueness constraint not working")
            
    except Exception as e:
        test_results.add_result("duplicate_key_retry_test", {
            "error": str(e),
            "test_failed": True
        })
        test_results.add_summary(f"❌ DuplicateKeyError retry test: ERROR - {str(e)}")
    
    test_results.add_result("unique_index_verification", {
        "index_found": unique_index_found,
        "index_name": "crm_customers_by_org_contact_unique"
    })

async def test_normalization(db, test_results):
    """Test 4: Normalization test"""
    print("\n🔍 Test 4: Contact Normalization")
    
    # Test email normalization
    test_cases = [
        {
            "input_email": "TEST@EXAMPLE.COM",
            "expected_email": "test@example.com",
            "input_phone": "+90 (555) 000 0004",
            "expected_phone": "905550000004"
        },
        {
            "input_email": "MixedCase@Test.Example",
            "expected_email": "mixedcase@test.example", 
            "input_phone": "0 (555) 123-4567",
            "expected_phone": "05551234567"
        }
    ]
    
    created_customers = []
    normalization_results = []
    
    for i, test_case in enumerate(test_cases):
        # Create customer with non-normalized contacts
        customer_data = {
            "type": "individual",
            "name": f"Normalization Test Customer {i+1}",
            "contacts": [
                {"type": "email", "value": test_case["input_email"], "is_primary": True},
                {"type": "phone", "value": test_case["input_phone"], "is_primary": False}
            ]
        }
        
        customer = await create_customer(db, TEST_ORG_ID, "system", customer_data)
        created_customers.append(customer["id"])
        
        # Retrieve customer from DB to check normalization
        db_customer = await db.customers.find_one({
            "organization_id": TEST_ORG_ID,
            "id": customer["id"]
        })
        
        # Check email normalization
        email_contact = next((c for c in db_customer["contacts"] if c["type"] == "email"), None)
        phone_contact = next((c for c in db_customer["contacts"] if c["type"] == "phone"), None)
        
        email_normalized = email_contact["value"] == test_case["expected_email"] if email_contact else False
        phone_normalized = phone_contact["value"] == test_case["expected_phone"] if phone_contact else False
        
        result = {
            "customer_id": customer["id"],
            "input_email": test_case["input_email"],
            "stored_email": email_contact["value"] if email_contact else None,
            "expected_email": test_case["expected_email"],
            "email_normalized": email_normalized,
            "input_phone": test_case["input_phone"],
            "stored_phone": phone_contact["value"] if phone_contact else None,
            "expected_phone": test_case["expected_phone"],
            "phone_normalized": phone_normalized
        }
        
        normalization_results.append(result)
        
        print(f"  Customer {i+1}:")
        print(f"    Email: {test_case['input_email']} → {email_contact['value'] if email_contact else 'None'} ({'✅' if email_normalized else '❌'})")
        print(f"    Phone: {test_case['input_phone']} → {phone_contact['value'] if phone_contact else 'None'} ({'✅' if phone_normalized else '❌'})")
    
    # Test exact match search with normalized values
    search_tests = []
    for result in normalization_results:
        # Search by normalized email
        email_matches = await db.customers.find({
            "organization_id": TEST_ORG_ID,
            "contacts.value": result["expected_email"]
        }).to_list(length=None)
        
        # Search by normalized phone
        phone_matches = await db.customers.find({
            "organization_id": TEST_ORG_ID,
            "contacts.value": result["expected_phone"]
        }).to_list(length=None)
        
        search_tests.append({
            "customer_id": result["customer_id"],
            "email_search_matches": len(email_matches),
            "phone_search_matches": len(phone_matches),
            "email_exact_match": any(c["id"] == result["customer_id"] for c in email_matches),
            "phone_exact_match": any(c["id"] == result["customer_id"] for c in phone_matches)
        })
    
    all_normalized = all(r["email_normalized"] and r["phone_normalized"] for r in normalization_results)
    all_searchable = all(s["email_exact_match"] and s["phone_exact_match"] for s in search_tests)
    
    test_results.add_result("normalization_test", {
        "customer_ids": created_customers,
        "normalization_results": normalization_results,
        "search_tests": search_tests,
        "all_normalized": all_normalized,
        "all_searchable": all_searchable
    })
    
    if all_normalized and all_searchable:
        test_results.add_summary("✅ Contact normalization: PASS - All emails lowercase, phones digits-only, exact search working")
    else:
        test_results.add_summary("❌ Contact normalization: FAIL - Normalization or search not working correctly")

async def main():
    """Main test execution"""
    print("🚀 Starting PR#7.4 Deterministic & Duplicate-safe Customer Match/Create Tests")
    print("=" * 80)
    
    test_results = PR74TestResults()
    
    try:
        # Connect to database
        await connect_mongo()
        db = await get_db()
        print("✅ Connected to MongoDB")
        
        # Get authentication token
        token = await get_auth_token()
        print("✅ Authenticated as admin")
        
        # Run all tests
        await test_deterministic_email_selection(db, test_results)
        await test_deterministic_phone_selection(db, test_results)
        await test_unique_index_verification(db, test_results)
        await test_normalization(db, test_results)
        
        # Clean up test data
        await cleanup_test_customers(db, test_results)
        
        # Print final results
        print("\n" + "=" * 80)
        print("📊 FINAL TEST RESULTS")
        print("=" * 80)
        
        for message in test_results.summary:
            print(message)
        
        # Save detailed results to file
        with open('/app/pr74_test_results.json', 'w') as f:
            json.dump(test_results.results, f, indent=2, default=str)
        
        print(f"\n📄 Detailed results saved to: /app/pr74_test_results.json")
        
        # Count passes and fails
        passes = sum(1 for msg in test_results.summary if "PASS" in msg)
        fails = sum(1 for msg in test_results.summary if "FAIL" in msg)
        errors = sum(1 for msg in test_results.summary if "ERROR" in msg)
        
        print(f"\n🎯 SUMMARY: {passes} PASS, {fails} FAIL, {errors} ERROR")
        
        if fails == 0 and errors == 0:
            print("🎉 ALL TESTS PASSED - PR#7.4 functionality is working correctly!")
        else:
            print("⚠️ SOME TESTS FAILED - Review results above for details")
            
    except Exception as e:
        print(f"❌ Test execution failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())