// Centralised admin navigation definition (FAZ 0)
// This describes sections + items; AppShell decides how to render.

export const adminNav = [
  {
    label: "Admin",
    children: [
      { label: "B2B Genel Bakış", path: "/app/admin/b2b/dashboard" },
      { label: "Acentalar", path: "/app/admin/agencies" },
      { label: "Oteller", path: "/app/admin/hotels" },
      { label: "Turlar", path: "/app/admin/tours" },
      { label: "Bağlantı Yönetimi", path: "/app/admin/links" },
      { label: "CMS Sayfaları", path: "/app/admin/cms/pages" },
      { label: "Kampanyalar", path: "/app/admin/campaigns" },
      { label: "Partnerler", path: "/app/admin/partners" },
      { label: "B2B Pazar Yeri", path: "/app/admin/b2b/marketplace" },
      { label: "Katalog", path: "/app/admin/catalog" },
      { label: "Otel Kataloğu", path: "/app/admin/catalog/hotels" },
      { label: "Fiyatlandırma", path: "/app/admin/pricing" },
      { label: "Kuponlar", path: "/app/admin/coupons" },
      { label: "Onay Görevleri", path: "/app/admin/approvals" },
      { label: "WebPOS", path: "/app/finance/webpos", requiredFeature: "webpos" },
      { label: "Finans / İadeler", path: "/app/admin/finance/refunds" },
      { label: "Açık Bakiye Takibi", path: "/app/admin/finance/exposure" },
      { label: "B2B Acenteler", path: "/app/admin/finance/b2b-agencies" },
      { label: "Satış Hunisi", path: "/app/admin/b2b/funnel" },
      { label: "Duyurular", path: "/app/admin/b2b/announcements" },
      { label: "Finans / Mutabakat", path: "/app/admin/finance/settlements" },
      { label: "Ops / B2B", path: "/app/admin/ops/b2b" },
      { label: "Özellik Ayarları", path: "/app/admin/tenant-features" },
      { label: "İşlem Geçmişi", path: "/app/admin/audit-logs" },
      { label: "Gelir Analizi", path: "/app/admin/analytics" },
      { label: "Sistem Durumu", path: "/app/admin/tenant-health" },
    ],
  },
  {
    label: "RİSK TAKİBİ",
    children: [
      { label: "Eşleşme Listesi", path: "/app/admin/matches" },
      { label: "Risk Raporu", path: "/app/admin/reports/match-risk" },
      { label: "Risk Eğilimleri", path: "/app/admin/reports/match-risk-trends" },
      { label: "Uyarı Kuralları", path: "/app/admin/settings/match-alerts" },
      { label: "İşlem Kuralları", path: "/app/admin/settings/action-policies" },
      { label: "Dışa Aktarma", path: "/app/admin/exports" },
    ],
  },
  {
    label: "SİSTEM YÖNETİMİ",
    children: [
      { label: "Sistem Yedekleri", path: "/app/admin/system-backups" },
      { label: "Veri Bütünlüğü", path: "/app/admin/system-integrity" },
      { label: "Sistem Metrikleri", path: "/app/admin/system-metrics" },
      { label: "Sistem Hataları", path: "/app/admin/system-errors" },
      { label: "Çalışma Süresi", path: "/app/admin/system-uptime" },
      { label: "Olay Yönetimi", path: "/app/admin/system-incidents" },
      { label: "Canlıya Geçiş Kontrolü", path: "/app/admin/preflight" },
      { label: "İşlem Kılavuzu", path: "/app/admin/runbook" },
      { label: "Performans Takibi", path: "/app/admin/perf-dashboard" },
      { label: "Tanıtım Rehberi", path: "/app/admin/demo-guide" },
    ],
  },
  {
    label: "VERİ AKTARIMI",
    children: [
      { label: "Veri Aktarma", path: "/app/admin/import" },
      { label: "Otomatik Eşitleme", path: "/app/admin/portfolio-sync" },
    ],
  },
];
