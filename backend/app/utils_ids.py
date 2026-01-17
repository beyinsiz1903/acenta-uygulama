from __future__ import annotations

from typing import Any, Dict, Optional

from bson import ObjectId


def build_id_filter(value: Optional[str], *, field_name: str = "_id") -> Dict[str, Any]:
    """Build a MongoDB filter for an ID field that may be string or ObjectId.

    - If value is falsy, returns empty dict.
    - If value looks like a valid ObjectId, matches either ObjectId or its string form.
    - Otherwise, matches string form only.
    """

    if not value:
        return {}

    v = str(value)

    # Try to interpret as ObjectId; if it fails, fall back to string match only.
    try:
        oid = ObjectId(v)
    except Exception:  # noqa: BLE001
        return {field_name: v}

    # Support both raw ObjectId and string-stored variants.
    return {"$or": [{field_name: oid}, {field_name: v}]}
