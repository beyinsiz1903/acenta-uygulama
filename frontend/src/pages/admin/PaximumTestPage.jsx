import React, { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api, apiErrorMessage } from "../../lib/api";

const todayPlus = (days) => {
  const d = new Date();
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10);
};

const Section = ({ title, children, right = null }) => (
  <div style={{ background: "#fff", border: "1px solid #e5e7eb", borderRadius: 12, padding: 16, marginBottom: 16 }}>
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
      <h3 style={{ margin: 0, fontSize: 16, color: "#0f172a" }}>{title}</h3>
      {right}
    </div>
    {children}
  </div>
);

const Row = ({ children }) => (
  <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "flex-end" }}>{children}</div>
);

const Field = ({ label, children, w = 160 }) => (
  <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 12, color: "#64748b", width: w }}>
    {label}
    {children}
  </label>
);

const inputStyle = {
  padding: "8px 10px", border: "1px solid #cbd5e1", borderRadius: 6, fontSize: 13,
};

const Button = ({ children, onClick, disabled, variant = "primary" }) => {
  const styles = {
    primary: { background: "#2563eb", color: "#fff", border: "1px solid #2563eb" },
    ghost: { background: "#fff", color: "#0f172a", border: "1px solid #cbd5e1" },
    danger: { background: "#dc2626", color: "#fff", border: "1px solid #dc2626" },
  }[variant];
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      style={{
        padding: "8px 14px", borderRadius: 6, fontSize: 13, cursor: disabled ? "not-allowed" : "pointer",
        opacity: disabled ? 0.6 : 1, ...styles,
      }}
    >
      {children}
    </button>
  );
};

const Code = ({ value }) => (
  <pre style={{
    background: "#0f172a", color: "#e2e8f0", padding: 12, borderRadius: 8,
    fontSize: 12, maxHeight: 360, overflow: "auto", margin: 0,
  }}>
    {typeof value === "string" ? value : JSON.stringify(value, null, 2)}
  </pre>
);

export default function PaximumTestPage() {
  // Health check
  const health = useQuery({
    queryKey: ["paximum-health"],
    queryFn: () => api.get("/paximum/health").then((r) => r.data),
  });

  // Search form
  const [destType, setDestType] = useState("hotel");
  const [destId, setDestId] = useState("100122");
  const [checkin, setCheckin] = useState(todayPlus(30));
  const [checkout, setCheckout] = useState(todayPlus(33));
  const [adults, setAdults] = useState(2);
  const [childrenAges, setChildrenAges] = useState("");
  const [nationality, setNationality] = useState("TR");
  const [currency, setCurrency] = useState("EUR");
  const [language, setLanguage] = useState("tr");
  const [onlyBest, setOnlyBest] = useState(true);
  const [includeContent, setIncludeContent] = useState(true);

  const [searchResult, setSearchResult] = useState(null);
  const [searchError, setSearchError] = useState("");

  const search = useMutation({
    mutationFn: (body) => api.post("/paximum/search/hotels", body).then((r) => r.data),
    onSuccess: (data) => { setSearchResult(data); setSearchError(""); },
    onError: (e) => { setSearchResult(null); setSearchError(apiErrorMessage(e)); },
  });

  const runSearch = () => {
    const ages = childrenAges
      .split(",").map((s) => s.trim()).filter(Boolean).map((n) => parseInt(n, 10))
      .filter((n) => !Number.isNaN(n));
    search.mutate({
      destinations: [{ type: destType, id: destId }],
      rooms: [{ adults: parseInt(adults, 10) || 2, childrenAges: ages }],
      checkinDate: checkin,
      checkoutDate: checkout,
      currency,
      customerNationality: nationality,
      language,
      onlyBestOffers: onlyBest,
      includeHotelContent: includeContent,
      filterUnavailable: true,
    });
  };

  // Hotel details / availability ad-hoc lookups
  const [hotelIdLookup, setHotelIdLookup] = useState("100122");
  const [offerIdLookup, setOfferIdLookup] = useState("");
  const [lookupResult, setLookupResult] = useState(null);
  const [lookupError, setLookupError] = useState("");

  const lookup = useMutation({
    mutationFn: ({ url, body }) => api.post(url, body).then((r) => r.data),
    onSuccess: (data) => { setLookupResult(data); setLookupError(""); },
    onError: (e) => { setLookupResult(null); setLookupError(apiErrorMessage(e)); },
  });

  // Booking lookup
  const [bookingId, setBookingId] = useState("");
  const [bookingResult, setBookingResult] = useState(null);
  const [bookingError, setBookingError] = useState("");
  const bookingMut = useMutation({
    mutationFn: ({ url, body }) => api.post(url, body).then((r) => r.data),
    onSuccess: (data) => { setBookingResult(data); setBookingError(""); },
    onError: (e) => { setBookingResult(null); setBookingError(apiErrorMessage(e)); },
  });

  const configured = health.data?.configured;

  return (
    <div style={{ padding: 24, maxWidth: 1100, margin: "0 auto" }}>
      <h2 style={{ margin: "0 0 16px", color: "#0f172a" }}>Paximum (San TSG) Test Konsolu</h2>
      <p style={{ color: "#64748b", marginTop: 0 }}>
        San TSG Paximum marketplace API'sini test etmek için geçici admin paneli.
        Üretim öncesi entegrasyon doğrulamada kullanılır.
      </p>

      <Section
        title="Bağlantı Durumu"
        right={
          <span style={{
            padding: "4px 10px", borderRadius: 999, fontSize: 12,
            background: configured ? "#dcfce7" : "#fee2e2",
            color: configured ? "#166534" : "#991b1b",
          }}>
            {health.isLoading ? "kontrol ediliyor..." : configured ? "Yapılandırılmış" : "Eksik secret"}
          </span>
        }
      >
        {!health.isLoading && !configured && (
          <div style={{ color: "#991b1b", fontSize: 13 }}>
            <code>PAXIMUM_BASE_URL</code> ve <code>PAXIMUM_BEARER_TOKEN</code> Replit Secrets üzerinden eklenmelidir.
          </div>
        )}
        {health.data && (
          <div style={{ display: "flex", gap: 16, fontSize: 13, color: "#334155" }}>
            <div>Base URL: <b>{health.data.base_url_set ? "✓" : "✗"}</b></div>
            <div>Token: <b>{health.data.token_set ? "✓" : "✗"}</b></div>
          </div>
        )}
      </Section>

      <Section title="1. Otel Arama (POST /api/paximum/search/hotels)">
        <Row>
          <Field label="Destination Type" w={120}>
            <select value={destType} onChange={(e) => setDestType(e.target.value)} style={inputStyle}>
              <option value="hotel">hotel</option>
              <option value="city">city</option>
            </select>
          </Field>
          <Field label="Destination ID">
            <input value={destId} onChange={(e) => setDestId(e.target.value)} style={inputStyle} />
          </Field>
          <Field label="Check-in" w={140}>
            <input type="date" value={checkin} onChange={(e) => setCheckin(e.target.value)} style={inputStyle} />
          </Field>
          <Field label="Check-out" w={140}>
            <input type="date" value={checkout} onChange={(e) => setCheckout(e.target.value)} style={inputStyle} />
          </Field>
          <Field label="Adults" w={80}>
            <input type="number" min={1} max={9} value={adults} onChange={(e) => setAdults(e.target.value)} style={inputStyle} />
          </Field>
          <Field label="Çocuk Yaşları (virgüllü)">
            <input value={childrenAges} onChange={(e) => setChildrenAges(e.target.value)} placeholder="örn: 5,8" style={inputStyle} />
          </Field>
          <Field label="Nationality" w={90}>
            <input value={nationality} onChange={(e) => setNationality(e.target.value.toUpperCase())} maxLength={2} style={inputStyle} />
          </Field>
          <Field label="Currency" w={90}>
            <input value={currency} onChange={(e) => setCurrency(e.target.value.toUpperCase())} maxLength={3} style={inputStyle} />
          </Field>
          <Field label="Language" w={90}>
            <input value={language} onChange={(e) => setLanguage(e.target.value)} maxLength={2} style={inputStyle} />
          </Field>
          <Field label="Best Offers" w={110}>
            <select value={onlyBest ? "1" : "0"} onChange={(e) => setOnlyBest(e.target.value === "1")} style={inputStyle}>
              <option value="1">true</option>
              <option value="0">false</option>
            </select>
          </Field>
          <Field label="Hotel Content" w={120}>
            <select value={includeContent ? "1" : "0"} onChange={(e) => setIncludeContent(e.target.value === "1")} style={inputStyle}>
              <option value="1">true</option>
              <option value="0">false</option>
            </select>
          </Field>
        </Row>
        <div style={{ marginTop: 12 }}>
          <Button onClick={runSearch} disabled={search.isPending || !configured}>
            {search.isPending ? "Aranıyor..." : "Otel Ara"}
          </Button>
        </div>

        {searchError && (
          <div style={{ marginTop: 12, color: "#991b1b", fontSize: 13 }}>{searchError}</div>
        )}

        {searchResult && (
          <div style={{ marginTop: 16 }}>
            <div style={{ fontSize: 13, color: "#475569", marginBottom: 8 }}>
              SearchId: <code>{searchResult.searchId}</code> · Otel sayısı: <b>{searchResult.hotels?.length ?? 0}</b>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 12 }}>
              {(searchResult.hotels || []).slice(0, 12).map((h) => (
                <div key={h.id} style={{ border: "1px solid #e2e8f0", borderRadius: 8, padding: 12, fontSize: 13 }}>
                  <div style={{ fontWeight: 600, color: "#0f172a" }}>{h.name}</div>
                  <div style={{ color: "#64748b", fontSize: 12 }}>
                    {h.city?.name} · {h.country?.name} · {h.stars}★
                  </div>
                  <div style={{ marginTop: 6, color: "#0f172a" }}>
                    Min: <b>{h.minimumPrice?.amount?.toFixed(2)} {h.minimumPrice?.currency}</b>
                  </div>
                  <div style={{ marginTop: 6 }}>
                    {(h.offers || []).slice(0, 3).map((o) => (
                      <div key={o.id} style={{ background: "#f1f5f9", padding: "4px 8px", borderRadius: 4, fontSize: 11, marginBottom: 3 }}>
                        <div>{o.board} · {o.price?.amount?.toFixed(2)} {o.price?.currency}</div>
                        <div style={{ display: "flex", gap: 6, marginTop: 4 }}>
                          <button
                            type="button"
                            onClick={() => { setOfferIdLookup(o.id); }}
                            style={{ fontSize: 11, padding: "2px 6px", border: "1px solid #cbd5e1", background: "#fff", borderRadius: 3, cursor: "pointer" }}
                          >
                            Offer ID kopyala
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
            <details style={{ marginTop: 12 }}>
              <summary style={{ cursor: "pointer", fontSize: 12, color: "#64748b" }}>Ham JSON</summary>
              <Code value={searchResult} />
            </details>
          </div>
        )}
      </Section>

      <Section title="2. Otel Detayı / Müsaitlik">
        <Row>
          <Field label="Hotel ID">
            <input value={hotelIdLookup} onChange={(e) => setHotelIdLookup(e.target.value)} style={inputStyle} />
          </Field>
          <Button
            variant="ghost"
            disabled={lookup.isPending || !configured}
            onClick={() => lookup.mutate({ url: "/paximum/search/hoteldetails", body: { hotelId: hotelIdLookup } })}
          >
            Otel Detayı
          </Button>

          <Field label="Offer ID">
            <input value={offerIdLookup} onChange={(e) => setOfferIdLookup(e.target.value)} style={inputStyle} />
          </Field>
          <Button
            variant="ghost"
            disabled={lookup.isPending || !configured || !offerIdLookup}
            onClick={() => lookup.mutate({ url: "/paximum/search/checkavailability", body: { offerId: offerIdLookup } })}
          >
            Check Availability
          </Button>
          <Button
            variant="ghost"
            disabled={lookup.isPending || !configured || !offerIdLookup}
            onClick={() => lookup.mutate({ url: "/paximum/search/checkhotelavailability", body: { offerId: offerIdLookup } })}
          >
            Check Hotel Availability
          </Button>
        </Row>
        {lookupError && <div style={{ marginTop: 12, color: "#991b1b", fontSize: 13 }}>{lookupError}</div>}
        {lookupResult && <div style={{ marginTop: 12 }}><Code value={lookupResult} /></div>}
      </Section>

      <Section title="3. Rezervasyon Sorgu / İptal">
        <Row>
          <Field label="Booking ID">
            <input value={bookingId} onChange={(e) => setBookingId(e.target.value)} style={inputStyle} />
          </Field>
          <Button
            variant="ghost"
            disabled={bookingMut.isPending || !configured || !bookingId}
            onClick={() => bookingMut.mutate({ url: "/paximum/booking/details", body: { bookingId } })}
          >
            Detay
          </Button>
          <Button
            variant="ghost"
            disabled={bookingMut.isPending || !configured || !bookingId}
            onClick={() => bookingMut.mutate({ url: "/paximum/booking/cancellationfee", body: { bookingId } })}
          >
            İptal Bedeli
          </Button>
          <Button
            variant="danger"
            disabled={bookingMut.isPending || !configured || !bookingId}
            onClick={() => {
              if (window.confirm("Rezervasyon iptal edilsin mi?")) {
                bookingMut.mutate({ url: "/paximum/booking/cancel", body: { bookingId } });
              }
            }}
          >
            İptal Et
          </Button>
          <Button
            variant="ghost"
            disabled={bookingMut.isPending || !configured}
            onClick={() => bookingMut.mutate({ url: "/paximum/booking/getbookings", body: { getAll: true } })}
          >
            Tüm Rezervasyonlar
          </Button>
        </Row>
        {bookingError && <div style={{ marginTop: 12, color: "#991b1b", fontSize: 13 }}>{bookingError}</div>}
        {bookingResult && <div style={{ marginTop: 12 }}><Code value={bookingResult} /></div>}
      </Section>

      <div style={{ fontSize: 12, color: "#64748b", marginTop: 8 }}>
        Place Order (rezervasyon oluşturma) bu konsolda manuel form yerine doğrudan UI üzerinden ilerleyecek bir sonraki fazda eklenecek.
      </div>
    </div>
  );
}
