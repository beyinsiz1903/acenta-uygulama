import React, { useEffect, useMemo, useState } from "react";
import { StatCard } from "../components/StatCard";
import { TrendChart } from "../components/TrendChart";
import { api, apiErrorMessage } from "../lib/api";

function formatHours(v) {
  if (v == null || Number.isNaN(Number(v))) return "—";
  const n = Number(v);
  if (n < 1) return `${Math.round(n * 60)} dk`;
  return `${n.toFixed(2)} saat`;
}

function normalizePeriod(overview, fallbackDays) {
  const period = overview?.period;
  if (period && typeof period.days === "number") {
    return {
      start: period.start || null,
      end: period.end || null,
      days: period.days,
    };
  }

  // Backward compatibility: older responses may only have period_days
  const days = overview?.period_days ?? fallbackDays ?? 7;
  return {
    start: null,
    end: null,
    days,
  };
}

function buildMetricsQuery(range) {
  if (!range) {
    return "?days=7";
  }

  if (range.mode === "custom" && range.start && range.end) {
    return `?start=${range.start}&end=${range.end}`;
  }

  const days = range.days || 7;
  return `?days=${days}`;
}

function toCsv(fieldnames, rows) {
  if (!rows || rows.length === 0) return "";

  const escape = (value) => {
    if (value == null) return "";
    const str = String(value);
    if (str.includes(";") || str.includes("\"") || str.includes("\n")) {
      return `"${str.replace(/"/g, '""')}"`;
    }
    return str;
  };

  const header = fieldnames.join(";");
  const body = rows
    .map((row) => fieldnames.map((name) => escape(row[name])).join(";"))
    .join("\n");

  return `${header}\n${body}`;
}

function triggerCsvDownload(filename, csv) {
  if (!csv) return;
  try {
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  } catch (e) {
    // Best-effort; CSV export is non-critical
    // eslint-disable-next-line no-console
    console.error("CSV export failed", e);
  }
}

export default function AdminMetricsPage() {
  const [overview, setOverview] = useState(null);
  const [trends, setTrends] = useState(null);

  // Shared date range state (FAZ-12.1)
  const [presetDays, setPresetDays] = useState(7); // UI preset selection
  const [rangeMode, setRangeMode] = useState("preset"); // "preset" | "custom"
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [appliedRange, setAppliedRange] = useState({ mode: "preset", days: 7 });

  // Last updated timestamp
  const [lastUpdated, setLastUpdated] = useState(null);

  // FAZ-11: Insights state
  const [queues, setQueues] = useState(null);
  const [funnel, setFunnel] = useState(null);
  const [activeTab, setActiveTab] = useState("slow"); // "slow" | "noted"
  const [followedBookings, setFollowedBookings] = useState(new Set());

  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [seeding, setSeeding] = useState(false);

  async function load(nextRange) {
    const range = nextRange || appliedRange;
    const overviewQuery = buildMetricsQuery(range);
    const trendsQuery = buildMetricsQuery(range);
    const daysForInsights = range && range.days ? range.days : 30;

    setErr("");
    setLoading(true);
    try {
      const [o, t, q, f] = await Promise.all([
        api.get(`/admin/metrics/overview${overviewQuery}`),
        api.get(`/admin/metrics/trends${trendsQuery}`),
        api.get(`/admin/insights/queues?days=${daysForInsights}&slow_hours=24&limit=50`),
        api.get(`/admin/insights/funnel?days=${daysForInsights}`),
      ]);
      setOverview(o.data);
      setTrends(t.data);
      setQueues(q.data);
      setFunnel(f.data);
      setLastUpdated(new Date().toISOString());
    } catch (e) {
      setErr(apiErrorMessage ? apiErrorMessage(e) : (e?.message || "Bir hata oluştu"));
    } finally {
      setLoading(false);
    }
  }

  async function seedDemoData() {
    if (!window.confirm("Demo verisi oluşturulsun mu? (Mevcut demo verisi silinecek)")) {
      return;
    }

    setSeeding(true);
    setErr("");
    try {
      const res = await api.post("/admin/demo/seed-bookings", {
        count: 20,
        days_back: 14,
        wipe_existing_seed: true,
      });

      if (res.data?.ok) {
        // Reload metrics
        await load();
        alert(`✅ Demo verisi oluşturuldu!\n${res.data.inserted} kayıt eklendi.`);
      }
    } catch (e) {
      setErr(apiErrorMessage ? apiErrorMessage(e) : (e?.message || "Demo verisi oluşturulamadı"));
    } finally {
      setSeeding(false);
    }
  }

  useEffect(() => {
    // Initial load with default range
    void load({ mode: "preset", days: 7 });
    setAppliedRange({ mode: "preset", days: 7 });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // FAZ-11: Load followed bookings from localStorage
  useEffect(() => {
    const followed = new Set();
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key && key.startsWith("admin_follow_booking:")) {
        const bookingId = key.replace("admin_follow_booking:", "");
        followed.add(bookingId);
      }
    }
    setFollowedBookings(followed);
  }, []);

  const normalizedPeriod = useMemo(() => normalizePeriod(overview, appliedRange.days || 7), [overview, appliedRange]);

  // FAZ-11: Toggle follow status
  function toggleFollow(bookingId) {
    const key = `admin_follow_booking:${bookingId}`;
    const isFollowed = followedBookings.has(bookingId);

    if (isFollowed) {
      localStorage.removeItem(key);
      setFollowedBookings((prev) => {
        const next = new Set(prev);
        next.delete(bookingId);
        return next;
      });
    } else {
      localStorage.setItem(key, "1");
      setFollowedBookings((prev) => new Set(prev).add(bookingId));
    }
  }

  // FAZ-11: WhatsApp follow message
  function openWhatsAppFollow(booking) {
    const hotelName = booking.hotel_name || booking.hotel_id || "Otel";
    const ageHours = booking.age_hours || 0;
    // Use text instead of emojis for better URL encoding
    const message = `Takip: ${booking.booking_id}\nOtel: ${hotelName}\nBekliyor: ${ageHours.toFixed(1)} saat`;
    const url = `https://wa.me/?text=${encodeURIComponent(message)}`;
    window.open(url, "_blank", "noopener,noreferrer");
  }

  const cards = useMemo(() => {
    const b = overview?.bookings || {};
    return {
      total: b.total ?? 0,
      pending: b.pending ?? 0,
      confirmed: b.confirmed ?? 0,
      cancelled: b.cancelled ?? 0,
      avg: overview?.avg_approval_time_hours ?? null,
      notesPct: overview?.bookings_with_notes_pct ?? 0,
    };
  }, [overview]);

  const topHotels = overview?.top_hotels || [];
  const trendData = trends?.daily_trends || [];

  return (
    <div className="p-4 md:p-6">
      <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-3">
        <div>
          <div className="text-xl font-semibold">📊 Dashboard Metrikleri</div>
          <div className="text-sm text-muted-foreground">
            Admin / Super Admin için rezervasyon operasyon metrikleri
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            className="ml-2 h-9 rounded-md border bg-background px-3 text-sm"
            onClick={() => void load()}
            disabled={loading}
          >
            {loading ? "Yükleniyor..." : "Yenile"}
          </button>

          <button
            type="button"
            className="ml-2 h-9 rounded-md border border-amber-500/30 bg-amber-500/10 hover:bg-amber-500/20 px-3 text-sm font-medium"
            onClick={() => void seedDemoData()}
            disabled={seeding || loading}
            data-testid="metrics-seed-demo"
            title="Demo verisi oluştur (20 kayıt)"
          >
            {seeding ? "Oluşturuluyor..." : "🎲 Demo Verisi"}
          </button>
        </div>
      </div>

      {err ? (
        <div className="mt-4 rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
          {err}
        </div>
      ) : null}

      <div className="mt-5 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <StatCard
          title="Toplam"
          value={cards.total}
          subtitle={normalizedPeriod.start && normalizedPeriod.end
            ? `${normalizedPeriod.start} → ${normalizedPeriod.end}`
            : `Son ${normalizedPeriod.days} gün`}
          testId="metrics-stat-total"
        />
        <StatCard
          title="Beklemede"
          value={cards.pending}
          subtitle="pending"
          testId="metrics-stat-pending"
        />
        <StatCard
          title="Onaylı"
          value={cards.confirmed}
          subtitle="confirmed"
          testId="metrics-stat-confirmed"
        />
        <StatCard
          title="Ortalama Onay"
          value={formatHours(cards.avg)}
          subtitle={`Notlu: %${cards.notesPct}`}
          testId="metrics-stat-avg-time"
        />
      </div>

      {/* Date Range Controls (FAZ-12.1) */}
      <div className="mt-4 flex flex-col md:flex-row md:items-center md:justify-between gap-3">
        <div className="text-xs text-muted-foreground">
          <div>
            Dönem: {normalizedPeriod.start && normalizedPeriod.end
              ? `${normalizedPeriod.start} → ${normalizedPeriod.end}`
              : `Son ${normalizedPeriod.days} gün`}
          </div>
          <div data-testid="metrics-last-updated">
            Son güncelleme: {lastUpdated ? new Date(lastUpdated).toLocaleString() : "—"}
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <div className="flex items-center gap-1 text-xs text-muted-foreground">
            <span>Preset:</span>
            {[7, 14, 30, 90].map((d) => (
              <button
                key={d}
                type="button"
                className={`px-2 py-1 rounded border text-xs ${
                  presetDays === d ? "bg-primary text-primary-foreground" : "bg-background hover:bg-muted"
                }`}
                onClick={() => {
                  setRangeMode("preset");
                  setPresetDays(d);
                  const next = { mode: "preset", days: d };
                  setAppliedRange(next);
                  void load(next);
                }}
              >
                {d}g
              </button>
            ))}
          </div>

          <div className="flex items-center gap-2 text-xs">
            <span>Custom:</span>
            <input
              type="date"
              className="h-8 rounded-md border bg-background px-2 text-xs"
              value={startDate}
              onChange={(e) => {
                setRangeMode("custom");
                setStartDate(e.target.value);
              }}
              data-testid="metrics-range-start"
            />
            <span>-</span>
            <input
              type="date"
              className="h-8 rounded-md border bg-background px-2 text-xs"
              value={endDate}
              onChange={(e) => {
                setRangeMode("custom");
                setEndDate(e.target.value);
              }}
              data-testid="metrics-range-end"
            />
            <button
              type="button"
              className="h-8 rounded-md border bg-background px-2 text-xs"
              onClick={() => {
                if (startDate && endDate) {
                  const next = { mode: "custom", start: startDate, end: endDate };
                  setAppliedRange(next);
                  void load(next);
                }
              }}
              disabled={!startDate || !endDate || loading}
              data-testid="metrics-range-apply"
            >
              Uygula
            </button>
            <button
              type="button"
              className="h-8 rounded-md border bg-background px-2 text-xs"
              onClick={() => {
                setStartDate("");
                setEndDate("");
                setRangeMode("preset");
                const next = { mode: "preset", days: 7 };
                setPresetDays(7);
                setAppliedRange(next);
                void load(next);
              }}
              disabled={loading}
              data-testid="metrics-range-clear"
            >
              Temizle
            </button>
          </div>
        </div>
      </div>

      {/* FAZ-11: Operational Insights */}
      <div className="mt-5 grid grid-cols-1 sm:grid-cols-3 gap-3">
        <StatCard
          title="⏳ Yavaş Onaylar"
          value={queues?.slow_pending?.length || 0}
          subtitle="24+ saat bekliyor"
          testId="metrics-insight-slow-count"
        />
        <StatCard
          title="📝 Notlu Talepler"
          value={queues?.noted_pending?.length || 0}
          subtitle="not içeren pending"
          testId="metrics-insight-noted-count"
        />
        <StatCard
          title="📈 Dönüşüm Oranı"
          value={`%${funnel?.conversion_pct || 0}`}
          subtitle={`${funnel?.confirmed || 0} / ${funnel?.total || 0} confirmed`}
          testId="metrics-funnel-conversion"
        />
      </div>

      {/* FAZ-11: Action Queue Table */}
      {queues && (queues.slow_pending?.length > 0 || queues.noted_pending?.length > 0) && (
        <div className="mt-5 rounded-xl border bg-card p-4">
          <div className="flex items-center gap-3 border-b pb-3">
            <button
              type="button"
              className={`px-3 py-1.5 text-sm font-medium rounded-md ${
                activeTab === "slow"
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:text-foreground"
              }`}
              onClick={() => setActiveTab("slow")}
            >
              ⏳ Yavaş Onaylar ({queues.slow_pending?.length || 0})
            </button>
            <button
              type="button"
              className={`px-3 py-1.5 text-sm font-medium rounded-md ${
                activeTab === "noted"
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:text-foreground"
              }`}
              onClick={() => setActiveTab("noted")}
            >
              📝 Notlu Talepler ({queues.noted_pending?.length || 0})
            </button>
          </div>

          <div className="mt-4 overflow-x-auto">
            <table
              className="w-full text-sm"
              data-testid={activeTab === "slow" ? "metrics-queue-slow-table" : "metrics-queue-noted-table"}
            >
              <thead>
                <tr className="border-b">
                  <th className="text-left py-2 px-2 font-medium">Otel</th>
                  <th className="text-left py-2 px-2 font-medium">Booking ID</th>
                  <th className="text-left py-2 px-2 font-medium">Yaş (saat)</th>
                  <th className="text-left py-2 px-2 font-medium">Takip</th>
                  <th className="text-left py-2 px-2 font-medium">Aksiyon</th>
                </tr>
              </thead>
              <tbody>
                {(activeTab === "slow" ? queues.slow_pending : queues.noted_pending)?.map((booking) => {
                  const isFollowed = followedBookings.has(booking.booking_id);
                  return (
                    <tr key={booking.booking_id} className="border-b last:border-0 hover:bg-muted/50">
                      <td className="py-2 px-2">
                        <div className="font-medium">{booking.hotel_name || booking.hotel_id}</div>
                        <div className="text-xs text-muted-foreground">{booking.hotel_id}</div>
                      </td>
                      <td className="py-2 px-2">
                        <button
                          type="button"
                          className="text-xs font-mono hover:underline"
                          onClick={() => navigator.clipboard.writeText(booking.booking_id)}
                          title="Kopyala"
                        >
                          {booking.booking_id.slice(0, 8)}...
                        </button>
                      </td>
                      <td className="py-2 px-2">
                        <span className={booking.age_hours > 48 ? "text-destructive font-semibold" : ""}>
                          {booking.age_hours.toFixed(1)}h
                        </span>
                      </td>
                      <td className="py-2 px-2">
                        <button
                          type="button"
                          className="text-lg hover:scale-110 transition-transform"
                          onClick={() => toggleFollow(booking.booking_id)}
                          data-testid="metrics-follow-toggle"
                          title={isFollowed ? "Takipten çıkar" : "Takibe al"}
                        >
                          {isFollowed ? "⭐" : "☆"}
                        </button>
                      </td>
                      <td className="py-2 px-2">
                        <button
                          type="button"
                          className="px-2 py-1 text-xs rounded border hover:bg-muted"
                          onClick={() => openWhatsAppFollow(booking)}
                          data-testid="metrics-wa-follow"
                          title="WhatsApp ile takip"
                        >
                          💬 WhatsApp
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <div className="mt-4 grid grid-cols-1 lg:grid-cols-3 gap-3">
        <div className="lg:col-span-2">
          <TrendChart data={trendData} testId="metrics-trend-chart" />
        </div>

        <div className="rounded-xl border bg-card p-4" data-testid="metrics-top-hotels">
          <div className="text-sm font-medium">🏨 En Çok Rezervasyon Alan Oteller</div>
          <div className="mt-1 text-xs text-muted-foreground">
            {normalizedPeriod.start && normalizedPeriod.end
              ? `${normalizedPeriod.start} → ${normalizedPeriod.end}`
              : `Son ${normalizedPeriod.days} gün`}
          </div>

      {/* CSV Export Buttons (FAZ-12.1) */}
      <div className="mt-4 flex flex-wrap gap-2">
        <button
          type="button"
          className="h-8 rounded-md border bg-background px-3 text-xs"
          onClick={() => {
            if (!overview) return;
            const period = normalizedPeriod;
            const headers = [
              "period_start",
              "period_end",
              "period_days",
              "total",
              "pending",
              "confirmed",
              "cancelled",
              "avg_approval_hours",
              "bookings_with_notes_pct",
            ];
            const row = {
              period_start: period.start || "",
              period_end: period.end || "",
              period_days: period.days,
              total: cards.total,
              pending: cards.pending,
              confirmed: cards.confirmed,
              cancelled: cards.cancelled,
              avg_approval_hours: cards.avg ?? "",
              bookings_with_notes_pct: cards.notesPct ?? "",
            };
            const csv = toCsv(headers, [row]);
            triggerCsvDownload("admin-metrics-overview.csv", csv);
          }}
          data-testid="metrics-export-overview"
        >
          Export Overview CSV
        </button>

        <button
          type="button"
          className="h-8 rounded-md border bg-background px-3 text-xs"
          onClick={() => {
            if (!trends || !trends.daily_trends) return;
            const period = normalizedPeriod;
            const headers = [
              "period_start",
              "period_end",
              "period_days",
              "date",
              "pending",
              "confirmed",
              "cancelled",
              "total",
            ];
            const rows = trends.daily_trends.map((d) => ({
              period_start: period.start || "",
              period_end: period.end || "",
              period_days: period.days,
              date: d.date,
              pending: d.pending,
              confirmed: d.confirmed,
              cancelled: d.cancelled,
              total: d.total,
            }));
            const csv = toCsv(headers, rows);
            triggerCsvDownload("admin-metrics-trends.csv", csv);
          }}
          data-testid="metrics-export-trends"
        >
          Export Trends CSV
        </button>

        <button
          type="button"
          className="h-8 rounded-md border bg-background px-3 text-xs"
          onClick={() => {
            if (!queues) return;
            const period = normalizedPeriod;
            const headers = [
              "queue_type",
              "period_start",
              "period_end",
              "period_days",
              "booking_id",
              "hotel_id",
              "hotel_name",
              "age_hours",
              "has_note",
            ];
            const rows = [];
            (queues.slow_pending || []).forEach((b) => {
              rows.push({
                queue_type: "slow_pending",
                period_start: period.start || "",
                period_end: period.end || "",
                period_days: period.days,
                booking_id: b.booking_id,
                hotel_id: b.hotel_id,
                hotel_name: b.hotel_name,
                age_hours: b.age_hours,
                has_note: b.has_note,
              });
            });
            (queues.noted_pending || []).forEach((b) => {
              rows.push({
                queue_type: "noted_pending",
                period_start: period.start || "",
                period_end: period.end || "",
                period_days: period.days,
                booking_id: b.booking_id,
                hotel_id: b.hotel_id,
                hotel_name: b.hotel_name,
                age_hours: b.age_hours,
                has_note: b.has_note,
              });
            });
            const csv = toCsv(headers, rows);
            triggerCsvDownload("admin-metrics-queues.csv", csv);
          }}
          data-testid="metrics-export-queues"
        >
          Export Queues CSV
        </button>
      </div>

          <div className="mt-4 space-y-2">
            {topHotels.length === 0 ? (
              <div className="text-sm text-muted-foreground py-8 text-center">
                Henüz veri yok.
              </div>
            ) : (
              topHotels.map((h, idx) => (
                <div
                  key={h.hotel_id || idx}
                  className="flex items-center justify-between rounded-lg border bg-background px-3 py-2"
                >
                  <div className="min-w-0">
                    <div className="text-sm font-medium truncate">
                      {idx + 1}. {h.hotel_name || h.hotel_id}
                    </div>
                    <div className="text-[11px] text-muted-foreground truncate">
                      {h.hotel_id}
                    </div>
                  </div>
                  <div className="text-sm font-semibold">{h.count}</div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      <div className="mt-4 text-[11px] text-muted-foreground">
        Not: Bu ekran read-only&apos;dır. Metrikler booking kayıtlarından hesaplanır.
      </div>
    </div>
  );
}
