#!/usr/bin/env python3
"""
Messaging Throttling Test - RETRY
Testing messaging system rate limiting functionality

Test Scenarios:
1. Single Message Send (email, SMS, WhatsApp)
2. Rate Limit Thresholds (Email: 100/hr, SMS: 50/hr, WhatsApp: 80/hr)
3. Rapid Fire Test (10 emails rapidly)
4. Input Validation (invalid email, phone, empty message)
5. SMS Character Warnings (>160 characters)
6. Rate Limit Info in responses

Base URL: https://error-kontrol.preview.emergentagent.com/api
Login: test@hotel.com / test123
"""

import requests
import json
import time
from datetime import datetime
import sys

# Configuration
BASE_URL = "https://error-kontrol.preview.emergentagent.com/api"
LOGIN_EMAIL = "test@hotel.com"
LOGIN_PASSWORD = "test123"

class MessagingThrottlingTester:
    def __init__(self):
        self.session = requests.Session()
        self.token = None
        self.test_results = []

    def log_test(self, test_name, status, details=""):
        """Log test result"""
        result = {
            'test': test_name,
            'status': status,
            'details': details,
            'timestamp': datetime.now().isoformat()
        }
        self.test_results.append(result)
        status_symbol = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{status_symbol} {test_name}: {details}")
        
    def login(self):
        """Login and get authentication token"""
        try:
            response = self.session.post(f"{BASE_URL}/auth/login", json={
                "email": LOGIN_EMAIL,
                "password": LOGIN_PASSWORD
            })
            
            if response.status_code == 200:
                data = response.json()
                self.token = data['access_token']
                self.session.headers.update({
                    'Authorization': f'Bearer {self.token}',
                    'Content-Type': 'application/json'
                })
                self.log_test("Authentication", "PASS", f"Successfully logged in as {LOGIN_EMAIL}")
                return True
            else:
                self.log_test("Authentication", "FAIL", f"Login failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Authentication", "FAIL", f"Login error: {str(e)}")
            return False
    
    def test_single_email_send(self):
        """Test 1: Single Email Send"""
        try:
            response = self.session.post(f"{BASE_URL}/messages/send-email", params={
                "recipient": "test@example.com",
                "subject": "Test Email",
                "body": "This is a test email message for rate limiting verification."
            })
            
            if response.status_code == 200:
                data = response.json()
                # Verify response structure
                required_fields = ['message', 'message_id', 'recipient', 'rate_limit']
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    self.log_test("Single Email Send", "FAIL", f"Missing fields: {missing_fields}")
                    return False
                
                # Verify rate limit info
                rate_limit = data['rate_limit']
                if rate_limit['limit'] != 100 or rate_limit['window'] != '1 hour':
                    self.log_test("Single Email Send", "FAIL", f"Incorrect rate limit info: {rate_limit}")
                    return False
                
                self.log_test("Single Email Send", "PASS", f"Email sent successfully. Remaining: {rate_limit['remaining']}/100")
                return True
            else:
                self.log_test("Single Email Send", "FAIL", f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Single Email Send", "FAIL", f"Error: {str(e)}")
            return False
    
    def test_single_sms_send(self):
        """Test 2: Single SMS Send"""
        try:
            response = self.session.post(f"{BASE_URL}/messages/send-sms", params={
                "recipient": "+1234567890",
                "body": "Test SMS message for rate limiting verification."
            })
            
            if response.status_code == 200:
                data = response.json()
                # Verify response structure
                required_fields = ['message', 'message_id', 'recipient', 'character_count', 'segments', 'rate_limit']
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    self.log_test("Single SMS Send", "FAIL", f"Missing fields: {missing_fields}")
                    return False
                
                # Verify rate limit info
                rate_limit = data['rate_limit']
                if rate_limit['limit'] != 50 or rate_limit['window'] != '1 hour':
                    self.log_test("Single SMS Send", "FAIL", f"Incorrect rate limit info: {rate_limit}")
                    return False
                
                self.log_test("Single SMS Send", "PASS", f"SMS sent successfully. Remaining: {rate_limit['remaining']}/50, Segments: {data['segments']}")
                return True
            else:
                self.log_test("Single SMS Send", "FAIL", f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Single SMS Send", "FAIL", f"Error: {str(e)}")
            return False
    
    def test_single_whatsapp_send(self):
        """Test 3: Single WhatsApp Send"""
        try:
            response = self.session.post(f"{BASE_URL}/messages/send-whatsapp", params={
                "recipient": "+1234567890",
                "body": "Test WhatsApp message for rate limiting verification."
            })
            
            if response.status_code == 200:
                data = response.json()
                # Verify response structure
                required_fields = ['message', 'message_id', 'recipient', 'character_count', 'rate_limit']
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    self.log_test("Single WhatsApp Send", "FAIL", f"Missing fields: {missing_fields}")
                    return False
                
                # Verify rate limit info
                rate_limit = data['rate_limit']
                if rate_limit['limit'] != 80 or rate_limit['window'] != '1 hour':
                    self.log_test("Single WhatsApp Send", "FAIL", f"Incorrect rate limit info: {rate_limit}")
                    return False
                
                self.log_test("Single WhatsApp Send", "PASS", f"WhatsApp sent successfully. Remaining: {rate_limit['remaining']}/80")
                return True
            else:
                self.log_test("Single WhatsApp Send", "FAIL", f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Single WhatsApp Send", "FAIL", f"Error: {str(e)}")
            return False
    
    def test_rate_limit_thresholds(self):
        """Test 4: Verify Rate Limit Thresholds"""
        thresholds = [
            ("email", 100, "/messages/send-email", {"recipient": "test@example.com", "subject": "Test", "body": "Test"}),
            ("sms", 50, "/messages/send-sms", {"recipient": "+1234567890", "body": "Test"}),
            ("whatsapp", 80, "/messages/send-whatsapp", {"recipient": "+1234567890", "body": "Test"})
        ]
        
        all_passed = True
        for channel, expected_limit, endpoint, payload in thresholds:
            try:
                response = self.session.post(f"{BASE_URL}{endpoint}", params=payload)
                if response.status_code == 200:
                    data = response.json()
                    actual_limit = data['rate_limit']['limit']
                    if actual_limit == expected_limit:
                        self.log_test(f"Rate Limit Threshold - {channel.upper()}", "PASS", f"Correct limit: {actual_limit}")
                    else:
                        self.log_test(f"Rate Limit Threshold - {channel.upper()}", "FAIL", f"Expected {expected_limit}, got {actual_limit}")
                        all_passed = False
                else:
                    self.log_test(f"Rate Limit Threshold - {channel.upper()}", "FAIL", f"HTTP {response.status_code}")
                    all_passed = False
            except Exception as e:
                self.log_test(f"Rate Limit Threshold - {channel.upper()}", "FAIL", f"Error: {str(e)}")
                all_passed = False
        
        return all_passed
    
    def test_rapid_fire_emails(self):
        """Test 5: Rapid Fire Test - Send 10 emails rapidly"""
        try:
            initial_response = self.session.post(f"{BASE_URL}/messages/send-email", params={
                "recipient": "test1@example.com",
                "subject": "Rapid Fire Test",
                "body": "Initial email to check starting count"
            })
            
            if initial_response.status_code != 200:
                self.log_test("Rapid Fire Test", "FAIL", "Failed to send initial email")
                return False
            
            initial_remaining = initial_response.json()['rate_limit']['remaining']
            
            # Send 10 emails rapidly
            success_count = 0
            for i in range(10):
                response = self.session.post(f"{BASE_URL}/messages/send-email", json={
                    "recipient": f"rapidfire{i}@example.com",
                    "subject": f"Rapid Fire Test {i+1}",
                    "body": f"This is rapid fire email number {i+1}"
                })
                
                if response.status_code == 200:
                    success_count += 1
                elif response.status_code == 429:
                    self.log_test("Rapid Fire Test", "FAIL", f"Rate limit hit too early at email {i+1}")
                    return False
                
                # Small delay to avoid overwhelming the server
                time.sleep(0.1)
            
            # Check final count
            final_response = self.session.post(f"{BASE_URL}/messages/send-email", json={
                "recipient": "final@example.com",
                "subject": "Final Check",
                "body": "Final email to check remaining count"
            })
            
            if final_response.status_code == 200:
                final_remaining = final_response.json()['rate_limit']['remaining']
                expected_decrease = success_count + 1  # +1 for the final check email
                actual_decrease = initial_remaining - final_remaining
                
                if actual_decrease >= expected_decrease:
                    self.log_test("Rapid Fire Test", "PASS", f"Sent {success_count} emails rapidly. Count decreased by {actual_decrease}")
                    return True
                else:
                    self.log_test("Rapid Fire Test", "FAIL", f"Count decrease mismatch. Expected: {expected_decrease}, Actual: {actual_decrease}")
                    return False
            else:
                self.log_test("Rapid Fire Test", "FAIL", "Failed to get final count")
                return False
                
        except Exception as e:
            self.log_test("Rapid Fire Test", "FAIL", f"Error: {str(e)}")
            return False
    
    def test_input_validation(self):
        """Test 6: Input Validation"""
        validation_tests = [
            # Invalid email tests
            {
                "name": "Invalid Email - No @",
                "endpoint": "/messages/send-email",
                "payload": {"recipient": "invalid-email", "subject": "Test", "body": "Test"},
                "expected_status": 400
            },
            {
                "name": "Invalid Email - Empty",
                "endpoint": "/messages/send-email", 
                "payload": {"recipient": "", "subject": "Test", "body": "Test"},
                "expected_status": 400
            },
            {
                "name": "Empty Email Body",
                "endpoint": "/messages/send-email",
                "payload": {"recipient": "test@example.com", "subject": "Test", "body": ""},
                "expected_status": 400
            },
            # Invalid phone tests
            {
                "name": "Invalid Phone - No + prefix",
                "endpoint": "/messages/send-sms",
                "payload": {"recipient": "1234567890", "body": "Test"},
                "expected_status": 400
            },
            {
                "name": "Invalid Phone - Empty",
                "endpoint": "/messages/send-sms",
                "payload": {"recipient": "", "body": "Test"},
                "expected_status": 400
            },
            {
                "name": "Empty SMS Body",
                "endpoint": "/messages/send-sms",
                "payload": {"recipient": "+1234567890", "body": ""},
                "expected_status": 400
            },
            # WhatsApp validation
            {
                "name": "Invalid WhatsApp Phone",
                "endpoint": "/messages/send-whatsapp",
                "payload": {"recipient": "1234567890", "body": "Test"},
                "expected_status": 400
            },
            {
                "name": "Empty WhatsApp Body",
                "endpoint": "/messages/send-whatsapp",
                "payload": {"recipient": "+1234567890", "body": ""},
                "expected_status": 400
            }
        ]
        
        all_passed = True
        for test in validation_tests:
            try:
                response = self.session.post(f"{BASE_URL}{test['endpoint']}", json=test['payload'])
                if response.status_code == test['expected_status']:
                    self.log_test(f"Input Validation - {test['name']}", "PASS", f"Correctly returned {response.status_code}")
                else:
                    self.log_test(f"Input Validation - {test['name']}", "FAIL", f"Expected {test['expected_status']}, got {response.status_code}")
                    all_passed = False
            except Exception as e:
                self.log_test(f"Input Validation - {test['name']}", "FAIL", f"Error: {str(e)}")
                all_passed = False
        
        return all_passed
    
    def test_sms_character_warnings(self):
        """Test 7: SMS Character Warnings (>160 characters)"""
        try:
            # Test message over 160 characters
            long_message = "This is a very long SMS message that exceeds 160 characters to test the segment count and warning functionality. " + \
                          "It should trigger a warning about multiple SMS segments being required for delivery. This message is intentionally long."
            
            response = self.session.post(f"{BASE_URL}/messages/send-sms", json={
                "recipient": "+1234567890",
                "body": long_message
            })
            
            if response.status_code == 200:
                data = response.json()
                
                # Check character count
                if data['character_count'] != len(long_message):
                    self.log_test("SMS Character Warnings", "FAIL", f"Character count mismatch: {data['character_count']} vs {len(long_message)}")
                    return False
                
                # Check segment count (should be > 1 for messages over 160 chars)
                expected_segments = (len(long_message) // 160) + 1
                if data['segments'] != expected_segments:
                    self.log_test("SMS Character Warnings", "FAIL", f"Segment count mismatch: {data['segments']} vs {expected_segments}")
                    return False
                
                # Check for warning message
                if 'warning' in data:
                    self.log_test("SMS Character Warnings", "PASS", f"Warning present: {data['warning']}. Segments: {data['segments']}")
                    return True
                else:
                    self.log_test("SMS Character Warnings", "WARN", f"No warning field, but segments calculated correctly: {data['segments']}")
                    return True
            else:
                self.log_test("SMS Character Warnings", "FAIL", f"HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("SMS Character Warnings", "FAIL", f"Error: {str(e)}")
            return False
    
    def test_rate_limit_info_format(self):
        """Test 8: Rate Limit Info Format Verification"""
        endpoints = [
            ("/messages/send-email", {"recipient": "info@example.com", "subject": "Info Test", "body": "Test"}, 100),
            ("/messages/send-sms", {"recipient": "+1234567890", "body": "Info test"}, 50),
            ("/messages/send-whatsapp", {"recipient": "+1234567890", "body": "Info test"}, 80)
        ]
        
        all_passed = True
        for endpoint, payload, expected_limit in endpoints:
            try:
                response = self.session.post(f"{BASE_URL}{endpoint}", json=payload)
                if response.status_code == 200:
                    data = response.json()
                    rate_limit = data.get('rate_limit', {})
                    
                    # Check required fields
                    required_fields = ['limit', 'window', 'remaining']
                    missing_fields = [field for field in required_fields if field not in rate_limit]
                    
                    if missing_fields:
                        self.log_test(f"Rate Limit Info Format - {endpoint}", "FAIL", f"Missing fields: {missing_fields}")
                        all_passed = False
                        continue
                    
                    # Check values
                    if rate_limit['limit'] != expected_limit:
                        self.log_test(f"Rate Limit Info Format - {endpoint}", "FAIL", f"Wrong limit: {rate_limit['limit']} vs {expected_limit}")
                        all_passed = False
                        continue
                    
                    if rate_limit['window'] != '1 hour':
                        self.log_test(f"Rate Limit Info Format - {endpoint}", "FAIL", f"Wrong window: {rate_limit['window']}")
                        all_passed = False
                        continue
                    
                    if not isinstance(rate_limit['remaining'], int) or rate_limit['remaining'] < 0:
                        self.log_test(f"Rate Limit Info Format - {endpoint}", "FAIL", f"Invalid remaining count: {rate_limit['remaining']}")
                        all_passed = False
                        continue
                    
                    self.log_test(f"Rate Limit Info Format - {endpoint}", "PASS", f"Correct format: {rate_limit}")
                else:
                    self.log_test(f"Rate Limit Info Format - {endpoint}", "FAIL", f"HTTP {response.status_code}")
                    all_passed = False
                    
            except Exception as e:
                self.log_test(f"Rate Limit Info Format - {endpoint}", "FAIL", f"Error: {str(e)}")
                all_passed = False
        
        return all_passed
    
    def run_all_tests(self):
        """Run all messaging throttling tests"""
        print("🚀 Starting Messaging Throttling Test Suite")
        print("=" * 60)
        
        # Login first
        if not self.login():
            print("❌ Authentication failed. Cannot proceed with tests.")
            return False
        
        print("\n📧 Testing Messaging System Rate Limiting...")
        print("-" * 40)
        
        # Run all tests
        tests = [
            self.test_single_email_send,
            self.test_single_sms_send,
            self.test_single_whatsapp_send,
            self.test_rate_limit_thresholds,
            self.test_rapid_fire_emails,
            self.test_input_validation,
            self.test_sms_character_warnings,
            self.test_rate_limit_info_format
        ]
        
        passed = 0
        failed = 0
        
        for test in tests:
            try:
                if test():
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                print(f"❌ Test {test.__name__} crashed: {str(e)}")
                failed += 1
            
            # Small delay between tests
            time.sleep(0.5)
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        total_tests = passed + failed
        success_rate = (passed / total_tests * 100) if total_tests > 0 else 0
        
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"📈 Success Rate: {success_rate:.1f}%")
        
        if failed == 0:
            print("\n🎉 All messaging throttling tests passed!")
        else:
            print(f"\n⚠️  {failed} test(s) failed. Check details above.")
        
        return failed == 0

def main():
    """Main function"""
    tester = MessagingThrottlingTester()
    success = tester.run_all_tests()
    
    if success:
        print("\n✅ Messaging throttling system is working correctly!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. Please review the issues above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
