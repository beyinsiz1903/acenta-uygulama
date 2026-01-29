from __future__ import annotations

from typing import Any

import pytest

from app.services.org_service import initialize_org_defaults
from app.utils import now_utc



@pytest.mark.exit_sprint1

@pytest.mark.anyio
async def test_org_defaults_created_for_fresh_org(test_db: Any) -> None:
    # Arrange: create bare org doc
    now = now_utc()
    res = await test_db.organizations.insert_one(
        {
            "name": "OrgDefaultsTest",
            "slug": "org-defaults-test",
            "created_at": now,
            "updated_at": now,
            "settings": {"currency": "TRY"},
        }
    )
    org_id = str(res.inserted_id)
    actor = {"email": "admin@example.com"}

    # Act
    await initialize_org_defaults(test_db, org_id, actor)

    # Assert: exactly one Standard credit profile
    credit_profiles = await test_db.credit_profiles.find({"organization_id": org_id}).to_list(10)
    assert len([cp for cp in credit_profiles if cp.get("name") == "Standard"]) == 1

    # Exactly one refund policy
    refund_policies = await test_db.refund_policies.find({"organization_id": org_id}).to_list(10)
    assert len(refund_policies) == 1

    # Exactly three risk rules
    risk_rules = await test_db.risk_rules.find({"organization_id": org_id}).to_list(10)
    assert len(risk_rules) == 3

    # Exactly two task queues: Ops and Finance
    task_queues = await test_db.task_queues.find({"organization_id": org_id}).to_list(10)
    names = sorted(q.get("name") for q in task_queues)
    assert names == ["Finance", "Ops"]
