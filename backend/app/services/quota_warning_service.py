from __future__ import annotations

from typing import Any, Dict, Optional

from app.constants.usage_metrics import UsageMetric


METRIC_UNITS = {
  UsageMetric.RESERVATION_CREATED: "rezervasyon",
  UsageMetric.REPORT_GENERATED: "rapor",
  UsageMetric.EXPORT_GENERATED: "export",
  UsageMetric.INTEGRATION_CALL: "entegrasyon çağrısı",
  UsageMetric.B2B_MATCH_REQUEST: "B2B talebi",
}


def calculate_warning_level(used: int, limit: Optional[int]) -> str:
  if limit in (None, 0):
    return "normal"

  ratio = used / limit
  if ratio >= 1.0:
    return "limit_reached"
  if ratio >= 0.85:
    return "critical"
  if ratio >= 0.70:
    return "warning"
  return "normal"


def recommend_plan(usage_ratio: float) -> str:
  if usage_ratio < 0.4:
    return "Starter"
  if usage_ratio < 0.8:
    return "Pro"
  return "Enterprise"


def generate_warning_message(metric: str, used: int, limit: Optional[int], warning_level: str) -> Optional[str]:
  if limit is None:
    return None

  unit = METRIC_UNITS.get(metric, "kullanım")
  remaining = max(0, limit - used)

  if warning_level == "limit_reached":
    return f"{unit.capitalize()} limitiniz doldu. Planınızı yükselterek devam edebilirsiniz."
  if warning_level == "critical":
    return f"Limitinize sadece {remaining} {unit} kaldı. Planınızı yükseltmeyi düşünebilirsiniz."
  if warning_level == "warning":
    return f"Limitinize {remaining} {unit} kaldı. Limitinize yaklaşıyorsunuz."
  return f"Limitinize {remaining} {unit} kaldı."


def should_recommend_upgrade(warning_level: str, *, is_trial: bool = False) -> bool:
  return warning_level in {"critical", "limit_reached"}


def build_metric_warning_payload(
  *,
  metric: str,
  used: int,
  limit: Optional[int],
  is_trial: bool = False,
) -> Dict[str, Any]:
  warning_level = calculate_warning_level(used, limit)
  return {
    "warning_level": warning_level,
    "warning_message": generate_warning_message(metric, used, limit, warning_level),
    "upgrade_recommended": should_recommend_upgrade(warning_level, is_trial=is_trial),
    "cta_href": "/pricing" if should_recommend_upgrade(warning_level, is_trial=is_trial) else None,
    "cta_label": "Planları Gör" if should_recommend_upgrade(warning_level, is_trial=is_trial) else None,
  }


def build_trial_conversion_payload(*, usage_ratio: float, is_trial: bool) -> Dict[str, Any]:
  if not is_trial or usage_ratio <= 0:
    return {
      "is_trial": is_trial,
      "show": False,
      "usage_ratio": 0,
      "recommended_plan": None,
      "message": None,
      "cta_href": None,
      "cta_label": None,
    }

  recommended_plan = recommend_plan(usage_ratio)
  percent = round(usage_ratio * 100)
  return {
    "is_trial": True,
    "show": True,
    "usage_ratio": round(usage_ratio, 4),
    "recommended_plan": recommended_plan,
    "message": f"Trial kullanımınızın %{percent}'ini kullandınız. Bu kullanım için önerilen plan: {recommended_plan}",
    "cta_href": "/pricing",
    "cta_label": "Planları Gör",
  }