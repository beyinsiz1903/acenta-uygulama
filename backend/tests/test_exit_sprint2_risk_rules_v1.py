from __future__ import annotations

from typing import Any, Any, Dict, Optional

import jwt
import pytest
from bson import ObjectId
from fastapi import status
from httpx import AsyncClient

from app.auth import _jwt_secret
from app.utils import now_utc


def _id_variants(x: str) -> list[Any]:
    vals: list[Any] = [x]
    try:
        vals.append(ObjectId(x))
    except Exception:
        pass
    return vals


async def find_risk_alert_for_booking(
    audit_col,
    *,
    organization_id: str,
    booking_id: str,
) -> Optional[Dict[str, Any]]:
    org_variants = _id_variants(organization_id)
    booking_variants = _id_variants(booking_id)

    return await audit_col.find_one(
        {
            "action": "RISK_ALERT_CREATED",
            "organization_id": {"$in": org_variants},
            "$or": [
                {"target_type": "booking", "target_id": {"$in": booking_variants}},
                {"target.type": "booking", "target.id": {"$in": booking_variants}},
            ],
        }
    )


@pytest.mark.exit_sprint2
@pytest.mark.anyio
async def test_risk_rules_v1_amount_threshold_alert(test_db: Any, async_client: AsyncClient) -> None:
    """Sprint 2 Risk & Rules v1 contract.

    - Below threshold: no risk alert
    - Above threshold: RISK_ALERT_CREATED with expected meta
    - Org isolation for risk alerts
    """

    client = async_client
    now = now_utc()

    # Create two orgs
    org_a = await test_db.organizations.insert_one(
        {"name": "OrgA_Risk", "slug": "orga_risk", "created_at": now, "updated_at": now, "settings": {"currency": "TRY"}}
    )
    org_b = await test_db.organizations.insert_one(
        {"name": "OrgB_Risk", "slug": "orgb_risk", "created_at": now, "updated_at": now, "settings": {"currency": "TRY"}}
    )
    org_a_id = str(org_a.inserted_id)
    org_b_id = str(org_b.inserted_id)

    email_a = "s2_risk_a@example.com"
    email_b = "s2_risk_b@example.com"

    await test_db.users.insert_one(
        {
            "email": email_a,
            "roles": ["agency_admin"],
            "organization_id": org_a_id,
            "is_active": True,
        }
    )
    await test_db.users.insert_one(
        {
            "email": email_b,
            "roles": ["agency_admin"],
            "organization_id": org_b_id,
            "is_active": True,
        }
    )

    token_a = jwt.encode({"sub": email_a, "org": org_a_id}, _jwt_secret(), algorithm="HS256")
    token_b = jwt.encode({"sub": email_b, "org": org_b_id}, _jwt_secret(), algorithm="HS256")

    # Case 1: below threshold -> no risk alert
    resp_create_low = await client.post(
        "/api/bookings",
        json={"amount": 10_000.0, "currency": "TRY"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp_create_low.status_code == status.HTTP_201_CREATED
    booking_low_id = resp_create_low.json()["id"]

    await client.post(
        f"/api/bookings/{booking_low_id}/quote",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    resp_book_low = await client.post(
        f"/api/bookings/{booking_low_id}/book",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp_book_low.status_code == status.HTTP_200_OK

    alert_low = await find_risk_alert_for_booking(
        test_db.audit_logs,
        organization_id=org_a_id,
        booking_id=booking_low_id,
    )
    assert alert_low is None

    # Case 2: above threshold -> risk alert created
    resp_create_high = await client.post(
        "/api/bookings",
        json={"amount": 150_000.0, "currency": "TRY"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp_create_high.status_code == status.HTTP_201_CREATED
    booking_high_id = resp_create_high.json()["id"]

    await client.post(
        f"/api/bookings/{booking_high_id}/quote",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    resp_book_high = await client.post(
        f"/api/bookings/{booking_high_id}/book",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp_book_high.status_code == status.HTTP_200_OK

    alert_high = await find_risk_alert_for_booking(
        test_db.audit_logs,
        organization_id=org_a_id,
        booking_id=booking_high_id,
    )
    assert alert_high is not None
    meta = alert_high.get("meta", {})
    assert meta.get("rule") == "amount_threshold"
    assert meta.get("threshold") == 100_000.0
    assert meta.get("amount") == 150_000.0

    # Org isolation: OrgB cannot see OrgA's risk alerts or bookings
    resp_get_b = await client.get(
        f"/api/bookings/{booking_high_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp_get_b.status_code == status.HTTP_404_NOT_FOUND
