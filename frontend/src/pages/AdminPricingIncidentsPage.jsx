import React, { useState } from "react";
import { api, apiErrorMessage } from "../lib/api";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Card } from "../components/ui/card";

function FieldError({ text }) {
  if (!text) return null;
  return (
    <div className="mt-2 rounded-md border border-destructive/30 bg-destructive/5 p-2 text-xs text-destructive">
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

      <Card className="p-3 text-xs space-y-3">
        <div className="flex flex-col gap-2 md:flex-row md:items-end md:gap-3">
          <div className="flex-1 space-y-1">
            <label
              htmlFor="pricing-incident-booking-id"
              className="text-xs font-medium"
            >
              Booking ID
            </label>
            <Input
              id="pricing-incident-booking-id"
              data-testid="pricing-incident-booking-id"
              placeholder="Mongo _id veya string booking id"
              value={bookingId}
              onChange={(e) => setBookingId(e.target.value)}
              className="h-8 text-xs"
            />
          </div>
          <div className="flex-1 space-y-1">
            <label
              htmlFor="pricing-incident-quote-id"
              className="text-xs font-medium"
            >
              Quote ID (opsiyonel)
            </label>
            <Input
              id="pricing-incident-quote-id"
              data-testid="pricing-incident-quote-id"
              placeholder="B2B quote ObjectId"
              value={quoteId}
              onChange={(e) => setQuoteId(e.target.value)}
              className="h-8 text-xs"
            />
          </div>
          <div className="flex flex-col gap-2 md:w-[220px]">
            <div className="space-y-1">
              <label className="text-xs font-medium" htmlFor="pricing-incident-mode">
                Mode
              </label>
              <select
                id="pricing-incident-mode"
                data-testid="pricing-incident-mode"
                className="h-8 w-full rounded-md border bg-background px-2 text-xs"
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
              className="h-8 text-xs w-full"
              data-testid="pricing-incident-fetch"
              onClick={onFetch}
              disabled={loading}
            >
              {loading ? "Yükleniyor..." : "Fetch Debug Bundle"}
            </Button>
            <Button
              size="sm"
              variant="outline"
              className="h-8 text-xs w-full"
              data-testid="pricing-incident-copy"
              onClick={onCopy}
              disabled={!bundle}
            >
              Copy Bundle
            </Button>
            </div>
          </div>
        </div>

        <FieldError text={error} />
      </Card>

      <Card className="p-3 text-xs space-y-3" data-testid="pricing-incident-result">
        {!bundle ? (
          <div className="text-xs text-muted-foreground">
            Henüz debug bundle yok. Üstten Booking ID/Quote ID girip &quot;Fetch&quot; ile yükleyin.
          </div>
        ) : (
          <>
            <div
              className="flex flex-wrap items-center gap-2"
              data-testid="incident-summary"
            >
              <div className="font-semibold text-xs">Summary</div>
              {trace?.rule_name && (
                <span className="inline-flex items-center rounded-full border bg-muted px-2 py-0.5 text-2xs font-semibold">
                  {trace.rule_name}
                </span>
              )}
              {trace?.fallback && (
                <span className="inline-flex items-center rounded-full border border-amber-300 bg-amber-50 px-2 py-0.5 text-2xs font-semibold text-amber-900">
                  FALLBACK (DEFAULT_10)
                </span>
              )}
              {checksTotal > 0 && (
                <span className="inline-flex items-center rounded-full bg-emerald-50 px-2 py-0.5 text-2xs font-semibold text-emerald-900 border border-emerald-200">
                  {checksPass}/{checksTotal} checks OK
                </span>
              )}
              {bundle?.payments && (
                <span className="inline-flex items-center rounded-full bg-slate-50 px-2 py-0.5 text-2xs font-semibold text-foreground border border-slate-200">
                  Payment: {bundle.payments.status || "unknown"}
                </span>
              )}
            </div>

            <div className="grid gap-3 md:grid-cols-3">
              <div className="space-y-1">
                <div className="font-semibold text-xs">Booking</div>
                {!bundle.booking ? (
                  <div className="text-xs text-muted-foreground">Booking yok.</div>
                ) : (
                  <div className="space-y-1">
                    <div>
                      <span className="font-mono">{bundle.booking.booking_id}</span>
                    </div>
                    <div className="text-xs text-muted-foreground">
                      Status: {bundle.booking.status || "?"}
                    </div>
                    {amounts && (
                      <div className="text-xs text-muted-foreground">
                        Net: {amounts.net} {bundle.booking.currency} · Sell: {amounts.sell} {bundle.booking.currency}
                      </div>
                    )}
                  </div>
                )}
              </div>

              <div className="space-y-1">
                <div className="font-semibold text-xs">Quote</div>
                {!bundle.quote ? (
                  <div className="text-xs text-muted-foreground">Quote yok.</div>
                ) : (
                  <div className="space-y-1">
                    <div>
                      <span className="font-mono">{bundle.quote.quote_id}</span>
                    </div>
                    {bundle.quote.offers_preview && bundle.quote.offers_preview.length > 0 && (
                      <div className="text-xs text-muted-foreground">
                        Offer: {bundle.quote.offers_preview[0].net} → {bundle.quote.offers_preview[0].sell} {bundle.quote.offers_preview[0].currency}
                      </div>
                    )}
                  </div>
                )}
              </div>

              <div className="space-y-1">
                <div className="font-semibold text-xs">Rule</div>
                {!rule ? (
                  <div className="text-xs text-muted-foreground">Rule yok (DEFAULT_10 olabilir).</div>
                ) : (
                  <div className="space-y-1">
                    <div className="text-xs text-muted-foreground">
                      ID: <span className="font-mono">{rule.rule_id || rule.id}</span>
                    </div>
                    <div className="text-xs text-muted-foreground">
                      Priority: {rule.priority} · Status: {rule.status}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      Action: {rule.action?.type} {rule.action?.value}
                    </div>
                  </div>
                )}
              </div>
            </div>

            {bundle.explain && bundle.explain.length > 0 && (
              <div
                className="space-y-1"
                data-testid="incident-explain"
              >
                <div className="font-semibold text-xs">Explain</div>
                <ul className="list-disc pl-4 text-xs text-muted-foreground">
                  {bundle.explain.map((line, idx) => (
                    <li key={idx}>{line}</li>
                  ))}
                </ul>
              </div>
            )}

            {bundle.checks && (
              <div
                className="space-y-1"
                data-testid="incident-checks"
              >
                <div className="font-semibold text-xs">Checks</div>
                <div className="grid gap-1 md:grid-cols-2">
                  {Object.entries(bundle.checks).map(([key, value]) => (
                    <div
                      key={key}
                      className="flex items-center justify-between rounded border bg-muted/40 px-2 py-1 text-2xs"
                      data-testid={`check-${key}`}
                    >
                      <span className="text-2xs font-mono">{key}</span>
                      <span
                        className={
                          value === true
                            ? "text-emerald-700"
                            : value === false
                              ? "text-red-600"
                              : "text-muted-foreground"
                        }
                      >
                        {String(value)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Raw JSON */}
            {bundle && (
              <div
                className="space-y-1"
                data-testid="incident-raw-json"
              >
                <button
                  type="button"
                  className="text-xs font-semibold underline"
                  onClick={() => setShowRaw((v) => !v)}
                >
                  {showRaw ? "Hide raw JSON" : "Show raw JSON"}
                </button>
                {showRaw && (
                  <pre className="bg-muted/40 rounded p-2 text-2xs overflow-x-auto max-h-80">
                    {JSON.stringify(bundle, null, 2)}
                  </pre>
                )}
              </div>
            )}
          </>
        )}
      </Card>
    </div>
  );
}
