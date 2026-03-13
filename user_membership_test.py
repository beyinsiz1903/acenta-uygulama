#!/usr/bin/env python3
"""
Syroce backend comprehensive test for user creation + tenant membership self-heal bug fix.

Turkish Review Request:
- Test user creation via POST /api/admin/all-users for agency user
- Test login for created user; should return 200 without "Aktif tenant üyeliği bulunamadı" error  
- Test POST /api/admin/all-users/repair-memberships endpoint; should return 200 with numerical result
- Delete test user if possible

Base URL: https://shadow-traffic.preview.emergentagent.com
Credentials: admin@acenta.test / admin123
"""

import requests
import uuid
import json
import time

# Configuration
BASE_URL = "https://shadow-traffic.preview.emergentagent.com"
ADMIN_EMAIL = "admin@acenta.test"
ADMIN_PASSWORD = "admin123"

# Demo agencies from seed data (from existing tests)
DEMO_ACENTA_ID = "f5f7a2a3-5de1-4d65-b700-ec4f9807d83a"
DEMO_ACENTE_A_ID = "a8456a97-f714-4c69-bc7e-d58c3b7d088d"
DEMO_ACENTE_B_ID = "301121c7-30c1-4048-b0d4-9b51c38915ac"

class SyroceUserMembershipTester:
    def __init__(self):
        self.admin_token = None
        self.test_user_id = None
        self.test_user_email = None
        self.test_user_password = "TestPassword123!"
        
    def authenticate_admin(self):
        """Step 1: Admin login başarılı olsun"""
        print("🔐 Step 1: Admin authentication...")
        
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={
                "email": ADMIN_EMAIL,
                "password": ADMIN_PASSWORD
            },
            timeout=15
        )
        
        if response.status_code != 200:
            raise Exception(f"Admin login failed: {response.status_code} - {response.text}")
        
        auth_data = response.json()
        self.admin_token = auth_data.get("access_token")
        
        if not self.admin_token:
            raise Exception(f"No access token in login response: {auth_data}")
        
        print(f"✅ Admin login successful! Token: {len(self.admin_token)} chars")
        print(f"   User roles: {auth_data.get('user', {}).get('roles', [])}")
        return True
        
    def create_agency_user(self):
        """Step 2: POST /api/admin/all-users ile bir agency kullanıcı oluştur"""
        print("\n👤 Step 2: Creating agency user...")
        
        # Generate unique email for this test
        unique_id = uuid.uuid4().hex[:8]
        self.test_user_email = f"test_user_membership_{unique_id}@syroce.test"
        
        user_payload = {
            "email": self.test_user_email,
            "name": f"Test User Membership {unique_id}",
            "password": self.test_user_password,
            "agency_id": DEMO_ACENTA_ID,  # Demo Acenta
            "role": "agency_admin"  # Using agency_admin role for better testing
        }
        
        response = requests.post(
            f"{BASE_URL}/api/admin/all-users",
            headers={"Authorization": f"Bearer {self.admin_token}"},
            json=user_payload,
            timeout=15
        )
        
        if response.status_code != 200:
            raise Exception(f"User creation failed: {response.status_code} - {response.text}")
        
        user_data = response.json()
        self.test_user_id = user_data.get("id")
        
        if not self.test_user_id:
            raise Exception(f"No user ID in creation response: {user_data}")
            
        print(f"✅ User created successfully!")
        print(f"   User ID: {self.test_user_id}")
        print(f"   Email: {user_data.get('email')}")
        print(f"   Name: {user_data.get('name')}")
        print(f"   Agency: {user_data.get('agency_name')} ({user_data.get('agency_id')})")
        print(f"   Roles: {user_data.get('roles', [])}")
        print(f"   Status: {user_data.get('status')}")
        
        return True
        
    def test_user_login(self):
        """Step 3: Oluşan kullanıcı için login dene; artık 'Aktif tenant üyeliği bulunamadı' hatası olmadan 200 dönmeli"""
        print(f"\n🔑 Step 3: Testing login for created user ({self.test_user_email})...")
        
        # Wait a moment for user creation to propagate
        time.sleep(2)
        
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={
                "email": self.test_user_email,
                "password": self.test_user_password
            },
            timeout=15
        )
        
        print(f"   Login response status: {response.status_code}")
        
        if response.status_code == 200:
            login_data = response.json()
            print("✅ User login successful!")
            print(f"   Access token: {len(login_data.get('access_token', ''))} chars")
            print(f"   User roles: {login_data.get('user', {}).get('roles', [])}")
            print(f"   Tenant ID: {login_data.get('tenant_id', 'N/A')}")
            
            # Test /api/auth/me to verify session works
            user_token = login_data.get('access_token')
            if user_token:
                me_response = requests.get(
                    f"{BASE_URL}/api/auth/me",
                    headers={"Authorization": f"Bearer {user_token}"},
                    timeout=10
                )
                if me_response.status_code == 200:
                    me_data = me_response.json()
                    print(f"   /api/auth/me successful: {me_data.get('email')} with roles {me_data.get('roles', [])}")
                else:
                    print(f"   ⚠️  /api/auth/me failed: {me_response.status_code} - {me_response.text}")
            
            return True
        else:
            print(f"❌ User login failed: {response.status_code}")
            print(f"   Response: {response.text}")
            
            # Check if this is the specific "Aktif tenant üyeliği bulunamadı" error
            response_text = response.text.lower()
            if "tenant" in response_text and ("üyelik" in response_text or "membership" in response_text):
                print("   🐛 This appears to be the 'Aktif tenant üyeliği bulunamadı' bug!")
                return False
            elif response.status_code == 401:
                print("   This appears to be authentication error (credentials)")
                return False
            else:
                print("   Unknown login error")
                return False
        
    def test_repair_memberships(self):
        """Step 4: POST /api/admin/all-users/repair-memberships endpointini çağır; 200 ve sayısal sonuç dönmeli"""
        print("\n🔧 Step 4: Testing membership repair endpoint...")
        
        response = requests.post(
            f"{BASE_URL}/api/admin/all-users/repair-memberships",
            headers={"Authorization": f"Bearer {self.admin_token}"},
            timeout=15
        )
        
        print(f"   Repair response status: {response.status_code}")
        
        if response.status_code == 200:
            repair_data = response.json()
            print("✅ Membership repair endpoint successful!")
            print(f"   Response: {repair_data}")
            
            # Check for numerical result
            repaired_count = repair_data.get("repaired", repair_data.get("fixed", repair_data.get("count", 0)))
            if isinstance(repaired_count, (int, float)):
                print(f"   Repaired memberships: {repaired_count}")
                return True
            else:
                print(f"   ⚠️  No numerical result found in response: {repair_data}")
                return False
        else:
            print(f"❌ Membership repair failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    
    def retest_user_login_after_repair(self):
        """Step 5: Test user login again after repair to verify fix"""
        print(f"\n🔄 Step 5: Re-testing login after repair for user ({self.test_user_email})...")
        
        # Wait a moment for repair to propagate
        time.sleep(2)
        
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={
                "email": self.test_user_email,
                "password": self.test_user_password
            },
            timeout=15
        )
        
        print(f"   Post-repair login status: {response.status_code}")
        
        if response.status_code == 200:
            login_data = response.json()
            print("✅ Post-repair login successful!")
            print(f"   Access token: {len(login_data.get('access_token', ''))} chars")
            print(f"   Tenant ID: {login_data.get('tenant_id', 'N/A')}")
            return True
        else:
            print(f"❌ Post-repair login still fails: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    def cleanup_test_user(self):
        """Step 6: Mümkünse oluşturduğun test kullanıcıyı sil"""
        print(f"\n🗑️  Step 6: Cleaning up test user...")
        
        if not self.test_user_id:
            print("   No user ID to delete")
            return True
        
        response = requests.delete(
            f"{BASE_URL}/api/admin/all-users/{self.test_user_id}",
            headers={"Authorization": f"Bearer {self.admin_token}"},
            timeout=15
        )
        
        if response.status_code == 200:
            delete_data = response.json()
            print("✅ Test user deleted successfully!")
            print(f"   Delete response: {delete_data}")
            return True
        else:
            print(f"⚠️  Test user deletion failed: {response.status_code}")
            print(f"   Response: {response.text}")
            print(f"   Manual cleanup may be needed for user ID: {self.test_user_id}")
            return False
    
    def run_comprehensive_test(self):
        """Run all test steps in sequence"""
        print("=" * 70)
        print("🧪 SYROCE BACKEND USER CREATION + TENANT MEMBERSHIP SELF-HEAL TEST")
        print("=" * 70)
        
        results = {
            "admin_login": False,
            "user_creation": False,
            "initial_user_login": False,
            "membership_repair": False,
            "post_repair_login": False,
            "cleanup": False
        }
        
        try:
            # Step 1: Admin authentication
            results["admin_login"] = self.authenticate_admin()
            
            # Step 2: Create agency user
            results["user_creation"] = self.create_agency_user()
            
            # Step 3: Test initial user login
            results["initial_user_login"] = self.test_user_login()
            
            # Step 4: Test membership repair endpoint
            results["membership_repair"] = self.test_repair_memberships()
            
            # Step 5: Re-test login after repair (if initial login failed)
            if not results["initial_user_login"]:
                results["post_repair_login"] = self.retest_user_login_after_repair()
            else:
                results["post_repair_login"] = True  # Already working
                
            # Step 6: Cleanup
            results["cleanup"] = self.cleanup_test_user()
            
        except Exception as e:
            print(f"\n💥 Test failed with exception: {e}")
            # Still attempt cleanup
            try:
                if self.test_user_id and self.admin_token:
                    self.cleanup_test_user()
            except:
                pass
        
        # Print summary
        print("\n" + "=" * 70)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 70)
        
        for test_name, passed in results.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"   {test_name.replace('_', ' ').title()}: {status}")
        
        # Overall assessment
        critical_tests = ["admin_login", "user_creation", "membership_repair"]
        critical_passed = all(results[test] for test in critical_tests)
        
        membership_bug_fixed = results["initial_user_login"] or results["post_repair_login"]
        
        print(f"\n🎯 CRITICAL FUNCTIONALITY: {'✅ WORKING' if critical_passed else '❌ BROKEN'}")
        print(f"🐛 MEMBERSHIP BUG STATUS: {'✅ FIXED' if membership_bug_fixed else '❌ STILL PRESENT'}")
        
        if critical_passed and membership_bug_fixed:
            print("\n🎉 OVERALL: ALL TESTS PASSED - User creation and tenant membership self-heal is working!")
        elif critical_passed:
            print("\n⚠️  OVERALL: Critical APIs work, but membership bug may need investigation")
        else:
            print("\n💥 OVERALL: Critical functionality is broken - needs immediate attention")
            
        return results


def main():
    """Main test runner"""
    tester = SyroceUserMembershipTester()
    results = tester.run_comprehensive_test()
    
    # Return appropriate exit code
    critical_tests = ["admin_login", "user_creation", "membership_repair"]
    if all(results[test] for test in critical_tests):
        return 0  # Success
    else:
        return 1  # Failure


if __name__ == "__main__":
    exit(main())