import asyncio
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from bson import ObjectId

from app.db import get_db
from app.services.ops_cases import create_case


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _find_demo_agency_user(db) -> Optional[Dict[str, Any]]:
    """Find demo agency user (agency1@demo.test)."""

    return await db.users.find_one({"email": "agency1@demo.test"})


async def _seed_booking(db, org_id: str, agency_id: str) -> str:
    """Insert a minimal B2B booking document for demo/testing.

    Shape is aligned with b2b booking detail endpoint expectations.
    """

    now = _now()
    check_in = (now + timedelta(days=7)).date().isoformat()
    check_out = (now + timedelta(days=10)).date().isoformat()

    booking_doc: Dict[str, Any] = {
        "organization_id": str(org_id),
        "agency_id": str(agency_id),
        "created_at": now,
        "status": "CONFIRMED",
        "payment_status": "unpaid",
        "currency": "TRY",
        "booking_code": f"DEMO-{now.strftime('%Y%m%d%H%M%S')}",
        "customer": {
            "name": "Demo Misafir",
            "email": "guest@demo.test",
            "phone": "+90 500 000 00 00",
        },
        "amounts": {
            "sell": 12500.0,
        },
        "items": [
            {
                "type": "hotel",
                "product_id": "demo-hotel-1",
                "product_name": "Demo Otel (B2B Seed)",
                "check_in": check_in,
                "check_out": check_out,
            }
        ],
        "quote_id": "seed-demo-quote-1",
    }

    res = await db.bookings.insert_one(booking_doc)
    return str(res.inserted_id)


async def _seed_initial_case(db, org_id: str, agency_id: str, booking_id: str, actor: Dict[str, Any]) -> Dict[str, Any]:
    """Attach a single initial case to the booking (source=ops_panel)."""

    return await create_case(
        db,
        organization_id=str(org_id),
        booking_id=str(booking_id),
        type="info",
        source="ops_panel",
        status="open",
        waiting_on=None,
        note="Seed case: demo amaçlı oluşturuldu.",
        booking_code=f"SEED-{booking_id[-6:]}",
        agency_id=str(agency_id),
        created_by=actor,
    )


async def main() -> None:
    # Safety: only allow in explicit dev/preview contexts
    allow = os.getenv("ALLOW_DEMO_SEED", "0") == "1"
    if not allow:
        raise SystemExit(
            "Refusing to run seed. Set ALLOW_DEMO_SEED=1 (dev/preview only).",
        )

    db = await get_db()

    user = await _find_demo_agency_user(db)
    if not user:
        raise SystemExit("Demo user agency1@demo.test not found in users collection.")

    org_id = user.get("organization_id")
    agency_id = user.get("agency_id")
    if not org_id or not agency_id:
        raise SystemExit("Demo user missing organization_id or agency_id.")

    actor = {
        "user_id": str(user.get("id") or user.get("_id") or ""),
        "email": user.get("email"),
        "roles": user.get("roles") or [],
    }

    booking_id = await _seed_booking(db, str(org_id), str(agency_id))
    seed_case = await _seed_initial_case(db, str(org_id), str(agency_id), booking_id, actor)

    print("✅ Seed OK")
    print(f"booking_id={booking_id}")
    print(f"seed_case_id={seed_case.get('case_id')}")
    print("Use this booking_id in /api/b2b/bookings/{booking_id} and /cases endpoints.")


if __name__ == "__main__":
    asyncio.run(main())
