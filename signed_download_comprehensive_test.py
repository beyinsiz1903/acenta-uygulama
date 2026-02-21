#!/usr/bin/env python3
"""
Comprehensive test for signed download link functionality
This test directly accesses MongoDB to get real tokens and test the full flow
"""
import requests
import asyncio
import sys
import os
from datetime import datetime, timedelta

# Add the backend directory to the path
sys.path.insert(0, '/app/backend')

from app.db import connect_mongo, get_db

class SignedDownloadComprehensiveTest:
    def __init__(self, base_url="https://jwt-revocation-add.preview.emergentagent.com"):
        self.base_url = base_url
        self.admin_token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.failed_tests = []
        
        # Store data for testing
        self.run_id = None
        self.download_token = None
        self.policy_key = None

    def log(self, msg):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    def run_test(self, name, method, endpoint, expected_status, data=None, headers_override=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        headers = headers_override or {'Content-Type': 'application/json'}
        if self.admin_token and not headers_override:
            headers['Authorization'] = f'Bearer {self.admin_token}'

        self.tests_run += 1
        self.log(f"🔍 Test #{self.tests_run}: {name}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=10)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=10)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=10)
            else:
                raise ValueError(f"Unsupported method: {method}")

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                self.log(f"✅ PASSED - Status: {response.status_code}")
                try:
                    return True, response.json() if response.content else {}, response
                except:
                    return True, {}, response
            else:
                self.tests_failed += 1
                self.failed_tests.append(f"{name} - Expected {expected_status}, got {response.status_code}")
                self.log(f"❌ FAILED - Expected {expected_status}, got {response.status_code}")
                try:
                    self.log(f"   Response: {response.text[:200]}")
                except:
                    pass
                return False, {}, response

        except Exception as e:
            self.tests_failed += 1
            self.failed_tests.append(f"{name} - Error: {str(e)}")
            self.log(f"❌ FAILED - Error: {str(e)}")
            return False, {}, None

    async def test_admin_login(self):
        """Test admin login"""
        self.log("\n=== AUTHENTICATION ===")
        success, response, _ = self.run_test(
            "Admin Login (admin@acenta.test/admin123)",
            "POST",
            "api/auth/login",
            200,
            data={"email": "admin@acenta.test", "password": "admin123"},
            headers_override={'Content-Type': 'application/json'}
        )
        if success and 'access_token' in response:
            self.admin_token = response['access_token']
            user = response.get('user', {})
            roles = user.get('roles', [])
            
            if 'admin' in roles or 'super_admin' in roles:
                self.log(f"✅ Admin login successful - roles: {roles}")
                return True
            else:
                self.log(f"❌ Missing admin/super_admin role: {roles}")
                return False
        return False

    async def test_run_export_and_inspect_download_field(self):
        """1) Run export and inspect export_runs doc for download field"""
        self.log("\n=== 1) RUN EXPORT AND INSPECT DOWNLOAD FIELD ===")
        
        # Use a unique policy key to avoid cooldown
        import time
        self.policy_key = f"match_risk_daily_{int(time.time())}"
        
        # First, set up the policy with recipients
        policy_data = {
            "key": self.policy_key,
            "enabled": True,
            "type": "match_risk_summary",
            "format": "csv",
            "recipients": ["alerts@acenta.test"],
            "cooldown_hours": 1,
            "params": {
                "days": 30,
                "min_matches": 1,
                "only_high_risk": False
            }
        }
        success, response, _ = self.run_test(
            f"Setup Policy {self.policy_key}",
            "PUT",
            f"api/admin/exports/policies/{self.policy_key}",
            200,
            data=policy_data
        )
        
        if not success:
            return False
        
        # Run export with dry_run=0
        success, response, _ = self.run_test(
            f"Run Export (dry_run=0) for {self.policy_key}",
            "POST",
            f"api/admin/exports/run?key={self.policy_key}&dry_run=0",
            200
        )
        
        if success and response.get('run_id'):
            self.run_id = response['run_id']
            self.log(f"✅ Export run created with ID: {self.run_id}")
            
            # Now access MongoDB directly to inspect the download field
            db = await get_db()
            from bson import ObjectId
            
            try:
                run_doc = await db.export_runs.find_one({"_id": ObjectId(self.run_id)})
                if run_doc:
                    download_info = run_doc.get('download', {})
                    token = download_info.get('token')
                    expires_at = download_info.get('expires_at')
                    
                    if token and expires_at:
                        self.download_token = token
                        self.log(f"✅ Download field exists with token: {token[:20]}...")
                        self.log(f"✅ Expires at: {expires_at}")
                        
                        # Verify expires_at is ~7 days in the future
                        now = datetime.utcnow()
                        if isinstance(expires_at, str):
                            expires_dt = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                        else:
                            expires_dt = expires_at
                        
                        days_diff = (expires_dt - now).days
                        if 6 <= days_diff <= 8:  # Allow some tolerance
                            self.log(f"✅ Expiry time is correct (~7 days): {days_diff} days")
                            return True
                        else:
                            self.log(f"❌ Expiry time incorrect: {days_diff} days (expected ~7)")
                            return False
                    else:
                        self.log(f"❌ Download field missing token or expires_at: {download_info}")
                        return False
                else:
                    self.log(f"❌ Could not find run document in MongoDB")
                    return False
            except Exception as e:
                self.log(f"❌ Error accessing MongoDB: {e}")
                return False
        else:
            self.log(f"❌ Export run failed")
            return False

    async def test_public_download_endpoint(self):
        """2) Test public download endpoint with real token"""
        self.log("\n=== 2) PUBLIC DOWNLOAD ENDPOINT TEST ===")
        
        if not self.download_token:
            self.log("❌ No download token available")
            return False
        
        # Test public download with real token
        success, response, http_response = self.run_test(
            f"Public Download with Real Token",
            "GET",
            f"api/exports/download/{self.download_token}",
            200,
            headers_override={}  # No auth required
        )
        
        if success and http_response:
            content_type = http_response.headers.get('content-type', '')
            content_disposition = http_response.headers.get('content-disposition', '')
            
            if 'text/csv' in content_type:
                self.log(f"✅ Public download returns CSV content")
                
                if 'attachment' in content_disposition:
                    self.log(f"✅ Proper Content-Disposition header: {content_disposition}")
                    
                    # Check CSV content
                    csv_content = http_response.text
                    lines = csv_content.strip().split('\n')
                    
                    if len(lines) >= 1:  # At least header
                        self.log(f"✅ CSV has {len(lines)} lines")
                        self.log(f"✅ First 3 lines of CSV:")
                        for i, line in enumerate(lines[:3]):
                            self.log(f"   Line {i+1}: {line}")
                        return True
                    else:
                        self.log(f"❌ CSV content too short: {len(lines)} lines")
                        return False
                else:
                    self.log(f"❌ Missing Content-Disposition header")
                    return False
            else:
                self.log(f"❌ Wrong content type: {content_type}")
                return False
        else:
            self.log(f"❌ Public download failed")
            return False

    async def test_expired_token_behavior(self):
        """3) Test expired token behavior"""
        self.log("\n=== 3) EXPIRED TOKEN BEHAVIOR TEST ===")
        
        if not self.run_id:
            self.log("❌ No run_id available")
            return False
        
        # Manually update the expires_at to a past time in MongoDB
        db = await get_db()
        from bson import ObjectId
        
        try:
            past_time = datetime.utcnow() - timedelta(days=1)
            result = await db.export_runs.update_one(
                {"_id": ObjectId(self.run_id)},
                {"$set": {"download.expires_at": past_time}}
            )
            
            if result.modified_count > 0:
                self.log(f"✅ Updated expires_at to past time: {past_time}")
                
                # Now test the download with expired token
                success, response, http_response = self.run_test(
                    f"Public Download with Expired Token",
                    "GET",
                    f"api/exports/download/{self.download_token}",
                    410,  # Expected 410 EXPORT_TOKEN_EXPIRED
                    headers_override={}
                )
                
                if success:
                    try:
                        error_response = http_response.json() if http_response else {}
                        if error_response.get('detail') == 'EXPORT_TOKEN_EXPIRED':
                            self.log(f"✅ Correct error for expired token: {error_response}")
                            return True
                        else:
                            self.log(f"❌ Wrong error message: {error_response}")
                            return False
                    except:
                        self.log(f"❌ Could not parse error response")
                        return False
                else:
                    self.log(f"❌ Expired token test failed")
                    return False
            else:
                self.log(f"❌ Could not update expires_at in MongoDB")
                return False
        except Exception as e:
            self.log(f"❌ Error updating MongoDB: {e}")
            return False

    async def test_email_body_link_format(self):
        """4) Test email body link format"""
        self.log("\n=== 4) EMAIL BODY LINK FORMAT TEST ===")
        
        # Check email_outbox for exports.ready event
        db = await get_db()
        
        try:
            email_record = await db.email_outbox.find_one({
                "event_type": "exports.ready"
            }, sort=[("created_at", -1)])
            
            if email_record:
                text_body = email_record.get('text_body', '')
                html_body = email_record.get('html_body', '')
                
                self.log(f"✅ Found email_outbox record with event_type='exports.ready'")
                
                # Check if text_body contains download link with token
                if '/api/exports/download/' in text_body:
                    self.log(f"✅ Text body contains signed download link")
                    
                    # Extract the download line
                    lines = text_body.split('\n')
                    download_line = None
                    for line in lines:
                        if 'Download:' in line:
                            download_line = line
                            break
                    
                    if download_line:
                        self.log(f"✅ Download line: {download_line}")
                        return True
                    else:
                        self.log(f"❌ Could not find Download line in text_body")
                        return False
                else:
                    self.log(f"❌ Text body does not contain signed download link")
                    self.log(f"   Text body: {text_body[:200]}...")
                    return False
            else:
                self.log(f"❌ No email_outbox record found with event_type='exports.ready'")
                return False
        except Exception as e:
            self.log(f"❌ Error checking email_outbox: {e}")
            return False

    def print_summary(self):
        """Print test summary"""
        self.log("\n" + "="*60)
        self.log("SIGNED DOWNLOAD LINK COMPREHENSIVE TEST SUMMARY")
        self.log("="*60)
        self.log(f"Total Tests: {self.tests_run}")
        self.log(f"✅ Passed: {self.tests_passed}")
        self.log(f"❌ Failed: {self.tests_failed}")
        self.log(f"Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        
        if self.failed_tests:
            self.log("\n❌ FAILED TESTS:")
            for i, test in enumerate(self.failed_tests, 1):
                self.log(f"  {i}. {test}")
        
        self.log("="*60)

    async def run_comprehensive_tests(self):
        """Run all comprehensive tests"""
        self.log("🚀 Starting Signed Download Link Comprehensive Tests")
        self.log(f"Base URL: {self.base_url}")
        
        # Connect to MongoDB
        await connect_mongo()
        
        # Authentication
        if not await self.test_admin_login():
            self.log("❌ Admin login failed - stopping tests")
            self.print_summary()
            return 1

        # 1) Run export and inspect download field
        if not await self.test_run_export_and_inspect_download_field():
            self.log("❌ Export and download field test failed")

        # 2) Test public download endpoint
        if self.download_token:
            await self.test_public_download_endpoint()

        # 3) Test expired token behavior
        if self.download_token:
            await self.test_expired_token_behavior()

        # 4) Test email body link format
        await self.test_email_body_link_format()

        # Summary
        self.print_summary()

        return 0 if self.tests_failed == 0 else 1


async def main():
    tester = SignedDownloadComprehensiveTest()
    exit_code = await tester.run_comprehensive_tests()
    sys.exit(exit_code)


if __name__ == "__main__":
    asyncio.run(main())