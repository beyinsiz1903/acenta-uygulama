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
  const [campaignUsage, setCampaignUsage] = useState([]);
  const [channelStats, setChannelStats] = useState(null);
  const [topB2BAgencies, setTopB2BAgencies] = useState([]);

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

      const [
        repRes,
        topRes,
        ovRes,
        trendRes,
        suppRes,
        b2bRes,
        campRes,
        channelRes,
        topB2BRes,
      ] = await Promise.all([
        api.get("/admin/reporting/summary", { params: { days: qsDays } }),
        api.get("/admin/reporting/top-products", { params: { days: qsDays, limit: 5, by: "sell" } }),
        api.get("/admin/metrics/overview", { params: { start: startStr, end: endStr } }),
        api.get("/admin/metrics/trends", { params: { start: startStr, end: endStr } }),
        api.get("/ops/finance/suppliers/payable-summary", { params: { currency: "EUR" } }),
        api.get("/admin/b2b/agencies/summary"),
        api.get("/admin/reporting/campaigns-usage", { params: { limit: 5 } }),
        api.get("/admin/metrics/channels", { params: { days: qsDays } }),
        api.get("/admin/reporting/top-b2b-agencies", { params: { days: qsDays, limit: 5 } }),
      ]);

      setReportingSummary(repRes.data || null);
      setTopProducts(topRes.data?.items || []);
      setMetricsOverview(ovRes.data || null);
      setMetricsTrends(trendRes.data?.daily_trends || []);
      setSuppliersSummary(suppRes.data || null);
      setB2bExposure(b2bRes.data?.items || []);
      setCampaignUsage(campRes.data?.items || []);
      setChannelStats(channelRes.data || null);
      setTopB2BAgencies(topB2BRes.data?.items || []);
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
            <div className="inline-flex rounded-lg bg-muted p-1 text-xs text-muted-foreground">
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
      <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
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

        <Card className="h-[280px]">
          <CardHeader className="pb-1">
            <CardTitle className="flex items-center gap-2 text-sm font-medium">
              <BarChart2 className="h-4 w-4" /> Kanal Kırılımı (B2B / B2C)
            </CardTitle>
          </CardHeader>
          <CardContent className="h-[220px] pt-2">
            {!channelStats ? (
              <p className="text-xs text-muted-foreground">Kanal istatistikleri yükleniyor...</p>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={[
                    {
                      channel: "B2B",
                      count: channelStats.channels?.b2b?.count || 0,
                      sell_total: channelStats.channels?.b2b?.sell_total || 0,
                    },
                    {
                      channel: "B2C",
                      count: channelStats.channels?.b2c?.count || 0,
                      sell_total: channelStats.channels?.b2c?.sell_total || 0,
                    },
                  ]}
                  margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis dataKey="channel" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 10 }} allowDecimals={false} />
                  <Tooltip
                    formatter={(value, key) =>
                      key === "sell_total" ? formatMoney(value, "EUR") : value
                    }
                    labelFormatter={(label) => `Kanal: ${label}`}
                  />
                  <Bar dataKey="count" fill="#0f766e" name="Rezervasyon" />
                  <Bar dataKey="sell_total" fill="#f97316" name="Ciro" />
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Top B2B acentalar */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">En Çok Ciro Yapan B2B Acentalar</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-xs">
          {topB2BAgencies.length === 0 ? (
            <p className="text-xs text-muted-foreground">
              Bu dönemde B2B acenta bazlı ciro verisi bulunamadı veya hiç B2B rezervasyon yok.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="text-xs">Acenta</TableHead>
                    <TableHead className="text-xs text-right">Rezervasyon</TableHead>
                    <TableHead className="text-xs text-right">Ciro</TableHead>
                    <TableHead className="text-xs text-right">Marj</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {topB2BAgencies.map((row) => (
                    <TableRow key={row.agency_id}>
                      <TableCell className="text-xs">
                        <div className="flex flex-col">
                          <span className="font-medium truncate max-w-[220px]">
                            {row.agency_name || row.agency_id}
                          </span>
                          <span className="text-2xs font-mono text-muted-foreground">
                            {row.agency_id}
                          </span>
                        </div>
                      </TableCell>
                      <TableCell className="text-xs text-right">{row.bookings}</TableCell>
                      <TableCell className="text-xs text-right">
                        {formatMoney(row.sell_total, "EUR")}
                      </TableCell>
                      <TableCell className="text-xs text-right">
                        {formatMoney(row.markup_total, "EUR")}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Kampanya performansı (kupon kullanımı) */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Kampanya Performansı (Kupon Kullanımı)</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-xs">
          {campaignUsage.length === 0 ? (
            <p className="text-xs text-muted-foreground">
              Bu dönemde kampanya ile ilişkilendirilmiş kupon kullanımı verisi bulunamadı.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="text-xs">Kampanya</TableHead>
                    <TableHead className="text-xs">Slug</TableHead>
                    <TableHead className="text-xs">Kuponlar</TableHead>
                    <TableHead className="text-xs text-right">Toplam kullanım</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {campaignUsage.map((row) => (
                    <TableRow key={row.id}>
                      <TableCell className="text-xs">
                        <div className="flex flex-col">
                          <span className="font-medium truncate max-w-[220px]">{row.name}</span>
                        </div>
                      </TableCell>
                      <TableCell className="text-xs font-mono truncate max-w-[160px]">{row.slug}</TableCell>
                      <TableCell className="text-xs">
                        <div className="flex flex-wrap gap-1">
                          {(row.coupon_codes || []).map((code) => (
                            <span
                              key={code}
                              className="inline-flex items-center rounded-md border bg-muted px-1.5 py-0.5 font-mono text-2xs"
                            >
                              {code}
                            </span>
                          ))}
                        </div>
                      </TableCell>
                      <TableCell className="text-xs text-right font-semibold">
                        {row.total_usage}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
