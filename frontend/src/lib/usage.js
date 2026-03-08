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

export const WARNING_LEVEL_META = {
  normal: {
    badgeClassName: "bg-muted text-muted-foreground border-border",
    messageClassName: "text-muted-foreground",
  },
  warning: {
    badgeClassName: "bg-amber-500/10 text-amber-700 border-amber-500/20",
    messageClassName: "text-amber-700",
  },
  critical: {
    badgeClassName: "bg-orange-500/10 text-orange-700 border-orange-500/20",
    messageClassName: "text-orange-700",
  },
  limit_reached: {
    badgeClassName: "bg-destructive/10 text-destructive border-destructive/20",
    messageClassName: "text-destructive",
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
    const warningLevel = raw.warning_level || "normal";
    const warningMeta = WARNING_LEVEL_META[warningLevel] || WARNING_LEVEL_META.normal;

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
      warningLevel,
      warningMessage: raw.warning_message || null,
      upgradeRecommended: Boolean(raw.upgrade_recommended),
      ctaHref: raw.cta_href || "/pricing",
      ctaLabel: raw.cta_label || "Planları Gör",
      color: meta.color,
      trackClassName: meta.trackClassName,
      barClassName: meta.barClassName,
      badgeClassName: meta.badgeClassName,
      warningBadgeClassName: warningMeta.badgeClassName,
      warningMessageClassName: warningMeta.messageClassName,
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

export function getTrialConversion(summary) {
  return summary?.trial_conversion || {
    is_trial: false,
    show: false,
    usage_ratio: 0,
    recommended_plan: null,
    message: null,
    cta_href: null,
    cta_label: null,
  };
}