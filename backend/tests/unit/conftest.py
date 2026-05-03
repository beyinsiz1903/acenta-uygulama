"""Minimal conftest for `tests/unit/` — DB-free unit tests.

This conftest *intentionally* does NOT import the parent ``tests/conftest.py``
fixtures (which require a live MongoDB connection via autouse fixtures).
Unit tests under this directory must NOT touch the database.

Provides only:
- ``anyio_backend`` parameter so ``@pytest.mark.anyio`` async tests work
  with the asyncio backend (consistent with the parent harness).
- Minimal sys.path bootstrapping so ``app`` imports resolve.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure backend root is importable for `app.*`.
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


# Session-scope to align with the parent harness (`tests/conftest.py`) — some
# session-scoped fixtures depend on `anyio_backend`, and a function-scope
# definition here would cause pytest ScopeMismatch errors when both conftests
# are loaded.
@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"
