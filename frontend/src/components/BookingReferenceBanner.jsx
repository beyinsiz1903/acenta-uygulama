import React, { useState } from "react";
import { safeCopyText } from "../utils/copyText";

export function BookingReferenceBanner({
  bookingId,
  extranetUrl,
  shareSummary,
  testIdPrefix = "",
}) {
  const [copiedId, setCopiedId] = useState(false);
  const [copiedSummary, setCopiedSummary] = useState(false);

  const displayId = bookingId || "-";
  const copyId = bookingId || "";

  const tid = (x) => (testIdPrefix ? `${testIdPrefix}${x}` : x);

  return (
    <div
      className="rounded-xl border bg-muted/40 px-4 py-3 flex items-center justify-between gap-3"
      data-testid={tid("booking-id-banner")}
    >
      <div className="min-w-0">
        <div className="text-xs text-muted-foreground">Rezervasyon ID</div>
        <div className="truncate font-mono text-sm">{displayId}</div>
        {extranetUrl && (
          <div className="mt-1">
            <a
              href={extranetUrl}
              target="_blank"
              rel="noreferrer"
              className="text-xs underline text-muted-foreground"
              data-testid={tid("open-hotel-extranet")}
            >
              Otel panelinde aç
            </a>
          </div>
        )}
      </div>

      <div className="shrink-0 flex items-center gap-2">
        <button
          type="button"
          className="inline-flex items-center justify-center rounded-md border bg-background px-3 py-2 text-xs font-medium"
          data-testid={tid("booking-id-copy")}
          onClick={async () => {
            const ok = await safeCopyText(copyId);
            setCopiedId(ok);
            if (ok) {
              window.setTimeout(() => setCopiedId(false), 1200);
            }
          }}
          disabled={!copyId}
        >
          {copiedId ? "Kopyalandı" : "Kopyala"}
        </button>

        <button
          type="button"
          className="inline-flex items-center justify-center rounded-md border bg-background px-3 py-2 text-xs font-medium"
          data-testid={tid("booking-summary-copy")}
          onClick={async () => {
            const ok = await safeCopyText(shareSummary);
            setCopiedSummary(ok);
            if (ok) {
              window.setTimeout(() => setCopiedSummary(false), 1200);
            }
          }}
          disabled={!shareSummary}
          title="Paylaşılabilir özeti kopyala"
        >
          {copiedSummary ? "Kopyalandı" : "Özeti Kopyala"}
        </button>
      </div>
    </div>
  );
}
