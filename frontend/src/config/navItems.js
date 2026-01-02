// Central navigation configuration for main sidebar/top nav
// Each item is controlled by a feature flag key coming from normalized tenant.features

export const PMS_LITE_NAV_KEYS = new Set([
  'dashboard',
  'reservation_calendar',
  'pms',
  'reports',
  'settings',
]);

export const NAV_ITEMS = [
  {
    key: "dashboard",
    label: "Dashboard",
    path: "/app/dashboard",
    feature: "dashboard",
  },
  {
    key: "reservation_calendar",
    label: "Takvim",
    path: "/app/reservation-calendar",
    feature: "reservation_calendar",
  },
  {
    key: "pms",
    label: "PMS",
    path: "/app/pms",
    feature: "pms",
  },
  {
    key: "reports",
    label: "Raporlar",
    path: "/app/reports",
    feature: "reports_lite",
  },
  {
    key: "settings",
    label: "Ayarlar",
    path: "/app/settings",
    feature: "settings_lite",
  },

  // FULL MODÜLLER (Lite'ta gizli kalacak)
  {
    key: "invoices",
    label: "Fatura",
    path: "/app/invoices",
    feature: "invoices",
  },
  {
    key: "cost_management",
    label: "Cost Management",
    path: "/app/cost-management",
    feature: "cost_management",
  },
  {
    key: "channel_manager",
    label: "Channel Manager",
    path: "/app/channel-manager",
    feature: "channel_manager",
  },
  {
    key: "rms",
    label: "RMS",
    path: "/app/rms",
    feature: "rms",
  },
  {
    key: "ai",
    label: "AI",
    path: "/app/ai",
    feature: "ai",
  },
  {
    key: "marketplace",
    label: "Marketplace",
    path: "/app/marketplace",
    feature: "marketplace",
  },
];
