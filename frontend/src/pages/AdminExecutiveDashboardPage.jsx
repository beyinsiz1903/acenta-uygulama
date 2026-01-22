import React, { useEffect, useMemo, useState } from "react";
import { subDays, format as formatDate, differenceInCalendarDays } from "date-fns";
import {
  Activity,
  BarChart2,
  CreditCard,
  DollarSign,
  PieChart,
  TrendingUp,
  AlertCircle,
} from "lucide-react";

import { api, apiErrorMessage } from "../lib/api";
import { useSeo } from "../hooks/useSeo";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table";

import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  LineChart,
  Line,
} from "recharts";

function formatMoney(value, currency = "EUR") {
  if (value == null) return "-";
  const num = Number(value);
  if (Number.isNaN(num)) return "-";
  return `${num.toFixed(2)} ${currency}`;
}

function percentage(n, d) {
  if (!d || d <= 0) return 0;
  return (Number(n || 0) / Number(d)) * 100;
}

export default function AdminExecutiveDashboardPage() {
  useSeo({
    title: "Yönetim Dashboard",
    description: "Ciro, B2B performans ve risk özetleri için yönetim paneli.",
    canonicalPath: "/admin/executive-dashboard",
    type: "website",
  });

  const [startDate, setStartDate] = useState(() => subDays(new Date(), 29));
  const [endDate, setEndDate] = useState(() => new Date());
  const [preset, setPreset] = useState("30"); // "7" | "30" | "custom"

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [reportingSummary, setReportingSummary] = useState(null);
  const [topProducts, setTopProducts] = useState([]);
  const [metricsOverview, setMetricsOverview] = useState(null);
  const [metricsTrends, setMetricsTrends] = useState([]);
  const [suppliersSummary, setSuppliersSummary] = useState(null);
  const [b2bExposure, setB2bExposure] = useState(null);

  const days = useMemo(() => {
    const diff = differenceInCalendarDays(endDate, startDate) + 1;
    if (!Number.isFinite(diff) || diff <= 0) return 7;
    return diff;
  }, [startDate, endDate]);

  useEffect(() => {
    void loadAll();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function loadAll() {
    setLoading(true);
    setError("");
    try {
      const qsDays = days || 7;
      const startStr = formatDate(startDate, "yyyy-MM-dd");
      const endStr = formatDate(endDate, "yyyy-MM-dd");

      const [repRes, topRes, ovRes, trendRes, suppRes, b2bRes] = await Promise.all([
        api.get("/admin/reporting/summary", { params: { days: qsDays } }),
        api.get("/admin/reporting/top-products", { params: { days: qsDays, limit: 5, by: "sell" } }),
        api.get("/admin/metrics/overview", { params: { start: startStr, end: endStr } }),
        api.get("/admin/metrics/trends", { params: { start: startStr, end: endStr } }),
        api.get("/ops/finance/suppliers/payable-summary", { params: { currency: "EUR" } }),
        api.get("/admin/b2b/agencies/summary"),
      ]);

      setReportingSummary(repRes.data || null);
      setTopProducts(topRes.data?.items || []);
      setMetricsOverview(ovRes.data || null);
      setMetricsTrends(trendRes.data?.daily_trends || []);
      setSuppliersSummary(suppRes.data || null);
      setB2bExposure(b2bRes.data?.items || []);
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  const kpi = useMemo(() => {
    const book = reportingSummary?.bookings || {};
    const metricsBook = metricsOverview?.bookings || {};

    const totalBookings = Number(book.count || metricsBook.total || 0);
    const sellTotal = Number(book.sell_total || 0);
    const netTotal = Number(book.net_total || 0);
    const markupTotal = Number(book.markup_total || (sellTotal - netTotal));
    const currency = book.currency || "EUR";

    const cancelled = Number(metricsBook.cancelled || 0);
    const cancelRate = percentage(cancelled, totalBookings);

    // B2B exposure özet
    let totalExposure = 0;
    let totalCreditLimit = 0;
    let overLimitCount = 0;
    let nearLimitCount = 0;
    if (Array.isArray(b2bExposure)) {
      b2bExposure.forEach((a) => {
        if (typeof a.exposure === "number") totalExposure += a.exposure;
        if (typeof a.credit_limit === "number") totalCreditLimit += a.credit_limit;
        if (a.risk_status === "over_limit") overLimitCount += 1;
        if (a.risk_status === "near_limit") nearLimitCount += 1;
      });
    }

    // Supplier payable
    const supplierTotal = Number(suppliersSummary?.total_payable || 0);
    const supplierCurrency = suppliersSummary?.currency || "EUR";
    const supplierCount = Number(suppliersSummary?.supplier_count || 0);

    return {
      totalBookings,
      sellTotal,
      netTotal,
      markupTotal,
      currency,
      cancelRate,
      cancelled,
      totalExposure,
      totalCreditLimit,
      overLimitCount,
      nearLimitCount,
      supplierTotal,
      supplierCurrency,
      supplierCount,
    };
  }, [reportingSummary, metricsOverview, b2bExposure, suppliersSummary]);

  const trendData = useMemo(() => {
    if (!metricsTrends || metricsTrends.length === 0) return [];
    return metricsTrends.map((row) => ({
      date: row.date,
      confirmed: row.confirmed,
      cancelled: row.cancelled,
      pending: row.pending,
      total: row.total,
    }));
  }, [metricsTrends]);

  function handlePresetClick(value) {
    setPreset(value);
    const today = new Date();
    if (value === "7") {
      setStartDate(subDays(today, 6));
      setEndDate(today);
    } else if (value === "30") {
      setStartDate(subDays(today, 29));
      setEndDate(today);
    }
    // custom durumda tarih picker üzerinden değişecek
  }

  return (
    <div className="space-y-4">
      <div className="space-y-1">
        <h1 className="text-2xl font-bold text-foreground">Yönetim Dashboard</h1>
        <p className="text-sm text-muted-foreground">
          Toplam ciro, B2B performans, iptal oranları ve tedarikçi riskini tek ekranda görüntüleyin.
        </p>
      </div>

      {/* Tarih / filtre satırı */}
      <Card>
        <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Activity className="h-4 w-4" /> Zaman Aralığı
            </CardTitle>
            <p className="text-xs text-muted-foreground mt-1">
              Son {days} günlük performans. Hazır filtrelerden seçim yapabilir veya tarih aralığını
              elle girebilirsiniz (YYYY-MM-DD).
            </p>
          </div>
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
            <div className="inline-flex rounded-lg bg-muted p-1 text-[11px] text-muted-foreground">
              <button
                type="button"
                className={`px-2 py-1 rounded-md ${
                  preset === "7" ? "bg-background text-foreground shadow" : ""
                }`}
                onClick={() => handlePresetClick("7")}
              >
                Son 7 gün
              </button>
              <button
                type="button"
                className={`px-2 py-1 rounded-md ${
                  preset === "30" ? "bg-background text-foreground shadow" : ""
                }`}
                onClick={() => handlePresetClick("30")}
              >
                Son 30 gün
              </button>
              <button
                type="button"
                className={`px-2 py-1 rounded-md ${
                  preset === "custom" ? "bg-background text-foreground shadow" : ""
                }`}
                onClick={() => setPreset("custom")}
              >
                Özel aralık
              </button>
            </div>
            <div className="flex gap-2 items-center text-xs">
              <Input
                type="date"
                className="h-8 w-32"
                value={formatDate(startDate, "yyyy-MM-dd")}
                onChange={(e) => {
                  const d = new Date(e.target.value);
                  if (!Number.isNaN(d.getTime())) setStartDate(d);
                }}
              />
              <span>→</span>
              <Input
                type="date"
                className="h-8 w-32"
                value={formatDate(endDate, "yyyy-MM-dd")}
                onChange={(e) => {
                  const d = new Date(e.target.value);
                  if (!Number.isNaN(d.getTime())) setEndDate(d);
                }}
              />
              <Button type="button" size="sm" className="text-xs" onClick={loadAll} disabled={loading}>
                {loading ? "Yükleniyor..." : "Uygula"}
              </Button>
            </div>
          </div>
        </CardHeader>
        {error && (
          <CardContent>
            <div className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-xs text-destructive">
              <AlertCircle className="h-4 w-4 mt-0.5" />
              <div>{error}</div>
            </div>
          </CardContent>
        )}
      </Card>

      {/* KPI kartları */}
      <div className="grid grid-cols-1 gap-3 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-1">
            <CardTitle className="flex items-center gap-2 text-sm font-medium">
              <DollarSign className="h-4 w-4" /> Toplam Ciro
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-1 text-sm">
            <div className="text-2xl font-bold">{formatMoney(kpi.sellTotal, kpi.currency)}</div>
            <div className="text-xs text-muted-foreground">
              Net: {formatMoney(kpi.netTotal, kpi.currency)}  b7 Marj: {formatMoney(kpi.markupTotal, kpi.currency)}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-1">
            <CardTitle className="flex items-center gap-2 text-sm font-medium">
              <BarChart2 className="h-4 w-4" /> Toplam Rezervasyon
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-1 text-sm">
            <div className="text-2xl font-bold">{kpi.totalBookings}</div>
            <div className="text-xs text-muted-foreground">
              İptal: {kpi.cancelled} ({kpi.cancelRate.toFixed(1)}%)
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-1">
            <CardTitle className="flex items-center gap-2 text-sm font-medium">
              <TrendingUp className="h-4 w-4" /> B2B Kredi Riski
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-1 text-sm">
            <div className="text-2xl font-bold">{formatMoney(kpi.totalExposure, "EUR")}</div>
            <div className="text-xs text-muted-foreground">
              Limit: {formatMoney(kpi.totalCreditLimit, "EUR")}  b7 Limit aşımı: {kpi.overLimitCount}  b7 Limite yakın: {kpi.nearLimitCount}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-1">
            <CardTitle className="flex items-center gap-2 text-sm font-medium">
              <CreditCard className="h-4 w-4" /> Tedarikçi Bakiyesi
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-1 text-sm">
            <div className="text-2xl font-bold">{formatMoney(kpi.supplierTotal, kpi.supplierCurrency)}</div>
            <div className="text-xs text-muted-foreground">
              Tedarikçi sayısı: {kpi.supplierCount}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Grafikler satırı */}
      <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
        <Card className="h-[280px]">
          <CardHeader className="pb-1">
            <CardTitle className="flex items-center gap-2 text-sm font-medium">
              <LineChart className="h-4 w-4" /> Günlük Rezervasyon Trendleri
            </CardTitle>
          </CardHeader>
          <CardContent className="h-[220px] pt-2">
            {trendData.length === 0 ? (
              <p className="text-xs text-muted-foreground">Seçilen dönemde rezervasyon bulunmuyor.</p>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={trendData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis dataKey="date" tick={{ fontSize: 10 }} />
                  <YAxis tick={{ fontSize: 10 }} allowDecimals={false} />
                  <Tooltip />
                  <Line type="monotone" dataKey="confirmed" stroke="#16a34a" strokeWidth={2} dot={false} name="Onaylanan" />
                  <Line type="monotone" dataKey="cancelled" stroke="#dc2626" strokeWidth={2} dot={false} name="İptal" />
                </LineChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        <Card className="h-[280px]">
          <CardHeader className="pb-1">
            <CardTitle className="flex items-center gap-2 text-sm font-medium">
              <PieChart className="h-4 w-4" /> Top Ürünler (Ciroya göre)
            </CardTitle>
          </CardHeader>
          <CardContent className="h-[220px] pt-2">
            {topProducts.length === 0 ? (
              <p className="text-xs text-muted-foreground">Bu dönemde ürün bazlı satış verisi bulunamadı.</p>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={topProducts} margin={{ top: 10, right: 10, left: 0, bottom: 0 }} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis type="number" tick={{ fontSize: 10 }} />
                  <YAxis
                    type="category"
                    dataKey="product_id"
                    tick={{ fontSize: 10 }}
                    width={120}
                  />
                  <Tooltip formatter={(value) => formatMoney(value, "EUR")} />
                  <Bar dataKey="sell_total" fill="#0f766e" name="Ciro" />
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Alt tablo: tedarikçi veya B2B özetini genişletmek için yer bırakıyoruz */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Notlar</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-xs text-muted-foreground">
            Bu dashboard ilk versiyonunda toplam ciro, rezervasyon adedi, iptal oranı, B2B kredi riski ve
            tedarikçi bakiyesini özetler. İlerleyen aşamalarda acenta bazlı top-5 listeleri ve daha detaylı
            grafikler eklenebilir.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
