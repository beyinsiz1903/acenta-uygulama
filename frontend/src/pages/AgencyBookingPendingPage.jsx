import React, { useEffect, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { BookingReferenceBanner } from "../components/BookingReferenceBanner";
import { buildBookingShareSummary } from "../utils/bookingShareSummary";
import { api, apiErrorMessage } from "../lib/api";

// --- FAZ-9 helpers: WhatsApp message (best-effort) ---
function buildPendingWhatsAppMessage({ booking, bookingIdFallback, shareSummary }) {
  const referenceId = booking?.id || bookingIdFallback || "";

  // Kısa, operasyonel: özet + referans
  // shareSummary zaten "✅ Rezervasyon Özeti" ile başlıyor; onu kullanıyoruz.
  const lines = [];

  lines.push("✅ Rezervasyon Talebi (Beklemede)");
  if (referenceId) lines.push(`Referans: ${referenceId}`);
  lines.push("");

  if (shareSummary) {
    // shareSummary içinde "✅ Rezervasyon Özeti" var; aynen ekleyelim
    lines.push(shareSummary);
  }

  return lines.filter(Boolean).join("\n");
}

function openWhatsAppWithText(text) {
  const msg = String(text || "").trim();
  if (!msg) return;

  // wa.me universal
  const url = `https://wa.me/?text=${encodeURIComponent(msg)}`;
  window.open(url, "_blank", "noopener,noreferrer");
}

export default function AgencyBookingPendingPage() {
  const { bookingId } = useParams();
  const location = useLocation();
  const navigate = useNavigate();

  const [booking, setBooking] = useState(location.state?.booking || null);
  const [loading, setLoading] = useState(!booking);
  const [error, setError] = useState("");
  
  // FAZ-9: pending note (localStorage)
  const [pendingNote, setPendingNote] = useState("");

  useEffect(() => {
    if (booking) return;
    if (!bookingId) {
      setError("Rezervasyon bulunamadı");
      return;
    }

    async function load() {
      try {
        setLoading(true);
        // Şimdilik sadece state ile çalışıyoruz; backend GET henüz yok.
        // İleride /agency/bookings/{id} eklendiğinde buraya GET çağrısı eklenebilir.
        setError("Rezervasyon bilgisi bulunamadı. Lütfen Rezervasyonlarım sayfasından kontrol edin.");
      } catch (err) {
        setError(apiErrorMessage(err));
      } finally {
        setLoading(false);
      }
    }

    void load();
  }, [booking, bookingId]);

  if (loading) {
    return (
      <div className="p-6 text-sm text-muted-foreground">
        Rezervasyon yükleniyor...
      </div>
    );
  }

  if (error || !booking) {
    return (
      <div className="p-6 space-y-3">
        <p className="font-semibold text-foreground">Rezervasyon bulunamadı</p>
        <p className="text-sm text-muted-foreground">{error}</p>
        <button
          type="button"
          className="text-xs underline text-muted-foreground hover:text-foreground"
          onClick={() => navigate("/app/agency/bookings")}
        >
          Rezervasyonlarım sayfasına dön
        </button>
      </div>
    );
  }

  const shareSummary = buildBookingShareSummary({
    booking,
    bookingIdFallback: bookingId,
    hotelNote: "",
  });

  return (
    <div className="space-y-6">
      <BookingReferenceBanner
        bookingId={booking.id || bookingId}
        extranetUrl={booking.hotel_extranet_url}
        shareSummary={shareSummary}
      />

      <div className="rounded-2xl border-2 border-amber-500/40 bg-gradient-to-br from-amber-500/10 to-amber-500/5 p-8">
        <div className="flex flex-col items-center text-center gap-4">
          <div className="h-16 w-16 rounded-full bg-amber-500 flex items-center justify-center text-white text-2xl">
            !
          </div>
          <div>
            <h1 className="text-2xl font-bold text-foreground">
              Rezervasyon Talebi Otel Onayını Bekliyor
            </h1>
            <p className="text-sm text-muted-foreground mt-2">
              Rezervasyon talebiniz otele iletildi. Otel onay verdiğinde size bilgi verilecektir.
            </p>
          </div>
        </div>
      </div>

      <div className="flex justify-center">
        <button
          type="button"
          className="text-xs underline text-muted-foreground hover:text-foreground"
          onClick={() => navigate("/app/agency/bookings")}
        >
          Rezervasyonlarım sayfasına git
        </button>
      </div>
    </div>
  );
}
