import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { Check, Building2, Package, UserPlus, Handshake, ArrowRight, Loader2 } from "lucide-react";

const STEPS = [
  { key: "company", label: "Şirket Ayarları", icon: Building2 },
  { key: "product", label: "İlk Ürün", icon: Package },
  { key: "invite", label: "Ekip Davet", icon: UserPlus },
  { key: "partner", label: "Partner (Opsiyonel)", icon: Handshake },
];

export default function OnboardingWizard({ onComplete }) {
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState(0);
  const [state, setState] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  // Step forms
  const [company, setCompany] = useState({ company_name: "", currency: "TRY", timezone: "Europe/Istanbul" });
  const [product, setProduct] = useState({ title: "", type: "accommodation", description: "" });
  const [invite, setInvite] = useState({ email: "", name: "", role: "agent" });
  const [partner, setPartner] = useState({ partner_name: "", partner_type: "agency" });

  useEffect(() => {
    loadState();
  }, []);

  const loadState = async () => {
    try {
      const res = await api.get("/onboarding/state");
      setState(res.data);
      // Find first incomplete step
      const steps = res.data?.steps || {};
      const firstIncomplete = STEPS.findIndex((s) => !steps[s.key]);
      if (firstIncomplete >= 0) setCurrentStep(firstIncomplete);
    } catch (err) {
      // Legacy tenant, skip wizard
      if (onComplete) onComplete();
    } finally {
      setLoading(false);
    }
  };

  const handleStepSubmit = async () => {
    const step = STEPS[currentStep];
    setSaving(true);
    setError("");
    try {
      let payload;
      switch (step.key) {
        case "company": payload = company; break;
        case "product": payload = product; break;
        case "invite": payload = invite; break;
        case "partner": payload = partner; break;
        default: payload = {};
      }
      const res = await api.put(`/onboarding/steps/${step.key}`, payload);
      setState(res.data);

      if (currentStep < STEPS.length - 1) {
        setCurrentStep(currentStep + 1);
      }
    } catch (err) {
      const msg = err?.response?.data?.error?.message || err?.response?.data?.detail || "Bir hata oluştu.";
      setError(msg);
    } finally {
      setSaving(false);
    }
  };

  const handleComplete = async () => {
    setSaving(true);
    try {
      await api.post("/onboarding/complete");
      if (onComplete) onComplete();
      navigate("/app", { replace: true });
    } catch {
      if (onComplete) onComplete();
    } finally {
      setSaving(false);
    }
  };

  const handleSkip = () => {
    if (currentStep < STEPS.length - 1) {
      setCurrentStep(currentStep + 1);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-blue-50 dark:from-slate-950 dark:to-slate-900">
        <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
      </div>
    );
  }

  // Already completed
  if (state?.completed_at || state?.completed) {
    if (onComplete) onComplete();
    return null;
  }

  const step = STEPS[currentStep];
  const StepIcon = step.icon;
  const steps = state?.steps || {};

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50 dark:from-slate-950 dark:to-slate-900 flex items-center justify-center p-4" data-testid="onboarding-wizard">
      <div className="w-full max-w-xl">
        {/* Progress */}
        <div className="flex items-center justify-center gap-2 mb-8">
          {STEPS.map((s, i) => (
            <div key={s.key} className="flex items-center gap-2">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium transition-all ${
                  steps[s.key]
                    ? "bg-green-500 text-white"
                    : i === currentStep
                    ? "bg-blue-500 text-white"
                    : "bg-gray-200 dark:bg-gray-700 text-gray-500"
                }`}
              >
                {steps[s.key] ? <Check className="h-4 w-4" /> : i + 1}
              </div>
              {i < STEPS.length - 1 && <div className="w-8 h-0.5 bg-gray-200 dark:bg-gray-700" />}
            </div>
          ))}
        </div>

        <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-xl border p-8">
          <div className="flex items-center gap-3 mb-6">
            <div className="h-10 w-10 rounded-xl bg-blue-100 dark:bg-blue-900 flex items-center justify-center">
              <StepIcon className="h-5 w-5 text-blue-600" />
            </div>
            <div>
              <h2 className="text-xl font-bold">Adım {currentStep + 1}: {step.label}</h2>
              <p className="text-sm text-muted-foreground">Hızlıca başlamak için bilgilerinizi girin</p>
            </div>
          </div>

          {error && (
            <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700 mb-4">{error}</div>
          )}

          {/* Step content */}
          {step.key === "company" && (
            <div className="space-y-4">
              <div><Label>Şirket Adı</Label><Input value={company.company_name} onChange={(e) => setCompany({ ...company, company_name: e.target.value })} placeholder="Şirketiniz" data-testid="wizard-company-name" /></div>
              <div><Label>Para Birimi</Label>
                <select className="w-full h-10 rounded-lg border px-3 text-sm bg-background" value={company.currency} onChange={(e) => setCompany({ ...company, currency: e.target.value })}>
                  <option value="TRY">TRY - Türk Lirası</option>
                  <option value="EUR">EUR - Euro</option>
                  <option value="USD">USD - Dolar</option>
                </select>
              </div>
            </div>
          )}

          {step.key === "product" && (
            <div className="space-y-4">
              <div><Label>Ürün Adı</Label><Input value={product.title} onChange={(e) => setProduct({ ...product, title: e.target.value })} placeholder="Örn: Deluxe Oda" data-testid="wizard-product-title" /></div>
              <div><Label>Tür</Label>
                <select className="w-full h-10 rounded-lg border px-3 text-sm bg-background" value={product.type} onChange={(e) => setProduct({ ...product, type: e.target.value })}>
                  <option value="accommodation">Konaklama</option>
                  <option value="tour">Tur</option>
                  <option value="activity">Aktivite</option>
                  <option value="transfer">Transfer</option>
                </select>
              </div>
              <div><Label>Açıklama (opsiyonel)</Label><Input value={product.description} onChange={(e) => setProduct({ ...product, description: e.target.value })} placeholder="Kısa açıklama" /></div>
            </div>
          )}

          {step.key === "invite" && (
            <div className="space-y-4">
              <div><Label>Ad Soyad</Label><Input value={invite.name} onChange={(e) => setInvite({ ...invite, name: e.target.value })} placeholder="Ekip üyesinin adı" data-testid="wizard-invite-name" /></div>
              <div><Label>E-posta</Label><Input type="email" value={invite.email} onChange={(e) => setInvite({ ...invite, email: e.target.value })} placeholder="ornek@sirket.com" data-testid="wizard-invite-email" /></div>
              <div><Label>Rol</Label>
                <select className="w-full h-10 rounded-lg border px-3 text-sm bg-background" value={invite.role} onChange={(e) => setInvite({ ...invite, role: e.target.value })}>
                  <option value="agent">Ajan</option>
                  <option value="super_admin">Yönetici</option>
                </select>
              </div>
            </div>
          )}

          {step.key === "partner" && (
            <div className="space-y-4">
              <p className="text-sm text-muted-foreground">Bu adım opsiyoneldir, daha sonra da yapabilirsiniz.</p>
              <div><Label>Partner Adı</Label><Input value={partner.partner_name} onChange={(e) => setPartner({ ...partner, partner_name: e.target.value })} placeholder="Partner şirket adı" data-testid="wizard-partner-name" /></div>
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center justify-between mt-8">
            <div>
              {step.key === "partner" && (
                <Button variant="ghost" onClick={handleComplete} disabled={saving} data-testid="wizard-skip-finish">
                  Atla ve Bitir
                </Button>
              )}
              {step.key === "invite" && (
                <Button variant="ghost" onClick={handleSkip} disabled={saving}>
                  Atla
                </Button>
              )}
            </div>
            <div className="flex gap-2">
              {currentStep === STEPS.length - 1 ? (
                <Button onClick={handleComplete} disabled={saving} data-testid="wizard-complete">
                  {saving ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
                  Tamamla <ArrowRight className="h-4 w-4 ml-1" />
                </Button>
              ) : (
                <Button onClick={handleStepSubmit} disabled={saving} data-testid="wizard-next">
                  {saving ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
                  Devam <ArrowRight className="h-4 w-4 ml-1" />
                </Button>
              )}
            </div>
          </div>
        </div>

        {/* Trial info */}
        {state?.trial && (
          <div className="text-center mt-4 text-sm text-muted-foreground">
            Deneme süreniz: {state.trial.days_remaining} gün kaldı
          </div>
        )}
      </div>
    </div>
  );
}
