#!/usr/bin/env python3
"""
B2B Announcements Debug Test - Investigate why B2B portal doesn't show announcements
"""

import requests
import json

# Backend URL from frontend/.env
BACKEND_URL = "https://enterprise-ops-8.preview.emergentagent.com"

def login_admin():
    """Login as admin and return JWT token and user info"""
    login_data = {
        "email": "admin@acenta.test",
        "password": "admin123"
    }
    
    response = requests.post(f"{BACKEND_URL}/api/auth/login", json=login_data)
    if response.status_code != 200:
        return None, None
        
    data = response.json()
    token = data.get("access_token")
    
    # Get user info
    headers = {"Authorization": f"Bearer {token}"}
    user_response = requests.get(f"{BACKEND_URL}/api/auth/me", headers=headers)
    user_info = user_response.json() if user_response.status_code == 200 else {}
    
    return token, user_info

def login_agency():
    """Login as agency user and return JWT token and user info"""
    login_data = {
        "email": "agency1@demo.test", 
        "password": "agency123"
    }
    
    response = requests.post(f"{BACKEND_URL}/api/auth/login", json=login_data)
    if response.status_code != 200:
        return None, None
        
    data = response.json()
    token = data.get("access_token")
    
    # Get user info
    headers = {"Authorization": f"Bearer {token}"}
    user_response = requests.get(f"{BACKEND_URL}/api/auth/me", headers=headers)
    user_info = user_response.json() if user_response.status_code == 200 else {}
    
    return token, user_info

def create_announcement_for_agency(admin_token, agency_id, org_id):
    """Create announcement specifically for an agency"""
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    payload = {
        "title": "Agency Specific Test",
        "body": "Bu agency'ye özel test duyurusudur.",
        "audience": "agency",
        "agency_id": agency_id,
        "days_valid": 7
    }
    
    response = requests.post(f"{BACKEND_URL}/api/admin/b2b/announcements", 
                           json=payload, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Agency-specific announcement created: {data.get('id')}")
        return data.get('id')
    else:
        print(f"❌ Failed to create agency announcement: {response.text}")
        return None

def main():
    print("🔍 B2B Announcements Debug Test")
    print("=" * 50)
    
    # Login both users
    admin_token, admin_info = login_admin()
    agency_token, agency_info = login_agency()
    
    if not admin_token or not agency_token:
        print("❌ Failed to login")
        return
    
    print(f"Admin org: {admin_info.get('organization_id')}")
    print(f"Agency org: {agency_info.get('organization_id')}")
    print(f"Agency ID: {agency_info.get('agency_id')}")
    
    # Check if organizations match
    admin_org = admin_info.get('organization_id')
    agency_org = agency_info.get('organization_id')
    agency_id = agency_info.get('agency_id')
    
    if admin_org != agency_org:
        print(f"⚠️ Organization mismatch! Admin: {admin_org}, Agency: {agency_org}")
    else:
        print(f"✅ Organizations match: {admin_org}")
    
    # Create announcements for testing
    print("\n📝 Creating test announcements...")
    
    # 1. Create "all" audience announcement
    headers = {"Authorization": f"Bearer {admin_token}"}
    all_payload = {
        "title": "All Users Announcement",
        "body": "Bu tüm kullanıcılar için duyurudur.",
        "audience": "all",
        "days_valid": 7
    }
    
    all_response = requests.post(f"{BACKEND_URL}/api/admin/b2b/announcements", 
                               json=all_payload, headers=headers)
    
    if all_response.status_code == 200:
        all_data = all_response.json()
        print(f"✅ 'All' announcement created: {all_data.get('id')}")
    else:
        print(f"❌ Failed to create 'all' announcement: {all_response.text}")
    
    # 2. Create agency-specific announcement if we have agency_id
    if agency_id:
        agency_announcement_id = create_announcement_for_agency(admin_token, agency_id, agency_org)
    else:
        print("⚠️ No agency_id found, skipping agency-specific announcement")
    
    # 3. List all announcements from admin view
    print("\n📋 Admin view of all announcements:")
    admin_list_response = requests.get(f"{BACKEND_URL}/api/admin/b2b/announcements", headers=headers)
    
    if admin_list_response.status_code == 200:
        admin_data = admin_list_response.json()
        items = admin_data.get('items', [])
        print(f"Found {len(items)} announcements:")
        
        for item in items:
            print(f"  - ID: {item.get('id')}")
            print(f"    Title: {item.get('title')}")
            print(f"    Audience: {item.get('audience')}")
            print(f"    Agency ID: {item.get('agency_id')}")
            print(f"    Is Active: {item.get('is_active')}")
            print(f"    Valid From: {item.get('valid_from')}")
            print(f"    Valid Until: {item.get('valid_until')}")
            print()
    
    # 4. Check B2B portal view
    print("🏢 B2B Portal view:")
    agency_headers = {"Authorization": f"Bearer {agency_token}"}
    b2b_response = requests.get(f"{BACKEND_URL}/api/b2b/announcements", headers=agency_headers)
    
    if b2b_response.status_code == 200:
        b2b_data = b2b_response.json()
        b2b_items = b2b_data.get('items', [])
        print(f"B2B Portal shows {len(b2b_items)} announcements:")
        
        for item in b2b_items:
            print(f"  - ID: {item.get('id')}")
            print(f"    Title: {item.get('title')}")
            print(f"    Body: {item.get('body')}")
            print()
    else:
        print(f"❌ B2B portal request failed: {b2b_response.text}")
    
    print("\n🔍 Analysis complete!")

if __name__ == "__main__":
    main()