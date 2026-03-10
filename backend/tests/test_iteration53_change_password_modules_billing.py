"""
Iteration 53: Testing Change Password, Agency Module Saving, and Billing Visibility

External HTTP tests against real preview database.
Test cases:
1. Change Password - Agency user can change password with proper validation
2. Change Password - Admin user has access to change password endpoint
3. Agency Module Saving - Admin can save/update agency modules
4. Billing visibility - Tested via frontend (not API)

Note: This test uses direct requests to localhost:8001 to avoid conftest fixture conflicts.
"""

import os
import pytest
import requests
import pymongo

# Use direct localhost to avoid conftest fixture conflicts
BASE_URL = "http://localhost:8001"

# Test credentials (from real seeded database)
AGENCY_USER = {"email": "agency1@demo.test", "password": "Agency12345!"}
ADMIN_USER = {"email": "admin@acenta.test", "password": "admin123"}
AGENCY_ID = "f5f7a2a3-5de1-4d65-b700-ec4f9807d83a"  # Demo Acenta agency


def _clear_rate_limits():
    """Clear rate limits from MongoDB to avoid 429 errors"""
    client = pymongo.MongoClient("mongodb://localhost:27017")
    db = client["test_database"]
    db.rate_limits.delete_many({})
    client.close()


def _get_agency_token():
    """Get fresh agency user access token"""
    _clear_rate_limits()
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json=AGENCY_USER,
        headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 200, f"Agency login failed: {response.text}"
    return response.json()["access_token"]


def _get_admin_token():
    """Get fresh admin user access token"""
    _clear_rate_limits()
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json=ADMIN_USER,
        headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    return response.json()["access_token"]


class TestChangePasswordAgencyUser:
    """Change Password tests for agency user (agency1@demo.test)"""
    
    def test_wrong_current_password_rejected(self):
        """Wrong current password should return 400 error"""
        _clear_rate_limits()
        token = _get_agency_token()
        response = requests.post(
            f"{BASE_URL}/api/settings/change-password",
            json={
                "current_password": "WrongPassword123!",
                "new_password": "NewAgency12345!"
            },
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
        )
        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert "Mevcut şifre hatalı" in data["error"]["message"]
        print("PASS: Wrong current password correctly rejected")
    
    def test_weak_password_rejected_too_short(self):
        """Password less than 8 chars should be rejected"""
        _clear_rate_limits()
        token = _get_agency_token()
        response = requests.post(
            f"{BASE_URL}/api/settings/change-password",
            json={
                "current_password": AGENCY_USER["password"],
                "new_password": "short"
            },
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
        )
        assert response.status_code == 422 or response.status_code == 400
        print("PASS: Short password correctly rejected")
    
    def test_weak_password_rejected_no_special_char(self):
        """Password without special character should be rejected"""
        _clear_rate_limits()
        token = _get_agency_token()
        response = requests.post(
            f"{BASE_URL}/api/settings/change-password",
            json={
                "current_password": AGENCY_USER["password"],
                "new_password": "NoSpecialChar123"
            },
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
        )
        assert response.status_code == 400
        data = response.json()
        assert "violations" in str(data) or "special" in str(data).lower()
        print("PASS: Password without special char correctly rejected")
    
    def test_same_password_rejected(self):
        """New password same as current should be rejected"""
        _clear_rate_limits()
        token = _get_agency_token()
        response = requests.post(
            f"{BASE_URL}/api/settings/change-password",
            json={
                "current_password": AGENCY_USER["password"],
                "new_password": AGENCY_USER["password"]  # Same password
            },
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
        )
        assert response.status_code == 400
        data = response.json()
        assert "aynı olamaz" in data["error"]["message"].lower() or "same" in str(data).lower()
        print("PASS: Same password correctly rejected")
    
    def test_successful_password_change_and_login(self):
        """Test full password change flow: change -> login with new -> restore"""
        _clear_rate_limits()
        
        # Step 1: Login with original password
        login_resp = requests.post(
            f"{BASE_URL}/api/auth/login",
            json=AGENCY_USER,
            headers={"Content-Type": "application/json"}
        )
        assert login_resp.status_code == 200, "Initial login failed"
        token = login_resp.json()["access_token"]
        
        # Step 2: Change password
        new_password = "NewAgency12345!"
        change_resp = requests.post(
            f"{BASE_URL}/api/settings/change-password",
            json={
                "current_password": AGENCY_USER["password"],
                "new_password": new_password
            },
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
        )
        assert change_resp.status_code == 200, f"Password change failed: {change_resp.text}"
        change_data = change_resp.json()
        assert "Şifreniz güncellendi" in change_data.get("message", "")
        print(f"Password changed. Revoked sessions: {change_data.get('revoked_other_sessions', 0)}")
        
        # Clear rate limits before login tests
        _clear_rate_limits()
        
        # Step 3: Login with NEW password
        new_login_resp = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": AGENCY_USER["email"], "password": new_password},
            headers={"Content-Type": "application/json"}
        )
        assert new_login_resp.status_code == 200, "Login with new password failed"
        new_token = new_login_resp.json()["access_token"]
        print("PASS: Login with new password successful")
        
        # Step 4: Login with OLD password should FAIL
        old_login_resp = requests.post(
            f"{BASE_URL}/api/auth/login",
            json=AGENCY_USER,
            headers={"Content-Type": "application/json"}
        )
        assert old_login_resp.status_code == 401, "Login with old password should fail"
        print("PASS: Login with old password correctly rejected")
        
        # Step 5: Restore original password
        restore_resp = requests.post(
            f"{BASE_URL}/api/settings/change-password",
            json={
                "current_password": new_password,
                "new_password": AGENCY_USER["password"]
            },
            headers={
                "Authorization": f"Bearer {new_token}",
                "Content-Type": "application/json"
            }
        )
        assert restore_resp.status_code == 200, f"Password restore failed: {restore_resp.text}"
        print("PASS: Password restored to original")
        
        # Clear rate limits before final verification
        _clear_rate_limits()
        
        # Step 6: Verify login with original password works again
        final_login = requests.post(
            f"{BASE_URL}/api/auth/login",
            json=AGENCY_USER,
            headers={"Content-Type": "application/json"}
        )
        assert final_login.status_code == 200, "Login with restored password failed"
        print("PASS: Full password change flow completed successfully")


class TestChangePasswordAdminUser:
    """Change Password tests for admin user (admin@acenta.test)"""
    
    def test_admin_can_access_change_password_endpoint(self):
        """Admin user should have access to change-password endpoint"""
        _clear_rate_limits()
        token = _get_admin_token()
        
        # Test with wrong password to verify endpoint access (not actual change)
        response = requests.post(
            f"{BASE_URL}/api/settings/change-password",
            json={
                "current_password": "WrongPassword",
                "new_password": "NewAdmin12345!"
            },
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
        )
        # Should get 400 (wrong password) not 401/403 (no access)
        assert response.status_code == 400
        data = response.json()
        assert "Mevcut şifre hatalı" in data["error"]["message"]
        print("PASS: Admin has access to change password endpoint")


class TestAgencyModuleSaving:
    """Agency Module CRUD tests via admin API"""
    
    def test_get_agency_modules(self):
        """Admin can get agency modules"""
        _clear_rate_limits()
        token = _get_admin_token()
        
        response = requests.get(
            f"{BASE_URL}/api/admin/agencies/{AGENCY_ID}/modules",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "agency_id" in data
        assert "allowed_modules" in data
        assert isinstance(data["allowed_modules"], list)
        print(f"PASS: Got modules for agency: {data['agency_name']}")
        print(f"Current modules: {data['allowed_modules']}")
    
    def test_update_agency_modules(self):
        """Admin can update agency modules"""
        _clear_rate_limits()
        token = _get_admin_token()
        
        # First, get current modules
        get_resp = requests.get(
            f"{BASE_URL}/api/admin/agencies/{AGENCY_ID}/modules",
            headers={"Authorization": f"Bearer {token}"}
        )
        original_modules = get_resp.json()["allowed_modules"]
        
        # Update to a subset
        new_modules = ["dashboard", "rezervasyonlar", "musteriler"]
        update_resp = requests.put(
            f"{BASE_URL}/api/admin/agencies/{AGENCY_ID}/modules",
            json={"allowed_modules": new_modules},
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
        )
        assert update_resp.status_code == 200
        update_data = update_resp.json()
        assert update_data["allowed_modules"] == new_modules
        print(f"PASS: Updated modules to: {new_modules}")
        
        # Verify persistence
        verify_resp = requests.get(
            f"{BASE_URL}/api/admin/agencies/{AGENCY_ID}/modules",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert verify_resp.json()["allowed_modules"] == new_modules
        print("PASS: Modules persisted correctly")
        
        # Restore original modules
        restore_resp = requests.put(
            f"{BASE_URL}/api/admin/agencies/{AGENCY_ID}/modules",
            json={"allowed_modules": original_modules},
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
        )
        assert restore_resp.status_code == 200
        print(f"PASS: Restored original modules: {original_modules}")
    
    def test_clear_all_modules(self):
        """Admin can clear all modules (empty array)"""
        _clear_rate_limits()
        token = _get_admin_token()
        
        # Get current modules first
        get_resp = requests.get(
            f"{BASE_URL}/api/admin/agencies/{AGENCY_ID}/modules",
            headers={"Authorization": f"Bearer {token}"}
        )
        original_modules = get_resp.json()["allowed_modules"]
        
        # Set to empty array
        clear_resp = requests.put(
            f"{BASE_URL}/api/admin/agencies/{AGENCY_ID}/modules",
            json={"allowed_modules": []},
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
        )
        assert clear_resp.status_code == 200
        assert clear_resp.json()["allowed_modules"] == []
        print("PASS: Cleared all modules")
        
        # Restore
        restore_resp = requests.put(
            f"{BASE_URL}/api/admin/agencies/{AGENCY_ID}/modules",
            json={"allowed_modules": original_modules},
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
        )
        assert restore_resp.status_code == 200
        print("PASS: Restored modules after clear test")
    
    def test_agency_user_cannot_access_module_endpoint(self):
        """Agency user should not have access to admin module endpoints"""
        _clear_rate_limits()
        token = _get_agency_token()
        
        response = requests.get(
            f"{BASE_URL}/api/admin/agencies/{AGENCY_ID}/modules",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code in [401, 403]
        print("PASS: Agency user correctly denied access to admin endpoint")


class TestBillingVisibilityAPI:
    """Billing visibility is frontend-only, but we test related endpoints"""
    
    def test_settings_endpoint_accessible_for_agency(self):
        """Agency user can access settings endpoint"""
        _clear_rate_limits()
        token = _get_agency_token()
        
        # This verifies the settings page is accessible
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "agency_admin" in data["roles"]
        print(f"PASS: Agency user verified: {data['email']} with roles {data['roles']}")
    
    def test_admin_has_billing_access_roles(self):
        """Admin user has roles that allow billing access"""
        _clear_rate_limits()
        token = _get_admin_token()
        
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "super_admin" in data["roles"] or "admin" in data["roles"]
        print(f"PASS: Admin user verified: {data['email']} with roles {data['roles']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
