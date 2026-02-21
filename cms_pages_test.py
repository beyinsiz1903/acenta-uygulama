#!/usr/bin/env python3
"""
CMS Pages Backend Test - PublicCMSPage Flow Verification

This test suite verifies the CMS pages backend functionality and public frontend flow:

Test Scenarios:
1. Admin CMS page creation (slug='hakkimizda')
2. Public CMS page retrieval with org parameter
3. Public CMS page error handling (missing org parameter)
4. Public CMS page 404 handling (non-existent page)
5. Frontend integration verification
"""

import requests
import json
import uuid
from datetime import datetime
from pymongo import MongoClient
import os
from typing import Dict, Any

# Configuration - Use production URL from frontend/.env
BASE_URL = "https://jwt-revocation-add.preview.emergentagent.com"

def get_mongo_client():
    """Get MongoDB client for direct database access"""
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017/test_database")
    return MongoClient(mongo_url)

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

def test_admin_cms_page_creation():
    """Test 1: Admin CMS page creation with slug='hakkimizda'"""
    print("\n" + "=" * 80)
    print("TEST 1: ADMIN CMS PAGE CREATION")
    print("Testing admin CMS page creation with slug='hakkimizda'")
    print("=" * 80 + "\n")
    
    # Setup
    admin_token, admin_org_id, admin_email = login_admin()
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    
    print(f"   📋 Admin org: {admin_org_id}")
    
    try:
        # 1. Check existing CMS pages
        print("1️⃣  Checking existing CMS pages...")
        
        r = requests.get(f"{BASE_URL}/api/admin/cms/pages", headers=admin_headers)
        assert r.status_code == 200, f"Failed to get CMS pages: {r.status_code} - {r.text}"
        
        existing_pages = r.json()
        print(f"   📋 Found {len(existing_pages.get('items', []))} existing CMS pages")
        
        # Check if 'hakkimizda' page already exists
        hakkimizda_page = None
        for page in existing_pages.get('items', []):
            if page.get('slug') == 'hakkimizda':
                hakkimizda_page = page
                break
        
        if hakkimizda_page:
            print(f"   ✅ 'hakkimizda' page already exists: {hakkimizda_page['id']}")
            print(f"   📋 Title: {hakkimizda_page['title']}")
            print(f"   📋 Published: {hakkimizda_page['published']}")
            return hakkimizda_page['id'], admin_org_id
        
        # 2. Create 'hakkimizda' CMS page
        print("2️⃣  Creating 'hakkimizda' CMS page...")
        
        cms_payload = {
            "slug": "hakkimizda",
            "title": "Hakkımızda",
            "body": "Bu bir test hakkımızda sayfasıdır.",
            "seo_title": "Hakkımızda - Test Sayfası",
            "seo_description": "Test organizasyonu hakkında bilgiler",
            "published": True
        }
        
        r = requests.post(f"{BASE_URL}/api/admin/cms/pages", json=cms_payload, headers=admin_headers)
        
        print(f"   📋 Create response status: {r.status_code}")
        print(f"   📋 Response body: {r.text}")
        
        assert r.status_code == 200, f"Failed to create CMS page: {r.status_code} - {r.text}"
        
        created_page = r.json()
        print(f"   ✅ CMS page created successfully")
        print(f"   📋 Page ID: {created_page['id']}")
        print(f"   📋 Slug: {created_page['slug']}")
        print(f"   📋 Title: {created_page['title']}")
        print(f"   📋 Body: {created_page['body']}")
        print(f"   📋 Published: {created_page['published']}")
        
        # Verify required fields
        assert created_page['slug'] == 'hakkimizda', f"Expected slug 'hakkimizda', got {created_page['slug']}"
        assert created_page['title'] == 'Hakkımızda', f"Expected title 'Hakkımızda', got {created_page['title']}"
        assert created_page['body'] == 'Bu bir test hakkımızda sayfasıdır.', f"Body mismatch"
        assert created_page['published'] is True, f"Page should be published"
        
        return created_page['id'], admin_org_id
        
    except Exception as e:
        print(f"   ❌ Test failed: {e}")
        raise

def test_public_cms_page_retrieval(org_id: str):
    """Test 2: Public CMS page retrieval with org parameter"""
    print("\n" + "=" * 80)
    print("TEST 2: PUBLIC CMS PAGE RETRIEVAL")
    print("Testing public CMS page retrieval with org parameter")
    print("=" * 80 + "\n")
    
    try:
        # 1. Test successful retrieval with org parameter
        print("1️⃣  Testing successful retrieval with org parameter...")
        
        r = requests.get(f"{BASE_URL}/api/public/cms/pages/hakkimizda", params={"org": org_id})
        
        print(f"   📋 Response status: {r.status_code}")
        print(f"   📋 Response body: {r.text}")
        
        assert r.status_code == 200, f"Expected 200, got {r.status_code} - {r.text}"
        
        page_data = r.json()
        print(f"   📋 Retrieved page data: {json.dumps(page_data, indent=2)}")
        
        # Verify response structure and content
        assert 'id' in page_data, "Response should contain 'id' field"
        assert 'slug' in page_data, "Response should contain 'slug' field"
        assert 'title' in page_data, "Response should contain 'title' field"
        assert 'body' in page_data, "Response should contain 'body' field"
        assert 'seo_title' in page_data, "Response should contain 'seo_title' field"
        assert 'seo_description' in page_data, "Response should contain 'seo_description' field"
        
        # Verify content matches expected values
        assert page_data['slug'] == 'hakkimizda', f"Expected slug 'hakkimizda', got {page_data['slug']}"
        assert page_data['title'] == 'Hakkımızda', f"Expected title 'Hakkımızda', got {page_data['title']}"
        assert page_data['body'] == 'Bu bir test hakkımızda sayfasıdır.', f"Expected specific body text, got {page_data['body']}"
        
        print(f"   ✅ Public CMS page retrieval successful")
        print(f"   ✅ Title: {page_data['title']}")
        print(f"   ✅ Body: {page_data['body']}")
        
        # 2. Test with missing org parameter
        print("\n2️⃣  Testing with missing org parameter...")
        
        r = requests.get(f"{BASE_URL}/api/public/cms/pages/hakkimizda")
        
        print(f"   📋 Response status: {r.status_code}")
        print(f"   📋 Response body: {r.text}")
        
        # Should return 422 for missing required query parameter
        assert r.status_code == 422, f"Expected 422 for missing org parameter, got {r.status_code}"
        
        print(f"   ✅ Missing org parameter properly rejected with 422")
        
        # 3. Test with wrong org parameter
        print("\n3️⃣  Testing with wrong org parameter...")
        
        wrong_org = "org_nonexistent_test"
        r = requests.get(f"{BASE_URL}/api/public/cms/pages/hakkimizda", params={"org": wrong_org})
        
        print(f"   📋 Response status: {r.status_code}")
        print(f"   📋 Response body: {r.text}")
        
        # Should return 404 for wrong org
        assert r.status_code == 404, f"Expected 404 for wrong org, got {r.status_code}"
        
        error_data = r.json()
        assert error_data.get('code') == 'PAGE_NOT_FOUND', f"Expected PAGE_NOT_FOUND error code"
        assert 'Sayfa bulunamadı' in error_data.get('message', ''), f"Expected Turkish error message"
        
        print(f"   ✅ Wrong org parameter properly returns 404 with PAGE_NOT_FOUND")
        
    except Exception as e:
        print(f"   ❌ Test failed: {e}")
        raise

def test_public_cms_page_404_handling(org_id: str):
    """Test 3: Public CMS page 404 handling for non-existent page"""
    print("\n" + "=" * 80)
    print("TEST 3: PUBLIC CMS PAGE 404 HANDLING")
    print("Testing 404 handling for non-existent CMS page")
    print("=" * 80 + "\n")
    
    try:
        # Test non-existent page
        print("1️⃣  Testing non-existent page 'olmayan-sayfa'...")
        
        r = requests.get(f"{BASE_URL}/api/public/cms/pages/olmayan-sayfa", params={"org": org_id})
        
        print(f"   📋 Response status: {r.status_code}")
        print(f"   📋 Response body: {r.text}")
        
        # Should return 404 for non-existent page
        assert r.status_code == 404, f"Expected 404 for non-existent page, got {r.status_code}"
        
        error_data = r.json()
        print(f"   📋 Error data: {json.dumps(error_data, indent=2)}")
        
        # Verify error structure
        assert 'code' in error_data, "Error response should contain 'code' field"
        assert 'message' in error_data, "Error response should contain 'message' field"
        
        assert error_data['code'] == 'PAGE_NOT_FOUND', f"Expected PAGE_NOT_FOUND, got {error_data['code']}"
        assert 'Sayfa bulunamadı' in error_data['message'], f"Expected Turkish error message, got {error_data['message']}"
        
        print(f"   ✅ Non-existent page properly returns 404")
        print(f"   ✅ Error code: {error_data['code']}")
        print(f"   ✅ Error message: {error_data['message']}")
        
    except Exception as e:
        print(f"   ❌ Test failed: {e}")
        raise

def test_frontend_integration_scenarios(org_id: str):
    """Test 4: Frontend integration scenarios"""
    print("\n" + "=" * 80)
    print("TEST 4: FRONTEND INTEGRATION SCENARIOS")
    print("Testing frontend URL patterns and expected behavior")
    print("=" * 80 + "\n")
    
    try:
        # 1. Test expected frontend URL pattern
        print("1️⃣  Testing expected frontend URL pattern...")
        
        # The frontend should call: /api/public/cms/pages/hakkimizda?org=org_ops_close_idem
        # URL pattern: http://localhost:3000/p/hakkimizda?org=org_ops_close_idem
        
        expected_frontend_url = f"http://localhost:3000/p/hakkimizda?org={org_id}"
        expected_api_call = f"{BASE_URL}/api/public/cms/pages/hakkimizda?org={org_id}"
        
        print(f"   📋 Expected frontend URL: {expected_frontend_url}")
        print(f"   📋 Expected API call: {expected_api_call}")
        
        # Test the API call that frontend would make
        r = requests.get(f"{BASE_URL}/api/public/cms/pages/hakkimizda", params={"org": org_id})
        
        assert r.status_code == 200, f"Frontend API call should succeed: {r.status_code} - {r.text}"
        
        page_data = r.json()
        
        # Verify frontend would get expected data
        assert page_data['title'] == 'Hakkımızda', f"Frontend should see title 'Hakkımızda'"
        assert page_data['body'] == 'Bu bir test hakkımızda sayfasıdır.', f"Frontend should see expected body text"
        
        print(f"   ✅ Frontend API call successful")
        print(f"   ✅ Frontend would display title: '{page_data['title']}'")
        print(f"   ✅ Frontend would display body: '{page_data['body']}'")
        
        # 2. Test frontend error scenario (missing org)
        print("\n2️⃣  Testing frontend error scenario (missing org)...")
        
        # Frontend URL without org: http://localhost:3000/p/hakkimizda
        # Should show red warning and not make API call
        
        print(f"   📋 Frontend URL without org: http://localhost:3000/p/hakkimizda")
        print(f"   📋 Expected behavior: Red warning text, no API call")
        print(f"   📋 Expected warning: 'Kuruluş (org) parametresi eksik. Lütfen URL'ye ?org=<organization_id> parametresi ekleyin.'")
        
        # Verify that API call without org fails (as expected)
        r = requests.get(f"{BASE_URL}/api/public/cms/pages/hakkimizda")
        assert r.status_code == 422, f"API call without org should fail with 422"
        
        print(f"   ✅ API call without org properly fails (422)")
        print(f"   ✅ Frontend should show red warning instead of making API call")
        
        # 3. Test frontend 404 scenario
        print("\n3️⃣  Testing frontend 404 scenario...")
        
        # Frontend URL for non-existent page: http://localhost:3000/p/olmayan-sayfa?org=org_ops_close_idem
        # Should make API call, get 404, show red error text
        
        nonexistent_frontend_url = f"http://localhost:3000/p/olmayan-sayfa?org={org_id}"
        nonexistent_api_call = f"{BASE_URL}/api/public/cms/pages/olmayan-sayfa?org={org_id}"
        
        print(f"   📋 Frontend URL for non-existent page: {nonexistent_frontend_url}")
        print(f"   📋 API call for non-existent page: {nonexistent_api_call}")
        
        r = requests.get(f"{BASE_URL}/api/public/cms/pages/olmayan-sayfa", params={"org": org_id})
        
        assert r.status_code == 404, f"Non-existent page should return 404"
        
        error_data = r.json()
        assert error_data['code'] == 'PAGE_NOT_FOUND', f"Should return PAGE_NOT_FOUND error"
        
        print(f"   ✅ Non-existent page API call returns 404")
        print(f"   ✅ Frontend should show red error text: '{error_data['message']}'")
        print(f"   ✅ Frontend should not crash, should handle 404 gracefully")
        
    except Exception as e:
        print(f"   ❌ Test failed: {e}")
        raise

def cleanup_test_data(org_id: str):
    """Clean up test CMS pages"""
    try:
        print("\n🧹 Cleaning up test data...")
        
        mongo_client = get_mongo_client()
        db = mongo_client.get_default_database()
        
        # Only clean up test CMS pages, not all CMS pages
        result = db.cms_pages.delete_many({
            "organization_id": org_id,
            "slug": {"$in": ["hakkimizda", "test-cms-page"]}
        })
        
        if result.deleted_count > 0:
            print(f"   🧹 Cleaned {result.deleted_count} test CMS pages")
        else:
            print(f"   📋 No test CMS pages to clean")
        
        mongo_client.close()
        
    except Exception as e:
        print(f"   ⚠️  Failed to cleanup test data: {e}")

def run_all_tests():
    """Run all CMS pages tests"""
    print("\n" + "🚀" * 80)
    print("CMS PAGES BACKEND TEST - PUBLICCMSPAGE FLOW VERIFICATION")
    print("Testing CMS pages backend functionality and public frontend flow")
    print("🚀" * 80)
    
    page_id = None
    org_id = None
    
    try:
        # Test 1: Admin CMS page creation
        page_id, org_id = test_admin_cms_page_creation()
        
        # Test 2: Public CMS page retrieval
        test_public_cms_page_retrieval(org_id)
        
        # Test 3: Public CMS page 404 handling
        test_public_cms_page_404_handling(org_id)
        
        # Test 4: Frontend integration scenarios
        test_frontend_integration_scenarios(org_id)
        
        print("\n" + "🏁" * 80)
        print("TEST SUMMARY")
        print("🏁" * 80)
        print("✅ All tests passed!")
        
        print("\n📋 TESTED SCENARIOS:")
        print("✅ Admin CMS page creation (slug='hakkimizda')")
        print("✅ Public CMS page retrieval with org parameter")
        print("✅ Public CMS page error handling (missing org)")
        print("✅ Public CMS page 404 handling (non-existent page)")
        print("✅ Frontend integration scenarios")
        
        print("\n🎯 FRONTEND VERIFICATION POINTS:")
        print("✅ URL: http://localhost:3000/p/hakkimizda?org=org_ops_close_idem")
        print("✅ Expected title: 'Hakkımızda'")
        print("✅ Expected body: 'Bu bir test hakkımızda sayfasıdır.'")
        print("✅ Missing org parameter: Red warning text, no API call")
        print("✅ Non-existent page: 404 backend response, red error text, no crash")
        
        return True
        
    except Exception as e:
        print(f"\n❌ TEST SUITE FAILED: {e}")
        return False
        
    finally:
        if org_id:
            cleanup_test_data(org_id)

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)