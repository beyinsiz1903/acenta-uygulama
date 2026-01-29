from __future__ import annotations

"""Guardrail test: prevent new code from bypassing repository layer for Motor access.

Scope (incremental):
- Enforced only for new Phase 1 code paths, so we don't break legacy modules.
- Currently enforced prefixes:
  - app/context/**
  - app/services/org_service.py

Allowed:
- Repository layer (app/repositories/**) may access Motor collections directly.
- Legacy modules outside enforced prefixes are currently ignored by this test.

TODO (expansion plan):
- Once legacy modules are refactored to use repositories, gradually add more
  enforced prefixes here (e.g. app/services/**, app/routers/**).
"""

from pathlib import Path
from typing import Iterable, List, Tuple

import pytest


# Root of the backend package for this repo
BACKEND_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = BACKEND_ROOT / "app"

# Paths where we allow direct Motor/Mongo access (repositories only)
ALLOWED_PATH_PREFIXES = [
    APP_ROOT / "repositories",
]

# Paths where we actively enforce the deny rules (Phase 1 new code)
ENFORCED_PATH_PREFIXES = [
    APP_ROOT / "context",
    APP_ROOT / "services" / "org_service.py",
]

# Simple string patterns to catch direct Motor usage / collection access
FORBIDDEN_PATTERNS = [
    "AsyncIOMotorCollection",
    ".get_collection(",
    "db[",
    "db.",
    "motor.motor_asyncio",
]


def _is_under_any(path: Path, prefixes: Iterable[Path]) -> bool:
    for p in prefixes:
        # File-specific prefix (e.g. org_service.py)
        if p.is_file():
            if path == p:
                return True
            continue
        # Directory prefix
        try:
            path.relative_to(p)
            return True
        except ValueError:
            continue
    return False


def _scan_file_forbidden_patterns(path: Path) -> List[Tuple[int, str]]:
    violations: List[Tuple[int, str]] = []
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return violations

    lines = text.splitlines()
    for lineno, line in enumerate(lines, start=1):
        # Skip comments quickly
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        for pattern in FORBIDDEN_PATTERNS:
            if pattern in line:
                violations.append((lineno, pattern))
    return violations


@pytest.mark.anyio
async def test_no_motor_collection_bypass_in_enforced_paths() -> None:
    """Fail if forbidden Motor/Mongo usage appears in enforced prefixes.

    This is intentionally incremental: it only enforces on new Phase 1 code
    paths, leaving legacy modules untouched for now.
    """

    violations: List[str] = []

    for py_file in APP_ROOT.rglob("*.py"):
        # Skip tests themselves
        if "tests" in py_file.parts:
            continue

        # Only enforce on selected prefixes
        if not _is_under_any(py_file, ENFORCED_PATH_PREFIXES):
            continue

        # Allowlist for repositories
        if _is_under_any(py_file, ALLOWED_PATH_PREFIXES):
            continue

        for lineno, pattern in _scan_file_forbidden_patterns(py_file):
            violations.append(f"{py_file.relative_to(BACKEND_ROOT)}:{lineno}: forbidden pattern '{pattern}'")

    if violations:
        joined = "\n".join(violations)
        pytest.fail(
            "Found direct Motor/Mongo access outside repositories in enforced paths:\n" + joined
        )
