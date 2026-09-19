"""A PNR may replay a booking, but must not silently identify a different one."""
import ast
import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
import uuid

import pytest
from pymongo.errors import DuplicateKeyError


class AppError(Exception):
    def __init__(self, status, code, message, details=None):
        self.status = status
        self.code = code


@pytest.mark.parametrize("status", ["confirmed", "completed"])
@pytest.mark.parametrize("changed", [None, "tenant_id", "room_type", "check_in", "check_out",
                                     "guest_name", "guest_email", "guest_phone", "adults",
                                     "children", "special_requests"])
def test_same_pnr_requires_same_booking(status, changed):
    body = SimpleNamespace(tenant_id="hotel-1", hotel_name="Hotel", room_type="Standard",
        check_in="2026-09-19", check_out="2026-09-21", external_reference=" REF1 ",
        guest_name="Test Guest", guest_email="test@example.test", guest_phone="12345",
        adults=2, children=0, special_requests=None)
    existing = dict(vars(body), status=status, id="local-1", organization_id="org-1",
                    syroce_tenant_id=body.tenant_id, external_reference="REF1", special_requests="")
    if changed:
        replacements = {"check_in": "2026-09-20", "check_out": "2026-09-22",
                        "adults": 3, "children": 1}
        setattr(body, changed, replacements.get(changed, "different"))
    collection = SimpleNamespace(insert_one=AsyncMock(side_effect=DuplicateKeyError("duplicate")),
        find_one=AsyncMock(return_value=existing), update_one=AsyncMock(), delete_one=AsyncMock())
    client = SimpleNamespace(create_reservation=AsyncMock())
    source = Path(__file__).resolve().parents[2] / "app/modules/inventory/routers/syroce_marketplace.py"
    fn = next(n for n in ast.parse(source.read_text()).body
              if isinstance(n, ast.AsyncFunctionDef) and n.name == "create_reservation")
    fn.decorator_list = []
    scope = {"UserDep": None, "uuid": uuid, "COLLECTION": "reservations",
        "AppError": AppError, "DuplicateKeyError": DuplicateKeyError,
        "_validate_date": lambda *a: None, "_ensure_indexes": AsyncMock(),
        "_org_id": lambda user: "org-1", "_now": lambda: "now", "_serialize": lambda doc: doc,
        "get_db": AsyncMock(return_value={"reservations": collection}),
        "_client": AsyncMock(return_value=client)}
    future = ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0)
    module = ast.fix_missing_locations(ast.Module(body=[future, fn], type_ignores=[]))
    exec(compile(module, str(source), "exec"), scope)

    async def scenario():
        if changed:
            with pytest.raises(AppError) as caught:
                await scope["create_reservation"](body, {"id": "user-1"})
            assert caught.value.status == 409
            assert caught.value.code == "external_reference_conflict"
        else:
            result = await scope["create_reservation"](body, {"id": "user-1"})
            assert result["idempotent"] is True
            assert result["reservation"]["id"] == "local-1"
        collection.find_one.assert_awaited_once_with({"organization_id": "org-1", "external_reference": "REF1"})
        client.create_reservation.assert_not_awaited()
        collection.update_one.assert_not_awaited()
        collection.delete_one.assert_not_awaited()

    asyncio.run(scenario())
