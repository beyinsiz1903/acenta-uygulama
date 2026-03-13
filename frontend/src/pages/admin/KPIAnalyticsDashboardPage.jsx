import React, { useState, useEffect, useCallback } from "react";
import {
  BarChart3, TrendingUp, Search, ShoppingCart, RefreshCw, Loader2,
  AlertTriangle, CheckCircle2, Zap, DollarSign, Award, ArrowDown,
  ArrowUp, Minus, Activity
} from "lucide-react";
import { Button } from "../../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Badge } from "../../components/ui/badge";
import {
  Select, SelectTrigger, SelectValue, SelectContent, SelectItem,
} from "../../components/ui/select";
import {
  Table, TableHeader, TableBody, TableRow, TableHead, TableCell,
} from "../../components/ui/table";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "../../components/ui/tabs";
import { toast } from "sonner";
import { getKPISummary, getSupplierScores, getDailyStats, getConversionFunnel } from "../../lib/unifiedBooking";

function formatPrice(amount, currency = "TRY") {
  if (!amount && amount !== 0) return "-";
  return new Intl.NumberFormat("tr-TR", { style: "currency", currency }).format(amount);
}

function formatSupplierName(code) {
  return (code || "").replace("real_", "").replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
}

const SUPPLIER_COLORS = {
  ratehawk: "bg-blue-100 text-blue-800",
  tbo: "bg-emerald-100 text-emerald-800",
  paximum: "bg-amber-100 text-amber-800",
  wwtatil: "bg-violet-100 text-violet-800",
};

function getSupplierBadgeClass(code) {
  const key = (code || "").toLowerCase().replace("real_", "");
  return SUPPLIER_COLORS[key] || "bg-gray-100 text-gray-700";
}

// ========================= KPI CARDS =========================
function KPICards({ kpi }) {
  const cards = [
    { label: "Toplam Arama", value: kpi.total_searches, icon: Search, color: "text-blue-600", bgColor: "bg-blue-50" },
    { label: "Toplam Rezervasyon", value: kpi.total_bookings, icon: ShoppingCart, color: "text-green-600", bgColor: "bg-green-50" },
    { label: "Donusum Orani", value: `%${kpi.conversion_rate}`, icon: TrendingUp, color: "text-violet-600", bgColor: "bg-violet-50" },
    { label: "Toplam Gelir", value: formatPrice(kpi.total_revenue), icon: DollarSign, color: "text-emerald-600", bgColor: "bg-emerald-50" },
    { label: "Basari Orani", value: `%${kpi.booking_success_rate}`, icon: CheckCircle2, color: "text-teal-600", bgColor: "bg-teal-50" },
    { label: "Fallback Orani", value: `%${kpi.fallback_rate}`, icon: RefreshCw, color: "text-amber-600", bgColor: "bg-amber-50" },
  ];

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4" data-testid="kpi-cards">
      {cards.map((c, idx) => (
        <Card key={idx} data-testid={`kpi-card-${idx}`} className="overflow-hidden">
          <CardContent className="pt-4 pb-3 px-4">
            <div className={`inline-flex items-center justify-center h-8 w-8 rounded-lg ${c.bgColor} mb-2`}>
              <c.icon className={`h-4 w-4 ${c.color}`} />
            </div>
            <p className="text-xl font-bold font-mono">{c.value}</p>
            <p className="text-[10px] text-muted-foreground mt-0.5">{c.label}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

// ========================= CONVERSION FUNNEL =========================
function ConversionFunnel({ funnel }) {
  const steps = [
    { key: "search_event", label: "Arama", icon: Search, color: "bg-blue-500" },
    { key: "result_view_event", label: "Sonuc Goruntuleme", icon: BarChart3, color: "bg-indigo-500" },
    { key: "supplier_select_event", label: "Supplier Secimi", icon: Zap, color: "bg-violet-500" },
    { key: "booking_start_event", label: "Booking Baslangic", icon: ShoppingCart, color: "bg-amber-500" },
    { key: "booking_confirm_event", label: "Booking Onay", icon: CheckCircle2, color: "bg-green-500" },
  ];

  const maxCount = Math.max(...steps.map(s => funnel[s.key] || 0), 1);

  return (
    <Card data-testid="conversion-funnel-card">
      <CardHeader className="pb-3">
        <CardTitle className="text-base font-semibold flex items-center gap-2">
          <Activity className="h-4 w-4 text-primary" />
          Donusum Hunisi
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {steps.map((step, idx) => {
            const count = funnel[step.key] || 0;
            const pct = maxCount > 0 ? (count / maxCount) * 100 : 0;
            const prevCount = idx > 0 ? (funnel[steps[idx - 1].key] || 0) : count;
            const dropOff = prevCount > 0 && idx > 0 ? round((1 - count / prevCount) * 100) : null;
            return (
              <div key={step.key} data-testid={`funnel-step-${idx}`}>
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2">
                    <step.icon className="h-3.5 w-3.5 text-muted-foreground" />
                    <span className="text-xs font-medium">{step.label}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-sm font-semibold">{count}</span>
                    {dropOff !== null && dropOff > 0 && (
                      <Badge variant="outline" className="text-[9px] text-red-600 border-red-200">
                        <ArrowDown className="h-2.5 w-2.5 mr-0.5" />
                        {dropOff}%
                      </Badge>
                    )}
                  </div>
                </div>
                <div className="h-2 bg-muted rounded-full overflow-hidden">
                  <div className={`h-full rounded-full transition-all duration-500 ${step.color}`} style={{ width: `${pct}%` }} />
                </div>
              </div>
            );
          })}
        </div>
        {/* Summary rates */}
        <div className="grid grid-cols-2 gap-4 mt-4 pt-4 border-t">
          <div className="text-center">
            <p className="text-[10px] text-muted-foreground">Arama → Booking</p>
            <p className="font-mono font-semibold text-lg">{funnel.search_to_confirm_rate || 0}%</p>
          </div>
          <div className="text-center">
            <p className="text-[10px] text-muted-foreground">Secim → Booking</p>
            <p className="font-mono font-semibold text-lg">{funnel.select_to_book_rate || 0}%</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function round(n) {
  return Math.round(n * 10) / 10;
}

// ========================= SUPPLIER SCORES =========================
function SupplierScoresTable({ scores }) {
  if (!scores || scores.length === 0) {
    return (
      <Card className="border-dashed" data-testid="no-scores">
        <CardContent className="py-8 text-center text-muted-foreground text-sm">
          <Award className="h-8 w-8 mx-auto mb-2 opacity-40" />
          Henuz supplier skor verisi yok. Aramalar ve rezervasyonlar arttikca skorlar hesaplanacak.
        </CardContent>
      </Card>
    );
  }

  const TAG_LABELS = {
    best_price: { label: "En Ucuz", color: "bg-green-100 text-green-700" },
    fastest_confirmation: { label: "En Hizli", color: "bg-amber-100 text-amber-700" },
    most_reliable: { label: "En Guvenilir", color: "bg-blue-100 text-blue-700" },
    best_cancellation: { label: "Iptal Guvenli", color: "bg-violet-100 text-violet-700" },
  };

  return (
    <Card data-testid="supplier-scores-card">
      <CardHeader className="pb-3">
        <CardTitle className="text-base font-semibold flex items-center gap-2">
          <Award className="h-4 w-4 text-primary" />
          Supplier Performans Skorlari
        </CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <div className="border rounded-lg overflow-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="text-xs">Supplier</TableHead>
                <TableHead className="text-xs text-center">Toplam Skor</TableHead>
                <TableHead className="text-xs text-center">Fiyat</TableHead>
                <TableHead className="text-xs text-center">Basari</TableHead>
                <TableHead className="text-xs text-center">Hiz</TableHead>
                <TableHead className="text-xs text-center">Iptal</TableHead>
                <TableHead className="text-xs text-center">Fallback</TableHead>
                <TableHead className="text-xs">Etiketler</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {scores.map((s, idx) => (
                <TableRow key={idx} data-testid={`score-row-${idx}`}>
                  <TableCell>
                    <Badge variant="outline" className={`text-[10px] ${getSupplierBadgeClass(s.supplier_code)}`}>
                      {formatSupplierName(s.supplier_code)}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-center">
                    <span className={`font-mono font-bold text-sm ${
                      s.total_score >= 70 ? "text-green-600" : s.total_score >= 40 ? "text-amber-600" : "text-red-600"
                    }`}>
                      {s.total_score}
                    </span>
                  </TableCell>
                  <TableCell className="text-center font-mono text-xs">{s.components.price_competitiveness}</TableCell>
                  <TableCell className="text-center font-mono text-xs">{s.components.booking_success_rate}</TableCell>
                  <TableCell className="text-center font-mono text-xs">{s.components.latency_score}</TableCell>
                  <TableCell className="text-center font-mono text-xs">{s.components.cancellation_reliability}</TableCell>
                  <TableCell className="text-center font-mono text-xs">{s.components.fallback_frequency_inverse}</TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-1">
                      {(s.tags || []).map((tag, tIdx) => {
                        const cfg = TAG_LABELS[tag] || { label: tag, color: "bg-gray-100 text-gray-600" };
                        return (
                          <Badge key={tIdx} variant="outline" className={`text-[9px] ${cfg.color}`}>
                            {cfg.label}
                          </Badge>
                        );
                      })}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
}

// ========================= REVENUE TABLE =========================
function RevenueBySupplier({ revenue }) {
  if (!revenue || revenue.length === 0) {
    return (
      <Card className="border-dashed" data-testid="no-revenue">
        <CardContent className="py-8 text-center text-muted-foreground text-sm">
          <DollarSign className="h-8 w-8 mx-auto mb-2 opacity-40" />
          Henuz gelir verisi yok
        </CardContent>
      </Card>
    );
  }

  return (
    <Card data-testid="revenue-by-supplier-card">
      <CardHeader className="pb-3">
        <CardTitle className="text-base font-semibold flex items-center gap-2">
          <DollarSign className="h-4 w-4 text-primary" />
          Supplier Bazli Gelir
        </CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <div className="border rounded-lg overflow-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="text-xs">Supplier</TableHead>
                <TableHead className="text-xs text-right">Rezervasyon</TableHead>
                <TableHead className="text-xs text-right">Toplam Gelir</TableHead>
                <TableHead className="text-xs text-right">Ort. Gelir</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {revenue.map((r, idx) => (
                <TableRow key={idx} data-testid={`revenue-row-${idx}`}>
                  <TableCell>
                    <Badge variant="outline" className={`text-[10px] ${getSupplierBadgeClass(r.supplier_code)}`}>
                      {formatSupplierName(r.supplier_code)}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right font-mono text-sm">{r.booking_count}</TableCell>
                  <TableCell className="text-right font-mono text-sm font-semibold">{formatPrice(r.total_revenue)}</TableCell>
                  <TableCell className="text-right font-mono text-sm">
                    {r.booking_count > 0 ? formatPrice(r.total_revenue / r.booking_count) : "-"}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
}

// ========================= DAILY CHART =========================
function DailyStatsChart({ stats }) {
  if (!stats || stats.length === 0) {
    return (
      <Card className="border-dashed" data-testid="no-daily-stats">
        <CardContent className="py-8 text-center text-muted-foreground text-sm">
          <BarChart3 className="h-8 w-8 mx-auto mb-2 opacity-40" />
          Henuz gunluk veri yok
        </CardContent>
      </Card>
    );
  }

  const maxSearches = Math.max(...stats.map(s => s.searches), 1);

  return (
    <Card data-testid="daily-stats-card">
      <CardHeader className="pb-3">
        <CardTitle className="text-base font-semibold flex items-center gap-2">
          <BarChart3 className="h-4 w-4 text-primary" />
          Gunluk Arama & Rezervasyon
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-1.5 max-h-[300px] overflow-y-auto">
          {stats.slice(-15).map((day, idx) => (
            <div key={idx} className="flex items-center gap-3" data-testid={`daily-row-${idx}`}>
              <span className="text-[10px] text-muted-foreground w-20 shrink-0 font-mono">{day.date}</span>
              <div className="flex-1 flex items-center gap-1 h-5">
                <div
                  className="h-full bg-blue-400 rounded-sm transition-all"
                  style={{ width: `${(day.searches / maxSearches) * 100}%` }}
                  title={`Arama: ${day.searches}`}
                />
                <div
                  className="h-full bg-green-500 rounded-sm transition-all"
                  style={{ width: `${(day.bookings / maxSearches) * 100}%` }}
                  title={`Booking: ${day.bookings}`}
                />
              </div>
              <div className="flex gap-2 text-[10px] font-mono w-24 shrink-0 justify-end">
                <span className="text-blue-600">{day.searches}</span>
                <span className="text-green-600">{day.bookings}</span>
              </div>
            </div>
          ))}
        </div>
        <div className="flex items-center gap-4 mt-3 pt-2 border-t">
          <span className="flex items-center gap-1 text-[10px]">
            <div className="h-2.5 w-2.5 rounded-sm bg-blue-400" /> Aramalar
          </span>
          <span className="flex items-center gap-1 text-[10px]">
            <div className="h-2.5 w-2.5 rounded-sm bg-green-500" /> Rezervasyonlar
          </span>
        </div>
      </CardContent>
    </Card>
  );
}

// ========================= MAIN PAGE =========================
export default function KPIAnalyticsDashboardPage() {
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState("30");
  const [kpi, setKpi] = useState(null);
  const [funnel, setFunnel] = useState(null);
  const [scores, setScores] = useState([]);
  const [dailyStats, setDailyStats] = useState([]);
  const [revenue, setRevenue] = useState([]);
  const [activeTab, setActiveTab] = useState("overview");

  const fetchData = useCallback(async () => {
    setLoading(true);
    const d = Number(days);
    try {
      const [kpiData, funnelData, scoresData, statsData] = await Promise.all([
        getKPISummary(d).catch(() => null),
        getConversionFunnel(d).catch(() => null),
        getSupplierScores(d).catch(() => ({ scores: [] })),
        getDailyStats(d).catch(() => ({ stats: [] })),
      ]);

      if (kpiData) {
        setKpi(kpiData.kpi);
        setRevenue(kpiData.revenue_by_supplier || []);
      }
      setFunnel(funnelData?.funnel || {});
      setScores(scoresData?.scores || []);
      setDailyStats(statsData?.stats || []);
    } catch (err) {
      toast.error("KPI verileri yuklenemedi");
    } finally {
      setLoading(false);
    }
  }, [days]);

  useEffect(() => { fetchData(); }, [fetchData]);

  return (
    <div className="space-y-6" data-testid="kpi-analytics-dashboard">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">KPI & Analitik</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Arama, donusum, supplier performansi ve gelir analizi
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Select value={days} onValueChange={setDays}>
            <SelectTrigger className="w-[120px]" data-testid="days-filter">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="7">Son 7 gun</SelectItem>
              <SelectItem value="30">Son 30 gun</SelectItem>
              <SelectItem value="90">Son 90 gun</SelectItem>
            </SelectContent>
          </Select>
          <Button
            variant="outline"
            size="sm"
            onClick={fetchData}
            disabled={loading}
            data-testid="refresh-kpi-btn"
          >
            <RefreshCw className={`h-4 w-4 mr-1 ${loading ? "animate-spin" : ""}`} />
            Yenile
          </Button>
        </div>
      </div>

      {loading && !kpi ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-primary" />
          <span className="ml-2 text-sm text-muted-foreground">Yukleniyor...</span>
        </div>
      ) : (
        <>
          {kpi && <KPICards kpi={kpi} />}

          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList>
              <TabsTrigger value="overview" data-testid="tab-kpi-overview">Genel Bakis</TabsTrigger>
              <TabsTrigger value="suppliers" data-testid="tab-kpi-suppliers">Supplier Performans</TabsTrigger>
              <TabsTrigger value="revenue" data-testid="tab-kpi-revenue">Gelir</TabsTrigger>
            </TabsList>

            <TabsContent value="overview" className="mt-4">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {funnel && <ConversionFunnel funnel={funnel} />}
                <DailyStatsChart stats={dailyStats} />
              </div>
            </TabsContent>

            <TabsContent value="suppliers" className="mt-4">
              <SupplierScoresTable scores={scores} />
            </TabsContent>

            <TabsContent value="revenue" className="mt-4">
              <RevenueBySupplier revenue={revenue} />
            </TabsContent>
          </Tabs>
        </>
      )}
    </div>
  );
}
