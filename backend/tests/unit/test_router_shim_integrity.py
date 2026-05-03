"""Task #4 — Compat shim integrity guard.

After the system module split refactor (Task #1), every legacy
``app.routers.*`` import path is preserved by a small compat shim that
re-mounts the canonical ``app.modules.*.routers.*`` module. These shims
are the *only* thing keeping older test files, scripts, and external
tooling working without code changes. If someone:

  - edits a shim's target string,
  - deletes a shim,
  - or renames a canonical module without updating the shim,

…those legacy imports break silently — and we typically only find out
in production. This test walks **every** shim under
``backend/app/routers/`` and verifies it still resolves to its canonical
module and (where applicable) exposes the expected ``router`` attribute
as a FastAPI ``APIRouter``.

DB-free; runs in well under one second.
"""
from __future__ import annotations

import ast
import importlib
import sys
from pathlib import Path

import pytest
from fastapi import APIRouter


# `app/routers/` lives at backend/app/routers — derive from this file's
# location so the test is robust to where pytest is invoked from.
ROUTERS_DIR = Path(__file__).resolve().parents[2] / "app" / "routers"


# Shim flavors we recognise:
#  1. `sys.modules` redirect:
#       _sys.modules[__name__] = _il.import_module("app.modules.X.routers.Y")
#  2. Re-export from another (already-redirected) shim:
#       from app.routers.<x> import router
#  3. Package marker (`__init__.py`) — handled separately below.

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_import_module_calls(tree: ast.AST) -> dict[str, str]:
    """Return ``{var_name: module_path}`` for every assignment of the
    form ``foo = (_il|importlib).import_module("...")`` in the tree.

    Used to resolve indirect shims like::

        _mod = _il.import_module("app.modules.x.routers.y")
        _sys.modules[__name__] = _mod
    """
    out: dict[str, str] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name):
            continue
        call = node.value
        if not (isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)):
            continue
        if call.func.attr != "import_module":
            continue
        if not call.args or not isinstance(call.args[0], ast.Constant):
            continue
        if isinstance(call.args[0].value, str):
            out[target.id] = call.args[0].value
    return out


def _extract_sys_modules_target(source: str) -> str | None:
    """If ``source`` is a sys.modules-redirect shim, return the canonical
    module path. Recognises both the inline variant::

        _sys.modules[__name__] = _il.import_module("...")

    and the two-step variant::

        _mod = _il.import_module("...")
        _sys.modules[__name__] = _mod
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    indirect = _extract_import_module_calls(tree)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        # Match `_sys.modules[__name__] = ...`.
        target = node.targets[0] if node.targets else None
        if not isinstance(target, ast.Subscript):
            continue
        value = target.value
        if not (isinstance(value, ast.Attribute) and value.attr == "modules"):
            continue
        rhs = node.value
        # Variant 1: inline `import_module("...")` call on the RHS.
        if isinstance(rhs, ast.Call) and isinstance(rhs.func, ast.Attribute):
            if rhs.func.attr == "import_module" and rhs.args:
                arg = rhs.args[0]
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    return arg.value
        # Variant 2: RHS is a name bound earlier to an import_module call.
        if isinstance(rhs, ast.Name) and rhs.id in indirect:
            return indirect[rhs.id]
    return None


def _extract_from_import_targets(source: str) -> list[tuple[str, list[tuple[str, str | None]]]]:
    """Return all ``from MODULE import name [as alias], ...`` statements
    as ``(module, [(real_name, alias_or_None), ...])`` tuples — used for
    re-export-style shims and for ``app/routers/inventory/__init__.py``.

    Returning both the real attribute name AND the alias matters: for
    ``from X import a as b``, the attribute that must exist on ``X`` is
    ``a`` (not ``b``), but the legacy module ends up exposing ``b``.
    """
    out: list[tuple[str, list[tuple[str, str | None]]]] = []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return out
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module:
            names = [(alias.name, alias.asname) for alias in node.names]
            out.append((node.module, names))
    return out


def _gather_shim_files() -> list[Path]:
    files = sorted(p for p in ROUTERS_DIR.rglob("*.py") if p.name != "__init__.py")
    assert files, f"no router files found under {ROUTERS_DIR} — test path is wrong"
    return files


# ---------------------------------------------------------------------------
# 1. Coverage canary — make sure we actually find shims to test.
# ---------------------------------------------------------------------------


def test_shim_inventory_is_substantial():
    """Tripwire: if the shim count drops dramatically (<200), either the
    cleanup happened intentionally and this number should be updated, or
    a directory rename silently dropped most files from coverage.
    """
    files = _gather_shim_files()
    assert len(files) >= 200, (
        f"only {len(files)} router files discovered under {ROUTERS_DIR}; "
        f"expected ≥200. Either a bulk delete happened or the test path is wrong."
    )


# ---------------------------------------------------------------------------
# 2. Per-shim integrity (parametrised)
# ---------------------------------------------------------------------------


SHIM_FILES = _gather_shim_files()


def _legacy_module_path(file: Path) -> str:
    """Convert backend/app/routers/foo/bar.py -> app.routers.foo.bar"""
    rel = file.relative_to(ROUTERS_DIR.parents[1])  # relative to backend/
    parts = list(rel.with_suffix("").parts)
    return ".".join(parts)


@pytest.mark.parametrize(
    "shim_file",
    SHIM_FILES,
    ids=lambda p: p.relative_to(ROUTERS_DIR).as_posix(),
)
def test_shim_resolves_to_canonical_module(shim_file: Path):
    """Every legacy `app.routers.*` import must still resolve. For
    sys.modules-redirect shims: the legacy module object must literally
    be the canonical module. For re-export shims: every imported name
    must exist on the source module.
    """
    source = shim_file.read_text(encoding="utf-8")
    legacy_path = _legacy_module_path(shim_file)

    # Force a fresh import so a stale entry in sys.modules doesn't mask
    # a broken shim.
    sys.modules.pop(legacy_path, None)
    try:
        legacy_mod = importlib.import_module(legacy_path)
    except Exception as exc:  # pragma: no cover - failure path
        pytest.fail(
            f"legacy import path `{legacy_path}` failed to import:\n  {type(exc).__name__}: {exc}"
        )

    target = _extract_sys_modules_target(source)
    if target is not None:
        # Domain guard: every legitimate redirect target must live under
        # `app.modules.*`. This catches the failure mode where someone
        # retargets a shim to another shim (creating a redirect chain) or
        # to a wrong-but-still-importable module.
        assert target.startswith("app.modules."), (
            f"shim {shim_file} declares non-canonical target `{target}`. "
            f"Every legacy `app.routers.*` shim must redirect to "
            f"`app.modules.<domain>.routers.<name>` per MIGRATION.md. "
            f"Re-targeting to another shim would create an unverified chain."
        )
        # sys.modules-redirect shim: must have been replaced in place.
        canonical = importlib.import_module(target)
        assert legacy_mod is canonical, (
            f"shim {shim_file} declares target `{target}` but the legacy "
            f"path `{legacy_path}` resolved to a different module object "
            f"({getattr(legacy_mod, '__name__', '?')}). The sys.modules "
            f"redirect is broken — likely the shim body was edited."
        )
        # If the canonical module exposes a `router`, it must be APIRouter.
        if hasattr(canonical, "router"):
            assert isinstance(canonical.router, APIRouter), (
                f"`{target}.router` is not a FastAPI APIRouter "
                f"(got {type(canonical.router).__name__})"
            )
        return

    # Re-export style shim: walk each `from X import name` and confirm
    # every imported attribute actually exists on X.
    from_imports = _extract_from_import_targets(source)
    assert from_imports, (
        f"{shim_file} is neither a sys.modules-redirect shim nor a "
        f"re-export shim — unrecognised compat pattern. Either update the "
        f"shim to follow the canonical pattern in app/routers/b2b_bookings.py, "
        f"or extend this test to recognise the new pattern."
    )
    for src_module, names in from_imports:
        try:
            source_mod = importlib.import_module(src_module)
        except Exception as exc:  # pragma: no cover - failure path
            pytest.fail(
                f"{shim_file} imports from `{src_module}` which fails to "
                f"import:\n  {type(exc).__name__}: {exc}"
            )
        for real_name, alias in names:
            # Existence check: the *real* name (LHS of `as`) must exist
            # on the source module. The alias (RHS) is just the local
            # binding and doesn't need to exist on `source_mod`.
            assert hasattr(source_mod, real_name), (
                f"{shim_file}: `from {src_module} import {real_name}"
                f"{' as ' + alias if alias else ''}` will fail — attribute "
                f"`{real_name}` missing on source module."
            )
            # Aliased import (`as foo`) implies the legacy module is
            # expected to expose the alias name. Verify that mirror.
            if alias is not None:
                assert hasattr(legacy_mod, alias), (
                    f"{shim_file}: legacy module `{legacy_path}` should "
                    f"expose alias `{alias}` after `from {src_module} "
                    f"import {real_name} as {alias}`, but it doesn't."
                )
    # If the legacy module ended up with a `router`, type-check it too.
    if hasattr(legacy_mod, "router"):
        assert isinstance(legacy_mod.router, APIRouter), (
            f"`{legacy_path}.router` is not a FastAPI APIRouter "
            f"(got {type(legacy_mod.router).__name__})"
        )


# ---------------------------------------------------------------------------
# 3. The `app/routers/inventory` compat package re-exports four named
#    sub-routers. Verify each is an APIRouter.
# ---------------------------------------------------------------------------


def test_inventory_package_reexports_named_subrouters():
    sys.modules.pop("app.routers.inventory", None)
    pkg = importlib.import_module("app.routers.inventory")
    expected = {"sync_router", "booking_router", "diagnostics_router", "onboarding_router"}
    missing = expected - set(vars(pkg))
    assert not missing, (
        f"app.routers.inventory.__init__ no longer re-exports: {missing}. "
        f"Legacy `from app.routers.inventory import sync_router, ...` "
        f"imports will break."
    )
    for name in expected:
        attr = getattr(pkg, name)
        assert isinstance(attr, APIRouter), (
            f"app.routers.inventory.{name} is {type(attr).__name__}, "
            f"expected APIRouter."
        )


# ---------------------------------------------------------------------------
# 4. Self-test for the AST helper — guards against false negatives in
#    the parser if someone changes shim style.
# ---------------------------------------------------------------------------


def test_extract_sys_modules_target_recognises_canonical_pattern():
    src = (
        '"""Compat shim — moved to app.modules.x.routers.y"""\n'
        "import importlib as _il\n"
        "import sys as _sys\n"
        '_sys.modules[__name__] = _il.import_module("app.modules.x.routers.y")\n'
    )
    assert _extract_sys_modules_target(src) == "app.modules.x.routers.y"


def test_extract_sys_modules_target_recognises_two_step_variant():
    """The two-step variant (used by `customer_portal.py` to avoid a
    circular import via `app.modules.public.__init__`) must also be
    recognised so the shim isn't flagged as an unknown pattern.
    """
    src = (
        "import importlib as _il\n"
        "import sys as _sys\n"
        '_mod = _il.import_module("app.modules.operations.routers.customer_portal")\n'
        "_sys.modules[__name__] = _mod\n"
    )
    assert _extract_sys_modules_target(src) == "app.modules.operations.routers.customer_portal"


def test_extract_sys_modules_target_returns_none_for_non_shim():
    assert _extract_sys_modules_target("from fastapi import APIRouter\nrouter = APIRouter()\n") is None


def test_extract_from_import_preserves_alias_pair():
    """The re-export parser must return both the real attribute name
    and the alias so consumers can validate the right thing on each
    side. This guards `e2e_demo_router.py`'s `as router` pattern.
    """
    src = "from app.routers.inventory.diagnostics_router import e2e_demo_router as router\n"
    parsed = _extract_from_import_targets(src)
    assert parsed == [("app.routers.inventory.diagnostics_router", [("e2e_demo_router", "router")])]
