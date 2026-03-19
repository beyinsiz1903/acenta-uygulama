"""Async ASGI-based tests for Accounting Provider Architecture (MEGA PROMPT #34).

Tests critical paths using the local ASGI client (no external HTTP):
  - Provider catalog & capability matrix
  - Provider health monitoring
  - Provider routing (configure/get/delete)
  - Credential validation & encryption
  - Connection test flow
  - Credential rotation
  - RBAC enforcement
  - Invoice accounting sync via queue
  - Provider failover logic

All tests use the isolated test_db from conftest.
"""
import pytest
from unittest.mock import AsyncMock, patch


def _unwrap(resp):
    """Unwrap response envelope if present."""
    data = _unwrap(resp)
    if isinstance(data, dict) and "ok" in data and "data" in data:
        return data["data"]
    return data


# ── Provider Catalog Tests ───────────────────────────────────────────

@pytest.mark.anyio
async def test_catalog_returns_all_providers(async_client, admin_token):
    """GET /api/accounting/providers/catalog - 4 providers with capability matrix."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = await async_client.get("/api/accounting/providers/catalog", headers=headers)
    assert resp.status_code == 200
    data = _unwrap(resp)
    providers = data["providers"]
    assert len(providers) == 4
    codes = {p["code"] for p in providers}
    assert codes == {"luca", "logo", "parasut", "mikro"}
    for p in providers:
        assert "capabilities" in p
        assert "rate_limit_rpm" in p
        assert "is_active" in p
        assert "credential_fields" in p


@pytest.mark.anyio
async def test_catalog_active_returns_only_luca(async_client, admin_token):
    """GET /api/accounting/providers/catalog/active - only Luca is active."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = await async_client.get("/api/accounting/providers/catalog/active", headers=headers)
    assert resp.status_code == 200
    providers = _unwrap(resp)["providers"]
    assert len(providers) == 1
    assert providers[0]["code"] == "luca"
    assert providers[0]["is_active"] is True


@pytest.mark.anyio
async def test_catalog_specific_provider(async_client, admin_token):
    """GET /api/accounting/providers/catalog/{code} - detail view."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = await async_client.get("/api/accounting/providers/catalog/luca", headers=headers)
    assert resp.status_code == 200
    p = _unwrap(resp)
    assert p["code"] == "luca"
    assert p["capabilities"]["customer_management"] is True
    assert p["capabilities"]["invoice_creation"] is True


@pytest.mark.anyio
async def test_catalog_unknown_provider_404(async_client, admin_token):
    """GET /api/accounting/providers/catalog/unknown - returns 404."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = await async_client.get("/api/accounting/providers/catalog/unknown", headers=headers)
    assert resp.status_code == 404


# ── Provider Routing / Config Tests ──────────────────────────────────

@pytest.mark.anyio
async def test_configure_luca_provider(async_client, admin_token):
    """POST /api/accounting/providers/config - configure Luca with credentials."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    payload = {
        "provider_code": "luca",
        "credentials": {
            "username": "test_user",
            "password": "test_pass",
            "company_id": "FIRMA001",
        },
    }
    resp = await async_client.post("/api/accounting/providers/config", headers=headers, json=payload)
    assert resp.status_code == 200
    data = _unwrap(resp)
    assert data["provider_code"] == "luca"
    assert data["status"] == "configured"
    assert "config_id" in data
    assert "encrypted_credentials" not in data  # must not expose


@pytest.mark.anyio
async def test_get_config_returns_masked_credentials(async_client, admin_token):
    """GET /api/accounting/providers/config - returns masked credentials."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    # Configure first
    await async_client.post("/api/accounting/providers/config", headers=headers, json={
        "provider_code": "luca",
        "credentials": {"username": "demo_user", "password": "demo_pass", "company_id": "C001"},
    })
    resp = await async_client.get("/api/accounting/providers/config", headers=headers)
    assert resp.status_code == 200
    data = _unwrap(resp)
    assert data["configured"] is True
    provider = data["provider"]
    assert provider["provider_code"] == "luca"
    masked = provider["masked_credentials"]
    # password and username must be masked, company_id is non-sensitive
    assert "***" in masked.get("password", "") or "******" in masked.get("password", "")
    assert "***" in masked.get("username", "") or "******" in masked.get("username", "")


@pytest.mark.anyio
async def test_configure_inactive_provider_rejected(async_client, admin_token):
    """POST /api/accounting/providers/config with inactive provider - returns 400."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    payload = {
        "provider_code": "logo",
        "credentials": {"api_key": "test"},
    }
    resp = await async_client.post("/api/accounting/providers/config", headers=headers, json=payload)
    assert resp.status_code == 400


@pytest.mark.anyio
async def test_configure_unknown_provider_rejected(async_client, admin_token):
    """POST /api/accounting/providers/config with unknown provider - returns 400."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    payload = {
        "provider_code": "unknown_xyz",
        "credentials": {"key": "val"},
    }
    resp = await async_client.post("/api/accounting/providers/config", headers=headers, json=payload)
    assert resp.status_code == 400


@pytest.mark.anyio
async def test_delete_provider_config(async_client, admin_token):
    """DELETE /api/accounting/providers/config - removes config."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    # Configure first
    await async_client.post("/api/accounting/providers/config", headers=headers, json={
        "provider_code": "luca",
        "credentials": {"username": "del_user", "password": "del_pass", "company_id": "DEL"},
    })
    # Delete
    resp = await async_client.delete("/api/accounting/providers/config", headers=headers)
    assert resp.status_code == 200
    assert _unwrap(resp)["deleted"] is True
    # Verify
    get_resp = await async_client.get("/api/accounting/providers/config", headers=headers)
    assert _unwrap(get_resp)["configured"] is False


# ── Connection Test ──────────────────────────────────────────────────

@pytest.mark.anyio
async def test_connection_test_flow(async_client, admin_token):
    """POST /api/accounting/providers/test-connection - test connection."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    # Configure Luca first
    await async_client.post("/api/accounting/providers/config", headers=headers, json={
        "provider_code": "luca",
        "credentials": {"username": "conn_user", "password": "conn_pass", "company_id": "CONN"},
    })
    resp = await async_client.post("/api/accounting/providers/test-connection", headers=headers)
    assert resp.status_code == 200
    data = _unwrap(resp)
    assert data["success"] is True
    assert data["status"] in ("connected", "simulated")


@pytest.mark.anyio
async def test_connection_test_no_config(async_client, admin_token):
    """POST /api/accounting/providers/test-connection without config - fails gracefully."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    # Delete any existing config
    await async_client.delete("/api/accounting/providers/config", headers=headers)
    resp = await async_client.post("/api/accounting/providers/test-connection", headers=headers)
    assert resp.status_code == 200
    data = _unwrap(resp)
    assert data["success"] is False


# ── Credential Rotation ─────────────────────────────────────────────

@pytest.mark.anyio
async def test_credential_rotation(async_client, admin_token):
    """POST /api/accounting/providers/rotate-credentials - rotates credentials."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    # Configure first
    await async_client.post("/api/accounting/providers/config", headers=headers, json={
        "provider_code": "luca",
        "credentials": {"username": "old_user", "password": "old_pass", "company_id": "OLD"},
    })
    # Rotate
    resp = await async_client.post("/api/accounting/providers/rotate-credentials", headers=headers, json={
        "credentials": {"username": "new_user", "password": "new_pass", "company_id": "NEW"},
    })
    assert resp.status_code == 200
    data = _unwrap(resp)
    assert data["status"] == "configured"
    assert "encrypted_credentials" not in data


# ── Provider Health ──────────────────────────────────────────────────

@pytest.mark.anyio
async def test_health_dashboard(async_client, admin_token):
    """GET /api/accounting/providers/health - health dashboard."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = await async_client.get("/api/accounting/providers/health", headers=headers)
    assert resp.status_code == 200
    data = _unwrap(resp)
    assert "tenant_providers" in data
    assert "metrics_24h" in data
    assert "metrics_1h" in data
    assert "available_providers" in data


@pytest.mark.anyio
async def test_health_metrics_endpoint(async_client, admin_token):
    """GET /api/accounting/providers/health/metrics - metrics for time window."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = await async_client.get("/api/accounting/providers/health/metrics", headers=headers, params={"hours": 1})
    assert resp.status_code == 200


# ── RBAC Tests ───────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_agency_admin_can_view_catalog(async_client, agency_token):
    """agency_admin CAN view provider catalog."""
    headers = {"Authorization": f"Bearer {agency_token}"}
    resp = await async_client.get("/api/accounting/providers/catalog", headers=headers)
    assert resp.status_code == 200
    assert len(_unwrap(resp)["providers"]) == 4


@pytest.mark.anyio
async def test_agency_admin_cannot_configure(async_client, agency_token):
    """agency_admin CANNOT configure provider."""
    headers = {"Authorization": f"Bearer {agency_token}"}
    resp = await async_client.post("/api/accounting/providers/config", headers=headers, json={
        "provider_code": "luca",
        "credentials": {"username": "x", "password": "y", "company_id": "z"},
    })
    assert resp.status_code in (401, 403)


@pytest.mark.anyio
async def test_agency_admin_cannot_test_connection(async_client, agency_token):
    """agency_admin CANNOT test connection."""
    headers = {"Authorization": f"Bearer {agency_token}"}
    resp = await async_client.post("/api/accounting/providers/test-connection", headers=headers)
    assert resp.status_code in (401, 403)


@pytest.mark.anyio
async def test_agency_admin_cannot_rotate_credentials(async_client, agency_token):
    """agency_admin CANNOT rotate credentials."""
    headers = {"Authorization": f"Bearer {agency_token}"}
    resp = await async_client.post("/api/accounting/providers/rotate-credentials", headers=headers, json={
        "credentials": {"username": "x"},
    })
    assert resp.status_code in (401, 403)


@pytest.mark.anyio
async def test_agency_admin_cannot_delete_config(async_client, agency_token):
    """agency_admin CANNOT delete provider config."""
    headers = {"Authorization": f"Bearer {agency_token}"}
    resp = await async_client.delete("/api/accounting/providers/config", headers=headers)
    assert resp.status_code in (401, 403)


# ── Credential Encryption Unit Tests ─────────────────────────────────

def test_encrypt_decrypt_round_trip():
    """Credential encryption is lossless."""
    from app.accounting.credential_encryption import encrypt_credentials, decrypt_credentials

    creds = {"username": "test_user", "password": "secret123", "company_id": "C001"}
    encrypted = encrypt_credentials(creds)
    assert isinstance(encrypted, str)
    assert encrypted != str(creds)
    decrypted = decrypt_credentials(encrypted)
    assert decrypted == creds


def test_mask_credentials_sensitive_fields():
    """Sensitive fields are masked, non-sensitive are passed through."""
    from app.accounting.credential_encryption import mask_credentials

    creds = {"username": "demo_user", "password": "secret123", "company_id": "FIRMA001"}
    masked = mask_credentials(creds)
    assert "***" in masked["password"] or "******" in masked["password"]
    assert "***" in masked["username"] or "******" in masked["username"]
    # company_id is non-sensitive
    assert masked["company_id"] == "FIRMA001"


# ── Provider Failover Logic Tests ────────────────────────────────────

def test_failover_retryable_errors():
    """Verify RETRYABLE_ERRORS set and backoff schedule."""
    from app.accounting.providers.provider_failover import RETRYABLE_ERRORS, BACKOFF_SCHEDULE

    assert "timeout" in RETRYABLE_ERRORS
    assert "provider_unreachable" in RETRYABLE_ERRORS
    assert "transient_error" in RETRYABLE_ERRORS
    assert len(BACKOFF_SCHEDULE) >= 3


def test_failover_escalation_strategy():
    """Verify failover uses retry -> queue -> manual escalation."""
    from app.accounting.providers.provider_failover import classify_failure
    from app.accounting.providers.base_provider import ProviderResponse

    failed = ProviderResponse(success=False, error_code="timeout", error_message="Timed out")

    # First failure: retry
    result = classify_failure(failed, attempt=0)
    assert result["action"] == "retry"

    # After immediate retries: queue
    result = classify_failure(failed, attempt=2)
    assert result["action"] == "queue"

    # After all retries: escalate
    result = classify_failure(failed, attempt=10)
    assert result["action"] == "escalate"


# ── Provider Registry Tests ──────────────────────────────────────────

def test_provider_registry_returns_luca():
    """Provider registry returns LucaProvider instance."""
    from app.accounting.providers.provider_registry import get_provider

    provider = get_provider("luca")
    assert provider is not None
    assert provider.provider_code == "luca"


def test_provider_registry_returns_none_for_unknown():
    """Provider registry returns None for unknown code."""
    from app.accounting.providers.provider_registry import get_provider

    provider = get_provider("nonexistent")
    assert provider is None


def test_provider_registry_lists_all_codes():
    """Provider registry lists all registered codes."""
    from app.accounting.providers.provider_registry import list_provider_codes

    codes = list_provider_codes()
    assert "luca" in codes


# ── Provider Health Event Tracking ───────────────────────────────────

@pytest.mark.anyio
async def test_record_health_event(test_db):
    """Health event is recorded in DB."""
    from app.accounting.providers.provider_health import record_health_event

    await record_health_event(
        tenant_id="test_tenant",
        provider_code="luca",
        operation="test_connection",
        success=True,
        latency_ms=42.5,
    )
    event = await test_db.accounting_provider_health_events.find_one(
        {"tenant_id": "test_tenant", "provider_code": "luca"},
        {"_id": 0},
    )
    assert event is not None
    assert event["success"] is True
    assert event["latency_ms"] == 42.5
    assert event["operation"] == "test_connection"


@pytest.mark.anyio
async def test_provider_timer_context_manager(test_db):
    """ProviderTimer records latency and success/failure."""
    from app.accounting.providers.provider_health import ProviderTimer

    async with ProviderTimer("test_tenant_timer", "luca", "create_invoice"):
        pass  # simulate successful operation

    event = await test_db.accounting_provider_health_events.find_one(
        {"tenant_id": "test_tenant_timer", "operation": "create_invoice"},
        {"_id": 0},
    )
    assert event is not None
    assert event["success"] is True
    assert event["latency_ms"] >= 0


# ── Accounting Sync Service Tests ────────────────────────────────────

@pytest.mark.anyio
async def test_sync_invoice_requires_issued_status(async_client, admin_token, test_db):
    """POST /api/accounting/sync/{id} - rejects non-issued invoices."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    # Create a draft invoice directly in DB
    from app.utils import now_utc
    draft_invoice = {
        "invoice_id": "INV-DRAFT-TEST",
        "status": "draft",
        "created_at": now_utc(),
    }
    await test_db.invoices.insert_one(draft_invoice)
    resp = await async_client.post(
        "/api/accounting/sync/INV-DRAFT-TEST",
        headers=headers,
        json={"provider": "luca"},
    )
    assert resp.status_code == 400


@pytest.mark.anyio
async def test_sync_nonexistent_invoice_returns_400(async_client, admin_token):
    """POST /api/accounting/sync/{id} - nonexistent invoice returns 400."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = await async_client.post(
        "/api/accounting/sync/INV-NONEXISTENT-XYZ",
        headers=headers,
        json={"provider": "luca"},
    )
    assert resp.status_code == 400


# ── Dashboard with Enhanced Stats ────────────────────────────────────

@pytest.mark.anyio
async def test_accounting_dashboard_structure(async_client, admin_token):
    """GET /api/accounting/dashboard - returns all expected fields."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = await async_client.get("/api/accounting/dashboard", headers=headers)
    assert resp.status_code == 200
    data = _unwrap(resp)
    # Core dashboard fields
    assert "providers" in data
    assert "failed" in data
    assert "pending" in data
    # Enhanced fields from iter96
    assert "customer_stats" in data
    assert "active_rules" in data


# ── Reconciliation Endpoints ─────────────────────────────────────────

@pytest.mark.anyio
async def test_reconciliation_summary(async_client, admin_token):
    """GET /api/reconciliation/summary - returns reconciliation stats."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = await async_client.get("/api/reconciliation/summary", headers=headers)
    assert resp.status_code == 200


@pytest.mark.anyio
async def test_reconciliation_aging(async_client, admin_token):
    """GET /api/reconciliation/aging - returns aging buckets."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = await async_client.get("/api/reconciliation/aging", headers=headers)
    assert resp.status_code == 200


@pytest.mark.anyio
async def test_reconciliation_run_trigger(async_client, admin_token):
    """POST /api/reconciliation/run - triggers manual reconciliation."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = await async_client.post(
        "/api/reconciliation/run", headers=headers, json={"run_type": "manual"},
    )
    assert resp.status_code == 200
    data = _unwrap(resp)
    assert "run_id" in data


# ── Finance Ops Queue Endpoints ──────────────────────────────────────

@pytest.mark.anyio
async def test_finance_ops_list(async_client, admin_token):
    """GET /api/reconciliation/ops - lists ops queue items."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = await async_client.get("/api/reconciliation/ops", headers=headers, params={"limit": 10})
    assert resp.status_code == 200
    data = _unwrap(resp)
    assert "items" in data
    assert "total" in data


@pytest.mark.anyio
async def test_finance_ops_stats(async_client, admin_token):
    """GET /api/reconciliation/ops/stats - ops statistics."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = await async_client.get("/api/reconciliation/ops/stats", headers=headers)
    assert resp.status_code == 200
    data = _unwrap(resp)
    assert "total" in data


@pytest.mark.anyio
async def test_finance_ops_claim_nonexistent(async_client, admin_token):
    """POST /api/reconciliation/ops/claim - 404 for non-existent ops_id."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = await async_client.post(
        "/api/reconciliation/ops/claim", headers=headers, json={"ops_id": "OPS-NONEXIST"},
    )
    assert resp.status_code == 404


# ── Financial Alerts ─────────────────────────────────────────────────

@pytest.mark.anyio
async def test_financial_alerts_list(async_client, admin_token):
    """GET /api/reconciliation/alerts - lists alerts."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = await async_client.get("/api/reconciliation/alerts", headers=headers, params={"limit": 10})
    assert resp.status_code == 200
    data = _unwrap(resp)
    assert "items" in data
    assert "total" in data


@pytest.mark.anyio
async def test_financial_alerts_stats(async_client, admin_token):
    """GET /api/reconciliation/alerts/stats - alert statistics."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = await async_client.get("/api/reconciliation/alerts/stats", headers=headers)
    assert resp.status_code == 200
    data = _unwrap(resp)
    assert "active_alerts" in data
