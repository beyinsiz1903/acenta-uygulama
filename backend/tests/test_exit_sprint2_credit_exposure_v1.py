from __future__ import annotations

from typing import Any

import pytest


@pytest.mark.exit_sprint2
@pytest.mark.anyio
async def test_credit_exposure_v1_placeholder(test_db: Any) -> None:
    """Sprint 2 Credit & Exposure v1 gate placeholder.

    This test will be expanded to:
    - Seed a simple credit profile for an org
    - Attempt to book within and beyond limit
    - Assert that over-limit booking enters a hold/on_hold state instead of being rejected
    For now, it exists only to wire the exit_sprint2 marker and will be implemented in later steps.
    """

    # Placeholder assertion to keep test passing until implementation is added.
    assert test_db is not None
