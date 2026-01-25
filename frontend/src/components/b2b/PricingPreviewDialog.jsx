import React, { useEffect, useMemo, useState } from "react";
import { api, apiErrorMessage } from "../../lib/api";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "../ui/dialog";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Badge } from "../ui/badge";

function toYmd(date) {
  // YYYY-MM-DD
  const d = date instanceof Date ? date : new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function addDaysYmd(ymd, days) {
  if (!ymd) return ymd;
  const parts = String(ymd).split("-");
  if (parts.length !== 3) return ymd;
  const [y, m, d] = parts.map((x) => Number(x));
  if (!Number.isFinite(y) || !Number.isFinite(m) || !Number.isFinite(d)) return ymd;
  const dt = new Date(Date.UTC(y, m - 1, d));
  dt.setUTCDate(dt.getUTCDate() + (Number.isFinite(days) ? days : 0));
  return toYmd(new Date(dt));
}

function fmtMoney(v, cur) {
  if (typeof v !== "number" || !Number.isFinite(v)) return "-";
  return `${v.toFixed(2)} ${cur}`;
}

function fmtPct(v) {
  if (typeof v !== "number" || !Number.isFinite(v)) return "-";
  return `%${v.toFixed(2)}`;
}

function fmtInt(v) {
  const n = Number(v);
  if (!Number.isFinite(n)) return "-";
  return String(Math.trunc(n));
}

function normalizeResult(data) {
  const cur = data?.currency ?? "EUR";
  const bd = data?.breakdown ?? null;

  const total =
    (bd && typeof bd.final_sell_price === "number" ? bd.final_sell_price : null) ??
    data?.total ??
    data?.final_price ??
    data?.sell_amount ??
    data?.amount ??
    null;

  return {
    currency: cur,
    total,
    checkin: data?.checkin ?? null,
    checkout: data?.checkout ?? null,
    occupancy: data?.occupancy ?? null,
    breakdown: bd && typeof bd === "object" && !Array.isArray(bd) ? bd : null,
    ruleHits: Array.isArray(data?.rule_hits) ? data.rule_hits : [],
    notes: Array.isArray(data?.notes) ? data.notes : [],
    debug: data?.debug && typeof data.debug === "object" ? data.debug : null,
    raw: data ?? null,
  };
}

function cleanPayload(ctx) {
  const product_id = ctx?.product_id ?? null;
  const partner_id = ctx?.partner_id ?? null;

  const checkin = ctx?.check_in ?? toYmd(new Date());
  const nightsRaw = Number(ctx?.nights);
  const nights = Number.isFinite(nightsRaw) && nightsRaw > 0 ? Math.trunc(nightsRaw) : 1;
  const checkout = addDaysYmd(checkin, nights);

  const adultsRaw = Number(ctx?.adults);
  const childrenRaw = Number(ctx?.children);
  const roomsRaw = Number(ctx?.rooms);

  const occupancy = {
    adults: Number.isFinite(adultsRaw) && adultsRaw > 0 ? Math.trunc(adultsRaw) : 2,
    children: Number.isFinite(childrenRaw) && childrenRaw >= 0 ? Math.trunc(childrenRaw) : 0,
    rooms: Number.isFinite(roomsRaw) && roomsRaw > 0 ? Math.trunc(roomsRaw) : 1,
  };

  const currency = ctx?.currency ?? "EUR";

  const payload = {
    product_id,
    partner_id,
    checkin,
    checkout,
    occupancy,
    currency,
    include_rules: true,
    include_breakdown: true,
  };

  if (!payload.partner_id) delete payload.partner_id;

  return payload;
}

function Field({ label, value, onChange, type = "text", min }) {
  return (
    <label className="flex flex-col gap-1">
      <div className="text-xs text-muted-foreground">{label}</div>
      <Input
        className="h-8 text-xs"
        type={type}
        min={min}
        value={value ?? ""}
        onChange={(e) => onChange(e.target.value)}
      />
    </label>
  );
}

export default function PricingPreviewDialog({ open, onOpenChange, initialContext }) {
  const [ctx, setCtx] = useState(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [result, setResult] = useState(null);
  const [showRaw, setShowRaw] = useState(false);
  const [showDebug, setShowDebug] = useState(false);

  useEffect(() => {
    if (!open) return;
    // Open olduğunda context’i initialize et
    if (!initialContext) {
      setCtx({
        check_in: toYmd(new Date()),
        nights: 1,
        rooms: 1,
        adults: 2,
        children: 0,
        currency: "EUR",
      });
      setResult(null);
      setErr("");
      return;
    }
    setCtx({
      check_in: initialContext.check_in ?? toYmd(new Date()),
      nights: initialContext.nights ?? 1,
      rooms: initialContext.rooms ?? 1,
      adults: initialContext.adults ?? 2,
      children: initialContext.children ?? 0,
      currency: initialContext.currency ?? "EUR",
      product_id: initialContext.product_id,
      partner_id: initialContext.partner_id ?? null,
      agency_id: initialContext.agency_id ?? null,
      channel_id: initialContext.channel_id ?? null,
    });
    setResult(null);
    setErr("");
    setShowRaw(false);
  }, [open, initialContext]);

  const normalized = useMemo(() => (result ? normalizeResult(result) : null), [result]);

  const runPreview = async () => {
    if (!ctx?.product_id) {
      setErr("Ürün seçilmeden önizleme yapılamaz.");
      return;
    }
    setLoading(true);
    setErr("");
    setResult(null);
    try {
      const payload = cleanPayload(ctx);

      // IMPORTANT: endpoint path burada tek kaynak.
      // Axios client zaten baseURL'e "/api" prefix'ini ekliyor.
      const res = await api.post("/admin/b2b/pricing/preview", payload);

      setResult(res.data ?? null);
    } catch (e) {
      setErr(apiErrorMessage(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl">
        <DialogHeader>
          <DialogTitle>Fiyat Önizleme</DialogTitle>
        </DialogHeader>

        {!ctx ? (
          <div className="text-sm text-muted-foreground">Yükleniyor…</div>
        ) : (
          <div className="flex flex-col gap-4">
            {/* Context form */}
            <div className="grid grid-cols-2 md:grid-cols-6 gap-2">
              <Field
                label="Check-in"
                type="date"
                value={ctx.check_in}
                onChange={(v) => setCtx((s) => ({ ...s, check_in: v }))}
              />
              <Field
                label="Gece"
                type="number"
                min={1}
                value={ctx.nights}
                onChange={(v) => setCtx((s) => ({ ...s, nights: v }))}
              />
              <Field
                label="Oda"
                type="number"
                min={1}
                value={ctx.rooms}
                onChange={(v) => setCtx((s) => ({ ...s, rooms: v }))}
              />
              <Field
                label="Yetişkin"
                type="number"
                min={1}
                value={ctx.adults}
                onChange={(v) => setCtx((s) => ({ ...s, adults: v }))}
              />
              <Field
                label="Çocuk"
                type="number"
                min={0}
                value={ctx.children}
                onChange={(v) => setCtx((s) => ({ ...s, children: v }))}
              />
              <Field
                label="Para birimi"
                value={ctx.currency}
                onChange={(v) => setCtx((s) => ({ ...s, currency: v }))}
              />
            </div>

            {/* Readonly ids */}
            <div className="flex flex-wrap gap-2 text-xs">
              {ctx.product_id ? (
                <Badge variant="outline">product_id: {ctx.product_id}</Badge>
              ) : (
                <Badge variant="destructive">product_id yok</Badge>
              )}
              {ctx.partner_id ? <Badge variant="outline">partner_id: {ctx.partner_id}</Badge> : null}
              {ctx.agency_id ? <Badge variant="outline">agency_id: {ctx.agency_id}</Badge> : null}
              {ctx.channel_id ? <Badge variant="outline">channel_id: {ctx.channel_id}</Badge> : null}
            </div>

            {/* Actions */}
            <div className="flex items-center gap-2">
              <Button onClick={runPreview} disabled={loading}>
                {loading ? "Hesaplanıyor…" : "Önizleme Hesapla"}
              </Button>
              <Button variant="outline" onClick={() => setShowRaw((s) => !s)} disabled={!result}>
                {showRaw ? "JSON Gizle" : "JSON Göster"}
              </Button>
              {err ? <div className="text-xs text-red-600">{err}</div> : null}
            </div>

            {/* Result */}
            {normalized ? (
              <div className="flex flex-col gap-3">
                <div className="flex items-center gap-2">
                  <div className="text-sm font-medium">Toplam:</div>
                  <div className="font-mono text-sm">
                    {normalized.total != null ? normalized.total : "-"} {normalized.currency}
                  </div>
                </div>

                {normalized.breakdown.length ? (
                  <div className="border rounded-md p-2">
                    <div className="text-xs font-medium mb-2">Breakdown</div>
                    <div className="grid grid-cols-1 gap-1">
                      {normalized.breakdown.map((b, i) => (
                        <div key={i} className="text-xs flex justify-between gap-2">
                          <div className="truncate">{b.label ?? b.key ?? `item_${i}`}</div>
                          <div className="font-mono">
                            {b.amount ?? b.value ?? "-"} {b.currency ?? normalized.currency}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : null}

                {normalized.ruleHits.length ? (
                  <div className="border rounded-md p-2">
                    <div className="text-xs font-medium mb-2">Rule Hits</div>
                    <ul className="list-disc pl-5">
                      {normalized.ruleHits.map((r, i) => (
                        <li key={i} className="text-xs">
                          {typeof r === "string" ? r : r.code ?? r.name ?? JSON.stringify(r)}
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}

                {normalized.notes.length ? (
                  <div className="border rounded-md p-2">
                    <div className="text-xs font-medium mb-2">Notlar</div>
                    <ul className="list-disc pl-5">
                      {normalized.notes.map((n, i) => (
                        <li key={i} className="text-xs">
                          {typeof n === "string" ? n : n.text ?? JSON.stringify(n)}
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}

                {showRaw ? (
                  <pre className="text-xs bg-muted p-2 rounded-md overflow-auto max-h-72">
                    {JSON.stringify(normalized.raw, null, 2)}
                  </pre>
                ) : null}
              </div>
            ) : (
              <div className="text-xs text-muted-foreground">
                Henüz sonuç yok. Parametreleri ayarlayıp “Önizleme Hesapla”ya basın.
              </div>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
