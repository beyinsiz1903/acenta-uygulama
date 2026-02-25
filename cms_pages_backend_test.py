#!/usr/bin/env python3
"""
CMS Pages Backend Flow Test

This test suite verifies the CMS pages backend functionality:
1. Admin - CMS page creation (POST /api/admin/cms/pages)
2. Admin - List CMS pages (GET /api/admin/cms/pages)
3. Public - Get CMS page (GET /api/public/cms/pages/{slug}?org=...)
4. Test 404 for non-existent page

Test Scenarios:
- Admin login and CMS page creation
- Admin listing of created pages
- Public access to published pages
- 404 handling for non-existent pages
"""

import requests
import json
import uuid
from datetime import datetime
from pymongo import MongoClient
import os
from typing import Dict, Any

# Configuration - Use production URL from frontend/.env
BASE_URL = "https://redis-cache-upgrade.preview.emergentagent.com"

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

def cleanup_test_cms_pages(org_id: str):
    """Clean up test CMS pages after testing"""
    try:
        mongo_client = get_mongo_client()
        db = mongo_client.get_default_database()
        
        # Clean up test CMS pages
        result = db.cms_pages.delete_many({
            "organization_id": org_id,
            "slug": {"$in": ["hakkimizda", "test-page-1", "test-page-2"]}
        })
        
        if result.deleted_count > 0:
            print(f"   🧹 Cleaned {result.deleted_count} test CMS pages")
        
        mongo_client.close()
        print(f"   ✅ Cleanup completed for org: {org_id}")
        
    except Exception as e:
        print(f"   ⚠️  Failed to cleanup test CMS pages: {e}")

def test_admin_cms_page_creation():
    """Test 1: Admin - CMS page creation"""
    print("\n" + "=" * 80)
    print("TEST 1: ADMIN CMS PAGE CREATION")
    print("Testing POST /api/admin/cms/pages")
    print("=" * 80 + "\n")
    
    # Setup
    admin_token, admin_org_id, admin_email = login_admin()
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    
    print(f"   📋 Admin logged in: {admin_email}")
    print(f"   📋 Organization ID: {admin_org_id}")
    
    try:
        # 1. Create CMS page
        print("1️⃣  Creating CMS page 'hakkimizda'...")
        
        cms_payload = {
            "slug": "hakkimizda",
            "title": "Hakkımızda",
            "body": "Bu bir test hakkımızda sayfasıdır.",
            "seo_title": "Hakkımızda - Test Sayfası",
            "seo_description": "Test organizasyonu hakkında bilgiler",
            "published": True
        }
        
        r = requests.post(
            f"{BASE_URL}/api/admin/cms/pages",
            json=cms_payload,
            headers=admin_headers
        )
        
        print(f"   📋 Response status: {r.status_code}")
        print(f"   📋 Response body: {r.text}")
        
        assert r.status_code == 200, f"CMS page creation failed: {r.status_code} - {r.text}"
        
        data = r.json()
        print(f"   📋 Parsed response: {json.dumps(data, indent=2)}")
        
        # Verify response structure
        assert "id" in data, "Response should contain 'id' field"
        assert "slug" in data, "Response should contain 'slug' field"
        assert "title" in data, "Response should contain 'title' field"
        assert "created_at" in data, "Response should contain 'created_at' field"
        assert "updated_at" in data, "Response should contain 'updated_at' field"
        
        # Verify field values
        assert data["slug"] == "hakkimizda", f"Expected slug 'hakkimizda', got {data['slug']}"
        assert data["title"] == "Hakkımızda", f"Expected title 'Hakkımızda', got {data['title']}"
        assert data["body"] == "Bu bir test hakkımızda sayfasıdır.", f"Body mismatch"
        assert data["published"] == True, f"Expected published=True, got {data['published']}"
        
        page_id = data["id"]
        print(f"   ✅ CMS page created successfully")
        print(f"   📋 Page ID: {page_id}")
        print(f"   📋 Slug: {data['slug']}")
        print(f"   📋 Title: {data['title']}")
        print(f"   📋 Published: {data['published']}")
        
        return page_id, admin_org_id, admin_headers
        
    except Exception as e:
        cleanup_test_cms_pages(admin_org_id)
        raise e

def test_admin_cms_pages_listing(admin_org_id: str, admin_headers: Dict[str, str]):
    """Test 2: Admin - List CMS pages"""
    print("\n" + "=" * 80)
    print("TEST 2: ADMIN CMS PAGES LISTING")
    print("Testing GET /api/admin/cms/pages")
    print("=" * 80 + "\n")
    
    # 1. List CMS pages
    print("1️⃣  Listing CMS pages...")
    
    r = requests.get(
        f"{BASE_URL}/api/admin/cms/pages",
        headers=admin_headers
    )
    
    print(f"   📋 Response status: {r.status_code}")
    print(f"   📋 Response body: {r.text}")
    
    assert r.status_code == 200, f"CMS pages listing failed: {r.status_code} - {r.text}"
    
    data = r.json()
    print(f"   📋 Parsed response: {json.dumps(data, indent=2)}")
    
    # Verify response structure
    assert "items" in data, "Response should contain 'items' field"
    assert isinstance(data["items"], list), "Items should be a list"
    
    # Find our created page
    hakkimizda_page = None
    for item in data["items"]:
        if item.get("slug") == "hakkimizda":
            hakkimizda_page = item
            break
    
    assert hakkimizda_page is not None, "Created 'hakkimizda' page should be in the list"
    
    # Verify page structure in list
    assert "id" in hakkimizda_page, "List item should contain 'id' field"
    assert "slug" in hakkimizda_page, "List item should contain 'slug' field"
    assert "title" in hakkimizda_page, "List item should contain 'title' field"
    assert "published" in hakkimizda_page, "List item should contain 'published' field"
    assert "created_at" in hakkimizda_page, "List item should contain 'created_at' field"
    assert "updated_at" in hakkimizda_page, "List item should contain 'updated_at' field"
    
    # Verify field values
    assert hakkimizda_page["slug"] == "hakkimizda", f"Expected slug 'hakkimizda', got {hakkimizda_page['slug']}"
    assert hakkimizda_page["title"] == "Hakkımızda", f"Expected title 'Hakkımızda', got {hakkimizda_page['title']}"
    assert hakkimizda_page["published"] == True, f"Expected published=True, got {hakkimizda_page['published']}"
    
    print(f"   ✅ CMS pages listing verified")
    print(f"   📋 Total pages: {len(data['items'])}")
    print(f"   📋 Found 'hakkimizda' page in list")
    print(f"   📋 Page ID: {hakkimizda_page['id']}")
    print(f"   📋 Created at: {hakkimizda_page['created_at']}")

def test_public_cms_page_access(admin_org_id: str):
    """Test 3: Public - Get CMS page"""
    print("\n" + "=" * 80)
    print("TEST 3: PUBLIC CMS PAGE ACCESS")
    print("Testing GET /api/public/cms/pages/{slug}?org=...")
    print("=" * 80 + "\n")
    
    # 1. Access published CMS page
    print("1️⃣  Accessing published CMS page 'hakkimizda'...")
    
    r = requests.get(f"{BASE_URL}/api/public/cms/pages/hakkimizda?org={admin_org_id}")
    
    print(f"   📋 Response status: {r.status_code}")
    print(f"   📋 Response body: {r.text}")
    
    assert r.status_code == 200, f"Public CMS page access failed: {r.status_code} - {r.text}"
    
    data = r.json()
    print(f"   📋 Parsed response: {json.dumps(data, indent=2)}")
    
    # Verify response structure
    assert "id" in data, "Response should contain 'id' field"
    assert "slug" in data, "Response should contain 'slug' field"
    assert "title" in data, "Response should contain 'title' field"
    assert "body" in data, "Response should contain 'body' field"
    assert "seo_title" in data, "Response should contain 'seo_title' field"
    assert "seo_description" in data, "Response should contain 'seo_description' field"
    
    # Verify field values
    assert data["slug"] == "hakkimizda", f"Expected slug 'hakkimizda', got {data['slug']}"
    assert data["title"] == "Hakkımızda", f"Expected title 'Hakkımızda', got {data['title']}"
    assert data["body"] == "Bu bir test hakkımızda sayfasıdır.", f"Body mismatch"
    assert data["seo_title"] == "Hakkımızda - Test Sayfası", f"SEO title mismatch"
    assert data["seo_description"] == "Test organizasyonu hakkında bilgiler", f"SEO description mismatch"
    
    print(f"   ✅ Public CMS page access verified")
    print(f"   📋 Page ID: {data['id']}")
    print(f"   📋 Slug: {data['slug']}")
    print(f"   📋 Title: {data['title']}")
    print(f"   📋 Body length: {len(data['body'])} characters")
    print(f"   📋 SEO title: {data['seo_title']}")

def test_public_cms_page_not_found(admin_org_id: str):
    """Test 4: Public - 404 for non-existent page"""
    print("\n" + "=" * 80)
    print("TEST 4: PUBLIC CMS PAGE NOT FOUND")
    print("Testing GET /api/public/cms/pages/olmayan-sayfa?org=...")
    print("=" * 80 + "\n")
    
    # 1. Access non-existent CMS page
    print("1️⃣  Accessing non-existent CMS page 'olmayan-sayfa'...")
    
    r = requests.get(f"{BASE_URL}/api/public/cms/pages/olmayan-sayfa?org={admin_org_id}")
    
    print(f"   📋 Response status: {r.status_code}")
    print(f"   📋 Response body: {r.text}")
    
    assert r.status_code == 404, f"Expected 404, got {r.status_code}"
    
    data = r.json()
    print(f"   📋 Parsed response: {json.dumps(data, indent=2)}")
    
    # Verify error response structure
    assert "code" in data, "Error response should contain 'code' field"
    assert "message" in data, "Error response should contain 'message' field"
    
    # Verify error values
    assert data["code"] == "PAGE_NOT_FOUND", f"Expected code 'PAGE_NOT_FOUND', got {data['code']}"
    assert data["message"] == "Sayfa bulunamadı", f"Expected Turkish message, got {data['message']}"
    
    print(f"   ✅ 404 error handling verified")
    print(f"   📋 Error code: {data['code']}")
    print(f"   📋 Error message: {data['message']}")

def test_additional_scenarios(admin_org_id: str, admin_headers: Dict[str, str]):
    """Test 5: Additional scenarios - validation, multiple pages"""
    print("\n" + "=" * 80)
    print("TEST 5: ADDITIONAL SCENARIOS")
    print("Testing validation and multiple pages")
    print("=" * 80 + "\n")
    
    # 1. Test validation - missing required fields
    print("1️⃣  Testing validation - missing slug...")
    
    invalid_payload = {
        "title": "Test Page Without Slug",
        "body": "This page has no slug"
    }
    
    r = requests.post(
        f"{BASE_URL}/api/admin/cms/pages",
        json=invalid_payload,
        headers=admin_headers
    )
    
    print(f"   📋 Response status: {r.status_code}")
    print(f"   📋 Response body: {r.text}")
    
    assert r.status_code == 400, f"Expected 400 for missing slug, got {r.status_code}"
    
    data = r.json()
    assert "error" in data or "detail" in data, "Should return error for missing slug"
    print(f"   ✅ Validation working - missing slug rejected")
    
    # 2. Create additional test pages
    print("\n2️⃣  Creating additional test pages...")
    
    test_pages = [
        {
            "slug": "test-page-1",
            "title": "Test Page 1",
            "body": "Content for test page 1",
            "published": True
        },
        {
            "slug": "test-page-2", 
            "title": "Test Page 2",
            "body": "Content for test page 2",
            "published": False  # Unpublished
        }
    ]
    
    created_pages = []
    for page_data in test_pages:
        r = requests.post(
            f"{BASE_URL}/api/admin/cms/pages",
            json=page_data,
            headers=admin_headers
        )
        
        assert r.status_code == 200, f"Failed to create {page_data['slug']}: {r.status_code} - {r.text}"
        
        data = r.json()
        created_pages.append(data)
        print(f"   ✅ Created page: {data['slug']} (published: {data['published']})")
    
    # 3. Verify unpublished page is not accessible publicly
    print("\n3️⃣  Testing unpublished page access...")
    
    r = requests.get(f"{BASE_URL}/api/public/cms/pages/test-page-2?org={admin_org_id}")
    
    print(f"   📋 Response status: {r.status_code}")
    
    assert r.status_code == 404, f"Unpublished page should return 404, got {r.status_code}"
    
    data = r.json()
    assert data["code"] == "PAGE_NOT_FOUND", "Should return PAGE_NOT_FOUND for unpublished page"
    print(f"   ✅ Unpublished page correctly returns 404")
    
    # 4. Verify published page is accessible
    print("\n4️⃣  Testing published page access...")
    
    r = requests.get(f"{BASE_URL}/api/public/cms/pages/test-page-1?org={admin_org_id}")
    
    assert r.status_code == 200, f"Published page should be accessible, got {r.status_code}"
    
    data = r.json()
    assert data["slug"] == "test-page-1", "Should return correct page data"
    assert data["title"] == "Test Page 1", "Should return correct title"
    print(f"   ✅ Published page correctly accessible")
    
    # 5. Verify all pages in admin list
    print("\n5️⃣  Verifying all pages in admin list...")
    
    r = requests.get(f"{BASE_URL}/api/admin/cms/pages", headers=admin_headers)
    
    assert r.status_code == 200, f"Admin list should work, got {r.status_code}"
    
    data = r.json()
    page_slugs = [item["slug"] for item in data["items"]]
    
    expected_slugs = ["hakkimizda", "test-page-1", "test-page-2"]
    for slug in expected_slugs:
        assert slug in page_slugs, f"Page {slug} should be in admin list"
    
    print(f"   ✅ All test pages found in admin list")
    print(f"   📋 Total pages in list: {len(data['items'])}")
    print(f"   📋 Test page slugs: {[slug for slug in page_slugs if slug in expected_slugs]}")

def run_all_cms_tests():
    """Run all CMS pages backend tests"""
    print("\n" + "🚀" * 80)
    print("CMS PAGES BACKEND FLOW TEST")
    print("Testing admin CMS page creation, listing, and public access")
    print("🚀" * 80)
    
    admin_org_id = None
    
    try:
        # Test 1: Admin CMS page creation
        page_id, admin_org_id, admin_headers = test_admin_cms_page_creation()
        
        # Test 2: Admin listing
        test_admin_cms_pages_listing(admin_org_id, admin_headers)
        
        # Test 3: Public access
        test_public_cms_page_access(admin_org_id)
        
        # Test 4: 404 handling
        test_public_cms_page_not_found(admin_org_id)
        
        # Test 5: Additional scenarios
        test_additional_scenarios(admin_org_id, admin_headers)
        
        print("\n" + "🏁" * 80)
        print("TEST SUMMARY")
        print("🏁" * 80)
        print("✅ All CMS pages backend tests passed!")
        
        print("\n📋 TESTED SCENARIOS:")
        print("✅ Admin login with admin@acenta.test/admin123")
        print("✅ POST /api/admin/cms/pages - CMS page creation")
        print("✅ GET /api/admin/cms/pages - CMS pages listing")
        print("✅ GET /api/public/cms/pages/{slug}?org=... - Public page access")
        print("✅ 404 handling for non-existent pages")
        print("✅ Validation for missing required fields")
        print("✅ Published vs unpublished page access control")
        print("✅ Multiple pages creation and listing")
        print("✅ Turkish character support in content")
        print("✅ SEO fields (seo_title, seo_description)")
        
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        return False
        
    finally:
        if admin_org_id:
            cleanup_test_cms_pages(admin_org_id)

if __name__ == "__main__":
    success = run_all_cms_tests()
    exit(0 if success else 1)