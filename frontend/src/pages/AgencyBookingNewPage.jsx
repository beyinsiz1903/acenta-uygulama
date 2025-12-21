import React, { useState } from "react";
import { useSearchParams, useNavigate, useLocation } from "react-router-dom";
import { ShoppingCart, ArrowLeft, User, Mail, Phone, FileText, Loader2 } from "lucide-react";
import { api, apiErrorMessage } from "../lib/api";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Textarea } from "../components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { formatMoney } from "../lib/format";
import { toast } from "sonner";

export default function AgencyBookingNewPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const location = useLocation();

  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    full_name: "",
    email: "",
    phone: "",
    special_requests: "",
  });
  const [formError, setFormError] = useState("");

  const context = {
    search_id: searchParams.get("search_id"),
    room_type_id: searchParams.get("room_type_id"),
    rate_plan_id: searchParams.get("rate_plan_id"),
  };

  const searchData = location.state?.searchData;

  // Find selected room and rate plan from searchData
  const selectedRoom = searchData?.rooms?.find((r) => r.room_type_id === context.room_type_id);
  const selectedRatePlan = selectedRoom?.rate_plans?.find((rp) => rp.rate_plan_id === context.rate_plan_id);

  async function handleCreateDraft(e) {
    e.preventDefault();
    setFormError("");

    // Validation
    if (!formData.full_name.trim()) {
      setFormError("Misafir adı gerekli");
      return;
    }

    if (!searchData || !selectedRoom || !selectedRatePlan) {
      setFormError("Oda veya fiyat bilgisi bulunamadı. Lütfen yeni arama yapın.");
      return;
    }

    setLoading(true);
    try {
      const payload = {
        search_id: context.search_id,
        hotel_id: searchData.hotel.id,
        room_type_id: context.room_type_id,
        rate_plan_id: context.rate_plan_id,
        // Stay snapshot
        check_in: searchData.stay.check_in,
        check_out: searchData.stay.check_out,
        nights: searchData.stay.nights,
        // Occupancy snapshot
        adults: searchData.occupancy.adults,
        children: searchData.occupancy.children,
        // Guest info
        guest: {
          full_name: formData.full_name.trim(),
          email: formData.email.trim() || undefined,
          phone: formData.phone.trim() || undefined,
        },
        special_requests: formData.special_requests.trim() || undefined,
      };

      console.log("[BookingDraft] Creating draft:", payload);

      const resp = await api.post("/agency/bookings/draft", payload);
      const draft = resp.data;

      console.log("[BookingDraft] Draft created:", draft.id);
      toast.success("Rezervasyon taslağı oluşturuldu");

      // Navigate to draft confirmation
      navigate(`/app/agency/booking/draft/${draft.id}`, {
        state: { draft },
      });
    } catch (err) {
      console.error("[BookingDraft] Create error:", err);
      setFormError(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  if (!searchData || !selectedRoom || !selectedRatePlan) {
    return (
      <div className="space-y-6">
        <div className="rounded-2xl border bg-card shadow-sm p-12 flex flex-col items-center justify-center gap-4">
          <div className="text-center">
            <p className="font-semibold text-foreground">Seçim bilgisi bulunamadı</p>
            <p className="text-sm text-muted-foreground mt-1">
              Lütfen yeni bir arama yapın.
            </p>
            <Button onClick={() => navigate("/app/agency/hotels")} className="mt-4">
              Sonuçlara Dön
            </Button>
          </div>
        </div>
      </div>
    );
  }

  const { hotel, stay, occupancy } = searchData;

  const total = selectedRatePlan.price.total;
  const currency = selectedRatePlan.price.currency;
  const perNight = selectedRatePlan.price.per_night;
  const commissionAmount = selectedRatePlan.commission_amount ?? selectedRatePlan.commission;
  const commissionRate = selectedRatePlan.commission_rate ?? selectedRatePlan.commission_percent ?? selectedRatePlan.commission_pct; // % olarak (örn: 10)
  const netAmount = selectedRatePlan.net_amount ?? selectedRatePlan.net_total ?? selectedRatePlan.net;

  return (
    <div className="space-y-6">
      {/* Header + Back */}
      <div className="flex items-center justify-between">
        <div className="space-y-1">
          <h1 className="text-2xl font-bold text-foreground">Hızlı Rezervasyon</h1>
          <p className="text-sm text-muted-foreground">
            Adım 3/3 — Misafir bilgilerini girip rezervasyonu gönderin.
          </p>
          <div className="mt-4">
            <StepBar current={3} />
          </div>
        </div>
        <Button
          onClick={() => navigate(-1)}
          variant="outline"
          className="gap-2"
        >
          <ArrowLeft className="h-4 w-4" />
          Sonuçlara Dön
        </Button>
      </div>

      {/* Özet Kart: Oda + Fiyat */}
      <Card className="border rounded-2xl">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ShoppingCart className="h-5 w-5" />
            Rezervasyon Özeti
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
            <div>
              <p className="text-muted-foreground">Otel</p>
              <p className="font-medium">{hotel.name}</p>
            </div>
            <div>
              <p className="text-muted-foreground">Tarih</p>
              <p className="font-medium">
                {stay.check_in} - {stay.check_out} ({stay.nights} gece)
              </p>
            </div>
            <div>
              <p className="text-muted-foreground">Misafir</p>
              <p className="font-medium">
                {occupancy.adults} yetişkin
                {occupancy.children > 0 && `, ${occupancy.children} çocuk`}
              </p>
            </div>
            <div>
              <p className="text-muted-foreground">Oda Tipi</p>
              <p className="font-medium">{selectedRoom.name}</p>
            </div>
          </div>

          <div className="border-t pt-4 grid grid-cols-1 md:grid-cols-3 gap-4 items-center text-sm">
            <div>
              <p className="font-medium">{selectedRatePlan.name}</p>
              <p className="text-xs text-muted-foreground mt-1">
                {selectedRatePlan.board} · {selectedRatePlan.cancellation === "NON_REFUNDABLE" ? "İade edilemez" : "Ücretsiz iptal"}
              </p>
            </div>
            <div className="text-left md:text-center">
              <p className="text-xs text-muted-foreground">Toplam ({stay.nights} gece)</p>
              <p className="text-xl font-bold text-primary">
                {formatMoney(total, currency)}
              </p>
              <p className="text-xs text-muted-foreground">
                Gecelik: {formatMoney(perNight, currency)}
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

      {/* Misafir Formu */}
      <Card className="border rounded-2xl">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <User className="h-5 w-5" />
            Misafir Bilgileri
          </CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleCreateDraft} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="guest-name" className="flex items-center gap-2">
                <User className="h-4 w-4" />
                Misafir Adı Soyadı *
              </Label>
              <Input
                id="guest-name"
                value={formData.full_name}
                onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                placeholder="Örn: Ahmet Yılmaz"
                disabled={loading}
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="guest-phone" className="flex items-center gap-2">
                  <Phone className="h-4 w-4" />
                  Telefon
                </Label>
                <Input
                  id="guest-phone"
                  value={formData.phone}
                  onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                  placeholder="+90 5XX XXX XX XX"
                  disabled={loading}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="guest-email" className="flex items-center gap-2">
                  <Mail className="h-4 w-4" />
                  Email (opsiyonel)
                </Label>
                <Input
                  id="guest-email"
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  placeholder="ornek@email.com"
                  disabled={loading}
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="special-requests" className="flex items-center gap-2">
                <FileText className="h-4 w-4" />
                Özel İstekler (opsiyonel)
              </Label>
              <Textarea
                id="special-requests"
                value={formData.special_requests}
                onChange={(e) => setFormData({ ...formData, special_requests: e.target.value })}
                placeholder="Örn: Geç check-in, yüksek kat tercihi..."
                rows={3}
                disabled={loading}
              />
            </div>

            {formError && (
              <div className="text-sm text-destructive bg-destructive/10 border border-destructive/20 rounded-lg p-3">
                {formError}
              </div>
            )}

            <Button type="submit" disabled={loading} className="w-full gap-2">
              {loading && <Loader2 className="h-4 w-4 animate-spin" />}
              {loading ? "Gönderiliyor..." : "Rezervasyonu Gönder"}
            </Button>

            <p className="text-xs text-muted-foreground text-center mt-1">
              Rezervasyonu gönderdikten sonra otele iletilir; durumunu Rezervasyonlarım ekranından takip edebilirsiniz.
            </p>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
