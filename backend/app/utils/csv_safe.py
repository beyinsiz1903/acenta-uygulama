from __future__ import annotations

from typing import Iterable, List

import csv
import io


_DANGEROUS_PREFIXES = ("=", "+", "-", "@")


def _sanitize_cell(value: object) -> str:
    """Return a CSV-safe string representation.

    Prevents CSV/Excel injection by prefixing cells that start with
    formula-like characters. Keep this intentionally simple and
    deterministic for statements/exports.
    """

    s = "" if value is None else str(value)
    if not s:
        return s

    if s[0] in _DANGEROUS_PREFIXES:
        return f"'{s}"
    return s


def to_safe_csv(rows: Iterable[dict[str, object]], fieldnames: List[str]) -> str:
    """Render rows to CSV with basic injection guards.

    All cells are passed through _sanitize_cell before writing.
    """

    buff = io.StringIO()
    writer = csv.DictWriter(buff, fieldnames=fieldnames)
    writer.writeheader()

    for row in rows:
        safe_row = {k: _sanitize_cell(row.get(k, "")) for k in fieldnames}
        writer.writerow(safe_row)

    return buff.getvalue()
