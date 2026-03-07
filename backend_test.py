#!/usr/bin/env python3

import requests
import json
import os
from pathlib import Path

# Configuration
BASE_URL = "https://api-versioning-hub.preview.emergentagent.com"
ADMIN_EMAIL = "admin@acenta.test"
ADMIN_PASSWORD = "admin123"
B2B_EMAIL = "agent@acenta.test"  
B2B_PASSWORD = "agent123"

def test_pr_v1_2b_session_rollout():
    """
    PR-V1-2B Backend Session Rollout Validation
    
    Tests the alias-first rollout for session auth endpoints while preserving 
    legacy behavior and cookie auth compatibility.
    """
    
    print("🔧 PR-V1-2B Backend Session Rollout Validation")
    print("=" * 60)
    
    results = {
        "legacy_v1_parity": False,
        "single_session_revoke": False, 
        "bulk_revoke": False,
        "cookie_auth_safety": False,
        "inventory_telemetry": False
    }
    
    try:
        # A. Legacy/v1 parity tests
        print("\n📋 A. Testing Legacy/V1 Parity...")
        results["legacy_v1_parity"] = test_legacy_v1_parity()
        
        # B. Single-session revoke behavior
        print("\n🔑 B. Testing Single-Session Revoke Behavior...")
        results["single_session_revoke"] = test_single_session_revoke()
        
        # C. Bulk revoke behavior
        print("\n🚫 C. Testing Bulk Revoke Behavior...")
        results["bulk_revoke"] = test_bulk_revoke()
        
        # D. Cookie auth safety
        print("\n🍪 D. Testing Cookie Auth Safety...")
        results["cookie_auth_safety"] = test_cookie_auth_safety()
        
        # E. Inventory/telemetry artifacts
        print("\n📊 E. Testing Inventory/Telemetry Artifacts...")
        results["inventory_telemetry"] = test_inventory_artifacts()
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 PR-V1-2B Test Results Summary:")
        passed = sum(1 for result in results.values() if result)
        total = len(results)
        
        for test_name, result in results.items():
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"   {test_name}: {status}")
        
        print(f"\n🎯 Overall: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 PR-V1-2B session rollout validation SUCCESSFUL!")
            return True
        else:
            print("⚠️  Some tests failed - see details above")
            return False
            
    except Exception as e:
        print(f"❌ Critical error during PR-V1-2B testing: {e}")
        return False


def test_legacy_v1_parity():
    """Test A: Legacy/v1 parity - Compare legacy and v1 session endpoints"""
    
    try:
        # Login and get bearer token
        print("  🔐 Logging in to get bearer token...")
        login_resp = requests.post(f"{BASE_URL}/api/auth/login", 
                                 json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
                                 timeout=30)
        
        if login_resp.status_code != 200:
            print(f"  ❌ Login failed: {login_resp.status_code} - {login_resp.text}")
            return False
            
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Compare GET /api/auth/sessions vs GET /api/v1/auth/sessions
        print("  📋 Comparing legacy vs v1 sessions endpoints...")
        
        legacy_resp = requests.get(f"{BASE_URL}/api/auth/sessions", headers=headers, timeout=30)
        v1_resp = requests.get(f"{BASE_URL}/api/v1/auth/sessions", headers=headers, timeout=30)
        
        if legacy_resp.status_code != 200:
            print(f"  ❌ Legacy sessions endpoint failed: {legacy_resp.status_code}")
            return False
            
        if v1_resp.status_code != 200:
            print(f"  ❌ V1 sessions endpoint failed: {v1_resp.status_code}")
            return False
        
        # Check compat headers on legacy endpoint
        if legacy_resp.headers.get("deprecation") != "true":
            print("  ❌ Legacy sessions endpoint missing Deprecation header")
            return False
            
        link_header = legacy_resp.headers.get("link", "")
        if "/api/v1/auth/sessions" not in link_header:
            print("  ❌ Legacy sessions endpoint missing Link successor header")
            return False
        
        # Compare session data
        legacy_sessions = legacy_resp.json()
        v1_sessions = v1_resp.json()
        
        legacy_session_ids = {session["id"] for session in legacy_sessions}
        v1_session_ids = {session["id"] for session in v1_sessions}
        
        if legacy_session_ids != v1_session_ids:
            print("  ❌ Session lists don't match between legacy and v1 endpoints")
            return False
            
        print(f"  ✅ Both endpoints return matching session sets ({len(legacy_sessions)} sessions)")
        return True
        
    except Exception as e:
        print(f"  ❌ Legacy/V1 parity test failed: {e}")
        return False


def test_single_session_revoke():
    """Test B: Single-session revoke behavior"""
    
    try:
        # Create at least 2 active sessions for same admin user
        print("  🔑 Creating multiple sessions...")
        
        session1_resp = requests.post(f"{BASE_URL}/api/v1/auth/login",
                                    json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
                                    timeout=30)
        session2_resp = requests.post(f"{BASE_URL}/api/v1/auth/login", 
                                    json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
                                    timeout=30)
        
        if session1_resp.status_code != 200 or session2_resp.status_code != 200:
            print("  ❌ Failed to create multiple sessions")
            return False
            
        token1 = session1_resp.json()["access_token"]
        token2 = session2_resp.json()["access_token"]
        session2_id = session2_resp.json()["session_id"]
        
        headers1 = {"Authorization": f"Bearer {token1}"}
        headers2 = {"Authorization": f"Bearer {token2}"}
        
        # Revoke session2 using token1 (keeping current session)
        print(f"  🚫 Revoking session {session2_id} via V1 endpoint...")
        
        revoke_resp = requests.post(f"{BASE_URL}/api/v1/auth/sessions/{session2_id}/revoke",
                                   headers=headers1, timeout=30)
        
        if revoke_resp.status_code != 200:
            print(f"  ❌ Session revoke failed: {revoke_resp.status_code}")
            return False
        
        # Confirm revoked session's token can no longer access /api/auth/me
        print("  🔍 Testing revoked session token...")
        revoked_me_resp = requests.get(f"{BASE_URL}/api/auth/me", headers=headers2, timeout=30)
        
        if revoked_me_resp.status_code != 401:
            print(f"  ❌ Revoked session token still works: {revoked_me_resp.status_code}")
            return False
            
        # Confirm current keeper session still works
        print("  ✅ Testing keeper session token...")
        keeper_me_resp = requests.get(f"{BASE_URL}/api/auth/me", headers=headers1, timeout=30)
        
        if keeper_me_resp.status_code != 200:
            print(f"  ❌ Keeper session token failed: {keeper_me_resp.status_code}")
            return False
        
        # Confirm revoked session no longer appears in session listing
        sessions_resp = requests.get(f"{BASE_URL}/api/v1/auth/sessions", headers=headers1, timeout=30)
        if sessions_resp.status_code == 200:
            sessions = sessions_resp.json()
            session_ids = {session["id"] for session in sessions}
            if session2_id in session_ids:
                print("  ❌ Revoked session still appears in session listing")
                return False
        
        # Test legacy route POST /api/auth/sessions/{id}/revoke also works
        print("  🔄 Testing legacy session revoke endpoint...")
        
        # Create another session to revoke via legacy endpoint
        session3_resp = requests.post(f"{BASE_URL}/api/auth/login",
                                    json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
                                    timeout=30)
        if session3_resp.status_code == 200:
            session3_id = session3_resp.json()["session_id"]
            token3 = session3_resp.json()["access_token"]
            
            # Revoke via legacy endpoint
            legacy_revoke_resp = requests.post(f"{BASE_URL}/api/auth/sessions/{session3_id}/revoke",
                                             headers=headers1, timeout=30)
            
            if legacy_revoke_resp.status_code != 200:
                print(f"  ❌ Legacy session revoke failed: {legacy_revoke_resp.status_code}")
                return False
                
            # Check compat headers
            if legacy_revoke_resp.headers.get("deprecation") != "true":
                print("  ❌ Legacy revoke endpoint missing Deprecation header")
                return False
        
        print("  ✅ Single-session revoke behavior working correctly")
        return True
        
    except Exception as e:
        print(f"  ❌ Single-session revoke test failed: {e}")
        return False


def test_bulk_revoke():
    """Test C: Bulk revoke behavior"""
    
    try:
        # Create a session for testing
        print("  🔑 Creating session for bulk revoke test...")
        
        login_resp = requests.post(f"{BASE_URL}/api/v1/auth/login",
                                 json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
                                 timeout=30)
        
        if login_resp.status_code != 200:
            print("  ❌ Login failed for bulk revoke test")
            return False
            
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # POST /api/v1/auth/revoke-all-sessions should revoke current session family
        print("  🚫 Testing V1 revoke-all-sessions...")
        
        revoke_all_resp = requests.post(f"{BASE_URL}/api/v1/auth/revoke-all-sessions",
                                       headers=headers, timeout=30)
        
        if revoke_all_resp.status_code != 200:
            print(f"  ❌ V1 revoke-all-sessions failed: {revoke_all_resp.status_code}")
            return False
        
        # After revoke-all, /api/auth/me with previous token should fail
        print("  🔍 Testing token after revoke-all-sessions...")
        me_after_resp = requests.get(f"{BASE_URL}/api/auth/me", headers=headers, timeout=30)
        
        if me_after_resp.status_code != 401:
            print(f"  ❌ Token still works after revoke-all-sessions: {me_after_resp.status_code}")
            return False
        
        # Test legacy POST /api/auth/revoke-all-sessions also works
        print("  🔄 Testing legacy revoke-all-sessions endpoint...")
        
        # Create new session for legacy test
        login2_resp = requests.post(f"{BASE_URL}/api/auth/login",
                                  json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
                                  timeout=30)
        
        if login2_resp.status_code == 200:
            token2 = login2_resp.json()["access_token"]
            headers2 = {"Authorization": f"Bearer {token2}"}
            
            legacy_revoke_all_resp = requests.post(f"{BASE_URL}/api/auth/revoke-all-sessions",
                                                  headers=headers2, timeout=30)
            
            if legacy_revoke_all_resp.status_code != 200:
                print(f"  ❌ Legacy revoke-all-sessions failed: {legacy_revoke_all_resp.status_code}")
                return False
                
            # Check compat headers
            if legacy_revoke_all_resp.headers.get("deprecation") != "true":
                print("  ❌ Legacy revoke-all endpoint missing Deprecation header")
                return False
        
        print("  ✅ Bulk revoke behavior working correctly")
        return True
        
    except Exception as e:
        print(f"  ❌ Bulk revoke test failed: {e}")
        return False


def test_cookie_auth_safety():
    """Test D: Cookie auth safety"""
    
    try:
        # Login via /api/v1/auth/login with header X-Client-Platform: web
        print("  🍪 Testing cookie auth with X-Client-Platform: web header...")
        
        session = requests.Session()
        web_headers = {
            "X-Client-Platform": "web",
            "Content-Type": "application/json"
        }
        
        login_resp = session.post(f"{BASE_URL}/api/v1/auth/login",
                                json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
                                headers=web_headers,
                                timeout=30)
        
        if login_resp.status_code != 200:
            print(f"  ❌ Cookie auth login failed: {login_resp.status_code}")
            return False
        
        # Confirm response auth_transport is cookie_compat
        login_data = login_resp.json()
        if login_data.get("auth_transport") != "cookie_compat":
            print(f"  ❌ Auth transport not cookie_compat: {login_data.get('auth_transport')}")
            return False
        
        # GET /api/v1/auth/sessions using only cookie session works
        print("  📋 Testing V1 sessions endpoint with cookie auth...")
        
        sessions_resp = session.get(f"{BASE_URL}/api/v1/auth/sessions", 
                                  headers={"X-Client-Platform": "web"},
                                  timeout=30)
        
        if sessions_resp.status_code != 200:
            print(f"  ❌ V1 sessions with cookies failed: {sessions_resp.status_code}")
            return False
            
        sessions = sessions_resp.json()
        if not sessions:
            print("  ❌ No sessions returned with cookie auth")
            return False
        
        # POST /api/v1/auth/revoke-all-sessions using cookie session works and clears access
        print("  🚫 Testing V1 revoke-all-sessions with cookie auth...")
        
        revoke_resp = session.post(f"{BASE_URL}/api/v1/auth/revoke-all-sessions",
                                 json={},
                                 headers=web_headers,
                                 timeout=30)
        
        if revoke_resp.status_code != 200:
            print(f"  ❌ V1 revoke-all with cookies failed: {revoke_resp.status_code}")
            return False
        
        # After revoke, access should be cleared
        me_after_resp = session.get(f"{BASE_URL}/api/v1/auth/me",
                                   headers={"X-Client-Platform": "web"},
                                   timeout=30)
        
        if me_after_resp.status_code != 401:
            print(f"  ❌ Cookie auth not cleared after revoke-all: {me_after_resp.status_code}")
            return False
        
        print("  ✅ Cookie auth safety working correctly")
        return True
        
    except Exception as e:
        print(f"  ❌ Cookie auth safety test failed: {e}")
        return False


def test_inventory_artifacts():
    """Test E: Inventory/telemetry artifacts"""
    
    try:
        print("  📊 Checking route inventory artifacts...")
        
        # Verify route_inventory.json contains the 3 new v1 auth session aliases
        inventory_path = "/app/backend/app/bootstrap/route_inventory.json"
        if not os.path.exists(inventory_path):
            print(f"  ❌ Route inventory file not found: {inventory_path}")
            return False
            
        with open(inventory_path, 'r') as f:
            inventory = json.load(f)
        
        required_v1_routes = [
            ("GET", "/api/v1/auth/sessions"),
            ("POST", "/api/v1/auth/sessions/{session_id}/revoke"),
            ("POST", "/api/v1/auth/revoke-all-sessions")
        ]
        
        inventory_routes = [(route["method"], route["path"]) for route in inventory]
        
        for method, path in required_v1_routes:
            if (method, path) not in inventory_routes:
                print(f"  ❌ Missing route in inventory: {method} {path}")
                return False
        
        print(f"  ✅ All 3 V1 session routes found in inventory")
        
        # Verify route_inventory_diff.json reports exactly these 3 added v1 routes
        diff_path = "/app/backend/app/bootstrap/route_inventory_diff.json"
        if not os.path.exists(diff_path):
            print(f"  ❌ Route inventory diff file not found: {diff_path}")
            return False
            
        with open(diff_path, 'r') as f:
            diff_data = json.load(f)
        
        added_paths = diff_data.get("added_paths", [])
        new_v1_route_count = diff_data.get("summary", {}).get("new_v1_route_count", 0)
        
        if new_v1_route_count != 3:
            print(f"  ❌ Expected 3 new V1 routes in diff, got {new_v1_route_count}")
            return False
        
        # Check that the specific routes are in the added paths
        added_route_keys = [(route["method"], route["path"]) for route in added_paths]
        for method, path in required_v1_routes:
            if (method, path) not in added_route_keys:
                print(f"  ❌ Missing route in diff added_paths: {method} {path}")
                return False
        
        print(f"  ✅ Route diff correctly shows 3 new V1 session routes")
        
        # Verify route_inventory_summary.json has v1_count >= 23 and contains domain_v1_progress.auth metrics
        summary_path = "/app/backend/app/bootstrap/route_inventory_summary.json"
        if not os.path.exists(summary_path):
            print(f"  ❌ Route inventory summary file not found: {summary_path}")
            return False
            
        with open(summary_path, 'r') as f:
            summary_data = json.load(f)
        
        v1_count = summary_data.get("v1_count", 0)
        if v1_count < 23:
            print(f"  ❌ V1 count too low: {v1_count} < 23")
            return False
        
        domain_v1_progress = summary_data.get("domain_v1_progress", {})
        auth_progress = domain_v1_progress.get("auth", {})
        
        if not auth_progress:
            print("  ❌ Missing domain_v1_progress.auth metrics")
            return False
            
        migrated_count = auth_progress.get("migrated_v1_route_count", 0)
        if migrated_count < 6:
            print(f"  ❌ Auth migrated V1 route count too low: {migrated_count} < 6")
            return False
        
        print(f"  ✅ Summary shows v1_count={v1_count}, auth migrated={migrated_count}")
        
        print("  ✅ All inventory/telemetry artifacts validated")
        return True
        
    except Exception as e:
        print(f"  ❌ Inventory artifacts test failed: {e}")
        return False


if __name__ == "__main__":
    success = test_pr_v1_2b_session_rollout()
    exit(0 if success else 1)