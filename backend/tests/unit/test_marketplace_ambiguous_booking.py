"""Exercise actual booking handler control flow with isolated DB/client doubles."""
import ast
import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
import uuid

import httpx
import pytest
from pymongo.errors import DuplicateKeyError

from app.services.syroce.agent import SyroceAgentClient
from app.services.syroce.errors import SyroceError
from app.services.syroce import agent


@pytest.mark.parametrize("status,content", [(200, b"<html>error</html>"), (204, b""), (302, b"{}")])
def test_invalid_http_confirmation_is_not_success(monkeypatch, status, content):
    monkeypatch.setenv("SYROCE_BASE_URL", "https://pms.example")
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(status, content=content)

    real_client = httpx.AsyncClient
    monkeypatch.setattr(agent.httpx, "AsyncClient", lambda **kwargs: real_client(
        transport=httpx.MockTransport(handler), **kwargs))
    client = SyroceAgentClient(organization_id="org-1", api_key="test")
    with pytest.raises(SyroceError) as caught:
        asyncio.run(client.create_reservation({"tenant_id": "hotel-1", "external_reference": "REF1"}))
    assert caught.value.http_status == 502
    assert len(calls) == 1


@pytest.mark.parametrize("response", [
    {}, {"ok": True}, {"ok": True, "reservation": []},
    {"ok": True, "reservation": {"id": "R1", "status": "confirmed", "tenant_id": "other"}},
    {"ok": True, "reservation": {"id": "R1", "status": "pending", "tenant_id": "hotel-1"}},
])
def test_missing_or_mismatched_confirmation_is_not_success(response):
    client = SyroceAgentClient(organization_id="org-1", api_key="test")
    client._request = AsyncMock(return_value=response)
    with pytest.raises(SyroceError) as caught:
        asyncio.run(client.create_reservation({"tenant_id": "hotel-1", "external_reference": "REF1"}))
    assert caught.value.http_status == 502


class AppError(Exception):
    def __init__(self, status, code, message, details=None):
        self.code = code
        self.details = details


class Collection:
    def __init__(self):
        self.doc = None
        self.deletes = 0

    async def insert_one(self, doc):
        if self.doc:
            raise DuplicateKeyError("duplicate reference")
        self.doc = dict(doc)

    async def find_one(self, query):
        return dict(self.doc) if self.doc else None

    async def update_one(self, query, update):
        assert query["organization_id"] == "org-1"
        self.doc.update(update["$set"])

    async def delete_one(self, query):
        self.deletes += 1
        self.doc = None


@pytest.mark.parametrize("status,ambiguous", [(502, True), (503, True), (504, True), (408, True), (403, False), (422, False)])
def test_handler_preserves_ambiguous_reference_and_blocks_resend(status, ambiguous):
    source = Path(__file__).resolve().parents[2] / "app/modules/inventory/routers/syroce_marketplace.py"
    fn = next(n for n in ast.parse(source.read_text()).body
              if isinstance(n, ast.AsyncFunctionDef) and n.name == "create_reservation")
    fn.decorator_list = []
    collection = Collection()
    client = SimpleNamespace(create_reservation=AsyncMock(side_effect=SyroceError(status, "failed")))
    scope = {"UserDep": None, "uuid": uuid, "COLLECTION": "reservations",
             "AppError": AppError, "SyroceError": SyroceError, "DuplicateKeyError": DuplicateKeyError,
             "_validate_date": lambda *a: None, "_ensure_indexes": AsyncMock(),
             "_org_id": lambda user: "org-1", "_now": lambda: "now",
             "get_db": AsyncMock(return_value={"reservations": collection}),
             "_client": AsyncMock(return_value=client), "_to_app_error": lambda exc: exc}
    future = ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0)
    module = ast.fix_missing_locations(ast.Module(body=[future, fn], type_ignores=[]))
    exec(compile(module, str(source), "exec"), scope)
    body = SimpleNamespace(check_in="2026-09-19", check_out="2026-09-21", external_reference="REF1",
        tenant_id="hotel-1", hotel_name="Hotel", room_type="Standard", guest_name="Test Guest",
        guest_email="test@example.test", guest_phone="12345", adults=2, children=0, special_requests=None)

    async def scenario():
        with pytest.raises((AppError, SyroceError)) as caught:
            await scope["create_reservation"](body, {"id": "user-1"})
        if ambiguous:
            assert caught.value.code == "reservation_outcome_unknown"
            assert collection.doc["status"] == "pending"
            assert collection.doc["reconciliation_required"] is True
            assert collection.deletes == 0
            with pytest.raises(AppError) as retry:
                await scope["create_reservation"](body, {"id": "user-1"})
            assert retry.value.code == "duplicate_external_reference"
            assert client.create_reservation.await_count == 1
        else:
            assert collection.doc is None
            assert collection.deletes == 1

    asyncio.run(scenario())
