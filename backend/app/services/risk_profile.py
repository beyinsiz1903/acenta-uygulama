from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass
class RiskProfile:
    organization_id: str
    rate_threshold: float = 0.5
    repeat_threshold_7: int = 3
    # v2 fields for no-show based risk
    no_show_rate_threshold: float | None = None
    repeat_no_show_threshold_7: int | None = None
    min_verified_bookings: int = 0
    mode: str = "rate_or_repeat"  # rate_only | repeat_only | rate_or_repeat

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        # organization_id internal, API tarafında ayrıca ihtiyaç yok
        data.pop("organization_id", None)
        return data


async def load_risk_profile(db, org_id: str) -> RiskProfile:
    """Load risk profile for organization or return defaults.

    Tek kaynaktan high-risk tanımlarını okumak için kullanılır.
    """
    doc = await db.risk_profiles.find_one({"organization_id": org_id})
    if not doc:
        # v1: single mode, rate_or_repeat
        return RiskProfile(organization_id=org_id, mode="rate_or_repeat")

    return RiskProfile(
        organization_id=org_id,
        rate_threshold=float(doc.get("rate_threshold", 0.5)),
        repeat_threshold_7=int(doc.get("repeat_threshold_7", 3)),
        mode="rate_or_repeat",
    )


def is_high_risk(rate: float, repeat_7: int, profile: RiskProfile) -> bool:
    """Centralized high-risk decision.

    v1: mode sabit olarak rate_or_repeat, yani rate >= threshold OR repeat >= threshold.
    """
    return rate >= profile.rate_threshold or repeat_7 >= profile.repeat_threshold_7