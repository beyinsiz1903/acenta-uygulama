import asyncio
import os
from datetime import datetime, timezone
from typing import Any, Dict

from app.db import get_db
from app.services.ops_cases import create_case


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def main() -> None:
    allow = os.getenv("ALLOW_DEMO_SEED", "0") == "1"
    if not allow:
        raise SystemExit("Set ALLOW_DEMO_SEED=1 to run this seed (dev/preview only).")

    db = await get_db()

    # Pick first reservation for any organization
    res = await db.reservations.find_one({})
    if not res:
        raise SystemExit("No reservations found to attach a case to.")

    org_id = res.get("organization_id")
    if not org_id:
        raise SystemExit("Seed reservation missing organization_id")

    reservation_id = str(res["_id"])

    actor: Dict[str, Any] = {
        "user_id": None,
        "email": "admin@acenta.test",
        "roles": ["admin"],
    }

    case_doc = await create_case(
        db,
        organization_id=str(org_id),
        booking_id=reservation_id,
        type="info",
        source="ops_panel",
        status="open",
        waiting_on=None,
        note="Debug seed: open case for reservation.",
        booking_code=f"RES-{reservation_id[-6:]}",
        agency_id=None,
        created_by=actor,
    )

    print("✅ Debug seed OK")
    print(f"reservation_id={reservation_id}")
    print(f"case_id={case_doc.get('case_id')}")


if __name__ == "__main__":
    asyncio.run(main())
