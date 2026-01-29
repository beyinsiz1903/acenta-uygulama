from __future__ import annotations

from typing import Any

import pytest


@pytest.mark.exit_sprint2
@pytest.mark.anyio
async def test_risk_rules_v1_placeholder(test_db: Any) -> None:
    """Sprint 2 Risk & Rules v1 gate placeholder.

    Will enforce at minimum:
    - a simple threshold rule (amount > X) emits a risk alert / audit event
    - booking state need not change in P0
    Implementation will be added in subsequent steps.
    """

    assert test_db is not None
