import React from "react";

export function StatCard({ title, value, subtitle, testId }) {
  return (
    <div
      className="rounded-xl border bg-card p-5"
      data-testid={testId}
    >
      <div className="text-sm font-medium text-muted-foreground">{title}</div>
      <div className="mt-2 text-3xl font-bold">{value}</div>
      {subtitle ? (
        <div className="mt-1 text-xs text-muted-foreground">{subtitle}</div>
      ) : null}
    </div>
  );
}
