import React, { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { CheckCircle2, Sparkles } from "lucide-react";

import { api } from "../../lib/api";
import { useLogin } from "../../hooks/useAuth";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { useSeo } from "../../hooks/useSeo";

const PAID_PLANS = [
  { key: "starter", label: "Starter", price: "₺990 / ay", desc: "Küçük acenteler için" },
  { key: "pro", label: "Pro", price: "₺2.490 / ay", desc: "Büyüyen acenteler için" },
  { key: "enterprise", label: "Enterprise", price: "₺6.990 / ay", desc: "Büyük operasyonlar için" },
];

export default function SignupPage() {
  const navigate = useNavigate();
  const loginMutation = useLogin();
  const [searchParams] = useSearchParams();
  const [form, setForm] = useState({
    company_name: "",
    admin_name: "",
    email: "",
    password: "",
    plan: "trial",
    billing_cycle: "monthly",
  });
  const [selectedPlan, setSelectedPlan] = useState("pro");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useSeo({
    title: "14 gün ücretsiz demo hesap oluştur",
    description: "Trial hesabınızı açın, 14 gün ücretsiz deneyin ve turizm operasyonunuzu tek panelden test edin.",
    canonicalPath: "/signup",
    type: "website",
  });

  const preferredPlan = useMemo(() => {
    const queryPlan = searchParams.get("selectedPlan") || searchParams.get("plan") || "pro";
    return PAID_PLANS.some((plan) => plan.key === queryPlan) ? queryPlan : "pro";
  }, [searchParams]);

  useEffect(() => {
    setSelectedPlan(preferredPlan);
    setForm((prev) => ({ ...prev, plan: "trial" }));
  }, [preferredPlan]);

  const handleChange = (event) => {
    setForm((prev) => ({ ...prev, [event.target.name]: event.target.value }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");
    setLoading(true);

    try {
      await api.post("/onboarding/signup", { ...form, plan: "trial" });

      const loginResp = await loginMutation.mutateAsync({
        email: form.email,
        password: form.password,
      });

      if (!loginResp?.user) {
        throw new Error("Oturum başlatılamadı. Lütfen giriş ekranından tekrar deneyin.");
      }

      navigate("/app");
    } catch (err) {
      const message = err?.response?.data?.error?.message || err?.response?.data?.detail || err?.message || "Kayıt başarısız.";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[linear-gradient(180deg,#fdfbf7_0%,#fff4ec_42%,#f7faf9_100%)] px-4 py-10" style={{ fontFamily: "Inter, sans-serif" }} data-testid="signup-page">
      <div className="mx-auto grid max-w-6xl gap-8 lg:grid-cols-[0.9fr_1.1fr]">
        <section className="rounded-[2rem] bg-[#264653] p-8 text-white shadow-[0_30px_120px_rgba(38,70,83,0.20)] lg:p-10" data-testid="signup-sidebar">
          <div className="inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.24em] text-[#e9c46a]" data-testid="signup-sidebar-badge">
            <Sparkles className="h-4 w-4" />
            Trial ile başlıyorsunuz
          </div>

          <h1 className="mt-6 text-4xl font-extrabold tracking-[-0.03em] text-white" style={{ fontFamily: "Manrope, Inter, sans-serif" }} data-testid="signup-title">
            14 gün ücretsiz deneyin, sonra karar verin
          </h1>
          <p className="mt-4 text-base leading-7 text-white/80" data-testid="signup-subtitle">
            Hesabınız Trial planı ile açılır. 100 rezervasyon, 2 kullanıcı ve tüm çekirdek özelliklerle gerçek akışınızı test edebilirsiniz.
          </p>

          <div className="mt-8 space-y-3" data-testid="signup-trial-points">
            {[
              "14 gün boyunca aktif trial",
              "100 rezervasyon limiti",
              "2 kullanıcı ile ekip testi",
              "Trial sonunda planınızı seçebilirsiniz",
            ].map((item, index) => (
              <div key={item} className="flex items-center gap-3 rounded-2xl bg-white/10 px-4 py-3" data-testid={`signup-trial-point-${index + 1}`}>
                <CheckCircle2 className="h-4 w-4 text-[#e9c46a]" />
                <span className="text-sm text-white/90">{item}</span>
              </div>
            ))}
          </div>

          <div className="mt-8 rounded-[1.5rem] bg-white/10 p-5" data-testid="signup-selected-plan-summary">
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[#e9c46a]" data-testid="signup-selected-plan-eyebrow">Trial sonrası hedef plan</p>
            <p className="mt-3 text-2xl font-extrabold tracking-[-0.03em]" style={{ fontFamily: "Manrope, Inter, sans-serif" }} data-testid="signup-selected-plan-title">
              {PAID_PLANS.find((plan) => plan.key === selectedPlan)?.label || "Pro"}
            </p>
            <p className="mt-2 text-sm text-white/80" data-testid="signup-selected-plan-description">
              İsterseniz bu tercihi şimdi değiştirin; hesabınız yine Trial olarak açılacak.
            </p>
          </div>
        </section>

        <section className="rounded-[2rem] border border-[#f1ddd0] bg-white/90 p-8 shadow-[0_30px_120px_rgba(38,70,83,0.10)] lg:p-10" data-testid="signup-form-section">
          <div className="mb-8">
            <p className="text-sm font-semibold uppercase tracking-[0.22em] text-[#d16024]" data-testid="signup-form-eyebrow">Demo hesap oluştur</p>
            <h2 className="mt-2 text-4xl font-extrabold tracking-[-0.03em] text-slate-900" style={{ fontFamily: "Manrope, Inter, sans-serif" }} data-testid="signup-form-title">
              Hemen Başla
            </h2>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5" data-testid="signup-form">
            {error ? (
              <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700" data-testid="signup-error">
                {error}
              </div>
            ) : null}

            <div className="grid gap-5 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="company_name">Şirket Adı</Label>
                <Input id="company_name" name="company_name" value={form.company_name} onChange={handleChange} required minLength={2} placeholder="Acentenizin adı" data-testid="signup-company" />
              </div>

              <div className="space-y-2">
                <Label htmlFor="admin_name">Adınız Soyadınız</Label>
                <Input id="admin_name" name="admin_name" value={form.admin_name} onChange={handleChange} required minLength={2} placeholder="Ad Soyad" data-testid="signup-name" />
              </div>
            </div>

            <div className="grid gap-5 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="email">E-posta</Label>
                <Input id="email" name="email" type="email" value={form.email} onChange={handleChange} required placeholder="ornek@acenta.com" data-testid="signup-email" />
              </div>

              <div className="space-y-2">
                <Label htmlFor="password">Şifre</Label>
                <Input id="password" name="password" type="password" value={form.password} onChange={handleChange} required minLength={6} placeholder="En az 6 karakter" data-testid="signup-password" />
              </div>
            </div>

            <div className="space-y-3" data-testid="signup-plan-picker">
              <div className="flex items-center justify-between gap-3">
                <Label>Trial sonrası ilginizi çeken plan</Label>
                <span className="text-xs font-medium text-slate-500" data-testid="signup-plan-picker-note">Hesap yine Trial olarak açılır</span>
              </div>

              <div className="grid gap-3 md:grid-cols-3">
                {PAID_PLANS.map((plan) => (
                  <button
                    key={plan.key}
                    type="button"
                    onClick={() => setSelectedPlan(plan.key)}
                    className={`rounded-[1.25rem] border p-4 text-left transition-all ${selectedPlan === plan.key ? "border-[#f3722c] bg-[#fff4ec] shadow-sm" : "border-slate-200 hover:border-[#f1c1a3]"}`}
                    data-testid={`signup-selected-plan-${plan.key}`}
                  >
                    <p className="text-sm font-semibold text-slate-900">{plan.label}</p>
                    <p className="mt-1 text-sm text-[#d16024]">{plan.price}</p>
                    <p className="mt-2 text-xs leading-5 text-slate-500">{plan.desc}</p>
                  </button>
                ))}
              </div>
            </div>

            <Button type="submit" className="h-12 w-full rounded-xl bg-[#f3722c] text-sm font-semibold text-white hover:bg-[#e05d1b]" disabled={loading || loginMutation.isPending} data-testid="signup-submit">
              {loading || loginMutation.isPending ? "Hesap oluşturuluyor..." : "Hemen Başla"}
            </Button>

            <p className="text-center text-sm text-slate-500" data-testid="signup-login-link-wrap">
              Zaten hesabınız var mı? <Link to="/login" className="font-semibold text-[#264653] hover:text-[#f3722c]" data-testid="signup-login-link">Giriş yapın</Link>
            </p>
          </form>
        </section>
      </div>
    </div>
  );
}