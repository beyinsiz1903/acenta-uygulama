/**
 * B2B Persona Navigation — Faz 3
 *
 * Used by B2BLayout (separate from AppShell).
 * 6 sidebar groups for B2B portal users.
 */
import {
  FileText,
  HelpCircle,
  LayoutGrid,
  Search,
  Ticket,
  Wallet,
} from "lucide-react";

export const B2B_SIDEBAR_SECTIONS = [
  {
    group: "DASHBOARD",
    showInSidebar: true,
    items: [
      {
        key: "b2b-dashboard",
        label: "Ana Panel",
        icon: LayoutGrid,
        to: "/b2b/bookings",
        end: true,
        isCore: true,
        visibleInSidebar: true,
        visibleInSearch: true,
      },
    ],
  },
  {
    group: "ARAMA",
    showInSidebar: true,
    items: [
      {
        key: "b2b-search",
        label: "Ürün Arama",
        icon: Search,
        to: "/b2b/search",
        isCore: true,
        visibleInSidebar: true,
        visibleInSearch: true,
      },
    ],
  },
  {
    group: "REZERVASYONLARIM",
    showInSidebar: true,
    items: [
      {
        key: "b2b-bookings",
        label: "Rezervasyonlarım",
        icon: Ticket,
        to: "/b2b/bookings",
        isCore: true,
        visibleInSidebar: true,
        visibleInSearch: true,
      },
    ],
  },
  {
    group: "DOKÜMANLAR",
    showInSidebar: true,
    items: [
      {
        key: "b2b-documents",
        label: "Dokümanlar",
        icon: FileText,
        to: "/b2b/documents",
        isCore: true,
        visibleInSidebar: true,
        visibleInSearch: true,
      },
    ],
  },
  {
    group: "HESAP ÖZETİ",
    showInSidebar: true,
    items: [
      {
        key: "b2b-account",
        label: "Cari Hesap",
        icon: Wallet,
        to: "/b2b/account",
        isCore: true,
        visibleInSidebar: true,
        visibleInSearch: true,
      },
    ],
  },
  {
    group: "DESTEK",
    showInSidebar: true,
    items: [
      {
        key: "b2b-support",
        label: "Destek",
        icon: HelpCircle,
        to: "/b2b/support",
        isCore: true,
        visibleInSidebar: true,
        visibleInSearch: true,
      },
    ],
  },
];

export const B2B_ACCOUNT_LINKS = [];
