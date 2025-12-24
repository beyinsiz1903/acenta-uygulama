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

export default function AdminMetricsPage() {
  const [daysOverview, setDaysOverview] = useState(7);
  const [daysTrends, setDaysTrends] = useState(30);

  const [overview, setOverview] = useState(null);
  const [trends, setTrends] = useState(null);
  
  // FAZ-11: Insights state
  const [queues, setQueues] = useState(null);
  const [funnel, setFunnel] = useState(null);
  const [activeTab, setActiveTab] = useState("slow"); // "slow" | "noted"
  const [followedBookings, setFollowedBookings] = useState(new Set());

  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [seeding, setSeeding] = useState(false);

  async function load() {
    setErr("");
    setLoading(true);
    try {
      const [o, t] = await Promise.all([
        api.get(`/admin/metrics/overview?days=${daysOverview}`),
        api.get(`/admin/metrics/trends?days=${daysTrends}`),
      ]);
      setOverview(o.data);
      setTrends(t.data);
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
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [daysOverview, daysTrends]);

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
          <label className="text-xs text-muted-foreground">Overview</label>
          <select
            className="h-9 rounded-md border bg-background px-2 text-sm"
            value={daysOverview}
            onChange={(e) => setDaysOverview(Number(e.target.value))}
          >
            <option value={7}>7 gün</option>
            <option value={14}>14 gün</option>
            <option value={30}>30 gün</option>
            <option value={90}>90 gün</option>
          </select>

          <label className="ml-2 text-xs text-muted-foreground">Trend</label>
          <select
            className="h-9 rounded-md border bg-background px-2 text-sm"
            value={daysTrends}
            onChange={(e) => setDaysTrends(Number(e.target.value))}
          >
            <option value={7}>7 gün</option>
            <option value={14}>14 gün</option>
            <option value={30}>30 gün</option>
            <option value={90}>90 gün</option>
          </select>

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
          subtitle={`Son ${overview?.period_days ?? daysOverview} gün`}
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

      <div className="mt-4 grid grid-cols-1 lg:grid-cols-3 gap-3">
        <div className="lg:col-span-2">
          <TrendChart data={trendData} testId="metrics-trend-chart" />
        </div>

        <div className="rounded-xl border bg-card p-4" data-testid="metrics-top-hotels">
          <div className="text-sm font-medium">🏨 En Çok Rezervasyon Alan Oteller</div>
          <div className="mt-1 text-xs text-muted-foreground">
            Son {overview?.period_days ?? daysOverview} gün
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
