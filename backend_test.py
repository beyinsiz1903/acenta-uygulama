#!/usr/bin/env python3
"""
Backend test for travel agency SaaS platform runtime split refactor
Turkish context: Operational bootstrap split / runtime separation refactor testing

Test Requirements:
1. API compat ve ingress smoke (server:app compat import chain intact, GET /api/health 200)
2. Auth / session smoke (POST /api/auth/login admin hesabıyla, GET /api/auth/me 200)
3. Mobile BFF smoke (GET /api/v1/mobile/auth/me same token 200)  
4. New runtime wiring validation (runtime_ops.md content check, entrypoints correct)
5. Dedicated runtime health smoke (worker/scheduler heartbeat validation)
6. Regression guard (test compatibility with existing test files)
"""

import asyncio
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict

import requests

# Base URL from frontend/.env
BACKEND_URL = "https://travel-saas-refactor.preview.emergentagent.com/api"
ADMIN_CREDENTIALS = {"email": "admin@acenta.test", "password": "admin123"}

class RuntimeTestSuite:
    def __init__(self):
        self.backend_url = BACKEND_URL
        self.admin_token = None
        self.test_results = {}
        self.backend_dir = Path("/app/backend")
        
    def log_test(self, test_name: str, success: bool, message: str):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message}")
        self.test_results[test_name] = {"success": success, "message": message}
        
    def test_1_api_compat_and_ingress_smoke(self):
        """Test 1: API compat and ingress smoke test"""
        print("\n=== Test 1: API Compat and Ingress Smoke ===")
        
        # Check server:app compat import chain
        try:
            from backend.server import app
            self.log_test("server:app import chain", True, "Import successful - compat chain intact")
        except Exception as e:
            self.log_test("server:app import chain", False, f"Import failed: {e}")
            return False
            
        # Test GET /api/health 
        try:
            response = requests.get(f"{self.backend_url}/health", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "ok":
                    self.log_test("GET /api/health", True, "Health endpoint returns 200 with status=ok")
                else:
                    self.log_test("GET /api/health", False, f"Health endpoint returns wrong status: {data}")
                    return False
            else:
                self.log_test("GET /api/health", False, f"Health endpoint returns {response.status_code}")
                return False
        except Exception as e:
            self.log_test("GET /api/health", False, f"Health endpoint error: {e}")
            return False
            
        return True
        
    def test_2_auth_session_smoke(self):
        """Test 2: Auth/session smoke test"""
        print("\n=== Test 2: Auth/Session Smoke ===")
        
        # POST /api/auth/login with admin credentials
        try:
            response = requests.post(
                f"{self.backend_url}/auth/login",
                json=ADMIN_CREDENTIALS,
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                if "access_token" in data:
                    self.admin_token = data["access_token"]
                    self.log_test("POST /api/auth/login", True, f"Login successful, token length: {len(self.admin_token)}")
                else:
                    self.log_test("POST /api/auth/login", False, "Login response missing access_token")
                    return False
            else:
                self.log_test("POST /api/auth/login", False, f"Login failed with status {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("POST /api/auth/login", False, f"Login request error: {e}")
            return False
            
        # GET /api/auth/me with token
        if self.admin_token:
            try:
                headers = {"Authorization": f"Bearer {self.admin_token}"}
                response = requests.get(f"{self.backend_url}/auth/me", headers=headers, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("email") == "admin@acenta.test":
                        self.log_test("GET /api/auth/me", True, f"Auth/me successful, email: {data['email']}")
                    else:
                        self.log_test("GET /api/auth/me", False, f"Auth/me wrong email: {data.get('email')}")
                        return False
                else:
                    self.log_test("GET /api/auth/me", False, f"Auth/me failed with status {response.status_code}")
                    return False
            except Exception as e:
                self.log_test("GET /api/auth/me", False, f"Auth/me request error: {e}")
                return False
        else:
            self.log_test("GET /api/auth/me", False, "No admin token available")
            return False
            
        return True
        
    def test_3_mobile_bff_smoke(self):
        """Test 3: Mobile BFF smoke test"""
        print("\n=== Test 3: Mobile BFF Smoke ===")
        
        if not self.admin_token:
            self.log_test("Mobile BFF auth check", False, "No admin token available from previous test")
            return False
            
        # GET /api/v1/mobile/auth/me with same token
        try:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
            response = requests.get(f"{self.backend_url}/v1/mobile/auth/me", headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                # Check mobile BFF response structure
                if data.get("email") == "admin@acenta.test" and "_id" not in data and "password_hash" not in data:
                    self.log_test("GET /api/v1/mobile/auth/me", True, "Mobile BFF auth/me successful with sanitized response")
                else:
                    self.log_test("GET /api/v1/mobile/auth/me", False, f"Mobile BFF auth/me response structure issue: {list(data.keys())}")
                    return False
            else:
                self.log_test("GET /api/v1/mobile/auth/me", False, f"Mobile BFF auth/me failed with status {response.status_code}")
                return False
        except Exception as e:
            self.log_test("GET /api/v1/mobile/auth/me", False, f"Mobile BFF auth/me request error: {e}")
            return False
            
        return True
        
    def test_4_runtime_wiring_validation(self):
        """Test 4: New runtime wiring validation"""
        print("\n=== Test 4: Runtime Wiring Validation ===")
        
        # Check runtime_ops.md exists and has expected content
        runtime_ops_path = self.backend_dir / "app" / "bootstrap" / "runtime_ops.md"
        if runtime_ops_path.exists():
            content = runtime_ops_path.read_text()
            if "API entrypoint:" in content and "Worker entrypoint:" in content and "Scheduler entrypoint:" in content:
                self.log_test("runtime_ops.md content", True, "Runtime operations documentation exists with correct entrypoints")
            else:
                self.log_test("runtime_ops.md content", False, "Runtime operations documentation missing required entrypoint info")
                return False
        else:
            self.log_test("runtime_ops.md content", False, "Runtime operations documentation file missing")
            return False
            
        # Check runtime scripts exist
        required_scripts = [
            "scripts/run_api_runtime.sh",
            "scripts/run_worker_runtime.sh", 
            "scripts/run_scheduler_runtime.sh",
            "scripts/check_runtime_health.py"
        ]
        
        all_scripts_exist = True
        for script_path in required_scripts:
            full_path = self.backend_dir / script_path
            if full_path.exists():
                self.log_test(f"Script {script_path}", True, "Runtime script exists")
            else:
                self.log_test(f"Script {script_path}", False, "Runtime script missing")
                all_scripts_exist = False
                
        # Check runtime bootstrap files exist
        required_bootstrap_files = [
            "app/bootstrap/runtime_health.py",
            "app/bootstrap/worker_app.py",
            "app/bootstrap/scheduler_app.py"
        ]
        
        for bootstrap_path in required_bootstrap_files:
            full_path = self.backend_dir / bootstrap_path
            if full_path.exists():
                self.log_test(f"Bootstrap {bootstrap_path}", True, "Bootstrap file exists")
            else:
                self.log_test(f"Bootstrap {bootstrap_path}", False, "Bootstrap file missing")
                all_scripts_exist = False
                
        return all_scripts_exist
        
    def test_5_dedicated_runtime_health_smoke(self):
        """Test 5: Dedicated runtime health smoke test"""
        print("\n=== Test 5: Dedicated Runtime Health Smoke ===")
        
        # Set temporary health directory
        with tempfile.TemporaryDirectory() as temp_dir:
            os.environ["RUNTIME_HEALTH_DIR"] = temp_dir
            
            # Test worker runtime briefly
            worker_success = self._test_runtime_health("worker", temp_dir)
            
            # Test scheduler runtime briefly  
            scheduler_success = self._test_runtime_health("scheduler", temp_dir)
            
            return worker_success and scheduler_success
            
    def _test_runtime_health(self, runtime_name: str, health_dir: str) -> bool:
        """Test individual runtime health"""
        print(f"\n--- Testing {runtime_name} runtime ---")
        
        # Start runtime process in background
        script_path = self.backend_dir / f"scripts/run_{runtime_name}_runtime.sh"
        if not script_path.exists():
            self.log_test(f"{runtime_name} runtime script", False, f"Script {script_path} not found")
            return False
            
        try:
            # Make script executable
            os.chmod(script_path, 0o755)
            
            # Start runtime process
            process = subprocess.Popen(
                [str(script_path)],
                cwd=self.backend_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env={**os.environ, "RUNTIME_HEALTH_DIR": health_dir}
            )
            
            # Wait for heartbeat to be created (max 30 seconds)
            heartbeat_path = Path(health_dir) / f"{runtime_name}.json"
            max_wait = 30
            wait_time = 0
            
            while wait_time < max_wait:
                if heartbeat_path.exists():
                    break
                time.sleep(1)
                wait_time += 1
                
            if heartbeat_path.exists():
                # Read heartbeat
                try:
                    heartbeat_data = json.loads(heartbeat_path.read_text())
                    if heartbeat_data.get("status") == "ready":
                        self.log_test(f"{runtime_name} heartbeat creation", True, f"Heartbeat created with status=ready")
                        
                        # Test health check script
                        check_script = self.backend_dir / "scripts/check_runtime_health.py"
                        if check_script.exists():
                            check_result = subprocess.run([
                                sys.executable, str(check_script), runtime_name, "--ttl-seconds", "60"
                            ], cwd=self.backend_dir, capture_output=True, text=True, 
                               env={**os.environ, "RUNTIME_HEALTH_DIR": health_dir})
                            
                            if check_result.returncode == 0:
                                self.log_test(f"{runtime_name} health check script", True, "Health check script validates heartbeat correctly")
                                success = True
                            else:
                                self.log_test(f"{runtime_name} health check script", False, f"Health check failed: {check_result.stderr}")
                                success = False
                        else:
                            self.log_test(f"{runtime_name} health check script", False, "Health check script not found")
                            success = False
                    else:
                        self.log_test(f"{runtime_name} heartbeat creation", False, f"Heartbeat status not ready: {heartbeat_data.get('status')}")
                        success = False
                except Exception as e:
                    self.log_test(f"{runtime_name} heartbeat creation", False, f"Failed to read heartbeat: {e}")
                    success = False
            else:
                self.log_test(f"{runtime_name} heartbeat creation", False, f"Heartbeat file not created within {max_wait} seconds")
                success = False
                
            # Cleanup: terminate process
            try:
                process.terminate()
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
                
            return success
            
        except Exception as e:
            self.log_test(f"{runtime_name} runtime execution", False, f"Failed to start runtime: {e}")
            return False
            
    def test_6_regression_guard(self):
        """Test 6: Regression guard - compatibility with existing tests"""
        print("\n=== Test 6: Regression Guard ===")
        
        # Check that existing test files are compatible
        test_files = [
            "tests/test_runtime_wiring.py",
            "tests/test_mobile_bff_contracts.py"
        ]
        
        all_compatible = True
        for test_file in test_files:
            test_path = self.backend_dir / test_file
            if test_path.exists():
                # Try to import the test file to check for syntax/import errors
                try:
                    # Add backend dir to path for imports
                    import sys
                    sys.path.insert(0, str(self.backend_dir))
                    
                    if test_file == "tests/test_runtime_wiring.py":
                        from tests.test_runtime_wiring import test_runtime_heartbeat_roundtrip
                        self.log_test(f"Regression test {test_file}", True, "Test file imports and functions accessible")
                    elif test_file == "tests/test_mobile_bff_contracts.py":
                        from tests.test_mobile_bff_contracts import test_mobile_bff_requires_auth
                        self.log_test(f"Regression test {test_file}", True, "Test file imports and functions accessible")
                        
                except Exception as e:
                    self.log_test(f"Regression test {test_file}", False, f"Import/compatibility error: {e}")
                    all_compatible = False
            else:
                self.log_test(f"Regression test {test_file}", False, "Test file not found")
                all_compatible = False
                
        return all_compatible
        
    def run_all_tests(self):
        """Run all tests in sequence"""
        print("🚀 Starting Runtime Operations Split Backend Testing")
        print(f"Backend URL: {self.backend_url}")
        
        tests = [
            self.test_1_api_compat_and_ingress_smoke,
            self.test_2_auth_session_smoke, 
            self.test_3_mobile_bff_smoke,
            self.test_4_runtime_wiring_validation,
            self.test_5_dedicated_runtime_health_smoke,
            self.test_6_regression_guard
        ]
        
        overall_success = True
        for test_func in tests:
            try:
                success = test_func()
                if not success:
                    overall_success = False
            except Exception as e:
                print(f"❌ FAIL {test_func.__name__}: Exception occurred: {e}")
                self.test_results[test_func.__name__] = {"success": False, "message": f"Exception: {e}"}
                overall_success = False
                
        # Summary
        print("\n" + "="*60)
        print("🧪 RUNTIME OPERATIONS SPLIT TEST SUMMARY")
        print("="*60)
        
        passed = sum(1 for result in self.test_results.values() if result["success"])
        total = len(self.test_results)
        
        print(f"Tests passed: {passed}/{total}")
        
        if overall_success:
            print("✅ ALL TESTS PASSED - Runtime operations split successful")
        else:
            print("❌ SOME TESTS FAILED - Runtime operations split needs attention")
            
        # Detailed results
        for test_name, result in self.test_results.items():
            status = "✅" if result["success"] else "❌"
            print(f"{status} {test_name}: {result['message']}")
            
        return overall_success

if __name__ == "__main__":
    suite = RuntimeTestSuite()
    success = suite.run_all_tests()
    sys.exit(0 if success else 1)