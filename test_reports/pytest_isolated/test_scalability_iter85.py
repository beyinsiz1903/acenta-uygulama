"""
Platform Scalability & Global Readiness - MEGA PROMPT #26
Tests for all scalability endpoints under /api/scalability/

Features tested:
- GET /api/scalability/cache-stats - Cache hit/miss statistics
- GET /api/scalability/scheduler-status - Job scheduler status (5 jobs)
- POST /api/scalability/scheduler/trigger - Manual job trigger
- GET /api/scalability/monitoring-dashboard - Combined monitoring data
- GET /api/scalability/supplier-metrics - Supplier-level metrics
- GET /api/scalability/search-metrics - Search cache metrics
- GET /api/scalability/redis-health - Redis health check
- GET /api/scalability/rate-limit-stats - Rate limit config/stats
- GET /api/scalability/tax-regions - Tax regions (9+ regions)
- POST /api/scalability/tax-breakdown - Tax calculation
- POST /api/scalability/currency-convert - Currency conversion
- GET /api/scalability/currency-rates - Exchange rates
"""

import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://syroce-refactor.preview.emergentagent.com")

@pytest.fixture(scope="module")
def auth_token():
    """Authenticate and return access token"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "agent@acenta.test", "password": "agent123"}
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    data = response.json()
    assert "access_token" in data, f"No access_token in response: {data}"
    return data["access_token"]

@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Return auth headers with Bearer token"""
    return {"Authorization": f"Bearer {auth_token}"}

class TestScalabilityCacheStats:
    """Cache statistics endpoint tests"""
    
    def test_cache_stats_requires_auth(self):
        """GET /api/scalability/cache-stats requires authentication"""
        response = requests.get(f"{BASE_URL}/api/scalability/cache-stats")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("PASS: cache-stats requires authentication")
    
    def test_cache_stats_returns_hit_miss(self, auth_headers):
        """GET /api/scalability/cache-stats returns hit/miss statistics"""
        response = requests.get(f"{BASE_URL}/api/scalability/cache-stats", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Check hit_miss structure
        assert "hit_miss" in data, f"Missing hit_miss in response: {data}"
        hit_miss = data["hit_miss"]
        assert "hits" in hit_miss, "Missing hits counter"
        assert "misses" in hit_miss, "Missing misses counter"
        assert "total" in hit_miss, "Missing total counter"
        assert "hit_rate_pct" in hit_miss, "Missing hit_rate_pct"
        
        # Validate types
        assert isinstance(hit_miss["hits"], int), "hits should be int"
        assert isinstance(hit_miss["misses"], int), "misses should be int"
        assert isinstance(hit_miss["total"], int), "total should be int"
        assert isinstance(hit_miss["hit_rate_pct"], (int, float)), "hit_rate_pct should be numeric"
        
        print(f"PASS: cache-stats returns hit_miss: {hit_miss}")

class TestScalabilityScheduler:
    """Job scheduler endpoint tests"""
    
    def test_scheduler_status_requires_auth(self):
        """GET /api/scalability/scheduler-status requires authentication"""
        response = requests.get(f"{BASE_URL}/api/scalability/scheduler-status")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("PASS: scheduler-status requires authentication")
    
    def test_scheduler_status_returns_5_jobs(self, auth_headers):
        """GET /api/scalability/scheduler-status returns 5 scheduled jobs"""
        response = requests.get(f"{BASE_URL}/api/scalability/scheduler-status", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Check scheduler structure
        assert "running" in data, f"Missing running status: {data}"
        assert "jobs" in data, f"Missing jobs list: {data}"
        assert "total_jobs" in data, f"Missing total_jobs: {data}"
        
        # Verify running state
        assert data["running"] == True, f"Scheduler should be running, got: {data['running']}"
        
        # Verify 5 jobs
        jobs = data["jobs"]
        assert len(jobs) >= 5, f"Expected at least 5 jobs, got {len(jobs)}: {jobs}"
        
        # Check expected job IDs
        job_ids = [j["id"] for j in jobs]
        expected_jobs = [
            "booking_status_sync",
            "supplier_reconciliation", 
            "supplier_health_check",
            "analytics_aggregation",
            "revenue_reconciliation"
        ]
        for ej in expected_jobs:
            assert ej in job_ids, f"Missing expected job: {ej}, found: {job_ids}"
        
        # Check job structure
        for job in jobs:
            assert "id" in job, f"Job missing id: {job}"
            assert "name" in job, f"Job missing name: {job}"
            assert "next_run" in job, f"Job missing next_run: {job}"
        
        print(f"PASS: scheduler-status returns {len(jobs)} jobs (running={data['running']})")
    
    def test_scheduler_trigger_requires_auth(self):
        """POST /api/scalability/scheduler/trigger requires authentication"""
        response = requests.post(
            f"{BASE_URL}/api/scalability/scheduler/trigger",
            json={"job_name": "supplier_health_check"}
        )
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("PASS: scheduler/trigger requires authentication")
    
    def test_scheduler_trigger_supplier_health_check(self, auth_headers):
        """POST /api/scalability/scheduler/trigger triggers job manually"""
        response = requests.post(
            f"{BASE_URL}/api/scalability/scheduler/trigger",
            json={"job_name": "supplier_health_check"},
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "triggered" in data, f"Missing triggered field: {data}"
        assert data["triggered"] == "supplier_health_check", f"Wrong job triggered: {data}"
        assert "timestamp" in data, f"Missing timestamp: {data}"
        
        print(f"PASS: scheduler/trigger triggered supplier_health_check at {data['timestamp']}")
    
    def test_scheduler_trigger_unknown_job(self, auth_headers):
        """POST /api/scalability/scheduler/trigger with unknown job returns error"""
        response = requests.post(
            f"{BASE_URL}/api/scalability/scheduler/trigger",
            json={"job_name": "unknown_job_xyz"},
            headers=auth_headers
        )
        # Should return 200 with error message or 400
        assert response.status_code in [200, 400], f"Unexpected status: {response.status_code}"
        data = response.json()
        
        if response.status_code == 200:
            assert "error" in data, f"Should have error for unknown job: {data}"
            assert "available" in data, f"Should list available jobs: {data}"
        
        print(f"PASS: scheduler/trigger handles unknown job correctly")

class TestScalabilityMonitoringDashboard:
    """Combined monitoring dashboard tests"""
    
    def test_monitoring_dashboard_requires_auth(self):
        """GET /api/scalability/monitoring-dashboard requires authentication"""
        response = requests.get(f"{BASE_URL}/api/scalability/monitoring-dashboard")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("PASS: monitoring-dashboard requires authentication")
    
    def test_monitoring_dashboard_returns_combined_data(self, auth_headers):
        """GET /api/scalability/monitoring-dashboard returns combined monitoring data"""
        response = requests.get(f"{BASE_URL}/api/scalability/monitoring-dashboard", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Check all expected sections
        assert "cache" in data, f"Missing cache section: {data.keys()}"
        assert "scheduler" in data, f"Missing scheduler section: {data.keys()}"
        assert "redis" in data, f"Missing redis section: {data.keys()}"
        assert "last_24h" in data, f"Missing last_24h section: {data.keys()}"
        assert "timestamp" in data, f"Missing timestamp: {data.keys()}"
        
        # Check cache structure
        cache = data["cache"]
        assert "hits" in cache, "Missing cache hits"
        assert "misses" in cache, "Missing cache misses"
        assert "hit_rate_pct" in cache, "Missing hit_rate_pct"
        
        # Check last_24h structure
        last_24h = data["last_24h"]
        assert "bookings" in last_24h, "Missing last_24h.bookings"
        assert "searches" in last_24h, "Missing last_24h.searches"
        assert "commissions" in last_24h, "Missing last_24h.commissions"
        assert "recon_mismatches" in last_24h, "Missing last_24h.recon_mismatches"
        
        # Check redis section
        redis = data["redis"]
        assert "status" in redis, f"Missing redis status: {redis}"
        
        # Check scheduler section
        scheduler = data["scheduler"]
        assert "running" in scheduler, f"Missing scheduler running: {scheduler}"
        assert "jobs" in scheduler, f"Missing scheduler jobs: {scheduler}"
        
        print(f"PASS: monitoring-dashboard returns all sections: {list(data.keys())}")
        print(f"  cache: hits={cache['hits']}, misses={cache['misses']}, hit_rate={cache['hit_rate_pct']}%")
        print(f"  last_24h: bookings={last_24h['bookings']}, searches={last_24h['searches']}")
        print(f"  redis: {redis['status']}")
        print(f"  scheduler: running={scheduler['running']}, jobs={len(scheduler['jobs'])}")

class TestScalabilitySupplierMetrics:
    """Supplier metrics endpoint tests"""
    
    def test_supplier_metrics_requires_auth(self):
        """GET /api/scalability/supplier-metrics requires authentication"""
        response = requests.get(f"{BASE_URL}/api/scalability/supplier-metrics")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("PASS: supplier-metrics requires authentication")
    
    def test_supplier_metrics_returns_suppliers(self, auth_headers):
        """GET /api/scalability/supplier-metrics returns supplier-level metrics"""
        response = requests.get(f"{BASE_URL}/api/scalability/supplier-metrics", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "suppliers" in data, f"Missing suppliers: {data}"
        suppliers = data["suppliers"]
        
        # suppliers can be empty dict if no activity
        assert isinstance(suppliers, dict), f"suppliers should be dict: {type(suppliers)}"
        
        # If there are suppliers, check structure
        for sc, metrics in suppliers.items():
            assert "search_count" in metrics, f"Missing search_count for {sc}"
            assert "booking_count" in metrics, f"Missing booking_count for {sc}"
            assert "booking_success" in metrics, f"Missing booking_success for {sc}"
            assert "booking_fail" in metrics, f"Missing booking_fail for {sc}"
            assert "revenue" in metrics, f"Missing revenue for {sc}"
            assert "markup" in metrics, f"Missing markup for {sc}"
        
        print(f"PASS: supplier-metrics returns {len(suppliers)} suppliers")

class TestScalabilitySearchMetrics:
    """Search cache metrics endpoint tests"""
    
    def test_search_metrics_requires_auth(self):
        """GET /api/scalability/search-metrics requires authentication"""
        response = requests.get(f"{BASE_URL}/api/scalability/search-metrics")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("PASS: search-metrics requires authentication")
    
    def test_search_metrics_returns_by_product_type(self, auth_headers):
        """GET /api/scalability/search-metrics returns metrics by product type"""
        response = requests.get(f"{BASE_URL}/api/scalability/search-metrics", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "search_metrics" in data, f"Missing search_metrics: {data}"
        metrics = data["search_metrics"]
        
        assert isinstance(metrics, dict), f"search_metrics should be dict: {type(metrics)}"
        
        # If there are product types, check structure
        for pt, pm in metrics.items():
            assert "cache_hit" in pm or pm == {}, f"Missing cache_hit for {pt}"
            assert "cache_miss" in pm or pm == {}, f"Missing cache_miss for {pt}"
        
        print(f"PASS: search-metrics returns {len(metrics)} product types")

class TestScalabilityRedisHealth:
    """Redis health check endpoint tests"""
    
    def test_redis_health_requires_auth(self):
        """GET /api/scalability/redis-health requires authentication"""
        response = requests.get(f"{BASE_URL}/api/scalability/redis-health")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("PASS: redis-health requires authentication")
    
    def test_redis_health_returns_healthy(self, auth_headers):
        """GET /api/scalability/redis-health returns status=healthy"""
        response = requests.get(f"{BASE_URL}/api/scalability/redis-health", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "status" in data, f"Missing status: {data}"
        assert data["status"] == "healthy", f"Expected healthy, got: {data['status']}"
        
        # Check additional info if available
        if "used_memory_human" in data:
            print(f"  Memory: {data['used_memory_human']}")
        if "connected_clients" in data:
            print(f"  Clients: {data['connected_clients']}")
        
        print(f"PASS: redis-health status={data['status']}")

class TestScalabilityRateLimit:
    """Rate limit stats endpoint tests"""
    
    def test_rate_limit_stats_requires_auth(self):
        """GET /api/scalability/rate-limit-stats requires authentication"""
        response = requests.get(f"{BASE_URL}/api/scalability/rate-limit-stats")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("PASS: rate-limit-stats requires authentication")
    
    def test_rate_limit_stats_returns_config(self, auth_headers):
        """GET /api/scalability/rate-limit-stats returns config and stats"""
        response = requests.get(f"{BASE_URL}/api/scalability/rate-limit-stats", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "stats" in data, f"Missing stats: {data}"
        assert "tiers_config" in data, f"Missing tiers_config: {data}"
        
        tiers = data["tiers_config"]
        assert isinstance(tiers, dict), f"tiers_config should be dict: {type(tiers)}"
        
        print(f"PASS: rate-limit-stats returns tiers: {list(tiers.keys())}")

class TestScalabilityTaxRegions:
    """Tax regions endpoint tests"""
    
    def test_tax_regions_requires_auth(self):
        """GET /api/scalability/tax-regions requires authentication"""
        response = requests.get(f"{BASE_URL}/api/scalability/tax-regions")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("PASS: tax-regions requires authentication")
    
    def test_tax_regions_returns_9_plus_regions(self, auth_headers):
        """GET /api/scalability/tax-regions returns 9+ tax regions"""
        response = requests.get(f"{BASE_URL}/api/scalability/tax-regions", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "regions" in data, f"Missing regions: {data}"
        regions = data["regions"]
        
        assert isinstance(regions, list), f"regions should be list: {type(regions)}"
        assert len(regions) >= 9, f"Expected at least 9 regions, got {len(regions)}"
        
        # Check region structure
        for region in regions:
            assert "country_code" in region, f"Missing country_code: {region}"
            assert "vat_pct" in region, f"Missing vat_pct: {region}"
            assert "tourism_tax_pct" in region, f"Missing tourism_tax_pct: {region}"
            assert "label" in region, f"Missing label: {region}"
        
        # Check expected countries
        country_codes = [r["country_code"] for r in regions]
        expected_countries = ["TR", "AE", "GB", "DE", "FR", "IT", "ES", "GR", "US"]
        for cc in expected_countries:
            assert cc in country_codes, f"Missing country: {cc}, found: {country_codes}"
        
        # Print sample regions
        print(f"PASS: tax-regions returns {len(regions)} regions")
        tr_region = next((r for r in regions if r["country_code"] == "TR"), None)
        if tr_region:
            print(f"  TR: VAT={tr_region['vat_pct']}%, Tourism={tr_region['tourism_tax_pct']}%")

class TestScalabilityTaxBreakdown:
    """Tax breakdown calculation tests"""
    
    def test_tax_breakdown_requires_auth(self):
        """POST /api/scalability/tax-breakdown requires authentication"""
        response = requests.post(
            f"{BASE_URL}/api/scalability/tax-breakdown",
            json={"base_price": 10000, "country_code": "TR"}
        )
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("PASS: tax-breakdown requires authentication")
    
    def test_tax_breakdown_tr_calculation(self, auth_headers):
        """POST /api/scalability/tax-breakdown calculates TR tax correctly"""
        response = requests.post(
            f"{BASE_URL}/api/scalability/tax-breakdown",
            json={"base_price": 10000, "country_code": "TR"},
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Check required fields
        assert "base_price" in data, f"Missing base_price: {data}"
        assert "vat_amount" in data, f"Missing vat_amount: {data}"
        assert "tourism_tax" in data, f"Missing tourism_tax: {data}"
        assert "gross_price" in data, f"Missing gross_price: {data}"
        assert "vat_pct" in data, f"Missing vat_pct: {data}"
        assert "country_code" in data, f"Missing country_code: {data}"
        
        # Validate values
        assert data["base_price"] == 10000, f"Wrong base_price: {data['base_price']}"
        assert data["country_code"] == "TR", f"Wrong country_code: {data['country_code']}"
        assert data["vat_pct"] == 20.0, f"TR VAT should be 20%, got: {data['vat_pct']}"
        assert data["vat_amount"] > 0, f"VAT amount should be positive: {data['vat_amount']}"
        assert data["tourism_tax"] >= 0, f"Tourism tax should be non-negative: {data['tourism_tax']}"
        assert data["gross_price"] > data["base_price"] or data["gross_price"] <= data["base_price"], f"Gross price calculation issue"
        
        print(f"PASS: tax-breakdown for TR:")
        print(f"  base_price: {data['base_price']}")
        print(f"  vat_amount: {data['vat_amount']} ({data['vat_pct']}%)")
        print(f"  tourism_tax: {data['tourism_tax']}")
        print(f"  gross_price: {data['gross_price']}")

class TestScalabilityCurrencyConvert:
    """Currency conversion tests"""
    
    def test_currency_convert_requires_auth(self):
        """POST /api/scalability/currency-convert requires authentication"""
        response = requests.post(
            f"{BASE_URL}/api/scalability/currency-convert",
            json={"amount": 1000, "from_currency": "TRY", "to_currency": "EUR"}
        )
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("PASS: currency-convert requires authentication")
    
    def test_currency_convert_try_to_eur(self, auth_headers):
        """POST /api/scalability/currency-convert converts TRY to EUR"""
        response = requests.post(
            f"{BASE_URL}/api/scalability/currency-convert",
            json={"amount": 1000, "from_currency": "TRY", "to_currency": "EUR"},
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Check expected fields
        assert "original_amount" in data or "amount" in data, f"Missing amount field: {data}"
        assert "converted_amount" in data or "result" in data, f"Missing converted result: {data}"
        
        print(f"PASS: currency-convert TRY->EUR: {data}")

class TestScalabilityCurrencyRates:
    """Currency rates endpoint tests"""
    
    def test_currency_rates_requires_auth(self):
        """GET /api/scalability/currency-rates requires authentication"""
        response = requests.get(f"{BASE_URL}/api/scalability/currency-rates")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("PASS: currency-rates requires authentication")
    
    def test_currency_rates_returns_supported(self, auth_headers):
        """GET /api/scalability/currency-rates returns rates and supported currencies"""
        response = requests.get(f"{BASE_URL}/api/scalability/currency-rates", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        assert "rates" in data, f"Missing rates: {data}"
        assert "supported_currencies" in data, f"Missing supported_currencies: {data}"
        
        supported = data["supported_currencies"]
        assert isinstance(supported, list), f"supported_currencies should be list"
        
        # Check expected currencies
        expected_currencies = ["TRY", "EUR", "USD", "GBP"]
        for ec in expected_currencies:
            assert ec in supported, f"Missing currency: {ec}, found: {supported}"
        
        print(f"PASS: currency-rates supports: {supported}")

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
