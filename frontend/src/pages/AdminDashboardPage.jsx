/**
 * Admin Dashboard — Sprint 3
 *
 * Yönetim odaklı kontrol paneli. Admin kullanıcının günlük
 * executive overview'ı — operasyon, finans, risk ve aksiyon.
 *
 * 6 Blok:
 *   1. Kritik Uyarılar
 *   2. Operasyon Özeti (KPI strip)
 *   3. Finansal Snapshot
 *   4. Onay Bekleyenler
 *   5. Sistem / Entegrasyon Sağlığı
 *   6. Son Yönetim Aksiyonları
 */
import React from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  AlertTriangle,
  ArrowRight,
  Activity,
  BarChart3,
  CheckCircle2,
  Clock,
  CreditCard,
  DollarSign,
  FileText,
  Inbox,
  Info,
  Shield,
  ShieldCheck,
  TrendingUp,
  Users,
  Zap,
  XCircle,
  Database,
  Server,
  Wifi,
} from "lucide-react";
import { Skeleton } from "../components/ui/skeleton";
import { getUser } from "../lib/api";
import { useAdminToday } from "../hooks/useAdminDashboard";

/* ------------------------------------------------------------------ */
/*  Helpers                                                             */
/* ------------------------------------------------------------------ */
function formatMoney(val) {
  if (!val && val !== 0) return "0";
  return Number(val).toLocaleString("tr-TR", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  });
}

function formatTime(dateStr) {
  if (!dateStr || dateStr === "None" || dateStr === "") return "";
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return "";
    return d.toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" });
  } catch {
    return "";
  }
}

function formatDate(dateStr) {
  if (!dateStr || dateStr === "None" || dateStr === "") return "";
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return "";
    return d.toLocaleDateString("tr-TR", { day: "2-digit", month: "2-digit" });
  } catch {
    return "";
  }
}

/* ------------------------------------------------------------------ */
/*  Greeting Header                                                     */
/* ------------------------------------------------------------------ */
function AdminGreeting({ user }) {
  const hour = new Date().getHours();
  let greeting = "İyi akşamlar";
  if (hour < 12) greeting = "Günaydın";
  else if (hour < 18) greeting = "İyi günler";

  const name = user?.name?.split(" ")[0] || user?.email?.split("@")[0] || "";

  return (
    <div className="mb-6" data-testid="admin-greeting">
      <h1 className="text-xl font-semibold text-foreground tracking-tight">
        {greeting}, {name}
      </h1>
      <p className="text-sm text-muted-foreground mt-0.5">
        Yönetim paneli — günlük operasyon ve sistem durumu.
      </p>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  BLOCK 1: Kritik Uyarılar                                           */
/* ------------------------------------------------------------------ */
function CriticalAlerts({ alerts, loading }) {
  const navigate = useNavigate();

  if (loading) {
    return (
      <div className="space-y-2" data-testid="alerts-loading">
        {[1, 2].map((i) => (
          <Skeleton key={i} className="h-14 w-full rounded-xl" />
        ))}
      </div>
    );
  }

  if (!alerts || alerts.length === 0) {
    return (
      <div
        className="rounded-xl border border-emerald-200/60 dark:border-emerald-800/30 bg-emerald-50/50 dark:bg-emerald-950/10 p-4 flex items-center gap-3"
        data-testid="alerts-clear"
      >
        <div className="h-9 w-9 rounded-lg bg-emerald-500/10 flex items-center justify-center shrink-0">
          <CheckCircle2 className="h-4.5 w-4.5 text-emerald-500" />
        </div>
        <div>
          <p className="text-sm font-medium text-emerald-700 dark:text-emerald-400">
            Kritik uyarı yok
          </p>
          <p className="text-xs text-emerald-600/70 dark:text-emerald-500/60">
            Tüm sistemler normal çalışıyor.
          </p>
        </div>
      </div>
    );
  }

  const typeStyles = {
    error: {
      border: "border-red-200/60 dark:border-red-800/30",
      bg: "bg-red-50/50 dark:bg-red-950/10",
      iconBg: "bg-red-500/10",
      icon: XCircle,
      iconColor: "text-red-500",
      titleColor: "text-red-700 dark:text-red-400",
    },
    warning: {
      border: "border-amber-200/60 dark:border-amber-800/30",
      bg: "bg-amber-50/50 dark:bg-amber-950/10",
      iconBg: "bg-amber-500/10",
      icon: AlertTriangle,
      iconColor: "text-amber-500",
      titleColor: "text-amber-700 dark:text-amber-400",
    },
    info: {
      border: "border-blue-200/60 dark:border-blue-800/30",
      bg: "bg-blue-50/50 dark:bg-blue-950/10",
      iconBg: "bg-blue-500/10",
      icon: Info,
      iconColor: "text-blue-500",
      titleColor: "text-blue-700 dark:text-blue-400",
    },
  };

  return (
    <section data-testid="critical-alerts-block" className="space-y-2">
      {alerts.map((alert, i) => {
        const style = typeStyles[alert.type] || typeStyles.info;
        const IconComp = style.icon;
        return (
          <div
            key={i}
            className={`rounded-xl border ${style.border} ${style.bg} p-3.5 flex items-center gap-3 cursor-pointer hover:shadow-sm transition-shadow`}
            onClick={() => alert.action_url && navigate(alert.action_url)}
            data-testid={`alert-${alert.type}-${i}`}
          >
            <div className={`h-9 w-9 rounded-lg ${style.iconBg} flex items-center justify-center shrink-0`}>
              <IconComp className={`h-4.5 w-4.5 ${style.iconColor}`} />
            </div>
            <div className="flex-1 min-w-0">
              <p className={`text-sm font-medium ${style.titleColor}`}>
                {alert.title}
              </p>
              <p className="text-xs text-muted-foreground mt-0.5">
                {alert.message}
              </p>
            </div>
            {alert.action_url && (
              <ArrowRight className="h-4 w-4 text-muted-foreground/40 shrink-0" />
            )}
          </div>
        );
      })}
    </section>
  );
}

/* ------------------------------------------------------------------ */
/*  BLOCK 2: Operasyon Özeti (KPI Strip)                               */
/* ------------------------------------------------------------------ */
function OperationsKpi({ ops, loading }) {
  if (loading) {
    return (
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3" data-testid="ops-kpi-loading">
        {[1, 2, 3, 4].map((i) => (
          <Skeleton key={i} className="h-[88px] rounded-xl" />
        ))}
      </div>
    );
  }

  const cards = [
    {
      label: "Bekleyen Rezervasyon",
      value: ops?.pending_reservations || 0,
      icon: Clock,
      color: "#f59e0b",
      to: "/app/reservations?status=pending",
    },
    {
      label: "Bugün Yeni",
      value: ops?.today_new_reservations || 0,
      suffix: " rez",
      icon: TrendingUp,
      color: "#3b82f6",
    },
    {
      label: "Bugün Check-in",
      value: ops?.today_checkins || 0,
      icon: Activity,
      color: "#10b981",
    },
    {
      label: "Açık Vaka",
      value: ops?.open_cases || 0,
      icon: AlertTriangle,
      color: (ops?.open_cases || 0) > 3 ? "#ef4444" : "#f59e0b",
      to: "/app/ops/guest-cases",
    },
  ];

  return (
    <section data-testid="operations-kpi-block">
      <div className="flex items-center gap-2 mb-4">
        <div className="h-7 w-7 rounded-lg bg-blue-500/10 flex items-center justify-center">
          <BarChart3 className="h-4 w-4 text-blue-500" />
        </div>
        <h2 className="text-base font-semibold text-foreground">Operasyon Özeti</h2>
      </div>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {cards.map((card) => (
          <KpiCard key={card.label} {...card} />
        ))}
      </div>
    </section>
  );
}

function KpiCard({ label, value, suffix, icon: Icon, color, to }) {
  const navigate = useNavigate();
  return (
    <div
      className={`rounded-xl border border-border/40 bg-card p-4 flex items-center gap-3 transition-all hover:shadow-sm ${
        to ? "cursor-pointer hover:-translate-y-0.5" : ""
      }`}
      onClick={() => to && navigate(to)}
      data-testid={`kpi-${label.toLowerCase().replace(/\s+/g, "-")}`}
    >
      <div
        className="h-10 w-10 rounded-xl flex items-center justify-center shrink-0"
        style={{ backgroundColor: `${color}12` }}
      >
        <Icon className="h-5 w-5" style={{ color }} />
      </div>
      <div className="min-w-0">
        <p className="text-xs text-muted-foreground truncate">{label}</p>
        <p className="text-lg font-bold text-foreground tracking-tight leading-tight">
          {value}
          {suffix && (
            <span className="text-xs font-normal text-muted-foreground ml-0.5">
              {suffix}
            </span>
          )}
        </p>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  BLOCK 3: Finansal Snapshot                                         */
/* ------------------------------------------------------------------ */
function FinancialSnapshot({ finance, ops, loading }) {
  if (loading) {
    return (
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3" data-testid="finance-loading">
        {[1, 2, 3, 4].map((i) => (
          <Skeleton key={i} className="h-[100px] rounded-xl" />
        ))}
      </div>
    );
  }

  const cards = [
    {
      label: "Toplam Gelir",
      value: `${formatMoney(finance?.total_revenue || 0)}₺`,
      icon: DollarSign,
      color: "#10b981",
    },
    {
      label: "Bu Hafta",
      value: `${formatMoney(finance?.week_revenue || 0)}₺`,
      icon: TrendingUp,
      color: "#3b82f6",
    },
    {
      label: "Bugün",
      value: `${formatMoney(finance?.today_revenue || 0)}₺`,
      icon: CreditCard,
      color: "#6366f1",
    },
    {
      label: "Tamamlanan / Toplam",
      value: `${ops?.completed_reservations || 0} / ${ops?.total_reservations || 0}`,
      icon: CheckCircle2,
      color: "#8b5cf6",
    },
  ];

  return (
    <section data-testid="financial-snapshot-block">
      <div className="flex items-center gap-2 mb-4">
        <div className="h-7 w-7 rounded-lg bg-emerald-500/10 flex items-center justify-center">
          <DollarSign className="h-4 w-4 text-emerald-500" />
        </div>
        <h2 className="text-base font-semibold text-foreground">Finansal Snapshot</h2>
      </div>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {cards.map((card) => (
          <div
            key={card.label}
            className="rounded-xl border border-border/40 bg-card p-4 hover:shadow-sm transition-all"
            data-testid={`finance-${card.label.toLowerCase().replace(/\s+/g, "-")}`}
          >
            <div className="flex items-center gap-2 mb-2">
              <div
                className="h-8 w-8 rounded-lg flex items-center justify-center"
                style={{ backgroundColor: `${card.color}12` }}
              >
                <card.icon className="h-4 w-4" style={{ color: card.color }} />
              </div>
              <p className="text-xs text-muted-foreground">{card.label}</p>
            </div>
            <p className="text-xl font-bold text-foreground tracking-tight">
              {card.value}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------ */
/*  BLOCK 4: Onay Bekleyenler                                         */
/* ------------------------------------------------------------------ */
function PendingApprovals({ items, loading }) {
  const navigate = useNavigate();

  if (loading) {
    return (
      <div className="rounded-xl border border-border/40 bg-card p-4" data-testid="approvals-loading">
        <Skeleton className="h-5 w-40 mb-4" />
        {[1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-12 w-full mb-2" />
        ))}
      </div>
    );
  }

  return (
    <div
      className="rounded-xl border border-border/40 bg-card p-4 hover:shadow-sm transition-shadow"
      data-testid="pending-approvals-block"
    >
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Inbox className="h-4 w-4 text-amber-500" />
          <h3 className="text-sm font-semibold text-foreground">Onay Bekleyenler</h3>
          {items && items.length > 0 && (
            <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-600 dark:text-amber-400">
              {items.length}
            </span>
          )}
        </div>
        <Link
          to="/app/reservations?status=pending"
          className="text-xs text-primary hover:underline flex items-center gap-1"
          data-testid="approvals-view-all"
        >
          Tümünü Gör <ArrowRight className="h-3 w-3" />
        </Link>
      </div>

      {items && items.length > 0 ? (
        <div className="space-y-0">
          {items.map((item, i) => (
            <div
              key={item.id || i}
              className="flex items-center justify-between py-2.5 border-b border-border/15 last:border-0 cursor-pointer hover:bg-muted/20 -mx-2 px-2 rounded-lg transition-colors"
              onClick={() => navigate("/app/reservations")}
            >
              <div className="flex-1 min-w-0 mr-3">
                <p className="text-sm font-medium text-foreground truncate">
                  {item.guest_name || item.product_name || "—"}
                </p>
                <p className="text-xs text-muted-foreground mt-0.5">
                  {item.pnr && `PNR: ${item.pnr}`}
                  {item.total_price > 0 && ` · ${formatMoney(item.total_price)}₺`}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-600">
                  Beklemede
                </span>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center py-6 text-center">
          <div className="h-10 w-10 rounded-full bg-emerald-500/10 flex items-center justify-center mb-2">
            <CheckCircle2 className="h-4 w-4 text-emerald-500" />
          </div>
          <p className="text-xs text-muted-foreground">Onay bekleyen öğe yok</p>
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  BLOCK 5: Sistem / Entegrasyon Sağlığı                             */
/* ------------------------------------------------------------------ */
function SystemHealth({ health, loading }) {
  if (loading) {
    return (
      <div className="rounded-xl border border-border/40 bg-card p-4" data-testid="health-loading">
        <Skeleton className="h-5 w-40 mb-4" />
        {[1, 2, 3, 4].map((i) => (
          <Skeleton key={i} className="h-10 w-full mb-2" />
        ))}
      </div>
    );
  }

  const statusItems = [
    {
      label: "Veritabanı",
      icon: Database,
      status: health?.database || "healthy",
    },
    {
      label: "Toplam Kullanıcı",
      icon: Users,
      value: health?.total_users || 0,
      status: "info",
    },
    {
      label: "Acenta Kullanıcıları",
      icon: Users,
      value: health?.agency_users || 0,
      status: "info",
    },
    {
      label: "Açık Incident",
      icon: AlertTriangle,
      value: health?.open_incidents || 0,
      status: (health?.open_incidents || 0) > 0 ? "warning" : "healthy",
    },
  ];

  const statusColors = {
    healthy: { dot: "bg-emerald-500", text: "text-emerald-600 dark:text-emerald-400", label: "Sağlıklı" },
    warning: { dot: "bg-amber-500", text: "text-amber-600 dark:text-amber-400", label: "Uyarı" },
    error: { dot: "bg-red-500", text: "text-red-600 dark:text-red-400", label: "Hata" },
    info: { dot: "bg-blue-500", text: "text-blue-600 dark:text-blue-400", label: "" },
  };

  return (
    <div
      className="rounded-xl border border-border/40 bg-card p-4 hover:shadow-sm transition-shadow"
      data-testid="system-health-block"
    >
      <div className="flex items-center gap-2 mb-4">
        <Shield className="h-4 w-4 text-blue-500" />
        <h3 className="text-sm font-semibold text-foreground">Sistem Sağlığı</h3>
      </div>

      <div className="space-y-0">
        {statusItems.map((item) => {
          const sc = statusColors[item.status] || statusColors.info;
          return (
            <div
              key={item.label}
              className="flex items-center justify-between py-2.5 border-b border-border/15 last:border-0"
            >
              <div className="flex items-center gap-2.5">
                <item.icon className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm text-foreground">{item.label}</span>
              </div>
              <div className="flex items-center gap-2">
                {item.value !== undefined && (
                  <span className="text-sm font-semibold text-foreground tabular-nums">
                    {item.value}
                  </span>
                )}
                {item.status !== "info" && (
                  <div className="flex items-center gap-1.5">
                    <div className={`h-2 w-2 rounded-full ${sc.dot}`} />
                    <span className={`text-xs font-medium ${sc.text}`}>
                      {sc.label}
                    </span>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  BLOCK 6: Son Yönetim Aksiyonları                                   */
/* ------------------------------------------------------------------ */
function RecentAdminActions({ actions, loading }) {
  if (loading) {
    return (
      <div className="rounded-xl border border-border/40 bg-card p-4" data-testid="actions-loading">
        <Skeleton className="h-5 w-40 mb-4" />
        {[1, 2, 3, 4, 5].map((i) => (
          <div key={i} className="flex gap-3 py-2">
            <Skeleton className="h-7 w-7 rounded-full shrink-0" />
            <div className="flex-1 space-y-1">
              <Skeleton className="h-3 w-3/4" />
              <Skeleton className="h-2.5 w-1/3" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div
      className="rounded-xl border border-border/40 bg-card p-4 hover:shadow-sm transition-shadow"
      data-testid="recent-admin-actions-block"
    >
      <div className="flex items-center gap-2 mb-4">
        <Activity className="h-4 w-4 text-blue-500" />
        <h3 className="text-sm font-semibold text-foreground">Son Yönetim Aksiyonları</h3>
      </div>

      {actions && actions.length > 0 ? (
        <div className="space-y-0">
          {actions.slice(0, 8).map((ev, i) => (
            <div
              key={ev.id || i}
              className="flex gap-3 py-2 border-b border-border/15 last:border-0"
            >
              <div className="h-7 w-7 rounded-full bg-blue-500/8 flex items-center justify-center shrink-0 mt-0.5">
                <Activity className="h-3.5 w-3.5 text-blue-500" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-xs text-foreground truncate">
                  {ev.action || ev.details || "Bilinmeyen olay"}
                </p>
                <div className="flex items-center gap-2 mt-0.5">
                  {ev.user_name && (
                    <span className="text-[10px] text-muted-foreground">
                      {typeof ev.user_name === "string"
                        ? ev.user_name
                        : ev.user_name?.email || ""}
                    </span>
                  )}
                  <span className="text-[10px] text-muted-foreground/60">
                    {formatDate(ev.created_at)} {formatTime(ev.created_at)}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center py-8 text-center">
          <div className="h-10 w-10 rounded-full bg-muted/50 flex items-center justify-center mb-2">
            <Clock className="h-4 w-4 text-muted-foreground/60" />
          </div>
          <p className="text-xs text-muted-foreground">Henüz aksiyon kaydı yok</p>
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Quick Actions for Admin                                            */
/* ------------------------------------------------------------------ */
function AdminQuickActions() {
  const actions = [
    { label: "Rezervasyonlar", icon: FileText, to: "/app/reservations", color: "#3b82f6" },
    { label: "Siparişler", icon: Inbox, to: "/app/admin/orders", color: "#6366f1" },
    { label: "Müşteriler", icon: Users, to: "/app/crm/customers", color: "#10b981" },
    { label: "Gelir Analizi", icon: BarChart3, to: "/app/admin/analytics", color: "#8b5cf6" },
    { label: "Kullanıcılar", icon: ShieldCheck, to: "/app/admin/all-users", color: "#f59e0b" },
    { label: "Entegrasyonlar", icon: Zap, to: "/app/admin/integrations", color: "#ec4899" },
  ];

  return (
    <section data-testid="admin-quick-actions-block">
      <div className="flex items-center gap-2 mb-4">
        <div className="h-7 w-7 rounded-lg bg-indigo-500/10 flex items-center justify-center">
          <Zap className="h-4 w-4 text-indigo-500" />
        </div>
        <h2 className="text-base font-semibold text-foreground">Hızlı Erişim</h2>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5">
        {actions.map((action) => (
          <Link
            key={action.label}
            to={action.to}
            className="group rounded-xl border border-border/40 bg-card p-3.5 flex flex-col items-center gap-2 text-center transition-all hover:shadow-md hover:-translate-y-0.5 hover:bg-muted/30"
            data-testid={`admin-action-${action.label.toLowerCase().replace(/\s+/g, "-")}`}
          >
            <div
              className="h-10 w-10 rounded-xl flex items-center justify-center transition-transform group-hover:scale-110"
              style={{ backgroundColor: `${action.color}12` }}
            >
              <action.icon className="h-5 w-5" style={{ color: action.color }} />
            </div>
            <span className="text-xs font-medium text-foreground leading-tight">
              {action.label}
            </span>
          </Link>
        ))}
      </div>
    </section>
  );
}

/* ================================================================== */
/*  MAIN ADMIN DASHBOARD                                                */
/* ================================================================== */
export default function AdminDashboardPage() {
  const user = getUser();
  const { data: adminData, isLoading } = useAdminToday();

  return (
    <div className="space-y-6" data-testid="admin-dashboard">
      {/* Greeting */}
      <AdminGreeting user={user} />

      {/* Block 1: Kritik Uyarılar */}
      <CriticalAlerts alerts={adminData?.alerts} loading={isLoading} />

      {/* Block 2: Operasyon Özeti */}
      <OperationsKpi ops={adminData?.operations} loading={isLoading} />

      {/* Block 3: Finansal Snapshot */}
      <FinancialSnapshot
        finance={adminData?.finance}
        ops={adminData?.operations}
        loading={isLoading}
      />

      {/* Quick Actions */}
      <AdminQuickActions />

      {/* Block 4+5+6: Grid layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Block 4: Onay Bekleyenler */}
        <PendingApprovals items={adminData?.pending_approvals} loading={isLoading} />

        {/* Block 5: Sistem Sağlığı */}
        <SystemHealth health={adminData?.system_health} loading={isLoading} />

        {/* Block 6: Son Yönetim Aksiyonları */}
        <RecentAdminActions actions={adminData?.recent_actions} loading={isLoading} />
      </div>
    </div>
  );
}
