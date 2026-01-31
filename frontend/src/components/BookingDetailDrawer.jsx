import React, { useEffect, useMemo, useRef, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetFooter } from "./ui/sheet";
import { Button } from "./ui/button";
import { Badge } from "./ui/badge";
import { Separator } from "./ui/separator";
import { toast } from "sonner";
import { buildBookingCopyText } from "../utils/buildBookingCopyText";
import { api, apiErrorMessage, getUser } from "../lib/api";
import { Loader2 } from "lucide-react";
import { makeIdempotencyKey } from "../lib/payments";

import EmptyState from "../components/EmptyState";
import ErrorState from "../components/ErrorState";

function StatusBadge({ status_tr, status }) {
  if (!status_tr && !status) return null;
  const tone = (status || "").toLowerCase();
  let variant = "outline";
  if (tone === "confirmed") variant = "default";
  if (tone === "completed") variant = "secondary";
  if (tone === "cancelled") variant = "destructive";

  return <Badge variant={variant}>{status_tr || status}</Badge>;
}

export function BookingDetailDrawer({ bookingId, mode = "agency", open, onOpenChange, onBookingChanged }) {
  const [booking, setBooking] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [voucherToken, setVoucherToken] = useState(null);
  const [voucherLoading, setVoucherLoading] = useState(false);
  const [ledgerSummary, setLedgerSummary] = useState(null);
  const [ledgerLoading, setLedgerLoading] = useState(false);
  const [ledgerError, setLedgerError] = useState("");
  const [cancelLoading, setCancelLoading] = useState(false);
  const [amendMode, setAmendMode] = useState(false);
  const [amendCheckIn, setAmendCheckIn] = useState("");
  const [amendCheckOut, setAmendCheckOut] = useState("");
  const [amendRequestId, setAmendRequestId] = useState("");
  const [amendProposal, setAmendProposal] = useState(null);
  const [amendQuoteLoading, setAmendQuoteLoading] = useState(false);
  const [amendConfirmLoading, setAmendConfirmLoading] = useState(false);
  const [amendError, setAmendError] = useState("");

  const [activeTab, setActiveTab] = useState("details");
  const navigate = useNavigate();

  // Check if user has privileged role for payment actions
  const user = getUser();
  const isPrivileged = user?.roles?.some((r) => ["admin", "ops", "super_admin"].includes(r));

  const [paymentState, setPaymentState] = useState(null);
  const [paymentActionLoading, setPaymentActionLoading] = useState(false);
  const [paymentActionStatus, setPaymentActionStatus] = useState("");

  const [paymentLoading, setPaymentLoading] = useState(false);
  const [paymentError, setPaymentError] = useState("");

  const [paymentAmountInput, setPaymentAmountInput] = useState("");
  const [lastPaymentIntentId, setLastPaymentIntentId] = useState("");

  const [events, setEvents] = useState([]);
  const [eventsLoading, setEventsLoading] = useState(false);
  const [eventsError, setEventsError] = useState("");
  const [eventsLoaded, setEventsLoaded] = useState(false);
  const eventsReqSeq = useRef(0);

  const [pollingPayment, setPollingPayment] = useState(false);
  const pollingTimerRef = useRef(null);
  const pollingStartedAtRef = useRef(null);

  function normalizeEvents(payload) {
    const arr = Array.isArray(payload) ? payload : (payload?.items || []);
    return arr.map((e) => ({
      id: e.id || e._id || `${e.event || e.type}-${e.occurred_at || e.created_at || ""}`,
      type: e.type || e.event || "EVENT",
      occurred_at: e.occurred_at || e.created_at || null,
      meta: e.meta || {},
      created_by: e.created_by || null,
      before: e.before || null,
      after: e.after || null,
      raw: e.raw || null,
    }));
  }

  const sortedEvents = useMemo(() => {
    const copy = [...events];
    copy.sort((a, b) => {
      const ta = a.occurred_at ? Date.parse(a.occurred_at) : 0;
      const tb = b.occurred_at ? Date.parse(b.occurred_at) : 0;
      return ta - tb;
    });
    return copy;
  }, [events]);

  function formatDateTime(iso) {
    if (!iso) return "—";
    try {
      return new Intl.DateTimeFormat("tr-TR", {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
      }).format(new Date(iso));
    } catch {
      return iso;
    }
  }

  function mapEventTypeLabel(type) {
    switch (type) {
      case "BOOKING_CREATED":
        return "Rezervasyon Oluşturuldu";
      case "BOOKING_CONFIRMED":
        return "Rezervasyon Onaylandı";
      case "BOOKING_CANCELLED":
        return "Rezervasyon İptal Edildi";
      case "BOOKING_AMENDED":
        return "Rezervasyon Değiştirildi";
      case "PAYMENT_CAPTURED":
        return "Ödeme Alındı";
      case "PAYMENT_REFUNDED":
        return "Ödeme İade Edildi";
      case "VOUCHER_ISSUED":
        return "Voucher Oluşturuldu";
      default:
        return type || "Event";
    }
  }

  function renderEventMeta(ev) {
    const meta = ev.meta || {};
    const lines = [];

    const actorEmail =
      meta.actor_email ||
      ev.created_by?.email ||
      meta.created_by_email;

    if (actorEmail) lines.push(`Kullanıcı: ${actorEmail}`);

    const amount =
      meta.amount_cents ?? meta.amount_minor ?? meta.amount;
    const currency = meta.currency;

    if (amount != null && currency) {
      lines.push(`Tutar: ${(Number(amount) / 100).toFixed(2)} ${currency}`);
    }

    if (meta.reason) lines.push(`Sebep: ${meta.reason}`);
    if (meta.amend_id) lines.push(`Amend: ${meta.amend_id}`);

    if (!lines.length) return null;

    return (
      <p className="text-xs text-muted-foreground">
        {lines.join(" · ")}
      </p>
    );
  }

  const generateAmendRequestId = () =>
    `amend_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;

  const PAYMENT_STATE_ENDPOINT = (id) => `/ops/finance/bookings/${id}/payment-state`;

  const loadPaymentState = useCallback(async (id) => {
    if (!id) return;
    setPaymentLoading(true);
    setPaymentError("");
    try {
      const resp = await api.get(PAYMENT_STATE_ENDPOINT(id));
      setPaymentState(resp.data || null);
    } catch (e) {
      setPaymentError(apiErrorMessage(e));
      setPaymentState(null);
    } finally {
      setPaymentLoading(false);
    }
  }, []);

  const stopPaymentPolling = useCallback(() => {
    if (pollingTimerRef.current) {
      clearInterval(pollingTimerRef.current);
      pollingTimerRef.current = null;
    }
    setPollingPayment(false);
  }, []);

  const startPaymentPolling = useCallback(
    (id, { expectedEventType = "PAYMENT_CAPTURED", timeoutMs = 30_000 } = {}) => {
      if (!id) return;
      stopPaymentPolling();
      pollingStartedAtRef.current = Date.now();
      setPollingPayment(true);

      const tick = async () => {
        const nowTs = Date.now();
        if (!id) {
          stopPaymentPolling();
          return;
        }

        try {
          await loadPaymentState(id);
          await loadEvents(id);
        } catch {
          // errors are handled inside loaders
        }

        const aggregate = paymentState?.aggregate;
        const status = aggregate?.status;

        const isTerminal = ["succeeded", "canceled", "failed", "requires_payment_method"].includes(
          (status || "").toLowerCase(),
        );
        const hasExpectedEvent = events.some((ev) => ev.type === expectedEventType);
        const elapsed = nowTs - (pollingStartedAtRef.current || nowTs);

        if (isTerminal || hasExpectedEvent || elapsed >= timeoutMs) {
          stopPaymentPolling();
          if (elapsed >= timeoutMs && !isTerminal && !hasExpectedEvent) {
            toast.message("Webhook gecikiyor", {
              description:
                "İşlem Stripe tarafında alınmış olabilir, webhook henüz işlenmedi. Birazdan tekrar deneyin.",
            });
          }
        }
      };

      tick();
      pollingTimerRef.current = setInterval(tick, 5_000);
    },
    [bookingId, events, loadEvents, loadPaymentState, paymentState, stopPaymentPolling],
  );

  const handleOpenAmend = () => {
    if (!bookingId || !booking) return;
    if (booking.status !== "CONFIRMED") return;
    setAmendMode(true);
    setAmendError("");
    setAmendProposal(null);
    setAmendRequestId(generateAmendRequestId());
    const item0 = booking?.items?.[0] || {};
    setAmendCheckIn(booking.check_in_date || item0.check_in || "");
    setAmendCheckOut(booking.check_out_date || item0.check_out || "");
  };

  const EVENTS_ENDPOINT = (id) => `/b2b/bookings/${id}/events`;

  function normalizeHttpError(err) {
    const status = err?.response?.status;
    const msg = apiErrorMessage(err);

    if (status === 401) {
      return {
        title: "Giriş gerekiyor",
        description: "Oturumunuzun süresi dolmuş olabilir. Lütfen yeniden giriş yapın.",
      };
    }
    if (status === 403) {
      return {
        title: "Yetkiniz yok",
        description: "Bu rezervasyonun timeline kaydını görüntüleme yetkiniz bulunmuyor.",
      };
    }
    if (status === 404) {
      return {
        title: "Timeline bulunamadı",
        description: "Bu ortamda timeline endpoint'i kapalı olabilir veya henüz yayında değildir.",
      };
    }
    if (status && status >= 500) {
      return {
        title: "Sunucu hatası",
        description: msg,
      };
    }
    return { title: "Hata", description: msg };
  }

  const loadEvents = useCallback(async (id) => {
    if (!id) return;

    const mySeq = ++eventsReqSeq.current;

    setEventsLoading(true);
    setEventsError("");

    try {
      const resp = await api.get(EVENTS_ENDPOINT(id));
      if (eventsReqSeq.current !== mySeq) return;

      const normalized = normalizeEvents(resp.data);
      setEvents(normalized);
      setEventsLoaded(true);
    } catch (err) {
      if (eventsReqSeq.current !== mySeq) return;

      setEventsError(normalizeHttpError(err));
      setEventsLoaded(true);
    } finally {
      if (eventsReqSeq.current !== mySeq) return;
      setEventsLoading(false);
    }
  }, []);

  useEffect(() => {
    setEvents([]);
    setEventsError("");
    setEventsLoaded(false);
    eventsReqSeq.current += 1;
  }, [bookingId]);

  useEffect(() => {
    if (activeTab !== "timeline") return;
    if (!bookingId) return;
    if (eventsLoaded) return;
    if (eventsLoading) return;

    void loadEvents(bookingId);
  }, [activeTab, bookingId, eventsLoaded, eventsLoading, loadEvents]);

  // Legacy polling effect removed; replaced by startPaymentPolling/stopPaymentPolling helpers.

  const reloadAfterAmend = async () => {
    if (!bookingId) return;
    try {
      const base = mode === "hotel" ? "/hotel/bookings" : "/agency/bookings";
      const resp = await api.get(`${base}/${bookingId}`);
      const fresh = resp.data || null;
      setBooking(fresh);
      setError("");
      if (fresh && onBookingChanged) {
        try {
          onBookingChanged(fresh);
        } catch (e) {
          // ignore callback errors
        }
      }
    } catch (e) {
      setError(apiErrorMessage(e));
      setBooking(null);
    }
    try {
      const respLedger = await api.get(`/ops/finance/bookings/${bookingId}/ledger-summary`);
      setLedgerSummary(respLedger.data || null);
      setLedgerError("");
    } catch (e) {
      setLedgerError(apiErrorMessage(e));
      setLedgerSummary(null);
    }
  };

  const handleAmendQuote = async () => {
    if (!bookingId || !booking) return;
    if (!amendCheckIn || !amendCheckOut) {
      toast.error("L fctfen yeni giri5f/ e731k315f tarihlerini se e7in.");
      return;
    }
    const reqId = amendRequestId || generateAmendRequestId();
    if (!amendRequestId) setAmendRequestId(reqId);
    setAmendQuoteLoading(true);
    setAmendError("");
    try {
      const resp = await api.post(`/b2b/bookings/${bookingId}/amend/quote`, {
        check_in: amendCheckIn,
        check_out: amendCheckOut,
        request_id: reqId,
      });
      const proposal = resp.data || null;
      setAmendProposal(proposal);
      const after = proposal?.after || {};
      if (after.check_in) setAmendCheckIn(after.check_in);
      if (after.check_out) setAmendCheckOut(after.check_out);
      const deltaEur = Number((proposal?.delta || {}).sell_eur ?? 0);
      if (Number.isFinite(deltaEur) && deltaEur !== 0) {
        if (deltaEur > 0) {
          toast.info(`Tarih de1fi5fikli1fi i e7in fark: ${deltaEur.toFixed(2)} EUR`);
        } else {
          toast.info(`Tarih de1fi5fikli1fi i e7in iade: ${Math.abs(deltaEur).toFixed(2)} EUR`);
        }
      } else {
        toast.info("Tarih de1fi5fikli1fi fiyat31 de1fi5ftirmiyor.");
      }
    } catch (e) {
      const msg = apiErrorMessage(e);
      setAmendError(msg);
      toast.error(msg);
    } finally {
      setAmendQuoteLoading(false);
    }
  };

  const handleAmendConfirm = async () => {
    if (!bookingId || !booking) return;
    const amendId = amendProposal?.amend_id;
    if (!amendId) {
      toast.error(" d6nce tarih de1fi5fikli1fi i e7in fiyat teklifini almal31s31n31z.");
      return;
    }
    setAmendConfirmLoading(true);
    setAmendError("");
    try {
      const resp = await api.post(`/b2b/bookings/${bookingId}/amend/confirm`, {
        amend_id: amendId,
      });
      const doc = resp.data || {};
      const deltaFromResp = Number((doc?.delta || {}).sell_eur ?? 0);
      const deltaFromQuote = Number((amendProposal?.delta || {}).sell_eur ?? 0);
      const deltaEur = Number.isFinite(deltaFromResp) && deltaFromResp !== 0 ? deltaFromResp : deltaFromQuote;
      if (Number.isFinite(deltaEur) && deltaEur !== 0) {
        if (deltaEur > 0) {
          toast.success(`Tarih değişikliği tamamlandı. Fark: ${deltaEur.toFixed(2)} EUR`);
        } else {
          toast.success(`Tarih değişikliği tamamlandı. İade: ${Math.abs(deltaEur).toFixed(2)} EUR`);
        }
      } else {
        toast.success("Tarih değişikliği tamamlandı. Fiyat değişmedi.");
      }
      setAmendMode(false);
      setAmendProposal(null);
      setEventsLoaded(false);
      await reloadAfterAmend();
    } catch (e) {
      const msg = apiErrorMessage(e);
      setAmendError(msg);
      toast.error(msg);
    } finally {
      setAmendConfirmLoading(false);
    }
  };



  async function handleCancel() {
    if (!bookingId || !booking) return;
    if (booking.status !== "CONFIRMED") return;
    const ok = window.confirm("Bu rezervasyonu iptal etmek istediğinize emin misiniz?");
    if (!ok) return;
    setCancelLoading(true);
    try {
      const resp = await api.post(`/b2b/bookings/${bookingId}/cancel`, {});
      const updated = {
        ...booking,
        status: resp.data?.status || "CANCELLED",
      };
      setBooking(updated);
      const { refund_eur, penalty_eur } = resp.data || {};
      if (Number.isFinite(refund_eur) && Number.isFinite(penalty_eur)) {
        toast.success(
          `Rezervasyon iptal edildi. İade: ${refund_eur.toFixed(2)} EUR, Ceza: ${penalty_eur.toFixed(2)} EUR`
        );
      } else {
        toast.success("Rezervasyon iptal edildi.");
      }
      setEventsLoaded(false);
    } catch (e) {
      toast.error(apiErrorMessage(e));
    } finally {
      setCancelLoading(false);
    }
  }

  useEffect(() => {
    if (!open || !bookingId) {
      setError("");
      setLedgerSummary(null);
      setLedgerError("");
      setCancelLoading(false);
      return;
    }

    let cancelled = false;
    async function load() {
      setLoading(true);
      setError("");
      try {
        const base = mode === "hotel" ? "/hotel/bookings" : "/agency/bookings";
        const resp = await api.get(`${base}/${bookingId}`);
        if (!cancelled) setBooking(resp.data || null);
      } catch (e) {
        if (!cancelled) {
          setError(apiErrorMessage(e));
          setBooking(null);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }


    async function loadLedger() {
      if (!bookingId) return;
      setLedgerLoading(true);
      setLedgerError("");
      try {
        const resp = await api.get(`/ops/finance/bookings/${bookingId}/ledger-summary`);
        setLedgerSummary(resp.data || null);
      } catch (e) {
        setLedgerError(apiErrorMessage(e));
        setLedgerSummary(null);
      } finally {
        setLedgerLoading(false);
      }
    }

    async function loadPayment() {
      if (!bookingId) return;
      await loadPaymentState(bookingId);
      // Varsayılan amount input'u aggregate üzerinden doldur
      try {
        const resp = await api.get(PAYMENT_STATE_ENDPOINT(bookingId));
        const data = resp.data || {};
        const agg = data.aggregate || {};
        const total = Number(agg.amount_total ?? 0);
        const paid = Number(agg.amount_paid ?? 0);
        const remaining = total - paid;
        const safeRemaining = Number.isFinite(remaining) ? Math.max(0, remaining) : 0;
        if (safeRemaining > 0) {
          setPaymentAmountInput(String((safeRemaining / 100).toFixed(2)));
        } else if (total > 0) {
          setPaymentAmountInput(String((total / 100).toFixed(2)));
        } else {
          setPaymentAmountInput("");
        }
      } catch {
        // ignore, loadPaymentState zaten error state'i yönetiyor
      }
    }

    load();
    loadLedger();
    loadPayment();

    return () => {
      cancelled = true;
    };
  }, [open, bookingId, mode, loadPaymentState]);

  const handleOpenChange = (next) => {
    if (!next) {
      setBooking(null);
      setError("");
      setVoucherToken(null);
      setVoucherLoading(false);
      setLedgerSummary(null);
      setLedgerError("");
      setCancelLoading(false);
      setAmendMode(false);
      setAmendProposal(null);
      setAmendError("");
      stopPaymentPolling();
    }
    onOpenChange?.(next);
  };

  const handleCopy = async () => {
    if (!booking) return;
    const text = buildBookingCopyText(booking);
    if (!text) return;

    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(text);
      } else {
        const textarea = document.createElement("textarea");
        textarea.value = text;
        textarea.style.position = "fixed";
        textarea.style.left = "-9999px";
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand("copy");
        textarea.remove();
      }
      toast.success("Rezervasyon bilgisi kopyalandı");
    } catch {
      toast.error("Kopyalama başarısız oldu");
    }
  };

  const ensureVoucherToken = async () => {
    if (!bookingId) return null;
    if (voucherToken) return voucherToken;

    setVoucherLoading(true);
    try {
      const resp = await api.post(`/voucher/${bookingId}/generate`);
      const token = resp?.data?.token;
      if (token) {
        setVoucherToken(token);
        return token;
      }
      throw new Error("TOKEN_MISSING");
    } catch (e) {
      toast.error(apiErrorMessage(e) || "Voucher oluşturulamadı");
      return null;
    } finally {
      setVoucherLoading(false);
    }
  };

  const getBackendBaseUrl = () => {
    // CRA: process.env.REACT_APP_BACKEND_URL, Vite: import.meta.env.VITE_BACKEND_URL
    if (typeof import.meta !== "undefined" && import.meta.env && import.meta.env.VITE_BACKEND_URL) {
      return import.meta.env.VITE_BACKEND_URL;
    }
    if (process.env.REACT_APP_BACKEND_URL) {
      return process.env.REACT_APP_BACKEND_URL;
    }
    // Fallback: relative (aynı origin). Public voucher endpoint yine çalışır.
    return "";
  };

  const handleCopyVoucherLink = async () => {
    const token = await ensureVoucherToken();
    if (!token) return;
    const base = getBackendBaseUrl();
    const url = `${base}/api/voucher/public/${token}?format=html`;

    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(url);
      } else {
        const textarea = document.createElement("textarea");
        textarea.value = url;
        textarea.style.position = "fixed";
        textarea.style.left = "-9999px";
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand("copy");
        textarea.remove();
      }
      toast.success("Voucher linki kopyalandı");
    } catch {
      toast.error("Voucher linki kopyalanamadı");
    }
  };

  const handleOpenVoucherPdf = async () => {
    const token = await ensureVoucherToken();
    if (!token) return;
    const base = getBackendBaseUrl();
    const url = `${base}/api/voucher/public/${token}?format=pdf`;
    try {
      window.open(url, "_blank", "noopener,noreferrer");
    } catch {
      toast.error("PDF açılamadı");
    }
  };

  const titleHotel = booking?.hotel_name || "Rezervasyon Detayı";
  const subtitleParts = [];
  if (booking?.guest_name) subtitleParts.push(booking.guest_name);
  if (booking?.check_in_date && booking?.check_out_date) {
    subtitleParts.push(`${booking.check_in_date} → ${booking.check_out_date}`);
  }

  const subtitle = subtitleParts.join(" • ");

  const infoRows = [
    ["Oda / Room", booking?.room_type],
    ["Pansiyon / Board", booking?.board_type],
    ["Pax", booking ? `${booking.adults ?? "-"} / ${booking.children ?? 0}` : null],
    [
      "Tutar / Total",
      booking?.total_amount != null
        ? `${Number(booking.total_amount).toLocaleString("tr-TR", {
            minimumFractionDigits: 0,
            maximumFractionDigits: 2,
          })} ${booking.currency || ""}`.trim()
        : null,
    ],
    ["Durum / Status", `${booking?.status_tr || ""}${booking?.status_en ? ` / ${booking.status_en}` : ""}`],
    ["Booking ID", booking?.code],
    ["Kaynak / Source", booking?.source],
    ["Ödeme / Payment", booking?.payment_status],
    ["Oluşturma / Created", booking?.created_at],
    ["Onay Zamanı / Confirmed At", booking?.confirmed_at],
    ["Özel İstekler / Special Requests", booking?.special_requests],
  ];

  return (
    <Sheet open={open} onOpenChange={handleOpenChange}>
      <SheetContent side="right" className="w-full sm:max-w-xl flex flex-col">
        <SheetHeader className="space-y-2 pb-4 border-b">
          <div className="flex items-start justify-between gap-3">
            <div>
              <SheetTitle className="text-xl font-semibold">{titleHotel}</SheetTitle>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={paymentLoading || !bookingId}
                    onClick={() => loadPaymentState(bookingId)}
                  >
                    {paymentLoading ? "Ödeme durumu yükleniyor..." : "Ödeme Durumu"}
                  </Button>
                </div>

              {subtitle && (
                <>
                  <p className="mt-1 text-sm text-muted-foreground">{subtitle}</p>
                  <div className="flex items-center gap-2 mt-1">
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={paymentLoading || !bookingId}
                      onClick={() => loadPaymentState(bookingId)}
                    >
                      {paymentLoading ? "Ödeme durumu yükleniyor..." : "Ödeme Durumu"}
                    </Button>
                  </div>
                </>
              )}
              <div className="flex items-center justify-between gap-2 mt-4">
                <div className="flex items-center gap-2">
                  {booking?.status === "CONFIRMED" && (
                    <>
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={cancelLoading}
                        onClick={handleCancel}
                      >
                        {cancelLoading ? "İptal ediliyor..." : "İptal Et"}
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        className="ml-2"
                        disabled={cancelLoading || amendQuoteLoading || amendConfirmLoading}
                        onClick={handleOpenAmend}
                      >
                        Tarih Değiştir
                      </Button>
                    </>
                  )}
                </div>
              </div>

            <button
              type="button"
              className={
                activeTab === "pricing_trace"
                  ? "border-b-2 border-primary pb-2 font-medium"
                  : "pb-2 text-muted-foreground"
              }
              onClick={() => setActiveTab("pricing_trace")}
            >
              Pricing Trace
            </button>

            </div>
            <StatusBadge status_tr={booking?.status_tr} status={booking?.status} />
          </div>
        </SheetHeader>

        <div className="flex-1 overflow-y-auto py-4">
          {/* DETAY / TIMELINE SEKME BAFLARI */}
          <div className="mb-4 border-b flex gap-4 text-sm">
            <button
              type="button"
              className={
                activeTab === "details"
                  ? "border-b-2 border-primary pb-2 font-medium"
                  : "pb-2 text-muted-foreground"
              }
              onClick={() => setActiveTab("details")}
            >
              Detay
            </button>
            <button
              type="button"
              className={
                activeTab === "payments"
                  ? "border-b-2 border-primary pb-2 font-medium"
                  : "pb-2 text-muted-foreground"
              }
              onClick={() => setActiveTab("payments")}
            >
              Payments
            </button>
            <button
              type="button"
              className={
                activeTab === "timeline"
                  ? "border-b-2 border-primary pb-2 font-medium"
                  : "pb-2 text-muted-foreground"
              }
              onClick={() => setActiveTab("timeline")}
            >
              Timeline
            </button>
          </div>

          {/* DETAY SEKME İÇERİĞİ */}
          {activeTab === "details" && (
            <div className="space-y-4">
              {loading && (
                <p className="text-sm text-muted-foreground px-1">Yükleniyor...</p>
              )}

              {!loading && error && (
                <p className="text-sm text-destructive px-1">{error}</p>
              )}

              {!loading && !error && booking && (
                <div className="space-y-4">
                  <div>
                    {booking && (
                      <React.Fragment>
                          {amendMode && (
                            <div className="mt-4 border rounded-md p-3 space-y-3">
                              <h3 className="text-sm font-medium text-muted-foreground">
                                Tarih Değiştir
                              </h3>
                              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                <div className="flex flex-col gap-1">
                                  <label className="text-xs text-muted-foreground">Yeni Giriş Tarihi</label>
                                  <input
                                    type="date"
                                    className="border rounded px-2 py-1 text-sm"
                                    value={amendCheckIn}
                                    onChange={(e) => setAmendCheckIn(e.target.value)}
                                  />
                                </div>
                                <div className="flex flex-col gap-1">
                                  <label className="text-xs text-muted-foreground">Yeni Çıkış Tarihi</label>
                                  <input
                                    type="date"
                                    className="border rounded px-2 py-1 text-sm"
                                    value={amendCheckOut}
                                    onChange={(e) => setAmendCheckOut(e.target.value)}
                                  />
                                </div>
                              </div>
                              {amendProposal && (
                                <div className="mt-2 space-y-1 text-xs">
                          {(() => {
                            const before = amendProposal.before || {};
                            const after = amendProposal.after || {};
                            const currency = before.currency || after.currency || booking?.currency || "EUR";
                            const beforeSell = Number(before.sell ?? 0);
                            const afterSell = Number(after.sell ?? 0);
                            const deltaEur = Number((amendProposal.delta || {}).sell_eur ?? 0);

                            let deltaLabel = "Fiyat Değişmedi";
                            let deltaValue = "0.00";
                            let toneClass = "text-muted-foreground";

                            if (Number.isFinite(deltaEur) && deltaEur !== 0) {
                              deltaValue = `${Math.abs(deltaEur).toFixed(2)} EUR`;
                              if (deltaEur > 0) {
                                deltaLabel = "Ek Ödeme";
                                toneClass = "text-red-600 dark:text-red-400";
                              } else {
                                deltaLabel = "İade";
                                toneClass = "text-emerald-600 dark:text-emerald-400";
                              }
                            }

                            return (
                              <>
                                <div className="flex items-center justify-between">
                                  <span className="text-[10px] uppercase tracking-wide text-muted-foreground">
                                    Eski Toplam
                                  </span>
                                  <span className="font-medium">
                                    {beforeSell.toFixed(2)} {currency}
                                  </span>
                                </div>
                                <div className="flex items-center justify-between">
                                  <span className="text-[10px] uppercase tracking-wide text-muted-foreground">
                                    Yeni Toplam
                                  </span>
                                  <span className="font-medium">
                                    {afterSell.toFixed(2)} {currency}
                                  </span>
                                </div>
                                <div className="flex items-center justify-between">
                                  <span className="text-[10px] uppercase tracking-wide text-muted-foreground">
                                    Fark (EUR)
                                  </span>
                                  <span className={`font-semibold ${toneClass}`}>
                                    {deltaLabel}: {deltaValue}
                                  </span>
                                </div>
                              </>
                            );
                          })()}
                        </div>
                      )}
                      {amendError && (
                        <p className="text-xs text-destructive">{amendError}</p>
                      )}
                      <div className="flex flex-wrap gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={handleAmendQuote}
                          disabled={amendQuoteLoading || amendConfirmLoading}
                        >
                          {amendQuoteLoading ? "Hesaplanıyor..." : "Fiyat Hesapla"}
                        </Button>
                        <Button
                          size="sm"
                          onClick={handleAmendConfirm}
                          disabled={!amendProposal || amendConfirmLoading || amendQuoteLoading}
                        >
                          {amendConfirmLoading ? "Onaylanıyor..." : "Onayla"}
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            setAmendMode(false);
                            setAmendProposal(null);
                            setAmendError("");
                          }}
                        >
                          Vazgeç
                        </Button>
                      </div>
                    </div>
                  )}
                  <Separator className="my-4" />
                  <div>
                    <h3 className="text-sm font-medium text-muted-foreground mb-2">
                      Ledger Özeti
                    </h3>
                    {ledgerLoading && (
                      <p className="text-xs text-muted-foreground">Ledger özeti yükleniyor...</p>
                    )}
                    {!ledgerLoading && ledgerError && (
                      <p className="text-xs text-destructive">{ledgerError}</p>
                    )}
                    {!ledgerLoading && !ledgerError && ledgerSummary && (
                      <div className="grid grid-cols-2 gap-x-6 gap-y-1 text-xs">
                        <div className="flex flex-col">
                          <span className="text-[10px] text-muted-foreground uppercase tracking-wide">
                            Para Birimi
                          </span>
                          <span>{ledgerSummary.currency}</span>
                        </div>
                        <div className="flex flex-col">
                          <span className="text-[10px] text-muted-foreground uppercase tracking-wide">
                            Kayıt Sayısı
                          </span>
                          <span>{ledgerSummary.postings_count}</span>
                        </div>
                        <div className="flex flex-col">
                          <span className="text-[10px] text-muted-foreground uppercase tracking-wide">
                            Toplam Debit
                          </span>
                          <span>{Number(ledgerSummary.total_debit).toFixed(2)}</span>
                        </div>
                        <div className="flex flex-col">
                          <span className="text-[10px] text-muted-foreground uppercase tracking-wide">
                            Toplam Credit
                          </span>
                          <span>{Number(ledgerSummary.total_credit).toFixed(2)}</span>
                        </div>
                        <div className="flex flex-col col-span-2">
                          <span className="text-[10px] text-muted-foreground uppercase tracking-wide">
                            Fark (Debit - Credit)
                          </span>
                          <span>{Number(ledgerSummary.diff).toFixed(4)}</span>
                        </div>
                        {ledgerSummary.events && ledgerSummary.events.length > 0 && (
                          <div className="flex flex-col col-span-2">
                            <span className="text-[10px] text-muted-foreground uppercase tracking-wide">
                              Event Seti
                            </span>
                            <span>{ledgerSummary.events.join(", ")}</span>
                          </div>
                        )}
                        <div className="flex flex-col col-span-2">
                          <span className="text-[10px] text-muted-foreground uppercase tracking-wide">
                            Kaynak Koleksiyon
                          </span>
                          <span>{ledgerSummary.source_collection}</span>
                        </div>
                      </div>
                    )}
                    {!ledgerLoading && !ledgerError && !ledgerSummary && (
                      <p className="text-xs text-muted-foreground">
                        Bu booking için henüz ledger kaydı bulunamadı.
                      </p>
                    )}
                  </div>
                
                  <h3 className="text-sm font-medium text-muted-foreground mb-2">
                    Özet / Summary
                  </h3>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-2 text-sm">
                    {infoRows.map(([label, value]) => (
                      <div key={label} className="flex flex-col">
                        <span className="text-xs text-muted-foreground uppercase tracking-wide">
                          {label}
                        </span>
                        <span className="text-foreground">
                          {value === null || value === undefined || value === "" ? "-" : value}
                        </span>
                      </div>
                    ))}
                  </div>

                  <Separator />

                  <div className="text-xs text-muted-foreground">
          {activeTab === "pricing_trace" && (
            <PricingTracePanel bookingId={bookingId} />
          )}

                    <p>
                      Bu görünüm, voucher ve email metinleri için normalize edilmiş{' '}
                      rezervasyon özetidir.
                    </p>
                  </div>
                </React.Fragment>
              )}
                  </div>
                </div>
              )}
            </div>
          )}

          {activeTab === "payments" && (
            <div className="space-y-3">
              {paymentLoading && (
                <div className="flex items-center gap-2 px-1">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span className="text-sm text-muted-foreground">Ödeme durumu yükleniyor...</span>
                </div>
              )}

              {!paymentLoading && paymentError && (
                <ErrorState
                  title="Ödeme durumu yüklenemedi"
                  description={paymentError}
                  onRetry={() => loadPaymentState(bookingId)}
                  className="max-w-md"
                />
              )}

              {!paymentLoading && !paymentError && (!paymentState || !paymentState.aggregate) && (
                <EmptyState
                  title="Bu booking için ödeme kaydı yok"
                  description="Henüz bu rezervasyon için Stripe üzerinden bir tahsilat başlatılmamış."
                  className="py-8"
                />
              )}

              {!paymentLoading && !paymentError && paymentState && paymentState.aggregate && isPrivileged && (
                <>
                  <div className="mt-4 border-t pt-3 space-y-3">
                    <h3 className="text-sm font-medium text-muted-foreground">Stripe Ödeme Aksiyonları</h3>
                    <p className="text-xs text-muted-foreground">
                      Bu alan sadece admin/ops/super_admin kullanıcıları içindir. Acenta ve otel rolleri için
                      yalnızca okuma modunda görüntülenir.
                    </p>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-[1.2fr_0.8fr] gap-3 text-xs items-end">
                    <div className="flex flex-col gap-1">
                      <label className="text-[11px] text-muted-foreground uppercase tracking-wide">
                        Tahsilat Tutarı (EUR)
                      </label>
                      <input
                        type="number"
                        min={0}
                        step="0.01"
                        value={paymentAmountInput}
                        onChange={(e) => setPaymentAmountInput(e.target.value)}
                        className="h-8 w-full rounded-md border border-input bg-background px-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                      />
                      <p className="text-[11px] text-muted-foreground">
                        Varsayılan olarak kalan tahsilat tutarı öne gelir. Değiştirerek kısmi ödeme alabilirsiniz.
                      </p>
                    </div>

                    <div className="flex flex-col gap-1">
                      <label className="text-[11px] text-muted-foreground uppercase tracking-wide">
                        PaymentIntent ID
                      </label>
                      <input
                        type="text"
                        value={lastPaymentIntentId}
                        onChange={(e) => setLastPaymentIntentId(e.target.value)}
                        placeholder="pi_..."
                        className="h-8 w-full rounded-md border border-input bg-background px-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                      />
                      <p className="text-[11px] text-muted-foreground">
                        Create Intent ile üretilen son PaymentIntent ID otomatik dolacaktır.
                      </p>
                    </div>
                  </div>

                  <div className="flex flex-wrap gap-2 mt-2">
                    <Button
                      type="button"
                      size="sm"
                      disabled={paymentActionLoading || !bookingId}
                      onClick={async () => {
                        if (!bookingId) return;
                        const amountFloat = Number(String(paymentAmountInput).replace(",", "."));
                        if (!Number.isFinite(amountFloat) || amountFloat <= 0) {
                          toast.error("Geçerli bir tutar girin.");
                          return;
                        }
                        const amountCents = Math.round(amountFloat * 100);

                        setPaymentActionLoading(true);
                        setPaymentActionStatus("create_intent");
                        try {
                          const idem = makeIdempotencyKey({
                            bookingId,
                            action: "create_intent",
                            amountCents,
                          });
                          const resp = await api.post(
                            "/payments/stripe/create-intent",
                            {
                              booking_id: bookingId,
                              amount_cents: amountCents,
                              currency: paymentState.aggregate.currency || "EUR",
                            },
                            {
                              headers: {
                                "Idempotency-Key": idem,
                              },
                            },
                          );
                          const pi = resp.data?.payment_intent || {};
                          if (pi.id) {
                            setLastPaymentIntentId(pi.id);
                          }
                          toast.success("PaymentIntent oluşturuldu.");
                        } catch (e) {
                          const msg = apiErrorMessage(e);
                          toast.error(msg || "PaymentIntent oluşturulamadı");
                        } finally {
                          setPaymentActionLoading(false);
                          setPaymentActionStatus("");
                        }
                      }}
                    >
                      {paymentActionLoading && paymentActionStatus === "create_intent"
                        ? "Oluşturuluyor..."
                        : "Create Payment Intent"}
                    </Button>

                    <Button
                      type="button"
                      size="sm"
                      variant="default"
                      disabled={paymentActionLoading || !bookingId || !lastPaymentIntentId}
                      onClick={async () => {
                        if (!bookingId || !lastPaymentIntentId) return;
                        setPaymentActionLoading(true);
                        setPaymentActionStatus("capture");
                        try {
                          const idem = makeIdempotencyKey({
                            bookingId,
                            action: "capture",
                            amountCents: 0,
                          });
                          await api.post(
                            "/payments/stripe/capture",
                            { payment_intent_id: lastPaymentIntentId },
                            {
                              headers: {
                                "Idempotency-Key": idem,
                              },
                            },
                          );
                          toast.success("Capture isteği Stripe'a gönderildi. Webhook bekleniyor...");
                          startPaymentPolling(bookingId, { expectedEventType: "PAYMENT_CAPTURED", timeoutMs: 30_000 });
                        } catch (e) {
                          const msg = apiErrorMessage(e);
                          toast.error(msg || "Capture başarısız oldu");
                        } finally {
                          setPaymentActionLoading(false);
                          setPaymentActionStatus("");
                        }
                      }}
                    >
                      {paymentActionLoading && paymentActionStatus === "capture"
                        ? "Capture gönderiliyor..."
                        : "Capture"}
                    </Button>

                    {pollingPayment && (
                      <span className="text-[11px] text-muted-foreground flex items-center gap-1">
                        <Loader2 className="h-3 w-3 animate-spin" /> Webhook bekleniyor...
                      </span>
                    )}
                  </div>


                  <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div className="flex flex-col">
                      <span className="text-xs text-muted-foreground uppercase tracking-wide">
                        Toplam Tutar
                      </span>
                      <span>
                        {Number(paymentState.aggregate.amount_total / 100).toFixed(2)} {paymentState.aggregate.currency}
                      </span>
                    </div>
                    <div className="flex flex-col">
                      <span className="text-xs text-muted-foreground uppercase tracking-wide">
                        Ödenen
                      </span>
                      <span>
                        {Number(paymentState.aggregate.amount_paid / 100).toFixed(2)} {paymentState.aggregate.currency}
                      </span>
                    </div>
                    <div className="flex flex-col">
                      <span className="text-xs text-muted-foreground uppercase tracking-wide">
                        İade Edilen
                      </span>
                      <span>
                        {Number(paymentState.aggregate.amount_refunded / 100).toFixed(2)} {paymentState.aggregate.currency}
                      </span>
                    </div>
                    <div className="flex flex-col">
                      <span className="text-xs text-muted-foreground uppercase tracking-wide">
                        Ödeme Durumu
                      </span>
                      <span>{paymentState.aggregate.status}</span>
                    </div>
                  </div>

                  {paymentState.transactions && paymentState.transactions.length > 0 && (
                    <div className="space-y-2 text-xs">
                      <h3 className="text-sm font-medium text-muted-foreground">İşlem Geçmişi</h3>
                      <div className="space-y-1">
                        {paymentState.transactions.map((tx) => (
                          <div key={`${tx.type}-${tx.occurred_at || tx.created_at}`} className="flex items-center justify-between border-b border-muted py-1">
                            <div className="flex flex-col">
                              <span className="font-medium">
                                {tx.type === "capture_succeeded" ? "Capture" : tx.type === "refund_succeeded" ? "Refund" : tx.type}
                              </span>
                              <span className="text-[11px] text-muted-foreground">
                                {tx.occurred_at || tx.created_at}
                              </span>
                            </div>
                            <div className="text-right">
                              <span className="font-semibold">
                                {Number(tx.amount / 100).toFixed(2)} {tx.currency}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
                </>
              )}
            </div>
          )}

          {/* TIMELINE SEKME İÇERİĞİ */}
          {activeTab === "timeline" && (
            <div className="space-y-3">
              {eventsLoading && (
                <div className="flex items-center gap-2 px-1">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span className="text-sm text-muted-foreground">Timeline yükleniyor...</span>
                </div>
              )}

              {!eventsLoading && eventsError && (
                <ErrorState
                  title={eventsError.title || "Timeline yüklenemedi"}
                  description={eventsError.description || "Beklenmeyen bir hata oluştu."}
                  onRetry={() => loadEvents(bookingId)}
                  className="max-w-md"
                />
              )}

              {!eventsLoading && !eventsError && eventsLoaded && sortedEvents.length === 0 && (
                <EmptyState
                  title="Bu rezervasyon için event kaydı yok"
                  description="Henüz bu rezervasyon için timeline olayı üretilmemiş olabilir."
                  className="py-8"
                />
              )}

              {!eventsLoading && !eventsError && sortedEvents.length > 0 && (
                <div className="space-y-3">
                  {sortedEvents.map((ev) => (
                    <div key={ev.id} className="border-l-2 border-muted pl-3 pb-2">
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex-1">
                          <p className="text-sm font-medium">
                            {mapEventTypeLabel(ev.type)}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            {formatDateTime(ev.occurred_at)}
                          </p>
                          {renderEventMeta(ev)}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        <SheetFooter className="gap-2 border-t pt-3 flex flex-row items-center justify-between">
          <div className="text-xs text-muted-foreground">
            {booking?.code && <span>PNR: {booking.code}</span>}
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={() => {
                if (!bookingId) return;
                navigate(`/app/inbox?booking_id=${bookingId}`);
              }}
              disabled={!bookingId}
            >
              Inbox&apos;ta Aç
            </Button>
            <Button variant="outline" onClick={handleCopy} disabled={!booking}>
              Bilgileri Kopyala
            </Button>
            <Button
              variant="outline"
              onClick={handleCopyVoucherLink}
              disabled={!booking || voucherLoading}
            >
              Voucher Linki
            </Button>
            <Button
              variant="outline"
              onClick={async () => {
                if (!bookingId) return;
                const pdfUrl = `/b2b/bookings/${bookingId}/voucher/latest`;
                try {
                  const res = await api.get(pdfUrl, { responseType: "blob" });
                  const blob = new Blob([res.data], { type: "application/pdf" });
                  const url = window.URL.createObjectURL(blob);
                  window.open(url, "_blank", "noopener,noreferrer");
                } catch (e) {
                  const msg = apiErrorMessage(e) || "";
                  toast.error(msg || "Voucher açılamadı");
                }
              }}
              disabled={!booking}
            >
              Voucher
            </Button>
          </div>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}
