#!/usr/bin/env python3
"""
FINAL VERIFICATION TEST - Hotel PMS Critical Fixes and Performance
Testing specific fixes and performance metrics as requested in the review
"""

import requests
import json
import time
import sys
from datetime import datetime, timedelta
import statistics

# Configuration
BACKEND_URL = "https://page-load-issue.preview.emergentagent.com/api"
TEST_USER = {
    "email": "admin@hotel.com",
    "password": "admin123"
}

class FinalVerificationTester:
    def __init__(self):
        self.token = None
        self.headers = {}
        self.results = {
            "fixes_verified": {},
            "performance_results": {},
            "system_health": {},
            "total_success_rate": 0,
            "average_response_time": 0,
            "issues_found": []
        }
        
    def authenticate(self):
        """Authenticate and get token"""
        try:
            response = requests.post(f"{BACKEND_URL}/auth/login", json=TEST_USER, timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.token = data.get('access_token')
                self.headers = {"Authorization": f"Bearer {self.token}"}
                print("✅ Authentication successful")
                return True
            else:
                print(f"❌ Authentication failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            return False

    def test_endpoint(self, method, endpoint, expected_status=200, data=None, timeout=5):
        """Test a single endpoint and measure response time"""
        start_time = time.time()
        try:
            if method.upper() == "GET":
                response = requests.get(f"{BACKEND_URL}{endpoint}", headers=self.headers, timeout=timeout)
            elif method.upper() == "POST":
                response = requests.post(f"{BACKEND_URL}{endpoint}", headers=self.headers, json=data, timeout=timeout)
            else:
                raise ValueError(f"Unsupported method: {method}")
                
            response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            return {
                "status_code": response.status_code,
                "response_time": response_time,
                "success": response.status_code == expected_status,
                "data": response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text,
                "error": None
            }
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return {
                "status_code": 0,
                "response_time": response_time,
                "success": False,
                "data": None,
                "error": str(e)
            }

    def verify_fixes(self):
        """Verify specific fixes mentioned in the request"""
        print("\n🔍 VERIFYING FIXES...")
        
        # 1. GET /api/pos/orders - ObjectId serialization fixed
        print("\n1. Testing POS Orders ObjectId serialization fix...")
        result = self.test_endpoint("GET", "/pos/orders")
        if result["success"]:
            # Check if response contains _id fields (should not)
            data = result["data"]
            has_id_fields = self._check_for_id_fields(data)
            if not has_id_fields:
                print(f"✅ POS Orders: No _id fields found - ObjectId serialization fixed ({result['response_time']:.1f}ms)")
                self.results["fixes_verified"]["pos_orders"] = {"status": "FIXED", "response_time": result['response_time']}
            else:
                print(f"❌ POS Orders: Still contains _id fields - ObjectId serialization not fixed")
                self.results["fixes_verified"]["pos_orders"] = {"status": "NOT_FIXED", "response_time": result['response_time']}
                self.results["issues_found"].append("POS Orders still contains _id fields")
        else:
            print(f"❌ POS Orders: HTTP {result['status_code']} - {result.get('error', 'Unknown error')}")
            self.results["fixes_verified"]["pos_orders"] = {"status": "ERROR", "error": result.get('error')}
            self.results["issues_found"].append(f"POS Orders endpoint error: {result['status_code']}")

        # 2. GET /api/approvals/pending - urgent_count field present
        print("\n2. Testing Approvals Pending urgent_count field...")
        result = self.test_endpoint("GET", "/approvals/pending")
        if result["success"]:
            data = result["data"]
            if isinstance(data, dict) and "urgent_count" in data:
                print(f"✅ Approvals Pending: urgent_count field present ({result['response_time']:.1f}ms)")
                self.results["fixes_verified"]["approvals_pending"] = {"status": "FIXED", "response_time": result['response_time']}
            else:
                print(f"❌ Approvals Pending: urgent_count field missing")
                print(f"   Response fields: {list(data.keys()) if isinstance(data, dict) else 'non-dict response'}")
                self.results["fixes_verified"]["approvals_pending"] = {"status": "NOT_FIXED", "response_time": result['response_time']}
                self.results["issues_found"].append("Approvals Pending missing urgent_count field")
        else:
            print(f"❌ Approvals Pending: HTTP {result['status_code']} - {result.get('error', 'Unknown error')}")
            self.results["fixes_verified"]["approvals_pending"] = {"status": "ERROR", "error": result.get('error')}
            self.results["issues_found"].append(f"Approvals Pending endpoint error: {result['status_code']}")

        # 3. GET /api/approvals/my-requests - returns 'requests' field
        print("\n3. Testing Approvals My Requests 'requests' field...")
        result = self.test_endpoint("GET", "/approvals/my-requests")
        if result["success"]:
            data = result["data"]
            if isinstance(data, dict) and "requests" in data:
                print(f"✅ Approvals My Requests: 'requests' field present ({result['response_time']:.1f}ms)")
                self.results["fixes_verified"]["approvals_my_requests"] = {"status": "FIXED", "response_time": result['response_time']}
            else:
                print(f"❌ Approvals My Requests: 'requests' field missing")
                print(f"   Response fields: {list(data.keys()) if isinstance(data, dict) else 'non-dict response'}")
                self.results["fixes_verified"]["approvals_my_requests"] = {"status": "NOT_FIXED", "response_time": result['response_time']}
                self.results["issues_found"].append("Approvals My Requests missing 'requests' field")
        else:
            print(f"❌ Approvals My Requests: HTTP {result['status_code']} - {result.get('error', 'Unknown error')}")
            self.results["fixes_verified"]["approvals_my_requests"] = {"status": "ERROR", "error": result.get('error')}
            self.results["issues_found"].append(f"Approvals My Requests endpoint error: {result['status_code']}")

        # 4. GET /api/guests/{guest_id}/profile-complete - No 500 errors
        print("\n4. Testing Guest Profile Complete - No 500 errors...")
        # First create a test guest
        guest_data = {
            "name": "Test Guest Final Verification",
            "email": "testguest.final@hotel.com",
            "phone": "+1234567890",
            "id_number": "TEST123456789"
        }
        create_result = self.test_endpoint("POST", "/guests", data=guest_data)
        if create_result["success"]:
            guest_id = create_result["data"].get("id")
            if guest_id:
                result = self.test_endpoint("GET", f"/guests/{guest_id}/profile-complete")
                if result["success"] and result["status_code"] != 500:
                    print(f"✅ Guest Profile Complete: No 500 errors ({result['response_time']:.1f}ms)")
                    self.results["fixes_verified"]["guest_profile_complete"] = {"status": "FIXED", "response_time": result['response_time']}
                else:
                    print(f"❌ Guest Profile Complete: HTTP {result['status_code']} - Still has 500 errors")
                    self.results["fixes_verified"]["guest_profile_complete"] = {"status": "NOT_FIXED", "response_time": result['response_time']}
                    self.results["issues_found"].append(f"Guest Profile Complete returns {result['status_code']} error")
            else:
                print("❌ Could not create test guest for profile testing")
                self.results["fixes_verified"]["guest_profile_complete"] = {"status": "ERROR", "error": "Could not create test guest"}
        else:
            print("❌ Could not create test guest for profile testing")
            self.results["fixes_verified"]["guest_profile_complete"] = {"status": "ERROR", "error": "Could not create test guest"}

    def performance_check(self):
        """Check performance of critical endpoints"""
        print("\n⚡ PERFORMANCE CHECK...")
        
        performance_endpoints = [
            ("/pms/rooms", "PMS Rooms", 100),  # <100ms target
            ("/pms/bookings", "PMS Bookings", 100),  # <100ms target
            ("/pms/dashboard", "PMS Dashboard", 300),  # <300ms target
            ("/executive/kpi-snapshot", "Executive KPI Snapshot", 300)  # <300ms target
        ]
        
        for endpoint, name, target_ms in performance_endpoints:
            print(f"\nTesting {name} performance...")
            
            # Test multiple times for accurate measurement
            response_times = []
            success_count = 0
            
            for i in range(3):  # Test 3 times
                result = self.test_endpoint("GET", endpoint, timeout=10)
                response_times.append(result["response_time"])
                if result["success"]:
                    success_count += 1
                time.sleep(0.1)  # Small delay between tests
            
            avg_time = statistics.mean(response_times)
            max_time = max(response_times)
            min_time = min(response_times)
            success_rate = (success_count / 3) * 100
            
            performance_status = "EXCELLENT" if avg_time < target_ms else "NEEDS_IMPROVEMENT"
            
            print(f"📊 {name}: Avg: {avg_time:.1f}ms, Min: {min_time:.1f}ms, Max: {max_time:.1f}ms, Success: {success_rate:.0f}%")
            
            if avg_time < target_ms:
                print(f"✅ {name}: Performance target met (<{target_ms}ms)")
            else:
                print(f"⚠️ {name}: Performance target missed (>{target_ms}ms)")
                self.results["issues_found"].append(f"{name} performance above {target_ms}ms target")
            
            self.results["performance_results"][endpoint] = {
                "name": name,
                "avg_response_time": avg_time,
                "min_response_time": min_time,
                "max_response_time": max_time,
                "success_rate": success_rate,
                "target_ms": target_ms,
                "status": performance_status
            }

    def system_health_check(self):
        """Check system health endpoints"""
        print("\n🏥 SYSTEM HEALTH CHECK...")
        
        # 1. GET /api/monitoring/health - Overall system status
        print("\n1. Testing System Health...")
        result = self.test_endpoint("GET", "/monitoring/health", timeout=15)
        if result["success"]:
            data = result["data"]
            status = data.get("status", "unknown")
            print(f"✅ System Health: Status '{status}' ({result['response_time']:.1f}ms)")
            self.results["system_health"]["health"] = {
                "status": status,
                "response_time": result['response_time'],
                "success": True
            }
        else:
            print(f"❌ System Health: HTTP {result['status_code']} - {result.get('error', 'Unknown error')}")
            self.results["system_health"]["health"] = {
                "status": "ERROR",
                "error": result.get('error'),
                "success": False
            }
            self.results["issues_found"].append(f"System Health endpoint error: {result['status_code']}")

        # 2. GET /api/monitoring/database - Connection pool stats
        print("\n2. Testing Database Health...")
        result = self.test_endpoint("GET", "/monitoring/database", timeout=10)
        if result["success"]:
            data = result["data"]
            connections = data.get("connections", {})
            current = connections.get("current", 0)
            available = connections.get("available", 0)
            print(f"✅ Database Health: {current} current, {available} available connections ({result['response_time']:.1f}ms)")
            self.results["system_health"]["database"] = {
                "current_connections": current,
                "available_connections": available,
                "response_time": result['response_time'],
                "success": True
            }
        else:
            print(f"❌ Database Health: HTTP {result['status_code']} - {result.get('error', 'Unknown error')}")
            self.results["system_health"]["database"] = {
                "status": "ERROR",
                "error": result.get('error'),
                "success": False
            }
            self.results["issues_found"].append(f"Database Health endpoint error: {result['status_code']}")

    def calculate_overall_metrics(self):
        """Calculate overall success rate and average response time"""
        total_tests = 0
        successful_tests = 0
        all_response_times = []
        
        # Count fixes
        for fix_name, fix_result in self.results["fixes_verified"].items():
            total_tests += 1
            if fix_result.get("status") == "FIXED":
                successful_tests += 1
            if "response_time" in fix_result:
                all_response_times.append(fix_result["response_time"])
        
        # Count performance tests
        for perf_name, perf_result in self.results["performance_results"].items():
            total_tests += 1
            if perf_result.get("success_rate", 0) > 0:
                successful_tests += 1
            all_response_times.append(perf_result["avg_response_time"])
        
        # Count health tests
        for health_name, health_result in self.results["system_health"].items():
            total_tests += 1
            if health_result.get("success"):
                successful_tests += 1
            if "response_time" in health_result:
                all_response_times.append(health_result["response_time"])
        
        self.results["total_success_rate"] = (successful_tests / total_tests * 100) if total_tests > 0 else 0
        self.results["average_response_time"] = statistics.mean(all_response_times) if all_response_times else 0

    def _check_for_id_fields(self, data):
        """Recursively check for _id fields in response data"""
        if isinstance(data, dict):
            if "_id" in data:
                return True
            for value in data.values():
                if self._check_for_id_fields(value):
                    return True
        elif isinstance(data, list):
            for item in data:
                if self._check_for_id_fields(item):
                    return True
        return False

    def generate_report(self):
        """Generate final verification report"""
        print("\n" + "="*80)
        print("🎯 FINAL VERIFICATION REPORT")
        print("="*80)
        
        print(f"\n📊 OVERALL METRICS:")
        print(f"   • Total Success Rate: {self.results['total_success_rate']:.1f}%")
        print(f"   • Average Response Time: {self.results['average_response_time']:.1f}ms")
        
        print(f"\n🔧 FIXES VERIFICATION:")
        for fix_name, fix_result in self.results["fixes_verified"].items():
            status_icon = "✅" if fix_result.get("status") == "FIXED" else "❌"
            print(f"   {status_icon} {fix_name}: {fix_result.get('status', 'UNKNOWN')}")
        
        print(f"\n⚡ PERFORMANCE RESULTS:")
        for perf_name, perf_result in self.results["performance_results"].items():
            target = perf_result["target_ms"]
            avg_time = perf_result["avg_response_time"]
            status_icon = "✅" if avg_time < target else "⚠️"
            print(f"   {status_icon} {perf_result['name']}: {avg_time:.1f}ms (target: <{target}ms)")
        
        print(f"\n🏥 SYSTEM HEALTH:")
        for health_name, health_result in self.results["system_health"].items():
            status_icon = "✅" if health_result.get("success") else "❌"
            print(f"   {status_icon} {health_name}: {health_result.get('status', 'ERROR')}")
        
        if self.results["issues_found"]:
            print(f"\n⚠️ ISSUES FOUND:")
            for issue in self.results["issues_found"]:
                print(f"   • {issue}")
        else:
            print(f"\n🎉 NO ISSUES FOUND - ALL SYSTEMS OPERATIONAL!")
        
        print("\n" + "="*80)
        
        # Success criteria check
        success_rate = self.results['total_success_rate']
        avg_response_time = self.results['average_response_time']
        
        print(f"\n🎯 SUCCESS CRITERIA CHECK:")
        print(f"   • All endpoints return 200/403/404 (no 500 errors): {'✅' if not any('500' in str(issue) for issue in self.results['issues_found']) else '❌'}")
        print(f"   • Critical endpoints <100ms: {'✅' if all(r['avg_response_time'] < 100 for r in self.results['performance_results'].values() if r['target_ms'] == 100) else '❌'}")
        print(f"   • Dashboard endpoints <300ms: {'✅' if all(r['avg_response_time'] < 300 for r in self.results['performance_results'].values() if r['target_ms'] == 300) else '❌'}")
        print(f"   • 100% success rate: {'✅' if success_rate == 100 else '❌'}")
        
        return self.results

    def run_verification(self):
        """Run complete final verification"""
        print("🚀 Starting Final Verification Test...")
        print(f"Backend URL: {BACKEND_URL}")
        
        if not self.authenticate():
            print("❌ Cannot proceed without authentication")
            return False
        
        # Run all verification steps
        self.verify_fixes()
        self.performance_check()
        self.system_health_check()
        self.calculate_overall_metrics()
        
        # Generate and return report
        return self.generate_report()

def main():
    tester = FinalVerificationTester()
    results = tester.run_verification()
    
    # Save results to file
    with open('/app/final_verification_results.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n💾 Results saved to: /app/final_verification_results.json")
    
    # Exit with appropriate code
    success_rate = results.get('total_success_rate', 0)
    if success_rate >= 90:
        print("🎉 VERIFICATION PASSED!")
        sys.exit(0)
    else:
        print("❌ VERIFICATION FAILED!")
        sys.exit(1)

if __name__ == "__main__":
    main()