from __future__ import annotations

from typing import Any

import pytest

from app.services.org_service import initialize_org_defaults
from app.utils import now_utc



@pytest.mark.exit_sprint1

@pytest.mark.anyio
async def test_org_init_writes_audit_events(test_db: Any) -> None:
    # Arrange: bare org
    now = now_utc()
    res = await test_db.organizations.insert_one(
        {
            "name": "OrgAuditTest",
            "slug": "org-audit-test",
            "created_at": now,
            "updated_at": now,
            "settings": {"currency": "TRY"},
        }
    )
    org_id = str(res.inserted_id)
    actor = {"email": "admin@example.com", "roles": ["super_admin"]}

    # Act
    await initialize_org_defaults(test_db, org_id, actor)

    # Assert: ORG_INITIALIZED and DEFAULTS_CREATED exist for this org
    logs = await test_db.audit_logs.find({"organization_id": org_id}).to_list(20)
    actions = {log.get("action") for log in logs}
    assert "ORG_INITIALIZED" in actions
    assert "DEFAULTS_CREATED" in actions
