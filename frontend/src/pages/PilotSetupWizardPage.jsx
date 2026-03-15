import React, { useState, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Badge } from "../components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { CheckCircle2, Circle, Loader2, XCircle, ArrowRight, ArrowLeft, Rocket } from "lucide-react";
import { api } from "../lib/api";

const STEPS = [
  { key: "agency", label: "Acenta Olustur", step: 1 },
  { key: "supplier", label: "Tedarikci Credential", step: 2 },
  { key: "accounting", label: "Muhasebe Credential", step: 3 },
  { key: "connection", label: "Baglanti Testi", step: 4 },
  { key: "search", label: "Arama Testi", step: 5 },
  { key: "booking", label: "Rezervasyon Testi", step: 6 },
  { key: "invoice", label: "Fatura Testi", step: 7 },
  { key: "accounting_sync", label: "Muhasebe Sync", step: 8 },
  { key: "reconciliation", label: "Mutabakat Kontrol", step: 9 },
];

const SUPPLIERS = [
  { value: "ratehawk", label: "RateHawk" },
  { value: "paximum", label: "Paximum" },
  { value: "tbo", label: "TBO" },
  { value: "wwtatil", label: "WWTatil" },
];

const ACCOUNTING_PROVIDERS = [
  { value: "luca", label: "Luca" },
  { value: "logo", label: "Logo" },
  { value: "parasut", label: "Parasut" },
  { value: "mikro", label: "Mikro" },
];

const MODES = [
  { value: "sandbox", label: "Sandbox", desc: "Platform testi" },
  { value: "simulation", label: "Simulation", desc: "Demo" },
  { value: "production", label: "Production", desc: "Gercek musteri" },
];

function StepIndicator({ steps, currentStep, stepResults }) {
  return (
    <div className="flex items-center gap-1 overflow-x-auto pb-2" data-testid="wizard-step-indicator">
      {steps.map((s, idx) => {
        const result = stepResults[s.key];
        const isCurrent = currentStep === s.step;
        const isPast = currentStep > s.step;
        let icon;
        if (result === "pass") icon = <CheckCircle2 className="h-4 w-4 text-emerald-500" />;
        else if (result === "fail") icon = <XCircle className="h-4 w-4 text-red-500" />;
        else if (isCurrent) icon = <Circle className="h-4 w-4 text-primary fill-primary" />;
        else if (isPast) icon = <CheckCircle2 className="h-4 w-4 text-muted-foreground" />;
        else icon = <Circle className="h-4 w-4 text-muted-foreground" />;

        return (
          <React.Fragment key={s.key}>
            <div className={`flex items-center gap-1.5 px-2 py-1 rounded-md text-xs whitespace-nowrap ${
              isCurrent ? "bg-primary/10 text-primary font-semibold" : "text-muted-foreground"
            }`}>
              {icon}
              <span className="hidden sm:inline">{s.label}</span>
              <span className="sm:hidden">{s.step}</span>
            </div>
            {idx < steps.length - 1 && <ArrowRight className="h-3 w-3 text-muted-foreground/40 flex-shrink-0" />}
          </React.Fragment>
        );
      })}
    </div>
  );
}

export default function PilotSetupWizardPage() {
  const [currentStep, setCurrentStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [agencyName, setAgencyName] = useState("");
  const [stepResults, setStepResults] = useState({});
  const [stepData, setStepData] = useState({});

  // Form states
  const [agencyForm, setAgencyForm] = useState({ name: "", contact_email: "", contact_phone: "", tax_id: "", mode: "sandbox" });
  const [supplierForm, setSupplierForm] = useState({ supplier_type: "ratehawk", api_key: "", api_secret: "", agency_code: "" });
  const [accountingForm, setAccountingForm] = useState({ provider_type: "luca", company_code: "", username: "", password: "" });

  const callApi = useCallback(async (method, url, body) => {
    setLoading(true);
    setError("");
    try {
      const resp = method === "get"
        ? await api.get(url)
        : method === "put"
          ? await api.put(url, body)
          : await api.post(url, body);
      return resp.data;
    } catch (e) {
      const msg = e?.response?.data?.detail || e?.message || "Islem basarisiz";
      setError(String(msg));
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const handleStep1 = async () => {
    if (!agencyForm.name.trim()) { setError("Acenta adi zorunlu"); return; }
    const data = await callApi("post", "/pilot/onboarding/setup", agencyForm);
    if (data) {
      setAgencyName(agencyForm.name);
      setStepResults((p) => ({ ...p, agency: "pass" }));
      setStepData((p) => ({ ...p, agency: data }));
      setCurrentStep(2);
    }
  };

  const handleStep2 = async () => {
    const data = await callApi("put", "/pilot/onboarding/setup/supplier", { ...supplierForm, agency_name: agencyName });
    if (data) {
      setStepResults((p) => ({ ...p, supplier: "pass" }));
      setStepData((p) => ({ ...p, supplier: data }));
      setCurrentStep(3);
    }
  };

  const handleStep3 = async () => {
    const data = await callApi("put", "/pilot/onboarding/setup/accounting", { ...accountingForm, agency_name: agencyName });
    if (data) {
      setStepResults((p) => ({ ...p, accounting: "pass" }));
      setStepData((p) => ({ ...p, accounting: data }));
      setCurrentStep(4);
    }
  };

  const runFlowTest = async (stepKey, stepNum, endpoint) => {
    const data = await callApi("post", endpoint, { agency_name: agencyName });
    if (data && !data.error) {
      const passed = data.status !== "failed" && data.status !== "fail" && data.overall !== "fail";
      setStepResults((p) => ({ ...p, [stepKey]: passed ? "pass" : "fail" }));
      setStepData((p) => ({ ...p, [stepKey]: data }));
      if (passed) setCurrentStep(stepNum + 1);
      else setError(`${STEPS[stepNum - 1].label} basarisiz. Tekrar deneyin.`);
    }
  };

  const isWizardComplete = currentStep > 9;

  return (
    <div className="space-y-6 max-w-4xl mx-auto" data-testid="pilot-setup-wizard">
      <div className="flex items-center gap-3">
        <Rocket className="h-6 w-6 text-primary" />
        <h1 className="text-2xl font-bold text-foreground" data-testid="wizard-title">Pilot Acenta Onboarding Wizard</h1>
      </div>
      <p className="text-sm text-muted-foreground">
        Yeni bir pilot acenta ekleyin. Tum 9 adimi basariyla tamamlamadan acenta <strong>ACTIVE</strong> olamaz.
      </p>

      <StepIndicator steps={STEPS} currentStep={Math.min(currentStep, 9)} stepResults={stepResults} />

      {error && (
        <div className="bg-destructive/10 border border-destructive/20 text-destructive px-4 py-2 rounded-md text-sm" data-testid="wizard-error">
          {error}
        </div>
      )}

      {isWizardComplete ? (
        <Card data-testid="wizard-complete-card">
          <CardContent className="py-12 text-center space-y-4">
            <CheckCircle2 className="h-16 w-16 text-emerald-500 mx-auto" />
            <h2 className="text-xl font-bold text-foreground">Pilot Acenta Aktif!</h2>
            <p className="text-muted-foreground">
              <strong>{agencyName}</strong> basariyla onboard edildi. Tum akis adimlari tamamlandi.
            </p>
            <div className="flex gap-3 justify-center mt-4">
              <Badge variant="outline" className="text-emerald-600">search → booking → invoice → accounting → reconciliation</Badge>
            </div>
            <Button onClick={() => { setCurrentStep(1); setStepResults({}); setStepData({}); setAgencyName(""); setError(""); setAgencyForm({ name: "", contact_email: "", contact_phone: "", tax_id: "", mode: "sandbox" }); }} variant="outline" data-testid="wizard-new-agency-btn">
              Yeni Acenta Ekle
            </Button>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Badge variant="secondary">{currentStep}/9</Badge>
              {STEPS[currentStep - 1]?.label}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Step 1: Agency Create */}
            {currentStep === 1 && (
              <div className="space-y-3" data-testid="wizard-step-1">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div>
                    <label className="text-sm font-medium text-foreground">Acenta Adi *</label>
                    <Input data-testid="agency-name-input" value={agencyForm.name} onChange={(e) => setAgencyForm((p) => ({ ...p, name: e.target.value }))} placeholder="Ornek: Antalya Travel Pro" />
                  </div>
                  <div>
                    <label className="text-sm font-medium text-foreground">E-posta</label>
                    <Input data-testid="agency-email-input" value={agencyForm.contact_email} onChange={(e) => setAgencyForm((p) => ({ ...p, contact_email: e.target.value }))} placeholder="agency@example.com" />
                  </div>
                  <div>
                    <label className="text-sm font-medium text-foreground">Telefon</label>
                    <Input data-testid="agency-phone-input" value={agencyForm.contact_phone} onChange={(e) => setAgencyForm((p) => ({ ...p, contact_phone: e.target.value }))} placeholder="+90 ..." />
                  </div>
                  <div>
                    <label className="text-sm font-medium text-foreground">Vergi No</label>
                    <Input data-testid="agency-tax-input" value={agencyForm.tax_id} onChange={(e) => setAgencyForm((p) => ({ ...p, tax_id: e.target.value }))} placeholder="VKN" />
                  </div>
                </div>
                <div>
                  <label className="text-sm font-medium text-foreground">Mod</label>
                  <Select value={agencyForm.mode} onValueChange={(v) => setAgencyForm((p) => ({ ...p, mode: v }))}>
                    <SelectTrigger data-testid="agency-mode-select"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {MODES.map((m) => <SelectItem key={m.value} value={m.value}>{m.label} - {m.desc}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                <Button onClick={handleStep1} disabled={loading} data-testid="step-1-submit">
                  {loading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null} Acenta Olustur
                </Button>
              </div>
            )}

            {/* Step 2: Supplier Credential */}
            {currentStep === 2 && (
              <div className="space-y-3" data-testid="wizard-step-2">
                <div>
                  <label className="text-sm font-medium text-foreground">Tedarikci</label>
                  <Select value={supplierForm.supplier_type} onValueChange={(v) => setSupplierForm((p) => ({ ...p, supplier_type: v }))}>
                    <SelectTrigger data-testid="supplier-type-select"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {SUPPLIERS.map((s) => <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div>
                    <label className="text-sm font-medium text-foreground">API Key</label>
                    <Input data-testid="supplier-api-key" value={supplierForm.api_key} onChange={(e) => setSupplierForm((p) => ({ ...p, api_key: e.target.value }))} placeholder="api_key" />
                  </div>
                  <div>
                    <label className="text-sm font-medium text-foreground">API Secret</label>
                    <Input data-testid="supplier-api-secret" type="password" value={supplierForm.api_secret} onChange={(e) => setSupplierForm((p) => ({ ...p, api_secret: e.target.value }))} placeholder="api_secret" />
                  </div>
                  <div>
                    <label className="text-sm font-medium text-foreground">Acenta Kodu</label>
                    <Input data-testid="supplier-agency-code" value={supplierForm.agency_code} onChange={(e) => setSupplierForm((p) => ({ ...p, agency_code: e.target.value }))} placeholder="RH001" />
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button variant="outline" onClick={() => setCurrentStep(1)} data-testid="step-2-back"><ArrowLeft className="h-4 w-4 mr-1" /> Geri</Button>
                  <Button onClick={handleStep2} disabled={loading} data-testid="step-2-submit">
                    {loading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null} Kaydet & Devam
                  </Button>
                </div>
              </div>
            )}

            {/* Step 3: Accounting Credential */}
            {currentStep === 3 && (
              <div className="space-y-3" data-testid="wizard-step-3">
                <div>
                  <label className="text-sm font-medium text-foreground">Muhasebe Saglayicisi</label>
                  <Select value={accountingForm.provider_type} onValueChange={(v) => setAccountingForm((p) => ({ ...p, provider_type: v }))}>
                    <SelectTrigger data-testid="accounting-type-select"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {ACCOUNTING_PROVIDERS.map((p) => <SelectItem key={p.value} value={p.value}>{p.label}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div>
                    <label className="text-sm font-medium text-foreground">Sirket Kodu</label>
                    <Input data-testid="accounting-company-code" value={accountingForm.company_code} onChange={(e) => setAccountingForm((p) => ({ ...p, company_code: e.target.value }))} placeholder="LC001" />
                  </div>
                  <div>
                    <label className="text-sm font-medium text-foreground">Kullanici Adi</label>
                    <Input data-testid="accounting-username" value={accountingForm.username} onChange={(e) => setAccountingForm((p) => ({ ...p, username: e.target.value }))} placeholder="username" />
                  </div>
                  <div>
                    <label className="text-sm font-medium text-foreground">Sifre</label>
                    <Input data-testid="accounting-password" type="password" value={accountingForm.password} onChange={(e) => setAccountingForm((p) => ({ ...p, password: e.target.value }))} placeholder="password" />
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button variant="outline" onClick={() => setCurrentStep(2)} data-testid="step-3-back"><ArrowLeft className="h-4 w-4 mr-1" /> Geri</Button>
                  <Button onClick={handleStep3} disabled={loading} data-testid="step-3-submit">
                    {loading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null} Kaydet & Devam
                  </Button>
                </div>
              </div>
            )}

            {/* Steps 4-9: Flow Tests */}
            {currentStep >= 4 && currentStep <= 9 && (
              <div className="space-y-4" data-testid={`wizard-step-${currentStep}`}>
                <p className="text-sm text-muted-foreground">
                  {currentStep === 4 && "Tedarikci ve muhasebe baglantilari test ediliyor..."}
                  {currentStep === 5 && `${supplierForm.supplier_type} uzerinden Antalya araması yapiliyor...`}
                  {currentStep === 6 && "Test rezervasyonu olusturuluyor..."}
                  {currentStep === 7 && "Rezervasyondan fatura olusturuluyor..."}
                  {currentStep === 8 && `Fatura ${accountingForm.provider_type} ile senkronize ediliyor...`}
                  {currentStep === 9 && "Booking vs Invoice vs Accounting mutabakati kontrol ediliyor..."}
                </p>

                {stepData[STEPS[currentStep - 1]?.key] && (
                  <div className="bg-muted/50 rounded-md p-3 text-xs font-mono overflow-auto max-h-48" data-testid="step-result-json">
                    <pre>{JSON.stringify(stepData[STEPS[currentStep - 1]?.key], null, 2)}</pre>
                  </div>
                )}

                <div className="flex gap-2">
                  {currentStep > 4 && (
                    <Button variant="outline" onClick={() => setCurrentStep(currentStep - 1)} data-testid={`step-${currentStep}-back`}>
                      <ArrowLeft className="h-4 w-4 mr-1" /> Geri
                    </Button>
                  )}
                  <Button
                    onClick={() => {
                      const endpoints = {
                        4: "/pilot/onboarding/test-connection",
                        5: "/pilot/onboarding/test-search",
                        6: "/pilot/onboarding/test-booking",
                        7: "/pilot/onboarding/test-invoice",
                        8: "/pilot/onboarding/test-accounting",
                        9: "/pilot/onboarding/test-reconciliation",
                      };
                      runFlowTest(STEPS[currentStep - 1]?.key, currentStep, endpoints[currentStep]);
                    }}
                    disabled={loading}
                    data-testid={`step-${currentStep}-run`}
                  >
                    {loading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
                    {stepResults[STEPS[currentStep - 1]?.key] === "fail" ? "Tekrar Dene" : "Testi Calistir"}
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
