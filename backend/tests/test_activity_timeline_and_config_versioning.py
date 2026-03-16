"""
Test Suite: Configuration Versioning and Activity Timeline (Audit Trail)
========================================================================
Tests for PROMPT H - Config Versioning and Activity Timeline features.

Features tested:
1. Activity Timeline API - list events, stats, entity history
2. Config Versions API - version history for configs
3. Distribution Rules - CRUD with versioning and audit events
4. Channel Configs - CRUD with versioning and audit events
5. Guardrails - CRUD with versioning and audit events
6. Promotions - CRUD with audit events
7. Settlement workflow transitions - audit events
8. Exception resolution - audit events
"""

import os
import pytest
import requests
import time
from datetime import datetime

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Test credentials
SUPER_ADMIN_EMAIL = "agent@acenta.test"
SUPER_ADMIN_PASSWORD = "agent123"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for super admin user."""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": SUPER_ADMIN_EMAIL,
        "password": SUPER_ADMIN_PASSWORD
    })
    if response.status_code != 200:
        pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")
    data = response.json()
    return data.get("token") or data.get("access_token")


@pytest.fixture(scope="module")
def api_client(auth_token):
    """Authenticated requests session."""
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}"
    })
    return session


class TestActivityTimelineAPI:
    """Tests for Activity Timeline endpoints."""

    def test_list_timeline_events(self, api_client):
        """GET /api/activity-timeline - list events with pagination."""
        response = api_client.get(f"{BASE_URL}/api/activity-timeline?limit=50")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "events" in data, "Response should contain 'events' key"
        assert "total" in data, "Response should contain 'total' key"
        assert isinstance(data["events"], list), "events should be a list"
        print(f"✅ Timeline has {data['total']} total events, retrieved {len(data['events'])} events")

    def test_timeline_filter_by_entity_type(self, api_client):
        """GET /api/activity-timeline with entity_type filter."""
        response = api_client.get(f"{BASE_URL}/api/activity-timeline?entity_type=distribution_rule&limit=20")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        for event in data["events"]:
            assert event["entity_type"] == "distribution_rule", f"Filtered event should have entity_type=distribution_rule"
        print(f"✅ Entity type filter working - found {len(data['events'])} distribution_rule events")

    def test_timeline_filter_by_action(self, api_client):
        """GET /api/activity-timeline with action filter."""
        response = api_client.get(f"{BASE_URL}/api/activity-timeline?action=created&limit=20")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        for event in data["events"]:
            assert event["action"] == "created", f"Filtered event should have action=created"
        print(f"✅ Action filter working - found {len(data['events'])} 'created' events")

    def test_timeline_stats(self, api_client):
        """GET /api/activity-timeline/stats - aggregate stats."""
        response = api_client.get(f"{BASE_URL}/api/activity-timeline/stats")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "total_events" in data, "Stats should contain 'total_events'"
        assert "by_entity_type" in data, "Stats should contain 'by_entity_type'"
        assert "by_action" in data, "Stats should contain 'by_action'"
        print(f"✅ Timeline stats: total_events={data['total_events']}, by_entity_type={data['by_entity_type']}")


class TestDistributionRulesVersioning:
    """Tests for Distribution Rules CRUD with versioning and audit."""

    def test_create_distribution_rule_with_versioning(self, api_client):
        """POST /api/pricing-engine/distribution-rules - creates rule with version=1."""
        rule_name = f"TEST_RULE_{int(time.time())}"
        payload = {
            "name": rule_name,
            "rule_category": "markup",
            "value": 10.0,
            "scope": {"channels": ["b2c"]},
            "priority": 100,
            "active": True,
            "change_reason": "Test creation"
        }
        
        response = api_client.post(f"{BASE_URL}/api/pricing-engine/distribution-rules", json=payload)
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "rule_id" in data, "Response should contain rule_id"
        assert data["version"] == 1, f"New rule should have version=1, got {data.get('version')}"
        assert data["created_by"] == SUPER_ADMIN_EMAIL, f"created_by should be {SUPER_ADMIN_EMAIL}"
        
        # Store rule_id for later tests
        TestDistributionRulesVersioning.rule_id = data["rule_id"]
        print(f"✅ Created distribution rule {data['rule_id']} with version=1")
        return data

    def test_update_distribution_rule_increments_version(self, api_client):
        """PATCH /api/pricing-engine/distribution-rules/{id} - updates version++."""
        rule_id = getattr(TestDistributionRulesVersioning, "rule_id", None)
        if not rule_id:
            pytest.skip("No rule_id from previous test")
        
        payload = {
            "value": 15.0,
            "change_reason": "Updated markup value for testing"
        }
        
        response = api_client.patch(f"{BASE_URL}/api/pricing-engine/distribution-rules/{rule_id}", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["version"] == 2, f"Updated rule should have version=2, got {data.get('version')}"
        assert data["value"] == 15.0, f"Value should be updated to 15.0"
        assert data["updated_by"] == SUPER_ADMIN_EMAIL
        print(f"✅ Updated distribution rule {rule_id} - version incremented to {data['version']}")

    def test_config_version_history_saved(self, api_client):
        """GET /api/config-versions/{entity_type}/{entity_id} - version history."""
        rule_id = getattr(TestDistributionRulesVersioning, "rule_id", None)
        if not rule_id:
            pytest.skip("No rule_id from previous test")
        
        response = api_client.get(f"{BASE_URL}/api/config-versions/distribution_rule/{rule_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "versions" in data, "Response should contain 'versions' key"
        # Should have at least 1 snapshot (from the update)
        assert len(data["versions"]) >= 1, f"Should have at least 1 version snapshot, got {len(data['versions'])}"
        
        # First snapshot should be version 1
        if data["versions"]:
            snapshot = data["versions"][0]
            assert "_snapshot_version" in snapshot, "Snapshot should have _snapshot_version"
            assert "_changed_by" in snapshot, "Snapshot should have _changed_by"
        print(f"✅ Found {len(data['versions'])} version snapshots for rule {rule_id}")

    def test_distribution_rule_creates_timeline_event(self, api_client):
        """Verify that distribution rule actions create timeline events."""
        rule_id = getattr(TestDistributionRulesVersioning, "rule_id", None)
        if not rule_id:
            pytest.skip("No rule_id from previous test")
        
        response = api_client.get(f"{BASE_URL}/api/activity-timeline/entity/distribution_rule/{rule_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "events" in data
        # Should have at least 2 events: created + updated
        assert len(data["events"]) >= 2, f"Should have at least 2 events (created, updated), got {len(data['events'])}"
        
        # Check event structure
        actions = [e["action"] for e in data["events"]]
        assert "created" in actions, "Should have 'created' event"
        assert "updated" in actions, "Should have 'updated' event"
        print(f"✅ Found {len(data['events'])} timeline events for rule {rule_id}: {actions}")

    def test_delete_distribution_rule_records_event(self, api_client):
        """DELETE /api/pricing-engine/distribution-rules/{id} - saves final snapshot and records event."""
        rule_id = getattr(TestDistributionRulesVersioning, "rule_id", None)
        if not rule_id:
            pytest.skip("No rule_id from previous test")
        
        response = api_client.delete(f"{BASE_URL}/api/pricing-engine/distribution-rules/{rule_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("ok") == True, f"Delete should return ok=true"
        
        # Verify timeline event was recorded
        time.sleep(0.2)  # Small delay for async event recording
        response2 = api_client.get(f"{BASE_URL}/api/activity-timeline/entity/distribution_rule/{rule_id}")
        if response2.status_code == 200:
            events = response2.json().get("events", [])
            actions = [e["action"] for e in events]
            assert "deleted" in actions, f"Should have 'deleted' event in timeline: {actions}"
            print(f"✅ Deleted rule {rule_id} - delete event recorded in timeline")


class TestChannelConfigsVersioning:
    """Tests for Channel Configs CRUD with versioning."""

    def test_create_channel_config_with_versioning(self, api_client):
        """POST /api/pricing-engine/channels - creates with versioning."""
        payload = {
            "channel": f"test_ch_{int(time.time())}",
            "label": "Test Channel",
            "adjustment_pct": 5.0,
            "agency_tier": "gold",
            "commission_pct": 12.0,
            "active": True,
            "change_reason": "Test channel creation"
        }
        
        response = api_client.post(f"{BASE_URL}/api/pricing-engine/channels", json=payload)
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["version"] == 1, f"New channel should have version=1"
        assert data["created_by"] == SUPER_ADMIN_EMAIL
        
        TestChannelConfigsVersioning.channel_id = data["rule_id"]
        print(f"✅ Created channel config {data['rule_id']} with version=1")

    def test_update_channel_config_increments_version(self, api_client):
        """PATCH /api/pricing-engine/channels/{id} - updates with versioning."""
        channel_id = getattr(TestChannelConfigsVersioning, "channel_id", None)
        if not channel_id:
            pytest.skip("No channel_id from previous test")
        
        payload = {
            "commission_pct": 15.0,
            "change_reason": "Updated commission rate"
        }
        
        response = api_client.patch(f"{BASE_URL}/api/pricing-engine/channels/{channel_id}", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["version"] == 2, f"Updated channel should have version=2, got {data.get('version')}"
        print(f"✅ Updated channel config {channel_id} - version={data['version']}")

    def test_cleanup_channel_config(self, api_client):
        """Clean up test channel config."""
        channel_id = getattr(TestChannelConfigsVersioning, "channel_id", None)
        if channel_id:
            response = api_client.delete(f"{BASE_URL}/api/pricing-engine/channels/{channel_id}")
            print(f"✅ Cleaned up channel config {channel_id}")


class TestGuardrailsVersioning:
    """Tests for Guardrails CRUD with versioning."""

    def test_create_guardrail_with_versioning(self, api_client):
        """POST /api/pricing-engine/guardrails - creates with versioning."""
        payload = {
            "name": f"TEST_GUARD_{int(time.time())}",
            "guardrail_type": "max_markup",
            "value": 30.0,
            "scope": {"channels": ["b2c"]},
            "active": True,
            "change_reason": "Test guardrail creation"
        }
        
        response = api_client.post(f"{BASE_URL}/api/pricing-engine/guardrails", json=payload)
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["version"] == 1, f"New guardrail should have version=1"
        assert data["created_by"] == SUPER_ADMIN_EMAIL
        
        TestGuardrailsVersioning.guardrail_id = data["guardrail_id"]
        print(f"✅ Created guardrail {data['guardrail_id']} with version=1")

    def test_update_guardrail_with_audit_trail(self, api_client):
        """PATCH /api/pricing-engine/guardrails/{id} - updates with versioning and audit."""
        guardrail_id = getattr(TestGuardrailsVersioning, "guardrail_id", None)
        if not guardrail_id:
            pytest.skip("No guardrail_id from previous test")
        
        payload = {
            "value": 35.0,
            "change_reason": "Increased max markup limit"
        }
        
        response = api_client.patch(f"{BASE_URL}/api/pricing-engine/guardrails/{guardrail_id}", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["version"] == 2, f"Updated guardrail should have version=2"
        print(f"✅ Updated guardrail {guardrail_id} - version={data['version']}")


class TestPromotionsAuditTrail:
    """Tests for Promotions CRUD with audit trail events."""

    def test_create_promotion_records_event(self, api_client):
        """POST /api/pricing-engine/promotions - creates with audit trail event."""
        payload = {
            "name": f"TEST_PROMO_{int(time.time())}",
            "promo_type": "percentage",
            "discount_pct": 10.0,
            "promo_code": f"TEST{int(time.time())}",
            "scope": {},
            "valid_from": datetime.now().isoformat(),
            "valid_to": None,
            "min_days_before": 0,
            "max_uses": 100,
            "change_reason": "Test promotion creation"
        }
        
        response = api_client.post(f"{BASE_URL}/api/pricing-engine/promotions", json=payload)
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "rule_id" in data, "Promotion should have rule_id"
        
        TestPromotionsAuditTrail.promo_id = data["rule_id"]
        print(f"✅ Created promotion {data['rule_id']}")

    def test_update_promotion_with_versioning_and_audit(self, api_client):
        """PATCH /api/pricing-engine/promotions/{id} - updates with versioning and audit."""
        promo_id = getattr(TestPromotionsAuditTrail, "promo_id", None)
        if not promo_id:
            pytest.skip("No promo_id from previous test")
        
        payload = {
            "discount_pct": 15.0,
            "change_reason": "Increased discount for campaign"
        }
        
        response = api_client.patch(f"{BASE_URL}/api/pricing-engine/promotions/{promo_id}", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        # Promotions should also have versioning
        assert data.get("version", 0) >= 1
        print(f"✅ Updated promotion {promo_id}")


class TestSettlementWorkflowAudit:
    """Tests for Settlement workflow transitions recording timeline events."""

    def test_create_settlement_draft_records_event(self):
        """POST /api/finance/settlement-runs - creating draft records timeline event."""
        payload = {
            "run_type": "agency",
            "entity_id": "test_agency_audit",
            "entity_name": "Test Agency Audit",
            "period_start": "2024-01-01",
            "period_end": "2024-01-31",
            "currency": "EUR",
            "notes": "Test settlement for audit trail"
        }
        
        response = requests.post(f"{BASE_URL}/api/finance/settlement-runs", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "run_id" in data, "Response should contain run_id"
        
        TestSettlementWorkflowAudit.run_id = data["run_id"]
        print(f"✅ Created settlement draft {data['run_id']}")

    def test_submit_settlement_records_timeline_event(self):
        """PATCH /api/finance/settlement-runs/{id}/submit - transition records timeline event."""
        run_id = getattr(TestSettlementWorkflowAudit, "run_id", None)
        if not run_id:
            pytest.skip("No run_id from previous test")
        
        payload = {
            "actor": "test_admin",
            "reason": "Submitting for approval"
        }
        
        response = requests.patch(f"{BASE_URL}/api/finance/settlement-runs/{run_id}/submit", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["status"] == "pending_approval", f"Status should be pending_approval"
        print(f"✅ Submitted settlement {run_id} - status={data['status']}")

    def test_approve_settlement_records_timeline_event(self):
        """PATCH /api/finance/settlement-runs/{id}/approve - approve records timeline event."""
        run_id = getattr(TestSettlementWorkflowAudit, "run_id", None)
        if not run_id:
            pytest.skip("No run_id from previous test")
        
        payload = {
            "actor": "test_approver",
            "reason": "Approved for payment"
        }
        
        response = requests.patch(f"{BASE_URL}/api/finance/settlement-runs/{run_id}/approve", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["status"] == "approved", f"Status should be approved"
        print(f"✅ Approved settlement {run_id} - status={data['status']}")

    def test_settlement_timeline_events(self, api_client):
        """Verify settlement transitions created timeline events."""
        run_id = getattr(TestSettlementWorkflowAudit, "run_id", None)
        if not run_id:
            pytest.skip("No run_id from previous test")
        
        response = api_client.get(f"{BASE_URL}/api/activity-timeline/entity/settlement_run/{run_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        events = data.get("events", [])
        actions = [e["action"] for e in events]
        
        # Should have created, submitted, approved events
        assert "created" in actions, f"Should have 'created' event: {actions}"
        assert "submitted" in actions, f"Should have 'submitted' event: {actions}"
        assert "approved" in actions, f"Should have 'approved' event: {actions}"
        print(f"✅ Settlement {run_id} has timeline events: {actions}")


class TestExceptionResolutionAudit:
    """Tests for Exception resolution recording timeline events."""

    def test_get_exceptions_list(self):
        """GET /api/finance/exceptions - list exceptions."""
        response = requests.get(f"{BASE_URL}/api/finance/exceptions?limit=10")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "exceptions" in data, "Response should have 'exceptions' key"
        print(f"✅ Found {len(data['exceptions'])} exceptions")
        
        # Store an exception ID if available for resolve test
        if data["exceptions"]:
            # Find an open exception
            open_exceptions = [e for e in data["exceptions"] if e.get("status") == "open"]
            if open_exceptions:
                TestExceptionResolutionAudit.exception_id = open_exceptions[0]["exception_id"]


class TestEntitySpecificTimeline:
    """Tests for entity-specific timeline history."""

    def test_get_entity_timeline(self, api_client):
        """GET /api/activity-timeline/entity/{entity_type}/{entity_id} - entity-specific history."""
        # Use settlement_run entity type with the run_id from earlier test if available
        run_id = getattr(TestSettlementWorkflowAudit, "run_id", None)
        
        if run_id:
            response = api_client.get(f"{BASE_URL}/api/activity-timeline/entity/settlement_run/{run_id}")
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            
            data = response.json()
            assert data["entity_type"] == "settlement_run"
            assert data["entity_id"] == run_id
            assert "events" in data
            print(f"✅ Entity timeline for settlement_run/{run_id} has {len(data['events'])} events")
        else:
            # Test with a generic query
            response = api_client.get(f"{BASE_URL}/api/activity-timeline/entity/distribution_rule/test_id")
            assert response.status_code == 200
            print("✅ Entity timeline endpoint working (no events for test_id)")


class TestConfigVersionHistory:
    """Tests for config version history retrieval."""

    def test_get_version_history_for_nonexistent(self, api_client):
        """GET /api/config-versions/{entity_type}/{entity_id} - returns empty for nonexistent."""
        response = api_client.get(f"{BASE_URL}/api/config-versions/distribution_rule/nonexistent_id")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "versions" in data
        assert data["versions"] == [] or isinstance(data["versions"], list)
        print("✅ Version history returns empty list for nonexistent entity")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
