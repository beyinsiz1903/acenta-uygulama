"""Contract-style checks for the PmsClient interface.

Not executed automatically in CI here, but can be used by testing agents.
"""

from __future__ import annotations

from app.services.connect_layer import get_pms_client


async def run_contract_tests():
    client = get_pms_client()
    assert hasattr(client, "quote")
    assert hasattr(client, "create_booking")
    assert hasattr(client, "cancel_booking")
