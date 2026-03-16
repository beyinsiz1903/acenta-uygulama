import React, { useState, useEffect } from "react";
import { Badge } from "../../../components/ui/badge";
import { Loader2, AlertCircle } from "lucide-react";
import { refundsApi } from "../api";

export function MiniRefundHistory({ bookingId }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!bookingId) { setItems([]); setError(""); return; }
    let cancelled = false;
    const run = async () => {
      try {
        setLoading(true);
        setError("");
        const resp = await refundsApi.bookingRefundHistory(bookingId);
        if (cancelled) return;
        setItems(resp?.items || []);
      } catch {
        if (cancelled) return;
        setError("Liste yuklenemedi");
        setItems([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    run();
    return () => { cancelled = true; };
  }, [bookingId]);

  if (!bookingId) return null;

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <Loader2 className="h-3 w-3 animate-spin" /><span>Yukleniyor...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center gap-2 text-xs text-destructive">
        <AlertCircle className="h-3 w-3" /><span>{error}</span>
      </div>
    );
  }

  if (!items.length) {
    return <div className="text-xs text-muted-foreground">Bu booking icin kapali refund yok.</div>;
  }

  return (
    <div className="space-y-1 text-xs" data-testid="mini-refund-history">
      {items.map((it) => (
        <div key={it.case_id} className="flex flex-wrap items-center justify-between gap-2 border-b last:border-0 py-1">
          <div className="flex flex-col gap-0.5">
            <div className="text-xs text-muted-foreground">
              {it.updated_at ? new Date(it.updated_at).toLocaleString() : "-"}
            </div>
            <div className="flex items-center gap-2">
              <Badge
                variant={it.decision === "approved" ? "default" : it.decision === "rejected" ? "destructive" : "secondary"}
                className="text-2xs px-1 py-0"
              >
                {it.decision || "-"}
              </Badge>
              {(() => {
                const amount = it.approved_amount ?? it.requested_amount ?? null;
                if (amount == null) return null;
                return <span>{Number(amount).toFixed(2)} {it.currency || ""}</span>;
              })()}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
