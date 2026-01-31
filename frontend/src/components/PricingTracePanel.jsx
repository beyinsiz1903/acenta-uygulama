import React, { useEffect, useState } from "react";
import { api, apiErrorMessage } from "../lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { AlertCircle, Loader2 } from "lucide-react";

function ErrorBanner({ message, onRetry }) {
  if (!message) return null;
  return (
    <div className="mb-3 flex items-center justify-between gap-2 rounded-md border border-destructive/40 bg-destructive/5 px-3 py-2 text-[11px] text-destructive">
      <div className="flex items-center gap-2">
        <AlertCircle className="h-4 w-4" />
        <span>{message}</span>
      </div>
      {onRetry && (
        <Button type="button" size="xs" variant="outline" className="h-7 text-[11px]" onClick={onRetry}>
          Tekrar dene
        </Button>
      )}
    </div>
  );
}

export default function PricingTracePanel({ bookingId }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [data, setData] = useState(null);

  const load = async () => {
    if (!bookingId) return;
    setLoading(true);
    setError("");
    try {
      const res = await api.get(`/bookings/${bookingId}/pricing-trace`);
      setData(res.data || null);
    } catch (err) {
      const msg = apiErrorMessage(err) || "Fiyat iz kaydı yüklenemedi.";
      setError(msg);
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [bookingId]);

  const pricing = data?.pricing || null;
  const audit = data?.pricing_audit || null;

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium">Fiyat İz Kaydı (Pricing Trace)</h3>
        <Button
          type="button"
          size="xs"
          variant="outline"
          className="h-7 text-[11px]"
          onClick={load}
          disabled={loading}
        >
          {loading && <Loader2 className="h-3 w-3 mr-1 animate-spin" />}
          Yenile
        </Button>
      </div>

      <ErrorBanner message={error} onRetry={load} />

      {!loading && !pricing && !audit && (
        <p className="text-[11px] text-muted-foreground">
          Bu rezervasyon için fiyat kırılımı veya audit kaydı bulunmuyor.
        </p>
      )}

      {loading && (
        <p className="text-[11px] text-muted-foreground flex items-center gap-2">
          <Loader2 className="h-3 w-3 animate-spin" /> Fiyat iz kaydı yükleniyor...
        </p>
      )}

      {!loading && pricing && (
        <Card className="border border-muted">
          <CardHeader className="py-2 px-3">
            <CardTitle className="text-xs font-semibold">Pricing Özeti</CardTitle>
          </CardHeader>
          <CardContent className="px-3 pb-3 pt-2 text-[11px] grid grid-cols-2 gap-2">
            <div className="flex flex-col">
              <span className="text-[10px] text-muted-foreground uppercase tracking-wide">Base</span>
              <span className="font-mono">
                {pricing.base_amount} {pricing.currency}
              </span>
            </div>
            <div className="flex flex-col">
              <span className="text-[10px] text-muted-foreground uppercase tracking-wide">Final</span>
              <span className="font-mono">
                {pricing.final_amount} {pricing.currency}
              </span>
            </div>
            <div className="flex flex-col">
              <span className="text-[10px] text-muted-foreground uppercase tracking-wide">Komisyon</span>
              <span className="font-mono">{pricing.commission_amount ?? "0.00"}</span>
            </div>
            <div className="flex flex-col">
              <span className="text-[10px] text-muted-foreground uppercase tracking-wide">Margin</span>
              <span className="font-mono">{pricing.margin_amount ?? "0.00"}</span>
            </div>
          </CardContent>
        </Card>
      )}

      {!loading && pricing && Array.isArray(pricing.applied_rules) && pricing.applied_rules.length > 0 && (
        <Card className="border border-muted">
          <CardHeader className="py-2 px-3">
            <CardTitle className="text-xs font-semibold">Uygulanan Kurallar</CardTitle>
          </CardHeader>
          <CardContent className="px-3 pb-3 pt-2 text-[11px] space-y-1">
            {pricing.applied_rules.map((r, idx) => (
              <div key={r.rule_id || idx} className="flex items-center justify-between gap-2 border-b last:border-0 py-1">
                <div className="flex flex-col">
                  <span className="font-mono text-[10px] text-muted-foreground">
                    {r.rule_id || "(id-yok)"}
                  </span>
                  <span>
                    {r.rule_type} / {r.value}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  {typeof r.priority !== "undefined" && (
                    <Badge variant="outline" className="text-[10px]">
                      prio {r.priority}
                    </Badge>
                  )}
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {!loading && audit && (
        <Card className="border border-muted">
          <CardHeader className="py-2 px-3">
            <CardTitle className="text-xs font-semibold">Pricing Audit</CardTitle>
          </CardHeader>
          <CardContent className="px-3 pb-3 pt-2 text-[11px] space-y-2">
            <div className="grid grid-cols-2 gap-2">
              <div className="flex flex-col">
                <span className="text-[10px] text-muted-foreground uppercase tracking-wide">Action</span>
                <span>{audit.action}</span>
              </div>
              <div className="flex flex-col">
                <span className="text-[10px] text-muted-foreground uppercase tracking-wide">Created At</span>
                <span>{audit.created_at}</span>
              </div>
              <div className="flex flex-col">
                <span className="text-[10px] text-muted-foreground uppercase tracking-wide">Tenant</span>
                <span>{audit.meta?.tenant_id ?? "-"}</span>
              </div>
              <div className="flex flex-col">
                <span className="text-[10px] text-muted-foreground uppercase tracking-wide">Kurallar</span>
                <span>
                  {(audit.meta?.applied_rule_ids || []).join(", ") || "-"}
                </span>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
