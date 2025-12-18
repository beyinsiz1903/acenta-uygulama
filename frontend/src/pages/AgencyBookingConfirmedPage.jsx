import React, { useEffect, useState } from "react";
import { useParams, useNavigate, useLocation } from "react-router-dom";
import { CheckCircle2, Hotel, Calendar, Users, User, Loader2, AlertCircle, Search } from "lucide-react";
import { api, apiErrorMessage } from "../lib/api";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { formatMoney } from "../lib/format";

export default function AgencyBookingConfirmedPage() {
  const { bookingId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();

  const [booking, setBooking] = useState(location.state?.booking || null);
  const [loading, setLoading] = useState(!booking);
  const [error, setError] = useState("");

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
            Otellerime Dön
          </Button>
        </div>
      </div>
    );
  }

  const { hotel_name, guest, rate_snapshot, status, stay, occupancy, confirmed_at } = booking;

  return (
    <div className="space-y-6">
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
                <Badge className="bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/20">
                  Onaylandı
                </Badge>
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

            <div className="border-t pt-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-semibold">Toplam Ücret</p>
                  <p className="text-xs text-muted-foreground mt-1">
                    {rate_snapshot.board} • {rate_snapshot.cancellation === "NON_REFUNDABLE" ? "İade edilemez" : "Ücretsiz iptal"}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-3xl font-bold text-emerald-600">
                    {formatMoney(rate_snapshot.price.total, rate_snapshot.price.currency)}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {stay.nights} gece × {formatMoney(rate_snapshot.price.per_night, rate_snapshot.price.currency)}
                  </p>
                </div>
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
              <Button onClick={() => navigate("/app/agency/hotels")} className="gap-2">
                <Search className="h-4 w-4" />
                Yeni Arama Yap
              </Button>
              <Button variant="outline" disabled>
                Voucher İndir (FAZ-3.2)
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
