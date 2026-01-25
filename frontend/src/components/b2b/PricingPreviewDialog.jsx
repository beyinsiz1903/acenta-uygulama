import React, { useEffect, useMemo, useState } from "react";
import { api, apiErrorMessage } from "../../lib/api";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "../ui/dialog";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Badge } from "../ui/badge";

const OCC_PRESETS = [
  { key: "1+0", adults: 1, children: 0, rooms: 1 },
  { key: "2+0", adults: 2, children: 0, rooms: 1 },
  { key: "2+1", adults: 2, children: 1, rooms: 1 },
  { key: "3+0", adults: 3, children: 0, rooms: 1 },
];

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

function safeNum(x) {
  const n = Number(x);
  return Number.isFinite(n) ? n : null;
}

function diffNights(checkin, checkout) {
  try {
    if (!checkin || !checkout) return null;
    const a = new Date(`${checkin}T00:00:00Z`).getTime();
    const b = new Date(`${checkout}T00:00:00Z`).getTime();
    const d = Math.round((b - a) / (1000 * 60 * 60 * 24));
    return d > 0 ? d : null;
  } catch {
    return null;
  }
}

async function copyToClipboard(text) {
  try {
    if (navigator?.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch (e) {
    // ignore, fallback below
  }

  try {
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.style.position = "fixed";
    ta.style.opacity = "0";
    document.body.appendChild(ta);
    ta.focus();
    ta.select();
    const ok = document.execCommand("copy");
    document.body.removeChild(ta);
    return !!ok;
  } catch (e) {
    return false;
  }
}

function normalizeResult(data) {
  const cur = data?.currency ?? data?.cur ?? "EUR";

  const breakdown = data?.breakdown ?? null;
  const breakdownObj =
    breakdown && !Array.isArray(breakdown) && typeof breakdown === "object" ? breakdown : null;
  const breakdownArr = Array.isArray(breakdown) ? breakdown : [];

  const total =
    safeNum(breakdownObj?.final_sell_price) ??
    safeNum(data?.final_sell_price) ??
    safeNum(data?.total) ??
    safeNum(data?.final_price) ??
    safeNum(data?.sell_amount) ??
    safeNum(data?.amount);

  const derivedNights = diffNights(data?.checkin, data?.checkout);
  const engineNights = safeNum(breakdownObj?.nights) ?? safeNum(data?.nights);

  const nights = engineNights ?? derivedNights;
  const nightsMismatch =
    derivedNights != null && engineNights != null && derivedNights !== engineNights;

  const basePrice = safeNum(breakdownObj?.base_price);
  const markupPercent = safeNum(breakdownObj?.markup_percent);
  const markupAmount = safeNum(breakdownObj?.markup_amount);
  const commissionRate = safeNum(breakdownObj?.commission_rate);
  const commissionAmount = safeNum(breakdownObj?.commission_amount);

  const perNight = total != null && nights != null && nights > 0 ? total / nights : null;

  return {
    currency: cur,
    total,
    nights,
    perNight,
    derivedNights,
    engineNights,
    nightsMismatch,
    breakdownObj,
    breakdownArr,
    ruleHits: Array.isArray(data?.rule_hits) ? data.rule_hits : [],
    notes: Array.isArray(data?.notes) ? data.notes : [],
    debug: data?.debug ?? null,
    raw: data ?? null,
    summary: {
      basePrice,
      markupPercent,
      markupAmount,
      commissionRate,
      commissionAmount,
      finalSellPrice: safeNum(breakdownObj?.final_sell_price) ?? total,
    },
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
  const [copyMsg, setCopyMsg] = useState("");
  const [selectedPreset, setSelectedPreset] = useState("2+0");

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
    setSelectedPreset("2+0");
    setResult(null);
    setErr("");
    setShowRaw(false);
    setShowDebug(false);
    setCopyMsg("");
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
            <div className="flex flex-col gap-2">
              {/* Occupancy presets */}
              <div className="flex flex-wrap gap-2 text-[11px] text-muted-foreground">
                <span>Hızlı occupancy:</span>
                {OCC_PRESETS.map((p) => (
                  <Button
                    key={p.key}
                    type="button"
                    size="xs"
                    variant={selectedPreset === p.key ? "secondary" : "outline"}
                    className="h-6 px-2 text-[11px]"
                    onClick={() => {
                      setCtx((s) =>
                        s
                          ? {
                              ...s,
                              adults: p.adults,
                              children: p.children,
                              rooms: p.rooms,
                            }
                          : s,
                      );
                      setSelectedPreset(p.key);
                    }}
                  >
                    {p.key}
                  </Button>
                ))}
              </div>

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
                onChange={(v) => {
                  setCtx((s) => ({ ...s, nights: v }));
                  setSelectedPreset(null);
                }}
              />
              <Field
                label="Oda"
                type="number"
                min={1}
                value={ctx.rooms}
                onChange={(v) => {
                  setCtx((s) => ({ ...s, rooms: v }));
                  setSelectedPreset(null);
                }}
              />
              <Field
                label="Yetişkin"
                type="number"
                min={1}
                value={ctx.adults}
                onChange={(v) => {
                  setCtx((s) => ({ ...s, adults: v }));
                  setSelectedPreset(null);
                }}
              />
              <Field
                label="Çocuk"
                type="number"
                min={0}
                value={ctx.children}
                onChange={(v) => {
                  setCtx((s) => ({ ...s, children: v }));
                  setSelectedPreset(null);
                }}
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
            <div className="flex flex-wrap items-center gap-2">
              <Button onClick={runPreview} disabled={loading}>
                {loading ? "Hesaplanıyor…" : "Önizleme Hesapla"}
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={async () => {
                  const payload = cleanPayload(ctx);
                  const ok = await copyToClipboard(JSON.stringify(payload, null, 2));
                  setCopyMsg(ok ? "Payload kopyalandı" : "Kopyalama başarısız");
                  window.setTimeout(() => setCopyMsg(""), 2000);
                }}
                disabled={!ctx?.product_id}
              >
                Payload&apos;ı Kopyala
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={async () => {
                  if (!normalized?.raw) return;
                  const ok = await copyToClipboard(JSON.stringify(normalized.raw, null, 2));
                  setCopyMsg(ok ? "Sonuç kopyalandı" : "Kopyalama başarısız");
                  window.setTimeout(() => setCopyMsg(""), 2000);
                }}
                disabled={!normalized?.raw}
              >
                Sonucu Kopyala

                {normalized.nightsMismatch && (
                  <div className="border border-amber-200 bg-amber-50 rounded-md p-2 text-xs">
                    <div className="font-semibold">Gece sayısı uyuşmazlığı</div>
                    <div className="text-muted-foreground">
                      Check-in/Check-out: <span className="font-mono">{normalized.derivedNights}</span> gece, engine: <span className="font-mono">{normalized.engineNights}</span> gece. Hesaplamada engine değeri baz alınmıştır.
                    </div>
                  </div>
                )}

              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowDebug((s) => !s)}
                disabled={!normalized?.debug}
              >
                {showDebug ? "Debug Gizle" : "Debug Göster"}
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowRaw((s) => !s)}
                disabled={!normalized?.raw}
              >
                {showRaw ? "JSON Gizle" : "JSON Göster"}
              </Button>
              {err ? <div className="text-xs text-red-600">{err}</div> : null}
              {copyMsg ? (
                <div className="text-xs text-muted-foreground">{copyMsg}</div>
              ) : null}
            </div>

            {/* Result */}
            {normalized ? (
              <div className="flex flex-col gap-3">
                {/* Request summary badges */}
                <div className="flex flex-wrap gap-2 text-[11px] text-muted-foreground">
                  <Badge variant="outline">
                    Check-in: {ctx.check_in}
                  </Badge>
                  <Badge variant="outline">
                    Check-out: {addDaysYmd(ctx.check_in, Number(ctx.nights) || 1)}
                  </Badge>
                  <Badge variant="outline">
                    {fmtInt(ctx.rooms)} oda · {fmtInt(ctx.adults)} yetişkin · {fmtInt(ctx.children)} çocuk
                  </Badge>
                </div>

                {/* Nights mismatch warning */}
                {normalized.nightsMismatch && (
                  <div className="border border-amber-200 bg-amber-50 rounded-md p-2 text-xs">
                    <div className="font-semibold">Gece sayısı uyuşmazlığı</div>
                    <div className="text-muted-foreground">
                      Check-in/Check-out: <span className="font-mono">{normalized.derivedNights}</span> gece, engine:{" "}
                      <span className="font-mono">{normalized.engineNights}</span> gece. Hesaplamada engine değeri baz alınmıştır.
                    </div>
                  </div>
                )}

                {/* Özet kartı */}
                <div className="border rounded-md p-3 space-y-1">
                  <div className="text-xs font-semibold mb-1">Özet</div>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-2 text-xs">
                    <div className="flex justify-between gap-2">
                      <span className="text-muted-foreground">Toplam satış</span>
                      <span className="font-mono font-medium">
                        {normalized.summary.finalSellPrice != null
                          ? `${fmtInt(normalized.summary.finalSellPrice)} ${normalized.currency}`
                          : "-"}
                      </span>
                    </div>
                    <div className="flex justify-between gap-2">
                      <span className="text-muted-foreground">Gece</span>
                      <span className="font-mono">
                        {normalized.nights != null ? fmtInt(normalized.nights) : "-"}
                      </span>
                    </div>
                    <div className="flex justify-between gap-2">
                      <span className="text-muted-foreground">Gece başı</span>
                      <span className="font-mono">
                        {normalized.perNight != null
                          ? `${fmtInt(normalized.perNight)} ${normalized.currency}`
                          : "-"}
                      </span>
                    </div>

                    <div className="flex justify-between gap-2">
                      <span className="text-muted-foreground">Base</span>
                      <span className="font-mono">
                        {normalized.summary.basePrice != null
                          ? `${fmtInt(normalized.summary.basePrice)} ${normalized.currency}`
                          : "-"}
                      </span>
                    </div>
                    <div className="flex justify-between gap-2">
                      <span className="text-muted-foreground">Markup</span>
                      <span className="font-mono">
                        {normalized.summary.markupPercent != null
                          ? `${fmtInt(normalized.summary.markupPercent)}%`
                          : "-"}
                        {" "}·{" "}
                        {normalized.summary.markupAmount != null
                          ? `${fmtInt(normalized.summary.markupAmount)} ${normalized.currency}`
                          : "-"}
                      </span>
                    </div>
                    <div className="flex justify-between gap-2">
                      <span className="text-muted-foreground">Komisyon</span>
                      <span className="font-mono">
                        {normalized.summary.commissionRate != null
                          ? `${fmtInt(normalized.summary.commissionRate)}%`
                          : "-"}
                        {" "}·{" "}
                        {normalized.summary.commissionAmount != null
                          ? `${fmtInt(normalized.summary.commissionAmount)} ${normalized.currency}`
                          : "-"}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Breakdown detayları (object) */}
                {normalized.breakdownObj && (
                  <div className="border rounded-md p-2">
                    <div className="text-xs font-medium mb-2">Detay</div>
                    <div className="space-y-1 text-xs">
                      {[
                        { k: "nights", label: "Gece", type: "int" },
                        { k: "base_price", label: "Baz Fiyat", type: "money" },
                        { k: "markup_percent", label: "Markup (%)", type: "pct" },
                        { k: "markup_amount", label: "Markup Tutarı", type: "money" },
                        { k: "commission_rate", label: "Komisyon Oranı (%)", type: "pct" },
                        { k: "commission_amount", label: "Komisyon Tutarı", type: "money" },
                        { k: "final_sell_price", label: "Final Satış", type: "money" },
                      ].map((row) => {
                        const v = normalized.breakdownObj[row.k];
                        let formatted = "-";
                        if (row.type === "int") formatted = fmtInt(v);
                        if (row.type === "money") formatted = fmtMoney(v, normalized.currency);
                        if (row.type === "pct") formatted = fmtPct(v);
                        return (
                          <div key={row.k} className="flex justify-between">
                            <span className="text-muted-foreground">{row.label}</span>
                            <span className="font-mono">{formatted}</span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* Legacy breakdown array */}
                {normalized.breakdownArr && normalized.breakdownArr.length > 0 && (
                  <div className="border rounded-md p-2">
                    <div className="text-xs font-medium mb-2">Breakdown (legacy)</div>
                    <div className="grid grid-cols-1 gap-1">
                      {normalized.breakdownArr.map((b, i) => (
                        <div key={i} className="text-xs flex justify-between gap-2">
                          <div className="truncate">{b.label ?? b.key ?? `item_${i}`}</div>
                          <div className="font-mono">
                            {b.amount ?? b.value ?? "-"} {b.currency ?? normalized.currency}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Uygulanan kurallar */}
                <div className="border rounded-md p-2">
                  <div className="text-xs font-medium mb-1">Uygulanan Kurallar</div>
                  {normalized.ruleHits.length === 0 ? (
                    <div className="text-[11px] text-muted-foreground">Kural uygulanmadı.</div>
                  ) : (
                    <ul className="space-y-1 text-[11px] text-muted-foreground">
                      {normalized.ruleHits.map((r, i) => {
                        const code = r.code || r.rule_id || "-";
                        return (
                          <li key={i} className="border rounded px-2 py-1">
                            <div className="font-mono text-[11px]">{code}</div>
                            {r.effect ? <div>{r.effect}</div> : null}
                            {r.priority != null ? (
                              <div className="text-[10px]">Öncelik: {fmtInt(r.priority)}</div>
                            ) : null}
                            {r.scope ? (
                              <div className="text-[10px] mt-1">
                                scope: {JSON.stringify(r.scope)}
                              </div>
                            ) : null}
                            {r.action ? (
                              <div className="text-[10px] mt-1">
                                action: {JSON.stringify(r.action)}
                              </div>
                            ) : null}
                          </li>
                        );
                      })}
                    </ul>
                  )}
                </div>

                {/* Notlar */}
                <div className="border rounded-md p-2">
                  <div className="text-xs font-medium mb-1">Notlar</div>
                  {normalized.notes.length === 0 ? (
                    <div className="text-[11px] text-muted-foreground">Not bulunmuyor.</div>
                  ) : (
                    <ul className="list-disc pl-5 space-y-1 text-[11px] text-muted-foreground">
                      {normalized.notes.map((n, i) => (
                        <li key={i}>{typeof n === "string" ? n : n.text ?? JSON.stringify(n)}</li>
                      ))}
                    </ul>
                  )}
                </div>

                {/* Debug & Raw JSON */}
                {showDebug && normalized.debug ? (
                  <pre className="text-xs bg-muted p-2 rounded-md overflow-auto max-h-64">
                    {JSON.stringify(normalized.debug, null, 2)}
                  </pre>
                ) : null}
                {showRaw && normalized.raw ? (
                  <pre className="text-xs bg-muted p-2 rounded-md overflow-auto max-h-64">
                    {JSON.stringify(normalized.raw, null, 2)}
                  </pre>
                ) : null}
              </div>
            ) : (
              <div className="text-xs text-muted-foreground">
                Henüz sonuç yok. Parametreleri ayarlayıp &quot;Önizleme Hesapla&quot;ya basın.
              </div>
            )}
          </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
