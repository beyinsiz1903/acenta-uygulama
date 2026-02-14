import React from "react";
import { AlertCircle } from "lucide-react";

import { cn } from "@/lib/utils";
import { Button } from "./ui/button";

/**
 * Shared error state surface for API / data load errors.
 *
 * - Used both in admin/ops and agency views.
 * - For ops pages, errorCode / requestId can be surfaced for support.
 */
export function ErrorState({
  title = "Bir hata oluştu",
  description,
  onRetry,
  errorCode,
  requestId,
  compact = false,
  className,
}) {
  return (
    <div
      className={cn(
        "rounded-2xl border border-destructive/50 bg-destructive/5 px-4 py-3 flex flex-col items-center text-center gap-3",
        compact && "rounded-xl px-3 py-2",
        className,
      )}
    >
      <div className="flex items-center gap-2 text-destructive">
        <AlertCircle className="h-5 w-5" />
        <span className="font-semibold text-sm">{title}</span>
      </div>
      {description ? (
        <p className="text-sm text-muted-foreground max-w-md">{description}</p>
      ) : null}
      {(errorCode || requestId) && (
        <div className="text-xs text-muted-foreground space-x-2">
          {errorCode && (
            <span>
              Kod: <span className="font-mono">{errorCode}</span>
            </span>
          )}
          {requestId && (
            <span>
              Req: <span className="font-mono">{requestId}</span>
            </span>
          )}
        </div>
      )}
      {onRetry ? (
        <Button size="sm" variant="outline" onClick={onRetry} className="mt-1">
          Tekrar dene
        </Button>
      ) : null}
    </div>
  );
}

export default ErrorState;
