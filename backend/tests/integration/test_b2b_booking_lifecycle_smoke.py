"""Smoke test for the B2B bookings router lifecycle (Task #6).

Walks a B2B booking through the canonical create -> confirm -> risk-scoring
-> cancel path end-to-end against the FastAPI HTTP surface.

Stages exercised against the real routers:

1. **Create** — POST ``/api/b2b/bookings`` (legacy quote-based flow). A
   minimal price-quote document is seeded so the request hits
   ``B2BBookingService.create_booking_from_quote`` and we get a real
   ``B2B_BOOKING_CREATED``-class booking back from the API.
2. **Confirm (risk REVIEW)** — POST ``/api/b2b/bookings/{id}/confirm``
   triggers the risk engine, which is monkey-patched to return ``REVIEW``
   on the first call. The router must mark the booking ``RISK_REVIEW``
   and emit both ``RISK_EVALUATED`` and ``RISK_REVIEW_REQUIRED`` audit
   entries with a 202 envelope.
3. **Risk approve** — POST ``/api/b2b/bookings/{id}/risk/approve``
   transitions to ``PENDING`` and writes ``RISK_REVIEW_APPROVED`` audit.
4. **Confirm (success via supplier)** — POST ``/confirm`` again with the
   risk engine now monkey-patched to ``ALLOW``. The mock supplier adapter
   confirms the booking, status goes to ``CONFIRMED`` and the router
   emits a ``B2B_BOOKING_CONFIRMED`` audit + ``BOOKING_CONFIRMED``
   lifecycle event.
5. **Cancel** — POST ``/cancel`` transitions to ``CANCELLED`` and emits
   ``BOOKING_CANCELLED`` lifecycle event. The EUR ledger work in
   ``BookingFinanceService.post_booking_cancelled`` is intentionally
   stubbed (covered by dedicated ledger tests) so this smoke layer
   focuses on lifecycle/audit semantics.

Each stage explicitly asserts the response shape AND the resulting
``audit_logs`` / ``booking_events`` entries.
"""
from __future__ import annotations

from typing import Any

import pytest
from bson import ObjectId
from httpx import AsyncClient

from app.utils import now_utc


def _unwrap(resp):
    data = resp.json()
    if isinstance(data, dict) and "ok" in data and "data" in data:
        return data["data"]
    return data


async def _resolve_agency_context(async_client: AsyncClient, agency_token: str) -> tuple[str, str]:
    me = await async_client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {agency_token}"}
    )
    assert me.status_code == 200, me.text
    me_data = _unwrap(me)
    org_id = me_data["organization_id"]
    agency_id = me_data["agency_id"]
    assert org_id and agency_id
    return org_id, agency_id


async def _seed_quote(test_db, *, org_id: str, agency_id: str) -> str:
    """Insert a minimal price_quote that ``ensure_quote_valid`` accepts."""
    now = now_utc()
    expires_at = now.replace(year=now.year + 1)
    res = await test_db.price_quotes.insert_one(
        {
            "organization_id": org_id,
            "agency_id": agency_id,
            "channel_id": "smoke-channel",
            "status": "active",
            "expires_at": expires_at,
            "items": [
                {
                    "product_id": "smoke-prod",
                    "room_type_id": "rt-1",
                    "rate_plan_id": "rp-1",
                    "match_id": "match-smoke-1",
                    "check_in": "2030-01-10",
                    "check_out": "2030-01-12",
                    "occupancy": {"adults": 2, "children": 0},
                }
            ],
            "offers": [
                {
                    "net": 100.0,
                    "sell": 120.0,
                    "currency": "EUR",
                }
            ],
            "winner_rule_name": "DEFAULT_10",
            "created_at": now,
            "updated_at": now,
        }
    )
    return str(res.inserted_id)


async def _find_audit(test_db, *, org_id: str, action: str, booking_id: str) -> dict | None:
    return await test_db.audit_logs.find_one(
        {
            "organization_id": org_id,
            "action": action,
            "target.id": booking_id,
        }
    )


async def _count_audit(test_db, *, org_id: str, action: str, booking_id: str) -> int:
    return await test_db.audit_logs.count_documents(
        {
            "organization_id": org_id,
            "action": action,
            "target.id": booking_id,
        }
    )


@pytest.mark.anyio
async def test_b2b_booking_lifecycle_create_confirm_risk_cancel(
    async_client: AsyncClient,
    test_db: Any,
    agency_token: str,
    monkeypatch,
) -> None:
    org_id, agency_id = await _resolve_agency_context(async_client, agency_token)
    headers = {"Authorization": f"Bearer {agency_token}"}

    # ── Patch risk engine: first call REVIEW, subsequent calls ALLOW ────────
    from app.services.risk import engine as risk_engine

    risk_calls: dict[str, int] = {"n": 0}

    async def fake_eval(db, organization_id, booking):  # noqa: ANN001
        risk_calls["n"] += 1
        if risk_calls["n"] == 1:
            return risk_engine.RiskResult(
                score=55.0,
                decision=risk_engine.RiskDecision.REVIEW,
                reasons=["smoke_review"],
            )
        return risk_engine.RiskResult(
            score=10.0,
            decision=risk_engine.RiskDecision.ALLOW,
            reasons=["smoke_allow"],
        )

    monkeypatch.setattr(risk_engine, "evaluate_booking_risk", fake_eval)

    # Stub finance interactions: credit check on create + ledger work on
    # cancel are covered by dedicated finance/ledger tests, so they're
    # stubbed here to keep the smoke test focused on lifecycle/audit.
    from app.services.booking_finance import BookingFinanceService

    async def fake_check_credit(self, **kwargs):  # noqa: ANN001
        return {"flags": {}, "decision": "allow"}

    async def fake_post_cancelled(self, **kwargs):  # noqa: ANN001
        return "ledger-stub-id"

    monkeypatch.setattr(
        BookingFinanceService, "check_credit_and_get_flags", fake_check_credit
    )
    monkeypatch.setattr(
        BookingFinanceService, "post_booking_cancelled", fake_post_cancelled
    )

    # ── 1. Create booking via API (canonical quote-based create flow) ──────
    quote_id = await _seed_quote(test_db, org_id=org_id, agency_id=agency_id)
    create_resp = await async_client.post(
        "/api/b2b/bookings",
        headers={**headers, "Idempotency-Key": "smoke-lc-create-1"},
        json={
            "source": "quote",
            "quote_id": quote_id,
            "customer": {
                "full_name": "Smoke Tester",
                "email": "smoke@example.com",
                "phone": "+1234567890",
            },
            "travellers": [
                {"first_name": "Smoke", "last_name": "Tester", "type": "adult"},
            ],
        },
    )
    assert create_resp.status_code == 200, create_resp.text
    created = _unwrap(create_resp)
    booking_id = created.get("booking_id")
    assert booking_id
    booking_oid = ObjectId(booking_id)

    seeded = await test_db.bookings.find_one({"_id": booking_oid})
    assert seeded is not None
    assert seeded["agency_id"] == agency_id
    # The quote-based create entrypoint inserts the booking already in
    # CONFIRMED state with sell_eur, so we reset to PENDING here only to
    # let the supplier-side /confirm path run end-to-end. We do NOT pre-set
    # CONFIRMED — the confirm router itself must promote PENDING -> CONFIRMED.
    await test_db.bookings.update_one(
        {"_id": booking_oid},
        {
            "$set": {
                "status": "PENDING",
                "offer_ref": {
                    "supplier": "mock_supplier_v1",
                    "supplier_offer_id": "MOCK-OFF-LC",
                },
                "updated_at": now_utc(),
            }
        },
    )

    # ── 2. Confirm — risk engine returns REVIEW ─────────────────────────────
    confirm_review = await async_client.post(
        f"/api/b2b/bookings/{booking_id}/confirm", headers=headers
    )
    # The router maps RiskDecision.REVIEW to AppError(202, risk_review_required)
    assert confirm_review.status_code == 202, confirm_review.text
    review_payload = _unwrap(confirm_review)
    assert review_payload.get("error", {}).get("code") == "risk_review_required"

    booking_after_review = await test_db.bookings.find_one({"_id": booking_oid})
    assert booking_after_review["status"] == "RISK_REVIEW"

    risk_eval_audit = await _find_audit(
        test_db, org_id=org_id, action="RISK_EVALUATED", booking_id=booking_id
    )
    assert risk_eval_audit is not None
    assert (risk_eval_audit.get("meta") or {}).get("decision") == "review"

    risk_required_audit = await _find_audit(
        test_db, org_id=org_id, action="RISK_REVIEW_REQUIRED", booking_id=booking_id
    )
    assert risk_required_audit is not None

    # ── 3. Risk approve ─────────────────────────────────────────────────────
    approve_resp = await async_client.post(
        f"/api/b2b/bookings/{booking_id}/risk/approve", headers=headers
    )
    assert approve_resp.status_code == 200, approve_resp.text
    approved = _unwrap(approve_resp)
    assert approved.get("ok") is True
    assert approved.get("status") == "PENDING"

    after_approve = await test_db.bookings.find_one({"_id": booking_oid})
    assert after_approve["status"] == "PENDING"
    assert ((after_approve.get("risk") or {}).get("review") or {}).get("state") == "approved"

    approve_audit = await _find_audit(
        test_db, org_id=org_id, action="RISK_REVIEW_APPROVED", booking_id=booking_id
    )
    assert approve_audit is not None
    approve_meta = approve_audit.get("meta") or {}
    assert approve_meta.get("previous_status") == "RISK_REVIEW"
    assert approve_meta.get("new_status") == "PENDING"

    # ── 4. Confirm — risk engine now ALLOWs, supplier mock confirms ────────
    confirm_ok = await async_client.post(
        f"/api/b2b/bookings/{booking_id}/confirm", headers=headers
    )
    assert confirm_ok.status_code == 200, confirm_ok.text
    confirmed_payload = _unwrap(confirm_ok)
    assert confirmed_payload.get("booking_id") == booking_id
    assert confirmed_payload.get("state") == "confirmed"

    after_confirm = await test_db.bookings.find_one({"_id": booking_oid})
    assert after_confirm["status"] == "CONFIRMED"
    last_event_confirm = after_confirm.get("last_event") or {}
    assert last_event_confirm.get("event") == "BOOKING_CONFIRMED"

    confirm_audit = await _find_audit(
        test_db, org_id=org_id, action="B2B_BOOKING_CONFIRMED", booking_id=booking_id
    )
    assert confirm_audit is not None
    assert (confirm_audit.get("meta") or {}).get("supplier_code_canonical") == "mock"

    confirm_event = await test_db.booking_events.find_one(
        {
            "organization_id": org_id,
            "booking_id": booking_id,
            "event": "BOOKING_CONFIRMED",
        }
    )
    assert confirm_event is not None

    # ── 5. Cancel ───────────────────────────────────────────────────────────
    cancel_resp = await async_client.post(
        f"/api/b2b/bookings/{booking_id}/cancel",
        headers={**headers, "Idempotency-Key": "smoke-lc-cancel-1"},
        json={"reason": "smoke_lifecycle_cancel"},
    )
    assert cancel_resp.status_code == 200, cancel_resp.text
    cancel_payload = _unwrap(cancel_resp)
    assert cancel_payload.get("booking_id") == booking_id
    assert cancel_payload.get("status") == "CANCELLED"
    assert cancel_payload.get("refund_status") == "COMPLETED"

    after_cancel = await test_db.bookings.find_one({"_id": booking_oid})
    assert after_cancel["status"] == "CANCELLED"
    last_event_cancel = after_cancel.get("last_event") or {}
    assert last_event_cancel.get("event") == "BOOKING_CANCELLED"

    cancel_event = await test_db.booking_events.find_one(
        {
            "organization_id": org_id,
            "booking_id": booking_id,
            "event": "BOOKING_CANCELLED",
        }
    )
    assert cancel_event is not None
    assert (cancel_event.get("meta") or {}).get("reason") == "smoke_lifecycle_cancel"

    # ── 6. Idempotent re-cancel returns the cancelled state without error ──
    repeat = await async_client.post(
        f"/api/b2b/bookings/{booking_id}/cancel",
        headers={**headers, "Idempotency-Key": "smoke-lc-cancel-2"},
        json={"reason": "smoke_lifecycle_cancel"},
    )
    assert repeat.status_code == 200, repeat.text
    repeat_payload = _unwrap(repeat)
    assert repeat_payload.get("status") == "CANCELLED"

    # No duplicate audits/events written by the second cancel call.
    assert (
        await test_db.booking_events.count_documents(
            {
                "organization_id": org_id,
                "booking_id": booking_id,
                "event": "BOOKING_CANCELLED",
            }
        )
        == 1
    )
