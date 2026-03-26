/**
 * Hotel Dashboard — Sprint 4
 *
 * Otel operasyon odaklı günlük kontrol paneli.
 *
 * 5 Blok:
 *   1. Bugünkü Check-in / Check-out
 *   2. Doluluk & Müsaitlik
 *   3. Kritik Uyarılar
 *   4. Yaklaşan Varışlar (bekleyen rez & overbooking riski)
 *   5. Son Aktiviteler
 */
import React from "react";
import { Link } from "react-router-dom";
import {
  AlertTriangle,
  ArrowRight,
  BedDouble,
  Calendar,
  CheckCircle2,
  Clock,
  DoorClosed,
  DoorOpen,
  Info,
  LogIn,
  LogOut,
  ShieldCheck,
  TrendingUp,
} from "lucide-react";
import { Skeleton } from "../components/ui/skeleton";
import { getUser } from "../lib/api";
import { useHotelToday } from "../hooks/useHotelDashboard";

function formatMoney(val) {
  if (!val && val !== 0) return "0";
  return Number(val).toLocaleString("tr-TR", { minimumFractionDigits: 0, maximumFractionDigits: 0 });
}

function formatDate(isoStr) {
  if (!isoStr) return "-";
  try {
    return new Date(isoStr).toLocaleDateString("tr-TR", { day: "2-digit", month: "short" });
  } catch { return isoStr; }
}

const ALERT_STYLES = {
  error: { bg: "bg-red-50 dark:bg-red-950/30", border: "border-red-200 dark:border-red-800", icon: AlertTriangle, iconColor: "text-red-500" },
  warning: { bg: "bg-amber-50 dark:bg-amber-950/30", border: "border-amber-200 dark:border-amber-800", icon: AlertTriangle, iconColor: "text-amber-500" },
  info: { bg: "bg-sky-50 dark:bg-sky-950/30", border: "border-sky-200 dark:border-sky-800", icon: Info, iconColor: "text-sky-500" },
};

const STATUS_COLORS = {
  confirmed: "bg-emerald-500/10 text-emerald-600",
  paid: "bg-emerald-500/10 text-emerald-600",
  pending: "bg-amber-500/10 text-amber-600",
  cancelled: "bg-red-500/10 text-red-600",
};

/* ─── Sub-components ─── */

function KpiCard({ icon: Icon, label, value, sub, color = "text-foreground" }) {
  return (
    <div className="rounded-xl border bg-card p-4 flex flex-col gap-1" data-testid={`hotel-kpi-${label.toLowerCase().replace(/\s+/g, "-")}`}>
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <Icon className="h-3.5 w-3.5" />
        <span>{label}</span>
      </div>
      <span className={`text-2xl font-semibold tracking-tight ${color}`}>{value}</span>
      {sub && <span className="text-xs text-muted-foreground">{sub}</span>}
    </div>
  );
}

function AlertCard({ alert }) {
  const s = ALERT_STYLES[alert.type] || ALERT_STYLES.info;
  const Icon = s.icon;
  return (
    <div className={`flex items-start gap-3 rounded-lg border p-3 ${s.bg} ${s.border}`}>
      <Icon className={`h-4 w-4 mt-0.5 shrink-0 ${s.iconColor}`} />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium">{alert.title}</p>
        <p className="text-xs text-muted-foreground mt-0.5">{alert.message}</p>
      </div>
      {alert.action_url && (
        <Link to={alert.action_url} className="text-xs text-primary hover:underline shrink-0 flex items-center gap-1">
          Git <ArrowRight className="h-3 w-3" />
        </Link>
      )}
    </div>
  );
}

function ArrivalRow({ item }) {
  const statusColor = STATUS_COLORS[item.status] || "bg-muted text-muted-foreground";
  return (
    <div className="flex items-center gap-3 py-2.5 border-b last:border-0">
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium truncate">{item.guest_name || "—"}</p>
        <p className="text-xs text-muted-foreground truncate">{item.room_type}</p>
      </div>
      <div className="text-right text-xs text-muted-foreground shrink-0">
        <p>{formatDate(item.check_in)}</p>
      </div>
      <span className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-medium ${statusColor}`}>
        {item.status}
      </span>
    </div>
  );
}

function ActivityRow({ item }) {
  return (
    <div className="flex items-start gap-3 py-2 border-b last:border-0">
      <Clock className="h-3.5 w-3.5 text-muted-foreground mt-0.5 shrink-0" />
      <div className="flex-1 min-w-0">
        <p className="text-sm truncate">{item.action} {item.details && `— ${item.details}`}</p>
        <p className="text-xs text-muted-foreground">{item.user_name} · {formatDate(item.created_at)}</p>
      </div>
    </div>
  );
}

function LoadingSkeleton() {
  return (
    <div className="space-y-6 p-6" data-testid="hotel-dashboard-loading">
      <Skeleton className="h-8 w-64" />
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-24 rounded-xl" />)}
      </div>
      <Skeleton className="h-48 rounded-xl" />
      <Skeleton className="h-64 rounded-xl" />
    </div>
  );
}

/* ─── Main Page ─── */

export default function HotelDashboardPage() {
  const user = getUser();
  const { data, isLoading, error } = useHotelToday();

  if (isLoading) return <LoadingSkeleton />;

  if (error) {
    return (
      <div className="p-6" data-testid="hotel-dashboard-error">
        <div className="rounded-xl border border-red-200 bg-red-50 dark:bg-red-950/20 p-6 text-center">
          <AlertTriangle className="h-8 w-8 text-red-400 mx-auto mb-3" />
          <p className="text-sm text-red-600">Dashboard verisi yüklenemedi.</p>
        </div>
      </div>
    );
  }

  const cc = data?.checkin_checkout || {};
  const occ = data?.occupancy || {};
  const alerts = data?.alerts || [];
  const pending = data?.pending || {};
  const revenue = data?.revenue || {};
  const arrivals = data?.upcoming_arrivals || [];
  const activity = data?.recent_activity || [];
  const userName = user?.name || user?.email || "Otel";

  return (
    <div className="space-y-6 p-6" data-testid="hotel-dashboard">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight" data-testid="hotel-dashboard-title">
          Otel Kontrol Paneli
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          Hoş geldiniz, {userName} — {new Date().toLocaleDateString("tr-TR", { weekday: "long", day: "numeric", month: "long" })}
        </p>
      </div>

      {/* ── Blok 1: Check-in / Check-out KPI ── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4" data-testid="hotel-checkin-checkout-section">
        <KpiCard icon={LogIn} label="Bugün Check-in" value={cc.today_checkins ?? 0} sub="beklenen varış" color="text-emerald-600" />
        <KpiCard icon={LogOut} label="Bugün Check-out" value={cc.today_checkouts ?? 0} sub="beklenen çıkış" />
        <KpiCard icon={Calendar} label="Yarın Check-in" value={cc.tomorrow_checkins ?? 0} sub="hazırlık gerekli" color="text-sky-600" />
        <KpiCard icon={BedDouble} label="Mevcut Konaklayan" value={cc.active_stays ?? 0} sub="in-house misafir" color="text-violet-600" />
      </div>

      {/* ── Blok 2: Doluluk & Müsaitlik ── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4" data-testid="hotel-occupancy-section">
        <KpiCard icon={BedDouble} label="Toplam Kontenjan" value={occ.total_allocations ?? 0} sub="kayıtlı birim" />
        <KpiCard icon={ShieldCheck} label="Aktif Stop Sell" value={occ.stop_sell_active ?? 0} sub="kısıtlı birim" color={occ.stop_sell_active > 0 ? "text-amber-600" : "text-foreground"} />
        <KpiCard icon={TrendingUp} label="Haftalık Rezervasyon" value={occ.week_bookings ?? 0} sub="son 7 gün" />
        <KpiCard icon={TrendingUp} label="Haftalık Gelir" value={`${formatMoney(revenue.week_revenue)} ${revenue.currency || "TRY"}`} sub="son 7 gün" color="text-emerald-600" />
      </div>

      {/* ── Blok 3: Kritik Uyarılar ── */}
      {alerts.length > 0 && (
        <div className="space-y-2" data-testid="hotel-alerts-section">
          <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">Uyarılar</h2>
          {alerts.map((a, i) => <AlertCard key={i} alert={a} />)}
        </div>
      )}

      {/* ── Blok 4: Bekleyen & Overbooking Riski ── */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4" data-testid="hotel-pending-section">
        <div className="rounded-xl border bg-card p-4">
          <div className="flex items-center gap-2 mb-3">
            <DoorClosed className="h-4 w-4 text-amber-500" />
            <h3 className="text-sm font-semibold">Bekleyen Rezervasyonlar</h3>
          </div>
          <div className="flex items-end gap-2">
            <span className="text-3xl font-bold text-amber-600">{pending.pending_count ?? 0}</span>
            <span className="text-sm text-muted-foreground mb-1">onay bekliyor</span>
          </div>
          {(pending.pending_count ?? 0) > 0 && (
            <Link to="/app/hotel/bookings" className="text-xs text-primary hover:underline mt-2 inline-flex items-center gap-1">
              Talepleri gör <ArrowRight className="h-3 w-3" />
            </Link>
          )}
        </div>

        <div className="rounded-xl border bg-card p-4">
          <div className="flex items-center gap-2 mb-3">
            <DoorOpen className="h-4 w-4 text-red-500" />
            <h3 className="text-sm font-semibold">Son 7 Gün İptaller</h3>
          </div>
          <div className="flex items-end gap-2">
            <span className="text-3xl font-bold text-red-600">{pending.cancelled_7d ?? 0}</span>
            <span className="text-sm text-muted-foreground mb-1">iptal edildi</span>
          </div>
        </div>
      </div>

      {/* ── Blok 5a: Yaklaşan Varışlar ── */}
      <div className="rounded-xl border bg-card" data-testid="hotel-arrivals-section">
        <div className="flex items-center justify-between px-4 pt-4 pb-2">
          <h2 className="text-sm font-semibold flex items-center gap-2">
            <Calendar className="h-4 w-4 text-muted-foreground" />
            Yaklaşan Varışlar (7 Gün)
          </h2>
          <Link to="/app/hotel/bookings" className="text-xs text-primary hover:underline flex items-center gap-1">
            Tümü <ArrowRight className="h-3 w-3" />
          </Link>
        </div>
        <div className="px-4 pb-4">
          {arrivals.length === 0 ? (
            <div className="text-center py-6 text-sm text-muted-foreground">
              <CheckCircle2 className="h-6 w-6 mx-auto mb-2 text-emerald-400" />
              Yaklaşan varış bulunmuyor.
            </div>
          ) : (
            arrivals.map((a, i) => <ArrivalRow key={a.id || i} item={a} />)
          )}
        </div>
      </div>

      {/* ── Blok 5b: Son Aktiviteler ── */}
      <div className="rounded-xl border bg-card" data-testid="hotel-activity-section">
        <div className="px-4 pt-4 pb-2">
          <h2 className="text-sm font-semibold flex items-center gap-2">
            <Clock className="h-4 w-4 text-muted-foreground" />
            Son Aktiviteler
          </h2>
        </div>
        <div className="px-4 pb-4">
          {activity.length === 0 ? (
            <p className="text-center py-4 text-sm text-muted-foreground">Henüz aktivite yok.</p>
          ) : (
            activity.map((a, i) => <ActivityRow key={a.id || i} item={a} />)
          )}
        </div>
      </div>
    </div>
  );
}
