import React, { useEffect, useMemo, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { AlertCircle, CalendarDays, Loader2, User, CreditCard, Timer, XCircle, RefreshCw, Store, Eye } from "lucide-react";
import { api, apiErrorMessage } from "../lib/api";
import { buildApiUrl } from "../lib/backendUrl";
import { bookingStatusLabelTr } from "../utils/bookingStatusLabels";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { B2BAnnouncementsCard } from "../components/B2BAnnouncementsCard";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "../components/ui/dialog";
import { toast } from "sonner";
import { Label } from "../components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { PageShell, StatusBadge } from "../design-system";

/* ── Helpers ──────────────────────────────────────────────── */
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

function B2BStatusBadge({ status }) {
  if (!status) return <Badge variant="outline">-</Badge>;
  const raw = String(status).toLowerCase();
  const label = bookingStatusLabelTr(raw);
  if (raw === "confirmed") return <Badge variant="secondary">{label}</Badge>;
  if (raw === "cancelled")
    return <Badge variant="destructive" className="gap-1"><XCircle className="h-3 w-3" /> {label}</Badge>;
  if (raw === "pending" || raw === "pending_approval")
    return <Badge variant="outline" className="gap-1"><Loader2 className="h-3 w-3 animate-spin" /> {label}</Badge>;
  if (raw === "voucher_issued" || raw === "vouchered") return <Badge variant="outline">{label}</Badge>;
  return <Badge variant="outline">{status}</Badge>;
}

function AccountStatusBadge({ status }) {
  const value = (status || "").toLowerCase();
  if (value === "over_limit") return <Badge variant="destructive" className="text-xs">Limit asildi</Badge>;
  if (value === "near_limit") return <Badge variant="secondary" className="text-xs">Limite yakin</Badge>;
  return <Badge variant="outline" className="text-xs">Normal</Badge>;
}

function friendlyError(err) {
  const resp = err?.response?.data;
  const code = resp?.error?.code;
  const raw = apiErrorMessage(err);
  const msg = String(err?.message || raw || "");
  const isNetwork = err?.code === "ECONNABORTED" || msg.toLowerCase().includes("network error") || msg.toLowerCase().includes("timeout") || msg.toLowerCase().includes("failed to fetch");
  if (isNetwork) return { title: "Baglanti hatasi. Lutfen tekrar deneyin.", detail: raw, code: code || err?.code, kind: "network" };
  if (resp?.error || err?.response?.status) return { title: "Islem basarisiz.", detail: resp?.error?.message || raw || "Islem basarisiz.", code, kind: "domain" };
  return { title: "Bir hata olustu.", detail: raw, code: code || err?.code, kind: "unknown" };
}

/* ── Account Summary ─────────────────────────────────────── */
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
        if (isMounted) setSummary(res.data || null);
      } catch (err) {
        if (isMounted) setError(apiErrorMessage(err));
      } finally {
        if (isMounted) setLoading(false);
      }
    })();
    return () => { isMounted = false; };
  }, []);

  const currency = summary?.currency || "EUR";
  const creditLimit = typeof summary?.credit_limit === "number" ? summary.credit_limit : null;
  const exposure = typeof summary?.exposure_eur === "number" ? summary.exposure_eur : null;
  const remainingLimit = creditLimit != null && exposure != null ? creditLimit - exposure : null;
  const net = typeof summary?.net === "number" ? summary.net : null;
  const dataSourceLabel = summary?.data_source === "ledger_based" ? "Veri kaynagi: Finans hesaplarindan turetilmis" : summary?.data_source === "derived_from_bookings" ? "Veri kaynagi: Rezervasyonlardan turetilmis" : null;

  return (
    <Card className="rounded-2xl border bg-card shadow-sm" data-testid="b2b-account-summary">
      <CardHeader className="flex flex-row items-center justify-between space-y-0">
        <div>
          <CardTitle className="flex items-center gap-2 text-base"><CreditCard className="h-4 w-4" /> Hesap Ozeti</CardTitle>
          <p className="mt-1 text-xs text-muted-foreground">Guncel kredi durumu ve ajans risk ozetiniz.</p>
        </div>
        {summary && <AccountStatusBadge status={summary.status} />}
      </CardHeader>
      <CardContent className="space-y-3 text-xs">
        {loading && <div className="flex items-center gap-2 text-muted-foreground"><Loader2 className="h-4 w-4 animate-spin" /><span>Hesap ozeti yukleniyor...</span></div>}
        {error && <div className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-xs text-destructive"><AlertCircle className="h-4 w-4 mt-0.5" /><div>{error}</div></div>}
        {!loading && !error && summary && (
          <>
            <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
              <div><div className="text-xs text-muted-foreground">Toplam Limit</div><div className="mt-0.5 text-sm font-semibold">{creditLimit != null ? `${creditLimit.toFixed(2)} ${currency}` : "-"}</div></div>
              <div><div className="text-xs text-muted-foreground">Kullanilan Limit</div><div className="mt-0.5 text-sm font-semibold">{exposure != null ? `${exposure.toFixed(2)} ${currency}` : "-"}</div></div>
              <div><div className="text-xs text-muted-foreground">Kalan Limit</div><div className="mt-0.5 text-sm font-semibold">{remainingLimit != null ? `${remainingLimit.toFixed(2)} ${currency}` : "-"}</div></div>
              <div><div className="text-xs text-muted-foreground">Toplam Risk (net)</div><div className="mt-0.5 text-sm font-semibold">{net != null ? `${net.toFixed(2)} ${currency}` : "-"}</div></div>
            </div>
            {dataSourceLabel && <p className="text-xs text-muted-foreground">{dataSourceLabel}</p>}
          </>
        )}
        {!loading && !error && !summary && <p className="text-xs text-muted-foreground">Hesap ozetiniz su anda gosterilemiyor.</p>}
      </CardContent>
    </Card>
  );
}

/* ── KPI Row ─────────────────────────────────────────────── */
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
        const res = await api.get("/b2b/bookings?limit=100");
        if (cancelled) return;
        const items = res.data?.items || [];
        const total = items.length;
        const confirmed = items.filter(b => String(b.status || "").toUpperCase() === "CONFIRMED").length;
        const cancelledCount = items.filter(b => String(b.status || "").toUpperCase() === "CANCELLED").length;
        const totalSell = items.reduce((acc, b) => acc + (typeof b.amount_sell === "number" ? b.amount_sell : 0), 0);
        const currency = items[0]?.currency || "EUR";
        setStats({ total, confirmed, cancelled: cancelledCount, totalSell, currency });
      } catch (e) {
        if (!cancelled) setError(apiErrorMessage(e));
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, []);

  return (
    <Card className="rounded-2xl border bg-card shadow-sm" data-testid="b2b-kpi-row">
      <CardHeader className="pb-2"><CardTitle className="text-sm font-semibold flex items-center gap-2"><CalendarDays className="h-4 w-4" /> Son B2B Aktivite Ozeti</CardTitle></CardHeader>
      <CardContent className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
        {error && <div className="col-span-2 md:col-span-4 text-xs text-destructive flex items-start gap-2"><AlertCircle className="h-3 w-3 mt-0.5" /><span>{error}</span></div>}
        {!error && (
          <>
            <div className="space-y-1"><div className="text-xs text-muted-foreground">Son 30 gunde booking</div><div className="text-sm font-semibold">{loading && !stats ? "..." : stats ? stats.total : "-"}</div></div>
            <div className="space-y-1"><div className="text-xs text-muted-foreground">Onaylanan</div><div className="text-sm font-semibold">{loading && !stats ? "..." : stats ? stats.confirmed : "-"}</div></div>
            <div className="space-y-1"><div className="text-xs text-muted-foreground">Toplam ciro (son N)</div><div className="text-sm font-semibold">{loading && !stats ? "..." : stats ? `${stats.totalSell.toFixed(2)} ${stats.currency}` : "-"}</div></div>
            <div className="space-y-1"><div className="text-xs text-muted-foreground">Bu oturumda</div><div className="text-xs"><span className="font-semibold">{sessionQuotes}</span> quote, <span className="font-semibold">{sessionBookings}</span> booking</div></div>
          </>
        )}
      </CardContent>
    </Card>
  );
}

/* ── Price Preview Dialog ────────────────────────────────── */
function PricePreviewDialog({ open, onOpenChange, checkIn, checkOut, adults, childrenCount, selectedOffer, quoteOffer }) {
  const sourceLabel = quoteOffer ? "Quote" : selectedOffer ? "Arama Sonucu" : "-";
  const offer = quoteOffer || selectedOffer || null;
  const total = (typeof offer?.sell === "number" && offer.sell) || (typeof offer?.selling_total === "number" && offer.selling_total) || (typeof offer?.selling_total === "string" && Number(offer.selling_total)) || null;
  const currency = offer?.currency || offer?.selling_currency || "EUR";
  const nightsFromOffer = (typeof offer?.nights === "number" && offer.nights) || (offer?.stay && typeof offer.stay.nights === "number" && offer.stay.nights) || null;
  let nights = nightsFromOffer;
  let nightsByDates = null;
  if (checkIn && checkOut) {
    try { const a = new Date(`${checkIn}T00:00:00`); const b = new Date(`${checkOut}T00:00:00`); const diff = Math.round((b - a) / (1000 * 60 * 60 * 24)); if (Number.isFinite(diff) && diff > 0) nightsByDates = diff; } catch { /* ignore */ }
  }
  if (!nights && nightsByDates) nights = nightsByDates;
  const perNight = nights && total ? total / nights : null;
  const occLabel = `${adults || 0} yetiskin${childrenCount ? `, ${childrenCount} cocuk` : ""}`;
  const dateLabel = checkIn && checkOut ? `${new Date(checkIn).toLocaleDateString("tr-TR")} → ${new Date(checkOut).toLocaleDateString("tr-TR")}` : checkIn || "-";
  const nightsMismatch = nightsFromOffer && nightsByDates && nightsFromOffer !== nightsByDates;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Hizli Fiyat Onizleme</DialogTitle>
          <DialogDescription>Bu dialog, mevcut arama veya quote sonuclarindan gelen fiyat bilgisi ile hazirlanir.</DialogDescription>
        </DialogHeader>
        {!offer ? (
          <p className="text-sm text-muted-foreground">Gosterilecek bir fiyat bulunamadi. Lutfen once arama yapip bir sonuc secin veya quote olusturun.</p>
        ) : (
          <div className="space-y-4 text-sm">
            <div className="text-xs text-muted-foreground">Kaynak: {sourceLabel}</div>
            <div className="space-y-1"><div className="text-xs text-muted-foreground">Tarih ve konaklama</div><div className="font-medium">{dateLabel}</div><div className="text-xs text-muted-foreground">{occLabel}</div>
              {nightsMismatch && <div className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-2 py-1 mt-1">Tarih araligi ile teklifin gece sayisi tam olarak uyusmuyor.</div>}
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div className="space-y-1"><div className="text-xs text-muted-foreground">Toplam satis</div><div className="text-base font-semibold">{total != null ? `${total.toFixed(2)} ${currency}` : "-"}</div></div>
              <div className="space-y-1"><div className="text-xs text-muted-foreground">Gece</div><div className="text-base font-semibold">{nights || "-"}</div></div>
              <div className="space-y-1"><div className="text-xs text-muted-foreground">Gece basi</div><div className="text-base font-semibold">{perNight != null ? `${perNight.toFixed(2)} ${currency}` : "-"}</div></div>
            </div>
            <div className="rounded-md border bg-muted/40 px-3 py-2 text-xs text-muted-foreground">Bu ozet, secili sonuca ait verilerden turetilmistir.</div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

/* ── Booking List Tab ────────────────────────────────────── */
function BookingListTab() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [listQuery, setListQuery] = useState("");
  const [checkInFilter, setCheckInFilter] = useState("");
  const [checkOutFilter, setCheckOutFilter] = useState("");

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
      setError(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  const canCancelStatuses = new Set();

  const filteredItems = useMemo(() => {
    return items.filter((b) => {
      const q = listQuery.trim().toLowerCase();
      if (q) {
        const haystack = `${b.booking_id || b.id || ""} ${b.primary_guest_name || b.guest_name || ""} ${b.product_name || b.hotel_name || ""} ${b.reference || b.voucher_code || ""}`.toLowerCase();
        if (!haystack.includes(q)) return false;
      }
      const from = checkInFilter ? new Date(checkInFilter) : null;
      const to = checkOutFilter ? new Date(checkOutFilter) : null;
      const rawDate = b.check_in || b.checkin || b.start_date || "";
      let d = null;
      if (rawDate) { const parsed = new Date(rawDate); if (!Number.isNaN(parsed.getTime())) d = parsed; }
      if (from && d && d < from) return false;
      if (to && d && d > to) return false;
      return true;
    });
  }, [items, listQuery, checkInFilter, checkOutFilter]);

  return (
    <Card className="rounded-2xl border bg-card shadow-sm" data-testid="b2b-booking-list">
      <CardHeader className="flex flex-row items-center justify-between space-y-0">
        <div>
          <CardTitle className="flex items-center gap-2 text-base"><CalendarDays className="h-4 w-4" /> Rezervasyonlarim</CardTitle>
          <p className="mt-1 text-xs text-muted-foreground">Son 50 B2B rezervasyonunuzu listeler.</p>
        </div>
        <div className="flex flex-wrap items-center gap-2 justify-end">
          <input className="h-8 rounded-md border bg-background px-2 text-xs" placeholder="Ara: Booking ID / Misafir / Otel" value={listQuery} onChange={(e) => setListQuery(e.target.value)} data-testid="b2b-booking-search" />
          {listQuery && <Button type="button" size="icon" variant="ghost" className="h-8 w-8 text-muted-foreground" onClick={() => setListQuery("")}>x</Button>}
          <input type="date" className="h-8 rounded-md border bg-background px-2 text-xs" value={checkInFilter} onChange={(e) => setCheckInFilter(e.target.value)} data-testid="b2b-checkin-filter" />
          <input type="date" className="h-8 rounded-md border bg-background px-2 text-xs" value={checkOutFilter} onChange={(e) => setCheckOutFilter(e.target.value)} data-testid="b2b-checkout-filter" />
          <select className="h-8 rounded-md border bg-background px-2 text-xs" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} data-testid="b2b-status-filter">
            <option value="">Tum durumlar</option>
            <option value="CONFIRMED">Onaylandi</option>
            <option value="VOUCHERED">Voucher kesildi</option>
            <option value="CANCELLED">Iptal edildi</option>
          </select>
          <Button size="sm" variant="outline" className="gap-1" onClick={load} disabled={loading} data-testid="b2b-booking-refresh">
            {loading && <Loader2 className="h-3 w-3 animate-spin" />}<RefreshCw className="h-3 w-3" /> Yenile
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {error && <div className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-xs text-destructive"><AlertCircle className="h-4 w-4 mt-0.5" /><div>{error}</div></div>}
        {!loading && !error && items.length === 0 && <div className="text-sm text-muted-foreground" data-testid="b2b-no-bookings">Henuz B2B rezervasyonunuz yok.</div>}
        {filteredItems.length === 0 && items.length > 0 && !loading && <div className="text-sm text-muted-foreground">Sonuc bulunamadi.</div>}
        {filteredItems.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b bg-muted/50 text-xs uppercase tracking-wide text-muted-foreground">
                <tr>
                  <th className="px-2 py-2">Booking ID</th>
                  <th className="px-2 py-2">Misafir</th>
                  <th className="px-2 py-2">Urun / Otel</th>
                  <th className="px-2 py-2">Giris</th>
                  <th className="px-2 py-2">Cikis</th>
                  <th className="px-2 py-2">Durum</th>
                  <th className="px-2 py-2 text-right">Tutar</th>
                  <th className="px-2 py-2 text-right">Aksiyonlar</th>
                </tr>
              </thead>
              <tbody>
                {filteredItems.map((b) => {
                  const s = String(b.status || "").toUpperCase();
                  const voucherUrl = s === "VOUCHERED" ? buildApiUrl(`/b2b/bookings/${b.booking_id}/voucher`) : null;
                  return (
                    <tr key={b.booking_id} className="border-b last:border-0" data-testid={`b2b-booking-row-${b.booking_id}`}>
                      <td className="px-2 py-2 font-mono text-xs max-w-[160px] truncate" title={b.booking_id}>{b.booking_id}</td>
                      <td className="px-2 py-2 text-xs">{b.primary_guest_name || "-"}</td>
                      <td className="px-2 py-2 text-xs">{b.product_name || "-"}</td>
                      <td className="px-2 py-2 text-xs">{b.check_in ? new Date(b.check_in).toLocaleDateString("tr-TR") : "-"}</td>
                      <td className="px-2 py-2 text-xs">{b.check_out ? new Date(b.check_out).toLocaleDateString("tr-TR") : "-"}</td>
                      <td className="px-2 py-2 text-xs"><B2BStatusBadge status={b.status} /></td>
                      <td className="px-2 py-2 text-right text-xs">{b.amount_sell != null ? `${b.amount_sell} ${b.currency || "EUR"}` : "-"}</td>
                      <td className="px-2 py-2 text-right text-xs">
                        <div className="flex justify-end gap-2">
                          {voucherUrl && <a href={voucherUrl} target="_blank" rel="noreferrer" className="inline-flex items-center text-xs text-primary hover:underline">Voucher</a>}
                          <Button size="xs" variant="ghost" className="h-7 px-2 text-xs" disabled title="Iptal icin Quote / Book / Cancel sekmesindeki iptal adimini kullanin.">Iptal Talebi</Button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
        {!loading && !error && items.length > 0 && (
          <div className="text-xs text-muted-foreground flex items-center justify-between mt-2">
            <span>{filteredItems.length}/{items.length} sonuc</span>
            {(checkInFilter || checkOutFilter) && <Button type="button" size="sm" variant="ghost" className="text-xs" onClick={() => { setCheckInFilter(""); setCheckOutFilter(""); }}>Tarih filtresini temizle</Button>}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

/* ── Quote Book Cancel Flow ──────────────────────────────── */
function QuoteBookCancelFlow({ sessionQuotes, setSessionQuotes, sessionBookings, setSessionBookings }) {
  const [city, setCity] = useState("Istanbul");
  const [checkIn, setCheckIn] = useState("");
  const [checkOut, setCheckOut] = useState("");
  const [nights, setNights] = useState(2);
  const [adults, setAdults] = useState(2);
  const [children, setChildren] = useState(0);
  const [searchResults, setSearchResults] = useState([]);
  const [selectedOffer, setSelectedOffer] = useState(null);
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchError, setSearchError] = useState("");
  const [cityError, setCityError] = useState("");
  const [dateError, setDateError] = useState("");
  const [pricePreviewOpen, setPricePreviewOpen] = useState(false);
  const [quote, setQuote] = useState(null);
  const [quoteError, setQuoteError] = useState("");
  const [quoteLoading, setQuoteLoading] = useState(false);
  const [marketplaceProducts, setMarketplaceProducts] = useState([]);
  const [marketplaceLoading, setMarketplaceLoading] = useState(false);
  const [marketplaceError, setMarketplaceError] = useState("");
  const [nowMs, setNowMs] = useState(Date.now());
  const [customerName, setCustomerName] = useState("Test Musteri");
  const [customerEmail, setCustomerEmail] = useState("test@example.com");
  const [travellerFirstName, setTravellerFirstName] = useState("Test");
  const [travellerLastName, setTravellerLastName] = useState("Traveller");
  const [booking, setBooking] = useState(null);
  const [bookingError, setBookingError] = useState("");
  const [bookingLoading, setBookingLoading] = useState(false);
  const [cancelReason, setCancelReason] = useState("customer_request");
  const [cancelAmount, setCancelAmount] = useState("100");
  const [cancelCurrency, setCancelCurrency] = useState("EUR");
  const [cancelResult, setCancelResult] = useState(null);
  const [cancelError, setCancelError] = useState("");
  const [cancelLoading, setCancelLoading] = useState(false);
  const [globalError, setGlobalError] = useState("");

  useEffect(() => { const id = setInterval(() => setNowMs(Date.now()), 1000); return () => clearInterval(id); }, []);

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
        if (String(msg).toLowerCase().includes("not found")) { setMarketplaceProducts([]); setMarketplaceError(""); }
        else setMarketplaceError(msg);
      } finally {
        if (!cancelled) setMarketplaceLoading(false);
      }
    }
    run();
    return () => { cancelled = true; };
  }, []);

  const expiresAtDate = useMemo(() => parseIso(quote?.expires_at), [quote]);
  const remainingMs = useMemo(() => expiresAtDate ? expiresAtDate.getTime() - nowMs : 0, [expiresAtDate, nowMs]);
  const isExpired = !!expiresAtDate && remainingMs <= 0;

  function updateCheckOut(ciValue, nightsValue) {
    if (!ciValue || !nightsValue) return;
    try {
      const d = new Date(ciValue);
      if (Number.isNaN(d.getTime())) return;
      const dt = new Date(d.getTime());
      dt.setDate(dt.getDate() + Number(nightsValue));
      setCheckOut(`${dt.getFullYear()}-${String(dt.getMonth() + 1).padStart(2, "0")}-${String(dt.getDate()).padStart(2, "0")}`);
    } catch { /* ignore */ }
  }

  async function handleSearch() {
    if (searchLoading) return;
    setSearchError(""); setCityError(""); setDateError("");
    setSearchResults([]); setSelectedOffer(null); setQuote(null); setBooking(null);
    const cityTrimmed = (city || "").trim();
    let hasErr = false;
    if (!cityTrimmed) { setCityError("Sehir bos birakilamaz."); hasErr = true; }
    if (!checkIn || !checkOut) { setDateError("Giris ve cikis tarihleri zorunludur."); hasErr = true; }
    if (!checkIn || !nights || nights <= 0) { setDateError("Gece sayisi en az 1 olmalidir."); hasErr = true; }
    if (hasErr) return;
    setSearchLoading(true);
    try {
      const params = new URLSearchParams({ city: cityTrimmed, check_in: checkIn, check_out: checkOut, adults: String(adults || 1), children: String(children || 0) });
      const res = await api.get(`/b2b/hotels/search?${params.toString()}`);
      const items = res.data?.items || [];
      setSearchResults(items);
      if (!items.length) setSearchError("Bu kriterlerle uygun sonuc bulunamadi.");
    } catch (err) {
      const fe = friendlyError(err);
      setSearchError(fe.detail ? `${fe.title} - ${fe.detail}` : fe.title);
    } finally { setSearchLoading(false); }
  }

  async function handleCreateQuote(e) {
    e.preventDefault();
    setQuoteError(""); setGlobalError(""); setQuote(null); setBookingError(""); setBooking(null); setCancelResult(null);
    setCityError(""); setDateError(""); setSearchError("");
    const cityTrimmed = (city || "").trim();
    let hasErr = false;
    if (!cityTrimmed) { setCityError("Sehir bos birakilamaz."); hasErr = true; }
    if (!checkIn || !checkOut) { setDateError("Giris ve cikis tarihleri zorunludur."); hasErr = true; }
    if (!selectedOffer) { setSearchError("Lutfen listeden bir otel / fiyat secin."); hasErr = true; }
    if (hasErr) return;
    setQuoteLoading(true);
    try {
      const payload = {
        channel_id: "ch_b2b_portal",
        items: [{ product_id: selectedOffer.product_id, room_type_id: "standard", rate_plan_id: selectedOffer.rate_plan_id, check_in: checkIn, check_out: checkOut, occupancy: selectedOffer.occupancy?.adults || adults || 1 }],
      };
      const resp = await api.post("/b2b/quotes", payload);
      const data = resp.data;
      const firstOffer = (data.offers && data.offers[0]) || null;
      setQuote({ quote_id: data.quote_id, expires_at: data.expires_at, offer: firstOffer });
      setSessionQuotes(prev => prev + 1);
    } catch (err) {
      const fe = friendlyError(err);
      const code = err?.response?.data?.error?.code;
      if (code === "product_not_available") setQuoteError("Bu urun sizin icin kapali gorunuyor.");
      else if (code === "invalid_date_range") setDateError("Cikis tarihi, giris tarihinden sonra olmali.");
      else setQuoteError(fe.detail ? `${fe.title} - ${fe.detail}` : fe.title);
    } finally { setQuoteLoading(false); }
  }

  async function handleBook(e) {
    e.preventDefault();
    setBookingError(""); setCancelResult(null); setGlobalError("");
    if (!quote?.quote_id) { setBookingError("Once bir teklif (quote) olusturmaniz gerekiyor"); return; }
    if (isExpired) { setBookingError("Quote suresi dolmus gorunuyor"); return; }
    setBookingLoading(true);
    try {
      const idemKey = crypto.randomUUID();
      const payload = { quote_id: quote.quote_id, customer: { name: customerName || "Demo Customer", email: customerEmail || "demo@example.com" }, travellers: [{ first_name: travellerFirstName || "Demo", last_name: travellerLastName || "Traveller" }] };
      const resp = await api.post("/b2b/bookings", payload, { headers: { "Idempotency-Key": idemKey } });
      const data = resp.data;
      setBooking({ booking_id: data.booking_id, status: data.status, voucher_status: data.voucher_status, finance_flags: data.finance_flags || null });
      setBookingError("");
      setSessionBookings(prev => prev + 1);
    } catch (err) {
      const fe = friendlyError(err);
      const code = err?.response?.data?.error?.code;
      if (code === "credit_limit_exceeded") {
        const d = err?.response?.data?.error?.details || {};
        setBookingError(typeof d.exposure === "number" ? `Kredi limiti asildi: Mevcut exposure ${d.exposure.toFixed(2)}, bu rezervasyon ile ${d.projected?.toFixed(2)} olacak (limit ${d.limit?.toFixed(2)}).` : "Kredi limiti asildi.");
      } else setBookingError(fe.detail ? `${fe.title} - ${fe.detail}` : fe.title);
    } finally { setBookingLoading(false); }
  }

  async function handleCancel(e) {
    e.preventDefault();
    setCancelError("");
    if (!booking?.booking_id) { setCancelError("Once bir rezervasyon olusturmaniz gerekiyor"); return; }
    setCancelLoading(true);
    try {
      const idemKey = crypto.randomUUID();
      const payload = { reason: cancelReason || "customer_request", requested_refund_currency: cancelCurrency || "EUR", requested_refund_amount: Number(cancelAmount || 0) || 0 };
      const resp = await api.post(`/b2b/bookings/${booking.booking_id}/cancel-requests`, payload, { headers: { "Idempotency-Key": idemKey } });
      setCancelResult({ case_id: resp.data.case_id, status: resp.data.status });
    } catch (err) {
      const fe = friendlyError(err);
      setCancelError(fe.detail ? `${fe.title} - ${fe.detail}` : fe.title);
    } finally { setCancelLoading(false); }
  }

  return (
    <div className="space-y-6">
      {globalError && <div className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive"><AlertCircle className="h-4 w-4 mt-0.5" /><div>{globalError}</div></div>}

      {/* Step 1: Search & Quote */}
      <Card className="rounded-2xl border bg-card shadow-sm" data-testid="b2b-step-quote">
        <CardHeader><CardTitle className="flex items-center gap-2 text-base"><CalendarDays className="h-4 w-4" /> 1. Adim - Quote Olustur</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <form onSubmit={handleCreateQuote} className="grid grid-cols-1 md:grid-cols-5 gap-4 items-end">
            <div className="space-y-1 md:col-span-2">
              <Label className="flex items-center gap-2 text-xs"><Store className="h-4 w-4" /> Otel Arama</Label>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                <div>
                  <Label className="text-xs text-muted-foreground">Sehir</Label>
                  <Input value={city} onChange={(e) => setCity(e.target.value)} data-testid="b2b-city-input" />
                  {cityError && <div className="text-xs text-destructive mt-1">{cityError}</div>}
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div><Label className="text-xs text-muted-foreground">Yetiskin</Label><Input type="number" min={1} max={8} value={adults} onChange={(e) => setAdults(Number(e.target.value) || 1)} data-testid="b2b-adults-input" /></div>
                  <div><Label className="text-xs text-muted-foreground">Cocuk</Label><Input type="number" min={0} max={8} value={children} onChange={(e) => setChildren(Number(e.target.value) || 0)} data-testid="b2b-children-input" /></div>
                </div>
              </div>
              {marketplaceLoading && <p className="mt-1 text-xs text-muted-foreground">Yetkili urunler yukleniyor...</p>}
              {!marketplaceLoading && marketplaceError && <p className="mt-1 text-xs text-destructive">{marketplaceError}</p>}
              {!marketplaceLoading && !marketplaceError && marketplaceProducts.length > 0 && (
                <div className="mt-2 max-h-32 overflow-y-auto rounded-md border bg-muted/40">
                  <table className="w-full text-xs">
                    <thead><tr className="text-muted-foreground"><th className="px-2 py-1 text-left font-medium">Urun</th><th className="px-2 py-1 text-left font-medium">Tur</th><th className="px-2 py-1 text-left font-medium">Durum</th><th className="px-2 py-1 text-right font-medium">Komisyon</th></tr></thead>
                    <tbody>
                      {marketplaceProducts.map((p) => (
                        <tr key={p.product_id} className="hover:bg-background">
                          <td className="px-2 py-1"><div className="flex flex-col"><span className="font-medium truncate max-w-[160px]">{p.title}</span><span className="font-mono text-[10px] text-muted-foreground truncate max-w-[200px]">{p.product_id}</span></div></td>
                          <td className="px-2 py-1 text-[10px] capitalize">{p.type || "-"}</td>
                          <td className="px-2 py-1 text-[10px]">{p.status === "active" ? "Aktif" : "Pasif"}</td>
                          <td className="px-2 py-1 text-[10px] text-right">{typeof p.commission_rate === "number" ? `${p.commission_rate}%` : "-"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
              <div className="flex items-center gap-2 mt-2">
                <Button type="button" size="sm" variant="secondary" disabled={searchLoading} onClick={handleSearch} data-testid="b2b-search-btn">
                  {searchLoading && <Loader2 className="h-3 w-3 animate-spin" />} Otel Ara
                </Button>
              </div>
              {searchError && (
                <div className="mt-2 flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-xs text-destructive">
                  <AlertCircle className="h-4 w-4 mt-0.5" />
                  <div className="flex-1 flex flex-col gap-1"><div className="font-medium">Arama basarisiz.</div><div className="text-xs">{searchError}</div>
                    <div><Button type="button" variant="outline" size="sm" className="text-xs" disabled={searchLoading} onClick={(e) => { e.preventDefault(); handleSearch(); }}>Tekrar dene</Button></div>
                  </div>
                </div>
              )}
              <div className="mt-2 text-xs text-muted-foreground">
                {checkIn && checkOut && nights ? <span>Cikis: {checkOut} ({nights} gece)</span> : checkIn && nights ? <span>{nights} gece icin cikis tarihi otomatik hesaplanacaktir.</span> : <span>Tarih ve gece sayisini sectiginizde burada ozet goreceksiniz.</span>}
              </div>
            </div>
            <div className="space-y-1">
              <Label className="flex items-center gap-2"><CalendarDays className="h-4 w-4" /> Giris</Label>
              <Input type="date" value={checkIn} onChange={(e) => { setCheckIn(e.target.value); updateCheckOut(e.target.value, nights); }} data-testid="b2b-checkin-input" />
              {dateError && <div className="text-xs text-destructive mt-1">{dateError}</div>}
            </div>
            <div className="space-y-1">
              <Label className="flex items-center gap-2"><CalendarDays className="h-4 w-4" /> Gece</Label>
              <Input type="number" min={1} value={nights} onChange={(e) => { const val = Number(e.target.value) || 1; setNights(val); updateCheckOut(checkIn, val); }} data-testid="b2b-nights-input" />
            </div>
            <div className="flex justify-end md:col-span-1">
              <Button type="submit" disabled={quoteLoading} className="w-full md:w-auto gap-2" data-testid="b2b-create-quote-btn">
                {quoteLoading && <Loader2 className="h-4 w-4 animate-spin" />} {quoteLoading ? "Hesaplaniyor..." : "Quote Olustur"}
              </Button>
            </div>
          </form>

          {/* Search Results */}
          {searchResults.length > 0 && (
            <div className="mt-4 space-y-3">
              <p className="text-xs font-medium text-muted-foreground">Bulunan oteller ({searchResults.length})</p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {searchResults.map((item, idx) => {
                  const isSelected = selectedOffer && selectedOffer.product_id === item.product_id && selectedOffer.rate_plan_id === item.rate_plan_id;
                  return (
                    <Card key={`${item.product_id}-${item.rate_plan_id}-${idx}`} className={`rounded-2xl border shadow-sm cursor-pointer transition ${isSelected ? "border-primary ring-1 ring-primary/40" : "hover:border-primary/40"}`} onClick={() => setSelectedOffer({ ...item })} data-testid={`b2b-search-result-${idx}`}>
                      <CardContent className="p-4 space-y-2">
                        <div className="flex items-center justify-between gap-2">
                          <div><div className="text-sm font-semibold">{item.hotel_name}</div><div className="text-xs text-muted-foreground">{item.city}, {item.country}</div></div>
                          <div className="text-right"><div className="text-lg font-semibold">{item.selling_total} {item.selling_currency}</div><div className="text-xs text-muted-foreground">{item.nights} gece</div><div className="text-xs text-muted-foreground">Net: {item.base_net} {item.base_currency}</div></div>
                        </div>
                        <div className="flex items-center justify-between text-xs text-muted-foreground">
                          <span>Plan: {item.board}</span>
                          {isSelected && <span className="text-primary font-medium">Secili</span>}
                        </div>
                        {isSelected && <div className="mt-2 flex justify-end"><Button type="button" size="sm" variant="ghost" className="text-xs text-muted-foreground hover:text-destructive" onClick={(e) => { e.stopPropagation(); setSelectedOffer(null); toast.success("Secim kaldirildi"); }}>Secimi kaldir</Button></div>}
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
              <div className="mt-4 flex flex-wrap items-center justify-between gap-2">
                <p className="text-xs text-muted-foreground">Secili otel ve tarihler icin hizli fiyat ozetini goruntuleyebilirsiniz.</p>
                <Button type="button" size="sm" variant="outline" className="gap-1 text-xs" onClick={() => { if (!selectedOffer && !quote?.offer) { toast.error("Lutfen once bir otel/fiyat secin."); return; } setPricePreviewOpen(true); }} data-testid="b2b-price-preview-btn"><Eye className="h-3 w-3" /> Fiyati Gor</Button>
              </div>
            </div>
          )}

          {quoteError && <div className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive"><AlertCircle className="h-4 w-4 mt-0.5" /><div>{quoteError}</div></div>}
          {quote && (
            <div className="mt-2 grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="space-y-1"><div className="text-xs text-muted-foreground">Quote ID</div><div className="font-mono text-sm break-all" data-testid="b2b-quote-id">{quote.quote_id}</div></div>
              <div className="space-y-1"><div className="text-xs text-muted-foreground">Fiyat (sell)</div><div className="text-lg font-semibold text-primary">{quote.offer?.sell} {quote.offer?.currency || "EUR"}</div></div>
              <div className="space-y-1">
                <div className="flex items-center gap-2 text-xs text-muted-foreground"><Timer className="h-3 w-3" /><span>Son kullanma</span></div>
                <Badge variant={isExpired ? "destructive" : "secondary"} className="text-xs">{isExpired ? "Suresi doldu" : `Kalan: ${formatRemaining(remainingMs)}`}</Badge>
                <div className="text-xs text-muted-foreground mt-1">Son gecerlilik: {expiresAtDate ? expiresAtDate.toLocaleString("tr-TR") : quote.expires_at}</div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Step 2: Book */}
      <Card className="rounded-2xl border bg-card shadow-sm" data-testid="b2b-step-book">
        <CardHeader><CardTitle className="flex items-center gap-2 text-base"><CreditCard className="h-4 w-4" /> 2. Adim - Rezervasyon Olustur (Book)</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <p className="text-xs text-muted-foreground">Not: Book isteginde kullanilan Idempotency-Key console&apos;a yaziliyor.</p>
          <form onSubmit={handleBook} className="grid grid-cols-1 md:grid-cols-3 gap-4 items-end">
            <div className="space-y-1"><Label>Musteri Adi</Label><Input value={customerName} onChange={(e) => setCustomerName(e.target.value)} data-testid="b2b-customer-name" /></div>
            <div className="space-y-1"><Label>Musteri Email</Label><Input type="email" value={customerEmail} onChange={(e) => setCustomerEmail(e.target.value)} data-testid="b2b-customer-email" /></div>
            <div className="space-y-1"><Label>Traveller Ad Soyad</Label><div className="flex gap-2"><Input placeholder="Ad" value={travellerFirstName} onChange={(e) => setTravellerFirstName(e.target.value)} data-testid="b2b-traveller-first" /><Input placeholder="Soyad" value={travellerLastName} onChange={(e) => setTravellerLastName(e.target.value)} data-testid="b2b-traveller-last" /></div></div>
            <div className="flex justify-end md:col-span-3"><Button type="submit" disabled={bookingLoading} className="w-full md:w-auto gap-2" data-testid="b2b-book-btn">{bookingLoading && <Loader2 className="h-4 w-4 animate-spin" />} {bookingLoading ? "Gonderiliyor..." : "Rezervasyon Olustur"}</Button></div>
          </form>
          {bookingError && <div className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive"><AlertCircle className="h-4 w-4 mt-0.5" /><div>{bookingError}</div></div>}
          {booking && (
            <div className="mt-2 space-y-2">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="space-y-1"><div className="text-xs text-muted-foreground">Booking ID</div><div className="font-mono text-sm break-all" data-testid="b2b-booking-id">{booking.booking_id}</div></div>
                <div className="space-y-1"><div className="text-xs text-muted-foreground">Durum</div><Badge variant="secondary" className="text-xs">{booking.status}</Badge></div>
                <div className="space-y-1"><div className="text-xs text-muted-foreground">Voucher Durumu</div><Badge variant="outline" className="text-xs">{booking.voucher_status}</Badge></div>
                {booking.status === "VOUCHERED" && (
                  <div className="space-y-1"><div className="text-xs text-muted-foreground">Voucher</div><a href={buildApiUrl(`/b2b/bookings/${booking.booking_id}/voucher`)} target="_blank" rel="noreferrer" className="inline-flex items-center text-xs text-primary hover:underline">Voucher Goruntule</a></div>
                )}
              </div>
              {booking.finance_flags?.near_limit && (
                <div className="rounded-xl border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-800 flex items-start gap-2">
                  <span className="mt-0.5 text-sm">!</span>
                  <div><div className="font-semibold">Kredi limitinize yaklastiniz</div><div className="mt-0.5">Hesap ozetinizi kontrol ederek limit artisi talep etmeyi degerlendirebilirsiniz.</div></div>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Step 3: Cancel */}
      <Card className="rounded-2xl border bg-card shadow-sm" data-testid="b2b-step-cancel">
        <CardHeader><CardTitle className="flex items-center gap-2 text-base"><XCircle className="h-4 w-4" /> 3. Adim - Iptal Talebi (Cancel Request)</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          {booking ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-1"><div className="text-xs text-muted-foreground">Son Booking</div><div className="font-mono text-sm break-all">{booking.booking_id}</div><div className="text-xs text-muted-foreground mt-1">Durum: <span className="font-medium">{booking.status}</span></div></div>
              <form onSubmit={handleCancel} className="space-y-3">
                <div className="space-y-1"><Label>Iptal Nedeni</Label><Input value={cancelReason} onChange={(e) => setCancelReason(e.target.value)} data-testid="b2b-cancel-reason" /></div>
                <div className="flex gap-2">
                  <div className="space-y-1 flex-1"><Label>Iade Talebi (Tutar)</Label><Input type="number" min={0} value={cancelAmount} onChange={(e) => setCancelAmount(e.target.value)} data-testid="b2b-cancel-amount" /></div>
                  <div className="space-y-1 w-24"><Label>Para Birimi</Label><Input value={cancelCurrency} onChange={(e) => setCancelCurrency(e.target.value)} data-testid="b2b-cancel-currency" /></div>
                </div>
                <div className="flex justify-end"><Button type="submit" disabled={cancelLoading} className="w-full md:w-auto gap-2" data-testid="b2b-cancel-btn">{cancelLoading && <Loader2 className="h-4 w-4 animate-spin" />} {cancelLoading ? "Gonderiliyor..." : "Iptal Talebi Olustur"}</Button></div>
              </form>
            </div>
          ) : (
            <div className="text-sm text-muted-foreground">Henuz bu oturumda olusturulmus bir booking yok. Once &quot;Rezervasyon Olustur&quot; adimini tamamlayin.</div>
          )}
          {cancelError && <div className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive"><AlertCircle className="h-4 w-4 mt-0.5" /><div>{cancelError}</div></div>}
          {cancelResult && (
            <div className="mt-2 grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-1"><div className="text-xs text-muted-foreground">Case ID</div><div className="font-mono text-sm break-all" data-testid="b2b-cancel-case-id">{cancelResult.case_id}</div></div>
              <div className="space-y-1"><div className="text-xs text-muted-foreground">Case Durumu</div><Badge variant="secondary" className="text-xs">{cancelResult.status}</Badge></div>
            </div>
          )}
        </CardContent>
      </Card>

      <PricePreviewDialog open={pricePreviewOpen} onOpenChange={setPricePreviewOpen} checkIn={checkIn} checkOut={checkOut} adults={adults} childrenCount={children} selectedOffer={selectedOffer} quoteOffer={quote?.offer || null} />
    </div>
  );
}

/* ── Main Page ────────────────────────────────────────────── */
export default function B2BPortalPage() {
  const [activeTab, setActiveTab] = useState("flow");
  const [sessionQuotes, setSessionQuotes] = useState(0);
  const [sessionBookings, setSessionBookings] = useState(0);

  const tabs = [
    { value: "flow", label: "Quote / Book / Cancel" },
    { value: "list", label: "Rezervasyonlarim" },
  ];

  return (
    <PageShell
      title="B2B Portal"
      description="Agentis sinifi demo akisi: Quote, Book, Cancel. Tum istekler agency token'i ile B2B backend'e gider."
      tabs={tabs}
      activeTab={activeTab}
      onTabChange={setActiveTab}
    >
      <div className="space-y-6" data-testid="b2b-portal-page">
        <AccountSummaryCard />
        <B2BAnnouncementsCard />
        <B2BDashboardKpiRow sessionQuotes={sessionQuotes} sessionBookings={sessionBookings} />

        {activeTab === "flow" && (
          <QuoteBookCancelFlow
            sessionQuotes={sessionQuotes}
            setSessionQuotes={setSessionQuotes}
            sessionBookings={sessionBookings}
            setSessionBookings={setSessionBookings}
          />
        )}

        {activeTab === "list" && <BookingListTab />}
      </div>
    </PageShell>
  );
}
