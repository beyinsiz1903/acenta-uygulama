"""Finance Ledger Phase 2A API Tests — Iteration 133.

Tests for Financial Ledger & Settlement Visibility Layer endpoints:
- Ledger entries, summary, recent postings
- Agency balances with filters
- Supplier payables with filters
- Settlement runs with filters, stats, detail
- Reconciliation summary, snapshots, margin revenue
- Finance overview (combined KPI data)
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")


class TestLedgerEndpoints:
    """Ledger summary and entries endpoints"""

    def test_ledger_summary_returns_totals(self):
        """GET /api/finance/ledger/summary returns ledger totals"""
        response = requests.get(f"{BASE_URL}/api/finance/ledger/summary")
        assert response.status_code == 200
        data = response.json()
        # Validate structure
        assert "total_entries" in data
        assert "total_debit" in data
        assert "total_credit" in data
        assert "net_balance" in data
        assert "posted_count" in data
        assert "settled_count" in data
        assert "voided_count" in data
        # Validate data types
        assert isinstance(data["total_entries"], int)
        assert isinstance(data["total_debit"], (int, float))
        assert isinstance(data["total_credit"], (int, float))
        # Verify seeded data exists
        assert data["total_entries"] > 0
        print(f"✅ Ledger summary: {data['total_entries']} entries, net_balance={data['net_balance']}")

    def test_receivable_payable_breakdown(self):
        """GET /api/finance/ledger/receivable-payable returns receivable/payable breakdown"""
        response = requests.get(f"{BASE_URL}/api/finance/ledger/receivable-payable")
        assert response.status_code == 200
        data = response.json()
        # Validate structure
        assert "total_receivable" in data
        assert "receivable_count" in data
        assert "total_payable" in data
        assert "payable_count" in data
        assert "total_revenue" in data
        assert "net_position" in data
        # Verify receivable > payable (positive margin business)
        assert data["total_receivable"] >= data["total_payable"]
        print(f"✅ Receivable: {data['total_receivable']}, Payable: {data['total_payable']}, Net: {data['net_position']}")

    def test_recent_postings_list(self):
        """GET /api/finance/ledger/recent-postings returns recent entries list"""
        response = requests.get(f"{BASE_URL}/api/finance/ledger/recent-postings?limit=10")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 10
        if data:
            entry = data[0]
            assert "entry_id" in entry
            assert "entry_type" in entry
            assert "account_type" in entry
            assert "entity_name" in entry
            assert "amount" in entry
            assert "financial_status" in entry
        print(f"✅ Recent postings: {len(data)} entries returned")

    def test_ledger_entries_paginated(self):
        """GET /api/finance/ledger/entries returns paginated ledger entries"""
        response = requests.get(f"{BASE_URL}/api/finance/ledger/entries?limit=5")
        assert response.status_code == 200
        data = response.json()
        assert "entries" in data
        assert "total" in data
        assert "skip" in data
        assert "limit" in data
        assert data["limit"] == 5
        assert len(data["entries"]) <= 5
        print(f"✅ Ledger entries: {data['total']} total, {len(data['entries'])} returned")

    def test_ledger_entries_filter_by_account_type(self):
        """GET /api/finance/ledger/entries with account_type filter"""
        response = requests.get(f"{BASE_URL}/api/finance/ledger/entries?account_type=RECEIVABLE")
        assert response.status_code == 200
        data = response.json()
        for entry in data["entries"]:
            assert entry["account_type"] == "RECEIVABLE"
        print(f"✅ Filtered RECEIVABLE entries: {data['total']}")

    def test_ledger_entry_detail_by_id(self):
        """GET /api/finance/ledger/entries/{id} returns single entry detail (LE-0001)"""
        response = requests.get(f"{BASE_URL}/api/finance/ledger/entries/LE-0001")
        assert response.status_code == 200
        data = response.json()
        assert data["entry_id"] == "LE-0001"
        assert "entry_type" in data
        assert "account_type" in data
        assert "entity_name" in data
        assert "amount" in data
        assert "booking_ref" in data
        print(f"✅ Entry LE-0001: {data['entity_name']}, {data['amount']} EUR")


class TestAgencyBalancesEndpoints:
    """Agency balance tracking endpoints"""

    def test_agency_balances_list(self):
        """GET /api/finance/ledger/agency-balances returns agency balance list"""
        response = requests.get(f"{BASE_URL}/api/finance/ledger/agency-balances")
        assert response.status_code == 200
        data = response.json()
        assert "balances" in data
        assert "total" in data
        assert isinstance(data["balances"], list)
        if data["balances"]:
            balance = data["balances"][0]
            assert "agency_id" in balance
            assert "agency_name" in balance
            assert "total_receivable" in balance
            assert "outstanding_balance" in balance
            assert "status" in balance
        print(f"✅ Agency balances: {data['total']} agencies")

    def test_agency_balances_filter_overdue(self):
        """GET /api/finance/ledger/agency-balances?status=overdue returns 2 agencies"""
        response = requests.get(f"{BASE_URL}/api/finance/ledger/agency-balances?status=overdue")
        assert response.status_code == 200
        data = response.json()
        # Per requirements, filter should return 2 overdue agencies
        assert data["total"] == 2
        for balance in data["balances"]:
            assert balance["status"] == "overdue"
        print(f"✅ Overdue agencies: {data['total']} (expected 2)")


class TestSupplierPayablesEndpoints:
    """Supplier payables tracking endpoints"""

    def test_supplier_payables_list(self):
        """GET /api/finance/ledger/supplier-payables returns supplier payables"""
        response = requests.get(f"{BASE_URL}/api/finance/ledger/supplier-payables")
        assert response.status_code == 200
        data = response.json()
        assert "payables" in data
        assert "total" in data
        assert isinstance(data["payables"], list)
        if data["payables"]:
            payable = data["payables"][0]
            assert "supplier_id" in payable
            assert "supplier_name" in payable
            assert "total_payable" in payable
            assert "outstanding_amount" in payable
            assert "status" in payable
        print(f"✅ Supplier payables: {data['total']} suppliers")

    def test_supplier_payables_filter_overdue(self):
        """GET /api/finance/ledger/supplier-payables?status=overdue returns 1 supplier (RateHawk)"""
        response = requests.get(f"{BASE_URL}/api/finance/ledger/supplier-payables?status=overdue")
        assert response.status_code == 200
        data = response.json()
        # Per requirements, filter should return 1 overdue supplier (RateHawk)
        assert data["total"] == 1
        assert data["payables"][0]["supplier_name"] == "RateHawk"
        assert data["payables"][0]["status"] == "overdue"
        print(f"✅ Overdue supplier: {data['payables'][0]['supplier_name']} (expected RateHawk)")


class TestSettlementRunEndpoints:
    """Settlement run lifecycle endpoints"""

    def test_settlement_runs_list(self):
        """GET /api/finance/settlement-runs returns settlement run list"""
        response = requests.get(f"{BASE_URL}/api/finance/settlement-runs")
        assert response.status_code == 200
        data = response.json()
        assert "runs" in data
        assert "total" in data
        assert isinstance(data["runs"], list)
        if data["runs"]:
            run = data["runs"][0]
            assert "run_id" in run
            assert "status" in run
            assert "run_type" in run
            assert "entity_name" in run
            assert "total_amount" in run
            assert "entries_count" in run
        print(f"✅ Settlement runs: {data['total']} runs")

    def test_settlement_runs_stats(self):
        """GET /api/finance/settlement-runs/stats returns run stats by status"""
        response = requests.get(f"{BASE_URL}/api/finance/settlement-runs/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_runs" in data
        assert "total_amount" in data
        assert "by_status" in data
        assert isinstance(data["by_status"], dict)
        print(f"✅ Settlement stats: {data['total_runs']} total runs, {data['total_amount']} EUR")

    def test_settlement_runs_filter_draft(self):
        """GET /api/finance/settlement-runs?status=draft returns 1 run"""
        response = requests.get(f"{BASE_URL}/api/finance/settlement-runs?status=draft")
        assert response.status_code == 200
        data = response.json()
        # Per requirements, filter should return 1 draft run
        assert data["total"] == 1
        assert data["runs"][0]["status"] == "draft"
        print(f"✅ Draft runs: {data['total']} (expected 1)")

    def test_settlement_run_detail_with_entries(self):
        """GET /api/finance/settlement-runs/{run_id} returns run detail with linked entries (SR-001)"""
        response = requests.get(f"{BASE_URL}/api/finance/settlement-runs/SR-001")
        assert response.status_code == 200
        data = response.json()
        assert data["run_id"] == "SR-001"
        assert data["status"] == "paid"
        assert "entries" in data
        assert isinstance(data["entries"], list)
        # SR-001 should have linked entries
        assert len(data["entries"]) > 0
        for entry in data["entries"]:
            assert entry["settlement_run_id"] == "SR-001"
        print(f"✅ Run SR-001 detail: {len(data['entries'])} linked entries")


class TestReconciliationEndpoints:
    """Reconciliation and margin analysis endpoints"""

    def test_reconciliation_summary(self):
        """GET /api/finance/reconciliation/summary returns recon summary"""
        response = requests.get(f"{BASE_URL}/api/finance/reconciliation/summary")
        assert response.status_code == 200
        data = response.json()
        assert "latest_snapshot" in data
        assert "aggregate" in data
        # Validate latest snapshot
        latest = data["latest_snapshot"]
        if latest:
            assert "snapshot_id" in latest
            assert "period" in latest
            assert "total_revenue" in latest
            assert "gross_margin" in latest
        # Validate aggregate
        agg = data["aggregate"]
        assert "total_revenue" in agg
        assert "gross_margin" in agg
        assert "total_reconciled" in agg
        assert "total_mismatches" in agg
        print(f"✅ Recon summary: margin={agg['gross_margin']} EUR, mismatches={agg['total_mismatches']}")

    def test_reconciliation_snapshots(self):
        """GET /api/finance/reconciliation/snapshots returns snapshot list"""
        response = requests.get(f"{BASE_URL}/api/finance/reconciliation/snapshots")
        assert response.status_code == 200
        data = response.json()
        assert "snapshots" in data
        assert "total" in data
        assert isinstance(data["snapshots"], list)
        if data["snapshots"]:
            snap = data["snapshots"][0]
            assert "snapshot_id" in snap
            assert "period" in snap
            assert "total_revenue" in snap
            assert "gross_margin_pct" in snap
            assert "status" in snap
        print(f"✅ Recon snapshots: {data['total']} periods")

    def test_margin_revenue_summary(self):
        """GET /api/finance/reconciliation/margin-revenue returns margin data"""
        response = requests.get(f"{BASE_URL}/api/finance/reconciliation/margin-revenue")
        assert response.status_code == 200
        data = response.json()
        assert "periods" in data
        assert "totals" in data
        assert isinstance(data["periods"], list)
        # Validate totals
        totals = data["totals"]
        assert "total_revenue" in totals
        assert "total_cost" in totals
        assert "gross_margin" in totals
        assert "gross_margin_pct" in totals
        print(f"✅ Margin revenue: {len(data['periods'])} periods, margin={totals['gross_margin_pct']}%")


class TestFinanceOverviewEndpoint:
    """Combined finance overview dashboard endpoint"""

    def test_finance_overview_combined_kpi(self):
        """GET /api/finance/ledger/overview returns combined KPI data"""
        response = requests.get(f"{BASE_URL}/api/finance/ledger/overview")
        assert response.status_code == 200
        data = response.json()
        # Validate all sections
        assert "ledger_summary" in data
        assert "receivable_payable" in data
        assert "settlement_stats" in data
        assert "reconciliation" in data
        # Validate ledger_summary
        ls = data["ledger_summary"]
        assert "total_entries" in ls
        assert "net_balance" in ls
        # Validate receivable_payable
        rp = data["receivable_payable"]
        assert "total_receivable" in rp
        assert "net_position" in rp
        # Validate settlement_stats
        ss = data["settlement_stats"]
        assert "total_runs" in ss
        assert "by_status" in ss
        # Validate reconciliation
        recon = data["reconciliation"]
        assert "latest_snapshot" in recon
        assert "aggregate" in recon
        print(f"✅ Finance overview: entries={ls['total_entries']}, runs={ss['total_runs']}, margin={recon['aggregate']['gross_margin']} EUR")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
