"""Iteration 47: Test Google Sheets Integration - Admin Page & Agency Hotels
Tests:
- Admin login and /app/admin/google-sheets alias route → /app/admin/portfolio-sync
- Admin Portfolio Sync page APIs: config, connections, sync
- Agency login and hotels page with sheet-related fields
- Missing credential handling (not_configured behavior)
"""
from __future__ import annotations

import os
import sys
import pytest

# Add backend root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from tests.preview_auth_helper import PreviewAuthSession, get_preview_base_url_or_skip


def _unwrap(resp):
    """Unwrap response envelope if present."""
    data = resp.json()
    if isinstance(data, dict) and "ok" in data and "data" in data:
        return data["data"]
    return data



BASE_URL = get_preview_base_url_or_skip("")

# Admin credentials
ADMIN_EMAIL = "admin@acenta.test"
ADMIN_PASS = "admin123"

# Agency credentials
AGENCY_EMAIL = "agent@acenta.test"
AGENCY_PASS = "agent123"


class TestAdminSheetsConfig:
    """Test admin sheets config endpoint"""

    @pytest.fixture(scope="class")
    def admin_session(self):
        return PreviewAuthSession(
            BASE_URL,
            email=ADMIN_EMAIL,
            password=ADMIN_PASS,
        )

    def test_sheets_config_returns_200(self, admin_session):
        """GET /api/admin/sheets/config should return 200"""
        response = admin_session.get("/api/admin/sheets/config")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = _unwrap(response)
        # Should have configured key
        assert "configured" in data
        # When not configured, should return False gracefully
        print(f"Config: configured={data.get('configured')}, service_account_email={data.get('service_account_email')}")

    def test_sheets_config_has_required_fields(self, admin_session):
        """Config should include required_service_account_fields"""
        response = admin_session.get("/api/admin/sheets/config")
        assert response.status_code == 200
        data = _unwrap(response)
        # Should have required fields for service account setup
        assert "required_service_account_fields" in data or "message" in data


class TestAdminSheetsConnections:
    """Test admin sheets connections endpoint"""

    @pytest.fixture(scope="class")
    def admin_session(self):
        return PreviewAuthSession(
            BASE_URL,
            email=ADMIN_EMAIL,
            password=ADMIN_PASS,
        )

    def test_connections_returns_200(self, admin_session):
        """GET /api/admin/sheets/connections should return 200"""
        response = admin_session.get("/api/admin/sheets/connections")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = _unwrap(response)
        assert isinstance(data, list), "Connections should be a list"
        print(f"Found {len(data)} sheet connections")

    def test_connections_have_required_fields(self, admin_session):
        """Each connection should have required fields"""
        response = admin_session.get("/api/admin/sheets/connections")
        assert response.status_code == 200
        connections = _unwrap(response)
        if connections:
            conn = connections[0]
            # Required fields for connection
            expected_fields = ["hotel_id", "sheet_id"]
            for field in expected_fields:
                assert field in conn, f"Connection missing field: {field}"


class TestAdminSheetsStatus:
    """Test admin sheets status (health dashboard)"""

    @pytest.fixture(scope="class")
    def admin_session(self):
        return PreviewAuthSession(
            BASE_URL,
            email=ADMIN_EMAIL,
            password=ADMIN_PASS,
        )

    def test_status_returns_200(self, admin_session):
        """GET /api/admin/sheets/status should return 200"""
        response = admin_session.get("/api/admin/sheets/status")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = _unwrap(response)
        # Should have dashboard stats
        assert "configured" in data
        print(f"Status: total={data.get('total')}, enabled={data.get('enabled')}, healthy={data.get('healthy')}")


class TestAdminSheetsSyncNotConfigured:
    """Test manual sync when Google credentials not configured"""

    @pytest.fixture(scope="class")
    def admin_session(self):
        return PreviewAuthSession(
            BASE_URL,
            email=ADMIN_EMAIL,
            password=ADMIN_PASS,
        )

    def test_sync_without_credentials_returns_not_configured(self, admin_session):
        """POST /api/admin/sheets/sync/{hotel_id} should return not_configured when no credentials"""
        # First get a connection
        response = admin_session.get("/api/admin/sheets/connections")
        assert response.status_code == 200
        connections = _unwrap(response)

        if not connections:
            pytest.skip("No sheet connections to test sync")

        hotel_id = connections[0]["hotel_id"]

        # Try to sync
        sync_response = admin_session.post(f"/api/admin/sheets/sync/{hotel_id}")
        assert sync_response.status_code == 200, f"Expected 200, got {sync_response.status_code}: {sync_response.text}"

        sync_data = _unwrap(sync_response)
        # Should gracefully return not_configured status
        if not sync_data.get("configured", True):
            assert sync_data.get("status") == "not_configured", "Expected not_configured status"
            print(f"Sync correctly returned not_configured: {sync_data.get('message')}")
        else:
            # If configured, check other status
            print(f"Sync status: {sync_data.get('status')}")


class TestAdminSheetsTemplates:
    """Test sheet templates endpoint"""

    @pytest.fixture(scope="class")
    def admin_session(self):
        return PreviewAuthSession(
            BASE_URL,
            email=ADMIN_EMAIL,
            password=ADMIN_PASS,
        )

    def test_templates_returns_200(self, admin_session):
        """GET /api/admin/sheets/templates should return 200"""
        response = admin_session.get("/api/admin/sheets/templates")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = _unwrap(response)
        # Should have checklist and downloadable_templates
        assert "checklist" in data or "downloadable_templates" in data
        print(f"Templates: checklist items={len(data.get('checklist', []))}")


class TestAdminSheetsWritebackStats:
    """Test writeback stats endpoint"""

    @pytest.fixture(scope="class")
    def admin_session(self):
        return PreviewAuthSession(
            BASE_URL,
            email=ADMIN_EMAIL,
            password=ADMIN_PASS,
        )

    def test_writeback_stats_returns_200(self, admin_session):
        """GET /api/admin/sheets/writeback/stats should return 200"""
        response = admin_session.get("/api/admin/sheets/writeback/stats")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = _unwrap(response)
        # Should have stats fields
        assert "configured" in data
        print(f"Writeback stats: queued={data.get('queued')}, completed={data.get('completed')}")


class TestAdminSheetsRuns:
    """Test sync runs history endpoint"""

    @pytest.fixture(scope="class")
    def admin_session(self):
        return PreviewAuthSession(
            BASE_URL,
            email=ADMIN_EMAIL,
            password=ADMIN_PASS,
        )

    def test_runs_returns_200(self, admin_session):
        """GET /api/admin/sheets/runs should return 200"""
        response = admin_session.get("/api/admin/sheets/runs")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = _unwrap(response)
        assert isinstance(data, list), "Runs should be a list"
        print(f"Found {len(data)} sync runs")


class TestAdminSheetsAvailableHotels:
    """Test available hotels for connect wizard"""

    @pytest.fixture(scope="class")
    def admin_session(self):
        return PreviewAuthSession(
            BASE_URL,
            email=ADMIN_EMAIL,
            password=ADMIN_PASS,
        )

    def test_available_hotels_returns_200(self, admin_session):
        """GET /api/admin/sheets/available-hotels should return 200"""
        response = admin_session.get("/api/admin/sheets/available-hotels")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = _unwrap(response)
        assert isinstance(data, list), "Available hotels should be a list"
        print(f"Found {len(data)} available hotels")
        if data:
            hotel = data[0]
            assert "_id" in hotel
            assert "name" in hotel


class TestAgencyHotels:
    """Test agency hotels endpoint with sheet-related fields"""

    @pytest.fixture(scope="class")
    def agency_session(self):
        return PreviewAuthSession(
            BASE_URL,
            email=AGENCY_EMAIL,
            password=AGENCY_PASS,
        )

    def test_agency_hotels_returns_200(self, agency_session):
        """GET /api/agency/hotels should return 200"""
        response = agency_session.get("/api/agency/hotels")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = _unwrap(response)
        # Can be list or dict with items
        if isinstance(data, dict):
            items = data.get("items", [])
        else:
            items = data
        print(f"Agency has {len(items)} hotels")

    def test_agency_hotels_have_sheet_fields(self, agency_session):
        """Agency hotels should include sheet-related fields"""
        response = agency_session.get("/api/agency/hotels")
        assert response.status_code == 200
        data = _unwrap(response)

        if isinstance(data, dict):
            items = data.get("items", [])
        else:
            items = data

        if not items:
            pytest.skip("No hotels for agency")

        hotel = items[0]
        # Check sheet-related fields exist (may be null)
        sheet_fields = [
            "sheet_managed_inventory",
            "allocation_available",
        ]
        for field in sheet_fields:
            assert field in hotel, f"Hotel missing sheet field: {field}"

        print(f"Hotel {hotel.get('hotel_name')} - sheet_managed_inventory={hotel.get('sheet_managed_inventory')}")

    def test_agency_hotels_have_status_fields(self, agency_session):
        """Agency hotels should include status fields"""
        response = agency_session.get("/api/agency/hotels")
        assert response.status_code == 200
        data = _unwrap(response)

        if isinstance(data, dict):
            items = data.get("items", [])
        else:
            items = data

        if not items:
            pytest.skip("No hotels for agency")

        hotel = items[0]
        # Check status fields
        assert "status_label" in hotel
        assert "hotel_id" in hotel
        assert "hotel_name" in hotel
        print(f"Hotel {hotel.get('hotel_name')} status: {hotel.get('status_label')}")


class TestAdminAgencyConnections:
    """Test agency-specific sheet connections"""

    @pytest.fixture(scope="class")
    def admin_session(self):
        return PreviewAuthSession(
            BASE_URL,
            email=ADMIN_EMAIL,
            password=ADMIN_PASS,
        )

    def test_agency_connections_returns_200(self, admin_session):
        """GET /api/admin/sheets/agency-connections should return 200"""
        response = admin_session.get("/api/admin/sheets/agency-connections")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = _unwrap(response)
        assert isinstance(data, list), "Agency connections should be a list"
        print(f"Found {len(data)} agency-specific connections")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
