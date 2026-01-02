// Central navigation configuration for main sidebar/top nav
// Each item is controlled by a feature flag key coming from normalized tenant.features

export const NAV_ITEMS = [
  {
    key: "dashboard",
    label: "Dashboard",
    path: "/dashboard",
    feature: "dashboard",
  },
  {
    key: "reservation_calendar",
    label: "Takvim",
    path: "/reservation-calendar",
    feature: "reservation_calendar",
  },
  {
    key: "pms",
    label: "PMS",
    path: "/pms",
    feature: "pms",
  },
  {
    key: "reports",
    label: "Raporlar",
    path: "/reports",
    feature: "reports_lite",
  },
  {
    key: "settings",
    label: "Ayarlar",
    path: "/settings",
    feature: "settings_lite",
  },

  // Full / advanced modules (examples). These will be visible only if corresponding
  // normalized feature flag is true for the tenant.
  {
    key: "rms",
    label: "RMS",
    path: "/rms",
    feature: "rms",
  },
  {
    key: "ai",
    label: "AI",
    path: "/ai",
    feature: "ai",
  },
  {
    key: "marketplace",
    label: "Marketplace",
    path: "/marketplace",
    feature: "marketplace",
  },
];
