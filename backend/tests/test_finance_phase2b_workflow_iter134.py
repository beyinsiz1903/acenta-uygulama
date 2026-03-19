"""
Phase 2B Finance Workflow & Ops Tests - Iteration 134
Tests settlement workflow actions, exception queue management, and state transitions.
"""
import os
import pytest
import requests


def _unwrap(resp):
    """Unwrap response envelope if present."""
    data = resp.json()
    if isinstance(data, dict) and "ok" in data and "data" in data:
        return data["data"]
    return data



BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")


class TestSettlementWorkflow:
    """Settlement Run workflow operations: create draft, submit, approve, reject, mark paid"""

    def test_create_settlement_draft(self):
        """POST /api/finance/settlement-runs - Create settlement draft"""
        payload = {
            "run_type": "AGENCY",
            "entity_id": "AGN-TEST-001",
            "entity_name": "Test Agency",
            "period_start": "2026-01-01",
            "period_end": "2026-01-31",
            "currency": "EUR",
            "notes": "Test draft creation"
        }
        response = requests.post(f"{BASE_URL}/api/finance/settlement-runs", json=payload)
        assert response.status_code == 200
        data = _unwrap(response)
        assert data["status"] == "draft"
        assert data["run_type"] == "AGENCY"
        assert data["entity_id"] == "AGN-TEST-001"
        assert data["entity_name"] == "Test Agency"
        assert "run_id" in data
        print(f"✅ Created draft settlement: {data['run_id']}")
        return data["run_id"]

    def test_submit_draft_for_approval(self):
        """PATCH /api/finance/settlement-runs/{run_id}/submit - Submit draft -> pending_approval"""
        # SR-004 is seeded as draft status
        run_id = "SR-004"
        payload = {"actor": "admin"}
        response = requests.patch(f"{BASE_URL}/api/finance/settlement-runs/{run_id}/submit", json=payload)
        assert response.status_code == 200
        data = _unwrap(response)
        assert data["status"] == "pending_approval"
        print(f"✅ Submitted {run_id} for approval, status: {data['status']}")

    def test_approve_pending_settlement(self):
        """PATCH /api/finance/settlement-runs/{run_id}/approve - Approve (pending_approval -> approved)"""
        # SR-003 is seeded as pending_approval status
        run_id = "SR-003"
        payload = {"actor": "finance_manager", "reason": "Budget approved"}
        response = requests.patch(f"{BASE_URL}/api/finance/settlement-runs/{run_id}/approve", json=payload)
        assert response.status_code == 200
        data = _unwrap(response)
        assert data["status"] == "approved"
        assert data["approved_at"] is not None
        print(f"✅ Approved {run_id}, approved_at: {data['approved_at']}")

    def test_reject_pending_settlement(self):
        """PATCH /api/finance/settlement-runs/{run_id}/reject - Reject (pending_approval -> rejected)"""
        # Need to create a new draft and submit it to test rejection
        # First create a draft
        create_payload = {
            "run_type": "SUPPLIER",
            "entity_id": "SUP-TEST-001",
            "entity_name": "Test Supplier Reject",
            "period_start": "2026-02-01",
            "period_end": "2026-02-28",
            "currency": "EUR"
        }
        create_res = requests.post(f"{BASE_URL}/api/finance/settlement-runs", json=create_payload)
        assert create_res.status_code == 200
        run_id = _unwrap(create_res)["run_id"]
        
        # Submit for approval
        submit_res = requests.patch(f"{BASE_URL}/api/finance/settlement-runs/{run_id}/submit", json={"actor": "admin"})
        assert submit_res.status_code == 200
        
        # Now reject
        reject_payload = {"actor": "finance_manager", "reason": "Documents incomplete"}
        response = requests.patch(f"{BASE_URL}/api/finance/settlement-runs/{run_id}/reject", json=reject_payload)
        assert response.status_code == 200
        data = _unwrap(response)
        assert data["status"] == "rejected"
        assert data["rejected_at"] is not None
        print(f"✅ Rejected {run_id}, status: {data['status']}")

    def test_mark_approved_as_paid(self):
        """PATCH /api/finance/settlement-runs/{run_id}/mark-paid - Mark as paid (approved -> paid)"""
        # SR-005 is seeded as approved status
        run_id = "SR-005"
        payload = {"actor": "treasury"}
        response = requests.patch(f"{BASE_URL}/api/finance/settlement-runs/{run_id}/mark-paid", json=payload)
        assert response.status_code == 200
        data = _unwrap(response)
        assert data["status"] == "paid"
        assert data["paid_at"] is not None
        print(f"✅ Marked {run_id} as paid, paid_at: {data['paid_at']}")

    def test_invalid_transition_draft_to_approved_fails(self):
        """Invalid state transition: draft -> approved directly should fail"""
        # Create a fresh draft
        create_payload = {
            "run_type": "AGENCY",
            "entity_id": "AGN-TEST-002",
            "entity_name": "Test Invalid Transition",
            "period_start": "2026-03-01",
            "period_end": "2026-03-31",
            "currency": "EUR"
        }
        create_res = requests.post(f"{BASE_URL}/api/finance/settlement-runs", json=create_payload)
        assert create_res.status_code == 200
        run_id = _unwrap(create_res)["run_id"]
        
        # Try to approve directly (should fail - draft can only go to pending_approval)
        approve_payload = {"actor": "admin"}
        response = requests.patch(f"{BASE_URL}/api/finance/settlement-runs/{run_id}/approve", json=approve_payload)
        assert response.status_code == 400
        data = _unwrap(response)
        assert "error" in data
        assert "Invalid transition" in data["error"]
        print(f"✅ Invalid transition correctly rejected: {data['error']}")

    def test_invalid_transition_draft_to_paid_fails(self):
        """Invalid state transition: draft -> paid directly should fail"""
        # Create a fresh draft
        create_payload = {
            "run_type": "AGENCY",
            "entity_id": "AGN-TEST-003",
            "entity_name": "Test Invalid Paid Transition",
            "period_start": "2026-04-01",
            "period_end": "2026-04-30",
            "currency": "EUR"
        }
        create_res = requests.post(f"{BASE_URL}/api/finance/settlement-runs", json=create_payload)
        run_id = _unwrap(create_res)["run_id"]
        
        # Try to mark paid directly (should fail)
        response = requests.patch(f"{BASE_URL}/api/finance/settlement-runs/{run_id}/mark-paid", json={"actor": "admin"})
        assert response.status_code == 400
        print(f"✅ Invalid draft->paid transition correctly rejected")


class TestSettlementEntries:
    """Settlement entries management: add/remove entries from drafts"""

    def test_get_unassigned_entries(self):
        """GET /api/finance/settlement-runs/unassigned-entries - Get unassigned ledger entries"""
        response = requests.get(f"{BASE_URL}/api/finance/settlement-runs/unassigned-entries")
        assert response.status_code == 200
        data = _unwrap(response)
        assert isinstance(data, list)
        print(f"✅ Got {len(data)} unassigned entries")

    def test_get_unassigned_entries_with_filter(self):
        """GET unassigned entries with entity_type filter"""
        response = requests.get(f"{BASE_URL}/api/finance/settlement-runs/unassigned-entries?entity_type=AGENCY")
        assert response.status_code == 200
        data = _unwrap(response)
        assert isinstance(data, list)
        # All returned entries should be AGENCY type
        for entry in data:
            assert entry.get("entity_type") == "AGENCY"
        print(f"✅ Got {len(data)} unassigned AGENCY entries")

    def test_add_entries_to_draft(self):
        """POST /api/finance/settlement-runs/{run_id}/add-entries - Add entries to draft"""
        # Create a fresh draft
        create_payload = {
            "run_type": "AGENCY",
            "entity_id": "AGN-001",  # Use existing agency
            "entity_name": "Sunshine Travel",
            "period_start": "2026-01-01",
            "period_end": "2026-01-31",
            "currency": "EUR"
        }
        create_res = requests.post(f"{BASE_URL}/api/finance/settlement-runs", json=create_payload)
        run_id = _unwrap(create_res)["run_id"]
        
        # Get some unassigned entries
        unassigned_res = requests.get(f"{BASE_URL}/api/finance/settlement-runs/unassigned-entries?entity_id=AGN-001&limit=3")
        unassigned = _unwrap(unassigned_res)
        
        if len(unassigned) > 0:
            entry_ids = [e["entry_id"] for e in unassigned[:2]]
            add_payload = {"entry_ids": entry_ids}
            response = requests.post(f"{BASE_URL}/api/finance/settlement-runs/{run_id}/add-entries", json=add_payload)
            assert response.status_code == 200
            data = _unwrap(response)
            assert "linked" in data
            print(f"✅ Added {data['linked']} entries to {run_id}, total: {data['total_entries']}")
        else:
            print("⚠️ No unassigned entries found for AGN-001, skipping add test")

    def test_add_entries_to_non_draft_fails(self):
        """Adding entries to non-draft run should fail"""
        # SR-001 is seeded as paid status
        run_id = "SR-001"
        add_payload = {"entry_ids": ["LE-0001"]}
        response = requests.post(f"{BASE_URL}/api/finance/settlement-runs/{run_id}/add-entries", json=add_payload)
        assert response.status_code == 400
        data = _unwrap(response)
        assert "draft" in data["error"].lower()
        print(f"✅ Add to non-draft correctly rejected: {data['error']}")


class TestExceptionQueue:
    """Exception Queue: list, filter, resolve, dismiss"""

    def test_get_exceptions_list(self):
        """GET /api/finance/exceptions - List all exceptions"""
        response = requests.get(f"{BASE_URL}/api/finance/exceptions")
        assert response.status_code == 200
        data = _unwrap(response)
        assert "exceptions" in data
        assert "total" in data
        assert isinstance(data["exceptions"], list)
        print(f"✅ Got {data['total']} exceptions")

    def test_get_exceptions_filter_by_status(self):
        """GET /api/finance/exceptions?status=open - Filter by status"""
        response = requests.get(f"{BASE_URL}/api/finance/exceptions?status=open")
        assert response.status_code == 200
        data = _unwrap(response)
        for exc in data["exceptions"]:
            assert exc["status"] == "open"
        print(f"✅ Got {len(data['exceptions'])} open exceptions")

    def test_get_exceptions_filter_by_severity(self):
        """GET /api/finance/exceptions?severity=high - Filter by severity"""
        response = requests.get(f"{BASE_URL}/api/finance/exceptions?severity=high")
        assert response.status_code == 200
        data = _unwrap(response)
        for exc in data["exceptions"]:
            assert exc["severity"] == "high"
        print(f"✅ Got {len(data['exceptions'])} high severity exceptions")

    def test_get_exceptions_filter_by_type(self):
        """GET /api/finance/exceptions?exception_type=amount_mismatch - Filter by type"""
        response = requests.get(f"{BASE_URL}/api/finance/exceptions?exception_type=amount_mismatch")
        assert response.status_code == 200
        data = _unwrap(response)
        for exc in data["exceptions"]:
            assert exc["exception_type"] == "amount_mismatch"
        print(f"✅ Got {len(data['exceptions'])} amount_mismatch exceptions")

    def test_get_exception_stats(self):
        """GET /api/finance/exceptions/stats - Exception statistics"""
        response = requests.get(f"{BASE_URL}/api/finance/exceptions/stats")
        assert response.status_code == 200
        data = _unwrap(response)
        assert "total" in data
        assert "by_status" in data
        assert "by_severity" in data
        print(f"✅ Exception stats: total={data['total']}, by_status={list(data['by_status'].keys())}")

    def test_resolve_exception(self):
        """PATCH /api/finance/exceptions/{id}/resolve - Resolve an exception"""
        # EXC-001 is seeded as open status
        exc_id = "EXC-001"
        payload = {
            "resolution": "adjusted",
            "resolved_by": "finance_admin",
            "notes": "Amount corrected in ledger"
        }
        response = requests.patch(f"{BASE_URL}/api/finance/exceptions/{exc_id}/resolve", json=payload)
        assert response.status_code == 200
        data = _unwrap(response)
        assert data["status"] == "resolved"
        assert data["resolution"] == "adjusted"
        assert data["resolved_by"] == "finance_admin"
        assert data["resolved_at"] is not None
        print(f"✅ Resolved {exc_id}, resolved_at: {data['resolved_at']}")

    def test_dismiss_exception(self):
        """PATCH /api/finance/exceptions/{id}/dismiss - Dismiss an exception"""
        # EXC-002 is seeded as open status
        exc_id = "EXC-002"
        payload = {"reason": "False positive - data entry error"}
        response = requests.patch(f"{BASE_URL}/api/finance/exceptions/{exc_id}/dismiss", json=payload)
        assert response.status_code == 200
        data = _unwrap(response)
        assert data["status"] == "dismissed"
        assert data["dismissed_at"] is not None
        print(f"✅ Dismissed {exc_id}")

    def test_double_resolve_fails(self):
        """Double resolve should fail (already resolved)"""
        # EXC-005 is seeded as resolved status
        exc_id = "EXC-005"
        payload = {"resolution": "waived", "resolved_by": "admin"}
        response = requests.patch(f"{BASE_URL}/api/finance/exceptions/{exc_id}/resolve", json=payload)
        assert response.status_code == 400
        data = _unwrap(response)
        assert "already resolved" in data["error"].lower()
        print(f"✅ Double resolve correctly rejected: {data['error']}")

    def test_resolve_nonexistent_exception(self):
        """Resolve non-existent exception returns 404"""
        exc_id = "EXC-FAKE-999"
        payload = {"resolution": "adjusted", "resolved_by": "admin"}
        response = requests.patch(f"{BASE_URL}/api/finance/exceptions/{exc_id}/resolve", json=payload)
        assert response.status_code == 404
        print(f"✅ Non-existent exception correctly returns 404")


class TestFinanceOverview:
    """Finance Overview endpoint should include exception_stats"""

    def test_overview_includes_exception_stats(self):
        """GET /api/finance/ledger/overview - Should include exception_stats"""
        response = requests.get(f"{BASE_URL}/api/finance/ledger/overview")
        assert response.status_code == 200
        data = _unwrap(response)
        assert "exception_stats" in data
        assert "by_status" in data["exception_stats"]
        assert "by_severity" in data["exception_stats"]
        print(f"✅ Overview includes exception_stats: {list(data.keys())}")


class TestSettlementRunDetail:
    """Settlement Run detail and history"""

    def test_get_settlement_run_detail(self):
        """GET /api/finance/settlement-runs/{run_id} - Get detail"""
        run_id = "SR-001"
        response = requests.get(f"{BASE_URL}/api/finance/settlement-runs/{run_id}")
        assert response.status_code == 200
        data = _unwrap(response)
        assert data["run_id"] == run_id
        assert "history" in data or data.get("status") is not None
        print(f"✅ Got detail for {run_id}: status={data['status']}, amount={data.get('total_amount')}")

    def test_get_settlement_runs_list(self):
        """GET /api/finance/settlement-runs - List all runs"""
        response = requests.get(f"{BASE_URL}/api/finance/settlement-runs")
        assert response.status_code == 200
        data = _unwrap(response)
        assert "runs" in data
        assert len(data["runs"]) >= 5  # Seeded 5 runs
        print(f"✅ Listed {len(data['runs'])} settlement runs")

    def test_get_settlement_run_stats(self):
        """GET /api/finance/settlement-runs/stats - Stats by status"""
        response = requests.get(f"{BASE_URL}/api/finance/settlement-runs/stats")
        assert response.status_code == 200
        data = _unwrap(response)
        assert "by_status" in data
        print(f"✅ Settlement stats: {list(data['by_status'].keys())}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
