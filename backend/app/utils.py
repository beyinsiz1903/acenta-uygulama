from __future__ import annotations

import csv
import io
import os
import secrets
import string
from datetime import datetime, timezone
from typing import Any, Iterable

from bson import ObjectId


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def serialize_doc(doc: Any) -> Any:
    """Recursively convert MongoDB docs into JSON-serializable structures."""
    if doc is None:
        return None

    if isinstance(doc, ObjectId):
        return str(doc)

    if isinstance(doc, datetime):
        return doc.isoformat()

    if isinstance(doc, list):
        return [serialize_doc(x) for x in doc]

    if isinstance(doc, dict):
        out: dict[str, Any] = {}
        for k, v in doc.items():
            if k == "_id":
                out["id"] = serialize_doc(v)
            else:
                out[k] = serialize_doc(v)
        return out

    return doc


def to_object_id(id_str: str) -> ObjectId:
    return ObjectId(id_str)


def generate_code(prefix: str, length: int = 6) -> str:
    alphabet = string.digits
    return f"{prefix}-{''.join(secrets.choice(alphabet) for _ in range(length))}"


def generate_pnr() -> str:
    return generate_code("PNR", 8)


def generate_voucher_no() -> str:
    yyyymm = datetime.now(timezone.utc).strftime("%Y%m")
    return generate_code(f"VCH-{yyyymm}", 6)


def to_csv(rows: Iterable[dict[str, Any]], fieldnames: list[str]) -> str:
    buff = io.StringIO()
    writer = csv.DictWriter(buff, fieldnames=fieldnames)
    writer.writeheader()
    for r in rows:
        writer.writerow({k: r.get(k, "") for k in fieldnames})
    return buff.getvalue()


def safe_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default


def safe_int(v: Any, default: int = 0) -> int:
    try:
        return int(v)
    except Exception:
        return default


def date_range_yyyy_mm_dd(start: str, end: str) -> list[str]:
    """Inclusive start, exclusive end (accommodation nights)."""
    from datetime import date, timedelta

    s = date.fromisoformat(start)
    e = date.fromisoformat(end)
    out: list[str] = []
    cur = s
    while cur < e:
        out.append(cur.isoformat())
        cur += timedelta(days=1)
    return out


def require_env(name: str) -> str:
    v = os.environ.get(name)
    if not v:
        raise RuntimeError(f"Missing env var {name}")
    return v
