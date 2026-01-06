from __future__ import annotations

import hashlib
import json
from typing import Any, Dict


def canonical_json(obj: Any) -> str:
    """Return a stable JSON string for hashing.

    - sort_keys ensures deterministic order
    - separators compacts whitespace
    """
    return json.dumps(obj, separators=(",", ":"), sort_keys=True, ensure_ascii=False)


def compute_request_hash(method: str, path: str, body: Dict[str, Any]) -> str:
    raw = f"{method.upper()}|{path}|{canonical_json(body)}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
