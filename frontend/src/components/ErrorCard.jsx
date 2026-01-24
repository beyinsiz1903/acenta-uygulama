import React from "react";
import { AlertTriangle, Copy, RotateCw } from "lucide-react";
import { Button } from "./ui/button";

/**
 * Standard error card for 5xx / network / 520 style errors.
 *
 * props.details shape is produced by parseErrorDetails(err):
 *   { status, code, message, correlationId, isRetryable }
 */
export function ErrorCard({ details, onRetry, onCopy }) {
  if (!details) return null;

  const { status, code, message, correlationId, isRetryable } = details;

  // 4xx durumlar in bu bileen genelde gsterilmez; yine de isRetryable kontrolna brakyoruz
  if (!isRetryable) return null;

  const titleStatus = status || 0;
  const title = titleStatus
    ? `Sunucu hatas (${titleStatus})`
    : "A balants hatas";

  const technicalLabelParts = [];
  if (status) technicalLabelParts.push(`Status: ${status}`);
  if (code) technicalLabelParts.push(`Code: ${code}`);
  if (correlationId) technicalLabelParts.push(`Correlation: ${correlationId}`);
  const technicalText = technicalLabelParts.join(" | ");

  const handleCopy = () => {
    if (!navigator?.clipboard) return;
    const lines = [
      technicalText || "",
      details?.message || "",
      details?.path ? `Path: ${details.path}` : "",
    ].filter(Boolean);
    const text = lines.join("\n");
    if (!text) return;
    navigator.clipboard.writeText(text).catch(() => {});
    if (onCopy) onCopy();
  };

  return (
    <div className="rounded-md border border-destructive/40 bg-destructive/5 p-3 text-xs flex flex-col gap-2">
      <div className="flex items-start gap-2">
        <AlertTriangle className="h-4 w-4 text-destructive mt-0.5" />
        <div className="space-y-1">
          <div className="font-semibold text-destructive">{title}</div>
          <p className="text-[11px] text-muted-foreground leading-snug">
            estek ilenirken beklenmeyen bir hata olutu. Ltfen tekrar deneyin.
            Sorun devam ederse afag teknik kimlii destek ekibiyle paylan.
          </p>
          {message && (
            <p className="text-[11px] text-foreground/90 mt-1 break-words">{message}</p>
          )}
          {correlationId && (
            <p className="text-[11px] text-muted-foreground mt-1 break-words">
              <span className="font-medium">Teknik Kimlik:</span> {correlationId}
            </p>
          )}
        </div>
      </div>
      <div className="flex items-center justify-end gap-2 mt-1">
        <Button
          type="button"
          variant="outline"
          size="xs"
          className="h-7 gap-1 px-2 text-[11px]"
          onClick={handleCopy}
        >
          <Copy className="h-3 w-3" />
          Kopyala
        </Button>
        {onRetry && (
          <Button
            type="button"
            size="xs"
            className="h-7 gap-1 px-2 text-[11px]"
            onClick={onRetry}
          >
            <RotateCw className="h-3 w-3" />
            Tekrar dene
          </Button>
        )}
      </div>
    </div>
  );
}

export default ErrorCard;
