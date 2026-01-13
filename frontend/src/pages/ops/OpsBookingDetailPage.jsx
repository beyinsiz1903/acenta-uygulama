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
import { listOpsGuestCasesForBooking } from "../../lib/opsCases";
import { createClickToPayLink } from "../../lib/clickToPay";
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
        const res = await listOpsGuestCasesForBooking(bookingId);
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
                <div className="space-y-2 text-sm">
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
                        if (expires) parts.push(`expires_at=${expires}`);
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
                    listOpsGuestCasesForBooking(bookingId)
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
