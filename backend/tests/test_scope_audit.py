"""Scope & Dependency Audit — Domain boundary, router registry, and metadata consistency.

Tests:
  1. Router Registry Completeness — Her modül __init__.py'deki import, gerçek dosyaya karşılık geliyor mu?
  2. Router Ownership Manifest Uyumu — Manifest'teki domain sayıları ile gerçek import sayıları uyuşuyor mu?
  3. Orphan Router Detection — app/routers/ altında hiçbir modül tarafından import edilmeyen router var mı?
  4. Domain Boundary Violations — __init__.py dışında cross-domain import var mı? (architecture guard ile örtüşür)
  5. Legacy Router in domain_router_registry — Registry'de kaç legacy import kaldı?
  6. Navigation Metadata Consistency — (gelecek: persona navigation dosyaları ile route tanımlarının uyumu)

Usage:
    python -m pytest tests/test_scope_audit.py -v
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
ROUTERS_DIR = BACKEND_ROOT / "app" / "routers"
MODULES_DIR = BACKEND_ROOT / "app" / "modules"
REGISTRY_FILE = BACKEND_ROOT / "app" / "bootstrap" / "domain_router_registry.py"

# These routers are intentionally NOT in any module (cross-domain utilities)
KNOWN_EXCEPTIONS = {
    "admin_orphan_migration.py",
    "admin_outbox.py",
    "webhooks.py",
    "admin_webhooks.py",
    "__init__.py",
}

# Routers that are sub-packages (directories), not single files
ROUTER_SUBPACKAGES = {
    "inventory",   # app/routers/inventory/ is a sub-package
}


def _get_all_router_files() -> set[str]:
    """Get all .py files in app/routers/ (excluding __init__.py and sub-packages)."""
    files = set()
    for f in ROUTERS_DIR.iterdir():
        if f.is_file() and f.suffix == ".py" and f.name != "__init__.py":
            files.add(f.name)
        elif f.is_dir() and f.name in ROUTER_SUBPACKAGES:
            files.add(f.name)  # Track as a package name
    return files


def _get_module_imported_routers() -> dict[str, set[str]]:
    """Parse each module __init__.py and extract imported router file names.

    Returns imports as:
      - "X.py"             → legacy `from app.routers.X` (lives in app/routers/)
      - "<domain>/X.py"    → module-local `from app.modules.<domain>.routers.X`
                              (lives in app/modules/<domain>/routers/)

    Distinguishing the two prevents false-positive duplicates when two domains
    each have their own internal `routers/onboarding.py` (they are different files).
    """
    result = {}
    for init_file in sorted(MODULES_DIR.glob("*/__init__.py")):
        domain = init_file.parent.name
        imports = set()
        with open(init_file) as f:
            content = f.read()

        # Match: from app.routers.XXX import ... (legacy path, pre-migration)
        for match in re.finditer(r"from app\.routers\.(\w+)", content):
            router_name = match.group(1)
            if (ROUTERS_DIR / f"{router_name}.py").exists():
                imports.add(f"{router_name}.py")
            elif (ROUTERS_DIR / router_name).is_dir():
                imports.add(router_name)

        # Match: from app.modules.{src_domain}.routers.XXX import ...
        # Tracked as "<src_domain>/X.py" so that two domains owning their own
        # internal `routers/X.py` are NOT treated as duplicates of one shared file.
        # Legacy `app/routers/X.py` shims are credited via the registry-import path,
        # not here.
        for match in re.finditer(r"from app\.modules\.(\w+)\.routers\.(\w+)", content):
            src_domain = match.group(1)
            router_name = match.group(2)
            imports.add(f"{src_domain}/{router_name}.py")

        result[domain] = imports
    return result


def _get_registry_imported_routers() -> set[str]:
    """Get router files imported from domain_router_registry.py."""
    imports = set()
    with open(REGISTRY_FILE) as f:
        content = f.read()
    for match in re.finditer(r"from app\.routers\.(\w+)", content):
        router_name = match.group(1)
        if (ROUTERS_DIR / f"{router_name}.py").exists():
            imports.add(f"{router_name}.py")
    return imports


# ═══════════════════════════════════════════════════
# TEST 1: Imported routers actually exist
# ═══════════════════════════════════════════════════
def test_imported_routers_exist():
    """Every router imported in module __init__.py must exist as a file."""
    module_imports = _get_module_imported_routers()
    all_router_files = _get_all_router_files()
    missing = []

    for domain, imports in module_imports.items():
        for imp in imports:
            if "/" in imp:
                # Module-local: "<src_domain>/X.py" must exist in app/modules/<src_domain>/routers/
                src_domain, fname = imp.split("/", 1)
                module_routers_dir = MODULES_DIR / src_domain / "routers"
                if not (module_routers_dir / fname).exists():
                    missing.append(
                        f"[{domain}] imports module-local '{imp}' but file not found"
                    )
            else:
                if imp not in all_router_files and imp not in ROUTER_SUBPACKAGES:
                    missing.append(f"[{domain}] imports '{imp}' but file not found")

    if missing:
        pytest.fail(
            "Router files imported but not found:\n"
            + "\n".join(f"  {m}" for m in missing)
        )


# ═══════════════════════════════════════════════════
# TEST 2: Orphan router detection
# ═══════════════════════════════════════════════════
def test_no_orphan_routers():
    """Every router file in app/routers/ should be imported by exactly one domain module
    or be in the known exceptions list."""
    all_files = _get_all_router_files()
    module_imports = _get_module_imported_routers()
    registry_imports = _get_registry_imported_routers()

    # Collect all imported files
    all_imported = set()
    for imports in module_imports.values():
        all_imported.update(imports)
    all_imported.update(registry_imports)

    orphans = []
    for f in sorted(all_files):
        if f in KNOWN_EXCEPTIONS:
            continue
        if f not in all_imported and f not in ROUTER_SUBPACKAGES:
            orphans.append(f)

    if orphans:
        msg = (
            f"Found {len(orphans)} orphan router(s) not imported by any domain module:\n"
            + "\n".join(f"  - {o}" for o in orphans)
            + "\n\nThese should be assigned to a domain module or added to KNOWN_EXCEPTIONS."
        )
        # Uyarı olarak göster ama şimdilik fail etme (kademeli enforcement)
        import warnings
        warnings.warn(msg)


# ═══════════════════════════════════════════════════
# TEST 3: No duplicate router ownership
# ═══════════════════════════════════════════════════
def test_no_duplicate_router_ownership():
    """Each router file should be owned by at most one domain module."""
    module_imports = _get_module_imported_routers()
    ownership: dict[str, list[str]] = {}

    for domain, imports in module_imports.items():
        for imp in imports:
            ownership.setdefault(imp, []).append(domain)

    duplicates = {k: v for k, v in ownership.items() if len(v) > 1}
    if duplicates:
        msg_lines = ["Router files owned by multiple domains:"]
        for router, domains in duplicates.items():
            msg_lines.append(f"  {router} → {', '.join(domains)}")
        pytest.fail("\n".join(msg_lines))


# ═══════════════════════════════════════════════════
# TEST 4: Registry legacy count
# ═══════════════════════════════════════════════════
def test_registry_legacy_count():
    """domain_router_registry.py should have minimal direct router imports.
    All routers should be in domain modules, not the registry."""
    registry_imports = _get_registry_imported_routers()
    # Current known legacy: admin_orphan_migration, admin_outbox, webhooks, admin_webhooks
    MAX_LEGACY = 4

    if len(registry_imports) > MAX_LEGACY:
        pytest.fail(
            f"domain_router_registry.py has {len(registry_imports)} direct router imports "
            f"(max allowed: {MAX_LEGACY}).\n"
            f"Legacy routers: {sorted(registry_imports)}\n"
            f"Move these to their domain module's __init__.py."
        )


# ═══════════════════════════════════════════════════
# TEST 5: Module __init__.py must have docstring
# ═══════════════════════════════════════════════════
def test_module_init_has_docstring():
    """Every domain module __init__.py must have a docstring describing its boundary."""
    missing = []
    for init_file in sorted(MODULES_DIR.glob("*/__init__.py")):
        domain = init_file.parent.name
        with open(init_file) as f:
            try:
                tree = ast.parse(f.read())
            except SyntaxError:
                missing.append(f"{domain}: SyntaxError")
                continue
        docstring = ast.get_docstring(tree)
        if not docstring:
            missing.append(domain)

    if missing:
        pytest.fail(
            "Domain modules missing docstring in __init__.py:\n"
            + "\n".join(f"  - {m}" for m in missing)
        )


# ═══════════════════════════════════════════════════
# TEST 6: Domain module count matches expected
# ═══════════════════════════════════════════════════
EXPECTED_DOMAINS = {
    "auth", "b2b", "booking", "crm", "enterprise", "finance",
    "identity", "inventory", "mobile", "operations", "pricing",
    "public", "reporting", "supplier", "system", "tenant",
}


def test_expected_domains_exist():
    """All expected domain modules must exist."""
    actual = {d.name for d in MODULES_DIR.iterdir() if d.is_dir() and (d / "__init__.py").exists()}
    missing = EXPECTED_DOMAINS - actual
    extra = actual - EXPECTED_DOMAINS

    msgs = []
    if missing:
        msgs.append(f"Missing domains: {sorted(missing)}")
    if extra:
        msgs.append(f"Unexpected domains: {sorted(extra)}")
    if msgs:
        pytest.fail("\n".join(msgs))


# ═══════════════════════════════════════════════════
# TEST 7: No forbidden imports in services layer
# ═══════════════════════════════════════════════════
FORBIDDEN_SERVICE_IMPORTS = [
    "from fastapi import",         # Services should not import FastAPI (that's router layer)
    "from starlette.requests",     # Services should not depend on HTTP layer
]

# Known exceptions where services legitimately use FastAPI types
SERVICE_IMPORT_EXCEPTIONS = {
    "app/services/rate_limit.py",
    "app/services/webhook_service.py",
    "app/services/click_to_pay.py",
    "app/services/integration_hub.py",
}


def test_services_no_fastapi_imports():
    """Service layer should not directly import FastAPI/HTTP types.
    This is a soft warning — not enforced strictly yet (kademeli)."""
    violations = []
    services_dir = BACKEND_ROOT / "app" / "services"
    for py_file in services_dir.rglob("*.py"):
        rel_path = str(py_file.relative_to(BACKEND_ROOT))
        if rel_path in SERVICE_IMPORT_EXCEPTIONS:
            continue
        with open(py_file) as f:
            for i, line in enumerate(f, 1):
                for pattern in FORBIDDEN_SERVICE_IMPORTS:
                    if pattern in line and not line.strip().startswith("#"):
                        violations.append(f"  {rel_path}:{i} → {line.strip()}")

    if violations:
        # Uyarı olarak göster, henüz fail etme (kademeli enforcement)
        import warnings
        warnings.warn(
            f"Found {len(violations)} service-layer FastAPI/HTTP imports:\n"
            + "\n".join(violations[:10])
            + (f"\n  ... and {len(violations) - 10} more" if len(violations) > 10 else "")
            + "\n\nConsider moving HTTP-specific logic to router layer."
        )
