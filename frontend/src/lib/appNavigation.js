import {
  BarChart3,
  BedDouble,
  Building2,
  CreditCard,
  DollarSign,
  DoorOpen,
  Eye,
  FileText,
  LayoutGrid,
  Megaphone,
  Settings,
  ShieldCheck,
  Ticket,
  Users,
  Wallet,
  Zap,
} from "lucide-react";
import { normalizeRoles } from "./roles";

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
    group: "PMS",
    showInSidebar: true,
    items: [
      {
        key: "pms-dashboard",
        label: "PMS Paneli",
        icon: BedDouble,
        pathByScope: {
          agency: "/app/agency/pms",
        },
        isCore: true,
        modeKey: "pms_paneli",
        minMode: "lite",
      },
      {
        key: "pms-rooms",
        label: "Oda Yonetimi",
        icon: DoorOpen,
        pathByScope: {
          agency: "/app/agency/pms/rooms",
        },
        isCore: true,
        modeKey: "oda_yonetimi",
        minMode: "lite",
      },
      {
        key: "pms-accounting",
        label: "Muhasebe",
        icon: Wallet,
        pathByScope: {
          agency: "/app/agency/pms/accounting",
        },
        isCore: true,
        modeKey: "muhasebe",
        minMode: "lite",
      },
      {
        key: "pms-invoices",
        label: "Faturalar",
        icon: FileText,
        pathByScope: {
          agency: "/app/agency/pms/invoices",
        },
        isCore: true,
        modeKey: "faturalar",
        minMode: "lite",
      },
    ],
  },
  {
    group: "SATIŞ & ENVANTER",
    showInSidebar: true,
    items: [
      {
        key: "agency-hotels",
        label: "Oteller",
        icon: Building2,
        pathByScope: {
          agency: "/app/agency/hotels",
        },
        feature: "inventory",
        modeKey: "oteller",
        moduleAliases: ["otellerim", "urunler"],
        minMode: "lite",
      },
      {
        key: "agency-availability",
        label: "Müsaitlik",
        icon: LayoutGrid,
        pathByScope: {
          agency: "/app/agency/availability",
        },
        feature: "inventory",
        modeKey: "musaitlik",
        moduleAliases: ["musaitlik_takibi"],
        minMode: "lite",
      },
      {
        key: "agency-tours",
        label: "Turlar",
        icon: Ticket,
        pathByScope: {
          agency: "/app/tours",
        },
        modeKey: "turlar",
        moduleAliases: ["turlarimiz"],
        minMode: "lite",
      },
      {
        key: "agency-sheet-connections",
        label: "Google Sheets",
        icon: Zap,
        pathByScope: {
          agency: "/app/agency/sheets",
        },
        modeKey: "sheet_baglantilari",
        moduleAliases: ["google_sheets", "google_sheet_baglantisi", "google_sheet_baglantilari"],
        minMode: "pro",
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
        modeKey: "sheet_baglantilari",
        moduleAliases: ["google_sheets", "google_sheet_baglantisi", "google_sheet_baglantilari"],
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

export const ADMIN_MODULE_SECTIONS = [
  {
    group: "ADMIN MERKEZ",
    showInSidebar: true,
    items: [
      {
        key: "admin-dashboard",
        label: "Yönetici Dashboard",
        icon: LayoutGrid,
        pathByScope: { admin: "/app/admin/dashboard" },
        isCore: true,
      },
      {
        key: "admin-tenants",
        label: "Tenant Yönetimi",
        icon: Building2,
        pathByScope: { admin: "/app/admin/agencies" },
        isCore: true,
      },
      {
        key: "admin-users",
        label: "Tüm Kullanıcılar",
        icon: Users,
        pathByScope: { admin: "/app/admin/all-users" },
        isCore: true,
      },
      {
        key: "admin-agency-modules",
        label: "Acenta Modülleri",
        icon: ShieldCheck,
        pathByScope: { admin: "/app/admin/agency-modules" },
        isCore: true,
      },
      {
        key: "admin-tenant-features",
        label: "Tenant Features",
        icon: ShieldCheck,
        pathByScope: { admin: "/app/admin/tenant-features" },
        isCore: true,
      },
      {
        key: "admin-tenant-health",
        label: "Tenant Sağlığı",
        icon: Eye,
        pathByScope: { admin: "/app/admin/tenant-health" },
        isCore: true,
      },
      {
        key: "admin-analytics",
        label: "Analytics",
        icon: BarChart3,
        pathByScope: { admin: "/app/admin/analytics" },
        isCore: true,
      },
      {
        key: "admin-audit-logs",
        label: "Audit Logs",
        icon: Eye,
        pathByScope: { admin: "/app/admin/audit-logs" },
        isCore: true,
      },
      {
        key: "admin-audit-legacy",
        label: "Audit (Legacy)",
        icon: Eye,
        pathByScope: { admin: "/app/admin/audit" },
        isCore: true,
      },
      {
        key: "admin-email-logs",
        label: "E-posta Logları",
        icon: Eye,
        pathByScope: { admin: "/app/admin/email-logs" },
        isCore: true,
      },
      {
        key: "admin-pilot-dashboard",
        label: "Pilot Dashboard",
        icon: LayoutGrid,
        pathByScope: { admin: "/app/admin/pilot-dashboard" },
        isCore: true,
      },
      {
        key: "admin-platform-metrics",
        label: "Platform Metrics",
        icon: BarChart3,
        pathByScope: { admin: "/app/admin/metrics" },
        isCore: true,
      },
    ],
  },
  {
    group: "KATALOG & İÇERİK",
    showInSidebar: true,
    items: [
      {
        key: "admin-hotels",
        label: "Oteller",
        icon: Building2,
        pathByScope: { admin: "/app/admin/hotels" },
        isCore: true,
      },
      {
        key: "admin-tours",
        label: "Turlar",
        icon: Ticket,
        pathByScope: { admin: "/app/admin/tours" },
        isCore: true,
      },
      {
        key: "admin-links",
        label: "Bağlantılar",
        icon: Zap,
        pathByScope: { admin: "/app/admin/links" },
        isCore: true,
      },
      {
        key: "admin-contracts",
        label: "Acenta Sözleşmeleri",
        icon: Settings,
        pathByScope: { admin: "/app/admin/agency-contracts" },
        isCore: true,
      },
      {
        key: "admin-cms",
        label: "CMS Sayfaları",
        icon: LayoutGrid,
        pathByScope: { admin: "/app/admin/cms/pages" },
        isCore: true,
      },
      {
        key: "admin-catalog",
        label: "Katalog",
        icon: LayoutGrid,
        pathByScope: { admin: "/app/admin/catalog" },
        isCore: true,
      },
      {
        key: "admin-catalog-hotels",
        label: "Katalog Oteller",
        icon: Building2,
        pathByScope: { admin: "/app/admin/catalog/hotels" },
        isCore: true,
      },
      {
        key: "admin-theme",
        label: "Tema",
        icon: Settings,
        pathByScope: { admin: "/app/admin/theme" },
        isCore: true,
      },
      {
        key: "admin-branding",
        label: "Branding",
        icon: Settings,
        pathByScope: { admin: "/app/admin/branding" },
        isCore: true,
      },
    ],
  },
  {
    group: "B2B & BÜYÜME",
    showInSidebar: true,
    items: [
      {
        key: "admin-b2b-dashboard",
        label: "B2B Dashboard",
        icon: Users,
        pathByScope: { admin: "/app/admin/b2b/dashboard" },
        isCore: true,
      },
      {
        key: "admin-b2b-marketplace",
        label: "B2B Marketplace",
        icon: Users,
        pathByScope: { admin: "/app/admin/b2b/marketplace" },
        isCore: true,
      },
      {
        key: "admin-b2b-funnel",
        label: "B2B Funnel",
        icon: Megaphone,
        pathByScope: { admin: "/app/admin/b2b/funnel" },
        isCore: true,
      },
      {
        key: "admin-b2b-announcements",
        label: "B2B Duyurular",
        icon: Megaphone,
        pathByScope: { admin: "/app/admin/b2b/announcements" },
        isCore: true,
      },
      {
        key: "admin-b2b-discounts",
        label: "B2B İndirimler",
        icon: Megaphone,
        pathByScope: { admin: "/app/admin/b2b/discounts" },
        isCore: true,
      },
      {
        key: "admin-partners",
        label: "Partnerler",
        icon: Users,
        pathByScope: { admin: "/app/admin/partners" },
        isCore: true,
      },
      {
        key: "admin-funnel",
        label: "Pricing Funnel",
        icon: Megaphone,
        pathByScope: { admin: "/app/admin/pricing/funnel" },
        isCore: true,
      },
      {
        key: "admin-campaigns",
        label: "Kampanyalar",
        icon: Megaphone,
        pathByScope: { admin: "/app/admin/campaigns" },
        isCore: true,
      },
      {
        key: "admin-coupons",
        label: "Kuponlar",
        icon: Megaphone,
        pathByScope: { admin: "/app/admin/coupons" },
        isCore: true,
      },
      {
        key: "admin-marketplace-listings",
        label: "Marketplace Listings",
        icon: LayoutGrid,
        pathByScope: { admin: "/app/admin/marketplace/listings" },
        isCore: true,
      },
      {
        key: "admin-b2b-agency-products",
        label: "B2B Agency Products",
        icon: Users,
        pathByScope: { admin: "/app/admin/b2b/agency-products" },
        isCore: true,
      },
      {
        key: "admin-ops-b2b",
        label: "Ops B2B",
        icon: Users,
        pathByScope: { admin: "/app/admin/ops/b2b" },
        isCore: true,
      },
    ],
  },
  {
    group: "FİNANS & RAPORLAMA",
    showInSidebar: true,
    items: [
      {
        key: "admin-pricing",
        label: "Fiyatlandırma",
        icon: CreditCard,
        pathByScope: { admin: "/app/admin/pricing" },
        isCore: true,
      },
      {
        key: "admin-pricing-rules",
        label: "Fiyat Kuralları",
        icon: CreditCard,
        pathByScope: { admin: "/app/admin/pricing/rules" },
        isCore: true,
      },
      {
        key: "admin-pricing-incidents",
        label: "Fiyat Olayları",
        icon: CreditCard,
        pathByScope: { admin: "/app/admin/pricing/incidents" },
        isCore: true,
      },
      {
        key: "admin-refunds",
        label: "İadeler",
        icon: DollarSign,
        pathByScope: { admin: "/app/admin/finance/refunds" },
        isCore: true,
      },
      {
        key: "admin-exposure",
        label: "Finans Exposure",
        icon: DollarSign,
        pathByScope: { admin: "/app/admin/finance/exposure" },
        isCore: true,
      },
      {
        key: "admin-b2b-agencies",
        label: "B2B Acenteleri",
        icon: Users,
        pathByScope: { admin: "/app/admin/finance/b2b-agencies" },
        isCore: true,
      },
      {
        key: "admin-settlements",
        label: "Mutabakat",
        icon: DollarSign,
        pathByScope: { admin: "/app/admin/finance/settlements" },
        isCore: true,
      },
      {
        key: "admin-settlement-runs",
        label: "Settlement Runs",
        icon: DollarSign,
        pathByScope: { admin: "/app/admin/finance/settlement-runs" },
        isCore: true,
      },
      {
        key: "admin-supplier-accruals",
        label: "Supplier Accruals",
        icon: DollarSign,
        pathByScope: { admin: "/app/admin/ops/finance/supplier-accruals" },
        isCore: true,
      },
      {
        key: "admin-settlement-bridge",
        label: "Settlement Bridge",
        icon: DollarSign,
        pathByScope: { admin: "/app/admin/finance/supplier-settlement-bridge" },
        isCore: true,
      },
      {
        key: "admin-reporting",
        label: "Reporting",
        icon: BarChart3,
        pathByScope: { admin: "/app/admin/reporting" },
        isCore: true,
      },
      {
        key: "admin-exports",
        label: "Exportlar",
        icon: BarChart3,
        pathByScope: { admin: "/app/admin/exports" },
        isCore: true,
      },
      {
        key: "admin-scheduled-reports",
        label: "Scheduled Reports",
        icon: BarChart3,
        pathByScope: { admin: "/app/admin/scheduled-reports" },
        isCore: true,
      },
      {
        key: "admin-matches",
        label: "Matches",
        icon: BarChart3,
        pathByScope: { admin: "/app/admin/matches" },
        isCore: true,
      },
      {
        key: "admin-match-risk-trends",
        label: "Match Risk Trends",
        icon: BarChart3,
        pathByScope: { admin: "/app/admin/reports/match-risk-trends" },
        isCore: true,
      },
      {
        key: "admin-match-alerts",
        label: "Match Alerts",
        icon: ShieldCheck,
        pathByScope: { admin: "/app/admin/settings/match-alerts" },
        isCore: true,
      },
      {
        key: "admin-action-policies",
        label: "Action Policies",
        icon: ShieldCheck,
        pathByScope: { admin: "/app/admin/settings/action-policies" },
        isCore: true,
      },
    ],
  },
  {
    group: "OPERASYON & SİSTEM",
    showInSidebar: true,
    items: [
      {
        key: "admin-integrations",
        label: "Entegrasyonlar",
        icon: Zap,
        pathByScope: { admin: "/app/admin/integrations" },
        isCore: true,
      },
      {
        key: "admin-jobs",
        label: "Jobs",
        icon: Zap,
        pathByScope: { admin: "/app/admin/jobs" },
        isCore: true,
      },
      {
        key: "admin-api-keys",
        label: "API Anahtarları",
        icon: ShieldCheck,
        pathByScope: { admin: "/app/admin/api-keys" },
        isCore: true,
      },
      {
        key: "admin-approval-inbox",
        label: "Approval Inbox",
        icon: Ticket,
        pathByScope: { admin: "/app/admin/approval-inbox" },
        isCore: true,
      },
      {
        key: "admin-approvals",
        label: "Approvals",
        icon: Ticket,
        pathByScope: { admin: "/app/admin/approvals" },
        isCore: true,
      },
      {
        key: "admin-efatura",
        label: "E-Fatura",
        icon: Settings,
        pathByScope: { admin: "/app/admin/efatura" },
        isCore: true,
      },
      {
        key: "admin-sms",
        label: "SMS",
        icon: Settings,
        pathByScope: { admin: "/app/admin/sms" },
        isCore: true,
      },
      {
        key: "admin-tickets",
        label: "Tickets",
        icon: Ticket,
        pathByScope: { admin: "/app/admin/tickets" },
        isCore: true,
      },
      {
        key: "admin-system-backups",
        label: "System Backups",
        icon: Settings,
        pathByScope: { admin: "/app/admin/system-backups" },
        isCore: true,
      },
      {
        key: "admin-system-integrity",
        label: "System Integrity",
        icon: ShieldCheck,
        pathByScope: { admin: "/app/admin/system-integrity" },
        isCore: true,
      },
      {
        key: "admin-system-metrics",
        label: "System Metrics",
        icon: BarChart3,
        pathByScope: { admin: "/app/admin/system-metrics" },
        isCore: true,
      },
      {
        key: "admin-system-errors",
        label: "System Errors",
        icon: Eye,
        pathByScope: { admin: "/app/admin/system-errors" },
        isCore: true,
      },
      {
        key: "admin-system-uptime",
        label: "System Uptime",
        icon: Eye,
        pathByScope: { admin: "/app/admin/system-uptime" },
        isCore: true,
      },
      {
        key: "admin-system-incidents",
        label: "System Incidents",
        icon: Eye,
        pathByScope: { admin: "/app/admin/system-incidents" },
        isCore: true,
      },
      {
        key: "admin-preflight",
        label: "Preflight",
        icon: ShieldCheck,
        pathByScope: { admin: "/app/admin/preflight" },
        isCore: true,
      },
      {
        key: "admin-runbook",
        label: "Runbook",
        icon: Settings,
        pathByScope: { admin: "/app/admin/runbook" },
        isCore: true,
      },
      {
        key: "admin-perf-dashboard",
        label: "Perf Dashboard",
        icon: BarChart3,
        pathByScope: { admin: "/app/admin/perf-dashboard" },
        isCore: true,
      },
      {
        key: "admin-product-mode",
        label: "Product Mode",
        icon: Settings,
        pathByScope: { admin: "/app/admin/product-mode" },
        isCore: true,
      },
      {
        key: "admin-import",
        label: "Import",
        icon: Settings,
        pathByScope: { admin: "/app/admin/import" },
        isCore: true,
      },
      {
        key: "admin-portfolio-sync",
        label: "Portfolio Sync",
        icon: Zap,
        pathByScope: { admin: "/app/admin/portfolio-sync" },
        isCore: true,
      },
      {
        key: "admin-demo-guide",
        label: "Demo Guide",
        icon: LayoutGrid,
        pathByScope: { admin: "/app/admin/demo-guide" },
        isCore: true,
      },
      {
        key: "admin-tenant-export",
        label: "Tenant Export",
        icon: LayoutGrid,
        pathByScope: { admin: "/app/admin/tenant-export" },
        isCore: true,
      },
    ],
  },
  {
    group: "DOĞRUDAN ERİŞİM",
    showInSidebar: true,
    items: [
      {
        key: "app-products",
        label: "Ürünler",
        icon: LayoutGrid,
        pathByScope: { admin: "/app/products" },
        isCore: true,
      },
      {
        key: "app-inventory",
        label: "Envanter",
        icon: LayoutGrid,
        pathByScope: { admin: "/app/inventory" },
        isCore: true,
      },
      {
        key: "app-b2b",
        label: "B2B",
        icon: Users,
        pathByScope: { admin: "/app/b2b" },
        isCore: true,
      },
      {
        key: "app-webpos",
        label: "WebPOS",
        icon: CreditCard,
        pathByScope: { admin: "/app/finance/webpos" },
        isCore: true,
      },
      {
        key: "app-inbox",
        label: "Inbox",
        icon: Ticket,
        pathByScope: { admin: "/app/inbox" },
        isCore: true,
      },
      {
        key: "app-partners",
        label: "Partner Ağı",
        icon: Users,
        pathByScope: { admin: "/app/partners" },
        isCore: true,
      },
      {
        key: "app-ops-tasks",
        label: "Operasyon Görevleri",
        icon: Ticket,
        pathByScope: { admin: "/app/ops/tasks" },
        isCore: true,
      },
      {
        key: "app-ops-incidents",
        label: "Operasyon Incident",
        icon: Eye,
        pathByScope: { admin: "/app/ops/incidents" },
        isCore: true,
      },
      {
        key: "app-guest-cases",
        label: "Misafir Vakaları",
        icon: Users,
        pathByScope: { admin: "/app/ops/guest-cases" },
        isCore: true,
      },
      {
        key: "app-tours",
        label: "Tur Operasyonları",
        icon: Ticket,
        pathByScope: { admin: "/app/tours" },
        isCore: true,
      },
      {
        key: "app-usage",
        label: "Kullanım Özeti",
        icon: BarChart3,
        pathByScope: { admin: "/app/usage" },
        isCore: true,
      },
      {
        key: "app-onboarding",
        label: "Onboarding",
        icon: LayoutGrid,
        pathByScope: { admin: "/app/onboarding" },
        isCore: true,
      },
    ],
  },
];

export const ADMIN_NAV_SECTIONS = [
  {
    group: "YÖNETİM",
    showInSidebar: true,
    items: [
      {
        key: "admin-dashboard",
        label: "Yönetici Dashboard",
        icon: LayoutGrid,
        pathByScope: { admin: "/app/admin/dashboard" },
        isCore: true,
      },
      {
        key: "admin-tenants",
        label: "Tenant Yönetimi",
        icon: Building2,
        pathByScope: { admin: "/app/admin/agencies" },
        isCore: true,
      },
      {
        key: "admin-agency-modules",
        label: "Acenta Modülleri",
        icon: ShieldCheck,
        pathByScope: { admin: "/app/admin/agency-modules" },
        isCore: true,
      },
      {
        key: "admin-tenant-features",
        label: "Tenant Features",
        icon: ShieldCheck,
        pathByScope: { admin: "/app/admin/tenant-features" },
        isCore: true,
      },
      {
        key: "admin-pricing",
        label: "Fiyatlandırma",
        icon: CreditCard,
        pathByScope: { admin: "/app/admin/pricing" },
        isCore: true,
      },
      {
        key: "admin-analytics",
        label: "Analytics",
        icon: BarChart3,
        pathByScope: { admin: "/app/admin/analytics" },
        isCore: true,
      },
      {
        key: "admin-perf-dashboard",
        label: "Perf Dashboard",
        icon: BarChart3,
        pathByScope: { admin: "/app/admin/perf-dashboard" },
        isCore: true,
      },
      {
        key: "admin-modules",
        label: "Tüm Modüller",
        icon: LayoutGrid,
        pathByScope: { admin: "/app/admin/modules" },
        isCore: true,
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
    visibleScopes: ["admin"],
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
  const roles = normalizeRoles(user);
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