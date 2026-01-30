from __future__ import annotations

from typing import Any, Dict, Optional

import jwt
import pytest
from bson import ObjectId
from fastapi import status
from httpx import AsyncClient

from app.auth import _jwt_secret
from app.utils import now_utc
from app.services.org_service import initialize_org_defaults


def _id_variants(x: str) -> list[Any]:
    vals: list[Any] = [x]
    try:
        vals.append(ObjectId(x))
    except Exception:
        pass
    return vals


async def find_audit_for_booking(
    audit_col,
    *,
    organization_id: str,
    action: str,
    booking_id: str,
) -> Optional[Dict[str, Any]]:
    org_variants = _id_variants(organization_id)
    booking_variants = _id_variants(booking_id)


async def _find_state_change(
    audit_col,
    *,
    org_id: str,
    booking_id: str,
    from_state: str,
    to_state: str,
) -> Optional[Dict[str, Any]]:
    org_variants = _id_variants(org_id)
    booking_variants = _id_variants(booking_id)

    return await audit_col.find_one(
        {
            "action": "BOOKING_STATE_CHANGED",
            "organization_id": {"$in": org_variants},
            "$or": [
                {"target_type": "booking", "target_id": {"$in": booking_variants}},
                {"target.type": "booking", "target.id": {"$in": booking_variants}},
            ],
            "meta.from": from_state,
            "meta.to": to_state,
        }
    )



    return await audit_col.find_one(
        {
            "action": action,
            "organization_id": {"$in": org_variants},
            "$or": [
                {"target_type": "booking", "target_id": {"$in": booking_variants}},
                {"target.type": "booking", "target.id": {"$in": booking_variants}},
            ],
        }
    )




@pytest.mark.exit_sprint2
@pytest.mark.anyio
async def test_refund_workflow_v1_contract(test_db: Any, async_client: AsyncClient) -> None:
    """Sprint 2 Refund Workflow v1 contract.

    - refund-request: booked -> refund_in_progress
    - refund-approve: refund_in_progress -> refunded
    - refund-reject: refund_in_progress -> booked
    - BOOKING_STATE_CHANGED audits remain and refund-specific audits are added.
    - Org isolation is preserved.
    """

    client = async_client
    now = now_utc()

    # Create two orgs
    org_a = await test_db.organizations.insert_one(
        {"name": "OrgA_Refund", "slug": "orga_refund", "created_at": now, "updated_at": now, "settings": {"currency": "TRY"}}
    )
    org_b = await test_db.organizations.insert_one(
        {"name": "OrgB_Refund", "slug": "orgb_refund", "created_at": now, "updated_at": now, "settings": {"currency": "TRY"}}
    )
    org_a_id = str(org_a.inserted_id)
    org_b_id = str(org_b.inserted_id)

    email_a = "s2_refund_a@example.com"
    email_b = "s2_refund_b@example.com"

    # Seed org defaults (Standard credit profile, task queues, etc.) so that
    # refund & credit behavior is consistent with real org initialization.
    await initialize_org_defaults(test_db, org_a_id, {"email": email_a})
    await initialize_org_defaults(test_db, org_b_id, {"email": email_b})

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

    # Happy path: refund approve
    resp_create = await client.post(
        "/api/bookings",
        json={"amount": 500.0, "currency": "TRY"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp_create.status_code == status.HTTP_201_CREATED
    booking = resp_create.json()
    booking_id = booking["id"]

    await client.post(
        f"/api/bookings/{booking_id}/quote",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    await client.post(
        f"/api/bookings/{booking_id}/book",
        headers={"Authorization": f"Bearer {token_a}"},
    )

    # refund-request => refund_in_progress
    resp_req = await client.post(
        f"/api/bookings/{booking_id}/refund-request",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp_req.status_code == status.HTTP_200_OK
    refund_in_progress = resp_req.json()
    assert refund_in_progress["state"] == "refund_in_progress"

    # refund-approve => refunded
    resp_approve = await client.post(
        f"/api/bookings/{booking_id}/refund-approve",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp_approve.status_code == status.HTTP_200_OK
    refunded = resp_approve.json()
    assert refunded["state"] == "refunded"

    # Refund-specific audits must exist alongside BOOKING_STATE_CHANGED audits
    refund_requested = await find_audit_for_booking(
        test_db.audit_logs,
        organization_id=org_a_id,
        action="REFUND_REQUESTED",
        booking_id=booking_id,
    )
    assert refund_requested is not None

    refund_approved = await find_audit_for_booking(
        test_db.audit_logs,
        organization_id=org_a_id,
        action="REFUND_APPROVED",
        booking_id=booking_id,
    )
    assert refund_approved is not None

    sc = await _find_state_change(
        test_db.audit_logs,
        org_id=org_a_id,
        booking_id=booking_id,
        from_state="booked",
        to_state="refund_in_progress",
    )
    assert sc is not None

    sc2 = await _find_state_change(
        test_db.audit_logs,
        org_id=org_a_id,
        booking_id=booking_id,
        from_state="refund_in_progress",
        to_state="refunded",
    )
    assert sc2 is not None

    # Reject path: new booking
    resp_create2 = await client.post(
        "/api/bookings",
        json={"amount": 700.0, "currency": "TRY"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp_create2.status_code == status.HTTP_201_CREATED
    booking2_id = resp_create2.json()["id"]

    await client.post(
        f"/api/bookings/{booking2_id}/quote",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    await client.post(
        f"/api/bookings/{booking2_id}/book",
        headers={"Authorization": f"Bearer {token_a}"},
    )

    resp_req2 = await client.post(
        f"/api/bookings/{booking2_id}/refund-request",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp_req2.status_code == status.HTTP_200_OK
    assert resp_req2.json()["state"] == "refund_in_progress"

    resp_reject = await client.post(
        f"/api/bookings/{booking2_id}/refund-reject",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp_reject.status_code == status.HTTP_200_OK
    rejected = resp_reject.json()
    assert rejected["state"] == "booked"

    refund_rejected = await find_audit_for_booking(
        test_db.audit_logs,
        organization_id=org_a_id,
        action="REFUND_REJECTED",
        booking_id=booking2_id,
    )
    assert refund_rejected is not None

    state_changes2 = await test_db.audit_logs.find(
        {
            "organization_id": org_a_id,
            "action": "BOOKING_STATE_CHANGED",
            "target_type": "booking",
            "target_id": booking2_id,
        }
    ).to_list(10)
    assert any(sc.get("meta", {}).get("from") == "booked" and sc.get("meta", {}).get("to") == "refund_in_progress" for sc in state_changes2)
    assert any(sc.get("meta", {}).get("from") == "refund_in_progress" and sc.get("meta", {}).get("to") == "booked" for sc in state_changes2)

    # Org isolation: OrgB cannot access OrgA's bookings
    resp_get_b = await client.get(
        f"/api/bookings/{booking_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp_get_b.status_code == status.HTTP_404_NOT_FOUND
