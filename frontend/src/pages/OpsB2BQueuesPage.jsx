import React, { useEffect, useMemo, useState } from "react";
import { AlertCircle, CheckCircle2, Loader2, RefreshCw, Search, XCircle } from "lucide-react";

import { api, apiErrorMessage } from "../lib/api";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Textarea } from "../components/ui/textarea";

function formatDate(value) {
  if (!value) return "-";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return String(value);
  return d.toLocaleString();
}

function formatDateTime(iso) {
  if (!iso) return "-";
  try {
    const d = new Date(iso);
    return d.toLocaleString();
  } catch {
    return String(iso);
  }
}

function safeJson(obj) {
  try {
    return JSON.stringify(obj ?? {}, null, 2);
  } catch {
    return String(obj);
  }
}

function eventLabel(ev) {
  const t = ev?.type;
  const m = ev?.meta || {};
  switch (t) {
    case "BOOKING_CREATED":
      return "Booking oluşturuldu";
    case "VOUCHER_GENERATED":
      return `Voucher oluşturuldu${m.voucher_version ? ` (v${m.voucher_version})` : ""}`;
    case "CANCEL_REQUESTED":
      return "İptal talebi açıldı";
    case "CASE_DECIDED":
      return `Case kararı: ${m.decision || "-"}`;
    case "BOOKING_STATUS_CHANGED":
      return `Durum değişti: ${m.status_from || "-"} → ${m.status_to || "-"}`;
    case "REFUND_APPROVED_STEP1":
      return "Refund 1. onay verildi";
    case "REFUND_APPROVED_STEP2":
      return "Refund 2. onay verildi";
    case "REFUND_MARKED_PAID":
      return "Refund ödendi";
    case "REFUND_REJECTED":
      return "Refund reddedildi";
    case "REFUND_CLOSED":
      return "Refund kapatıldı";
    case "DOCUMENT_UPLOADED":
      return "Doküman yüklendi";
    case "DOCUMENT_DELETED":
      return "Doküman silindi";
    case "OPS_TASK_CREATED":
      return "Görev oluşturuldu";
    case "OPS_TASK_UPDATED":
      return "Görev güncellendi";
    case "OPS_TASK_DONE":
      return "Görev tamamlandı";
    case "OPS_TASK_CANCELLED":
      return "Görev iptal edildi";
    default:
      return t || "EVENT";
  }
}

function eventSubline(ev) {
  const m = ev?.meta || {};
  const t = ev?.type;

  if (t === "BOOKING_CREATED") {
    const parts = [];
    if (m.quote_id) parts.push(`quote: ${m.quote_id}`);
    if (m.channel_id) parts.push(`channel: ${m.channel_id}`);
    if (m.amount_sell != null) parts.push(`sell: ${m.amount_sell}`);
    return parts.join(" · ");
  }

  if (t === "VOUCHER_GENERATED") {
    const parts = [];
    if (m.voucher_id) parts.push(`voucher: ${m.voucher_id}`);
    if (m.template_key) parts.push(`template: ${m.template_key}`);
    return parts.join(" · ");
  }

  if (t === "CANCEL_REQUESTED") {
    const parts = [];
    if (m.case_id) parts.push(`case: ${m.case_id}`);
    if (m.requested_refund_amount != null && m.requested_refund_currency) {
      parts.push(`refund: ${m.requested_refund_amount} ${m.requested_refund_currency}`);
    }
    if (m.reason) parts.push(`reason: ${m.reason}`);
    return parts.join(" · ");
  }

  if (t === "CASE_DECIDED") {
    const parts = [];
    if (m.case_id) parts.push(`case: ${m.case_id}`);
    if (m.decision_by_email) parts.push(`by: ${m.decision_by_email}`);
    return parts.join(" · ");
  }

  if (t === "REFUND_APPROVED_STEP1") {
    const parts = [];
    if (m.case_id) parts.push(`case: ${m.case_id}`);
    if (m.approved_amount != null && m.currency) {
      parts.push(`tutar: ${m.approved_amount} ${m.currency}`);
    }
    if (m.by_email) parts.push(`by: ${m.by_email}`);
    return parts.join(" · ");
  }

  if (t === "REFUND_APPROVED_STEP2") {
    const parts = [];
    if (m.case_id) parts.push(`case: ${m.case_id}`);
    if (m.by_email) parts.push(`by: ${m.by_email}`);
    return parts.join(" · ");
  }

  if (t === "REFUND_MARKED_PAID") {
    const parts = [];
    if (m.case_id) parts.push(`case: ${m.case_id}`);
    if (m.payment_reference) parts.push(`ref: ${m.payment_reference}`);
    if (m.by_email) parts.push(`by: ${m.by_email}`);
    return parts.join(" · ");
  }

  if (t === "REFUND_REJECTED") {
    const parts = [];
    if (m.case_id) parts.push(`case: ${m.case_id}`);
    if (m.reason) parts.push(`sebep: ${m.reason}`);
    if (m.by_email) parts.push(`by: ${m.by_email}`);
    return parts.join(" · ");
  }

  if (t === "REFUND_CLOSED") {
    const parts = [];
    if (m.case_id) parts.push(`case: ${m.case_id}`);
    if (m.by_email) parts.push(`by: ${m.by_email}`);
    return parts.join(" · ");
  }

  if (t === "DOCUMENT_UPLOADED") {
    const parts = [];
    if (m.entity_id) parts.push(`case: ${m.entity_id}`);
    if (m.filename) parts.push(`dosya: ${m.filename}`);
    if (m.tag) parts.push(`etiket: ${m.tag}`);
    if (m.by_email) parts.push(`by: ${m.by_email}`);
    return parts.join(" · ");
  }

  if (t === "DOCUMENT_DELETED") {
    const parts = [];
    if (m.entity_id) parts.push(`case: ${m.entity_id}`);
    if (m.filename) parts.push(`dosya: ${m.filename}`);
    if (m.tag) parts.push(`etiket: ${m.tag}`);
    if (m.by_email) parts.push(`by: ${m.by_email}`);
    return parts.join(" · ");
  }

  return "";
}

function StatusBadge({ status }) {
  if (!status) return <Badge variant="outline">-</Badge>;
  const raw = String(status).toLowerCase();
  const label = raw === "confirmed" ? "Onaylandı" : raw === "cancelled" ? "İptal edildi" : raw === "pending" || raw === "pending_approval" ? "Beklemede" : status;
  if (raw === "confirmed") return <Badge variant="secondary">{label}</Badge>;
  if (raw === "cancelled")
    return (
      <Badge variant="destructive" className="gap-1">
        <XCircle className="h-3 w-3" /> {label}
      </Badge>
    );
  if (raw === "pending" || raw === "pending_approval")
    return (
      <Badge variant="outline" className="gap-1">
        <Loader2 className="h-3 w-3 animate-spin" /> {label}
      </Badge>
    );
  return <Badge variant="outline">{status}</Badge>;
}

export default function OpsB2BQueuesPage() {
  const [activeTab, setActiveTab] = useState("bookings");

  // Bookings state
  const [bookings, setBookings] = useState([]);
  const [bookingsLoading, setBookingsLoading] = useState(false);
  const [bookingsError, setBookingsError] = useState("");
  const [bookingStatusFilter, setBookingStatusFilter] = useState("");
  const [bookingFrom, setBookingFrom] = useState("");
  const [bookingTo, setBookingTo] = useState("");
  const [selectedBookingId, setSelectedBookingId] = useState(null);
  const [bookingDetail, setBookingDetail] = useState(null);
  const [bookingDetailLoading, setBookingDetailLoading] = useState(false);
  const [bookingDetailTab, setBookingDetailTab] = useState("general"); // "general" | "snapshots" | "voucher" | "timeline"
  const [voucherHistory, setVoucherHistory] = useState([]);
  const [voucherHistoryLoading, setVoucherHistoryLoading] = useState(false);
  const [voucherHistoryError, setVoucherHistoryError] = useState("");
  const [voucherGenerateLoading, setVoucherGenerateLoading] = useState(false);
  const [voucherResendLoading, setVoucherResendLoading] = useState(false);
  const [voucherResendOpen, setVoucherResendOpen] = useState(false);
  const [voucherResendEmail, setVoucherResendEmail] = useState("");
  const [voucherResendMessage, setVoucherResendMessage] = useState("");
  const [voucherResendError, setVoucherResendError] = useState("");
  const [bookingEvents, setBookingEvents] = useState([]);
  const [bookingEventsLoading, setBookingEventsLoading] = useState(false);
  const [bookingEventsError, setBookingEventsError] = useState("");
  const [expandedEventIds, setExpandedEventIds] = useState(() => new Set());

  function toggleEventExpand(key) {
    setExpandedEventIds((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }


  // Cases state
  const [cases, setCases] = useState([]);
  const [casesLoading, setCasesLoading] = useState(false);
  const [casesError, setCasesError] = useState("");
  const [caseStatusFilter, setCaseStatusFilter] = useState("open");
  const [caseTypeFilter, setCaseTypeFilter] = useState("cancel");
  const [caseFrom, setCaseFrom] = useState("");
  const [caseTo, setCaseTo] = useState("");
  const [selectedCaseId, setSelectedCaseId] = useState(null);
  const [caseDetail, setCaseDetail] = useState(null);
  const [caseDetailLoading, setCaseDetailLoading] = useState(false);
  const [caseActionLoading, setCaseActionLoading] = useState(false);
  const [caseActionError, setCaseActionError] = useState("");

  // Initial load
  useEffect(() => {
    if (activeTab === "bookings") {
      void loadBookings();
    } else {
      void loadCases();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab]);

  async function loadBookings() {
    setBookingsLoading(true);
    setBookingsError("");
    try {
      const params = new URLSearchParams();
      if (bookingStatusFilter) params.set("status", bookingStatusFilter);
      if (bookingFrom) params.set("from", bookingFrom);
      if (bookingTo) params.set("to", bookingTo);
      const res = await api.get(`/ops/bookings?${params.toString()}`);
      setBookings(res.data?.items || []);
    } catch (err) {
      console.error("[OpsB2B] loadBookings error:", err);
      setBookingsError(apiErrorMessage(err));
    } finally {
      setBookingsLoading(false);
    }
  }

  async function loadBookingDetail(id) {
    setSelectedBookingId(id);
    setBookingDetail(null);
    setBookingDetailLoading(true);
    setVoucherHistory([]);
    setVoucherHistoryError("");
    setBookingEvents([]);
    setBookingEventsError("");
    setExpandedEventIds(new Set());
    try {
      const res = await api.get(`/ops/bookings/${id}`);
      setBookingDetail(res.data || null);
      setBookingDetailTab("general");
    } catch (err) {
      console.error("[OpsB2B] loadBookingDetail error:", err);
      setBookingDetail(null);
    } finally {
      setBookingDetailLoading(false);
    }
  }

  async function loadVoucherHistory(id) {
    if (!id) return;
    setVoucherHistoryLoading(true);
    setVoucherHistoryError("");
    try {
      const res = await api.get(`/ops/bookings/${id}/vouchers`);
      setVoucherHistory(res.data?.items || []);
    } catch (err) {
      console.error("[OpsB2B] loadVoucherHistory error:", err);
      setVoucherHistoryError(apiErrorMessage(err));
      setVoucherHistory([]);
    } finally {
      setVoucherHistoryLoading(false);
    }
  }

  async function loadBookingEvents(id) {
    if (!id) return;
    setBookingEventsLoading(true);
    setBookingEventsError("");
    try {
      const res = await api.get(`/ops/bookings/${id}/events?limit=200`);
      setBookingEvents(res.data?.items || []);
    } catch (err) {
      console.error("[OpsB2B] loadBookingEvents error:", err);
      setBookingEventsError(apiErrorMessage(err));
      setBookingEvents([]);
    } finally {
      setBookingEventsLoading(false);
    }
  }

  const hasActiveVoucher = useMemo(
    () => voucherHistory?.some((v) => v.status === "active"),
    [voucherHistory],
  );

  async function loadCases() {
    setCasesLoading(true);
    setCasesError("");
    try {
      const params = new URLSearchParams();
      if (caseStatusFilter) params.set("status", caseStatusFilter);
      if (caseTypeFilter) params.set("type", caseTypeFilter);
      if (caseFrom) params.set("from", caseFrom);
      if (caseTo) params.set("to", caseTo);
      const res = await api.get(`/ops/cases?${params.toString()}`);
      setCases(res.data?.items || []);
    } catch (err) {
      console.error("[OpsB2B] loadCases error:", err);
      setCasesError(apiErrorMessage(err));
    } finally {
      setCasesLoading(false);
    }
  }

  async function loadCaseDetail(id) {
    setSelectedCaseId(id);
    setCaseDetail(null);
    setCaseDetailLoading(true);
    setCaseActionError("");
    try {
      const res = await api.get(`/ops/cases/${id}`);
      setCaseDetail(res.data || null);
    } catch (err) {
      console.error("[OpsB2B] loadCaseDetail error:", err);
      setCaseDetail(null);
    } finally {
      setCaseDetailLoading(false);
    }
  }

  async function handleCaseAction(id, action) {
    setCaseActionLoading(true);
    setCaseActionError("");
    try {
      const res = await api.post(`/ops/cases/${id}/${action}`);
      setCaseDetail((prev) => ({ ...(prev || {}), ...res.data }));
      await loadCases();
    } catch (err) {
      console.error("[OpsB2B] case action error:", err);
      setCaseActionError(apiErrorMessage(err));
    } finally {
      setCaseActionLoading(false);
    }
  }

  const bookingRows = useMemo(() => bookings || [], [bookings]);
  const caseRows = useMemo(() => cases || [], [cases]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">B2B Ops – Booking & Case Queues</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Minimal ops görünümü: B2B booking kuyruğu ve cancel case kuyruğu (approve/reject).
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant={activeTab === "bookings" ? "default" : "outline"}
            size="sm"
            onClick={() => setActiveTab("bookings")}
          >
            Booking Queue
          </Button>
          <Button
            variant={activeTab === "cases" ? "default" : "outline"}
            size="sm"
            onClick={() => setActiveTab("cases")}
          >
            Case Queue
          </Button>
        </div>
      </div>

      {activeTab === "bookings" ? (
        <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,2fr)_minmax(0,1.2fr)] gap-4">
          {/* Left: Booking list */}
          <Card className="rounded-2xl border bg-card shadow-sm">
            <CardHeader className="flex flex-row items-center justify-between gap-4">
              <div>
                <CardTitle className="flex items-center gap-2 text-base">
                  <Search className="h-4 w-4" /> Booking Queue
                </CardTitle>
                <p className="text-xs text-muted-foreground mt-1">
                  Filtrele: status + created_at (ops ekranı için minimal liste).
                </p>
              </div>
              <Button variant="outline" size="icon" onClick={loadBookings} disabled={bookingsLoading}>
                <RefreshCw className={`h-4 w-4 ${bookingsLoading ? "animate-spin" : ""}`} />
              </Button>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="grid grid-cols-1 md:grid-cols-4 gap-3 items-end">
                <div className="space-y-1">
                  <Label className="text-xs">Status</Label>
                  <select
                    className="h-9 rounded-md border bg-background px-2 text-xs"
                    value={bookingStatusFilter}
                    onChange={(e) => setBookingStatusFilter(e.target.value)}
                  >
                    <option value="">Tümü</option>
                    <option value="CONFIRMED">CONFIRMED</option>
                    <option value="CANCELLED">CANCELLED</option>
                    <option value="PENDING">PENDING</option>
                  </select>
                </div>
                <div className="space-y-1">
                  <Label htmlFor="b-from" className="text-xs">
                    Created From
                  </Label>
                  <Input
                    id="b-from"
                    type="datetime-local"
                    className="h-9 text-xs"
                    value={bookingFrom}
                    onChange={(e) => setBookingFrom(e.target.value)}
                  />
                </div>
                <div className="space-y-1">
                  <Label htmlFor="b-to" className="text-xs">
                    Created To
                  </Label>
                  <Input
                    id="b-to"
                    type="datetime-local"
                    className="h-9 text-xs"
                    value={bookingTo}
                    onChange={(e) => setBookingTo(e.target.value)}
                  />
                </div>
                <div className="flex gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="mt-5 w-full"
                    onClick={loadBookings}
                    disabled={bookingsLoading}
                  >
                    Uygula
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="mt-5 text-xs"
                    onClick={() => {
                      const now = new Date();
                      const from = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
                      // datetime-local value (no timezone info) but we feed ISO to backend
                      const toIso = now.toISOString();
                      const fromIso = from.toISOString();
                      setBookingFrom(fromIso.slice(0, 16));
                      setBookingTo(toIso.slice(0, 16));
                      void loadBookings();
                    }}
                  >
                    Son 7 gn
                  </Button>
                </div>
              </div>

              {bookingsError && (
                <div className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-xs text-destructive">
                  <AlertCircle className="h-4 w-4 mt-0.5" />
                  <div>{bookingsError}</div>
                </div>
              )}

              {bookingsLoading ? (
                <div className="flex items-center justify-center py-12 text-sm text-muted-foreground gap-2">
                  <Loader2 className="h-4 w-4 animate-spin" /> Yükleniyor...
                </div>
              ) : bookingRows.length === 0 ? (
                <div className="py-8 text-center text-sm text-muted-foreground">Kriterlere uyan booking bulunamadı.</div>
              ) : (
                <div className="border rounded-xl overflow-hidden">
                  <div className="grid grid-cols-6 gap-2 bg-muted/60 px-3 py-2 text-[11px] font-medium text-muted-foreground">
                    <div>Booking ID</div>
                    <div>Agency</div>
                    <div>Status</div>
                    <div>Created</div>
                    <div>Sell</div>
                    <div>Channel</div>
                  </div>
                  <div className="max-h-[360px] overflow-y-auto text-xs">
                    {bookingRows.map((b) => (
                      <button
                        key={b.booking_id}
                        type="button"
                        className={`grid w-full grid-cols-6 gap-2 border-t px-3 py-2 text-left hover:bg-accent/60 transition ${
                          selectedBookingId === b.booking_id ? "bg-accent/40" : "bg-background"
                        }`}
                        onClick={() => loadBookingDetail(b.booking_id)}
                      >
                        <div className="font-mono truncate" title={b.booking_id}>
                          {b.booking_id}
                        </div>
                        <div
                          className="truncate"
                          title={b.agency_name || b.agency_id || "-"}
                        >
                          {b.agency_name || b.agency_id || "-"}
                        </div>
                        <div className="flex flex-col gap-1">
                          <StatusBadge status={b.status} />
                          {b.credit_status && b.credit_status !== "ok" && (
                            <div className="text-[10px]">
                              {b.credit_status === "near_limit" && (
                                <span className="inline-flex items-center rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-medium text-amber-700">
                                  Limite yakın
                                </span>
                              )}
                              {b.credit_status === "over_limit" && (
                                <span className="inline-flex items-center rounded-full bg-red-50 px-2 py-0.5 text-[10px] font-medium text-red-700">
                                  Limit aşıldı
                                </span>
                              )}
                            </div>
                          )}
                        </div>
                        <div className="truncate" title={String(b.created_at || "-")}> 
                          {formatDate(b.created_at)}
                        </div>
                        <div>
                          {b.sell_price != null ? (
                            <span>
                              {b.sell_price} {b.currency || ""}
                            </span>
                          ) : (
                            "-"
                          )}
                        </div>
                        <div
                          className="truncate"
                          title={b.channel_name || b.channel_id || "-"}
                        >
                          {b.channel_name || b.channel_id || "-"}
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Right: Booking detail */}
          <Card className="rounded-2xl border bg-card shadow-sm">
            <CardHeader>
              <CardTitle className="text-base">Booking Detayı</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {!selectedBookingId && <p className="text-xs text-muted-foreground">Soldaki listeden bir booking seçin.</p>}

              {bookingDetailLoading && (
                <div className="flex items-center justify-center py-8 text-sm text-muted-foreground gap-2">
                  <Loader2 className="h-4 w-4 animate-spin" /> Yükleniyor...
                </div>
              )}

              {bookingDetail && (
                <div className="space-y-3 text-xs">
                  {/* Tabs */}
                  <div className="flex gap-2 border-b pb-2 text-xs">
                    {[
                      ["general", "Genel"],
                      ["snapshots", "Snapshots"],
                      ["voucher", "Voucher"],
                      ["timeline", "Timeline"],
                    ].map(([key, label]) => (
                      <button
                        key={key}
                        type="button"
                        className={`px-2 py-1 rounded-md text-xs ${
                          bookingDetailTab === key
                            ? "bg-primary text-primary-foreground"
                            : "border bg-background text-foreground"
                        }`}
                        onClick={() => {
                          setBookingDetailTab(key);
                          if (!bookingDetail?.booking_id) return;
                          if (key === "voucher") void loadVoucherHistory(bookingDetail.booking_id);
                          if (key === "timeline") void loadBookingEvents(bookingDetail.booking_id);
                        }}
                      >
                        {label}
                      </button>
                    ))}
                  </div>

                  {/* Genel tabı */}
                  {bookingDetailTab === "general" && (
                    <div className="space-y-1">
                      <div className="font-semibold">Genel Bilgiler</div>
                      <div className="grid grid-cols-2 gap-2">
                        <div>
                          <div className="text-muted-foreground">Booking ID</div>
                          <div className="font-mono break-all">{bookingDetail.booking_id}</div>
                        </div>
                        <div>
                          <div className="text-muted-foreground">Status</div>
                          <StatusBadge status={bookingDetail.status} />
                        </div>
                        <div>
                          <div className="text-muted-foreground">Agency</div>
                          <div>{bookingDetail.agency_name || bookingDetail.agency_id || "-"}</div>
                        </div>
                        <div>
                          <div className="text-muted-foreground">Channel</div>
                          <div>{bookingDetail.channel_name || bookingDetail.channel_id || "-"}</div>
                        </div>
                        <div>
                          <div className="text-muted-foreground">Created</div>
                          <div>{formatDateTime(bookingDetail.created_at)}</div>
                        </div>
                        <div>
                          <div className="text-muted-foreground">Updated</div>
                          <div>{formatDateTime(bookingDetail.updated_at)}</div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Snapshots tabı */}
                  {bookingDetailTab === "snapshots" && (
                    <>
                      <div className="space-y-1">
                        <div className="font-semibold">Risk Snapshot (raw JSON)</div>
                        <Textarea
                          value={safeJson(bookingDetail.risk_snapshot)}
                          readOnly
                          className="font-mono text-[11px] h-40"
                        />
                      </div>

                      <div className="space-y-1">
                        <div className="font-semibold">Policy Snapshot (raw JSON)</div>
                        <Textarea
                          value={safeJson(bookingDetail.policy_snapshot)}
                          readOnly
                          className="font-mono text-[11px] h-40"
                        />
                      </div>
                    </>
                  )}

                  {/* Voucher tabı */}
                  {bookingDetailTab === "voucher" && (
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <div className="font-semibold">Voucher</div>
                        <button
                          type="button"
                          className="text-[11px] text-muted-foreground underline-offset-2 hover:underline"
                          onClick={() => loadVoucherHistory(bookingDetail.booking_id)}
                          disabled={voucherHistoryLoading}
                        >
                          Yenile
                        </button>
                      </div>

                      {voucherHistoryLoading && (
                        <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
                          <Loader2 className="h-3 w-3 animate-spin" /> Yükleniyor...
                        </div>
                      )}

                      {voucherHistoryError && (
                        <div className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/5 p-2 text-[11px] text-destructive">
                          <AlertCircle className="h-3 w-3 mt-0.5" />
                          <div>{voucherHistoryError}</div>
                        </div>
                      )}

                      {!voucherHistoryLoading && !voucherHistoryError && voucherHistory.length === 0 && (
                        <div className="text-[11px] text-muted-foreground">
                          Bu booking için henüz voucher yok.
                        </div>
                      )}

                      {/* Generate button */}
                      <div className="flex flex-wrap gap-2 text-[11px]">
                        {!hasActiveVoucher && (
                          <Button
                            type="button"
                            size="sm"
                            className="gap-1 text-xs"
                            disabled={voucherGenerateLoading}
                            onClick={async () => {
                              setVoucherGenerateLoading(true);
                              try {
                                await api.post(`/ops/bookings/${bookingDetail.booking_id}/voucher/generate`);
                                await loadVoucherHistory(bookingDetail.booking_id);
                                await loadBookingDetail(bookingDetail.booking_id);
                              } finally {
                                setVoucherGenerateLoading(false);
                              }
                            }}
                          >
                            {voucherGenerateLoading && <Loader2 className="h-3 w-3 animate-spin" />}
                            Voucher Oluştur
                          </Button>
                        )}
                      </div>

                      {hasActiveVoucher && (
                        <div className="flex flex-wrap items-center gap-3 text-[11px]">
                          <a
                            href={`${process.env.REACT_APP_BACKEND_URL}/api/ops/bookings/${bookingDetail.booking_id}/voucher`}
                            target="_blank"
                            rel="noreferrer"
                            className="text-primary hover:underline"
                          >
                            View HTML
                          </a>
                          <Button
                            type="button"
                            size="sm"
                            variant="outline"
                            className="h-7 px-2 text-[11px]"
                            onClick={() => {
                              const c = bookingDetail.customer || {};
                              setVoucherResendEmail(c.email || "");
                              setVoucherResendMessage("");
                              setVoucherResendError("");
                              setVoucherResendOpen(true);
                            }}
                          >
                            Voucher Gönder
                          </Button>
                        </div>
                      )}

                      {voucherResendOpen && (
                        <div className="mt-3 space-y-2 rounded-md border bg-muted/30 p-3 text-[11px]">
                          <div className="flex items-center justify-between">
                            <div className="font-semibold">Voucher Gönder</div>
                            <button
                              type="button"
                              className="text-xs text-muted-foreground hover:underline"
                              onClick={() => setVoucherResendOpen(false)}
                            >
                              Kapat
                            </button>
                          </div>
                          <div className="grid grid-cols-1 gap-2">
                            <div className="space-y-1">
                              <Label htmlFor="voucher_resend_email" className="text-[11px]">
                                Alıcı Email
                              </Label>
                              <Input
                                id="voucher_resend_email"
                                type="email"
                                className="h-8 text-[11px]"
                                value={voucherResendEmail}
                                onChange={(e) => setVoucherResendEmail(e.target.value)}
                              />
                            </div>
                            <div className="space-y-1">
                              <Label htmlFor="voucher_resend_msg" className="text-[11px]">
                                Mesaj (opsiyonel)
                              </Label>
                              <Textarea
                                id="voucher_resend_msg"
                                className="h-20 text-[11px]"
                                value={voucherResendMessage}
                                onChange={(e) => setVoucherResendMessage(e.target.value)}
                              />
                            </div>
                          </div>

                          {voucherResendError && (
                            <div className="flex items-start gap-2 rounded-md border border-destructive/40 bg-destructive/5 p-2 text-[11px] text-destructive">
                              <AlertCircle className="h-3 w-3 mt-0.5" />
                              <div>{voucherResendError}</div>
                            </div>
                          )}

                          <div className="flex justify-end gap-2">
                            <Button
                              type="button"
                              size="sm"
                              variant="ghost"
                              className="h-7 px-2 text-[11px]"
                              onClick={() => setVoucherResendOpen(false)}
                              disabled={voucherResendLoading}
                            >
                              Vazgeç
                            </Button>
                            <Button
                              type="button"
                              size="sm"
                              className="h-7 px-3 text-[11px]"
                              disabled={voucherResendLoading}
                              onClick={async () => {
                                setVoucherResendError("");
                                if (!voucherResendEmail) {
                                  setVoucherResendError("Lütfen geçerli bir email adresi girin.");
                                  return;
                                }
                                setVoucherResendLoading(true);
                                try {
                                  await api.post(`/ops/bookings/${bookingDetail.booking_id}/voucher/resend`, {
                                    to_email: voucherResendEmail,
                                    message: voucherResendMessage || undefined,
                                  });
                                  setVoucherResendOpen(false);
                                } catch (err) {
                                  console.error("[OpsB2B] voucher resend error:", err);
                                  setVoucherResendError(apiErrorMessage(err));
                                } finally {
                                  setVoucherResendLoading(false);
                                }
                              }}
                            >
                              {voucherResendLoading && <Loader2 className="h-3 w-3 animate-spin" />}
                              Gönder
                            </Button>
                          </div>
                        </div>
                      )}

                      {/* History list */}
                      {voucherHistory.length > 0 && (
                        <div className="mt-2 border rounded-lg overflow-hidden">
                          <div className="grid grid-cols-4 gap-2 bg-muted/60 px-2 py-1 text-[11px] font-medium text-muted-foreground">
                            <div>Version</div>
                            <div>Status</div>
                            <div>Created</div>
                            <div>Created By</div>
                          </div>
                          <div className="max-h-40 overflow-y-auto text-[11px]">
                            {voucherHistory.map((v) => (
                              <div
                                key={v.voucher_id}
                                className="grid grid-cols-4 gap-2 border-t px-2 py-1 bg-background"
                              >
                                <div>{v.version}</div>
                                <div>
                                  <Badge
                                    variant={v.status === "active" ? "secondary" : "outline"}
                                    className="text-[10px]"
                                  >
                                    {v.status}
                                  </Badge>
                                </div>
                                <div>{formatDateTime(v.created_at)}</div>
                                <div className="truncate" title={v.created_by_email || "-"}>
                                  {v.created_by_email || "-"}
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {bookingDetailTab === "timeline" && (
                    <div className="mt-4 space-y-3">
                      <div className="flex items-center justify-between gap-2">
                        <div className="text-sm font-medium">Timeline</div>
                        <button
                          type="button"
                          className="text-xs text-primary hover:underline"
                          onClick={() => void loadBookingEvents(bookingDetail.booking_id)}
                          disabled={bookingEventsLoading}
                        >
                          Yenile
                        </button>
                      </div>

                      {bookingEventsLoading && (
                        <div className="flex items-center gap-2 text-xs text-muted-foreground">
                          <Loader2 className="h-3 w-3 animate-spin" />
                          Yükleniyor
                        </div>
                      )}

                      {!!bookingEventsError && (
                        <div className="rounded-md border border-destructive/50 bg-destructive/5 p-2 text-xs text-destructive">
                          {bookingEventsError}
                        </div>
                      )}

                      {!bookingEventsLoading && !bookingEventsError && bookingEvents.length === 0 && (
                        <div className="text-xs text-muted-foreground">Henüz event yok.</div>
                      )}

                      {bookingEvents.length > 0 && (
                        <div className="space-y-2">
                          {bookingEvents.map((ev, idx) => {
                            const key = `${ev.created_at || "t"}:${ev.type || "x"}:${idx}`;
                            const expanded = expandedEventIds.has(key);
                            return (
                              <div key={key} className="rounded-md border p-3">
                                <div className="flex items-start justify-between gap-3">
                                  <div className="min-w-[140px] text-xs text-muted-foreground">
                                    {formatDateTime(ev.created_at)}
                                  </div>
                                  <div className="flex-1">
                                    <div className="text-xs font-medium">{eventLabel(ev)}</div>
                                    <div className="mt-0.5 text-[11px] text-muted-foreground">
                                      {eventSubline(ev)}
                                    </div>
                                    <div className="mt-1 text-[11px] text-muted-foreground">
                                      {ev.actor?.email ? `${ev.actor.email}` : "-"}
                                      {ev.actor?.role ? ` · ${ev.actor.role}` : ""}
                                      {ev.actor?.agency_id ? ` · ${ev.actor.agency_id}` : ""}
                                    </div>
                                  </div>
                                  <button
                                    type="button"
                                    className="text-xs text-primary hover:underline"
                                    onClick={() => toggleEventExpand(key)}
                                  >
                                    {expanded ? "Kapat" : "Detay"}
                                  </button>
                                </div>

                                {expanded && (
                                  <pre className="mt-3 overflow-auto rounded-md bg-muted/40 p-2 text-[11px] leading-relaxed">
                                    {safeJson({ type: ev.type, actor: ev.actor, meta: ev.meta })}
                                  </pre>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,2fr)_minmax(0,1.2fr)] gap-4">
          {/* Left: Case list */}
          <Card className="rounded-2xl border bg-card shadow-sm">
            <CardHeader className="flex flex-row items-center justify-between gap-4">
              <div>
                <CardTitle className="flex items-center gap-2 text-base">
                  <Search className="h-4 w-4" /> Case Queue
                </CardTitle>
                <p className="text-xs text-muted-foreground mt-1">
                  Cancel caseleri için minimal kuyruk (status/type filtreli).
                </p>
              </div>
              <Button variant="outline" size="icon" onClick={loadCases} disabled={casesLoading}>
                <RefreshCw className={`h-4 w-4 ${casesLoading ? "animate-spin" : ""}`} />
              </Button>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="grid grid-cols-1 md:grid-cols-4 gap-3 items-end">
                <div className="space-y-1">
                  <Label className="text-xs">Status</Label>
                  <select
                    className="h-9 rounded-md border bg-background px-2 text-xs"
                    value={caseStatusFilter}
                    onChange={(e) => setCaseStatusFilter(e.target.value)}
                  >
                    <option value="">Tümü</option>
                    <option value="open">open</option>
                    <option value="pending_approval">pending_approval</option>
                    <option value="closed">closed</option>
                  </select>
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">Type</Label>
                  <select
                    className="h-9 rounded-md border bg-background px-2 text-xs"
                    value={caseTypeFilter}
                    onChange={(e) => setCaseTypeFilter(e.target.value)}
                  >
                    <option value="">Tümü</option>
                    <option value="cancel">cancel</option>
                  </select>
                </div>
                <div className="space-y-1">
                  <Label htmlFor="c-from" className="text-xs">
                    Created From
                  </Label>
                  <Input
                    id="c-from"
                    type="datetime-local"
                    className="h-9 text-xs"
                    value={caseFrom}
                    onChange={(e) => setCaseFrom(e.target.value)}
                  />
                </div>
                <div className="space-y-1">
                  <Label htmlFor="c-to" className="text-xs">
                    Created To
                  </Label>
                  <Input
                    id="c-to"
                    type="datetime-local"
                    className="h-9 text-xs"
                    value={caseTo}
                    onChange={(e) => setCaseTo(e.target.value)}
                  />
                </div>
                <div className="md:col-span-4 flex gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="mt-1 w-full md:w-auto"
                    onClick={loadCases}
                    disabled={casesLoading}
                  >
                    Uygula
                  </Button>
                </div>
              </div>

              {casesError && (
                <div className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-xs text-destructive">
                  <AlertCircle className="h-4 w-4 mt-0.5" />
                  <div>{casesError}</div>
                </div>
              )}

              {casesLoading ? (
                <div className="flex items-center justify-center py-12 text-sm text-muted-foreground gap-2">
                  <Loader2 className="h-4 w-4 animate-spin" /> Yükleniyor...
                </div>
              ) : caseRows.length === 0 ? (
                <div className="py-8 text-center text-sm text-muted-foreground">Kriterlere uyan case bulunamadı.</div>
              ) : (
                <div className="border rounded-xl overflow-hidden">
                  <div className="grid grid-cols-6 gap-2 bg-muted/60 px-3 py-2 text-[11px] font-medium text-muted-foreground">
                    <div>Case ID</div>
                    <div>Type</div>
                    <div>Status</div>
                    <div>Booking</div>
                    <div>Decision</div>
                    <div>Created</div>
                  </div>
                  <div className="max-h-[360px] overflow-y-auto text-xs">
                    {caseRows.map((c) => (
                      <button
                        key={c.case_id}
                        type="button"
                        className={`grid w-full grid-cols-6 gap-2 border-t px-3 py-2 text-left hover:bg-accent/60 transition ${
                          selectedCaseId === c.case_id ? "bg-accent/40" : "bg-background"
                        }`}
                        onClick={() => loadCaseDetail(c.case_id)}
                      >
                        <div className="font-mono truncate" title={c.case_id}>
                          {c.case_id}
                        </div>
                        <div>{c.type || "-"}</div>
                        <div>
                          <StatusBadge status={c.status} />
                        </div>
                        <div className="truncate" title={c.booking_id || "-"}>
                          {c.booking_id || "-"}
                        </div>
                        <div className="truncate" title={c.decision || "-"}>
                          {c.decision || "-"}
                        </div>
                        <div className="truncate" title={String(c.created_at || "-")}>{formatDate(c.created_at)}</div>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Right: Case detail + actions */}
          <Card className="rounded-2xl border bg-card shadow-sm">
            <CardHeader>
              <CardTitle className="text-base">Case Detayı</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {!selectedCaseId && <p className="text-xs text-muted-foreground">Soldaki listeden bir case seçin.</p>}

              {caseDetailLoading && (
                <div className="flex items-center justify-center py-8 text-sm text-muted-foreground gap-2">
                  <Loader2 className="h-4 w-4 animate-spin" /> Yükleniyor...
                </div>
              )}

              {caseDetail && (
                <div className="space-y-3 text-xs">
                  <div className="space-y-1">
                    <div className="font-semibold">Genel Bilgiler</div>
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <div className="text-muted-foreground">Case ID</div>
                        <div className="font-mono break-all">{caseDetail.case_id}</div>
                      </div>
                      <div>
                        <div className="text-muted-foreground">Status</div>
                        <StatusBadge status={caseDetail.status} />
                      </div>
                      <div>
                        <div className="text-muted-foreground">Type</div>
                        <div>{caseDetail.type}</div>
                      </div>
                      <div>
                        <div className="text-muted-foreground">Booking</div>
                        <div className="font-mono break-all">{caseDetail.booking_id || "-"}</div>
                      </div>
                      <div>
                        <div className="text-muted-foreground">Booking Status</div>
                        <div>{caseDetail.booking_status || "-"}</div>
                      </div>
                      <div>
                        <div className="text-muted-foreground">Created</div>
                        <div>{formatDate(caseDetail.created_at)}</div>
                      </div>
                      <div>
                        <div className="text-muted-foreground">Updated</div>
                        <div>{formatDate(caseDetail.updated_at)}</div>
                      </div>
                    </div>
                  </div>

                  <div className="space-y-1">
                    <div className="font-semibold">Cancel Request Payload</div>
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <div className="text-muted-foreground">Reason</div>
                        <div>{caseDetail.reason || "-"}</div>
                      </div>
                      <div>
                        <div className="text-muted-foreground">Amount</div>
                        <div>
                          {caseDetail.requested_refund_amount != null
                            ? `${caseDetail.requested_refund_amount} ${caseDetail.requested_refund_currency || ""}`
                            : "-"}
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <div className="font-semibold">Aksiyonlar</div>
                    {caseDetail.decision && (
                      <div className="flex items-center gap-1 text-[11px] text-muted-foreground">
                        <span className="font-medium">Son karar:</span>
                        <span>{caseDetail.decision}</span>
                        {caseDetail.decision_by_email && (
                          <span className="ml-1">({caseDetail.decision_by_email})</span>
                        )}
                        {caseDetail.decision_at && (
                          <span className="ml-1">{formatDate(caseDetail.decision_at)}</span>
                        )}
                      </div>
                    )}
                    {caseActionError && (
                      <div className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-xs text-destructive">
                        <AlertCircle className="h-4 w-4 mt-0.5" />
                        <div>{caseActionError}</div>
                      </div>
                    )}
                    <div className="flex flex-wrap gap-2">
                      <Button
                        type="button"
                        size="sm"
                        className="gap-1"
                        disabled={caseActionLoading || caseDetail.status === "closed"}
                        onClick={() => handleCaseAction(caseDetail.case_id, "approve")}
                      >
                        {caseActionLoading && <Loader2 className="h-3 w-3 animate-spin" />}
                        <CheckCircle2 className="h-4 w-4" /> Onayla (Approve)
                      </Button>
                      <Button
                        type="button"
                        size="sm"
                        variant="outline"
                        className="gap-1"
                        disabled={caseActionLoading || caseDetail.status === "closed"}
                        onClick={() => handleCaseAction(caseDetail.case_id, "reject")}
                      >
                        {caseActionLoading && <Loader2 className="h-3 w-3 animate-spin" />}
                        <XCircle className="h-4 w-4" /> Reddet (Reject)
                      </Button>
                    </div>
                    <p className="text-[11px] text-muted-foreground">
                      approve → case closed + booking CANCELLED, reject → case closed (booking aynı kalır).
                    </p>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
