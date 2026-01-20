import React, { useEffect, useMemo, useState } from "react";
import { api, apiErrorMessage } from "../lib/api";
import { useToast } from "../hooks/use-toast";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";

function formatPercent(value) {
  if (value == null || Number.isNaN(Number(value))) return "—";
  const n = Number(value);
  return `${Math.round(n * 100)}%`;
}

function formatDate(dateStr) {
  if (!dateStr) return "—";
  const d = new Date(dateStr);
  if (Number.isNaN(d.getTime())) return dateStr;
  return d.toISOString().slice(0, 10);
}

function computeKpi(deltaMetric) {
  if (!deltaMetric) return { startLabel: "—", endLabel: "—", changeLabel: "—" };
  const { start, end, pct_change: pctChange, direction } = deltaMetric;
  const startLabel = formatPercent(start);
  const endLabel = formatPercent(end);
  let changeLabel = "—";
  if (pctChange == null) {
    changeLabel = "n/a";
  } else {
    const n = Number(pctChange);
    const sign = n > 0 ? "+" : "";
    changeLabel = `${sign}${Math.round(n)}%`;
  }
  return { startLabel, endLabel, changeLabel, direction };
}

function TrendLineChart({ points }) {
  if (!points || points.length === 0) {
    return (
      <div
        className="flex h-48 items-center justify-center text-sm text-muted-foreground"
        data-testid="match-risk-trends-chart"
      >
        No snapshots yet. Run a snapshot to start tracking trends.
      </div>
    );
  }

  const values1 = points.map((p) => Number(p.high_risk_rate || 0));
  const values2 = points.map((p) => Number(p.verified_share_avg || 0));
  const allValues = [...values1, ...values2];
  const maxVal = Math.max(0, ...allValues, 1); // avoid 0-height chart

  const width = 600;
  const height = 200;
  const paddingLeft = 24;
  const paddingRight = 8;
  const paddingTop = 16;
  const paddingBottom = 24;

  const innerWidth = width - paddingLeft - paddingRight;
  const innerHeight = height - paddingTop - paddingBottom;

  const xForIndex = (idx) => {
    if (points.length === 1) return paddingLeft + innerWidth / 2;
    const t = idx / (points.length - 1);
    return paddingLeft + t * innerWidth;
  };

  const yForValue = (v) => {
    const n = typeof v === "number" ? v : Number(v || 0);
    const ratio = n / maxVal;
    return paddingTop + (1 - ratio) * innerHeight;
  };

  const buildPath = (vals) => {
    return vals
      .map((v, idx) => {
        const x = xForIndex(idx);
        const y = yForValue(v);
        return `${idx === 0 ? "M" : "L"}${x},${y}`;
      })
      .join(" ");
  };

  const path1 = buildPath(values1);
  const path2 = buildPath(values2);

  return (
    <div data-testid="match-risk-trends-chart" className="w-full overflow-x-auto">
      <svg
        width={width}
        height={height}
        className="max-w-full"
        role="img"
        aria-label="Match risk trend chart"
      >
        {/* Y axis baseline */}
        <line
          x1={paddingLeft}
          y1={paddingTop + innerHeight}
          x2={paddingLeft + innerWidth}
          y2={paddingTop + innerHeight}
          stroke="#e5e7eb"
          strokeWidth="1"
        />

        {/* 0%, 50%, 100% grid lines */}
        {[0, 0.5, 1].map((ratio) => {
          const y = paddingTop + (1 - ratio) * innerHeight;
          return (
            <g key={ratio}>
              <line
                x1={paddingLeft}
                y1={y}
                x2={paddingLeft + innerWidth}
                y2={y}
                stroke="#e5e7eb"
                strokeWidth="0.5"
                strokeDasharray="4 4"
              />
              <text
                x={4}
                y={y + 4}
                fontSize="10"
                fill="#9ca3af"
              >
                {Math.round(ratio * 100)}%
              </text>
            </g>
          );
        })}

        {/* Lines */}
        <path d={path1} fill="none" stroke="#ef4444" strokeWidth="2" />
        <path d={path2} fill="none" stroke="#3b82f6" strokeWidth="2" />

        {/* Points */}
        {points.map((p, idx) => {
          const x = xForIndex(idx);
          return (
            <g key={idx}>
              <circle
                cx={x}
                cy={yForValue(values1[idx])}
                r={3}
                fill="#ef4444"
              />
              <circle
                cx={x}
                cy={yForValue(values2[idx])}
                r={3}
                fill="#3b82f6"
              />
            </g>
          );
        })}

        {/* X labels (dates) */}
        {points.map((p, idx) => {
          const x = xForIndex(idx);
          const label = formatDate(p.generated_at);
          return (
            <text
              key={idx}
              x={x}
              y={height - 6}
              fontSize="10"
              fill="#6b7280"
              textAnchor="middle"
            >
              {label}
            </text>
          );
        })}

        {/* Legend */}
        <g transform={`translate(${paddingLeft}, ${paddingTop})`}>
          <rect x={0} y={0} width={10} height={2} fill="#ef4444" />
          <text x={16} y={4} fontSize="11" fill="#4b5563">
            High risk rate
          </text>
          <rect x={120} y={0} width={10} height={2} fill="#3b82f6" />
          <text x={136} y={4} fontSize="11" fill="#4b5563">
            Verified share
          </text>
        </g>
      </svg>
    </div>
  );
}

export default function AdminMatchRiskTrendsPage() {
  const { toast } = useToast();
  const [points, setPoints] = useState([]);
  const [delta, setDelta] = useState(null);
  const [limit, setLimit] = useState(30);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function load(nextLimit) {
    const effectiveLimit = nextLimit || limit;
    setLoading(true);
    setError("");
    try {
      const res = await api.get(
        `/admin/risk-snapshots/trend?snapshot_key=match_risk_daily&limit=${effectiveLimit}`
      );
      setPoints(res.data?.points || []);
      setDelta(res.data?.delta || null);
    } catch (e) {
      const msg = apiErrorMessage ? apiErrorMessage(e) : e?.message || "Bir hata oluştu";
      setError(msg);
      toast({
        title: "Failed to load trends",
        description: msg,
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load(limit);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const kpiHighRisk = useMemo(
    () => (delta ? computeKpi(delta.high_risk_rate) : null),
    [delta]
  );
  const kpiVerifiedShare = useMemo(
    () => (delta ? computeKpi(delta.verified_share_avg) : null),
    [delta]
  );

  const hasDelta = Boolean(delta && points && points.length >= 2);

  return (
    <div className="p-4 md:p-6" data-testid="match-risk-trends-page">
      <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-3 mb-4">
        <div>
          <div className="text-xl font-semibold">Match Risk Trendleri</div>
          <div className="text-sm text-muted-foreground">
            Günlük snapshot&apos;lar üzerinden yüksek risk oranı (high-risk rate) ve verified share trendini izleyin.
          </div>
        </div>

        <div className="flex items-center gap-2">
          <label className="text-xs text-muted-foreground" htmlFor="match-risk-trends-limit">
            Limit
          </label>
          <select
            id="match-risk-trends-limit"
            data-testid="match-risk-trends-limit"
            className="h-8 rounded-md border bg-background px-2 text-xs"
            value={limit}
            onChange={(e) => {
              const next = Number(e.target.value) || 30;
              setLimit(next);
              void load(next);
            }}
            disabled={loading}
          >
            {[7, 14, 30, 90].map((opt) => (
              <option key={opt} value={opt}>
                {opt}g
              </option>
            ))}
          </select>

          <Button
            type="button"
            size="sm"
            variant="outline"
            data-testid="match-risk-trends-download-exec-pdf"
            onClick={() => {
              try {
                const url = "/api/admin/reports/match-risk/executive-summary.pdf";
                window.open(url, "_blank");
              } catch (e) {
                const msg = e?.message || "PDF indirilemiyor";
                toast({
                  title: "Failed to download executive report",
                  description: msg,
                  variant: "destructive",
                });
              }
            }}
          >
            Download Executive PDF
          </Button>
        </div>
      </div>

      {error ? (
        <div className="mb-4 rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
          {error}
        </div>
      ) : null}

      {/* KPI Cards */}
      {hasDelta ? (
        <div className="mb-4 grid grid-cols-1 sm:grid-cols-2 gap-3">
          <Card data-testid="match-risk-trends-kpi-high-risk-rate">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">High risk rate</CardTitle>
            </CardHeader>
            <CardContent className="pt-0 text-sm">
              <div className="flex items-baseline gap-2">
                <div className="text-2xl font-semibold">
                  {kpiHighRisk ? kpiHighRisk.endLabel : "—"}
                </div>
                <div className="text-xs text-muted-foreground">
                  {kpiHighRisk ? `(${kpiHighRisk.startLabel} → ${kpiHighRisk.endLabel})` : ""}
                </div>
              </div>
              <div className="mt-1 text-xs">
                {kpiHighRisk ? (
                  <span
                    className={
                      kpiHighRisk.direction === "up"
                        ? "text-red-600"
                        : kpiHighRisk.direction === "down"
                        ? "text-emerald-600"
                        : "text-muted-foreground"
                    }
                  >
                    {kpiHighRisk.changeLabel === "n/a"
                      ? "Değişim: n/a"
                      : `Değişim: ${kpiHighRisk.changeLabel}`}
                  </span>
                ) : (
                  <span className="text-muted-foreground">Not enough snapshots to compute change.</span>
                )}
              </div>
            </CardContent>
          </Card>

          <Card data-testid="match-risk-trends-kpi-verified-share">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">Verified share avg</CardTitle>
            </CardHeader>
            <CardContent className="pt-0 text-sm">
              <div className="flex items-baseline gap-2">
                <div className="text-2xl font-semibold">
                  {kpiVerifiedShare ? kpiVerifiedShare.endLabel : "—"}
                </div>
                <div className="text-xs text-muted-foreground">
                  {kpiVerifiedShare
                    ? `(${kpiVerifiedShare.startLabel} → ${kpiVerifiedShare.endLabel})`
                    : ""}
                </div>
              </div>
              <div className="mt-1 text-xs">
                {kpiVerifiedShare ? (
                  <span
                    className={
                      kpiVerifiedShare.direction === "up"
                        ? "text-emerald-600"
                        : kpiVerifiedShare.direction === "down"
                        ? "text-red-600"
                        : "text-muted-foreground"
                    }
                  >
                    {kpiVerifiedShare.changeLabel === "n/a"
                      ? "Değişim: n/a"
                      : `Değişim: ${kpiVerifiedShare.changeLabel}`}
                  </span>
                ) : (
                  <span className="text-muted-foreground">Not enough snapshots to compute change.</span>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      ) : (
        <div className="mb-4 text-sm text-muted-foreground">
          Not enough snapshots to compute change.
        </div>
      )}

      {/* Chart */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Trend</CardTitle>
        </CardHeader>
        <CardContent className="pt-0">
          <TrendLineChart points={points} />
        </CardContent>
      </Card>

      {/* Table */}
      <div className="mt-4 rounded-xl border bg-card p-4" data-testid="match-risk-trends-table">
        <div className="mb-2 text-xs text-muted-foreground">
          Latest {Math.min(10, points.length || 0)} snapshots
        </div>
        {points && points.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-2 px-2 font-medium">Date</th>
                  <th className="text-left py-2 px-2 font-medium">Matches evaluated</th>
                  <th className="text-left py-2 px-2 font-medium">High-risk matches</th>
                  <th className="text-left py-2 px-2 font-medium">High risk rate</th>
                  <th className="text-left py-2 px-2 font-medium">Verified share avg</th>
                </tr>
              </thead>
              <tbody>
                {points
                  .slice(-10)
                  .map((p, idx) => (
                    <tr key={`${p.generated_at}-${idx}`} className="border-b last:border-0 hover:bg-muted/50">
                      <td className="py-2 px-2 text-xs">{formatDate(p.generated_at)}</td>
                      <td className="py-2 px-2">{p.matches_evaluated}</td>
                      <td className="py-2 px-2">{p.high_risk_matches}</td>
                      <td className="py-2 px-2">{formatPercent(p.high_risk_rate)}</td>
                      <td className="py-2 px-2">{formatPercent(p.verified_share_avg)}</td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="py-8 text-sm text-muted-foreground">
            No snapshots yet. Run a snapshot to start tracking trends.
          </div>
        )}
      </div>
    </div>
  );
}
