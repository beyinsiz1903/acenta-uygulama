from __future__ import annotations

import unicodedata
from typing import Iterable, List


MODULE_ALIASES = {
    "dashboard": {"dashboard", "genel_bakis"},
    "rezervasyonlar": {"rezervasyonlar"},
    "musteriler": {"musteriler"},
    "mutabakat": {"mutabakat", "finans"},
    "raporlar": {"raporlar"},
    "oteller": {"oteller", "otellerim", "urunler"},
    "musaitlik": {"musaitlik", "musaitlik_takibi"},
    "turlar": {"turlar", "turlarimiz"},
    "sheet_baglantilari": {
        "sheet_baglantilari",
        "google_sheets",
        "google_sheet_baglantisi",
        "google_sheet_baglantilari",
    },
}


ALIAS_TO_CANONICAL = {
    alias: canonical
    for canonical, aliases in MODULE_ALIASES.items()
    for alias in aliases
}


def _slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return ascii_text.strip().lower().replace("-", "_").replace(" ", "_")


def normalize_agency_module_key(value: str | None) -> str:
    key = _slugify(str(value or ""))
    if not key:
        return ""
    return ALIAS_TO_CANONICAL.get(key, key)


def normalize_agency_modules(values: Iterable[str] | None) -> List[str]:
    seen: set[str] = set()
    normalized: List[str] = []

    for raw_value in values or []:
        key = normalize_agency_module_key(raw_value)
        if not key or key in seen:
            continue
        seen.add(key)
        normalized.append(key)

    return normalized