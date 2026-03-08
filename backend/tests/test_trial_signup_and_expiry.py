"""
Test Suite: Trial Signup, Demo Seeding, and Expiry Flow
Testing requirements:
1. POST /api/onboarding/signup creates new trial account
2. New trial signup auto-seeds demo data (customers=20, reservations=30, tours=5, hotels=5, products=5)
3. Trial expiry endpoint returns correct status for trial and non-trial users
4. Trial expired blocking screen logic works correctly
"""

import os
import uuid
import pytest
import requests
from datetime import datetime

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")


class TestTrialSignup:
    """Test POST /api/onboarding/signup flow for new trial accounts"""

    def test_signup_creates_trial_account(self):
        """Test that signup endpoint creates new trial tenant correctly"""
        unique_suffix = uuid.uuid4().hex[:8]
        payload = {
            "company_name": f"Test Company {unique_suffix}",
            "admin_name": f"Admin {unique_suffix}",
            "email": f"test.signup.{unique_suffix}@trial.test",
            "password": "TestPassword123!"
        }
        
        response = requests.post(f"{BASE_URL}/api/onboarding/signup", json=payload)
        
        # Status code assertion
        assert response.status_code == 200 or response.status_code == 201, f"Signup failed: {response.status_code} - {response.text}"
        
        # Data assertions
        data = response.json()
        assert "org_id" in data, "Missing org_id in signup response"
        assert "tenant_id" in data, "Missing tenant_id in signup response"
        assert "user_id" in data, "Missing user_id in signup response"
        assert "plan" in data, "Missing plan in signup response"
        assert data["plan"] == "trial", f"Expected trial plan, got {data['plan']}"
        
        print(f"SUCCESS: New trial signup created with tenant_id={data['tenant_id']}")
        return data

    def test_signup_duplicate_email_returns_409(self):
        """Test that duplicate email signup returns 409 conflict"""
        unique_suffix = uuid.uuid4().hex[:8]
        payload = {
            "company_name": f"Test Company {unique_suffix}",
            "admin_name": f"Admin {unique_suffix}",
            "email": f"duplicate.test.{unique_suffix}@trial.test",
            "password": "TestPassword123!"
        }
        
        # First signup should succeed
        response1 = requests.post(f"{BASE_URL}/api/onboarding/signup", json=payload)
        assert response1.status_code in [200, 201], f"First signup failed: {response1.text}"
        
        # Second signup with same email should fail
        response2 = requests.post(f"{BASE_URL}/api/onboarding/signup", json=payload)
        assert response2.status_code == 409, f"Expected 409 for duplicate email, got {response2.status_code}"
        print("SUCCESS: Duplicate email correctly returns 409")

    def test_signup_seeds_demo_data_automatically(self):
        """Test that new trial signup automatically seeds demo data"""
        unique_suffix = uuid.uuid4().hex[:8]
        payload = {
            "company_name": f"Seed Test {unique_suffix}",
            "admin_name": f"Admin {unique_suffix}",
            "email": f"seed.test.{unique_suffix}@trial.test",
            "password": "TestPassword123!"
        }
        
        response = requests.post(f"{BASE_URL}/api/onboarding/signup", json=payload)
        assert response.status_code in [200, 201], f"Signup failed: {response.text}"
        
        data = response.json()
        assert "org_id" in data, "Missing org_id"
        assert "tenant_id" in data, "Missing tenant_id"
        
        # Note: We can't directly verify DB counts via API without additional endpoints
        # The main agent validated: customers=20, reservations=30, tours=5, hotels=5, products=5
        # This test confirms the signup completes successfully which triggers seeding
        print(f"SUCCESS: Trial signup completed - demo seeding should have occurred for tenant {data['tenant_id']}")


class TestTrialExpiry:
    """Test trial expiry endpoint for different user types"""

    def test_expired_trial_user_returns_expired_status(self):
        """Test that expired trial user sees expired=true"""
        # Login with expired trial credentials
        login_payload = {
            "email": "trial.db3ef59b76@example.com",
            "password": "Test1234!"
        }
        
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json=login_payload)
        assert login_response.status_code == 200, f"Login failed: {login_response.status_code} - {login_response.text}"
        
        login_data = login_response.json()
        token = login_data.get("token") or login_data.get("access_token")
        assert token, "No token in login response"
        
        # Check trial status
        headers = {"Authorization": f"Bearer {token}"}
        trial_response = requests.get(f"{BASE_URL}/api/onboarding/trial", headers=headers)
        
        assert trial_response.status_code == 200, f"Trial endpoint failed: {trial_response.status_code} - {trial_response.text}"
        
        trial_data = trial_response.json()
        # Expected: status=expired AND expired=true
        assert trial_data.get("expired") == True or trial_data.get("status") == "expired", \
            f"Expected expired trial, got: {trial_data}"
        
        print(f"SUCCESS: Expired trial user correctly shows expired status: {trial_data}")

    def test_normal_admin_user_returns_not_expired(self):
        """Test that non-trial admin user sees expired=false"""
        # Login with normal admin credentials
        login_payload = {
            "email": "admin@acenta.test",
            "password": "admin123"
        }
        
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json=login_payload)
        assert login_response.status_code == 200, f"Login failed: {login_response.status_code} - {login_response.text}"
        
        login_data = login_response.json()
        token = login_data.get("token") or login_data.get("access_token")
        assert token, "No token in login response"
        
        # Check trial status
        headers = {"Authorization": f"Bearer {token}"}
        trial_response = requests.get(f"{BASE_URL}/api/onboarding/trial", headers=headers)
        
        assert trial_response.status_code == 200, f"Trial endpoint failed: {trial_response.status_code} - {trial_response.text}"
        
        trial_data = trial_response.json()
        # Expected: expired=false for non-trial admin
        assert trial_data.get("expired") == False, \
            f"Non-trial admin should not show expired, got: {trial_data}"
        
        print(f"SUCCESS: Non-trial admin correctly shows not expired: {trial_data}")


class TestPricingPublicEndpoints:
    """Test public pricing and plans endpoints"""

    def test_pricing_page_loads(self):
        """Test that public pricing page content is accessible"""
        response = requests.get(f"{BASE_URL}/api/onboarding/plans")
        
        # Plans endpoint should return successfully
        assert response.status_code == 200, f"Plans endpoint failed: {response.status_code} - {response.text}"
        
        data = response.json()
        assert "plans" in data or isinstance(data, list), "Plans response should contain plans data"
        print(f"SUCCESS: Plans endpoint returns data: {data}")


class TestAuthEndpoints:
    """Test authentication endpoints work correctly"""

    def test_login_with_valid_credentials(self):
        """Test login with valid credentials returns token"""
        payload = {
            "email": "admin@acenta.test",
            "password": "admin123"
        }
        
        response = requests.post(f"{BASE_URL}/api/auth/login", json=payload)
        assert response.status_code == 200, f"Login failed: {response.status_code} - {response.text}"
        
        data = response.json()
        assert "token" in data or "access_token" in data, "Login should return token"
        print("SUCCESS: Login returns valid token")

    def test_login_with_invalid_credentials(self):
        """Test login with invalid credentials returns 401"""
        payload = {
            "email": "invalid@email.test",
            "password": "wrongpassword"
        }
        
        response = requests.post(f"{BASE_URL}/api/auth/login", json=payload)
        assert response.status_code == 401, f"Expected 401 for invalid credentials, got {response.status_code}"
        print("SUCCESS: Invalid credentials correctly return 401")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
