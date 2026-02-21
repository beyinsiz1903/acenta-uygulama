#!/usr/bin/env python3
"""
Platform Hardening Features Backend Testing Script
Tests all newly implemented platform hardening & security features
"""

import asyncio
import json
import sys
from typing import Any, Dict, Optional

import httpx


class PlatformHardeningTester:
    def __init__(self, base_url: str = "https://booking-lifecycle-2.preview.emergentagent.com"):
        self.base_url = base_url.rstrip('/')
        self.session = httpx.AsyncClient(timeout=30.0)
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        
    async def cleanup(self):
        """Close the HTTP session"""
        await self.session.aclose()

    def get_auth_headers(self) -> Dict[str, str]:
        """Get authorization headers with Bearer token"""
        if not self.access_token:
            return {}
        return {"Authorization": f"Bearer {self.access_token}"}

    async def test_login_and_refresh_token(self) -> Dict[str, Any]:
        """Test 1: Login & Refresh Token functionality"""
        print("\n🔐 Testing Login & Refresh Token...")
        
        # Test login
        login_payload = {
            "email": "admin@acenta.test",
            "password": "admin123"
        }
        
        try:
            response = await self.session.post(
                f"{self.base_url}/api/auth/login",
                json=login_payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code != 200:
                return {
                    "success": False,
                    "error": f"Login failed with status {response.status_code}: {response.text}"
                }
            
            data = response.json()
            
            # Check required fields
            required_fields = ["access_token", "refresh_token", "expires_in"]
            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                return {
                    "success": False,
                    "error": f"Missing required fields in login response: {missing_fields}"
                }
            
            self.access_token = data["access_token"]
            self.refresh_token = data["refresh_token"]
            
            print(f"✅ Login successful - got access_token and refresh_token")
            
            # Test refresh token
            refresh_payload = {
                "refresh_token": self.refresh_token
            }
            
            refresh_response = await self.session.post(
                f"{self.base_url}/api/auth/refresh",
                json=refresh_payload,
                headers={"Content-Type": "application/json"}
            )
            
            if refresh_response.status_code != 200:
                return {
                    "success": False,
                    "error": f"Refresh token failed with status {refresh_response.status_code}: {refresh_response.text}"
                }
            
            refresh_data = refresh_response.json()
            
            # Check refresh response
            refresh_required_fields = ["access_token", "refresh_token", "expires_in"]
            missing_refresh_fields = [field for field in refresh_required_fields if field not in refresh_data]
            if missing_refresh_fields:
                return {
                    "success": False,
                    "error": f"Missing fields in refresh response: {missing_refresh_fields}"
                }
            
            # Update tokens
            self.access_token = refresh_data["access_token"]
            self.refresh_token = refresh_data["refresh_token"]
            
            print(f"✅ Refresh token successful - got new tokens")
            
            return {
                "success": True,
                "login_status": response.status_code,
                "refresh_status": refresh_response.status_code,
                "has_access_token": bool(self.access_token),
                "has_refresh_token": bool(self.refresh_token),
                "expires_in": data.get("expires_in")
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Exception during login/refresh test: {str(e)}"
            }

    async def test_sessions(self) -> Dict[str, Any]:
        """Test 2: Sessions management"""
        print("\n📊 Testing Sessions...")
        
        if not self.access_token:
            return {
                "success": False,
                "error": "No access token available - login test must run first"
            }
        
        try:
            response = await self.session.get(
                f"{self.base_url}/api/auth/sessions",
                headers=self.get_auth_headers()
            )
            
            if response.status_code != 200:
                return {
                    "success": False,
                    "error": f"Sessions request failed with status {response.status_code}: {response.text}"
                }
            
            data = response.json()
            
            # Should return array of sessions
            if not isinstance(data, list):
                return {
                    "success": False,
                    "error": f"Sessions response should be an array, got: {type(data)}"
                }
            
            print(f"✅ Sessions endpoint working - returned {len(data)} session(s)")
            
            return {
                "success": True,
                "status_code": response.status_code,
                "session_count": len(data),
                "sessions": data[:2] if data else []  # Return first 2 sessions for inspection
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Exception during sessions test: {str(e)}"
            }

    async def test_cancel_reason_codes(self) -> Dict[str, Any]:
        """Test 3: Cancel Reason Codes (no auth required)"""
        print("\n📋 Testing Cancel Reason Codes...")
        
        try:
            response = await self.session.get(
                f"{self.base_url}/api/reference/cancel-reasons"
            )
            
            if response.status_code != 200:
                return {
                    "success": False,
                    "error": f"Cancel reasons request failed with status {response.status_code}: {response.text}"
                }
            
            data = response.json()
            
            # Should return list of cancel reason codes
            if not isinstance(data, list):
                return {
                    "success": False,
                    "error": f"Cancel reasons should be a list, got: {type(data)}"
                }
            
            if not data:
                return {
                    "success": False,
                    "error": "Cancel reasons list is empty"
                }
            
            # Check structure of first item
            first_item = data[0]
            if not isinstance(first_item, dict) or "code" not in first_item or "label" not in first_item:
                return {
                    "success": False,
                    "error": f"Cancel reason items should have 'code' and 'label' fields. Got: {first_item}"
                }
            
            print(f"✅ Cancel reasons working - returned {len(data)} codes")
            
            return {
                "success": True,
                "status_code": response.status_code,
                "reason_count": len(data),
                "sample_reasons": data[:3]  # Return first 3 for inspection
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Exception during cancel reasons test: {str(e)}"
            }

    async def test_multi_currency(self) -> Dict[str, Any]:
        """Test 4: Multi-currency functionality"""
        print("\n💱 Testing Multi-currency...")
        
        try:
            # Test 1: Get supported currencies (no auth required)
            currencies_response = await self.session.get(
                f"{self.base_url}/api/finance/currency/supported"
            )
            
            if currencies_response.status_code != 200:
                return {
                    "success": False,
                    "error": f"Supported currencies failed with status {currencies_response.status_code}: {currencies_response.text}"
                }
            
            currencies_data = currencies_response.json()
            
            if not isinstance(currencies_data, list):
                return {
                    "success": False,
                    "error": f"Supported currencies should be a list, got: {type(currencies_data)}"
                }
            
            print(f"✅ Supported currencies working - {len(currencies_data)} currencies")
            
            # Test 2: Currency conversion (requires auth)
            if not self.access_token:
                return {
                    "success": False,
                    "error": "No access token for currency conversion test"
                }
            
            convert_payload = {
                "amount": 100,
                "from_currency": "EUR",
                "to_currency": "TRY"
            }
            
            convert_response = await self.session.post(
                f"{self.base_url}/api/finance/currency/convert",
                json=convert_payload,
                headers={**self.get_auth_headers(), "Content-Type": "application/json"}
            )
            
            if convert_response.status_code != 200:
                return {
                    "success": False,
                    "error": f"Currency convert failed with status {convert_response.status_code}: {convert_response.text}"
                }
            
            convert_data = convert_response.json()
            
            print(f"✅ Currency conversion working - EUR to TRY conversion successful")
            
            return {
                "success": True,
                "currencies_status": currencies_response.status_code,
                "convert_status": convert_response.status_code,
                "supported_currencies": currencies_data,
                "conversion_result": convert_data
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Exception during multi-currency test: {str(e)}"
            }

    async def test_health_dashboard(self) -> Dict[str, Any]:
        """Test 5: Health Dashboard & Prometheus"""
        print("\n🏥 Testing Health Dashboard & Prometheus...")
        
        try:
            # Test 1: Simple ping (no auth)
            ping_response = await self.session.get(
                f"{self.base_url}/api/system/ping"
            )
            
            if ping_response.status_code != 200:
                return {
                    "success": False,
                    "error": f"Ping failed with status {ping_response.status_code}: {ping_response.text}"
                }
            
            ping_data = ping_response.json()
            if ping_data.get("status") != "pong":
                return {
                    "success": False,
                    "error": f"Ping should return status: pong, got: {ping_data}"
                }
            
            print(f"✅ Ping/pong working")
            
            # Test 2: Health dashboard (requires auth)
            if not self.access_token:
                return {
                    "success": False,
                    "error": "No access token for health dashboard test"
                }
            
            health_response = await self.session.get(
                f"{self.base_url}/api/system/health-dashboard",
                headers=self.get_auth_headers()
            )
            
            if health_response.status_code != 200:
                return {
                    "success": False,
                    "error": f"Health dashboard failed with status {health_response.status_code}: {health_response.text}"
                }
            
            health_data = health_response.json()
            
            print(f"✅ Health dashboard working")
            
            # Test 3: Prometheus metrics (requires auth)
            prometheus_response = await self.session.get(
                f"{self.base_url}/api/system/prometheus",
                headers=self.get_auth_headers()
            )
            
            if prometheus_response.status_code != 200:
                return {
                    "success": False,
                    "error": f"Prometheus metrics failed with status {prometheus_response.status_code}: {prometheus_response.text}"
                }
            
            prometheus_data = prometheus_response.text
            
            # Should return Prometheus-style text metrics
            if not prometheus_data or not isinstance(prometheus_data, str):
                return {
                    "success": False,
                    "error": "Prometheus metrics should return text format"
                }
            
            print(f"✅ Prometheus metrics working - {len(prometheus_data)} characters")
            
            return {
                "success": True,
                "ping_status": ping_response.status_code,
                "health_status": health_response.status_code,
                "prometheus_status": prometheus_response.status_code,
                "ping_response": ping_data,
                "health_checks_available": bool(health_data),
                "prometheus_metrics_length": len(prometheus_data)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Exception during health/prometheus test: {str(e)}"
            }

    async def test_gdpr(self) -> Dict[str, Any]:
        """Test 6: GDPR functionality"""
        print("\n🛡️ Testing GDPR...")
        
        if not self.access_token:
            return {
                "success": False,
                "error": "No access token available for GDPR test"
            }
        
        try:
            # Test 1: Submit consent
            consent_payload = {
                "consent_type": "marketing",
                "granted": True
            }
            
            consent_response = await self.session.post(
                f"{self.base_url}/api/gdpr/consent",
                json=consent_payload,
                headers={**self.get_auth_headers(), "Content-Type": "application/json"}
            )
            
            if consent_response.status_code != 200:
                return {
                    "success": False,
                    "error": f"GDPR consent failed with status {consent_response.status_code}: {consent_response.text}"
                }
            
            consent_data = consent_response.json()
            
            print(f"✅ GDPR consent submission working")
            
            # Test 2: Get consents
            consents_response = await self.session.get(
                f"{self.base_url}/api/gdpr/consents",
                headers=self.get_auth_headers()
            )
            
            if consents_response.status_code != 200:
                return {
                    "success": False,
                    "error": f"GDPR consents list failed with status {consents_response.status_code}: {consents_response.text}"
                }
            
            consents_data = consents_response.json()
            
            print(f"✅ GDPR consents retrieval working - {len(consents_data) if isinstance(consents_data, list) else 0} consent(s)")
            
            return {
                "success": True,
                "consent_status": consent_response.status_code,
                "consents_status": consents_response.status_code,
                "consent_recorded": bool(consent_data.get("status") == "ok"),
                "consents_count": len(consents_data) if isinstance(consents_data, list) else 0
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Exception during GDPR test: {str(e)}"
            }

    async def test_security_headers(self) -> Dict[str, Any]:
        """Test 7: Security Headers on API responses"""
        print("\n🔒 Testing Security Headers...")
        
        try:
            # Test on a simple endpoint
            response = await self.session.get(
                f"{self.base_url}/api/system/ping"
            )
            
            if response.status_code != 200:
                return {
                    "success": False,
                    "error": f"Failed to get response for headers check: {response.status_code}"
                }
            
            headers = response.headers
            
            # Expected security headers
            expected_headers = {
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY", 
                "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
                "Content-Security-Policy": None,  # Check if present
                "Referrer-Policy": "strict-origin-when-cross-origin"
            }
            
            found_headers = {}
            missing_headers = []
            
            for header_name, expected_value in expected_headers.items():
                header_value = headers.get(header_name)
                if header_value:
                    found_headers[header_name] = header_value
                    if expected_value and header_value != expected_value:
                        print(f"⚠️ Header {header_name} value mismatch: expected '{expected_value}', got '{header_value}'")
                else:
                    missing_headers.append(header_name)
            
            success = len(missing_headers) == 0
            
            if success:
                print(f"✅ Security headers working - all expected headers present")
            else:
                print(f"❌ Missing security headers: {missing_headers}")
            
            return {
                "success": success,
                "found_headers": found_headers,
                "missing_headers": missing_headers,
                "status_code": response.status_code
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Exception during security headers test: {str(e)}"
            }

    async def test_cache_stats(self) -> Dict[str, Any]:
        """Test 8: Cache Stats"""
        print("\n💾 Testing Cache Stats...")
        
        if not self.access_token:
            return {
                "success": False,
                "error": "No access token available for cache stats test"
            }
        
        try:
            response = await self.session.get(
                f"{self.base_url}/api/admin/cache/stats",
                headers=self.get_auth_headers()
            )
            
            if response.status_code != 200:
                return {
                    "success": False,
                    "error": f"Cache stats failed with status {response.status_code}: {response.text}"
                }
            
            data = response.json()
            
            print(f"✅ Cache stats working")
            
            return {
                "success": True,
                "status_code": response.status_code,
                "cache_stats": data
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Exception during cache stats test: {str(e)}"
            }

    async def test_distributed_locks(self) -> Dict[str, Any]:
        """Test 9: Distributed Locks"""
        print("\n🔐 Testing Distributed Locks...")
        
        if not self.access_token:
            return {
                "success": False,
                "error": "No access token available for distributed locks test"
            }
        
        try:
            response = await self.session.get(
                f"{self.base_url}/api/admin/locks/",
                headers=self.get_auth_headers()
            )
            
            if response.status_code != 200:
                return {
                    "success": False,
                    "error": f"Distributed locks failed with status {response.status_code}: {response.text}"
                }
            
            data = response.json()
            
            print(f"✅ Distributed locks working - {len(data) if isinstance(data, list) else 0} active lock(s)")
            
            return {
                "success": True,
                "status_code": response.status_code,
                "active_locks_count": len(data) if isinstance(data, list) else 0,
                "locks": data if isinstance(data, list) else []
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Exception during distributed locks test: {str(e)}"
            }

    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all platform hardening tests"""
        print("🚀 Starting Platform Hardening Backend Tests...")
        print(f"🌐 Base URL: {self.base_url}")
        
        results = {}
        
        # Test 1: Login & Refresh Token (prerequisite for other tests)
        results["login_refresh"] = await self.test_login_and_refresh_token()
        
        # Test 2: Sessions
        results["sessions"] = await self.test_sessions()
        
        # Test 3: Cancel Reason Codes (no auth required)
        results["cancel_reasons"] = await self.test_cancel_reason_codes()
        
        # Test 4: Multi-currency
        results["multi_currency"] = await self.test_multi_currency()
        
        # Test 5: Health Dashboard & Prometheus
        results["health_dashboard"] = await self.test_health_dashboard()
        
        # Test 6: GDPR
        results["gdpr"] = await self.test_gdpr()
        
        # Test 7: Security Headers
        results["security_headers"] = await self.test_security_headers()
        
        # Test 8: Cache Stats
        results["cache_stats"] = await self.test_cache_stats()
        
        # Test 9: Distributed Locks
        results["distributed_locks"] = await self.test_distributed_locks()
        
        return results


async def main():
    """Main test runner"""
    tester = PlatformHardeningTester()
    
    try:
        results = await tester.run_all_tests()
        
        print("\n" + "="*80)
        print("🎯 PLATFORM HARDENING TESTS SUMMARY")
        print("="*80)
        
        passed_count = 0
        total_count = 0
        
        for test_name, result in results.items():
            total_count += 1
            status = "✅ PASS" if result.get("success") else "❌ FAIL"
            print(f"{status} {test_name.replace('_', ' ').title()}")
            
            if result.get("success"):
                passed_count += 1
            else:
                error = result.get("error", "Unknown error")
                print(f"    Error: {error}")
        
        print("="*80)
        print(f"📊 Results: {passed_count}/{total_count} tests passed")
        
        if passed_count == total_count:
            print("🎉 All platform hardening features are working correctly!")
        else:
            print(f"⚠️  {total_count - passed_count} test(s) failed - requires attention")
            
        # Write detailed results to file for debugging
        with open("platform_hardening_test_results.json", "w") as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"📝 Detailed results saved to platform_hardening_test_results.json")
        
        return passed_count == total_count
        
    except Exception as e:
        print(f"\n💥 Critical error during testing: {e}")
        return False
    
    finally:
        await tester.cleanup()


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)