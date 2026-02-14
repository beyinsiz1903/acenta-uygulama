import React, { useState } from "react";

// Simple test page without external dependencies
export default function SimpleBookingTest() {
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    full_name: "",
    email: "",
    phone: "",
    special_requests: "",
  });
  const [formError, setFormError] = useState("");

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
        hotel_id: "test-hotel",
        room_type_id: "test-room",
        rate_plan_id: "test-rate",
        check_in: "2025-01-15",
        check_out: "2025-01-17",
        nights: 2,
        adults: 2,
        children: 0,
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

  return (
    <div className="p-5 max-w-[800px] mx-auto font-body">
      <h1 className="text-xl font-bold text-foreground">Booking Wizard Test Page</h1>
      
      <div className="mb-5 p-4 border border-border rounded-lg">
        <h2 className="text-lg font-bold text-foreground">Rezervasyon Özeti</h2>
        <p className="text-sm text-foreground"><strong>Otel:</strong> Test Hotel</p>
        <p className="text-sm text-foreground"><strong>Tarih:</strong> 2025-01-15 - 2025-01-17 (2 gece)</p>
        <p className="text-sm text-foreground"><strong>Misafir:</strong> 2 yetişkin</p>
        <p className="text-sm text-foreground"><strong>Oda Tipi:</strong> Standard Room</p>
        <p className="text-sm text-foreground"><strong>Toplam:</strong> 200 TRY</p>
      </div>

      <div className="p-4 border border-border rounded-lg">
        <h2 className="text-lg font-bold text-foreground">Misafir Bilgileri</h2>
        
        <form
          onSubmit={handleCreateDraft}
          onKeyDown={handleFormKeyDown}
          data-testid="booking-wizard-form"
          className="flex flex-col gap-4"
        >
          <div>
            <label htmlFor="guest-name" className="block mb-1 font-semibold text-sm text-foreground">
              Misafir Adı Soyadı *
            </label>
            <input
              id="guest-name"
              type="text"
              value={formData.full_name}
              onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
              placeholder="Örn: Ahmet Yılmaz"
              disabled={loading}
              className="w-full p-2 border border-border rounded bg-card text-sm text-foreground placeholder:text-muted-foreground"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="guest-phone" className="block mb-1 font-semibold text-sm text-foreground">
                Telefon
              </label>
              <input
                id="guest-phone"
                type="text"
                value={formData.phone}
                onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                placeholder="+90 5XX XXX XX XX"
                disabled={loading}
                className="w-full p-2 border border-border rounded bg-card text-sm text-foreground placeholder:text-muted-foreground"
              />
            </div>

            <div>
              <label htmlFor="guest-email" className="block mb-1 font-semibold text-sm text-foreground">
                Email (opsiyonel)
              </label>
              <input
                id="guest-email"
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                placeholder="ornek@email.com"
                disabled={loading}
                className="w-full p-2 border border-border rounded bg-card text-sm text-foreground placeholder:text-muted-foreground"
              />
            </div>
          </div>

          <div>
            <label htmlFor="special-requests" className="block mb-1 font-semibold text-sm text-foreground">
              Özel İstekler (opsiyonel)
            </label>
            <textarea
              id="special-requests"
              value={formData.special_requests}
              onChange={(e) => setFormData({ ...formData, special_requests: e.target.value })}
              placeholder="Örn: Geç check-in, yüksek kat tercihi..."
              rows={3}
              disabled={loading}
              className="w-full p-2 border border-border rounded bg-card text-sm text-foreground resize-y placeholder:text-muted-foreground"
            />
          </div>

          {formError && (
            <div
              data-testid="booking-wizard-error"
              className="p-2.5 bg-destructive/5 border border-destructive/30 rounded text-destructive text-sm"
            >
              {formError}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            data-testid="booking-wizard-create-send"
            className="py-3 px-6 bg-primary text-primary-foreground border-none rounded text-base font-bold cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed hover:opacity-90 transition-opacity"
          >
            {loading ? "Gönderiliyor..." : "Oluştur & Gönder"}
          </button>

          <p className="text-xs text-muted-foreground text-center my-2.5">
            Rezervasyonu gönderdikten sonra otele iletilir; durumunu Rezervasyonlarım ekranından takip edebilirsiniz.
            <span className="block mt-1" data-testid="booking-wizard-shortcut-hint">
              Kısayol: <span className="font-mono bg-muted px-1 py-0.5 rounded-sm">Ctrl/⌘ + Enter</span>
            </span>
          </p>
        </form>
      </div>
    </div>
  );
}