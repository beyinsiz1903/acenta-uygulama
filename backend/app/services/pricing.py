from __future__ import annotations

from typing import Any, Optional

from app.utils import safe_float


def calc_price_for_date(rate_plan: dict[str, Any], date_str: str) -> float:
    base = safe_float(rate_plan.get("base_price"), 0.0)

    # Seasons override base if within range
    for season in rate_plan.get("seasons") or []:
        start = season.get("start")
        end = season.get("end")
        if start and end and start <= date_str <= end:
            base = safe_float(season.get("price"), base)

    # Actions apply on top of base
    for action in rate_plan.get("actions") or []:
        start = action.get("start")
        end = action.get("end")
        if start and end and start <= date_str <= end:
            t = action.get("type")
            val = safe_float(action.get("value"), 0.0)
            if t == "percent":
                base = base * (1.0 - val / 100.0)
            elif t == "fixed":
                base = max(0.0, base - val)

    return round(base, 2)
