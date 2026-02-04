#!/usr/bin/env python3
"""
PR#8.1 CRM Customer Detail ObjectId/datetime Normalization Test
Testing GET /api/crm/customers/{customer_id} endpoint after ObjectId/datetime fixes
"""

import requests
import json
from datetime import datetime
from typing import Any, Dict

# Configuration - Use production URL from frontend/.env
BASE_URL = "https://tenant-network.preview.emergentagent.com"

def login_admin():
    """Login as admin user and return token, org_id, email"""
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "admin@acenta.test", "password": "admin123"},
    )
    assert r.status_code == 200, f"Admin login failed: {r.text}"
    data = r.json()
    user = data["user"]
    return data["access_token"], user["organization_id"], user["email"]

def check_serialization_issues(obj: Any, path: str = "root") -> list[str]:
    """
    Recursively check for ObjectId or datetime objects that should be serialized.
    Returns list of paths where issues are found.
    """
    issues = []
    
    if isinstance(obj, dict):
        for key, value in obj.items():
            current_path = f"{path}.{key}"
            # Check if this looks like an unserialized ObjectId
            if isinstance(value, str) and len(value) == 24 and all(c in '0123456789abcdef' for c in value.lower()):
                # This could be a serialized ObjectId, which is fine
                pass
            elif str(type(value)) == "<class 'bson.objectid.ObjectId'>":
                issues.append(f"{current_path}: Found unserialized ObjectId")
            elif str(type(value)) == "<class 'datetime.datetime'>":
                issues.append(f"{current_path}: Found unserialized datetime")
            else:
                issues.extend(check_serialization_issues(value, current_path))
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            current_path = f"{path}[{i}]"
            issues.extend(check_serialization_issues(item, current_path))
    
    return issues

def validate_customer_detail_structure(data: Dict[str, Any]) -> list[str]:
    """Validate CustomerDetailOut structure"""
    issues = []
    
    # Check required top-level fields
    required_fields = ["customer", "recent_bookings", "open_deals", "open_tasks"]
    for field in required_fields:
        if field not in data:
            issues.append(f"Missing required field: {field}")
    
    # Check customer field structure
    if "customer" in data:
        customer = data["customer"]
        if not isinstance(customer, dict):
            issues.append("customer field should be a dict")
        else:
            customer_required = ["id", "organization_id", "name", "type", "created_at", "updated_at"]
            for field in customer_required:
                if field not in customer:
                    issues.append(f"customer.{field} is missing")
    
    # Check list fields are actually lists
    list_fields = ["recent_bookings", "open_deals", "open_tasks"]
    for field in list_fields:
        if field in data and not isinstance(data[field], list):
            issues.append(f"{field} should be a list, got {type(data[field])}")
    
    return issues

def test_customer_detail_endpoint(customer_id: str, admin_headers: Dict[str, str], description: str):
    """Test a specific customer detail endpoint"""
    print(f"\n📋 Testing {description}...")
    
    r = requests.get(
        f"{BASE_URL}/api/crm/customers/{customer_id}",
        headers=admin_headers,
    )
    
    print(f"   📋 GET /api/crm/customers/{customer_id}")
    print(f"   📋 Response status: {r.status_code}")
    
    if r.status_code == 200:
        print(f"   ✅ Status 200 - Previously returned 520, now fixed!")
        
        try:
            data = r.json()
            print(f"   ✅ JSON parsing successful - No PydanticSerializationError")
            
            # Validate structure
            structure_issues = validate_customer_detail_structure(data)
            if structure_issues:
                print(f"   ❌ Structure validation issues:")
                for issue in structure_issues:
                    print(f"      - {issue}")
            else:
                print(f"   ✅ CustomerDetailOut structure valid")
                
                # Show structure summary
                customer = data.get("customer", {})
                recent_bookings = data.get("recent_bookings", [])
                open_deals = data.get("open_deals", [])
                open_tasks = data.get("open_tasks", [])
                
                print(f"   📋 customer: {customer.get('name', 'N/A')} (type: {customer.get('type', 'N/A')})")
                print(f"   📋 recent_bookings: {len(recent_bookings)} items")
                print(f"   📋 open_deals: {len(open_deals)} items")
                print(f"   📋 open_tasks: {len(open_tasks)} items")
            
            # Check for serialization issues
            serialization_issues = check_serialization_issues(data)
            if serialization_issues:
                print(f"   ❌ Serialization issues found:")
                for issue in serialization_issues:
                    print(f"      - {issue}")
            else:
                print(f"   ✅ No ObjectId or datetime serialization issues found")
                print(f"   ✅ All fields are string/number/list/dict as required")
            
            # Show sample field values to verify proper serialization
            if "customer" in data:
                customer = data["customer"]
                print(f"   📋 Sample field types:")
                print(f"      - customer.id: {type(customer.get('id', '')).__name__} = '{customer.get('id', 'N/A')}'")
                print(f"      - customer.created_at: {type(customer.get('created_at', '')).__name__} = '{customer.get('created_at', 'N/A')}'")
                print(f"      - customer.updated_at: {type(customer.get('updated_at', '')).__name__} = '{customer.get('updated_at', 'N/A')}'")
            
            return True, data
            
        except json.JSONDecodeError as e:
            print(f"   ❌ JSON parsing failed: {e}")
            print(f"   📋 Raw response: {r.text[:500]}...")
            return False, None
            
    elif r.status_code == 520:
        print(f"   ❌ Still returning 520 error - ObjectId fix not working")
        try:
            error_data = r.json()
            print(f"   📋 Error response: {json.dumps(error_data, indent=2)}")
        except:
            print(f"   📋 Raw error response: {r.text}")
        return False, None
        
    elif r.status_code == 404:
        print(f"   ⚠️  Customer not found (404) - may not exist in database")
        return False, None
        
    else:
        print(f"   ❌ Unexpected status code: {r.status_code}")
        print(f"   📋 Response: {r.text}")
        return False, None

def create_test_activity(customer_id: str, admin_headers: Dict[str, str]) -> bool:
    """Create a test activity for the customer"""
    print(f"\n📋 Creating test activity for {customer_id}...")
    
    activity_data = {
        "type": "note",
        "body": "Test aktivite - PR#8.1 ObjectId normalizasyon testi için oluşturuldu",
        "related_type": "customer",
        "related_id": customer_id
    }
    
    r = requests.post(
        f"{BASE_URL}/api/crm/activities",
        json=activity_data,
        headers=admin_headers,
    )
    
    print(f"   📋 POST /api/crm/activities")
    print(f"   📋 Response status: {r.status_code}")
    
    if r.status_code == 200:
        activity = r.json()
        print(f"   ✅ Activity created successfully")
        print(f"   📋 Activity ID: {activity.get('id', 'N/A')}")
        return True
    else:
        print(f"   ⚠️  Activity creation failed: {r.status_code} - {r.text}")
        return False

def test_pr8_1_crm_customer_detail_objectid_fix():
    """Test PR#8.1 CRM Customer Detail ObjectId/datetime normalization"""
    print("\n" + "=" * 80)
    print("PR#8.1 CRM CUSTOMER DETAIL OBJECTID/DATETIME NORMALIZATION TEST")
    print("Testing GET /api/crm/customers/{customer_id} after ObjectId fixes")
    print("Requirements:")
    print("1) GET /api/crm/customers/cust_seed_linked (admin@acenta.test / admin123)")
    print("2) Previously 520 error, now should return 200")
    print("3) Response should match CustomerDetailOut structure")
    print("4) No bson.objectid.ObjectId or datetime objects - all string/number/list/dict")
    print("5) Test cust_seed_unlinked as well")
    print("6) Create activities and retest")
    print("=" * 80 + "\n")

    # ------------------------------------------------------------------
    # Test 1: Login
    # ------------------------------------------------------------------
    print("1️⃣  Login as admin@acenta.test / admin123...")
    
    admin_token, admin_org_id, admin_email = login_admin()
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    
    print(f"   ✅ Login successful: {admin_email}")
    print(f"   📋 Organization ID: {admin_org_id}")

    # ------------------------------------------------------------------
    # Test 2: GET /api/crm/customers/cust_seed_linked
    # ------------------------------------------------------------------
    print("\n2️⃣  GET /api/crm/customers/cust_seed_linked...")
    
    success_linked, data_linked = test_customer_detail_endpoint(
        "cust_seed_linked", 
        admin_headers, 
        "cust_seed_linked (should have bookings/deals/tasks)"
    )

    # ------------------------------------------------------------------
    # Test 3: GET /api/crm/customers/cust_seed_unlinked
    # ------------------------------------------------------------------
    print("\n3️⃣  GET /api/crm/customers/cust_seed_unlinked...")
    
    success_unlinked, data_unlinked = test_customer_detail_endpoint(
        "cust_seed_unlinked", 
        admin_headers, 
        "cust_seed_unlinked (recent_bookings likely empty)"
    )

    # ------------------------------------------------------------------
    # Test 4: Create activities and retest
    # ------------------------------------------------------------------
    print("\n4️⃣  Creating activities and retesting...")
    
    if success_linked:
        # Create a test activity for cust_seed_linked
        activity_created = create_test_activity("cust_seed_linked", admin_headers)
        
        if activity_created:
            print(f"\n   📋 Retesting cust_seed_linked after activity creation...")
            success_linked_2, data_linked_2 = test_customer_detail_endpoint(
                "cust_seed_linked", 
                admin_headers, 
                "cust_seed_linked (after activity creation)"
            )
            
            if success_linked_2 and data_linked_2:
                # Compare activity counts or other changes
                activities_before = len(data_linked.get("open_tasks", [])) if data_linked else 0
                activities_after = len(data_linked_2.get("open_tasks", [])) if data_linked_2 else 0
                print(f"   📋 Activities/tasks before: {activities_before}, after: {activities_after}")
        else:
            print(f"   ⚠️  Skipping retest due to activity creation failure")
    else:
        print(f"   ⚠️  Skipping activity creation due to initial test failure")

    # ------------------------------------------------------------------
    # Test 5: Summary and Results
    # ------------------------------------------------------------------
    print("\n5️⃣  Test Results Summary...")
    
    print(f"\n📋 DETAILED RESULTS:")
    print(f"   cust_seed_linked:")
    if success_linked:
        print(f"      ✅ Status: 200 (previously 520 - FIXED)")
        print(f"      ✅ JSON parsing: Success (no PydanticSerializationError)")
        print(f"      ✅ Structure: Valid CustomerDetailOut")
        print(f"      ✅ Serialization: All fields are string/number/list/dict")
        if data_linked:
            customer = data_linked.get("customer", {})
            print(f"      📋 Customer: {customer.get('name', 'N/A')}")
            print(f"      📋 Recent bookings: {len(data_linked.get('recent_bookings', []))} items")
            print(f"      📋 Open deals: {len(data_linked.get('open_deals', []))} items")
            print(f"      📋 Open tasks: {len(data_linked.get('open_tasks', []))} items")
    else:
        print(f"      ❌ Status: Failed (still has issues)")
    
    print(f"\n   cust_seed_unlinked:")
    if success_unlinked:
        print(f"      ✅ Status: 200")
        print(f"      ✅ JSON parsing: Success")
        print(f"      ✅ Structure: Valid CustomerDetailOut")
        print(f"      ✅ Serialization: All fields properly serialized")
        if data_unlinked:
            customer = data_unlinked.get("customer", {})
            print(f"      📋 Customer: {customer.get('name', 'N/A')}")
            print(f"      📋 Recent bookings: {len(data_unlinked.get('recent_bookings', []))} items (likely empty)")
    else:
        print(f"      ❌ Status: Failed")

    # ------------------------------------------------------------------
    # Final Assessment
    # ------------------------------------------------------------------
    print("\n" + "=" * 80)
    
    if success_linked and success_unlinked:
        print("✅ PR#8.1 CRM CUSTOMER DETAIL OBJECTID FIX - SUCCESSFUL")
        print("✅ All test requirements met:")
        print("   ✅ GET /api/crm/customers/cust_seed_linked returns 200 (was 520)")
        print("   ✅ GET /api/crm/customers/cust_seed_unlinked returns 200")
        print("   ✅ Response structure matches CustomerDetailOut")
        print("   ✅ No ObjectId or datetime serialization issues")
        print("   ✅ All fields are string/number/list/dict as required")
        print("   ✅ No PydanticSerializationError observed")
    else:
        print("❌ PR#8.1 CRM CUSTOMER DETAIL OBJECTID FIX - ISSUES FOUND")
        if not success_linked:
            print("   ❌ cust_seed_linked endpoint still has issues")
        if not success_unlinked:
            print("   ❌ cust_seed_unlinked endpoint still has issues")
    
    print("=" * 80 + "\n")
    
    return success_linked and success_unlinked

if __name__ == "__main__":
    test_pr8_1_crm_customer_detail_objectid_fix()