// Centralised agency navigation definition (FAZ 0)

export const agencyNav = [
  {
    label: "PMS",
    children: [
      { label: "PMS Paneli", path: "/app/agency/pms" },
      { label: "Oda Yonetimi", path: "/app/agency/pms/rooms" },
    ],
  },
  {
    label: "B2B",
    children: [
      { label: "Otellerim", path: "/app/agency/hotels" },
      { label: "Müsaitlik", path: "/app/agency/availability" },
      { label: "Sheet Bağlantıları", path: "/app/agency/sheets" },
      { label: "Rezervasyonlarım", path: "/app/agency/bookings" },
      { label: "Mutabakat", path: "/app/agency/settlements" },
      { label: "Yardım", path: "/app/agency/help" },
    ],
  },
];
