"""Physical Router Migration Script — Phase 2.5

Moves router files from app/routers/ to app/modules/{domain}/routers/
Creates backward-compatible shim files at old locations.
Updates module __init__.py to import from new local path.

Usage:
    python scripts/migrate_routers.py --dry-run   # Preview changes
    python scripts/migrate_routers.py              # Execute migration
    python scripts/migrate_routers.py --verify     # Post-migration verification
"""
from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
ROUTERS_DIR = BACKEND_ROOT / "app" / "routers"
MODULES_DIR = BACKEND_ROOT / "app" / "modules"

# Files that stay in app/routers/ (cross-domain utilities, kept in registry)
SKIP_FILES = {
    "__init__.py",
    "admin_orphan_migration.py",
    "admin_outbox.py",
    "webhooks.py",
    "admin_webhooks.py",
}

# Sub-package: app/routers/inventory/ stays as-is (handled differently)
SKIP_DIRS = {"inventory", "__pycache__"}


def build_migration_map() -> dict[str, list[str]]:
    """Parse each module __init__.py to build domain → [router_files] map."""
    migration = {}

    for init_file in sorted(MODULES_DIR.glob("*/__init__.py")):
        domain = init_file.parent.name
        with open(init_file) as f:
            content = f.read()

        routers = []
        for match in re.finditer(r"from app\.routers\.(\w+)", content):
            name = match.group(1)
            # Only add if it's a simple file (not a sub-package)
            if (ROUTERS_DIR / f"{name}.py").exists() and f"{name}.py" not in SKIP_FILES:
                routers.append(f"{name}.py")

        if routers:
            # Deduplicate
            migration[domain] = sorted(set(routers))

    return migration


def create_routers_init(domain_dir: Path, router_files: list[str]) -> None:
    """Create __init__.py for the new routers sub-package."""
    lines = [f'"""Routers for {domain_dir.parent.name} domain."""\n']
    (domain_dir / "__init__.py").write_text("\n".join(lines))


def create_shim(old_path: Path, domain: str, filename: str) -> None:
    """Create backward-compatible shim at old location."""
    module_name = filename.replace(".py", "")
    shim_content = (
        f'"""Compat shim — this router moved to app.modules.{domain}.routers.{module_name}\n'
        f'\n'
        f'This file is kept for backward compatibility during migration.\n'
        f'Update imports to: from app.modules.{domain}.routers.{module_name} import ...\n'
        f'"""\n'
        f'from app.modules.{domain}.routers.{module_name} import *  # noqa: F401,F403\n'
        f'\n'
        f'# Re-export router explicitly for FastAPI include_router\n'
        f'try:\n'
        f'    from app.modules.{domain}.routers.{module_name} import router  # noqa: F811\n'
        f'except ImportError:\n'
        f'    pass\n'
    )
    old_path.write_text(shim_content)


def update_module_init(init_file: Path, domain: str, router_files: list[str]) -> str:
    """Update module __init__.py to import from local routers/ instead of app.routers."""
    with open(init_file) as f:
        content = f.read()

    original = content

    for filename in router_files:
        module_name = filename.replace(".py", "")
        # Replace: from app.routers.{name} import ...
        # With:    from app.modules.{domain}.routers.{name} import ...
        old_pattern = f"from app.routers.{module_name}"
        new_pattern = f"from app.modules.{domain}.routers.{module_name}"
        content = content.replace(old_pattern, new_pattern)

    return content


def verify_migration(migration_map: dict[str, list[str]]) -> list[str]:
    """Verify all files are in the right place after migration."""
    errors = []

    for domain, files in migration_map.items():
        target_dir = MODULES_DIR / domain / "routers"
        for filename in files:
            target = target_dir / filename
            if not target.exists():
                errors.append(f"MISSING: {target}")

            shim = ROUTERS_DIR / filename
            if not shim.exists():
                errors.append(f"MISSING SHIM: {shim}")

    return errors


def main():
    dry_run = "--dry-run" in sys.argv
    verify_only = "--verify" in sys.argv

    migration_map = build_migration_map()

    if verify_only:
        errors = verify_migration(migration_map)
        if errors:
            print("❌ Verification failed:")
            for e in errors:
                print(f"  {e}")
            sys.exit(1)
        else:
            total = sum(len(v) for v in migration_map.values())
            print(f"✅ All {total} router files verified in correct locations.")
            sys.exit(0)

    total = sum(len(v) for v in migration_map.values())
    print(f"📁 Router Migration: {total} files across {len(migration_map)} domains\n")

    for domain, files in sorted(migration_map.items()):
        target_dir = MODULES_DIR / domain / "routers"
        print(f"\n{'='*60}")
        print(f"  {domain.upper()} ({len(files)} files)")
        print(f"  Target: {target_dir.relative_to(BACKEND_ROOT)}")
        print(f"{'='*60}")

        if not dry_run:
            target_dir.mkdir(parents=True, exist_ok=True)
            create_routers_init(target_dir, files)

        for filename in sorted(files):
            source = ROUTERS_DIR / filename
            target = target_dir / filename

            print(f"  {'[DRY]' if dry_run else '[MOVE]'} {filename}")

            if not dry_run:
                # Move file
                shutil.copy2(source, target)
                # Create shim at old location
                create_shim(source, domain, filename)

        if not dry_run:
            # Update module __init__.py
            init_file = MODULES_DIR / domain / "__init__.py"
            new_content = update_module_init(init_file, domain, files)
            init_file.write_text(new_content)
            print(f"  [UPDATE] {domain}/__init__.py imports updated")

    if dry_run:
        print(f"\n🔍 Dry run complete. {total} files would be migrated.")
        print("   Run without --dry-run to execute.")
    else:
        print(f"\n✅ Migration complete. {total} files moved.")
        print("   Shim files created at old locations for backward compatibility.")
        print("\n   Run: python scripts/migrate_routers.py --verify")


if __name__ == "__main__":
    main()
