"""
Growth Engine API Tests - Iteration 89
Tests for Travel Platform Growth Engine with:
- Agency Acquisition Funnel (7 stages)
- Lead & Demo Management  
- Referral System (with fraud prevention & rewards)
- Activation Metrics
- Customer Success Dashboard
- Onboarding Automation
- Agency Segmentation
- Supplier Expansion Model
- Growth KPI Dashboard
- Full Growth Report (25 tasks, 15 risks)
"""
import pytest
import requests
import os
import time
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
SUPER_ADMIN = {"email": "agent@acenta.test", "password": "agent123"}


@pytest.fixture(scope="module")
def auth_session():
    """Get authenticated session for super_admin"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    
    # Login
    resp = session.post(f"{BASE_URL}/api/auth/login", json=SUPER_ADMIN)
    if resp.status_code != 200:
        pytest.skip(f"Auth failed: {resp.status_code} - {resp.text}")
    
    data = resp.json()
    token = data.get("access_token") or data.get("token")
    if token:
        session.headers.update({"Authorization": f"Bearer {token}"})
    
    return session


# =====================================================
# PART 1: FUNNEL METRICS
# =====================================================
class TestFunnel:
    """Agency Acquisition Funnel tests"""
    
    def test_get_funnel_metrics(self, auth_session):
        """GET /api/growth/funnel - Returns funnel stages with counts"""
        resp = auth_session.get(f"{BASE_URL}/api/growth/funnel")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        data = resp.json()
        assert "stages" in data, "Response should have 'stages'"
        assert "total_leads" in data, "Response should have 'total_leads'"
        assert "overall_conversion_pct" in data, "Response should have 'overall_conversion_pct'"
        
        # Verify 7 funnel stages
        stages = data["stages"]
        assert len(stages) == 7, f"Expected 7 stages, got {len(stages)}"
        
        stage_keys = [s["key"] for s in stages]
        expected_keys = ["lead_captured", "demo_scheduled", "demo_completed", 
                        "pilot_started", "first_search", "first_booking", "activated"]
        assert stage_keys == expected_keys, f"Stage keys mismatch: {stage_keys}"
        
        # Each stage should have count and conversion_pct
        for stage in stages:
            assert "count" in stage, f"Stage {stage['key']} missing count"
            assert "conversion_pct" in stage, f"Stage {stage['key']} missing conversion_pct"
        
        print(f"Funnel: {data['total_leads']} leads, {data['activated']} activated, {data['overall_conversion_pct']}% conversion")


# =====================================================
# PART 2: LEAD MANAGEMENT
# =====================================================
class TestLeads:
    """Lead & Demo Management tests"""
    
    def test_list_leads(self, auth_session):
        """GET /api/growth/leads - Lists all leads"""
        resp = auth_session.get(f"{BASE_URL}/api/growth/leads")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        data = resp.json()
        assert "leads" in data, "Response should have 'leads'"
        assert "count" in data, "Response should have 'count'"
        print(f"Found {data['count']} leads")
    
    def test_create_lead(self, auth_session):
        """POST /api/growth/leads - Create a new lead"""
        test_id = str(uuid.uuid4())[:8]
        payload = {
            "company_name": f"TEST_Company_{test_id}",
            "contact_name": "Test Contact",
            "contact_email": f"test_{test_id}@example.com",
            "contact_phone": "+90555123456",
            "source": "inbound"
        }
        
        resp = auth_session.post(f"{BASE_URL}/api/growth/leads", json=payload)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        data = resp.json()
        assert "lead_id" in data, "Response should have 'lead_id'"
        assert data["company_name"] == payload["company_name"], "Company name mismatch"
        assert data["stage"] == "lead_captured", "New lead should be at 'lead_captured' stage"
        
        print(f"Created lead: {data['lead_id']} - {data['company_name']}")
        return data["lead_id"]
    
    def test_update_lead_stage(self, auth_session):
        """PUT /api/growth/leads/{lead_id}/stage - Update lead stage"""
        # First create a lead
        test_id = str(uuid.uuid4())[:8]
        create_resp = auth_session.post(f"{BASE_URL}/api/growth/leads", json={
            "company_name": f"TEST_StageUpdate_{test_id}",
            "contact_name": "Stage Test"
        })
        assert create_resp.status_code == 200
        lead_id = create_resp.json()["lead_id"]
        
        # Update stage to demo_scheduled
        resp = auth_session.put(f"{BASE_URL}/api/growth/leads/{lead_id}/stage", json={
            "stage": "demo_scheduled"
        })
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        data = resp.json()
        assert data.get("updated") == True, "Should mark as updated"
        assert data.get("stage") == "demo_scheduled", "Stage should be demo_scheduled"
        
        print(f"Updated lead {lead_id} to stage: demo_scheduled")
    
    def test_update_lead_stage_invalid(self, auth_session):
        """PUT /api/growth/leads/{lead_id}/stage - Reject invalid stage"""
        # First create a lead
        test_id = str(uuid.uuid4())[:8]
        create_resp = auth_session.post(f"{BASE_URL}/api/growth/leads", json={
            "company_name": f"TEST_InvalidStage_{test_id}"
        })
        assert create_resp.status_code == 200
        lead_id = create_resp.json()["lead_id"]
        
        # Try invalid stage
        resp = auth_session.put(f"{BASE_URL}/api/growth/leads/{lead_id}/stage", json={
            "stage": "invalid_stage"
        })
        assert resp.status_code == 200  # Returns 200 with error in body
        data = resp.json()
        assert "error" in data, "Should return error for invalid stage"
        print(f"Correctly rejected invalid stage: {data.get('error')}")
    
    def test_update_lead_to_churned(self, auth_session):
        """PUT /api/growth/leads/{lead_id}/stage - Can set to 'churned'"""
        test_id = str(uuid.uuid4())[:8]
        create_resp = auth_session.post(f"{BASE_URL}/api/growth/leads", json={
            "company_name": f"TEST_Churned_{test_id}"
        })
        assert create_resp.status_code == 200
        lead_id = create_resp.json()["lead_id"]
        
        resp = auth_session.put(f"{BASE_URL}/api/growth/leads/{lead_id}/stage", json={
            "stage": "churned"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("stage") == "churned", "Should accept 'churned' as valid stage"
        print(f"Lead {lead_id} marked as churned")
    
    def test_list_leads_by_stage(self, auth_session):
        """GET /api/growth/leads?stage=X - Filter by stage"""
        resp = auth_session.get(f"{BASE_URL}/api/growth/leads?stage=lead_captured")
        assert resp.status_code == 200
        data = resp.json()
        # All returned leads should be at lead_captured stage
        for lead in data.get("leads", []):
            assert lead["stage"] == "lead_captured", f"Expected lead_captured, got {lead['stage']}"
        print(f"Found {data['count']} leads at lead_captured stage")


# =====================================================
# PART 3: DEMO MANAGEMENT
# =====================================================
class TestDemos:
    """Demo Management tests"""
    
    def test_list_demos(self, auth_session):
        """GET /api/growth/demos - Lists all demos"""
        resp = auth_session.get(f"{BASE_URL}/api/growth/demos")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        data = resp.json()
        assert "demos" in data, "Response should have 'demos'"
        assert "count" in data, "Response should have 'count'"
        print(f"Found {data['count']} demos")
    
    def test_create_demo(self, auth_session):
        """POST /api/growth/demos - Create a demo (sets lead stage to demo_scheduled)"""
        # First create a lead
        test_id = str(uuid.uuid4())[:8]
        lead_resp = auth_session.post(f"{BASE_URL}/api/growth/leads", json={
            "company_name": f"TEST_DemoCompany_{test_id}",
            "contact_name": "Demo Contact"
        })
        assert lead_resp.status_code == 200
        lead_id = lead_resp.json()["lead_id"]
        
        # Create demo for this lead
        demo_payload = {
            "lead_id": lead_id,
            "company_name": f"TEST_DemoCompany_{test_id}",
            "contact_name": "Demo Contact",
            "scheduled_at": "2026-02-01T10:00:00Z",
            "notes": "Test demo"
        }
        
        resp = auth_session.post(f"{BASE_URL}/api/growth/demos", json=demo_payload)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        data = resp.json()
        assert "demo_id" in data, "Response should have 'demo_id'"
        assert data["status"] == "scheduled", "New demo should be 'scheduled'"
        
        # Verify lead stage was updated
        lead_check = auth_session.get(f"{BASE_URL}/api/growth/leads")
        leads = lead_check.json().get("leads", [])
        created_lead = next((l for l in leads if l["lead_id"] == lead_id), None)
        if created_lead:
            assert created_lead["stage"] == "demo_scheduled", "Lead should be moved to demo_scheduled"
        
        print(f"Created demo: {data['demo_id']}, lead stage updated to demo_scheduled")
        return data["demo_id"]
    
    def test_update_demo_completed(self, auth_session):
        """PUT /api/growth/demos/{demo_id} - Update demo status/outcome"""
        # Create lead and demo
        test_id = str(uuid.uuid4())[:8]
        lead_resp = auth_session.post(f"{BASE_URL}/api/growth/leads", json={
            "company_name": f"TEST_DemoUpdate_{test_id}"
        })
        lead_id = lead_resp.json()["lead_id"]
        
        demo_resp = auth_session.post(f"{BASE_URL}/api/growth/demos", json={
            "lead_id": lead_id,
            "company_name": f"TEST_DemoUpdate_{test_id}",
            "scheduled_at": "2026-02-01T10:00:00Z"
        })
        demo_id = demo_resp.json()["demo_id"]
        
        # Update demo to completed
        resp = auth_session.put(f"{BASE_URL}/api/growth/demos/{demo_id}", json={
            "status": "completed",
            "outcome": "interested"
        })
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        data = resp.json()
        assert data.get("updated") == True, "Should mark as updated"
        
        # Verify lead stage was updated to demo_completed
        lead_check = auth_session.get(f"{BASE_URL}/api/growth/leads")
        leads = lead_check.json().get("leads", [])
        created_lead = next((l for l in leads if l["lead_id"] == lead_id), None)
        if created_lead:
            assert created_lead["stage"] == "demo_completed", "Lead should be at demo_completed"
        
        print(f"Demo {demo_id} completed, lead stage updated to demo_completed")


# =====================================================
# PART 4: REFERRAL SYSTEM
# =====================================================
class TestReferrals:
    """Referral System tests (fraud prevention & rewards)"""
    
    def test_list_referrals(self, auth_session):
        """GET /api/growth/referrals - Lists referrals with stats and reward rules"""
        resp = auth_session.get(f"{BASE_URL}/api/growth/referrals")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        data = resp.json()
        assert "referrals" in data, "Response should have 'referrals'"
        assert "stats" in data, "Response should have 'stats'"
        assert "reward_rules" in data, "Response should have 'reward_rules'"
        
        # Check reward rules structure
        rules = data["reward_rules"]
        assert "registered" in rules, "Should have 'registered' reward rule"
        assert "activated" in rules, "Should have 'activated' reward rule"
        
        print(f"Found {data['stats'].get('total', 0)} referrals, stats: {data['stats']}")
    
    def test_create_referral(self, auth_session):
        """POST /api/growth/referrals - Create referral"""
        test_id = str(uuid.uuid4())[:8]
        payload = {
            "referrer_agency_id": "test-agency",
            "referrer_name": "Test Referrer",
            "referred_company_name": f"TEST_RefCompany_{test_id}",
            "referred_contact_name": "Referred Contact",
            "referred_email": f"referred_{test_id}@example.com",
            "referred_phone": "+90555000111"
        }
        
        resp = auth_session.post(f"{BASE_URL}/api/growth/referrals", json=payload)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        data = resp.json()
        assert "referral_id" in data, "Response should have 'referral_id'"
        assert data["status"] == "pending", "New referral should be 'pending'"
        
        print(f"Created referral: {data['referral_id']} - {data['referred_company_name']}")
        return data["referral_id"], payload["referred_email"]
    
    def test_referral_fraud_prevention_duplicate_email(self, auth_session):
        """POST /api/growth/referrals - Rejects duplicate email (fraud prevention)"""
        test_id = str(uuid.uuid4())[:8]
        email = f"fraud_test_{test_id}@example.com"
        
        # First referral
        first_resp = auth_session.post(f"{BASE_URL}/api/growth/referrals", json={
            "referrer_name": "Referrer 1",
            "referred_company_name": f"TEST_Fraud1_{test_id}",
            "referred_email": email
        })
        assert first_resp.status_code == 200
        first_data = first_resp.json()
        assert "referral_id" in first_data, "First referral should succeed"
        
        # Second referral with same email - should be rejected
        second_resp = auth_session.post(f"{BASE_URL}/api/growth/referrals", json={
            "referrer_name": "Referrer 2",
            "referred_company_name": f"TEST_Fraud2_{test_id}",
            "referred_email": email
        })
        assert second_resp.status_code == 200
        second_data = second_resp.json()
        assert "error" in second_data, "Duplicate email should be rejected"
        
        print(f"Fraud prevention working: {second_data.get('error')}")
    
    def test_update_referral_status_with_reward(self, auth_session):
        """PUT /api/growth/referrals/{referral_id}/status - Status change applies reward rules"""
        # Create referral
        test_id = str(uuid.uuid4())[:8]
        create_resp = auth_session.post(f"{BASE_URL}/api/growth/referrals", json={
            "referrer_name": "Reward Test",
            "referred_company_name": f"TEST_Reward_{test_id}",
            "referred_email": f"reward_{test_id}@example.com"
        })
        assert create_resp.status_code == 200
        referral_id = create_resp.json()["referral_id"]
        
        # Update to 'registered' - should apply reward
        resp = auth_session.put(f"{BASE_URL}/api/growth/referrals/{referral_id}/status", json={
            "status": "registered"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("updated") == True, "Should mark as updated"
        
        # Verify reward was applied by checking referral list
        list_resp = auth_session.get(f"{BASE_URL}/api/growth/referrals")
        referrals = list_resp.json().get("referrals", [])
        updated_ref = next((r for r in referrals if r["referral_id"] == referral_id), None)
        
        assert updated_ref is not None, "Referral should exist"
        assert updated_ref["status"] == "registered", "Status should be updated"
        assert updated_ref.get("reward_type") == "discount", "Should have discount reward"
        assert updated_ref.get("reward_amount") == 10, "Should have 10% discount"
        
        print(f"Referral {referral_id} registered with reward: {updated_ref['reward_amount']}% discount")
    
    def test_update_referral_to_activated(self, auth_session):
        """PUT /api/growth/referrals/{referral_id}/status - 'activated' gives credit reward"""
        test_id = str(uuid.uuid4())[:8]
        create_resp = auth_session.post(f"{BASE_URL}/api/growth/referrals", json={
            "referrer_name": "Activate Test",
            "referred_company_name": f"TEST_Activate_{test_id}",
            "referred_email": f"activate_{test_id}@example.com"
        })
        referral_id = create_resp.json()["referral_id"]
        
        # Update directly to 'activated'
        resp = auth_session.put(f"{BASE_URL}/api/growth/referrals/{referral_id}/status", json={
            "status": "activated"
        })
        assert resp.status_code == 200
        
        # Verify credit reward
        list_resp = auth_session.get(f"{BASE_URL}/api/growth/referrals")
        referrals = list_resp.json().get("referrals", [])
        updated_ref = next((r for r in referrals if r["referral_id"] == referral_id), None)
        
        assert updated_ref["reward_type"] == "credit", "Should have credit reward"
        assert updated_ref["reward_amount"] == 50, "Should have 50 EUR credit"
        
        print(f"Referral {referral_id} activated with reward: {updated_ref['reward_amount']} EUR credit")


# =====================================================
# PART 5: ACTIVATION METRICS
# =====================================================
class TestActivation:
    """Activation Metrics tests"""
    
    def test_list_all_activations(self, auth_session):
        """GET /api/growth/activation - Lists all agency activations"""
        resp = auth_session.get(f"{BASE_URL}/api/growth/activation")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        data = resp.json()
        assert "agencies" in data, "Response should have 'agencies'"
        assert "total" in data, "Response should have 'total'"
        
        print(f"Found {data['total']} agencies with activation data")
    
    def test_get_agency_activation(self, auth_session):
        """GET /api/growth/activation/{agency_id} - Get activation score for specific agency"""
        test_agency_id = f"test-agency-{str(uuid.uuid4())[:8]}"
        
        resp = auth_session.get(f"{BASE_URL}/api/growth/activation/{test_agency_id}")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        data = resp.json()
        assert "agency_id" in data, "Response should have 'agency_id'"
        assert "activation_score" in data, "Response should have 'activation_score'"
        assert "status" in data, "Response should have 'status'"
        assert "milestones" in data, "Response should have 'milestones'"
        
        # Check 5 milestones
        milestones = data["milestones"]
        assert len(milestones) == 5, f"Expected 5 milestones, got {len(milestones)}"
        
        milestone_keys = [m["key"] for m in milestones]
        expected_keys = ["credential_entered", "connection_tested", "first_search", "first_booking", "first_revenue"]
        assert milestone_keys == expected_keys, f"Milestone keys mismatch: {milestone_keys}"
        
        print(f"Agency {test_agency_id}: score={data['activation_score']}, status={data['status']}")
    
    def test_record_activation_event(self, auth_session):
        """POST /api/growth/activation/{agency_id}/event - Record activation event"""
        test_agency_id = f"test-agency-{str(uuid.uuid4())[:8]}"
        
        resp = auth_session.post(f"{BASE_URL}/api/growth/activation/{test_agency_id}/event", json={
            "event_type": "credential_entered",
            "details": "Test credential entry"
        })
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        data = resp.json()
        assert data.get("event_type") == "credential_entered" or "message" in data
        
        # Record more events and check score
        auth_session.post(f"{BASE_URL}/api/growth/activation/{test_agency_id}/event", json={
            "event_type": "connection_tested"
        })
        auth_session.post(f"{BASE_URL}/api/growth/activation/{test_agency_id}/event", json={
            "event_type": "first_search"
        })
        
        # Verify score increased
        check_resp = auth_session.get(f"{BASE_URL}/api/growth/activation/{test_agency_id}")
        check_data = check_resp.json()
        
        # Score should be 60 (20+20+20) if 3 events recorded
        assert check_data["activation_score"] == 60, f"Expected score 60, got {check_data['activation_score']}"
        assert check_data["status"] == "progressing", "Status should be 'progressing' (score >= 40)"
        
        print(f"Agency {test_agency_id} activation score: {check_data['activation_score']}, status: {check_data['status']}")
    
    def test_record_duplicate_event(self, auth_session):
        """POST /api/growth/activation/{agency_id}/event - Duplicate event returns message"""
        test_agency_id = f"test-agency-{str(uuid.uuid4())[:8]}"
        
        # First event
        auth_session.post(f"{BASE_URL}/api/growth/activation/{test_agency_id}/event", json={
            "event_type": "first_booking"
        })
        
        # Duplicate event
        resp = auth_session.post(f"{BASE_URL}/api/growth/activation/{test_agency_id}/event", json={
            "event_type": "first_booking"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "message" in data, "Duplicate event should return message"
        print(f"Duplicate event handled: {data.get('message')}")
    
    def test_invalid_event_type(self, auth_session):
        """POST /api/growth/activation/{agency_id}/event - Reject invalid event type"""
        resp = auth_session.post(f"{BASE_URL}/api/growth/activation/test-agency/event", json={
            "event_type": "invalid_event"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "error" in data, "Should return error for invalid event type"
        print(f"Invalid event rejected: {data.get('error')}")


# =====================================================
# PART 6: CUSTOMER SUCCESS
# =====================================================
class TestCustomerSuccess:
    """Customer Success Dashboard tests"""
    
    def test_customer_success_dashboard(self, auth_session):
        """GET /api/growth/customer-success - Customer success dashboard with categorized agencies"""
        resp = auth_session.get(f"{BASE_URL}/api/growth/customer-success")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        data = resp.json()
        assert "summary" in data, "Response should have 'summary'"
        assert "success_playbook" in data, "Response should have 'success_playbook'"
        
        summary = data["summary"]
        expected_keys = ["total_agencies", "active", "dormant", "at_risk", "failed_connections", "zero_bookings"]
        for key in expected_keys:
            assert key in summary, f"Summary missing '{key}'"
        
        # Check playbook has triggers and actions
        playbook = data["success_playbook"]
        assert len(playbook) > 0, "Playbook should have entries"
        for entry in playbook:
            assert "trigger" in entry, "Playbook entry should have 'trigger'"
            assert "action" in entry, "Playbook entry should have 'action'"
        
        print(f"Customer Success: total={summary['total_agencies']}, active={summary['active']}, at_risk={summary['at_risk']}")


# =====================================================
# PART 7: ONBOARDING
# =====================================================
class TestOnboarding:
    """Onboarding Automation tests"""
    
    def test_get_onboarding_status(self, auth_session):
        """GET /api/growth/onboarding/{agency_id} - Get onboarding checklist"""
        test_agency_id = f"test-agency-{str(uuid.uuid4())[:8]}"
        
        resp = auth_session.get(f"{BASE_URL}/api/growth/onboarding/{test_agency_id}")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        data = resp.json()
        assert "agency_id" in data, "Response should have 'agency_id'"
        assert "checklist" in data, "Response should have 'checklist'"
        assert "progress_pct" in data, "Response should have 'progress_pct'"
        assert "triggers" in data, "Response should have 'triggers'"
        
        checklist = data["checklist"]
        assert len(checklist) == 8, f"Expected 8 checklist items, got {len(checklist)}"
        
        print(f"Onboarding for {test_agency_id}: {data['completed_count']}/{data['total_tasks']} ({data['progress_pct']}%)")
    
    def test_complete_onboarding_task(self, auth_session):
        """POST /api/growth/onboarding/{agency_id}/complete - Complete onboarding task"""
        test_agency_id = f"test-agency-{str(uuid.uuid4())[:8]}"
        
        resp = auth_session.post(f"{BASE_URL}/api/growth/onboarding/{test_agency_id}/complete", json={
            "task_key": "first_login"
        })
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        data = resp.json()
        assert data.get("completed") == True, "Task should be marked completed"
        
        # Verify progress increased
        check_resp = auth_session.get(f"{BASE_URL}/api/growth/onboarding/{test_agency_id}")
        check_data = check_resp.json()
        assert check_data["completed_count"] >= 1, "Should have at least 1 completed task"
        
        print(f"Completed task 'first_login' for {test_agency_id}")
    
    def test_complete_invalid_task(self, auth_session):
        """POST /api/growth/onboarding/{agency_id}/complete - Reject invalid task"""
        resp = auth_session.post(f"{BASE_URL}/api/growth/onboarding/test-agency/complete", json={
            "task_key": "invalid_task"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "error" in data, "Should return error for invalid task"
        print(f"Invalid task rejected: {data.get('error')}")


# =====================================================
# PART 8: SEGMENTATION
# =====================================================
class TestSegmentation:
    """Agency Segmentation tests"""
    
    def test_get_agency_segments(self, auth_session):
        """GET /api/growth/segments - Agency segmentation (enterprise/growth/starter/inactive)"""
        resp = auth_session.get(f"{BASE_URL}/api/growth/segments")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        data = resp.json()
        assert "segments" in data, "Response should have 'segments'"
        assert "summary" in data, "Response should have 'summary'"
        assert "segmentation_rules" in data, "Response should have 'segmentation_rules'"
        
        # Check all 4 segments exist
        segments = data["segments"]
        expected_segments = ["enterprise", "growth", "starter", "inactive"]
        for seg in expected_segments:
            assert seg in segments, f"Missing segment: {seg}"
        
        # Check summary counts
        summary = data["summary"]
        for seg in expected_segments:
            assert seg in summary, f"Summary missing '{seg}'"
        
        print(f"Segmentation: enterprise={summary['enterprise']}, growth={summary['growth']}, starter={summary['starter']}, inactive={summary['inactive']}")


# =====================================================
# PART 9: SUPPLIER EXPANSION
# =====================================================
class TestSupplierExpansion:
    """Supplier Expansion Model tests"""
    
    def test_list_supplier_requests(self, auth_session):
        """GET /api/growth/supplier-requests - List supplier expansion requests"""
        resp = auth_session.get(f"{BASE_URL}/api/growth/supplier-requests")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        data = resp.json()
        assert "requests" in data, "Response should have 'requests'"
        assert "total" in data, "Response should have 'total'"
        
        print(f"Found {data['total']} supplier expansion requests")
    
    def test_create_supplier_request(self, auth_session):
        """POST /api/growth/supplier-requests - Create supplier request"""
        test_id = str(uuid.uuid4())[:8]
        payload = {
            "supplier_name": f"TEST_Supplier_{test_id}",
            "supplier_type": "hotel",
            "region": "Europe",
            "requested_by": "test-user",
            "notes": "Test request"
        }
        
        resp = auth_session.post(f"{BASE_URL}/api/growth/supplier-requests", json=payload)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        data = resp.json()
        assert "request_id" in data or "message" in data, "Response should have request_id or message"
        
        if "request_id" in data:
            assert data["demand_count"] == 1, "New request should have demand_count=1"
            print(f"Created supplier request: {data['request_id']} - {data['supplier_name']}")
            return data["request_id"]
        else:
            print(f"Existing supplier updated: {data.get('message')}")
    
    def test_supplier_request_increments_demand(self, auth_session):
        """POST /api/growth/supplier-requests - Increments demand if exists"""
        test_id = str(uuid.uuid4())[:8]
        supplier_name = f"TEST_DemandInc_{test_id}"
        
        # First request
        first_resp = auth_session.post(f"{BASE_URL}/api/growth/supplier-requests", json={
            "supplier_name": supplier_name,
            "supplier_type": "flight",
            "requested_by": "user1"
        })
        assert first_resp.status_code == 200
        first_data = first_resp.json()
        assert "request_id" in first_data, "First request should create new entry"
        
        # Second request for same supplier - should increment demand
        second_resp = auth_session.post(f"{BASE_URL}/api/growth/supplier-requests", json={
            "supplier_name": supplier_name,
            "supplier_type": "flight",
            "requested_by": "user2"
        })
        assert second_resp.status_code == 200
        second_data = second_resp.json()
        assert "message" in second_data, "Second request should increment existing"
        
        print(f"Demand incremented for {supplier_name}: {second_data.get('message')}")
    
    def test_update_supplier_request_status(self, auth_session):
        """PUT /api/growth/supplier-requests/{request_id} - Update supplier request status"""
        test_id = str(uuid.uuid4())[:8]
        # Create request
        create_resp = auth_session.post(f"{BASE_URL}/api/growth/supplier-requests", json={
            "supplier_name": f"TEST_Update_{test_id}",
            "supplier_type": "tour"
        })
        assert create_resp.status_code == 200
        request_id = create_resp.json().get("request_id")
        
        if not request_id:
            pytest.skip("Could not get request_id")
        
        # Update status
        resp = auth_session.put(f"{BASE_URL}/api/growth/supplier-requests/{request_id}", json={
            "status": "in_progress",
            "priority_score": 80
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("updated") == True, "Should mark as updated"
        
        print(f"Updated supplier request {request_id} to in_progress")


# =====================================================
# PART 10: GROWTH KPIs
# =====================================================
class TestGrowthKPIs:
    """Growth KPI Dashboard tests"""
    
    def test_get_growth_kpis(self, auth_session):
        """GET /api/growth/kpis - Growth KPIs (default 30 days)"""
        resp = auth_session.get(f"{BASE_URL}/api/growth/kpis")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        data = resp.json()
        assert "period_days" in data, "Response should have 'period_days'"
        assert "kpis" in data, "Response should have 'kpis'"
        assert "funnel_distribution" in data, "Response should have 'funnel_distribution'"
        
        kpis = data["kpis"]
        expected_kpis = [
            "new_leads", "total_leads", "activated_agencies", "first_booking_rate_pct",
            "total_referrals", "referral_conversions", "referral_conversion_rate_pct",
            "bookings_period", "pending_supplier_requests"
        ]
        for kpi in expected_kpis:
            assert kpi in kpis, f"KPIs missing '{kpi}'"
        
        print(f"KPIs (last {data['period_days']} days): leads={kpis['total_leads']}, activated={kpis['activated_agencies']}")
    
    def test_get_growth_kpis_custom_period(self, auth_session):
        """GET /api/growth/kpis?days=7 - Custom period"""
        resp = auth_session.get(f"{BASE_URL}/api/growth/kpis?days=7")
        assert resp.status_code == 200
        data = resp.json()
        assert data["period_days"] == 7, "Period should be 7 days"
        print(f"KPIs for 7 days: {data['kpis']}")


# =====================================================
# PART 11: FULL GROWTH REPORT
# =====================================================
class TestGrowthReport:
    """Full Growth Report tests (25 tasks, 15 risks)"""
    
    def test_get_growth_report(self, auth_session):
        """GET /api/growth/report - Full growth report with maturity score, tasks, risks"""
        resp = auth_session.get(f"{BASE_URL}/api/growth/report")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        
        data = resp.json()
        
        # Check maturity score
        assert "growth_maturity_score" in data, "Response should have 'growth_maturity_score'"
        assert "dimension_scores" in data, "Response should have 'dimension_scores'"
        
        # Check tasks - should have 25
        assert "implementation_tasks" in data, "Response should have 'implementation_tasks'"
        tasks = data["implementation_tasks"]
        assert len(tasks) == 25, f"Expected 25 tasks, got {len(tasks)}"
        
        # Check tasks have priority
        for task in tasks:
            assert "priority" in task, "Task should have 'priority'"
            assert "task" in task, "Task should have 'task'"
            assert task["priority"] in ["P0", "P1", "P2"], f"Invalid priority: {task['priority']}"
        
        # Check risks - should have 15
        assert "growth_risks" in data, "Response should have 'growth_risks'"
        risks = data["growth_risks"]
        assert len(risks) == 15, f"Expected 15 risks, got {len(risks)}"
        
        # Check risks have severity
        for risk in risks:
            assert "risk" in risk, "Risk should have 'risk'"
            assert "severity" in risk, "Risk should have 'severity'"
            assert "mitigation" in risk, "Risk should have 'mitigation'"
            assert risk["severity"] in ["high", "medium", "low"], f"Invalid severity: {risk['severity']}"
        
        # Check KPIs and summaries
        assert "kpis" in data, "Response should have 'kpis'"
        assert "funnel_summary" in data, "Response should have 'funnel_summary'"
        assert "segments_summary" in data, "Response should have 'segments_summary'"
        assert "customer_success_summary" in data, "Response should have 'customer_success_summary'"
        
        print(f"Growth Maturity Score: {data['growth_maturity_score']}/10")
        print(f"Tasks: P0={sum(1 for t in tasks if t['priority']=='P0')}, P1={sum(1 for t in tasks if t['priority']=='P1')}, P2={sum(1 for t in tasks if t['priority']=='P2')}")
        print(f"Risks: high={sum(1 for r in risks if r['severity']=='high')}, medium={sum(1 for r in risks if r['severity']=='medium')}, low={sum(1 for r in risks if r['severity']=='low')}")


# =====================================================
# RUN TESTS
# =====================================================
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
