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
              Otellerime Dön
            </Button>
          </div>
        </div>
      </div>
    );
  }

  const { hotel, stay, occupancy } = searchData;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <Button
          onClick={() => navigate(-1)}
          variant="outline"
          className="gap-2"
        >
          <ArrowLeft className="h-4 w-4" />
          Geri
        </Button>
      </div>

      {/* Booking Summary */}
      <Card>
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

          <div className="border-t pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">{selectedRatePlan.name}</p>
                <p className="text-xs text-muted-foreground mt-1">
                  {selectedRatePlan.board} • {selectedRatePlan.cancellation === "NON_REFUNDABLE" ? "İade edilemez" : "Ücretsiz iptal"}
                </p>
              </div>
              <div className="text-right">
                <p className="text-2xl font-bold text-primary">
                  {formatMoney(selectedRatePlan.price.total, selectedRatePlan.price.currency)}
                </p>
                <p className="text-xs text-muted-foreground">
                  Gecelik: {formatMoney(selectedRatePlan.price.per_night, selectedRatePlan.price.currency)}
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Guest Form */}
      <Card>
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
                <Label htmlFor="guest-email" className="flex items-center gap-2">
                  <Mail className="h-4 w-4" />
                  Email
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
            </div>

            <div className="space-y-2">
              <Label htmlFor="special-requests" className="flex items-center gap-2">
                <FileText className="h-4 w-4" />
                Özel İstekler
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
              {loading ? "Oluşturuluyor..." : "Rezervasyon Taslağı Oluştur"}
            </Button>

            <p className="text-xs text-muted-foreground text-center">
              FAZ-3.0: Taslak oluşturulacak (henüz ödeme yok)
            </p>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
