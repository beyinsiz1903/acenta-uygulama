import React, { useCallback, useEffect, useMemo, useState } from "react";
import { X, Loader2 } from "lucide-react";

import { getOpsCase, closeOpsCase, apiErrorMessage } from "../lib/opsCases";
import { api } from "../lib/api";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Textarea } from "./ui/textarea";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "./ui/alert-dialog";
import ErrorState from "./ErrorState";
import SlaTooltip from "./ops/SlaTooltip";
import { toast } from "sonner";

const SLA_DAYS = 7;

function parseDateSafe(value) {
  if (!value) return null;
  try {
    const s = String(value).slice(0, 10);
    const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s);
    let d;
    if (m) {
      const y = Number(m[1]);
      const mo = Number(m[2]) - 1;
      const da = Number(m[3]);
      d = new Date(y, mo, da);
    } else {
      d = new Date(value);
    }
    if (Number.isNaN(d.getTime())) return null;
    return d;
  } catch {
    return null;
  }
}

function daysBetween(a, b) {
  if (!a || !b) return null;
  const ms = b.getTime() - a.getTime();
  return Math.floor(ms / (1000 * 60 * 60 * 24));
}

function classifyRisk(caseItem, now) {
  const status = String(caseItem?.status || "").toLowerCase();
  if (!["open", "waiting", "in_progress"].includes(status)) return "na";

  const created = parseDateSafe(caseItem?.created_at);
  if (!created) return "no_date";

  const ageDays = daysBetween(created, now);
  if (ageDays === null) return "no_date";

  if (ageDays <= 1) return "fresh";
  if (ageDays <= 6) return "active_risk";
  return "sla_breach";
}

function normalizeWaitingOn(v) {
  const s = String(v || "").toLowerCase().trim();
  if (!s) return "none";
  if (s.includes("cust")) return "customer";
  if (s.includes("sup")) return "supplier";
  if (s.includes("ops")) return "ops";
  return "other";
}

function RiskBadge({ kind }) {
  if (!kind || kind === "na") return null;

  let label = "";
  let cls = "border text-[10px] px-2 py-0.5 rounded-full inline-flex font-semibold";

  if (kind === "sla_breach") {
    label = "SLA BREACH";
    cls += " bg-red-100 text-red-900 border-red-200";
  } else if (kind === "active_risk") {
    label = "ACTIVE RISK";
    cls += " bg-amber-100 text-amber-900 border-amber-200";
  } else if (kind === "fresh") {
    label = "FRESH";
    cls += " bg-emerald-100 text-emerald-900 border-emerald-200";
  } else if (kind === "no_date") {
    label = "NO DATE";
    cls += " bg-slate-100 text-slate-700 border-slate-200";
  } else {
    label = "N/A";
    cls += " bg-slate-100 text-slate-700 border-slate-200";
  }

  return <span className={cls}>{label}</span>;
}

function WaitingBadge({ waitingOn }) {
  const w = normalizeWaitingOn(waitingOn);
  if (!w || w === "none") return null;

  let label = "";
  let cls = "border text-[10px] px-2 py-0.5 rounded-full inline-flex font-semibold";

  if (w === "customer") {
    label = "WAITING: CUSTOMER";
    cls += " bg-sky-100 text-sky-900 border-sky-200";
  } else if (w === "supplier") {
    label = "WAITING: SUPPLIER";
    cls += " bg-violet-100 text-violet-900 border-violet-200";
  } else if (w === "ops") {
    label = "WAITING: OPS";
    cls += " bg-slate-100 text-slate-900 border-slate-200";
  } else {
    label = "WAITING: OTHER";
    cls += " bg-slate-100 text-slate-900 border-slate-200";
  }

  return <span className={cls}>{label}</span>;
}
function parseDateTimeSafe(value) {
  if (!value) return null;
  try {
    const d = new Date(value);
    if (Number.isNaN(d.getTime())) return null;
    return d;
  } catch {
    return null;
  }
}

function formatTs(d) {
  if (!d) return "—";
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  const hh = String(d.getHours()).padStart(2, "0");
  const mi = String(d.getMinutes()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd} ${hh}:${mi}`;
}

function normalizeTimelineEvents(caseData) {
  const eventsRaw = Array.isArray(caseData?.timeline) ? caseData.timeline : null;

  if (eventsRaw && eventsRaw.length) {
    return eventsRaw
      .map((e, idx) => {
        const ts = parseDateTimeSafe(e.timestamp || e.ts || e.created_at || e.at);
        const kind = String(e.kind || e.type || "event").toLowerCase();
        const actor = e.actor || e.by || null;
        const message = e.message || e.note || e.title || null;
        const isSystem = Boolean(e.system === true || e.is_system === true);
        const patch = e.patch || null;

        return {
          _key: e.id || e._id || `${kind}-${idx}`,
          ts,
          kind,
          actor,
          message,
          isSystem,
          patch,
          raw: e,
        };
      })
      .filter((x) => x.ts)
      .sort((a, b) => b.ts.getTime() - a.ts.getTime());
  }

  const created = parseDateTimeSafe(caseData?.created_at);
  const updated = parseDateTimeSafe(caseData?.updated_at);

  const out = [];
  if (created) {
    out.push({
      _key: "created",
      ts: created,
      kind: "created",
      actor: caseData?.created_by?.email || null,
      message: "Case created",
      isSystem: false,
      patch: { status: caseData?.status ?? null },
      raw: null,
    });
  }
  if (updated && (!created || updated.getTime() !== created.getTime())) {
    out.push({
      _key: "updated",
      ts: updated,
      kind: "updated",
      actor: null,
      message: "Case updated",
      isSystem: true,
      patch: {
        status: caseData?.status ?? null,
        waiting_on: caseData?.waiting_on ?? null,
      },
      raw: null,
    });
  }

  return out.sort((a, b) => b.ts.getTime() - a.ts.getTime());
}

function dayBucket(ts) {
  if (!ts) return "older";
  const now = new Date();
  const startToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const startYesterday = new Date(startToday.getTime() - 24 * 60 * 60 * 1000);

  if (ts >= startToday) return "today";
  if (ts >= startYesterday) return "yesterday";
  return "older";
}

function bucketLabel(bucket) {
  if (bucket === "today") return "Bugün";
  if (bucket === "yesterday") return "Dün";
  return "Önceki";
}

function EventBadge({ kind, isSystem }) {
  const k = String(kind || "event").toLowerCase();
  let label = k.toUpperCase();
  let cls = "border text-[9px] px-1.5 py-0.5 rounded-full inline-flex";

  if (k.includes("status")) {
    label = "STATUS";
    cls += " bg-blue-100 text-blue-900 border-blue-200";
  } else if (k.includes("waiting")) {
    label = "WAITING";
    cls += " bg-sky-100 text-sky-900 border-sky-200";
  } else if (k.includes("note")) {
    label = "NOTE";
    cls += " bg-amber-100 text-amber-900 border-amber-200";
  } else if (k.includes("created")) {
    label = "CREATED";
    cls += " bg-emerald-100 text-emerald-900 border-emerald-200";
  } else {
    label = "EVENT";
    cls += " bg-slate-100 text-slate-800 border-slate-200";
  }

  if (isSystem) {
    cls += " opacity-80";
  }

  return <span className={cls}>{label}</span>;
}




function OpsGuestCaseDrawer({ caseId, open, onClose, onClosed }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [data, setData] = useState(null);
  const [closing, setClosing] = useState(false);
  const [closeNote, setCloseNote] = useState("");

  const [timelineLoading, setTimelineLoading] = useState(false);
  const [timelineError, setTimelineError] = useState("");
  const [timelineItems, setTimelineItems] = useState([]);

  const [hideSystem, setHideSystem] = useState(true);
  const [onlyStatus, setOnlyStatus] = useState(false);

  const [editStatus, setEditStatus] = useState("");
  const [editWaitingOn, setEditWaitingOn] = useState("");
  const [editNote, setEditNote] = useState("");
  const [saving, setSaving] = useState(false);

  const [initialSnapshot, setInitialSnapshot] = useState({
    status: "",
    waiting_on: "",
    note: "",
  });
  const [showUnsavedDialog, setShowUnsavedDialog] = useState(false);
  const [pendingCloseIntent, setPendingCloseIntent] = useState(false);

  const timelineEvents = useMemo(() => {
    if (!data) return [];
    const all = normalizeTimelineEvents(data);
    return all.filter((ev) => {
      if (hideSystem && ev.isSystem) return false;
      if (onlyStatus) {
        const k = String(ev.kind || "");
        return k.includes("status");
      }
      return true;
    });
  }, [data, hideSystem, onlyStatus]);

  const timelineGroups = useMemo(() => {
    const buckets = { today: [], yesterday: [], older: [] };
    for (const ev of timelineEvents) {
      const b = dayBucket(ev.ts);
      buckets[b].push(ev);
    }
    return ["today", "yesterday", "older"]
      .map((bucket) => ({ bucket, items: buckets[bucket] }))
      .filter((g) => g.items.length > 0);
  }, [timelineEvents]);

  const loadTimeline = useCallback(
    async (bookingId) => {
      if (!bookingId) {
        setTimelineItems([]);
        return;
      }
      setTimelineLoading(true);
      setTimelineError("");
      try {
        const res = await api.get(`/ops/bookings/${bookingId}/events`, {
          params: { limit: 50 },
        });
        const all = res.data?.items || [];
        // Son 5 eventi created_at DESC ile göster
        const last5 = [...all]
          .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
          .slice(0, 5);
        setTimelineItems(last5);
      } catch (e) {
        // Booking bulunamadı (ör. orphan case) → error yerine empty göster
        if (e?.response?.status === 404) {
          setTimelineError("");
          setTimelineItems([]);
        } else {
          setTimelineError(apiErrorMessage(e));
          setTimelineItems([]);
        }
      } finally {
        setTimelineLoading(false);
      }
    },
    [],
  );

  useEffect(() => {
    if (!open || !caseId) {
      setData(null);
      setError("");
      setCloseNote("");
      setTimelineItems([]);
      setInitialSnapshot({ status: "", waiting_on: "", note: "" });
      setEditStatus("");
      setEditWaitingOn("");
      setEditNote("");
      setShowUnsavedDialog(false);
      setPendingCloseIntent(false);
      return;
    }

    const load = async () => {
      setLoading(true);
      setError("");
      try {
        const doc = await getOpsCase(caseId);
        setData(doc);
        const nextStatus = doc.status || "open";
        const nextWaiting = doc.waiting_on || "";
        const nextNote = doc.note || "";
        setEditStatus(nextStatus);
        setEditWaitingOn(nextWaiting);
        setEditNote(nextNote);
        setInitialSnapshot({
          status: nextStatus,
          waiting_on: nextWaiting,
          note: nextNote,
        });
        if (doc?.booking_id) {
          await loadTimeline(doc.booking_id);
        } else {
          setTimelineItems([]);
        }
      } catch (e) {
        setError(apiErrorMessage(e));
      } finally {
        setLoading(false);
      }
    };

    load();
  }, [open, caseId, loadTimeline]);

  const isClosed = data?.status === "closed";

  const normalizedInitialWaiting = normalizeWaitingOn(initialSnapshot.waiting_on);
  const normalizedDraftWaiting = normalizeWaitingOn(editWaitingOn);

  const isDirty =
    Boolean(data) &&
    (String(editStatus || "") !== String(initialSnapshot.status || "") ||
      normalizedDraftWaiting !== normalizedInitialWaiting ||
      String(editNote || "") !== String(initialSnapshot.note || ""));

  const disableStatusSelect =
    isClosed || (normalizedDraftWaiting !== "none" && normalizedDraftWaiting !== "other");

  const effectiveStatusValue = disableStatusSelect ? "waiting" : editStatus || "open";

  const requestClose = () => {
    if (!isDirty) {
      if (onClose) onClose();
      return;
    }
    setPendingCloseIntent(true);
    setShowUnsavedDialog(true);
  };

  const discardChangesAndClose = () => {
    setEditStatus(initialSnapshot.status || "");
    setEditWaitingOn(initialSnapshot.waiting_on || "");
    setEditNote(initialSnapshot.note || "");
    setShowUnsavedDialog(false);
    setPendingCloseIntent(false);
    if (onClose) onClose();
  };

  const cancelUnsavedDialog = () => {
    setShowUnsavedDialog(false);
    setPendingCloseIntent(false);
  };

  const handleClose = async () => {
    if (!caseId || isClosed) return;
    const confirmed = window.confirm("Bu case'i kapatmak istediğinize emin misiniz?");
    if (!confirmed) return;
    setClosing(true);
    try {
      const res = await closeOpsCase(caseId, closeNote || undefined);
      toast.success("Case başarıyla kapatıldı.");
      setData((prev) =>
        prev
          ? {
              ...prev,
              status: "closed",
              closed_at: new Date().toISOString(),
              close_note: closeNote || prev.close_note,
            }
          : prev,
      );
      setCloseNote("");
      if (onClosed) onClosed();
      // Timeline'ı da tazele (yeni OPS_CASE_CLOSED event'ini görmek için)
      if (data?.booking_id) {
        await loadTimeline(data.booking_id);
      }
    } catch (e) {
      toast.error(apiErrorMessage(e));
    } finally {
      setClosing(false);
    }
  };
  const handleSave = async () => {
    if (!data || !caseId || isClosed || !isDirty) return;
    setSaving(true);
    try {
      const payload = {};
      const baseStatus = initialSnapshot.status || "";

      if (effectiveStatusValue && effectiveStatusValue !== baseStatus) {
        payload.status = effectiveStatusValue;
      }

      if (normalizedDraftWaiting === "none") {
        if (normalizedInitialWaiting !== "none") {
          payload.waiting_on = null;
        }
      } else if (normalizedDraftWaiting !== normalizedInitialWaiting) {
        payload.waiting_on = editWaitingOn || normalizedDraftWaiting;
      }

      if (String(editNote || "") !== String(initialSnapshot.note || "")) {
        payload.note = editNote;
      }

      if (Object.keys(payload).length === 0) {
        setSaving(false);
        return;
      }

      const res = await api.patch(`/ops-cases/${caseId}`, payload);
      const updated = res || {};
      setData((prev) => (prev ? { ...prev, ...updated } : updated));

      const nextStatus = updated.status || effectiveStatusValue;
      const nextWaiting = updated.waiting_on || "";
      const nextNote = updated.note || "";

      setEditStatus(nextStatus);
      setEditWaitingOn(nextWaiting);
      setEditNote(nextNote);
      setInitialSnapshot({ status: nextStatus, waiting_on: nextWaiting, note: nextNote });

      toast.success("Case güncellendi.");
      if (onClosed) {
        onClosed();
      }
    } catch (e) {
      toast.error(apiErrorMessage(e));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      className={`fixed inset-0 z-40 transition ${
        open ? "pointer-events-auto" : "pointer-events-none"
      }`}
      aria-hidden={!open}
    >
      {/* Backdrop */}
      <div
        className={`absolute inset-0 bg-black/30 transition-opacity ${open ? "opacity-100" : "opacity-0"}`}
        onClick={saving ? undefined : requestClose}
      />

      {/* Panel */}
      <div
        className={`absolute inset-y-0 right-0 w-full max-w-md bg-background border-l shadow-xl transition-transform duration-200 flex flex-col ${
          open ? "translate-x-0" : "translate-x-full"
        }`}
      >
        <div className="flex items-center justify-between px-4 py-3 border-b">
          <div className="flex flex-col gap-0.5">
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Guest Case
            </span>
            <span className="text-sm font-semibold">
              {data?.case_id || caseId || "Case detayı"}
            </span>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={requestClose}
            className="h-8 w-8"
            disabled={saving}
          >
            <X className="h-4 w-4" />
          </Button>
        </div>

        <div className="flex-1 overflow-y-auto px-4 py-3 space-y-4">
          {data && !loading && !error && (
            (() => {
              const now = new Date();
              const riskKind = classifyRisk(data, now);
              const created = parseDateSafe(data.created_at);
              const ageDays = created ? daysBetween(created, now) : null;
              const slaDays = SLA_DAYS;
              const remainingDays =
                typeof ageDays === "number" ? Math.max(slaDays - ageDays, 0) : null;

              return (
                <div
                  className="rounded-xl border bg-white p-3 flex flex-col gap-2"
                  data-testid="case-drawer-range-summary"
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <span data-testid="drawer-risk-badge">
                      <RiskBadge kind={riskKind} />
                    </span>
                    <span data-testid="drawer-waiting-badge">
                      <WaitingBadge waitingOn={data.waiting_on} />
                    </span>
                    <span className="ml-auto">
                      <SlaTooltip slaDays={slaDays} testId="sla-tooltip-drawer" />
                    </span>
                  </div>
                  <div
                    className="text-xs text-muted-foreground"
                    data-testid="drawer-age-sla"
                  >
                    {ageDays === null ? (
                      <span>
                        Age: — · SLA: {slaDays}d
                      </span>
                    ) : (
                      <span>
                        Age: {ageDays}d · SLA: {slaDays}d · {" "}
                        {ageDays >= slaDays ? (
                          <span className="font-semibold text-red-700">Breached</span>
                        ) : (
                          <span className="font-semibold">
                            Remaining: {remainingDays}d
                          </span>
                        )}
                      </span>
                    )}
                  </div>
                </div>
              );
            })()
          )}

          {loading ? (
            <div className="flex items-center justify-center py-10 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 mr-2 animate-spin" /> Case y1kleniyor...
            </div>
          ) : error ? (
            <ErrorState description={error} compact />
          ) : !data ? (
            <div className="text-sm text-muted-foreground py-6">Case bilgisi bulunamad1.</div>
          ) : (
            <>
              {/* Status + meta */}
              <div className="flex items-center justify-between gap-2">
                <div className="space-y-1">
                  <div className="text-xs text-muted-foreground">Durum</div>
                  <div className="flex items-center gap-2">
                    <select
                      className="rounded-md border px-2 py-1 text-[11px] bg-background"
                      value={effectiveStatusValue}
                      onChange={(e) => setEditStatus(e.target.value)}
                      disabled={disableStatusSelect}
                      data-testid="case-edit-status"
                    >
                      <option value="open">Açık</option>
                      <option value="waiting">Beklemede</option>
                      <option value="in_progress">Devam ediyor</option>
                      <option value="closed" disabled>
                        Kapalı (sadece özel aksiyon ile)
                      </option>
                    </select>
                    <div>
                      {(() => {
                        switch (data.status) {
                          case "open":
                            return (
                              <span className="inline-flex items-center rounded-full bg-emerald-50 text-emerald-700 px-2 py-0.5 text-[11px]">
                                Açık
                              </span>
                            );
                          case "waiting":
                            return (
                              <span className="inline-flex items-center rounded-full bg-amber-50 text-amber-700 px-2 py-0.5 text-[11px]">
                                Beklemede
                              </span>
                            );
                          case "in_progress":
                            return (
                              <span className="inline-flex items-center rounded-full bg-blue-50 text-blue-700 px-2 py-0.5 text-[11px]">
                                Devam ediyor
                              </span>
                            );
                          case "closed":
                          default:
                            return (
                              <span className="inline-flex items-center rounded-full bg-muted text-muted-foreground px-2 py-0.5 text-[11px]">
                                Kapalı
                              </span>
                            );
                        }
                      })()}
                    </div>
                  </div>
                  <div className="text-[11px] text-muted-foreground">
                    Kapama sadece aşağıdaki {"Case'i kapat"} aksiyonundan yapılabilir.
                  </div>
                </div>
                <div className="space-y-1 text-right text-xs text-muted-foreground">
                  <div>Olufturulma: {data.created_at ? new Date(data.created_at).toLocaleString("tr-TR") : "-"}</div>
                  {data.closed_at && (
                    <div>Kapat1lma: {new Date(data.closed_at).toLocaleString("tr-TR")}</div>
                  )}
                </div>
              </div>

              <div className="space-y-1">
                <div className="text-xs font-medium text-muted-foreground">Bekleme Durumu</div>
                <select
                  className="rounded-md border px-2 py-1 text-[11px] bg-background"
                  value={normalizedDraftWaiting === "none" ? "" : editWaitingOn}
                  onChange={(e) => setEditWaitingOn(e.target.value)}
                  disabled={isClosed || saving}
                  data-testid="case-edit-waiting-on"
                >
                  <option value="">Seçilmemiş</option>
                  <option value="customer">Müşteri</option>
                  <option value="supplier">Tedarikçi</option>
                  <option value="ops">Ops</option>
                  <option value="other">Diğer</option>
                </select>
              </div>

              <div className="space-y-1">
                <div className="text-xs font-medium text-muted-foreground">Rezervasyon</div>
                <div className="flex flex-col gap-0.5 text-xs">
                  <div>
                    <span className="font-medium">Booking ID:</span> {data.booking_id || "-"}
                  </div>
                  <div>
                    <span className="font-medium">Rezervasyon Kodu:</span> {data.booking_code || "-"}
                  </div>
                </div>
              </div>

              {/* Case Timeline (normalized) */}
              <div
                className="rounded-xl border bg-white p-3 space-y-2"
                data-testid="case-drawer-timeline"
              >
                <div className="flex items-center gap-2">
                  <div className="font-semibold text-sm">Timeline</div>
                  <div className="ml-auto flex items-center gap-2">
                    <label className="text-[11px] text-muted-foreground flex items-center gap-1">
                      <input
                        type="checkbox"
                        checked={hideSystem}
                        onChange={(e) => setHideSystem(e.target.checked)}
                        data-testid="timeline-filter-hide-system"
                      />
                      Hide system
                    </label>
                    <label className="text-[11px] text-muted-foreground flex items-center gap-1">
                      <input
                        type="checkbox"
                        checked={onlyStatus}
                        onChange={(e) => setOnlyStatus(e.target.checked)}
                        data-testid="timeline-filter-only-status"
                      />
                      Only status
                    </label>
                  </div>
                </div>

                <div className="text-[11px] text-muted-foreground">
                  Newest first 0 grouped by day
                </div>

                <div className="space-y-3" data-testid="timeline-groups">
                  {timelineGroups.map((g) => (
                    <div
                      key={g.bucket}
                      data-testid={`timeline-group-${g.bucket}`}
                    >
                      <div className="text-[11px] font-semibold text-muted-foreground mb-1">
                        {bucketLabel(g.bucket)}
                      </div>
                      <div className="space-y-2">
                        {g.items.map((ev) => (
                          <div
                            key={ev._key}
                            className="rounded-lg border px-2 py-2"
                            data-testid={`timeline-item-${ev._key}`}
                          >
                            <div className="flex items-start gap-2">
                              <EventBadge kind={ev.kind} isSystem={ev.isSystem} />
                              <div className="flex-1 min-w-0">
                                <div className="text-xs font-medium truncate">
                                  {ev.message || "(no message)"}
                                </div>
                                <div className="text-[11px] text-muted-foreground">
                                  {formatTs(ev.ts)}
                                  {ev.actor ? ` 0 ${ev.actor}` : ""}
                                </div>
                                {ev.patch ? (
                                  <pre className="mt-1 text-[10px] bg-muted/40 rounded p-2 overflow-x-auto">
                                    {JSON.stringify(ev.patch, null, 2)}
                                  </pre>
                                ) : null}
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}

                  {!timelineGroups.length && !timelineLoading && !timelineError && (
                    <div
                      className="text-[11px] text-muted-foreground"
                      data-testid="timeline-empty"
                    >

      <AlertDialog open={showUnsavedDialog} onOpenChange={(openDialog) => {
        if (!openDialog) {
          cancelUnsavedDialog();
        }
      }}>
        <AlertDialogContent data-testid="unsaved-dialog">
          <AlertDialogHeader>
            <AlertDialogTitle>Unsaved changes</AlertDialogTitle>
            <AlertDialogDescription>
              You have unsaved changes. Discard them?
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel data-testid="unsaved-keep" onClick={cancelUnsavedDialog}>
              Keep editing
            </AlertDialogCancel>
            <AlertDialogAction data-testid="unsaved-discard" onClick={discardChangesAndClose}>
              Discard
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

                      No timeline events.
                    </div>
                  )}

                  {timelineLoading && (
                    <div className="text-xs text-muted-foreground flex items-center gap-1">
                      <Loader2 className="h-3 w-3 animate-spin" /> Yckleniyor...
                    </div>
                  )}

                  {timelineError && (
                    <ErrorState description={timelineError} compact />
                  )}
                </div>
              </div>

              <div className="mt-4 flex items-center justify-end gap-2">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setEditStatus(initialSnapshot.status || "");
                    setEditWaitingOn(initialSnapshot.waiting_on || "");
                    setEditNote(initialSnapshot.note || "");
                  }}
                  className="text-[11px]"
                  disabled={!isDirty || saving}
                  data-testid="case-edit-reset"
                >
                  Reset
                </Button>
                <Button
                  type="button"
                  size="sm"
                  className="text-[11px]"
                  onClick={handleSave}
                  disabled={isClosed || saving || !isDirty}
                  data-testid="case-edit-apply"
                >
                  {saving ? (
                    <span
                      className="inline-flex items-center mr-1"
                      data-testid="case-edit-saving"
                    >
                      <Loader2 className="h-3 w-3 animate-spin" />
                    </span>
                  ) : null}
                  Kaydet
                </Button>
              </div>

              <div className="space-y-1">
                <div className="text-xs font-medium text-muted-foreground">Ops Notu</div>
                <Textarea
                  rows={3}
                  className="text-sm"
                  placeholder="Case notu"
                  value={editNote}
                  onChange={(e) => setEditNote(e.target.value)}
                  disabled={saving}
                  data-testid="case-edit-note"
                />
              </div>

              <div className="space-y-1">
                <div className="text-xs font-medium text-muted-foreground">Misafir Talebi</div>
                <div className="rounded-xl border bg-muted/30 px-3 py-2 text-xs space-y-1">
                  <div>
                    <span className="font-medium">Tip:</span> {data.type || "-"}
                  </div>
                  {data.payload?.requested_changes && (
                    <div>
                      <span className="font-medium">Talep edilen defifiklikler:</span> {data.payload.requested_changes}
                    </div>
                  )}
                  {data.payload?.note && (
                    <div>
                      <span className="font-medium">Not:</span> {data.payload.note}
                    </div>
                  )}
                  <div>
                    <span className="font-medium">Kaynak:</span> {data.source === "guest_portal" ? "Guest portal" : data.source || "-"}
                  </div>
                </div>
              </div>

              {data.request_context && (
                <div className="space-y-1">
                  <div className="text-xs font-medium text-muted-foreground">0stek baflam1</div>
                  <div className="rounded-xl border bg-muted/20 px-3 py-2 text-[11px] text-muted-foreground space-y-1">
                    {data.request_context.ip && (
                      <div>IP: {data.request_context.ip}</div>
                    )}
                    {data.request_context.user_agent && (
                      <div className="break-all">UA: {data.request_context.user_agent}</div>
                    )}
                  </div>
                </div>
              )}

              {data.closed_by && (
                <div className="space-y-1">
                  <div className="text-xs font-medium text-muted-foreground">Kapatma bilgisi</div>
                  <div className="rounded-xl border bg-muted/20 px-3 py-2 text-[11px] text-muted-foreground space-y-1">
                    {data.closed_by.email && <div>Kapat1lan kullan1c1: {data.closed_by.email}</div>}
                    {data.close_note && <div>Kapan1f notu: {data.close_note}</div>}
                  </div>
                </div>
              )}

              {/* Close action */}
              <div className="mt-4 pt-3 border-t space-y-2">
                <div className="flex items-center justify-between">
                  <div className="text-xs font-medium text-muted-foreground">Case&apos;i kapat</div>
                  {isClosed && (
                    <span className="text-[11px] text-muted-foreground">Bu case zaten kapal1.</span>
                  )}
                </div>
                {!isClosed && (
                  <>
                    <Textarea
                      rows={3}
                      className="text-sm"
                      placeholder="Opsiyonel kapan1f notu yazabilirsiniz."
                      value={closeNote}
                      onChange={(e) => setCloseNote(e.target.value)}
                    />
                    <Button
                      type="button"
                      size="sm"
                      disabled={closing}
                      onClick={handleClose}
                    >
                      {closing ? <Loader2 className="h-3 w-3 mr-1 animate-spin" /> : null}
                      Case&apos;i kapat
                    </Button>
                  </>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default OpsGuestCaseDrawer;
