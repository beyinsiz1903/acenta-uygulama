import React, { useEffect, useMemo, useState } from "react";
import { Hotel, AlertCircle, Loader2 } from "lucide-react";
import { format } from "date-fns";
import { toast } from "../hooks/use-toast";
import { api, apiErrorMessage, getUser } from "../lib/api";
import { useNavigate } from "react-router-dom";
import { Input } from "../components/ui/input";
import { Badge } from "../components/ui/badge";
import { Card, CardContent } from "../components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { Button } from "../components/ui/button";
import StepBar from "../components/StepBar";

const CM_META = {
  connected: { label: "CM: Connected", variant: "default" },
  configured: { label: "CM: Configured", variant: "secondary" },
  error: { label: "CM: Error", variant: "destructive" },
  disabled: { label: "CM: Disabled", variant: "outline" },
  not_configured: { label: "CM: Not configured", variant: "outline" },
};

function isLinkActive(hotel) {
  if (typeof hotel?.active === "boolean") return hotel.active;
  const status = (hotel?.status_label || "").toLowerCase();
  if (status === "satışa açık") return true;
  return false;
}

export default function AgencyHotelsPage() {
  const navigate = useNavigate();
  // Legacy agency_hotel_links listing (FAZ-7). Kept for backward compatibility but P0.2'de
  // asıl arama/fiyatlama akışını alttaki 3 adımlı search/quote/booking akışı taşıyor.
  const [hotels, setHotels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [locationFilter, setLocationFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");

  // P0.2 Search → Quote → Booking state
  const [step, setStep] = useState(1); // 1: arama, 2: fiyat, 3: misafir
  const [city, setCity] = useState("Istanbul");
  const [checkIn, setCheckIn] = useState("");
  const [checkOut, setCheckOut] = useState("");
  const [adults, setAdults] = useState(2);
  const [children, setChildren] = useState(0);
  const [searchResults, setSearchResults] = useState([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchError, setSearchError] = useState("");
  const [cityError, setCityError] = useState("");
  const [dateError, setDateError] = useState("");


  const [selectedOffer, setSelectedOffer] = useState(null); // { product_id, rate_plan_id, ... }
  const [quote, setQuote] = useState(null); // { quote_id, expires_at, offer }
  const [quoteLoading, setQuoteLoading] = useState(false);
  const [quoteError, setQuoteError] = useState("");

  const [customerName, setCustomerName] = useState("P0.2 Test Misafir");
  const [customerEmail, setCustomerEmail] = useState("p02-test@example.com");
  const [travellerFirstName, setTravellerFirstName] = useState("P0.2");
  const [travellerLastName, setTravellerLastName] = useState("Guest");
  const [booking, setBooking] = useState(null);
  const [bookingLoading, setBookingLoading] = useState(false);
  const [bookingError, setBookingError] = useState("");

  const user = getUser();

  const goHotelBookings = (hotelId) => {
    navigate(`/app/agency/bookings?hotel_id=${encodeURIComponent(hotelId)}`);
  };

  const goHotelDetail = (hotelId) => {
    navigate(`/app/agency/hotels/${encodeURIComponent(hotelId)}`);
  };

  useEffect(() => {
    // Debug: agency_id kontrolü
    console.log("[AgencyHotelsPage] User context:", {
      email: user?.email,
      agency_id: user?.agency_id,
      roles: user?.roles,
    });

    loadHotels();

    // Tarihleri P0.2 için deterministik set et (bugün+1 / bugün+3)
    const today = new Date();
    const plus1 = new Date(today.getTime() + 24 * 60 * 60 * 1000);
    const plus3 = new Date(today.getTime() + 3 * 24 * 60 * 60 * 1000);
    setCheckIn(format(plus1, "yyyy-MM-dd"));
    setCheckOut(format(plus3, "yyyy-MM-dd"));
  }, []);

  async function loadHotels() {
    setLoading(true);
    setError("");
    try {
      const resp = await api.get("/agency/hotels");
      console.log("[AgencyHotelsPage] Loaded hotels:", resp.data);
      const items = resp.data?.items || resp.data || [];
      setHotels(items);
    } catch (err) {
      console.error("[AgencyHotelsPage] Load error:", err);
      const msg = apiErrorMessage(err) || "";
      // 404 / Not Found durumunda bof liste gibi davran, kdrmdz hata gstermeyelim
      if (msg.toLowerCase().includes("not found")) {
        setHotels([]);
        setError("");
      } else {
        setError(msg);
      }
    } finally {
      setLoading(false);
    }
  }

  const filtered = useMemo(() => {
    const query = search.trim().toLowerCase();

    return hotels.filter((h) => {
      const statusKey = (h.status_label || "").toLowerCase();

      const matchesQuery =
        !query ||
        (h?.hotel_name || "").toLowerCase().includes(query) ||
        (h?.location || "").toLowerCase().includes(query);

      const matchesLocation =
        locationFilter === "all" || (h?.location || "") === locationFilter;

      const matchesStatus =
        statusFilter === "all" ||
        (statusFilter === "open" && statusKey === "satışa açık") ||
        (statusFilter === "restricted" && statusKey === "kısıtlı") ||
        (statusFilter === "closed" && statusKey === "satışa kapalı");

      return matchesQuery && matchesLocation && matchesStatus;
    });
  }, [hotels, search, locationFilter, statusFilter]);

  const currentStep = quote ? 3 : searchResults.length > 0 ? 2 : 1;

  // Loading state (legacy hotel list)
  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Hızlı Rezervasyon</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Adım 1/3 — Otel seçin, tarih & kişi bilgisini girerek fiyatları görün.
          </p>
          <div className="mt-4">
            <StepBar current={1} />
          </div>
        </div>

        <div className="rounded-2xl border bg-card shadow-sm p-12 flex flex-col items-center justify-center gap-4">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-sm text-muted-foreground">Oteller yükleniyor...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Hızlı Rezervasyon</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Adım 1/3 — Otel seçin, tarih & kişi bilgisini girerek fiyatları görün.
          </p>
        </div>

        <div className="rounded-2xl border border-destructive/50 bg-destructive/5 p-8 flex flex-col items-center justify-center gap-4">
          <AlertCircle className="h-10 w-10 text-destructive" />
          <div className="text-center">
            <p className="font-semibold text-foreground">Otel listesi yüklenemedi</p>
            <p className="text-sm text-muted-foreground mt-1">{error}</p>
          </div>
          <button
            onClick={loadHotels}
            className="mt-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition"
          >
            Tekrar Dene
          </button>
        </div>
      </div>
    );
  }

  // Empty state (hiç hotel yok)
  if (!loading && hotels.length === 0) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Hızlı Rezervasyon</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Adım 1/3 — Anlaşmalı olduğunuz ve satış yapabileceğiniz tesisler
          </p>
        </div>

        <div className="rounded-2xl border bg-card shadow-sm p-12 flex flex-col items-center justify-center gap-4">
      {/* P0.2 Search → Quote → Booking form */}
      <Card className="rounded-2xl border bg-card shadow-sm">
        <CardContent className="p-4 space-y-4">
          <div className="flex items-center justify-between gap-2 flex-wrap">
            <div className="space-y-1">
              <p className="text-xs font-medium text-muted-foreground">P0.2 · Arama & Fiyat</p>
              <StepBar current={currentStep} />
            </div>
            <div className="text-xs text-muted-foreground max-w-xs">
              Bu blok, Agentis seviyesinde tek akışı taşır: katalog → arama → fiyat → misafir.
            </div>
          </div>

          {/* Step 1: Arama formu */}
          <div className="grid grid-cols-1 md:grid-cols-5 gap-3 items-end">
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Şehir</label>
              <Input value={city} onChange={(e) => setCity(e.target.value)} />
              {cityError && (
                <div className="text-xs text-destructive">{cityError}</div>
              )}
            </div>
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Giriş</label>
              <Input type="date" value={checkIn} onChange={(e) => setCheckIn(e.target.value)} />
            </div>
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Çıkış</label>
              <Input type="date" value={checkOut} onChange={(e) => setCheckOut(e.target.value)} />
              {dateError && (
                <div className="text-xs text-destructive">{dateError}</div>
              )}
            </div>
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Yetişkin</label>
              <Input
                type="number"
                min={1}
                max={8}
                value={adults}
                onChange={(e) => setAdults(Number(e.target.value) || 1)}
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Çocuk</label>
              <Input
                type="number"
                min={0}
                max={8}
                value={children}
                onChange={(e) => setChildren(Number(e.target.value) || 0)}
              />
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Button
              size="sm"
              onClick={async () => {
                setSearchError("");
                setCityError("");
                setDateError("");
                setSearchResults([]);
                setSelectedOffer(null);
                setQuote(null);
                setBooking(null);

                const cityTrimmed = city.trim();
                let hasError = false;
                if (!cityTrimmed) {
                  setCityError("Şehir boş bırakılamaz.");
                  hasError = true;
                }
                if (!checkIn || !checkOut) {
                  setDateError("Giriş ve çıkış tarihleri zorunludur.");
                  hasError = true;
                }
                if (hasError) {
                  return;
                }

                setSearchLoading(true);
                try {
                  const params = new URLSearchParams({
                    city: city.trim(),
                    check_in: checkIn,
                    check_out: checkOut,
                    adults: String(adults || 1),
                    children: String(children || 0),
                  });
                  const res = await api.get(`/b2b/hotels/search?${params.toString()}`);
                  const items = res.data?.items || [];
                  setSearchResults(items);
                  if (items.length) {
                    setStep(2);
                  } else {
                    setStep(1);
                    setSearchError("Bu kriterlerle uygun sonuç bulunamadı.");
                  }
                } catch (err) {
                  const msg = apiErrorMessage(err);
                  if (msg.toLowerCase().includes("invalid_date_range")) {
                    setDateError("Çıkış tarihi, giriş tarihinden sonra olmalı.");
                  } else {
                    setSearchError(msg);
                  }
                  setStep(1);
                } finally {
                  setSearchLoading(false);
                }
              }}
              disabled={searchLoading}
            >
              {searchLoading && <Loader2 className="h-3 w-3 animate-spin" />}
              Fiyatları Gör
            </Button>
            {searchError && (
              <div className="text-xs text-destructive">{searchError}</div>
            )}
          </div>

          {/* Step 2: Sonuç listesi + Quote seçimi */}
          {searchResults.length > 0 && (
            <div className="space-y-3">
              <p className="text-xs font-medium text-muted-foreground">
                Adım 2/3 — Sonuçlar ({searchResults.length})
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
                      onClick={() => {
                        setSelectedOffer({ ...item });
                        setStep(2);
                      }}
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
                              {item.nights} gece · {item.occupancy?.adults || 0} yetişkin
                            </div>
                            <div className="text-[11px] text-muted-foreground">
                              Net: {item.base_net} {item.base_currency}
                            </div>
                          </div>
                        </div>
                        <div className="text-[11px] text-muted-foreground flex items-center justify-between">
                          <span>Plan: {item.board}</span>
                          {isSelected && <span className="text-primary font-medium">Seçili</span>}
                        </div>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>

              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  variant="secondary"
                  disabled={!selectedOffer || quoteLoading}
                  onClick={async () => {
                    if (!selectedOffer) return;
                    setQuoteError("");
                    setQuote(null);
                    setBooking(null);

                    try {
                      setQuoteLoading(true);
                      const payload = {
                        channel_id: "agency_extranet",
                        items: [
                          {
                            product_id: selectedOffer.product_id,
                            room_type_id: "default_room",
                            rate_plan_id: selectedOffer.rate_plan_id,
                            check_in: checkIn,
                            check_out: checkOut,
                            occupancy: selectedOffer.occupancy?.adults || adults || 2,
                          },
                        ],
                        client_context: { source: "p0.2-agency-hotels" },
                      };
                      const res = await api.post("/b2b/quotes", payload);
                      const q = res.data;
                      const offer = (q.offers && q.offers[0]) || null;
                      setQuote({ ...q, offer });
                      setStep(3);
                    } catch (err) {
                      setQuoteError(apiErrorMessage(err));
                      setStep(2);
                    } finally {
                      setQuoteLoading(false);
                    }
                  }}
                >
                  {quoteLoading && <Loader2 className="h-3 w-3 animate-spin" />}
                  Seçili Fiyatla Devam Et
                </Button>
                {quoteError && <div className="text-xs text-destructive">{quoteError}</div>}
              </div>
            </div>
          )}

          {/* Step 3: Misafir bilgisi ve rezervasyon */}
          {quote && (
            <div className="space-y-3 border-t pt-4 mt-2">
              <p className="text-xs font-medium text-muted-foreground">Adım 3/3 — Misafir bilgisi</p>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
                <div className="space-y-1">
                  <div className="font-semibold text-foreground">Otel</div>
                  <div className="text-sm">{selectedOffer?.hotel_name}</div>
                  <div className="text-[11px] text-muted-foreground">
                    {city}, {selectedOffer?.country}
                  </div>
                </div>
                <div className="space-y-1">
                  <div className="font-semibold text-foreground">Konaklama</div>
                  <div className="text-sm">
                    {checkIn} → {checkOut}
                  </div>
                  <div className="text-[11px] text-muted-foreground">
                    {quote.offer?.currency} {quote.offer?.sell} · {adults} yetişkin
                  </div>
                </div>
                <div className="space-y-1 text-right">
                  <div className="font-semibold text-foreground">Toplam</div>
                  <div className="text-lg font-semibold">
                    {quote.offer?.sell} {quote.offer?.currency}
                  </div>
                  <div className="text-[11px] text-muted-foreground">Quote ID: {quote.quote_id}</div>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
                <div className="space-y-1">
                  <label className="text-xs text-muted-foreground">Müşteri Adı</label>
                  <Input
                    value={customerName}
                    onChange={(e) => setCustomerName(e.target.value)}
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-xs text-muted-foreground">Müşteri Email</label>
                  <Input
                    type="email"
                    value={customerEmail}
                    onChange={(e) => setCustomerEmail(e.target.value)}
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-xs text-muted-foreground">Misafir (Ad / Soyad)</label>
                  <div className="grid grid-cols-2 gap-2">
                    <Input
                      placeholder="Ad"
                      value={travellerFirstName}
                      onChange={(e) => setTravellerFirstName(e.target.value)}
                    />
                    <Input
                      placeholder="Soyad"
                      value={travellerLastName}
                      onChange={(e) => setTravellerLastName(e.target.value)}
                    />
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  onClick={async () => {
                    if (!quote?.quote_id) return;
                    setBookingError("");
                    setBooking(null);
                    setBookingLoading(true);
                    try {
                      const payload = {
                        quote_id: quote.quote_id,
                        customer: {
                          name: customerName || "P0.2 Test Misafir",
                          email: customerEmail || "p02-test@example.com",
                        },
                        travellers: [
                          {
                            first_name: travellerFirstName || "P0.2",
                            last_name: travellerLastName || "Guest",
                          },
                        ],
                        notes: "P0.2 agency hotelflow",
                      };
                      const headers = {
                        "Idempotency-Key": `p0.2-${quote.quote_id}`,
                      };
                      const res = await api.post("/b2b/bookings", payload, { headers });
                      setBooking(res.data);
                      setBookingError("");
                    } catch (err) {
                      const resp = err?.response?.data;
                      if (resp?.error?.code === "credit_limit_exceeded") {
                        const d = resp.error.details || {};
                        const exposure = d.exposure;
                        const limit = d.limit;
                        const projected = d.projected;
                        let msg = "Kredi limiti aşıldı.";
                        if (
                          typeof exposure === "number" &&
                          typeof limit === "number" &&
                          typeof projected === "number"
                        ) {
                          msg = `Kredi limiti aşıldı: Mevcut exposure ${exposure.toFixed(
                            2,
                          )}, bu rezervasyon ile ${projected.toFixed(2)} olacak (limit ${limit.toFixed(2)}).`;
                        }
                        setBookingError(msg);
                      } else {
                        setBookingError(apiErrorMessage(err));
                      }
                    } finally {
                      setBookingLoading(false);
                    }
                  }}
                  disabled={bookingLoading}
                >
                  {bookingLoading && <Loader2 className="h-3 w-3 animate-spin" />}
                  Rezervasyonu Oluştur
                </Button>
                {bookingError && <div className="text-xs text-destructive">{bookingError}</div>}
              </div>

              {booking && (
                <div className="mt-2 space-y-2">
                  <div className="rounded-xl border bg-muted/20 px-3 py-2 text-xs flex items-center justify-between">
                    <div className="space-y-1">
                      <div className="font-semibold text-foreground">
                        Rezervasyon Oluşturuldu
                      </div>
                      <div className="text-[11px] text-muted-foreground">
                        Booking ID: <span className="font-mono">{booking.booking_id}</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => navigate(`/app/agency/bookings?new=${booking.booking_id}`)}
                      >
                        Rezervasyonlarım
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={async () => {
                          if (!booking?.booking_id) return;
                          const pdfUrl = `/b2b/bookings/${booking.booking_id}/voucher.pdf`;
                          const htmlUrl = `/b2b/bookings/${booking.booking_id}/voucher`;
                          try {
                            const res = await api.get(pdfUrl, { responseType: "blob" });
                            const blob = new Blob([res.data], { type: "application/pdf" });
                            const url = window.URL.createObjectURL(blob);
                            window.open(url, "_blank");
                          } catch (err) {
                            const msg = apiErrorMessage(err) || "";
                            if (
                              msg.toLowerCase().includes("pdf_not_configured") ||
                              msg.toLowerCase().includes("pdf_render_failed")
                            ) {
                              toast({
                                title: "Voucher PDF kullanılamıyor",
                                description: "PDF şimdilik kullanılamıyor, HTML voucher açıldı.",
                              });
                              window.open(htmlUrl, "_blank");
                            } else {
                              toast({
                                title: "Voucher açılamadı",
                                description: msg,
                                variant: "destructive",
                              });
                            }
                          }
                        }}
                      >
                        Voucher
                      </Button>
                    </div>
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
            </div>
          )}
        </CardContent>
      </Card>

          <div className="h-16 w-16 rounded-full bg-muted flex items-center justify-center">
            <Hotel className="h-8 w-8 text-muted-foreground" />
          </div>
          <div className="text-center max-w-md space-y-2">
            <p className="font-semibold text-foreground">
              Henüz size tanımlı bir tesis yok
            </p>
            <p className="text-sm text-muted-foreground">
              Bu ekranda satış yapabileceğiniz oteller listelenir. Merkez ekip otel eklediğinde burada göreceksiniz.
            </p>
          </div>
        </div>
      </div>
    );
  }

  const hasFiltered = filtered.length > 0;

  // Data table (legacy hotel list summary) + P0.2 search/quote/booking flow
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Hızlı Rezervasyon</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Adım 1/3 — Anlaşmalı olduğunuz ve satış yapabileceğiniz {hotels.length} tesis arasından seçim yapın.
          </p>
        </div>
        <div>
          <Button variant="outline" size="sm" onClick={loadHotels} disabled={loading}>
            Yenile
          </Button>
        </div>
      </div>
      {/* P0.2 Search → Quote → Booking form */}
      <Card className="rounded-2xl border bg-card shadow-sm">
        <CardContent className="p-4 space-y-4">
          <div className="flex items-center justify-between gap-2 flex-wrap">
            <div className="space-y-1">
              <p className="text-xs font-medium text-muted-foreground">P0.2 · Arama & Fiyat</p>
              <StepBar current={currentStep} />
            </div>
            <div className="text-xs text-muted-foreground max-w-xs">
              Bu blok, Agentis seviyesinde tek akışı taşır: katalog → arama → fiyat → misafir.
            </div>
          </div>

          {/* Step 1: Arama formu */}
          <div className="grid grid-cols-1 md:grid-cols-5 gap-3 items-end">
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Şehir</label>
              <Input value={city} onChange={(e) => setCity(e.target.value)} />
              {cityError && (
                <div className="text-xs text-destructive">{cityError}</div>
              )}
            </div>
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Giriş</label>
              <Input type="date" value={checkIn} onChange={(e) => setCheckIn(e.target.value)} />
            </div>
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Çıkış</label>
              <Input type="date" value={checkOut} onChange={(e) => setCheckOut(e.target.value)} />
              {dateError && (
                <div className="text-xs text-destructive">{dateError}</div>
              )}
            </div>
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Yetişkin</label>
              <Input
                type="number"
                min={1}
                max={8}
                value={adults}
                onChange={(e) => setAdults(Number(e.target.value) || 1)}
              />
            </div>
            <div className="space-y-1">
              <label className="text-xs text-muted-foreground">Çocuk</label>
              <Input
                type="number"
                min={0}
                max={8}
                value={children}
                onChange={(e) => setChildren(Number(e.target.value) || 0)}
              />
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Button
              size="sm"
              onClick={async () => {
                setSearchError("");
                setCityError("");
                setDateError("");
                setSearchResults([]);
                setSelectedOffer(null);
                setQuote(null);
                setBooking(null);

                const cityTrimmed = city.trim();
                let hasError = false;
                if (!cityTrimmed) {
                  setCityError("Şehir boş bırakılamaz.");
                  hasError = true;
                }
                if (!checkIn || !checkOut) {
                  setDateError("Giriş ve çıkış tarihleri zorunludur.");
                  hasError = true;
                }
                if (hasError) {
                  return;
                }

                setSearchLoading(true);
                try {
                  const params = new URLSearchParams({
                    city: city.trim(),
                    check_in: checkIn,
                    check_out: checkOut,
                    adults: String(adults || 1),
                    children: String(children || 0),
                  });
                  const res = await api.get(`/b2b/hotels/search?${params.toString()}`);
                  const items = res.data?.items || [];
                  setSearchResults(items);
                  if (items.length) {
                    setStep(2);
                  } else {
                    setStep(1);
                    setSearchError("Bu kriterlerle uygun sonuç bulunamadı.");
                  }
                } catch (err) {
                  const msg = apiErrorMessage(err);
                  if (msg.toLowerCase().includes("invalid_date_range")) {
                    setDateError("Çıkış tarihi, giriş tarihinden sonra olmalı.");
                  } else {
                    setSearchError(msg);
                  }
                  setStep(1);
                } finally {
                  setSearchLoading(false);
                }
              }}
              disabled={searchLoading}
            >
              {searchLoading && <Loader2 className="h-3 w-3 animate-spin" />}
              Fiyatları Gör
            </Button>
            {searchError && (
              <div className="text-xs text-destructive">{searchError}</div>
            )}
          </div>

          {/* Step 2: Sonuç listesi + Quote seçimi */}
          {searchResults.length > 0 && (
            <div className="space-y-3">
              <p className="text-xs font-medium text-muted-foreground">
                Adım 2/3 — Sonuçlar ({searchResults.length})
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
                      onClick={() => {
                        setSelectedOffer({ ...item });
                        setStep(2);
                      }}
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
                              {item.nights} gece · {item.occupancy?.adults || 0} yetişkin
                            </div>
                            <div className="text-[11px] text-muted-foreground">
                              Net: {item.base_net} {item.base_currency}
                            </div>
                          </div>
                        </div>
                        <div className="text-[11px] text-muted-foreground flex items-center justify-between">
                          <span>Plan: {item.board}</span>
                          {isSelected && <span className="text-primary font-medium">Seçili</span>}
                        </div>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>

              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  variant="secondary"
                  disabled={!selectedOffer || quoteLoading}
                  onClick={async () => {
                    if (!selectedOffer) return;
                    setQuoteError("");
                    setQuote(null);
                    setBooking(null);

                    try {
                      setQuoteLoading(true);
                      const payload = {
                        channel_id: "agency_extranet",
                        items: [
                          {
                            product_id: selectedOffer.product_id,
                            room_type_id: "default_room",
                            rate_plan_id: selectedOffer.rate_plan_id,
                            check_in: checkIn,
                            check_out: checkOut,
                            occupancy: selectedOffer.occupancy?.adults || adults || 2,
                          },
                        ],
                        client_context: { source: "p0.2-agency-hotels" },
                      };
                      const res = await api.post("/b2b/quotes", payload);
                      const q = res.data;
                      const offer = (q.offers && q.offers[0]) || null;
                      setQuote({ ...q, offer });
                      setStep(3);
                    } catch (err) {
                      setQuoteError(apiErrorMessage(err));
                      setStep(2);
                    } finally {
                      setQuoteLoading(false);
                    }
                  }}
                >
                  {quoteLoading && <Loader2 className="h-3 w-3 animate-spin" />}
                  Seçili Fiyatla Devam Et
                </Button>
                {quoteError && <div className="text-xs text-destructive">{quoteError}</div>}
              </div>
            </div>
          )}

          {/* Step 3: Misafir bilgisi ve rezervasyon */}
          {quote && (
            <div className="space-y-3 border-t pt-4 mt-2">
              <p className="text-xs font-medium text-muted-foreground">Adım 3/3 — Misafir bilgisi</p>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
                <div className="space-y-1">
                  <div className="font-semibold text-foreground">Otel</div>
                  <div className="text-sm">{selectedOffer?.hotel_name}</div>
                  <div className="text-[11px] text-muted-foreground">
                    {city}, {selectedOffer?.country}
                  </div>
                </div>
                <div className="space-y-1">
                  <div className="font-semibold text-foreground">Konaklama</div>
                  <div className="text-sm">
                    {checkIn} → {checkOut}
                  </div>
                  <div className="text-[11px] text-muted-foreground">
                    {quote.offer?.currency} {quote.offer?.sell} · {adults} yetişkin
                  </div>
                </div>
                <div className="space-y-1 text-right">
                  <div className="font-semibold text-foreground">Toplam</div>
                  <div className="text-lg font-semibold">
                    {quote.offer?.sell} {quote.offer?.currency}
                  </div>
                  <div className="text-[11px] text-muted-foreground">Quote ID: {quote.quote_id}</div>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
                <div className="space-y-1">
                  <label className="text-xs text-muted-foreground">Müşteri Adı</label>
                  <Input
                    value={customerName}
                    onChange={(e) => setCustomerName(e.target.value)}
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-xs text-muted-foreground">Müşteri Email</label>
                  <Input
                    type="email"
                    value={customerEmail}
                    onChange={(e) => setCustomerEmail(e.target.value)}
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-xs text-muted-foreground">Misafir (Ad / Soyad)</label>
                  <div className="grid grid-cols-2 gap-2">
                    <Input
                      placeholder="Ad"
                      value={travellerFirstName}
                      onChange={(e) => setTravellerFirstName(e.target.value)}
                    />
                    <Input
                      placeholder="Soyad"
                      value={travellerLastName}
                      onChange={(e) => setTravellerLastName(e.target.value)}
                    />
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  onClick={async () => {
                    if (!quote?.quote_id) return;
                    setBookingError("");
                    setBooking(null);
                    setBookingLoading(true);
                    try {
                      const payload = {
                        quote_id: quote.quote_id,
                        customer: {
                          name: customerName || "P0.2 Test Misafir",
                          email: customerEmail || "p02-test@example.com",
                        },
                        travellers: [
                          {
                            first_name: travellerFirstName || "P0.2",
                            last_name: travellerLastName || "Guest",
                          },
                        ],
                        notes: "P0.2 agency hotelflow",
                      };
                      const headers = {
                        "Idempotency-Key": `p0.2-${quote.quote_id}`,
                      };
                      const res = await api.post("/b2b/bookings", payload, { headers });
                      setBooking(res.data);
                      setBookingError("");
                    } catch (err) {
                      const resp = err?.response?.data;
                      if (resp?.error?.code === "credit_limit_exceeded") {
                        const d = resp.error.details || {};
                        const exposure = d.exposure;
                        const limit = d.limit;
                        const projected = d.projected;
                        let msg = "Kredi limiti aşıldı.";
                        if (
                          typeof exposure === "number" &&
                          typeof limit === "number" &&
                          typeof projected === "number"
                        ) {
                          msg = `Kredi limiti aşıldı: Mevcut exposure ${exposure.toFixed(
                            2,
                          )}, bu rezervasyon ile ${projected.toFixed(2)} olacak (limit ${limit.toFixed(2)}).`;
                        }
                        setBookingError(msg);
                      } else {
                        setBookingError(apiErrorMessage(err));
                      }
                    } finally {
                      setBookingLoading(false);
                    }
                  }}
                  disabled={bookingLoading}
                >
                  {bookingLoading && <Loader2 className="h-3 w-3 animate-spin" />}
                  Rezervasyonu Oluştur
                </Button>
                {bookingError && <div className="text-xs text-destructive">{bookingError}</div>}
              </div>

              {booking && (
                <div className="mt-2 space-y-2">
                  <div className="rounded-xl border bg-muted/20 px-3 py-2 text-xs flex items-center justify-between">
                    <div className="space-y-1">
                      <div className="font-semibold text-foreground">
                        Rezervasyon Oluşturuldu
                      </div>
                      <div className="text-[11px] text-muted-foreground">
                        Booking ID: <span className="font-mono">{booking.booking_id}</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => navigate(`/app/agency/bookings?new=${booking.booking_id}`)}
                      >
                        Rezervasyonlarım
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={async () => {
                          if (!booking?.booking_id) return;
                          const pdfUrl = `/b2b/bookings/${booking.booking_id}/voucher.pdf`;
                          const htmlUrl = `/b2b/bookings/${booking.booking_id}/voucher`;
                          try {
                            const res = await api.get(pdfUrl, { responseType: "blob" });
                            const blob = new Blob([res.data], { type: "application/pdf" });
                            const url = window.URL.createObjectURL(blob);
                            window.open(url, "_blank");
                          } catch (err) {
                            const msg = apiErrorMessage(err) || "";
                            if (
                              msg.toLowerCase().includes("pdf_not_configured") ||
                              msg.toLowerCase().includes("pdf_render_failed")
                            ) {
                              toast({
                                title: "Voucher PDF kullanılamıyor",
                                description: "PDF şimdilik kullanılamıyor, HTML voucher açıldı.",
                              });
                              window.open(htmlUrl, "_blank");
                            } else {
                              toast({
                                title: "Voucher açılamadı",
                                description: msg,
                                variant: "destructive",
                              });
                            }
                          }
                        }}
                      >
                        Voucher
                      </Button>
                    </div>
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
            </div>
          )}
        </CardContent>
      </Card>


      <Card className="rounded-2xl border bg-card shadow-sm p-4 mb-2">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex-1 min-w-[200px]">
            <Input
              placeholder="🔍 Otel ara... (ad / lokasyon)"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <Select value={locationFilter} onValueChange={setLocationFilter}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Lokasyon" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Tüm Lokasyonlar</SelectItem>
                {(() => {
                  const uniq = new Set();
                  hotels.forEach((h) => {
                    const loc = (h?.location || "").trim();
                    if (loc) uniq.add(loc);
                  });
                  return Array.from(uniq).sort((a, b) => a.localeCompare(b));
                })()
                  .map((loc) => (
                    <SelectItem key={loc} value={loc}>
                      {loc}
                    </SelectItem>
                  ))}
              </SelectContent>
            </Select>

            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Durum" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Tüm Durumlar</SelectItem>
                <SelectItem value="open">Satışa Açık</SelectItem>
                <SelectItem value="restricted">Kısıtlı</SelectItem>
                <SelectItem value="closed">Satışa Kapalı</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        {filtered.map((hotel) => (
          <Card key={hotel.hotel_id} className="rounded-2xl border bg-card shadow-sm">
            <CardContent className="p-5 flex items-start justify-between gap-4">
              <div className="space-y-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <div className="text-lg font-semibold">{hotel.hotel_name || "-"}</div>
                  <Badge
                    className={
                      hotel.status_label === "Satışa Açık"
                        ? "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/20"
                        : hotel.status_label === "Kısıtlı"
                        ? "bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-500/20"
                        : "bg-red-500/10 text-red-700 dark:text-red-400 border-red-500/20"
                    }
                  >
                    {hotel.status_label || "-"}
                  </Badge>
                </div>
                <div className="text-sm text-muted-foreground">
                  {hotel.location || "-"}
                </div>
              </div>

              <div className="flex flex-col gap-2 shrink-0">
                <Button
                  className="px-3 py-1.5 text-xs font-medium"
                  onClick={() => navigate(`/app/agency/hotels/${hotel.hotel_id}/search`)}
                  disabled={!isLinkActive(hotel) || hotel.status_label === "Satışa Kapalı"}
                >
                  Rezervasyon Oluştur
                </Button>
                <Button
                  variant="outline"
                  className="px-3 py-1.5 text-xs font-medium"
                  type="button"
                  onClick={() => goHotelBookings(hotel.hotel_id)}
                >
                  Rezervasyonlar
                </Button>
                <Button
                  variant="ghost"
                  className="px-3 py-1.5 text-xs font-medium"
                  type="button"
                  onClick={() => goHotelDetail(hotel.hotel_id)}
                >
                  Detay
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
