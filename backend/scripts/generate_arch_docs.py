"""Generate Architecture Documentation from Code.

Generates:
  1. DOMAIN_OWNERSHIP.md — Module → router ownership map
  2. ROUTER_MAP.md — All endpoint → domain mapping
  3. EVENT_CATALOG.md — All domain events and their targets
  4. CACHE_SURFACES.md — Cache key prefixes, TTLs, invalidation rules
  5. NAVIGATION_INDEX.md — Persona-based navigation metadata

Usage:
    python scripts/generate_arch_docs.py                    # Generate all
    python scripts/generate_arch_docs.py --check            # Check if docs are stale
    python scripts/generate_arch_docs.py --only event_catalog
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = BACKEND_ROOT.parents[0] / "docs" / "generated"
MODULES_DIR = BACKEND_ROOT / "app" / "modules"
ROUTERS_DIR = BACKEND_ROOT / "app" / "routers"

TIMESTAMP = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _ensure_docs_dir():
    DOCS_DIR.mkdir(parents=True, exist_ok=True)


# ═══════════════════════════════════════════════════════════
# 1. Domain Ownership
# ═══════════════════════════════════════════════════════════
def generate_domain_ownership() -> str:
    """Generate DOMAIN_OWNERSHIP.md from module __init__.py files."""
    lines = [
        "# Domain Ownership Map",
        f"> Auto-generated: {TIMESTAMP}",
        "> Source: `app/modules/*/` structure and `__init__.py` imports",
        "",
        "| Domain | Router Count | Has Dedicated Routers Dir | Docstring |",
        "|--------|-------------|--------------------------|-----------|",
    ]

    total_routers = 0
    for init_file in sorted(MODULES_DIR.glob("*/__init__.py")):
        domain = init_file.parent.name
        with open(init_file) as f:
            content = f.read()

        # Count routers
        router_count = content.count("include_router(")
        total_routers += router_count

        # Check dedicated routers dir
        has_routers_dir = (init_file.parent / "routers").is_dir()

        # Check docstring
        import ast
        try:
            tree = ast.parse(content)
            docstring = ast.get_docstring(tree)
            has_doc = "Yes" if docstring else "No"
        except Exception:
            has_doc = "Error"

        lines.append(
            f"| **{domain}** | {router_count} | {'Yes' if has_routers_dir else 'No'} | {has_doc} |"
        )

    lines.extend([
        "",
        f"**Total**: {total_routers} routers across {len(list(MODULES_DIR.glob('*/__init__.py')))} domains",
        "",
        "## Domain Descriptions",
        "",
    ])

    for init_file in sorted(MODULES_DIR.glob("*/__init__.py")):
        domain = init_file.parent.name
        with open(init_file) as f:
            content = f.read()
        import ast
        try:
            tree = ast.parse(content)
            docstring = ast.get_docstring(tree) or "No description"
            first_line = docstring.split("\n")[0]
        except Exception:
            first_line = "Parse error"
        lines.append(f"- **{domain}**: {first_line}")

    return "\n".join(lines) + "\n"


# ═══════════════════════════════════════════════════════════
# 2. Router Map
# ═══════════════════════════════════════════════════════════
def generate_router_map() -> str:
    """Generate ROUTER_MAP.md — endpoint prefix → domain mapping."""
    lines = [
        "# Router Map — Endpoint → Domain",
        f"> Auto-generated: {TIMESTAMP}",
        "> Source: `app/modules/*/` router registrations",
        "",
    ]

    for init_file in sorted(MODULES_DIR.glob("*/__init__.py")):
        domain = init_file.parent.name
        with open(init_file) as f:
            content = f.read()

        routers = re.findall(r"from\s+\S+\s+import\s+(\w+)\s+as\s+(\w+)", content)
        if not routers:
            routers = re.findall(r"from\s+\S+\s+import\s+(\w+)", content)
            routers = [(r, r) for r in routers if r.endswith("router") or r.endswith("_router")]

        if routers:
            lines.append(f"## {domain.upper()}")
            lines.append("")
            lines.append("| Import | Alias |")
            lines.append("|--------|-------|")
            for orig, alias in routers[:30]:  # Limit to avoid huge tables
                lines.append(f"| `{orig}` | `{alias}` |")
            if len(routers) > 30:
                lines.append(f"| ... | {len(routers) - 30} more |")
            lines.append("")

    return "\n".join(lines) + "\n"


# ═══════════════════════════════════════════════════════════
# 3. Event Catalog
# ═══════════════════════════════════════════════════════════
def generate_event_catalog() -> str:
    """Generate EVENT_CATALOG.md from event contracts."""
    sys.path.insert(0, str(BACKEND_ROOT))

    try:
        from app.infrastructure.event_contracts import EVENT_CATALOG
    except ImportError:
        return "# Event Catalog\n\n> Unable to import event contracts.\n"

    lines = [
        "# Event Catalog",
        f"> Auto-generated: {TIMESTAMP}",
        "> Source: `app/infrastructure/event_contracts.py`",
        "",
        "| Event Type | Description | Cache Invalidation Targets |",
        "|-----------|-------------|---------------------------|",
    ]

    domains: dict[str, list] = {}
    for entry in EVENT_CATALOG:
        domain = entry["event_type"].split(".")[0]
        domains.setdefault(domain, []).append(entry)

    for domain, events in sorted(domains.items()):
        lines.append(f"| **{domain}** | | |")
        for entry in events:
            targets = ", ".join(f"`{t}`" for t in entry["invalidates"])
            lines.append(f"| `{entry['event_type']}` | {entry['description']} | {targets} |")

    lines.extend([
        "",
        f"**Total**: {len(EVENT_CATALOG)} events across {len(domains)} domains",
        "",
        "## Event Naming Convention",
        "",
        "```",
        "{domain}.{entity}.{action}",
        "```",
        "",
        "Examples: `booking.reservation.created`, `ops.checkin.completed`",
    ])

    return "\n".join(lines) + "\n"


# ═══════════════════════════════════════════════════════════
# 4. Cache Surfaces
# ═══════════════════════════════════════════════════════════
def generate_cache_surfaces() -> str:
    """Generate CACHE_SURFACES.md from TTL config and event invalidation."""
    sys.path.insert(0, str(BACKEND_ROOT))

    try:
        from app.services.cache_ttl_config import TTL_MATRIX, SUPPLIER_TTL_OVERRIDES
        from app.infrastructure.event_contracts import EVENT_CATALOG
    except ImportError:
        return "# Cache Surfaces\n\n> Unable to import cache/event modules.\n"

    lines = [
        "# Cache Surfaces & TTL Strategy",
        f"> Auto-generated: {TIMESTAMP}",
        "> Source: `app/services/cache_ttl_config.py`, `app/infrastructure/event_contracts.py`",
        "",
        "## TTL Matrix (Default)",
        "",
        "| Category | Redis L1 (s) | MongoDB L2 (s) | Notes |",
        "|----------|-------------|---------------|-------|",
    ]

    # Group by category type
    for category, ttls in sorted(TTL_MATRIX.items()):
        redis_ttl = ttls.get("redis", "?")
        mongo_ttl = ttls.get("mongo", "?")
        note = ""
        if redis_ttl <= 30:
            note = "Ultra-short, high freshness"
        elif redis_ttl <= 120:
            note = "Short, near real-time"
        elif redis_ttl <= 300:
            note = "Medium, semi-static"
        elif redis_ttl <= 900:
            note = "Long, mostly static"
        else:
            note = "Very long, rarely changes"
        lines.append(f"| `{category}` | {redis_ttl} | {mongo_ttl} | {note} |")

    lines.extend([
        "",
        "## Supplier-Specific Overrides",
        "",
        "| Supplier | Category | Redis (s) | MongoDB (s) |",
        "|----------|----------|-----------|------------|",
    ])

    for supplier, categories in sorted(SUPPLIER_TTL_OVERRIDES.items()):
        for cat, ttls in categories.items():
            lines.append(f"| `{supplier}` | `{cat}` | {ttls.get('redis', '?')} | {ttls.get('mongo', '?')} |")

    # Invalidation matrix
    lines.extend([
        "",
        "## Cache Invalidation Matrix",
        "",
        "Shows which events invalidate which cache prefixes:",
        "",
        "| Cache Prefix | Invalidated By |",
        "|-------------|---------------|",
    ])

    prefix_to_events: dict[str, list[str]] = {}
    for entry in EVENT_CATALOG:
        for prefix in entry["invalidates"]:
            prefix_to_events.setdefault(prefix, []).append(entry["event_type"])

    for prefix, events in sorted(prefix_to_events.items()):
        event_list = ", ".join(f"`{e}`" for e in events[:5])
        if len(events) > 5:
            event_list += f" (+{len(events) - 5} more)"
        lines.append(f"| `{prefix}` | {event_list} |")

    lines.extend([
        "",
        "## Cache Policy Guidelines",
        "",
        "### Cache Safely",
        "- Dashboard summaries (eventual consistency acceptable)",
        "- KPI aggregations",
        "- Static metadata (hotel details, supplier registry)",
        "- CMS pages",
        "",
        "### Do NOT Cache Aggressively",
        "- Booking status checks (financial accuracy)",
        "- Payment verifications",
        "- Real-time availability during booking flow",
        "- Auth tokens / session data",
    ])

    return "\n".join(lines) + "\n"


# ═══════════════════════════════════════════════════════════
# 5. Navigation Index
# ═══════════════════════════════════════════════════════════
def generate_navigation_index() -> str:
    """Generate NAVIGATION_INDEX.md from frontend navigation configs."""
    frontend_root = BACKEND_ROOT.parents[0] / "frontend" / "src"
    nav_dir = frontend_root / "navigation"

    lines = [
        "# Navigation Index — Persona-Based Route Map",
        f"> Auto-generated: {TIMESTAMP}",
        "> Source: `frontend/src/navigation/` configs",
        "",
    ]

    if not nav_dir.exists():
        lines.append("Navigation directory not found. Skipping.")
        return "\n".join(lines) + "\n"

    for nav_file in sorted(nav_dir.glob("*.js")):
        persona = nav_file.stem
        lines.append(f"## {persona}")
        lines.append(f"Source: `navigation/{nav_file.name}`")
        lines.append("")

        with open(nav_file) as f:
            content = f.read()

        # Extract route paths
        paths = re.findall(r'path:\s*["\']([^"\']+)["\']', content)
        labels = re.findall(r'label:\s*["\']([^"\']+)["\']', content)

        if paths:
            lines.append("| Path | Label |")
            lines.append("|------|-------|")
            for i, path in enumerate(paths):
                label = labels[i] if i < len(labels) else "—"
                lines.append(f"| `{path}` | {label} |")
            lines.append("")

    return "\n".join(lines) + "\n"


# ═══════════════════════════════════════════════════════════
# Main: Generate All + Staleness Check
# ═══════════════════════════════════════════════════════════
GENERATORS = {
    "domain_ownership": ("DOMAIN_OWNERSHIP.md", generate_domain_ownership),
    "router_map": ("ROUTER_MAP.md", generate_router_map),
    "event_catalog": ("EVENT_CATALOG.md", generate_event_catalog),
    "cache_surfaces": ("CACHE_SURFACES.md", generate_cache_surfaces),
    "navigation_index": ("NAVIGATION_INDEX.md", generate_navigation_index),
}


def _content_hash(text: str) -> str:
    """Hash content excluding timestamp lines for staleness comparison."""
    lines = [l for l in text.splitlines() if not l.startswith("> Auto-generated:")]
    return hashlib.md5("\n".join(lines).encode()).hexdigest()


def _file_content_hash(path: Path) -> str:
    if not path.exists():
        return ""
    return _content_hash(path.read_text())


def main():
    _ensure_docs_dir()

    check_mode = "--check" in sys.argv
    only = None
    if "--only" in sys.argv:
        idx = sys.argv.index("--only")
        if idx + 1 < len(sys.argv):
            only = sys.argv[idx + 1]

    stale = []
    generated = []

    for key, (filename, generator) in GENERATORS.items():
        if only and key != only:
            continue

        output_path = DOCS_DIR / filename
        old_hash = _file_content_hash(output_path)

        content = generator()
        new_hash = _content_hash(content)

        if check_mode:
            if old_hash != new_hash:
                stale.append(filename)
        else:
            output_path.write_text(content)
            generated.append(filename)
            status = "UPDATED" if old_hash != new_hash else "UNCHANGED"
            print(f"  [{status}] {filename}")

    if check_mode:
        if stale:
            print(f"STALE docs ({len(stale)}):")
            for s in stale:
                print(f"  {s}")
            print("\nRun: python scripts/generate_arch_docs.py")
            sys.exit(1)
        else:
            print("All generated docs are up to date.")
    else:
        print(f"\nGenerated {len(generated)} docs in {DOCS_DIR.relative_to(BACKEND_ROOT.parents[0])}/")


if __name__ == "__main__":
    main()
