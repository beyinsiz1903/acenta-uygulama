#!/usr/bin/env python3
"""
Syroce Backend Auth/RBAC Smoke Validation Test
Turkish Review Request: Syroce backend için auth/RBAC smoke doğrulaması

Test Cases:
1) POST /api/auth/login admin@acenta.test / admin123 -> super_admin role verification
2) GET /api/auth/me with admin bearer token -> super_admin role verification  
3) GET /api/admin/all-users?limit=2 with admin token -> 200 + user list
4) POST /api/auth/login agent@acenta.test / agent123 -> agency role verification
5) GET /api/auth/me with agency bearer token -> agency user payload verification

Base URL: https://syroce-preview.preview.emergentagent.com
"""

import requests
import json
import sys

# Base configuration
BASE_URL = "https://syroce-preview.preview.emergentagent.com"
API_BASE = f"{BASE_URL}/api"

# Test credentials
ADMIN_CREDENTIALS = {
    "email": "admin@acenta.test",
    "password": "admin123"
}

AGENCY_CREDENTIALS = {
    "email": "agent@acenta.test", 
    "password": "agent123"
}

def log_test_result(test_name, success, details=""):
    """Log test result with Turkish descriptions"""
    status = "✅ BAŞARILI" if success else "❌ BAŞARISIZ"
    print(f"{status} {test_name}")
    if details:
        print(f"   {details}")
    print()

def test_admin_login_and_role():
    """Test 1: Admin login and super_admin role verification"""
    print("=== TEST 1: Admin Login + Super Admin Role Doğrulaması ===")
    
    try:
        # Login request
        login_url = f"{API_BASE}/auth/login"
        response = requests.post(login_url, json=ADMIN_CREDENTIALS)
        
        if response.status_code != 200:
            log_test_result("Admin Login", False, f"Status: {response.status_code}, Response: {response.text}")
            return None
            
        login_data = response.json()
        
        # Verify response structure
        if 'access_token' not in login_data:
            log_test_result("Admin Login", False, "access_token bulunamadı response içinde")
            return None
            
        # Verify user roles contains super_admin
        if 'user' in login_data and 'roles' in login_data['user']:
            user_roles = login_data['user']['roles']
            if 'super_admin' in user_roles:
                log_test_result("Admin Login + Role Doğrulaması", True, 
                               f"super_admin rolü doğrulandı, access_token uzunluk: {len(login_data['access_token'])} chars")
                return login_data['access_token']
            else:
                log_test_result("Admin Login + Role Doğrulaması", False, 
                               f"super_admin rolü bulunamadı. Mevcut roller: {user_roles}")
                return None
        else:
            log_test_result("Admin Login + Role Doğrulaması", False, 
                           "user.roles alanı response içinde bulunamadı")
            return None
            
    except Exception as e:
        log_test_result("Admin Login", False, f"Exception: {str(e)}")
        return None

def test_admin_auth_me(admin_token):
    """Test 2: GET /api/auth/me with admin bearer token"""
    print("=== TEST 2: GET /api/auth/me Admin Bearer Token ile ===")
    
    try:
        headers = {"Authorization": f"Bearer {admin_token}"}
        me_url = f"{API_BASE}/auth/me"
        response = requests.get(me_url, headers=headers)
        
        if response.status_code != 200:
            log_test_result("Admin /auth/me", False, f"Status: {response.status_code}, Response: {response.text}")
            return False
            
        me_data = response.json()
        
        # Verify super_admin role in response
        if 'roles' in me_data and 'super_admin' in me_data['roles']:
            log_test_result("Admin /auth/me Super Admin Rolü", True, 
                           f"Kullanıcı email: {me_data.get('email', 'N/A')}, roles: {me_data['roles']}")
            return True
        else:
            log_test_result("Admin /auth/me Super Admin Rolü", False, 
                           f"super_admin rolü /auth/me response içinde bulunamadı. Response: {json.dumps(me_data, indent=2)}")
            return False
            
    except Exception as e:
        log_test_result("Admin /auth/me", False, f"Exception: {str(e)}")
        return False

def test_admin_all_users(admin_token):
    """Test 3: GET /api/admin/all-users?limit=2 with admin token"""
    print("=== TEST 3: GET /api/admin/all-users Admin Token ile ===")
    
    try:
        headers = {"Authorization": f"Bearer {admin_token}"}
        users_url = f"{API_BASE}/admin/all-users?limit=2"
        response = requests.get(users_url, headers=headers)
        
        if response.status_code != 200:
            log_test_result("Admin /admin/all-users", False, f"Status: {response.status_code}, Response: {response.text}")
            return False
            
        users_data = response.json()
        
        # Verify response is non-empty user list
        if isinstance(users_data, list) and len(users_data) > 0:
            log_test_result("Admin /admin/all-users", True, 
                           f"200 OK response, {len(users_data)} kullanıcı döndü (limit=2)")
            return True
        elif isinstance(users_data, dict) and 'users' in users_data and len(users_data['users']) > 0:
            log_test_result("Admin /admin/all-users", True, 
                           f"200 OK response, {len(users_data['users'])} kullanıcı döndü (limit=2)")
            return True
        else:
            log_test_result("Admin /admin/all-users", False, 
                           f"Boş kullanıcı listesi döndü. Response: {json.dumps(users_data, indent=2)}")
            return False
            
    except Exception as e:
        log_test_result("Admin /admin/all-users", False, f"Exception: {str(e)}")
        return False

def test_agency_login_and_role():
    """Test 4: Agency user login and role verification"""
    print("=== TEST 4: Agency Login + Agency Role Doğrulaması ===")
    
    try:
        # Login request
        login_url = f"{API_BASE}/auth/login"
        response = requests.post(login_url, json=AGENCY_CREDENTIALS)
        
        if response.status_code != 200:
            log_test_result("Agency Login", False, f"Status: {response.status_code}, Response: {response.text}")
            return None
            
        login_data = response.json()
        
        # Verify response structure
        if 'access_token' not in login_data:
            log_test_result("Agency Login", False, "access_token bulunamadı response içinde")
            return None
            
        # Verify user has agency role (agency_admin or similar)
        if 'user' in login_data and 'roles' in login_data['user']:
            user_roles = login_data['user']['roles']
            # Check for any agency-related roles
            agency_roles = [role for role in user_roles if 'agency' in role.lower() or 'agent' in role.lower()]
            if agency_roles:
                log_test_result("Agency Login + Role Doğrulaması", True, 
                               f"Agency rolü doğrulandı: {agency_roles}, access_token uzunluk: {len(login_data['access_token'])} chars")
                return login_data['access_token']
            else:
                # Also accept if user has other valid roles but not super_admin
                if 'super_admin' not in user_roles and len(user_roles) > 0:
                    log_test_result("Agency Login + Role Doğrulaması", True, 
                                   f"Non-admin kullanıcı rolü doğrulandı: {user_roles}, access_token uzunluk: {len(login_data['access_token'])} chars")
                    return login_data['access_token']
                else:
                    log_test_result("Agency Login + Role Doğrulaması", False, 
                                   f"Beklenen agency rolü bulunamadı. Mevcut roller: {user_roles}")
                    return None
        else:
            log_test_result("Agency Login + Role Doğrulaması", False, 
                           "user.roles alanı response içinde bulunamadı")
            return None
            
    except Exception as e:
        log_test_result("Agency Login", False, f"Exception: {str(e)}")
        return None

def test_agency_auth_me(agency_token):
    """Test 5: GET /api/auth/me with agency bearer token"""
    print("=== TEST 5: GET /api/auth/me Agency Bearer Token ile ===")
    
    try:
        headers = {"Authorization": f"Bearer {agency_token}"}
        me_url = f"{API_BASE}/auth/me"
        response = requests.get(me_url, headers=headers)
        
        if response.status_code != 200:
            log_test_result("Agency /auth/me", False, f"Status: {response.status_code}, Response: {response.text}")
            return False
            
        me_data = response.json()
        
        # Verify agency user payload (should not be super_admin)
        if 'roles' in me_data:
            user_roles = me_data['roles']
            if 'super_admin' not in user_roles:
                log_test_result("Agency /auth/me Agency User Payload", True, 
                               f"Agency user doğrulandı. Email: {me_data.get('email', 'N/A')}, roles: {user_roles}")
                return True
            else:
                log_test_result("Agency /auth/me Agency User Payload", False, 
                               f"Agency user super_admin rolüne sahip olmamalı. Roles: {user_roles}")
                return False
        else:
            log_test_result("Agency /auth/me Agency User Payload", False, 
                           f"roles alanı bulunamadı. Response: {json.dumps(me_data, indent=2)}")
            return False
            
    except Exception as e:
        log_test_result("Agency /auth/me", False, f"Exception: {str(e)}")
        return False

def main():
    """Run all auth/RBAC smoke tests"""
    print("🚀 Syroce Backend Auth/RBAC Smoke Doğrulaması Başlatılıyor...")
    print(f"Base URL: {BASE_URL}")
    print("=" * 70)
    
    test_results = []
    
    # Test 1: Admin login + super_admin role verification
    admin_token = test_admin_login_and_role()
    test_results.append(admin_token is not None)
    
    if admin_token:
        # Test 2: Admin /auth/me with bearer token
        admin_me_result = test_admin_auth_me(admin_token)
        test_results.append(admin_me_result)
        
        # Test 3: Admin /admin/all-users endpoint
        admin_users_result = test_admin_all_users(admin_token)
        test_results.append(admin_users_result)
    else:
        print("⚠️  Admin token alınamadı, admin /auth/me ve /admin/all-users testleri atlanıyor\n")
        test_results.extend([False, False])
    
    # Test 4: Agency login + role verification
    agency_token = test_agency_login_and_role()
    test_results.append(agency_token is not None)
    
    if agency_token:
        # Test 5: Agency /auth/me with bearer token  
        agency_me_result = test_agency_auth_me(agency_token)
        test_results.append(agency_me_result)
    else:
        print("⚠️  Agency token alınamadı, agency /auth/me testi atlanıyor\n")
        test_results.append(False)
    
    # Final summary
    print("=" * 70)
    print("📊 TEST SONUÇLARI:")
    print("=" * 70)
    
    test_names = [
        "1) Admin login + super_admin role doğrulaması",
        "2) GET /api/auth/me admin bearer token ile",
        "3) GET /api/admin/all-users admin token ile",
        "4) Agency login + agency role doğrulaması", 
        "5) GET /api/auth/me agency bearer token ile"
    ]
    
    passed_count = sum(test_results)
    total_count = len(test_results)
    
    for i, (test_name, result) in enumerate(zip(test_names, test_results)):
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\n📈 BAŞARI ORANI: {passed_count}/{total_count} ({int(passed_count/total_count*100)}%)")
    
    if passed_count == total_count:
        print("🎉 TÜM TESTLER BAŞARILI! Auth/RBAC smoke doğrulaması tamamlandı.")
        sys.exit(0)
    else:
        print(f"⚠️  {total_count - passed_count} test başarısız. Detayları yukarıda inceleyiniz.")
        sys.exit(1)

if __name__ == "__main__":
    main()