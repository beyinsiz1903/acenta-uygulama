import React, { useCallback, useEffect, useState } from "react";
import { X, Loader2 } from "lucide-react";

import { getOpsCase, closeOpsCase, apiErrorMessage } from "../lib/opsCases";
import { api } from "../lib/api";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Textarea } from "./ui/textarea";
import ErrorState from "./ErrorState";
import { toast } from "sonner";

function OpsGuestCaseDrawer({ caseId, open, onClose, onClosed }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [data, setData] = useState(null);
  const [closing, setClosing] = useState(false);
  const [closeNote, setCloseNote] = useState("");

  const [timelineLoading, setTimelineLoading] = useState(false);
  const [timelineError, setTimelineError] = useState("");
  const [timelineItems, setTimelineItems] = useState([]);

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
      return;
    }

    const load = async () => {
      setLoading(true);
      setError("");
      try {
        const doc = await getOpsCase(caseId);
        setData(doc);
        setEditStatus(doc.status || "open");
        setEditWaitingOn(doc.waiting_on || "");
        setEditNote(doc.note || "");
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
  const [editStatus, setEditStatus] = useState("");
  const [editWaitingOn, setEditWaitingOn] = useState("");
  const [editNote, setEditNote] = useState("");
  const [saving, setSaving] = useState(false);


  const handleClose = async () => {
    if (!caseId || isClosed) return;
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
  const handleSave = async () => {
    if (!data || !caseId || isClosed) return;
    setSaving(true);
    try {
      const payload = {};
      if (editStatus && editStatus !== data.status) payload.status = editStatus;
      if (editStatus === "waiting") {
        if (editWaitingOn) payload.waiting_on = editWaitingOn;
      }
      if (editStatus !== "waiting") {
        // waiting_on UI'da disabled ve null olarak gösteriliyor; backend'e göndermiyoruz
      }
      if (editNote !== (data.note || "")) {
        payload.note = editNote;
      }
      if (Object.keys(payload).length === 0) {
        setSaving(false);
        return;
      }
      const res = await api.patch(`/ops-cases/${caseId}`, payload);
      setData((prev) => (prev ? { ...prev, ...res } : prev));
      toast.success("Case güncellendi.");
      if (onClosed) {
        // Genel listeyi tazelemek için opsiyonel callback; isim legacy ama yeniden kullanıyoruz
        onClosed();
      }
    } catch (e) {
      toast.error(apiErrorMessage(e));
    } finally {
      setSaving(false);
    }
  };

        await loadTimeline(data.booking_id);
      }
    } catch (e) {
      toast.error(apiErrorMessage(e));
    } finally {
      setClosing(false);
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
        onClick={onClose}
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
          <Button variant="ghost" size="icon" onClick={onClose} className="h-8 w-8">
            <X className="h-4 w-4" />
          </Button>
        </div>

        <div className="flex-1 overflow-y-auto px-4 py-3 space-y-4">
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
                      value={editStatus}
                      onChange={(e) => setEditStatus(e.target.value)}
                      disabled={isClosed}
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
                    Kapama sadece aşağıdaki "Case&apos;i kapat" aksiyonundan yapılabilir.
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
                <div className="text-xs font-medium text-muted-foreground">Rezervasyon</div>
                <div className="flex flex-col gap-0.5 text-xs">
                  <div>
                    <span className="font-medium">Booking ID:</span> {data.booking_id || "-"}
                  </div>
                  <div>
                    <span className="font-medium">Rezervasyon Kodu:</span> {data.booking_code || "-"}
              {/* Booking timeline */}
              <div className="mt-4 pt-3 border-t space-y-2">
                <div className="text-xs font-medium text-muted-foreground">İlgili Booking Timeline</div>
                {timelineLoading ? (
                  <div className="text-xs text-muted-foreground flex items-center gap-1">
                    <Loader2 className="h-3 w-3 animate-spin" /> Yükleniyor...
                  </div>
                ) : timelineError ? (
                  <ErrorState description={timelineError} compact />
                ) : timelineItems.length === 0 ? (
                  <div className="text-[11px] text-muted-foreground">Gösterilecek event yok.</div>
                ) : (
                  <ul className="space-y-1 text-xs">
                    {timelineItems.map((ev) => {
                      const created = ev.created_at ? new Date(ev.created_at) : null;
                      let label = ev.type || ev.event || "Event";
                      let metaLine = "";
                      if (ev.type === "OPS_CASE_CLOSED") {
                        label = "Ops Case Kapatıldı";
                        const m = ev.meta || {};
                        const parts = [];
                        if (m.case_id) parts.push(`Case ID: ${m.case_id}`);
                        if (m.note) parts.push(`Not: ${m.note}`);
                        if (m.actor_email) parts.push(`Kapatma: ${m.actor_email}`);
                        metaLine = parts.join(" · ");
                      } else if (ev.meta && ev.meta.note) {
                        metaLine = ev.meta.note;
                      }
                      return (
                        <li key={ev._id || `${ev.type}-${ev.created_at}`} className="border-l pl-2 ml-1">
                          <div className="flex items-center justify-between gap-2">
                            <span className="font-medium">{label}</span>
                            {created && (
                              <span className="text-[11px] text-muted-foreground">
                                {created.toLocaleString("tr-TR")}
                              </span>
                            )}
                          </div>
                          {metaLine && (
                            <div className="text-[11px] text-muted-foreground break-words">{metaLine}</div>
                          )}
                        </li>
                      );
                    })}
                  </ul>
                )}
              </div>

                  </div>
                </div>
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
