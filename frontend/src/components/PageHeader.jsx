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
          <div className="mt-1 shrink-0">{icon}</div>
        ) : null}
        <div className="min-w-0">
          <h1 className="text-2xl md:text-3xl font-bold text-foreground truncate">
            {title}
          </h1>
          {subtitle ? (
            <p className="mt-1 text-sm text-muted-foreground break-words">
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
