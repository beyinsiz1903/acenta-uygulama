from __future__ import annotations

from typing import Any

import pytest


@pytest.mark.exit_sprint2
@pytest.mark.anyio
async def test_refund_workflow_v1_placeholder(test_db: Any) -> None:
    """Sprint 2 Refund Workflow v1 gate placeholder.

    Final contract to cover:
    - refund_in_progress state via refund-request API
    - refund-approve => refunded
    - refund-reject  => booked
    - audit entries for each transition
    For now this is a placeholder to define scope and marker wiring.
    """

    assert test_db is not None
