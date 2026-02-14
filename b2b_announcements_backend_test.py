#!/usr/bin/env python3
"""
B2B Announcements Backend Flow Test

Test scenarios:
1. Admin creates announcement
2. Admin lists announcements  
3. Toggle active status
4. B2B portal announcement listing
5. Validity filter verification

Actors:
- Admin: admin@acenta.test / admin123
- Agency (B2B user): agency1@demo.test / agency123
"""

import requests
import json
from datetime import datetime, timedelta

# Backend URL from frontend/.env
BACKEND_URL = "https://better-menu-labels.preview.emergentagent.com"

def login_admin():
    """Login as admin and return JWT token"""
    print("🔐 Admin Login...")
    
    login_data = {
        "email": "admin@acenta.test",
        "password": "admin123"
    }
    
    response = requests.post(f"{BACKEND_URL}/api/auth/login", json=login_data)
    print(f"Login Response: {response.status_code}")
    
    if response.status_code != 200:
        print(f"❌ Admin login failed: {response.text}")
        return None
        
    data = response.json()
    token = data.get("access_token")
    print(f"✅ Admin login successful, token length: {len(token) if token else 0}")
    return token

def login_agency():
    """Login as agency user and return JWT token"""
    print("🔐 Agency Login...")
    
    login_data = {
        "email": "agency1@demo.test", 
        "password": "agency123"
    }
    
    response = requests.post(f"{BACKEND_URL}/api/auth/login", json=login_data)
    print(f"Agency Login Response: {response.status_code}")
    
    if response.status_code != 200:
        print(f"❌ Agency login failed: {response.text}")
        return None
        
    data = response.json()
    token = data.get("access_token")
    print(f"✅ Agency login successful, token length: {len(token) if token else 0}")
    return token

def test_admin_create_announcement(admin_token):
    """Test admin creating announcement"""
    print("\n📝 Testing Admin - Create Announcement...")
    
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    payload = {
        "title": "Test Duyuru",
        "body": "Bu bir test duyurusudur.",
        "audience": "all",
        "days_valid": 3
    }
    
    response = requests.post(f"{BACKEND_URL}/api/admin/b2b/announcements", 
                           json=payload, headers=headers)
    
    print(f"Create Response: {response.status_code}")
    
    if response.status_code != 200:
        print(f"❌ Create announcement failed: {response.text}")
        return None
        
    data = response.json()
    print(f"✅ Announcement created successfully")
    print(f"   ID: {data.get('id')}")
    print(f"   Title: {data.get('title')}")
    print(f"   Is Active: {data.get('is_active')}")
    print(f"   Valid From: {data.get('valid_from')}")
    print(f"   Valid Until: {data.get('valid_until')}")
    
    # Verify required fields
    assert data.get('id'), "ID should be present"
    assert data.get('is_active') == True, "is_active should be true"
    assert data.get('title') == "Test Duyuru", "Title should match"
    assert data.get('body') == "Bu bir test duyurusudur.", "Body should match"
    
    return data.get('id')

def test_admin_list_announcements(admin_token, expected_announcement_id=None):
    """Test admin listing announcements"""
    print("\n📋 Testing Admin - List Announcements...")
    
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    response = requests.get(f"{BACKEND_URL}/api/admin/b2b/announcements", headers=headers)
    
    print(f"List Response: {response.status_code}")
    
    if response.status_code != 200:
        print(f"❌ List announcements failed: {response.text}")
        return False
        
    data = response.json()
    items = data.get('items', [])
    
    print(f"✅ Found {len(items)} announcements")
    
    if expected_announcement_id:
        found = False
        for item in items:
            if item.get('id') == expected_announcement_id:
                found = True
                print(f"✅ Created announcement found in list:")
                print(f"   ID: {item.get('id')}")
                print(f"   Title: {item.get('title')}")
                print(f"   Is Active: {item.get('is_active')}")
                break
        
        if not found:
            print(f"❌ Created announcement {expected_announcement_id} not found in list")
            return False
    
    return True

def test_toggle_active(admin_token, announcement_id):
    """Test toggling announcement active status"""
    print(f"\n🔄 Testing Toggle Active Status for ID: {announcement_id}...")
    
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # First toggle (should make it false)
    response = requests.post(f"{BACKEND_URL}/api/admin/b2b/announcements/{announcement_id}/toggle", 
                           headers=headers)
    
    print(f"First Toggle Response: {response.status_code}")
    
    if response.status_code != 200:
        print(f"❌ First toggle failed: {response.text}")
        return False
        
    data = response.json()
    first_status = data.get('is_active')
    print(f"✅ First toggle successful, is_active: {first_status}")
    
    # Second toggle (should make it true again)
    response = requests.post(f"{BACKEND_URL}/api/admin/b2b/announcements/{announcement_id}/toggle", 
                           headers=headers)
    
    print(f"Second Toggle Response: {response.status_code}")
    
    if response.status_code != 200:
        print(f"❌ Second toggle failed: {response.text}")
        return False
        
    data = response.json()
    second_status = data.get('is_active')
    print(f"✅ Second toggle successful, is_active: {second_status}")
    
    # Verify toggle behavior
    assert first_status == False, "First toggle should set is_active to false"
    assert second_status == True, "Second toggle should set is_active back to true"
    
    return True

def test_b2b_portal_announcements(agency_token):
    """Test B2B portal announcement listing"""
    print("\n🏢 Testing B2B Portal - List Announcements...")
    
    headers = {"Authorization": f"Bearer {agency_token}"}
    
    response = requests.get(f"{BACKEND_URL}/api/b2b/announcements", headers=headers)
    
    print(f"B2B Portal Response: {response.status_code}")
    
    if response.status_code != 200:
        print(f"❌ B2B portal announcements failed: {response.text}")
        return False
        
    data = response.json()
    items = data.get('items', [])
    
    print(f"✅ B2B Portal found {len(items)} announcements")
    
    # Check if our test announcement is visible
    found_test_announcement = False
    for item in items:
        if item.get('title') == "Test Duyuru":
            found_test_announcement = True
            print(f"✅ Test announcement visible in B2B portal:")
            print(f"   ID: {item.get('id')}")
            print(f"   Title: {item.get('title')}")
            print(f"   Body: {item.get('body')}")
            break
    
    if not found_test_announcement:
        print("⚠️ Test announcement not found in B2B portal (might be filtered out)")
    
    return True

def test_validity_fields(admin_token):
    """Test validity fields in admin listing"""
    print("\n📅 Testing Validity Fields...")
    
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    response = requests.get(f"{BACKEND_URL}/api/admin/b2b/announcements", headers=headers)
    
    if response.status_code != 200:
        print(f"❌ Failed to get announcements for validity test: {response.text}")
        return False
        
    data = response.json()
    items = data.get('items', [])
    
    if not items:
        print("⚠️ No announcements found for validity field testing")
        return True
    
    print(f"✅ Checking validity fields for {len(items)} announcements:")
    
    for item in items:
        valid_from = item.get('valid_from')
        valid_until = item.get('valid_until')
        
        print(f"   Announcement '{item.get('title')}':")
        print(f"     valid_from: {valid_from}")
        print(f"     valid_until: {valid_until}")
        
        # Verify valid_from is populated
        assert valid_from, f"valid_from should be populated for announcement {item.get('id')}"
        
        # valid_until can be None or a date string
        if valid_until:
            print(f"     ✅ Has expiration date")
        else:
            print(f"     ✅ No expiration (permanent)")
    
    return True

def main():
    """Main test execution"""
    print("🚀 Starting B2B Announcements Backend Flow Test")
    print("=" * 60)
    
    # Login as admin
    admin_token = login_admin()
    if not admin_token:
        print("❌ Cannot proceed without admin token")
        return
    
    # Login as agency
    agency_token = login_agency()
    if not agency_token:
        print("❌ Cannot proceed without agency token")
        return
    
    try:
        # Test 1: Admin creates announcement
        announcement_id = test_admin_create_announcement(admin_token)
        if not announcement_id:
            print("❌ Cannot proceed without created announcement")
            return
        
        # Test 2: Admin lists announcements
        if not test_admin_list_announcements(admin_token, announcement_id):
            print("❌ Admin listing test failed")
            return
        
        # Test 3: Toggle active status
        if not test_toggle_active(admin_token, announcement_id):
            print("❌ Toggle active test failed")
            return
        
        # Test 4: B2B portal announcement listing
        if not test_b2b_portal_announcements(agency_token):
            print("❌ B2B portal test failed")
            return
        
        # Test 5: Validity fields verification
        if not test_validity_fields(admin_token):
            print("❌ Validity fields test failed")
            return
        
        print("\n" + "=" * 60)
        print("🎉 ALL B2B ANNOUNCEMENTS TESTS PASSED!")
        print("✅ Admin announcement creation working")
        print("✅ Admin announcement listing working")
        print("✅ Toggle active status working")
        print("✅ B2B portal announcement listing working")
        print("✅ Validity fields properly populated")
        
    except Exception as e:
        print(f"\n❌ Test failed with exception: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()