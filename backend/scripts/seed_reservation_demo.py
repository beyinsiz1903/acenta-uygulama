import asyncio
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.db import get_db
from app.services.ops_cases import create_case
from app.utils import generate_pnr, generate_voucher_no


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _find_admin_user(db) -> Optional[Dict[str, Any]]:
    return await db.users.find_one({"email": "admin@acenta.test"})


async def _seed_reservation(db, org_id: str) -> str:
    now = _now()

    res_doc: Dict[str, Any] = {
        "organization_id": str(org_id),
        "pnr": generate_pnr(),
        "voucher_no": generate_voucher_no(),
        "product_id": None,
        "customer_id": None,
        "start_date": now.date().isoformat(),
        "end_date": None,
        "dates": [now.date().isoformat()],
        "pax": 2,
        "status": "confirmed",
        "currency": "TRY",
        "total_price": 1000.0,
        "discount_amount": 0.0,
        "commission_amount": 0.0,
        "paid_amount": 0.0,
        "channel": "direct",
        "agency_id": None,
        "created_at": now,
        "updated_at": now,
        "created_by": "seed_script",
        "updated_by": "seed_script",
    }

    ins = await db.reservations.insert_one(res_doc)
    return str(ins.inserted_id)


async def _seed_case(db, org_id: str, reservation_id: str) -> Dict[str, Any]:
    actor = {
        "user_id": None,
        "email": "admin@acenta.test",
        "roles": ["admin"],
    }
    return await create_case(
        db,
        organization_id=str(org_id),
        booking_id=reservation_id,
        type="info",
        source="ops_panel",
        status="open",
        waiting_on=None,
        note="Seed reservation case for demo.",
        booking_code=f"RES-{reservation_id[-6:]}",
        agency_id=None,
        created_by=actor,
    )


async def main() -> None:
    allow = os.getenv("ALLOW_DEMO_SEED", "0") == "1"
    if not allow:
        raise SystemExit("Set ALLOW_DEMO_SEED=1 to run this seed (dev/preview only).")

    db = await get_db()

    user = await _find_admin_user(db)
    if not user:
        raise SystemExit("admin@acenta.test user not found")

    org_id = user.get("organization_id")
    if not org_id:
        raise SystemExit("Admin user missing organization_id")

    res_id = await _seed_reservation(db, str(org_id))
    case_doc = await _seed_case(db, str(org_id), res_id)

    print("✅ Seed reservation + case OK")
    print(f"reservation_id={res_id}")
    print(f"case_id={case_doc.get('case_id')}")


if __name__ == "__main__":
    asyncio.run(main())
