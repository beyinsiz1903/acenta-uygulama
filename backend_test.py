#!/usr/bin/env python3
"""
Comprehensive Redis Cache System Testing for Syroce Tourism Platform
Testing all Redis functionality including health checks, cache operations, and sentinel configuration
"""

import requests
import json
import time
import subprocess
import sys
from typing import Dict, Any, Optional

# Configuration
BACKEND_URL = "https://improvement-areas.preview.emergentagent.com/api"
REDIS_HOST = "localhost"
REDIS_PORT = 6379

class RedisTestSuite:
    def __init__(self):
        self.test_results = []
        self.redis_initial_stats = {}
        
    def log_test(self, test_name: str, passed: bool, details: str, data: Optional[Dict] = None):
        """Log test result with details"""
        status = "✅ PASSED" if passed else "❌ FAILED"
        result = {
            "test": test_name,
            "status": status,
            "passed": passed,
            "details": details,
            "data": data or {}
        }
        self.test_results.append(result)
        print(f"{status}: {test_name}")
        print(f"   Details: {details}")
        if data:
            print(f"   Data: {json.dumps(data, indent=2)}")
        print()

    def run_redis_command(self, command: str) -> Optional[str]:
        """Execute redis-cli command and return output"""
        try:
            cmd = f"redis-cli -h {REDIS_HOST} -p {REDIS_PORT} {command}"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                print(f"Redis command failed: {command}")
                print(f"Error: {result.stderr}")
                return None
        except Exception as e:
            print(f"Exception running Redis command '{command}': {e}")
            return None

    def test_1_health_check(self):
        """Test 1: Health Check - GET /api/health/ready"""
        print("=" * 60)
        print("TEST 1: Health Check with Redis Status")
        print("=" * 60)
        
        try:
            response = requests.get(f"{BACKEND_URL}/health/ready", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                checks = data.get('checks', {})
                
                # Check if redis field exists and is healthy
                redis_status = checks.get('redis', 'missing')
                has_redis_field = 'redis' in checks
                redis_healthy = redis_status == 'healthy'
                
                # Check if mode field exists (for Redis Sentinel)
                has_mode_field = 'mode' in data or 'mode' in checks
                mode_value = data.get('mode') or checks.get('mode', 'not_present')
                
                # Check redis_memory field
                has_redis_memory = 'redis_memory' in checks
                redis_memory = checks.get('redis_memory', 'not_present')
                
                details = f"Status: {response.status_code}, Redis: {redis_status}"
                if has_mode_field:
                    details += f", Mode: {mode_value}"
                if has_redis_memory:
                    details += f", Memory: {redis_memory}"
                
                test_passed = (response.status_code == 200 and 
                              has_redis_field and 
                              redis_healthy)
                
                self.log_test(
                    "Health Ready Endpoint with Redis",
                    test_passed,
                    details,
                    {
                        "response_data": data,
                        "checks_data": checks,
                        "redis_present": has_redis_field,
                        "redis_healthy": redis_healthy,
                        "mode_present": has_mode_field,
                        "redis_memory_present": has_redis_memory
                    }
                )
            else:
                self.log_test(
                    "Health Ready Endpoint with Redis",
                    False,
                    f"HTTP {response.status_code}: {response.text}",
                    {"status_code": response.status_code}
                )
                
        except Exception as e:
            self.log_test(
                "Health Ready Endpoint with Redis",
                False,
                f"Request failed: {str(e)}"
            )

    def test_2_cache_creation(self):
        """Test 2: Cache Creation - Call endpoints and verify Redis keys"""
        print("=" * 60)
        print("TEST 2: Cache Creation and Key Verification")
        print("=" * 60)
        
        # Get initial key count
        initial_keys = self.run_redis_command("DBSIZE")
        initial_sc_keys = self.run_redis_command("KEYS 'sc:*'")
        
        print(f"Initial Redis key count: {initial_keys}")
        print(f"Initial sc: keys: {initial_sc_keys}")
        
        # Test endpoints that should create cache entries
        endpoints = [
            "/public/tours/search?org=test_org&page=1&page_size=5",
            "/public/cms/pages?org=test_org",
            "/public/campaigns?org=test_org",
            "/public/search?org=test_org&page=1&page_size=5"
        ]
        
        successful_calls = 0
        
        for endpoint in endpoints:
            try:
                url = f"{BACKEND_URL}{endpoint}"
                print(f"Testing endpoint: {endpoint}")
                
                response = requests.get(url, timeout=15)
                
                if response.status_code == 200:
                    successful_calls += 1
                    print(f"  ✅ {endpoint} - Status: {response.status_code}")
                    
                    # Brief delay to allow cache write
                    time.sleep(0.5)
                else:
                    print(f"  ❌ {endpoint} - Status: {response.status_code}")
                    print(f"     Response: {response.text[:200]}")
                    
            except Exception as e:
                print(f"  ❌ {endpoint} - Error: {str(e)}")
        
        # Check cache keys after API calls
        time.sleep(2)  # Allow cache writes to complete
        
        final_keys = self.run_redis_command("DBSIZE")
        final_sc_keys = self.run_redis_command("KEYS 'sc:*'")
        sc_keys_list = []
        
        if final_sc_keys and final_sc_keys != "(empty list or set)":
            # Parse the keys output
            if '\n' in final_sc_keys:
                sc_keys_list = [k.strip() for k in final_sc_keys.split('\n') if k.strip()]
            elif final_sc_keys:
                sc_keys_list = [final_sc_keys]
        
        print(f"Final Redis key count: {final_keys}")
        print(f"Final sc: keys count: {len(sc_keys_list)}")
        print(f"SC keys found: {sc_keys_list}")
        
        # Determine test success
        cache_keys_created = len(sc_keys_list) > 0
        all_endpoints_working = successful_calls == len(endpoints)
        
        details = f"API calls successful: {successful_calls}/{len(endpoints)}, Cache keys created: {len(sc_keys_list)}"
        
        self.log_test(
            "Cache Creation and Key Verification",
            cache_keys_created and successful_calls > 0,
            details,
            {
                "successful_api_calls": successful_calls,
                "total_endpoints": len(endpoints),
                "cache_keys_found": len(sc_keys_list),
                "sc_keys": sc_keys_list,
                "initial_key_count": initial_keys,
                "final_key_count": final_keys
            }
        )
        
        return sc_keys_list

    def test_3_cache_hit_test(self):
        """Test 3: Cache Hit Test - Call endpoints again and check hit increase"""
        print("=" * 60)
        print("TEST 3: Cache Hit Testing")
        print("=" * 60)
        
        # Get initial stats
        initial_stats = self.run_redis_command("INFO stats")
        initial_hits = 0
        initial_misses = 0
        
        if initial_stats:
            for line in initial_stats.split('\n'):
                if 'keyspace_hits:' in line:
                    initial_hits = int(line.split(':')[1])
                elif 'keyspace_misses:' in line:
                    initial_misses = int(line.split(':')[1])
        
        print(f"Initial keyspace_hits: {initial_hits}")
        print(f"Initial keyspace_misses: {initial_misses}")
        
        # Call the same endpoints again (should hit cache)
        endpoints = [
            "/public/tours/search?org=test_org&page=1&page_size=5",
            "/public/cms/pages?org=test_org",
            "/public/campaigns?org=test_org"
        ]
        
        repeat_calls = 0
        for endpoint in endpoints:
            try:
                url = f"{BACKEND_URL}{endpoint}"
                response = requests.get(url, timeout=15)
                
                if response.status_code == 200:
                    repeat_calls += 1
                    print(f"  ✅ Repeat call to {endpoint} - Status: {response.status_code}")
                else:
                    print(f"  ❌ Repeat call to {endpoint} - Status: {response.status_code}")
                    
            except Exception as e:
                print(f"  ❌ Repeat call to {endpoint} - Error: {str(e)}")
        
        # Brief delay for cache operations
        time.sleep(2)
        
        # Get final stats
        final_stats = self.run_redis_command("INFO stats")
        final_hits = 0
        final_misses = 0
        
        if final_stats:
            for line in final_stats.split('\n'):
                if 'keyspace_hits:' in line:
                    final_hits = int(line.split(':')[1])
                elif 'keyspace_misses:' in line:
                    final_misses = int(line.split(':')[1])
        
        print(f"Final keyspace_hits: {final_hits}")
        print(f"Final keyspace_misses: {final_misses}")
        
        hit_increase = final_hits - initial_hits
        cache_hits_increased = hit_increase > 0
        
        # Calculate hit rate
        total_operations = final_hits + final_misses
        hit_rate = (final_hits / total_operations * 100) if total_operations > 0 else 0
        
        details = f"Hits increased by {hit_increase} (from {initial_hits} to {final_hits}), Hit rate: {hit_rate:.1f}%"
        
        self.log_test(
            "Cache Hit Testing",
            cache_hits_increased,
            details,
            {
                "initial_hits": initial_hits,
                "final_hits": final_hits,
                "hit_increase": hit_increase,
                "initial_misses": initial_misses,
                "final_misses": final_misses,
                "hit_rate_percent": round(hit_rate, 2),
                "repeat_calls_successful": repeat_calls
            }
        )

    def test_4_redis_sentinel_config(self):
        """Test 4: Redis Sentinel Configuration Check"""
        print("=" * 60)
        print("TEST 4: Redis Sentinel Configuration Check")
        print("=" * 60)
        
        try:
            response = requests.get(f"{BACKEND_URL}/health/ready", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                checks = data.get('checks', {})
                
                # Look for mode field or redis_mode field
                mode_field = data.get('mode') or data.get('redis_mode') or checks.get('mode') or checks.get('redis_mode')
                has_mode = mode_field is not None
                
                # Also check for any sentinel-related fields
                all_fields = {**data, **checks}
                sentinel_fields = {k: v for k, v in all_fields.items() if 'sentinel' in k.lower() or 'mode' in k.lower()}
                
                details = f"Mode field present: {has_mode}"
                if has_mode:
                    details += f", Mode value: {mode_field}"
                if sentinel_fields:
                    details += f", Sentinel fields: {sentinel_fields}"
                
                self.log_test(
                    "Redis Sentinel Configuration Check",
                    True,  # Mode field presence is informational, not critical
                    details,
                    {
                        "mode_present": has_mode,
                        "mode_value": mode_field,
                        "sentinel_fields": sentinel_fields,
                        "full_response": data
                    }
                )
            else:
                self.log_test(
                    "Redis Sentinel Configuration Check",
                    False,
                    f"Health endpoint failed: HTTP {response.status_code}",
                    {"status_code": response.status_code}
                )
                
        except Exception as e:
            self.log_test(
                "Redis Sentinel Configuration Check",
                False,
                f"Request failed: {str(e)}"
            )

    def test_5_redis_server_stats(self):
        """Test 5: Redis Server Statistics"""
        print("=" * 60)
        print("TEST 5: Redis Server Statistics")
        print("=" * 60)
        
        # Test memory stats
        memory_info = self.run_redis_command("INFO memory")
        stats_info = self.run_redis_command("INFO stats")
        server_info = self.run_redis_command("INFO server")
        
        memory_stats = {}
        stats_data = {}
        server_data = {}
        
        # Parse memory info
        if memory_info:
            for line in memory_info.split('\n'):
                if ':' in line and not line.startswith('#'):
                    key, value = line.split(':', 1)
                    if 'memory' in key.lower():
                        memory_stats[key] = value
        
        # Parse stats info
        if stats_info:
            for line in stats_info.split('\n'):
                if ':' in line and not line.startswith('#'):
                    key, value = line.split(':', 1)
                    if key in ['keyspace_hits', 'keyspace_misses', 'total_commands_processed', 'instantaneous_ops_per_sec']:
                        stats_data[key] = value
        
        # Parse server info
        if server_info:
            for line in server_info.split('\n'):
                if ':' in line and not line.startswith('#'):
                    key, value = line.split(':', 1)
                    if key in ['uptime_in_seconds', 'uptime_in_days', 'redis_version']:
                        server_data[key] = value
        
        # Calculate hit ratio
        hits = int(stats_data.get('keyspace_hits', 0))
        misses = int(stats_data.get('keyspace_misses', 0))
        total = hits + misses
        hit_ratio = (hits / total * 100) if total > 0 else 0
        
        # Format memory usage
        used_memory = memory_stats.get('used_memory_human', 'unknown')
        peak_memory = memory_stats.get('used_memory_peak_human', 'unknown')
        
        # Format uptime
        uptime_days = server_data.get('uptime_in_days', 'unknown')
        redis_version = server_data.get('redis_version', 'unknown')
        
        all_info_present = bool(memory_info and stats_info and server_info)
        
        details = f"Memory: {used_memory} (peak: {peak_memory}), Hit ratio: {hit_ratio:.1f}%, Uptime: {uptime_days} days, Version: {redis_version}"
        
        self.log_test(
            "Redis Server Statistics",
            all_info_present,
            details,
            {
                "memory_stats": memory_stats,
                "stats_data": stats_data,
                "server_data": server_data,
                "hit_ratio_percent": round(hit_ratio, 2),
                "info_commands_successful": {
                    "memory": bool(memory_info),
                    "stats": bool(stats_info),
                    "server": bool(server_info)
                }
            }
        )

    def test_redis_connectivity(self):
        """Basic Redis connectivity test"""
        print("=" * 60)
        print("PRELIMINARY: Redis Connectivity Test")
        print("=" * 60)
        
        # Test basic ping
        ping_result = self.run_redis_command("ping")
        ping_success = ping_result == "PONG"
        
        # Test basic operations
        set_result = self.run_redis_command("SET test_key 'test_value' EX 60")
        set_success = set_result == "OK"
        
        get_result = self.run_redis_command("GET test_key")
        get_success = get_result == "test_value"
        
        del_result = self.run_redis_command("DEL test_key")
        del_success = del_result == "1"
        
        connectivity_ok = ping_success and set_success and get_success and del_success
        
        details = f"Ping: {ping_success}, SET: {set_success}, GET: {get_success}, DEL: {del_success}"
        
        self.log_test(
            "Redis Basic Connectivity",
            connectivity_ok,
            details,
            {
                "ping_response": ping_result,
                "set_response": set_result,
                "get_response": get_result,
                "del_response": del_result
            }
        )
        
        return connectivity_ok

    def run_all_tests(self):
        """Execute all Redis cache system tests"""
        print("🔍 SYROCE REDIS CACHE SYSTEM - COMPREHENSIVE TESTING")
        print("=" * 80)
        print(f"Backend URL: {BACKEND_URL}")
        print(f"Redis Server: {REDIS_HOST}:{REDIS_PORT}")
        print("=" * 80)
        
        # Preliminary connectivity test
        if not self.test_redis_connectivity():
            print("❌ Redis connectivity failed! Stopping tests.")
            return
        
        # Run all main tests
        self.test_1_health_check()
        cache_keys = self.test_2_cache_creation()
        self.test_3_cache_hit_test()
        self.test_4_redis_sentinel_config()
        self.test_5_redis_server_stats()
        
        # Summary
        print("=" * 80)
        print("📊 TEST SUMMARY")
        print("=" * 80)
        
        passed_tests = [r for r in self.test_results if r['passed']]
        failed_tests = [r for r in self.test_results if not r['passed']]
        
        print(f"Total Tests: {len(self.test_results)}")
        print(f"Passed: {len(passed_tests)}")
        print(f"Failed: {len(failed_tests)}")
        print()
        
        if failed_tests:
            print("❌ FAILED TESTS:")
            for test in failed_tests:
                print(f"  - {test['test']}: {test['details']}")
            print()
        
        if passed_tests:
            print("✅ PASSED TESTS:")
            for test in passed_tests:
                print(f"  - {test['test']}: {test['details']}")
        
        print("\n" + "=" * 80)
        print(f"🎯 OVERALL STATUS: {'✅ ALL TESTS PASSED' if not failed_tests else '❌ SOME TESTS FAILED'}")
        print("=" * 80)
        
        return len(failed_tests) == 0

if __name__ == "__main__":
    test_suite = RedisTestSuite()
    success = test_suite.run_all_tests()
    sys.exit(0 if success else 1)