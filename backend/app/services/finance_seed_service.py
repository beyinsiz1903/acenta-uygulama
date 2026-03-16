"""Finance Seed Service — Demo data for Phase 2A.

Creates realistic demo data covering:
- confirmed, cancelled, refunded bookings
- open & overdue payables
- agency negative balance
- successful settlement run
- partially reconciled settlement run
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
import random

from app.db import get_db


async def seed_finance_data(org_id: str) -> dict:
    db = await get_db()

    # Clear existing data
    await db.ledger_entries.delete_many({"org_id": org_id})
    await db.settlement_runs.delete_many({"org_id": org_id})
    await db.agency_balances.delete_many({"org_id": org_id})
    await db.supplier_payables.delete_many({"org_id": org_id})
    await db.reconciliation_snapshots.delete_many({"org_id": org_id})

    now = datetime.now(timezone.utc)

    # ----- Agencies -----
    agencies = [
        {"id": "AGN-001", "name": "Sunshine Travel"},
        {"id": "AGN-002", "name": "BlueSky Tours"},
        {"id": "AGN-003", "name": "Anatolian Voyages"},
        {"id": "AGN-004", "name": "Mediterranean Holidays"},
        {"id": "AGN-005", "name": "Cappadocia Adventures"},
    ]

    # ----- Suppliers -----
    suppliers = [
        {"id": "SUP-RH", "name": "RateHawk", "terms": 30},
        {"id": "SUP-TBO", "name": "TBO Holidays", "terms": 45},
        {"id": "SUP-PAX", "name": "Paximum", "terms": 30},
        {"id": "SUP-WT", "name": "WTatil", "terms": 15},
    ]

    # ----- Ledger Entries -----
    ledger_entries = []
    entry_counter = 0

    booking_scenarios = [
        # (booking_ref, booking_status, financial_status, agency, supplier, sell_price, cost_price, description)
        ("BK-2026-001", "confirmed", "posted", 0, 0, 2500.00, 1800.00, "Grand Hotel Antalya - 5 gece"),
        ("BK-2026-002", "confirmed", "posted", 0, 1, 1800.00, 1300.00, "Bodrum Beach Resort - 3 gece"),
        ("BK-2026-003", "confirmed", "settled", 1, 0, 3200.00, 2400.00, "Istanbul Hilton - 4 gece"),
        ("BK-2026-004", "confirmed", "settled", 1, 2, 1500.00, 1100.00, "Cappadocia Cave Hotel - 2 gece"),
        ("BK-2026-005", "cancelled", "voided", 2, 0, 2800.00, 2000.00, "Side Premium Resort - 7 gece (iptal)"),
        ("BK-2026-006", "refunded", "posted", 2, 1, 1200.00, 900.00, "Fethiye Villa - 3 gece (iade)"),
        ("BK-2026-007", "confirmed", "posted", 3, 2, 4500.00, 3200.00, "Antalya All-Inclusive - 7 gece"),
        ("BK-2026-008", "confirmed", "posted", 3, 3, 1900.00, 1400.00, "Cesme Boutique Hotel - 3 gece"),
        ("BK-2026-009", "confirmed", "settled", 4, 0, 2100.00, 1500.00, "Goreme Heritage - 2 gece"),
        ("BK-2026-010", "confirmed", "posted", 4, 3, 3800.00, 2700.00, "Kas Luxury Villa - 5 gece"),
        ("BK-2026-011", "confirmed", "posted", 0, 0, 5200.00, 3800.00, "Dalaman Premium Resort - 7 gece"),
        ("BK-2026-012", "confirmed", "posted", 1, 1, 1600.00, 1200.00, "Alanya Beach Hotel - 4 gece"),
        ("BK-2026-013", "confirmed", "settled", 2, 2, 2900.00, 2100.00, "Kemer Pine Resort - 5 gece"),
        ("BK-2026-014", "cancelled", "voided", 3, 0, 1100.00, 800.00, "Marmaris City Hotel (iptal)"),
        ("BK-2026-015", "confirmed", "posted", 4, 1, 4200.00, 3000.00, "Belek Golf Resort - 7 gece"),
        ("BK-2026-016", "confirmed", "posted", 0, 2, 1750.00, 1250.00, "Kusadasi Marina Hotel - 3 gece"),
        ("BK-2026-017", "refunded", "posted", 1, 3, 950.00, 700.00, "Trabzon Uzungol Cabin (iade)"),
        ("BK-2026-018", "confirmed", "posted", 2, 0, 3100.00, 2200.00, "Bodrum Lux Residence - 4 gece"),
        ("BK-2026-019", "confirmed", "posted", 3, 1, 2600.00, 1900.00, "Izmir Kordon Hotel - 5 gece"),
        ("BK-2026-020", "confirmed", "settled", 4, 2, 1400.00, 1000.00, "Safranbolu Ottoman Inn - 2 gece"),
    ]

    for i, (bk_ref, bk_status, fin_status, agn_idx, sup_idx, sell, cost, desc) in enumerate(booking_scenarios):
        entry_counter += 1
        days_ago = random.randint(1, 60)
        created = now - timedelta(days=days_ago, hours=random.randint(0, 23))

        # Receivable entry (agency owes us)
        ledger_entries.append({
            "entry_id": f"LE-{entry_counter:04d}",
            "entry_type": "DEBIT",
            "account_type": "RECEIVABLE",
            "entity_type": "AGENCY",
            "entity_id": agencies[agn_idx]["id"],
            "entity_name": agencies[agn_idx]["name"],
            "booking_ref": bk_ref,
            "booking_status": bk_status,
            "financial_status": fin_status,
            "amount": sell,
            "currency": "EUR",
            "description": desc,
            "settlement_run_id": None,
            "created_at": created.isoformat(),
            "posted_at": created.isoformat(),
            "org_id": org_id,
        })

        entry_counter += 1
        # Payable entry (we owe supplier)
        ledger_entries.append({
            "entry_id": f"LE-{entry_counter:04d}",
            "entry_type": "CREDIT",
            "account_type": "PAYABLE",
            "entity_type": "SUPPLIER",
            "entity_id": suppliers[sup_idx]["id"],
            "entity_name": suppliers[sup_idx]["name"],
            "booking_ref": bk_ref,
            "booking_status": bk_status,
            "financial_status": fin_status,
            "amount": cost,
            "currency": "EUR",
            "description": desc,
            "settlement_run_id": None,
            "created_at": created.isoformat(),
            "posted_at": created.isoformat(),
            "org_id": org_id,
        })

        entry_counter += 1
        # Revenue entry (margin)
        if bk_status == "confirmed":
            ledger_entries.append({
                "entry_id": f"LE-{entry_counter:04d}",
                "entry_type": "CREDIT",
                "account_type": "REVENUE",
                "entity_type": "AGENCY",
                "entity_id": agencies[agn_idx]["id"],
                "entity_name": agencies[agn_idx]["name"],
                "booking_ref": bk_ref,
                "booking_status": bk_status,
                "financial_status": fin_status,
                "amount": round(sell - cost, 2),
                "currency": "EUR",
                "description": f"Marj: {desc}",
                "settlement_run_id": None,
                "created_at": created.isoformat(),
                "posted_at": created.isoformat(),
                "org_id": org_id,
            })

    # Link settled entries to settlement runs
    settled_entries = [e for e in ledger_entries if e["financial_status"] == "settled"]
    for e in settled_entries[:6]:
        e["settlement_run_id"] = "SR-001"
    for e in settled_entries[6:]:
        e["settlement_run_id"] = "SR-002"

    await db.ledger_entries.insert_many(ledger_entries)

    # ----- Settlement Runs -----
    settlement_runs = [
        {
            "run_id": "SR-001",
            "status": "paid",
            "run_type": "AGENCY",
            "entity_id": "AGN-002",
            "entity_name": "BlueSky Tours",
            "total_amount": 4700.00,
            "currency": "EUR",
            "entries_count": 4,
            "period_start": (now - timedelta(days=45)).strftime("%Y-%m-%d"),
            "period_end": (now - timedelta(days=15)).strftime("%Y-%m-%d"),
            "created_at": (now - timedelta(days=14)).isoformat(),
            "approved_at": (now - timedelta(days=12)).isoformat(),
            "paid_at": (now - timedelta(days=10)).isoformat(),
            "notes": "Ocak donemi mutabakat - odeme tamamlandi",
            "org_id": org_id,
        },
        {
            "run_id": "SR-002",
            "status": "partially_reconciled",
            "run_type": "SUPPLIER",
            "entity_id": "SUP-RH",
            "entity_name": "RateHawk",
            "total_amount": 7900.00,
            "currency": "EUR",
            "entries_count": 5,
            "period_start": (now - timedelta(days=30)).strftime("%Y-%m-%d"),
            "period_end": now.strftime("%Y-%m-%d"),
            "created_at": (now - timedelta(days=5)).isoformat(),
            "approved_at": (now - timedelta(days=3)).isoformat(),
            "paid_at": None,
            "notes": "Subat donemi - kismi uzlasma, 2 kayit uyumsuz",
            "org_id": org_id,
        },
        {
            "run_id": "SR-003",
            "status": "pending_approval",
            "run_type": "AGENCY",
            "entity_id": "AGN-004",
            "entity_name": "Mediterranean Holidays",
            "total_amount": 6400.00,
            "currency": "EUR",
            "entries_count": 3,
            "period_start": (now - timedelta(days=20)).strftime("%Y-%m-%d"),
            "period_end": now.strftime("%Y-%m-%d"),
            "created_at": (now - timedelta(days=2)).isoformat(),
            "approved_at": None,
            "paid_at": None,
            "notes": "Onay bekliyor",
            "org_id": org_id,
        },
        {
            "run_id": "SR-004",
            "status": "draft",
            "run_type": "SUPPLIER",
            "entity_id": "SUP-TBO",
            "entity_name": "TBO Holidays",
            "total_amount": 3100.00,
            "currency": "EUR",
            "entries_count": 2,
            "period_start": (now - timedelta(days=15)).strftime("%Y-%m-%d"),
            "period_end": now.strftime("%Y-%m-%d"),
            "created_at": (now - timedelta(days=1)).isoformat(),
            "approved_at": None,
            "paid_at": None,
            "notes": "Taslak - henuz onaya gonderilmedi",
            "org_id": org_id,
        },
        {
            "run_id": "SR-005",
            "status": "approved",
            "run_type": "AGENCY",
            "entity_id": "AGN-001",
            "entity_name": "Sunshine Travel",
            "total_amount": 9450.00,
            "currency": "EUR",
            "entries_count": 4,
            "period_start": (now - timedelta(days=25)).strftime("%Y-%m-%d"),
            "period_end": (now - timedelta(days=5)).strftime("%Y-%m-%d"),
            "created_at": (now - timedelta(days=4)).isoformat(),
            "approved_at": (now - timedelta(days=1)).isoformat(),
            "paid_at": None,
            "notes": "Onaylandi, odeme bekleniyor",
            "org_id": org_id,
        },
    ]
    await db.settlement_runs.insert_many(settlement_runs)

    # ----- Agency Balances -----
    agency_balances = [
        {
            "agency_id": "AGN-001",
            "agency_name": "Sunshine Travel",
            "total_receivable": 9450.00,
            "total_collected": 5200.00,
            "outstanding_balance": 4250.00,
            "overdue_amount": 0,
            "credit_limit": 15000.00,
            "currency": "EUR",
            "last_payment_date": (now - timedelta(days=8)).isoformat(),
            "status": "current",
            "booking_count": 4,
            "open_settlement_runs": 1,
            "updated_at": now.isoformat(),
            "org_id": org_id,
        },
        {
            "agency_id": "AGN-002",
            "agency_name": "BlueSky Tours",
            "total_receivable": 7050.00,
            "total_collected": 7050.00,
            "outstanding_balance": 0,
            "overdue_amount": 0,
            "credit_limit": 12000.00,
            "currency": "EUR",
            "last_payment_date": (now - timedelta(days=10)).isoformat(),
            "status": "current",
            "booking_count": 4,
            "open_settlement_runs": 0,
            "updated_at": now.isoformat(),
            "org_id": org_id,
        },
        {
            "agency_id": "AGN-003",
            "agency_name": "Anatolian Voyages",
            "total_receivable": 7200.00,
            "total_collected": 2900.00,
            "outstanding_balance": 4300.00,
            "overdue_amount": 2800.00,
            "credit_limit": 8000.00,
            "currency": "EUR",
            "last_payment_date": (now - timedelta(days=35)).isoformat(),
            "status": "overdue",
            "booking_count": 4,
            "open_settlement_runs": 1,
            "updated_at": now.isoformat(),
            "org_id": org_id,
        },
        {
            "agency_id": "AGN-004",
            "agency_name": "Mediterranean Holidays",
            "total_receivable": 10100.00,
            "total_collected": 12500.00,
            "outstanding_balance": -2400.00,
            "overdue_amount": 0,
            "credit_limit": 20000.00,
            "currency": "EUR",
            "last_payment_date": (now - timedelta(days=3)).isoformat(),
            "status": "negative",
            "booking_count": 4,
            "open_settlement_runs": 1,
            "updated_at": now.isoformat(),
            "org_id": org_id,
        },
        {
            "agency_id": "AGN-005",
            "agency_name": "Cappadocia Adventures",
            "total_receivable": 11500.00,
            "total_collected": 7200.00,
            "outstanding_balance": 4300.00,
            "overdue_amount": 1500.00,
            "credit_limit": 10000.00,
            "currency": "EUR",
            "last_payment_date": (now - timedelta(days=18)).isoformat(),
            "status": "overdue",
            "booking_count": 4,
            "open_settlement_runs": 1,
            "updated_at": now.isoformat(),
            "org_id": org_id,
        },
    ]
    await db.agency_balances.insert_many(agency_balances)

    # ----- Supplier Payables -----
    supplier_payables = [
        {
            "supplier_id": "SUP-RH",
            "supplier_name": "RateHawk",
            "total_payable": 11700.00,
            "total_paid": 4200.00,
            "outstanding_amount": 7500.00,
            "overdue_amount": 3200.00,
            "currency": "EUR",
            "payment_terms_days": 30,
            "next_due_date": (now + timedelta(days=5)).strftime("%Y-%m-%d"),
            "status": "overdue",
            "booking_count": 7,
            "open_settlement_runs": 1,
            "updated_at": now.isoformat(),
            "org_id": org_id,
        },
        {
            "supplier_id": "SUP-TBO",
            "supplier_name": "TBO Holidays",
            "total_payable": 6100.00,
            "total_paid": 3800.00,
            "outstanding_amount": 2300.00,
            "overdue_amount": 0,
            "currency": "EUR",
            "payment_terms_days": 45,
            "next_due_date": (now + timedelta(days=20)).strftime("%Y-%m-%d"),
            "status": "current",
            "booking_count": 4,
            "open_settlement_runs": 1,
            "updated_at": now.isoformat(),
            "org_id": org_id,
        },
        {
            "supplier_id": "SUP-PAX",
            "supplier_name": "Paximum",
            "total_payable": 7550.00,
            "total_paid": 7550.00,
            "outstanding_amount": 0,
            "overdue_amount": 0,
            "currency": "EUR",
            "payment_terms_days": 30,
            "next_due_date": None,
            "status": "paid",
            "booking_count": 4,
            "open_settlement_runs": 0,
            "updated_at": now.isoformat(),
            "org_id": org_id,
        },
        {
            "supplier_id": "SUP-WT",
            "supplier_name": "WTatil",
            "total_payable": 4800.00,
            "total_paid": 2100.00,
            "outstanding_amount": 2700.00,
            "overdue_amount": 0,
            "currency": "EUR",
            "payment_terms_days": 15,
            "next_due_date": (now + timedelta(days=8)).strftime("%Y-%m-%d"),
            "status": "current",
            "booking_count": 3,
            "open_settlement_runs": 0,
            "updated_at": now.isoformat(),
            "org_id": org_id,
        },
    ]
    await db.supplier_payables.insert_many(supplier_payables)

    # ----- Reconciliation Snapshots -----
    reconciliation_snapshots = [
        {
            "snapshot_id": "REC-2025-12",
            "period": "2025-12",
            "total_revenue": 42000.00,
            "total_cost": 30500.00,
            "gross_margin": 11500.00,
            "gross_margin_pct": 27.4,
            "total_receivable": 42000.00,
            "total_payable": 30500.00,
            "reconciled_amount": 42000.00,
            "unreconciled_amount": 0,
            "mismatch_count": 0,
            "mismatch_amount": 0,
            "currency": "EUR",
            "status": "completed",
            "created_at": (now - timedelta(days=75)).isoformat(),
            "org_id": org_id,
        },
        {
            "snapshot_id": "REC-2026-01",
            "period": "2026-01",
            "total_revenue": 48500.00,
            "total_cost": 35200.00,
            "gross_margin": 13300.00,
            "gross_margin_pct": 27.4,
            "total_receivable": 48500.00,
            "total_payable": 35200.00,
            "reconciled_amount": 45000.00,
            "unreconciled_amount": 3500.00,
            "mismatch_count": 2,
            "mismatch_amount": 1200.00,
            "currency": "EUR",
            "status": "has_mismatches",
            "created_at": (now - timedelta(days=45)).isoformat(),
            "org_id": org_id,
        },
        {
            "snapshot_id": "REC-2026-02",
            "period": "2026-02",
            "total_revenue": 55200.00,
            "total_cost": 39800.00,
            "gross_margin": 15400.00,
            "gross_margin_pct": 27.9,
            "total_receivable": 55200.00,
            "total_payable": 39800.00,
            "reconciled_amount": 48000.00,
            "unreconciled_amount": 7200.00,
            "mismatch_count": 3,
            "mismatch_amount": 1800.00,
            "currency": "EUR",
            "status": "in_progress",
            "created_at": (now - timedelta(days=10)).isoformat(),
            "org_id": org_id,
        },
    ]
    await db.reconciliation_snapshots.insert_many(reconciliation_snapshots)

    # ----- Finance Exceptions (Phase 2B) -----
    await db.finance_exceptions.delete_many({"org_id": org_id})

    finance_exceptions = [
        {
            "exception_id": "EXC-001",
            "exception_type": "amount_mismatch",
            "severity": "high",
            "status": "open",
            "booking_ref": "BK-2026-003",
            "entity_type": "SUPPLIER",
            "entity_id": "SUP-RH",
            "entity_name": "RateHawk",
            "expected_amount": 2400.00,
            "actual_amount": 2520.00,
            "amount_difference": 120.00,
            "currency": "EUR",
            "description": "Tedarikci faturasi ile kayitli maliyet arasinda 120 EUR fark",
            "source": "supplier_invoice",
            "related_settlement_run": "SR-002",
            "created_at": (now - timedelta(days=3)).isoformat(),
            "resolution": None,
            "resolved_by": None,
            "resolved_at": None,
            "resolution_notes": "",
            "org_id": org_id,
        },
        {
            "exception_id": "EXC-002",
            "exception_type": "duplicate_entry",
            "severity": "medium",
            "status": "open",
            "booking_ref": "BK-2026-007",
            "entity_type": "AGENCY",
            "entity_id": "AGN-004",
            "entity_name": "Mediterranean Holidays",
            "expected_amount": 4500.00,
            "actual_amount": 9000.00,
            "amount_difference": 4500.00,
            "currency": "EUR",
            "description": "Ayni rezervasyon icin mukerrer kayit tespit edildi",
            "source": "ledger_audit",
            "related_settlement_run": None,
            "created_at": (now - timedelta(days=2)).isoformat(),
            "resolution": None,
            "resolved_by": None,
            "resolved_at": None,
            "resolution_notes": "",
            "org_id": org_id,
        },
        {
            "exception_id": "EXC-003",
            "exception_type": "currency_mismatch",
            "severity": "high",
            "status": "open",
            "booking_ref": "BK-2026-011",
            "entity_type": "SUPPLIER",
            "entity_id": "SUP-RH",
            "entity_name": "RateHawk",
            "expected_amount": 3800.00,
            "actual_amount": 3650.00,
            "amount_difference": 150.00,
            "currency": "EUR",
            "description": "Doviz kuru farkindan kaynakli tutar uyumsuzlugu (USD->EUR)",
            "source": "reconciliation",
            "related_settlement_run": "SR-002",
            "created_at": (now - timedelta(days=4)).isoformat(),
            "resolution": None,
            "resolved_by": None,
            "resolved_at": None,
            "resolution_notes": "",
            "org_id": org_id,
        },
        {
            "exception_id": "EXC-004",
            "exception_type": "missing_invoice",
            "severity": "low",
            "status": "open",
            "booking_ref": "BK-2026-015",
            "entity_type": "SUPPLIER",
            "entity_id": "SUP-TBO",
            "entity_name": "TBO Holidays",
            "expected_amount": 3000.00,
            "actual_amount": 0,
            "amount_difference": 3000.00,
            "currency": "EUR",
            "description": "Tedarikci faturasi henuz alinmadi, vade yaklasıyor",
            "source": "supplier_check",
            "related_settlement_run": "SR-004",
            "created_at": (now - timedelta(days=1)).isoformat(),
            "resolution": None,
            "resolved_by": None,
            "resolved_at": None,
            "resolution_notes": "",
            "org_id": org_id,
        },
        {
            "exception_id": "EXC-005",
            "exception_type": "amount_mismatch",
            "severity": "medium",
            "status": "resolved",
            "booking_ref": "BK-2026-009",
            "entity_type": "AGENCY",
            "entity_id": "AGN-005",
            "entity_name": "Cappadocia Adventures",
            "expected_amount": 2100.00,
            "actual_amount": 2050.00,
            "amount_difference": 50.00,
            "currency": "EUR",
            "description": "Acenta odemesinde 50 EUR eksik tahsilat",
            "source": "payment_reconciliation",
            "related_settlement_run": "SR-001",
            "created_at": (now - timedelta(days=12)).isoformat(),
            "resolution": "adjusted",
            "resolved_by": "admin",
            "resolved_at": (now - timedelta(days=10)).isoformat(),
            "resolution_notes": "Fark sonraki donem mahsup edildi",
            "org_id": org_id,
        },
        {
            "exception_id": "EXC-006",
            "exception_type": "booking_status_conflict",
            "severity": "high",
            "status": "open",
            "booking_ref": "BK-2026-006",
            "entity_type": "AGENCY",
            "entity_id": "AGN-003",
            "entity_name": "Anatolian Voyages",
            "expected_amount": 0,
            "actual_amount": 1200.00,
            "amount_difference": 1200.00,
            "currency": "EUR",
            "description": "Iade edilmis rezervasyon icin hala acik alacak kaydi mevcut",
            "source": "status_audit",
            "related_settlement_run": None,
            "created_at": (now - timedelta(days=5)).isoformat(),
            "resolution": None,
            "resolved_by": None,
            "resolved_at": None,
            "resolution_notes": "",
            "org_id": org_id,
        },
    ]
    await db.finance_exceptions.insert_many(finance_exceptions)

    return {
        "status": "ok",
        "seeded": {
            "ledger_entries": len(ledger_entries),
            "settlement_runs": len(settlement_runs),
            "agency_balances": len(agency_balances),
            "supplier_payables": len(supplier_payables),
            "reconciliation_snapshots": len(reconciliation_snapshots),
            "finance_exceptions": len(finance_exceptions),
        },
    }
