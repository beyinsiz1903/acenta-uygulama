"""Exercise the real cancellation handler's early uncertainty guard."""

import ast
import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest


@pytest.mark.parametrize(
    "status,required", [("pending", False), ("pending", True), ("confirmed", True)]
)
def test_pending_cancellation_never_reaches_pms(status, required):
    class AppError(Exception):
        def __init__(self, status, code, message):
            self.status = status
            self.code = code

    local = {
        "status": status,
        "reconciliation_required": required,
        "syroce_reservation_id": "pms-1",
    }
    collection = SimpleNamespace(
        find_one=AsyncMock(return_value=local), update_one=AsyncMock()
    )
    client_factory = AsyncMock()
    source = (
        Path(__file__).resolve().parents[2]
        / "app/modules/inventory/routers/syroce_marketplace.py"
    )
    function = next(
        node
        for node in ast.parse(source.read_text()).body
        if isinstance(node, ast.AsyncFunctionDef)
        and node.name == "cancel_local_reservation"
    )
    function.decorator_list = []
    scope = {
        "AppError": AppError,
        "UserDep": None,
        "COLLECTION": "reservations",
        "get_db": AsyncMock(return_value={"reservations": collection}),
        "_org_id": lambda user: "org-1",
        "_client": client_factory,
    }
    future = ast.ImportFrom(
        module="__future__", names=[ast.alias(name="annotations")], level=0
    )
    module = ast.fix_missing_locations(
        ast.Module(body=[future, function], type_ignores=[])
    )
    exec(compile(module, str(source), "exec"), scope)
    with pytest.raises(AppError) as caught:
        asyncio.run(scope["cancel_local_reservation"]("local-1", user={"id": "user-1"}))
    assert caught.value.status == 409
    assert caught.value.code == "reconciliation_pending"
    collection.find_one.assert_awaited_once_with(
        {"organization_id": "org-1", "id": "local-1"}
    )
    client_factory.assert_not_awaited()
    collection.update_one.assert_not_awaited()
