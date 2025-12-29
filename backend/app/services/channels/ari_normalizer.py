from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, Tuple




def _pick(d: dict, *keys, default=None):
    """Return the first present, non-None key from mapping `d`.

    This makes the normalizer tolerant to different provider field names
    (roomTypeId vs room_type_id, ratePlanId vs rate_plan_id, etc.).
    """

    if not isinstance(d, dict):
        return default
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return default


def _to_int(x):
    try:
        if x is None or x == "":
            return None
        return int(x)
    except Exception:  # noqa: BLE001
        return None


def _to_float(x):
    try:
        if x is None or x == "":
            return None
        return float(x)
    except Exception:  # noqa: BLE001
        return None


def _to_bool(x):
    if x is None:
        return None
    if isinstance(x, bool):
        return x
    if isinstance(x, (int, float)):
        try:
            return bool(int(x))
        except Exception:  # noqa: BLE001
            return None
    s = str(x).strip().lower()
    if s in {"true", "1", "yes", "y"}:
        return True
    if s in {"false", "0", "no", "n"}:
        return False
    return None

def _date_range(from_date: date, to_date: date):
    """Yield all dates between from_date and to_date inclusive."""
    d = from_date
    while d <= to_date:
        yield d
        d += timedelta(days=1)


def _build_mapping_dict(mappings_doc: Dict[str, Any]) -> Tuple[Dict[str, str], Dict[str, str]]:
    """Build channel_id -> PMS id dicts for room types and rate plans.

    Only active mappings are included.
    """

    room_map: Dict[str, str] = {}
    for m in mappings_doc.get("room_type_mappings") or []:
        if not m.get("active", True):
            continue
        ch = str(m.get("channel_room_type_id") or "").strip()
        pms = str(m.get("pms_room_type_id") or "").strip()
        if ch and pms:
            room_map[ch] = pms

    rate_map: Dict[str, str] = {}
    for m in mappings_doc.get("rate_plan_mappings") or []:
        if not m.get("active", True):
            continue
        ch = str(m.get("channel_rate_plan_id") or "").strip()
        pms = str(m.get("pms_rate_plan_id") or "").strip()
        if ch and pms:
            rate_map[ch] = pms

    return room_map, rate_map


async def normalize_exely_ari(
    *,
    raw: Dict[str, Any],
    mappings: Dict[str, Any],
    from_date: date,
    to_date: date,
) -> Tuple[Dict[str, Any], Dict[str, int]]:
    """Normalize Exely ARI payload into a canonical structure.

    Returns (canonical_ari, stats) where:
      canonical_ari = {
        "roomTypes": {pms_room_type_id: {"dates": {"YYYY-MM-DD": {..}}}},
        "ratePlans": {pms_rate_plan_id: {"dates": {"YYYY-MM-DD": {..}}}},
      }

      stats = {
        "unmapped_rooms": int,
        "unmapped_rates": int,
        "parsed_items": int,
        "parsed_days": int,
      }

    The function is deliberately tolerant about raw payload shape. It looks for
    common keys like "availability"/"availabilities" and "rates"/"ratePlans".
    """

    room_map, rate_map = _build_mapping_dict(mappings)

    canonical: Dict[str, Any] = {"roomTypes": {}, "ratePlans": {}}
    stats: Dict[str, int] = {
        "unmapped_rooms": 0,
        "unmapped_rates": 0,
        "parsed_items": 0,
        "parsed_days": 0,
    }

    availability_items = (
        raw.get("availability")
        or raw.get("availabilities")
        or []
    )
    rate_items = raw.get("rates") or raw.get("ratePlans") or []

    def _put_room(pms_room_id: str, day: date, available=None, stop_sell=None) -> None:
        rt = canonical["roomTypes"].setdefault(pms_room_id, {"dates": {}})
        payload: Dict[str, Any] = {}
        if available is not None:
            payload["available"] = available
        if stop_sell is not None:
            payload["stop_sell"] = stop_sell
        if not payload:
            return
        rt["dates"][day.isoformat()] = payload

    def _put_rate(pms_rate_id: str, day: date, price=None, currency=None, min_stay=None) -> None:
        rp = canonical["ratePlans"].setdefault(pms_rate_id, {"dates": {}})
        payload: Dict[str, Any] = {}
        if price is not None:
            payload["price"] = price
        if currency is not None:
            payload["currency"] = currency
        if min_stay is not None:
            payload["min_stay"] = min_stay
        if not payload:
            return
        rp["dates"][day.isoformat()] = payload

    # Availability parse
    for it in availability_items:
        # Channel room type id alias'ları (room_type_id, roomTypeId, roomType, ...)
        ch_id = str(
            _pick(
                it,
                "room_type_id",
                "channel_room_type_id",
                "roomTypeId",
                "roomTypeID",
                "roomType",
                "room_type",
            )
            or ""
        ).strip()
        if not ch_id or ch_id not in room_map:
            if ch_id:
                stats["unmapped_rooms"] += 1
            continue

        pms_id = room_map[ch_id]
        # Tarih alias'ları
        day_str = str(_pick(it, "date", "day", "stayDate", "stay_date") or "").strip()
        try:
            day = date.fromisoformat(day_str)
        except Exception:  # noqa: BLE001
            continue

        if day < from_date or day > to_date:
            continue

        available_raw = _pick(
            it,
            "available",
            "availability",
            "count",
            "roomsAvailable",
            "rooms_available",
        )
        stop_sell_raw = _pick(
            it,
            "stop_sell",
            "stopSell",
            "stop_sale",
            "stopSale",
        )

        available = _to_int(available_raw)
        stop_sell = _to_bool(stop_sell_raw)

        _put_room(pms_id, day, available=available, stop_sell=stop_sell)
        stats["parsed_items"] += 1

    # Rate parse
    for it in rate_items:
        ch_id = str(
            _pick(
                it,
                "rate_plan_id",
                "channel_rate_plan_id",
                "ratePlanId",
                "ratePlanID",
                "ratePlan",
                "rate_plan",
            )
            or ""
        ).strip()
        if not ch_id or ch_id not in rate_map:
            if ch_id:
                stats["unmapped_rates"] += 1
            continue

        pms_id = rate_map[ch_id]
        day_str = str(_pick(it, "date", "day", "stayDate", "stay_date") or "").strip()
        try:
            day = date.fromisoformat(day_str)
        except Exception:  # noqa: BLE001
            continue

        if day < from_date or day > to_date:
            continue

        price_raw = _pick(it, "price", "amount", "value", "rate", "dailyRate", "daily_rate")
        currency = _pick(it, "currency", "currencyCode", "currency_code")
        min_stay_raw = _pick(it, "min_stay", "minStay", "minNights", "min_nights")

        price = _to_float(price_raw)
        min_stay = _to_int(min_stay_raw)

        _put_rate(pms_id, day, price=price, currency=currency, min_stay=min_stay)
        stats["parsed_items"] += 1

    stats["parsed_days"] = sum(1 for _ in _date_range(from_date, to_date))
    return canonical, stats
