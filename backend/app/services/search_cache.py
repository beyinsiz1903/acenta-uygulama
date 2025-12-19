from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_search_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Normalize request params to maximize cache hit.

    Rules:
    - ensure occupancy.children exists
    - normalize currency
    - stable key ordering via JSON dump
    """
    p = {
        "hotel_id": payload.get("hotel_id"),
        "check_in": payload.get("check_in"),
        "check_out": payload.get("check_out"),
        "currency": payload.get("currency") or "TRY",
        "occupancy": {
            "adults": int((payload.get("occupancy") or {}).get("adults") or 0),
            "children": int((payload.get("occupancy") or {}).get("children") or 0),
        },
        "channel": payload.get("channel") or "agency_extranet",
    }
    return p


def cache_key(organization_id: str, agency_id: str, normalized: dict[str, Any]) -> str:
    raw = json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    h = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]
    return f"srchcache:{organization_id}:{agency_id}:{h}"
