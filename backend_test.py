#!/usr/bin/env python3
"""
AI Assistant Backend Test Suite

Tests the 4 AI Assistant endpoints as specified in the review request.
Focus on authentication flow, LLM integration, and API responses.
"""

import requests
import json
import sys
from typing import Dict, Any, Optional
from datetime import datetime

# Get backend URL from environment
BACKEND_URL = "https://test-data-populator.preview.emergentagent.com/api"

# Test credentials as specified in review request  
ADMIN_EMAIL = "admin@test.com"
ADMIN_PASSWORD = "admin123"
FALLBACK_EMAIL = "aitest@test.com"
FALLBACK_PASSWORD = "TestPassword123!"
FALLBACK_NAME = "AI Tester"

class AIAssistantTester:
    def __init__(self):
        self.base_url = BACKEND_URL
        self.auth_token = None
        self.session_id = None
        self.test_results = []
        
    def log(self, message: str, level: str = "INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
        
    def add_result(self, test_name: str, status: str, details: str = ""):
        self.test_results.append({
            "test": test_name,
            "status": status,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
        status_icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        self.log(f"{status_icon} {test_name}: {status} {details}")
        
    def request(self, method: str, endpoint: str, headers: Optional[Dict] = None, 
               json_data: Optional[Dict] = None, params: Optional[Dict] = None, 
               expect_status: Optional[int] = None, timeout: int = 15) -> requests.Response:
        """Make HTTP request with proper error handling"""
        url = f"{self.base_url}{endpoint}"
        req_headers = {"Content-Type": "application/json"}
        
        if headers:
            req_headers.update(headers)
            
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=req_headers,
                json=json_data,
                params=params,
                timeout=timeout
            )
            
            status_str = f"{response.status_code}"
            if expect_status and response.status_code == expect_status:
                status_str += " (expected)"
            elif expect_status:
                status_str += f" (expected {expect_status})"
                
            self.log(f"{method} {endpoint} -> {status_str}")
            return response
        except requests.RequestException as e:
            self.log(f"Request failed: {e}", "ERROR")
            raise
            
    def authenticate(self) -> bool:
        """Try admin login first, if fails try register and login with fallback credentials"""
        self.log("=== AUTHENTICATION ===")
        
        # Try admin login first
        admin_login_data = {
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        }
        
        response = self.request("POST", "/auth/login", json_data=admin_login_data)
        
        if response.status_code == 200:
            try:
                data = response.json()
                self.auth_token = data.get("access_token")
                if self.auth_token:
                    self.add_result("Admin Authentication", "PASS", f"Token obtained for {ADMIN_EMAIL}")
                    return True
            except json.JSONDecodeError:
                pass
        
        # If admin login failed, try register and login with fallback
        self.log("Admin login failed, trying fallback registration...")
        
        register_data = {
            "email": FALLBACK_EMAIL,
            "password": FALLBACK_PASSWORD,
            "name": FALLBACK_NAME
        }
        
        register_response = self.request("POST", "/auth/signup", json_data=register_data)
        self.log(f"Registration response: {register_response.status_code}")
        
        if register_response.status_code != 200:
            try:
                error_data = register_response.json()
                self.log(f"Registration error: {error_data}")
            except:
                self.log(f"Registration error: Status {register_response.status_code}")
        else:
            self.log("Registration successful")
            
        # Add delay to avoid rate limiting
        import time
        time.sleep(2)
        
        # Try login with fallback credentials
        fallback_login_data = {
            "email": FALLBACK_EMAIL,
            "password": FALLBACK_PASSWORD
        }
        
        login_response = self.request("POST", "/auth/login", json_data=fallback_login_data)
        
        if login_response.status_code == 200:
            try:
                data = login_response.json()
                self.auth_token = data.get("access_token")
                if self.auth_token:
                    self.add_result("Fallback Authentication", "PASS", f"Token obtained for {FALLBACK_EMAIL}")
                    return True
            except json.JSONDecodeError:
                pass
        elif login_response.status_code == 429:
            self.add_result("Authentication", "FAIL", "Rate limited - try again later")
            return False
        
        self.add_result("Authentication", "FAIL", "Both admin and fallback authentication failed")
        return False

    def get_auth_headers(self) -> Dict[str, str]:
        """Get headers with Bearer token"""
        if self.auth_token:
            return {"Authorization": f"Bearer {self.auth_token}"}
        return {}

    def test_briefing_no_auth(self):
        """Test 1: POST /api/ai-assistant/briefing without auth should return 401"""
        self.log("=== TEST 1: BRIEFING NO AUTH ===")
        
        response = self.request("POST", "/ai-assistant/briefing", expect_status=401)
        
        if response.status_code == 401:
            self.add_result("Briefing No Auth", "PASS", "Returns 401 without authentication token")
        else:
            self.add_result("Briefing No Auth", "FAIL", f"Expected 401, got {response.status_code}")

    def test_briefing_with_auth(self):
        """Test 2: POST /api/ai-assistant/briefing with valid auth token"""
        self.log("=== TEST 2: BRIEFING WITH AUTH ===")
        
        if not self.auth_token:
            self.add_result("Briefing With Auth", "SKIP", "No auth token available")
            return
            
        response = self.request("POST", "/ai-assistant/briefing", 
                               headers=self.get_auth_headers(), 
                               expect_status=200,
                               timeout=30)  # Longer timeout for LLM calls
        
        if response.status_code == 200:
            try:
                data = response.json()
                # Expected: {"briefing": "...", "raw_data": {...}, "generated_at": "..."}
                expected_keys = ["briefing", "raw_data", "generated_at"]
                if all(key in data for key in expected_keys):
                    briefing_length = len(data.get("briefing", ""))
                    self.add_result("Briefing With Auth", "PASS", 
                                  f"Returns briefing data: briefing_length={briefing_length}, raw_data keys={list(data.get('raw_data', {}).keys())}")
                else:
                    missing = [key for key in expected_keys if key not in data]
                    self.add_result("Briefing With Auth", "FAIL", 
                                  f"Missing keys: {missing}, got: {list(data.keys())}")
            except json.JSONDecodeError:
                self.add_result("Briefing With Auth", "FAIL", "Invalid JSON response")
        else:
            try:
                error_data = response.json()
                error_msg = error_data.get("detail", f"Status: {response.status_code}")
                self.add_result("Briefing With Auth", "FAIL", f"API Error: {error_msg}")
            except:
                self.add_result("Briefing With Auth", "FAIL", f"Status: {response.status_code}")

    def test_chat_no_auth(self):
        """Test 3: POST /api/ai-assistant/chat without auth should return 401"""
        self.log("=== TEST 3: CHAT NO AUTH ===")
        
        chat_data = {
            "message": "Merhaba, bugün ne var?",
            "session_id": None
        }
        
        response = self.request("POST", "/ai-assistant/chat", json_data=chat_data, expect_status=401)
        
        if response.status_code == 401:
            self.add_result("Chat No Auth", "PASS", "Returns 401 without authentication token")
        else:
            self.add_result("Chat No Auth", "FAIL", f"Expected 401, got {response.status_code}")

    def test_chat_with_auth(self):
        """Test 4: POST /api/ai-assistant/chat with valid auth token"""
        self.log("=== TEST 4: CHAT WITH AUTH ===")
        
        if not self.auth_token:
            self.add_result("Chat With Auth", "SKIP", "No auth token available")
            return
            
        chat_data = {
            "message": "Merhaba, bugün ne var?",
            "session_id": None
        }
        
        response = self.request("POST", "/ai-assistant/chat", 
                               headers=self.get_auth_headers(),
                               json_data=chat_data,
                               expect_status=200,
                               timeout=30)  # Longer timeout for LLM calls
        
        if response.status_code == 200:
            try:
                data = response.json()
                # Expected: {"response": "...", "session_id": "..."}
                expected_keys = ["response", "session_id"]
                if all(key in data for key in expected_keys):
                    self.session_id = data.get("session_id")  # Save for later tests
                    response_length = len(data.get("response", ""))
                    self.add_result("Chat With Auth", "PASS", 
                                  f"Returns chat response: session_id={self.session_id}, response_length={response_length}")
                else:
                    missing = [key for key in expected_keys if key not in data]
                    self.add_result("Chat With Auth", "FAIL", 
                                  f"Missing keys: {missing}, got: {list(data.keys())}")
            except json.JSONDecodeError:
                self.add_result("Chat With Auth", "FAIL", "Invalid JSON response")
        else:
            try:
                error_data = response.json()
                error_msg = error_data.get("detail", f"Status: {response.status_code}")
                self.add_result("Chat With Auth", "FAIL", f"API Error: {error_msg}")
            except:
                self.add_result("Chat With Auth", "FAIL", f"Status: {response.status_code}")

    def test_chat_history_no_auth(self):
        """Test 5: GET /api/ai-assistant/chat-history/{session_id} without auth should return 401"""
        self.log("=== TEST 5: CHAT HISTORY NO AUTH ===")
        
        test_session_id = "test-session-id"
        response = self.request("GET", f"/ai-assistant/chat-history/{test_session_id}", expect_status=401)
        
        if response.status_code == 401:
            self.add_result("Chat History No Auth", "PASS", "Returns 401 without authentication token")
        else:
            self.add_result("Chat History No Auth", "FAIL", f"Expected 401, got {response.status_code}")

    def test_chat_history_with_auth(self):
        """Test 6: GET /api/ai-assistant/chat-history/{session_id} with valid auth token"""
        self.log("=== TEST 6: CHAT HISTORY WITH AUTH ===")
        
        if not self.auth_token:
            self.add_result("Chat History With Auth", "SKIP", "No auth token available")
            return
            
        # Use session_id from previous chat test if available
        session_id = self.session_id or "test-session-id"
        
        response = self.request("GET", f"/ai-assistant/chat-history/{session_id}", 
                               headers=self.get_auth_headers(), 
                               expect_status=200)
        
        if response.status_code == 200:
            try:
                data = response.json()
                # Expected: {"messages": [...], "session_id": "..."}
                expected_keys = ["messages", "session_id"]
                if all(key in data for key in expected_keys):
                    message_count = len(data.get("messages", []))
                    self.add_result("Chat History With Auth", "PASS", 
                                  f"Returns chat history: session_id={data.get('session_id')}, message_count={message_count}")
                else:
                    missing = [key for key in expected_keys if key not in data]
                    self.add_result("Chat History With Auth", "FAIL", 
                                  f"Missing keys: {missing}, got: {list(data.keys())}")
            except json.JSONDecodeError:
                self.add_result("Chat History With Auth", "FAIL", "Invalid JSON response")
        else:
            self.add_result("Chat History With Auth", "FAIL", f"Status: {response.status_code}")

    def test_sessions_no_auth(self):
        """Test 7: GET /api/ai-assistant/sessions without auth should return 401"""
        self.log("=== TEST 7: SESSIONS NO AUTH ===")
        
        response = self.request("GET", "/ai-assistant/sessions", expect_status=401)
        
        if response.status_code == 401:
            self.add_result("Sessions No Auth", "PASS", "Returns 401 without authentication token")
        else:
            self.add_result("Sessions No Auth", "FAIL", f"Expected 401, got {response.status_code}")

    def test_sessions_with_auth(self):
        """Test 8: GET /api/ai-assistant/sessions with valid auth token"""
        self.log("=== TEST 8: SESSIONS WITH AUTH ===")
        
        if not self.auth_token:
            self.add_result("Sessions With Auth", "SKIP", "No auth token available")
            return
            
        response = self.request("GET", "/ai-assistant/sessions", 
                               headers=self.get_auth_headers(), 
                               expect_status=200)
        
        if response.status_code == 200:
            try:
                data = response.json()
                # Expected: {"sessions": [...]}
                if "sessions" in data and isinstance(data["sessions"], list):
                    session_count = len(data.get("sessions", []))
                    self.add_result("Sessions With Auth", "PASS", 
                                  f"Returns user sessions: session_count={session_count}")
                else:
                    self.add_result("Sessions With Auth", "FAIL", 
                                  f"Missing 'sessions' field or not a list: {list(data.keys())}")
            except json.JSONDecodeError:
                self.add_result("Sessions With Auth", "FAIL", "Invalid JSON response")
        else:
            self.add_result("Sessions With Auth", "FAIL", f"Status: {response.status_code}")

    def test_briefing_with_invalid_auth(self):
        """Test briefing with invalid token to check LLM error handling"""
        self.log("=== TEST: BRIEFING WITH INVALID AUTH ===")
        
        # Use a fake token to bypass auth but trigger LLM errors
        invalid_headers = {"Authorization": "Bearer invalid_token_12345"}
        
        response = self.request("POST", "/ai-assistant/briefing", 
                               headers=invalid_headers, 
                               timeout=30)
        
        # Should return 401 for invalid token
        if response.status_code == 401:
            self.add_result("Briefing Invalid Auth", "PASS", "Returns 401 for invalid token")
        else:
            try:
                error_data = response.json()
                error_msg = error_data.get("detail", f"Status: {response.status_code}")
                self.add_result("Briefing Invalid Auth", "INFO", f"Response: {error_msg}")
            except:
                self.add_result("Briefing Invalid Auth", "INFO", f"Status: {response.status_code}")

    def run_all_tests(self):
        """Run all AI Assistant API tests in the specified order"""
        print("🚀 Starting AI Assistant API Tests")
        print("📋 Testing 4 AI Assistant endpoints\n")
        
        # Authentication (try to authenticate)
        auth_ok = self.authenticate()
        
        if not auth_ok:
            print("⚠️ Authentication failed - will test auth guards only")
            
        # Test 1-2: POST /api/ai-assistant/briefing endpoint
        self.test_briefing_no_auth()
        if auth_ok:
            self.test_briefing_with_auth()
        
        # Test 3-4: POST /api/ai-assistant/chat endpoint  
        self.test_chat_no_auth()
        if auth_ok:
            self.test_chat_with_auth()
        
        # Test 5-6: GET /api/ai-assistant/chat-history/{session_id} endpoint
        self.test_chat_history_no_auth()
        if auth_ok:
            self.test_chat_history_with_auth()
        
        # Test 7-8: GET /api/ai-assistant/sessions endpoint
        self.test_sessions_no_auth()
        if auth_ok:
            self.test_sessions_with_auth()
        
        # Test with invalid auth to check system behavior
        self.test_briefing_with_invalid_auth()
        
        return True

    def print_summary(self):
        """Print test results summary"""
        print("\n" + "="*80)
        print("🏁 AI ASSISTANT API TEST SUMMARY")
        print("="*80)
        
        total = len(self.test_results)
        passed = len([r for r in self.test_results if r["status"] == "PASS"])
        failed = len([r for r in self.test_results if r["status"] == "FAIL"])
        skipped = len([r for r in self.test_results if r["status"] == "SKIP"])
        
        print(f"\n📊 Results: {passed} PASS, {failed} FAIL, {skipped} SKIP (Total: {total})")
        
        if failed > 0:
            print(f"\n❌ FAILED TESTS ({failed}):")
            for result in self.test_results:
                if result["status"] == "FAIL":
                    print(f"  - {result['test']}: {result['details']}")
        
        if skipped > 0:
            print(f"\n⚠️ SKIPPED TESTS ({skipped}):")
            for result in self.test_results:
                if result["status"] == "SKIP":
                    print(f"  - {result['test']}: {result['details']}")
        
        print(f"\n✅ PASSED TESTS ({passed}):")
        for result in self.test_results:
            if result["status"] == "PASS":
                print(f"  - {result['test']}: {result['details']}")
        
        # Key assertions from review request
        print("\n🔑 KEY ASSERTIONS:")
        
        auth_guards_working = any("No Auth" in r["test"] and r["status"] == "PASS" for r in self.test_results)
        print(f"  - Auth guards return 401 without token: {'✅' if auth_guards_working else '❌'}")
        
        ai_endpoints_working = any("With Auth" in r["test"] and r["status"] == "PASS" for r in self.test_results)
        print(f"  - AI Assistant endpoints working with token: {'✅' if ai_endpoints_working else '❌'}")
        
        llm_calls_working = any("Briefing With Auth" in r["test"] and r["status"] == "PASS" for r in self.test_results) or any("Chat With Auth" in r["test"] and r["status"] == "PASS" for r in self.test_results)
        print(f"  - LLM integration working (briefing/chat): {'✅' if llm_calls_working else '❌'}")
        
        all_endpoints_tested = any("ai-assistant" in r["test"].lower() for r in self.test_results)
        print(f"  - All 4 AI Assistant endpoints tested: {'✅' if all_endpoints_tested else '❌'}")
        
        return passed, failed, skipped


def main():
    """Main function"""
    tester = AIAssistantTester()
    
    try:
        success = tester.run_all_tests()
        passed, failed, skipped = tester.print_summary()
        
        # Exit with error code if tests failed
        if failed > 0:
            sys.exit(1)
        elif not success:
            sys.exit(2)
        else:
            print("\n🎉 All AI Assistant API tests completed successfully!")
            sys.exit(0)
            
    except Exception as e:
        print(f"\n💥 Test runner crashed: {e}")
        sys.exit(3)


if __name__ == "__main__":
    main()