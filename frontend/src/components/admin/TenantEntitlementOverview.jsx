import React, { useMemo } from "react";
import { Layers3, Users, CalendarRange, Gauge, Sparkles } from "lucide-react";
import { Badge } from "../ui/badge";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../ui/card";
import { LIMIT_LABELS, USAGE_ALLOWANCE_LABELS, formatEntitlementValue, mapEntitlementEntries } from "../../lib/entitlementLabels";

const primaryMetricConfig = {
  "users.active": { icon: Users, suffix: "" },
  "reservations.monthly": { icon: CalendarRange, suffix: "/ay" },
};

function EntitlementMetricCard({ metricKey, label, value }) {
  const config = primaryMetricConfig[metricKey] || { icon: Gauge, suffix: "" };
  const Icon = config.icon;

  return (
    <div className="rounded-xl border bg-muted/15 p-3" data-testid={`entitlement-metric-${metricKey.replace(/\./g, "-")}`}>
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <Icon className="h-3.5 w-3.5" />
        <span>{label}</span>
      </div>
      <p className="mt-2 text-lg font-semibold text-foreground" data-testid={`entitlement-metric-value-${metricKey.replace(/\./g, "-")}`}>
        {formatEntitlementValue(value, config.suffix)}
      </p>
    </div>
  );
}

export const TenantEntitlementOverview = ({
  planLabel,
  source,
  limits,
  usageAllowances,
  activeFeatureCount,
  addOnCount,
}) => {
  const limitEntries = useMemo(() => mapEntitlementEntries(limits, LIMIT_LABELS), [limits]);
  const usageEntries = useMemo(() => mapEntitlementEntries(usageAllowances, USAGE_ALLOWANCE_LABELS), [usageAllowances]);

  return (
    <Card className="border-border/70 shadow-sm" data-testid="tenant-entitlement-overview-card">
      <CardHeader className="pb-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <CardTitle className="text-base" data-testid="tenant-entitlement-plan-label">{planLabel || "Plan atanmadı"}</CardTitle>
            <CardDescription data-testid="tenant-entitlement-source">Kaynak: {source || "unassigned"}</CardDescription>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="secondary" data-testid="tenant-entitlement-feature-count-badge">
              <Layers3 className="mr-1 h-3 w-3" /> {activeFeatureCount} modül
            </Badge>
            <Badge variant="outline" data-testid="tenant-entitlement-addon-count-badge">
              <Sparkles className="mr-1 h-3 w-3" /> {addOnCount} add-on
            </Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {limitEntries.length === 0 ? (
            <div className="rounded-xl border border-dashed bg-muted/10 px-4 py-5 text-sm text-muted-foreground" data-testid="tenant-entitlement-empty-state">
              Bu tenant için henüz limit projeksiyonu bulunmuyor.
            </div>
          ) : (
            limitEntries.map((item) => (
              <EntitlementMetricCard key={item.key} metricKey={item.key} label={item.label} value={item.value} />
            ))
          )}
        </div>

        <div className="rounded-xl border bg-background/60 p-4" data-testid="tenant-entitlement-usage-allowances">
          <div className="mb-3 flex items-center gap-2 text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground">
            <Gauge className="h-3.5 w-3.5" />
            Usage Allowances
          </div>
          {usageEntries.length === 0 ? (
            <p className="text-sm text-muted-foreground" data-testid="tenant-entitlement-usage-empty">Henüz tanımlı usage allowance yok.</p>
          ) : (
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              {usageEntries.map((item) => (
                <div
                  key={item.key}
                  className="flex items-center justify-between rounded-lg border border-border/70 bg-muted/10 px-3 py-2 text-sm"
                  data-testid={`tenant-usage-allowance-${item.key.replace(/\./g, "-")}`}
                >
                  <span className="text-muted-foreground">{item.label}</span>
                  <span className="font-medium text-foreground">{formatEntitlementValue(item.value, "/ay")}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
};
