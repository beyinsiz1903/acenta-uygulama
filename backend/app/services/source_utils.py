from __future__ import annotations

from typing import Any, Literal

Source = Literal["local", "pms"]


def ensure_source(doc: dict[str, Any], default: Source = "local") -> dict[str, Any]:
    if "source" not in doc or not doc.get("source"):
        doc["source"] = default
    return doc
