/**
 * Syroce Design System (SDS) — StatusBadge
 *
 * Semantic status indicator with color coding and optional dot.
 */
import React from "react";
import { cn } from "../../lib/utils";

const STATUS_CONFIG = {
  // Booking statuses
  pending:     { color: "warning",  label: "Beklemede" },
  confirmed:   { color: "info",     label: "Onaylandı" },
  paid:        { color: "success",  label: "Ödendi" },
  cancelled:   { color: "danger",   label: "İptal" },
  refunded:    { color: "muted",    label: "İade Edildi" },
  expired:     { color: "muted",    label: "Süresi Dolmuş" },
  // System statuses
  healthy:     { color: "success",  label: "Sağlıklı" },
  degraded:    { color: "warning",  label: "Bozulmuş" },
  down:        { color: "danger",   label: "Çökmüş" },
  // Generic
  active:      { color: "success",  label: "Aktif" },
  inactive:    { color: "muted",    label: "Pasif" },
  draft:       { color: "muted",    label: "Taslak" },
  processing:  { color: "info",     label: "İşleniyor" },
  error:       { color: "danger",   label: "Hata" },
  warning:     { color: "warning",  label: "Uyarı" },
  success:     { color: "success",  label: "Başarılı" },
  completed:   { color: "success",  label: "Tamamlandı" },
};

const COLOR_CLASSES = {
  success: {
    bg: "bg-emerald-50 dark:bg-emerald-500/10",
    text: "text-emerald-700 dark:text-emerald-400",
    dot: "bg-emerald-500",
  },
  warning: {
    bg: "bg-amber-50 dark:bg-amber-500/10",
    text: "text-amber-700 dark:text-amber-400",
    dot: "bg-amber-500",
  },
  danger: {
    bg: "bg-red-50 dark:bg-red-500/10",
    text: "text-red-700 dark:text-red-400",
    dot: "bg-red-500",
  },
  info: {
    bg: "bg-blue-50 dark:bg-blue-500/10",
    text: "text-blue-700 dark:text-blue-400",
    dot: "bg-blue-500",
  },
  muted: {
    bg: "bg-gray-100 dark:bg-gray-500/10",
    text: "text-gray-600 dark:text-gray-400",
    dot: "bg-gray-400",
  },
};

const SIZE_CLASSES = {
  sm: "px-1.5 py-0.5 text-[10px]",
  md: "px-2 py-0.5 text-xs",
};

export function StatusBadge({
  status,
  label: customLabel,
  color: customColor,
  size = "md",
  showDot = true,
  className,
}) {
  const config = STATUS_CONFIG[status] || {};
  const colorKey = customColor || config.color || "muted";
  const colors = COLOR_CLASSES[colorKey] || COLOR_CLASSES.muted;
  const displayLabel = customLabel || config.label || status;

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full font-medium whitespace-nowrap",
        colors.bg,
        colors.text,
        SIZE_CLASSES[size],
        className
      )}
      data-testid={`status-badge-${status}`}
    >
      {showDot && (
        <span className={cn("h-1.5 w-1.5 rounded-full shrink-0", colors.dot)} />
      )}
      {displayLabel}
    </span>
  );
}

export default StatusBadge;
