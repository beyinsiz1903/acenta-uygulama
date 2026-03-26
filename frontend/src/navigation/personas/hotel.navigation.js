/**
 * Hotel Persona Navigation — Faz 3
 *
 * 7 sidebar groups. Focused on inventory, pricing, bookings, restrictions.
 * Groups 3 (Fiyatlandirma) and 6 (Performans) are placeholders for future sprints.
 */
import {
  BarChart3,
  BedDouble,
  HelpCircle,
  LayoutGrid,
  Settings,
  ShieldCheck,
  Ticket,
  Zap,
} from "lucide-react";

export const HOTEL_SIDEBAR_SECTIONS = [
  /* ────────────────────────────────────────────── */
  /*  1. DASHBOARD                                   */
  /* ────────────────────────────────────────────── */
  {
    group: "DASHBOARD",
    showInSidebar: true,
    items: [
      {
        key: "hotel-dashboard",
        label: "Genel Bakış",
        icon: LayoutGrid,
        to: "/app/hotel/dashboard",
        end: true,
        isCore: true,
        visibleInSidebar: true,
        visibleInSearch: true,
      },
    ],
  },

  /* ────────────────────────────────────────────── */
  /*  2. ENVANTER                                    */
  /* ────────────────────────────────────────────── */
  {
    group: "ENVANTER",
    showInSidebar: true,
    items: [
      {
        key: "hotel-allocations",
        label: "Kontenjan Yönetimi",
        icon: BedDouble,
        to: "/app/hotel/allocations",
        isCore: true,
        visibleInSidebar: true,
        visibleInSearch: true,
      },
    ],
  },

  /* ────────────────────────────────────────────── */
  /*  3. FİYATLANDIRMA (gelecek sprint)              */
  /* ────────────────────────────────────────────── */
  // Placeholder — items will be added in Sprint 3

  /* ────────────────────────────────────────────── */
  /*  4. REZERVASYONLAR                              */
  /* ────────────────────────────────────────────── */
  {
    group: "REZERVASYONLAR",
    showInSidebar: true,
    items: [
      {
        key: "hotel-bookings",
        label: "Gelen Talepler",
        icon: Ticket,
        to: "/app/hotel/bookings",
        isCore: true,
        visibleInSidebar: true,
        visibleInSearch: true,
      },
    ],
  },

  /* ────────────────────────────────────────────── */
  /*  5. KISITLAR                                    */
  /* ────────────────────────────────────────────── */
  {
    group: "KISITLAR",
    showInSidebar: true,
    items: [
      {
        key: "hotel-stop-sell",
        label: "Stop Sell",
        icon: ShieldCheck,
        to: "/app/hotel/stop-sell",
        isCore: true,
        visibleInSidebar: true,
        visibleInSearch: true,
      },
    ],
  },

  /* ────────────────────────────────────────────── */
  /*  6. PERFORMANS (gelecek sprint)                 */
  /* ────────────────────────────────────────────── */
  // Placeholder — analytics/doluluk items will be added later

  /* ────────────────────────────────────────────── */
  /*  7. AYARLAR                                     */
  /* ────────────────────────────────────────────── */
  {
    group: "AYARLAR",
    showInSidebar: true,
    items: [
      {
        key: "hotel-integrations",
        label: "Entegrasyonlar",
        icon: Zap,
        to: "/app/hotel/integrations",
        isCore: true,
        visibleInSidebar: true,
        visibleInSearch: true,
      },
      {
        key: "hotel-settlements",
        label: "Mutabakat",
        icon: BarChart3,
        to: "/app/hotel/settlements",
        isCore: true,
        visibleInSidebar: true,
        visibleInSearch: true,
      },
      {
        key: "hotel-help",
        label: "Yardım",
        icon: HelpCircle,
        to: "/app/hotel/help",
        isCore: true,
        visibleInSidebar: true,
        visibleInSearch: true,
      },
    ],
  },
];

export const HOTEL_ACCOUNT_LINKS = [];
