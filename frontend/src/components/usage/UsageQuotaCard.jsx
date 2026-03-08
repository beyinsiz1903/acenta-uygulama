import React from "react";
import { Link } from "react-router-dom";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import { formatUsageLimit } from "../../lib/usage";

const WARNING_LABELS = {
  normal: "Normal",
  warning: "Yaklaşıyor",
  critical: "Kritik",
  limit_reached: "Limit doldu",
};

export const UsageQuotaCard = ({ entry, compact = false, showCta = false, testIdPrefix = "usage-card" }) => {
  if (!entry) return null;

  return (
    <div className="rounded-2xl border bg-card/80 p-4 shadow-sm" data-testid={`${testIdPrefix}-${entry.testId}-card`}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground" data-testid={`${testIdPrefix}-${entry.testId}-label`}>{entry.label}</p>
          <p className={`mt-2 font-semibold text-foreground ${compact ? "text-lg" : "text-2xl"}`} data-testid={`${testIdPrefix}-${entry.testId}-value`}>
            {entry.used.toLocaleString("tr-TR")} / {formatUsageLimit(entry.limit)}
          </p>
        </div>
        <div className="flex flex-col items-end gap-2">
          <Badge variant="outline" className={entry.badgeClassName} data-testid={`${testIdPrefix}-${entry.testId}-percent`}>
            {entry.limit === null ? "Sınırsız" : `%${Math.round(entry.percent)}`}
          </Badge>
          <Badge variant="outline" className={entry.warningBadgeClassName} data-testid={`${testIdPrefix}-${entry.testId}-warning-level`}>
            {WARNING_LABELS[entry.warningLevel] || "Normal"}
          </Badge>
        </div>
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
          {entry.warningMessage && (
            <p className={`text-xs leading-relaxed ${entry.warningMessageClassName}`} data-testid={`${testIdPrefix}-${entry.testId}-message`}>
              {entry.warningMessage}
            </p>
          )}
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span data-testid={`${testIdPrefix}-${entry.testId}-remaining`}>Kalan: {formatUsageLimit(entry.remaining)}</span>
          </div>
        </div>
      ) : (
        <p className="mt-4 text-xs text-muted-foreground" data-testid={`${testIdPrefix}-${entry.testId}-unlimited`}>
          Bu metrik mevcut planınızda sınırsız.
        </p>
      )}

      {showCta && entry.upgradeRecommended && (
        <Button asChild size="sm" className="mt-4 w-full" data-testid={`${testIdPrefix}-${entry.testId}-cta-button`}>
          <Link to={entry.ctaHref}>{entry.ctaLabel}</Link>
        </Button>
      )}
    </div>
  );
};