import React, { useEffect, useMemo, useState, useRef } from "react";
import { Link, useNavigate, useLocation, useSearchParams } from "react-router-dom";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell,
} from "recharts";
import {
  Ticket, CalendarDays, AlertCircle, TrendingUp,
  CheckCircle2, Clock, Activity, ChevronRight, ChevronLeft,
  BarChart3, ListChecks, Package, FileWarning, ExternalLink,
  DollarSign, Users, ShoppingCart, Percent, Eye, Calendar,
  UserPlus, XCircle, RefreshCw, MapPin, Star,
} from "lucide-react";

import { api, getUser } from "../lib/api";
import { Skeleton } from "../components/ui/skeleton";
import DashboardFilterBar from "../components/DashboardFilterBar";
import ActivationChecklist from "../components/ActivationChecklist";
import DemoSeedButton from "../components/DemoSeedButton";
import {
  resolveFilters, saveToLocalStorage, saveDensity, filtersToQuery,
  getPresetDays, getPresetDateRange, DEFAULT_FILTERS, exportDashboardCSV,
} from "../lib/dashboardFilters";

/* ------------------------------------------------------------------ */
/*  COLORS                                                             */
/* ------------------------------------------------------------------ */
const STATUS_COLORS = {
  pending: "#f59e0b",
  confirmed: "#3b82f6",
  paid: "#10b981",
  cancelled: "#ef4444",
  other: "#94a3b8",
};

/* ------------------------------------------------------------------ */
/*  BIG KPI CARD (Agentis style - 2x2 grid)                           */
/* ------------------------------------------------------------------ */
function BigKpiCard({ label, value, icon: Icon, color, bgColor, loading, suffix }) {
  if (loading) {
    return (
      <div className="rounded-xl border border-border/60 bg-card p-5 flex flex-col items-center justify-center min-h-[130px]">
        <Skeleton className="h-10 w-10 rounded-lg mb-3" />
        <Skeleton className="h-3 w-20 mb-2" />
        <Skeleton className="h-8 w-24" />
      </div>
    );
  }
  return (
    <div className={`rounded-xl border border-border/40 p-5 flex flex-col items-center justify-center min-h-[130px] transition-all hover:shadow-md hover:scale-[1.01] ${bgColor || "bg-card"}`}>
      <div
        className="flex items-center justify-center h-11 w-11 rounded-xl mb-3"
        style={{ backgroundColor: `${color}18` }}
      >
        <Icon className="h-5 w-5" style={{ color }} />
      </div>
      <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground mb-1">{label}</p>
      <p className="text-[28px] font-bold leading-tight text-foreground tracking-tight">
        {value}{suffix || ""}
      </p>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  RESERVATION WIDGET (Gerçekleşen / Bekleyen / Sepet Terk)           */
/* ------------------------------------------------------------------ */
function ReservationWidget({ title, icon: Icon, iconColor, items, count, loading, emptyText, type }) {
  const navigate = useNavigate();

  if (loading) {
    return (
      <div className="rounded-xl border border-border/60 bg-card p-4">
        <div className="flex items-center justify-between mb-4">
          <Skeleton className="h-5 w-40" />
          <Skeleton className="h-5 w-5 rounded-full" />
        </div>
        {[1, 2, 3].map((i) => (
          <div key={i} className="flex items-center justify-between py-3 border-b border-border/20 last:border-0">
            <div className="space-y-1.5 flex-1">
              <Skeleton className="h-3 w-3/4" />
            </div>
            <Skeleton className="h-3 w-24" />
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-border/60 bg-card p-4 hover:shadow-sm transition-shadow">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-[15px] font-bold text-foreground">{title}</h3>
        <div className="flex items-center gap-2">
          {count > 0 && (
            <span className="text-[11px] font-medium px-2 py-0.5 rounded-full" style={{ backgroundColor: `${iconColor}15`, color: iconColor }}>
              {count}
            </span>
          )}
          <Icon className="h-5 w-5" style={{ color: iconColor }} />
        </div>
      </div>

      {items && items.length > 0 ? (
        <div className="space-y-0">
          {items.map((item, idx) => (
            <div
              key={item.id || idx}
              className="flex items-center justify-between py-2.5 border-b border-border/15 last:border-0 cursor-pointer hover:bg-muted/30 -mx-2 px-2 rounded-lg transition-colors"
              onClick={() => item.id && navigate(`/app/reservations`)}
            >
              <div className="flex-1 min-w-0 mr-3">
                <p className="text-[13px] text-foreground truncate font-medium">
                  {item.product_name || item.guest_name || "—"}
                </p>
                {item.check_in && item.check_in !== "None" && (
                  <p className="text-[10px] text-muted-foreground/60 mt-0.5">{item.check_in}</p>
                )}
              </div>
              <p className="text-[13px] font-medium text-foreground whitespace-nowrap">
                {item.guest_name || ""}
              </p>
            </div>
          ))}
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center py-6 text-center">
          <div className="h-10 w-10 rounded-full bg-muted/50 flex items-center justify-center mb-2">
            <Icon className="h-4 w-4 text-muted-foreground/60" />
          </div>
          <p className="text-[12px] text-muted-foreground">{emptyText || "Henüz kayıt yok"}</p>
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  WEEKLY SUMMARY TABLE (Haftalık Özet)                               */
/* ------------------------------------------------------------------ */
function WeeklySummaryTable({ data, loading }) {
  if (loading) {
    return (
      <div className="rounded-xl border border-border/60 bg-card p-4">
        <div className="flex items-center justify-between mb-4">
          <Skeleton className="h-5 w-32" />
          <Skeleton className="h-5 w-5" />
        </div>
        {[1, 2, 3, 4, 5].map((i) => (
          <div key={i} className="flex items-center justify-between py-3 border-b border-border/20">
            <Skeleton className="h-3 w-12" />
            <Skeleton className="h-3 w-12" />
            <Skeleton className="h-3 w-12" />
            <Skeleton className="h-3 w-12" />
            <Skeleton className="h-3 w-12" />
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-border/60 bg-card p-4 hover:shadow-sm transition-shadow">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-[15px] font-bold text-foreground">Haftalık Özet</h3>
        <Calendar className="h-5 w-5 text-blue-500" />
      </div>

      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-border/30">
              <th className="text-[11px] font-semibold text-muted-foreground text-left py-2 pr-2">Gün</th>
              <th className="text-[11px] font-semibold text-muted-foreground text-center py-2 px-2">Tur</th>
              <th className="text-[11px] font-semibold text-blue-500 text-center py-2 px-2">Rezervasyon</th>
              <th className="text-[11px] font-semibold text-muted-foreground text-center py-2 px-2">Koltuk</th>
              <th className="text-[11px] font-semibold text-muted-foreground text-center py-2 pl-2">Ödeme</th>
            </tr>
          </thead>
          <tbody>
            {(data || []).map((row, idx) => (
              <tr
                key={idx}
                className={`border-b border-border/10 last:border-0 transition-colors ${
                  row.is_today ? "bg-blue-50/50 dark:bg-blue-950/20" : "hover:bg-muted/20"
                }`}
              >
                <td className="py-2.5 pr-2">
                  <div className="flex flex-col">
                    <span className={`text-[15px] font-bold ${row.is_today ? "text-blue-600 dark:text-blue-400" : "text-foreground"}`}>
                      {row.date}
                    </span>
                    <span className="text-[10px] text-muted-foreground">{row.day_name}</span>
                  </div>
                </td>
                <td className="py-2.5 px-2 text-center">
                  <span className="text-[14px] font-semibold text-foreground">
                    {row.tours > 100 ? "100+" : row.tours}
                  </span>
                  <span className="text-[10px] text-muted-foreground block">Tur</span>
                </td>
                <td className="py-2.5 px-2 text-center">
                  <span className={`text-[14px] font-semibold ${row.reservations > 0 ? "text-blue-600" : "text-blue-400"}`}>
                    {row.reservations}
                  </span>
                  <span className="text-[10px] text-blue-400 block">Rezervasyon</span>
                </td>
                <td className="py-2.5 px-2 text-center">
                  <span className={`text-[14px] font-semibold ${row.pax > 0 ? "text-foreground" : "text-muted-foreground"}`}>
                    {row.pax}
                  </span>
                  <span className="text-[10px] text-muted-foreground block">Koltuk</span>
                </td>
                <td className="py-2.5 pl-2 text-center">
                  <span className={`text-[14px] font-semibold ${row.payments > 0 ? "text-emerald-600" : "text-muted-foreground"}`}>
                    {row.payments > 0 ? `₺${row.payments.toLocaleString("tr-TR")}` : "0"}
                  </span>
                  <span className="text-[10px] text-muted-foreground block">Ödeme</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  POPULAR PRODUCTS CAROUSEL (En Çok Tıklananlar)                     */
/* ------------------------------------------------------------------ */
function PopularProductsCarousel({ products, loading }) {
  const scrollRef = useRef(null);
  const [canScrollLeft, setCanScrollLeft] = useState(false);
  const [canScrollRight, setCanScrollRight] = useState(false);

  const checkScroll = () => {
    if (scrollRef.current) {
      const { scrollLeft, scrollWidth, clientWidth } = scrollRef.current;
      setCanScrollLeft(scrollLeft > 0);
      setCanScrollRight(scrollLeft + clientWidth < scrollWidth - 10);
    }
  };

  useEffect(() => {
    checkScroll();
    const ref = scrollRef.current;
    if (ref) ref.addEventListener("scroll", checkScroll);
    return () => { if (ref) ref.removeEventListener("scroll", checkScroll); };
  }, [products]);

  const scroll = (dir) => {
    if (scrollRef.current) {
      scrollRef.current.scrollBy({ left: dir * 280, behavior: "smooth" });
    }
  };

  if (loading) {
    return (
      <div className="rounded-xl border border-border/60 bg-card p-4">
        <Skeleton className="h-5 w-40 mb-4" />
        <div className="flex gap-3">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-[160px] w-[260px] rounded-xl shrink-0" />
          ))}
        </div>
      </div>
    );
  }

  const defaultImage = "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=400&h=250&fit=crop";

  return (
    <div className="rounded-xl border border-border/60 bg-card p-4 hover:shadow-sm transition-shadow">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-[15px] font-bold text-foreground">En Çok Tıklananlar</h3>
        <div className="flex gap-1">
          <button
            onClick={() => scroll(-1)}
            disabled={!canScrollLeft}
            className={`p-1 rounded-lg border border-border/60 transition-all ${
              canScrollLeft ? "hover:bg-muted/50 text-foreground" : "opacity-30 cursor-not-allowed"
            }`}
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
          <button
            onClick={() => scroll(1)}
            disabled={!canScrollRight}
            className={`p-1 rounded-lg border border-border/60 transition-all ${
              canScrollRight ? "hover:bg-muted/50 text-foreground" : "opacity-30 cursor-not-allowed"
            }`}
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      </div>

      {products && products.length > 0 ? (
        <div
          ref={scrollRef}
          className="flex gap-3 overflow-x-auto scrollbar-hide pb-1"
          style={{ scrollbarWidth: "none", msOverflowStyle: "none" }}
        >
          {products.map((product, idx) => (
            <div
              key={product.product_id || idx}
              className="shrink-0 w-[260px] rounded-xl overflow-hidden border border-border/30 hover:shadow-md transition-all cursor-pointer group"
            >
              <div className="relative h-[130px] overflow-hidden">
                <img
                  src={product.image_url || defaultImage}
                  alt={product.product_name}
                  className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                  onError={(e) => { e.target.src = defaultImage; }}
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent" />
                <div className="absolute bottom-2 left-2 right-2">
                  <p className="text-white text-[13px] font-semibold truncate drop-shadow-lg">
                    {product.product_name}
                  </p>
                  <div className="flex items-center gap-3 mt-1">
                    <span className="flex items-center gap-1 text-white/90 text-[10px]">
                      <Eye className="h-3 w-3" /> {product.view_count} Ziyaret
                    </span>
                    <span className="flex items-center gap-1 text-white/90 text-[10px]">
                      <Ticket className="h-3 w-3" /> {product.reservation_count} Satış
                    </span>
                  </div>
                </div>
                {idx === 0 && product.reservation_count > 0 && (
                  <div className="absolute top-2 right-2 bg-red-500 text-white text-[10px] font-bold rounded-full h-5 w-5 flex items-center justify-center">
                    1
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center py-8 text-center">
          <div className="h-12 w-12 rounded-full bg-muted/50 flex items-center justify-center mb-3">
            <Star className="h-5 w-5 text-muted-foreground/50" />
          </div>
          <p className="text-[12px] text-muted-foreground">Henüz popüler ürün yok</p>
          <p className="text-[11px] text-muted-foreground/60 mt-0.5">Ürünler eklendikçe burada görünecek</p>
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  RECENT CUSTOMERS (Son Üyeler)                                      */
/* ------------------------------------------------------------------ */
function RecentCustomersList({ customers, loading }) {
  if (loading) {
    return (
      <div className="rounded-xl border border-border/60 bg-card p-4">
        <div className="flex items-center justify-between mb-4">
          <Skeleton className="h-5 w-28" />
          <Skeleton className="h-5 w-5" />
        </div>
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="flex items-center justify-between py-3 border-b border-border/20">
            <Skeleton className="h-3 w-40" />
            <Skeleton className="h-3 w-20" />
          </div>
        ))}
      </div>
    );
  }

  const formatDate = (dateStr) => {
    if (!dateStr || dateStr === "None") return "";
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString("tr-TR", { day: "2-digit", month: "2-digit", year: "numeric" });
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="rounded-xl border border-border/60 bg-card p-4 hover:shadow-sm transition-shadow">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-[15px] font-bold text-foreground">Son Üyeler</h3>
        <UserPlus className="h-5 w-5 text-blue-500" />
      </div>

      {customers && customers.length > 0 ? (
        <div className="space-y-0">
          {customers.map((customer, idx) => (
            <div
              key={customer.id || idx}
              className="flex items-center justify-between py-2.5 border-b border-border/15 last:border-0 hover:bg-muted/20 -mx-2 px-2 rounded-lg transition-colors"
            >
              <div className="flex-1 min-w-0 mr-3">
                <p className="text-[13px] font-semibold text-foreground truncate">
                  {customer.name}
                </p>
                <p className="text-[11px] text-muted-foreground truncate">
                  {customer.email}
                </p>
              </div>
              <p className="text-[12px] text-muted-foreground whitespace-nowrap">
                {formatDate(customer.created_at)}
              </p>
            </div>
          ))}
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center py-6 text-center">
          <div className="h-10 w-10 rounded-full bg-muted/50 flex items-center justify-center mb-2">
            <Users className="h-4 w-4 text-muted-foreground/60" />
          </div>
          <p className="text-[12px] text-muted-foreground">Henüz müşteri kaydı yok</p>
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  COMPACT KPI CARD (original style)                                  */
/* ------------------------------------------------------------------ */
function KpiCard({ label, value, icon: Icon, to, color, loading, comfort }) {
  const navigate = useNavigate();
  const handleClick = () => { if (to) navigate(to); };

  if (loading) {
    return (
      <div className={`flex items-center gap-3 rounded-[10px] border border-border/60 bg-card px-3 ${comfort ? "py-4 h-auto" : "py-3 h-[82px]"}`}>
        <Skeleton className="h-9 w-9 rounded-lg shrink-0" />
        <div className="flex-1 space-y-2">
          <Skeleton className="h-3 w-16" />
          <Skeleton className="h-7 w-12" />
        </div>
      </div>
    );
  }

  return (
    <div
      onClick={handleClick}
      className={`group flex items-center gap-3 rounded-[10px] border border-border/60 bg-card px-3
        ${comfort ? "py-4 h-auto" : "py-3 h-[82px]"}
        ${to ? "cursor-pointer hover:border-primary/40 hover:shadow-sm transition-all duration-150" : ""}
      `}
    >
      <div
        className="flex items-center justify-center h-9 w-9 rounded-lg shrink-0"
        style={{ backgroundColor: `${color || "hsl(var(--primary))"}15` }}
      >
        <Icon className="h-4.5 w-4.5" style={{ color: color || "hsl(var(--primary))" }} />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-[11px] leading-tight text-muted-foreground truncate">{label}</p>
        <p className={`${comfort ? "text-[34px]" : "text-[28px]"} font-semibold leading-tight text-foreground tracking-tight`}>{value}</p>
      </div>
      {to && (
        <ChevronRight className="h-3.5 w-3.5 text-muted-foreground/40 group-hover:text-primary transition-colors shrink-0" />
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  MINI DONUT CARD                                                    */
/* ------------------------------------------------------------------ */
function MiniDonutCard({ title, data, colors, loading, emptyText }) {
  const hasData = data && data.some((d) => d.value > 0);

  if (loading) {
    return (
      <div className="rounded-[10px] border border-border/60 bg-card p-4">
        <Skeleton className="h-4 w-24 mb-3" />
        <div className="flex items-center gap-4">
          <Skeleton className="h-[80px] w-[80px] rounded-full shrink-0" />
          <div className="space-y-2 flex-1">
            <Skeleton className="h-3 w-full" />
            <Skeleton className="h-3 w-3/4" />
            <Skeleton className="h-3 w-1/2" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-[10px] border border-border/60 bg-card p-4">
      <p className="text-[13px] font-medium text-foreground mb-3">{title}</p>
      {hasData ? (
        <div className="flex items-center gap-3">
          <div className="shrink-0" style={{ width: 80, height: 80, minWidth: 80, minHeight: 80 }}>
            <PieChart width={80} height={80}>
              <Pie
                data={data}
                dataKey="value"
                cx="50%"
                cy="50%"
                innerRadius={24}
                outerRadius={38}
                strokeWidth={1}
                stroke="hsl(var(--card))"
              >
                {data.map((entry, i) => (
                  <Cell key={i} fill={colors[entry.name] || colors.other || "#94a3b8"} />
                ))}
              </Pie>
            </PieChart>
          </div>
          <div className="flex-1 space-y-1.5 min-w-0">
            {data.map((d) => (
              <div key={d.name} className="flex items-center gap-2 text-[11px]">
                <span
                  className="h-2 w-2 rounded-full shrink-0"
                  style={{ backgroundColor: colors[d.name] || "#94a3b8" }}
                />
                <span className="text-muted-foreground truncate flex-1">{d.label}</span>
                <span className="font-medium text-foreground tabular-nums">{d.value}</span>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center py-4 text-center">
          <div className="h-10 w-10 rounded-full bg-muted/50 flex items-center justify-center mb-2">
            <BarChart3 className="h-4 w-4 text-muted-foreground/60" />
          </div>
          <p className="text-[11px] text-muted-foreground">{emptyText || "Veri yok"}</p>
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  CHART TOGGLE CHIPS                                                 */
/* ------------------------------------------------------------------ */
function ChipGroup({ options, value, onChange }) {
  return (
    <div className="inline-flex rounded-lg border border-border/60 overflow-hidden">
      {options.map((opt) => (
        <button
          key={opt.value}
          onClick={() => onChange(opt.value)}
          className={`px-3 py-1 text-[11px] font-medium transition-colors
            ${value === opt.value
              ? "bg-primary text-primary-foreground"
              : "bg-card text-muted-foreground hover:bg-muted/50"
            }
          `}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  CUSTOM CHART TOOLTIP                                               */
/* ------------------------------------------------------------------ */
function ChartTooltip({ active, payload, label, metric }) {
  if (!active || !payload?.length) return null;
  const val = payload[0]?.value;
  return (
    <div className="rounded-lg border border-border/60 bg-card px-3 py-2 shadow-md">
      <p className="text-[11px] text-muted-foreground">{label}</p>
      <p className="text-[14px] font-semibold text-foreground">
        {metric === "revenue"
          ? `₺${Number(val || 0).toLocaleString("tr-TR", { minimumFractionDigits: 0 })}`
          : val}
      </p>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  ATTENTION LIST                                                     */
/* ------------------------------------------------------------------ */
function AttentionList({ items, loading }) {
  const navigate = useNavigate();

  if (loading) {
    return (
      <div className="rounded-[10px] border border-border/60 bg-card p-4">
        <Skeleton className="h-4 w-36 mb-4" />
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="flex items-center gap-3">
              <Skeleton className="h-8 w-8 rounded-lg shrink-0" />
              <Skeleton className="h-3 w-3/4 flex-1" />
              <Skeleton className="h-5 w-8 rounded" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  const hasItems = items && items.some((it) => it.count > 0);

  return (
    <div className="rounded-[10px] border border-border/60 bg-card p-4">
      <div className="flex items-center gap-2 mb-4">
        <ListChecks className="h-4 w-4 text-amber-500" />
        <p className="text-[14px] font-medium text-foreground">Hemen İlgilenilmesi Gerekenler</p>
      </div>
      {hasItems ? (
        <div className="space-y-1">
          {items.map((item) => (
            <div
              key={item.label}
              onClick={() => item.to && navigate(item.to)}
              className={`flex items-center gap-3 rounded-lg px-3 py-2.5
                ${item.to ? "cursor-pointer hover:bg-muted/50 transition-colors" : ""}
                ${item.count === 0 ? "opacity-40" : ""}
              `}
            >
              <div
                className="flex items-center justify-center h-8 w-8 rounded-lg shrink-0"
                style={{ backgroundColor: `${item.color}12` }}
              >
                <item.icon className="h-3.5 w-3.5" style={{ color: item.color }} />
              </div>
              <p className="text-[13px] text-foreground truncate flex-1">{item.label}</p>
              <span
                className="text-[13px] font-semibold tabular-nums px-2 py-0.5 rounded-md min-w-[32px] text-center"
                style={{
                  color: item.count > 0 ? item.color : undefined,
                  backgroundColor: item.count > 0 ? `${item.color}10` : undefined,
                }}
              >
                {item.count}
              </span>
              {item.to && <ChevronRight className="h-3.5 w-3.5 text-muted-foreground/40 shrink-0" />}
            </div>
          ))}
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center py-6 text-center">
          <div className="h-10 w-10 rounded-full bg-emerald-500/10 flex items-center justify-center mb-2">
            <CheckCircle2 className="h-4 w-4 text-emerald-500" />
          </div>
          <p className="text-[12px] text-muted-foreground">Tüm işler yolunda görünüyor</p>
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  ACTIVITY TIMELINE                                                  */
/* ------------------------------------------------------------------ */
function ActivityTimeline({ loading, events }) {
  if (loading) {
    return (
      <div className="rounded-[10px] border border-border/60 bg-card p-4">
        <Skeleton className="h-4 w-28 mb-4" />
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="flex gap-3">
              <Skeleton className="h-6 w-6 rounded-full shrink-0" />
              <div className="flex-1 space-y-1.5">
                <Skeleton className="h-3 w-full" />
                <Skeleton className="h-2.5 w-1/3" />
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-[10px] border border-border/60 bg-card p-4">
      <div className="flex items-center gap-2 mb-4">
        <Activity className="h-4 w-4 text-blue-500" />
        <p className="text-[14px] font-medium text-foreground">Son Aktiviteler</p>
      </div>
      {events && events.length > 0 ? (
        <div className="space-y-0.5">
          {events.slice(0, 10).map((ev, i) => {
            const time = ev.created_at
              ? new Date(ev.created_at).toLocaleString('tr-TR', { dateStyle: 'short', timeStyle: 'short' })
              : '';
            return (
              <div key={ev.id || i} className="flex gap-3 py-2 border-b border-border/20 last:border-0">
                <div className="h-6 w-6 rounded-full bg-blue-500/10 flex items-center justify-center shrink-0 mt-0.5">
                  <Activity className="h-3 w-3 text-blue-500" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-[12px] text-foreground truncate">{ev.action || 'Bilinmeyen olay'}</p>
                  <p className="text-[10px] text-muted-foreground/60">{time}</p>
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
          <p className="text-[12px] text-muted-foreground">Henüz aktivite kaydı yok</p>
          <p className="text-[11px] text-muted-foreground/60 mt-0.5">
            Rezervasyon ve case işlemleri burada görünecek
          </p>
        </div>
      )}
    </div>
  );
}

/* ================================================================== */
/*  MAIN DASHBOARD                                                     */
/* ================================================================== */
export default function DashboardPage() {
  const user = getUser();
  const location = useLocation();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const isHotel = (user?.roles || []).some((r) => r.startsWith("hotel_"));
  const isAgency = (user?.roles || []).some((r) => r.startsWith("agency_"));

  // Filters
  const [filters, setFilters] = useState(() => resolveFilters(location.search));
  const [density, setDensity] = useState(() => filters.density || 'compact');

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [resSummary, setResSummary] = useState([]);
  const [sales, setSales] = useState([]);
  const [caseCounters, setCaseCounters] = useState({ open: 0, waiting: 0, in_progress: 0 });
  const [activityEvents, setActivityEvents] = useState([]);

  // Enhanced dashboard state
  const [kpiStats, setKpiStats] = useState(null);
  const [resWidgets, setResWidgets] = useState(null);
  const [weeklySummary, setWeeklySummary] = useState([]);
  const [popularProducts, setPopularProducts] = useState([]);
  const [recentCustomers, setRecentCustomers] = useState([]);
  const [enhancedLoading, setEnhancedLoading] = useState(true);

  const chartDays = getPresetDays(filters.preset || '30d');
  const [chartMetric, setChartMetric] = useState("revenue");

  const bookingsBase = isHotel ? "/app/hotel/bookings" : isAgency ? "/app/agency/bookings" : "/app/reservations";
  const casesBase = "/app/ops/guest-cases";
  const isComfort = density === 'comfort';

  /* ---------- fetch original data ---------- */
  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      setLoading(true);
      setError("");
      const safe = async (fn) => {
        try { return await fn(); }
        catch { return null; }
      };
      const [a, b, c, d] = await Promise.all([
        safe(() => api.get("/reports/reservations-summary")),
        safe(() => api.get(`/reports/sales-summary?days=${chartDays}`)),
        safe(() => api.get("/ops-cases/counters")),
        safe(() => api.get("/audit/logs", { params: { range: "7d", limit: 10 } })),
      ]);
      if (cancelled) return;
      if (a?.data) setResSummary(a.data);
      if (b?.data) setSales(b.data);
      if (c?.data) setCaseCounters(c.data);
      if (d?.data) setActivityEvents(d.data);
      setLoading(false);
    };
    load();
    return () => { cancelled = true; };
  }, [chartDays]);

  /* ---------- fetch enhanced dashboard data ---------- */
  useEffect(() => {
    let cancelled = false;
    const loadEnhanced = async () => {
      setEnhancedLoading(true);
      const safe = async (fn) => {
        try { return await fn(); }
        catch { return null; }
      };
      const [kpi, widgets, weekly, popular, customers] = await Promise.all([
        safe(() => api.get("/dashboard/kpi-stats")),
        safe(() => api.get("/dashboard/reservation-widgets")),
        safe(() => api.get("/dashboard/weekly-summary")),
        safe(() => api.get("/dashboard/popular-products")),
        safe(() => api.get("/dashboard/recent-customers")),
      ]);
      if (cancelled) return;
      if (kpi?.data) setKpiStats(kpi.data);
      if (widgets?.data) setResWidgets(widgets.data);
      if (weekly?.data) setWeeklySummary(weekly.data);
      if (popular?.data) setPopularProducts(popular.data);
      if (customers?.data) setRecentCustomers(customers.data);
      setEnhancedLoading(false);
    };
    loadEnhanced();
    return () => { cancelled = true; };
  }, []);

  /* ---------- derived data ---------- */
  const totals = useMemo(() => {
    const map = new Map(resSummary.map((r) => [r.status, r.count]));
    const total = resSummary.reduce((a, r) => a + Number(r.count || 0), 0);
    return {
      total,
      pending: map.get("pending") || 0,
      confirmed: map.get("confirmed") || 0,
      paid: map.get("paid") || 0,
    };
  }, [resSummary]);

  const resDonutData = useMemo(() => [
    { name: "pending", label: "Beklemede", value: totals.pending },
    { name: "confirmed", label: "Onaylı", value: totals.confirmed },
    { name: "paid", label: "Ödendi", value: totals.paid },
    {
      name: "other", label: "Diğer",
      value: Math.max(0, totals.total - totals.pending - totals.confirmed - totals.paid),
    },
  ], [totals]);

  const totalCases = caseCounters.open + caseCounters.waiting + caseCounters.in_progress;
  const caseDonutData = useMemo(() => [
    { name: "open", label: "Açık", value: caseCounters.open },
    { name: "waiting", label: "Beklemede", value: caseCounters.waiting },
    { name: "in_progress", label: "İşlemde", value: caseCounters.in_progress },
  ], [caseCounters]);

  const attentionItems = useMemo(() => [
    { label: "Ödeme Bekleyen Rezervasyonlar", count: totals.pending, icon: Clock, color: "#f59e0b", to: `${bookingsBase}?status=pending` },
    { label: "Onay Bekleyen Rezervasyonlar", count: totals.confirmed, icon: CheckCircle2, color: "#3b82f6", to: `${bookingsBase}?status=confirmed` },
    { label: "Açık Destek Talepleri", count: caseCounters.open, icon: AlertCircle, color: "#ef4444", to: `${casesBase}?status=open` },
    { label: "Beklemede Destek Talepleri", count: caseCounters.waiting, icon: FileWarning, color: "#f59e0b", to: `${casesBase}?status=waiting` },
  ], [totals, caseCounters, bookingsBase, casesBase]);

  const chartData = useMemo(() => {
    if (!sales.length) return [];
    return sales.slice(-chartDays).map((s) => ({
      day: s.day ? s.day.slice(5) : "",
      revenue: s.revenue || 0,
      count: s.count || 0,
    }));
  }, [sales, chartDays]);

  /* ---------- filter handlers ---------- */
  const handleApplyFilters = () => {
    saveToLocalStorage(filters);
    const qs = filtersToQuery(filters);
    navigate(`/app${qs}`, { replace: true });
  };

  const handleResetFilters = () => {
    const reset = { ...DEFAULT_FILTERS, density };
    setFilters(reset);
    saveToLocalStorage(reset);
    navigate('/app', { replace: true });
  };

  const handleDensityChange = (d) => {
    setDensity(d);
    saveDensity(d);
    setFilters((f) => ({ ...f, density: d }));
  };

  const handleExport = () => {
    const dateRange = getPresetDateRange(filters.preset || '30d');
    exportDashboardCSV({
      kpis: {
        'Toplam Rezervasyon': totals.total,
        'Beklemede': totals.pending,
        'Onaylı': totals.confirmed,
        'Ödendi': totals.paid,
        'Açık Talep': caseCounters.open,
        'İşlemdeki Talep': caseCounters.in_progress,
      },
      chartData,
      attentionItems,
      chartMetric,
      dateRange,
    });
  };

  const formatMoney = (val) => {
    if (!val && val !== 0) return "0₺";
    return `${Number(val).toLocaleString("tr-TR", { minimumFractionDigits: 0, maximumFractionDigits: 0 })}₺`;
  };

  /* ================================================================ */
  /*  RENDER                                                           */
  /* ================================================================ */
  return (
    <div className={`space-y-${isComfort ? '6' : '5'} pb-8`} data-testid="dashboard-page">
      {/* ---------- HEADER ---------- */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-[20px] font-bold text-foreground">Genel Bakış</h2>
          <p className="text-[12px] text-muted-foreground mt-0.5">
            Rezervasyon ve operasyon özetini buradan takip edebilirsin.
          </p>
        </div>
        <div className="flex gap-2">
          <DemoSeedButton />
          <Link
            to="/app/products"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-medium rounded-lg border border-border/60 bg-card text-foreground hover:bg-muted/50 transition-colors"
          >
            Ürünler
          </Link>
          <Link
            to="/app/reservations"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-medium rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
          >
            Rezervasyonlar
          </Link>
        </div>
      </div>

      {/* ---------- ACTIVATION CHECKLIST ---------- */}
      <ActivationChecklist />

      {/* ========== ROW 0: AGENTIS-STYLE BIG KPI CARDS (4 cards) ========== */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3" data-testid="big-kpi-cards">
        <BigKpiCard
          label="SATIŞLAR"
          value={formatMoney(kpiStats?.total_sales || 0)}
          icon={BarChart3}
          color="#3b82f6"
          loading={enhancedLoading}
        />
        <BigKpiCard
          label="REZERVASYON"
          value={`${kpiStats?.completed_reservations || 0} / ${kpiStats?.total_reservations || 0}`}
          icon={Ticket}
          color="#6366f1"
          loading={enhancedLoading}
        />
        <BigKpiCard
          label="DÖNÜŞÜM ORANI"
          value={`%${(kpiStats?.conversion_rate || 0).toFixed(3)}`}
          icon={ShoppingCart}
          color="#f59e0b"
          loading={enhancedLoading}
        />
        <BigKpiCard
          label="ONLINE"
          value={kpiStats?.online_count || 0}
          icon={Users}
          color="#10b981"
          loading={enhancedLoading}
        />
      </div>

      {/* ========== ROW 1: RESERVATION WIDGETS (3 cards) ========== */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <ReservationWidget
          title="Gerçekleşen Rezervasyonlar"
          icon={CheckCircle2}
          iconColor="#10b981"
          items={resWidgets?.completed || []}
          count={resWidgets?.completed_count || 0}
          loading={enhancedLoading}
          emptyText="Tamamlanan rezervasyon yok"
          type="completed"
        />
        <ReservationWidget
          title="Bekleyen Rezervasyonlar"
          icon={RefreshCw}
          iconColor="#f59e0b"
          items={resWidgets?.pending || []}
          count={resWidgets?.pending_count || 0}
          loading={enhancedLoading}
          emptyText="Bekleyen rezervasyon yok"
          type="pending"
        />
        <ReservationWidget
          title="Sepet Terk"
          icon={XCircle}
          iconColor="#ef4444"
          items={resWidgets?.abandoned || []}
          count={resWidgets?.abandoned_count || 0}
          loading={enhancedLoading}
          emptyText="Terk edilen sepet yok"
          type="abandoned"
        />
      </div>

      {/* ========== ROW 2: EN ÇOK TIKLANANLAR CAROUSEL ========== */}
      <PopularProductsCarousel products={popularProducts} loading={enhancedLoading} />

      {/* ========== ROW 3: HAFTALIK ÖZET + SON ÜYELER ========== */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <WeeklySummaryTable data={weeklySummary} loading={enhancedLoading} />
        <RecentCustomersList customers={recentCustomers} loading={enhancedLoading} />
      </div>

      {/* ---------- FILTER BAR ---------- */}
      <DashboardFilterBar
        filters={filters}
        onFiltersChange={setFilters}
        onApply={handleApplyFilters}
        onReset={handleResetFilters}
        onExport={handleExport}
        density={density}
        onDensityChange={handleDensityChange}
      />

      {/* ---------- ERROR ---------- */}
      {error && (
        <div className="rounded-[10px] border border-rose-200 bg-rose-50 dark:border-rose-800 dark:bg-rose-950/30 px-4 py-2.5 text-[12px] text-rose-700 dark:text-rose-300" data-testid="dash-error">
          {error}
        </div>
      )}

      {/* ========== ROW 4: DETAILED KPI BAR ========== */}
      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3" data-testid="dashboard-kpi-bar">
        <KpiCard label="Toplam Rezervasyon" value={totals.total} icon={Ticket} color="#6366f1" to={bookingsBase} loading={loading} comfort={isComfort} />
        <KpiCard label="Beklemede" value={totals.pending} icon={Clock} color="#f59e0b" to={`${bookingsBase}?status=pending`} loading={loading} comfort={isComfort} />
        <KpiCard label="Onaylı" value={totals.confirmed} icon={CheckCircle2} color="#3b82f6" to={`${bookingsBase}?status=confirmed`} loading={loading} comfort={isComfort} />
        <KpiCard label="Ödendi" value={totals.paid} icon={TrendingUp} color="#10b981" to={`${bookingsBase}?status=paid`} loading={loading} comfort={isComfort} />
        <KpiCard label="Açık Talep" value={caseCounters.open} icon={AlertCircle} color="#ef4444" to={`${casesBase}?status=open`} loading={loading} comfort={isComfort} />
        <KpiCard label="İşlemdeki Talep" value={caseCounters.in_progress} icon={Activity} color="#8b5cf6" to={`${casesBase}?status=in_progress`} loading={loading} comfort={isComfort} />
      </div>

      {/* ========== ROW 5: CHART + RIGHT RAIL ========== */}
      <div className="grid grid-cols-1 xl:grid-cols-[1fr_320px] gap-4">
        <div className="rounded-[10px] border border-border/60 bg-card p-4">
          <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
            <p className="text-[14px] font-medium text-foreground">Satış Grafiği</p>
            <ChipGroup
              options={[
                { label: "Satış", value: "revenue" },
                { label: "Rezervasyon", value: "count" },
              ]}
              value={chartMetric}
              onChange={setChartMetric}
            />
          </div>
          {loading ? (
            <div className="space-y-3" style={{ minHeight: 280 }}>
              <div className="flex items-end gap-1 h-[260px] px-4">
                {[65, 40, 75, 50, 85, 35, 60, 45, 70, 55, 80, 42, 68, 52].map((h, i) => (
                  <Skeleton key={i} className="flex-1 rounded-t" style={{ height: `${h}%` }} />
                ))}
              </div>
            </div>
          ) : chartData.length > 0 ? (
            <div style={{ minHeight: 280, minWidth: 200 }} data-testid="sales-chart">
              <ResponsiveContainer width="100%" height={280} minWidth={200}>
                <BarChart data={chartData} margin={{ left: 0, right: 4, top: 8, bottom: 0 }}>
                  <XAxis dataKey="day" tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} axisLine={false} tickLine={false} width={40} />
                  <Tooltip content={<ChartTooltip metric={chartMetric} />} cursor={{ fill: "hsl(var(--muted))", opacity: 0.4 }} />
                  <Bar dataKey={chartMetric} fill="hsl(var(--primary))" radius={[6, 6, 0, 0]} maxBarSize={32} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center text-center" style={{ minHeight: 280 }}>
              <div className="h-12 w-12 rounded-full bg-muted/50 flex items-center justify-center mb-3">
                <BarChart3 className="h-5 w-5 text-muted-foreground/50" />
              </div>
              <p className="text-[13px] text-muted-foreground">Grafik verisi bulunamadı</p>
              <p className="text-[11px] text-muted-foreground/60 mt-0.5">Son {chartDays} günde satış kaydı yok</p>
            </div>
          )}
        </div>

        <div className="flex flex-col gap-3">
          <MiniDonutCard title="Rezervasyon Dağılımı" data={resDonutData} colors={STATUS_COLORS} loading={loading} emptyText="Rezervasyon verisi yok" />
          <MiniDonutCard title="Talep Dağılımı" data={caseDonutData} colors={{ open: "#ef4444", waiting: "#f59e0b", in_progress: "#3b82f6" }} loading={loading} emptyText="Talep verisi yok" />
        </div>
      </div>

      {/* ========== ROW 6: ATTENTION + ACTIVITY ========== */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <AttentionList items={attentionItems} loading={loading} />
        <ActivityTimeline loading={loading} events={activityEvents} />
      </div>
    </div>
  );
}
