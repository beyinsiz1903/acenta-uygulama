#!/usr/bin/env python3
"""
Simple Syroce Backend Regression Check - Turkish Review Request
Focus on specific flows mentioned in the review request
"""

import requests
import time

def test_syroce_backend_regression():
    """Test specific backend flows from review request"""
    base_url = "https://syroce-staging-1.preview.emergentagent.com/api"
    results = []
    
    print("🔍 SYROCE BACKEND REGRESSION CHECK - TURKISH REVIEW REQUEST")
    print("Testing backend/API flows per review request")
    print("=" * 80)
    
    session = requests.Session()
    
    # 1. Test admin login
    print("1️⃣ Testing admin login (admin@acenta.test/admin123)...")
    try:
        response = session.post(f"{base_url}/auth/login", 
                               json={"email": "admin@acenta.test", "password": "admin123"})
        
        if response.status_code == 200:
            admin_data = response.json()
            admin_token = admin_data.get('access_token')
            admin_roles = admin_data.get('user', {}).get('roles', [])
            
            if 'super_admin' in admin_roles:
                print("✅ Admin login successful - super_admin role confirmed")
                results.append("✅ Admin login working")
            else:
                print(f"❌ Admin login - missing super_admin role: {admin_roles}")
                results.append("❌ Admin login role issue")
                admin_token = None
        else:
            print(f"❌ Admin login failed - Status {response.status_code}: {response.text[:100]}")
            results.append("❌ Admin login failed")
            admin_token = None
    except Exception as e:
        print(f"❌ Admin login error: {e}")
        results.append("❌ Admin login error")
        admin_token = None
    
    time.sleep(1)  # Rate limit protection
    
    # 2. Test agency login
    print("\n2️⃣ Testing agency admin login (agent@acenta.test/agent123)...")
    try:
        response = session.post(f"{base_url}/auth/login", 
                               json={"email": "agent@acenta.test", "password": "agent123"})
        
        if response.status_code == 200:
            agency_data = response.json()
            agency_token = agency_data.get('access_token')
            agency_roles = agency_data.get('user', {}).get('roles', [])
            
            if 'agency_admin' in agency_roles:
                print("✅ Agency login successful - agency_admin role confirmed")
                results.append("✅ Agency login working")
            else:
                print(f"❌ Agency login - missing agency_admin role: {agency_roles}")
                results.append("❌ Agency login role issue")
                agency_token = None
        else:
            print(f"❌ Agency login failed - Status {response.status_code}: {response.text[:100]}")
            results.append("❌ Agency login failed")
            agency_token = None
    except Exception as e:
        print(f"❌ Agency login error: {e}")
        results.append("❌ Agency login error")
        agency_token = None
    
    time.sleep(1)  # Rate limit protection
    
    # 3. Test /auth/me authenticated behavior
    print("\n3️⃣ Testing /auth/me authenticated behavior...")
    if admin_token:
        try:
            response = session.get(f"{base_url}/auth/me", 
                                 headers={"Authorization": f"Bearer {admin_token}"})
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Authenticated /auth/me working - User: {data.get('email')}, Roles: {data.get('roles')}")
                results.append("✅ Authenticated /auth/me working")
            else:
                print(f"❌ Authenticated /auth/me failed - Status {response.status_code}")
                results.append("❌ Authenticated /auth/me failed")
        except Exception as e:
            print(f"❌ Authenticated /auth/me error: {e}")
            results.append("❌ Authenticated /auth/me error")
    else:
        print("❌ Cannot test authenticated /auth/me - no admin token")
        results.append("❌ Cannot test authenticated /auth/me")
    
    time.sleep(1)  # Rate limit protection
    
    # 4. Test /auth/me unauthenticated behavior
    print("\n4️⃣ Testing /auth/me unauthenticated behavior...")
    try:
        response = session.get(f"{base_url}/auth/me")  # No auth header
        
        if response.status_code == 401:
            print("✅ Unauthenticated /auth/me correctly returns 401")
            results.append("✅ Unauthenticated /auth/me working")
        else:
            print(f"❌ Unauthenticated /auth/me - Expected 401, got {response.status_code}")
            results.append("❌ Unauthenticated /auth/me unexpected status")
    except Exception as e:
        print(f"❌ Unauthenticated /auth/me error: {e}")
        results.append("❌ Unauthenticated /auth/me error")
    
    time.sleep(1)  # Rate limit protection
    
    # 5. Test agency profile
    print("\n5️⃣ Testing agency profile...")
    if agency_token:
        try:
            response = session.get(f"{base_url}/agency/profile", 
                                 headers={"Authorization": f"Bearer {agency_token}"})
            
            if response.status_code == 200:
                data = response.json()
                modules = data.get('allowed_modules', [])
                print(f"✅ Agency profile working - Modules: {modules}")
                results.append("✅ Agency profile working")
            else:
                print(f"❌ Agency profile failed - Status {response.status_code}")
                results.append("❌ Agency profile failed")
        except Exception as e:
            print(f"❌ Agency profile error: {e}")
            results.append("❌ Agency profile error")
    else:
        print("❌ Cannot test agency profile - no agency token")
        results.append("❌ Cannot test agency profile")
    
    time.sleep(1)  # Rate limit protection
    
    # 6. Test admin agencies modules endpoint (GET)
    print("\n6️⃣ Testing admin agencies modules GET...")
    if admin_token:
        # Use the known working agency ID
        agency_id = "f5f7a2a3-5de1-4d65-b700-ec4f9807d83a"
        try:
            response = session.get(f"{base_url}/admin/agencies/{agency_id}/modules", 
                                 headers={"Authorization": f"Bearer {admin_token}"})
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Admin agencies modules GET working - Response keys: {list(data.keys())}")
                results.append("✅ Admin agencies modules GET working")
            else:
                print(f"❌ Admin agencies modules GET failed - Status {response.status_code}")
                results.append("❌ Admin agencies modules GET failed")
        except Exception as e:
            print(f"❌ Admin agencies modules GET error: {e}")
            results.append("❌ Admin agencies modules GET error")
    else:
        print("❌ Cannot test admin agencies modules - no admin token")
        results.append("❌ Cannot test admin agencies modules")
    
    time.sleep(1)  # Rate limit protection
    
    # 7. Test admin agencies modules endpoint (PUT) - Simple test
    print("\n7️⃣ Testing admin agencies modules PUT...")
    if admin_token:
        agency_id = "f5f7a2a3-5de1-4d65-b700-ec4f9807d83a"
        try:
            # Simple module update test
            test_modules = ["dashboard", "rezervasyonlar", "musteriler", "musaitlik", "turlar"]
            response = session.put(f"{base_url}/admin/agencies/{agency_id}/modules", 
                                 json={"allowed_modules": test_modules},
                                 headers={"Authorization": f"Bearer {admin_token}", 
                                         "Content-Type": "application/json"})
            
            if response.status_code == 200:
                print("✅ Admin agencies modules PUT working - Update successful")
                results.append("✅ Admin agencies modules PUT working")
            else:
                print(f"❌ Admin agencies modules PUT failed - Status {response.status_code}: {response.text[:100]}")
                results.append("❌ Admin agencies modules PUT failed")
        except Exception as e:
            print(f"❌ Admin agencies modules PUT error: {e}")
            results.append("❌ Admin agencies modules PUT error")
    else:
        print("❌ Cannot test admin agencies modules PUT - no admin token")
        results.append("❌ Cannot test admin agencies modules PUT")
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 SUMMARY:")
    for result in results:
        print(f"  {result}")
    
    passed_count = sum(1 for r in results if "✅" in r)
    total_count = len(results)
    print(f"\n📈 RESULTS: {passed_count}/{total_count} tests passed")
    
    if passed_count == total_count:
        print("🎉 ALL TESTS PASSED - No regression detected!")
        return True
    else:
        print("⚠️ Some tests failed - Regression detected!")
        return False

if __name__ == "__main__":
    success = test_syroce_backend_regression()
    exit(0 if success else 1)