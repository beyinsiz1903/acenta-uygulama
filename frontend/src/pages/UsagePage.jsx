import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Activity, RefreshCw } from "lucide-react";
import { Button } from "../components/ui/button";
import { api } from "../lib/api";
import { buildUsageTrendData, getUsageMetricEntries } from "../lib/usage";
import { UsageMetricTiles } from "../components/usage/UsageMetricTiles";
import { UsageTrendChart } from "../components/usage/UsageTrendChart";

export default function UsagePage() {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);

  const loadSummary = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get("/tenant/usage-summary?days=30");
      setSummary(res.data);
    } catch {
      setSummary(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadSummary(); }, [loadSummary]);

  const entries = useMemo(() => getUsageMetricEntries(summary), [summary]);
  const trendData = useMemo(() => buildUsageTrendData(summary), [summary]);

  if (loading && !summary) {
    return <div className="rounded-3xl border bg-card/85 p-6 text-sm text-muted-foreground" data-testid="usage-page-loading">Usage verisi yükleniyor...</div>;
  }

  if (!summary) {
    return <div className="rounded-3xl border border-dashed bg-muted/10 p-6 text-sm text-muted-foreground" data-testid="usage-page-empty">Usage verisi şu anda alınamıyor.</div>;
  }

  return (
    <div className="space-y-6" data-testid="usage-page">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 text-sm font-semibold uppercase tracking-[0.22em] text-muted-foreground">
            <Activity className="h-4 w-4 text-primary" />
            <span>Usage</span>
          </div>
          <h1 className="mt-2 text-4xl font-semibold tracking-tight text-foreground" data-testid="usage-page-heading">Kullanım görünürlüğü</h1>
          <p className="mt-2 max-w-2xl text-sm text-muted-foreground" data-testid="usage-page-description">
            Reservations, reports ve exports kullanımınızı izleyin; son 30 gün trendini tek ekranda görün.
          </p>
          <p className="mt-2 text-xs text-muted-foreground" data-testid="usage-page-meta">
            Plan: {summary?.plan_label || "—"} · Dönem: {summary?.period || "—"}
          </p>
        </div>

        <Button variant="outline" onClick={loadSummary} data-testid="usage-page-refresh-button">
          <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          Yenile
        </Button>
      </div>

      <UsageMetricTiles entries={entries} testIdPrefix="usage-page" />
      <UsageTrendChart data={trendData} testId="usage-page-trend-chart" title="Last 30 days" />
    </div>
  );
}