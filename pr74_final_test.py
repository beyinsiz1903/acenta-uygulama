#!/usr/bin/env python3
"""
PR#7.4 Final Test - Focus on deterministic behavior and application logic
"""

import asyncio
import json
import sys
from datetime import datetime, timedelta
from typing import Dict, Any

sys.path.append('/app/backend')

from app.db import connect_mongo, get_db
from app.services.crm_customers import find_or_create_customer_for_booking, create_customer, _normalize_phone

TEST_ORG_ID = "695e03c80b04ed31c4eaa899"

class PR74FinalResults:
    def __init__(self):
        self.results = {}
        self.summary = []

    def add_result(self, test_name: str, data: Dict[str, Any]):
        self.results[test_name] = data
        
    def add_summary(self, message: str):
        self.summary.append(message)
        print(f"📋 {message}")

async def cleanup_test_data(db):
    """Clean up any test data"""
    await db.customers.delete_many({
        "organization_id": TEST_ORG_ID,
        "name": {"$regex": "^(Test Customer|Normalization Test|PR74)"}
    })

async def test_deterministic_email_behavior(db, results):
    """Test deterministic email selection with updated_at ordering"""
    print("\n🔍 Test 1: Deterministic Email Selection (updated_at ordering)")
    
    test_email = "deterministic.email@test.example"
    
    # Clean up any existing data
    await db.customers.delete_many({
        "organization_id": TEST_ORG_ID,
        "contacts.value": test_email
    })
    
    now = datetime.utcnow()
    older_time = now - timedelta(hours=2)
    newer_time = now - timedelta(minutes=30)
    
    # Create customer M1 (older)
    customer_m1_data = {
        "type": "individual",
        "name": "PR74 Test Customer M1",
        "contacts": [{"type": "email", "value": test_email, "is_primary": True}]
    }
    customer_m1 = await create_customer(db, TEST_ORG_ID, "system", customer_m1_data)
    await db.customers.update_one(
        {"organization_id": TEST_ORG_ID, "id": customer_m1["id"]},
        {"$set": {"updated_at": older_time}}
    )
    
    # Create customer M2 (newer)
    customer_m2_data = {
        "type": "individual",
        "name": "PR74 Test Customer M2", 
        "contacts": [{"type": "email", "value": test_email, "is_primary": True}]
    }
    customer_m2 = await create_customer(db, TEST_ORG_ID, "system", customer_m2_data)
    await db.customers.update_one(
        {"organization_id": TEST_ORG_ID, "id": customer_m2["id"]},
        {"$set": {"updated_at": newer_time}}
    )
    
    # Test multiple calls - should always return M2 (newer)
    booking_data = {"customer": {"email": test_email}}
    selected_ids = []
    
    for i in range(5):
        selected_id = await find_or_create_customer_for_booking(db, TEST_ORG_ID, booking=booking_data)
        selected_ids.append(selected_id)
    
    all_consistent = all(id == selected_ids[0] for id in selected_ids)
    selected_newer = selected_ids[0] == customer_m2["id"]
    
    # Reverse the times and test again
    await db.customers.update_one(
        {"organization_id": TEST_ORG_ID, "id": customer_m1["id"]},
        {"$set": {"updated_at": newer_time}}
    )
    await db.customers.update_one(
        {"organization_id": TEST_ORG_ID, "id": customer_m2["id"]},
        {"$set": {"updated_at": older_time}}
    )
    
    reversed_selected_ids = []
    for i in range(5):
        selected_id = await find_or_create_customer_for_booking(db, TEST_ORG_ID, booking=booking_data)
        reversed_selected_ids.append(selected_id)
    
    reversed_consistent = all(id == reversed_selected_ids[0] for id in reversed_selected_ids)
    reversed_selected_m1 = reversed_selected_ids[0] == customer_m1["id"]
    
    results.add_result("deterministic_email", {
        "customer_m1_id": customer_m1["id"],
        "customer_m2_id": customer_m2["id"],
        "test_email": test_email,
        "initial_selection_consistent": all_consistent,
        "initial_selected_newer": selected_newer,
        "initial_selected_ids": selected_ids,
        "reversed_selection_consistent": reversed_consistent,
        "reversed_selected_older_as_newer": reversed_selected_m1,
        "reversed_selected_ids": reversed_selected_ids
    })
    
    if all_consistent and selected_newer and reversed_consistent and reversed_selected_m1:
        results.add_summary("✅ Deterministic email selection: PASS - Always selects most recently updated customer")
    else:
        results.add_summary("❌ Deterministic email selection: FAIL - Not deterministic or not selecting by updated_at")

async def test_deterministic_phone_behavior(db, results):
    """Test deterministic phone selection with normalization"""
    print("\n🔍 Test 2: Deterministic Phone Selection (with normalization)")
    
    test_phone_formatted = "+90 (555) 000 0005"
    test_phone_normalized = _normalize_phone(test_phone_formatted)
    
    # Clean up
    await db.customers.delete_many({
        "organization_id": TEST_ORG_ID,
        "contacts.value": {"$in": [test_phone_formatted, test_phone_normalized]}
    })
    
    now = datetime.utcnow()
    older_time = now - timedelta(hours=1)
    newer_time = now - timedelta(minutes=15)
    
    # Create customer M3 (older) with formatted phone
    customer_m3_data = {
        "type": "individual",
        "name": "PR74 Test Customer M3",
        "contacts": [{"type": "phone", "value": test_phone_formatted, "is_primary": True}]
    }
    customer_m3 = await create_customer(db, TEST_ORG_ID, "system", customer_m3_data)
    await db.customers.update_one(
        {"organization_id": TEST_ORG_ID, "id": customer_m3["id"]},
        {"$set": {"updated_at": older_time}}
    )
    
    # Create customer M4 (newer) with normalized phone
    customer_m4_data = {
        "type": "individual",
        "name": "PR74 Test Customer M4",
        "contacts": [{"type": "phone", "value": test_phone_normalized, "is_primary": True}]
    }
    customer_m4 = await create_customer(db, TEST_ORG_ID, "system", customer_m4_data)
    await db.customers.update_one(
        {"organization_id": TEST_ORG_ID, "id": customer_m4["id"]},
        {"$set": {"updated_at": newer_time}}
    )
    
    # Test with formatted phone - should find M4 (newer, normalized)
    booking_data = {"customer": {"phone": test_phone_formatted}}
    selected_ids = []
    
    for i in range(5):
        selected_id = await find_or_create_customer_for_booking(db, TEST_ORG_ID, booking=booking_data)
        selected_ids.append(selected_id)
    
    all_consistent = all(id == selected_ids[0] for id in selected_ids)
    selected_newer = selected_ids[0] == customer_m4["id"]
    
    results.add_result("deterministic_phone", {
        "customer_m3_id": customer_m3["id"],
        "customer_m4_id": customer_m4["id"],
        "test_phone_formatted": test_phone_formatted,
        "test_phone_normalized": test_phone_normalized,
        "selection_consistent": all_consistent,
        "selected_newer_normalized": selected_newer,
        "selected_ids": selected_ids
    })
    
    if all_consistent and selected_newer:
        results.add_summary("✅ Deterministic phone selection: PASS - Selects most recent customer with phone normalization")
    else:
        results.add_summary("❌ Deterministic phone selection: FAIL - Not deterministic or normalization issue")

async def test_contact_normalization(db, results):
    """Test contact value normalization"""
    print("\n🔍 Test 3: Contact Normalization")
    
    test_cases = [
        {
            "name": "PR74 Normalization Test 1",
            "input_email": "UPPERCASE@EXAMPLE.COM",
            "expected_email": "uppercase@example.com",
            "input_phone": "+90 (555) 123-4567",
            "expected_phone": "905551234567"
        },
        {
            "name": "PR74 Normalization Test 2", 
            "input_email": "MixedCase@Test.Domain",
            "expected_email": "mixedcase@test.domain",
            "input_phone": "0 555 999 8877",
            "expected_phone": "05559998877"
        }
    ]
    
    normalization_results = []
    created_customer_ids = []
    
    for i, test_case in enumerate(test_cases):
        customer_data = {
            "type": "individual",
            "name": test_case["name"],
            "contacts": [
                {"type": "email", "value": test_case["input_email"], "is_primary": True},
                {"type": "phone", "value": test_case["input_phone"], "is_primary": False}
            ]
        }
        
        customer = await create_customer(db, TEST_ORG_ID, "system", customer_data)
        created_customer_ids.append(customer["id"])
        
        # Check what was stored
        stored_customer = await db.customers.find_one({"id": customer["id"]})
        
        email_contact = next((c for c in stored_customer["contacts"] if c["type"] == "email"), None)
        phone_contact = next((c for c in stored_customer["contacts"] if c["type"] == "phone"), None)
        
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
        print(f"  Test {i+1}: Email {test_case['input_email']} → {email_contact['value'] if email_contact else 'None'} ({'✅' if email_normalized else '❌'})")
        print(f"          Phone {test_case['input_phone']} → {phone_contact['value'] if phone_contact else 'None'} ({'✅' if phone_normalized else '❌'})")
    
    all_normalized = all(r["email_normalized"] and r["phone_normalized"] for r in normalization_results)
    
    results.add_result("contact_normalization", {
        "customer_ids": created_customer_ids,
        "test_cases": normalization_results,
        "all_normalized": all_normalized
    })
    
    if all_normalized:
        results.add_summary("✅ Contact normalization: PASS - All emails lowercase, phones digits-only")
    else:
        results.add_summary("❌ Contact normalization: FAIL - Normalization not working correctly")

async def test_application_level_duplicate_handling(db, results):
    """Test application-level duplicate prevention"""
    print("\n🔍 Test 4: Application-Level Duplicate Handling")
    
    test_email = "app.duplicate.test@example.com"
    
    # Clean up
    await db.customers.delete_many({
        "organization_id": TEST_ORG_ID,
        "contacts.value": test_email
    })
    
    # Create first customer
    customer_data = {
        "type": "individual",
        "name": "PR74 App Duplicate Test",
        "contacts": [{"type": "email", "value": test_email, "is_primary": True}]
    }
    customer = await create_customer(db, TEST_ORG_ID, "system", customer_data)
    
    # Try multiple find_or_create calls - should always return the same customer
    booking_data = {"customer": {"email": test_email}}
    found_ids = []
    
    for i in range(10):
        found_id = await find_or_create_customer_for_booking(db, TEST_ORG_ID, booking=booking_data)
        found_ids.append(found_id)
    
    # Check that only one customer exists with this email
    customers_count = await db.customers.count_documents({
        "organization_id": TEST_ORG_ID,
        "contacts.value": test_email
    })
    
    all_same_id = all(id == found_ids[0] for id in found_ids)
    found_original = found_ids[0] == customer["id"]
    
    results.add_result("application_duplicate_handling", {
        "original_customer_id": customer["id"],
        "test_email": test_email,
        "found_ids": found_ids,
        "customers_count": customers_count,
        "all_same_id": all_same_id,
        "found_original": found_original,
        "no_duplicates_created": customers_count == 1
    })
    
    if all_same_id and found_original and customers_count == 1:
        results.add_summary("✅ Application duplicate handling: PASS - Always returns same customer, no duplicates created")
    else:
        results.add_summary("❌ Application duplicate handling: FAIL - Duplicates created or inconsistent behavior")

async def main():
    """Main test execution"""
    print("🚀 PR#7.4 Final Test - Deterministic & Duplicate-safe Customer Match/Create")
    print("=" * 80)
    
    results = PR74FinalResults()
    
    try:
        await connect_mongo()
        db = await get_db()
        print("✅ Connected to MongoDB")
        
        # Clean up any existing test data
        await cleanup_test_data(db)
        
        # Run all tests
        await test_deterministic_email_behavior(db, results)
        await test_deterministic_phone_behavior(db, results)
        await test_contact_normalization(db, results)
        await test_application_level_duplicate_handling(db, results)
        
        # Clean up test data
        await cleanup_test_data(db)
        
        # Print results
        print("\n" + "=" * 80)
        print("📊 FINAL TEST RESULTS")
        print("=" * 80)
        
        for message in results.summary:
            print(message)
        
        # Save results
        with open('/app/pr74_final_results.json', 'w') as f:
            json.dump(results.results, f, indent=2, default=str)
        
        print(f"\n📄 Detailed results saved to: /app/pr74_final_results.json")
        
        # Summary
        passes = sum(1 for msg in results.summary if "PASS" in msg)
        fails = sum(1 for msg in results.summary if "FAIL" in msg)
        
        print(f"\n🎯 SUMMARY: {passes} PASS, {fails} FAIL")
        
        if fails == 0:
            print("🎉 ALL TESTS PASSED - PR#7.4 deterministic customer matching is working correctly!")
        else:
            print("⚠️ SOME TESTS FAILED - Review results for details")
            
    except Exception as e:
        print(f"❌ Test execution failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())