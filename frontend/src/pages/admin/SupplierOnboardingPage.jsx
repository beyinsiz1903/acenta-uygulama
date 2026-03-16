import React, { useState, useCallback } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import {
  CheckCircle2, XCircle, ArrowLeft, ArrowRight, Eye, EyeOff,
  Globe, Key, Lock, User, Building2, Shield, Zap, Play, RotateCcw,
  ChevronRight, Activity, FileText, Clock, AlertTriangle, Power,
  Loader2
} from "lucide-react";
import { api } from "../../lib/api";

const STATUS_CONFIG = {
  not_started: { label: "Baslanmadi", color: "bg-zinc-700/40 text-zinc-400 border-zinc-600/40" },
  credentials_saved: { label: "Credential Kaydedildi", color: "bg-amber-500/20 text-amber-300 border-amber-500/30" },
  health_check_passed: { label: "Saglik Kontrolu OK", color: "bg-blue-500/20 text-blue-300 border-blue-500/30" },
  health_check_failed: { label: "Saglik Kontrolu Basarisiz", color: "bg-red-500/20 text-red-300 border-red-500/30" },
  certified: { label: "Sertifika OK", color: "bg-emerald-500/20 text-emerald-300 border-emerald-500/30" },
  certification_failed: { label: "Sertifika Basarisiz", color: "bg-red-500/20 text-red-300 border-red-500/30" },
  live: { label: "CANLI", color: "bg-emerald-500/30 text-emerald-200 border-emerald-400/50" },
};

const STEP_LABELS = [
  "Supplier Sec",
  "Credential Gir",
  "Dogrulama + Saglik",
  "Sertifikasyon",
  "Rapor",
  "Go Live",
];

const SUPPLIER_COLORS = {
  ratehawk: "from-orange-600 to-red-600",
  paximum: "from-emerald-600 to-teal-700",
  tbo: "from-sky-600 to-blue-700",
  wwtatil: "from-blue-600 to-indigo-700",
  hotelbeds: "from-rose-600 to-pink-700",
  juniper: "from-violet-600 to-purple-700",
};

const FIELD_ICONS = { base_url: Globe, key_id: Key, api_key: Lock, username: User, password: Lock, client_id: Building2, agency_code: Building2, application_secret_key: Key, secret: Lock, agency_id: Building2 };

function StepIndicator({ current, supplierStatus }) {
  const getStepState = (idx) => {
    if (idx < current) return "done";
    if (idx === current) return "active";
    return "pending";
  };
  return (
    <div data-testid="step-indicator" className="flex items-center gap-1 mb-6">
      {STEP_LABELS.map((label, i) => {
        const state = getStepState(i);
        return (
          <React.Fragment key={i}>
            <div className="flex items-center gap-1.5">
              <div className={`w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold transition-all ${state === "done" ? "bg-emerald-500/30 text-emerald-300 border border-emerald-500/50" : state === "active" ? "bg-sky-500/30 text-sky-200 border border-sky-400/60 ring-2 ring-sky-500/20" : "bg-zinc-800/60 text-zinc-500 border border-zinc-700/50"}`}>
                {state === "done" ? <CheckCircle2 className="w-3.5 h-3.5" /> : i + 1}
              </div>
              <span className={`text-[10px] hidden lg:inline ${state === "active" ? "text-sky-300 font-medium" : state === "done" ? "text-emerald-400" : "text-zinc-600"}`}>{label}</span>
            </div>
            {i < STEP_LABELS.length - 1 && <div className={`flex-1 h-px min-w-[16px] ${state === "done" ? "bg-emerald-500/40" : "bg-zinc-800"}`} />}
          </React.Fragment>
        );
      })}
    </div>
  );
}

function CredentialForm({ supplier, onSave, saving }) {
  const [fields, setFields] = useState(() => {
    const init = {};
    supplier.credential_fields.forEach(f => { init[f.key] = ""; });
    return init;
  });
  const [showSensitive, setShowSensitive] = useState({});

  const filled = supplier.credential_fields.filter(f => f.required).every(f => fields[f.key]?.trim());

  return (
    <div data-testid="credential-form" className="space-y-3">
      <div className="bg-zinc-800/40 rounded-lg p-4 border border-zinc-700/50">
        <h4 className="text-xs font-medium text-zinc-300 mb-3 flex items-center gap-2"><Key className="w-3.5 h-3.5 text-amber-400" />API Credential Bilgileri</h4>
        <div className="space-y-2.5">
          {supplier.credential_fields.map(f => {
            const Icon = FIELD_ICONS[f.key] || Key;
            return (
              <div key={f.key} className="flex items-center gap-2.5">
                <Icon className="w-3.5 h-3.5 text-zinc-500 shrink-0" />
                <label className="text-zinc-400 w-28 shrink-0 text-[11px]">{f.label}{f.required && <span className="text-red-400 ml-0.5">*</span>}</label>
                <div className="flex-1 relative">
                  <Input
                    data-testid={`cred-input-${f.key}`}
                    type={f.sensitive && !showSensitive[f.key] ? "password" : "text"}
                    value={fields[f.key] || ""}
                    onChange={e => setFields(p => ({ ...p, [f.key]: e.target.value }))}
                    placeholder={f.placeholder}
                    className="h-8 text-xs bg-zinc-900/80 border-zinc-700 focus:border-sky-600"
                  />
                  {f.sensitive && (
                    <button className="absolute right-2.5 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-300" onClick={() => setShowSensitive(p => ({ ...p, [f.key]: !p[f.key] }))}>
                      {showSensitive[f.key] ? <EyeOff className="w-3 h-3" /> : <Eye className="w-3 h-3" />}
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
      {supplier.sandbox_url && (
        <div className="flex items-center gap-2 text-[10px] text-zinc-500 px-1">
          <Globe className="w-3 h-3" />
          <span>Sandbox: {supplier.sandbox_url}</span>
          {supplier.docs_url && <a href={supplier.docs_url} target="_blank" rel="noreferrer" className="text-sky-500 hover:text-sky-400 ml-auto flex items-center gap-1"><FileText className="w-3 h-3" />Dokumantasyon</a>}
        </div>
      )}
      <Button data-testid="save-credentials-btn" className="w-full h-9 text-xs" disabled={!filled || saving} onClick={() => onSave(fields)}>
        {saving ? <><Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" />Kaydediliyor...</> : <>Credential Kaydet<ArrowRight className="w-3.5 h-3.5 ml-1.5" /></>}
      </Button>
    </div>
  );
}

function HealthCheckPanel({ result, running, onRun }) {
  return (
    <div data-testid="health-check-panel" className="space-y-3">
      {!result && !running && (
        <div className="text-center py-6">
          <Activity className="w-8 h-8 text-zinc-600 mx-auto mb-3" />
          <p className="text-xs text-zinc-500 mb-4">Credential dogrulamasi ve API saglik kontrolu calistirilmadi.</p>
          <Button data-testid="run-health-check-btn" className="h-9 text-xs" onClick={onRun}><Zap className="w-3.5 h-3.5 mr-1.5" />Dogrulama + Saglik Kontrolu Calistir</Button>
        </div>
      )}
      {running && (
        <div className="flex flex-col items-center py-8">
          <Loader2 className="w-8 h-8 text-sky-400 animate-spin mb-3" />
          <p className="text-xs text-zinc-400">Saglik kontrolu calisiyor...</p>
        </div>
      )}
      {result && !running && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {result.overall === "pass" ? <CheckCircle2 className="w-5 h-5 text-emerald-400" /> : <XCircle className="w-5 h-5 text-red-400" />}
              <span className="text-sm font-semibold text-zinc-200">{result.overall === "pass" ? "Tum Kontroller Gecti" : "Bazi Kontroller Basarisiz"}</span>
            </div>
            <Badge variant="outline" className={`text-xs font-mono ${result.overall === "pass" ? "text-emerald-300 border-emerald-600/40" : "text-red-300 border-red-600/40"}`}>{result.score}%</Badge>
          </div>
          <div className="space-y-2">
            {result.checks.map(c => (
              <div key={c.id} data-testid={`health-${c.id}`} className={`flex items-start gap-3 p-3 rounded-lg border ${c.status === "pass" ? "bg-emerald-950/30 border-emerald-800/40" : "bg-red-950/30 border-red-800/40"}`}>
                {c.status === "pass" ? <CheckCircle2 className="w-4 h-4 text-emerald-400 mt-0.5 shrink-0" /> : <XCircle className="w-4 h-4 text-red-400 mt-0.5 shrink-0" />}
                <div className="flex-1 min-w-0">
                  <div className="text-xs font-medium text-zinc-200">{c.name}</div>
                  <div className="text-[11px] text-zinc-400 mt-0.5">{c.message}</div>
                </div>
                <span className="text-[10px] text-zinc-600 font-mono shrink-0">{c.duration_ms}ms</span>
              </div>
            ))}
          </div>
          <div className="flex justify-between items-center pt-1">
            <span className="text-[10px] text-zinc-600">Toplam sure: {result.total_duration_ms}ms</span>
            <Button data-testid="rerun-health-btn" size="sm" variant="outline" className="text-xs h-7" onClick={onRun}><RotateCcw className="w-3 h-3 mr-1" />Tekrar Calistir</Button>
          </div>
        </div>
      )}
    </div>
  );
}

function CertificationPanel({ result, running, onRun }) {
  return (
    <div data-testid="certification-panel" className="space-y-3">
      {!result && !running && (
        <div className="text-center py-6">
          <Shield className="w-8 h-8 text-zinc-600 mx-auto mb-3" />
          <p className="text-xs text-zinc-500 mb-1">Sandbox sertifikasyon testleri henuz calistirilmadi.</p>
          <p className="text-[10px] text-zinc-600 mb-4">Search, Detail, Revalidation, Booking, Status, Cancel adimlari test edilecek.</p>
          <Button data-testid="run-certification-btn" className="h-9 text-xs" onClick={onRun}><Play className="w-3.5 h-3.5 mr-1.5" />Sertifikasyon Testlerini Calistir</Button>
        </div>
      )}
      {running && (
        <div className="flex flex-col items-center py-8">
          <Loader2 className="w-8 h-8 text-sky-400 animate-spin mb-3" />
          <p className="text-xs text-zinc-400">Sertifikasyon testleri calisiyor...</p>
          <p className="text-[10px] text-zinc-600 mt-1">6 adimlik E2E test akisi</p>
        </div>
      )}
      {result && !running && (
        <div className="space-y-4">
          {/* Score header */}
          <div className="bg-zinc-800/40 rounded-xl p-4 border border-zinc-700/50">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs text-zinc-400 font-medium">Certification Score</span>
              <Badge variant="outline" className={`text-sm font-mono font-bold px-3 ${result.go_live_eligible ? "text-emerald-300 border-emerald-500/50 bg-emerald-500/10" : "text-red-300 border-red-500/50 bg-red-500/10"}`}>{result.score}%</Badge>
            </div>
            <div className="w-full bg-zinc-800 rounded-full h-2.5 overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-1000 ${result.score >= 80 ? "bg-emerald-500" : result.score >= 50 ? "bg-amber-500" : "bg-red-500"}`}
                style={{ width: `${result.score}%` }}
              />
            </div>
            <div className="flex justify-between mt-1.5">
              <span className="text-[10px] text-zinc-600">{result.passed}/{result.total} test gecti</span>
              <span className={`text-[10px] font-medium ${result.go_live_eligible ? "text-emerald-400" : "text-red-400"}`}>{result.go_live_eligible ? "Go-Live Uygun" : `Minimum %${result.go_live_threshold} gerekli`}</span>
            </div>
          </div>
          {/* Test results */}
          <div className="space-y-2">
            {result.results.map(r => (
              <div key={r.id} data-testid={`cert-${r.id}`} className={`flex items-start gap-3 p-3 rounded-lg border ${r.status === "pass" ? "bg-emerald-950/20 border-emerald-800/30" : "bg-red-950/20 border-red-800/30"}`}>
                {r.status === "pass" ? <CheckCircle2 className="w-4 h-4 text-emerald-400 mt-0.5 shrink-0" /> : <XCircle className="w-4 h-4 text-red-400 mt-0.5 shrink-0" />}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-medium text-zinc-200">{r.name}</span>
                    <span className="text-[10px] text-zinc-600">{r.description}</span>
                  </div>
                  <div className="text-[11px] text-zinc-400 mt-0.5">{r.message}</div>
                </div>
                <span className="text-[10px] text-zinc-600 font-mono shrink-0">{r.duration_ms}ms</span>
              </div>
            ))}
          </div>
          <div className="flex justify-between items-center pt-1">
            <span className="text-[10px] text-zinc-600">Toplam: {result.total_duration_ms}ms | Run: {result.test_run_id}</span>
            <Button data-testid="rerun-cert-btn" size="sm" variant="outline" className="text-xs h-7" onClick={onRun}><RotateCcw className="w-3 h-3 mr-1" />Tekrar Calistir</Button>
          </div>
        </div>
      )}
    </div>
  );
}

function GoLivePanel({ supplier, onToggle, toggling }) {
  const cert = supplier.certification;
  const isLive = supplier.status === "live";
  const eligible = cert?.go_live_eligible;

  return (
    <div data-testid="go-live-panel" className="space-y-4">
      <div className={`rounded-xl p-5 border ${isLive ? "bg-emerald-950/30 border-emerald-700/50" : eligible ? "bg-zinc-800/40 border-zinc-700/50" : "bg-red-950/20 border-red-800/30"}`}>
        <div className="flex items-center gap-3 mb-4">
          <Power className={`w-6 h-6 ${isLive ? "text-emerald-400" : eligible ? "text-amber-400" : "text-zinc-600"}`} />
          <div>
            <h4 className="text-sm font-semibold text-zinc-200">{isLive ? "Supplier CANLI" : eligible ? "Go-Live Hazir" : "Go-Live Icin Sertifika Gerekli"}</h4>
            <p className="text-[11px] text-zinc-500 mt-0.5">{isLive ? "Bu supplier uretim trafigine acik." : eligible ? "Sertifikasyon tamamlandi. Go-Live aktif edilebilir." : `Minimum %80 sertifikasyon puani gerekli. Mevcut: %${cert?.score || 0}`}</p>
          </div>
        </div>
        {cert && (
          <div className="grid grid-cols-3 gap-3 mb-4">
            <div className="bg-zinc-900/60 rounded-lg p-3 text-center border border-zinc-800/50">
              <div className="text-lg font-bold text-zinc-200 font-mono">{cert.score}%</div>
              <div className="text-[10px] text-zinc-500">Sertifika Puani</div>
            </div>
            <div className="bg-zinc-900/60 rounded-lg p-3 text-center border border-zinc-800/50">
              <div className="text-lg font-bold text-zinc-200 font-mono">{cert.passed}/{cert.total}</div>
              <div className="text-[10px] text-zinc-500">Gecen Testler</div>
            </div>
            <div className="bg-zinc-900/60 rounded-lg p-3 text-center border border-zinc-800/50">
              <div className={`text-lg font-bold font-mono ${eligible ? "text-emerald-400" : "text-red-400"}`}>{eligible ? "EVET" : "HAYIR"}</div>
              <div className="text-[10px] text-zinc-500">Go-Live Uygun</div>
            </div>
          </div>
        )}
        <Button
          data-testid="go-live-toggle-btn"
          className={`w-full h-10 text-xs font-medium ${isLive ? "bg-red-600 hover:bg-red-700" : "bg-emerald-600 hover:bg-emerald-700"}`}
          disabled={!eligible || toggling}
          onClick={() => onToggle(!isLive)}
        >
          {toggling ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Power className="w-4 h-4 mr-2" />}
          {isLive ? "Devre Disi Birak" : "Go Live — Uretimi Aktif Et"}
        </Button>
      </div>
      {supplier.go_live_at && (
        <div className="flex items-center gap-2 text-[10px] text-zinc-600 px-1">
          <Clock className="w-3 h-3" />
          <span>Son Go-Live: {new Date(supplier.go_live_at).toLocaleString("tr-TR")}</span>
        </div>
      )}
    </div>
  );
}

function SupplierWizard({ supplierCode, onBack }) {
  const queryClient = useQueryClient();
  const [step, setStep] = useState(0);
  const [saving, setSaving] = useState(false);
  const [healthRunning, setHealthRunning] = useState(false);
  const [certRunning, setCertRunning] = useState(false);
  const [toggling, setToggling] = useState(false);
  const [healthResult, setHealthResult] = useState(null);
  const [certResult, setCertResult] = useState(null);

  const { data: supplier, refetch } = useQuery({
    queryKey: ["supplier-onboarding", "detail", supplierCode],
    queryFn: async () => {
      const r = await api.get(`/supplier-onboarding/detail/${supplierCode}`);
      return r.data;
    },
    enabled: !!supplierCode,
  });

  // Determine step from status
  React.useEffect(() => {
    if (!supplier) return;
    const s = supplier.status;
    if (s === "not_started") setStep(1);
    else if (s === "credentials_saved") setStep(2);
    else if (s === "health_check_passed") setStep(3);
    else if (s === "health_check_failed") setStep(2);
    else if (s === "certified" || s === "certification_failed") setStep(4);
    else if (s === "live") setStep(5);
    // Load existing results
    if (supplier.health_check) setHealthResult(supplier.health_check);
    if (supplier.certification) setCertResult(supplier.certification);
  }, [supplier]);

  const saveCredentials = useCallback(async (fields) => {
    setSaving(true);
    try {
      await api.post("/supplier-onboarding/credentials", { supplier_code: supplierCode, credentials: fields });
      await refetch();
      setStep(2);
    } catch (e) { console.error(e); }
    setSaving(false);
  }, [supplierCode, refetch]);

  const runHealthCheck = useCallback(async () => {
    setHealthRunning(true);
    setHealthResult(null);
    try {
      const r = await api.post(`/supplier-onboarding/validate/${supplierCode}`);
      setHealthResult(r.data);
      await refetch();
      if (r.data.overall === "pass") setStep(3);
    } catch (e) { console.error(e); }
    setHealthRunning(false);
  }, [supplierCode, refetch]);

  const runCertification = useCallback(async () => {
    setCertRunning(true);
    setCertResult(null);
    try {
      const r = await api.post(`/supplier-onboarding/certify/${supplierCode}`);
      setCertResult(r.data);
      await refetch();
      if (r.data.go_live_eligible) setStep(4);
    } catch (e) { console.error(e); }
    setCertRunning(false);
  }, [supplierCode, refetch]);

  const toggleGoLive = useCallback(async (enabled) => {
    setToggling(true);
    try {
      await api.post(`/supplier-onboarding/go-live/${supplierCode}`, { enabled });
      await refetch();
      queryClient.invalidateQueries({ queryKey: ["supplier-onboarding"] });
      if (enabled) setStep(5);
    } catch (e) { console.error(e); }
    setToggling(false);
  }, [supplierCode, refetch, queryClient]);

  if (!supplier) return <div className="flex items-center justify-center py-12"><Loader2 className="w-6 h-6 text-zinc-600 animate-spin" /></div>;

  const sc = STATUS_CONFIG[supplier.status] || STATUS_CONFIG.not_started;
  const gradColor = SUPPLIER_COLORS[supplierCode] || "from-zinc-600 to-zinc-700";

  return (
    <div data-testid="supplier-wizard" className="space-y-5">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Button data-testid="wizard-back-btn" size="sm" variant="outline" className="text-xs h-8 border-zinc-700" onClick={onBack}><ArrowLeft className="w-3.5 h-3.5 mr-1" />Geri</Button>
        <div className={`w-9 h-9 rounded-lg bg-gradient-to-br ${gradColor} flex items-center justify-center`}><Globe className="w-4 h-4 text-white" /></div>
        <div>
          <h3 className="text-sm font-bold text-zinc-100">{supplier.name} Onboarding</h3>
          <div className="flex items-center gap-2 mt-0.5">
            <Badge variant="outline" className={`text-[9px] ${sc.color}`}>{sc.label}</Badge>
            {supplier.product_types?.map(t => <Badge key={t} variant="outline" className="text-[9px] text-zinc-500 border-zinc-700">{t}</Badge>)}
          </div>
        </div>
      </div>

      <StepIndicator current={step} supplierStatus={supplier.status} />

      {/* Step Content */}
      <Card className="bg-zinc-900/70 border-zinc-800">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-semibold text-zinc-200 flex items-center gap-2">
            {step === 1 && <><Key className="w-4 h-4 text-amber-400" />Adim 2: Credential Girisi</>}
            {step === 2 && <><Activity className="w-4 h-4 text-sky-400" />Adim 3: Dogrulama + API Saglik Kontrolu</>}
            {step === 3 && <><Shield className="w-4 h-4 text-violet-400" />Adim 4: Sandbox Sertifikasyon</>}
            {step === 4 && <><FileText className="w-4 h-4 text-emerald-400" />Adim 5: Sertifika Raporu + Go Live</>}
            {step === 5 && <><Power className="w-4 h-4 text-emerald-400" />Adim 6: Go Live Durumu</>}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {step === 1 && <CredentialForm supplier={supplier} onSave={saveCredentials} saving={saving} />}
          {step === 2 && (
            <div className="space-y-4">
              {supplier.credentials_preview && Object.keys(supplier.credentials_preview).length > 0 && (
                <div className="bg-zinc-800/30 rounded-lg p-3 border border-zinc-700/40">
                  <h5 className="text-[10px] text-zinc-500 mb-2 font-medium">Kayitli Credential</h5>
                  <div className="grid grid-cols-2 gap-1.5">
                    {Object.entries(supplier.credentials_preview).map(([k, v]) => (
                      <div key={k} className="flex items-center gap-1.5 text-[11px]">
                        <span className="text-zinc-500">{k}:</span>
                        <span className="text-zinc-300 font-mono">{v}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              <HealthCheckPanel result={healthResult} running={healthRunning} onRun={runHealthCheck} />
            </div>
          )}
          {step === 3 && <CertificationPanel result={certResult} running={certRunning} onRun={runCertification} />}
          {(step === 4 || step === 5) && <GoLivePanel supplier={supplier} onToggle={toggleGoLive} toggling={toggling} />}
        </CardContent>
      </Card>

      {/* Navigation */}
      {step > 1 && step < 5 && (
        <div className="flex justify-between">
          <Button size="sm" variant="outline" className="text-xs h-8 border-zinc-700" onClick={() => setStep(s => Math.max(1, s - 1))}><ArrowLeft className="w-3 h-3 mr-1" />Onceki Adim</Button>
          {step === 2 && healthResult?.overall === "pass" && <Button size="sm" className="text-xs h-8" onClick={() => setStep(3)}>Sertifikasyona Gec<ArrowRight className="w-3 h-3 ml-1" /></Button>}
          {step === 3 && certResult?.go_live_eligible && <Button size="sm" className="text-xs h-8" onClick={() => setStep(4)}>Go Live Adimina Gec<ArrowRight className="w-3 h-3 ml-1" /></Button>}
        </div>
      )}
    </div>
  );
}

export default function SupplierOnboardingPage() {
  const [selectedSupplier, setSelectedSupplier] = useState(null);

  const { data: dashboard, isLoading } = useQuery({
    queryKey: ["supplier-onboarding", "dashboard"],
    queryFn: async () => {
      const r = await api.get("/supplier-onboarding/dashboard");
      return r.data;
    },
  });

  if (selectedSupplier) {
    return (
      <div data-testid="supplier-onboarding-page" className="p-6 max-w-4xl mx-auto">
        <SupplierWizard supplierCode={selectedSupplier} onBack={() => setSelectedSupplier(null)} />
      </div>
    );
  }

  const suppliers = dashboard?.suppliers || [];
  const liveCount = suppliers.filter(s => s.status === "live").length;
  const certifiedCount = suppliers.filter(s => s.status === "certified").length;
  const inProgress = suppliers.filter(s => !["not_started", "live"].includes(s.status)).length;

  return (
    <div data-testid="supplier-onboarding-page" className="p-6 max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-lg font-bold text-zinc-100 flex items-center gap-2"><Shield className="w-5 h-5 text-sky-400" />Supplier Onboarding</h2>
        <p className="text-xs text-zinc-500 mt-1">Supplier ekle, credential gir, test calistir ve go-live aktif et</p>
      </div>

      {/* KPI cards */}
      <div className="grid grid-cols-4 gap-3">
        {[
          { label: "Toplam Supplier", value: suppliers.length, icon: Globe, color: "text-zinc-300" },
          { label: "Canli (Live)", value: liveCount, icon: Zap, color: "text-emerald-400" },
          { label: "Sertifika OK", value: certifiedCount, icon: Shield, color: "text-sky-400" },
          { label: "Devam Ediyor", value: inProgress, icon: Activity, color: "text-amber-400" },
        ].map(kpi => (
          <Card key={kpi.label} className="bg-zinc-900/70 border-zinc-800">
            <CardContent className="p-3 flex items-center gap-3">
              <kpi.icon className={`w-5 h-5 ${kpi.color}`} />
              <div>
                <div className={`text-xl font-bold font-mono ${kpi.color}`}>{kpi.value}</div>
                <div className="text-[10px] text-zinc-500">{kpi.label}</div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Supplier grid */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12"><Loader2 className="w-6 h-6 text-zinc-600 animate-spin" /></div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {suppliers.map(s => {
            const sc = STATUS_CONFIG[s.status] || STATUS_CONFIG.not_started;
            const gradColor = SUPPLIER_COLORS[s.supplier_code] || "from-zinc-600 to-zinc-700";
            const certScore = s.certification?.score;
            return (
              <Card
                key={s.supplier_code}
                data-testid={`supplier-card-${s.supplier_code}`}
                className="bg-zinc-900/70 border-zinc-800 hover:border-zinc-600 cursor-pointer transition-all group"
                onClick={() => setSelectedSupplier(s.supplier_code)}
              >
                <CardContent className="p-4">
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-2.5">
                      <div className={`w-9 h-9 rounded-lg bg-gradient-to-br ${gradColor} flex items-center justify-center`}><Globe className="w-4 h-4 text-white" /></div>
                      <div>
                        <h4 className="text-sm font-semibold text-zinc-100">{s.name || s.supplier_code}</h4>
                        <Badge variant="outline" className={`text-[9px] mt-0.5 ${sc.color}`}>{sc.label}</Badge>
                      </div>
                    </div>
                    <ChevronRight className="w-4 h-4 text-zinc-700 group-hover:text-zinc-400 transition-colors mt-1" />
                  </div>
                  {certScore != null && (
                    <div className="mt-2">
                      <div className="flex justify-between text-[10px] text-zinc-500 mb-1">
                        <span>Sertifika Puani</span>
                        <span className={`font-mono font-medium ${certScore >= 80 ? "text-emerald-400" : "text-red-400"}`}>{certScore}%</span>
                      </div>
                      <div className="w-full bg-zinc-800 rounded-full h-1.5 overflow-hidden">
                        <div className={`h-full rounded-full ${certScore >= 80 ? "bg-emerald-500" : certScore >= 50 ? "bg-amber-500" : "bg-red-500"}`} style={{ width: `${certScore}%` }} />
                      </div>
                    </div>
                  )}
                  {s.status === "not_started" && (
                    <div className="flex items-center gap-1.5 text-[10px] text-zinc-600 mt-3"><AlertTriangle className="w-3 h-3" />Onboarding baslatilmadi</div>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
