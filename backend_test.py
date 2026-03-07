#!/usr/bin/env python3
"""
Backend Test for PR-V1-2A Auth Bootstrap Rollout

This test validates:
1. Legacy auth routes with compat headers
2. New v1 auth alias routes  
3. Cookie-compatible web flow and bearer flow
4. Mobile BFF safety
5. Route inventory expectations
"""
import json
import asyncio
import aiohttp
import sys
from typing import Dict, Any, Optional

# Configuration
BASE_URL = "https://saas-modernize-2.preview.emergentagent.com"
ADMIN_EMAIL = "admin@acenta.test"
ADMIN_PASSWORD = "admin123"
WEB_HEADER = {"X-Client-Platform": "web"}

class TestResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.tests = []
        
    def add_test(self, name: str, success: bool, message: str):
        self.tests.append({
            "name": name,
            "success": success,
            "message": message
        })
        if success:
            self.passed += 1
        else:
            self.failed += 1
            
    def print_summary(self):
        print(f"\n{'='*60}")
        print(f"PR-V1-2A AUTH BOOTSTRAP ROLLOUT TEST SUMMARY")
        print(f"{'='*60}")
        print(f"✅ PASSED: {self.passed}")
        print(f"❌ FAILED: {self.failed}")
        print(f"📊 SUCCESS RATE: {self.passed / (self.passed + self.failed) * 100:.1f}%")
        print(f"{'='*60}")
        
        for test in self.tests:
            status = "✅" if test["success"] else "❌"
            print(f"{status} {test['name']}")
            if not test["success"] or True:  # Show details for all tests
                print(f"   {test['message']}")
        print(f"{'='*60}")

result = TestResult()

async def make_request(
    session: aiohttp.ClientSession,
    method: str,
    url: str,
    headers: Optional[Dict] = None,
    json_data: Optional[Dict] = None,
    cookies: Optional[Dict] = None
) -> Dict[str, Any]:
    """Make HTTP request and return response details."""
    try:
        kwargs = {}
        if headers:
            kwargs['headers'] = headers
        if json_data:
            kwargs['json'] = json_data
        if cookies:
            kwargs['cookies'] = cookies
            
        async with session.request(method, f"{BASE_URL}{url}", **kwargs) as response:
            try:
                response_json = await response.json()
            except:
                response_json = {}
                
            return {
                "status_code": response.status,
                "headers": {k.lower(): v for k, v in response.headers.items()},  # Normalize headers to lowercase
                "json": response_json,
                "cookies": {name: morsel.value for name, morsel in response.cookies.items()},
                "text": await response.text() if response.status != 200 else ""
            }
    except Exception as e:
        return {
            "status_code": 0,
            "headers": {},
            "json": {},
            "cookies": {},
            "text": str(e),
            "error": str(e)
        }

async def test_legacy_auth_routes_with_compat_headers():
    """Test legacy auth routes return proper deprecation headers."""
    connector = aiohttp.TCPConnector()
    jar = aiohttp.CookieJar()
    async with aiohttp.ClientSession(connector=connector, cookie_jar=jar) as session:
        # Test POST /api/auth/login
        async with session.post(f"{BASE_URL}/api/auth/login", 
                               json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
                               headers=WEB_HEADER) as resp:
            login_success = resp.status == 200
            headers = {k.lower(): v for k, v in resp.headers.items()}
            has_deprecation = headers.get("deprecation") == "true"
            link_header = headers.get("link", "")
            has_link = "</api/v1/auth/login>; rel=\"successor-version\"" in link_header
            
            result.add_test(
                "Legacy POST /api/auth/login with compat headers",
                login_success and has_deprecation and has_link,
                f"Status: {resp.status}, Deprecation: {has_deprecation}, Link header: {has_link}"
            )
            
            if not login_success:
                return None
                
            data = await resp.json()
            access_token = data.get("access_token")
        
        # Test GET /api/auth/me - cookies should be automatic  
        async with session.get(f"{BASE_URL}/api/auth/me", headers=WEB_HEADER) as resp:
            me_success = resp.status == 200
            headers = {k.lower(): v for k, v in resp.headers.items()}
            has_deprecation = headers.get("deprecation") == "true" 
            link_header = headers.get("link", "")
            has_link = "</api/v1/auth/me>; rel=\"successor-version\"" in link_header
            
            result.add_test(
                "Legacy GET /api/auth/me with compat headers",
                me_success and has_deprecation and has_link,
                f"Status: {resp.status}, Deprecation: {has_deprecation}, Link header: {has_link}"
            )
        
        # Test POST /api/auth/refresh - cookies should be automatic
        async with session.post(f"{BASE_URL}/api/auth/refresh", 
                               json={}, headers=WEB_HEADER) as resp:
            refresh_success = resp.status == 200
            headers = {k.lower(): v for k, v in resp.headers.items()}
            has_deprecation = headers.get("deprecation") == "true"
            link_header = headers.get("link", "")
            has_link = "</api/v1/auth/refresh>; rel=\"successor-version\"" in link_header
            
            result.add_test(
                "Legacy POST /api/auth/refresh with compat headers", 
                refresh_success and has_deprecation and has_link,
                f"Status: {resp.status}, Deprecation: {has_deprecation}, Link header: {has_link}"
            )
        
        return access_token

async def test_v1_auth_alias_routes():
    """Test new v1 auth alias routes work correctly."""
    connector = aiohttp.TCPConnector()
    jar = aiohttp.CookieJar()
    async with aiohttp.ClientSession(connector=connector, cookie_jar=jar) as session:
        # Test POST /api/v1/auth/login
        async with session.post(f"{BASE_URL}/api/v1/auth/login", 
                               json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
                               headers=WEB_HEADER) as resp:
            login_success = resp.status == 200
            data = await resp.json() if login_success else {}
            auth_transport = data.get("auth_transport")
            
            result.add_test(
                "New POST /api/v1/auth/login works",
                login_success and auth_transport == "cookie_compat",
                f"Status: {resp.status}, Auth transport: {auth_transport}"
            )
            
            if not login_success:
                return None
                
            access_token = data.get("access_token")
        
        # Test GET /api/v1/auth/me
        async with session.get(f"{BASE_URL}/api/v1/auth/me", headers=WEB_HEADER) as resp:
            me_success = resp.status == 200
            data = await resp.json() if me_success else {}
            email = data.get("email")
            
            result.add_test(
                "New GET /api/v1/auth/me works",
                me_success and email == ADMIN_EMAIL,
                f"Status: {resp.status}, Email: {email}"
            )
        
        # Test POST /api/v1/auth/refresh
        async with session.post(f"{BASE_URL}/api/v1/auth/refresh", 
                               json={}, headers=WEB_HEADER) as resp:
            refresh_success = resp.status == 200
            data = await resp.json() if refresh_success else {}
            new_token = data.get("access_token")
            
            result.add_test(
                "New POST /api/v1/auth/refresh works", 
                refresh_success and new_token is not None,
                f"Status: {resp.status}, New token received: {new_token is not None}"
            )
        
        return access_token

async def test_cookie_and_bearer_flows():
    """Test both cookie-compatible web flow and bearer flow."""
    async with aiohttp.ClientSession() as session:
        # Test cookie-compatible web flow
        response = await make_request(
            session,
            "POST",
            "/api/v1/auth/login",
            headers=WEB_HEADER,
            json_data={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        
        cookie_login_success = response["status_code"] == 200
        auth_transport = response["json"].get("auth_transport")
        has_cookies = len(response["cookies"]) > 0
        
        result.add_test(
            "Cookie-compatible web flow",
            cookie_login_success and auth_transport == "cookie_compat" and has_cookies,
            f"Status: {response['status_code']}, Transport: {auth_transport}, Cookies: {has_cookies}"
        )
        
        # Test bearer flow (without X-Client-Platform header)
        response = await make_request(
            session,
            "POST", 
            "/api/v1/auth/login",
            json_data={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        
        bearer_login_success = response["status_code"] == 200
        auth_transport = response["json"].get("auth_transport")
        access_token = response["json"].get("access_token")
        
        result.add_test(
            "Bearer flow works",
            bearer_login_success and auth_transport == "bearer" and access_token,
            f"Status: {response['status_code']}, Transport: {auth_transport}, Token: {bool(access_token)}"
        )
        
        if bearer_login_success and access_token:
            # Test bearer token works with /api/v1/auth/me
            response = await make_request(
                session,
                "GET",
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            bearer_me_success = response["status_code"] == 200
            email = response["json"].get("email")
            
            result.add_test(
                "Bearer token auth works with v1/auth/me",
                bearer_me_success and email == ADMIN_EMAIL,
                f"Status: {response['status_code']}, Email: {email}"
            )

async def test_mobile_bff_safety():
    """Test Mobile BFF safety: GET /api/v1/mobile/auth/me with bearer token."""
    async with aiohttp.ClientSession() as session:
        # Get bearer token
        response = await make_request(
            session,
            "POST",
            "/api/v1/auth/login", 
            json_data={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        
        if response["status_code"] != 200:
            result.add_test(
                "Mobile BFF safety test - login failed",
                False,
                f"Failed to get bearer token: {response['status_code']}"
            )
            return
            
        access_token = response["json"].get("access_token")
        
        # Test mobile auth/me endpoint
        response = await make_request(
            session,
            "GET",
            "/api/v1/mobile/auth/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        mobile_success = response["status_code"] == 200
        email = response["json"].get("email")
        
        result.add_test(
            "Mobile BFF GET /api/v1/mobile/auth/me works with bearer token",
            mobile_success and email == ADMIN_EMAIL,
            f"Status: {response['status_code']}, Email: {email}"
        )

async def test_route_inventory_expectations():
    """Test route inventory expectations: 678 total routes, 20 v1 routes, 658 legacy routes."""
    try:
        # Read route inventory summary
        with open("/app/backend/app/bootstrap/route_inventory_summary.json", "r") as f:
            summary = json.load(f)
            
        total_routes = summary.get("route_count", 0)
        v1_routes = summary.get("v1_count", 0) 
        legacy_routes = summary.get("legacy_count", 0)
        auth_routes = summary.get("namespaces", {}).get("auth", 0)
        
        # Expected: 678 total, 20 v1, 658 legacy, auth aliases +3
        expected_total = 678
        expected_v1 = 20
        expected_legacy = 658
        
        total_match = total_routes == expected_total
        v1_match = v1_routes == expected_v1  
        legacy_match = legacy_routes == expected_legacy
        auth_increase = auth_routes >= 17  # Should have increased from previous count
        
        result.add_test(
            f"Route inventory total routes ({expected_total})",
            total_match,
            f"Expected: {expected_total}, Actual: {total_routes}"
        )
        
        result.add_test(
            f"Route inventory v1 routes ({expected_v1})", 
            v1_match,
            f"Expected: {expected_v1}, Actual: {v1_routes}"
        )
        
        result.add_test(
            f"Route inventory legacy routes ({expected_legacy})",
            legacy_match, 
            f"Expected: {expected_legacy}, Actual: {legacy_routes}"
        )
        
        result.add_test(
            "Route inventory auth namespace has aliases",
            auth_increase,
            f"Auth routes count: {auth_routes} (should be >= 17 with new aliases)"
        )
        
    except Exception as e:
        result.add_test(
            "Route inventory file accessible",
            False,
            f"Error reading route inventory: {str(e)}"
        )

async def test_parity_between_legacy_and_v1():
    """Test that legacy and v1 routes return identical responses (except headers)."""
    async with aiohttp.ClientSession() as session:
        # Get tokens for both flows
        legacy_response = await make_request(
            session,
            "POST",
            "/api/auth/login",
            headers=WEB_HEADER,
            json_data={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        
        v1_response = await make_request(
            session,
            "POST", 
            "/api/v1/auth/login",
            headers=WEB_HEADER,
            json_data={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        
        if legacy_response["status_code"] == 200 and v1_response["status_code"] == 200:
            # Compare key fields (ignoring headers and timestamps)
            legacy_user = legacy_response["json"].get("user", {})
            v1_user = v1_response["json"].get("user", {})
            
            email_match = legacy_user.get("email") == v1_user.get("email")
            roles_match = legacy_user.get("roles") == v1_user.get("roles")
            transport_match = (legacy_response["json"].get("auth_transport") == 
                             v1_response["json"].get("auth_transport"))
            
            result.add_test(
                "Legacy and V1 auth/login return equivalent data",
                email_match and roles_match and transport_match,
                f"Email match: {email_match}, Roles match: {roles_match}, Transport match: {transport_match}"
            )
        else:
            result.add_test(
                "Legacy and V1 auth/login parity test",
                False,
                f"Login failed - Legacy: {legacy_response['status_code']}, V1: {v1_response['status_code']}"
            )

async def main():
    """Run all PR-V1-2A auth bootstrap rollout tests."""
    print("🚀 Starting PR-V1-2A Auth Bootstrap Rollout Tests")
    print(f"🎯 Base URL: {BASE_URL}")
    print(f"👤 Admin Email: {ADMIN_EMAIL}")
    print("="*60)
    
    try:
        # Test 1: Legacy auth routes with compat headers
        print("1️⃣  Testing legacy auth routes with compat headers...")
        await test_legacy_auth_routes_with_compat_headers()
        
        # Test 2: New v1 auth alias routes
        print("2️⃣  Testing new v1 auth alias routes...")
        await test_v1_auth_alias_routes()
        
        # Test 3: Cookie and bearer flows
        print("3️⃣  Testing cookie-compatible web flow and bearer flow...")
        await test_cookie_and_bearer_flows()
        
        # Test 4: Mobile BFF safety
        print("4️⃣  Testing Mobile BFF safety...")
        await test_mobile_bff_safety()
        
        # Test 5: Route inventory expectations
        print("5️⃣  Testing route inventory expectations...")
        await test_route_inventory_expectations()
        
        # Test 6: Parity between legacy and v1
        print("6️⃣  Testing parity between legacy and v1 routes...")
        await test_parity_between_legacy_and_v1()
        
    except Exception as e:
        result.add_test(
            "Test execution",
            False,
            f"Test execution error: {str(e)}"
        )
    
    # Print results
    result.print_summary()
    
    # Exit with appropriate code
    return 0 if result.failed == 0 else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)