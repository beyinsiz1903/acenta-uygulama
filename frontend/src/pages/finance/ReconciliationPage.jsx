import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import {
  Scale,
  TrendingUp,
  AlertTriangle,
  CheckCircle2,
  BarChart3,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../../components/ui/table";
import { fetchReconciliationSummary, fetchMarginRevenueSummary, fetchReconciliationSnapshots } from "./lib/financeApi";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line, Legend } from "recharts";

const fmt = (v) => new Intl.NumberFormat("tr-TR", { style: "currency", currency: "EUR" }).format(v || 0);

const SNAP_STATUS = {
  completed: { label: "Tamamlandı", color: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300" },
  in_progress: { label: "Devam Ediyor", color: "bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300" },
  has_mismatches: { label: "Uyumsuzluk Var", color: "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300" },
};

export default function ReconciliationPage() {
  const navigate = useNavigate();

  const { data: summary, isLoading } = useQuery({
    queryKey: ["reconciliation-summary"],
    queryFn: fetchReconciliationSummary,
  });

  const { data: marginData } = useQuery({
    queryKey: ["margin-revenue-summary"],
    queryFn: fetchMarginRevenueSummary,
  });

  const { data: snapshotsData } = useQuery({
    queryKey: ["reconciliation-snapshots"],
    queryFn: () => fetchReconciliationSnapshots({}),
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <div className="h-8 w-8 animate-spin rounded-full border-3 border-primary border-t-transparent" />
      </div>
    );
  }

  const agg = summary?.aggregate || {};
  const latest = summary?.latest_snapshot || {};
  const periods = marginData?.periods || [];
  const totals = marginData?.totals || {};
  const snapshots = snapshotsData?.snapshots || [];

  // Chart data
  const chartData = periods.map((p) => ({
    period: p.period,
    Gelir: p.total_revenue,
    Maliyet: p.total_cost,
    Marj: p.gross_margin,
  }));

  const reconChart = periods.map((p) => ({
    period: p.period,
    "Uzlaşmış": p.reconciled_amount,
    "Uzlaşmamış": p.unreconciled_amount,
    Uyumsuzluk: p.mismatch_count,
  }));

  return (
    <div className="space-y-6" data-testid="reconciliation-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight" data-testid="reconciliation-title">Uzlaştırma & Marj Analizi</h1>
          <p className="text-sm text-muted-foreground mt-1">Dönemsel uzlaştırma durumu, marj ve uyumsuzluk özeti</p>
        </div>
        <Button variant="outline" size="sm" onClick={() => navigate("/app/admin/finance/overview-v2")} data-testid="back-to-overview-btn">
          Genel Bakış
        </Button>
      </div>

      {/* Aggregate KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4" data-testid="recon-kpi-grid">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2 mb-2">
              <div className="p-1.5 rounded-lg bg-teal-50 dark:bg-teal-900/20">
                <TrendingUp className="h-4 w-4 text-teal-600" />
              </div>
              <span className="text-xs text-muted-foreground uppercase tracking-wide">Toplam Gelir</span>
            </div>
            <div className="text-xl font-bold" data-testid="kpi-total-revenue">{fmt(totals.total_revenue)}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2 mb-2">
              <div className="p-1.5 rounded-lg bg-emerald-50 dark:bg-emerald-900/20">
                <BarChart3 className="h-4 w-4 text-emerald-600" />
              </div>
              <span className="text-xs text-muted-foreground uppercase tracking-wide">Brüt Marj</span>
            </div>
            <div className="text-xl font-bold" data-testid="kpi-gross-margin">{fmt(totals.gross_margin)}</div>
            <div className="text-xs text-muted-foreground">%{totals.gross_margin_pct}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2 mb-2">
              <div className="p-1.5 rounded-lg bg-blue-50 dark:bg-blue-900/20">
                <CheckCircle2 className="h-4 w-4 text-blue-600" />
              </div>
              <span className="text-xs text-muted-foreground uppercase tracking-wide">Uzlaşmış</span>
            </div>
            <div className="text-xl font-bold" data-testid="kpi-reconciled">{fmt(agg.total_reconciled)}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-2 mb-2">
              <div className="p-1.5 rounded-lg bg-red-50 dark:bg-red-900/20">
                <AlertTriangle className="h-4 w-4 text-red-600" />
              </div>
              <span className="text-xs text-muted-foreground uppercase tracking-wide">Uyumsuzluk</span>
            </div>
            <div className="text-xl font-bold text-red-600" data-testid="kpi-mismatches">{agg.total_mismatches}</div>
            <div className="text-xs text-muted-foreground">{fmt(agg.total_mismatch_amount)}</div>
          </CardContent>
        </Card>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Revenue/Cost/Margin Chart */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold">Gelir, Maliyet & Marj Trendi</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[260px]" data-testid="margin-trend-chart">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                  <XAxis dataKey="period" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 12 }} tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`} />
                  <Tooltip formatter={(v) => fmt(v)} />
                  <Legend />
                  <Bar dataKey="Gelir" fill="hsl(185, 60%, 35%)" radius={[3, 3, 0, 0]} />
                  <Bar dataKey="Maliyet" fill="hsl(8, 76%, 46%)" radius={[3, 3, 0, 0]} />
                  <Bar dataKey="Marj" fill="hsl(151, 55%, 32%)" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* Reconciliation Status Chart */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold">Uzlaştırma Durumu</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[260px]" data-testid="recon-status-chart">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={reconChart}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                  <XAxis dataKey="period" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 12 }} tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`} />
                  <Tooltip formatter={(v, name) => name === "Uyumsuzluk" ? v : fmt(v)} />
                  <Legend />
                  <Line type="monotone" dataKey="Uzlaşmış" stroke="hsl(151, 55%, 32%)" strokeWidth={2} dot={{ r: 4 }} />
                  <Line type="monotone" dataKey="Uzlaşmamış" stroke="hsl(35, 92%, 45%)" strokeWidth={2} dot={{ r: 4 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Latest Snapshot */}
      {latest.snapshot_id && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <Scale className="h-4 w-4" />
              Son Dönem: {latest.period}
            </CardTitle>
          </CardHeader>
          <CardContent data-testid="latest-snapshot-card">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
              <div>
                <div className="text-xs text-muted-foreground mb-1">Gelir</div>
                <div className="font-medium">{fmt(latest.total_revenue)}</div>
              </div>
              <div>
                <div className="text-xs text-muted-foreground mb-1">Maliyet</div>
                <div className="font-medium">{fmt(latest.total_cost)}</div>
              </div>
              <div>
                <div className="text-xs text-muted-foreground mb-1">Brüt Marj</div>
                <div className="font-medium">{fmt(latest.gross_margin)} (%{latest.gross_margin_pct})</div>
              </div>
              <div>
                <div className="text-xs text-muted-foreground mb-1">Durum</div>
                <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${(SNAP_STATUS[latest.status] || SNAP_STATUS.in_progress).color}`}>
                  {(SNAP_STATUS[latest.status] || SNAP_STATUS.in_progress).label}
                </span>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Snapshots History */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-semibold">Dönem Geçmişi</CardTitle>
        </CardHeader>
        <CardContent className="p-0" data-testid="snapshots-table">
          <div className="overflow-auto border rounded-lg">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="text-xs">Dönem</TableHead>
                  <TableHead className="text-xs text-right">Gelir</TableHead>
                  <TableHead className="text-xs text-right">Maliyet</TableHead>
                  <TableHead className="text-xs text-right">Marj</TableHead>
                  <TableHead className="text-xs text-right">Marj %</TableHead>
                  <TableHead className="text-xs text-right">Uzlaşmış</TableHead>
                  <TableHead className="text-xs text-right">Uzlaşmamış</TableHead>
                  <TableHead className="text-xs text-center">Uyumsuzluk</TableHead>
                  <TableHead className="text-xs">Durum</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {snapshots.map((s) => {
                  const cfg = SNAP_STATUS[s.status] || SNAP_STATUS.in_progress;
                  return (
                    <TableRow key={s.snapshot_id} data-testid={`snapshot-row-${s.snapshot_id}`}>
                      <TableCell className="font-medium text-sm">{s.period}</TableCell>
                      <TableCell className="text-right text-sm">{fmt(s.total_revenue)}</TableCell>
                      <TableCell className="text-right text-sm">{fmt(s.total_cost)}</TableCell>
                      <TableCell className="text-right text-sm font-medium">{fmt(s.gross_margin)}</TableCell>
                      <TableCell className="text-right text-sm">%{s.gross_margin_pct}</TableCell>
                      <TableCell className="text-right text-sm">{fmt(s.reconciled_amount)}</TableCell>
                      <TableCell className="text-right text-sm">
                        <span className={s.unreconciled_amount > 0 ? "text-amber-600" : ""}>
                          {fmt(s.unreconciled_amount)}
                        </span>
                      </TableCell>
                      <TableCell className="text-center">
                        {s.mismatch_count > 0 ? (
                          <Badge variant="destructive" className="text-xs">{s.mismatch_count}</Badge>
                        ) : (
                          <Badge variant="outline" className="text-xs">0</Badge>
                        )}
                      </TableCell>
                      <TableCell>
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${cfg.color}`}>
                          {cfg.label}
                        </span>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
