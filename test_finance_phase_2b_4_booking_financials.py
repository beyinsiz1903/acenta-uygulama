"""
Finance OS Phase 2B.4 Backend Test
Booking financials: denormalized booking_financials state

Scenarios:
1) ensure_financials creates single doc per booking
2) apply_refund_approved via refund approve flow updates totals
3) approve retry (closed case) does not change booking_financials (idempotent at case level)
4) multiple refunds on same booking accumulate correctly
5) clamp safety: penalty_total never negative even if refunded_total > sell_total
"""

import requests
import pymongo
from bson import ObjectId
from datetime import datetime

import anyio

BASE_URL = "http://localhost:8001"
MONGO_URL = "mongodb://localhost:27017/"


def _login_admin():
    r = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": "admin@acenta.test", "password": "admin123"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    return data["access_token"], data["user"]["organization_id"], data["user"]["email"]


def test_phase_2b_4_booking_financials():
    print("\n" + "=" * 80)
    print("FINANCE OS PHASE 2B.4 BACKEND TEST - BOOKING FINANCIALS")
    print("=" * 80 + "\n")

    client = pymongo.MongoClient(MONGO_URL)
    db = client["test_database"]

    token, org_id, admin_email = _login_admin()
    headers = {"Authorization": f"Bearer {token}"}

    # ------------------------------------------------------------------
    # 1) ensure_financials creates once per booking
    # ------------------------------------------------------------------
    print("1️⃣  ensure_financials creates single doc per booking...")

    booking1_id = ObjectId()
    db.bookings.insert_one(
        {
            "_id": booking1_id,
            "organization_id": org_id,
            "agency_id": f"phase2b4_ag_{ObjectId()}",
            "status": "CONFIRMED",
            "currency": "EUR",
            "amounts": {"sell": 1000.0},
        }
    )

    # First call should create booking_financials
    r1 = requests.get(
        f"{BASE_URL}/api/ops/finance/bookings/{booking1_id}/financials",
        headers=headers,
    )
    assert r1.status_code == 200, r1.text
    fin1 = r1.json()
    assert abs(fin1["sell_total"] - 1000.0) < 0.01

    # Second call should not create a new document
    r1b = requests.get(
        f"{BASE_URL}/api/ops/finance/bookings/{booking1_id}/financials",
        headers=headers,
    )
    assert r1b.status_code == 200, r1b.text

    cnt1 = db.booking_financials.count_documents(
        {"organization_id": org_id, "booking_id": str(booking1_id)}
    )
    assert cnt1 == 1

    print("   ✅ ensure_financials idempotent per booking")

    # ------------------------------------------------------------------
    # 2) Refund approve updates totals
    # ------------------------------------------------------------------
    print("2️⃣  Refund approve updates refunded_total and penalty_total...")

    from app.services.refund_calculator import RefundCalculatorService

    booking2_id = ObjectId()
    agency2_id = f"phase2b4_ag_{ObjectId()}"

    db.agencies.insert_one(
        {"_id": agency2_id, "organization_id": org_id, "name": "BF Agency 2", "status": "active"}
    )

    db.bookings.insert_one(
        {
            "_id": booking2_id,
            "organization_id": org_id,
            "agency_id": agency2_id,
            "status": "CONFIRMED",
            "currency": "EUR",
            "amounts": {"sell": 1000.0},
        }
    )

    calc = RefundCalculatorService(currency="EUR")
    booking2 = db.bookings.find_one({"_id": booking2_id})
    comp2 = calc.compute_refund(
        booking2,
        datetime.utcnow(),
        mode="policy_first",
        manual_requested_amount=300.0,
    )

    case2_id = ObjectId()
    now2 = datetime.utcnow()
    db.refund_cases.insert_one(
        {
            "_id": case2_id,
            "organization_id": org_id,
            "type": "refund",
            "booking_id": str(booking2_id),
            "agency_id": agency2_id,
            "status": "open",
            "reason": "customer_request",
            "currency": "EUR",
            "requested": {"amount": 300.0, "message": "BF 2 refund"},
            "computed": {
                "gross_sell": comp2.gross_sell,
                "penalty": comp2.penalty,
                "refundable": comp2.refundable,
                "basis": comp2.basis,
                "policy_ref": comp2.policy_ref,
            },
            "decision": None,
            "approved": {"amount": None},
            "ledger_posting_id": None,
            "booking_financials_id": None,
            "created_at": now2,
            "updated_at": now2,
            "decision_by_email": None,
            "decision_at": None,
        }
    )

    r2 = requests.post(
        f"{BASE_URL}/api/ops/finance/refunds/{case2_id}/approve",
        json={"approved_amount": 300.0},
        headers=headers,
    )
    assert r2.status_code == 200, r2.text

    fin2 = db.booking_financials.find_one(
        {"organization_id": org_id, "booking_id": str(booking2_id)}
    )
    assert fin2 is not None
    assert abs(fin2.get("sell_total", 0.0) - 1000.0) < 0.01
    assert abs(fin2.get("refunded_total", 0.0) - 300.0) < 0.01
    assert abs(fin2.get("penalty_total", 0.0) - 700.0) < 0.01

    print("   ✅ Refund approve updates totals correctly")

    # ------------------------------------------------------------------
    # 3) Approve retry does not change booking_financials
    # ------------------------------------------------------------------
    print("3️⃣  Approve retry keeps booking_financials unchanged...")

    before = db.booking_financials.find_one(
        {"organization_id": org_id, "booking_id": str(booking2_id)}
    )
    refunds_before = list(before.get("refunds_applied", []))

    r3 = requests.post(
        f"{BASE_URL}/api/ops/finance/refunds/{case2_id}/approve",
        json={"approved_amount": 300.0},
        headers=headers,
    )
    assert r3.status_code == 409, r3.text

    after = db.booking_financials.find_one(
        {"organization_id": org_id, "booking_id": str(booking2_id)}
    )
    assert abs(after.get("refunded_total", 0.0) - before.get("refunded_total", 0.0)) < 0.01
    assert abs(after.get("penalty_total", 0.0) - before.get("penalty_total", 0.0)) < 0.01
    assert len(after.get("refunds_applied", [])) == len(refunds_before)

    print("   ✅ Duplicate approve is idempotent at case level")

    # ------------------------------------------------------------------
    # 4) Multiple refunds accumulate correctly
    # ------------------------------------------------------------------
    print("4️⃣  Multiple refunds on same booking accumulate correctly...")

    booking3_id = ObjectId()
    agency3_id = f"phase2b4_ag_{ObjectId()}"

    db.agencies.insert_one(
        {"_id": agency3_id, "organization_id": org_id, "name": "BF Agency 3", "status": "active"}
    )

    db.bookings.insert_one(
        {
            "_id": booking3_id,
            "organization_id": org_id,
            "agency_id": agency3_id,
            "status": "CONFIRMED",
            "currency": "EUR",
            "amounts": {"sell": 1000.0},
        }
    )

    booking3 = db.bookings.find_one({"_id": booking3_id})

    # First refund 300
    comp3a = calc.compute_refund(
        booking3,
        datetime.utcnow(),
        mode="policy_first",
        manual_requested_amount=300.0,
    )
    case3a_id = ObjectId()
    now3a = datetime.utcnow()
    db.refund_cases.insert_one(
        {
            "_id": case3a_id,
            "organization_id": org_id,
            "type": "refund",
            "booking_id": str(booking3_id),
            "agency_id": agency3_id,
            "status": "open",
            "reason": "customer_request",
            "currency": "EUR",
            "requested": {"amount": 300.0, "message": "BF 3 refund A"},
            "computed": {
                "gross_sell": comp3a.gross_sell,
                "penalty": comp3a.penalty,
                "refundable": comp3a.refundable,
                "basis": comp3a.basis,
                "policy_ref": comp3a.policy_ref,
            },
            "decision": None,
            "approved": {"amount": None},
            "ledger_posting_id": None,
            "booking_financials_id": None,
            "created_at": now3a,
            "updated_at": now3a,
            "decision_by_email": None,
            "decision_at": None,
        }
    )

    r4a = requests.post(
        f"{BASE_URL}/api/ops/finance/refunds/{case3a_id}/approve",
        json={"approved_amount": 300.0},
        headers=headers,
    )
    assert r4a.status_code == 200, r4a.text

    # Second refund 200
    comp3b = calc.compute_refund(
        booking3,
        datetime.utcnow(),
        mode="policy_first",
        manual_requested_amount=200.0,
    )
    case3b_id = ObjectId()
    now3b = datetime.utcnow()
    db.refund_cases.insert_one(
        {
            "_id": case3b_id,
            "organization_id": org_id,
            "type": "refund",
            "booking_id": str(booking3_id),
            "agency_id": agency3_id,
            "status": "open",
            "reason": "customer_request",
            "currency": "EUR",
            "requested": {"amount": 200.0, "message": "BF 3 refund B"},
            "computed": {
                "gross_sell": comp3b.gross_sell,
                "penalty": comp3b.penalty,
                "refundable": comp3b.refundable,
                "basis": comp3b.basis,
                "policy_ref": comp3b.policy_ref,
            },
            "decision": None,
            "approved": {"amount": None},
            "ledger_posting_id": None,
            "booking_financials_id": None,
            "created_at": now3b,
            "updated_at": now3b,
            "decision_by_email": None,
            "decision_at": None,
        }
    )

    r4b = requests.post(
        f"{BASE_URL}/api/ops/finance/refunds/{case3b_id}/approve",
        json={"approved_amount": 200.0},
        headers=headers,
    )
    assert r4b.status_code == 200, r4b.text

    fin3 = db.booking_financials.find_one(
        {"organization_id": org_id, "booking_id": str(booking3_id)}
    )
    assert fin3 is not None
    assert abs(fin3.get("refunded_total", 0.0) - 500.0) < 0.01
    assert abs(fin3.get("penalty_total", 0.0) - 500.0) < 0.01
    assert len(fin3.get("refunds_applied", [])) == 2

    print("   ✅ Multiple refunds accumulated correctly")

    # ------------------------------------------------------------------
    # 5) Clamp safety: penalty_total never negative
    # ------------------------------------------------------------------
    print("5️⃣  Clamp safety: penalty_total >= 0 even if refunded_total > sell_total...")

    from app.services.booking_financials import BookingFinancialsService
    from app.db import get_db

    booking4_id = ObjectId()
    agency4_id = f"phase2b4_ag_{ObjectId()}"

    db.agencies.insert_one(
        {"_id": agency4_id, "organization_id": org_id, "name": "BF Agency 4", "status": "active"}
    )

    db.bookings.insert_one(
        {
            "_id": booking4_id,
            "organization_id": org_id,
            "agency_id": agency4_id,
            "status": "CONFIRMED",
            "currency": "EUR",
            "amounts": {"sell": 500.0},
        }
    )

    async def _clamp_flow():
        db_async = await get_db()
        svc = BookingFinancialsService(db_async)
        booking4 = await db_async.bookings.find_one(
            {"_id": booking4_id, "organization_id": org_id}
        )
        await svc.ensure_financials(org_id, booking4)
        await svc.apply_refund_approved(
            organization_id=org_id,
            booking_id=str(booking4_id),
            refund_case_id="clamp_case",
            ledger_posting_id="post_clamp",
            approved_amount=600.0,  # deliberately > sell_total
            applied_at=datetime.utcnow(),
        )
        return await db_async.booking_financials.find_one(
            {"organization_id": org_id, "booking_id": str(booking4_id)}
        )

    fin4 = anyio.run(_clamp_flow)
    assert fin4 is not None
    assert fin4.get("refunded_total", 0.0) > fin4.get("sell_total", 0.0)
    assert fin4.get("penalty_total", 0.0) >= 0.0

    print("   ✅ Clamp safety verified (penalty_total not negative)")

    client.close()


if __name__ == "__main__":
    test_phase_2b_4_booking_financials()
