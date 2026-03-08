import React from "react";
import { UsageQuotaCard } from "./UsageQuotaCard";

export const UsageMetricTiles = ({ entries = [], compact = false, testIdPrefix = "usage-metric", showCta = false }) => {
  if (!entries.length) {
    return <div className="rounded-2xl border border-dashed p-4 text-sm text-muted-foreground" data-testid={`${testIdPrefix}-empty`}>Henüz usage verisi yok.</div>;
  }

  return (
    <div className={`grid gap-3 ${compact ? "md:grid-cols-3" : "md:grid-cols-2 xl:grid-cols-3"}`} data-testid={`${testIdPrefix}-grid`}>
      {entries.map((entry) => <UsageQuotaCard key={entry.key} entry={entry} compact={compact} showCta={showCta} testIdPrefix={testIdPrefix} />)}
    </div>
  );
};