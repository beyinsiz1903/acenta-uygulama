import React, { useCallback, useMemo, useState } from "react";
import { BarChart3, Download, Loader2, Search, Sparkles, TrendingUp } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useQuery, useMutation } from "@tanstack/react-query";

import { api, apiErrorMessage } from "../lib/api";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Input } from "../components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table";
import EmptyState from "../components/EmptyState";
import { PageShell } from "../design-system";
import { toast } from "sonner";

const REPORT_DAY_OPTIONS = [7, 30, 90];

const formatTRY = (amount) => new Intl.NumberFormat("tr-TR", {
  style: "currency",
  currency: "TRY",
  maximumFractionDigits: 0,
}).format(Number(amount || 0));

function ReportKpiCard({ title, value, subtitle, testId }) {
  return (
    <div className="rounded-[1.5rem] border bg-card/90 p-4 shadow-sm" data-testid={testId}>
      <div className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">{title}</div>
      <div className="mt-3 text-3xl font-semibold tracking-tight text-foreground">{value}</div>
      <div className="mt-1 text-sm text-muted-foreground">{subtitle}</div>
    </div>
  );
}

function SearchResultGroup({ title, items, onOpen, testId }) {
  return (
    <div className="space-y-2" data-testid={testId}>
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-foreground">{title}</h3>
        <span className="text-xs text-muted-foreground">{items.length} sonuç</span>
      </div>
      <div className="space-y-2">
        {items.map((item) => (
          <button
            key={`${item.type}-${item.id}`}
            type="button"
            onClick={() => onOpen(item)}
            className="w-full rounded-2xl border bg-background/70 px-4 py-3 text-left transition-colors hover:border-primary/30 hover:bg-primary/5"
            data-testid={`search-result-${item.type}-${item.id}`}
          >
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-foreground">{item.title}</p>
                {item.subtitle ? <p className="truncate text-xs text-muted-foreground">{item.subtitle}</p> : null}
              </div>
              {item.amount ? <span className="text-xs font-medium text-foreground">{formatTRY(item.amount)}</span> : null}
            </div>
            {item.description ? <p className="mt-2 text-xs text-muted-foreground">{item.description}</p> : null}
          </button>
        ))}
      </div>
    </div>
  );
}

export default function AdvancedReportsPage() {
  const navigate = useNavigate();
  const [days, setDays] = useState(30);
  const [overview, setOverview] = useState(null);
  const [overviewError, setOverviewError] = useState("");
  const [overviewLoading, setOverviewLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState(null);
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchError, setSearchError] = useState("");

  const { data: reportData, error: fetchError } = useQuery({
    queryKey: ["reports", "summary", days],
    queryFn: async () => {
      const [a, b] = await Promise.all([
        api.get("/reports/reservations-summary"),
        api.get("/reports/sales-summary", { params: { days } }),
      ]);
      return { resSummary: a.data || [], sales: b.data || [] };
    },
    staleTime: 60_000,
    retry: (count, err) => err?.response?.status === 404 ? false : count < 2,
  });
  const resSummary = reportData?.resSummary || [];
  const sales = reportData?.sales || [];
  const error = fetchError ? (fetchError?.response?.status === 404 ? "" : apiErrorMessage(fetchError)) : "";

  const generateOverview = useCallback(async () => {
    setOverviewLoading(true);
    setOverviewError("");
    try {
      const response = await api.get("/reports/generate", { params: { days } });
      setOverview(response.data || null);
    } catch (e) {
      setOverviewError(apiErrorMessage(e));
      setOverview(null);
    } finally {
      setOverviewLoading(false);
    }
  }, [days]);

  const runSearch = useCallback(async () => {
    if (!searchQuery.trim()) {
      setSearchError("Arama yapmak için en az 2 karakter girin.");
      setSearchResults(null);
      return;
    }
    setSearchLoading(true);
    setSearchError("");
    try {
      const response = await api.get("/search", {
        params: {
          q: searchQuery.trim(),
          limit: 4,
        },
      });
      setSearchResults(response.data || null);
    } catch (e) {
      setSearchError(apiErrorMessage(e));
      setSearchResults(null);
    } finally {
      setSearchLoading(false);
    }
  }, [searchQuery]);

  async function downloadCsv() {
    try {
      const resp = await api.get("/reports/sales-summary.csv", { params: { days }, responseType: "blob" });
      const blob = new Blob([resp.data], { type: "text/csv" });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `sales-summary-${days}d.csv`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      toast.error(apiErrorMessage(e));
    }
  }

  const searchSections = useMemo(() => {
    if (!searchResults?.sections) return [];
    return [
      { key: "customers", title: "Müşteriler", items: searchResults.sections.customers || [] },
      { key: "bookings", title: "Rezervasyonlar", items: searchResults.sections.bookings || [] },
      { key: "hotels", title: "Oteller", items: searchResults.sections.hotels || [] },
      { key: "tours", title: "Turlar", items: searchResults.sections.tours || [] },
    ].filter((section) => section.items.length > 0);
  }, [searchResults]);

  const recentBookings = overview?.recent_bookings || [];
  const dailyRevenue = overview?.daily_revenue || [];
  const maxRevenue = Math.max(...dailyRevenue.map((entry) => entry.revenue || 0), 1);

  return (
    <PageShell
      title="Raporlar"
      description="Operasyon içinde arama yapın, satış özetini indirin ve seçili dönem için tek ekranda yönetim özeti oluşturun."
      actions={
        <div className="flex flex-wrap items-center gap-2" data-testid="reports-day-filter-group">
          {REPORT_DAY_OPTIONS.map((option) => (
            <Button
              key={option}
              type="button"
              variant={days === option ? "default" : "outline"}
              onClick={() => setDays(option)}
              size="sm"
              className="text-xs"
              data-testid={`reports-day-filter-${option}`}
            >
              Son {option} gün
            </Button>
          ))}
          <Button variant="outline" onClick={downloadCsv} className="gap-2" size="sm" data-testid="export-csv">
            <Download className="h-3.5 w-3.5" /> CSV
          </Button>
        </div>
      }
    >
    <div className="space-y-6" data-testid="reports-page">

      {error ? (
        <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700" data-testid="reports-error">
          {error}
        </div>
      ) : null}

      <Card className="rounded-[2rem] border bg-card/95 shadow-sm" data-testid="global-search-card">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Search className="h-4 w-4 text-muted-foreground" />
            Hızlı operasyon araması
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-col gap-3 md:flex-row">
            <Input
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
              placeholder="Müşteri, rezervasyon, otel veya tur ara..."
              data-testid="global-search-input"
            />
            <Button
              type="button"
              onClick={runSearch}
              disabled={searchLoading}
              className="gap-2"
              data-testid="global-search-submit-button"
            >
              {searchLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
              Ara
            </Button>
          </div>
          {searchError ? <p className="text-sm text-rose-600" data-testid="global-search-error">{searchError}</p> : null}
          {!searchResults && !searchError ? (
            <p className="text-sm text-muted-foreground" data-testid="global-search-empty-state">Arama kutusu CRM, rezervasyon, otel ve tur kayıtlarını tek yerden tarar.</p>
          ) : null}
          {searchResults ? (
            <div className="space-y-4" data-testid="global-search-results">
              <div className="rounded-2xl border bg-muted/20 px-4 py-3 text-sm text-muted-foreground" data-testid="global-search-summary">
                <strong className="text-foreground">{searchResults.total_results}</strong> sonuç bulundu · kapsam: {searchResults.scope}
              </div>
              {searchSections.length === 0 ? (
                <EmptyState
                  title="Eşleşen kayıt bulunamadı"
                  description="Daha farklı bir anahtar kelime veya rezervasyon referansı deneyin."
                />
              ) : (
                <div className="grid gap-4 xl:grid-cols-2">
                  {searchSections.map((section) => (
                    <SearchResultGroup
                      key={section.key}
                      title={section.title}
                      items={section.items}
                      testId={`global-search-group-${section.key}`}
                      onOpen={(item) => navigate(item.route || "/app")}
                    />
                  ))}
                </div>
              )}
            </div>
          ) : null}
        </CardContent>
      </Card>

      <Card className="rounded-[2rem] border bg-card/95 shadow-sm" data-testid="generated-report-card">
        <CardHeader className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <CardTitle className="flex items-center gap-2 text-base">
              <Sparkles className="h-4 w-4 text-muted-foreground" />
              Operasyon raporu üret
            </CardTitle>
            <p className="mt-1 text-sm text-muted-foreground">Bu işlem seçili dönem için özet raporu hazırlar ve kullanım hakkınızdan 1 rapor düşer.</p>
          </div>
          <Button
            type="button"
            onClick={generateOverview}
            disabled={overviewLoading}
            className="gap-2"
            data-testid="generate-operations-report-button"
          >
            {overviewLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <TrendingUp className="h-4 w-4" />}
            {overview ? "Raporu yenile" : "Rapor oluştur"}
          </Button>
        </CardHeader>
        <CardContent className="space-y-4">
          {overviewError ? <p className="text-sm text-rose-600" data-testid="generated-report-error">{overviewError}</p> : null}
          {!overview && !overviewLoading ? (
            <EmptyState
              title="Henüz operasyon raporu üretilmedi"
              description="KPI, ödeme sağlığı, en güçlü oteller ve son rezervasyonları görmek için yukarıdaki butonu kullanın."
            />
          ) : null}
          {overview ? (
            <>
              <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
                <ReportKpiCard
                  title="Toplam rezervasyon"
                  value={overview.kpis?.booking_count || 0}
                  subtitle={`${overview.period?.start} → ${overview.period?.end}`}
                  testId="generated-report-booking-count"
                />
                <ReportKpiCard
                  title="Toplam ciro"
                  value={formatTRY(overview.kpis?.revenue_total || 0)}
                  subtitle="İptal dışı kayıtlar"
                  testId="generated-report-revenue"
                />
                <ReportKpiCard
                  title="Ortalama rezervasyon"
                  value={formatTRY(overview.kpis?.avg_booking_value || 0)}
                  subtitle="Rezervasyon başına gelir"
                  testId="generated-report-average"
                />
                <ReportKpiCard
                  title="Aktif müşteri"
                  value={overview.kpis?.active_customer_count || 0}
                  subtitle={`Onaylı: ${overview.kpis?.confirmed_count || 0} · İptal: ${overview.kpis?.cancelled_count || 0}`}
                  testId="generated-report-customers"
                />
              </div>

              <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
                <div className="rounded-[1.5rem] border bg-background/70 p-4" data-testid="generated-report-daily-revenue">
                  <div className="mb-4 flex items-center justify-between">
                    <h3 className="text-sm font-semibold text-foreground">Günlük gelir akışı</h3>
                    <span className="text-xs text-muted-foreground">{dailyRevenue.length} gün</span>
                  </div>
                  <div className="space-y-3">
                    {dailyRevenue.length === 0 ? (
                      <p className="text-sm text-muted-foreground">Bu aralıkta günlük gelir verisi oluşmadı.</p>
                    ) : dailyRevenue.map((entry) => (
                      <div key={entry.day} className="space-y-1" data-testid={`generated-report-day-${entry.day}`}>
                        <div className="flex items-center justify-between text-xs text-muted-foreground">
                          <span>{entry.day}</span>
                          <span>{entry.count} rezervasyon · {formatTRY(entry.revenue)}</span>
                        </div>
                        <div className="h-2 overflow-hidden rounded-full bg-muted">
                          <div className="h-full rounded-full bg-primary" style={{ width: `${Math.max(6, Math.round((entry.revenue / maxRevenue) * 100))}%` }} />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="rounded-[1.5rem] border bg-background/70 p-4" data-testid="generated-report-payment-health">
                  <h3 className="text-sm font-semibold text-foreground">Ödeme sağlığı</h3>
                  <div className="mt-4 space-y-2">
                    {(overview.payment_health || []).map((item) => (
                      <div key={item.status} className="flex items-center justify-between rounded-xl border px-3 py-2 text-sm" data-testid={`generated-report-payment-${item.status}`}>
                        <span className="capitalize text-muted-foreground">{item.status}</span>
                        <span className="font-medium text-foreground">{item.count}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              <div className="grid gap-4 xl:grid-cols-2">
                <Card className="rounded-[1.5rem] border bg-background/70" data-testid="generated-report-top-hotels">
                  <CardHeader>
                    <CardTitle className="text-base">En güçlü oteller</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Otel</TableHead>
                          <TableHead>Rez.</TableHead>
                          <TableHead>Ciro</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {(overview.top_hotels || []).map((hotel) => (
                          <TableRow key={hotel.hotel_name}>
                            <TableCell className="font-medium text-foreground">{hotel.hotel_name}</TableCell>
                            <TableCell>{hotel.booking_count}</TableCell>
                            <TableCell>{formatTRY(hotel.revenue)}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </CardContent>
                </Card>

                <Card className="rounded-[1.5rem] border bg-background/70" data-testid="generated-report-recent-bookings">
                  <CardHeader>
                    <CardTitle className="text-base">Son rezervasyonlar</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {recentBookings.length === 0 ? (
                      <p className="text-sm text-muted-foreground">Bu dönemde rezervasyon kaydı bulunamadı.</p>
                    ) : recentBookings.map((booking) => (
                      <div key={`${booking.source}-${booking.id}`} className="rounded-xl border px-4 py-3" data-testid={`generated-report-booking-${booking.id}`}>
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <p className="text-sm font-medium text-foreground">{booking.reference}</p>
                            <p className="text-xs text-muted-foreground">{booking.hotel_name} · {booking.guest_name}</p>
                          </div>
                          <div className="text-right">
                            <p className="text-sm font-medium text-foreground">{formatTRY(booking.amount)}</p>
                            <p className="text-xs text-muted-foreground">{booking.status}</p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </CardContent>
                </Card>
              </div>
            </>
          ) : null}
        </CardContent>
      </Card>

      <Card className="rounded-2xl shadow-sm">
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
            Satış Özeti
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table data-testid="sales-table">
              <TableHeader>
                <TableRow>
                  <TableHead>Gün</TableHead>
                  <TableHead>Rezervasyon</TableHead>
                  <TableHead>Ciro</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sales.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={3} className="py-6">
                      <EmptyState
                        title="Henüz satış özeti yok"
                        description="Satış raporu oluşturmak için önce rezervasyon ve tahsilat akışını kullanın."
                      />
                    </TableCell>
                  </TableRow>
                ) : (
                  sales.map((r) => (
                    <TableRow key={r.day}>
                      <TableCell className="font-medium text-foreground">{r.day}</TableCell>
                      <TableCell className="text-foreground/80">{r.count}</TableCell>
                      <TableCell className="text-foreground/80">{formatTRY(r.revenue)}</TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      <Card className="rounded-2xl shadow-sm">
        <CardHeader>
          <CardTitle className="text-base">Rezervasyon Durum Dağılımı</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3" data-testid="res-summary">
            {resSummary.length === 0 ? (
              <p className="col-span-2 md:col-span-4 text-xs text-muted-foreground">
                Henüz rezervasyon durum verisi oluşmamış. Rezervasyon oluştukça bu dağılım burada görünecektir.
              </p>
            ) : (
              resSummary.map((r) => (
                <div key={r.status} className="rounded-2xl border bg-card p-3" data-testid={`reservation-summary-${r.status}`}>
                  <div className="text-xs text-muted-foreground">{r.status}</div>
                  <div className="text-2xl font-semibold text-foreground">{r.count}</div>
                </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>
    </div>
    </PageShell>
  );
}