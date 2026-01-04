export const MENU_CONFIG = {
  super_admin: [
    {
      label: "Admin",
      children: [
        { label: "Acentalar", path: "/app/admin/agencies" },
        { label: "Oteller", path: "/app/admin/hotels" },
        { label: "Link Yönetimi", path: "/app/admin/links" },
        { label: "Pilot Dashboard", path: "/app/admin/pilot-dashboard" },
        { label: "Metrikler", path: "/app/admin/metrics" },
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
        { label: "Finansal Raporlar", path: "/app/agency/reports" },
        { label: "CRM (Takip)", path: "/app/agency/crm" },
        { label: "Ödeme Ayarları", path: "/app/agency/settings/payment" },
        { label: "Yardım", path: "/app/agency/help" },
      ],
    },
    {
      label: "Ürünler",
      children: [
        { label: "Oteller", path: "/app/agency/products/hotels" },
        { label: "Turlarım", path: "/app/agency/tours" },
        { label: "Tur Talepleri", path: "/app/agency/tour-bookings" },
      ],
    },
    {
      label: "Katalog",
      children: [
        { label: "Ürünler", path: "/app/agency/catalog/products" },
        { label: "Rezervasyonlar", path: "/app/agency/catalog/bookings" },
        { label: "Kapasite", path: "/app/agency/catalog/capacity" },
      ],
    },
  ],

  hotel: [
    {
      label: "Otel",
      children: [
        { label: "Rezervasyonlarım", path: "/app/hotel/bookings" },
        { label: "Finansal Özet", path: "/app/hotel/dashboard" },
        { label: "Satışa Kapat", path: "/app/hotel/stop-sell" },
        { label: "Acenta Kotası", path: "/app/hotel/allocations" },
        { label: "Mutabakat", path: "/app/hotel/settlements" },
        // Channel Hub will be shown conditionally based on hotel.package === "channel"
        { label: "Channel Hub", path: "/app/hotel/integrations", featureKey: "channel_hub" },
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
