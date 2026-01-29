from __future__ import annotations

from typing import Any

import pytest

from app.services.org_service import initialize_org_defaults
from app.utils import now_utc


@pytest.mark.anyio
async def test_initialize_org_defaults_idempotent(test_db: Any) -> None:
    # Arrange: create bare org doc
    now = now_utc()
    res = await test_db.organizations.insert_one(
        {
            "name": "OrgDefaultsIdempotent",
            "slug": "org-defaults-idem",
            "created_at": now,
            "updated_at": now,
            "settings": {"currency": "TRY"},
        }
    )
    org_id = str(res.inserted_id)
    actor = {"email": "admin@example.com"}

    # First init
    await initialize_org_defaults(test_db, org_id, actor)

    # Capture counts
    cp_count_1 = await test_db.credit_profiles.count_documents({"organization_id": org_id})
    rp_count_1 = await test_db.refund_policies.count_documents({"organization_id": org_id})
    rr_count_1 = await test_db.risk_rules.count_documents({"organization_id": org_id})
    tq_count_1 = await test_db.task_queues.count_documents({"organization_id": org_id})

    # Second init (should not create duplicates)
    await initialize_org_defaults(test_db, org_id, actor)

    cp_count_2 = await test_db.credit_profiles.count_documents({"organization_id": org_id})
    rp_count_2 = await test_db.refund_policies.count_documents({"organization_id": org_id})
    rr_count_2 = await test_db.risk_rules.count_documents({"organization_id": org_id})
    tq_count_2 = await test_db.task_queues.count_documents({"organization_id": org_id})

    assert cp_count_1 == cp_count_2 == 1
    assert rp_count_1 == rp_count_2 == 1
    assert rr_count_1 == rr_count_2 == 3
    assert tq_count_1 == tq_count_2 == 2
