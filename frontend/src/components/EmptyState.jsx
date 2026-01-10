import React from "react";
import { cn } from "@/lib/utils";

/**
 * Generic empty state component used when an endpoint returns 200 + [] / 0 items.
 */
export function EmptyState({ title, description, icon, action, className }) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center text-center gap-3 py-10 px-4",
        className,
      )}
    >
      {icon ? (
        <div className="h-16 w-16 rounded-full bg-muted flex items-center justify-center">
          {icon}
        </div>
      ) : null}
      <div className="max-w-md space-y-1">
        <p className="font-semibold text-foreground">{title}</p>
        {description ? (
          <p className="text-sm text-muted-foreground">{description}</p>
        ) : null}
      </div>
      {action ? <div className="mt-1">{action}</div> : null}
    </div>
  );
}

export default EmptyState;
