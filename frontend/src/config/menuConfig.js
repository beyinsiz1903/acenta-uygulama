export const MENU_CONFIG = {
  super_admin: [
    {
      label: "Admin",
      children: [
        { label: "Acentalar", path: "/app/admin/agencies" },
        { label: "Oteller", path: "/app/admin/hotels" },
        { label: "Link Yönetimi", path: "/app/admin/links" },
        { label: "Pilot Dashboard", path: "/app/admin/pilot-dashboard" },
      ],
    },
    {
      label: "Ops (Gelişmiş)",
      children: [
        { label: "Audit Logs", path: "/app/admin/audit" },
        { label: "Email Aktiviteleri", path: "/app/admin/email-logs" },
      ],
    },
  ],

  agency: [
    {
      label: "Acenta",
      children: [
        { label: "Hızlı Rezervasyon", path: "/app/agency/hotels" },
        { label: "Rezervasyonlarım", path: "/app/agency/bookings" },
        { label: "Mutabakat", path: "/app/agency/settlements" },
        { label: "Yardım", path: "/app/agency/help" },
      ],
    },
  ],

  hotel: [
    {
      label: "Otel",
      children: [
        { label: "Rezervasyonlarım", path: "/app/hotel/bookings" },
        { label: "Satışa Kapat", path: "/app/hotel/stop-sell" },
        { label: "Acenta Kotası", path: "/app/hotel/allocations" },
        { label: "Mutabakat", path: "/app/hotel/settlements" },
        { label: "Yardım", path: "/app/hotel/help" },
      ],
    },
  ],
};

export function getMenuForUser(user) {
  if (!user) return [];

  if (user.roles?.includes("super_admin")) {
    return MENU_CONFIG.super_admin;
  }

  if (
    user.roles?.includes("agency_admin") ||
    user.roles?.includes("agency_agent")
  ) {
    return MENU_CONFIG.agency;
  }

  if (user.roles?.includes("hotel_admin") || user.roles?.includes("hotel_staff")) {
    return MENU_CONFIG.hotel;
  }

  return [];
}
