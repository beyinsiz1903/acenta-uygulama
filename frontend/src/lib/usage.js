export const PRIMARY_USAGE_METRICS = [
  "reservation.created",
  "report.generated",
  "export.generated",
];

export const USAGE_METRIC_META = {
  "reservation.created": {
    label: "Reservations",
    shortLabel: "Reservations",
    color: "#0f766e",
    trackClassName: "bg-emerald-500/15",
    barClassName: "bg-emerald-500",
    badgeClassName: "bg-emerald-500/10 text-emerald-700 border-emerald-500/20",
  },
  "report.generated": {
    label: "Reports",
    shortLabel: "Reports",
    color: "#2563eb",
    trackClassName: "bg-blue-500/15",
    barClassName: "bg-blue-500",
    badgeClassName: "bg-blue-500/10 text-blue-700 border-blue-500/20",
  },
  "export.generated": {
    label: "Exports",
    shortLabel: "Exports",
    color: "#ea580c",
    trackClassName: "bg-orange-500/15",
    barClassName: "bg-orange-500",
    badgeClassName: "bg-orange-500/10 text-orange-700 border-orange-500/20",
  },
  "integration.call": {
    label: "Integrations",
    shortLabel: "Integrations",
    color: "#7c3aed",
    trackClassName: "bg-violet-500/15",
    barClassName: "bg-violet-500",
    badgeClassName: "bg-violet-500/10 text-violet-700 border-violet-500/20",
  },
};

export function formatUsageLimit(limit) {
  if (limit === null || limit === undefined) return "Sınırsız";
  return Number(limit).toLocaleString("tr-TR");
}

export function getUsageMetricEntries(summary, metricKeys = PRIMARY_USAGE_METRICS) {
  return metricKeys.map((metric) => {
    const raw = summary?.metrics?.[metric] || {};
    const meta = USAGE_METRIC_META[metric] || {};

    return {
      key: metric,
      testId: metric.replace(/\./g, "-"),
      label: raw.label || meta.label || metric,
      shortLabel: meta.shortLabel || raw.label || metric,
      used: Number(raw.used || 0),
      limit: raw.limit ?? raw.quota ?? null,
      remaining: raw.remaining ?? null,
      percent: Number(raw.percent || 0),
      exceeded: Boolean(raw.exceeded),
      color: meta.color,
      trackClassName: meta.trackClassName,
      barClassName: meta.barClassName,
      badgeClassName: meta.badgeClassName,
    };
  });
}

export function buildUsageTrendData(summary) {
  return (summary?.trend?.daily || []).map((row) => ({
    date: row.date,
    reservationCreated: Number(row["reservation.created"] || 0),
    reportGenerated: Number(row["report.generated"] || 0),
    exportGenerated: Number(row["export.generated"] || 0),
  }));
}