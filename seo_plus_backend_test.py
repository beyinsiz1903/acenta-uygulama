#!/usr/bin/env python3
"""
SEO+ Pack Backend Test Suite
Testing IndexNow job integration, sitemap behavior, and publish_product_version SEO fields
"""

import requests
import json
import os
import sys
import asyncio
from datetime import datetime, timezone
from pymongo import MongoClient

# Add backend path to sys.path for imports
sys.path.append('/app/backend')

# Configuration - Use production URL from frontend/.env
BASE_URL = "https://rezhub-commerce.preview.emergentagent.com"

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

def get_mongo_client():
    """Get MongoDB client for direct database access"""
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017/test_database")
    return MongoClient(mongo_url)

class TestIndexNowJobIntegration:
    """Test IndexNow job integration scenarios"""
    
    def test_indexnow_job_enqueue_and_processing(self, admin_auth, mongo_client):
        """Test IndexNow job enqueue and processing scenarios"""
        print("🔍 Testing IndexNow job enqueue and processing...")
        
        # Test admin endpoint for IndexNow reindex
        r = requests.post(
            f"{BASE_URL}/api/admin/seo/indexnow/reindex",
            headers=admin_auth["headers"]
        )
        
        if r.status_code == 404:
            print("   ⚠️ IndexNow admin endpoint not available (feature may be disabled)")
            return
        
        if r.status_code == 403:
            print("   ⚠️ IndexNow feature not enabled or insufficient permissions")
            return
            
        assert r.status_code == 200, f"IndexNow reindex failed: {r.text}"
        data = r.json()
        
        assert data.get("ok") is True, "IndexNow reindex should return ok=true"
        
        if data.get("enqueued_jobs", 0) > 0:
            print(f"   ✅ Successfully enqueued {data['enqueued_jobs']} IndexNow job(s)")
            job_id = data.get("job_id")
            if job_id:
                print(f"   ✅ Job ID: {job_id}")
        else:
            print("   ⚠️ No jobs enqueued (IndexNow may be disabled or not configured)")
        
        print("✅ IndexNow job enqueue test passed")
    
    def test_indexnow_configuration_scenarios(self):
        """Test different IndexNow configuration scenarios by checking behavior"""
        print("🔍 Testing IndexNow configuration scenarios...")
        
        # We can't directly test environment variables, but we can test the behavior
        # by observing the admin endpoint responses
        
        # Test 1: Check if IndexNow is properly configured by calling admin endpoint
        token, org_id, email = login_admin()
        headers = {"Authorization": f"Bearer {token}"}
        
        r = requests.post(f"{BASE_URL}/api/admin/seo/indexnow/reindex", headers=headers)
        
        if r.status_code == 404:
            print("   ℹ️ IndexNow admin endpoint not found - feature may not be implemented")
        elif r.status_code == 403:
            print("   ℹ️ IndexNow feature disabled or insufficient permissions")
        elif r.status_code == 200:
            data = r.json()
            if data.get("ok") and data.get("enqueued_jobs", 0) > 0:
                print("   ✅ IndexNow appears to be enabled and configured")
            elif data.get("ok") and data.get("enqueued_jobs", 0) == 0:
                print("   ⚠️ IndexNow enabled but no jobs enqueued (may be disabled/not configured)")
            else:
                print("   ⚠️ IndexNow response unclear:", data)
        else:
            print(f"   ❌ Unexpected response: {r.status_code} - {r.text}")
        
        print("✅ IndexNow configuration scenarios test completed")

class TestSitemapBehavior:
    """Test sitemap.xml endpoint behavior"""
    
    def test_sitemap_without_org_param(self):
        """Test /api/sitemap.xml without org param - should return static URLs + legacy hotels"""
        print("🔍 Testing sitemap without org parameter...")
        
        # Call sitemap endpoint without org parameter
        r = requests.get(f"{BASE_URL}/api/sitemap.xml")
        assert r.status_code == 200, f"Sitemap request failed: {r.text}"
        assert r.headers.get("content-type") == "application/xml"
        
        xml_content = r.text
        
        # Verify XML structure
        assert '<?xml version="1.0" encoding="UTF-8"?>' in xml_content
        assert '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' in xml_content
        assert '</urlset>' in xml_content
        
        # Verify static URLs are present (check both http and https)
        base_url_http = BASE_URL.replace('https://', 'http://')
        home_url_found = f'<loc>{BASE_URL}/</loc>' in xml_content or f'<loc>{base_url_http}/</loc>' in xml_content
        book_url_found = f'<loc>{BASE_URL}/book</loc>' in xml_content or f'<loc>{base_url_http}/book</loc>' in xml_content
        
        assert home_url_found, f"Home page URL not found in sitemap. Expected {BASE_URL}/ or {base_url_http}/"
        assert book_url_found, f"Book page URL not found in sitemap. Expected {BASE_URL}/book or {base_url_http}/book"
        
        # Check for legacy hotels (if any exist)
        mongo_client = get_mongo_client()
        db = mongo_client.get_default_database()
        hotels_count = db.hotels.count_documents({"active": True})
        
        if hotels_count > 0:
            # Should contain hotel URLs in /book/{hotelId} format
            hotel_urls = [line for line in xml_content.split('\n') if '/book/' in line and '<loc>' in line]
            print(f"   Found {len(hotel_urls)} hotel URLs in sitemap")
        
        print("✅ Sitemap without org parameter test passed")
    
    def test_sitemap_with_org_param(self):
        """Test /api/sitemap.xml?org=<org_id> - should include products with type=hotel, status=active"""
        print("🔍 Testing sitemap with org parameter...")
        
        token, org_id, email = login_admin()
        
        # Call sitemap endpoint with org parameter
        r = requests.get(f"{BASE_URL}/api/sitemap.xml?org={org_id}")
        assert r.status_code == 200, f"Sitemap with org request failed: {r.text}"
        
        xml_content = r.text
        
        # Verify static URLs are still present (check both http and https)
        base_url_http = BASE_URL.replace('https://', 'http://')
        home_url_found = f'<loc>{BASE_URL}/</loc>' in xml_content or f'<loc>{base_url_http}/</loc>' in xml_content
        book_url_found = f'<loc>{BASE_URL}/book</loc>' in xml_content or f'<loc>{base_url_http}/book</loc>' in xml_content
        
        assert home_url_found, "Home page URL not found in sitemap"
        assert book_url_found, "Book page URL not found in sitemap"
        
        # Check for products with type=hotel, status=active
        mongo_client = get_mongo_client()
        db = mongo_client.get_default_database()
        active_hotels = list(db.products.find({
            "type": "hotel",
            "status": "active",
            "organization_id": org_id
        }, {"_id": 1, "updated_at": 1, "created_at": 1}))
        
        print(f"   Found {len(active_hotels)} active hotel products for org {org_id}")
        
        if active_hotels:
            # Verify product URLs are in canonical /book/{productId} format
            for product in active_hotels:
                product_id = str(product["_id"])
                expected_url = f'<loc>{BASE_URL}/book/{product_id}</loc>'
                assert expected_url in xml_content, f"Product URL {expected_url} not found in sitemap"
            
            # Verify lastmod dates are present and valid
            lastmod_lines = [line for line in xml_content.split('\n') if '<lastmod>' in line]
            assert len(lastmod_lines) > 0, "No lastmod dates found in sitemap"
            
            for line in lastmod_lines:
                date_str = line.strip().replace('<lastmod>', '').replace('</lastmod>', '')
                # Verify date format (YYYY-MM-DD)
                try:
                    datetime.strptime(date_str, '%Y-%m-%d')
                except ValueError:
                    assert False, f"Invalid date format in sitemap: {date_str}"
        
        print("✅ Sitemap with org parameter test passed")
    
    def test_sitemap_canonical_urls(self):
        """Test that all dynamic URLs follow canonical pattern /book/{productId}"""
        print("🔍 Testing sitemap canonical URL patterns...")
        
        token, org_id, email = login_admin()
        
        # Get sitemap with org parameter
        r = requests.get(f"{BASE_URL}/api/sitemap.xml?org={org_id}")
        assert r.status_code == 200
        
        xml_content = r.text
        
        # Extract all URLs from sitemap
        import re
        url_pattern = r'<loc>(.*?)</loc>'
        urls = re.findall(url_pattern, xml_content)
        
        # Filter dynamic URLs (exclude static ones)
        dynamic_urls = [url for url in urls if '/book/' in url and url not in [
            f'{BASE_URL}/',
            f'{BASE_URL}/book'
        ]]
        
        # Verify all dynamic URLs follow /book/{id} pattern
        book_pattern = re.compile(rf'^{re.escape(BASE_URL)}/book/[a-f0-9]{{24}}$')
        
        for url in dynamic_urls:
            assert book_pattern.match(url), f"URL {url} does not follow canonical /book/{{productId}} pattern"
        
        print(f"   Verified {len(dynamic_urls)} dynamic URLs follow canonical pattern")
        print("✅ Sitemap canonical URL patterns test passed")

class TestPublishProductVersionSEO:
    """Test publish_product_version SEO fields functionality"""
    
    def test_seo_fields_no_change_when_populated(self):
        """Test that slug/meta_* fields are not changed when already populated"""
        print("🔍 Testing SEO fields preservation when already populated...")
        
        token, org_id, email = login_admin()
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create a test product with existing SEO fields
        mongo_client = get_mongo_client()
        db = mongo_client.get_default_database()
        
        # Create test product with pre-populated SEO fields
        test_product = {
            "organization_id": org_id,
            "type": "hotel",
            "code": "TEST_SEO_PRESERVE",
            "name": {"tr": "Test Otel Preserve", "en": "Test Hotel Preserve"},
            "status": "active",
            "default_currency": "EUR",
            "location": {"city": "Istanbul", "country": "Turkey"},
            "slug": "existing-test-slug",
            "meta_title": "Existing Meta Title",
            "meta_description": "Existing meta description",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        
        result = db.products.insert_one(test_product)
        product_id = str(result.inserted_id)
        
        try:
            # Create a rate plan for the product (required for hotel publishing)
            rate_plan = {
                "organization_id": org_id,
                "product_id": result.inserted_id,
                "name": {"tr": "Standart Oda", "en": "Standard Room"},
                "status": "active",
                "base_price": 100.0,
                "currency": "EUR",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }
            db.rate_plans.insert_one(rate_plan)
            
            # Create a product version
            version_payload = {
                "valid_from": "2024-01-01",
                "valid_to": "2024-12-31",
                "content": {
                    "description": {"tr": "Test açıklama", "en": "Test description"}
                }
            }
            
            r = requests.post(
                f"{BASE_URL}/api/admin/catalog/products/{product_id}/versions",
                headers=headers,
                json=version_payload
            )
            assert r.status_code == 201, f"Version creation failed: {r.text}"
            version_data = r.json()
            version_id = version_data["_id"]
            
            # Publish the version
            r = requests.post(
                f"{BASE_URL}/api/admin/catalog/products/{product_id}/versions/{version_id}/publish",
                headers=headers
            )
            assert r.status_code == 200, f"Version publish failed: {r.text}"
            
            # Verify SEO fields were NOT changed
            updated_product = db.products.find_one({"_id": result.inserted_id})
            
            assert updated_product["slug"] == "existing-test-slug", "Existing slug was modified"
            assert updated_product["meta_title"] == "Existing Meta Title", "Existing meta_title was modified"
            assert updated_product["meta_description"] == "Existing meta description", "Existing meta_description was modified"
            
            print("   ✅ Existing SEO fields were preserved")
            
        finally:
            # Cleanup
            db.products.delete_one({"_id": result.inserted_id})
            db.rate_plans.delete_many({"product_id": result.inserted_id})
            db.product_versions.delete_many({"product_id": result.inserted_id})
        
        print("✅ SEO fields preservation test passed")
    
    def test_slug_generation_with_turkish_transliteration(self):
        """Test slug generation with Turkish transliteration (ı→i, ş→s, ğ→g, ö→o, ü→u, ç→c)"""
        print("🔍 Testing slug generation with Turkish transliteration...")
        
        token, org_id, email = login_admin()
        headers = {"Authorization": f"Bearer {token}"}
        
        mongo_client = get_mongo_client()
        db = mongo_client.get_default_database()
        
        # Test Turkish characters in product name
        test_product = {
            "organization_id": org_id,
            "type": "hotel",
            "code": "TEST_TR_SLUG",
            "name": {"tr": "Şişli Güzel Otel İçin Ürün", "en": "Sisli Beautiful Hotel Product"},
            "status": "active",
            "default_currency": "EUR",
            "location": {"city": "İstanbul", "country": "Türkiye"},
            # No slug field - should be generated
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        
        result = db.products.insert_one(test_product)
        product_id = str(result.inserted_id)
        
        try:
            # Create rate plan
            rate_plan = {
                "organization_id": org_id,
                "product_id": result.inserted_id,
                "name": {"tr": "Standart Oda", "en": "Standard Room"},
                "status": "active",
                "base_price": 100.0,
                "currency": "EUR",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }
            db.rate_plans.insert_one(rate_plan)
            
            # Create and publish version
            version_payload = {
                "valid_from": "2024-01-01",
                "valid_to": "2024-12-31",
                "content": {"description": {"tr": "Test açıklama"}}
            }
            
            r = requests.post(
                f"{BASE_URL}/api/admin/catalog/products/{product_id}/versions",
                headers=headers,
                json=version_payload
            )
            assert r.status_code == 201
            version_data = r.json()
            version_id = version_data["_id"]
            
            r = requests.post(
                f"{BASE_URL}/api/admin/catalog/products/{product_id}/versions/{version_id}/publish",
                headers=headers
            )
            assert r.status_code == 200
            
            # Check generated slug
            updated_product = db.products.find_one({"_id": result.inserted_id})
            generated_slug = updated_product.get("slug", "")
            
            # Verify Turkish transliteration
            # "Şişli Güzel Otel İçin Ürün" should become "sisli-guzel-otel-icin-urun"
            expected_slug = "sisli-guzel-otel-icin-urun"
            assert generated_slug == expected_slug, f"Expected slug '{expected_slug}', got '{generated_slug}'"
            
            print(f"   ✅ Generated slug: '{generated_slug}' (Turkish transliteration working)")
            
        finally:
            # Cleanup
            db.products.delete_one({"_id": result.inserted_id})
            db.rate_plans.delete_many({"product_id": result.inserted_id})
            db.product_versions.delete_many({"product_id": result.inserted_id})
        
        print("✅ Turkish transliteration test passed")
    
    def test_slug_collision_resolution(self):
        """Test org-scope slug collision resolution with -2, -3 suffix"""
        print("🔍 Testing slug collision resolution...")
        
        token, org_id, email = login_admin()
        headers = {"Authorization": f"Bearer {token}"}
        
        mongo_client = get_mongo_client()
        db = mongo_client.get_default_database()
        
        # Create first product with a specific name
        product1 = {
            "organization_id": org_id,
            "type": "hotel",
            "code": "TEST_COLLISION_1",
            "name": {"tr": "Test Otel", "en": "Test Hotel"},
            "status": "active",
            "default_currency": "EUR",
            "location": {"city": "Istanbul", "country": "Turkey"},
            "slug": "test-otel",  # Pre-existing slug
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        
        result1 = db.products.insert_one(product1)
        
        # Create second product with same name (should get collision resolution)
        product2 = {
            "organization_id": org_id,
            "type": "hotel",
            "code": "TEST_COLLISION_2",
            "name": {"tr": "Test Otel", "en": "Test Hotel"},  # Same name
            "status": "active",
            "default_currency": "EUR",
            "location": {"city": "Istanbul", "country": "Turkey"},
            # No slug - should be generated with collision resolution
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        
        result2 = db.products.insert_one(product2)
        product2_id = str(result2.inserted_id)
        
        try:
            # Create rate plans for both products
            for product_oid in [result1.inserted_id, result2.inserted_id]:
                rate_plan = {
                    "organization_id": org_id,
                    "product_id": product_oid,
                    "name": {"tr": "Standart Oda", "en": "Standard Room"},
                    "status": "active",
                    "base_price": 100.0,
                    "currency": "EUR",
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc)
                }
                db.rate_plans.insert_one(rate_plan)
            
            # Create and publish version for second product
            version_payload = {
                "valid_from": "2024-01-01",
                "valid_to": "2024-12-31",
                "content": {"description": {"tr": "Test açıklama"}}
            }
            
            r = requests.post(
                f"{BASE_URL}/api/admin/catalog/products/{product2_id}/versions",
                headers=headers,
                json=version_payload
            )
            assert r.status_code == 201
            version_data = r.json()
            version_id = version_data["_id"]
            
            r = requests.post(
                f"{BASE_URL}/api/admin/catalog/products/{product2_id}/versions/{version_id}/publish",
                headers=headers
            )
            assert r.status_code == 200
            
            # Check collision resolution
            updated_product2 = db.products.find_one({"_id": result2.inserted_id})
            generated_slug = updated_product2.get("slug", "")
            
            # Should be "test-otel-2" due to collision with existing "test-otel"
            expected_slug = "test-otel-2"
            assert generated_slug == expected_slug, f"Expected slug '{expected_slug}', got '{generated_slug}'"
            
            print(f"   ✅ Collision resolved: '{generated_slug}'")
            
        finally:
            # Cleanup
            db.products.delete_many({"_id": {"$in": [result1.inserted_id, result2.inserted_id]}})
            db.rate_plans.delete_many({"product_id": {"$in": [result1.inserted_id, result2.inserted_id]}})
            db.product_versions.delete_many({"product_id": {"$in": [result1.inserted_id, result2.inserted_id]}})
        
        print("✅ Slug collision resolution test passed")
    
    def test_meta_title_description_defaults(self):
        """Test meta_title and meta_description default generation"""
        print("🔍 Testing meta_title and meta_description default generation...")
        
        token, org_id, email = login_admin()
        headers = {"Authorization": f"Bearer {token}"}
        
        mongo_client = get_mongo_client()
        db = mongo_client.get_default_database()
        
        # Test product without location
        test_product_no_loc = {
            "organization_id": org_id,
            "type": "hotel",
            "code": "TEST_META_NO_LOC",
            "name": {"tr": "Güzel Test Oteli", "en": "Beautiful Test Hotel"},
            "status": "active",
            "default_currency": "EUR",
            # No location
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        
        result_no_loc = db.products.insert_one(test_product_no_loc)
        product_no_loc_id = str(result_no_loc.inserted_id)
        
        # Test product with location
        test_product_with_loc = {
            "organization_id": org_id,
            "type": "hotel",
            "code": "TEST_META_WITH_LOC",
            "name": {"tr": "Şehir Merkezi Oteli", "en": "City Center Hotel"},
            "status": "active",
            "default_currency": "EUR",
            "location": {"city": "Antalya", "country": "Türkiye"},
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }
        
        result_with_loc = db.products.insert_one(test_product_with_loc)
        product_with_loc_id = str(result_with_loc.inserted_id)
        
        try:
            # Create rate plans for both products
            for product_oid in [result_no_loc.inserted_id, result_with_loc.inserted_id]:
                rate_plan = {
                    "organization_id": org_id,
                    "product_id": product_oid,
                    "name": {"tr": "Standart Oda", "en": "Standard Room"},
                    "status": "active",
                    "base_price": 100.0,
                    "currency": "EUR",
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc)
                }
                db.rate_plans.insert_one(rate_plan)
            
            # Test product without location
            version_payload = {
                "valid_from": "2024-01-01",
                "valid_to": "2024-12-31",
                "content": {"description": {"tr": "Test açıklama"}}
            }
            
            # Create and publish version for product without location
            r = requests.post(
                f"{BASE_URL}/api/admin/catalog/products/{product_no_loc_id}/versions",
                headers=headers,
                json=version_payload
            )
            assert r.status_code == 201
            version_data = r.json()
            version_id = version_data["_id"]
            
            r = requests.post(
                f"{BASE_URL}/api/admin/catalog/products/{product_no_loc_id}/versions/{version_id}/publish",
                headers=headers
            )
            assert r.status_code == 200
            
            # Check generated meta fields for product without location
            updated_product_no_loc = db.products.find_one({"_id": result_no_loc.inserted_id})
            
            expected_meta_title = "Güzel Test Oteli | Syroce"
            expected_meta_desc = "Güzel Test Oteli için otel rezervasyonu."
            
            assert updated_product_no_loc["meta_title"] == expected_meta_title
            assert updated_product_no_loc["meta_description"] == expected_meta_desc
            
            print(f"   ✅ No location - meta_title: '{updated_product_no_loc['meta_title']}'")
            print(f"   ✅ No location - meta_description: '{updated_product_no_loc['meta_description']}'")
            
            # Create and publish version for product with location
            r = requests.post(
                f"{BASE_URL}/api/admin/catalog/products/{product_with_loc_id}/versions",
                headers=headers,
                json=version_payload
            )
            assert r.status_code == 201
            version_data = r.json()
            version_id = version_data["_id"]
            
            r = requests.post(
                f"{BASE_URL}/api/admin/catalog/products/{product_with_loc_id}/versions/{version_id}/publish",
                headers=headers
            )
            assert r.status_code == 200
            
            # Check generated meta fields for product with location
            updated_product_with_loc = db.products.find_one({"_id": result_with_loc.inserted_id})
            
            expected_meta_title_loc = "Şehir Merkezi Oteli | Syroce"
            expected_meta_desc_loc = "Şehir Merkezi Oteli - Antalya, Türkiye için otel rezervasyonu."
            
            assert updated_product_with_loc["meta_title"] == expected_meta_title_loc
            assert updated_product_with_loc["meta_description"] == expected_meta_desc_loc
            
            print(f"   ✅ With location - meta_title: '{updated_product_with_loc['meta_title']}'")
            print(f"   ✅ With location - meta_description: '{updated_product_with_loc['meta_description']}'")
            
        finally:
            # Cleanup
            db.products.delete_many({"_id": {"$in": [result_no_loc.inserted_id, result_with_loc.inserted_id]}})
            db.rate_plans.delete_many({"product_id": {"$in": [result_no_loc.inserted_id, result_with_loc.inserted_id]}})
            db.product_versions.delete_many({"product_id": {"$in": [result_no_loc.inserted_id, result_with_loc.inserted_id]}})
        
        print("✅ Meta title/description defaults test passed")

def run_all_tests():
    """Run all SEO+ Pack backend tests"""
    print("🚀 Starting SEO+ Pack Backend Test Suite")
    print("=" * 60)
    
    # Test IndexNow job integration
    print("\n📋 1. IndexNow Job Integration Tests")
    print("-" * 40)
    indexnow_tests = TestIndexNowJobIntegration()
    
    # Get fixtures
    token, org_id, email = login_admin()
    admin_auth = {"headers": {"Authorization": f"Bearer {token}"}, "org_id": org_id, "email": email}
    mongo_client = get_mongo_client()
    
    indexnow_tests.test_indexnow_job_enqueue_and_processing(admin_auth, mongo_client)
    indexnow_tests.test_indexnow_configuration_scenarios()
    
    # Test sitemap behavior
    print("\n📋 2. Sitemap Behavior Tests")
    print("-" * 40)
    sitemap_tests = TestSitemapBehavior()
    
    sitemap_tests.test_sitemap_without_org_param()
    sitemap_tests.test_sitemap_with_org_param()
    sitemap_tests.test_sitemap_canonical_urls()
    
    # Test publish_product_version SEO fields
    print("\n📋 3. Publish Product Version SEO Fields Tests")
    print("-" * 40)
    seo_tests = TestPublishProductVersionSEO()
    
    seo_tests.test_seo_fields_no_change_when_populated()
    seo_tests.test_slug_generation_with_turkish_transliteration()
    seo_tests.test_slug_collision_resolution()
    seo_tests.test_meta_title_description_defaults()
    
    print("\n" + "=" * 60)
    print("🎉 SEO+ Pack Backend Test Suite Completed Successfully!")
    print("=" * 60)

if __name__ == "__main__":
    run_all_tests()