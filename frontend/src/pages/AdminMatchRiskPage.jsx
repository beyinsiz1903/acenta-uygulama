import React, { useEffect, useMemo, useState } from "react";
import { AlertTriangle, Check, Copy } from "lucide-react";
import { api, apiErrorMessage } from "../lib/api";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "../components/ui/tooltip";

function todayIsoDate() {
  return new Date().toISOString().slice(0, 10);
}

function addDays(base, delta) {
  const d = new Date(base);
  d.setDate(d.getDate() + delta);
  return d.toISOString().slice(0, 10);
}

function formatPercent(v) {
  if (v == null || Number.isNaN(Number(v))) return "—";
  const n = Number(v) * 100;
  return `${n.toFixed(1)}%`;
}

function riskBadge(level, label) {
  const base = "inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium";
  if (level === "high") {
    return (
      <span className={`${base} bg-red-500/10 text-red-700`}>{label}</span>
    );
  }
  if (level === "medium") {
    return (
      <span className={`${base} bg-amber-500/10 text-amber-700`}>{label}</span>
    );
  }
  return (
    <span className={`${base} bg-emerald-500/10 text-emerald-700`}>{label}</span>
  );
}

function deriveRiskLevel(rate) {
  const n = Number(rate || 0);
  if (n >= 0.3) return "high";
  if (n >= 0.1) return "medium";
  return "low";
}

export default function AdminMatchRiskPage() {
  const today = todayIsoDate();
  const defaultFrom = addDays(today, -30);

  const [from, setFrom] = useState(defaultFrom);
  const [to, setTo] = useState(today);
  const [groupBy, setGroupBy] = useState("pair");
  const [minMatches, setMinMatches] = useState(5);

  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  const [drillOpen, setDrillOpen] = useState(false);
  const [drillLoading, setDrillLoading] = useState(false);
  const [drillErr, setDrillErr] = useState("");
  const [drillItems, setDrillItems] = useState([]);
  const [activeRow, setActiveRow] = useState(null);

  const [view, setView] = useState("main"); // future: can add charts
  const [copied, setCopied] = useState("");
  const [hotelMap, setHotelMap] = useState({});
  const [hotelMapLoading, setHotelMapLoading] = useState(false);
  const [onlyHighRisk, setOnlyHighRisk] = useState(false);

  const periodLabel = useMemo(() => {
    if (!from || !to) return "Tarih aralığı seçilmedi";
    return `${from} → ${to}`;
  }, [from, to]);

  const visibleItems = useMemo(() => {
    const rows = Array.isArray(items) ? items : [];
    if (!onlyHighRisk) return rows;
    return rows.filter((r) => Number(r?.not_arrived_rate || 0) >= 0.5);
  }, [items, onlyHighRisk]);

  async function loadHotelsMap() {
    setHotelMapLoading(true);
    try {
      const resp = await api.get("/admin/hotels");
      const raw = resp.data || [];
      const map = {};
      for (const h of raw) {
        const id = String(h.id || h._id || "");
        if (!id) continue;
        map[id] = h.name || h.title || h.hotel_name || id;
      }
      setHotelMap(map);
    } catch (e) {
      // mapping yoksa id göstererek devam edeceğiz
      setHotelMap({});
    } finally {
      setHotelMapLoading(false);
    }
  }

  function hotelLabel(id) {
    const s = String(id || "");
    if (!s) return "?";
    return hotelMap[s] || s;
  }

  async function loadSummary() {
    if (!from || !to) return;

    setLoading(true);
    setErr("");
    try {
      const params = new URLSearchParams();
      params.set("from", from);
      params.set("to", to);
      params.set("group_by", groupBy);
      if (minMatches) {
        params.set("min_matches", String(minMatches));
      }

      const resp = await api.get(`/reports/match-risk?${params.toString()}`);
      setItems(resp.data?.items || []);
    } catch (e) {
      setErr(apiErrorMessage(e));
    } finally {
      setLoading(false);
    }
  }

  async function openDrilldown(row) {
    if (!row) return;
    setActiveRow(row);
    setDrillOpen(true);
    setDrillLoading(true);
    setDrillErr("");
    setDrillItems([]);

    try {
      const params = new URLSearchParams();
      params.set("from", from);
      params.set("to", to);
      params.set("limit", "50");

      if (groupBy === "pair") {
        if (row.from_hotel_id) params.set("from_hotel_id", row.from_hotel_id);
        if (row.to_hotel_id) params.set("to_hotel_id", row.to_hotel_id);
      } else if (groupBy === "to_hotel") {
        if (row.to_hotel_id) params.set("to_hotel_id", row.to_hotel_id);
      } else if (groupBy === "from_hotel") {
        if (row.from_hotel_id) params.set("from_hotel_id", row.from_hotel_id);
      }

      const resp = await api.get(`/reports/match-risk/drilldown?${params.toString()}`);
      setDrillItems(resp.data?.items || []);
    } catch (e) {
      setDrillErr(apiErrorMessage(e));
    } finally {
      setDrillLoading(false);
    }
  }

  async function copyText(value) {
    const str = String(value || "");
    if (!str) return;
    try {
      await navigator.clipboard.writeText(str);
      setCopied(str);
      window.setTimeout(() => setCopied(""), 1200);
    } catch (e) {
      try {
        const el = document.createElement("textarea");
        el.value = str;
        el.setAttribute("readonly", "");
        el.style.position = "fixed";
        el.style.top = "-1000px";
        el.style.left = "-1000px";
        document.body.appendChild(el);
        el.select();
        document.execCommand("copy");
        document.body.removeChild(el);
        setCopied(str);
        window.setTimeout(() => setCopied(""), 1200);
      } catch {
        // ignore
      }
    }
  }

  useEffect(() => {
    void loadHotelsMap();
    void loadSummary();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <TooltipProvider>
      <div className="p-4 md:p-6" data-testid="admin-match-risk-page">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
        <div>
          <div className="text-xl font-semibold">Match Risk Dashboard</div>
          <div className="text-sm text-muted-foreground">
            Admin / Super Admin için match outcome istatistikleri
          </div>
          <div className="mt-1 text-[11px] text-muted-foreground max-w-xl">
            Outcome sinyalleri yalnızca operasyonel istatistiktir; ücretlendirmeyi etkilemez.
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            className={
              view === "main"
                ? "h-8 rounded-md border bg-primary text-primary-foreground px-3 text-xs font-medium"
                : "h-8 rounded-md border bg-background px-3 text-xs"
            }
            onClick={() => setView("main")}
            data-testid="match-risk-view-main"
          >
            Liste
          </button>
        </div>
      </div>

      <div className="mt-4 rounded-xl border bg-card p-4" data-testid="match-risk-filters">
        <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-3">
          <div className="flex flex-wrap items-center gap-3 text-xs">
            <div className="flex items-center gap-1">
              <span className="text-muted-foreground">Tarih:</span>
              <input
                type="date"
                className="h-8 rounded-md border bg-background px-2 text-xs"
                value={from}
                onChange={(e) => setFrom(e.target.value)}
                data-testid="match-risk-from"
              />
              <span>-</span>
              <input
                type="date"
            <label className="inline-flex items-center gap-2 text-xs">
              <input
                type="checkbox"
                checked={onlyHighRisk}
                onChange={(e) => setOnlyHighRisk(e.target.checked)}
                data-testid="match-risk-only-high-toggle"
              />
              Sadece yüksek risk (≥ %50)
            </label>

                className="h-8 rounded-md border bg-background px-2 text-xs"
                value={to}
                onChange={(e) => setTo(e.target.value)}
                data-testid="match-risk-to"
              />
            </div>

            <div className="flex items-center gap-1">
              <span className="text-muted-foreground">Gruplama:</span>
              <select
                className="h-8 rounded-md border bg-background px-2 text-xs"
                value={groupBy}
                onChange={(e) => setGroupBy(e.target.value)}
        <div className="mt-2 flex flex-wrap items-center justify-between gap-2 text-[11px] text-muted-foreground" data-testid="match-risk-period-label">
          <span>Dönem: {periodLabel}</span>
          {hotelMapLoading ? (
            <span>Hotel isimleri yükleniyor...</span>
          ) : Object.keys(hotelMap).length > 0 ? (
            <span>
              Hotel isimleri: <span className="font-medium">açık</span>
            </span>
          ) : (
            <span>
              Hotel isimleri: <span className="font-medium">ID</span> (isim verisi yok)
            </span>
          )}
        </div>

                data-testid="match-risk-group-by"
              >
                <option value="pair">Çift (from → to)</option>
                <option value="to_hotel">To Hotel</option>
                <option value="from_hotel">From Hotel</option>
              </select>
            </div>

            <div className="flex items-center gap-1">
              <span className="text-muted-foreground">Min match:</span>
              <input
                type="number"
                min="1"
                className="h-8 w-20 rounded-md border bg-background px-2 text-xs"
                value={minMatches}
                onChange={(e) => setMinMatches(Number(e.target.value) || 0)}
                data-testid="match-risk-min-matches"
              />
            </div>
          </div>
        {hotelMapLoading ? (
          <div className="mt-1 text-[11px] text-muted-foreground">
            Hotel isimleri yükleniyor...
          </div>
        ) : Object.keys(hotelMap).length > 0 ? (
          <div className="mt-1 text-[11px] text-muted-foreground">
            Hotel isimleri: <span className="font-medium">açık</span>
          </div>
        ) : (
          <div className="mt-1 text-[11px] text-muted-foreground">
            Hotel isimleri: <span className="font-medium">ID</span> (isim verisi yok)
          </div>
        )}


          <div className="flex items-center gap-2">
            <button
              type="button"
              className="h-8 rounded-md border bg-background px-3 text-xs"
              onClick={() => {
                setFrom(defaultFrom);
                setTo(today);
                setGroupBy("pair");
                setMinMatches(5);
                setOnlyHighRisk(false);
                void loadSummary();
              }}
              disabled={loading}
              data-testid="match-risk-reset"
            >
              Sıfırla
            </button>
            <button
              type="button"
              className="h-8 rounded-md border bg-primary text-primary-foreground px-3 text-xs font-medium"
              onClick={() => void loadSummary()}
              disabled={loading}
              data-testid="match-risk-refresh"
            >
              {loading ? "Yükleniyor..." : "Yenile"}
            </button>
          </div>
        </div>

              </div>

      {err ? (
        <div
          className="mt-4 rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive"
          data-testid="match-risk-error"
        >
          {err}
        </div>
      ) : null}

      <div className="mt-4 rounded-xl border bg-card p-4 overflow-x-auto" data-testid="match-risk-summary-table">
        {items.length === 0 && !loading ? (
          <div className="text-sm text-muted-foreground text-center py-6">
            Bu aralıkta eşleşme verisi bulunamadı.
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-xs text-muted-foreground">
                <th className="text-left py-2 px-2 font-medium">Grup</th>
                <th className="text-left py-2 px-2 font-medium">Match sayısı</th>
                <th className="text-left py-2 px-2 font-medium">Outcome known/missing</th>
                <th className="text-left py-2 px-2 font-medium">Not arrived</th>
                <th className="text-left py-2 px-2 font-medium">Not arrived oranı</th>
                <th className="text-left py-2 px-2 font-medium">Tekrar not arrived (7g)</th>
                <th className="text-left py-2 px-2 font-medium">Detay</th>
              </tr>
            </thead>
            <tbody>
              {items.map((row, idx) => {
                const rate = Number(row.not_arrived_rate || 0);
                const level = deriveRiskLevel(rate);
                const label = formatPercent(row.not_arrived_rate);
                const isHighRisk = rate >= 0.5;

                let groupLabel = "";
                if (groupBy === "pair") {
                  groupLabel = `${hotelLabel(row.from_hotel_id)} → ${hotelLabel(row.to_hotel_id)}`;
                } else if (groupBy === "to_hotel") {
                  groupLabel = hotelLabel(row.to_hotel_id);
                } else {
                  groupLabel = hotelLabel(row.from_hotel_id);
                }

                return (
                  <tr
                    key={idx}
                    className="border-b last:border-0 hover:bg-muted/50 cursor-pointer"
                    onClick={() => openDrilldown(row)}
                    data-testid="match-risk-row"
                  >
                    <td className="py-2 px-2 text-xs">
                      <div className="flex items-center gap-2">
                        {isHighRisk ? (
                          <Tooltip>
                              <TooltipTrigger asChild>
                                <span
                                  className="inline-flex h-5 w-5 items-center justify-center rounded-full border border-border/60 bg-background"
                                  data-testid="match-risk-high-flag"
                                  aria-label="Yüksek risk"
                                >
                                  <AlertTriangle className="h-3.5 w-3.5 text-red-600" />
                                </span>
                              </TooltipTrigger>
                              <TooltipContent side="right" className="max-w-xs">
                                <p className="text-[11px] leading-snug">
                                  Yüksek risk sinyali: not_arrived_rate ≥ 50%. Öncelikli inceleme önerilir.
                                </p>
                              </TooltipContent>
                            </Tooltip>
                        ) : null}
                        <span className="font-medium truncate max-w-[260px]">{groupLabel}</span>
                      </div>
                      <div className="text-[11px] text-muted-foreground">
                        group_by: {groupBy}
                      </div>
                    </td>
                    <td className="py-2 px-2 font-medium">{row.matches_total}</td>
                    <td className="py-2 px-2 text-xs">
                      {row.outcome_known} / {row.outcome_missing}
                    </td>
                    <td className="py-2 px-2 text-xs">{row.not_arrived}</td>
                    <td className="py-2 px-2 text-xs">{riskBadge(level, label)}</td>
                    <td className="py-2 px-2 text-xs">{row.repeat_not_arrived_7 ?? "—"}</td>
                    <td className="py-2 px-2 text-xs">
                      <button
                        type="button"
                        className="px-2 py-1 rounded-md border bg-background text-xs hover:bg-muted"
                        onClick={(e) => {
                          e.stopPropagation();
                          void openDrilldown(row);
                        }}
                        data-testid="match-risk-drill-btn"
                      >
                        Drilldown
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* Drilldown drawer (simple panel) */}
      {drillOpen && (
        <div
          className="fixed inset-0 z-[200] flex justify-end bg-black/30"
          onClick={() => setDrillOpen(false)}
          data-testid="match-risk-drill-overlay"
        >
          <div
            className="h-full w-full max-w-xl bg-background shadow-xl border-l flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between border-b px-4 py-3">
              <div>
                <div className="text-sm font-semibold">Drilldown</div>
                <div className="text-[11px] text-muted-foreground">{periodLabel}</div>
                <div className="mt-1 text-[11px] text-muted-foreground max-w-md">
                  Outcome istatistik amaçlıdır; ücretlendirmeyi etkilemez.
                </div>
              </div>
              <button
                type="button"
                className="h-8 rounded-md border bg-background px-2 text-xs"
                onClick={() => setDrillOpen(false)}
                data-testid="match-risk-drill-close"
              >
                Kapat
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-4">
              {drillErr ? (
                <div
                  className="mb-3 rounded-lg border border-destructive/30 bg-destructive/10 p-2 text-xs text-destructive"
                  data-testid="match-risk-drill-error"
                >
                  {drillErr}
                </div>
              ) : null}

              {drillLoading ? (
                <div className="text-sm text-muted-foreground">Yükleniyor...</div>
              ) : drillItems.length === 0 ? (
                <div className="text-sm text-muted-foreground">Bu grup için kayıt bulunamadı.</div>
              ) : (
                <table className="w-full text-xs" data-testid="match-risk-drill-table">
                  <thead>
                    <tr className="border-b">
                      <th className="text-left py-2 px-2 font-medium">Tarih</th>
                      <th className="text-left py-2 px-2 font-medium">Ref</th>
                      <th className="text-left py-2 px-2 font-medium">From → To</th>
                      <th className="text-left py-2 px-2 font-medium">Outcome</th>
                      <th className="text-left py-2 px-2 font-medium">Not</th>
                    </tr>
                  </thead>
                  <tbody>
                    {drillItems.map((m, idx) => {
                      const createdAt = m.created_at || m.createdAt || null;
                      const markedAt = m.outcome_marked_at || m.marked_at || null;
                      const refVal = m.reference_code || m.reference || m.match_id || m.id || idx;
                      const fromId = m.from_hotel_id || "?";
                      const toId = m.to_hotel_id || "?";
                      const outcome = m.outcome || "unknown";
                      const note = m.outcome_note || m.note || "";

                      const copiedForThis = copied && copied === String(refVal || "");

                      return (
                        <tr key={idx} className="border-b last:border-0">
                          <td className="py-2 px-2">
                            <div>{createdAt ? new Date(createdAt).toLocaleDateString() : "—"}</div>
                            <div className="text-[11px] text-muted-foreground">
                              {markedAt ? new Date(markedAt).toLocaleTimeString() : ""}
                            </div>
                          </td>
                          <td className="py-2 px-2">
                            <div className="flex items-center gap-2">
                              <span className="font-mono text-[11px] truncate max-w-[120px] inline-block">
                                {String(refVal)}
                              </span>
                              {refVal ? (
                                <button
                                  type="button"
                                  className="inline-flex items-center gap-1 rounded-md border border-border/60 bg-background px-2 py-1 text-[11px]"
                                  onClick={() => void copyText(refVal)}
                                  data-testid="match-risk-copy-ref"
                                  aria-label="Referansı kopyala"
                                >
                                  {copiedForThis ? (
                                    <>
                                      <Check className="h-3 w-3" />
                                      Kopyalandı
                                    </>
                                  ) : (
                                    <>
                                      <Copy className="h-3 w-3" />
                                      Kopyala
                                    </>
                                  )}
                                </button>
                              ) : null}
                            </div>
                          </td>
                          <td className="py-2 px-2 text-xs">
                            <div className="truncate max-w-[260px]">
                              {hotelLabel(fromId)} → {hotelLabel(toId)}
                            </div>
                            <div className="text-[10px] text-muted-foreground font-mono">
                              {fromId} → {toId}
                            </div>
                          </td>
                          <td className="py-2 px-2">
                            <span className="inline-flex items-center rounded-full bg-muted px-2 py-0.5 text-[11px]">
                              {outcome}
                            </span>
                          </td>
                          <td className="py-2 px-2 max-w-[200px]">
                            {note ? (
                              <div className="text-[11px] text-foreground whitespace-pre-wrap break-words">
                                {note}
                              </div>
                            ) : (
                              <span className="text-[11px] text-muted-foreground">—</span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </div>
      )}

      <div className="mt-4 text-[11px] text-muted-foreground max-w-2xl">
        Not: Bu ekran yalnızca istatistiksel amaçlıdır. Match outcome kayıtları ücretlendirme,
        komisyon veya fatura hesaplarını etkilemez; sadece olası kötüye kullanım desenlerini
        tespit etmek için kullanılır.
      </div>
      </div>
    </TooltipProvider>
  );
}
