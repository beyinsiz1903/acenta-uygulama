import React, { useEffect, useMemo, useState, useCallback } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { formatMoney, formatMoneyCompact } from "../lib/format";
import {
  LayoutGrid, CalendarDays, Ticket, Users, Layers, FileText,
  Building2, Settings, BarChart3, LogOut, Menu, Hotel,
  Link as LinkIcon, AlertTriangle, ChevronLeft, ChevronRight,
  Inbox, Bell, PanelLeftClose, PanelLeft,
  Briefcase, ShieldCheck, TrendingUp, MessageSquare, Globe,
  ClipboardList, Tag, Megaphone, Network, DollarSign,
  Scale, Activity, Eye, Zap, BookOpen, Search,
  Palette, Download, Calendar,
} from "lucide-react";

import { Button } from "./ui/button";
import { Sheet, SheetContent } from "./ui/sheet";
import ThemeToggle from "./ThemeToggle";
import { cn } from "../lib/utils";
import { api, clearToken, getUser } from "../lib/api";
import { getMenuForUser } from "../config/menuConfig";
import { FeatureProvider, useFeatures } from "../contexts/FeatureContext";
import { ProductModeProvider, useProductMode } from "../contexts/ProductModeContext";
import { Badge as UIBadge } from "./ui/badge";
import { fetchPartnerNotificationsSummary } from "../lib/partnerGraph";
import { getActiveTenantKey, getActiveTenantId, setActiveTenantId, subscribeTenantChange } from "../lib/tenantContext";
import NotificationDrawer from "./NotificationDrawer";
import NotificationBell from "./NotificationBell";
import TrialBanner from "./TrialBanner";

/* ------------------------------------------------------------------ */
/*  Sidebar collapse persistence                                       */
/* ------------------------------------------------------------------ */
const COLLAPSE_KEY = "sidebar_collapsed";
function loadCollapsed() {
  try { return localStorage.getItem(COLLAPSE_KEY) === "true"; } catch { return false; }
}
function saveCollapsed(v) {
  try { localStorage.setItem(COLLAPSE_KEY, v ? "true" : "false"); } catch { /* */ }
}

/* ------------------------------------------------------------------ */
/*  ICON MAP for sidebar items                                         */
/* ------------------------------------------------------------------ */
const sidebarIconMap = {
  "Dashboard": LayoutGrid,
  "Ürünler": Layers,
  "Müsaitlik": CalendarDays,
  "Rezervasyonlar": Ticket,
  "Müşteriler": Users,
  "CRM Müşteriler": Users,
  "CRM Duplicate Müşteriler": Users,
  "CRM Pipeline": TrendingUp,
  "CRM Görevler": ClipboardList,
  "CRM Olaylar": Activity,
  "Inbox": Inbox,
  "B2B / Acenteler": Building2,
  "B2B Rezervasyon": Ticket,
  "Raporlar": BarChart3,
  "Ayarlar": Settings,
  "Acentalar": Building2,
  "Oteller": Hotel,
  "Link Yönetimi": LinkIcon,
  "Otellerim": Hotel,
  "Mutabakat": Scale,
  "Exposure & Aging": BarChart3,
  "B2B Dashboard": BarChart3,
  "Turlar": Globe,
  "CMS Sayfaları": BookOpen,
  "Kampanyalar": Megaphone,
  "Partnerler": Network,
  "B2B Marketplace": Globe,
  "Katalog": Search,
  "Otel Kataloğu": Hotel,
  "Fiyatlandırma": Tag,
  "Kuponlar": Tag,
  "Onay Görevleri": ShieldCheck,
  "Finans / İadeler": DollarSign,
  "Exposure & Aging (Acenta)": BarChart3,
  "B2B Acenteler": Building2,
  "B2B Funnel": TrendingUp,
  "B2B Duyuruları": Megaphone,
  "Finans / Mutabakat": Scale,
  "Ops / B2B": Briefcase,
  "Tenant Özellikleri": Zap,
  "Audit Log": Eye,
  "Revenue Analytics": TrendingUp,
  "Match Listesi": ShieldCheck,
  "Match Risk Raporu": AlertTriangle,
  "Match Risk Trendleri": TrendingUp,
  "Match Alert Politikaları": Bell,
  "Aksiyon Politikaları": ShieldCheck,
  "Export Çalıştırma": FileText,
  "Genel Bakış": LayoutGrid,
  "Gelen Talepler": Inbox,
  "Stop Sell": AlertTriangle,
  "Allocations": CalendarDays,
  "Entegrasyonlar": Zap,
  "Yardım": MessageSquare,
  "Rezervasyonlarım": Ticket,
  "Ops Tasks": ClipboardList,
  "Ops Incidents": AlertTriangle,
};

/* ------------------------------------------------------------------ */
/*  GROUPED SIDEBAR SECTIONS for admin                                  */
/* ------------------------------------------------------------------ */
const ADMIN_GROUPED_NAV = [
  {
    group: "CORE",
    items: [
      { to: "/app", label: "Dashboard", icon: LayoutGrid, end: true, modeKey: "dashboard", minMode: "lite" },
      { to: "/app/reservations", label: "Rezervasyonlar", icon: Ticket, modeKey: "rezervasyonlar", minMode: "lite" },
      { to: "/app/products", label: "Ürünler", icon: Layers, modeKey: "urunler", minMode: "lite" },
      { to: "/app/inventory", label: "Müsaitlik", icon: CalendarDays, feature: "inventory", modeKey: "musaitlik", minMode: "lite" },
    ],
  },
  {
    group: "CRM",
    items: [
      { to: "/app/crm/customers", label: "Müşteriler", icon: Users, feature: "crm", modeKey: "musteriler", minMode: "lite" },
      { to: "/app/crm/pipeline", label: "Pipeline", icon: TrendingUp, feature: "crm", modeKey: "pipeline", minMode: "lite" },
      { to: "/app/crm/tasks", label: "Görevler", icon: ClipboardList, feature: "crm", modeKey: "gorevler", minMode: "lite" },
      { to: "/app/inbox", label: "Inbox", icon: Inbox, modeKey: "inbox", minMode: "lite" },
    ],
  },
  {
    group: "B2B AĞ",
    minGroupMode: "pro",
    items: [
      { to: "/app/partners", label: "Partner Yönetimi", icon: Network, modeKey: "partner_yonetimi", minMode: "pro" },
      { to: "/app/b2b", label: "B2B Acenteler", icon: Building2, feature: "b2b", modeKey: "b2b_acenteler", minMode: "pro" },
      { to: "/app/admin/b2b/marketplace", label: "Marketplace", icon: Globe, modeKey: "marketplace", minMode: "pro" },
      { to: "/app/admin/b2b/funnel", label: "B2B Funnel", icon: TrendingUp, modeKey: "b2b_funnel", minMode: "pro" },
    ],
  },
  {
    group: "FİNANS",
    items: [
      { to: "/app/finance/webpos", label: "WebPOS", icon: DollarSign, feature: "webpos", modeKey: "webpos", minMode: "pro" },
      { to: "/app/admin/finance/settlements", label: "Mutabakat", icon: Scale, modeKey: "mutabakat", minMode: "pro" },
      { to: "/app/admin/finance/refunds", label: "İadeler", icon: DollarSign, modeKey: "iadeler", minMode: "lite" },
      { to: "/app/admin/finance/exposure", label: "Exposure", icon: BarChart3, modeKey: "exposure", minMode: "pro" },
      { to: "/app/reports", label: "Raporlar", icon: BarChart3, feature: "reports", modeKey: "raporlar", minMode: "lite" },
    ],
  },
  {
    group: "OPS",
    minGroupMode: "pro",
    items: [
      { to: "/app/ops/guest-cases", label: "Guest Cases", icon: MessageSquare, modeKey: "guest_cases", minMode: "pro" },
      { to: "/app/ops/tasks", label: "Ops Tasks", icon: ClipboardList, modeKey: "ops_tasks", minMode: "pro" },
      { to: "/app/ops/incidents", label: "Incidents", icon: AlertTriangle, modeKey: "ops_incidents", minMode: "pro" },
    ],
  },
  {
    group: "YÖNETİM",
    items: [
      { to: "/app/admin/agencies", label: "Acentalar", icon: Building2, modeKey: "acentalar", minMode: "pro" },
      { to: "/app/admin/hotels", label: "Oteller", icon: Hotel, modeKey: "oteller", minMode: "lite" },
      { to: "/app/admin/tours", label: "Turlar", icon: Globe, modeKey: "turlar", minMode: "lite" },
      { to: "/app/admin/pricing", label: "Fiyatlandırma", icon: Tag, modeKey: "fiyatlandirma", minMode: "pro" },
      { to: "/app/admin/coupons", label: "Kuponlar", icon: Tag, modeKey: "kuponlar", minMode: "pro" },
      { to: "/app/admin/campaigns", label: "Kampanyalar", icon: Megaphone, modeKey: "kampanyalar", minMode: "pro" },
      { to: "/app/admin/links", label: "Linkler", icon: LinkIcon, modeKey: "linkler", minMode: "pro" },
      { to: "/app/admin/cms/pages", label: "CMS", icon: BookOpen, modeKey: "cms", minMode: "pro" },
      { to: "/app/admin/tenant-features", label: "Tenant Ayarları", icon: Zap, modeKey: "tenant_ayarlari", minMode: "enterprise" },
      { to: "/app/admin/tenant-health", label: "Tenant Sağlık", icon: Activity, modeKey: "tenant_saglik", minMode: "enterprise" },
      { to: "/app/admin/audit-logs", label: "Audit Log", icon: Eye, modeKey: "audit_log", minMode: "enterprise" },
      { to: "/app/settings", label: "Ayarlar", icon: Settings, modeKey: "ayarlar", minMode: "lite" },
    ],
  },
  {
    group: "ENTERPRISE",
    minGroupMode: "enterprise",
    items: [
      { to: "/app/admin/branding", label: "White-Label", icon: Palette, modeKey: "white_label", minMode: "enterprise" },
      { to: "/app/admin/approval-inbox", label: "Onay İstekleri", icon: ShieldCheck, modeKey: "onay_istekleri", minMode: "enterprise" },
      { to: "/app/admin/tenant-export", label: "Veri Export", icon: Download, modeKey: "veri_export", minMode: "enterprise" },
      { to: "/app/admin/scheduled-reports", label: "Zamanlanmış Raporlar", icon: Calendar, modeKey: "zamanlanmis_raporlar", minMode: "enterprise" },
      { to: "/app/admin/efatura", label: "E-Fatura", icon: FileText, modeKey: "efatura", minMode: "enterprise" },
      { to: "/app/admin/sms", label: "SMS Bildirimleri", icon: MessageSquare, modeKey: "sms", minMode: "enterprise" },
      { to: "/app/admin/tickets", label: "QR Bilet", icon: Ticket, modeKey: "qr_bilet", minMode: "enterprise" },
    ],
  },
];

/* ------------------------------------------------------------------ */
/*  Legacy nav helper                                                   */
/* ------------------------------------------------------------------ */
function userHasRole(user, allowed) {
  const roles = user?.roles || [];
  return allowed.some((r) => roles.includes(r));
}

/* ================================================================== */
/*  SIDEBAR ITEM                                                       */
/* ================================================================== */
function SidebarItem({ to, label, icon: Icon, collapsed, end, onClick }) {
  return (
    <NavLink
      to={to}
      end={end}
      onClick={onClick}
      className={({ isActive }) =>
        cn(
          "flex items-center gap-2.5 rounded-lg px-2.5 py-1.5 text-[13px] font-medium transition-colors",
          isActive
            ? "bg-primary text-primary-foreground shadow-sm"
            : "text-muted-foreground hover:bg-accent hover:text-foreground",
          collapsed && "justify-center px-2"
        )
      }
      title={collapsed ? label : undefined}
    >
      <Icon className="h-4 w-4 shrink-0" />
      {!collapsed && <span className="truncate">{label}</span>}
    </NavLink>
  );
}

/* ================================================================== */
/*  MAIN APP SHELL                                                     */
/* ================================================================== */
export default function AppShell() {
  const user = getUser();
  const location = useLocation();
  const navigate = useNavigate();

  const [resSummary, setResSummary] = useState([]);
  const [sales, setSales] = useState([]);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [partnerSummary, setPartnerSummary] = useState(null);
  const [activeTenantKey, setActiveTenantKeyState] = useState(() => getActiveTenantKey());
  const [collapsed, setCollapsed] = useState(() => loadCollapsed());
  const [notifOpen, setNotifOpen] = useState(false);
  const [onboardingChecked, setOnboardingChecked] = useState(false);

  // Enterprise White-Label branding
  const [branding, setBranding] = useState(null);
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await api.get("/admin/whitelabel-settings");
        if (!cancelled && res.data) {
          setBranding(res.data);
          // Apply brand color as CSS variable
          if (res.data.primary_color) {
            document.documentElement.style.setProperty("--brand-color", res.data.primary_color);
          }
        }
      } catch { /* No branding or not admin - use defaults */ }
    })();
    return () => { cancelled = true; };
  }, []);

  const brandName = branding?.company_name || branding?.brand_name || "Acenta Master";
  const brandLogo = branding?.logo_url;
  const brandInitial = brandName.charAt(0).toUpperCase();

  // ── P0: Onboarding auto-redirect ──────────────────────────
  useEffect(() => {
    if (onboardingChecked) return;
    if (location.pathname === "/app/onboarding") { setOnboardingChecked(true); return; }
    let cancelled = false;
    (async () => {
      try {
        const res = await api.get("/onboarding/state");
        if (cancelled) return;
        const state = res.data;
        if (state && !state.completed_at && !state.completed && state.steps) {
          navigate("/app/onboarding", { replace: true });
          return;
        }
      } catch { /* legacy tenant or no onboarding state – skip */ }
      if (!cancelled) setOnboardingChecked(true);
    })();
    return () => { cancelled = true; };
  }, [location.pathname, onboardingChecked, navigate]);

  // Tenant setup
  useEffect(() => {
    try { void getActiveTenantKey(); } catch { /* */ }
  }, []);

  // Fetch sidebar metrics
  useEffect(() => {
    (async () => {
      try {
        const [a, b] = await Promise.all([
          api.get("/reports/reservations-summary"),
          api.get("/reports/sales-summary?days=7"),
        ]);
        setResSummary(a.data || []);
        setSales(b.data || []);
      } catch { /* sidebar metrics are optional */ }
    })();
  }, []);

  // Tenant sync
  useEffect(() => {
    const syncFromStorage = () => { setActiveTenantKeyState(getActiveTenantKey()); };
    syncFromStorage();
    try {
      const currentId = getActiveTenantId();
      const defId = process.env.REACT_APP_DEFAULT_TENANT_ID;
      if (!currentId && defId) setActiveTenantId(defId);
    } catch { /* */ }

    let unsubscribe = () => {};
    if (typeof window !== "undefined") {
      unsubscribe = subscribeTenantChange((detail) => {
        const nextKey = detail?.tenantKey ?? getActiveTenantKey();
        setActiveTenantKeyState(nextKey);
      });
      window.addEventListener("storage", syncFromStorage);
    }
    return () => {
      if (typeof window !== "undefined") window.removeEventListener("storage", syncFromStorage);
      unsubscribe();
    };
  }, []);

  // Partner notifications
  useEffect(() => {
    let active = true;
    let intervalId;
    const loadSummary = async () => {
      try {
        const data = await fetchPartnerNotificationsSummary();
        if (active) setPartnerSummary(data);
      } catch { /* */ }
    };
    void loadSummary();
    intervalId = window.setInterval(loadSummary, 60_000);
    return () => { active = false; if (intervalId) window.clearInterval(intervalId); };
  }, [activeTenantKey]);

  // Build stamp
  useEffect(() => {
    if (typeof window !== "undefined" && window.location.search?.includes("e2e=1")) {
      import("../version").then(({ BUILD_STAMP }) => {
        window.__BUILD_STAMP__ = BUILD_STAMP;
      });
    }
  }, []);

  const sidebarStats = useMemo(() => {
    const map = new Map((resSummary || []).map((r) => [r.status, Number(r.count || 0)]));
    const total = (resSummary || []).reduce((a, r) => a + Number(r.count || 0), 0);
    const revenue7d = (sales || []).reduce((a, r) => a + Number(r.revenue || 0), 0);
    return { total, pending: map.get("pending") || 0, revenue7d };
  }, [resSummary, sales]);

  const isAdmin = (user?.roles || []).some((r) => ["super_admin", "admin"].includes(r));
  const { hasFeature, loading: featuresLoading, quotaAlerts } = useFeatures();
  const { mode: productMode, isAtLeast: isModeAtLeast, hiddenNavItems, labelOverrides, loading: modeLoading } = useProductMode();

  /* Mode-aware nav filter helper */
  const MODE_ORDER_MAP = { lite: 0, pro: 1, enterprise: 2 };
  const currentModeLevel = MODE_ORDER_MAP[productMode] ?? 2;

  const filterNavByMode = useCallback((items) => {
    return items.filter((it) => {
      // Feature flag filter
      if (it.feature && !(!featuresLoading && hasFeature(it.feature))) return false;
      // Mode filter: item's minMode must be <= current mode
      if (it.minMode) {
        const itemLevel = MODE_ORDER_MAP[it.minMode] ?? 0;
        if (itemLevel > currentModeLevel) return false;
      }
      // Server-side hidden items check
      if (it.modeKey && hiddenNavItems.includes(it.modeKey)) return false;
      return true;
    });
  }, [featuresLoading, hasFeature, currentModeLevel, hiddenNavItems]);

  const toggleCollapse = () => {
    setCollapsed((v) => {
      const next = !v;
      saveCollapsed(next);
      return next;
    });
  };

  /* ================================================================ */
  /*  RENDER                                                           */
  /* ================================================================ */
  return (
    <FeatureProvider>
    <div className="min-h-screen bg-background">
      {/* ========== TOP BAR ========== */}
      <div className="sticky top-0 z-40 border-b bg-background/80 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="flex items-center justify-between px-4 py-2.5">
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="icon"
              className="md:hidden h-8 w-8"
              onClick={() => setMobileNavOpen(true)}
              data-testid="mobile-nav-open"
            >
              <Menu className="h-5 w-5" />
            </Button>
            <div className="hidden md:flex items-center gap-2">
              {brandLogo ? (
                <img src={brandLogo} alt={brandName} className="h-7 w-7 rounded-lg object-contain" data-testid="brand-logo" />
              ) : (
                <div className="h-7 w-7 rounded-lg bg-primary text-primary-foreground grid place-items-center font-semibold text-xs" style={branding?.primary_color ? { backgroundColor: branding.primary_color } : {}}>
                  {brandInitial}
                </div>
              )}
              <span className="text-[13px] font-semibold text-foreground" data-testid="brand-name">{brandName}</span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Partner inbox */}
            <NavLink
              to="/app/partners"
              className={({ isActive }) =>
                cn(
                  "relative inline-flex items-center justify-center rounded-lg border px-2 py-1 text-xs transition hover:bg-accent hover:text-foreground",
                  isActive ? "bg-primary text-primary-foreground border-primary" : "border-border text-muted-foreground"
                )
              }
            >
              <Inbox className="h-3.5 w-3.5 mr-1" />
              <span className="hidden sm:inline text-[11px]">Partner</span>
              {partnerSummary?.counts?.invites_received > 0 && (
                <UIBadge
                  variant="destructive"
                  className="ml-1 h-4 min-w-[1.25rem] px-1 text-[10px] flex items-center justify-center rounded-full"
                >
                  {partnerSummary.counts.invites_received}
                </UIBadge>
              )}
            </NavLink>

            {/* Notification bell - in-app notifications */}
            <NotificationBell />

            {/* Activity log bell */}
            <button
              onClick={() => setNotifOpen(true)}
              className="relative inline-flex items-center justify-center h-8 w-8 rounded-lg border border-border text-muted-foreground hover:bg-accent hover:text-foreground transition"
              data-testid="notif-bell"
              title="Aktivite Logu"
            >
              <Bell className="h-4 w-4" />
            </button>

            <ThemeToggle />

            <div className="hidden sm:block text-right">
              <div className="text-[12px] font-medium text-foreground">{user?.name || user?.email}</div>
              <div className="text-[10px] text-muted-foreground">{(user?.roles || []).join(", ")}</div>
            </div>

            <Button
              variant="outline"
              size="sm"
              data-testid="logout-btn"
              onClick={() => { clearToken(); window.location.href = "/login"; }}
              className="gap-1.5 h-8 text-[11px]"
            >
              <LogOut className="h-3.5 w-3.5" />
              Çıkış
            </Button>
          </div>
        </div>
      </div>

      {/* ========== NOTIFICATION DRAWER ========== */}
      <NotificationDrawer open={notifOpen} onClose={() => setNotifOpen(false)} />

      {/* ========== MOBILE NAV DRAWER ========== */}
      <Sheet open={mobileNavOpen} onOpenChange={setMobileNavOpen}>
        <SheetContent side="left" className="p-0 w-[280px]" data-testid="mobile-nav-sheet">
          <div className="border-b px-4 py-3">
            <div className="flex items-center gap-2">
              {brandLogo ? (
                <img src={brandLogo} alt={brandName} className="h-8 w-8 rounded-lg object-contain" />
              ) : (
                <div className="h-8 w-8 rounded-lg bg-primary text-primary-foreground grid place-items-center font-semibold text-xs" style={branding?.primary_color ? { backgroundColor: branding.primary_color } : {}}>
                  {brandInitial}
                </div>
              )}
              <div>
                <div className="text-[13px] font-semibold text-foreground">{brandName}</div>
                <div className="text-[10px] text-muted-foreground">{user?.email}</div>
              </div>
            </div>
          </div>
          <div className="overflow-y-auto h-[calc(100vh-120px)] px-3 py-3">
            {ADMIN_GROUPED_NAV.map((section) => {
              // Group-level mode check
              if (section.minGroupMode) {
                const groupLevel = MODE_ORDER_MAP[section.minGroupMode] ?? 0;
                if (groupLevel > currentModeLevel) return null;
              }
              const visibleItems = filterNavByMode(section.items);
              if (!visibleItems.length) return null;
              return (
              <div key={section.group} className="mb-3">
                <div className="px-2 py-1 text-[10px] font-bold text-muted-foreground/70 uppercase tracking-wider">
                  {section.group}
                </div>
                {visibleItems.map((item) => (
                    <SidebarItem
                      key={item.to}
                      to={item.to}
                      label={item.label}
                      icon={item.icon}
                      end={item.end}
                      onClick={() => setMobileNavOpen(false)}
                    />
                  ))}
              </div>
              );
            })}
          </div>
          <div className="border-t px-3 py-3">
            <Button
              variant="outline"
              size="sm"
              className="w-full gap-2 text-[11px]"
              onClick={() => { setMobileNavOpen(false); clearToken(); window.location.href = "/login"; }}
              data-testid="mobile-logout"
            >
              <LogOut className="h-3.5 w-3.5" /> Çıkış
            </Button>
          </div>
        </SheetContent>
      </Sheet>

      {/* ========== MAIN LAYOUT ========== */}
      <div className="flex">
        {/* --- Desktop Sidebar --- */}
        <aside
          className={cn(
            "hidden md:flex flex-col border-r bg-card/60 sticky top-[53px] h-[calc(100vh-53px)] transition-all duration-200 shrink-0",
            collapsed ? "w-[56px]" : "w-[220px]"
          )}
          data-testid="sidebar"
        >
          {/* Collapse toggle */}
          <div className="flex items-center justify-end px-2 py-1.5 border-b border-border/40">
            <button
              onClick={toggleCollapse}
              className="h-7 w-7 rounded-md flex items-center justify-center hover:bg-muted/50 transition-colors text-muted-foreground"
              data-testid="sidebar-toggle"
              title={collapsed ? "Genişlet" : "Daralt"}
            >
              {collapsed ? <PanelLeft className="h-4 w-4" /> : <PanelLeftClose className="h-4 w-4" />}
            </button>
          </div>

          {/* Mini stats (only when expanded) */}
          {!collapsed && (
            <div className="grid grid-cols-3 gap-1 px-2 py-2 border-b border-border/40">
              <div className="rounded-md bg-muted/30 p-1.5 text-center">
                <div className="text-[9px] text-muted-foreground">Toplam</div>
                <div className="text-[12px] font-semibold text-foreground" data-testid="sb-total">{sidebarStats.total}</div>
              </div>
              <div className="rounded-md bg-muted/30 p-1.5 text-center">
                <div className="text-[9px] text-muted-foreground">Bekleyen</div>
                <div className="text-[12px] font-semibold text-foreground" data-testid="sb-pending">{sidebarStats.pending}</div>
              </div>
              <div className="rounded-md bg-muted/30 p-1.5 text-center">
                <div className="text-[9px] text-muted-foreground">Ciro 7G</div>
                <div className="text-[12px] font-semibold text-foreground" data-testid="sb-rev7">{formatMoneyCompact(sidebarStats.revenue7d, "TRY")}</div>
              </div>
            </div>
          )}

          {/* Nav sections */}
          <nav className="flex-1 overflow-y-auto px-2 py-2 space-y-3">
            {ADMIN_GROUPED_NAV.map((section) => {
              // Group-level mode check
              if (section.minGroupMode) {
                const groupLevel = MODE_ORDER_MAP[section.minGroupMode] ?? 0;
                if (groupLevel > currentModeLevel) return null;
              }
              const visibleItems = filterNavByMode(section.items);
              if (!visibleItems.length) return null;
              return (
                <div key={section.group}>
                  {!collapsed && (
                    <div className="px-2 py-0.5 text-[9px] font-bold text-muted-foreground/60 uppercase tracking-wider">
                      {section.group}
                    </div>
                  )}
                  {collapsed && <div className="h-px bg-border/40 mx-1 my-1" />}
                  <div className="space-y-0.5">
                    {visibleItems.map((item) => (
                      <SidebarItem
                        key={item.to}
                        to={item.to}
                        label={item.label}
                        icon={item.icon}
                        collapsed={collapsed}
                        end={item.end}
                      />
                    ))}
                  </div>
                </div>
              );
            })}
          </nav>

          {/* Footer */}
          {!collapsed && (
            <div className="border-t border-border/40 px-3 py-2">
              <div className="text-[9px] text-muted-foreground/50">
                {(user?.roles || ["-"])[0]} · {new Date().toLocaleDateString("tr-TR")}
              </div>
            </div>
          )}
        </aside>

        {/* --- Main Content --- */}
        <main className="flex-1 min-h-[calc(100vh-53px)] overflow-auto">
          <TrialBanner />
          {quotaAlerts && quotaAlerts.length > 0 && (
            <div className="mx-4 mt-3 space-y-2" data-testid="quota-alert-banners">
              {quotaAlerts.map((q) => (
                <div
                  key={q.metric}
                  className={`rounded-lg border px-4 py-2 text-[12px] flex items-center justify-between ${
                    q.exceeded
                      ? "border-destructive/40 bg-destructive/5 text-destructive"
                      : "border-amber-500/40 bg-amber-500/5 text-amber-700"
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
                    <span>{q.exceeded ? "Quota aşıldı" : "Quota'ya yaklaşıyorsunuz"}: {q.used}/{q.quota} ({Math.round(q.ratio * 100)}%)</span>
                  </div>
                  {q.recommendation && <span className="text-[10px] font-medium shrink-0 ml-3">{q.recommendation}</span>}
                </div>
              ))}
            </div>
          )}
          <div className="p-4 md:p-6 max-w-[1400px]">
            <Outlet />
          </div>
        </main>
      </div>

      <footer className="border-t bg-background">
        <div className="px-4 py-3 text-[10px] text-muted-foreground">
          © {new Date().getFullYear()} — v1
        </div>
      </footer>
    </div>
    </FeatureProvider>
  );
}
