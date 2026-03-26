"""Architecture Guard — forbidden import rules for domain boundaries.

Enforces that domain modules do not directly import from other domain modules.
Cross-domain communication should go through service layer or events.

Usage:
    python -m pytest tests/test_architecture_guard.py -v
"""
from __future__ import annotations

import ast
import os
from pathlib import Path
from typing import Dict, List, Set, Tuple

import pytest

# Domain module paths and their forbidden imports
DOMAIN_MODULES = {
    "auth": "app/modules/auth",
    "identity": "app/modules/identity",
    "booking": "app/modules/booking",
    "b2b": "app/modules/b2b",
    "supplier": "app/modules/supplier",
    "finance": "app/modules/finance",
    "crm": "app/modules/crm",
    "operations": "app/modules/operations",
    "enterprise": "app/modules/enterprise",
    "system": "app/modules/system",
    "inventory": "app/modules/inventory",
    "pricing": "app/modules/pricing",
    "public": "app/modules/public",
    "reporting": "app/modules/reporting",
    "tenant": "app/modules/tenant",
}

# Allowed cross-domain imports (explicit exceptions)
ALLOWED_CROSS_IMPORTS = {
    # Any domain can import from these shared layers:
    "app.config",
    "app.db",
    "app.auth",
    "app.errors",
    "app.utils",
    "app.infrastructure",
    "app.services",         # Service layer is shared (for now)
    "app.routers",          # Router files are still in routers/ (Phase 2 moves references only)
    "app.constants",
    "app.schemas",
    "app.billing",
    "app.suppliers",        # Supplier package has shared adapters
    "app.domain",
    "app.middleware",
    "app.modules.tenant",   # Tenant context is used everywhere (security boundary)
}


def _get_imports_from_file(filepath: str) -> List[str]:
    """Extract all import module paths from a Python file."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=filepath)
    except (SyntaxError, UnicodeDecodeError):
        return []

    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
    return imports


def _is_cross_domain_import(import_path: str, own_domain: str) -> bool:
    """Check if an import crosses domain boundaries."""
    # Check if it imports from another domain module
    for domain_name, domain_path in DOMAIN_MODULES.items():
        if domain_name == own_domain:
            continue
        module_prefix = domain_path.replace("/", ".")
        if import_path.startswith(module_prefix):
            return True
    return False


def _is_allowed_import(import_path: str) -> bool:
    """Check if an import is in the allowed list."""
    for allowed in ALLOWED_CROSS_IMPORTS:
        if import_path.startswith(allowed):
            return True
    return False


def collect_violations() -> List[Tuple[str, str, str, str]]:
    """Collect all cross-domain import violations.

    Returns list of (domain, file, import_path, target_domain).
    """
    violations = []
    backend_root = Path(__file__).resolve().parents[1]

    for domain_name, domain_path in DOMAIN_MODULES.items():
        full_domain_path = backend_root / domain_path
        if not full_domain_path.exists():
            continue

        for py_file in full_domain_path.rglob("*.py"):
            # Skip __init__.py (these are the aggregation files that import routers)
            if py_file.name == "__init__.py":
                continue

            rel_path = str(py_file.relative_to(backend_root))
            imports = _get_imports_from_file(str(py_file))

            for imp in imports:
                if _is_cross_domain_import(imp, domain_name) and not _is_allowed_import(imp):
                    # Find which domain it's importing from
                    target = "unknown"
                    for dn, dp in DOMAIN_MODULES.items():
                        if imp.startswith(dp.replace("/", ".")):
                            target = dn
                            break
                    violations.append((domain_name, rel_path, imp, target))

    return violations


def test_no_cross_domain_imports():
    """Ensure no domain module directly imports from another domain module.

    Exceptions:
    - __init__.py files (router aggregation layer)
    - Allowed shared imports (config, db, auth, services, etc.)
    - tenant module (security boundary, used everywhere)
    """
    violations = collect_violations()

    if violations:
        msg_lines = ["Cross-domain import violations found:\n"]
        for domain, filepath, imp, target in violations:
            msg_lines.append(f"  [{domain}] {filepath}")
            msg_lines.append(f"    imports {imp} (from domain: {target})")
        msg_lines.append(f"\nTotal violations: {len(violations)}")
        msg_lines.append("Fix: Use service layer or event-driven communication instead.")
        pytest.fail("\n".join(msg_lines))


if __name__ == "__main__":
    violations = collect_violations()
    if violations:
        print("Cross-domain import violations:")
        for domain, filepath, imp, target in violations:
            print(f"  [{domain}] {filepath} → {imp} (target: {target})")
        print(f"\nTotal: {len(violations)} violations")
    else:
        print("No cross-domain import violations found.")
