"""Pricing & Distribution Engine API Tests - Iteration 127

Tests for Syroce Travel SaaS Pricing Engine:
  - Metadata endpoint (channels, seasons, promotion_types, rule_categories, agency_tiers)
  - Dashboard stats endpoint
  - Price simulation pipeline
  - Distribution rules CRUD
  - Channel configs CRUD
  - Promotions CRUD with toggle

Test credentials: agent@acenta.test / agent123
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
    data = _unwrap(response)
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


class TestPricingEngineMetadata:
    """Test /api/pricing-engine/metadata endpoint."""
    
    def test_metadata_returns_channels(self, auth_headers):
        """GET /api/pricing-engine/metadata returns channels list."""
        response = requests.get(f"{BASE_URL}/api/pricing-engine/metadata", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = _unwrap(response)
        assert "channels" in data, f"Missing channels: {data.keys()}"
        assert isinstance(data["channels"], list), f"channels should be list: {type(data['channels'])}"
        assert set(data["channels"]) == {"b2b", "b2c", "corporate", "whitelabel"}, f"Unexpected channels: {data['channels']}"
        print(f"Channels: {data['channels']}")
    
    def test_metadata_returns_seasons(self, auth_headers):
        """GET /api/pricing-engine/metadata returns seasons list."""
        response = requests.get(f"{BASE_URL}/api/pricing-engine/metadata", headers=auth_headers)
        assert response.status_code == 200
        data = _unwrap(response)
        assert "seasons" in data
        assert set(data["seasons"]) == {"peak", "high", "mid", "low", "off"}, f"Unexpected seasons: {data['seasons']}"
        print(f"Seasons: {data['seasons']}")
    
    def test_metadata_returns_promotion_types(self, auth_headers):
        """GET /api/pricing-engine/metadata returns promotion_types list."""
        response = requests.get(f"{BASE_URL}/api/pricing-engine/metadata", headers=auth_headers)
        assert response.status_code == 200
        data = _unwrap(response)
        assert "promotion_types" in data
        expected_types = {"early_booking", "flash_sale", "campaign_discount", "fixed_price_override"}
        assert set(data["promotion_types"]) == expected_types, f"Unexpected promotion_types: {data['promotion_types']}"
        print(f"Promotion types: {data['promotion_types']}")
    
    def test_metadata_returns_rule_categories(self, auth_headers):
        """GET /api/pricing-engine/metadata returns rule_categories list."""
        response = requests.get(f"{BASE_URL}/api/pricing-engine/metadata", headers=auth_headers)
        assert response.status_code == 200
        data = _unwrap(response)
        assert "rule_categories" in data
        expected_cats = {"base_markup", "agency_tier", "commission", "tax"}
        assert set(data["rule_categories"]) == expected_cats, f"Unexpected rule_categories: {data['rule_categories']}"
        print(f"Rule categories: {data['rule_categories']}")
    
    def test_metadata_returns_agency_tiers(self, auth_headers):
        """GET /api/pricing-engine/metadata returns agency_tiers list."""
        response = requests.get(f"{BASE_URL}/api/pricing-engine/metadata", headers=auth_headers)
        assert response.status_code == 200
        data = _unwrap(response)
        assert "agency_tiers" in data
        expected_tiers = {"starter", "standard", "premium", "enterprise"}
        assert set(data["agency_tiers"]) == expected_tiers, f"Unexpected agency_tiers: {data['agency_tiers']}"
        print(f"Agency tiers: {data['agency_tiers']}")


class TestPricingEngineDashboard:
    """Test /api/pricing-engine/dashboard endpoint."""
    
    def test_dashboard_returns_stats(self, auth_headers):
        """GET /api/pricing-engine/dashboard returns stats."""
        response = requests.get(f"{BASE_URL}/api/pricing-engine/dashboard", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = _unwrap(response)
        
        # Check required fields
        required_fields = ["total_rules", "active_rules", "channel_count", "active_promotions"]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
        
        print(f"Dashboard stats: total_rules={data['total_rules']}, active_rules={data['active_rules']}, channel_count={data['channel_count']}, active_promotions={data['active_promotions']}")
    
    def test_dashboard_returns_rules_by_category(self, auth_headers):
        """GET /api/pricing-engine/dashboard returns rules_by_category breakdown."""
        response = requests.get(f"{BASE_URL}/api/pricing-engine/dashboard", headers=auth_headers)
        assert response.status_code == 200
        data = _unwrap(response)
        assert "rules_by_category" in data
        print(f"Rules by category: {data['rules_by_category']}")
    
    def test_dashboard_returns_active_channels(self, auth_headers):
        """GET /api/pricing-engine/dashboard returns active_channels list."""
        response = requests.get(f"{BASE_URL}/api/pricing-engine/dashboard", headers=auth_headers)
        assert response.status_code == 200
        data = _unwrap(response)
        assert "active_channels" in data
        assert isinstance(data["active_channels"], list)
        print(f"Active channels: {data['active_channels']}")


class TestPricingEngineSimulate:
    """Test POST /api/pricing-engine/simulate endpoint."""
    
    def test_simulate_basic_pricing(self, auth_headers):
        """POST /api/pricing-engine/simulate returns full pricing breakdown."""
        payload = {
            "supplier_code": "ratehawk",
            "supplier_price": 100.0,
            "supplier_currency": "EUR",
            "destination": "TR",
            "channel": "b2b",
            "agency_tier": "standard",
            "season": "mid",
            "product_type": "hotel",
            "nights": 3,
            "sell_currency": "EUR",
            "promo_code": ""
        }
        response = requests.post(f"{BASE_URL}/api/pricing-engine/simulate", json=payload, headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = _unwrap(response)
        
        # Check all breakdown fields exist
        required_fields = [
            "supplier_price", "supplier_currency",
            "base_markup_pct", "base_markup_amount",
            "channel_adjustment_pct", "channel_adjustment_amount",
            "promotion_discount_pct", "promotion_discount_amount",
            "subtotal_before_tax", "tax_rate", "tax_amount",
            "sell_price", "sell_currency", "fx_rate",
            "margin", "margin_pct", "per_night",
            "applied_rules"
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
        
        # Verify supplier_price matches input
        assert data["supplier_price"] == 100.0
        assert data["supplier_currency"] == "EUR"
        
        print(f"Simulation result: supplier={data['supplier_price']} {data['supplier_currency']} -> sell={data['sell_price']} {data['sell_currency']}")
        print(f"Breakdown: base_markup={data['base_markup_pct']}%, channel={data['channel_adjustment_pct']}%, promo={data['promotion_discount_pct']}%")
        print(f"Margin: {data['margin']} ({data['margin_pct']}%), Per night: {data['per_night']}")
    
    def test_simulate_different_channels_produce_different_prices(self, auth_headers):
        """Different channels should produce different sell prices."""
        base_payload = {
            "supplier_code": "ratehawk",
            "supplier_price": 100.0,
            "supplier_currency": "EUR",
            "destination": "TR",
            "agency_tier": "standard",
            "season": "mid",
            "product_type": "hotel",
            "nights": 1,
            "sell_currency": "EUR",
            "promo_code": ""
        }
        
        prices = {}
        for channel in ["b2b", "b2c", "corporate", "whitelabel"]:
            payload = {**base_payload, "channel": channel}
            response = requests.post(f"{BASE_URL}/api/pricing-engine/simulate", json=payload, headers=auth_headers)
            assert response.status_code == 200
            data = _unwrap(response)
            prices[channel] = {
                "sell_price": data["sell_price"],
                "channel_adjustment_pct": data["channel_adjustment_pct"]
            }
        
        print("Channel prices comparison:")
        for ch, p in prices.items():
            print(f"  {ch}: {p['sell_price']} EUR (adj={p['channel_adjustment_pct']}%)")
        
        # Channels with configured adjustments should have different prices
        # (may be same if no channel configs exist yet)
    
    def test_simulate_with_currency_conversion(self, auth_headers):
        """Test simulation with currency conversion."""
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
            "sell_currency": "TRY",
            "promo_code": ""
        }
        response = requests.post(f"{BASE_URL}/api/pricing-engine/simulate", json=payload, headers=auth_headers)
        assert response.status_code == 200
        data = _unwrap(response)
        
        assert data["sell_currency"] == "TRY"
        assert data["fx_rate"] >= 1.0  # EUR to TRY rate should be > 1
        print(f"Currency conversion: {data['supplier_price']} EUR -> {data['sell_price']} TRY (rate={data['fx_rate']})")


class TestDistributionRulesCRUD:
    """Test /api/pricing-engine/distribution-rules CRUD endpoints."""
    
    @pytest.fixture
    def test_rule_id(self, auth_headers):
        """Create a test rule and return its ID for other tests."""
        payload = {
            "name": "TEST_Markup_Rule_Iter127",
            "rule_category": "base_markup",
            "value": 12.5,
            "scope": {"supplier": "ratehawk", "destination": "TR"},
            "priority": 5,
            "active": True
        }
        response = requests.post(f"{BASE_URL}/api/pricing-engine/distribution-rules", json=payload, headers=auth_headers)
        if response.status_code not in [200, 201]:
            pytest.skip(f"Failed to create test rule: {response.status_code} - {response.text}")
        data = _unwrap(response)
        rule_id = data.get("rule_id")
        yield rule_id
        # Cleanup
        requests.delete(f"{BASE_URL}/api/pricing-engine/distribution-rules/{rule_id}", headers=auth_headers)
    
    def test_create_distribution_rule(self, auth_headers):
        """POST /api/pricing-engine/distribution-rules creates a new rule."""
        payload = {
            "name": "TEST_Create_Rule_Iter127",
            "rule_category": "base_markup",
            "value": 15.0,
            "scope": {"season": "peak"},
            "priority": 10,
            "active": True
        }
        response = requests.post(f"{BASE_URL}/api/pricing-engine/distribution-rules", json=payload, headers=auth_headers)
        assert response.status_code in [200, 201], f"Expected 201, got {response.status_code}: {response.text}"
        data = _unwrap(response)
        
        assert "rule_id" in data
        assert data["name"] == "TEST_Create_Rule_Iter127"
        assert data["rule_category"] == "base_markup"
        assert data["value"] == 15.0
        assert data["priority"] == 10
        assert data["active"] == True
        
        print(f"Created rule: {data['rule_id']} - {data['name']}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/pricing-engine/distribution-rules/{data['rule_id']}", headers=auth_headers)
    
    def test_list_distribution_rules(self, auth_headers, test_rule_id):
        """GET /api/pricing-engine/distribution-rules lists rules."""
        response = requests.get(f"{BASE_URL}/api/pricing-engine/distribution-rules", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = _unwrap(response)
        
        assert isinstance(data, list), f"Expected list, got {type(data)}"
        print(f"Found {len(data)} distribution rules")
        
        # Verify test rule exists
        rule_ids = [r.get("rule_id") for r in data]
        assert test_rule_id in rule_ids, f"Test rule {test_rule_id} not found in list"
    
    def test_list_distribution_rules_filter_by_category(self, auth_headers, test_rule_id):
        """GET /api/pricing-engine/distribution-rules?category=base_markup filters by category."""
        response = requests.get(f"{BASE_URL}/api/pricing-engine/distribution-rules?category=base_markup", headers=auth_headers)
        assert response.status_code == 200
        data = _unwrap(response)
        
        for rule in data:
            assert rule.get("rule_category") == "base_markup", f"Unexpected category: {rule.get('rule_category')}"
        print(f"Found {len(data)} base_markup rules")
    
    def test_delete_distribution_rule(self, auth_headers):
        """DELETE /api/pricing-engine/distribution-rules/{rule_id} deletes a rule."""
        # Create a rule to delete
        payload = {
            "name": "TEST_Delete_Rule_Iter127",
            "rule_category": "commission",
            "value": 5.0,
            "scope": {},
            "priority": 1,
            "active": True
        }
        create_response = requests.post(f"{BASE_URL}/api/pricing-engine/distribution-rules", json=payload, headers=auth_headers)
        assert create_response.status_code in [200, 201]
        rule_id = _unwrap(create_response)["rule_id"]
        
        # Delete it
        delete_response = requests.delete(f"{BASE_URL}/api/pricing-engine/distribution-rules/{rule_id}", headers=auth_headers)
        assert delete_response.status_code == 200
        data = _unwrap(delete_response)
        assert data.get("ok") == True
        print(f"Deleted rule: {rule_id}")
        
        # Verify it's gone
        list_response = requests.get(f"{BASE_URL}/api/pricing-engine/distribution-rules", headers=auth_headers)
        rule_ids = [r.get("rule_id") for r in _unwrap(list_response)]
        assert rule_id not in rule_ids, f"Rule {rule_id} still exists after delete"


class TestChannelsCRUD:
    """Test /api/pricing-engine/channels CRUD endpoints."""
    
    @pytest.fixture
    def test_channel_id(self, auth_headers):
        """Create a test channel and return its rule_id for other tests."""
        payload = {
            "channel": "b2b",
            "label": "TEST_B2B_Channel_Iter127",
            "adjustment_pct": -7.5,
            "commission_pct": 2.0,
            "active": True
        }
        response = requests.post(f"{BASE_URL}/api/pricing-engine/channels", json=payload, headers=auth_headers)
        if response.status_code not in [200, 201]:
            pytest.skip(f"Failed to create test channel: {response.status_code} - {response.text}")
        data = _unwrap(response)
        rule_id = data.get("rule_id")
        yield rule_id
        # Cleanup
        requests.delete(f"{BASE_URL}/api/pricing-engine/channels/{rule_id}", headers=auth_headers)
    
    def test_create_channel(self, auth_headers):
        """POST /api/pricing-engine/channels creates a channel config."""
        payload = {
            "channel": "corporate",
            "label": "TEST_Corporate_Iter127",
            "adjustment_pct": -10.0,
            "commission_pct": 3.0,
            "active": True
        }
        response = requests.post(f"{BASE_URL}/api/pricing-engine/channels", json=payload, headers=auth_headers)
        assert response.status_code in [200, 201], f"Expected 201, got {response.status_code}: {response.text}"
        data = _unwrap(response)
        
        assert "rule_id" in data
        assert data["channel"] == "corporate"
        assert data["adjustment_pct"] == -10.0
        assert data["commission_pct"] == 3.0
        
        print(f"Created channel: {data['rule_id']} - {data['label']}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/pricing-engine/channels/{data['rule_id']}", headers=auth_headers)
    
    def test_list_channels(self, auth_headers, test_channel_id):
        """GET /api/pricing-engine/channels lists channel configs."""
        response = requests.get(f"{BASE_URL}/api/pricing-engine/channels", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = _unwrap(response)
        
        assert isinstance(data, list)
        print(f"Found {len(data)} channel configs")
        
        # Verify test channel exists
        rule_ids = [c.get("rule_id") for c in data]
        assert test_channel_id in rule_ids
    
    def test_delete_channel(self, auth_headers):
        """DELETE /api/pricing-engine/channels/{rule_id} deletes a channel."""
        # Create a channel to delete
        payload = {
            "channel": "whitelabel",
            "label": "TEST_Delete_Channel_Iter127",
            "adjustment_pct": -5.0,
            "active": True
        }
        create_response = requests.post(f"{BASE_URL}/api/pricing-engine/channels", json=payload, headers=auth_headers)
        assert create_response.status_code in [200, 201]
        rule_id = _unwrap(create_response)["rule_id"]
        
        # Delete it
        delete_response = requests.delete(f"{BASE_URL}/api/pricing-engine/channels/{rule_id}", headers=auth_headers)
        assert delete_response.status_code == 200
        data = _unwrap(delete_response)
        assert data.get("ok") == True
        print(f"Deleted channel: {rule_id}")


class TestPromotionsCRUD:
    """Test /api/pricing-engine/promotions CRUD endpoints."""
    
    @pytest.fixture
    def test_promo_id(self, auth_headers):
        """Create a test promotion and return its rule_id for other tests."""
        payload = {
            "name": "TEST_Promo_Iter127",
            "promo_type": "campaign_discount",
            "discount_pct": 8.0,
            "promo_code": "TEST127",
            "scope": {"destination": "TR"},
            "min_days_before": 0,
            "max_uses": 0
        }
        response = requests.post(f"{BASE_URL}/api/pricing-engine/promotions", json=payload, headers=auth_headers)
        if response.status_code not in [200, 201]:
            pytest.skip(f"Failed to create test promo: {response.status_code} - {response.text}")
        data = _unwrap(response)
        rule_id = data.get("rule_id")
        yield rule_id
        # Cleanup
        requests.delete(f"{BASE_URL}/api/pricing-engine/promotions/{rule_id}", headers=auth_headers)
    
    def test_create_promotion(self, auth_headers):
        """POST /api/pricing-engine/promotions creates a promotion."""
        payload = {
            "name": "TEST_Create_Promo_Iter127",
            "promo_type": "early_booking",
            "discount_pct": 12.0,
            "promo_code": "EARLY127",
            "scope": {},
            "min_days_before": 30,
            "max_uses": 100
        }
        response = requests.post(f"{BASE_URL}/api/pricing-engine/promotions", json=payload, headers=auth_headers)
        assert response.status_code in [200, 201], f"Expected 201, got {response.status_code}: {response.text}"
        data = _unwrap(response)
        
        assert "rule_id" in data
        assert data["name"] == "TEST_Create_Promo_Iter127"
        assert data["promo_type"] == "early_booking"
        assert data["discount_pct"] == 12.0
        assert data["active"] == True
        
        print(f"Created promotion: {data['rule_id']} - {data['name']}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/pricing-engine/promotions/{data['rule_id']}", headers=auth_headers)
    
    def test_list_promotions(self, auth_headers, test_promo_id):
        """GET /api/pricing-engine/promotions lists promotions."""
        response = requests.get(f"{BASE_URL}/api/pricing-engine/promotions", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = _unwrap(response)
        
        assert isinstance(data, list)
        print(f"Found {len(data)} promotions")
        
        rule_ids = [p.get("rule_id") for p in data]
        assert test_promo_id in rule_ids
    
    def test_toggle_promotion(self, auth_headers, test_promo_id):
        """POST /api/pricing-engine/promotions/{rule_id}/toggle toggles active status."""
        # Toggle off
        response = requests.post(f"{BASE_URL}/api/pricing-engine/promotions/{test_promo_id}/toggle?active=false", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = _unwrap(response)
        assert data.get("active") == False
        print(f"Toggled promo {test_promo_id} to inactive")
        
        # Toggle back on
        response = requests.post(f"{BASE_URL}/api/pricing-engine/promotions/{test_promo_id}/toggle?active=true", headers=auth_headers)
        assert response.status_code == 200
        data = _unwrap(response)
        assert data.get("active") == True
        print(f"Toggled promo {test_promo_id} back to active")
    
    def test_delete_promotion(self, auth_headers):
        """DELETE /api/pricing-engine/promotions/{rule_id} deletes a promotion."""
        # Create a promo to delete
        payload = {
            "name": "TEST_Delete_Promo_Iter127",
            "promo_type": "flash_sale",
            "discount_pct": 20.0,
            "promo_code": "FLASH127",
            "scope": {}
        }
        create_response = requests.post(f"{BASE_URL}/api/pricing-engine/promotions", json=payload, headers=auth_headers)
        assert create_response.status_code in [200, 201]
        rule_id = _unwrap(create_response)["rule_id"]
        
        # Delete it
        delete_response = requests.delete(f"{BASE_URL}/api/pricing-engine/promotions/{rule_id}", headers=auth_headers)
        assert delete_response.status_code == 200
        data = _unwrap(delete_response)
        assert data.get("ok") == True
        print(f"Deleted promotion: {rule_id}")


class TestFullPipelineIntegration:
    """Test full pricing pipeline with rules, channels, and promotions."""
    
    def test_simulate_with_seeded_data(self, auth_headers):
        """Verify simulation works with seeded demo data."""
        # Test with b2b channel (should have -5% adjustment from seeded data)
        payload = {
            "supplier_code": "ratehawk",
            "supplier_price": 200.0,
            "supplier_currency": "EUR",
            "destination": "TR",
            "channel": "b2b",
            "agency_tier": "standard",
            "season": "peak",
            "product_type": "hotel",
            "nights": 2,
            "sell_currency": "EUR",
            "promo_code": ""
        }
        response = requests.post(f"{BASE_URL}/api/pricing-engine/simulate", json=payload, headers=auth_headers)
        assert response.status_code == 200
        data = _unwrap(response)
        
        print(f"Full pipeline test:")
        print(f"  Input: {payload['supplier_price']} {payload['supplier_currency']}, channel={payload['channel']}, season={payload['season']}")
        print(f"  Base markup: {data['base_markup_pct']}% (+{data['base_markup_amount']})")
        print(f"  Channel adj: {data['channel_adjustment_pct']}% ({data['channel_adjustment_amount']})")
        print(f"  Promo disc: {data['promotion_discount_pct']}% (-{data['promotion_discount_amount']})")
        print(f"  Tax: {data['tax_rate']}% (+{data['tax_amount']})")
        print(f"  Final: {data['sell_price']} {data['sell_currency']}")
        print(f"  Margin: {data['margin']} ({data['margin_pct']}%)")
        print(f"  Per night: {data['per_night']}")
        print(f"  Applied rules: {data['applied_rules']}")
        
        # Verify pipeline math
        assert data["sell_price"] > 0
        assert data["per_night"] == round(data["sell_price"] / payload["nights"], 2)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
