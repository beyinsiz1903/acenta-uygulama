import os

import pytest

from tests.preview_auth_helper import PreviewAuthSession, get_preview_base_url_or_skip

BASE_URL = get_preview_base_url_or_skip(os.environ.get("REACT_APP_BACKEND_URL", ""))

ADMIN_EMAIL = "admin@acenta.test"
ADMIN_PASSWORD = "admin123"


@pytest.fixture
def admin_client():
    return PreviewAuthSession(
        BASE_URL,
        email=ADMIN_EMAIL,
        password=ADMIN_PASSWORD,
        default_headers={"Content-Type": "application/json"},
    )


def test_templates_endpoint_returns_downloadables(admin_client):
    response = admin_client.get(f"{BASE_URL}/api/admin/sheets/templates")
    assert response.status_code == 200, response.text
    data = response.json()
    assert "downloadable_templates" in data
    template_names = {item["name"] for item in data["downloadable_templates"]}
    assert {"inventory-sync", "reservation-writeback"}.issubset(template_names)


def test_validate_sheet_returns_graceful_not_configured_payload(admin_client):
    response = admin_client.post(
        f"{BASE_URL}/api/admin/sheets/validate-sheet",
        json={
            "sheet_id": "test-sheet-id",
            "sheet_tab": "Sheet1",
            "writeback_tab": "Rezervasyonlar",
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert "configured" in data
    if data["configured"] is False:
        assert "required_service_account_fields" in data
        assert "checklist" in data


def test_download_inventory_sync_template(admin_client):
    response = admin_client.get(f"{BASE_URL}/api/admin/sheets/download-template/inventory-sync")
    assert response.status_code == 200, response.text
    assert "text/csv" in response.headers.get("content-type", "")
    content = response.content.decode("utf-8-sig")
    assert "Tarih" in content
    assert "Oda Tipi" in content


def test_download_writeback_template(admin_client):
    response = admin_client.get(f"{BASE_URL}/api/admin/sheets/download-template/reservation-writeback")
    assert response.status_code == 200, response.text
    assert "text/csv" in response.headers.get("content-type", "")
    content = response.content.decode("utf-8-sig")
    assert "Kayit Tipi" in content
    assert "Misafir Ad Soyad" in content


def test_rest_style_create_connection_alias_when_not_configured(admin_client):
    config_response = admin_client.get(f"{BASE_URL}/api/admin/sheets/config")
    assert config_response.status_code == 200, config_response.text
    config = config_response.json()
    if config.get("configured"):
        pytest.skip("Gercek sheet id gerekecegi icin configured ortamda bu smoke test atlandi")

    hotels_response = admin_client.get(f"{BASE_URL}/api/admin/sheets/available-hotels")
    assert hotels_response.status_code == 200, hotels_response.text
    hotels = hotels_response.json()
    hotel = next((item for item in hotels if not item.get("connected")), None)
    if hotel is None:
        pytest.skip("Baglanabilir otel bulunamadi")

    create_response = admin_client.post(
        f"{BASE_URL}/api/admin/sheets/connections",
        json={
            "hotel_id": hotel["_id"],
            "sheet_id": "pending-config-sheet-id",
            "sheet_tab": "Sheet1",
            "writeback_tab": "Rezervasyonlar",
            "sync_enabled": False,
            "sync_interval_minutes": 15,
        },
    )
    assert create_response.status_code == 200, create_response.text
    created = create_response.json()
    assert created["hotel_id"] == hotel["_id"]
    assert created["validation_status"] == "pending_configuration"

    delete_response = admin_client.delete(f"{BASE_URL}/api/admin/sheets/connections/{hotel['_id']}")
    assert delete_response.status_code == 200, delete_response.text
