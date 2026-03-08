from app.constants.usage_metrics import UsageMetric
from app.services.quota_warning_service import (
  build_metric_warning_payload,
  build_trial_conversion_payload,
  calculate_warning_level,
  recommend_plan,
)


def test_calculate_warning_level_normal() -> None:
  assert calculate_warning_level(50, 100) == "normal"


def test_calculate_warning_level_warning() -> None:
  assert calculate_warning_level(70, 100) == "warning"


def test_calculate_warning_level_critical() -> None:
  assert calculate_warning_level(85, 100) == "critical"


def test_calculate_warning_level_limit_reached() -> None:
  assert calculate_warning_level(100, 100) == "limit_reached"


def test_recommend_plan_thresholds() -> None:
  assert recommend_plan(0.2) == "Starter"
  assert recommend_plan(0.6) == "Pro"
  assert recommend_plan(0.95) == "Enterprise"


def test_metric_warning_payload_for_critical_usage() -> None:
  payload = build_metric_warning_payload(
    metric=UsageMetric.RESERVATION_CREATED,
    used=92,
    limit=100,
  )
  assert payload["warning_level"] == "critical"
  assert payload["upgrade_recommended"] is True
  assert payload["cta_href"] == "/pricing"
  assert "sadece 8 rezervasyon" in str(payload["warning_message"])


def test_trial_conversion_payload() -> None:
  payload = build_trial_conversion_payload(usage_ratio=0.6, is_trial=True)
  assert payload["show"] is True
  assert payload["recommended_plan"] == "Pro"
  assert payload["cta_href"] == "/pricing"