import React, { useMemo } from "react";

function buildSlaHelpText({ slaDays }) {
  // keep it short, ops-friendly, deterministic
  return [
    `SLA: ${slaDays} gün`,
    "Risk bantları (case açıkken):",
    "• 0–1g: FRESH",
    "• 2–6g: ACTIVE RISK",
    `• ≥${slaDays}g: SLA BREACH`,
    "Age hesabı: created_at → bugün (lokal saat, 00:00 normalize).",
  ].join("\n");
}

/**
 * Minimal tooltip: native title + optional inline popover later.
 * Deterministic text, no deps.
 */
export default function SlaTooltip({
  slaDays = 7,
  testId = "sla-tooltip",
  className = "",
}) {
  const text = useMemo(() => buildSlaHelpText({ slaDays }), [slaDays]);

  return (
    <span
      className={[
        "inline-flex items-center justify-center rounded-full border bg-muted px-2 py-0.5 text-2xs font-semibold text-muted-foreground",
        "cursor-help select-none",
        className,
      ].join(" ")}
      title={text}
      data-testid={testId}
      aria-label="SLA info"
    >
      SLA ?
    </span>
  );
}
