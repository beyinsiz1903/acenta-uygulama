from __future__ import annotations

PLAN_MATRIX = {
  "starter": {
    "label": "Starter",
    "features": [
      "dashboard",
      "reservations",
      "crm",
      "inventory",
      "reports",
    ],
  },
  "pro": {
    "label": "Pro",
    "features": [
      "dashboard",
      "reservations",
      "crm",
      "inventory",
      "reports",
      "accounting",
      "webpos",
      "partners",
    ],
  },
  "enterprise": {
    "label": "Enterprise",
    "features": [
      "dashboard",
      "reservations",
      "crm",
      "inventory",
      "reports",
      "accounting",
      "webpos",
      "partners",
      "b2b",
      "ops",
    ],
  },
}

VALID_PLANS = list(PLAN_MATRIX.keys())
DEFAULT_PLAN = "starter"

_all = set()
for p in PLAN_MATRIX.values():
  _all.update(p["features"])
ALL_PLAN_FEATURE_KEYS = sorted(_all)
