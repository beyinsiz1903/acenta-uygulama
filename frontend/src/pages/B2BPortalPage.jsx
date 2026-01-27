import React, { useEffect, useMemo, useState } from "react";
import { AlertCircle, CalendarDays, Loader2, User, CreditCard, Timer, XCircle, RefreshCw, Store, Eye } from "lucide-react";
import { api, apiErrorMessage } from "../lib/api";
import { bookingStatusLabelTr } from "../utils/bookingStatusLabels";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { B2BAnnouncementsCard } from "../components/B2BAnnouncementsCard";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "../components/ui/dialog";
import { toast } from "sonner";
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

function PricePreviewDialog({ open, onOpenChange, checkIn, checkOut, adults, childrenCount, selectedOffer, quoteOffer }) {
  const sourceLabel = quoteOffer ? "Quote" : selectedOffer ? "Arama Sonucu" : "-";
  const offer = quoteOffer || selectedOffer || null;
  const total =
    (typeof offer?.sell === "number" && offer.sell) ||
    (typeof offer?.selling_total === "number" && offer.selling_total) ||
    (typeof offer?.selling_total === "string" && Number(offer.selling_total)) ||
    null;
  const currency = offer?.currency || offer?.selling_currency || "EUR";

  const nightsFromOffer =
    (typeof offer?.nights === "number" && offer.nights) ||
    (offer?.stay && typeof offer.stay.nights === "number" && offer.stay.nights) ||
    null;

  let nights = nightsFromOffer;
  let nightsByDates: number | null = null;
  if (checkIn && checkOut) {
    try {
      const a = new Date(`${checkIn}T00:00:00`);
      const b = new Date(`${checkOut}T00:00:00`);
      const diff = Math.round((b - a) / (1000 * 60 * 60 * 24));
      if (Number.isFinite(diff) && diff > 0) nightsByDates = diff;
    } catch {
      // ignore
    }
  }
  if (!nights && nightsByDates) {
    nights = nightsByDates;
  }

  const perNight = nights && total ? total / nights : null;

  const occLabel = `${adults || 0} yetişkin${childrenCount ? `, ${childrenCount} çocuk` : ""}`;
  const dateLabel = checkIn && checkOut
    ? `${new Date(checkIn).toLocaleDateString("tr-TR")} → ${new Date(checkOut).toLocaleDateString("tr-TR")}`
    : checkIn || "-";

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Hızlı Fiyat Önizleme</DialogTitle>
          <DialogDescription>
            Bu dialog, mevcut arama veya quote sonuçlarından gelen fiyat bilgisi ile hazırlanır. Backend&apos;e
            ek istek göndermez.
          </DialogDescription>
        </DialogHeader>

        {!offer ? (
          <p className="text-sm text-muted-foreground">
            Gösterilecek bir fiyat bulunamadı. Lütfen önce arama yapıp bir sonuç seçin veya quote oluşturun.
          </p>
        ) : (
          <div className="space-y-4 text-sm">
            <div className="text-xs text-muted-foreground">Kaynak: {sourceLabel}</div>
            <div className="space-y-1">
              <div className="text-xs text-muted-foreground">Tarih ve konaklama</div>
              <div className="font-medium">{dateLabel}</div>
              <div className="text-xs text-muted-foreground">{occLabel}</div>
            </div>

            <div className="grid grid-cols-3 gap-3">
              <div className="space-y-1">
                <div className="text-xs text-muted-foreground">Toplam satış</div>
                <div className="text-base font-semibold">
                  {total != null ? (
                    <>
                      {total.toFixed(2)} {currency}
                    </>
                  ) : (
                    "-"
                  )}
                </div>
              </div>
              <div className="space-y-1">
                <div className="text-xs text-muted-foreground">Gece</div>
                <div className="text-base font-semibold">{nights || "-"}</div>
              </div>
              <div className="space-y-1">
                <div className="text-xs text-muted-foreground">Gece başı</div>
                <div className="text-base font-semibold">
                  {perNight != null ? (
                    <>
                      {perNight.toFixed(2)} {currency}
                    </>
                  ) : (
                    "-"
                  )}
                </div>
              </div>
            </div>

            <div className="rounded-md border bg-muted/40 px-3 py-2 text-[11px] text-muted-foreground">
              Bu özet, seçili sonuca ait verilerden türetilmiştir. Kesin tutar için rezervasyon akışındaki detay
              ekranını kullanın.
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

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
        <div className="flex flex-wrap items-center gap-2 justify-end">
          <div className="flex items-center gap-1">
            <input
              className="h-8 rounded-md border bg-background px-2 text-xs"
              placeholder="Ara: Booking ID / Misafir / Otel"
              value={listQuery}
              onChange={(e) => setListQuery(e.target.value)}
            />
            {listQuery && (
              <Button
                type="button"
                size="icon"
                variant="ghost"
                className="h-8 w-8 text-muted-foreground"
                onClick={() => setListQuery("")}
              >
                ×
              </Button>
            )}
          </div>
          <input
            type="date"
            className="h-8 rounded-md border bg-background px-2 text-xs"
            value={checkInFilter}
            onChange={(e) => setCheckInFilter(e.target.value)}
          />
          <input
            type="date"
            className="h-8 rounded-md border bg-background px-2 text-xs"
            value={checkOutFilter}
            onChange={(e) => setCheckOutFilter(e.target.value)}
          />
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

        {items.length > 0 && (() => {
          const filteredItems = items.filter((b) => {
            const q = listQuery.trim().toLowerCase();
            const hasQuery = !!q;

            const id = String(b.booking_id || b.id || "").toLowerCase();
            const guest = String(b.primary_guest_name || b.guest_name || "").toLowerCase();
            const product = String(b.product_name || b.hotel_name || "").toLowerCase();
            const ref = String(b.reference || b.voucher_code || "").toLowerCase();
            const haystack = `${id} ${guest} ${product} ${ref}`;

            if (hasQuery && !haystack.includes(q)) return false;

            // Tarih filtresi (check_in date string üzerinden)
            const from = checkInFilter ? new Date(checkInFilter) : null;
            const to = checkOutFilter ? new Date(checkOutFilter) : null;
            const rawDate = b.check_in || b.checkin || b.start_date || "";
            let d = null;
            if (rawDate) {
              const parsed = new Date(rawDate);
              if (!Number.isNaN(parsed.getTime())) d = parsed;
            }
            if (from && d && d < from) return false;
            if (to && d && d > to) return false;

            return true;
          });

          return (
            <>
              {!loading && !error && items.length > 0 && filteredItems.length === 0 && (
                <div className="text-sm text-muted-foreground">
                  Sonuç bulunamadı.
                  <div className="text-[11px] text-muted-foreground">Arama terimini kısaltmayı deneyin.</div>
                </div>
              )}

              {filteredItems.length > 0 && (
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
                  {filteredItems.map((b) => {
                  const s = String(b.status || "").toUpperCase();
                  const canCancel = canCancelStatuses.has(s);
                  const voucherUrl = s === "VOUCHERED" ? `${process.env.REACT_APP_BACKEND_URL}/api/b2b/bookings/${b.booking_id}/voucher` : null;

                  return (
                    <tr key={b.booking_id} className="border-b last:border-0">
                      <td className="px-2 py-2 font-mono text-[11px] max-w-[160px] truncate" title={b.booking_id}>
                        {b.booking_id}
                      </td>
                      <td className="px-2 py-2 text-xs">{b.primary_guest_name || "-"}</td>
        {!loading && !error && items.length > 0 && (
          <div className="text-[11px] text-muted-foreground flex items-center justify-between mt-2">
            <span>
              {filteredItems.length}/{items.length} sonuç
            </span>
            {(checkInFilter || checkOutFilter) && (
              <Button
                type="button"
                size="xs"
                variant="ghost"
                className="text-[11px]"
                onClick={() => {
                  setCheckInFilter("");
                  setCheckOutFilter("");
                }}
              >
                Tarih filtresini temizle
              </Button>
            )}
          </div>
        )}

                      <td className="px-2 py-2 text-xs">{b.product_name || "-"}</td>
                      <td className="px-2 py-2 text-xs">
                        {b.check_in ? new Date(b.check_in).toLocaleDateString("tr-TR") : "-"}
                      </td>
                      <td className="px-2 py-2 text-xs">
                        {b.check_out ? new Date(b.check_out).toLocaleDateString("tr-TR") : "-"}
                      </td>
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
            </>
          );
        })()}
      </CardContent>
    </Card>
  );
}

export default function B2BPortalPage() {
  const [activeTab, setActiveTab] = useState("flow"); // "flow" | "list"

  // Session KPIs
  const [sessionQuotes, setSessionQuotes] = useState(0);
  const [sessionBookings, setSessionBookings] = useState(0);

  // Search + quote form state (P0.2: otel arama)
  const [city, setCity] = useState("Istanbul");
  const [checkIn, setCheckIn] = useState("");
  const [checkOut, setCheckOut] = useState("");
  const [nights, setNights] = useState(2);
  const [adults, setAdults] = useState(2);
  const [children, setChildren] = useState(0);
  const [quoteProductId, setQuoteProductId] = useState("demo_product_1");
  const [occupancy, setOccupancy] = useState(1);

  // Search results & selection
  const [searchResults, setSearchResults] = useState([]); // HotelSearchResponseItem[]
  const [selectedOffer, setSelectedOffer] = useState(null); // Seçili hotel + rate plan
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchError, setSearchError] = useState("");
  const [cityError, setCityError] = useState("");
  const [dateError, setDateError] = useState("");

  // Quick fiyat önizleme (UI-only)
  const [pricePreviewOpen, setPricePreviewOpen] = useState(false);

  // Quote result
  const [quote, setQuote] = useState(null); // { quote_id, expires_at, offer }
  const [quoteError, setQuoteError] = useState("");
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
  function friendlyError(err) {
    const resp = err?.response?.data;
    const code = resp?.error?.code;
    const hasDomain = !!(resp?.error || err?.response?.status);
    const raw = apiErrorMessage(err);

    // Network / timeout tespiti
    const msg = String(err?.message || raw || "");
    const isNetwork =
      err?.code === "ECONNABORTED" ||
      msg.toLowerCase().includes("network error") ||
      msg.toLowerCase().includes("timeout") ||
      msg.toLowerCase().includes("failed to fetch");

    if (isNetwork) {
      return {
        title: "Bağlantı hatası. Lütfen tekrar deneyin.",
        detail: raw || undefined,
        code: code || err?.code,
        kind: "network",
      };
    }

    if (hasDomain) {
      const backendMsg = resp?.error?.message || raw || "İşlem başarısız.";
      return {
        title: "İşlem başarısız.",
        detail: backendMsg,
        code: code,
        kind: "domain",
      };
    }

    return {
      title: "Bir hata oluştu.",
      detail: raw || undefined,
      code: code || err?.code,
      kind: "unknown",
    };
  }

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

  async function handleSearch() {
    if (searchLoading) return;

    setSearchError("");
    setCityError("");
    setDateError("");

    setSearchResults([]);
    setSelectedOffer(null);
    setQuote(null);
    setBooking(null);

    const cityTrimmed = (city || "").trim();
    let hasErrorLocal = false;
    if (!cityTrimmed) {
      setCityError("Şehir boş bırakılamaz.");
      hasErrorLocal = true;
    }
    if (!checkIn || !checkOut) {
      setDateError("Giriş ve çıkış tarihleri zorunludur.");
      hasErrorLocal = true;
    }
    if (!checkIn || !nights || nights <= 0) {
      setDateError("Gece sayısı en az 1 olmalıdır.");
      hasErrorLocal = true;
    }
    if (hasErrorLocal) return;

    setSearchLoading(true);
    try {
      const params = new URLSearchParams({
        city: cityTrimmed,
        check_in: checkIn,
        check_out: checkOut,
        adults: String(adults || 1),
        children: String(children || 0),
      });
      const res = await api.get(`/b2b/hotels/search?${params.toString()}`);
      const items = res.data?.items || [];
      setSearchResults(items);
      if (!items.length) {
        setSearchError("Bu kriterlerle uygun sonuç bulunamadı.");
      }
    } catch (err) {
      const fe = friendlyError(err);
      const detail = fe.detail || "";
      const suffix = fe.code ? ` (${fe.code})` : "";
      setSearchError(detail ? `${fe.title} ${suffix} - ${detail}` : `${fe.title}${suffix}`);
    } finally {
      setSearchLoading(false);
    }
  }

  async function handleCreateQuote(e) {
    e.preventDefault();
    setQuoteError("");
    setGlobalError("");
    setQuote(null);
    setBookingError("");
    setBooking(null);
    setCancelResult(null);

    // Basit form validasyonu
    setCityError("");
    setDateError("");
    setSearchError("");

    const cityTrimmed = (city || "").trim();
    let hasError = false;
    if (!cityTrimmed) {
      setCityError("Şehir boş bırakılamaz.");
      hasError = true;
    }
    if (!checkIn || !checkOut) {
      setDateError("Giriş ve çıkış tarihleri zorunludur.");
      hasError = true;
    }
    if (!checkIn || !nights || nights <= 0) {
      setDateError("Gece sayısı en az 1 olmalıdır.");
      hasError = true;
    }
    if (!selectedOffer) {
      setSearchError("Lütfen listeden bir otel / fiyat seçin.");
      hasError = true;
    }
    if (hasError) return;

    setQuoteLoading(true);
    try {
      const payload = {
        channel_id: "ch_b2b_portal",
        items: [
          {
            product_id: selectedOffer.product_id,
            room_type_id: "standard",
            rate_plan_id: selectedOffer.rate_plan_id,
            check_in: checkIn,
            check_out: checkOut,
            occupancy: selectedOffer.occupancy?.adults || adults || 1,
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
      const resp = err?.response?.data;
      const fe = friendlyError(err);
      const code = resp?.error?.code;

      if (code === "product_not_available") {
        setQuoteError(
          "Bu ürün sizin için kapalı görünüyor. Lütfen B2B Marketplace yetkilendirmelerinizi kontrol edin veya farklı bir otel seçin."
        );
      } else if (code === "invalid_date_range") {
        setDateError("Çıkış tarihi, giriş tarihinden sonra olmalı.");
      } else {
        const detail = fe.detail || "";
        const suffix = fe.code ? ` (${fe.code})` : "";
        setQuoteError(detail ? `${fe.title} ${suffix} - ${detail}` : `${fe.title}${suffix}`);
      }
    } finally {
      setQuoteLoading(false);
    }
  }

  async function handleBook(e) {
    e.preventDefault();
    setBookingError("");
    setCancelResult(null);
    setGlobalError("");

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
      const code = resp?.error?.code;
      const fe = friendlyError(err);

      if (code === "credit_limit_exceeded") {
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
      } else {
        const detail = fe.detail || "";
        const suffix = fe.code ? ` (${fe.code})` : "";
        setBookingError(detail ? `${fe.title} ${suffix} - ${detail}` : `${fe.title}${suffix}`);
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
      const fe = friendlyError(err);
      const detail = fe.detail || "";
      const suffix = fe.code ? ` (${fe.code})` : "";
      setCancelError(detail ? `${fe.title} ${suffix} - ${detail}` : `${fe.title}${suffix}`);
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
                    Otel Arama
                  </Label>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                    <div>
                      <Label className="text-[11px] text-muted-foreground">Şehir</Label>
                      <Input value={city} onChange={(e) => setCity(e.target.value)} />
                      {cityError && <div className="text-[11px] text-destructive mt-1">{cityError}</div>}
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <Label className="text-[11px] text-muted-foreground">Yetişkin</Label>
                        <Input
                          type="number"
                          min={1}
                          max={8}
                          value={adults}
                          onChange={(e) => setAdults(Number(e.target.value) || 1)}
                        />
                      </div>
                      <div>
                        <Label className="text-[11px] text-muted-foreground">Çocuk</Label>
                        <Input
                          type="number"
                          min={0}
                          max={8}
                          value={children}
                          onChange={(e) => setChildren(Number(e.target.value) || 0)}
                        />
                      </div>
                    </div>
                  </div>

                  {/* Marketplace ürün listesi: referans amaçlı */}
                  {marketplaceLoading && (
                    <p className="mt-1 text-[11px] text-muted-foreground">Yetkili ürünler yükleniyor...</p>
                  )}
                  {!marketplaceLoading && marketplaceError && (
                    <p className="mt-1 text-[11px] text-destructive">{marketplaceError}</p>
                  )}
                  {!marketplaceLoading && !marketplaceError && marketplaceProducts.length > 0 && (
                    <div className="mt-2 max-h-32 overflow-y-auto rounded-md border bg-muted/40">
                      <table className="w-full text-[11px]">
                        <thead>
                          <tr className="text-muted-foreground">
                            <th className="px-2 py-1 text-left font-medium">Ürün</th>
                            <th className="px-2 py-1 text-left font-medium">Tür</th>
                            <th className="px-2 py-1 text-left font-medium">Durum</th>
                            <th className="px-2 py-1 text-right font-medium">Komisyon</th>
                          </tr>
                        </thead>
                        <tbody>
                          {marketplaceProducts.map((p) => (
                            <tr key={p.product_id} className="hover:bg-background">
                              <td className="px-2 py-1">
                                <div className="flex flex-col">
                                  <span className="font-medium truncate max-w-[160px]">{p.title}</span>
                                  <span className="font-mono text-[10px] text-muted-foreground truncate max-w-[200px]">
                                    {p.product_id}
                                  </span>
                                </div>
                              </td>
                              <td className="px-2 py-1 text-[10px] capitalize">{p.type || "-"}</td>
                              <td className="px-2 py-1 text-[10px]">
                                {p.status === "active" ? "Aktif" : "Pasif"}
                              </td>
                              <td className="px-2 py-1 text-[10px] text-right">
                                {typeof p.commission_rate === "number" ? `${p.commission_rate}%` : "-"}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
          <div className="flex items-center gap-2 mt-2">
            <Button
              type="button"
              size="sm"
              variant="secondary"
              disabled={searchLoading}
              onClick={handleSearch}
            >
              {searchLoading && <Loader2 className="h-3 w-3 animate-spin" />}
              Otel Ara
            </Button>
          </div>

          {searchError && (
            <div className="mt-2 flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-xs text-destructive">
              <AlertCircle className="h-4 w-4 mt-0.5" />
              <div className="flex-1 flex flex-col gap-1">
                <div className="font-medium">Arama başarısız.</div>
                <div className="text-[11px] text-destructive/90">{searchError}</div>
                <div>
                  <Button
                    type="button"
                    variant="outline"
                    size="xs"
                    className="text-[11px]"
                    disabled={searchLoading}
                    onClick={(e) => {
                      e.preventDefault();
                      handleSearch();
                    }}
                  >
                    Tekrar dene
                  </Button>
                </div>
              </div>
            </div>
          )}

          {/* Tarih özet satırı */}
          <div className="mt-2 text-[11px] text-muted-foreground">
            {checkIn && checkOut && nights ? (
              <span>
                Çıkış: {checkOut} ({nights} gece)
              </span>
            ) : checkIn && nights ? (
              <span>
                {nights} gece için çıkış tarihi otomatik hesaplanacaktır.
              </span>
            ) : (
              <span>Tarih ve gece sayısını seçtiğinizde burada özet göreceksiniz.</span>
            )}
          </div>

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
                    onChange={(e) => {
                      const value = e.target.value;
                      setCheckIn(value);
                      // check-out otomatik: nights varsayılan 2
                      if (value && nights) {
                        try {
                          const d = new Date(value);
                          if (!Number.isNaN(d.getTime())) {
                            const dt = new Date(d.getTime());
                            dt.setDate(dt.getDate() + Number(nights) || 0);
                            const y = dt.getFullYear();
                            const m = String(dt.getMonth() + 1).padStart(2, "0");
                            const day = String(dt.getDate()).padStart(2, "0");
                            setCheckOut(`${y}-${m}-${day}`);
                          }
                        } catch {
                          // ignore
                        }
                      }
                    }}
                  />
                  {dateError && (
                    <div className="text-[11px] text-destructive mt-1">{dateError}</div>
                  )}
                </div>

                <div className="space-y-1">
                  <Label htmlFor="nights" className="flex items-center gap-2">
                    <CalendarDays className="h-4 w-4" />
                    Gece
                  </Label>
                  <Input
                    id="nights"
                    type="number"
                    min={1}
                    value={nights}
                    onChange={(e) => {
                      const val = Number(e.target.value) || 1;
                      setNights(val);
                      if (checkIn) {
                        try {
                          const d = new Date(checkIn);
                          if (!Number.isNaN(d.getTime())) {
                            const dt = new Date(d.getTime());
                            dt.setDate(dt.getDate() + val);
                            const y = dt.getFullYear();
                            const m = String(dt.getMonth() + 1).padStart(2, "0");
                            const day = String(dt.getDate()).padStart(2, "0");
                            setCheckOut(`${y}-${m}-${day}`);
                          }
                        } catch {
                          // ignore
                        }
                      }
                    }}
                  />
                </div>

                <div className="flex justify-end md:col-span-1">
                  <Button type="submit" disabled={quoteLoading} className="w-full md:w-auto gap-2">
                    {quoteLoading && <Loader2 className="h-4 w-4 animate-spin" />}
                    {quoteLoading ? "Hesaplanıyor..." : "Quote Oluştur"}
                  </Button>
                </div>
              </form>

              {/* Adım 1.5: Arama Sonuçları (otel kartları) */}
              {searchResults.length > 0 && (
                <div className="mt-4 space-y-3">
                  <p className="text-xs font-medium text-muted-foreground">
                    Bulunan oteller ({searchResults.length})
                  </p>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {searchResults.map((item, idx) => {
                      const isSelected =
                        selectedOffer &&
                        selectedOffer.product_id === item.product_id &&
                        selectedOffer.rate_plan_id === item.rate_plan_id;

                      return (
                        <Card
                          key={`${item.product_id}-${item.rate_plan_id}-${idx}`}
                          className={`rounded-2xl border shadow-sm cursor-pointer transition ${
                            isSelected ? "border-primary ring-1 ring-primary/40" : "hover:border-primary/40"
                          }`}
                          onClick={() => setSelectedOffer({ ...item })}
                        >
                          <CardContent className="p-4 space-y-2">
                            <div className="flex items-center justify-between gap-2">
                              <div>
                                <div className="text-sm font-semibold">{item.hotel_name}</div>
                                <div className="text-xs text-muted-foreground">
                                  {item.city}, {item.country}
                                </div>
                              </div>
                              <div className="text-right">
                                <div className="text-lg font-semibold">
                                  {item.selling_total} {item.selling_currency}
                                </div>
                                <div className="text-[11px] text-muted-foreground">
                                  {item.nights} gece · {item.occupancy?.adults || adults || 0} yetişkin
                                </div>
                                <div className="text-[11px] text-muted-foreground">
                                  Net: {item.base_net} {item.base_currency}
                                </div>
                              </div>
                            </div>
                            <div className="flex items-center justify-between text-[11px] text-muted-foreground">
                              <span>Plan: {item.board}</span>
                              {isSelected && <span className="text-primary font-medium">Seçili</span>}
                            {isSelected && (
                              <div className="mt-2 flex justify-end">
                                <Button
                                  type="button"
                                  size="xs"
                                  variant="ghost"
                                  className="text-[11px] text-muted-foreground hover:text-destructive"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    setSelectedOffer(null);
                                    toast.success("Seçim kaldırıldı");
                                  }}
                                >
                                  Seçimi kaldır
                                </Button>
                              </div>
                            )}

                            </div>
                          </CardContent>
                        </Card>
                      );
                    })}
                  </div>

                  {/* Hızlı fiyat önizleme butonu */}
                  <div className="mt-4 flex flex-wrap items-center justify-between gap-2">
                    <p className="text-[11px] text-muted-foreground">
                      Seçili otel ve tarihler için hızlı fiyat özetini görüntüleyebilirsiniz.
                    </p>
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      className="gap-1 text-xs"
                      onClick={() => {
                        if (!selectedOffer && !quote?.offer) {
                          toast.error("Lütfen önce bir otel/fiyat seçin veya bir quote oluşturun.");
                          return;
                        }
                        setPricePreviewOpen(true);
                      }}
                    >
                      <Eye className="h-3 w-3" />
                      Fiyatı Gör
                    </Button>
                  </div>
                </div>
              )}

              {/* Quote error and results section */}
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


      {/* Hızlı fiyat önizleme dialog'u (UI-only) */}
      <PricePreviewDialog
        open={pricePreviewOpen}
        onOpenChange={setPricePreviewOpen}
        checkIn={checkIn}
        checkOut={checkOut}
        adults={adults}
        childrenCount={children}
        selectedOffer={selectedOffer}
        quoteOffer={quote?.offer || null}
      />

      {activeTab === "list" && <BookingListTab />}
    </div>
  );
}
