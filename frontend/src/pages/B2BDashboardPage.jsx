/**
 * B2B Dashboard — Sprint 4
 *
 * B2B bayi/partner odaklı ticari kontrol paneli.
 *
 * 5 Blok:
 *   1. Teklif / Satış Pipeline
 *   2. Partner Performansı
 *   3. Bekleyen Onaylar
 *   4. Tahsilat / Ciro Özeti
 *   5. Son Ticari Aktiviteler
 */
import React from "react";
import { Link } from "react-router-dom";
import {
  AlertTriangle,
  ArrowRight,
  BarChart3,
  CheckCircle2,
  Clock,
  DollarSign,
  FileText,
  Handshake,
  Inbox,
  PieChart,
  ShoppingCart,
  TrendingUp,
  Users,
} from "lucide-react";
import { Skeleton } from "../components/ui/skeleton";
import { getUser } from "../lib/api";
import { useB2BToday } from "../hooks/useB2BDashboard";

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

const STATUS_COLORS = {
  confirmed: "bg-emerald-500/10 text-emerald-600",
  paid: "bg-emerald-500/10 text-emerald-600",
  completed: "bg-emerald-500/10 text-emerald-600",
  pending: "bg-amber-500/10 text-amber-600",
  cancelled: "bg-red-500/10 text-red-600",
  draft: "bg-muted text-muted-foreground",
};

/* ─── Sub-components ─── */

function KpiCard({ icon: Icon, label, value, sub, color = "text-foreground" }) {
  return (
    <div className="rounded-xl border bg-card p-4 flex flex-col gap-1" data-testid={`b2b-kpi-${label.toLowerCase().replace(/\s+/g, "-")}`}>
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <Icon className="h-3.5 w-3.5" />
        <span>{label}</span>
      </div>
      <span className={`text-2xl font-semibold tracking-tight ${color}`}>{value}</span>
      {sub && <span className="text-xs text-muted-foreground">{sub}</span>}
    </div>
  );
}

function BookingRow({ item }) {
  const statusColor = STATUS_COLORS[item.status] || "bg-muted text-muted-foreground";
  return (
    <div className="flex items-center gap-3 py-2.5 border-b last:border-0">
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium truncate">{item.guest_name || "—"}</p>
        <p className="text-xs text-muted-foreground truncate">{item.product_name}</p>
      </div>
      <div className="text-right text-xs shrink-0">
        <p className="font-medium">{formatMoney(item.total_price)} {item.currency}</p>
        <p className="text-muted-foreground">{formatDate(item.created_at)}</p>
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

function AnnouncementCard({ item }) {
  return (
    <div className="rounded-lg border bg-sky-50/50 dark:bg-sky-950/20 border-sky-200 dark:border-sky-800 p-3">
      <p className="text-sm font-medium">{item.title}</p>
      {item.body && <p className="text-xs text-muted-foreground mt-1 line-clamp-2">{item.body}</p>}
      <p className="text-[10px] text-muted-foreground/60 mt-1">{formatDate(item.created_at)}</p>
    </div>
  );
}

function LoadingSkeleton() {
  return (
    <div className="space-y-6 p-6" data-testid="b2b-dashboard-loading">
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

export default function B2BDashboardPage() {
  const user = getUser();
  const { data, isLoading, error } = useB2BToday();

  if (isLoading) return <LoadingSkeleton />;

  if (error) {
    return (
      <div className="p-6" data-testid="b2b-dashboard-error">
        <div className="rounded-xl border border-red-200 bg-red-50 dark:bg-red-950/20 p-6 text-center">
          <AlertTriangle className="h-8 w-8 text-red-400 mx-auto mb-3" />
          <p className="text-sm text-red-600">Dashboard verisi yüklenemedi.</p>
        </div>
      </div>
    );
  }

  const pipeline = data?.pipeline || {};
  const partners = data?.partners || {};
  const pending = data?.pending || {};
  const revenue = data?.revenue || {};
  const recentBookings = data?.recent_bookings || [];
  const activity = data?.recent_activity || [];
  const announcements = data?.announcements || [];
  const userName = user?.name || user?.email || "Partner";

  return (
    <div className="space-y-6 p-6" data-testid="b2b-dashboard">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight" data-testid="b2b-dashboard-title">
          B2B Kontrol Paneli
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          Hoş geldiniz, {userName} — {new Date().toLocaleDateString("tr-TR", { weekday: "long", day: "numeric", month: "long" })}
        </p>
      </div>

      {/* Announcements */}
      {announcements.length > 0 && (
        <div className="space-y-2" data-testid="b2b-announcements-section">
          <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">Duyurular</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {announcements.map((a, i) => <AnnouncementCard key={a.id || i} item={a} />)}
          </div>
        </div>
      )}

      {/* ── Blok 1: Pipeline KPI ── */}
      <div data-testid="b2b-pipeline-section">
        <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-3">Satış Pipeline</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <KpiCard icon={FileText} label="Açık Teklifler" value={pipeline.open_quotes ?? 0} sub="bekleyen" color="text-amber-600" />
          <KpiCard icon={CheckCircle2} label="Kazanılan" value={pipeline.won_deals_30d ?? 0} sub="son 30 gün" color="text-emerald-600" />
          <KpiCard icon={AlertTriangle} label="Kaybedilen" value={pipeline.lost_deals_30d ?? 0} sub="son 30 gün" color="text-red-500" />
          <KpiCard icon={PieChart} label="Dönüşüm Oranı" value={`%${pipeline.conversion_rate ?? 0}`} sub="kazanma oranı" color="text-sky-600" />
        </div>
      </div>

      {/* ── Blok 2: Partner Performansı ── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4" data-testid="b2b-partner-section">
        <KpiCard icon={Handshake} label="Aktif Partnerler" value={partners.active_partners ?? 0} sub="onaylı bayi" color="text-emerald-600" />
        <KpiCard icon={Users} label="Onay Bekleyen" value={partners.pending_approvals ?? 0} sub="yeni başvuru" color={(partners.pending_approvals ?? 0) > 0 ? "text-amber-600" : "text-foreground"} />
        <KpiCard icon={ShoppingCart} label="Bugün Satış" value={revenue.today_bookings ?? 0} sub="B2B rezervasyon" />
        <KpiCard icon={BarChart3} label="Aylık Satış" value={revenue.month_bookings ?? 0} sub="son 30 gün" />
      </div>

      {/* ── Blok 3: Bekleyen Onaylar ── */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4" data-testid="b2b-pending-section">
        <div className="rounded-xl border bg-card p-4">
          <div className="flex items-center gap-2 mb-3">
            <Inbox className="h-4 w-4 text-amber-500" />
            <h3 className="text-sm font-semibold">Bekleyen Rezervasyonlar</h3>
          </div>
          <div className="flex items-end gap-2">
            <span className="text-3xl font-bold text-amber-600">{pending.pending_reservations ?? 0}</span>
            <span className="text-sm text-muted-foreground mb-1">onay bekliyor</span>
          </div>
        </div>

        <div className="rounded-xl border bg-card p-4">
          <div className="flex items-center gap-2 mb-3">
            <Users className="h-4 w-4 text-sky-500" />
            <h3 className="text-sm font-semibold">Partner Başvuruları</h3>
          </div>
          <div className="flex items-end gap-2">
            <span className="text-3xl font-bold text-sky-600">{pending.pending_partners ?? 0}</span>
            <span className="text-sm text-muted-foreground mb-1">başvuru bekliyor</span>
          </div>
        </div>
      </div>

      {/* ── Blok 4: Ciro Özeti ── */}
      <div data-testid="b2b-revenue-section">
        <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-3">Tahsilat & Ciro</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="rounded-xl border bg-card p-5">
            <div className="flex items-center gap-2 text-xs text-muted-foreground mb-2">
              <DollarSign className="h-3.5 w-3.5" />
              <span>Aylık Ciro (30 gün)</span>
            </div>
            <span className="text-3xl font-bold text-emerald-600 tracking-tight">
              {formatMoney(revenue.month_revenue)} {revenue.currency || "TRY"}
            </span>
          </div>
          <div className="rounded-xl border bg-card p-5">
            <div className="flex items-center gap-2 text-xs text-muted-foreground mb-2">
              <TrendingUp className="h-3.5 w-3.5" />
              <span>Haftalık Ciro (7 gün)</span>
            </div>
            <span className="text-3xl font-bold text-sky-600 tracking-tight">
              {formatMoney(revenue.week_revenue)} {revenue.currency || "TRY"}
            </span>
          </div>
        </div>
      </div>

      {/* ── Blok 5a: Son Satışlar ── */}
      <div className="rounded-xl border bg-card" data-testid="b2b-recent-bookings-section">
        <div className="flex items-center justify-between px-4 pt-4 pb-2">
          <h2 className="text-sm font-semibold flex items-center gap-2">
            <ShoppingCart className="h-4 w-4 text-muted-foreground" />
            Son B2B Satışlar
          </h2>
        </div>
        <div className="px-4 pb-4">
          {recentBookings.length === 0 ? (
            <div className="text-center py-6 text-sm text-muted-foreground">
              <CheckCircle2 className="h-6 w-6 mx-auto mb-2 text-muted-foreground/40" />
              Henüz B2B satış bulunmuyor.
            </div>
          ) : (
            recentBookings.map((b, i) => <BookingRow key={b.id || i} item={b} />)
          )}
        </div>
      </div>

      {/* ── Blok 5b: Son Aktiviteler ── */}
      <div className="rounded-xl border bg-card" data-testid="b2b-activity-section">
        <div className="px-4 pt-4 pb-2">
          <h2 className="text-sm font-semibold flex items-center gap-2">
            <Clock className="h-4 w-4 text-muted-foreground" />
            Son Ticari Aktiviteler
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
