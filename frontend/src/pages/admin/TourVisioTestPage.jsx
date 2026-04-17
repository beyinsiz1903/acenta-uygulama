import React, { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api, apiErrorMessage } from "../../lib/api";

const todayPlus = (days) => {
  const d = new Date();
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10);
};

const PRODUCT_TYPES = [
  { id: 1, name: "Holiday Package" },
  { id: 2, name: "Hotel" },
  { id: 3, name: "Flight" },
  { id: 4, name: "Excursion" },
  { id: 5, name: "Transfer" },
  { id: 6, name: "Tour Culture" },
  { id: 13, name: "Dynamic Package" },
  { id: 14, name: "Rent a Car" },
];

const Section = ({ title, children, right = null }) => (
  <div style={{ background: "#fff", border: "1px solid #e5e7eb", borderRadius: 12, padding: 16, marginBottom: 16 }}>
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
      <h3 style={{ margin: 0, fontSize: 16, color: "#0f172a" }}>{title}</h3>
      {right}
    </div>
    {children}
  </div>
);

const Field = ({ label, children, w = 160 }) => (
  <label style={{ display: "flex", flexDirection: "column", gap: 4, fontSize: 12, color: "#64748b", width: w }}>
    {label}
    {children}
  </label>
);

const inputStyle = { padding: "8px 10px", border: "1px solid #cbd5e1", borderRadius: 6, fontSize: 13 };

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
    fontSize: 12, maxHeight: 380, overflow: "auto", margin: 0, whiteSpace: "pre-wrap",
  }}>
    {typeof value === "string" ? value : JSON.stringify(value, null, 2)}
  </pre>
);

const Tabs = ({ value, onChange, tabs }) => (
  <div style={{ display: "flex", gap: 4, borderBottom: "1px solid #e5e7eb", marginBottom: 16, flexWrap: "wrap" }}>
    {tabs.map((t) => {
      const active = value === t.id;
      return (
        <button
          key={t.id}
          type="button"
          onClick={() => onChange(t.id)}
          style={{
            padding: "8px 14px", border: "none", background: "transparent",
            borderBottom: active ? "2px solid #2563eb" : "2px solid transparent",
            color: active ? "#2563eb" : "#64748b", fontWeight: active ? 600 : 400,
            cursor: "pointer", fontSize: 13,
          }}
        >
          {t.label}
        </button>
      );
    })}
  </div>
);

export default function TourVisioTestPage() {
  // ─── Health & Token ───
  const health = useQuery({
    queryKey: ["tourvisio-health"],
    queryFn: () => api.get("/tourvisio/health").then((r) => r.data),
  });

  const loginMut = useMutation({
    mutationFn: () => api.post("/tourvisio/auth/login").then((r) => r.data),
    onSuccess: () => health.refetch(),
  });
  const clearMut = useMutation({
    mutationFn: () => api.post("/tourvisio/auth/clear").then((r) => r.data),
    onSuccess: () => health.refetch(),
  });

  // ─── Tabs ───
  const [tab, setTab] = useState("search");

  // ─── Autocomplete ───
  const [acProductType, setAcProductType] = useState(2);
  const [acQuery, setAcQuery] = useState("Dubai");
  const [acCulture, setAcCulture] = useState("en-US");
  const acMut = useMutation({
    mutationFn: () =>
      api.post("/tourvisio/search/arrival-autocomplete", {
        body: { ProductType: acProductType, Query: acQuery, Culture: acCulture },
      }).then((r) => r.data),
  });

  // ─── Price Search ───
  const [psProductType, setPsProductType] = useState(2);
  const [psCheckIn, setPsCheckIn] = useState(todayPlus(30));
  const [psNights, setPsNights] = useState(3);
  const [psAdult, setPsAdult] = useState(2);
  const [psChildAges, setPsChildAges] = useState("");
  const [psArrivalCode, setPsArrivalCode] = useState("");
  const [psDepartureCode, setPsDepartureCode] = useState("");
  const [psNationality, setPsNationality] = useState("DE");
  const [psCurrency, setPsCurrency] = useState("EUR");

  const psBody = useMemo(() => {
    const childAges = psChildAges
      ? psChildAges.split(",").map((s) => parseInt(s.trim(), 10)).filter((n) => !Number.isNaN(n))
      : [];
    return {
      ProductType: psProductType,
      CheckIn: psCheckIn,
      NightCount: parseInt(psNights, 10) || 1,
      Currency: psCurrency,
      Nationality: psNationality,
      RoomCriteria: [{ Adult: parseInt(psAdult, 10) || 1, ChildAges: childAges }],
      ArrivalLocations: psArrivalCode ? [{ Id: psArrivalCode, Type: 2 }] : [],
      DepartureLocations: psDepartureCode ? [{ Id: psDepartureCode, Type: 2 }] : [],
    };
  }, [psProductType, psCheckIn, psNights, psAdult, psChildAges, psArrivalCode, psDepartureCode, psNationality, psCurrency]);

  const psMut = useMutation({
    mutationFn: () => api.post("/tourvisio/search/pricesearch", { body: psBody }).then((r) => r.data),
  });

  // ─── Lookups ───
  const lookupPay = useMutation({
    mutationFn: () => api.post("/tourvisio/lookup/payment-types", { body: {} }).then((r) => r.data),
  });
  const lookupTransport = useMutation({
    mutationFn: () => api.post("/tourvisio/lookup/transportations", { body: {} }).then((r) => r.data),
  });
  const lookupRates = useMutation({
    mutationFn: () => api.post("/tourvisio/lookup/exchange-rates", { body: {} }).then((r) => r.data),
  });

  // ─── Cancellation lookup ───
  const [cancelResId, setCancelResId] = useState("");
  const cancelPenaltyMut = useMutation({
    mutationFn: () =>
      api.post("/tourvisio/cancellation/penalty", { body: { ReservationNumber: cancelResId } }).then((r) => r.data),
  });

  // ─── Generic proxy ───
  const [proxyPath, setProxyPath] = useState("/api/productservice/getcheckindates");
  const [proxyBody, setProxyBody] = useState('{\n  "ProductType": 2\n}');
  const proxyMut = useMutation({
    mutationFn: () => {
      let body;
      try { body = JSON.parse(proxyBody || "{}"); }
      catch (e) { throw new Error("Geçersiz JSON: " + e.message); }
      return api.post("/tourvisio/proxy", { path: proxyPath, body }).then((r) => r.data);
    },
  });

  return (
    <div style={{ maxWidth: 1100, margin: "0 auto", padding: 24, fontFamily: "system-ui, sans-serif" }}>
      <h1 style={{ fontSize: 22, color: "#0f172a", marginBottom: 8 }}>TourVisio (San TSG) Test Konsolu</h1>
      <p style={{ color: "#64748b", fontSize: 13, marginBottom: 16 }}>
        TourVisio çoklu ürün API'si — Uçak, Otel, Transfer, Araç, Excursion, Tatil Paketi, Tour Culture, Dynamic Package
        ve booking/cancellation/lookup uç noktalarına proxy. Yetki: super_admin / admin / operator.
      </p>

      <Section
        title="Sağlık & Token"
        right={
          <div style={{ display: "flex", gap: 8 }}>
            <Button variant="ghost" onClick={() => health.refetch()}>Yenile</Button>
            <Button onClick={() => loginMut.mutate()} disabled={loginMut.isPending}>
              {loginMut.isPending ? "Login..." : "Login (yenile)"}
            </Button>
            <Button variant="danger" onClick={() => clearMut.mutate()} disabled={clearMut.isPending}>
              Token sıfırla
            </Button>
          </div>
        }
      >
        {health.isLoading && <div>Yükleniyor...</div>}
        {health.error && <div style={{ color: "#dc2626" }}>{apiErrorMessage(health.error)}</div>}
        {health.data && <Code value={health.data} />}
        {loginMut.error && <div style={{ color: "#dc2626", marginTop: 8 }}>{apiErrorMessage(loginMut.error)}</div>}
      </Section>

      <Tabs
        value={tab}
        onChange={setTab}
        tabs={[
          { id: "search", label: "Arama" },
          { id: "lookup", label: "Lookup" },
          { id: "cancel", label: "İptal" },
          { id: "proxy", label: "Generic Proxy" },
        ]}
      />

      {tab === "search" && (
        <>
          <Section title="Arrival Autocomplete (lokasyon ara)">
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "flex-end" }}>
              <Field label="Ürün Tipi" w={180}>
                <select style={inputStyle} value={acProductType} onChange={(e) => setAcProductType(parseInt(e.target.value, 10))}>
                  {PRODUCT_TYPES.map((p) => <option key={p.id} value={p.id}>{p.id} — {p.name}</option>)}
                </select>
              </Field>
              <Field label="Query" w={200}>
                <input style={inputStyle} value={acQuery} onChange={(e) => setAcQuery(e.target.value)} />
              </Field>
              <Field label="Culture" w={120}>
                <input style={inputStyle} value={acCulture} onChange={(e) => setAcCulture(e.target.value)} />
              </Field>
              <Button onClick={() => acMut.mutate()} disabled={acMut.isPending}>
                {acMut.isPending ? "Aranıyor..." : "Ara"}
              </Button>
            </div>
            {acMut.error && <div style={{ color: "#dc2626", marginTop: 8 }}>{apiErrorMessage(acMut.error)}</div>}
            {acMut.data && <div style={{ marginTop: 12 }}><Code value={acMut.data} /></div>}
          </Section>

          <Section title="Price Search (tüm ürün tipleri)">
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "flex-end", marginBottom: 8 }}>
              <Field label="Ürün Tipi" w={180}>
                <select style={inputStyle} value={psProductType} onChange={(e) => setPsProductType(parseInt(e.target.value, 10))}>
                  {PRODUCT_TYPES.map((p) => <option key={p.id} value={p.id}>{p.id} — {p.name}</option>)}
                </select>
              </Field>
              <Field label="CheckIn" w={150}>
                <input type="date" style={inputStyle} value={psCheckIn} onChange={(e) => setPsCheckIn(e.target.value)} />
              </Field>
              <Field label="Geceler" w={90}>
                <input type="number" style={inputStyle} value={psNights} onChange={(e) => setPsNights(e.target.value)} />
              </Field>
              <Field label="Adult" w={80}>
                <input type="number" style={inputStyle} value={psAdult} onChange={(e) => setPsAdult(e.target.value)} />
              </Field>
              <Field label="Çocuk yaşları (vs. 5,8)" w={160}>
                <input style={inputStyle} value={psChildAges} onChange={(e) => setPsChildAges(e.target.value)} />
              </Field>
            </div>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "flex-end", marginBottom: 8 }}>
              <Field label="ArrivalLocation Id" w={170}>
                <input style={inputStyle} value={psArrivalCode} onChange={(e) => setPsArrivalCode(e.target.value)} placeholder="autocomplete'den" />
              </Field>
              <Field label="DepartureLocation Id" w={170}>
                <input style={inputStyle} value={psDepartureCode} onChange={(e) => setPsDepartureCode(e.target.value)} placeholder="opsiyonel" />
              </Field>
              <Field label="Nationality" w={120}>
                <input style={inputStyle} value={psNationality} onChange={(e) => setPsNationality(e.target.value)} />
              </Field>
              <Field label="Currency" w={100}>
                <input style={inputStyle} value={psCurrency} onChange={(e) => setPsCurrency(e.target.value)} />
              </Field>
              <Button onClick={() => psMut.mutate()} disabled={psMut.isPending}>
                {psMut.isPending ? "Aranıyor..." : "Price Search"}
              </Button>
            </div>
            <div style={{ fontSize: 11, color: "#64748b", marginBottom: 8 }}>
              Gönderilecek body önizleme:
            </div>
            <Code value={psBody} />
            {psMut.error && <div style={{ color: "#dc2626", marginTop: 8 }}>{apiErrorMessage(psMut.error)}</div>}
            {psMut.data && <div style={{ marginTop: 12 }}><Code value={psMut.data} /></div>}
          </Section>
        </>
      )}

      {tab === "lookup" && (
        <>
          <Section
            title="Payment Types"
            right={<Button onClick={() => lookupPay.mutate()} disabled={lookupPay.isPending}>Çağır</Button>}
          >
            {lookupPay.error && <div style={{ color: "#dc2626" }}>{apiErrorMessage(lookupPay.error)}</div>}
            {lookupPay.data && <Code value={lookupPay.data} />}
          </Section>
          <Section
            title="Transportations"
            right={<Button onClick={() => lookupTransport.mutate()} disabled={lookupTransport.isPending}>Çağır</Button>}
          >
            {lookupTransport.error && <div style={{ color: "#dc2626" }}>{apiErrorMessage(lookupTransport.error)}</div>}
            {lookupTransport.data && <Code value={lookupTransport.data} />}
          </Section>
          <Section
            title="Exchange Rates"
            right={<Button onClick={() => lookupRates.mutate()} disabled={lookupRates.isPending}>Çağır</Button>}
          >
            {lookupRates.error && <div style={{ color: "#dc2626" }}>{apiErrorMessage(lookupRates.error)}</div>}
            {lookupRates.data && <Code value={lookupRates.data} />}
          </Section>
        </>
      )}

      {tab === "cancel" && (
        <Section title="Cancellation Penalty (test)">
          <div style={{ display: "flex", gap: 8, alignItems: "flex-end" }}>
            <Field label="Reservation Number" w={260}>
              <input style={inputStyle} value={cancelResId} onChange={(e) => setCancelResId(e.target.value)} />
            </Field>
            <Button onClick={() => cancelPenaltyMut.mutate()} disabled={!cancelResId || cancelPenaltyMut.isPending}>
              Penalty sorgula
            </Button>
          </div>
          <div style={{ fontSize: 11, color: "#dc2626", marginTop: 8 }}>
            Uyarı: gerçek iptal (`/cancellation/cancel`) production rezervasyonlarını iptal eder. Bu konsoldan etkin değildir;
            generic proxy ile çağırın.
          </div>
          {cancelPenaltyMut.error && <div style={{ color: "#dc2626", marginTop: 8 }}>{apiErrorMessage(cancelPenaltyMut.error)}</div>}
          {cancelPenaltyMut.data && <div style={{ marginTop: 12 }}><Code value={cancelPenaltyMut.data} /></div>}
        </Section>
      )}

      {tab === "proxy" && (
        <Section title="Generic Proxy — herhangi bir TourVisio endpoint'i">
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            <Field label="Path" w="100%">
              <input style={inputStyle} value={proxyPath} onChange={(e) => setProxyPath(e.target.value)} />
            </Field>
            <Field label="Body (JSON)" w="100%">
              <textarea
                rows={10}
                style={{ ...inputStyle, fontFamily: "monospace" }}
                value={proxyBody}
                onChange={(e) => setProxyBody(e.target.value)}
              />
            </Field>
            <div>
              <Button onClick={() => proxyMut.mutate()} disabled={proxyMut.isPending}>
                {proxyMut.isPending ? "Çağrılıyor..." : "POST"}
              </Button>
            </div>
          </div>
          {proxyMut.error && <div style={{ color: "#dc2626", marginTop: 8 }}>{apiErrorMessage(proxyMut.error)}</div>}
          {proxyMut.data && <div style={{ marginTop: 12 }}><Code value={proxyMut.data} /></div>}
        </Section>
      )}
    </div>
  );
}
