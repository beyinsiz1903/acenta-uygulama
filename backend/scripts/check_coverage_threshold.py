"""Coverage Threshold Check — Kademeli enforcement.

3 seviye threshold:
  1. Overall: Tüm backend kodu için minimum % (başlangıç: düşük, aşırı agresif değil)
  2. Critical modules: Yüksek riskli modüller için daha yüksek eşik
  3. Changed-files: Sadece uyarı (henüz enforcement yok)

Çalıştırma:
    python scripts/check_coverage_threshold.py
    python scripts/check_coverage_threshold.py --xml coverage.xml
"""
from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# ── Thresholds ──────────────────────────────────────
OVERALL_MIN = 20          # Başlangıç düşük — eski kod nedeniyle pipeline kırılmasın
CRITICAL_MODULES_MIN = 30  # Kritik modüller için biraz daha yüksek
WARN_THRESHOLD = 50       # Bu altındaysa uyarı

CRITICAL_MODULES = [
    "app/modules/booking",
    "app/modules/auth",
    "app/modules/tenant",
    "app/infrastructure",
]


def parse_coverage_xml(xml_path: str) -> dict:
    """Parse coverage.xml and return module-level stats."""
    tree = ET.parse(xml_path)
    root = tree.getroot()

    # Overall
    overall_rate = float(root.attrib.get("line-rate", "0")) * 100

    # Per-package
    packages = {}
    for pkg in root.findall(".//package"):
        name = pkg.attrib.get("name", "")
        rate = float(pkg.attrib.get("line-rate", "0")) * 100
        packages[name] = rate

    return {"overall": overall_rate, "packages": packages}


def check_thresholds(stats: dict) -> list[str]:
    """Check coverage against thresholds. Returns list of failures."""
    failures = []
    warnings = []

    # 1. Overall
    if stats["overall"] < OVERALL_MIN:
        failures.append(
            f"❌ Overall coverage {stats['overall']:.1f}% < minimum {OVERALL_MIN}%"
        )
    elif stats["overall"] < WARN_THRESHOLD:
        warnings.append(
            f"⚠️  Overall coverage {stats['overall']:.1f}% < warning threshold {WARN_THRESHOLD}%"
        )
    else:
        print(f"✅ Overall coverage: {stats['overall']:.1f}% (min: {OVERALL_MIN}%)")

    # 2. Critical modules
    for mod in CRITICAL_MODULES:
        mod_key = mod.replace("/", ".")
        # Find matching packages
        matched = {k: v for k, v in stats["packages"].items() if mod_key in k}
        if matched:
            avg = sum(matched.values()) / len(matched)
            if avg < CRITICAL_MODULES_MIN:
                failures.append(
                    f"❌ Critical module '{mod}' coverage {avg:.1f}% < minimum {CRITICAL_MODULES_MIN}%"
                )
            else:
                print(f"✅ Critical module '{mod}': {avg:.1f}% (min: {CRITICAL_MODULES_MIN}%)")

    for w in warnings:
        print(w)

    return failures


def main():
    xml_path = "coverage.xml"

    # Allow override
    if len(sys.argv) > 2 and sys.argv[1] == "--xml":
        xml_path = sys.argv[2]

    coverage_file = Path(xml_path)
    if not coverage_file.exists():
        print(f"⚠️  Coverage file not found: {xml_path}")
        print("   Run 'make test-backend' first to generate coverage data.")
        print("   Skipping threshold check (non-blocking).")
        sys.exit(0)

    stats = parse_coverage_xml(xml_path)
    print(f"\n📊 Coverage Report")
    print(f"   Overall: {stats['overall']:.1f}%")
    print(f"   Packages: {len(stats['packages'])}")
    print()

    failures = check_thresholds(stats)

    if failures:
        print("\n🚫 Coverage threshold violations:")
        for f in failures:
            print(f"   {f}")
        sys.exit(1)
    else:
        print("\n✅ All coverage thresholds met.")


if __name__ == "__main__":
    main()
