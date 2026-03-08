import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Activity, RefreshCw } from "lucide-react";
import { Button } from "../ui/button";
import { api } from "../../lib/api";
import { buildUsageTrendData, getUsageMetricEntries } from "../../lib/usage";
import { UsageMetricTiles } from "../usage/UsageMetricTiles";
import { UsageTrendChart } from "../usage/UsageTrendChart";

export const AdminTenantUsageOverview = ({ tenantId }) => {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);

  const loadSummary = useCallback(async () => {
    if (!tenantId) return;
    setLoading(true);
    try {
      const res = await api.get(`/admin/billing/tenants/${tenantId}/usage?days=30`);
      setSummary(res.data);
    } catch {
      setSummary(null);
    } finally {
      setLoading(false);
    }
  }, [tenantId]);

  useEffect(() => { loadSummary(); }, [loadSummary]);

  const entries = useMemo(() => getUsageMetricEntries(summary), [summary]);
  const trendData = useMemo(() => buildUsageTrendData(summary), [summary]);

  if (loading) {
    return <div className="rounded-lg border bg-card p-4 text-sm text-muted-foreground" data-testid="admin-tenant-usage-loading">Usage yükleniyor...</div>;
  }

  if (!summary) {
    return <div className="rounded-lg border border-dashed bg-muted/10 p-4 text-sm text-muted-foreground" data-testid="admin-tenant-usage-empty">Tenant usage verisi alınamadı.</div>;
  }

  return (
    <div className="space-y-4 rounded-3xl border bg-card/90 p-4" data-testid="admin-tenant-usage-overview">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 text-sm font-semibold text-foreground">
            <Activity className="h-4 w-4 text-primary" />
            <span data-testid="admin-tenant-usage-title">Usage Overview</span>
          </div>
          <p className="mt-1 text-sm text-muted-foreground" data-testid="admin-tenant-usage-meta">
            Plan: {summary.plan_label || summary.plan || "—"} · Dönem: {summary.period || "—"} · Kaynak: {summary.totals_source || "—"}
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={loadSummary} data-testid="admin-tenant-usage-refresh-button">
          <RefreshCw className="mr-1.5 h-3.5 w-3.5" />Yenile
        </Button>
      </div>

      <UsageMetricTiles entries={entries} testIdPrefix="admin-tenant-usage" />
      <UsageTrendChart data={trendData} testId="admin-tenant-usage-trend-chart" title="Last 30 days" />
    </div>
  );
};