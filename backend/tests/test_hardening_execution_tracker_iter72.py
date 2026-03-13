"""
Platform Hardening Execution Tracker Tests (Iteration 72)

Tests the NEW execution tracking system:
- GET /api/hardening/status returns dual scores (architecture_maturity, production_readiness) and blockers
- GET /api/hardening/execution/status returns all 10 phases, 3 sprints, 6 blockers, readiness scores
- GET /api/hardening/execution/phase/{id} returns phase detail with tasks
- POST /api/hardening/execution/phase/{id}/start marks phase as in_progress
- POST /api/hardening/execution/phase/{id}/task/{task_id}/complete marks task as completed
- POST /api/hardening/execution/blocker/{blocker_id}/resolve marks blocker as resolved
- GET /api/hardening/execution/certification returns go-live certification report
"""

import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    BASE_URL = "https://agency-marketplace-1.preview.emergentagent.com"


@pytest.fixture(scope="module")
def auth_session():
    """Module-scoped authenticated session for super_admin."""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    
    # Login with super_admin credentials
    login_response = session.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "agent@acenta.test", "password": "agent123"}
    )
    assert login_response.status_code == 200, f"Login failed: {login_response.text}"
    
    data = login_response.json()
    token = data.get("access_token") or data.get("token")
    if token:
        session.headers.update({"Authorization": f"Bearer {token}"})
    
    return session


# ============================================================================
# Test Dual Score System: GET /api/hardening/status
# ============================================================================

class TestDualScoreStatus:
    """Test the updated /api/hardening/status with dual scoring system."""

    def test_status_returns_dual_scores(self, auth_session):
        """GET /api/hardening/status should return architecture_maturity AND production_readiness scores."""
        response = auth_session.get(f"{BASE_URL}/api/hardening/status")
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        
        # Verify dual scores exist
        assert "architecture_maturity" in data, "Missing architecture_maturity score"
        assert "production_readiness" in data, "Missing production_readiness score"
        
        # Verify architecture maturity is around 9.2 as per CTO assessment
        arch_score = data["architecture_maturity"]
        assert isinstance(arch_score, (int, float)), f"architecture_maturity should be number, got {type(arch_score)}"
        assert 9.0 <= arch_score <= 10.0, f"Architecture maturity should be ~9.2, got {arch_score}"
        
        # Verify production readiness starts at 0 (no execution done)
        prod_score = data["production_readiness"]
        assert isinstance(prod_score, (int, float)), f"production_readiness should be number, got {type(prod_score)}"
        assert 0.0 <= prod_score <= 10.0, f"Production readiness out of range: {prod_score}"
        
        print(f"✓ Dual scores: architecture_maturity={arch_score}, production_readiness={prod_score}")

    def test_status_returns_architecture_breakdown(self, auth_session):
        """GET /api/hardening/status should return architecture breakdown by category."""
        response = auth_session.get(f"{BASE_URL}/api/hardening/status")
        assert response.status_code == 200
        
        data = response.json()
        
        # Verify architecture breakdown exists
        assert "architecture_breakdown" in data, "Missing architecture_breakdown"
        breakdown = data["architecture_breakdown"]
        
        # Expected categories from CTO assessment
        expected_categories = ["architecture", "reliability", "security", "domain_model", "operations"]
        for cat in expected_categories:
            assert cat in breakdown, f"Missing category: {cat}"
            assert isinstance(breakdown[cat], (int, float)), f"Category {cat} should be number"
            assert 8.0 <= breakdown[cat] <= 10.0, f"Category {cat} score out of expected range"
        
        print(f"✓ Architecture breakdown: {breakdown}")

    def test_status_returns_blockers(self, auth_session):
        """GET /api/hardening/status should return blocker information."""
        response = auth_session.get(f"{BASE_URL}/api/hardening/status")
        assert response.status_code == 200
        
        data = response.json()
        
        # Verify blockers object exists
        assert "blockers" in data, "Missing blockers section"
        blockers = data["blockers"]
        
        assert "total" in blockers, "Missing blockers.total"
        assert "open" in blockers, "Missing blockers.open"
        assert "resolved" in blockers, "Missing blockers.resolved"
        
        # Should have 6 total blockers initially
        assert blockers["total"] >= 6, f"Expected at least 6 blockers, got {blockers['total']}"
        
        print(f"✓ Blockers: total={blockers['total']}, open={blockers['open']}, resolved={blockers['resolved']}")


# ============================================================================
# Test Execution Status: GET /api/hardening/execution/status
# ============================================================================

class TestExecutionStatus:
    """Test GET /api/hardening/execution/status endpoint."""

    def test_execution_status_returns_all_phases(self, auth_session):
        """GET /api/hardening/execution/status should return all 10 phases."""
        response = auth_session.get(f"{BASE_URL}/api/hardening/execution/status")
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        
        # Verify phases exist
        assert "phases" in data, "Missing phases array"
        phases = data["phases"]
        
        assert len(phases) == 10, f"Expected 10 phases, got {len(phases)}"
        
        # Verify each phase has required fields
        for phase in phases:
            assert "id" in phase
            assert "name" in phase
            assert "sprint" in phase
            assert "priority" in phase
            assert "status" in phase
            assert "total_tasks" in phase
            assert "completed_tasks" in phase
            assert "progress_pct" in phase
        
        print(f"✓ Execution status has {len(phases)} phases")

    def test_execution_status_returns_sprints(self, auth_session):
        """GET /api/hardening/execution/status should return 3 sprints with progress."""
        response = auth_session.get(f"{BASE_URL}/api/hardening/execution/status")
        assert response.status_code == 200
        
        data = response.json()
        
        # Verify sprints exist
        assert "sprints" in data, "Missing sprints object"
        sprints = data["sprints"]
        
        # Should have 3 sprints
        expected_sprints = ["sprint_1", "sprint_2", "sprint_3"]
        for sprint_key in expected_sprints:
            assert sprint_key in sprints, f"Missing {sprint_key}"
            sprint = sprints[sprint_key]
            assert "phases" in sprint
            assert "total_tasks" in sprint
            assert "completed_tasks" in sprint
            assert "progress_pct" in sprint
        
        # Verify sprint distribution: Sprint 1 has 4 phases (20 tasks), Sprint 2 has 1 phase (5 tasks), Sprint 3 has 5 phases (21 tasks)
        assert sprints["sprint_1"]["phases"] == 4, f"Sprint 1 should have 4 phases"
        assert sprints["sprint_2"]["phases"] == 1, f"Sprint 2 should have 1 phase"
        assert sprints["sprint_3"]["phases"] == 5, f"Sprint 3 should have 5 phases"
        
        print(f"✓ Sprints: {sprints}")

    def test_execution_status_returns_blockers(self, auth_session):
        """GET /api/hardening/execution/status should return 6 blockers."""
        response = auth_session.get(f"{BASE_URL}/api/hardening/execution/status")
        assert response.status_code == 200
        
        data = response.json()
        
        # Verify blockers exist
        assert "blockers" in data, "Missing blockers array"
        blockers = data["blockers"]
        
        assert len(blockers) >= 6, f"Expected at least 6 blockers, got {len(blockers)}"
        
        # Verify blocker structure
        for blocker in blockers:
            assert "id" in blocker
            assert "blocker" in blocker
            assert "risk" in blocker
            assert "category" in blocker
            assert "fix_strategy" in blocker
            assert "status" in blocker
            assert "phase" in blocker
        
        # Check specific blocker IDs exist
        blocker_ids = [b["id"] for b in blockers]
        expected_ids = ["BLK-001", "BLK-002", "BLK-003", "BLK-004", "BLK-005", "BLK-006"]
        for expected_id in expected_ids:
            assert expected_id in blocker_ids, f"Missing blocker: {expected_id}"
        
        print(f"✓ Found {len(blockers)} blockers: {blocker_ids}")

    def test_execution_status_returns_readiness(self, auth_session):
        """GET /api/hardening/execution/status should return readiness scores."""
        response = auth_session.get(f"{BASE_URL}/api/hardening/execution/status")
        assert response.status_code == 200
        
        data = response.json()
        
        # Verify readiness object exists
        assert "readiness" in data, "Missing readiness object"
        readiness = data["readiness"]
        
        assert "architecture_maturity_score" in readiness
        assert "production_readiness_score" in readiness
        assert "total_tasks" in readiness
        assert "completed_tasks" in readiness
        assert "completion_pct" in readiness
        assert "open_blockers" in readiness
        assert "go_live_ready" in readiness
        assert "target_score" in readiness
        
        # Verify target is 8.5
        assert readiness["target_score"] == 8.5
        
        print(f"✓ Readiness: arch={readiness['architecture_maturity_score']}, prod={readiness['production_readiness_score']}, tasks={readiness['completed_tasks']}/{readiness['total_tasks']}")


# ============================================================================
# Test Phase Detail: GET /api/hardening/execution/phase/{id}
# ============================================================================

class TestPhaseDetail:
    """Test GET /api/hardening/execution/phase/{id} endpoint."""

    def test_phase_detail_returns_tasks(self, auth_session):
        """GET /api/hardening/execution/phase/1 should return phase 1 with all tasks."""
        response = auth_session.get(f"{BASE_URL}/api/hardening/execution/phase/1")
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        
        # Verify phase structure
        assert data.get("id") == 1
        assert "name" in data
        assert "sprint" in data
        assert "tasks" in data
        assert "description" in data
        assert "priority" in data
        
        # Phase 1 should have 6 tasks
        tasks = data["tasks"]
        assert len(tasks) == 6, f"Phase 1 should have 6 tasks, got {len(tasks)}"
        
        # Verify task structure
        for task in tasks:
            assert "id" in task
            assert "name" in task
            assert "status" in task
            assert "category" in task
        
        print(f"✓ Phase 1: '{data['name']}' with {len(tasks)} tasks")

    def test_phase_detail_invalid_id(self, auth_session):
        """GET /api/hardening/execution/phase/999 should return error."""
        response = auth_session.get(f"{BASE_URL}/api/hardening/execution/phase/999")
        assert response.status_code == 200  # Returns 200 with error field
        
        data = response.json()
        assert "error" in data
        
        print("✓ Invalid phase ID returns error")


# ============================================================================
# Test Phase Start: POST /api/hardening/execution/phase/{id}/start
# ============================================================================

class TestPhaseStart:
    """Test POST /api/hardening/execution/phase/{id}/start endpoint."""

    def test_start_phase(self, auth_session):
        """POST /api/hardening/execution/phase/1/start should mark phase as in_progress."""
        response = auth_session.post(f"{BASE_URL}/api/hardening/execution/phase/1/start")
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        
        assert data.get("status") == "started"
        assert data.get("phase_id") == 1
        assert "name" in data
        
        # Verify phase is now in_progress
        check_response = auth_session.get(f"{BASE_URL}/api/hardening/execution/phase/1")
        check_data = check_response.json()
        assert check_data.get("status") == "in_progress"
        
        print(f"✓ Phase 1 started: {data}")


# ============================================================================
# Test Task Complete: POST /api/hardening/execution/phase/{id}/task/{task_id}/complete
# ============================================================================

class TestTaskComplete:
    """Test POST /api/hardening/execution/phase/{id}/task/{task_id}/complete endpoint."""

    def test_complete_task(self, auth_session):
        """POST /api/hardening/execution/phase/1/task/1.1/complete should mark task as completed."""
        response = auth_session.post(f"{BASE_URL}/api/hardening/execution/phase/1/task/1.1/complete")
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        
        assert data.get("status") == "completed"
        assert data.get("task_id") == "1.1"
        assert "phase_status" in data
        assert "phase_complete" in data
        
        # Verify task is now completed
        check_response = auth_session.get(f"{BASE_URL}/api/hardening/execution/phase/1")
        check_data = check_response.json()
        task_1_1 = next((t for t in check_data["tasks"] if t["id"] == "1.1"), None)
        assert task_1_1 is not None
        assert task_1_1["status"] == "completed"
        
        print(f"✓ Task 1.1 completed: {data}")

    def test_complete_task_invalid(self, auth_session):
        """POST /api/hardening/execution/phase/1/task/invalid/complete should return error."""
        response = auth_session.post(f"{BASE_URL}/api/hardening/execution/phase/1/task/99.99/complete")
        assert response.status_code == 200  # Returns 200 with error field
        
        data = response.json()
        assert "error" in data
        
        print("✓ Invalid task ID returns error")


# ============================================================================
# Test Blocker Resolve: POST /api/hardening/execution/blocker/{blocker_id}/resolve
# ============================================================================

class TestBlockerResolve:
    """Test POST /api/hardening/execution/blocker/{blocker_id}/resolve endpoint."""

    def test_resolve_blocker(self, auth_session):
        """POST /api/hardening/execution/blocker/BLK-002/resolve should mark blocker as resolved."""
        response = auth_session.post(f"{BASE_URL}/api/hardening/execution/blocker/BLK-002/resolve")
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        
        assert data.get("status") == "resolved"
        assert data.get("blocker_id") == "BLK-002"
        
        # Verify blocker is now resolved in status
        check_response = auth_session.get(f"{BASE_URL}/api/hardening/execution/status")
        check_data = check_response.json()
        blocker = next((b for b in check_data["blockers"] if b["id"] == "BLK-002"), None)
        assert blocker is not None
        assert blocker["status"] == "resolved"
        
        print(f"✓ Blocker BLK-002 resolved: {data}")

    def test_resolve_blocker_invalid(self, auth_session):
        """POST /api/hardening/execution/blocker/INVALID/resolve should return error."""
        response = auth_session.post(f"{BASE_URL}/api/hardening/execution/blocker/INVALID/resolve")
        assert response.status_code == 200  # Returns 200 with error field
        
        data = response.json()
        assert "error" in data
        
        print("✓ Invalid blocker ID returns error")


# ============================================================================
# Test Certification: GET /api/hardening/execution/certification
# ============================================================================

class TestCertification:
    """Test GET /api/hardening/execution/certification endpoint."""

    def test_certification_report(self, auth_session):
        """GET /api/hardening/execution/certification should return full certification report."""
        response = auth_session.get(f"{BASE_URL}/api/hardening/execution/certification")
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        
        # Verify certification report structure
        assert "timestamp" in data
        assert "architecture_maturity" in data
        assert "architecture_breakdown" in data
        assert "production_readiness" in data
        assert "target_readiness" in data
        assert "gap" in data
        assert "certified" in data
        assert "phases_completed" in data
        assert "phases_total" in data
        assert "blockers_resolved" in data
        assert "blockers_open" in data
        assert "risk_level" in data
        assert "recommendation" in data
        
        # Verify target is 8.5
        assert data["target_readiness"] == 8.5
        
        # Verify architecture maturity is high (~9.2)
        assert data["architecture_maturity"] >= 9.0
        
        # Verify phases total is 10
        assert data["phases_total"] == 10
        
        print(f"✓ Certification: certified={data['certified']}, risk={data['risk_level']}, gap={data['gap']}")
        print(f"  Recommendation: {data['recommendation']}")


# ============================================================================
# Test Auth Required
# ============================================================================

class TestAuthRequired:
    """Test that all execution endpoints require authentication."""

    def test_execution_status_requires_auth(self):
        """GET /api/hardening/execution/status should require auth."""
        response = requests.get(f"{BASE_URL}/api/hardening/execution/status")
        assert response.status_code == 401
        print("✓ /api/hardening/execution/status requires auth")

    def test_phase_detail_requires_auth(self):
        """GET /api/hardening/execution/phase/1 should require auth."""
        response = requests.get(f"{BASE_URL}/api/hardening/execution/phase/1")
        assert response.status_code == 401
        print("✓ /api/hardening/execution/phase/1 requires auth")

    def test_certification_requires_auth(self):
        """GET /api/hardening/execution/certification should require auth."""
        response = requests.get(f"{BASE_URL}/api/hardening/execution/certification")
        assert response.status_code == 401
        print("✓ /api/hardening/execution/certification requires auth")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
