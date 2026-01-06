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

function StatusBadge({ status }) {
  if (!status) return <Badge variant="outline">-</Badge>;
  const s = String(status).toUpperCase();
  if (s === "CONFIRMED") return <Badge variant="secondary">CONFIRMED</Badge>;
  if (s === "CANCELLED")
    return (
      <Badge variant="destructive" className="gap-1">
        <XCircle className="h-3 w-3" /> CANCELLED
      </Badge>
    );
  if (s === "PENDING" || s === "PENDING_APPROVAL")
    return (
      <Badge variant="outline" className="gap-1">
        <Loader2 className="h-3 w-3 animate-spin" /> {s}
      </Badge>
    );
  return <Badge variant="outline">{s}</Badge>;
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
    try {
      const res = await api.get(`/ops/bookings/${id}`);
      setBookingDetail(res.data || null);
    } catch (err) {
      console.error("[OpsB2B] loadBookingDetail error:", err);
      setBookingDetail(null);
    } finally {
      setBookingDetailLoading(false);
    }
  }

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
                      setBookingFrom(toIso.slice(0, 16));
                      setBookingTo(now.toISOString().slice(0, 16));
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
                        <div>
                          <StatusBadge status={b.status} />
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
                <div className="space-y-3">
                  <div className="space-y-1 text-xs">
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
                        <div>{bookingDetail.agency_id || "-"}</div>
                      </div>
                      <div>
                        <div className="text-muted-foreground">Channel</div>
                        <div>{bookingDetail.channel_id || "-"}</div>
                      </div>
                      <div>
                        <div className="text-muted-foreground">Created</div>
                        <div>{formatDate(bookingDetail.created_at)}</div>
                      </div>
                      <div>
                        <div className="text-muted-foreground">Updated</div>
                        <div>{formatDate(bookingDetail.updated_at)}</div>
                      </div>
                    </div>
                  </div>

                  <div className="space-y-1 text-xs">
                    <div className="font-semibold">Risk Snapshot (raw JSON)</div>
                    <Textarea
                      value={JSON.stringify(bookingDetail.risk_snapshot || {}, null, 2)}
                      readOnly
                      className="font-mono text-[11px] h-40"
                    />
                  </div>

                  <div className="space-y-1 text-xs">
                    <div className="font-semibold">Policy Snapshot (raw JSON)</div>
                    <Textarea
                      value={JSON.stringify(bookingDetail.policy_snapshot || {}, null, 2)}
                      readOnly
                      className="font-mono text-[11px] h-40"
                    />
                  </div>
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
