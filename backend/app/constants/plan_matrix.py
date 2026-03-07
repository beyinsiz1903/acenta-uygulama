from __future__ import annotations

PLAN_MATRIX = {
  "starter": {
    "label": "Starter",
    "description": "Yeni başlayan acentalar için temel operasyon paketi.",
    "features": [
      "dashboard",
      "reservations",
      "crm",
      "inventory",
      "reports",
    ],
    "limits": {
      "users.active": 2,
      "reservations.monthly": 100,
    },
    "quotas": {
      "reservation.created": 100,
      "report.generated": 25,
      "export.generated": 10,
      "integration.call": 500,
      "b2b.match_request": 25,
    },
  },
  "pro": {
    "label": "Pro",
    "description": "Büyüyen ekipler için satış ve otomasyon odaklı paket.",
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
    "limits": {
      "users.active": 10,
      "reservations.monthly": None,
    },
    "quotas": {
      "reservation.created": None,
      "report.generated": 250,
      "export.generated": 100,
      "integration.call": 5000,
      "b2b.match_request": 100,
    },
  },
  "enterprise": {
    "label": "Enterprise",
    "description": "Kurumsal ekipler için sınırsız kapasite ve genişletilmiş modüller.",
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
    "limits": {
      "users.active": None,
      "reservations.monthly": None,
    },
    "quotas": {
      "reservation.created": None,
      "report.generated": None,
      "export.generated": None,
      "integration.call": None,
      "b2b.match_request": None,
    },
  },
}

VALID_PLANS = list(PLAN_MATRIX.keys())
DEFAULT_PLAN = "starter"

_all = set()
for p in PLAN_MATRIX.values():
  _all.update(p["features"])
ALL_PLAN_FEATURE_KEYS = sorted(_all)
