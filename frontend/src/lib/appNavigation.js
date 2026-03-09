import {
  BarChart3,
  Building2,
  CreditCard,
  DollarSign,
  Eye,
  LayoutGrid,
  Megaphone,
  Settings,
  ShieldCheck,
  Ticket,
  Users,
  Zap,
} from "lucide-react";

export const APP_NAV_SECTIONS = [
  {
    group: "ANA MENÜ",
    showInSidebar: true,
    items: [
      {
        key: "dashboard",
        label: "Dashboard",
        icon: LayoutGrid,
        pathByScope: {
          admin: "/app",
          agency: "/app",
          hotel: "/app/hotel/bookings",
          default: "/app",
        },
        isCore: true,
        end: true,
        modeKey: "dashboard",
        minMode: "lite",
      },
      {
        key: "reservations",
        label: "Rezervasyonlar",
        icon: Ticket,
        pathByScope: {
          admin: "/app/reservations",
          agency: "/app/agency/bookings",
          hotel: "/app/hotel/bookings",
        },
        isCore: true,
        modeKey: "rezervasyonlar",
        minMode: "lite",
      },
      {
        key: "customers",
        label: "Müşteriler",
        icon: Users,
        pathByScope: {
          admin: "/app/crm/customers",
          agency: "/app/crm/customers",
        },
        isCore: true,
        feature: "crm",
        modeKey: "musteriler",
        minMode: "lite",
      },
      {
        key: "finance",
        label: "Finans",
        icon: DollarSign,
        pathByScope: {
          admin: "/app/admin/finance/settlements",
          agency: "/app/agency/settlements",
          hotel: "/app/hotel/settlements",
        },
        isCore: true,
        modeKey: "mutabakat",
        minMode: "lite",
      },
      {
        key: "reports",
        label: "Raporlar",
        icon: BarChart3,
        pathByScope: {
          admin: "/app/reports",
          agency: "/app/reports",
        },
        isCore: true,
        feature: "reports",
        modeKey: "raporlar",
        minMode: "lite",
      },
    ],
  },
  {
    group: "EXPANSION",
    showInSidebar: false,
    items: [
      {
        key: "integrations",
        label: "Entegrasyonlar",
        icon: Zap,
        pathByScope: {
          admin: "/app/admin/integrations",
          agency: "/app/agency/sheets",
          hotel: "/app/hotel/integrations",
        },
        minMode: "pro",
      },
      {
        key: "campaigns",
        label: "Kampanyalar",
        icon: Megaphone,
        pathByScope: { admin: "/app/admin/campaigns" },
        visibleScopes: ["admin"],
        minMode: "pro",
      },
    ],
  },
  {
    group: "ENTERPRISE",
    showInSidebar: false,
    items: [
      {
        key: "tenant-management",
        label: "Tenant yönetimi",
        icon: Building2,
        pathByScope: { admin: "/app/admin/agencies" },
        visibleScopes: ["admin"],
        minMode: "enterprise",
      },
      {
        key: "audit",
        label: "Audit",
        icon: Eye,
        pathByScope: { admin: "/app/admin/audit-logs" },
        visibleScopes: ["admin"],
        minMode: "enterprise",
      },
      {
        key: "advanced-permissions",
        label: "Advanced permissions",
        icon: ShieldCheck,
        pathByScope: { admin: "/app/admin/tenant-features" },
        visibleScopes: ["admin"],
        minMode: "enterprise",
      },
    ],
  },
];

export const ACCOUNT_NAV_ITEMS = [
  {
    key: "billing",
    label: "Faturalama",
    icon: CreditCard,
    pathByScope: { default: "/app/settings/billing" },
    visibleScopes: ["admin", "agency"],
  },
  {
    key: "settings",
    label: "Ayarlar",
    icon: Settings,
    pathByScope: { default: "/app/settings" },
    visibleScopes: ["admin", "agency"],
  },
];

export function userHasRole(user, allowed) {
  const roles = user?.roles || [];
  return allowed.some((role) => roles.includes(role));
}

export function getUserScope(user) {
  if (userHasRole(user, ["super_admin", "admin", "sales", "ops", "accounting", "b2b_agent"])) {
    return "admin";
  }
  if (userHasRole(user, ["agency_admin", "agency_agent"])) {
    return "agency";
  }
  if (userHasRole(user, ["hotel_admin", "hotel_staff"])) {
    return "hotel";
  }
  return "admin";
}

export function resolveScopedPath(pathByScope, scope) {
  if (!pathByScope) {
    return null;
  }
  return pathByScope[scope] || pathByScope.default || null;
}

export function buildScopedNavSections(sections, scope) {
  return sections.map((section) => ({
    ...section,
    items: section.items.map((item) => ({
      ...item,
      to: resolveScopedPath(item.pathByScope, scope),
    })),
  }));
}

export function buildScopedNavItems(items, scope) {
  return items
    .map((item) => ({
      ...item,
      to: resolveScopedPath(item.pathByScope, scope),
    }))
    .filter((item) => {
      if (!item.to) {
        return false;
      }
      if (item.visibleScopes && !item.visibleScopes.includes(scope)) {
        return false;
      }
      return true;
    });
}