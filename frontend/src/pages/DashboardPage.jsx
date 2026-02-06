import React, { useEffect, useMemo, useState, useCallback } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell,
} from "recharts";
import {
  Ticket, CalendarDays, AlertCircle, TrendingUp,
  CheckCircle2, Clock, Activity, ChevronRight,
  BarChart3, ListChecks, Package, FileWarning,
} from "lucide-react";

import { api, getUser } from "../lib/api";
import { Skeleton } from "../components/ui/skeleton";

/* ------------------------------------------------------------------ */
/*  COLORS                                                             */
/* ------------------------------------------------------------------ */
const STATUS_COLORS = {
  pending: "#f59e0b",
  confirmed: "#3b82f6",
  paid: "#10b981",
  cancelled: "#ef4444",
  other: "#94a3b8",
};
const CASE_COLORS = {
  open: "#ef4444",
  waiting: "#f59e0b",
  in_progress: "#3b82f6",
};

/* ------------------------------------------------------------------ */
/*  KPI CARD (compact, 90px max, fully clickable)                      */
/* ------------------------------------------------------------------ */
function KpiCard({ label, value, icon: Icon, to, color, loading }) {
  const navigate = useNavigate();
  const handleClick = () => { if (to) navigate(to); };

  if (loading) {
    return (
      <div className="flex items-center gap-3 rounded-[10px] border border-border/60 bg-card px-4 py-3 h-[82px]">
        <Skeleton className="h-9 w-9 rounded-lg shrink-0" />
        <div className="flex-1 space-y-2">
          <Skeleton className="h-3 w-16" />
          <Skeleton className="h-7 w-12" />
        </div>
      </div>
    );
  }

  return (
    <div
      onClick={handleClick}
      className={`group flex items-center gap-3 rounded-[10px] border border-border/60 bg-card px-3 py-3 h-[82px]
        ${to ? "cursor-pointer hover:border-primary/40 hover:shadow-sm transition-all duration-150" : ""}
      `}
    >
      <div
        className="flex items-center justify-center h-9 w-9 rounded-lg shrink-0"
        style={{ backgroundColor: `${color || "hsl(var(--primary))"}15` }}
      >
        <Icon className="h-4.5 w-4.5" style={{ color: color || "hsl(var(--primary))" }} />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-[11px] leading-tight text-muted-foreground truncate">{label}</p>
        <p className="text-[28px] font-semibold leading-tight text-foreground tracking-tight">{value}</p>
      </div>
      {to && (
        <ChevronRight className="h-3.5 w-3.5 text-muted-foreground/40 group-hover:text-primary transition-colors shrink-0" />
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  MINI DONUT CARD                                                    */
/* ------------------------------------------------------------------ */
function MiniDonutCard({ title, data, colors, loading, emptyText }) {
  const hasData = data && data.some((d) => d.value > 0);

  if (loading) {
    return (
      <div className="rounded-[10px] border border-border/60 bg-card p-4">
        <Skeleton className="h-4 w-24 mb-3" />
        <div className="flex items-center gap-4">
          <Skeleton className="h-[80px] w-[80px] rounded-full shrink-0" />
          <div className="space-y-2 flex-1">
            <Skeleton className="h-3 w-full" />
            <Skeleton className="h-3 w-3/4" />
            <Skeleton className="h-3 w-1/2" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-[10px] border border-border/60 bg-card p-4">
      <p className="text-[13px] font-medium text-foreground mb-3">{title}</p>
      {hasData ? (
        <div className="flex items-center gap-3">
          <div className="shrink-0" style={{ width: 80, height: 80 }}>
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={data}
                  dataKey="value"
                  cx="50%"
                  cy="50%"
                  innerRadius={24}
                  outerRadius={38}
                  strokeWidth={1}
                  stroke="hsl(var(--card))"
                >
                  {data.map((entry, i) => (
                    <Cell key={i} fill={colors[entry.name] || colors.other || "#94a3b8"} />
                  ))}
                </Pie>
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="flex-1 space-y-1.5 min-w-0">
            {data.map((d) => (
              <div key={d.name} className="flex items-center gap-2 text-[11px]">
                <span
                  className="h-2 w-2 rounded-full shrink-0"
                  style={{ backgroundColor: colors[d.name] || "#94a3b8" }}
                />
                <span className="text-muted-foreground truncate flex-1">{d.label}</span>
                <span className="font-medium text-foreground tabular-nums">{d.value}</span>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center py-4 text-center">
          <div className="h-10 w-10 rounded-full bg-muted/50 flex items-center justify-center mb-2">
            <BarChart3 className="h-4 w-4 text-muted-foreground/60" />
          </div>
          <p className="text-[11px] text-muted-foreground">{emptyText || "Veri yok"}</p>
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  TOP PRODUCTS CARD (placeholder)                                    */
/* ------------------------------------------------------------------ */
function TopProductsCard({ loading }) {
  if (loading) {
    return (
      <div className="rounded-[10px] border border-border/60 bg-card p-4">
        <Skeleton className="h-4 w-28 mb-3" />
        <div className="space-y-2.5">
          <Skeleton className="h-3 w-full" />
          <Skeleton className="h-3 w-4/5" />
          <Skeleton className="h-3 w-3/5" />
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-[10px] border border-border/60 bg-card p-4">
      <p className="text-[13px] font-medium text-foreground mb-3">En Çok Satılanlar</p>
      <div className="flex flex-col items-center justify-center py-3 text-center">
        <div className="h-10 w-10 rounded-full bg-muted/50 flex items-center justify-center mb-2">
          <Package className="h-4 w-4 text-muted-foreground/60" />
        </div>
        <p className="text-[11px] text-muted-foreground">Henüz yeterli veri yok</p>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  ATTENTION LIST                                                     */
/* ------------------------------------------------------------------ */
function AttentionList({ items, loading }) {
  const navigate = useNavigate();

  if (loading) {
    return (
      <div className="rounded-[10px] border border-border/60 bg-card p-4">
        <Skeleton className="h-4 w-36 mb-4" />
        <div className="space-y-3">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="flex items-center gap-3">
              <Skeleton className="h-8 w-8 rounded-lg shrink-0" />
              <div className="flex-1 space-y-1.5">
                <Skeleton className="h-3 w-3/4" />
                <Skeleton className="h-2.5 w-1/2" />
              </div>
              <Skeleton className="h-5 w-8 rounded" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  const hasItems = items && items.some((it) => it.count > 0);

  return (
    <div className="rounded-[10px] border border-border/60 bg-card p-4">
      <div className="flex items-center gap-2 mb-4">
        <ListChecks className="h-4 w-4 text-amber-500" />
        <p className="text-[14px] font-medium text-foreground">Hemen İlgilenilmesi Gerekenler</p>
      </div>
      {hasItems ? (
        <div className="space-y-1">
          {items.map((item) => (
            <div
              key={item.label}
              onClick={() => item.to && navigate(item.to)}
              className={`flex items-center gap-3 rounded-lg px-3 py-2.5
                ${item.to ? "cursor-pointer hover:bg-muted/50 transition-colors" : ""}
                ${item.count === 0 ? "opacity-40" : ""}
              `}
            >
              <div
                className="flex items-center justify-center h-8 w-8 rounded-lg shrink-0"
                style={{ backgroundColor: `${item.color}12` }}
              >
                <item.icon className="h-3.5 w-3.5" style={{ color: item.color }} />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-[13px] text-foreground truncate">{item.label}</p>
              </div>
              <span
                className="text-[13px] font-semibold tabular-nums px-2 py-0.5 rounded-md min-w-[32px] text-center"
                style={{
                  color: item.count > 0 ? item.color : undefined,
                  backgroundColor: item.count > 0 ? `${item.color}10` : undefined,
                }}
              >
                {item.count}
              </span>
              {item.to && (
                <ChevronRight className="h-3.5 w-3.5 text-muted-foreground/40 shrink-0" />
              )}
            </div>
          ))}
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center py-6 text-center">
          <div className="h-10 w-10 rounded-full bg-emerald-500/10 flex items-center justify-center mb-2">
            <CheckCircle2 className="h-4 w-4 text-emerald-500" />
          </div>
          <p className="text-[12px] text-muted-foreground">Tüm işler yolunda görünüyor</p>
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  ACTIVITY TIMELINE                                                  */
/* ------------------------------------------------------------------ */
function ActivityTimeline({ loading }) {
  if (loading) {
    return (
      <div className="rounded-[10px] border border-border/60 bg-card p-4">
        <Skeleton className="h-4 w-28 mb-4" />
        <div className="space-y-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="flex gap-3">
              <Skeleton className="h-6 w-6 rounded-full shrink-0" />
              <div className="flex-1 space-y-1.5">
                <Skeleton className="h-3 w-full" />
                <Skeleton className="h-2.5 w-1/3" />
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-[10px] border border-border/60 bg-card p-4">
      <div className="flex items-center gap-2 mb-4">
        <Activity className="h-4 w-4 text-blue-500" />
        <p className="text-[14px] font-medium text-foreground">Son Aktiviteler</p>
      </div>
      <div className="flex flex-col items-center justify-center py-8 text-center">
        <div className="h-10 w-10 rounded-full bg-muted/50 flex items-center justify-center mb-2">
          <Clock className="h-4 w-4 text-muted-foreground/60" />
        </div>
        <p className="text-[12px] text-muted-foreground">Henüz aktivite kaydı yok</p>
        <p className="text-[11px] text-muted-foreground/60 mt-0.5">
          Rezervasyon ve case işlemleri burada görünecek
        </p>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  CHART TOGGLE CHIPS                                                 */
/* ------------------------------------------------------------------ */
function ChipGroup({ options, value, onChange }) {
  return (
    <div className="inline-flex rounded-lg border border-border/60 overflow-hidden">
      {options.map((opt) => (
        <button
          key={opt.value}
          onClick={() => onChange(opt.value)}
          className={`px-3 py-1 text-[11px] font-medium transition-colors
            ${value === opt.value
              ? "bg-primary text-primary-foreground"
              : "bg-card text-muted-foreground hover:bg-muted/50"
            }
          `}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  CUSTOM CHART TOOLTIP                                               */
/* ------------------------------------------------------------------ */
function ChartTooltip({ active, payload, label, metric }) {
  if (!active || !payload?.length) return null;
  const val = payload[0]?.value;
  return (
    <div className="rounded-lg border border-border/60 bg-card px-3 py-2 shadow-md">
      <p className="text-[11px] text-muted-foreground">{label}</p>
      <p className="text-[14px] font-semibold text-foreground">
        {metric === "revenue"
          ? `₺${Number(val || 0).toLocaleString("tr-TR", { minimumFractionDigits: 0 })}`
          : val}
      </p>
    </div>
  );
}

/* ================================================================== */
/*  MAIN DASHBOARD                                                     */
/* ================================================================== */
export default function DashboardPage() {
  const user = getUser();
  const isHotel = (user?.roles || []).some((r) => r.startsWith("hotel_"));
  const isAgency = (user?.roles || []).some((r) => r.startsWith("agency_"));

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [resSummary, setResSummary] = useState([]);
  const [sales, setSales] = useState([]);
  const [caseCounters, setCaseCounters] = useState({ open: 0, waiting: 0, in_progress: 0 });

  // Chart toggles
  const [chartDays, setChartDays] = useState(14);
  const [chartMetric, setChartMetric] = useState("revenue");

  const bookingsBase = isHotel ? "/app/hotel/bookings" : isAgency ? "/app/agency/bookings" : "/app/reservations";
  const casesBase = "/app/ops/guest-cases";

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      setLoading(true);
      setError("");
      const safe = async (fn) => {
        try { return await fn(); }
        catch { return null; }
      };
      const [a, b, c] = await Promise.all([
        safe(() => api.get("/reports/reservations-summary")),
        safe(() => api.get(`/reports/sales-summary?days=${chartDays}`)),
        safe(() => api.get("/ops-cases/counters")),
      ]);
      if (cancelled) return;
      if (a?.data) setResSummary(a.data);
      if (b?.data) setSales(b.data);
      if (c?.data) setCaseCounters(c.data);
      setLoading(false);
    };
    load();
    return () => { cancelled = true; };
  }, [chartDays]);

  /* ---------- derived data ---------- */
  const totals = useMemo(() => {
    const map = new Map(resSummary.map((r) => [r.status, r.count]));
    const total = resSummary.reduce((a, r) => a + Number(r.count || 0), 0);
    return {
      total,
      pending: map.get("pending") || 0,
      confirmed: map.get("confirmed") || 0,
      paid: map.get("paid") || 0,
    };
  }, [resSummary]);

  const resDonutData = useMemo(() => [
    { name: "pending", label: "Beklemede", value: totals.pending },
    { name: "confirmed", label: "Onaylı", value: totals.confirmed },
    { name: "paid", label: "Ödendi", value: totals.paid },
    {
      name: "other",
      label: "Diğer",
      value: Math.max(0, totals.total - totals.pending - totals.confirmed - totals.paid),
    },
  ], [totals]);

  const totalCases = caseCounters.open + caseCounters.waiting + caseCounters.in_progress;
  const caseDonutData = useMemo(() => [
    { name: "open", label: "Açık", value: caseCounters.open },
    { name: "waiting", label: "Beklemede", value: caseCounters.waiting },
    { name: "in_progress", label: "İşlemde", value: caseCounters.in_progress },
  ], [caseCounters]);

  const attentionItems = useMemo(() => [
    {
      label: "Ödeme Bekleyen Rezervasyonlar",
      count: totals.pending,
      icon: Clock,
      color: "#f59e0b",
      to: `${bookingsBase}?status=pending`,
    },
    {
      label: "Onay Bekleyen Rezervasyonlar",
      count: totals.confirmed,
      icon: CheckCircle2,
      color: "#3b82f6",
      to: `${bookingsBase}?status=confirmed`,
    },
    {
      label: "Açık Destek Talepleri",
      count: caseCounters.open,
      icon: AlertCircle,
      color: "#ef4444",
      to: `${casesBase}?status=open`,
    },
    {
      label: "Beklemede Destek Talepleri",
      count: caseCounters.waiting,
      icon: FileWarning,
      color: "#f59e0b",
      to: `${casesBase}?status=waiting`,
    },
  ], [totals, caseCounters, bookingsBase, casesBase]);

  /* ---------- chart data ---------- */
  const chartData = useMemo(() => {
    if (!sales.length) return [];
    // Last N days
    return sales.slice(-chartDays).map((s) => ({
      day: s.day ? s.day.slice(5) : "",
      revenue: s.revenue || 0,
      count: s.count || 0,
    }));
  }, [sales, chartDays]);

  /* ================================================================ */
  /*  RENDER                                                           */
  /* ================================================================ */
  return (
    <div className="space-y-5 pb-8">
      {/* ---------- HEADER ---------- */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-[18px] font-semibold text-foreground">Dashboard</h2>
          <p className="text-[12px] text-muted-foreground mt-0.5">
            Rezervasyon ve operasyon özetini buradan takip edebilirsin.
          </p>
        </div>
        <div className="flex gap-2">
          <Link
            to="/app/products"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-medium rounded-lg border border-border/60 bg-card text-foreground hover:bg-muted/50 transition-colors"
          >
            Ürünler
          </Link>
          <Link
            to="/app/reservations"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-medium rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
          >
            Rezervasyonlar
          </Link>
        </div>
      </div>

      {/* ---------- ERROR ---------- */}
      {error && (
        <div className="rounded-[10px] border border-rose-200 bg-rose-50 dark:border-rose-800 dark:bg-rose-950/30 px-4 py-2.5 text-[12px] text-rose-700 dark:text-rose-300" data-testid="dash-error">
          {error}
        </div>
      )}

      {/* ---------- EMPTY BANNER ---------- */}
      {!loading && totals.total === 0 && totalCases === 0 && !error && (
        <div className="rounded-[10px] border border-border/40 bg-muted/30 px-4 py-2.5 text-[12px] text-muted-foreground">
          Son 30 günde veri bulunamadı. Veriler geldikçe özet kartlar otomatik güncellenecektir.
        </div>
      )}

      {/* ========== ROW 1: KPI BAR ========== */}
      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3">
        <KpiCard
          label="Toplam Rez."
          value={totals.total}
          icon={Ticket}
          color="#6366f1"
          to={bookingsBase}
          loading={loading}
        />
        <KpiCard
          label="Beklemede"
          value={totals.pending}
          icon={Clock}
          color="#f59e0b"
          to={`${bookingsBase}?status=pending`}
          loading={loading}
        />
        <KpiCard
          label="Onaylı"
          value={totals.confirmed}
          icon={CheckCircle2}
          color="#3b82f6"
          to={`${bookingsBase}?status=confirmed`}
          loading={loading}
        />
        <KpiCard
          label="Ödendi"
          value={totals.paid}
          icon={TrendingUp}
          color="#10b981"
          to={`${bookingsBase}?status=paid`}
          loading={loading}
        />
        <KpiCard
          label="Açık Case"
          value={caseCounters.open}
          icon={AlertCircle}
          color="#ef4444"
          to={`${casesBase}?status=open`}
          loading={loading}
        />
        <KpiCard
          label="İşlemde"
          value={caseCounters.in_progress}
          icon={Activity}
          color="#8b5cf6"
          to={`${casesBase}?status=in_progress`}
          loading={loading}
        />
      </div>

      {/* ========== ROW 2: CHART + RIGHT RAIL ========== */}
      <div className="grid grid-cols-1 xl:grid-cols-[1fr_320px] gap-4">
        {/* --- Chart --- */}
        <div className="rounded-[10px] border border-border/60 bg-card p-4">
          <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
            <p className="text-[14px] font-medium text-foreground">Satış Grafiği</p>
            <div className="flex items-center gap-2">
              <ChipGroup
                options={[
                  { label: "14G", value: 14 },
                  { label: "30G", value: 30 },
                ]}
                value={chartDays}
                onChange={setChartDays}
              />
              <ChipGroup
                options={[
                  { label: "Satış", value: "revenue" },
                  { label: "Rezervasyon", value: "count" },
                ]}
                value={chartMetric}
                onChange={setChartMetric}
              />
            </div>
          </div>

          {loading ? (
            <div className="space-y-3" style={{ minHeight: 280 }}>
              <div className="flex items-end gap-1 h-[260px] px-4">
                {[65, 40, 75, 50, 85, 35, 60, 45, 70, 55, 80, 42, 68, 52].map((h, i) => (
                  <Skeleton
                    key={i}
                    className="flex-1 rounded-t"
                    style={{ height: `${h}%` }}
                  />
                ))}
              </div>
            </div>
          ) : chartData.length > 0 ? (
            <div style={{ minHeight: 280 }} data-testid="sales-chart">
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={chartData} margin={{ left: 0, right: 4, top: 8, bottom: 0 }}>
                  <XAxis
                    dataKey="day"
                    tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <YAxis
                    tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                    axisLine={false}
                    tickLine={false}
                    width={40}
                  />
                  <Tooltip content={<ChartTooltip metric={chartMetric} />} cursor={{ fill: "hsl(var(--muted))", opacity: 0.4 }} />
                  <Bar
                    dataKey={chartMetric}
                    fill="hsl(var(--primary))"
                    radius={[6, 6, 0, 0]}
                    maxBarSize={32}
                  />
                </BarChart>
              </ResponsiveContainer>
              <p className="text-[11px] text-muted-foreground/60 mt-2 px-1">
                {chartMetric === "revenue"
                  ? "Not: Gelir hesaplaması rezervasyon toplam fiyatı üzerinden yapılır."
                  : "Not: Sayı, toplam rezervasyon adedini gösterir."}
              </p>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center text-center" style={{ minHeight: 280 }}>
              <div className="h-12 w-12 rounded-full bg-muted/50 flex items-center justify-center mb-3">
                <BarChart3 className="h-5 w-5 text-muted-foreground/50" />
              </div>
              <p className="text-[13px] text-muted-foreground">Grafik verisi bulunamadı</p>
              <p className="text-[11px] text-muted-foreground/60 mt-0.5">
                Son {chartDays} günde satış kaydı yok
              </p>
            </div>
          )}
        </div>

        {/* --- Right Rail --- */}
        <div className="flex flex-col gap-3">
          <MiniDonutCard
            title="Rezervasyon Dağılımı"
            data={resDonutData}
            colors={STATUS_COLORS}
            loading={loading}
            emptyText="Rezervasyon verisi yok"
          />
          <MiniDonutCard
            title="Case Dağılımı"
            data={caseDonutData}
            colors={CASE_COLORS}
            loading={loading}
            emptyText="Case verisi yok"
          />
          <TopProductsCard loading={loading} />
        </div>
      </div>

      {/* ========== ROW 3: ATTENTION + ACTIVITY ========== */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <AttentionList items={attentionItems} loading={loading} />
        <ActivityTimeline loading={loading} />
      </div>
    </div>
  );
}
