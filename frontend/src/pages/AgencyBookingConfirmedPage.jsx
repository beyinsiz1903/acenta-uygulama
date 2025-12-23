import React, { useEffect, useState } from "react";
import { useParams, useNavigate, useLocation } from "react-router-dom";
import { CheckCircle2, Hotel, Calendar, Users, User, Loader2, AlertCircle, Search } from "lucide-react";
import { api, apiErrorMessage } from "../lib/api";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { formatMoney } from "../lib/format";
import { statusInfo, badgeToneClass } from "../utils/bookingStatus";


// Safe clipboard helper (modern API + fallback)
async function copyText(text) {
  try {
    if (!text) return false;
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(String(text));
      return true;
    }
  } catch {
    // ignore and try fallback
  }

  try {
    const ta = document.createElement("textarea");
    ta.value = String(text ?? "");
    ta.setAttribute("readonly", "");
    ta.style.position = "absolute";
    ta.style.left = "-9999px";
    document.body.appendChild(ta);
    ta.select();
    const ok = document.execCommand("copy");
    document.body.removeChild(ta);
    return ok;
  } catch {
    return false;
  }
}

export default function AgencyBookingConfirmedPage() {
  const { bookingId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();

  const [booking, setBooking] = useState(location.state?.booking || null);
  const [loading, setLoading] = useState(!booking);
  const [error, setError] = useState("");
  const [copiedId, setCopiedId] = useState(false);
  const [copiedSummary, setCopiedSummary] = useState(false);
  const [hotelNote, setHotelNote] = useState("");

  useEffect(() => {
    console.log("[BookingConfirmed] booking_id:", bookingId);
    if (!booking) {
      loadBooking();
    }
  }, [bookingId]);

  async function loadBooking() {
    setLoading(true);
    setError("");
    try {
      const resp = await api.get(`/agency/bookings/${bookingId}`);
      console.log("[BookingConfirmed] Loaded:", resp.data);
      setBooking(resp.data);
    } catch (err) {
      console.error("[BookingConfirmed] Load error:", err);
      setError(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="rounded-2xl border bg-card shadow-sm p-12 flex flex-col items-center justify-center gap-4">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-sm text-muted-foreground">Rezervasyon yükleniyor...</p>
        </div>
      </div>
    );
  }

  if (error || !booking) {
    return (
      <div className="space-y-6">
        <div className="rounded-2xl border border-destructive/50 bg-destructive/5 p-8 flex flex-col items-center justify-center gap-4">
          <AlertCircle className="h-10 w-10 text-destructive" />
          <div className="text-center">
            <p className="font-semibold text-foreground">Rezervasyon bulunamadı</p>
            <p className="text-sm text-muted-foreground mt-1">{error || "Rezervasyon bilgisi bulunamadı"}</p>
          </div>
          <Button onClick={() => navigate("/app/agency/hotels")}>
            Yeni Rezervasyon
          </Button>
        </div>
      </div>
    );
  }

  const { hotel_name, guest, rate_snapshot, status, stay, occupancy, confirmed_at } = booking;

  const referenceId = booking?.id || bookingId || "";

  const paxTotal = (occupancy?.adults || 0) + (occupancy?.children || 0);

  const dateRangeText =
    stay?.check_in && stay?.check_out
      ? `${stay.check_in} → ${stay.check_out}`
      : "";

  const hotelNoteClean = (hotelNote || "").trim();
  const hotelNoteLine = hotelNoteClean ? `Not: ${hotelNoteClean}` : null;

  const roomLine =
    booking?.rate_snapshot?.room_type_name
      ? `Oda: ${booking.rate_snapshot.room_type_name}`
      : null;

  const planLine =
    booking?.rate_snapshot?.rate_plan_name
      ? `Plan: ${booking.rate_snapshot.rate_plan_name}`
      : null;

  const shareSummary = [
    "✅ Rezervasyon Özeti",
    referenceId ? `Referans: ${referenceId}` : null,
    hotel_name ? `Otel: ${hotel_name}` : null,
    dateRangeText ? `Tarih: ${dateRangeText}` : null,
    paxTotal ? `Kişi: ${paxTotal}` : null,
    roomLine,
    planLine,
    typeof rate_snapshot?.price?.total === "number"
      ? `Tutar: ${formatMoney(rate_snapshot.price.total, rate_snapshot.price.currency || "TRY")}`
      : null,
    hotelNoteLine,
  ]
    .filter(Boolean)
    .join("\n");

  const total = rate_snapshot?.price?.total;
  const currency = rate_snapshot?.price?.currency;
  const perNight = rate_snapshot?.price?.per_night;
  const commissionAmount = rate_snapshot?.commission_amount ?? rate_snapshot?.commission;
  const commissionRate =
    rate_snapshot?.commission_rate ??
    rate_snapshot?.commission_percent ??
    rate_snapshot?.commission_pct;
  const netAmount = rate_snapshot?.net_amount ?? rate_snapshot?.net_total ?? rate_snapshot?.net;

  function buildWhatsAppMessage() {
    const lines = [];

    lines.push("✅ Rezervasyon Talebi");
    if (referenceId) {
      lines.push(`Referans: ${referenceId}`);
    }
    if (hotelNoteClean) {
      lines.push(`Not: ${hotelNoteClean}`);
    }
    lines.push("");

    if (hotel_name) lines.push(`🏨 ${hotel_name}`);
    if (stay?.check_in && stay?.check_out) {
      const nightsText = stay.nights ? ` (${stay.nights} gece)` : "";
      lines.push(`📅 ${stay.check_in} – ${stay.check_out}${nightsText}`);
    }

    const occupancyLine = occupancy
      ? `${occupancy.adults || 0}Y${occupancy.children ? ` ${occupancy.children}Ç` : ""}`
      : "";
    if (guest?.full_name) {
      lines.push(`👤 ${guest.full_name}${occupancyLine ? ` • ${occupancyLine}` : ""}`);
    }

    const roomBoard = [rate_snapshot?.room_type_name, rate_snapshot?.rate_plan_name]
      .filter(Boolean)
      .join(" / ");
    if (roomBoard) {
      lines.push(`🛏️ ${roomBoard}`);
    }

    lines.push("");

    if (typeof total === "number" && currency) {
      lines.push(`💰 Toplam: ${formatMoney(total, currency)}`);
    }
    if (typeof netAmount === "number" && currency) {
      lines.push(`💵 Net: ${formatMoney(netAmount, currency)}`);
    }
    if (typeof commissionAmount === "number" && currency) {
      const pctPart = typeof commissionRate === "number" ? ` (%${commissionRate})` : "";
      lines.push(`🤝 Komisyon: ${formatMoney(commissionAmount, currency)}${pctPart}`);
    }

    if (status) {
      const info = statusInfo(status);
      lines.push("");
      if (info.canonical === "confirmed") {
        lines.push(`🟢 Durum: ${info.text}`);
      } else if (info.canonical === "cancelled" || info.canonical === "rejected") {
        lines.push(`🔴 Durum: ${info.text}`);
      } else {
        lines.push(`🟡 Durum: ${info.text}`);
      }
    }

    return lines.join("\n");
  }

  async function openWhatsApp() {
    const text = buildWhatsAppMessage();
    const url = "https://wa.me/?text=" + encodeURIComponent(text);
    
    // Track WhatsApp click BEFORE opening window (prevents request drop)
    // Use sendBeacon for reliability (or keepalive fetch as fallback)
    try {
      const token = localStorage.getItem("token");
      const trackingUrl = `${import.meta.env.REACT_APP_BACKEND_URL || process.env.REACT_APP_BACKEND_URL}/api/bookings/${bookingId}/track/whatsapp-click`;
      
      // Try sendBeacon first (most reliable for navigation scenarios)
      if (navigator.sendBeacon) {
        const blob = new Blob([JSON.stringify({})], { type: "application/json" });
        const headers = new Headers();
        headers.append("Authorization", `Bearer ${token}`);
        
        // sendBeacon doesn't support custom headers directly, fallback to fetch with keepalive
        await fetch(trackingUrl, {
          method: "POST",
          headers: {
            "Authorization": `Bearer ${token}`,
            "Content-Type": "application/json"
          },
          body: JSON.stringify({}),
          keepalive: true  // Critical: ensures request completes even if page navigates
        });
      } else {
        // Fallback for older browsers
        await api.post(`/bookings/${bookingId}/track/whatsapp-click`);
      }
      console.log("[BookingConfirmed] WhatsApp click tracked");
    } catch (err) {
      console.error("[BookingConfirmed] WhatsApp tracking failed:", err);
      // Don't block user experience if tracking fails
    }
    
    // Open WhatsApp AFTER tracking to avoid race condition
    window.open(url, "_blank", "noopener,noreferrer");
  }

  return (
    <div className="space-y-6">
      {/* Booking ID Banner */}
      <div
        className="rounded-xl border bg-muted/40 px-4 py-3 flex items-center justify-between gap-3"
        data-testid="booking-id-banner"
      >
        <div className="min-w-0">
          <div className="text-xs text-muted-foreground">Rezervasyon ID</div>
          <div className="truncate font-mono text-sm">
            {booking?.id || bookingId || "-"}
          </div>
          {booking?.hotel_extranet_url && (
            <div className="mt-1">
              <a
                href={booking.hotel_extranet_url}
                target="_blank"
                rel="noreferrer"
                className="text-[11px] underline text-muted-foreground"
                data-testid="open-hotel-extranet"
              >
                Otel panelinde aç
              </a>
            </div>
          )}
        </div>
        <div className="shrink-0 flex items-center gap-2">
          <button
            type="button"
            className="inline-flex items-center justify-center rounded-md border bg-background px-3 py-2 text-xs font-medium"
            data-testid="booking-id-copy"
            onClick={async () => {
              const id = booking?.id || bookingId;
              const ok = await copyText(id);
              setCopiedId(ok);
              if (ok) {
                window.setTimeout(() => setCopiedId(false), 1200);
              }
            }}
            disabled={!(booking?.id || bookingId)}
          >
            {copiedId ? "Kopyalandı" : "Kopyala"}
          </button>

          <button
            type="button"
            className="inline-flex items-center justify-center rounded-md border bg-background px-3 py-2 text-xs font-medium"
            data-testid="booking-summary-copy"
            onClick={async () => {
              const ok = await copyText(shareSummary);
              setCopiedSummary(ok);
              if (ok) {
                window.setTimeout(() => setCopiedSummary(false), 1200);
              }
      {/* Hotel Note */}
      <div className="rounded-xl border bg-background p-4">
        <div className="text-sm font-medium">Otele Not (opsiyonel)</div>
        <div className="mt-1 text-xs text-muted-foreground">
          Otel ekibinin görmesi için kısa bir not ekleyebilirsiniz (örn: kapasite aşıyor, bebek var, geç giriş).
        </div>

        <textarea
          className="mt-3 w-full min-h-[90px] rounded-md border bg-background p-3 text-sm"
          placeholder="Notunuz…"
          value={hotelNote}
          onChange={(e) => setHotelNote(e.target.value)}
          data-testid="hotel-note-input"
        />
      </div>


            }}
            disabled={!shareSummary}
            title="Paylaşılabilir özeti kopyala"
          >
            {copiedSummary ? "Kopyalandı" : "Özeti Kopyala"}
          </button>
        </div>
      </div>

      {/* Success Banner */}
      <div className="rounded-2xl border-2 border-emerald-500/30 bg-gradient-to-br from-emerald-500/10 to-emerald-500/5 p-8">
        <div className="flex flex-col items-center text-center gap-4">
          <div className="h-16 w-16 rounded-full bg-emerald-500 flex items-center justify-center">
            <CheckCircle2 className="h-10 w-10 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-foreground">Rezervasyon Onaylandı!</h1>
            <p className="text-sm text-muted-foreground mt-2">
              Rezervasyon No: <span className="font-mono font-semibold">{booking.id}</span>
            </p>
            {confirmed_at && (
              <p className="text-xs text-muted-foreground mt-1">
                Onay Zamanı: {new Date(confirmed_at).toLocaleString("tr-TR")}
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Stay Summary */}
      {stay && occupancy && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Calendar className="h-5 w-5" />
              Konaklama Özeti
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
              <div>
                <p className="text-muted-foreground">Otel</p>
                <p className="font-medium">{hotel_name}</p>
              </div>
              <div>
                <p className="text-muted-foreground">Durum</p>
                {(() => {
                  const info = statusInfo(status);
                  return <Badge className={badgeToneClass(info.tone)}>{info.text}</Badge>;
                })()}
              </div>
              <div>
                <p className="text-muted-foreground">Giriş - Çıkış</p>
                <p className="font-medium">
                  {stay.check_in} - {stay.check_out}
                </p>
                <p className="text-xs text-muted-foreground">{stay.nights} gece</p>
              </div>
              <div>
                <p className="text-muted-foreground">Misafir Sayısı</p>
                <p className="font-medium">
                  {occupancy.adults} yetişkin
                  {occupancy.children > 0 && `, ${occupancy.children} çocuk`}
                </p>
              </div>
              <div>
                <p className="text-muted-foreground">Oda</p>
                <p className="font-medium">{rate_snapshot.room_type_name}</p>
              </div>
              <div>
                <p className="text-muted-foreground">Plan</p>
                <p className="font-medium">{rate_snapshot.rate_plan_name}</p>
              </div>
            </div>

            <div className="border-t pt-4 grid grid-cols-1 md:grid-cols-3 gap-4 items-center text-sm">
              <div>
                <p className="text-sm font-semibold">Toplam Ücret</p>
                <p className="text-xs text-muted-foreground mt-1">
                  {rate_snapshot.board} • {rate_snapshot.cancellation === "NON_REFUNDABLE" ? "İade edilemez" : "Ücretsiz iptal"}
                </p>
              </div>
              <div className="text-left md:text-center">
                <p className="text-xs text-muted-foreground">Toplam ({stay.nights} gece)</p>
                <p className="text-3xl font-bold text-emerald-600">
                  {formatMoney(total, currency)}
                </p>
                <p className="text-xs text-muted-foreground">
                  {stay.nights} gece × {formatMoney(perNight, currency)}
                </p>
              </div>
              <div className="text-left md:text-right">
                {typeof netAmount === "number" && (
                  <p className="text-sm font-semibold text-foreground">
                    Net: {formatMoney(netAmount, currency)}
                  </p>
                )}
                {typeof commissionAmount === "number" && (
                  <p className="text-xs text-muted-foreground">
                    Komisyon: {formatMoney(commissionAmount, currency)}
                    {typeof commissionRate === "number" && ` (%${commissionRate})`}
                  </p>
                )}
                {!netAmount && !commissionAmount && (
                  <p className="text-xs text-muted-foreground">Net/komisyon detayı mutabakat ekranında netleşir.</p>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Guest Info */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <User className="h-5 w-5" />
            Misafir Bilgileri
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3 text-sm">
            <div>
              <p className="text-muted-foreground">Ad Soyad</p>
              <p className="font-medium">{guest.full_name}</p>
            </div>
            {guest.email && (
              <div>
                <p className="text-muted-foreground">Email</p>
                <p className="font-medium">{guest.email}</p>
              </div>
            )}
            {guest.phone && (
              <div>
                <p className="text-muted-foreground">Telefon</p>
                <p className="font-medium">{guest.phone}</p>
              </div>
            )}
            {booking.special_requests && (
              <div>
                <p className="text-muted-foreground">Özel İstekler</p>
                <p className="font-medium">{booking.special_requests}</p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Actions */}
      <Card className="border-dashed">
        <CardContent className="pt-6">
          <div className="text-center space-y-4">
            <p className="text-sm text-muted-foreground">
              Rezervasyonunuz başarıyla oluşturuldu.
            </p>

            <div className="flex flex-col sm:flex-row gap-3 justify-center">
              <Button onClick={openWhatsApp} className="gap-2" data-testid="whatsapp-send">
                WhatsApp&apos;a Gönder
              </Button>
              <Button onClick={() => navigate("/app/agency/hotels")} variant="outline" className="gap-2">
                <Search className="h-4 w-4" />
                Yeni Rezervasyon
              </Button>
              <Button variant="ghost" onClick={() => navigate("/app/agency/bookings")}>
                Rezervasyonlarım
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
