"""
Iteration 48 - Bulk Sheet Connections Tests
Tests for toplu otel/acenta bağlantısı feature:
- Bulk template download for hotel and agency
- Bulk preview-text endpoint for hotel and agency
- Bulk preview-upload endpoint (CSV/XLSX)
- Bulk preview-master-sheet endpoint (graceful when not configured)
- Bulk execute endpoint with cleanup
"""
from __future__ import annotations

import io
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from tests.preview_auth_helper import PreviewAuthSession, get_preview_base_url_or_skip


def _unwrap(resp):
    """Unwrap response envelope if present."""
    data = resp.json()
    if isinstance(data, dict) and "ok" in data and "data" in data:
        return data["data"]
    return data




BASE_URL = get_preview_base_url_or_skip("")
ADMIN_EMAIL = "admin@acenta.test"
ADMIN_PASS = "admin123"


def _pick_available_hotel(admin_session: PreviewAuthSession) -> dict:
    response = admin_session.get("/api/admin/sheets/available-hotels")
    assert response.status_code == 200, response.text
    hotels = _unwrap(response)
    available = [hotel for hotel in hotels if not hotel.get("connected")]
    if not available:
        pytest.skip("Bulk test için baglanabilir otel kalmadi")
    return available[0]


def _pick_available_agency(admin_session: PreviewAuthSession, hotel_id: str) -> dict:
    response = admin_session.get(f"/api/admin/sheets/agencies-for-hotel/{hotel_id}")
    assert response.status_code == 200, response.text
    agencies = _unwrap(response)
    available = [agency for agency in agencies if not agency.get("connected")]
    if not available:
        pytest.skip("Bulk test için baglanabilir acenta kalmadi")
    return available[0]


class TestBulkSheetConnectionsIteration48:
    """Tests for bulk sheet connection feature (Iteration 48)"""

    @pytest.fixture(scope="class")
    def admin_session(self):
        return PreviewAuthSession(
            BASE_URL,
            email=ADMIN_EMAIL,
            password=ADMIN_PASS,
        )

    # ── Template Download Tests ──────────────────────────────────────

    def test_bulk_template_download_hotel(self, admin_session):
        """GET /api/admin/sheets/bulk-template/hotel returns CSV template"""
        response = admin_session.get("/api/admin/sheets/bulk-template/hotel")
        assert response.status_code == 200, response.text
        assert "text/csv" in response.headers.get("content-type", "")
        content = response.text
        assert "hotel_id" in content
        assert "sheet_id" in content
        assert "sheet_tab" in content
        assert "writeback_tab" in content
        assert "sync_enabled" in content
        assert "sync_interval_minutes" in content

    def test_bulk_template_download_agency(self, admin_session):
        """GET /api/admin/sheets/bulk-template/agency returns CSV template with agency_id"""
        response = admin_session.get("/api/admin/sheets/bulk-template/agency")
        assert response.status_code == 200, response.text
        assert "text/csv" in response.headers.get("content-type", "")
        content = response.text
        assert "hotel_id" in content
        assert "agency_id" in content  # Agency-specific column
        assert "sheet_id" in content

    # ── Preview Text Tests ───────────────────────────────────────────

    def test_bulk_preview_text_for_hotel_connections(self, admin_session):
        """POST /api/admin/sheets/bulk/preview-text validates hotel rows from pasted text"""
        hotel = _pick_available_hotel(admin_session)
        response = admin_session.post(
            "/api/admin/sheets/bulk/preview-text",
            json={
                "scope": "hotel",
                "raw_text": (
                    "hotel_id\tsheet_id\tsheet_tab\twriteback_tab\tsync_enabled\tsync_interval_minutes\n"
                    f"{hotel['_id']}\tbulk-preview-{hotel['_id'][:6]}\tSheet1\tRezervasyonlar\ttrue\t5"
                ),
            },
        )
        assert response.status_code == 200, response.text
        data = _unwrap(response)
        assert data["scope"] == "hotel"
        assert data["source"] == "paste"
        assert data["summary"]["valid_rows"] == 1
        assert data["summary"]["invalid_rows"] == 0
        assert len(data["valid_rows"]) == 1
        assert data["valid_rows"][0]["hotel_id"] == hotel["_id"]

    def test_bulk_preview_text_for_agency_connections(self, admin_session):
        """POST /api/admin/sheets/bulk/preview-text validates agency rows from pasted text"""
        hotel = _pick_available_hotel(admin_session)
        agency = _pick_available_agency(admin_session, hotel["_id"])
        response = admin_session.post(
            "/api/admin/sheets/bulk/preview-text",
            json={
                "scope": "agency",
                "raw_text": (
                    "hotel_id\tagency_id\tsheet_id\tsheet_tab\twriteback_tab\tsync_enabled\tsync_interval_minutes\n"
                    f"{hotel['_id']}\t{agency['_id']}\tagency-preview-{hotel['_id'][:4]}\tSheet1\tRezervasyonlar\ttrue\t5"
                ),
            },
        )
        assert response.status_code == 200, response.text
        data = _unwrap(response)
        assert data["scope"] == "agency"
        assert data["summary"]["valid_rows"] == 1
        assert data["summary"]["invalid_rows"] == 0
        assert data["valid_rows"][0]["agency_id"] == agency["_id"]

    def test_bulk_preview_text_invalid_hotel_id(self, admin_session):
        """POST /api/admin/sheets/bulk/preview-text shows invalid row when hotel_id doesn't exist"""
        response = admin_session.post(
            "/api/admin/sheets/bulk/preview-text",
            json={
                "scope": "hotel",
                "raw_text": (
                    "hotel_id\tsheet_id\tsheet_tab\twriteback_tab\tsync_enabled\tsync_interval_minutes\n"
                    "fake-hotel-does-not-exist\tsheet-abc\tSheet1\tRezervasyonlar\ttrue\t5"
                ),
            },
        )
        assert response.status_code == 200, response.text
        data = _unwrap(response)
        assert data["summary"]["valid_rows"] == 0
        assert data["summary"]["invalid_rows"] == 1
        assert len(data["invalid_rows"]) == 1
        # Check error message exists
        errors = data["invalid_rows"][0].get("errors", [])
        assert any("bulunamad" in str(e.get("message", "")).lower() for e in errors)

    # ── Preview Upload Tests ─────────────────────────────────────────

    def test_bulk_preview_upload_for_hotel_connections(self, admin_session):
        """POST /api/admin/sheets/bulk/preview-upload validates hotel rows from CSV upload"""
        hotel = _pick_available_hotel(admin_session)
        csv_text = (
            "hotel_id,sheet_id,sheet_tab,writeback_tab,sync_enabled,sync_interval_minutes\n"
            f"{hotel['_id']},bulk-upload-{hotel['_id'][:6]},Sheet1,Rezervasyonlar,true,5"
        )
        response = admin_session.post(
            "/api/admin/sheets/bulk/preview-upload",
            data={"scope": "hotel"},
            files={"file": ("bulk_connections.csv", io.BytesIO(csv_text.encode("utf-8")), "text/csv")},
        )
        assert response.status_code == 200, response.text
        data = _unwrap(response)
        assert data["source"] == "upload"
        assert data["filename"] == "bulk_connections.csv"
        assert data["summary"]["valid_rows"] == 1
        assert data["summary"]["invalid_rows"] == 0

    def test_bulk_preview_upload_semicolon_delimiter(self, admin_session):
        """POST /api/admin/sheets/bulk/preview-upload handles semicolon delimiter CSV"""
        hotel = _pick_available_hotel(admin_session)
        csv_text = (
            "hotel_id;sheet_id;sheet_tab;writeback_tab;sync_enabled;sync_interval_minutes\n"
            f"{hotel['_id']};bulk-upload-semi-{hotel['_id'][:4]};Sheet1;Rezervasyonlar;true;5"
        )
        response = admin_session.post(
            "/api/admin/sheets/bulk/preview-upload",
            data={"scope": "hotel"},
            files={"file": ("semicolon.csv", io.BytesIO(csv_text.encode("utf-8")), "text/csv")},
        )
        assert response.status_code == 200, response.text
        data = _unwrap(response)
        assert data["summary"]["valid_rows"] == 1

    # ── Master Sheet Preview Tests ───────────────────────────────────

    def test_bulk_preview_master_sheet_not_configured(self, admin_session):
        """POST /api/admin/sheets/bulk/preview-master-sheet returns graceful payload when no credentials"""
        response = admin_session.post(
            "/api/admin/sheets/bulk/preview-master-sheet",
            json={
                "scope": "hotel",
                "sheet_id": "test-master-sheet-abc",
                "sheet_tab": "Connections",
            },
        )
        assert response.status_code == 200, response.text
        data = _unwrap(response)
        assert data["configured"] is False
        assert data["source"] == "master_sheet"
        assert "message" in data
        assert "Google" in data["message"] or "gerekli" in data["message"]
        assert data["summary"]["valid_rows"] == 0

    # ── Execute Tests ────────────────────────────────────────────────

    def test_bulk_execute_hotel_connection_and_cleanup(self, admin_session):
        """POST /api/admin/sheets/bulk/execute creates connections and cleanup works"""
        hotel = _pick_available_hotel(admin_session)
        preview_response = admin_session.post(
            "/api/admin/sheets/bulk/preview-text",
            json={
                "scope": "hotel",
                "raw_text": (
                    "hotel_id\tsheet_id\tsheet_tab\twriteback_tab\tsync_enabled\tsync_interval_minutes\n"
                    f"{hotel['_id']}\tbulk-execute-{hotel['_id'][:6]}\tSheet1\tRezervasyonlar\ttrue\t5"
                ),
            },
        )
        assert preview_response.status_code == 200, preview_response.text
        preview_data = _unwrap(preview_response)
        assert preview_data["summary"]["valid_rows"] == 1

        # Execute bulk connection
        execute_response = admin_session.post(
            "/api/admin/sheets/bulk/execute",
            json={"scope": "hotel", "rows": preview_data["valid_rows"]},
        )
        assert execute_response.status_code == 200, execute_response.text
        execute_data = _unwrap(execute_response)
        assert execute_data["scope"] == "hotel"
        assert execute_data["created_count"] == 1
        assert execute_data["error_count"] == 0
        assert len(execute_data.get("created_preview", [])) >= 1

        # Cleanup - delete the created connection
        cleanup_response = admin_session.delete(f"/api/admin/sheets/connections/{hotel['_id']}")
        assert cleanup_response.status_code == 200, cleanup_response.text
        cleanup_data = _unwrap(cleanup_response)
        assert cleanup_data.get("deleted") is True

        # Verify cleanup - connection should no longer exist
        verify_response = admin_session.get(f"/api/admin/sheets/connections/{hotel['_id']}")
        assert verify_response.status_code == 200
        assert _unwrap(verify_response).get("connected") is False

    def test_bulk_execute_empty_rows_returns_error(self, admin_session):
        """POST /api/admin/sheets/bulk/execute with empty rows returns 400"""
        response = admin_session.post(
            "/api/admin/sheets/bulk/execute",
            json={"scope": "hotel", "rows": []},
        )
        assert response.status_code == 400, response.text

    def test_bulk_execute_duplicate_hotel_returns_conflict_error(self, admin_session):
        """POST /api/admin/sheets/bulk/execute returns conflict error for duplicate hotel"""
        hotel = _pick_available_hotel(admin_session)

        # First: create a connection
        preview_response = admin_session.post(
            "/api/admin/sheets/bulk/preview-text",
            json={
                "scope": "hotel",
                "raw_text": (
                    "hotel_id\tsheet_id\tsheet_tab\twriteback_tab\tsync_enabled\tsync_interval_minutes\n"
                    f"{hotel['_id']}\tbulk-dup-test-{hotel['_id'][:4]}\tSheet1\tRezervasyonlar\ttrue\t5"
                ),
            },
        )
        assert preview_response.status_code == 200
        execute_response = admin_session.post(
            "/api/admin/sheets/bulk/execute",
            json={"scope": "hotel", "rows": _unwrap(preview_response)["valid_rows"]},
        )
        assert execute_response.status_code == 200, execute_response.text

        try:
            # Second: try to create duplicate - should fail
            duplicate_execute = admin_session.post(
                "/api/admin/sheets/bulk/execute",
                json={
                    "scope": "hotel",
                    "rows": [{
                        "hotel_id": hotel["_id"],
                        "sheet_id": "another-sheet",
                        "sheet_tab": "Sheet1",
                        "writeback_tab": "Rezervasyonlar",
                        "sync_enabled": True,
                        "sync_interval_minutes": 5,
                    }],
                },
            )
            assert duplicate_execute.status_code == 200
            dup_data = _unwrap(duplicate_execute)
            assert dup_data["error_count"] >= 1  # Should have error for duplicate
        finally:
            # Cleanup
            admin_session.delete(f"/api/admin/sheets/connections/{hotel['_id']}")
