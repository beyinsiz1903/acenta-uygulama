from __future__ import annotations

from typing import Any, Dict, Optional

import jwt
import pytest
from bson import ObjectId
from fastapi import status
from httpx import AsyncClient

from app.auth import _jwt_secret
from app.utils import now_utc


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
    refund_requested = await test_db.audit_logs.find_one(
        {
            "organization_id": org_a_id,
            "action": "REFUND_REQUESTED",
            "target_type": "booking",
            "target_id": booking_id,
        }
    )
    assert refund_requested is not None

    refund_approved = await test_db.audit_logs.find_one(
        {
            "organization_id": org_a_id,
            "action": "REFUND_APPROVED",
            "target_type": "booking",
            "target_id": booking_id,
        }
    )
    assert refund_approved is not None

    state_changes = await test_db.audit_logs.find(
        {
            "organization_id": org_a_id,
            "action": "BOOKING_STATE_CHANGED",
            "target_type": "booking",
            "target_id": booking_id,
        }
    ).to_list(10)
    assert any(sc.get("meta", {}).get("from") == "booked" and sc.get("meta", {}).get("to") == "refund_in_progress" for sc in state_changes)
    assert any(sc.get("meta", {}).get("from") == "refund_in_progress" and sc.get("meta", {}).get("to") == "refunded" for sc in state_changes)

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

    refund_rejected = await test_db.audit_logs.find_one(
        {
            "organization_id": org_a_id,
            "action": "REFUND_REJECTED",
            "target_type": "booking",
            "target_id": booking2_id,
        }
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
