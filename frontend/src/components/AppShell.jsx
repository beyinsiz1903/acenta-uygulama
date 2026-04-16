import React, { useEffect, useMemo, useState, useCallback, lazy, Suspense } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { AlertTriangle, Bell, Inbox, LogOut, Menu, Search } from "lucide-react";

import { Button } from "./ui/button";
import { Sheet, SheetContent } from "./ui/sheet";
import { PageErrorBoundary } from "./PageErrorBoundary";
import ThemeToggle from "./ThemeToggle";
import { cn } from "../lib/utils";
import { api, getUser } from "../lib/api";
import { useLogout } from "../hooks/useAuth";
import { FeatureProvider, useFeatures } from "../contexts/FeatureContext";
import { ProductModeProvider, useProductMode } from "../contexts/ProductModeContext";
import { Badge as UIBadge } from "./ui/badge";
import { fetchPartnerNotificationsSummary } from "../lib/partnerGraph";
import { getActiveTenantKey, getActiveTenantId, setActiveTenantId, subscribeTenantChange } from "../lib/tenantContext";
import NotificationBell from "./NotificationBell";
import TrialBanner from "./TrialBanner";
import TrialExpiredGate from "./TrialExpiredGate";
import AgencyContractBanner from "./AgencyContractBanner";
import AgencyContractExpiredGate from "./AgencyContractExpiredGate";
import { LanguageSwitcher, useI18n } from "../contexts/I18nContext";
import { NewSidebar } from "./NewSidebar";

// ─── P2: Lazy-loaded non-critical components ───
const NotificationDrawer = lazy(() => import("./NotificationDrawer"));
const AiAssistant = lazy(() => import("./AiAssistant"));

// ─── P3: Enterprise UX ───
import { CommandPalette } from "./CommandPalette";
import { useKeyboardShortcuts } from "../hooks/useKeyboardShortcuts";
import { normalizeAgencyModuleKeys } from "../lib/agencyModules";
import { hasAnyRole } from "../lib/roles";
import {
  resolvePersona,
  getPersonaNavSections,
  getPersonaAccountLinks,
} from "../navigation";

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

/* ================================================================== */
/*  MAIN APP SHELL                                                     */
/* ================================================================== */
export default function AppShell() {
  return (
    <FeatureProvider>
      <ProductModeProvider>
        <AppShellInner />
      </ProductModeProvider>
    </FeatureProvider>
  );
}

function AppShellInner() {
  const { t, lang } = useI18n();
  const user = getUser();
  const location = useLocation();
  const navigate = useNavigate();
  const showPartnerEntry = location.pathname.startsWith("/app/partners");
  const logoutMutation = useLogout();

  const [resSummary, setResSummary] = useState([]);
  const [sales, setSales] = useState([]);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [partnerSummary, setPartnerSummary] = useState(null);
  const [activeTenantKey, setActiveTenantKeyState] = useState(() => getActiveTenantKey());
  const [collapsed, setCollapsed] = useState(() => loadCollapsed());
  const [notifOpen, setNotifOpen] = useState(false);
  const [commandOpen, setCommandOpen] = useState(false);
  const [onboardingChecked, setOnboardingChecked] = useState(false);
  const [agencyAllowedModules, setAgencyAllowedModules] = useState(null); // null = not loaded, [] = no restrictions
  const [orgEnabledModules, setOrgEnabledModules] = useState(null); // null = not loaded (all enabled)
  const [agencyContract, setAgencyContract] = useState(null);
  const [userAllowedScreens, setUserAllowedScreens] = useState(null); // null = not loaded, [] = full access
  const [trialStatus, setTrialStatus] = useState(null);
  const canLoadAdminBranding = hasAnyRole(user, ["super_admin", "admin"]);

  // ─── P3: Keyboard shortcuts ───
  useKeyboardShortcuts({
    onOpenPalette: useCallback(() => setCommandOpen(true), []),
  });

  // Enterprise White-Label branding
  const [branding, setBranding] = useState(null);
  const loadBranding = useCallback(async () => {
    if (!canLoadAdminBranding) {
      setBranding(null);
      return;
    }

    try {
      const res = await api.get("/admin/whitelabel-settings");
      if (res.data) {
        setBranding(res.data);
        // Apply brand color as CSS variable
        if (res.data.primary_color) {
          const hex = res.data.primary_color;
          if (hex && hex.startsWith("#")) {
            const h = hex.replace("#", "");
            let r = parseInt(h.substring(0, 2), 16) / 255;
            let g = parseInt(h.substring(2, 4), 16) / 255;
            let b = parseInt(h.substring(4, 6), 16) / 255;
            const max = Math.max(r, g, b), min = Math.min(r, g, b);
            let hue = 0, sat = 0, lit = (max + min) / 2;
            if (max !== min) {
              const d = max - min;
              sat = lit > 0.5 ? d / (2 - max - min) : d / (max + min);
              if (max === r) hue = ((g - b) / d + (g < b ? 6 : 0)) / 6;
              else if (max === g) hue = ((b - r) / d + 2) / 6;
              else hue = ((r - g) / d + 4) / 6;
            }
            const hsl = `${Math.round(hue * 360)} ${Math.round(sat * 100)}% ${Math.round(lit * 100)}%`;
            document.documentElement.style.setProperty("--primary", hsl);
            document.documentElement.style.setProperty("--ring", hsl);
            document.documentElement.style.setProperty("--brand-color", hex);
            const lum = 0.2126 * r + 0.7152 * g + 0.0722 * b;
            const fg = lum > 0.5 ? "224 26% 16%" : "210 40% 98%";
            document.documentElement.style.setProperty("--primary-foreground", fg);
          }
        }
      }
    } catch {
      setBranding(null);
    }
  }, [canLoadAdminBranding]);

  useEffect(() => { loadBranding(); }, [loadBranding]);

  // Listen for branding updates from AdminBrandingPage
  useEffect(() => {
    const handler = (e) => {
      if (e.detail) setBranding(e.detail);
      else loadBranding();
    };
    window.addEventListener("branding-updated", handler);
    return () => window.removeEventListener("branding-updated", handler);
  }, [loadBranding]);

  const brandName = branding?.company_name || branding?.brand_name || "Syroce";
  const brandLogo = useMemo(() => {
    const candidate = branding?.logo_url?.trim();
    if (!candidate || /^https?:\/\/example\.com\//i.test(candidate)) {
      return "";
    }
    return candidate;
  }, [branding?.logo_url]);
  const [brandLogoFailed, setBrandLogoFailed] = useState(false);
  const brandInitial = brandName.charAt(0).toUpperCase();

  useEffect(() => {
    setBrandLogoFailed(false);
  }, [brandLogo]);

  // ── Org-level module restrictions ──────────────────────────
  useEffect(() => {
    if (!hasAnyRole(user, ["super_admin", "admin"])) {
      setOrgEnabledModules(null);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const res = await api.get("/admin/org-modules");
        if (!cancelled) {
          if (res.data?.all_enabled) {
            setOrgEnabledModules(null);
          } else {
            setOrgEnabledModules(new Set(res.data?.enabled_modules || []));
          }
        }
      } catch (err) {
        if (!cancelled) {
          if (err?.response?.status === 401 || err?.response?.status === 403) {
            setOrgEnabledModules(null);
          }
        }
      }
    })();
    const handler = () => {
      (async () => {
        try {
          const res = await api.get("/admin/org-modules");
          if (res.data?.all_enabled) {
            setOrgEnabledModules(null);
          } else {
            setOrgEnabledModules(new Set(res.data?.enabled_modules || []));
          }
        } catch { /* */ }
      })();
    };
    window.addEventListener("org-modules-updated", handler);
    return () => { cancelled = true; window.removeEventListener("org-modules-updated", handler); };
  }, [user]);

  // ── Agency module restrictions (dynamic nav) ──────────────
  const isAgencyUser = hasAnyRole(user, ["agency_admin", "agency_agent"])
    && !hasAnyRole(user, ["super_admin", "admin"]);

  useEffect(() => {
    if (!isAgencyUser) {
      setAgencyAllowedModules(null);
      setAgencyContract(null);
      return undefined;
    }
    let cancelled = false;
    (async () => {
      try {
        const res = await api.get("/agency/profile");
        if (!cancelled) {
          const modules = res.data?.allowed_modules || [];
          setAgencyAllowedModules(modules);
          setAgencyContract(res.data?.contract || null);
        }
      } catch {
        if (!cancelled) {
          setAgencyAllowedModules([]);
          setAgencyContract(null);
        }
      }
    })();
    return () => { cancelled = true; };
  }, [isAgencyUser]);

  // ── Load user-level screen permissions ──────────────────────
  useEffect(() => {
    // Only agency_agent users can have screen restrictions
    const isAgentOnly = hasAnyRole(user, ["agency_agent"])
      && !hasAnyRole(user, ["agency_admin", "super_admin", "admin"]);
    if (!isAgentOnly) {
      setUserAllowedScreens(null);
      return;
    }
    // Read from cached user object (set during login/me)
    const screens = user?.allowed_screens;
    if (Array.isArray(screens) && screens.length > 0) {
      setUserAllowedScreens(screens);
    } else {
      setUserAllowedScreens(null); // null = full access
    }
  }, [user]);

  // ── P0: Onboarding auto-redirect ──────────────────────────
  useEffect(() => {
    if (onboardingChecked) return;
    if (location.pathname === "/app/onboarding" || location.pathname.startsWith("/app/settings")) {
      setOnboardingChecked(true);
      return;
    }
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

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await api.get("/onboarding/trial");
        if (!cancelled) setTrialStatus(res.data || null);
      } catch {
        if (!cancelled) setTrialStatus(null);
      }
    })();
    return () => { cancelled = true; };
  }, [user?.organization_id]);

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
    if (!showPartnerEntry) {
      setPartnerSummary(null);
      return undefined;
    }
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
  }, [activeTenantKey, showPartnerEntry]);

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

  const isAdmin = hasAnyRole(user, ["super_admin", "admin"]);
  const persona = useMemo(() => resolvePersona(user), [user]);
  const trialExpired = Boolean(trialStatus?.expired || trialStatus?.status === "expired");
  const agencyContractExpired = Boolean(isAgencyUser && agencyContract?.access_blocked);
  const showAgencyContractWarning = Boolean(
    isAgencyUser &&
    !agencyContractExpired &&
    agencyContract?.contract_status === "expiring_soon"
  );
  const { hasFeature, loading: featuresLoading, quotaAlerts } = useFeatures();
  const { mode: productMode, hiddenNavItems, loading: modeLoading } = useProductMode();
  const normalizedAgencyAllowedModules = useMemo(
    () => new Set(normalizeAgencyModuleKeys(agencyAllowedModules || [])),
    [agencyAllowedModules]
  );

  /* Mode-aware nav filter helper */
  const MODE_ORDER_MAP = { lite: 0, pro: 1, enterprise: 2 };
  const currentModeLevel = MODE_ORDER_MAP[productMode] ?? 2;

  const isAgencyModuleVisible = useCallback((item) => {
    if (!isAgencyUser) return true;
    if (normalizedAgencyAllowedModules.size === 0) return true;
    if (!item?.modeKey || item.modeKey === "dashboard") return true;

    const candidateKeys = normalizeAgencyModuleKeys([item.modeKey, ...(item.moduleAliases || [])]);
    return candidateKeys.some((moduleKey) => normalizedAgencyAllowedModules.has(moduleKey));
  }, [isAgencyUser, normalizedAgencyAllowedModules]);

  const isOrgModuleEnabled = useCallback((item) => {
    if (!orgEnabledModules) return true;
    if (!item.moduleKey) return true;
    return orgEnabledModules.has(item.moduleKey);
  }, [orgEnabledModules]);

  const filterNavByMode = useCallback((items) => {
    return items.filter((it) => {
      if (it.visibleInSidebar === false) return false;
      if (it.visibleScopes && !it.visibleScopes.includes(persona)) return false;
      if (!it.to) return false;
      if (!it.isCore && it.feature && !(!featuresLoading && hasFeature(it.feature))) return false;
      if (it.minMode) {
        const itemLevel = MODE_ORDER_MAP[it.minMode] ?? 0;
        if (itemLevel > currentModeLevel) return false;
      }
      if (!it.isCore && it.modeKey && hiddenNavItems.includes(it.modeKey)) return false;
      if (!isAgencyModuleVisible(it)) return false;
      if (!isOrgModuleEnabled(it)) return false;
      if (userAllowedScreens && userAllowedScreens.length > 0 && it.modeKey) {
        if (!userAllowedScreens.includes(it.modeKey)) return false;
      }
      return true;
    });
  }, [featuresLoading, hasFeature, currentModeLevel, hiddenNavItems, isAgencyModuleVisible, isOrgModuleEnabled, persona, userAllowedScreens]);

  const navSections = useMemo(() => getPersonaNavSections(persona), [persona]);
  const visibleNavSections = useMemo(
    () => navSections.filter((section) => section.showInSidebar !== false),
    [navSections],
  );
  const accountLinks = useMemo(() => getPersonaAccountLinks(persona), [persona]);

  /* ── Mode Route Guard: redirect if current path is hidden by mode ── */
  useEffect(() => {
    if (modeLoading) return;
    const currentPath = location.pathname;
    // Collect ALL hidden paths (from hidden groups AND hidden individual items)
    const hiddenPaths = [];
    navSections.forEach((section) => {
      // If entire group is hidden by minGroupMode, all its items are hidden
      if (section.minGroupMode) {
        const groupLevel = MODE_ORDER_MAP[section.minGroupMode] ?? 0;
        if (groupLevel > currentModeLevel) {
          section.items.forEach((it) => {
            if (it.to) hiddenPaths.push(it.to);
          });
          return;
        }
      }
      // Check individual items
      section.items.forEach((it) => {
        if (it.minMode) {
          const itemLevel = MODE_ORDER_MAP[it.minMode] ?? 0;
          if (itemLevel > currentModeLevel) {
            if (it.to) hiddenPaths.push(it.to);
            return;
          }
        }
        if (!it.isCore && it.modeKey && hiddenNavItems.includes(it.modeKey)) {
          if (it.to) hiddenPaths.push(it.to);
          return;
        }
        if (!isAgencyModuleVisible(it) && it.to) {
          hiddenPaths.push(it.to);
        }
        if (!isOrgModuleEnabled(it) && it.to) {
          hiddenPaths.push(it.to);
        }
        // User-level screen permissions enforcement
        if (userAllowedScreens && userAllowedScreens.length > 0 && it.modeKey && !userAllowedScreens.includes(it.modeKey) && it.to) {
          hiddenPaths.push(it.to);
        }
      });
    });
    // If current path starts with a hidden path, redirect
    const isBlocked = hiddenPaths.some((hp) => currentPath === hp || currentPath.startsWith(hp + "/"));
    if (isBlocked) {
      navigate("/app", { replace: true });
    }
  }, [location.pathname, modeLoading, currentModeLevel, hiddenNavItems, isAgencyModuleVisible, isOrgModuleEnabled, navigate, navSections, userAllowedScreens]);

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
              {brandLogo && !brandLogoFailed ? (
                <img
                  src={brandLogo}
                  alt={brandName}
                  className="h-7 w-7 rounded-lg object-contain"
                  data-testid="brand-logo"
                  onError={() => setBrandLogoFailed(true)}
                />
              ) : (
                <div className="h-7 w-7 rounded-lg bg-primary text-primary-foreground grid place-items-center font-semibold text-xs" style={branding?.primary_color ? { backgroundColor: branding.primary_color } : {}}>
                  {brandInitial}
                </div>
              )}
              <span className="text-sm font-semibold text-foreground" data-testid="brand-name">{brandName}</span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* P3: Command Palette trigger */}
            <button
              onClick={() => setCommandOpen(true)}
              className="hidden sm:inline-flex items-center gap-2 rounded-lg border border-border bg-muted/40 px-3 py-1.5 text-xs text-muted-foreground transition hover:bg-accent hover:text-foreground"
              data-testid="command-palette-trigger"
            >
              <Search className="h-3.5 w-3.5" />
              <span>Ara...</span>
              <kbd className="pointer-events-none ml-2 inline-flex h-5 select-none items-center gap-0.5 rounded border bg-background px-1.5 font-mono text-[10px] font-medium text-muted-foreground/70">
                ⌘K
              </kbd>
            </button>

            <LanguageSwitcher />
            {showPartnerEntry ? (
              <NavLink
                to="/app/partners"
                className={({ isActive }) =>
                  cn(
                    "relative inline-flex items-center justify-center rounded-lg border px-2 py-1 text-xs transition hover:bg-accent hover:text-foreground",
                    isActive ? "bg-primary text-primary-foreground border-primary" : "border-border text-muted-foreground"
                  )
                }
                data-testid="topbar-partners-link"
              >
                <Inbox className="h-3.5 w-3.5 mr-1" />
                <span className="hidden sm:inline text-xs">{t("topbar.partners")}</span>
                {partnerSummary?.counts?.invites_received > 0 && (
                  <UIBadge
                    variant="destructive"
                    className="ml-1 h-4 min-w-[1.25rem] px-1 text-2xs flex items-center justify-center rounded-full"
                  >
                    {partnerSummary.counts.invites_received}
                  </UIBadge>
                )}
              </NavLink>
            ) : null}

            {/* Notification bell - in-app notifications */}
            <NotificationBell />

            {/* Activity log bell */}
            <button
              onClick={() => setNotifOpen(true)}
              className="relative inline-flex items-center justify-center h-8 w-8 rounded-lg border border-border text-muted-foreground hover:bg-accent hover:text-foreground transition"
              data-testid="notif-bell"
              title={t("topbar.activity_log")}
            >
              <Bell className="h-4 w-4" />
            </button>

            <ThemeToggle />

            <div className="hidden sm:block text-right">
              <div className="text-xs font-medium text-foreground">{user?.name || user?.email}</div>
              <div className="text-2xs text-muted-foreground">{(user?.roles || []).join(", ")}</div>
            </div>

            <Button
              variant="outline"
              size="sm"
              data-testid="logout-btn"
              onClick={() => { logoutMutation.mutate(undefined, { onSettled: () => window.location.href = "/login" }); }}
              className="gap-1.5 h-8 text-xs"
            >
              <LogOut className="h-3.5 w-3.5" />
              {t("topbar.logout")}
            </Button>
          </div>
        </div>
      </div>

      {/* ========== NOTIFICATION DRAWER (lazy) ========== */}
      {notifOpen && (
        <Suspense fallback={null}>
          <NotificationDrawer open={notifOpen} onClose={() => setNotifOpen(false)} />
        </Suspense>
      )}

      {/* ========== MOBILE NAV DRAWER ========== */}
      <Sheet open={mobileNavOpen} onOpenChange={setMobileNavOpen}>
        <SheetContent side="left" className="p-0 w-[280px]" data-testid="mobile-nav-sheet">
          <div className="border-b px-4 py-3">
            <div className="flex items-center gap-2">
              {brandLogo && !brandLogoFailed ? (
                <img
                  src={brandLogo}
                  alt={brandName}
                  className="h-8 w-8 rounded-lg object-contain"
                  onError={() => setBrandLogoFailed(true)}
                />
              ) : (
                <div className="h-8 w-8 rounded-lg bg-primary text-primary-foreground grid place-items-center font-semibold text-xs" style={branding?.primary_color ? { backgroundColor: branding.primary_color } : {}}>
                  {brandInitial}
                </div>
              )}
              <div>
                <div className="text-sm font-semibold text-foreground">{brandName}</div>
                <div className="text-2xs text-muted-foreground">{user?.email}</div>
              </div>
            </div>
          </div>
          <NewSidebar
            variant="mobile"
            sections={visibleNavSections}
            accountLinks={accountLinks}
            filterItems={filterNavByMode}
            showStats={!isAdmin}
            onItemClick={() => setMobileNavOpen(false)}
            onLogout={() => {
              setMobileNavOpen(false);
              logoutMutation.mutate(undefined, { onSettled: () => { window.location.href = "/login"; } });
            }}
            user={user}
            lang={lang}
          />
        </SheetContent>
      </Sheet>

      {/* ========== MAIN LAYOUT ========== */}
      <div className="flex">
        <NewSidebar
          sections={visibleNavSections}
          accountLinks={accountLinks}
          filterItems={filterNavByMode}
          collapsed={collapsed}
          onToggleCollapse={toggleCollapse}
          sidebarStats={sidebarStats}
          showStats={!isAdmin}
          user={user}
          lang={lang}
        />

        {/* --- Main Content --- */}
        <main className="flex-1 min-h-[calc(100vh-53px)] overflow-auto">
          {!trialExpired ? <TrialBanner /> : null}
          {!trialExpired && showAgencyContractWarning ? (
            <div className="mx-4 mt-3">
              <AgencyContractBanner contract={agencyContract} />
            </div>
          ) : null}
          {!trialExpired && !agencyContractExpired && !isAdmin && quotaAlerts && quotaAlerts.length > 0 && (
            <div className="mx-4 mt-3 space-y-2" data-testid="quota-alert-banners">
              {quotaAlerts.map((q) => (
                <div
                  key={q.metric}
                  className={`rounded-lg border px-4 py-2 text-xs flex items-center justify-between ${
                    q.warning_level === "limit_reached"
                      ? "border-destructive/40 bg-destructive/5 text-destructive"
                      : q.warning_level === "critical"
                        ? "border-orange-500/40 bg-orange-500/5 text-orange-700"
                        : "border-amber-500/40 bg-amber-500/5 text-amber-700"
                  }`}
                  data-testid={`quota-alert-${String(q.metric || "metric").replace(/\./g, "-")}`}
                >
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
                    <span>{q.warning_message || `${q.used}/${q.quota}`}</span>
                  </div>
                  {q.upgrade_recommended && (
                    <Button asChild size="sm" variant="outline" className="ml-3 h-7 text-2xs" data-testid={`quota-alert-${String(q.metric || "metric").replace(/\./g, "-")}-cta`}>
                      <Link to={q.cta_href || "/pricing"}>{q.cta_label || "Planları Gör"}</Link>
                    </Button>
                  )}
                </div>
              ))}
            </div>
          )}
          <div className="p-4 md:p-6 max-w-[1400px]">
            <PageErrorBoundary>
              <Outlet />
            </PageErrorBoundary>
          </div>
        </main>
      </div>

      <footer className="border-t bg-background">
        <div className="px-4 py-3 text-2xs text-muted-foreground">
          © {new Date().getFullYear()} — v1
        </div>
      </footer>

      {trialExpired ? <TrialExpiredGate /> : null}
      {!trialExpired && agencyContractExpired ? <AgencyContractExpiredGate contract={agencyContract} /> : null}

      {/* P3: Command Palette (Cmd+K) */}
      <CommandPalette open={commandOpen} onOpenChange={setCommandOpen} persona={persona} />

      {/* AI Assistant floating panel (lazy) */}
      <Suspense fallback={null}>
        <AiAssistant />
      </Suspense>
    </div>
  );
}
