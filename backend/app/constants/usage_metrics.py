from __future__ import annotations


class UsageMetric:
  RESERVATION_CREATED = "reservation.created"
  REPORT_GENERATED = "report.generated"
  EXPORT_GENERATED = "export.generated"
  INTEGRATION_CALL = "integration.call"

  # Legacy compat — existing quota/usage flows still rely on this metric.
  B2B_MATCH_REQUEST = "b2b.match_request"


ALL_METRICS = {
  UsageMetric.RESERVATION_CREATED,
  UsageMetric.REPORT_GENERATED,
  UsageMetric.EXPORT_GENERATED,
  UsageMetric.INTEGRATION_CALL,
}

LEGACY_COMPAT_METRICS = {
  UsageMetric.B2B_MATCH_REQUEST,
}

VALID_USAGE_METRICS = ALL_METRICS | LEGACY_COMPAT_METRICS
