"""
Test configuration and fixtures for P0.3 FX & Ledger tests
"""
import pytest
import httpx
from typing import AsyncGenerator

# Use production URL from frontend/.env
BASE_URL = "https://commerce-os.preview.emergentagent.com"

@pytest.fixture
async def async_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """Async HTTP client for testing"""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        yield client

@pytest.fixture
async def admin_token(async_client: httpx.AsyncClient) -> str:
    """Login as admin and return access token"""
    response = await async_client.post(
        "/api/auth/login",
        json={"email": "admin@acenta.test", "password": "admin123"}
    )
    assert response.status_code == 200, f"Admin login failed: {response.text}"
    data = response.json()
    return data["access_token"]

@pytest.fixture
async def agency_token(async_client: httpx.AsyncClient) -> str:
    """Login as agency user and return access token"""
    response = await async_client.post(
        "/api/auth/login", 
        json={"email": "agency1@demo.test", "password": "agency123"}
    )
    assert response.status_code == 200, f"Agency login failed: {response.text}"
    data = response.json()
    return data["access_token"]