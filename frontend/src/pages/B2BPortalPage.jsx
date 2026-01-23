import React, { useEffect, useMemo, useState } from "react";
import { AlertCircle, CalendarDays, Loader2, User, CreditCard, Timer, XCircle, RefreshCw, Store } from "lucide-react";
import { api, apiErrorMessage } from "../lib/api";
import { bookingStatusLabelTr } from "../utils/bookingStatusLabels";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { B2BAnnouncementsCard } from "../components/B2BAnnouncementsCard";
import { Label } from "../components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";

// Basit helper: ISO tarih -> Date
function parseIso(value) {
  if (!value) return null;
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? null : d;
}

function formatRemaining(ms) {
  if (ms <= 0) return "0:00";
  const totalSec = Math.floor(ms / 1000);
  const m = Math.floor(totalSec / 60);
  const s = totalSec % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function StatusBadge({ status }) {
  if (!status) return <Badge variant="outline">-</Badge>;
  const raw = String(status).toLowerCase();
  const label = bookingStatusLabelTr(raw);
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
  if (raw === "voucher_issued" || raw === "vouchered") return <Badge variant="outline">{label}</Badge>;
  return <Badge variant="outline">{status}</Badge>;
}

function AccountStatusBadge({ status }) {
  const value = (status || "").toLowerCase();
  if (value === "over_limit") {
    return (
      <Badge variant="destructive" className="text-[11px]">
        Limit aşıldı
      </Badge>
    );
  }
  if (value === "near_limit") {
    return (
      <Badge variant="secondary" className="text-[11px]">
        Limite yakın
      </Badge>
    );
  }
  return (
    <Badge variant="outline" className="text-[11px]">
      Normal
    </Badge>
  );
}

function AccountSummaryCard() {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let isMounted = true;

    (async () => {
      setLoading(true);
      setError("");
      try {
        const res = await api.get("/b2b/account/summary");
        if (isMounted) {
          setSummary(res.data || null);
        }
      } catch (err) {
        if (isMounted) {
          setError(apiErrorMessage(err));
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    })();

    return () => {
      isMounted = false;
    };
  }, []);

  const currency = summary?.currency || "EUR";
  const creditLimit =
    typeof summary?.credit_limit === "number" && !Number.isNaN(summary.credit_limit)
      ? summary.credit_limit
      : null;
  const exposure =
    typeof summary?.exposure_eur === "number" && !Number.isNaN(summary.exposure_eur)
      ? summary.exposure_eur
      : null;
  const remainingLimit =
    creditLimit != null && exposure != null ? creditLimit - exposure : null;
  const net = typeof summary?.net === "number" && !Number.isNaN(summary.net) ? summary.net : null;

  const dataSourceLabel =
    summary?.data_source === "ledger_based"
      ? "Veri kaynağı: Finans hesaplarından türetilmiş"
      : summary?.data_source === "derived_from_bookings"
      ? "Veri kaynağı: Rezervasyonlardan türetilmiş"
      : null;

  return (
    <Card className="rounded-2xl border bg-card shadow-sm">
      <CardHeader className="flex flex-row items-center justify-between space-y-0">
        <div>
          <CardTitle className="flex items-center gap-2 text-base">
            <CreditCard className="h-4 w-4" />
            Hesap Özeti
          </CardTitle>
          <p className="mt-1 text-xs text-muted-foreground">
            Güncel kredi durumu ve ajans risk özetiniz.
          </p>
        </div>
        {summary && <AccountStatusBadge status={summary.status} />}
      </CardHeader>
      <CardContent className="space-y-3 text-xs">
        {loading && (
          <div className="flex items-center gap-2 text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            <span>Hesap özeti yükleniyor...</span>
          </div>
        )}

        {error && (
          <div className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-[11px] text-destructive">
            <AlertCircle className="h-4 w-4 mt-0.5" />
            <div>{error}</div>
          </div>
        )}

        {!loading && !error && summary && (
          <>
            <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
              <div>
                <div className="text-[11px] text-muted-foreground">Toplam Limit</div>
                <div className="mt-0.5 text-sm font-semibold">
                  {creditLimit != null ? (
                    <>
                      {creditLimit.toFixed(2)} {currency}
                    </>
                  ) : (
                    "-"
                  )}
                </div>
              </div>
              <div>
                <div className="text-[11px] text-muted-foreground">Kullanılan Limit</div>
                <div className="mt-0.5 text-sm font-semibold">
                  {exposure != null ? (
                    <>
                      {exposure.toFixed(2)} {currency}
                    </>
                  ) : (
                    "-"
                  )}
                </div>
              </div>
              <div>
                <div className="text-[11px] text-muted-foreground">Kalan Limit</div>
                <div className="mt-0.5 text-sm font-semibold">
                  {remainingLimit != null ? (
                    <>
                      {remainingLimit.toFixed(2)} {currency}
                    </>
                  ) : (
                    "-"
                  )}
                </div>
              </div>
              <div>
                <div className="text-[11px] text-muted-foreground">Toplam Risk (net)</div>
                <div className="mt-0.5 text-sm font-semibold">
                  {net != null ? (
                    <>
                      {net.toFixed(2)} {currency}
                    </>
                  ) : (
                    "-"
                  )}
                </div>
              </div>
            </div>

            {dataSourceLabel && (
              <p className="text-[11px] text-muted-foreground">{dataSourceLabel}</p>
            )}
          </>
        )}

        {!loading && !error && !summary && (
          <p className="text-[11px] text-muted-foreground">
            Hesap özetiniz şu anda gösterilemiyor.
          </p>
        )}
      </CardContent>
    </Card>
  );
}

function B2BDashboardKpiRow({ sessionQuotes, sessionBookings }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [stats, setStats] = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError("");
      try {
        const params = new URLSearchParams();
        params.append("limit", "100");
        const res = await api.get(`/b2b/bookings?${params.toString()}`);
        if (cancelled) return;
        const items = res.data?.items || [];
        const total = items.length;
        const confirmed = items.filter((b) => String(b.status || "").toUpperCase() === "CONFIRMED").length;
        const cancelledCount = items.filter((b) => String(b.status || "").toUpperCase() === "CANCELLED").length;
        const totalSell = items.reduce((acc, b) => {
          const val = typeof b.amount_sell === "number" ? b.amount_sell : 0;
          return acc + val;
        }, 0);
        const currency = (items[0]?.currency) || "EUR";
        setStats({ total, confirmed, cancelled: cancelledCount, totalSell, currency });
      } catch (e) {
        if (!cancelled) setError(apiErrorMessage(e));
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <Card className="rounded-2xl border bg-card shadow-sm">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-semibold flex items-center gap-2">
          <CalendarDays className="h-4 w-4" />
          Son B2B Aktivite Özeti
        </CardTitle>
      </CardHeader>
      <CardContent className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
        {error && (
          <div className="col-span-2 md:col-span-4 text-[11px] text-destructive flex items-start gap-2">
            <AlertCircle className="h-3 w-3 mt-0.5" />
            <span>{error}</span>
          </div>
        )}
        {!error && (
          <>
            <div className="space-y-1">
              <div className="text-[11px] text-muted-foreground">Son 30 günde booking</div>
              <div className="text-sm font-semibold">
                {loading && !stats ? "..." : stats ? stats.total : "-"}
              </div>
            </div>
            <div className="space-y-1">
              <div className="text-[11px] text-muted-foreground">Onaylanan</div>
              <div className="text-sm font-semibold">
                {loading && !stats ? "..." : stats ? stats.confirmed : "-"}
              </div>
            </div>
            <div className="space-y-1">
              <div className="text-[11px] text-muted-foreground">Toplam ciro (son N)</div>
              <div className="text-sm font-semibold">
                {loading && !stats
                  ? "..."
                  : stats
                  ? `${stats.totalSell.toFixed(2)} ${stats.currency}`
                  : "-"}
              </div>
            </div>
            <div className="space-y-1">
              <div className="text-[11px] text-muted-foreground">Bu oturumda</div>
              <div className="text-[11px]">
                <span className="font-semibold">{sessionQuotes}</span> quote, {" "}
                <span className="font-semibold">{sessionBookings}</span> booking
              </div>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}



function BookingListTab() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  async function load() {
    setLoading(true);
    setError("");
    try {
      const params = new URLSearchParams();
      if (statusFilter) params.append("status", statusFilter);
      params.append("limit", "50");
      const res = await api.get(`/b2b/bookings?${params.toString()}`);
      setItems(res.data?.items || []);
    } catch (err) {
      console.error("[B2BPortal] load bookings error:", err);
      setError(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Phase 1: Liste üzerinden iptal işlemi yok; sadece ana flow kullanılsın.
  const canCancelStatuses = new Set();

  return (
    <Card className="rounded-2xl border bg-card shadow-sm">
      <CardHeader className="flex flex-row items-center justify-between space-y-0">
        <div>
          <CardTitle className="flex items-center gap-2 text-base">
            <CalendarDays className="h-4 w-4" />
            Rezervasyonlarım
          </CardTitle>
          <p className="mt-1 text-xs text-muted-foreground">
            Son 50 B2B rezervasyonunuzu listeler. Varsayılan sıralama: en yeni üstte.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <select
            className="h-8 rounded-md border bg-background px-2 text-xs"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="">Tüm durumlar</option>
            <option value="CONFIRMED">Onaylandı</option>
            <option value="VOUCHERED">Voucher kesildi</option>
            <option value="CANCELLED">İptal edildi</option>
          </select>
          <Button size="sm" variant="outline" className="gap-1" onClick={load} disabled={loading}>
            {loading && <Loader2 className="h-3 w-3 animate-spin" />}
            <RefreshCw className="h-3 w-3" />
            Yenile
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {error && (
          <div className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-xs text-destructive">
            <AlertCircle className="h-4 w-4 mt-0.5" />
            <div>{error}</div>
          </div>
        )}

        {!loading && !error && items.length === 0 && (
          <div className="text-sm text-muted-foreground">Henüz B2B rezervasyonunuz yok.</div>
        )}

        {items.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b bg-muted/50 text-[11px] uppercase tracking-wide text-muted-foreground">
                <tr>
                  <th className="px-2 py-2">Booking ID</th>
                  <th className="px-2 py-2">Misafir</th>
                  <th className="px-2 py-2">Ürün / Otel</th>
                  <th className="px-2 py-2">Giriş</th>
                  <th className="px-2 py-2">Çıkış</th>
                  <th className="px-2 py-2">Durum</th>
                  <th className="px-2 py-2 text-right">Tutar</th>
                  <th className="px-2 py-2 text-right">Aksiyonlar</th>
                </tr>
              </thead>
              <tbody>
                {items.map((b) => {
                  const s = String(b.status || "").toUpperCase();
                  const canCancel = canCancelStatuses.has(s);
                  const voucherUrl = s === "VOUCHERED" ? `${process.env.REACT_APP_BACKEND_URL}/api/b2b/bookings/${b.booking_id}/voucher` : null;

                  return (
                    <tr key={b.booking_id} className="border-b last:border-0">
                      <td className="px-2 py-2 font-mono text-[11px] max-w-[160px] truncate" title={b.booking_id}>
                        {b.booking_id}
                      </td>
                      <td className="px-2 py-2 text-xs">{b.primary_guest_name || "-"}</td>
                      <td className="px-2 py-2 text-xs">{b.product_name || "-"}</td>
                      <td className="px-2 py-2 text-xs">{b.check_in || "-"}</td>
                      <td className="px-2 py-2 text-xs">{b.check_out || "-"}</td>
                      <td className="px-2 py-2 text-xs">
                        <StatusBadge status={b.status} />
                      </td>
                      <td className="px-2 py-2 text-right text-xs">
                        {b.amount_sell != null ? (
                          <span>
                            {b.amount_sell} {b.currency || "EUR"}
                          </span>
                        ) : (
                          "-"
                        )}
                      </td>
                      <td className="px-2 py-2 text-right text-xs">
                        <div className="flex justify-end gap-2">
                          {voucherUrl && (
                            <a
                              href={voucherUrl}
                              target="_blank"
                              rel="noreferrer"
                              className="inline-flex items-center text-[11px] text-primary hover:underline"
                            >
                              Voucher
                            </a>
                          )}
                          <Button
                            size="xs"
                            variant="ghost"
                            className="h-7 px-2 text-[11px]"
                            disabled
                            title="İptal için 'Quote / Book / Cancel' sekmesindeki iptal adımını kullanın."
                          >
                            İptal Talebi
                          </Button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default function B2BPortalPage() {
  const [activeTab, setActiveTab] = useState("flow"); // "flow" | "list"

  // Session KPIs
  const [sessionQuotes, setSessionQuotes] = useState(0);
  const [sessionBookings, setSessionBookings] = useState(0);

  // Quote form state
  const [checkIn, setCheckIn] = useState("");
  const [checkOut, setCheckOut] = useState("");
  const [occupancy, setOccupancy] = useState(2);

  // Quote result
  const [quote, setQuote] = useState(null); // { quote_id, expires_at, offer }
  const [quoteError, setQuoteError] = useState("");
  const [quoteProductId, setQuoteProductId] = useState("demo_product_1");
  const [quoteLoading, setQuoteLoading] = useState(false);

  // B2B Marketplace ürün listesi (bu acenteye açık ürünler)
  const [marketplaceProducts, setMarketplaceProducts] = useState([]);
  const [marketplaceLoading, setMarketplaceLoading] = useState(false);
  const [marketplaceError, setMarketplaceError] = useState("");

  // Countdown
  const [nowMs, setNowMs] = useState(Date.now());

  // Booking state
  const [customerName, setCustomerName] = useState("Test Müşteri");
  const [customerEmail, setCustomerEmail] = useState("test@example.com");
  const [travellerFirstName, setTravellerFirstName] = useState("Test");
  const [travellerLastName, setTravellerLastName] = useState("Traveller");
  const [booking, setBooking] = useState(null); // { booking_id, status, voucher_status, finance_flags? }
  const [bookingError, setBookingError] = useState("");
  const [bookingLoading, setBookingLoading] = useState(false);

  // Cancel state
  const [cancelReason, setCancelReason] = useState("customer_request");
  const [cancelAmount, setCancelAmount] = useState("100");
  const [cancelCurrency, setCancelCurrency] = useState("EUR");
  const [cancelResult, setCancelResult] = useState(null); // { case_id, status }
  const [cancelError, setCancelError] = useState("");
  const [cancelLoading, setCancelLoading] = useState(false);

  // Global error (env/auth vs.)
  const [globalError, setGlobalError] = useState("");

  // Countdown timer effect
  useEffect(() => {
    const id = setInterval(() => {
      setNowMs(Date.now());
    }, 1000);
    return () => clearInterval(id);
  }, []);

  // Countdown timer effect
  useEffect(() => {
    const id = setInterval(() => {
      setNowMs(Date.now());
    }, 1000);
    return () => clearInterval(id);
  }, []);

  // B2B Marketplace: bu acenteye açık ürünleri yükle
  useEffect(() => {
    let cancelled = false;
    async function run() {
      setMarketplaceLoading(true);
      setMarketplaceError("");
      try {
        const res = await api.get("/b2b/marketplace/products");
        if (cancelled) return;
        setMarketplaceProducts(res.data?.items || []);
      } catch (err) {
        if (cancelled) return;
        const msg = apiErrorMessage(err);
        // 404 / Not Found durumunda boş liste gibi davran, kırmızı hata göstermeyelim
        if (String(msg).toLowerCase().includes("not found")) {
          setMarketplaceProducts([]);
          setMarketplaceError("");
        } else {
          setMarketplaceError(msg);
        }
      } finally {
        if (!cancelled) setMarketplaceLoading(false);
      }
    }
    run();
    return () => {
      cancelled = true;
    };
  }, []);

  const expiresAtDate = useMemo(() => parseIso(quote?.expires_at), [quote]);
  const remainingMs = useMemo(() => {
    if (!expiresAtDate) return 0;
    return expiresAtDate.getTime() - nowMs;
  }, [expiresAtDate, nowMs]);

  const isExpired = !!expiresAtDate && remainingMs <= 0;

  async function handleCreateQuote(e) {
    e.preventDefault();
    setQuoteError("");
    setGlobalError("");
    setQuote(null);
    setBooking(null);
    setCancelResult(null);

    if (!checkIn || !checkOut) {
      setQuoteError("Giriş ve çıkış tarihleri gerekli");
      return;
    }

    setQuoteLoading(true);
    try {
      const payload = {
        channel_id: "ch_b2b_portal",
        items: [
          {
            product_id: quoteProductId || "demo_product_1",
            room_type_id: "standard",
            rate_plan_id: "base",
            check_in: checkIn,
            check_out: checkOut,
            occupancy: occupancy ? Number(occupancy) : 1,
          },
        ],
      };

      console.log("[B2BPortal] Quote payload:", payload);

      const resp = await api.post("/b2b/quotes", payload);
      const data = resp.data;
      console.log("[B2BPortal] Quote response:", data);

      const firstOffer = (data.offers && data.offers[0]) || null;
      setQuote({
        quote_id: data.quote_id,
        expires_at: data.expires_at,
        offer: firstOffer,
      });
      setSessionQuotes((prev) => prev + 1);
    } catch (err) {
      console.error("[B2BPortal] Quote error:", err);
      // Backend standard error body: { error: { code, message, details } }
      const resp = err?.response?.data;
      if (resp?.error?.code) {
        const code = resp.error.code;
        const backendMsg = resp.error.message || "Hata oluştu";
        if (code === "product_not_available") {
          setQuoteError("Bu ürün sizin için kapalı görünüyor. Lütfen B2B Marketplace'te bu acente için yetkilendirilmiş bir ürün ID'si kullanın veya farklı bir ürün deneyin.");
        } else {
          setQuoteError(`${code}: ${backendMsg}`);
        }
      } else {
        setQuoteError(apiErrorMessage(err));
      }
    } finally {
      setQuoteLoading(false);
    }
  }

  async function handleBook(e) {
    e.preventDefault();
    setBookingError("");
    setCancelResult(null);

    if (!quote?.quote_id) {
      setBookingError("Önce bir teklif (quote) oluşturmanız gerekiyor");
      return;
    }

    if (isExpired) {
      setBookingError("Quote süresi dolmuş görünüyor (expired)");
      return;
    }

    setBookingLoading(true);
    try {
      const idemKey = crypto.randomUUID();
      console.log("[B2BPortal] BOOKING Idempotency-Key:", idemKey);

      const payload = {
        quote_id: quote.quote_id,
        customer: {
          name: customerName || "Demo Customer",
          email: customerEmail || "demo@example.com",
        },
        travellers: [
          {
            first_name: travellerFirstName || "Demo",
            last_name: travellerLastName || "Traveller",
          },
        ],
      };

      console.log("[B2BPortal] Booking payload:", payload);

      const resp = await api.post("/b2b/bookings", payload, {
        headers: {
          "Idempotency-Key": idemKey,
        },
      });

      const data = resp.data;
      console.log("[B2BPortal] Booking response:", data);

      setBooking({
        booking_id: data.booking_id,
        status: data.status,
        voucher_status: data.voucher_status,
        finance_flags: data.finance_flags || null,
      });
      setBookingError("");
      setSessionBookings((prev) => prev + 1);
    } catch (err) {
      console.error("[B2BPortal] Booking error:", err);
      const resp = err?.response?.data;
      if (resp?.error?.code === "credit_limit_exceeded") {
        const d = resp.error.details || {};
        const exposure = d.exposure;
        const limit = d.limit;
        const projected = d.projected;
        let msg = "Kredi limiti aşıldı.";
        if (typeof exposure === "number" && typeof limit === "number" && typeof projected === "number") {
          msg = `Kredi limiti aşıldı: Mevcut exposure ${exposure.toFixed(2)}, bu rezervasyon ile ${projected.toFixed(
            2,
          )} olacak (limit ${limit.toFixed(2)}).`;
        }
        setBookingError(msg);
      } else if (resp?.error?.code) {
        setBookingError(`${resp.error.code}: ${resp.error.message || "Hata oluştu"}`);
      } else {
        setBookingError(apiErrorMessage(err));
      }
    } finally {
      setBookingLoading(false);
    }
  }

  async function handleCancel(e) {
    e.preventDefault();
    setCancelError("");

    if (!booking?.booking_id) {
      setCancelError("Önce bir rezervasyon oluşturmanız gerekiyor");
      return;
    }

    setCancelLoading(true);
    try {
      const idemKey = crypto.randomUUID();
      console.log("[B2BPortal] CANCEL Idempotency-Key:", idemKey);

      const payload = {
        reason: cancelReason || "customer_request",
        requested_refund_currency: cancelCurrency || "EUR",
        requested_refund_amount: Number(cancelAmount || 0) || 0,
      };

      console.log("[B2BPortal] Cancel payload:", payload);

      const resp = await api.post(`/b2b/bookings/${booking.booking_id}/cancel-requests`, payload, {
        headers: {
          "Idempotency-Key": idemKey,
        },
      });

      const data = resp.data;
      console.log("[B2BPortal] Cancel response:", data);

      setCancelResult({
        case_id: data.case_id,
        status: data.status,
      });
    } catch (err) {
      console.error("[B2BPortal] Cancel error:", err);
      const resp = err?.response?.data;
      if (resp?.error?.code) {
        setCancelError(`${resp.error.code}: ${resp.error.message || "Hata oluştu"}`);
      } else {
        setCancelError(apiErrorMessage(err));
      }
    } finally {
      setCancelLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <h1 className="text-2xl font-bold text-foreground">B2B Portal</h1>
        <p className="text-sm text-muted-foreground">
          Agentis sınıfı demo akışı: Quote → Book → Cancel. Tüm istekler agency token&apos;ı ile B2B backend&apos;e gider.
        </p>
      </div>

      <AccountSummaryCard />

      <B2BAnnouncementsCard />

      <B2BDashboardKpiRow sessionQuotes={sessionQuotes} sessionBookings={sessionBookings} />

      <div className="flex gap-2 border-b pb-1 text-sm">
        <button
          type="button"
          className={`border-b-2 px-2 pb-1 text-xs font-medium ${
            activeTab === "flow"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
          onClick={() => setActiveTab("flow")}
        >
          Quote / Book / Cancel akışı
        </button>
        <button
          type="button"
          className={`border-b-2 px-2 pb-1 text-xs font-medium ${
            activeTab === "list"
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
          onClick={() => setActiveTab("list")}
        >
          Rezervasyonlarım
        </button>
      </div>

      {globalError && (
        <div className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
          <AlertCircle className="h-4 w-4 mt-0.5" />
          <div>{globalError}</div>
        </div>
      )}

      {activeTab === "flow" && (
        <>
          {/* 1) Search / Quote */}
          <Card className="rounded-2xl border bg-card shadow-sm">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <CalendarDays className="h-4 w-4" />
                1. Adım – Quote Oluştur
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <form onSubmit={handleCreateQuote} className="grid grid-cols-1 md:grid-cols-5 gap-4 items-end">
                <div className="space-y-1 md:col-span-2">
                  <Label className="flex items-center gap-2 text-xs">
                    <Store className="h-4 w-4" />
                    Ürün (demo)
                  </Label>
                  <Input
                    type="text"
                    value={quoteProductId}
                    onChange={(e) => setQuoteProductId(e.target.value)}
                    className="text-xs font-mono"
                    placeholder="product_id (örneğin: demo_product_1)"
                  />
                </div>

                <div className="space-y-1">
                  <Label htmlFor="check_in" className="flex items-center gap-2">
                    <CalendarDays className="h-4 w-4" />
                    Giriş
                  </Label>
                  <Input
                    id="check_in"
                    type="date"
                    value={checkIn}
                    onChange={(e) => setCheckIn(e.target.value)}
                  />
                </div>

            <div className="space-y-1">
              <Label htmlFor="check_out" className="flex items-center gap-2">
                <CalendarDays className="h-4 w-4" />
                Çıkış
              </Label>
              <Input
                id="check_out"
                type="date"
                value={checkOut}
                onChange={(e) => setCheckOut(e.target.value)}
              />
            </div>

            <div className="space-y-1">
              <Label htmlFor="occupancy" className="flex items-center gap-2">
                <User className="h-4 w-4" />
                Kişi Sayısı
              </Label>
              <Input
                id="occupancy"
                type="number"
                min={1}
                value={occupancy}
                onChange={(e) => setOccupancy(e.target.value)}
              />
            </div>

            <div className="flex justify-end md:col-span-1">
              <Button type="submit" disabled={quoteLoading} className="w-full md:w-auto gap-2">
                {quoteLoading && <Loader2 className="h-4 w-4 animate-spin" />}
                {quoteLoading ? "Hesaplanıyor..." : "Quote Oluştur"}
              </Button>
            </div>
          </form>

          {quoteError && (
            <div className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
              <AlertCircle className="h-4 w-4 mt-0.5" />
              <div>{quoteError}</div>
            </div>
          )}

          {quote && (
            <div className="mt-2 grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="space-y-1">
                <div className="text-xs text-muted-foreground">Quote ID</div>
                <div className="font-mono text-sm break-all">{quote.quote_id}</div>
              </div>
              <div className="space-y-1">
                <div className="text-xs text-muted-foreground">Fiyat (sell)</div>
                <div className="text-lg font-semibold text-primary">
                  {quote.offer?.sell} {quote.offer?.currency || "EUR"}
                </div>
              </div>
              <div className="space-y-1">
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <Timer className="h-3 w-3" />
                  <span>Son kullanma</span>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant={isExpired ? "destructive" : "secondary"} className="text-xs">
                    {isExpired ? "Süresi doldu" : `Kalan: ${formatRemaining(remainingMs)}`}
                  </Badge>
                </div>
                <div className="text-[11px] text-muted-foreground mt-1">
                  expires_at (UTC): {quote.expires_at}
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* 2) Checkout / Book */}
      <Card className="rounded-2xl border bg-card shadow-sm">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <CreditCard className="h-4 w-4" />
            2. Adım – Rezervasyon Oluştur (Book)
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-xs text-muted-foreground">
            Not: Book isteğinde kullanılan <span className="font-mono">Idempotency-Key</span> console&apos;a yazılıyor.
          </p>
          <form onSubmit={handleBook} className="grid grid-cols-1 md:grid-cols-3 gap-4 items-end">
            <div className="space-y-1">
              <Label htmlFor="customer_name">Müşteri Adı</Label>
              <Input
                id="customer_name"
                value={customerName}
                onChange={(e) => setCustomerName(e.target.value)}
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="customer_email">Müşteri Email</Label>
              <Input
                id="customer_email"
                type="email"
                value={customerEmail}
                onChange={(e) => setCustomerEmail(e.target.value)}
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="traveller_name">Traveller Ad Soyad</Label>
              <div className="flex gap-2">
                <Input
                  id="traveller_first_name"
                  placeholder="Ad"
                  value={travellerFirstName}
                  onChange={(e) => setTravellerFirstName(e.target.value)}
                />
                <Input
                  id="traveller_last_name"
                  placeholder="Soyad"
                  value={travellerLastName}
                  onChange={(e) => setTravellerLastName(e.target.value)}
                />
              </div>
            </div>
            <div className="flex justify-end md:col-span-3">
              <Button
                type="submit"
                disabled={bookingLoading}
                className="w-full md:w-auto gap-2"
              >
                {bookingLoading && <Loader2 className="h-4 w-4 animate-spin" />}
                {bookingLoading ? "Gönderiliyor..." : "Rezervasyon Oluştur"}
              </Button>
            </div>
          </form>

          {bookingError && (
            <div className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
              <AlertCircle className="h-4 w-4 mt-0.5" />
              <div>{bookingError}</div>
            </div>
          )}

          {booking && (
            <div className="mt-2 space-y-2">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="space-y-1">
                  <div className="text-xs text-muted-foreground">Booking ID</div>
                  <div className="font-mono text-sm break-all">{booking.booking_id}</div>
                </div>
                <div className="space-y-1">
                  <div className="text-xs text-muted-foreground">Durum</div>
                  <Badge variant="secondary" className="text-xs">
                    {booking.status}
                  </Badge>
                </div>
                <div className="space-y-1">
                  <div className="text-xs text-muted-foreground">Voucher Durumu</div>
                  <Badge variant="outline" className="text-xs">
                    {booking.voucher_status}
                  </Badge>
                </div>
                {booking.status === "VOUCHERED" && (
                  <div className="space-y-1">
                    <div className="text-xs text-muted-foreground">Voucher</div>
                    <a
                      href={`${process.env.REACT_APP_BACKEND_URL}/api/b2b/bookings/${booking.booking_id}/voucher`}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center text-xs text-primary hover:underline"
                    >
                      Voucher Görüntüle
                    </a>
                  </div>
                )}
              </div>

              {booking.finance_flags?.near_limit && (
                <div className="rounded-xl border border-amber-300 bg-amber-50 px-3 py-2 text-[11px] text-amber-800 flex items-start gap-2">
                  <span className="mt-0.5 text-sm">!</span>
                  <div>
                    <div className="font-semibold">Kredi limitinize yaklaştınız</div>
                    <div className="mt-0.5">
                      Kredi limitiniz EUR bazında hesaplanır. Hesap özetinizi kontrol ederek yeni rezervasyonlarda
                      reddedilme riskini azaltmak için ödeme yapmayı veya limit artışı talep etmeyi
                      değerlendirebilirsiniz.
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* 3) My Booking + Cancel Request */}
      <Card className="rounded-2xl border bg-card shadow-sm">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <XCircle className="h-4 w-4" />
            3. Adım – İptal Talebi (Cancel Request)
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-xs text-muted-foreground">
            Not: Cancel isteğinde kullanılan <span className="font-mono">Idempotency-Key</span> console&apos;a yazıldı.
          </p>

          {booking ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-1">
                <div className="text-xs text-muted-foreground">Son Booking</div>
                <div className="font-mono text-sm break-all">{booking.booking_id}</div>
                <div className="text-xs text-muted-foreground mt-1">
                  Durum: <span className="font-medium">{booking.status}</span>
                </div>
              </div>

              <form onSubmit={handleCancel} className="space-y-3">
                <div className="space-y-1">
                  <Label htmlFor="cancel_reason">İptal Nedeni</Label>
                  <Input
                    id="cancel_reason"
                    value={cancelReason}
                    onChange={(e) => setCancelReason(e.target.value)}
                  />
                </div>
                <div className="flex gap-2">
                  <div className="space-y-1 flex-1">
                    <Label htmlFor="cancel_amount">İade Talebi (Tutar)</Label>
                    <Input
                      id="cancel_amount"
                      type="number"
                      min={0}
                      value={cancelAmount}
                      onChange={(e) => setCancelAmount(e.target.value)}
                    />
                  </div>
                  <div className="space-y-1 w-24">
                    <Label htmlFor="cancel_currency">Para Birimi</Label>
                    <Input
                      id="cancel_currency"
                      value={cancelCurrency}
                      onChange={(e) => setCancelCurrency(e.target.value)}
                    />
                  </div>
                </div>
                <div className="flex justify-end">
                  <Button
                    type="submit"
                    disabled={cancelLoading}
                    className="w-full md:w-auto gap-2"
                  >
                    {cancelLoading && <Loader2 className="h-4 w-4 animate-spin" />}
                    {cancelLoading ? "Gönderiliyor..." : "İptal Talebi Oluştur"}
                  </Button>
                </div>
              </form>
            </div>
          ) : (
            <div className="text-sm text-muted-foreground">
              Henüz bu oturumda oluşturulmuş bir booking yok. Önce &quot;Rezervasyon Oluştur&quot; adımını tamamlayın.
            </div>
          )}

          {cancelError && (
            <div className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
              <AlertCircle className="h-4 w-4 mt-0.5" />
              <div>{cancelError}</div>
            </div>
          )}

          {cancelResult && (
            <div className="mt-2 grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-1">
                <div className="text-xs text-muted-foreground">Case ID</div>
                <div className="font-mono text-sm break-all">{cancelResult.case_id}</div>
              </div>
              <div className="space-y-1">
                <div className="text-xs text-muted-foreground">Case Durumu</div>
                <Badge variant="secondary" className="text-xs">
                  {cancelResult.status}
                </Badge>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
        </>
      )}

      {activeTab === "list" && <BookingListTab />}
    </div>
  );
}
