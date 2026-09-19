"""Agency requests must target the routes exposed by the PMS marketplace."""
import asyncio

import httpx
import pytest

from app.services.syroce import agent


@pytest.mark.parametrize("base", [
    "https://pms.example",
    "https://pms.example/",
    "https://pms.example/api/marketplace/v1",
    "https://pms.example/api/marketplace/v1/",
])
@pytest.mark.parametrize("operation,method,path", [
    ("hotels", "GET", "/hotels"),
    ("search", "POST", "/search"),
    ("rates", "GET", "/hotels/hotel-1/rates"),
    ("create", "POST", "/reservations"),
    ("get", "GET", "/reservations/res-1"),
    ("cancel", "DELETE", "/reservations/res-1"),
    ("reconcile", "GET", "/reconciliation/agency"),
    ("propose", "POST", "/contracts/propose"),
    ("contracts", "GET", "/contracts/mine"),
    ("contract", "GET", "/contracts/contract-1"),
    ("withdraw", "DELETE", "/contracts/contract-1"),
])
def test_marketplace_wire_routes(monkeypatch, base, operation, method, path):
    monkeypatch.setenv("SYROCE_BASE_URL", base)
    requests = []

    def handler(request):
        requests.append(request)
        if operation == "create":
            return httpx.Response(200, json={"ok": True, "reservation": {
                "id": "res-1", "status": "confirmed", "tenant_id": "hotel-1",
                "external_reference": None,
            }})
        return httpx.Response(200, json={"ok": True})

    real_client = httpx.AsyncClient
    monkeypatch.setattr(agent.httpx, "AsyncClient", lambda **kwargs: real_client(
        transport=httpx.MockTransport(handler), **kwargs
    ))
    client = agent.SyroceAgentClient(organization_id="org-1", api_key="test-key")

    async def invoke():
        calls = {
            "hotels": lambda: client.list_hotels(city="Antalya"),
            "search": lambda: client.search_availability({"tenant_id": "hotel-1"}),
            "rates": lambda: client.get_rates(tenant_id="hotel-1", room_type="Standard",
                check_in="2026-09-19", check_out="2026-09-21"),
            "create": lambda: client.create_reservation({"tenant_id": "hotel-1"}),
            "get": lambda: client.get_reservation("res-1"),
            "cancel": lambda: client.cancel_reservation("res-1"),
            "reconcile": lambda: client.reconciliation(period_start="2026-09-01", period_end="2026-09-30"),
            "propose": lambda: client.propose_contract({"tenant_id": "hotel-1"}),
            "contracts": lambda: client.list_contracts(status="approved"),
            "contract": lambda: client.get_contract("contract-1"),
            "withdraw": lambda: client.withdraw_contract("contract-1"),
        }
        assert (await calls[operation]())["ok"] is True

    asyncio.run(invoke())
    assert len(requests) == 1
    request = requests[0]
    assert request.method == method
    assert request.url.path == "/api/marketplace/v1" + path
    assert request.headers["X-API-Key"] == "test-key"
    if operation == "rates":
        assert dict(request.url.params) == {
            "room_type": "Standard", "start_date": "2026-09-19", "end_date": "2026-09-21"
        }
