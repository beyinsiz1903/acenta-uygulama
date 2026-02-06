// Centralised admin navigation definition (FAZ 0)
// This describes sections + items; AppShell decides how to render.

export const adminNav = [
  {
    label: "Admin",
    children: [
      { label: "B2B Dashboard", path: "/app/admin/b2b/dashboard" },
      { label: "Acentalar", path: "/app/admin/agencies" },
      { label: "Oteller", path: "/app/admin/hotels" },
      { label: "Turlar", path: "/app/admin/tours" },
      { label: "Link Yönetimi", path: "/app/admin/links" },
      { label: "CMS Sayfaları", path: "/app/admin/cms/pages" },
      { label: "Kampanyalar", path: "/app/admin/campaigns" },
      { label: "Partnerler", path: "/app/admin/partners" },
      { label: "B2B Marketplace", path: "/app/admin/b2b/marketplace" },
      { label: "Katalog", path: "/app/admin/catalog" },
      { label: "Otel Kataloğu", path: "/app/admin/catalog/hotels" },
      { label: "Fiyatlandırma", path: "/app/admin/pricing" },
      { label: "Kuponlar", path: "/app/admin/coupons" },
      { label: "Onay Görevleri", path: "/app/admin/approvals" },
      { label: "Finans / İadeler", path: "/app/admin/finance/refunds" },
      { label: "Exposure & Aging (Acenta)", path: "/app/admin/finance/exposure" },
      { label: "B2B Acenteler", path: "/app/admin/finance/b2b-agencies" },
      { label: "B2B Funnel", path: "/app/admin/b2b/funnel" },
      { label: "B2B Duyuruları", path: "/app/admin/b2b/announcements" },
      { label: "Finans / Mutabakat", path: "/app/admin/finance/settlements" },
      { label: "Ops / B2B", path: "/app/admin/ops/b2b" },
      { label: "Tenant Özellikleri", path: "/app/admin/tenant-features" },
      { label: "Audit Log", path: "/app/admin/audit-logs" },
    ],
  },
  {
    label: "Risk & Matches",
    children: [
      { label: "Match Listesi", path: "/app/admin/matches" },
      { label: "Match Risk Raporu", path: "/app/admin/reports/match-risk" },
      { label: "Match Risk Trendleri", path: "/app/admin/reports/match-risk-trends" },
      { label: "Match Alert Politikaları", path: "/app/admin/settings/match-alerts" },
      { label: "Aksiyon Politikaları", path: "/app/admin/settings/action-policies" },
      { label: "Export Çalıştırma", path: "/app/admin/exports" },
    ],
  },
];
