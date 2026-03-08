import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Activity, RefreshCw } from "lucide-react";
import { Button } from "../ui/button";
import { api } from "../../lib/api";
import { buildUsageTrendData, getUsageMetricEntries } from "../../lib/usage";
import { UsageMetricTiles } from "./UsageMetricTiles";

export const DashboardUsageSummaryCard = () => {
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
  const lastActiveDay = [...trendData].reverse().find((item) => item.reservationCreated || item.reportGenerated || item.exportGenerated)?.date;

  if (loading && !summary) {
    return <section className="rounded-3xl border bg-card/85 p-5 text-sm text-muted-foreground" data-testid="dashboard-usage-summary-loading">Usage snapshot yükleniyor...</section>;
  }

  if (!summary) {
    return <section className="rounded-3xl border border-dashed bg-muted/10 p-5 text-sm text-muted-foreground" data-testid="dashboard-usage-summary-empty">Usage snapshot şu anda alınamıyor.</section>;
  }

  return (
    <section className="rounded-3xl border bg-card/85 p-5 shadow-sm" data-testid="dashboard-usage-summary-card">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 text-sm font-semibold text-foreground">
            <Activity className="h-4 w-4 text-primary" />
            <span data-testid="dashboard-usage-summary-title">Usage snapshot</span>
          </div>
          <p className="mt-1 text-sm text-muted-foreground" data-testid="dashboard-usage-summary-subtitle">
            Plan: {summary?.plan_label || "—"} · Dönem: {summary?.period || "—"}
          </p>
          {lastActiveDay && <p className="mt-1 text-xs text-muted-foreground" data-testid="dashboard-usage-summary-last-active">Son hareket: {lastActiveDay}</p>}
        </div>

        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={loadSummary} data-testid="dashboard-usage-refresh-button">
            <RefreshCw className={`mr-1.5 h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
            Yenile
          </Button>
          <Button asChild size="sm" data-testid="dashboard-usage-open-page-button">
            <Link to="/app/usage">Detaylı görünüm</Link>
          </Button>
        </div>
      </div>

      <div className="mt-4">
        <UsageMetricTiles entries={entries} compact testIdPrefix="dashboard-usage-summary" />
      </div>
    </section>
  );
};