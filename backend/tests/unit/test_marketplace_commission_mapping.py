"""Map the PMS marketplace commission fields into the local reservation."""
import ast
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.mark.parametrize("reservation,rate,amount", [
    ({"commission_pct": 10, "commission_amount": 300}, 10, 300),
    ({"commission_pct": 0, "commission_amount": 0}, 0, 0),
    ({"agency_commission_rate": 12, "agency_commission_amount": 360}, 12, 360),
    ({"commission_pct": 0, "commission_amount": 0,
      "agency_commission_rate": 12, "agency_commission_amount": 360}, 0, 0),
])
def test_pms_commission_response_is_preserved(reservation, rate, amount):
    source = Path(__file__).resolve().parents[2] / "app/modules/inventory/routers/syroce_marketplace.py"
    fn = next(n for n in ast.parse(source.read_text()).body
              if isinstance(n, ast.AsyncFunctionDef) and n.name == "create_reservation")
    update = next(n for n in fn.body if isinstance(n, ast.Assign)
                  and any(isinstance(t, ast.Name) and t.id == "update" for t in n.targets))
    scope = {"reservation": reservation, "result": {"reservation": reservation},
             "body": SimpleNamespace(tenant_id="hotel-1", hotel_name="Hotel", room_type="Standard"),
             "_now": lambda: "2026-09-19"}
    exec(compile(ast.Module(body=[update], type_ignores=[]), str(source), "exec"), scope)
    assert scope["update"]["commission_rate"] == rate
    assert scope["update"]["commission_amount"] == amount
