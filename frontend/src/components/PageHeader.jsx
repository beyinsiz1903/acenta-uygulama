import React from "react";
import { cn } from "@/lib/utils";

/**
 * Shared page header component for admin/agency/ops pages.
 *
 * Keeps title/subtitle hierarchy and optional right-aligned actions
 * consistent across the app.
 */
export function PageHeader({ title, subtitle, icon, actions, className }) {
  return (
    <div className={cn("flex items-start justify-between gap-4", className)}>
      <div className="flex items-start gap-3 min-w-0">
        {icon ? (
          <div className="mt-0.5 shrink-0 opacity-50">{icon}</div>
        ) : null}
        <div className="min-w-0">
          <h1 className="text-xl font-semibold tracking-tight text-foreground truncate">
            {title}
          </h1>
          {subtitle ? (
            <p className="mt-0.5 text-xs font-medium text-muted-foreground/70 break-words">
              {subtitle}
            </p>
          ) : null}
        </div>
      </div>
      {actions ? (
        <div className="flex items-center gap-2 shrink-0">{actions}</div>
      ) : null}
    </div>
  );
}

export default PageHeader;
