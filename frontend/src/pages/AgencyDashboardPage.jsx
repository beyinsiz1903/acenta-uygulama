/**
 * Agency Dashboard — Sprint 2
 *
 * Görev odaklı kontrol paneli. Raporlama ekranı DEĞİL.
 * Kullanıcı ilk bakışta 3 sorunun cevabını almalı:
 *   1. Bugün ne yapmalıyım?
 *   2. Nerede risk var?
 *   3. Hangi işlemi hemen başlatabilirim?
 *
 * Layout:  Bugün Yapılacaklar → KPI → Hızlı Aksiyonlar → Son Aktivite
 */
import React, { useMemo } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  AlertTriangle,
  ArrowRight,
  CalendarCheck,
  CheckCircle2,
  Clock,
  CreditCard,
  FileText,
  Hotel,
  Plane,
  Plus,
  Search,
  TrendingUp,
  Users,
  Zap,
  Activity,
  ClipboardList,
  Timer,
  Receipt,
} from "lucide-react";
import { Skeleton } from "../components/ui/skeleton";
import { getUser } from "../lib/api";
import { useAgencyToday } from "../hooks/useAgencyDashboard";
import {
  useDashboardKPI,
  useDashboardWeeklySummary,
} from "../hooks/useDashboard";

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

function formatDate(dateStr) {
  if (!dateStr || dateStr === "None" || dateStr === "") return "";
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return "";
    return d.toLocaleDateString("tr-TR", {
      day: "2-digit",
      month: "2-digit",
    });
  } catch {
    return "";
  }
}

function formatTime(dateStr) {
  if (!dateStr || dateStr === "None" || dateStr === "") return "";
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return "";
    return d.toLocaleTimeString("tr-TR", {
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return "";
  }
}

const STATUS_MAP = {
  pending: { label: "Beklemede", color: "#f59e0b", bg: "bg-amber-50 dark:bg-amber-950/20" },
  confirmed: { label: "Onaylı", color: "#3b82f6", bg: "bg-blue-50 dark:bg-blue-950/20" },
  paid: { label: "Ödendi", color: "#10b981", bg: "bg-emerald-50 dark:bg-emerald-950/20" },
  completed: { label: "Tamamlandı", color: "#10b981", bg: "bg-emerald-50 dark:bg-emerald-950/20" },
  cancelled: { label: "İptal", color: "#ef4444", bg: "bg-red-50 dark:bg-red-950/20" },
};

/* ------------------------------------------------------------------ */
/*  SECTION: Greeting Header                                           */
/* ------------------------------------------------------------------ */
function GreetingHeader({ user }) {
  const hour = new Date().getHours();
  let greeting = "İyi akşamlar";
  if (hour < 12) greeting = "Günaydın";
  else if (hour < 18) greeting = "İyi günler";

  const name = user?.name?.split(" ")[0] || user?.email?.split("@")[0] || "";

  return (
    <div className="mb-6" data-testid="agency-greeting">
      <h1 className="text-xl font-semibold text-foreground tracking-tight">
        {greeting}, {name}
      </h1>
      <p className="text-sm text-muted-foreground mt-0.5">
        Bugünkü operasyon özetin hazır.
      </p>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  BLOCK 1: Bugün Yapılacaklar                                        */
/* ------------------------------------------------------------------ */
function TodayTasksBlock({ data, counters, loading }) {
  const navigate = useNavigate();

  if (loading) {
    return (
      <div className="space-y-3" data-testid="today-tasks-loading">
        <div className="flex items-center gap-2 mb-2">
          <Skeleton className="h-5 w-5 rounded" />
          <Skeleton className="h-5 w-48" />
        </div>
        {[1, 2, 3, 4].map((i) => (
          <Skeleton key={i} className="h-16 w-full rounded-xl" />
        ))}
      </div>
    );
  }

  const taskGroups = [
    {
      key: "pending",
      label: "Onay Bekleyen Rezervasyonlar",
      icon: Clock,
      color: "#f59e0b",
      count: counters?.pending_reservations || 0,
      items: data?.pending_reservations || [],
      to: "/app/agency/bookings?status=pending",
      emptyText: "Bekleyen rezervasyon yok",
    },
    {
      key: "checkins",
      label: "Bugünkü Giriş/Çıkışlar",
      icon: CalendarCheck,
      color: "#3b82f6",
      count: counters?.today_checkins || 0,
      items: data?.today_checkins || [],
      to: "/app/agency/bookings",
      emptyText: "Bugün giriş/çıkış yok",
    },
    {
      key: "tasks",
      label: "Açık CRM Görevleri",
      icon: ClipboardList,
      color: "#8b5cf6",
      count: counters?.open_crm_tasks || 0,
      items: data?.crm_tasks || [],
      to: "/app/crm/tasks",
      emptyText: "Açık görev yok",
    },
    {
      key: "quotes",
      label: "Süresi Dolan Teklifler",
      icon: Timer,
      color: "#ef4444",
      count: counters?.expiring_quotes || 0,
      items: data?.expiring_quotes || [],
      to: "/app/crm/pipeline",
      emptyText: "Risk altında teklif yok",
    },
  ];

  const totalTaskCount = taskGroups.reduce((a, g) => a + g.count, 0);

  return (
    <section data-testid="today-tasks-block">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <div className="h-7 w-7 rounded-lg bg-amber-500/10 flex items-center justify-center">
            <Zap className="h-4 w-4 text-amber-500" />
          </div>
          <h2 className="text-base font-semibold text-foreground">
            Bugün Yapılacaklar
          </h2>
          {totalTaskCount > 0 && (
            <span className="ml-1 text-xs font-medium px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-600 dark:text-amber-400">
              {totalTaskCount}
            </span>
          )}
        </div>
      </div>

      {totalTaskCount === 0 ? (
        <div className="rounded-xl border border-border/40 bg-card p-6 text-center">
          <div className="h-11 w-11 rounded-full bg-emerald-500/10 flex items-center justify-center mx-auto mb-3">
            <CheckCircle2 className="h-5 w-5 text-emerald-500" />
          </div>
          <p className="text-sm font-medium text-foreground">
            Tüm işler yolunda!
          </p>
          <p className="text-xs text-muted-foreground mt-1">
            Bekleyen aksiyon bulunmuyor.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {taskGroups.map((group) => (
            <div
              key={group.key}
              className="rounded-xl border border-border/40 bg-card overflow-hidden hover:shadow-sm transition-shadow"
              data-testid={`today-task-${group.key}`}
            >
              {/* Header */}
              <div
                className="flex items-center justify-between px-4 py-3 cursor-pointer hover:bg-muted/30 transition-colors"
                onClick={() => navigate(group.to)}
              >
                <div className="flex items-center gap-2.5">
                  <div
                    className="h-8 w-8 rounded-lg flex items-center justify-center"
                    style={{ backgroundColor: `${group.color}12` }}
                  >
                    <group.icon className="h-4 w-4" style={{ color: group.color }} />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-foreground">{group.label}</p>
                    <p className="text-xs text-muted-foreground">
                      {group.count > 0 ? `${group.count} adet` : group.emptyText}
                    </p>
                  </div>
                </div>
                {group.count > 0 && (
                  <span
                    className="text-lg font-bold tabular-nums"
                    style={{ color: group.color }}
                  >
                    {group.count}
                  </span>
                )}
              </div>

              {/* Items preview (max 3) */}
              {group.items.length > 0 && (
                <div className="border-t border-border/30 px-4 py-2">
                  {group.items.slice(0, 3).map((item, idx) => (
                    <div
                      key={item.id || idx}
                      className="flex items-center justify-between py-1.5 text-xs"
                    >
                      <span className="text-foreground truncate flex-1 mr-2">
                        {item.guest_name || item.customer_name || item.title || item.product_name || "—"}
                      </span>
                      <span className="text-muted-foreground whitespace-nowrap">
                        {item.product_name ? item.product_name.slice(0, 20) : ""}
                        {item.due_date ? formatDate(item.due_date) : ""}
                        {item.expires_at ? formatDate(item.expires_at) : ""}
                        {item.check_in ? formatDate(item.check_in) : ""}
                      </span>
                    </div>
                  ))}
                  {group.items.length > 3 && (
                    <button
                      onClick={() => navigate(group.to)}
                      className="text-xs text-primary hover:underline mt-1 flex items-center gap-1"
                    >
                      +{group.items.length - 3} daha
                      <ArrowRight className="h-3 w-3" />
                    </button>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

/* ------------------------------------------------------------------ */
/*  BLOCK 2: KPI Strip                                                 */
/* ------------------------------------------------------------------ */
function KpiStrip({ todayKpi, globalKpi, loading }) {
  if (loading) {
    return (
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3" data-testid="kpi-strip-loading">
        {[1, 2, 3, 4].map((i) => (
          <Skeleton key={i} className="h-[88px] rounded-xl" />
        ))}
      </div>
    );
  }

  const cards = [
    {
      label: "Bugünün Geliri",
      value: `${formatMoney(todayKpi?.revenue || 0)}`,
      suffix: "₺",
      icon: TrendingUp,
      color: "#10b981",
    },
    {
      label: "Yeni Rezervasyon",
      value: todayKpi?.new_reservations || 0,
      suffix: " bugün",
      icon: Receipt,
      color: "#3b82f6",
    },
    {
      label: "Toplam Satış",
      value: `${formatMoney(globalKpi?.total_sales || 0)}`,
      suffix: "₺",
      icon: CreditCard,
      color: "#6366f1",
    },
    {
      label: "Aksiyon Bekleyen",
      value: todayKpi?.pending_action || 0,
      suffix: " adet",
      icon: AlertTriangle,
      color: (todayKpi?.pending_action || 0) > 5 ? "#ef4444" : "#f59e0b",
    },
  ];

  return (
    <section data-testid="kpi-strip-block">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {cards.map((card) => (
          <div
            key={card.label}
            className="rounded-xl border border-border/40 bg-card p-4 flex items-center gap-3 hover:shadow-sm transition-all"
            data-testid={`kpi-card-${card.label.toLowerCase().replace(/\s+/g, "-")}`}
          >
            <div
              className="h-10 w-10 rounded-xl flex items-center justify-center shrink-0"
              style={{ backgroundColor: `${card.color}12` }}
            >
              <card.icon className="h-5 w-5" style={{ color: card.color }} />
            </div>
            <div className="min-w-0">
              <p className="text-xs text-muted-foreground truncate">{card.label}</p>
              <p className="text-lg font-bold text-foreground tracking-tight leading-tight">
                {card.value}
                <span className="text-xs font-normal text-muted-foreground ml-0.5">
                  {card.suffix}
                </span>
              </p>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------ */
/*  BLOCK 3: Hızlı Aksiyonlar                                         */
/* ------------------------------------------------------------------ */
function QuickActions() {
  const actions = [
    {
      label: "Otel Ara",
      icon: Search,
      to: "/app/agency/hotels",
      color: "#3b82f6",
      primary: true,
    },
    {
      label: "Çoklu Arama",
      icon: Hotel,
      to: "/app/agency/unified-search",
      color: "#6366f1",
    },
    {
      label: "Yeni Teklif",
      icon: FileText,
      to: "/app/crm/pipeline",
      color: "#8b5cf6",
    },
    {
      label: "Müşteriler",
      icon: Users,
      to: "/app/crm/customers",
      color: "#10b981",
    },
    {
      label: "Turlar",
      icon: Plane,
      to: "/app/tours",
      color: "#f59e0b",
    },
    {
      label: "Rezervasyonlarım",
      icon: ClipboardList,
      to: "/app/agency/bookings",
      color: "#ec4899",
    },
  ];

  return (
    <section data-testid="quick-actions-block">
      <div className="flex items-center gap-2 mb-4">
        <div className="h-7 w-7 rounded-lg bg-blue-500/10 flex items-center justify-center">
          <Zap className="h-4 w-4 text-blue-500" />
        </div>
        <h2 className="text-base font-semibold text-foreground">
          Hızlı Aksiyonlar
        </h2>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5">
        {actions.map((action) => (
          <Link
            key={action.label}
            to={action.to}
            className={`group rounded-xl border p-3.5 flex flex-col items-center gap-2 text-center transition-all hover:shadow-md hover:-translate-y-0.5 ${
              action.primary
                ? "border-primary/30 bg-primary/5 hover:bg-primary/10"
                : "border-border/40 bg-card hover:bg-muted/30"
            }`}
            data-testid={`quick-action-${action.label.toLowerCase().replace(/\s+/g, "-")}`}
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

/* ------------------------------------------------------------------ */
/*  BLOCK 4: Son Aktivite + Haftalık Özet                              */
/* ------------------------------------------------------------------ */
function RecentActivityBlock({ events, loading }) {
  if (loading) {
    return (
      <div className="rounded-xl border border-border/40 bg-card p-4" data-testid="activity-loading">
        <Skeleton className="h-5 w-32 mb-4" />
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

  const actionIcons = {
    reservation: Receipt,
    booking: Receipt,
    customer: Users,
    payment: CreditCard,
    quote: FileText,
    task: ClipboardList,
  };

  const getActionIcon = (event) => {
    const type = (event.entity_type || event.action || "").toLowerCase();
    for (const [key, Icon] of Object.entries(actionIcons)) {
      if (type.includes(key)) return Icon;
    }
    return Activity;
  };

  return (
    <div
      className="rounded-xl border border-border/40 bg-card p-4 hover:shadow-sm transition-shadow"
      data-testid="recent-activity-block"
    >
      <div className="flex items-center gap-2 mb-4">
        <Activity className="h-4 w-4 text-blue-500" />
        <h3 className="text-sm font-semibold text-foreground">Son Aktiviteler</h3>
      </div>

      {events && events.length > 0 ? (
        <div className="space-y-0">
          {events.slice(0, 8).map((ev, i) => {
            const IconComp = getActionIcon(ev);
            return (
              <div
                key={ev.id || i}
                className="flex gap-3 py-2 border-b border-border/15 last:border-0"
              >
                <div className="h-7 w-7 rounded-full bg-blue-500/8 flex items-center justify-center shrink-0 mt-0.5">
                  <IconComp className="h-3.5 w-3.5 text-blue-500" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-xs text-foreground truncate">
                    {ev.action || ev.details || "Bilinmeyen olay"}
                  </p>
                  <div className="flex items-center gap-2 mt-0.5">
                    {ev.user_name && (
                      <span className="text-2xs text-muted-foreground">
                        {typeof ev.user_name === "string" ? ev.user_name : ev.user_name?.email || ""}
                      </span>
                    )}
                    <span className="text-2xs text-muted-foreground/60">
                      {formatDate(ev.created_at)} {formatTime(ev.created_at)}
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center py-8 text-center">
          <div className="h-10 w-10 rounded-full bg-muted/50 flex items-center justify-center mb-2">
            <Clock className="h-4 w-4 text-muted-foreground/60" />
          </div>
          <p className="text-xs text-muted-foreground">Henüz aktivite kaydı yok</p>
          <p className="text-xs text-muted-foreground/60 mt-0.5">
            İşlemler burada görünecek
          </p>
        </div>
      )}
    </div>
  );
}

/* Mini Weekly Summary for Agency */
function MiniWeeklySummary({ data, loading }) {
  if (loading) {
    return (
      <div className="rounded-xl border border-border/40 bg-card p-4" data-testid="weekly-loading">
        <Skeleton className="h-5 w-32 mb-4" />
        {[1, 2, 3, 4, 5, 6, 7].map((i) => (
          <Skeleton key={i} className="h-8 w-full mb-1.5" />
        ))}
      </div>
    );
  }

  return (
    <div
      className="rounded-xl border border-border/40 bg-card p-4 hover:shadow-sm transition-shadow"
      data-testid="mini-weekly-summary"
    >
      <div className="flex items-center gap-2 mb-4">
        <CalendarCheck className="h-4 w-4 text-blue-500" />
        <h3 className="text-sm font-semibold text-foreground">Haftalık Özet</h3>
      </div>

      {data && data.length > 0 ? (
        <div className="space-y-0">
          {data.map((row, idx) => (
            <div
              key={idx}
              className={`flex items-center justify-between py-2 px-2 -mx-2 rounded-lg text-xs ${
                row.is_today
                  ? "bg-blue-50/60 dark:bg-blue-950/20 font-medium"
                  : "hover:bg-muted/20"
              }`}
            >
              <div className="flex items-center gap-2 min-w-0">
                <span
                  className={`w-6 text-center font-bold tabular-nums ${
                    row.is_today ? "text-blue-600 dark:text-blue-400" : "text-foreground"
                  }`}
                >
                  {row.date}
                </span>
                <span className="text-muted-foreground w-12 truncate">
                  {row.day_name?.slice(0, 3)}
                </span>
              </div>
              <div className="flex items-center gap-4">
                <span className="text-foreground tabular-nums">
                  <span className="text-blue-600 font-semibold">{row.reservations}</span>
                  <span className="text-muted-foreground ml-0.5">rez</span>
                </span>
                <span className="text-foreground tabular-nums w-16 text-right">
                  {row.payments > 0 ? (
                    <span className="text-emerald-600 font-semibold">
                      {formatMoney(row.payments)}₺
                    </span>
                  ) : (
                    <span className="text-muted-foreground">—</span>
                  )}
                </span>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center py-6 text-center">
          <p className="text-xs text-muted-foreground">Haftalık veri yok</p>
        </div>
      )}
    </div>
  );
}

/* ================================================================== */
/*  MAIN AGENCY DASHBOARD                                              */
/* ================================================================== */
export default function AgencyDashboardPage() {
  const user = getUser();
  const { data: agencyData, isLoading: agencyLoading } = useAgencyToday();
  const { data: globalKpi, isLoading: kpiLoading } = useDashboardKPI();
  const { data: weeklySummary, isLoading: weeklyLoading } = useDashboardWeeklySummary();

  return (
    <div className="space-y-6" data-testid="agency-dashboard">
      {/* Greeting */}
      <GreetingHeader user={user} />

      {/* Block 1: Bugün Yapılacaklar */}
      <TodayTasksBlock
        data={agencyData?.today_tasks}
        counters={agencyData?.counters}
        loading={agencyLoading}
      />

      {/* Block 2: KPI Strip */}
      <KpiStrip
        todayKpi={agencyData?.today_kpi}
        globalKpi={globalKpi}
        loading={agencyLoading || kpiLoading}
      />

      {/* Block 3: Hızlı Aksiyonlar */}
      <QuickActions />

      {/* Block 4: Son Aktivite + Haftalık Özet */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <RecentActivityBlock
          events={agencyData?.recent_activity}
          loading={agencyLoading}
        />
        <MiniWeeklySummary
          data={weeklySummary}
          loading={weeklyLoading}
        />
      </div>
    </div>
  );
}
