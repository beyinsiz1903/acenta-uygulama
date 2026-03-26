/**
 * Agency Persona Navigation — Faz 3
 *
 * 7 sidebar groups. Task-oriented, not module-oriented.
 * Uses business language: "Arama & Satis", "Teklifler", "Müşteriler"
 */
import {
  BarChart3,
  BedDouble,
  Building2,
  CreditCard,
  DollarSign,
  DoorOpen,
  FileText,
  HelpCircle,
  LayoutGrid,
  Search,
  Ticket,
  Users,
  Wallet,
  Zap,
} from "lucide-react";

export const AGENCY_SIDEBAR_SECTIONS = [
  /* ────────────────────────────────────────────── */
  /*  1. DASHBOARD                                   */
  /* ────────────────────────────────────────────── */
  {
    group: "DASHBOARD",
    showInSidebar: true,
    items: [
      {
        key: "agency-dashboard",
        label: "Ana Panel",
        icon: LayoutGrid,
        to: "/app",
        end: true,
        isCore: true,
        visibleInSidebar: true,
        visibleInSearch: true,
        modeKey: "dashboard",
        minMode: "lite",
      },
    ],
  },

  /* ────────────────────────────────────────────── */
  /*  2. ARAMA & SATIŞ                               */
  /* ────────────────────────────────────────────── */
  {
    group: "ARAMA & SATIŞ",
    showInSidebar: true,
    items: [
      {
        key: "agency-hotel-search",
        label: "Otel Arama",
        icon: Building2,
        to: "/app/agency/hotels",
        isCore: true,
        visibleInSidebar: true,
        visibleInSearch: true,
        feature: "inventory",
        modeKey: "oteller",
        moduleAliases: ["otellerim", "urunler"],
        minMode: "lite",
      },
      {
        key: "agency-unified-search",
        label: "Çoklu Arama",
        icon: Search,
        to: "/app/agency/unified-search",
        isCore: true,
        visibleInSidebar: true,
        visibleInSearch: true,
        modeKey: "coklu_arama",
        minMode: "lite",
      },
      {
        key: "agency-availability",
        label: "Müsaitlik",
        icon: LayoutGrid,
        to: "/app/agency/availability",
        isCore: true,
        visibleInSidebar: true,
        visibleInSearch: true,
        feature: "inventory",
        modeKey: "musaitlik",
        moduleAliases: ["musaitlik_takibi"],
        minMode: "lite",
      },
      {
        key: "agency-tours",
        label: "Turlar",
        icon: Ticket,
        to: "/app/tours",
        isCore: true,
        visibleInSidebar: true,
        visibleInSearch: true,
        modeKey: "turlar",
        moduleAliases: ["turlarimiz"],
        minMode: "lite",
      },
    ],
  },

  /* ────────────────────────────────────────────── */
  /*  3. REZERVASYONLAR                              */
  /* ────────────────────────────────────────────── */
  {
    group: "REZERVASYONLAR",
    showInSidebar: true,
    items: [
      {
        key: "agency-bookings",
        label: "Rezervasyonlarım",
        icon: Ticket,
        to: "/app/agency/bookings",
        isCore: true,
        visibleInSidebar: true,
        visibleInSearch: true,
        modeKey: "rezervasyonlar",
        minMode: "lite",
      },
      // directAccessOnly
      {
        key: "agency-all-reservations",
        label: "Tüm Rezervasyonlar",
        icon: Ticket,
        to: "/app/reservations",
        isCore: true,
        visibleInSidebar: false,
        visibleInSearch: true,
        directAccessOnly: true,
      },
    ],
  },

  /* ────────────────────────────────────────────── */
  /*  4. TEKLİFLER                                   */
  /* ────────────────────────────────────────────── */
  {
    group: "TEKLİFLER",
    showInSidebar: true,
    items: [
      {
        key: "agency-pipeline",
        label: "Satış Pipeline",
        icon: BarChart3,
        to: "/app/crm/pipeline",
        isCore: true,
        visibleInSidebar: true,
        visibleInSearch: true,
        feature: "crm",
        modeKey: "teklifler",
        minMode: "lite",
      },
      {
        key: "agency-crm-tasks",
        label: "CRM Görevleri",
        icon: FileText,
        to: "/app/crm/tasks",
        isCore: true,
        visibleInSidebar: true,
        visibleInSearch: true,
        feature: "crm",
        modeKey: "crm_gorevleri",
        minMode: "lite",
      },
    ],
  },

  /* ────────────────────────────────────────────── */
  /*  5. MÜŞTERİLER                                  */
  /* ────────────────────────────────────────────── */
  {
    group: "MÜŞTERİLER",
    showInSidebar: true,
    items: [
      {
        key: "agency-customers",
        label: "Müşteri Listesi",
        icon: Users,
        to: "/app/crm/customers",
        isCore: true,
        visibleInSidebar: true,
        visibleInSearch: true,
        feature: "crm",
        modeKey: "musteriler",
        minMode: "lite",
      },
    ],
  },

  /* ────────────────────────────────────────────── */
  /*  6. HESAP / FİNANS                              */
  /* ────────────────────────────────────────────── */
  {
    group: "HESAP & FİNANS",
    showInSidebar: true,
    items: [
      {
        key: "agency-settlements",
        label: "Mutabakat",
        icon: DollarSign,
        to: "/app/agency/settlements",
        isCore: true,
        visibleInSidebar: true,
        visibleInSearch: true,
        modeKey: "mutabakat",
        minMode: "lite",
      },
      {
        key: "agency-pms",
        label: "PMS Paneli",
        icon: BedDouble,
        to: "/app/agency/pms",
        isCore: true,
        visibleInSidebar: true,
        visibleInSearch: true,
        modeKey: "pms_paneli",
        minMode: "lite",
      },
      {
        key: "agency-accounting",
        label: "Muhasebe",
        icon: Wallet,
        to: "/app/agency/pms/accounting",
        isCore: true,
        visibleInSidebar: true,
        visibleInSearch: true,
        modeKey: "muhasebe",
        minMode: "lite",
      },
      {
        key: "agency-invoices",
        label: "Faturalar",
        icon: FileText,
        to: "/app/invoices",
        isCore: true,
        visibleInSidebar: true,
        visibleInSearch: true,
        modeKey: "faturalar",
        minMode: "lite",
      },
      // directAccessOnly
      {
        key: "agency-pms-rooms",
        label: "Oda Yönetimi",
        icon: DoorOpen,
        to: "/app/agency/pms/rooms",
        isCore: true,
        visibleInSidebar: false,
        visibleInSearch: true,
        directAccessOnly: true,
        modeKey: "oda_yonetimi",
        minMode: "lite",
      },
      {
        key: "agency-pms-invoices",
        label: "PMS Faturalar",
        icon: FileText,
        to: "/app/agency/pms/invoices",
        isCore: true,
        visibleInSidebar: false,
        visibleInSearch: true,
        directAccessOnly: true,
      },
    ],
  },

  /* ────────────────────────────────────────────── */
  /*  7. DESTEK                                      */
  /* ────────────────────────────────────────────── */
  {
    group: "DESTEK",
    showInSidebar: true,
    items: [
      {
        key: "agency-help",
        label: "Yardım",
        icon: HelpCircle,
        to: "/app/agency/help",
        isCore: true,
        visibleInSidebar: true,
        visibleInSearch: true,
      },
      {
        key: "agency-sheets",
        label: "Google Sheets",
        icon: Zap,
        to: "/app/agency/sheets",
        isCore: true,
        visibleInSidebar: true,
        visibleInSearch: true,
        modeKey: "sheet_baglantilari",
        moduleAliases: ["google_sheets", "google_sheet_baglantisi", "google_sheet_baglantilari"],
        minMode: "pro",
      },
      // directAccessOnly
      {
        key: "agency-reports",
        label: "Raporlar",
        icon: BarChart3,
        to: "/app/reports",
        isCore: true,
        visibleInSidebar: false,
        visibleInSearch: true,
        directAccessOnly: true,
        feature: "reports",
        modeKey: "raporlar",
        minMode: "lite",
      },
    ],
  },
];

export const AGENCY_ACCOUNT_LINKS = [
  {
    key: "settings",
    label: "Ayarlar",
    icon: CreditCard,
    to: "/app/settings",
    visibleInSidebar: true,
    visibleInSearch: true,
  },
];
