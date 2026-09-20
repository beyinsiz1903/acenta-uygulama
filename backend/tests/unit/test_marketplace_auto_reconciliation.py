import asyncio
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from app.services.syroce import agent, reconciliation as recon


def fixtures():
    local = dict(
        id="local-1",
        organization_id="org-1",
        external_reference="REF1",
        syroce_tenant_id="hotel-1",
        check_in="2026-09-20",
        check_out="2026-09-22",
        guest_name="Guest",
        guest_email="g@example.test",
        guest_phone="123",
        room_type="Standard",
        adults=2,
        children=0,
    )
    summary = dict(
        id="pms-1",
        agency_id="agency-1",
        tenant_id="hotel-1",
        external_reference="REF1",
        check_in=local["check_in"],
        check_out=local["check_out"],
        guest_name="Guest",
        status="confirmed",
        total_amount=1000,
        commission_pct=0,
        commission_amount=0,
        net_to_hotel=1000,
    )
    booking = dict(
        local,
        id="pms-1",
        marketplace_agency_id="agency-1",
        status="confirmed",
        check_in="2026-09-20T14:00:00",
        check_out="2026-09-22T11:00:00",
        total_amount=1000,
        agency_commission_rate=0,
        agency_commission_amount=0,
        net_to_hotel=1000,
    )
    client = SimpleNamespace(
        syroce_agency_id="agency-1",
        list_reservations_for_reconciliation=AsyncMock(
            return_value={"reservations": [summary], "total": 1}
        ),
        get_reservation=AsyncMock(
            return_value={"summary": deepcopy(summary), "booking": booking}
        ),
    )
    return local, client


@pytest.mark.parametrize("status", ["confirmed", "cancelled"])
def test_verified_booking_preserves_zero_commission(status):
    local, client = fixtures()
    detail = client.get_reservation.return_value
    detail["summary"]["status"] = detail["booking"]["status"] = status
    result = asyncio.run(recon.verified_update(client, local))
    assert result["status"] == status
    assert result["commission_rate"] == result["commission_amount"] == 0
    assert result["syroce_reservation_id"] == "pms-1"
    assert result["reconciliation_required"] is False


@pytest.mark.parametrize(
    "case",
    [
        "empty",
        "duplicate",
        "cap",
        "invalid_list",
        "total",
        "foreign_agency",
        "foreign_hotel",
        "wrong_pnr",
        "wrong_date",
        "missing_agency",
        "missing_booking",
        "wrong_id",
        "wrong_guest",
        "wrong_room",
        "wrong_occupancy",
        "wrong_booking_agency",
        "wrong_booking_pnr",
        "wrong_booking_date",
        "unknown_status",
        "inconsistent_status",
        "bad_amount",
        "amount_mismatch",
        "special_requests",
    ],
)
def test_ambiguous_data_stays_pending(case):
    local, client = fixtures()
    listing = client.list_reservations_for_reconciliation.return_value
    detail = client.get_reservation.return_value
    if case == "empty":
        listing.update(reservations=[], total=0)
    elif case == "duplicate":
        listing.update(reservations=listing["reservations"] * 2, total=2)
    elif case == "cap":
        listing.update(reservations=listing["reservations"] * 500, total=500)
    elif case == "invalid_list":
        listing["reservations"] = {}
    elif case == "total":
        listing["total"] = 5
    elif case == "missing_agency":
        client.syroce_agency_id = None
    elif case == "missing_booking":
        detail["booking"] = None
    elif case in {"foreign_agency", "foreign_hotel", "wrong_pnr", "wrong_date"}:
        field = {
            "foreign_agency": "agency_id",
            "foreign_hotel": "tenant_id",
            "wrong_pnr": "external_reference",
            "wrong_date": "check_in",
        }[case]
        listing["reservations"][0][field] = "other"
    else:
        field, value = {
            "wrong_id": ("id", "other"),
            "wrong_guest": ("guest_name", "other"),
            "wrong_room": ("room_type", "other"),
            "wrong_occupancy": ("adults", 3),
            "wrong_booking_agency": ("marketplace_agency_id", "other"),
            "wrong_booking_pnr": ("external_reference", "other"),
            "wrong_booking_date": ("check_in", "2026-09-21T14:00:00"),
            "unknown_status": ("status", "checked_in"),
            "inconsistent_status": ("status", "cancelled"),
            "bad_amount": ("total_amount", float("nan")),
            "amount_mismatch": ("total_amount", 900),
            "special_requests": ("special_requests", "different"),
        }[case]
        detail["booking"][field] = value
    assert asyncio.run(recon.verified_update(client, local)) is None


@pytest.mark.parametrize("failure", [False, True])
def test_worker_claim_and_finalize_are_scoped_and_conditional(failure):
    local, client = fixtures()
    if failure:
        client.get_reservation.side_effect = TimeoutError()
    collection = SimpleNamespace(
        find_one_and_update=AsyncMock(return_value=local), update_one=AsyncMock()
    )
    factory = AsyncMock(return_value=client)
    assert asyncio.run(
        recon.reconcile_one({recon.COLLECTION: collection}, client_factory=factory)
    )
    factory.assert_awaited_once_with("org-1")
    claim, claim_update = collection.find_one_and_update.await_args.args
    assert claim["status"] == "pending"
    assert claim["channel"] == "syroce_marketplace"
    assert len(claim["$and"]) == 2
    query, update = collection.update_one.await_args.args
    assert query["organization_id"] == "org-1"
    assert query["status"] == "pending"
    assert query["reconciliation_token"] == claim_update["$set"]["reconciliation_token"]
    assert "$gt" in query["reconciliation_lease_until"]
    assert update["$inc"]["reconciliation_attempts"] == 1
    assert update["$set"]["reconciliation_outcome"] == (
        "lookup_failed" if failure else "verified"
    )
    if failure:
        assert "status" not in update["$set"]
        assert update["$set"]["reconciliation_required"] is True


def test_no_claim_does_not_load_credentials():
    collection = SimpleNamespace(find_one_and_update=AsyncMock(return_value=None))
    factory = AsyncMock()
    assert (
        asyncio.run(
            recon.reconcile_one({recon.COLLECTION: collection}, client_factory=factory)
        )
        is False
    )
    factory.assert_not_awaited()


def test_lookup_is_get_only_and_scoped(monkeypatch):
    monkeypatch.setenv("SYROCE_BASE_URL", "https://pms.example")
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, json={"reservations": [], "total": 0})

    original = httpx.AsyncClient
    monkeypatch.setattr(
        agent.httpx,
        "AsyncClient",
        lambda **kw: original(transport=httpx.MockTransport(handler), **kw),
    )
    client = agent.SyroceAgentClient(organization_id="org-1", api_key="test-key")
    asyncio.run(
        client.list_reservations_for_reconciliation(
            tenant_id="hotel-1", check_in="2026-09-20"
        )
    )
    assert len(calls) == 1 and calls[0].method == "GET"
    assert calls[0].url.path == "/api/marketplace/v1/reservations"
    assert dict(calls[0].url.params) == dict(
        tenant_id="hotel-1",
        check_in_from="2026-09-20",
        check_in_to="2026-09-20",
        limit="500",
    )
    assert calls[0].headers["X-API-Key"] == "test-key"


def test_worker_runs_automatically_and_propagates_shutdown(monkeypatch):
    from app import db as db_module

    collection = SimpleNamespace(create_index=AsyncMock())
    monkeypatch.setenv("SYROCE_BASE_URL", "https://pms.example")
    monkeypatch.setattr(
        db_module, "get_db", AsyncMock(return_value={recon.COLLECTION: collection})
    )
    cycle = AsyncMock(return_value=False)
    monkeypatch.setattr(recon, "reconcile_one", cycle)
    monkeypatch.setattr(
        recon.asyncio, "sleep", AsyncMock(side_effect=asyncio.CancelledError())
    )
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(recon.run())
    cycle.assert_awaited_once()
    collection.create_index.assert_awaited_once()
