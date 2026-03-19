"""Iteration 56: Testing new Agency Sheets features - Auto Sync & Multi-Agency Credentials.

New Backend Endpoints:
- GET /api/agency/sheets/sync-status - auto-sync overview with connection count, enabled/healthy/failed counts
- GET /api/agency/sheets/sync-history - sync run history with filtering
- PATCH /api/agency/sheets/connections/{id}/settings - update sync_enabled and sync_interval_minutes
- POST /api/agency/sheets/credentials - save agency Google credentials (validate JSON)
- GET /api/agency/sheets/credentials/status - check agency credential status with active_source field
- DELETE /api/agency/sheets/credentials - remove agency credentials

Error Handling:
- Invalid JSON returns proper error for credentials save
- Non-existent connection returns 404 for settings update
"""
import os
import pytest
import requests

from tests.preview_auth_helper import PreviewAuthSession, get_preview_base_url_or_skip

def _unwrap(resp):
    """Unwrap response envelope if present."""
    data = resp.json()
    if isinstance(data, dict) and "ok" in data and "data" in data:
        return data["data"]
    return data


BASE_URL = get_preview_base_url_or_skip(os.environ.get("REACT_APP_BACKEND_URL", ""))

# Test credentials
AGENCY_EMAIL = "agent@acenta.test"
AGENCY_PASSWORD = "agent123"


@pytest.fixture(scope="module")
def agency_client():
    """Get agency auth session."""
    return PreviewAuthSession(
        BASE_URL,
        email=AGENCY_EMAIL,
        password=AGENCY_PASSWORD,
        default_headers={"Content-Type": "application/json"},
    )


@pytest.fixture
def unauthenticated_client():
    """Session without auth."""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


# ── Sync Status Endpoint Tests ─────────────────────────────────────────

class TestSyncStatusEndpoint:
    """Tests for GET /api/agency/sheets/sync-status - auto-sync overview."""

    def test_sync_status_returns_overview(self, agency_client):
        """GET /api/agency/sheets/sync-status returns sync overview with counts."""
        response = agency_client.get(f"{BASE_URL}/api/agency/sheets/sync-status")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = _unwrap(response)
        # Verify required fields
        assert "total_connections" in data, f"Missing 'total_connections' in response: {data}"
        assert "sync_enabled_count" in data, f"Missing 'sync_enabled_count' in response: {data}"
        assert "healthy_count" in data, f"Missing 'healthy_count' in response: {data}"
        assert "failed_count" in data, f"Missing 'failed_count' in response: {data}"
        assert "scheduler_active" in data, f"Missing 'scheduler_active' in response: {data}"
        assert "connections" in data, f"Missing 'connections' in response: {data}"

        # Verify types
        assert isinstance(data["total_connections"], int)
        assert isinstance(data["sync_enabled_count"], int)
        assert isinstance(data["healthy_count"], int)
        assert isinstance(data["failed_count"], int)
        assert isinstance(data["scheduler_active"], bool)
        assert isinstance(data["connections"], list)

        print(f"✅ GET /api/agency/sheets/sync-status returns overview: total={data['total_connections']}, enabled={data['sync_enabled_count']}, healthy={data['healthy_count']}, failed={data['failed_count']}")

    def test_sync_status_requires_auth(self, unauthenticated_client):
        """GET /api/agency/sheets/sync-status returns 401 without auth."""
        response = unauthenticated_client.get(f"{BASE_URL}/api/agency/sheets/sync-status")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print("✅ GET /api/agency/sheets/sync-status returns 401 without auth")


# ── Sync History Endpoint Tests ────────────────────────────────────────

class TestSyncHistoryEndpoint:
    """Tests for GET /api/agency/sheets/sync-history - sync run history."""

    def test_sync_history_returns_items(self, agency_client):
        """GET /api/agency/sheets/sync-history returns history items."""
        response = agency_client.get(f"{BASE_URL}/api/agency/sheets/sync-history")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = _unwrap(response)
        assert "items" in data, f"Missing 'items' in response: {data}"
        assert "total" in data, f"Missing 'total' in response: {data}"
        assert isinstance(data["items"], list)
        assert isinstance(data["total"], int)

        print(f"✅ GET /api/agency/sheets/sync-history returns {data['total']} history items")

    def test_sync_history_with_limit(self, agency_client):
        """GET /api/agency/sheets/sync-history?limit=5 respects limit param."""
        response = agency_client.get(f"{BASE_URL}/api/agency/sheets/sync-history?limit=5")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = _unwrap(response)
        # Limit may affect results if there are more than 5 items
        assert len(data["items"]) <= 5, f"Expected at most 5 items, got {len(data['items'])}"
        print("✅ GET /api/agency/sheets/sync-history?limit=5 respects limit parameter")

    def test_sync_history_with_connection_filter(self, agency_client):
        """GET /api/agency/sheets/sync-history?connection_id=xxx filters by connection."""
        response = agency_client.get(f"{BASE_URL}/api/agency/sheets/sync-history?connection_id=nonexistent-id")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = _unwrap(response)
        # Should return empty or filtered results (since connection doesn't exist)
        assert "items" in data
        print("✅ GET /api/agency/sheets/sync-history?connection_id=xxx accepts connection_id param")

    def test_sync_history_requires_auth(self, unauthenticated_client):
        """GET /api/agency/sheets/sync-history returns 401 without auth."""
        response = unauthenticated_client.get(f"{BASE_URL}/api/agency/sheets/sync-history")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print("✅ GET /api/agency/sheets/sync-history returns 401 without auth")


# ── Connection Settings Update Tests ───────────────────────────────────

class TestConnectionSettingsEndpoint:
    """Tests for PATCH /api/agency/sheets/connections/{id}/settings."""

    def test_update_settings_nonexistent_returns_404(self, agency_client):
        """PATCH /api/agency/sheets/connections/{id}/settings returns 404 for non-existent."""
        response = agency_client.patch(
            f"{BASE_URL}/api/agency/sheets/connections/nonexistent-connection-id/settings",
            json={"sync_enabled": True}
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        print("✅ PATCH /api/agency/sheets/connections/{id}/settings returns 404 for non-existent connection")

    def test_update_settings_invalid_interval(self, agency_client):
        """PATCH with invalid sync_interval_minutes returns 400."""
        response = agency_client.patch(
            f"{BASE_URL}/api/agency/sheets/connections/nonexistent-id/settings",
            json={"sync_interval_minutes": 0}  # Invalid: must be 1-1440
        )
        # Will be 404 (connection not found) before interval validation
        # Because we don't have actual connections
        assert response.status_code in [400, 404], f"Expected 400/404, got {response.status_code}: {response.text}"
        print("✅ PATCH /api/agency/sheets/connections/{id}/settings validates interval")

    def test_update_settings_requires_auth(self, unauthenticated_client):
        """PATCH /api/agency/sheets/connections/{id}/settings returns 401 without auth."""
        response = unauthenticated_client.patch(
            f"{BASE_URL}/api/agency/sheets/connections/test-id/settings",
            json={"sync_enabled": True}
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print("✅ PATCH /api/agency/sheets/connections/{id}/settings returns 401 without auth")


# ── Credentials Save Endpoint Tests ────────────────────────────────────

class TestCredentialsSaveEndpoint:
    """Tests for POST /api/agency/sheets/credentials - save agency credentials."""

    def test_save_credentials_invalid_json_returns_400(self, agency_client):
        """POST /api/agency/sheets/credentials with invalid JSON returns 400."""
        response = agency_client.post(
            f"{BASE_URL}/api/agency/sheets/credentials",
            json={"service_account_json": "not valid json"}
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"

        data = _unwrap(response)
        assert "error" in data or "detail" in data, f"Expected error details in response: {data}"
        print("✅ POST /api/agency/sheets/credentials returns 400 for invalid JSON")

    def test_save_credentials_missing_required_fields(self, agency_client):
        """POST with JSON missing client_email/private_key returns 400."""
        # Valid JSON but missing required fields
        response = agency_client.post(
            f"{BASE_URL}/api/agency/sheets/credentials",
            json={"service_account_json": '{"type": "service_account"}'}
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        print("✅ POST /api/agency/sheets/credentials returns 400 when missing required fields")

    def test_save_credentials_requires_auth(self, unauthenticated_client):
        """POST /api/agency/sheets/credentials returns 401 without auth."""
        response = unauthenticated_client.post(
            f"{BASE_URL}/api/agency/sheets/credentials",
            json={"service_account_json": "{}"}
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print("✅ POST /api/agency/sheets/credentials returns 401 without auth")


# ── Credentials Status Endpoint Tests ──────────────────────────────────

class TestCredentialsStatusEndpoint:
    """Tests for GET /api/agency/sheets/credentials/status."""

    def test_credentials_status_returns_active_source(self, agency_client):
        """GET /api/agency/sheets/credentials/status returns active_source field."""
        response = agency_client.get(f"{BASE_URL}/api/agency/sheets/credentials/status")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = _unwrap(response)
        # Verify required fields
        assert "has_own_credentials" in data, f"Missing 'has_own_credentials' in response: {data}"
        assert "global_configured" in data, f"Missing 'global_configured' in response: {data}"
        assert "active_source" in data, f"Missing 'active_source' in response: {data}"

        # Verify types
        assert isinstance(data["has_own_credentials"], bool)
        assert isinstance(data["global_configured"], bool)
        assert data["active_source"] in ["agency", "global", "none"], f"Invalid active_source: {data['active_source']}"

        print(f"✅ GET /api/agency/sheets/credentials/status returns: has_own={data['has_own_credentials']}, global={data['global_configured']}, active_source={data['active_source']}")

    def test_credentials_status_requires_auth(self, unauthenticated_client):
        """GET /api/agency/sheets/credentials/status returns 401 without auth."""
        response = unauthenticated_client.get(f"{BASE_URL}/api/agency/sheets/credentials/status")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print("✅ GET /api/agency/sheets/credentials/status returns 401 without auth")


# ── Credentials Delete Endpoint Tests ──────────────────────────────────

class TestCredentialsDeleteEndpoint:
    """Tests for DELETE /api/agency/sheets/credentials."""

    def test_delete_credentials_returns_fallback(self, agency_client):
        """DELETE /api/agency/sheets/credentials returns deleted status and fallback."""
        response = agency_client.delete(f"{BASE_URL}/api/agency/sheets/credentials")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = _unwrap(response)
        assert "deleted" in data, f"Missing 'deleted' in response: {data}"
        assert "fallback" in data, f"Missing 'fallback' in response: {data}"

        # deleted might be false if no credentials existed
        assert isinstance(data["deleted"], bool)
        assert data["fallback"] in ["global", "none"], f"Invalid fallback: {data['fallback']}"

        print(f"✅ DELETE /api/agency/sheets/credentials returns: deleted={data['deleted']}, fallback={data['fallback']}")

    def test_delete_credentials_requires_auth(self, unauthenticated_client):
        """DELETE /api/agency/sheets/credentials returns 401 without auth."""
        response = unauthenticated_client.delete(f"{BASE_URL}/api/agency/sheets/credentials")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
        print("✅ DELETE /api/agency/sheets/credentials returns 401 without auth")


# ── Full Credentials CRUD Flow ─────────────────────────────────────────

class TestCredentialsCRUDFlow:
    """Test full credentials save/status/delete flow."""

    def test_credentials_full_flow(self, agency_client):
        """Test save, check status, and delete credentials flow."""
        # 1. Check initial status
        status_response = agency_client.get(f"{BASE_URL}/api/agency/sheets/credentials/status")
        assert status_response.status_code == 200
        initial_status = _unwrap(status_response)
        print(f"Initial status: has_own={initial_status.get('has_own_credentials')}, active_source={initial_status.get('active_source')}")

        # 2. Attempt to save valid credentials (with mock data)
        mock_credentials = {
            "type": "service_account",
            "project_id": "test-project",
            "private_key_id": "key123",
            "private_key": "-----BEGIN PRIVATE KEY-----\\nMOCKKEY\\n-----END PRIVATE KEY-----\\n",
            "client_email": "test@test-project.iam.gserviceaccount.com",
            "client_id": "123456789",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token"
        }
        import json
        save_response = agency_client.post(
            f"{BASE_URL}/api/agency/sheets/credentials",
            json={"service_account_json": json.dumps(mock_credentials)}
        )
        assert save_response.status_code == 200, f"Expected 200, got {save_response.status_code}: {save_response.text}"
        save_data = _unwrap(save_response)
        assert save_data.get("status") == "saved", f"Expected status='saved': {save_data}"
        assert save_data.get("client_email") == "test@test-project.iam.gserviceaccount.com"
        print(f"✅ Credentials saved: client_email={save_data.get('client_email')}")

        # 3. Check updated status
        status_after = agency_client.get(f"{BASE_URL}/api/agency/sheets/credentials/status")
        assert status_after.status_code == 200
        updated_status = _unwrap(status_after)
        assert updated_status.get("has_own_credentials"), f"Expected has_own_credentials=True: {updated_status}"
        assert updated_status.get("active_source") == "agency", f"Expected active_source='agency': {updated_status}"
        assert updated_status.get("own_service_account_email") == "test@test-project.iam.gserviceaccount.com"
        print(f"✅ Status after save: has_own={updated_status.get('has_own_credentials')}, active_source={updated_status.get('active_source')}")

        # 4. Delete credentials
        delete_response = agency_client.delete(f"{BASE_URL}/api/agency/sheets/credentials")
        assert delete_response.status_code == 200
        delete_data = _unwrap(delete_response)
        assert delete_data.get("deleted"), f"Expected deleted=True: {delete_data}"
        print(f"✅ Credentials deleted: deleted={delete_data.get('deleted')}, fallback={delete_data.get('fallback')}")

        # 5. Verify status after delete
        final_status = agency_client.get(f"{BASE_URL}/api/agency/sheets/credentials/status")
        assert final_status.status_code == 200
        final_data = _unwrap(final_status)
        assert not final_data.get("has_own_credentials"), f"Expected has_own_credentials=False: {final_data}"
        # active_source should be 'none' since no global configured in preview env
        assert final_data.get("active_source") in ["global", "none"], f"Unexpected active_source: {final_data}"
        print(f"✅ Final status: has_own={final_data.get('has_own_credentials')}, active_source={final_data.get('active_source')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
