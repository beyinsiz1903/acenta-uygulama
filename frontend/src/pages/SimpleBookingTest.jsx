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
    <div style={{ padding: "20px", maxWidth: "800px", margin: "0 auto", fontFamily: "Inter, system-ui, sans-serif" }}>
      <h1>Booking Wizard Test Page</h1>
      
      <div style={{ marginBottom: "20px", padding: "15px", border: "1px solid #ddd", borderRadius: "8px" }}>
        <h2>Rezervasyon Özeti</h2>
        <p><strong>Otel:</strong> Test Hotel</p>
        <p><strong>Tarih:</strong> 2025-01-15 - 2025-01-17 (2 gece)</p>
        <p><strong>Misafir:</strong> 2 yetişkin</p>
        <p><strong>Oda Tipi:</strong> Standard Room</p>
        <p><strong>Toplam:</strong> 200 TRY</p>
      </div>

      <div style={{ padding: "15px", border: "1px solid #ddd", borderRadius: "8px" }}>
        <h2>Misafir Bilgileri</h2>
        
        <form
          onSubmit={handleCreateDraft}
          onKeyDown={handleFormKeyDown}
          data-testid="booking-wizard-form"
          style={{ display: "flex", flexDirection: "column", gap: "15px" }}
        >
          <div>
            <label htmlFor="guest-name" style={{ display: "block", marginBottom: "5px", fontWeight: "bold" }}>
              Misafir Adı Soyadı *
            </label>
            <input
              id="guest-name"
              type="text"
              value={formData.full_name}
              onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
              placeholder="Örn: Ahmet Yılmaz"
              disabled={loading}
              style={{ 
                width: "100%", 
                padding: "8px", 
                border: "1px solid #ccc", 
                borderRadius: "4px",
                fontSize: "14px"
              }}
            />
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "15px" }}>
            <div>
              <label htmlFor="guest-phone" style={{ display: "block", marginBottom: "5px", fontWeight: "bold" }}>
                Telefon
              </label>
              <input
                id="guest-phone"
                type="text"
                value={formData.phone}
                onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                placeholder="+90 5XX XXX XX XX"
                disabled={loading}
                style={{ 
                  width: "100%", 
                  padding: "8px", 
                  border: "1px solid #ccc", 
                  borderRadius: "4px",
                  fontSize: "14px"
                }}
              />
            </div>

            <div>
              <label htmlFor="guest-email" style={{ display: "block", marginBottom: "5px", fontWeight: "bold" }}>
                Email (opsiyonel)
              </label>
              <input
                id="guest-email"
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                placeholder="ornek@email.com"
                disabled={loading}
                style={{ 
                  width: "100%", 
                  padding: "8px", 
                  border: "1px solid #ccc", 
                  borderRadius: "4px",
                  fontSize: "14px"
                }}
              />
            </div>
          </div>

          <div>
            <label htmlFor="special-requests" style={{ display: "block", marginBottom: "5px", fontWeight: "bold" }}>
              Özel İstekler (opsiyonel)
            </label>
            <textarea
              id="special-requests"
              value={formData.special_requests}
              onChange={(e) => setFormData({ ...formData, special_requests: e.target.value })}
              placeholder="Örn: Geç check-in, yüksek kat tercihi..."
              rows={3}
              disabled={loading}
              style={{ 
                width: "100%", 
                padding: "8px", 
                border: "1px solid #ccc", 
                borderRadius: "4px",
                fontSize: "14px",
                resize: "vertical"
              }}
            />
          </div>

          {formError && (
            <div
              data-testid="booking-wizard-error"
              style={{ 
                padding: "10px", 
                backgroundColor: "#fee", 
                border: "1px solid #fcc", 
                borderRadius: "4px",
                color: "#c00",
                fontSize: "14px"
              }}
            >
              {formError}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            data-testid="booking-wizard-create-send"
            style={{ 
              padding: "12px 24px", 
              backgroundColor: loading ? "#ccc" : "#007bff", 
              color: "white", 
              border: "none", 
              borderRadius: "4px",
              fontSize: "16px",
              fontWeight: "bold",
              cursor: loading ? "not-allowed" : "pointer"
            }}
          >
            {loading ? "Gönderiliyor..." : "Oluştur & Gönder"}
          </button>

          <p style={{ fontSize: "12px", color: "hsl(220, 10%, 45%)", textAlign: "center", margin: "10px 0" }}>
            Rezervasyonu gönderdikten sonra otele iletilir; durumunu Rezervasyonlarım ekranından takip edebilirsiniz.
            <span style={{ display: "block", marginTop: "5px" }} data-testid="booking-wizard-shortcut-hint">
              Kısayol: <span style={{ fontFamily: "Roboto Mono, ui-monospace, monospace", backgroundColor: "#f5f5f5", padding: "2px 4px", borderRadius: "2px" }}>Ctrl/⌘ + Enter</span>
            </span>
          </p>
        </form>
      </div>
    </div>
  );
}