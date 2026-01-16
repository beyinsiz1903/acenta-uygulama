import React, { useState } from "react";
import { api, apiErrorMessage } from "../lib/api";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Card } from "../components/ui/card";

function FieldError({ text }) {
  if (!text) return null;
  return (
    <div className="mt-2 rounded-md border border-destructive/30 bg-destructive/5 p-2 text-[11px] text-destructive">
      {text}
    </div>
  );
}

export default function AdminPricingIncidentsPage() {
  const [bookingId, setBookingId] = useState("");
  const [quoteId, setQuoteId] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [bundle, setBundle] = useState(null);
  const [mode, setMode] = useState("auto");
  const [showRaw, setShowRaw] = useState(false);

  const onFetch = async () => {
    setError("");
    setBundle(null);
    if (!bookingId && !quoteId) {
      setError("Lütfen en az bir Booking ID veya Quote ID girin.");
      return;
    }
    setLoading(true);
    try {
      const res = await api.get("/admin/pricing/incidents/debug-bundle", {
        params: {
          booking_id: bookingId || undefined,
          quote_id: quoteId || undefined,
          mode,
        },
      });
      setBundle(res.data || null);
      setShowRaw(false);
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setLoading(false);
    }
  };

  const onCopy = async () => {
    if (!bundle) return;
    try {
      await navigator.clipboard.writeText(JSON.stringify(bundle, null, 2));
    } catch (e) {
      // ignore
    }
  };

  const trace = bundle?.pricing?.trace || bundle?.booking?.applied_rules?.trace || bundle?.quote?.pricing_trace || {};
  const rule = bundle?.rule || null;
  const amounts = bundle?.pricing?.amounts || bundle?.booking?.amounts || null;
  const checks = bundle?.checks || {};

  const checksEntries = Object.entries(checks || {});
  const checksTotal = checksEntries.length;
  const checksPass = checksEntries.filter(([, v]) => v === true).length;

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold">Pricing Incidents Playbook</h1>
        <p className="text-xs text-muted-foreground">
          Booking / quote bazlı fiyatlama incident&apos;larını tek JSON bundle ile inceleyin.
        </p>
      </div>

      <Card className="p-3 text-[11px] space-y-3">
        <div className="flex flex-col gap-2 md:flex-row md:items-end md:gap-3">
          <div className="flex-1 space-y-1">
            <label
              htmlFor="pricing-incident-booking-id"
              className="text-[11px] font-medium"
            >
              Booking ID
            </label>
            <Input
              id="pricing-incident-booking-id"
              data-testid="pricing-incident-booking-id"
              placeholder="Mongo _id veya string booking id"
              value={bookingId}
              onChange={(e) => setBookingId(e.target.value)}
              className="h-8 text-[11px]"
            />
          </div>
          <div className="flex-1 space-y-1">
            <label
              htmlFor="pricing-incident-quote-id"
              className="text-[11px] font-medium"
            >
              Quote ID (opsiyonel)
            </label>
            <Input
              id="pricing-incident-quote-id"
              data-testid="pricing-incident-quote-id"
              placeholder="B2B quote ObjectId"
              value={quoteId}
              onChange={(e) => setQuoteId(e.target.value)}
              className="h-8 text-[11px]"
            />
          </div>
          <div className="flex flex-col gap-2 md:w-[220px]">
            <div className="space-y-1">
              <label className="text-[11px] font-medium" htmlFor="pricing-incident-mode">
                Mode
              </label>
              <select
                id="pricing-incident-mode"
                data-testid="pricing-incident-mode"
                className="h-8 w-full rounded-md border bg-background px-2 text-[11px]"
                value={mode}
                onChange={(e) => setMode(e.target.value)}
              >
                <option value="auto">auto</option>
                <option value="booking">booking</option>
                <option value="quote">quote</option>
              </select>
            </div>
            <div className="flex flex-row gap-2 md:flex-col">
              <Button
              size="sm"
              className="h-8 text-[11px] w-full"
              data-testid="pricing-incident-fetch"
              onClick={onFetch}
              disabled={loading}
            >
              {loading ? "Yükleniyor..." : "Fetch Debug Bundle"}
            </Button>
            <Button
              size="sm"
              variant="outline"
              className="h-8 text-[11px] w-full"
              data-testid="pricing-incident-copy"
              onClick={onCopy}
              disabled={!bundle}
            >
              Copy Bundle
            </Button>
          </div>
        </div>

        <FieldError text={error} />
      </Card>

      <Card className="p-3 text-[11px] space-y-3" data-testid="pricing-incident-result">
        {!bundle ? (
          <div className="text-[11px] text-muted-foreground">
            Henüz debug bundle yok. Üstten Booking ID/Quote ID girip &quot;Fetch&quot; ile yükleyin.
          </div>
        ) : (
          <>
            <div className="flex flex-wrap items-center gap-2">
              <div className="font-semibold text-xs">Summary</div>
              {trace?.rule_name && (
                <span className="inline-flex items-center rounded-full border bg-muted px-2 py-0.5 text-[10px] font-semibold">
                  {trace.rule_name}
                </span>
              )}
              {trace?.fallback && (
                <span className="inline-flex items-center rounded-full border border-amber-300 bg-amber-50 px-2 py-0.5 text-[10px] font-semibold text-amber-900">
                  FALLBACK (DEFAULT_10)
                </span>
              )}
            </div>

            <div className="grid gap-3 md:grid-cols-3">
              <div className="space-y-1">
                <div className="font-semibold text-[11px]">Booking</div>
                {!bundle.booking ? (
                  <div className="text-[11px] text-muted-foreground">Booking yok.</div>
                ) : (
                  <div className="space-y-1">
                    <div>
                      <span className="font-mono">{bundle.booking.booking_id}</span>
                    </div>
                    <div className="text-[11px] text-muted-foreground">
                      Status: {bundle.booking.status || "?"}
                    </div>
                    {amounts && (
                      <div className="text-[11px] text-muted-foreground">
                        Net: {amounts.net} {bundle.booking.currency} · Sell: {amounts.sell} {bundle.booking.currency}
                      </div>
                    )}
                  </div>
                )}
              </div>

              <div className="space-y-1">
                <div className="font-semibold text-[11px]">Quote</div>
                {!bundle.quote ? (
                  <div className="text-[11px] text-muted-foreground">Quote yok.</div>
                ) : (
                  <div className="space-y-1">
                    <div>
                      <span className="font-mono">{bundle.quote.quote_id}</span>
                    </div>
                    {bundle.quote.offers_preview && bundle.quote.offers_preview.length > 0 && (
                      <div className="text-[11px] text-muted-foreground">
                        Offer: {bundle.quote.offers_preview[0].net} → {bundle.quote.offers_preview[0].sell} {bundle.quote.offers_preview[0].currency}
                      </div>
                    )}
                  </div>
                )}
              </div>

              <div className="space-y-1">
                <div className="font-semibold text-[11px]">Rule</div>
                {!rule ? (
                  <div className="text-[11px] text-muted-foreground">Rule yok (DEFAULT_10 olabilir).</div>
                ) : (
                  <div className="space-y-1">
                    <div className="text-[11px] text-muted-foreground">
                      ID: <span className="font-mono">{rule.rule_id || rule.id}</span>
                    </div>
                    <div className="text-[11px] text-muted-foreground">
                      Priority: {rule.priority} · Status: {rule.status}
                    </div>
                    <div className="text-[11px] text-muted-foreground">
                      Action: {rule.action?.type} {rule.action?.value}
                    </div>
                  </div>
                )}
              </div>
            </div>

            {bundle.explain && bundle.explain.length > 0 && (
              <div className="space-y-1">
                <div className="font-semibold text-[11px]">Explain</div>
                <ul className="list-disc pl-4 text-[11px] text-muted-foreground">
                  {bundle.explain.map((line, idx) => (
                    <li key={idx}>{line}</li>
                  ))}
                </ul>
              </div>
            )}

            {bundle.checks && (
              <div className="space-y-1">
                <div className="font-semibold text-[11px]">Checks</div>
                <pre className="bg-muted/40 rounded p-2 text-[10px] overflow-x-auto">
                  {JSON.stringify(bundle.checks, null, 2)}
                </pre>
              </div>
            )}
          </>
        )}
      </Card>
    </div>
  );
}
