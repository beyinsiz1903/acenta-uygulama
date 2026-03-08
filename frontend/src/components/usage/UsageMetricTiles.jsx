import React from "react";
import { Badge } from "../ui/badge";
import { formatUsageLimit } from "../../lib/usage";

export const UsageMetricTiles = ({ entries = [], compact = false, testIdPrefix = "usage-metric" }) => {
  if (!entries.length) {
    return <div className="rounded-2xl border border-dashed p-4 text-sm text-muted-foreground" data-testid={`${testIdPrefix}-empty`}>Henüz usage verisi yok.</div>;
  }

  return (
    <div className={`grid gap-3 ${compact ? "md:grid-cols-3" : "md:grid-cols-2 xl:grid-cols-3"}`} data-testid={`${testIdPrefix}-grid`}>
      {entries.map((entry) => (
        <div key={entry.key} className="rounded-2xl border bg-card/80 p-4 shadow-sm" data-testid={`${testIdPrefix}-${entry.testId}-card`}>
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground" data-testid={`${testIdPrefix}-${entry.testId}-label`}>{entry.label}</p>
              <p className={`mt-2 font-semibold text-foreground ${compact ? "text-lg" : "text-2xl"}`} data-testid={`${testIdPrefix}-${entry.testId}-value`}>
                {entry.used.toLocaleString("tr-TR")} / {formatUsageLimit(entry.limit)}
              </p>
            </div>
            <Badge variant="outline" className={entry.badgeClassName} data-testid={`${testIdPrefix}-${entry.testId}-percent`}>
              {entry.limit === null ? "Sınırsız" : `%${Math.round(entry.percent)}`}
            </Badge>
          </div>

          {entry.limit !== null ? (
            <div className="mt-4 space-y-2">
              <div className={`h-2.5 overflow-hidden rounded-full ${entry.trackClassName}`} data-testid={`${testIdPrefix}-${entry.testId}-progress-track`}>
                <div
                  className={`h-full rounded-full transition-[width] duration-500 ${entry.exceeded ? "bg-destructive" : entry.barClassName}`}
                  style={{ width: `${Math.min(entry.percent, 100)}%` }}
                  data-testid={`${testIdPrefix}-${entry.testId}-progress-bar`}
                />
              </div>
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span data-testid={`${testIdPrefix}-${entry.testId}-remaining`}>Kalan: {formatUsageLimit(entry.remaining)}</span>
                {entry.exceeded && <span className="font-medium text-destructive" data-testid={`${testIdPrefix}-${entry.testId}-exceeded`}>Limit aşıldı</span>}
              </div>
            </div>
          ) : (
            <p className="mt-4 text-xs text-muted-foreground" data-testid={`${testIdPrefix}-${entry.testId}-unlimited`}>
              Bu metrik mevcut planınızda sınırsız.
            </p>
          )}
        </div>
      ))}
    </div>
  );
};