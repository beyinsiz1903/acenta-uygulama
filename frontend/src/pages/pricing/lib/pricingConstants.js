import {
  TrendingUp, Tag, Shield, Layers, Globe, Building2, Store, Users,
} from "lucide-react";

export const CHANNEL_ICONS = { b2b: Building2, b2c: Store, corporate: Globe, whitelabel: Users };

export const CHANNEL_COLORS = {
  b2b: "bg-blue-50 text-blue-700 border-blue-200",
  b2c: "bg-emerald-50 text-emerald-700 border-emerald-200",
  corporate: "bg-violet-50 text-violet-700 border-violet-200",
  whitelabel: "bg-amber-50 text-amber-700 border-amber-200",
};

export const GUARDRAIL_LABELS = {
  min_margin_pct: "Minimum Marj %",
  max_discount_pct: "Maksimum Indirim %",
  channel_floor_price: "Kanal Taban Fiyat",
  supplier_max_markup_pct: "Supplier Maks Markup %",
};

export const GUARDRAIL_ICONS = {
  min_margin_pct: TrendingUp,
  max_discount_pct: Tag,
  channel_floor_price: Shield,
  supplier_max_markup_pct: Layers,
};

export const STEP_COLORS = {
  supplier_price: { bg: "bg-slate-100", border: "border-slate-300", text: "text-slate-700", accent: "bg-slate-600" },
  base_markup: { bg: "bg-blue-50", border: "border-blue-200", text: "text-blue-700", accent: "bg-blue-600" },
  channel_rule: { bg: "bg-violet-50", border: "border-violet-200", text: "text-violet-700", accent: "bg-violet-600" },
  agency_rule: { bg: "bg-indigo-50", border: "border-indigo-200", text: "text-indigo-700", accent: "bg-indigo-600" },
  promotion: { bg: "bg-amber-50", border: "border-amber-200", text: "text-amber-700", accent: "bg-amber-600" },
  tax: { bg: "bg-gray-50", border: "border-gray-200", text: "text-gray-600", accent: "bg-gray-500" },
  currency_conversion: { bg: "bg-teal-50", border: "border-teal-200", text: "text-teal-700", accent: "bg-teal-600" },
};

export function fmtCurrency(amt, cur = "EUR") {
  if (amt == null) return "-";
  return new Intl.NumberFormat("tr-TR", { style: "currency", currency: cur }).format(amt);
}
