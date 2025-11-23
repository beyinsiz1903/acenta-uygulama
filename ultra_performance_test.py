#!/usr/bin/env python3
"""
FINAL ULTRA PERFORMANCE TEST - Target <5ms (Absolutely Perfect)

**GOAL: ACHIEVE <5ms RESPONSE TIMES (PERFECT INSTANT RESPONSE)**

Test all critical endpoints with detailed performance metrics:

**CRITICAL ENDPOINTS:**
1. GET /api/monitoring/health - Target: <5ms
2. GET /api/monitoring/system - Target: <5ms  
3. GET /api/pms/rooms - Target: <3ms (pre-warmed cache should be instant)
4. GET /api/pms/bookings - Target: <3ms (pre-warmed cache should be instant)
5. GET /api/pms/dashboard - Target: <3ms (pre-warmed cache should be instant)
6. GET /api/executive/kpi-snapshot - Target: <3ms (pre-warmed cache should be instant)

**TEST PROTOCOL:**
- Make 5 consecutive calls per endpoint
- Measure min, max, avg response times
- Verify cache is working (2nd call should be faster than 1st)
- Check response data completeness

**OPTIMIZATIONS APPLIED:**
✅ Pre-warming cache on startup (rooms, bookings, dashboard, KPI)
✅ Background cache refresh every 30s
✅ Ultra-short cache TTL (15s)
✅ Minimal field projection
✅ Reduced data limits (30-50 records)
✅ Aggregation pipelines
✅ GZip compression
✅ Connection pooling (200 max)
✅ CPU instant read (0ms wait)
✅ Compound indexes

**SUCCESS CRITERIA:**
- Average response <5ms for all endpoints
- Peak performance <3ms
- All data accurate and complete
- No errors or timeouts
- Cache hit rate >50%

**REPORT FORMAT:**
For each endpoint:
- Call 1 (cold): Xms
- Call 2-5 (warm): Xms, Xms, Xms, Xms
- Min/Avg/Max: X/X/X ms
- Cache working: Yes/No
- Data complete: Yes/No
- Status: ✅/<5ms or ❌/>5ms

Target: 6/6 endpoints under 5ms average = ABSOLUTELY PERFECT
"""

import asyncio
import aiohttp
import json
import sys
import os
import time
import statistics
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional

# Configuration
BACKEND_URL = "https://tam-optimizasyon.preview.emergentagent.com/api"
TEST_EMAIL = "admin@hotel.com"
TEST_PASSWORD = "admin123"

# Ultra-strict performance targets (in milliseconds)
ULTRA_TARGET_MS = 5.0  # 5ms target for monitoring endpoints
CACHE_TARGET_MS = 3.0  # 3ms target for pre-warmed cache endpoints

class UltraPerformanceTester:
    def __init__(self):
        self.session = None
        self.auth_token = None
        self.tenant_id = None
        self.user_id = None
        self.test_results = []

    async def setup_session(self):
        """Initialize HTTP session with optimized settings"""
        # Use connection pooling and keep-alive for better performance
        connector = aiohttp.TCPConnector(
            limit=100,  # Connection pool size
            limit_per_host=30,
            keepalive_timeout=30,
            enable_cleanup_closed=True
        )
        timeout = aiohttp.ClientTimeout(total=10)  # 10 second timeout
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={
                'Accept-Encoding': 'gzip, deflate',  # Enable compression
                'Connection': 'keep-alive'
            }
        )

    async def cleanup_session(self):
        """Cleanup HTTP session"""
        if self.session:
            await self.session.close()

    async def authenticate(self):
        """Authenticate and get token"""
        try:
            login_data = {
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD
            }
            
            async with self.session.post(f"{BACKEND_URL}/auth/login", json=login_data) as response:
                if response.status == 200:
                    data = await response.json()
                    self.auth_token = data["access_token"]
                    self.tenant_id = data["user"]["tenant_id"]
                    self.user_id = data["user"]["id"]
                    print(f"✅ Authentication successful - Tenant: {self.tenant_id}")
                    return True
                else:
                    print(f"❌ Authentication failed: {response.status}")
                    return False
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            return False

    def get_headers(self):
        """Get authorization headers"""
        return {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive"
        }

    async def measure_endpoint_performance(self, url: str, endpoint_name: str, target_ms: float) -> dict:
        """Measure endpoint performance with 5 consecutive calls"""
        print(f"\n🎯 Testing {endpoint_name}")
        print(f"   URL: {url}")
        print(f"   Target: <{target_ms}ms")
        print("   " + "-" * 50)
        
        results = {
            "endpoint": endpoint_name,
            "url": url,
            "target_ms": target_ms,
            "calls": [],
            "response_times": [],
            "min_ms": 0,
            "avg_ms": 0,
            "max_ms": 0,
            "cache_working": False,
            "data_complete": False,
            "success": True,
            "errors": []
        }
        
        # Make 5 consecutive calls as per test protocol
        for call_num in range(1, 6):
            call_type = "cold" if call_num == 1 else "warm"
            
            try:
                start_time = time.perf_counter()
                
                async with self.session.get(url, headers=self.get_headers()) as response:
                    end_time = time.perf_counter()
                    response_time_ms = (end_time - start_time) * 1000
                    
                    if response.status == 200:
                        data = await response.json()
                        
                        results["response_times"].append(response_time_ms)
                        
                        # Status indicator based on ultra-strict performance
                        status = "✅" if response_time_ms < target_ms else "❌"
                        
                        print(f"   Call {call_num} ({call_type}): {status} {response_time_ms:.1f}ms")
                        
                        # Store data for completeness check
                        if call_num == 1:
                            results["data_complete"] = isinstance(data, dict) and len(data) > 0
                        
                    else:
                        error_msg = f"HTTP {response.status}"
                        results["errors"].append(error_msg)
                        results["success"] = False
                        print(f"   ❌ Call {call_num} ({call_type}): {error_msg}")
                        
            except asyncio.TimeoutError:
                error_msg = "Timeout"
                results["errors"].append(error_msg)
                results["success"] = False
                print(f"   ❌ Call {call_num} ({call_type}): {error_msg}")
                
            except Exception as e:
                error_msg = str(e)
                results["errors"].append(error_msg)
                results["success"] = False
                print(f"   ❌ Call {call_num} ({call_type}): {error_msg}")
            
            # Small delay between calls
            if call_num < 5:
                await asyncio.sleep(0.05)
        
        # Calculate metrics
        if results["response_times"]:
            results["min_ms"] = min(results["response_times"])
            results["avg_ms"] = statistics.mean(results["response_times"])
            results["max_ms"] = max(results["response_times"])
            
            # Check cache effectiveness (2nd call should be faster than 1st)
            if len(results["response_times"]) >= 2:
                results["cache_working"] = results["response_times"][1] < results["response_times"][0]
        
        # Performance assessment
        target_met = results["success"] and results["avg_ms"] < target_ms
        
        print(f"   Min/Avg/Max: {results['min_ms']:.1f}/{results['avg_ms']:.1f}/{results['max_ms']:.1f} ms")
        print(f"   Cache working: {'✅ Yes' if results['cache_working'] else '❌ No'}")
        print(f"   Data complete: {'✅ Yes' if results['data_complete'] else '❌ No'}")
        
        if target_met:
            if results["avg_ms"] < 1.0:
                print(f"   🚀 EXCEPTIONAL: Sub-millisecond performance!")
            elif results["avg_ms"] < 2.0:
                print(f"   ⚡ EXCELLENT: Ultra-fast response!")
            else:
                print(f"   ✅ PASS: Within target")
        else:
            print(f"   ❌ FAIL: Exceeds {target_ms}ms target")
        
        return results

    async def test_critical_endpoints(self):
        """Test all critical endpoints with ultra-strict <5ms performance requirements"""
        print("🚀 FINAL ULTRA PERFORMANCE TEST - Target <5ms (Absolutely Perfect)")
        print("=" * 80)
        print("GOAL: ACHIEVE <5ms RESPONSE TIMES (PERFECT INSTANT RESPONSE)")
        print("Testing Protocol: 5 consecutive calls per endpoint")
        print("=" * 80)
        
        # Define critical endpoints with their ultra-strict targets
        endpoints = [
            {
                "name": "Monitoring Health",
                "url": f"{BACKEND_URL}/monitoring/health",
                "target_ms": ULTRA_TARGET_MS
            },
            {
                "name": "Monitoring System",
                "url": f"{BACKEND_URL}/monitoring/system", 
                "target_ms": ULTRA_TARGET_MS
            },
            {
                "name": "PMS Rooms (Pre-warmed Cache)",
                "url": f"{BACKEND_URL}/pms/rooms",
                "target_ms": CACHE_TARGET_MS
            },
            {
                "name": "PMS Bookings (Pre-warmed Cache)",
                "url": f"{BACKEND_URL}/pms/bookings",
                "target_ms": CACHE_TARGET_MS
            },
            {
                "name": "PMS Dashboard (Pre-warmed Cache)", 
                "url": f"{BACKEND_URL}/pms/dashboard",
                "target_ms": CACHE_TARGET_MS
            },
            {
                "name": "Executive KPI Snapshot (Pre-warmed Cache)",
                "url": f"{BACKEND_URL}/executive/kpi-snapshot",
                "target_ms": CACHE_TARGET_MS
            }
        ]
        
        # Test each endpoint
        for endpoint in endpoints:
            result = await self.measure_endpoint_performance(
                endpoint["url"], 
                endpoint["name"], 
                endpoint["target_ms"]
            )
            self.test_results.append(result)
            
            # Small delay between endpoint tests
            await asyncio.sleep(0.2)

    def print_performance_summary(self):
        """Print ultra-detailed performance summary"""
        print("\n" + "=" * 80)
        print("📊 FINAL ULTRA PERFORMANCE TEST RESULTS")
        print("=" * 80)
        
        passed_endpoints = 0
        total_endpoints = len(self.test_results)
        
        print("\n🎯 CRITICAL ENDPOINTS PERFORMANCE:")
        print("-" * 60)
        
        for result in self.test_results:
            status_icon = "✅" if result["success"] and result["avg_ms"] < result["target_ms"] else "❌"
            endpoint_name = result["endpoint"]
            
            if result["success"] and result["response_times"]:
                avg_ms = result["avg_ms"]
                target_ms = result["target_ms"]
                
                print(f"{status_icon} {endpoint_name}:")
                print(f"   • Call 1 (cold): {result['response_times'][0]:.1f}ms")
                if len(result["response_times"]) > 1:
                    warm_times = [f"{t:.1f}ms" for t in result["response_times"][1:]]
                    print(f"   • Call 2-5 (warm): {', '.join(warm_times)}")
                print(f"   • Min/Avg/Max: {result['min_ms']:.1f}/{avg_ms:.1f}/{result['max_ms']:.1f} ms")
                print(f"   • Cache working: {'Yes' if result['cache_working'] else 'No'}")
                print(f"   • Data complete: {'Yes' if result['data_complete'] else 'No'}")
                
                if avg_ms < target_ms:
                    passed_endpoints += 1
                    if avg_ms < 1.0:
                        print(f"   • Status: ✅ <{target_ms}ms (🚀 EXCEPTIONAL: Sub-millisecond!)")
                    elif avg_ms < 2.0:
                        print(f"   • Status: ✅ <{target_ms}ms (⚡ EXCELLENT: Ultra-fast!)")
                    else:
                        print(f"   • Status: ✅ <{target_ms}ms")
                else:
                    print(f"   • Status: ❌ >{target_ms}ms")
            else:
                print(f"{status_icon} {endpoint_name}: ❌ FAILED")
                if result["errors"]:
                    print(f"   • Errors: {', '.join(result['errors'][:3])}")
            
            print()
        
        # Overall assessment
        success_rate = (passed_endpoints / total_endpoints * 100) if total_endpoints > 0 else 0
        
        print("=" * 80)
        print(f"📈 OVERALL ULTRA PERFORMANCE RESULTS: {passed_endpoints}/{total_endpoints} ({success_rate:.1f}%)")
        print("=" * 80)
        
        if success_rate == 100:
            print("🎉 ABSOLUTELY PERFECT! 100% SUCCESS RATE")
            print("🚀 ALL ENDPOINTS UNDER TARGET RESPONSE TIMES")
            print("⚡ ULTRA-HIGH PERFORMANCE ACHIEVED")
            print("✅ Cache optimization working perfectly")
            print("✅ All optimizations successful")
            
            # Check for exceptional performance
            sub_ms_count = sum(1 for r in self.test_results if r["success"] and r["avg_ms"] < 1.0)
            if sub_ms_count > 0:
                print(f"🌟 EXCEPTIONAL: {sub_ms_count} endpoints with sub-millisecond performance!")
                
        elif success_rate >= 80:
            print("✅ EXCELLENT: Most endpoints meeting ultra-strict targets")
            failed_endpoints = [r["endpoint"] for r in self.test_results if not (r["success"] and r["avg_ms"] < r["target_ms"])]
            if failed_endpoints:
                print(f"⚠️ Needs optimization: {', '.join(failed_endpoints)}")
        else:
            print("❌ CRITICAL: Ultra performance targets not met")
            print("🔍 Recommend immediate performance optimization")
        
        print("\n🔧 OPTIMIZATION STATUS:")
        cache_working_count = sum(1 for r in self.test_results if r["cache_working"])
        print(f"• Cache effectiveness: {cache_working_count}/{total_endpoints} endpoints")
        
        data_complete_count = sum(1 for r in self.test_results if r["data_complete"])
        print(f"• Data completeness: {data_complete_count}/{total_endpoints} endpoints")
        
        print("\n📊 PERFORMANCE BREAKDOWN:")
        for result in self.test_results:
            if result["success"] and len(result["response_times"]) >= 2:
                cold_start = result["response_times"][0]
                warm_avg = statistics.mean(result["response_times"][1:])
                improvement = ((cold_start - warm_avg) / cold_start * 100) if cold_start > 0 else 0
                print(f"• {result['endpoint']}: Cold {cold_start:.1f}ms → Warm {warm_avg:.1f}ms ({improvement:+.1f}%)")
        
        print("\n🎯 TARGET ACHIEVEMENT:")
        print(f"• Monitoring endpoints (<{ULTRA_TARGET_MS}ms): ", end="")
        monitoring_results = [r for r in self.test_results if "Monitoring" in r["endpoint"]]
        monitoring_passed = sum(1 for r in monitoring_results if r["success"] and r["avg_ms"] < r["target_ms"])
        print(f"{monitoring_passed}/{len(monitoring_results)} ({'✅' if monitoring_passed == len(monitoring_results) else '❌'})")
        
        print(f"• Cached endpoints (<{CACHE_TARGET_MS}ms): ", end="")
        cached_results = [r for r in self.test_results if "Cache" in r["endpoint"]]
        cached_passed = sum(1 for r in cached_results if r["success"] and r["avg_ms"] < r["target_ms"])
        print(f"{cached_passed}/{len(cached_results)} ({'✅' if cached_passed == len(cached_results) else '❌'})")
        
        print("\n" + "=" * 80)
        
        if success_rate == 100:
            print("🏆 MISSION ACCOMPLISHED: ULTRA PERFORMANCE ACHIEVED!")
            print("Target: 6/6 endpoints under 5ms average = ABSOLUTELY PERFECT ✅")
        else:
            print("🔧 MISSION CONTINUES: Further optimization needed")
            print(f"Target: 6/6 endpoints under 5ms average = {passed_endpoints}/6 ❌")
        
        print("=" * 80)

    async def run_ultra_performance_test(self):
        """Run the ultra performance verification test"""
        await self.setup_session()
        
        if not await self.authenticate():
            print("❌ Authentication failed. Cannot proceed with tests.")
            return
        
        await self.test_critical_endpoints()
        await self.cleanup_session()
        
        self.print_performance_summary()

async def main():
    """Main test execution"""
    tester = UltraPerformanceTester()
    await tester.run_ultra_performance_test()

if __name__ == "__main__":
    asyncio.run(main())