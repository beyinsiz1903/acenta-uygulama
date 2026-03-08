from __future__ import annotations

PLAN_MATRIX = {
  "trial": {
    "label": "Trial",
    "description": "14 gün boyunca tüm özellikleri deneyin, kullanım alışkanlığınızı görün.",
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
      "users.active": 2,
      "reservations.monthly": 100,
    },
    "quotas": {
      "reservation.created": 100,
      "report.generated": 20,
      "export.generated": 10,
      "integration.call": 250,
      "b2b.match_request": 25,
    },
    "pricing": {
      "monthly": 0,
      "currency": "TRY",
      "label": "14 Gün Ücretsiz",
    },
    "audience": "Ürünü gerçek akışta denemek isteyen acentalar",
    "is_public": False,
    "is_popular": False,
  },
  "starter": {
    "label": "Starter",
    "description": "Excel kullanan küçük acentalar için sıcak başlangıç paketi.",
    "features": [
      "dashboard",
      "reservations",
      "crm",
      "inventory",
      "reports",
    ],
    "limits": {
      "users.active": 3,
      "reservations.monthly": 100,
    },
    "quotas": {
      "reservation.created": 100,
      "report.generated": 30,
      "export.generated": 20,
      "integration.call": 1000,
      "b2b.match_request": 25,
    },
    "pricing": {
      "monthly": 990,
      "currency": "TRY",
    },
    "audience": "Küçük acenteler",
    "is_public": True,
    "is_popular": False,
  },
  "pro": {
    "label": "Pro",
    "description": "Büyüyen acenteler için satış ve operasyonu tek panelde toplayan ana plan.",
    "features": [
      "dashboard",
      "reservations",
      "crm",
      "inventory",
      "reports",
      "accounting",
      "webpos",
      "partners",
      "ops",
    ],
    "limits": {
      "users.active": 10,
      "reservations.monthly": 500,
    },
    "quotas": {
      "reservation.created": 500,
      "report.generated": 250,
      "export.generated": 100,
      "integration.call": 5000,
      "b2b.match_request": 100,
    },
    "pricing": {
      "monthly": 2490,
      "currency": "TRY",
    },
    "audience": "Büyüyen acenteler",
    "is_public": True,
    "is_popular": True,
  },
  "enterprise": {
    "label": "Enterprise",
    "description": "Büyük operasyonlar için sınırsız kapasite, özel entegrasyon ve white-label destek.",
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
    "pricing": {
      "monthly": 6990,
      "currency": "TRY",
    },
    "audience": "Büyük operasyonlar",
    "is_public": True,
    "is_popular": False,
  },
}

VALID_PLANS = list(PLAN_MATRIX.keys())
DEFAULT_PLAN = "starter"

_all = set()
for p in PLAN_MATRIX.values():
  _all.update(p["features"])
ALL_PLAN_FEATURE_KEYS = sorted(_all)
