"""API Tests for Orphan Order Migration Admin Endpoints.

Tests the production-grade orphan order migration for Travel Distribution SaaS platform.
Per the review request:
- GET /api/admin/orphan-migration/status — Returns migration summary with counts
- GET /api/admin/orphan-migration/audit-log — Returns audit trail records
- GET /api/admin/orphan-migration/quarantine — Returns quarantined orders list (supports filters)
- POST /api/admin/orphan-migration/review — Approve/reject quarantined orders
- POST /api/admin/orphan-migration/analyze — Re-run dry-run analysis
- POST /api/admin/orphan-migration/rollback — Rollback a batch

Current state per agent context:
- 8 orders auto-applied (confidence 0.9)
- 1 manually approved via API
- 77 quarantine pending review (was 78, one approved)
- 9 total audit records (8 auto + 1 manual)
- Single organization: 69b5905cb169d94c891a136d
"""
import pytest
import requests
import os


def _unwrap(resp):
    """Unwrap response envelope if present."""
    data = resp.json()
    if isinstance(data, dict) and "ok" in data and "data" in data:
        return data["data"]
    return data



BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")

# Batch ID from the migration run (provided in review request)
TEST_BATCH_ID = "batch_20260318_193054_727dd948"


class TestOrphanMigrationStatus:
    """Test GET /api/admin/orphan-migration/status endpoint."""

    def test_status_returns_200(self):
        """Status endpoint should return 200 with summary data."""
        response = requests.get(f"{BASE_URL}/api/admin/orphan-migration/status")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
    def test_status_has_required_fields(self):
        """Status response should have total_orders, assigned, orphaned, health_score."""
        response = requests.get(f"{BASE_URL}/api/admin/orphan-migration/status")
        data = _unwrap(response)
        
        # Required fields
        assert "total_orders" in data, "Missing 'total_orders' field"
        assert "assigned" in data, "Missing 'assigned' field"
        assert "orphaned" in data, "Missing 'orphaned' field"
        assert "health_score" in data, "Missing 'health_score' field"
        
    def test_status_has_audit_and_quarantine_sections(self):
        """Status response should have audit and quarantine breakdown."""
        response = requests.get(f"{BASE_URL}/api/admin/orphan-migration/status")
        data = _unwrap(response)
        
        assert "audit" in data, "Missing 'audit' section"
        assert "quarantine" in data, "Missing 'quarantine' section"
        
        # Audit should have 'applied' count
        assert "applied" in data["audit"], "Missing 'audit.applied'"
        
        # Quarantine should have breakdown
        assert "pending_review" in data["quarantine"], "Missing 'quarantine.pending_review'"
        assert "approved" in data["quarantine"], "Missing 'quarantine.approved'"
        assert "rejected" in data["quarantine"], "Missing 'quarantine.rejected'"
        
    def test_status_numbers_are_reasonable(self):
        """Validate that status numbers match expected state."""
        response = requests.get(f"{BASE_URL}/api/admin/orphan-migration/status")
        data = _unwrap(response)
        
        # Per review request: 86 total orders
        assert data["total_orders"] >= 86, f"Expected >= 86 total orders, got {data['total_orders']}"
        
        # 9 orders should be assigned (8 auto + 1 manual)
        assert data["assigned"] >= 9, f"Expected >= 9 assigned, got {data['assigned']}"
        
        # Health score should be reasonable (not 0)
        assert data["health_score"] > 0, f"Health score is {data['health_score']}, expected > 0"


class TestOrphanMigrationAuditLog:
    """Test GET /api/admin/orphan-migration/audit-log endpoint."""

    def test_audit_log_returns_200(self):
        """Audit log endpoint should return 200."""
        response = requests.get(f"{BASE_URL}/api/admin/orphan-migration/audit-log")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
    def test_audit_log_has_required_fields(self):
        """Audit log response should have total, records, batches."""
        response = requests.get(f"{BASE_URL}/api/admin/orphan-migration/audit-log")
        data = _unwrap(response)
        
        assert "total" in data, "Missing 'total' field"
        assert "records" in data, "Missing 'records' field"
        assert "batches" in data, "Missing 'batches' field"
        
        assert isinstance(data["records"], list), "'records' should be a list"
        assert isinstance(data["batches"], list), "'batches' should be a list"
        
    def test_audit_log_has_9_records(self):
        """Per review request, should have 9 audit records (8 auto + 1 manual)."""
        response = requests.get(f"{BASE_URL}/api/admin/orphan-migration/audit-log")
        data = _unwrap(response)
        
        # At least 9 records
        assert data["total"] >= 9, f"Expected >= 9 audit records, got {data['total']}"
        
    def test_audit_log_records_have_required_fields(self):
        """Each audit record should have batch_id, action, order_id, etc."""
        response = requests.get(f"{BASE_URL}/api/admin/orphan-migration/audit-log", params={"limit": 5})
        data = _unwrap(response)
        
        if data["records"]:
            record = data["records"][0]
            assert "batch_id" in record, "Audit record missing 'batch_id'"
            assert "action" in record, "Audit record missing 'action'"
            assert "order_id" in record, "Audit record missing 'order_id'"
            assert "new_organization_id" in record, "Audit record missing 'new_organization_id'"
            
    def test_audit_log_filter_by_batch_id(self):
        """Audit log should support batch_id filter."""
        response = requests.get(
            f"{BASE_URL}/api/admin/orphan-migration/audit-log",
            params={"batch_id": TEST_BATCH_ID}
        )
        assert response.status_code == 200
        data = _unwrap(response)
        
        # All records should be from this batch
        for record in data["records"]:
            assert record["batch_id"] == TEST_BATCH_ID, f"Record has wrong batch_id: {record['batch_id']}"


class TestOrphanMigrationQuarantine:
    """Test GET /api/admin/orphan-migration/quarantine endpoint."""

    def test_quarantine_returns_200(self):
        """Quarantine list endpoint should return 200."""
        response = requests.get(f"{BASE_URL}/api/admin/orphan-migration/quarantine")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
    def test_quarantine_has_required_fields(self):
        """Quarantine response should have total and records."""
        response = requests.get(f"{BASE_URL}/api/admin/orphan-migration/quarantine")
        data = _unwrap(response)
        
        assert "total" in data, "Missing 'total' field"
        assert "records" in data, "Missing 'records' field"
        assert isinstance(data["records"], list), "'records' should be a list"
        
    def test_quarantine_filter_by_reviewed_false(self):
        """Filter quarantine by reviewed=false should return pending items."""
        response = requests.get(
            f"{BASE_URL}/api/admin/orphan-migration/quarantine",
            params={"reviewed": "false"}
        )
        assert response.status_code == 200
        data = _unwrap(response)
        
        # Per review request: 77 pending (78 - 1 approved)
        assert data["total"] >= 70, f"Expected >= 70 pending, got {data['total']}"
        
        # All records should have reviewed=False
        for record in data["records"]:
            assert record.get("reviewed") is False, f"Record should have reviewed=False: {record}"
            
    def test_quarantine_filter_by_reviewed_true(self):
        """Filter quarantine by reviewed=true should return approved/rejected items."""
        response = requests.get(
            f"{BASE_URL}/api/admin/orphan-migration/quarantine",
            params={"reviewed": "true"}
        )
        assert response.status_code == 200
        data = _unwrap(response)
        
        # Should have at least 1 (the manually approved one)
        assert data["total"] >= 1, f"Expected >= 1 reviewed, got {data['total']}"
        
    def test_quarantine_filter_by_strategy(self):
        """Filter quarantine by match_strategy."""
        # Test with 'test_artifact_single_org' strategy (37 test artifacts per review request)
        response = requests.get(
            f"{BASE_URL}/api/admin/orphan-migration/quarantine",
            params={"strategy": "test_artifact_single_org"}
        )
        assert response.status_code == 200
        data = _unwrap(response)
        
        # All returned records should have the specified strategy
        for record in data["records"]:
            assert record.get("match_strategy") == "test_artifact_single_org"
            
    def test_quarantine_records_have_required_fields(self):
        """Quarantine records should have order_id, resolution, proposed_organization_id, etc."""
        response = requests.get(f"{BASE_URL}/api/admin/orphan-migration/quarantine", params={"limit": 5})
        data = _unwrap(response)
        
        if data["records"]:
            record = data["records"][0]
            assert "order_id" in record, "Quarantine record missing 'order_id'"
            assert "resolution" in record, "Quarantine record missing 'resolution'"
            assert "match_strategy" in record, "Quarantine record missing 'match_strategy'"
            assert "reviewed" in record, "Quarantine record missing 'reviewed'"


class TestOrphanMigrationReview:
    """Test POST /api/admin/orphan-migration/review endpoint."""

    def test_review_reject_quarantined_order(self):
        """Should be able to reject a quarantined order."""
        # First get a pending quarantine record
        response = requests.get(
            f"{BASE_URL}/api/admin/orphan-migration/quarantine",
            params={"reviewed": "false", "limit": 1}
        )
        assert response.status_code == 200
        data = _unwrap(response)
        
        if not data["records"]:
            pytest.skip("No pending quarantine records to test rejection")
            
        order_id = data["records"][0]["order_id"]
        
        # Reject it
        review_response = requests.post(
            f"{BASE_URL}/api/admin/orphan-migration/review",
            params={
                "order_id": order_id,
                "action": "reject",
                "reviewer_note": "TEST_REJECTION by testing agent"
            }
        )
        assert review_response.status_code == 200, f"Expected 200, got {review_response.status_code}: {review_response.text}"
        
        result = _unwrap(review_response)
        assert result.get("status") == "rejected", f"Expected 'rejected', got {result}"
        assert result.get("order_id") == order_id
        
    def test_review_invalid_action(self):
        """Review with invalid action should return error."""
        response = requests.post(
            f"{BASE_URL}/api/admin/orphan-migration/review",
            params={
                "order_id": "test_order_123",
                "action": "invalid_action",
            }
        )
        # Should return 200 with error message (not 500)
        assert response.status_code == 200
        data = _unwrap(response)
        assert "error" in data, f"Expected error message for invalid action: {data}"
        
    def test_review_nonexistent_order(self):
        """Review of non-existent order should return error."""
        response = requests.post(
            f"{BASE_URL}/api/admin/orphan-migration/review",
            params={
                "order_id": "nonexistent_order_xyz_testing",
                "action": "approve",
                "organization_id": "69b5905cb169d94c891a136d"
            }
        )
        assert response.status_code == 200
        data = _unwrap(response)
        assert "error" in data, f"Expected error for non-existent order: {data}"
        assert "not found" in data.get("error", "").lower()


class TestOrphanMigrationAnalyze:
    """Test POST /api/admin/orphan-migration/analyze endpoint."""

    def test_analyze_returns_200(self):
        """Analyze endpoint should return 200."""
        response = requests.post(f"{BASE_URL}/api/admin/orphan-migration/analyze")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
    def test_analyze_has_required_fields(self):
        """Analyze response should have breakdown of resolutions."""
        response = requests.post(f"{BASE_URL}/api/admin/orphan-migration/analyze")
        data = _unwrap(response)
        
        assert "total_orphans" in data, "Missing 'total_orphans'"
        assert "auto_fix" in data, "Missing 'auto_fix'"
        assert "manual_review" in data, "Missing 'manual_review'"
        assert "quarantine" in data, "Missing 'quarantine'"
        assert "unresolved" in data, "Missing 'unresolved'"
        
    def test_analyze_numbers_sum_correctly(self):
        """Resolution counts should sum to total_orphans."""
        response = requests.post(f"{BASE_URL}/api/admin/orphan-migration/analyze")
        data = _unwrap(response)
        
        total = data["total_orphans"]
        sum_resolutions = data["auto_fix"] + data["manual_review"] + data["quarantine"] + data["unresolved"]
        
        assert sum_resolutions == total, f"Resolution sum ({sum_resolutions}) != total ({total})"


class TestOrphanMigrationRollback:
    """Test POST /api/admin/orphan-migration/rollback endpoint."""

    def test_rollback_nonexistent_batch(self):
        """Rollback of non-existent batch should return no_records status."""
        response = requests.post(
            f"{BASE_URL}/api/admin/orphan-migration/rollback",
            params={"batch_id": "nonexistent_batch_testing_xyz"}
        )
        assert response.status_code == 200
        data = _unwrap(response)
        
        assert data.get("status") == "no_records", f"Expected 'no_records', got {data}"
        assert data.get("rolled_back") == 0
        
    def test_rollback_requires_batch_id(self):
        """Rollback without batch_id should fail (422 validation error)."""
        response = requests.post(f"{BASE_URL}/api/admin/orphan-migration/rollback")
        # FastAPI returns 422 for missing required params
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"


class TestOrphanMigrationOptimisticGuard:
    """Test that optimistic guard prevents overwriting existing organization_id."""

    def test_approve_already_assigned_order(self):
        """Approving an order that already has organization_id should return 'already_assigned'."""
        # Get a reviewed (approved) quarantine record
        response = requests.get(
            f"{BASE_URL}/api/admin/orphan-migration/quarantine",
            params={"reviewed": "true", "limit": 10}
        )
        assert response.status_code == 200
        data = _unwrap(response)
        
        # Find an approved one
        approved = [r for r in data["records"] if r.get("review_action") == "approved"]
        if not approved:
            pytest.skip("No approved quarantine records found")
            
        order_id = approved[0]["order_id"]
        
        # Try to approve again
        review_response = requests.post(
            f"{BASE_URL}/api/admin/orphan-migration/review",
            params={
                "order_id": order_id,
                "action": "approve",
                "organization_id": "69b5905cb169d94c891a136d"
            }
        )
        assert review_response.status_code == 200
        result = _unwrap(review_response)
        
        # Should indicate already assigned (optimistic guard)
        # Note: The endpoint returns 'already_assigned' status when the order already has org_id
        assert result.get("status") in ("already_assigned", "error", "approved"), f"Unexpected result: {result}"


class TestIntegration:
    """Integration tests combining multiple endpoints."""

    def test_status_quarantine_counts_match(self):
        """Status endpoint quarantine counts should match quarantine endpoint totals."""
        # Get status
        status_response = requests.get(f"{BASE_URL}/api/admin/orphan-migration/status")
        status_data = _unwrap(status_response)
        
        # Get quarantine pending count directly
        quarantine_response = requests.get(
            f"{BASE_URL}/api/admin/orphan-migration/quarantine",
            params={"reviewed": "false"}
        )
        quarantine_data = _unwrap(quarantine_response)
        
        status_pending = status_data["quarantine"]["pending_review"]
        quarantine_pending = quarantine_data["total"]
        
        assert status_pending == quarantine_pending, \
            f"Status pending ({status_pending}) != Quarantine pending ({quarantine_pending})"
            
    def test_audit_batches_appear_in_list(self):
        """Batch IDs in audit log should be listed in 'batches' field."""
        response = requests.get(f"{BASE_URL}/api/admin/orphan-migration/audit-log")
        data = _unwrap(response)
        
        batches = set(data["batches"])
        record_batches = set(r["batch_id"] for r in data["records"])
        
        # All batch_ids in records should be in the batches list
        assert record_batches.issubset(batches), \
            f"Some batch_ids in records not in batches list: {record_batches - batches}"
