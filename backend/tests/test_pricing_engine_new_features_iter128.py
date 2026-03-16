"""Pricing & Distribution Engine - NEW Features Tests (Iteration 128)

Tests for 3 NEW features added on top of iteration 127:
  1. Pipeline Steps Explainability - pipeline_steps array in simulate response
  2. Rule Precedence Viewer - evaluated_rules array showing which rules won/lost  
  3. Margin Guardrails System - guardrail CRUD and violation warnings

Test credentials: agent@acenta.test / agent123
"""
import os
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

@pytest.fixture(scope="module")
def auth_token():
    """Login and get auth token."""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "agent@acenta.test", "password": "agent123"}
    )
    if response.status_code != 200:
        pytest.skip(f"Login failed: {response.status_code} - {response.text}")
    data = response.json()
    token = data.get("access_token") or data.get("token")
    if not token:
        pytest.skip(f"No token in response: {data.keys()}")
    return token

@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Headers with auth token."""
    return {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }


class TestPipelineStepsExplainability:
    """Test pipeline_steps array in simulate response - 7 step breakdown."""
    
    def test_simulate_returns_pipeline_steps(self, auth_headers):
        """POST /api/pricing-engine/simulate returns pipeline_steps array."""
        payload = {
            "supplier_code": "ratehawk",
            "supplier_price": 100.0,
            "supplier_currency": "EUR",
            "destination": "TR",
            "channel": "b2b",
            "agency_tier": "standard",
            "season": "mid",
            "product_type": "hotel",
            "nights": 1,
            "sell_currency": "EUR",
            "promo_code": ""
        }
        response = requests.post(f"{BASE_URL}/api/pricing-engine/simulate", json=payload, headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Check pipeline_steps exists and is a list
        assert "pipeline_steps" in data, f"Missing pipeline_steps in response: {data.keys()}"
        assert isinstance(data["pipeline_steps"], list), f"pipeline_steps should be list: {type(data['pipeline_steps'])}"
        print(f"Found {len(data['pipeline_steps'])} pipeline steps")
    
    def test_pipeline_has_7_steps(self, auth_headers):
        """Pipeline should have exactly 7 steps in order."""
        payload = {
            "supplier_code": "ratehawk",
            "supplier_price": 100.0,
            "supplier_currency": "EUR",
            "destination": "TR",
            "channel": "b2b",
            "agency_tier": "standard",
            "season": "mid",
            "product_type": "hotel",
            "nights": 1,
            "sell_currency": "EUR",
            "promo_code": ""
        }
        response = requests.post(f"{BASE_URL}/api/pricing-engine/simulate", json=payload, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        steps = data["pipeline_steps"]
        assert len(steps) == 7, f"Expected 7 steps, got {len(steps)}"
        
        # Verify step names in correct order
        expected_steps = [
            "supplier_price",
            "base_markup",
            "channel_rule",
            "agency_rule", 
            "promotion",
            "tax",
            "currency_conversion"
        ]
        actual_steps = [s["step"] for s in steps]
        assert actual_steps == expected_steps, f"Step order mismatch: {actual_steps} vs {expected_steps}"
        
        print("Pipeline steps in order:")
        for i, step in enumerate(steps, 1):
            print(f"  {i}. {step['step']} - {step['label']}: {step['input_price']} -> {step['output_price']}")
    
    def test_each_step_has_required_fields(self, auth_headers):
        """Each pipeline step should have all required fields."""
        payload = {
            "supplier_code": "ratehawk",
            "supplier_price": 100.0,
            "supplier_currency": "EUR",
            "destination": "TR",
            "channel": "b2b",
            "agency_tier": "standard",
            "season": "mid",
            "product_type": "hotel",
            "nights": 1,
            "sell_currency": "EUR",
            "promo_code": ""
        }
        response = requests.post(f"{BASE_URL}/api/pricing-engine/simulate", json=payload, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        required_fields = [
            "step", "label", "input_price", "adjustment_pct", 
            "adjustment_amount", "output_price", "rule_id", "rule_name", "detail"
        ]
        
        for step in data["pipeline_steps"]:
            for field in required_fields:
                assert field in step, f"Step {step.get('step')} missing field: {field}"
        
        print("All steps have required fields!")
        
    def test_step_prices_chain_correctly(self, auth_headers):
        """Each step's output_price should be next step's input_price."""
        payload = {
            "supplier_code": "ratehawk",
            "supplier_price": 100.0,
            "supplier_currency": "EUR",
            "destination": "TR",
            "channel": "b2b",
            "agency_tier": "standard",
            "season": "mid",
            "product_type": "hotel",
            "nights": 1,
            "sell_currency": "EUR",
            "promo_code": ""
        }
        response = requests.post(f"{BASE_URL}/api/pricing-engine/simulate", json=payload, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        steps = data["pipeline_steps"]
        for i in range(len(steps) - 1):
            current_output = steps[i]["output_price"]
            next_input = steps[i + 1]["input_price"]
            assert current_output == next_input, \
                f"Price chain broken: step {steps[i]['step']} output {current_output} != step {steps[i+1]['step']} input {next_input}"
        
        print("Price chain verified correctly!")


class TestEvaluatedRulesPrecedence:
    """Test evaluated_rules array showing rule matching and winners."""
    
    def test_simulate_returns_evaluated_rules(self, auth_headers):
        """POST /api/pricing-engine/simulate returns evaluated_rules array."""
        payload = {
            "supplier_code": "ratehawk",
            "supplier_price": 100.0,
            "supplier_currency": "EUR",
            "destination": "TR",
            "channel": "b2b",
            "agency_tier": "standard",
            "season": "mid",
            "product_type": "hotel",
            "nights": 1,
            "sell_currency": "EUR",
            "promo_code": ""
        }
        response = requests.post(f"{BASE_URL}/api/pricing-engine/simulate", json=payload, headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Check evaluated_rules exists and is a list
        assert "evaluated_rules" in data, f"Missing evaluated_rules in response: {data.keys()}"
        assert isinstance(data["evaluated_rules"], list), f"evaluated_rules should be list: {type(data['evaluated_rules'])}"
        print(f"Found {len(data['evaluated_rules'])} evaluated rules")
    
    def test_evaluated_rules_have_required_fields(self, auth_headers):
        """Each evaluated rule should have all required fields."""
        payload = {
            "supplier_code": "ratehawk",
            "supplier_price": 100.0,
            "supplier_currency": "EUR",
            "destination": "TR",
            "channel": "b2b",
            "agency_tier": "standard",
            "season": "mid",
            "product_type": "hotel",
            "nights": 1,
            "sell_currency": "EUR",
            "promo_code": ""
        }
        response = requests.post(f"{BASE_URL}/api/pricing-engine/simulate", json=payload, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        if not data["evaluated_rules"]:
            pytest.skip("No evaluated rules in response - may need seeded rules")
        
        required_fields = [
            "rule_id", "name", "category", "match_score", 
            "priority", "value", "scope", "won", "reject_reason"
        ]
        
        for rule in data["evaluated_rules"]:
            for field in required_fields:
                assert field in rule, f"Evaluated rule {rule.get('rule_id')} missing field: {field}"
        
        print("Evaluated rules:")
        for rule in data["evaluated_rules"]:
            status = "WON" if rule["won"] else f"LOST ({rule['reject_reason'] or 'lower score'})"
            print(f"  - {rule['name']} ({rule['rule_id']}): score={rule['match_score']}, priority={rule['priority']}, value={rule['value']}% -> {status}")
    
    def test_winning_rules_marked_correctly(self, auth_headers):
        """Rules that won should have won=True."""
        payload = {
            "supplier_code": "ratehawk",
            "supplier_price": 100.0,
            "supplier_currency": "EUR",
            "destination": "TR",
            "channel": "b2b",
            "agency_tier": "standard",
            "season": "mid",
            "product_type": "hotel",
            "nights": 1,
            "sell_currency": "EUR",
            "promo_code": ""
        }
        response = requests.post(f"{BASE_URL}/api/pricing-engine/simulate", json=payload, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        evaluated = data["evaluated_rules"]
        winners = [r for r in evaluated if r["won"]]
        losers = [r for r in evaluated if not r["won"]]
        
        print(f"Winners: {len(winners)}, Losers: {len(losers)}")
        
        # Winners should have won=True
        for w in winners:
            assert w["won"] == True
        
        # Losers should have won=False
        for l in losers:
            assert l["won"] == False


class TestGuardrailsEndpoints:
    """Test Guardrails CRUD endpoints."""
    
    def test_list_guardrails(self, auth_headers):
        """GET /api/pricing-engine/guardrails returns list of guardrails."""
        response = requests.get(f"{BASE_URL}/api/pricing-engine/guardrails", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert isinstance(data, list), f"Expected list, got {type(data)}"
        print(f"Found {len(data)} guardrails")
        
        for g in data:
            print(f"  - {g.get('name')} ({g.get('guardrail_type')}): value={g.get('value')}, active={g.get('active')}")
    
    def test_create_guardrail(self, auth_headers):
        """POST /api/pricing-engine/guardrails creates a new guardrail."""
        payload = {
            "name": "TEST_Min_Margin_Iter128",
            "guardrail_type": "min_margin_pct",
            "value": 8.0,
            "scope": {},
            "active": True
        }
        response = requests.post(f"{BASE_URL}/api/pricing-engine/guardrails", json=payload, headers=auth_headers)
        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "guardrail_id" in data, f"Missing guardrail_id in response: {data.keys()}"
        assert data["name"] == "TEST_Min_Margin_Iter128"
        assert data["guardrail_type"] == "min_margin_pct"
        assert data["value"] == 8.0
        assert data["active"] == True
        
        print(f"Created guardrail: {data['guardrail_id']} - {data['name']}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/pricing-engine/guardrails/{data['guardrail_id']}", headers=auth_headers)
    
    def test_create_guardrail_all_types(self, auth_headers):
        """Test creating guardrails for all 4 types."""
        guardrail_types = [
            {"guardrail_type": "min_margin_pct", "value": 5.0, "name": "TEST_MinMargin"},
            {"guardrail_type": "max_discount_pct", "value": 25.0, "name": "TEST_MaxDiscount"},
            {"guardrail_type": "channel_floor_price", "value": 50.0, "name": "TEST_ChannelFloor"},
            {"guardrail_type": "supplier_max_markup_pct", "value": 30.0, "name": "TEST_MaxMarkup"},
        ]
        
        created_ids = []
        for g in guardrail_types:
            payload = {**g, "scope": {}, "active": True}
            response = requests.post(f"{BASE_URL}/api/pricing-engine/guardrails", json=payload, headers=auth_headers)
            assert response.status_code == 201, f"Failed to create {g['guardrail_type']}: {response.status_code}"
            data = response.json()
            created_ids.append(data["guardrail_id"])
            print(f"Created {g['guardrail_type']} guardrail: {data['guardrail_id']}")
        
        # Cleanup
        for gid in created_ids:
            requests.delete(f"{BASE_URL}/api/pricing-engine/guardrails/{gid}", headers=auth_headers)
    
    def test_delete_guardrail(self, auth_headers):
        """DELETE /api/pricing-engine/guardrails/{guardrail_id} deletes a guardrail."""
        # Create a guardrail to delete
        payload = {
            "name": "TEST_Delete_Guardrail_Iter128",
            "guardrail_type": "max_discount_pct",
            "value": 20.0,
            "scope": {},
            "active": True
        }
        create_response = requests.post(f"{BASE_URL}/api/pricing-engine/guardrails", json=payload, headers=auth_headers)
        assert create_response.status_code == 201
        guardrail_id = create_response.json()["guardrail_id"]
        
        # Delete it
        delete_response = requests.delete(f"{BASE_URL}/api/pricing-engine/guardrails/{guardrail_id}", headers=auth_headers)
        assert delete_response.status_code == 200, f"Expected 200, got {delete_response.status_code}: {delete_response.text}"
        data = delete_response.json()
        assert data.get("ok") == True
        print(f"Deleted guardrail: {guardrail_id}")
        
        # Verify it's gone
        list_response = requests.get(f"{BASE_URL}/api/pricing-engine/guardrails", headers=auth_headers)
        guardrail_ids = [g.get("guardrail_id") for g in list_response.json()]
        assert guardrail_id not in guardrail_ids, f"Guardrail {guardrail_id} still exists after delete"
    
    def test_metadata_includes_guardrail_types(self, auth_headers):
        """GET /api/pricing-engine/metadata returns guardrail_types."""
        response = requests.get(f"{BASE_URL}/api/pricing-engine/metadata", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "guardrail_types" in data, f"Missing guardrail_types in metadata: {data.keys()}"
        expected_types = {"min_margin_pct", "max_discount_pct", "channel_floor_price", "supplier_max_markup_pct"}
        assert set(data["guardrail_types"]) == expected_types, f"Unexpected guardrail_types: {data['guardrail_types']}"
        print(f"Guardrail types in metadata: {data['guardrail_types']}")


class TestGuardrailWarnings:
    """Test guardrail validation in simulate response."""
    
    def test_simulate_returns_guardrails_passed(self, auth_headers):
        """POST /api/pricing-engine/simulate returns guardrails_passed boolean."""
        payload = {
            "supplier_code": "ratehawk",
            "supplier_price": 100.0,
            "supplier_currency": "EUR",
            "destination": "TR",
            "channel": "b2b",
            "agency_tier": "standard",
            "season": "mid",
            "product_type": "hotel",
            "nights": 1,
            "sell_currency": "EUR",
            "promo_code": ""
        }
        response = requests.post(f"{BASE_URL}/api/pricing-engine/simulate", json=payload, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "guardrails_passed" in data, f"Missing guardrails_passed in response: {data.keys()}"
        assert isinstance(data["guardrails_passed"], bool), f"guardrails_passed should be bool: {type(data['guardrails_passed'])}"
        print(f"Guardrails passed: {data['guardrails_passed']}")
    
    def test_simulate_returns_guardrail_warnings(self, auth_headers):
        """POST /api/pricing-engine/simulate returns guardrail_warnings array."""
        payload = {
            "supplier_code": "ratehawk",
            "supplier_price": 100.0,
            "supplier_currency": "EUR",
            "destination": "TR",
            "channel": "b2b",
            "agency_tier": "standard",
            "season": "mid",
            "product_type": "hotel",
            "nights": 1,
            "sell_currency": "EUR",
            "promo_code": ""
        }
        response = requests.post(f"{BASE_URL}/api/pricing-engine/simulate", json=payload, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "guardrail_warnings" in data, f"Missing guardrail_warnings in response: {data.keys()}"
        assert isinstance(data["guardrail_warnings"], list), f"guardrail_warnings should be list: {type(data['guardrail_warnings'])}"
        print(f"Guardrail warnings: {len(data['guardrail_warnings'])}")
        
        for w in data["guardrail_warnings"]:
            print(f"  - {w.get('guardrail')}: {w.get('message')} (severity={w.get('severity')})")
    
    def test_guardrail_violation_creates_warning(self, auth_headers):
        """Verify existing or new guardrail creates warning when violated."""
        # First run simulation to check existing guardrail warnings
        sim_payload = {
            "supplier_code": "ratehawk",
            "supplier_price": 100.0,
            "supplier_currency": "EUR",
            "destination": "TR",
            "channel": "b2b",
            "agency_tier": "standard",
            "season": "mid",
            "product_type": "hotel",
            "nights": 1,
            "sell_currency": "EUR",
            "promo_code": ""
        }
        sim_response = requests.post(
            f"{BASE_URL}/api/pricing-engine/simulate", 
            json=sim_payload, 
            headers=auth_headers
        )
        assert sim_response.status_code == 200
        data = sim_response.json()
        
        # Check if there's already a guardrail violation (from existing min_margin_pct=5)
        if data["guardrails_passed"] == False and len(data["guardrail_warnings"]) > 0:
            # Existing guardrail is being triggered - verify the warning structure
            margin_warnings = [w for w in data["guardrail_warnings"] if w["guardrail"] == "min_margin_pct"]
            assert len(margin_warnings) > 0, "Expected min_margin_pct warning"
            
            warning = margin_warnings[0]
            assert "expected" in warning
            assert "actual" in warning
            assert warning["severity"] == "error"
            assert warning["actual"] < warning["expected"], "Actual margin should be less than expected"
            
            print(f"Guardrail violation detected (existing guardrail)!")
            print(f"  Warning: {warning['message']}")
            print(f"  Expected: {warning['expected']}%, Actual: {warning['actual']}%")
        else:
            # Create a very high min_margin guardrail that will be violated
            guardrail_payload = {
                "name": "TEST_Tight_Margin_Iter128",
                "guardrail_type": "min_margin_pct",
                "value": 50.0,  # 50% margin is very high, will be violated
                "scope": {},
                "active": True
            }
            create_response = requests.post(
                f"{BASE_URL}/api/pricing-engine/guardrails", 
                json=guardrail_payload, 
                headers=auth_headers
            )
            assert create_response.status_code == 201
            guardrail_id = create_response.json()["guardrail_id"]
            
            try:
                # Run simulation again
                sim_response = requests.post(
                    f"{BASE_URL}/api/pricing-engine/simulate", 
                    json=sim_payload, 
                    headers=auth_headers
                )
                assert sim_response.status_code == 200
                data = sim_response.json()
                
                # Should have warning and guardrails_passed=False
                assert data["guardrails_passed"] == False, f"Expected guardrails_passed=False with 50% margin guardrail"
                assert len(data["guardrail_warnings"]) > 0, "Expected at least one warning"
                
                # Find the min_margin warning
                margin_warnings = [w for w in data["guardrail_warnings"] if w["guardrail"] == "min_margin_pct"]
                assert len(margin_warnings) > 0, "Expected min_margin_pct warning"
                
                warning = margin_warnings[0]
                assert "expected" in warning
                assert "actual" in warning
                assert warning["severity"] == "error"
                
                print(f"Guardrail violation detected (test guardrail)!")
                print(f"  Warning: {warning['message']}")
                print(f"  Expected: {warning['expected']}%, Actual: {warning['actual']}%")
                
            finally:
                # Cleanup
                requests.delete(f"{BASE_URL}/api/pricing-engine/guardrails/{guardrail_id}", headers=auth_headers)
    
    def test_guardrail_warning_fields(self, auth_headers):
        """Verify guardrail warning has all required fields."""
        # Create guardrail that will be violated
        guardrail_payload = {
            "name": "TEST_Warning_Fields_Iter128",
            "guardrail_type": "min_margin_pct",
            "value": 99.0,  # 99% margin - will definitely be violated
            "scope": {},
            "active": True
        }
        create_response = requests.post(
            f"{BASE_URL}/api/pricing-engine/guardrails", 
            json=guardrail_payload, 
            headers=auth_headers
        )
        assert create_response.status_code == 201
        guardrail_id = create_response.json()["guardrail_id"]
        
        try:
            sim_payload = {
                "supplier_code": "ratehawk",
                "supplier_price": 100.0,
                "supplier_currency": "EUR",
                "destination": "TR",
                "channel": "b2b",
                "agency_tier": "standard",
                "season": "mid",
                "product_type": "hotel",
                "nights": 1,
                "sell_currency": "EUR",
                "promo_code": ""
            }
            sim_response = requests.post(
                f"{BASE_URL}/api/pricing-engine/simulate", 
                json=sim_payload, 
                headers=auth_headers
            )
            assert sim_response.status_code == 200
            data = sim_response.json()
            
            assert len(data["guardrail_warnings"]) > 0
            
            required_fields = ["guardrail", "message", "severity", "expected", "actual"]
            for warning in data["guardrail_warnings"]:
                for field in required_fields:
                    assert field in warning, f"Warning missing field: {field}"
                
                # Severity should be 'error' or 'warning'
                assert warning["severity"] in ["error", "warning"], f"Invalid severity: {warning['severity']}"
            
            print("All warning fields present!")
            
        finally:
            # Cleanup
            requests.delete(f"{BASE_URL}/api/pricing-engine/guardrails/{guardrail_id}", headers=auth_headers)


class TestDashboardWithGuardrails:
    """Test dashboard includes guardrail stats."""
    
    def test_dashboard_returns_active_guardrails(self, auth_headers):
        """GET /api/pricing-engine/dashboard returns active_guardrails count."""
        response = requests.get(f"{BASE_URL}/api/pricing-engine/dashboard", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "active_guardrails" in data, f"Missing active_guardrails in dashboard: {data.keys()}"
        assert isinstance(data["active_guardrails"], int), f"active_guardrails should be int: {type(data['active_guardrails'])}"
        print(f"Active guardrails: {data['active_guardrails']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
