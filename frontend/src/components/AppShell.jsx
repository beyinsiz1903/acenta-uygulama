import React, { useEffect, useMemo, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { formatMoney, formatMoneyCompact } from "../lib/format";
import {
  LayoutGrid,
  CalendarDays,
  Ticket,
  Users,
  Layers,
  FileText,
  Building2,
  Settings,
  BarChart3,
  LogOut,
  Menu,
  Hotel,
  Link as LinkIcon,
  AlertTriangle,
} from "lucide-react";

import { Button } from "./ui/button";
import { Sheet, SheetContent } from "./ui/sheet";
import ThemeToggle from "./ThemeToggle";
import { cn } from "../lib/utils";
import { api, clearToken, getUser } from "../lib/api";
import { getMenuForUser } from "../config/menuConfig";
import { FeatureProvider, useFeatures } from "../contexts/FeatureContext";
import { Inbox } from "lucide-react";
import { Badge as UIBadge } from "./ui/badge";
import { fetchPartnerNotificationsSummary } from "../lib/partnerGraph";
import { getActiveTenantKey, getActiveTenantId, setActiveTenantId, subscribeTenantChange } from "../lib/tenantContext";

const legacyNav = [
  { to: "/app", label: "Dashboard", icon: LayoutGrid, roles: ["admin", "sales", "ops", "accounting", "b2b_agent", "super_admin"] },
  { to: "/app/products", label: "Ürünler", icon: Layers, roles: ["admin", "sales", "ops", "super_admin"] },
  { to: "/app/inventory", label: "Müsaitlik", icon: CalendarDays, roles: ["admin", "sales", "ops", "super_admin"] },
  { to: "/app/reservations", label: "Rezervasyonlar", icon: Ticket, roles: ["admin", "sales", "ops", "accounting", "b2b_agent", "super_admin"] },
  { to: "/app/customers", label: "Müşteriler", icon: Users, roles: ["admin", "sales", "ops", "super_admin"] },
  { to: "/app/crm/customers", label: "CRM Müşteriler", icon: Users, roles: ["admin", "sales", "ops", "super_admin"] },
  { to: "/app/crm/duplicates", label: "CRM Duplicate Müşteriler", icon: Users, roles: ["admin", "super_admin"] },
  { to: "/app/crm/pipeline", label: "CRM Pipeline", icon: FileText, roles: ["admin", "sales", "ops", "super_admin"] },
  { to: "/app/crm/tasks", label: "CRM Görevler", icon: CalendarDays, roles: ["admin", "sales", "ops", "super_admin"] },
  { to: "/app/crm/events", label: "CRM Olaylar", icon: FileText, roles: ["admin", "super_admin"] },
  { to: "/app/inbox", label: "Inbox", icon: Inbox, roles: ["admin", "super_admin", "ops"] },
  { to: "/app/b2b", label: "B2B / Acenteler", icon: Building2, roles: ["admin", "super_admin"] },
  { to: "/app/b2b-book", label: "B2B Rezervasyon", icon: Ticket, roles: ["b2b_agent"] },
  { to: "/app/reports", label: "Raporlar", icon: BarChart3, roles: ["admin", "sales", "accounting", "super_admin"] },
  { to: "/app/settings", label: "Ayarlar", icon: Settings, roles: ["admin", "super_admin"] },
];

const iconMap = {
  "Acentalar": Building2,
  "Oteller": Hotel,
  "Link Yönetimi": LinkIcon,
  "Otellerim": Hotel,
  "Mutabakat": FileText,
  "Exposure & Aging": BarChart3,
};

function userHasRole(user, allowed) {
  const roles = user?.roles || [];
  return allowed.some((r) => roles.includes(r));
}

export default function AppShell() {
  const user = getUser();
  const location = useLocation();

  const [resSummary, setResSummary] = useState([]);
  const [sales, setSales] = useState([]);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [partnerSummary, setPartnerSummary] = useState(null);
  const [activeTenantKey, setActiveTenantKey] = useState(() => getActiveTenantKey());

  // On first load, if there is a default tenant id configured and no active tenant set,
  // seed it into storage so that tenant-aware APIs (X-Tenant-Id) work even before a
  // dedicated tenant switcher exists.
  useEffect(() => {
    // Eski davranış: burada default tenant id'yi localStorage'a yazmaya
    // hazırlanıyorduk. Artık interceptor env default'u sadece header'da
    // kullanıyor ve localStorage'a dokunmuyor. Bu effect'i no-op bırakıyoruz.
    try {
      void getActiveTenantKey();
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    (async () => {
      try {
        const [a, b] = await Promise.all([
          api.get("/reports/reservations-summary"),
          api.get("/reports/sales-summary?days=7"),
        ]);
        setResSummary(a.data || []);
        setSales(b.data || []);
      } catch {
        // Sidebar metrikleri opsiyonel; hata UI'ı bozmasın.
      }
    })();
  }, []);

  // Keep activeTenantKey in sync with tenant change events and storage changes
  useEffect(() => {
    const syncFromStorage = () => {
      setActiveTenantKey(getActiveTenantKey());
    };

    // Initial sync
    syncFromStorage();

    // If no tenant id is set yet, and a default tenant id is provided via env,
    // seed it once so that tenant-aware APIs can function until a real switcher exists.
    try {
      const currentId = getActiveTenantId();
      const defId = process.env.REACT_APP_DEFAULT_TENANT_ID;
      if (!currentId && defId) {
        setActiveTenantId(defId);
      }
    } catch {
      // ignore
    }

    let unsubscribeTenant = () => {};
    if (typeof window !== "undefined") {
      // Custom event from tenant switcher
      unsubscribeTenant = subscribeTenantChange((detail) => {
        const nextKey = detail?.tenantKey ?? getActiveTenantKey();
        setActiveTenantKey(nextKey);
      });

      // Cross-tab storage changes
      window.addEventListener("storage", syncFromStorage);
    }

    return () => {
      if (typeof window !== "undefined") {
        window.removeEventListener("storage", syncFromStorage);
      }
      unsubscribeTenant();
    };
  }, []);

  // Partner notifications summary (header badge)
  useEffect(() => {
    let active = true;
    let intervalId;

    const loadSummary = async () => {
      try {
        const data = await fetchPartnerNotificationsSummary();
        if (!active) return;
        setPartnerSummary(data);
      } catch (err) {
        if (!active) return;
        // Partner özeti kritik değil; hata UI'ı bozmasın ancak debug için iz bırak.
        if (typeof console !== "undefined" && console.debug) {
          console.debug("[partner-graph] notifications summary failed", err?.message || err);
        }
      }
    };

    void loadSummary();
    intervalId = window.setInterval(loadSummary, 60_000);

    return () => {
      active = false;
      if (intervalId) {
        window.clearInterval(intervalId);
      }
    };
  }, [activeTenantKey]);

  useEffect(() => {
    if (typeof window !== "undefined" && window.location.search && window.location.search.includes("e2e=1")) {
      import("../version").then(({ BUILD_STAMP }) => {
        window.__BUILD_STAMP__ = BUILD_STAMP;
        console.info("BUILD_STAMP", BUILD_STAMP);
      });
    }
  }, []);

  const sidebarStats = useMemo(() => {
    const map = new Map((resSummary || []).map((r) => [r.status, Number(r.count || 0)]));
    const total = (resSummary || []).reduce((a, r) => a + Number(r.count || 0), 0);
    const revenue7d = (sales || []).reduce((a, r) => a + Number(r.revenue || 0), 0);
    return {
      total,
      pending: map.get("pending") || 0,
      confirmed: map.get("confirmed") || 0,
      revenue7d,
    };
  }, [resSummary, sales]);

  const isHotel = (user?.roles || []).includes("hotel_admin") || (user?.roles || []).includes("hotel_staff");
  const isAgency = (user?.roles || []).includes("agency_admin") || (user?.roles || []).includes("agency_agent");

  // Role-based menu (new structure)
  const roleBasedMenu = getMenuForUser(user);
  
  // Legacy nav (filtered by role)
  const visibleLegacyNav = legacyNav.filter((n) => userHasRole(user, n.roles));

  // Combine both menus
  const allMenuItems = [...roleBasedMenu, ...visibleLegacyNav];

  const partnerSection = {
    label: "Partners",
    children: [
      { label: "Genel Bakış", path: "/app/partners" },
    ],
  };

  return (
    <div className="min-h-screen bg-background">
      <div className="sticky top-0 z-40 border-b bg-background/80 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3">
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="icon"
              className="md:hidden"
              onClick={() => setMobileNavOpen(true)}
              data-testid="mobile-nav-open"
            >
              <Menu className="h-5 w-5" />
            </Button>

            <div className="flex items-center gap-3">
              <div className="sr-only">Acenta Master</div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Partner inbox header badge */}
            <NavLink
              to="/app/partners"
              className={({ isActive }) =>
                cn(
                  "relative inline-flex items-center justify-center rounded-full border px-2 py-1 text-xs transition hover:bg-accent hover:text-foreground",
                  isActive ? "bg-primary text-primary-foreground border-primary" : "border-border text-muted-foreground"
                )
              }
            >
              <Inbox className="h-4 w-4 mr-1" />
              <span className="hidden sm:inline">Partner Gelen Kutusu</span>
              {partnerSummary?.counts?.invites_received > 0 && (
                <UIBadge
                  variant="destructive"
                  className="ml-1 h-4 min-w-[1.25rem] px-1 text-[10px] flex items-center justify-center rounded-full"
                >
                  {partnerSummary.counts.invites_received}
                </UIBadge>
              )}
            </NavLink>

            <ThemeToggle />
            <div className="hidden sm:block text-right">
              <div className="text-sm font-medium text-foreground">{user?.name || user?.email}</div>
              <div className="text-xs text-muted-foreground">{(user?.roles || []).join(", ")}</div>
            </div>
            <Button
              variant="outline"
              size="sm"
              data-testid="logout-btn"
              onClick={() => {
                clearToken();
                window.location.href = "/login";
              }}
              className="gap-2"
            >
              <LogOut className="h-4 w-4" />
              Çıkış
            </Button>
          </div>
        </div>
      </div>

      {/* Mobile nav drawer */}
      <Sheet open={mobileNavOpen} onOpenChange={setMobileNavOpen}>
        <SheetContent side="left" className="p-0" data-testid="mobile-nav-sheet">
          <div className="border-b px-5 py-4">
            <div className="flex items-center gap-3">
              <div className="h-9 w-9 rounded-xl bg-primary text-primary-foreground grid place-items-center font-semibold">
                A
              </div>
              <div>
                <div className="sr-only">Acenta Master</div>
                <div className="text-xs text-muted-foreground">Menü</div>
              </div>
            </div>
          </div>

          <div className="px-4 py-4 pb-32">
            <div className="grid grid-cols-3 gap-2">
              {isAgency ? (
                <div className="rounded-xl border bg-background/50 p-2 opacity-70 cursor-default">
                  <div className="text-[11px] text-muted-foreground">Toplam</div>
                  <div className="text-sm font-semibold text-foreground">{sidebarStats.total}</div>
                </div>
              ) : (
                <NavLink
                  to={isHotel ? "/app/hotel/bookings" : "/app"}
                  onClick={() => setMobileNavOpen(false)}
                  className={({ isActive }) =>
                    cn(
                      "rounded-xl border bg-background/50 p-2 transition hover:bg-accent/40 hover:shadow-sm",
                      isActive ? "ring-1 ring-ring" : ""
                    )
                  }
                >
                  <div className="text-[11px] text-muted-foreground">Toplam</div>
                  <div className="text-sm font-semibold text-foreground">{sidebarStats.total}</div>
                </NavLink>
              )}

              {isAgency ? (
                <div className="rounded-xl border bg-background/50 p-2 opacity-70 cursor-default">
                  <div className="text-[11px] text-muted-foreground">Bekleyen</div>
                  <div className="text-sm font-semibold text-foreground">{sidebarStats.pending}</div>
                </div>
              ) : (
                <NavLink
                  to={isHotel ? "/app/hotel/bookings?status=pending" : "/app"}
                  onClick={() => setMobileNavOpen(false)}
                  className={({ isActive }) =>
                    cn(
                      "rounded-xl border bg-background/50 p-2 transition hover:bg-accent/40 hover:shadow-sm",
                      isActive ? "ring-1 ring-ring" : ""
                    )
                  }
                >
                  <div className="text-[11px] text-muted-foreground">Bekleyen</div>
                  <div className="text-sm font-semibold text-foreground">{sidebarStats.pending}</div>
                </NavLink>
              )}

              {isAgency ? (
                <div className="rounded-xl border bg-background/50 p-2 opacity-70 cursor-default">
                  <div className="text-[11px] text-muted-foreground">Ciro (7G)</div>
                  <div className="text-sm font-semibold text-foreground">{formatMoneyCompact(sidebarStats.revenue7d, "TRY")}</div>
                </div>
              ) : (
                <NavLink
                  to={isHotel ? "/app/hotel/settlements" : "/app"}
                  onClick={() => setMobileNavOpen(false)}
                  className={({ isActive }) =>
                    cn(
                      "rounded-xl border bg-background/50 p-2 transition hover:bg-accent/40 hover:shadow-sm",
                      isActive ? "ring-1 ring-ring" : ""
                    )
                  }
                >
                  <div className="text-[11px] text-muted-foreground">Ciro (7G)</div>
                  <div className="text-sm font-semibold text-foreground">{formatMoneyCompact(sidebarStats.revenue7d, "TRY")}</div>
                </NavLink>
              )}
            </div>

            <div className="mt-4 rounded-2xl border bg-card p-2 shadow-sm">
              {roleBasedMenu.map((section) => (
                <div key={section.label} className="mb-3 last:mb-0">
                  <div className="px-3 py-1 text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                    {section.label}
                  </div>
                  {section.children.map((item) => {
                    const Icon = iconMap[item.label] || Building2;
                    return (
                      <NavLink
                        key={`rb-${item.path}`}
                        to={item.path}
                        end
                        onClick={() => setMobileNavOpen(false)}
                        className={({ isActive }) =>
                          cn(
                            "relative flex items-center gap-3 rounded-xl px-3 py-2 text-sm font-medium transition hover:shadow-sm",
                            "border-l-4",
                            isActive
                              ? "bg-primary text-primary-foreground shadow border-primary"
                              : "border-transparent text-muted-foreground hover:bg-accent hover:text-foreground"
                          )
                        }
                      >
                        <Icon className="h-4 w-4" />
                        {item.label}
                      </NavLink>
                    );
                  })}
                </div>
              ))}

              {/* Ops Tasks Section */}
              <div className="mb-3">
                <div className="px-3 py-1 text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                  Ops Queues
                </div>
                <NavLink
                  to="/app/ops/tasks"
                  end
                  className={({ isActive }) =>
                    cn(
                      "relative flex items-center gap-3 rounded-xl px-3 py-2 text-sm font-medium transition hover:shadow-sm",
                      "border-l-4",
                      isActive
                        ? "bg-primary text-primary-foreground shadow border-primary"
                        : "border-transparent text-muted-foreground hover:bg-accent hover:text-foreground"
                    )
                  }
                >
                  <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-primary/10 text-primary">
                    <CalendarDays className="h-4 w-4" />
                  </div>
                  <div className="flex-1 overflow-hidden">
                    <div className="truncate">Ops Tasks</div>
                  </div>
                </NavLink>
              </div>

              {/* Ops Queues Section */}
              <div className="mb-3">
                <div className="px-3 py-1 text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                  Ops Queues
                </div>
                <NavLink
                  to="/app/ops/tasks"
                  end
                  onClick={() => setMobileNavOpen(false)}
                  className={({ isActive }) =>
                    cn(
                      "relative flex items-center gap-3 rounded-xl px-3 py-2 text-sm font-medium transition hover:shadow-sm",
                      "border-l-4",
                      isActive
                        ? "bg-primary text-primary-foreground shadow border-primary"
                        : "border-transparent text-muted-foreground hover:bg-accent hover:text-foreground"
                    )
                  }
                >
                  <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-primary/10 text-primary">
                    <CalendarDays className="h-4 w-4" />
                  </div>
                  <div className="flex-1 overflow-hidden">
                    <div className="truncate">Ops Tasks</div>
                  </div>
                </NavLink>
                <NavLink
                  to="/app/ops/incidents"
                  end
                  onClick={() => setMobileNavOpen(false)}
                  className={({ isActive }) =>
                    cn(
                      "relative flex items-center gap-3 rounded-xl px-3 py-2 text-sm font-medium transition hover:shadow-sm",
                      "border-l-4",
                      isActive
                        ? "bg-primary text-primary-foreground shadow border-primary"
                        : "border-transparent text-muted-foreground hover:bg-accent hover:text-foreground"
                    )
                  }
                >
                  <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-primary/10 text-primary">
                    <AlertTriangle className="h-4 w-4" />
                  </div>
                  <div className="flex-1 overflow-hidden">
                    <div className="truncate">Ops Incidents</div>
                  </div>
                </NavLink>
              </div>

              {visibleLegacyNav.length > 0 && (roleBasedMenu.length > 0 || true) && (
                <div className="my-2 border-t" />
              )}

              {visibleLegacyNav.map((item) => {
                const Icon = item.icon;
                return (
                  <NavLink
                    key={`m-${item.to}`}
                    to={item.to}
                    end={item.to === "/app"}
                    onClick={() => setMobileNavOpen(false)}
                    className={({ isActive }) =>
                      cn(
                        "relative flex items-center gap-3 rounded-xl px-3 py-2 text-sm font-medium transition hover:shadow-sm",
                        "border-l-4",
                        isActive
                          ? "bg-primary text-primary-foreground shadow border-primary"
                          : "border-transparent text-muted-foreground hover:bg-accent hover:text-foreground"
                      )
                    }
                  >
                    <Icon className="h-4 w-4" />
                    {item.label}
                  </NavLink>
                );
              })}
            </div>
          </div>

          <div className="fixed bottom-3 left-3 right-3 rounded-2xl border bg-background/80 backdrop-blur supports-[backdrop-filter]:bg-background/60 px-4 py-3 shadow-lg">
            <div className="flex items-center justify-between gap-2">
              <div className="text-xs text-muted-foreground truncate">{user?.email || ""}</div>
              <div className="flex items-center gap-2">
                <Button variant="ghost" size="sm" onClick={() => setMobileNavOpen(false)} className="gap-2">
                  Kapat
                </Button>
                <ThemeToggle testId="theme-toggle-mobile" />
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setMobileNavOpen(false);
                    clearToken();
                    window.location.href = "/login";
                  }}
                  className="gap-2"
                  data-testid="mobile-logout"
                >
                  <LogOut className="h-4 w-4" />
                  Çıkış
                </Button>
              </div>
            </div>
          </div>

        </SheetContent>
      </Sheet>


      <div className="mx-auto grid max-w-7xl grid-cols-12 gap-4 px-4 py-6">
        <aside className="col-span-12 md:col-span-3 lg:col-span-2 md:sticky md:top-[84px] md:h-[calc(100vh-104px)]">
          <div className="rounded-2xl border bg-card/60 p-3 shadow-sm select-none">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="h-9 w-9 rounded-xl bg-primary text-primary-foreground grid place-items-center font-semibold">
                  A
                </div>
                <div>
                  <div className="text-sm font-semibold text-foreground">Acenta Master</div>
                  <div className="text-xs text-muted-foreground">Kurumsal Panel</div>
                </div>
              </div>
              <div className="hidden md:block h-2 w-2 rounded-full bg-emerald-500" title="Online" />
            </div>

            <div className="mt-3 grid grid-cols-3 gap-2">
              <div className="rounded-xl border bg-background/50 p-2 opacity-70 cursor-default">
                <div className="text-[11px] text-muted-foreground">Toplam adet</div>
                <div
                  className="mt-1 text-sm font-semibold text-foreground truncate"
                  title={sidebarStats.total?.toLocaleString("tr-TR")}
                  data-testid="sb-total"
                >
                  {sidebarStats.total >= 1000
                    ? `${(sidebarStats.total / (sidebarStats.total >= 1_000_000 ? 1_000_000 : 1_000)).toFixed(1)}${
                        sidebarStats.total >= 1_000_000 ? "M" : "K"
                      }`
                    : sidebarStats.total}
                </div>
              </div>

              <div className="rounded-xl border bg-background/50 p-2 opacity-70 cursor-default">
                <div className="text-[11px] text-muted-foreground">Bekleyen adet</div>
                <div
                  className="mt-1 text-sm font-semibold text-foreground truncate"
                  title={sidebarStats.pending?.toLocaleString("tr-TR")}
                  data-testid="sb-pending"
                >
                  {sidebarStats.pending >= 1000
                    ? `${(sidebarStats.pending / (sidebarStats.pending >= 1_000_000 ? 1_000_000 : 1_000)).toFixed(1)}${
                        sidebarStats.pending >= 1_000_000 ? "M" : "K"
                      }`
                    : sidebarStats.pending}
                </div>
              </div>

              <div className="rounded-xl border bg-background/50 p-2 opacity-70 cursor-default">
                <div className="text-[11px] text-muted-foreground">Ciro (7G, ₺)</div>
                <div
                  className="mt-1 text-sm font-semibold text-foreground truncate"
                  title={formatMoney(sidebarStats.revenue7d, "TRY")}
                  data-testid="sb-rev7"
                >
                  {formatMoneyCompact(sidebarStats.revenue7d, "TRY")}
                </div>
              </div>
            </div>

            <div className="mt-2 flex items-center justify-between text-[11px] text-muted-foreground">
              <span>Rol: {(user?.roles || ["-"])[0]}</span>
              <span>{new Date().toLocaleDateString("tr-TR")}</span>
            </div>

            <div className="mt-3">
              <nav className="rounded-2xl border bg-card p-2 shadow-sm max-h-[calc(100vh-330px)] overflow-y-auto">
                {[partnerSection, ...roleBasedMenu].map((section) => (
                  <div key={section.label} className="mb-3 last:mb-0">
                    <div className="px-3 py-1 text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                      {section.label}
                    </div>
                    {section.children.map((item) => {
                      const Icon = iconMap[item.label] || Building2;
                      return (
                        <NavLink
                          key={`d-${item.path}`}
                          to={item.path}
                          end
                          className={({ isActive }) =>
                            cn(
                              "flex items-center gap-3 rounded-xl px-3 py-2 text-sm font-medium transition hover:shadow-sm",
                              isActive
                                ? "bg-primary text-primary-foreground shadow"
                                : "text-muted-foreground hover:bg-accent hover:text-foreground"
                            )
                          }
                        >
                          <Icon className="h-4 w-4" />
                          {item.label}
                        </NavLink>
                      );
                    })}
                  </div>
                ))}

                {/* Ops Queues Section */}
                <div className="mb-3">
                  <div className="px-3 py-1 text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                    Ops Queues
                  </div>
                  <NavLink
                    to="/app/ops/tasks"
                    end
                    className={({ isActive }) =>
                      cn(
                        "flex items-center gap-3 rounded-xl px-3 py-2 text-sm font-medium transition hover:shadow-sm",
                        isActive
                          ? "bg-primary text-primary-foreground shadow"
                          : "text-muted-foreground hover:bg-accent hover:text-foreground"
                      )
                    }
                  >
                    <CalendarDays className="h-4 w-4" />
                    Ops Tasks
                  </NavLink>
                  <NavLink
                    to="/app/ops/incidents"
                    end
                    className={({ isActive }) =>
                      cn(
                        "flex items-center gap-3 rounded-xl px-3 py-2 text-sm font-medium transition hover:shadow-sm",
                        isActive
                          ? "bg-primary text-primary-foreground shadow"
                          : "text-muted-foreground hover:bg-accent hover:text-foreground"
                      )
                    }
                  >
                    <AlertTriangle className="h-4 w-4" />
                    Ops Incidents
                  </NavLink>
                </div>

                {visibleLegacyNav.length > 0 && (roleBasedMenu.length > 0 || true) && (
                  <div className="my-2 border-t" />
                )}

                {visibleLegacyNav.map((item) => {
                  const Icon = item.icon;
                  return (
                    <NavLink
                      key={item.to}
                      to={item.to}
                      end={item.to === "/app"}
                      className={({ isActive }) =>
                        cn(
                          "flex items-center gap-3 rounded-xl px-3 py-2 text-sm font-medium transition hover:shadow-sm",
                          isActive
                            ? "bg-primary text-primary-foreground shadow"
                            : "text-muted-foreground hover:bg-accent hover:text-foreground"
                        )
                      }
                      data-testid={`nav-${item.label}`}
                    >
                      <Icon className="h-4 w-4" />
                      {item.label}
                    </NavLink>
                  );
                })}
              </nav>
            </div>
          </div>

          <div className="mt-4 rounded-2xl border bg-card p-4 shadow-sm">
            <div className="text-xs font-semibold text-foreground">Hızlı İpuçları</div>
            <div className="mt-2 text-xs text-muted-foreground">
              Müsaitlik ekranında kapasite ve fiyatı güncelleyip rezervasyon akışını
              hızlıca test edebilirsin.
            </div>
          </div>
        </aside>

        <main className="col-span-12 md:col-span-9 lg:col-span-10 md:min-h-[calc(100vh-104px)]">
          <Outlet />
        </main>
      </div>

      <footer className="border-t bg-background">
        <div className="mx-auto max-w-7xl px-4 py-4 text-xs text-muted-foreground">
          © {new Date().getFullYear()} — v1
        </div>
      </footer>
    </div>
  );
}
