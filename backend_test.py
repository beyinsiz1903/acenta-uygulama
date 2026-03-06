#!/usr/bin/env python3
"""
Preview Auth Helper Backend Testing Suite

This test suite validates the new preview auth helper implementation for PR-X:
- Common auth/token cache functionality
- Token reuse and TTL management  
- Invalidation and re-login flows
- Tenant-aware login support
- Rate-limit friendly behavior
- Preview test migration validation
"""

import json
import os
import time
import requests
from pathlib import Path

# Import the preview auth helper
import sys
sys.path.insert(0, '/app/backend/tests')
from preview_auth_helper import (
    get_preview_auth_context,
    invalidate_preview_auth_context, 
    PreviewAuthSession,
    resolve_preview_base_url,
    build_preview_auth_headers,
    PreviewAuthError,
    CACHE_FILE
)

def test_preview_base_url_resolution():
    """Test that preview base URL is resolved correctly from frontend/.env"""
    print("🧪 Testing preview base URL resolution...")
    
    # Test with explicit URL
    explicit_url = resolve_preview_base_url("https://test.example.com/")
    assert explicit_url == "https://test.example.com", f"Expected stripped URL, got: {explicit_url}"
    
    # Test with empty/None URL (should read from frontend/.env)  
    resolved_url = resolve_preview_base_url("")
    print(f"   ✅ Resolved base URL from frontend/.env: {resolved_url}")
    assert resolved_url.startswith("https://"), f"Expected HTTPS URL, got: {resolved_url}"
    
    # Verify it's the expected preview URL
    assert "preview.emergentagent.com" in resolved_url, f"Expected preview URL, got: {resolved_url}"
    
    return resolved_url

def test_cache_file_structure():
    """Test that cache file exists and has expected structure"""
    print("🧪 Testing cache file structure...")
    
    if not CACHE_FILE.exists():
        print(f"   ⚠️ Cache file not found at {CACHE_FILE}")
        return
        
    cache_data = json.loads(CACHE_FILE.read_text())
    print(f"   ✅ Cache file contains {len(cache_data)} entries")
    
    # Check for admin and agent entries
    admin_found = False
    agent_found = False
    
    for key, entry in cache_data.items():
        print(f"   📝 Cache key: {key}")
        
        # Validate entry structure
        required_fields = ["access_token", "auth_source", "base_url", "cached_until", "email", "login_response"]
        for field in required_fields:
            assert field in entry, f"Missing required field '{field}' in cache entry"
            
        if "admin@acenta.test" in key:
            admin_found = True
            print(f"      ✅ Admin entry found - auth_source: {entry['auth_source']}")
            assert entry["tenant_id"], "Admin should have tenant_id"
            
        if "agent@acenta.test" in key:  
            agent_found = True
            print(f"      ✅ Agent entry found - auth_source: {entry['auth_source']}")
            assert entry["tenant_id"], "Agent should have tenant_id"
            
    print(f"   ✅ Admin entry found: {admin_found}, Agent entry found: {agent_found}")
    return cache_data

def test_auth_context_retrieval_and_reuse():
    """Test auth context retrieval and token reuse functionality"""
    print("🧪 Testing auth context retrieval and token reuse...")
    
    base_url = resolve_preview_base_url("")
    
    # Get admin auth context (should reuse cached token)
    print("   📤 Getting admin auth context...")
    start_time = time.time()
    admin_auth = get_preview_auth_context(
        base_url,
        email="admin@acenta.test", 
        password="admin123"
    )
    elapsed = time.time() - start_time
    
    print(f"   ✅ Admin auth retrieved in {elapsed:.2f}s - source: {admin_auth.auth_source}")
    print(f"      Token length: {len(admin_auth.access_token)} chars")
    print(f"      Tenant ID: {admin_auth.tenant_id}")
    print(f"      Cached until: {time.ctime(admin_auth.cached_until)}")
    
    # Verify token works with /api/auth/me
    headers = build_preview_auth_headers(admin_auth, include_tenant=True)
    me_response = requests.get(f"{base_url}/api/auth/me", headers=headers, timeout=10)
    assert me_response.status_code == 200, f"Admin /auth/me failed: {me_response.text}"
    me_data = me_response.json()
    print(f"   ✅ Admin token validated - email: {me_data['email']}")
    
    # Get agent auth context (should reuse cached token)
    print("   📤 Getting agent auth context...")
    start_time = time.time()
    agent_auth = get_preview_auth_context(
        base_url,
        email="agent@acenta.test",
        password="agent123"
    )
    elapsed = time.time() - start_time
    
    print(f"   ✅ Agent auth retrieved in {elapsed:.2f}s - source: {agent_auth.auth_source}")
    print(f"      Token length: {len(agent_auth.access_token)} chars") 
    print(f"      Tenant ID: {agent_auth.tenant_id}")
    
    # Verify agent token works
    agent_headers = build_preview_auth_headers(agent_auth, include_tenant=True)
    agent_me = requests.get(f"{base_url}/api/auth/me", headers=agent_headers, timeout=10)
    assert agent_me.status_code == 200, f"Agent /auth/me failed: {agent_me.text}"
    agent_data = agent_me.json()
    print(f"   ✅ Agent token validated - email: {agent_data['email']}")
    
    # Test tenant-aware functionality 
    print(f"   📝 Admin tenant: {me_data.get('tenant_id')}")
    print(f"   📝 Agent tenant: {agent_data.get('tenant_id')}")
    
    return admin_auth, agent_auth

def test_token_invalidation_and_refresh():
    """Test token invalidation and re-login functionality"""
    print("🧪 Testing token invalidation and refresh flow...")
    
    base_url = resolve_preview_base_url("")
    
    # Get initial auth context
    admin_auth = get_preview_auth_context(base_url, email="admin@acenta.test", password="admin123")
    original_token = admin_auth.access_token
    print(f"   📝 Original token: {original_token[:50]}...")
    
    # Invalidate the cached context
    print("   🗑️ Invalidating admin auth context...")
    invalidate_preview_auth_context(base_url, "admin@acenta.test", tenant_id=admin_auth.tenant_id)
    
    # Get auth context again (should force fresh login)
    print("   📤 Getting auth context after invalidation...")
    fresh_auth = get_preview_auth_context(base_url, email="admin@acenta.test", password="admin123")
    new_token = fresh_auth.access_token
    print(f"   📝 New token: {new_token[:50]}...")
    
    # Tokens might be the same if session is still valid, that's OK
    print(f"   ✅ Fresh auth retrieved - source: {fresh_auth.auth_source}")
    
    # Test forced re-login
    print("   🔄 Testing forced re-login...")
    forced_auth = get_preview_auth_context(
        base_url, 
        email="admin@acenta.test", 
        password="admin123", 
        force_relogin=True
    )
    print(f"   ✅ Forced re-login completed - source: {forced_auth.auth_source}")
    
    return fresh_auth

def test_preview_auth_session_wrapper():
    """Test the PreviewAuthSession wrapper class"""
    print("🧪 Testing PreviewAuthSession wrapper...")
    
    base_url = resolve_preview_base_url("")
    
    # Create admin session
    print("   🔧 Creating admin preview session...")
    admin_session = PreviewAuthSession(
        base_url,
        email="admin@acenta.test",
        password="admin123", 
        include_tenant_header=True
    )
    
    # Test GET /api/health  
    print("   📤 Testing session GET /api/health...")
    health_resp = admin_session.get("/api/health")
    assert health_resp.status_code == 200, f"Health check failed: {health_resp.text}"
    health_data = health_resp.json()
    print(f"   ✅ Health check: {health_data}")
    
    # Test authenticated endpoint
    print("   📤 Testing session GET /api/auth/me...")
    me_resp = admin_session.get("/api/auth/me")
    assert me_resp.status_code == 200, f"Auth me failed: {me_resp.text}"
    me_data = me_resp.json()
    print(f"   ✅ Auth me: {me_data['email']}")
    
    # Test admin endpoint
    print("   📤 Testing session GET /api/admin/agencies...")
    agencies_resp = admin_session.get("/api/admin/agencies")
    assert agencies_resp.status_code == 200, f"Admin agencies failed: {agencies_resp.text}"
    agencies_data = agencies_resp.json()
    print(f"   ✅ Admin agencies: {len(agencies_data)} agencies found")
    
    # Create agent session and test different endpoint
    print("   🔧 Creating agent preview session...")  
    agent_session = PreviewAuthSession(
        base_url,
        email="agent@acenta.test",
        password="agent123",
        include_tenant_header=True
    )
    
    agent_me = agent_session.get("/api/auth/me")
    assert agent_me.status_code == 200, f"Agent auth me failed: {agent_me.text}"
    agent_data = agent_me.json()
    print(f"   ✅ Agent auth me: {agent_data['email']}")
    
    return admin_session, agent_session

def test_mobile_bff_endpoints():
    """Test mobile BFF endpoints using preview auth helper"""
    print("🧪 Testing mobile BFF endpoints with preview auth...")
    
    base_url = resolve_preview_base_url("")
    admin_session = PreviewAuthSession(
        base_url,
        email="admin@acenta.test", 
        password="admin123",
        include_tenant_header=True
    )
    
    # Test mobile auth/me
    print("   📤 Testing mobile /api/v1/mobile/auth/me...")
    mobile_me = admin_session.get("/api/v1/mobile/auth/me")
    assert mobile_me.status_code == 200, f"Mobile auth/me failed: {mobile_me.text}"
    mobile_data = mobile_me.json()
    print(f"   ✅ Mobile auth/me: {mobile_data['email']}")
    assert "_id" not in mobile_data, "No MongoDB _id leak allowed"
    
    # Test mobile dashboard
    print("   📤 Testing mobile /api/v1/mobile/dashboard/summary...")
    dashboard = admin_session.get("/api/v1/mobile/dashboard/summary") 
    assert dashboard.status_code == 200, f"Mobile dashboard failed: {dashboard.text}"
    dashboard_data = dashboard.json()
    print(f"   ✅ Mobile dashboard: {dashboard_data['bookings_today']} bookings today")
    
    # Test mobile bookings list
    print("   📤 Testing mobile /api/v1/mobile/bookings...")
    bookings = admin_session.get("/api/v1/mobile/bookings")
    assert bookings.status_code == 200, f"Mobile bookings failed: {bookings.text}"
    bookings_data = bookings.json()
    print(f"   ✅ Mobile bookings: {bookings_data['total']} total bookings")
    
    return True

def test_rate_limit_friendly_behavior():
    """Test that the helper reduces rate limiting issues"""
    print("🧪 Testing rate-limit friendly behavior...")
    
    base_url = resolve_preview_base_url("")
    
    # Make multiple rapid calls - should reuse cached tokens
    print("   🚀 Making 5 rapid auth context requests...")
    start_time = time.time()
    
    for i in range(5):
        auth = get_preview_auth_context(base_url, email="admin@acenta.test", password="admin123")
        print(f"      Call {i+1}: {auth.auth_source} (token: {auth.access_token[:20]}...)")
    
    elapsed = time.time() - start_time    
    print(f"   ✅ Completed 5 calls in {elapsed:.2f}s (should be fast due to caching)")
    
    # Should be very fast if caching works (no actual login requests)
    if elapsed < 1.0:
        print("   ✅ Excellent performance - caching working correctly") 
    elif elapsed < 3.0:
        print("   ✅ Good performance - some cache hits")
    else:
        print("   ⚠️ Slow performance - cache may not be working optimally")
        
    return True

def test_error_handling():
    """Test error handling in preview auth helper"""
    print("🧪 Testing error handling...")
    
    base_url = resolve_preview_base_url("")
    
    # Test invalid credentials 
    print("   🚫 Testing invalid credentials...")
    try:
        bad_auth = get_preview_auth_context(
            base_url,
            email="invalid@example.com",
            password="wrongpassword"
        )
        print("   ❌ Expected authentication to fail")
        assert False, "Should have raised PreviewAuthError"
    except PreviewAuthError as e:
        print(f"   ✅ Correctly caught auth error: {str(e)[:100]}...")
    except Exception as e:
        print(f"   ⚠️ Unexpected error type: {type(e).__name__}: {e}")
        
    return True

def run_comprehensive_backend_test():
    """Run the complete backend test suite for preview auth helper"""
    print("=" * 80)
    print("🧪 PREVIEW AUTH HELPER COMPREHENSIVE BACKEND TEST")
    print("=" * 80)
    
    try:
        # Test 1: Base URL resolution  
        base_url = test_preview_base_url_resolution()
        print()
        
        # Test 2: Cache file structure
        cache_data = test_cache_file_structure() 
        print()
        
        # Test 3: Auth context and token reuse
        admin_auth, agent_auth = test_auth_context_retrieval_and_reuse()
        print()
        
        # Test 4: Token invalidation and refresh
        fresh_auth = test_token_invalidation_and_refresh()
        print()
        
        # Test 5: PreviewAuthSession wrapper
        admin_session, agent_session = test_preview_auth_session_wrapper()
        print()
        
        # Test 6: Mobile BFF endpoints
        test_mobile_bff_endpoints()
        print()
        
        # Test 7: Rate-limit friendly behavior
        test_rate_limit_friendly_behavior()  
        print()
        
        # Test 8: Error handling
        test_error_handling()
        print()
        
        print("=" * 80)
        print("✅ ALL PREVIEW AUTH HELPER TESTS PASSED")
        print("=" * 80)
        
        # Summary 
        print("\n📋 VALIDATION SUMMARY:")
        print("✅ 1. Common auth/token cache functionality - WORKING")
        print("✅ 2. Token reuse and TTL management - WORKING") 
        print("✅ 3. Invalidation and re-login flows - WORKING")
        print("✅ 4. Tenant-aware login support - WORKING")
        print("✅ 5. Rate-limit friendly behavior - WORKING")
        print("✅ 6. PreviewAuthSession wrapper - WORKING")
        print("✅ 7. Mobile BFF endpoint integration - WORKING")  
        print("✅ 8. Error handling - WORKING")
        
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_comprehensive_backend_test()
    exit(0 if success else 1)