import React, { useState } from "react";
import { ShoppingCart, ArrowLeft, User, Mail, Phone, FileText, Loader2 } from "lucide-react";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Textarea } from "../components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import StepBar from "../components/StepBar";

// Test version of AgencyBookingNewPage for testing purposes
export default function AgencyBookingTestPage() {
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    full_name: "",
    email: "",
    phone: "",
    special_requests: "",
  });
  const [formError, setFormError] = useState("");

  // Mock search data for testing
  const mockSearchData = {
    hotel: { id: "test-hotel", name: "Test Hotel" },
    stay: { check_in: "2025-01-15", check_out: "2025-01-17", nights: 2 },
    occupancy: { adults: 2, children: 0 },
    rooms: [{
      room_type_id: "test-room",
      name: "Standard Room",
      rate_plans: [{
        rate_plan_id: "test-rate",
        name: "Best Available Rate",
        board: "Room Only",
        cancellation: "FREE_CANCELLATION",
        price: { total: 200, currency: "TRY", per_night: 100 },
        commission_amount: 20,
        commission_rate: 10,
        net_amount: 180
      }]
    }]
  };

  const selectedRoom = mockSearchData.rooms[0];
  const selectedRatePlan = selectedRoom.rate_plans[0];

  function handleFormKeyDown(e) {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      if (!loading) {
        void submitDraft();
      }
    }
  }

  async function handleCreateDraft(e) {
    e.preventDefault();
    await submitDraft();
  }

  async function submitDraft() {
    setFormError("");

    // Validation
    if (!formData.full_name.trim()) {
      setFormError("Misafir adı gerekli");
      return;
    }

    setLoading(true);
    try {
      const payload = {
        search_id: "test-search",
        hotel_id: mockSearchData.hotel.id,
        room_type_id: "test-room",
        rate_plan_id: "test-rate",
        // Stay snapshot
        check_in: mockSearchData.stay.check_in,
        check_out: mockSearchData.stay.check_out,
        nights: mockSearchData.stay.nights,
        // Occupancy snapshot
        adults: mockSearchData.occupancy.adults,
        children: mockSearchData.occupancy.children,
        // Guest info
        guest: {
          full_name: formData.full_name.trim(),
          email: formData.email.trim() || undefined,
          phone: formData.phone.trim() || undefined,
        },
        special_requests: formData.special_requests.trim() || undefined,
      };

      console.log("[BookingDraft] Creating draft:", payload);

      // Mock API call for testing
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      console.log("[BookingDraft] Draft created successfully (mocked)");
      alert("Test: Rezervasyon taslağı oluşturuldu (mocked)");

    } catch (err) {
      console.error("[BookingDraft] Create error:", err);
      setFormError("Test error occurred");
    } finally {
      setLoading(false);
    }
  }

  const { hotel, stay, occupancy } = mockSearchData;
  const total = selectedRatePlan.price.total;
  const currency = selectedRatePlan.price.currency;
  const perNight = selectedRatePlan.price.per_night;
  const commissionAmount = selectedRatePlan.commission_amount;
  const commissionRate = selectedRatePlan.commission_rate;
  const netAmount = selectedRatePlan.net_amount;

  return (
    <div className="min-h-screen bg-gray-50 p-4">
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Header + Back */}
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <h1 className="text-2xl font-bold text-foreground">Hızlı Rezervasyon (Test)</h1>
            <p className="text-sm text-muted-foreground">
              Adım 3/3 — Misafir bilgilerini girip rezervasyonu oluşturun ve gönderin.
            </p>
            <div className="mt-4">
              <StepBar current={3} />
            </div>
          </div>
          <Button
            onClick={() => window.history.back()}
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
                  {total} {currency}
                </p>
                <p className="text-xs text-muted-foreground">
                  Gecelik: {perNight} {currency}
                </p>
              </div>
              <div className="text-left md:text-right">
                <p className="text-sm font-semibold text-foreground">
                  Net: {netAmount} {currency}
                </p>
                <p className="text-xs text-muted-foreground">
                  Komisyon: {commissionAmount} {currency} (%{commissionRate})
                </p>
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
            <form
              onSubmit={handleCreateDraft}
              onKeyDown={handleFormKeyDown}
              className="space-y-4"
              data-testid="booking-wizard-form"
            >
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
                <div
                  className="text-sm text-destructive bg-destructive/10 border border-destructive/20 rounded-lg p-3"
                  data-testid="booking-wizard-error"
                >
                  {formError}
                </div>
              )}

              <Button
                type="submit"
                disabled={loading}
                className="w-full gap-2"
                data-testid="booking-wizard-create-send"
              >
                {loading && <Loader2 className="h-4 w-4 animate-spin" />}
                {loading ? "Gönderiliyor..." : "Oluştur & Gönder"}
              </Button>

              <p className="text-xs text-muted-foreground text-center mt-1">
                Rezervasyonu gönderdikten sonra otele iletilir; durumunu Rezervasyonlarım ekranından takip edebilirsiniz.
                <span className="block mt-1" data-testid="booking-wizard-shortcut-hint">
                  Kısayol: <span className="font-mono">Ctrl/⌘ + Enter</span>
                </span>
              </p>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}