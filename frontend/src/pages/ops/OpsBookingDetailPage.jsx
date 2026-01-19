import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Loader2 } from "lucide-react";

import { api, apiErrorMessage } from "../../lib/api";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "../../components/ui/tabs";
import { Card } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import ErrorState from "../../components/ErrorState";
import EmptyState from "../../components/EmptyState";
import OpsGuestCaseDrawer from "../../components/OpsGuestCaseDrawer";
import { listOpsCasesForBooking, createOpsCase } from "../../lib/opsCases";
import { createClickToPayLink } from "../../lib/clickToPay";
import { getCustomer, patchTask } from "../../lib/crm";
import { toast } from "sonner";

function formatDateTime(iso) {
  if (!iso) return "-";
  try {
    return new Date(iso).toLocaleString("tr-TR");
  } catch {
    return String(iso);
  }
}

function StatusPill({ status }) {
  if (!status) return null;
  const tone = String(status).toUpperCase();
  let cls = "bg-muted text-muted-foreground";
  if (tone === "CONFIRMED") cls = "bg-emerald-50 text-emerald-700";
  if (tone === "CANCELLED") cls = "bg-red-50 text-red-700";
  if (tone === "VOUCHERED") cls = "bg-blue-50 text-blue-700";
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium ${cls}`}>
      {tone}
    </span>
  );
}

function CrmBookingSnapshot({ booking, bookingId, onCustomerLinked }) {
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [linking, setLinking] = useState(false);
  const [linkError, setLinkError] = useState("");
  const [customerIdInput, setCustomerIdInput] = useState("");
  const [completingId, setCompletingId] = useState("");

  const hasCustomer = Boolean(booking && booking.customer_id);
  const customerId = booking?.customer_id || "";

  async function loadDetail(id) {
    if (!id) return;
    setLoading(true);
    setError("");
    try {
      const res = await getCustomer(id);
      setDetail(res || null);
    } catch (e) {
      setError(e.message || apiErrorMessage(e.raw || e));
      setDetail(null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!hasCustomer) {
      setDetail(null);
      setError("");
      return;
    }
    loadDetail(customerId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [customerId, hasCustomer]);

  async function handleLink(e) {
    e.preventDefault();
    if (!bookingId) return;
    setLinking(true);
    setLinkError("");
    try {
      const payloadCustomerId = customerIdInput.trim() || null;
      const res = await api.patch(`/ops/bookings/${bookingId}/customer`, {
        customer_id: payloadCustomerId,
      });
      const nextId = res.data?.customer_id || null;
      if (onCustomerLinked) {
        onCustomerLinked(nextId);
      }
      if (nextId) {
        setCustomerIdInput(nextId);
        await loadDetail(nextId);
        toast.success("M\u00fc\u015fteri ba\u011fland\u0131.");
      } else {
        setDetail(null);
        toast.success("M\u00fc\u015fteri ba\u011f\u0131 kald\u0131r\u0131ld\u0131.");
      }
    } catch (e) {
      const msg = apiErrorMessage(e);
      setLinkError(msg);
      toast.error(msg);
    } finally {
      setLinking(false);
    }
  }

  async function handleCompleteTask(taskId) {
    if (!taskId) return;
    setCompletingId(taskId);
    try {
      await patchTask(taskId, { status: "done" });
      if (customerId) {
        await loadDetail(customerId);
      }
      toast.success("G\u00f6rev tamamland\u0131.");
    } catch (e) {
      const msg = e.message || apiErrorMessage(e.raw || e);
      toast.error(msg);
    } finally {
      setCompletingId("");
    }
  }

  return (
    <div className="mt-4 border rounded-xl p-3 bg-muted/30">
      <div className="flex items-center justify-between gap-2 mb-2">
        <div>
          <div className="text-xs font-semibold text-muted-foreground">CRM {"\u00d6zeti"}</div>
          <div className="text-[11px] text-muted-foreground">
            {"M\u00fc\u015fteri kart\u0131, a\u00e7\u0131k f\u0131rsatlar ve g\u00f6revleri tek bak\u0131\u015fta g\u00f6r\u00fcn."}
          </div>
        </div>
      </div>

      {!hasCustomer ? (
        <div className="space-y-2 text-xs">
          <div className="text-muted-foreground">
            {"Bu rezervasyona hen\u00fcz bir m\u00fc\u015fteri ba\u011fl\u0131 de\u011fil."}
          </div>
          <form onSubmit={handleLink} className="flex flex-col sm:flex-row gap-2 items-start sm:items-center mt-1">
            <input
              type="text"
              value={customerIdInput}
              onChange={(e) => setCustomerIdInput(e.target.value)}
              placeholder="cust_..."
              className="w-full sm:w-48 rounded-md border px-2 py-1 text-xs"
            />
            <Button
              type="submit"
              size="xs"
              disabled={linking || !bookingId}
              className="text-xs"
            >
              {linking ? "Ba\u011flan\u0131yor..." : "M\u00fc\u015fteri ba\u011fla"}
            </Button>
          </form>
          {linkError && <div className="text-[11px] text-red-600">{linkError}</div>}
        </div>
      ) : (
        <div className="space-y-3 text-xs">
          {loading ? (
            <div className="text-muted-foreground">{"CRM bilgileri y\u00fckleniyor..."}</div>
          ) : error ? (
            <div className="text-red-600 text-[11px]">{error}</div>
          ) : !detail ? (
            <div className="text-muted-foreground">{"CRM kayd\u0131 bulunamad\u0131."}</div>
          ) : (
            <>
              {/* Customer card */}
              <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-2">
                <div className="space-y-1">
                  <div className="text-sm font-medium">{detail.customer?.name || "M\u00fc\u015fteri"}</div>
                  <div className="flex flex-wrap gap-1">
                    {(detail.customer?.tags || []).slice(0, 5).map((tag) => (
                      <span
                        key={tag}
                        className="inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] text-muted-foreground"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                  <div className="text-[11px] text-muted-foreground">
                    {(() => {
                      const contacts = detail.customer?.contacts || [];
                      if (!contacts.length) return "Birincil ileti\u015fim bilgisi yok.";
                      const primary = contacts.find((c) => c.is_primary) || contacts[0];
                      const typeLabel = primary.type === "email" ? "E-posta" : "Telefon";
                      return `${typeLabel}: ${primary.value}`;
                    })()}
                  </div>
                </div>
                <div className="flex flex-col items-end gap-1">
                  <Button
                    type="button"
                    size="xs"
                    variant="outline"
                    className="text-[11px]"
                    onClick={() => {
                      window.open(`/app/crm/customers/${customerId}`, "_blank");
                    }}
                  >
                    {"CRM'de a\u00e7"}
                  </Button>
                </div>
              </div>

              {/* Open deals & tasks */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="border rounded-lg p-2 bg-background">
                  <div className="text-[11px] font-semibold mb-1">{"A\u00e7\u0131k F\u0131rsatlar"}</div>
                  {(detail.open_deals || []).length === 0 ? (
                    <div className="text-[11px] text-muted-foreground">
                      {"Bu m\u00fc\u015fteri i\u00e7in a\u00e7\u0131k f\u0131rsat yok."}
                    </div>
                  ) : (
                    <ul className="space-y-1">
                      {detail.open_deals.slice(0, 3).map((deal) => (
                        <li key={deal.id || deal.title} className="border rounded-md px-2 py-1">
                          <div className="text-[11px] font-medium truncate">
                            {deal.title || deal.id}
                          </div>
                          <div className="flex items-center justify-between gap-2 mt-0.5 text-[10px] text-muted-foreground">
                            <span>{deal.stage || "stage"}</span>
                            <span>
                              {deal.amount != null ? `${deal.amount} ${deal.currency || ""}` : ""}
                            </span>
                          </div>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>

                <div className="border rounded-lg p-2 bg-background">
                  <div className="text-[11px] font-semibold mb-1">{"A\u00e7\u0131k G\u00f6revler"}</div>
                  {(detail.open_tasks || []).length === 0 ? (
                    <div className="text-[11px] text-muted-foreground">
                      {"Bu m\u00fc\u015fteri i\u00e7in a\u00e7\u0131k g\u00f6rev yok."}
                    </div>
                  ) : (
                    <ul className="space-y-1">
                      {detail.open_tasks.slice(0, 3).map((task) => (
                        <li key={task.id || task.title} className="border rounded-md px-2 py-1 flex items-center justify-between gap-2">
                          <div className="min-w-0">
                            <div className="text-[11px] font-medium truncate">{task.title}</div>
                            <div className="text-[10px] text-muted-foreground flex flex-wrap gap-1 mt-0.5">
                              <span>{task.priority || "normal"}</span>
                              {task.due_date && (
                                <span>
                                  {new Date(task.due_date).toLocaleDateString("tr-TR")}
                                </span>
                              )}
                            </div>
                          </div>
                          <Button
                            type="button"
                            size="xs"
                            variant="outline"
                            className="text-[10px] whitespace-nowrap"
                            disabled={completingId === task.id}
                            onClick={() => handleCompleteTask(task.id)}
                          >
                            {completingId === task.id ? "Tamamlan\u0131yor..." : "Tamamla"}
                          </Button>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}

function ParasutPushPanel({ bookingId }) {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [pushing, setPushing] = useState(false);
  const [idempotentHint, setIdempotentHint] = useState("");

  async function loadLogs() {
    if (!bookingId) {
      setLogs([]);
      setError("");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const res = await api.get("/admin/finance/parasut/pushes", {
        params: { booking_id: bookingId, limit: 50 },
      });
      setLogs(res.data?.items || []);
    } catch (e) {
      setError(apiErrorMessage(e));
      setLogs([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadLogs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [bookingId]);

  async function handlePush() {
    if (!bookingId) return;
    setPushing(true);
    try {
      const res = await api.post("/admin/finance/parasut/push-invoice-v1", {
        booking_id: bookingId,
      });
      const data = res.data || {};
      const status = data.status;
      const reason = data.reason;

      if (status === "success") {
        toast.success("Paraşüt'e fatura push'u başarılı.");
      } else if (status === "skipped") {
        toast.info(reason ? `İşlem atlandı: ${reason}` : "İşlem atlandı.");
      } else if (status === "failed") {
        toast.error(reason ? `Paraşüt push'u başarısız: ${reason}` : "Paraşüt push'u başarısız oldu.");
      } else {
        toast.success("Paraşüt push isteği işlendi.");
      }

      await loadLogs();
    } catch (e) {
      toast.error(apiErrorMessage(e));
    } finally {
      setPushing(false);
    }
  }

  return (
    <div className="border rounded-xl p-3 bg-muted/30 space-y-2">
      <div className="flex items-center justify-between gap-2">
        <div className="space-y-0.5">
          <div className="text-xs font-semibold text-muted-foreground">Paraşüt Fatura Push</div>
          <div className="text-[11px] text-muted-foreground">
            Bu booking&apos;i Paraşüt&apos;e fatura olarak göndermek için kullanılır. Sadece yetkili admin kullanıcılar
            erişebilir.
          </div>
        </div>
        <Button
          size="sm"
          variant="outline"
          disabled={!bookingId || pushing}
          onClick={handlePush}
        >
          {pushing ? "Gönderiliyor..." : "Paraşüt'e gönder"}
        </Button>
      </div>

      {loading && (
        <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
          <Loader2 className="h-3 w-3 animate-spin" /> Paraşüt logları yükleniyor...
        </div>
      )}
      {!loading && error && <ErrorState description={error} />}

      {!loading && !error && logs.length === 0 && (
        <div className="text-[11px] text-muted-foreground">
          Bu booking için henüz Paraşüt push logu yok.
        </div>
      )}

      {!loading && !error && logs.length > 0 && (
        <div className="mt-1 rounded-lg border overflow-hidden text-[11px]">
          <table className="min-w-full">
            <thead className="bg-muted/40 text-[10px] text-muted-foreground">
              <tr>
                <th className="px-2 py-1 text-left">Durum</th>
                <th className="px-2 py-1 text-left">Tip</th>
                <th className="px-2 py-1 text-left">Deneme</th>
                <th className="px-2 py-1 text-left">Son hata</th>
                <th className="px-2 py-1 text-left">Güncellendi</th>
                <th className="px-2 py-1 text-right">Aksiyon</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((log) => {
                const status = log.status;
                let statusLabel = status;
                let statusClass = "bg-muted text-muted-foreground";
                if (status === "success") {
                  statusLabel = "Başarılı";
                  statusClass = "bg-emerald-50 text-emerald-700";
                } else if (status === "failed") {
                  statusLabel = "Hatalı";
                  statusClass = "bg-red-50 text-red-700";
                } else if (status === "pending") {
                  statusLabel = "Beklemede";
                  statusClass = "bg-amber-50 text-amber-700";
                }

                return (
                  <tr key={log.id} className="border-t">
                    <td className="px-2 py-1">
                      <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] ${statusClass}`}>
                        {statusLabel}
                      </span>
                    </td>
                    <td className="px-2 py-1 font-mono">{log.push_type}</td>
                    <td className="px-2 py-1 font-mono">{log.attempt_count}</td>
                    <td className="px-2 py-1 max-w-xs truncate" title={log.last_error || "-"}>
                      {log.last_error || "-"}
                    </td>
                    <td className="px-2 py-1 text-muted-foreground">
                      {log.updated_at ? formatDateTime(log.updated_at) : "-"}
                    </td>
                    <td className="px-2 py-1 text-right">
                      {log.status === "failed" && (
                        <Button
                          type="button"
                          size="xs"
                          variant="outline"
                          disabled={pushing}
                          onClick={handlePush}
                        >
                          Tekrar dene
                        </Button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}


export default function OpsBookingDetailPage() {
  const { bookingId } = useParams();
  const navigate = useNavigate();

  const [booking, setBooking] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [ledgerSummary, setLedgerSummary] = useState(null);
  const [ledgerLoading, setLedgerLoading] = useState(false);
  const [ledgerError, setLedgerError] = useState("");

  const [events, setEvents] = useState([]);
  const [eventsLoading, setEventsLoading] = useState(false);
  const [eventsError, setEventsError] = useState("");

  const [cases, setCases] = useState([]);
  const [creatingCase, setCreatingCase] = useState(false);
  const [createCaseError, setCreateCaseError] = useState("");
  const [newCaseType, setNewCaseType] = useState("cancel");
  const [newCaseNote, setNewCaseNote] = useState("");

  const handleCreateCase = async (e) => {
    e.preventDefault();
    if (!bookingId) return;
    setCreatingCase(true);
    setCreateCaseError("");
    try {
      const payload = {
        booking_id: bookingId,
        type: newCaseType,
        source: "ops_panel",
        status: "open",
        note: newCaseNote || undefined,
      };
      await createOpsCase(payload);
      setNewCaseNote("");
      setNewCaseType("cancel");
      await (async () => {
        try {
          const res = await listOpsCasesForBooking(bookingId);
          setCases(res.items || []);
        } catch (err) {
          setCasesError(apiErrorMessage(err));
        }
      })();
    } catch (err) {
      setCreateCaseError(apiErrorMessage(err));
    } finally {
      setCreatingCase(false);
    }
  };

  const [casesLoading, setCasesLoading] = useState(false);
  const [casesError, setCasesError] = useState("");
  const [selectedCaseId, setSelectedCaseId] = useState(null);

  const [activeTab, setActiveTab] = useState("summary");

  useEffect(() => {
    if (!bookingId) return;

    async function loadBooking() {
      setLoading(true);
      setError("");
      try {
        const res = await api.get(`/ops/bookings/${bookingId}`);
        setBooking(res.data || null);
      } catch (e) {
        setError(apiErrorMessage(e));
        setBooking(null);
      } finally {
        setLoading(false);
      }
    }

    async function loadLedger() {
      setLedgerLoading(true);
      setLedgerError("");
      try {
        const res = await api.get(`/ops/finance/bookings/${bookingId}/ledger-summary`);
        setLedgerSummary(res.data || null);
      } catch (e) {
        setLedgerError(apiErrorMessage(e));
        setLedgerSummary(null);
      } finally {
        setLedgerLoading(false);
      }
    }

    async function loadEventsLocal() {
      setEventsLoading(true);
      setEventsError("");
      try {
        const res = await api.get(`/ops/bookings/${bookingId}/events`, { params: { limit: 200 } });
        setEvents(res.data?.items || []);
      } catch (e) {
        setEventsError(apiErrorMessage(e));
        setEvents([]);
      } finally {
        setEventsLoading(false);
      }
    }

    async function loadCasesLocal() {
      setCasesLoading(true);
      setCasesError("");
      try {
        const res = await listOpsCasesForBooking(bookingId);
        setCases(res.items || []);
      } catch (e) {
        setCasesError(apiErrorMessage(e));
        setCases([]);
      } finally {
        setCasesLoading(false);
      }
    }

    loadBooking();
    loadLedger();
    loadEventsLocal();
    loadCasesLocal();
  }, [bookingId]);

  const title = booking?.booking_id || bookingId;

  return (
    <div className="p-4 md:p-6 max-w-6xl mx-auto space-y-4">
      <div className="flex items-center justify-between gap-2">
        <div className="space-y-1">
          <h1 className="text-xl font-semibold">Ops Booking Detail</h1>
          <p className="text-xs text-muted-foreground">
            Booking, ödemeler, ledger, timeline ve guest case&apos;ler için tek merkez ops görünümü.
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => navigate(-1)}
        >
          Geri
        </Button>
      </div>

      <Card className="p-4 space-y-3">
        {loading ? (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" /> Booking yükleniyor...
          </div>
        ) : error ? (
          <ErrorState description={error} />
        ) : !booking ? (
          <EmptyState
            title="Booking bulunamadı"
            description="URL&apos;deki bookingId hatalı olabilir veya bu organizasyona ait değildir."
          />
        ) : (
          <>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="space-y-1">
                <div className="text-sm font-medium">{title}</div>
                <div className="text-xs text-muted-foreground flex flex-wrap gap-2">
                  {booking.agency_id && <span>Agency: {booking.agency_id}</span>}
                  {booking.channel_id && <span>Channel: {booking.channel_id}</span>}
                  {booking.currency && booking.amounts?.sell != null && (
                    <span>
                      Tutar: {booking.amounts.sell} {booking.currency}
                    </span>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <StatusPill status={booking.status} />
              </div>
            </div>

            <CrmBookingSnapshot
              booking={booking}
              bookingId={bookingId}
              onCustomerLinked={(nextCustomerId) => {
                setBooking((prev) => (prev ? { ...prev, customer_id: nextCustomerId } : prev));
              }}
            />

            <Tabs value={activeTab} onValueChange={setActiveTab} className="mt-2">
              <TabsList className="mb-3">
                <TabsTrigger value="summary">Summary</TabsTrigger>
                <TabsTrigger value="payments">Payments</TabsTrigger>
                <TabsTrigger value="ledger">Ledger</TabsTrigger>
                <TabsTrigger value="timeline">Timeline</TabsTrigger>
                <TabsTrigger value="cases">Cases</TabsTrigger>
              </TabsList>

              <TabsContent value="summary" className="mt-0">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
                  <div>
                    <div className="text-xs text-muted-foreground">Booking ID</div>
                    <div className="font-mono break-all">{booking.booking_id}</div>
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground">Status</div>
                    <div>{booking.status}</div>
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground">Created</div>
                    <div>{formatDateTime(booking.created_at)}</div>
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground">Updated</div>
                    <div>{formatDateTime(booking.updated_at)}</div>
                  </div>
                </div>
              </TabsContent>

              <TabsContent value="payments" className="mt-0">
                <div className="space-y-4 text-sm">
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="space-y-0.5">
                        <div className="text-xs text-muted-foreground">Click-to-Pay</div>
                        <div className="text-[11px] text-muted-foreground">
                          Misafire ödeme linki göndererek kalan tahsilatı tek adımda tamamlayın.
                        </div>
                      </div>
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={!booking}
                        onClick={async () => {
                          if (!booking) return;
                          try {
                            const res = await createClickToPayLink(booking.booking_id || bookingId);
                            if (!res.ok) {
                              if (res.reason === "nothing_to_collect") {
                                toast.info("Kalan tahsilat yok.");
                              } else {
                                toast.error("Ödeme linki oluşturulamadı.");
                              }
                              return;
                            }
                            const origin = window.location.origin;
                            const url = `${origin}${res.url}`;
                            await navigator.clipboard.writeText(url).catch(() => {});
                            toast.success("Ödeme linki oluşturuldu ve panoya kopyalandı.");
                          } catch (e) {
                            toast.error(apiErrorMessage(e));
                          }
                        }}
                      >
                        Ödeme linki oluştur
                      </Button>
                    </div>
                    <p className="text-[11px] text-muted-foreground">
                      Link, 24 saat sonra otomatik olarak geçersiz hale gelir. Ödeme başarıyla tamamlandığında
                      Stripe webhook ve ledger akışı mevcut payment-state görünümünü güncelleyecektir.
                    </p>
                  </div>

                  <ParasutPushPanel bookingId={booking?.booking_id || bookingId} />
                </div>
              </TabsContent>

              <TabsContent value="ledger" className="mt-0">
                {ledgerLoading && (
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Loader2 className="h-4 w-4 animate-spin" /> Ledger özeti yükleniyor...
                  </div>
                )}
                {!ledgerLoading && ledgerError && <ErrorState description={ledgerError} />}
                {!ledgerLoading && !ledgerError && ledgerSummary && (
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div>
                      <div className="text-xs text-muted-foreground">Para Birimi</div>
                      <div>{ledgerSummary.currency}</div>
                    </div>
                    <div>
                      <div className="text-xs text-muted-foreground">Kayıt Sayısı</div>
                      <div>{ledgerSummary.postings_count}</div>
                    </div>
                    <div>
                      <div className="text-xs text-muted-foreground">Toplam Debit</div>
                      <div>{Number(ledgerSummary.total_debit).toFixed(2)}</div>
                    </div>
                    <div>
                      <div className="text-xs text-muted-foreground">Toplam Credit</div>
                      <div>{Number(ledgerSummary.total_credit).toFixed(2)}</div>
                    </div>
                    <div className="col-span-2">
                      <div className="text-xs text-muted-foreground">Fark (Debit - Credit)</div>
                      <div>{Number(ledgerSummary.diff).toFixed(4)}</div>
                    </div>
                  </div>
                )}
                {!ledgerLoading && !ledgerError && !ledgerSummary && (
                  <EmptyState
                    title="Ledger kaydı yok"
                    description="Bu booking için henüz finansal kayıt oluşmamış."
                  />
                )}
              </TabsContent>

              <TabsContent value="timeline" className="mt-0">
                {eventsLoading && (
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Loader2 className="h-4 w-4 animate-spin" /> Timeline yükleniyor...
                  </div>
                )}
                {!eventsLoading && eventsError && <ErrorState description={eventsError} />}
                {!eventsLoading && !eventsError && events.length === 0 && (
                  <EmptyState
                    title="Event yok"
                    description="Bu booking için henüz event üretilmemiş olabilir."
                  />
                )}
                {!eventsLoading && !eventsError && events.length > 0 && (
                  <ul className="space-y-2 text-xs">
                    {events.map((ev, idx) => {
                      const eventType = ev.type || ev.event || "Event";
                      const meta = ev.meta || {};

                      let title = eventType;
                      let subtitle = "";

                      if (eventType === "MY_BOOKING_TOKEN_CREATED") {
                        const channel = meta.channel || "unknown";
                        const prefix = meta.token_hash_prefix || "";
                        const expires = meta.expires_at || meta.expiry || "";
                        title = `MyBooking token oluşturuldu (${channel})`;
                        const parts = [];
                        if (prefix) parts.push(`prefix=${prefix}`);
                        if (expires) parts.push(`expires_at=${formatDateTime(expires)}`);
                        subtitle = parts.join(" • ");
                      } else if (eventType === "MY_BOOKING_TOKEN_ROTATED") {
                        const rootPrefix = meta.root_hash_prefix || "";
                        const rotatedPrefix = meta.rotated_hash_prefix || "";
                        title = "MyBooking token rotate edildi";
                        if (rootPrefix && rotatedPrefix) {
                          subtitle = `${rootPrefix} → ${rotatedPrefix}`;
                        }
                      } else if (eventType === "MY_BOOKING_TOKEN_ACCESSED") {
                        const tokenType = meta.token_type || "unknown";
                        const hasIp = meta.has_ip ? "var" : "yok";
                        const hasUa = meta.has_ua ? "var" : "yok";
                        const sampled = meta.sampled === true;
                        title = `MyBooking erişildi (${tokenType})`;
                        subtitle = `IP:${hasIp} • UA:${hasUa} • sampled=${sampled ? "true" : "false"}`;
                      }

                      const when = ev.created_at || ev.occurred_at;

                      return (
                        <li
                          key={`${eventType}-${ev.created_at || ev.occurred_at || idx}`}
                          className="border-l pl-2 ml-1"
                        >
                          <div className="flex items-center justify-between gap-2">
                            <span className="font-medium">{title}</span>
                            <span className="text-[11px] text-muted-foreground">
                              {formatDateTime(when)}
                            </span>
                          </div>
                          {subtitle && (
                            <div className="mt-0.5 text-[11px] text-muted-foreground">
                              {subtitle}
                            </div>
                          )}
                        </li>
                      );
                    })}
                  </ul>
                )}
              </TabsContent>

              <TabsContent value="cases" className="mt-0">
                {casesLoading && (
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Loader2 className="h-4 w-4 animate-spin" /> Guest case&apos;ler yükleniyor...
                  </div>
                )}
                {!casesLoading && casesError && <ErrorState description={casesError} />}
                {!casesLoading && !casesError && cases.length === 0 && (
                  <EmptyState
                    title="Açık guest case yok"
                    description="Bu booking için şu anda open status&apos;te guest case bulunmuyor."
                  />
                )}
                {!casesLoading && !casesError && cases.length > 0 && (
                  <div className="border rounded-xl overflow-hidden text-xs">
                    <div className="grid grid-cols-4 gap-2 bg-muted/60 px-3 py-2 text-[11px] font-medium text-muted-foreground">
                      <div>Case ID</div>
                      <div>Type</div>
                      <div>Kaynak</div>
                      <div>Oluşturulma</div>
                    </div>
                    <div className="max-h-64 overflow-y-auto">
                      {cases.map((c) => (
                        <button
                          key={c.case_id}
                          type="button"
                          className="grid w-full grid-cols-4 gap-2 border-t px-3 py-2 text-left hover:bg-accent/60"
                          onClick={() => setSelectedCaseId(c.case_id)}
                        >
                          <div className="font-mono truncate" title={c.case_id}>
                            {c.case_id}
                          </div>
                          <div>{c.type || "-"}</div>
                          <div>{c.source === "guest_portal" ? "Guest portal" : c.source || "-"}</div>
                          <div className="truncate" title={String(c.created_at || "-")}>
                            {formatDateTime(c.created_at)}
                          </div>
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                <OpsGuestCaseDrawer
                  caseId={selectedCaseId}
                  open={Boolean(selectedCaseId)}
                  onClose={() => setSelectedCaseId(null)}
                  onClosed={() => {
                    // Close sonrası listeyi tazele
                    if (!bookingId) return;
                    listOpsCasesForBooking(bookingId)
                      .then((res) => setCases(res.items || []))
                      .catch(() => {});
                  }}
                />
              </TabsContent>
            </Tabs>
          </>
        )}
      </Card>
    </div>
  );
}
