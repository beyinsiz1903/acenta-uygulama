import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { api, setToken, setUser } from "../../lib/api";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";

const PLANS = [
  { key: "starter", label: "Starter", desc: "Temel özellikler", price: "Ücretsiz Deneme" },
  { key: "pro", label: "Pro", desc: "Gelişmiş özellikler", price: "₺299/ay" },
  { key: "enterprise", label: "Enterprise", desc: "Tüm özellikler", price: "₺799/ay" },
];

export default function SignupPage() {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    company_name: "",
    admin_name: "",
    email: "",
    password: "",
    plan: "starter",
    billing_cycle: "monthly",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleChange = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const resp = await api.post("/onboarding/signup", form);
      const data = resp.data;
      setToken(data.access_token);
      setUser({
        id: data.user_id,
        email: form.email,
        name: form.admin_name,
        roles: ["super_admin"],
        organization_id: data.org_id,
        tenant_id: data.tenant_id,
      });
      // Store tenant_id for API calls
      try { localStorage.setItem("acenta_tenant_id", data.tenant_id); } catch {}
      navigate("/app");
    } catch (err) {
      const msg = err?.response?.data?.error?.message || err?.response?.data?.detail || "Kayıt başarısız.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50 dark:from-slate-950 dark:to-slate-900 flex items-center justify-center p-4">
      <div className="w-full max-w-lg">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-foreground">Hemen Başlayın</h1>
          <p className="text-muted-foreground mt-2">14 gün ücretsiz deneyin, kredi kartı gerekmez</p>
        </div>

        <form onSubmit={handleSubmit} className="bg-white dark:bg-slate-900 rounded-2xl shadow-xl border p-8 space-y-5" data-testid="signup-form">
          {error && (
            <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700" data-testid="signup-error">
              {error}
            </div>
          )}

          <div className="space-y-2">
            <Label htmlFor="company_name">Şirket Adı</Label>
            <Input id="company_name" name="company_name" value={form.company_name} onChange={handleChange} required minLength={2} placeholder="Şirketinizin adı" data-testid="signup-company" />
          </div>

          <div className="space-y-2">
            <Label htmlFor="admin_name">Adınız Soyadınız</Label>
            <Input id="admin_name" name="admin_name" value={form.admin_name} onChange={handleChange} required minLength={2} placeholder="Ad Soyad" data-testid="signup-name" />
          </div>

          <div className="space-y-2">
            <Label htmlFor="email">E-posta</Label>
            <Input id="email" name="email" type="email" value={form.email} onChange={handleChange} required placeholder="ornek@sirket.com" data-testid="signup-email" />
          </div>

          <div className="space-y-2">
            <Label htmlFor="password">Şifre</Label>
            <Input id="password" name="password" type="password" value={form.password} onChange={handleChange} required minLength={6} placeholder="En az 6 karakter" data-testid="signup-password" />
          </div>

          {/* Plan Selection */}
          <div className="space-y-2">
            <Label>Plan Seçimi</Label>
            <div className="grid grid-cols-3 gap-2">
              {PLANS.map((p) => (
                <button
                  key={p.key}
                  type="button"
                  onClick={() => setForm({ ...form, plan: p.key })}
                  className={`p-3 rounded-xl border-2 text-center transition-all ${
                    form.plan === p.key
                      ? "border-blue-500 bg-blue-50 dark:bg-blue-950"
                      : "border-border hover:border-blue-300"
                  }`}
                  data-testid={`plan-${p.key}`}
                >
                  <div className="font-semibold text-sm">{p.label}</div>
                  <div className="text-xs text-muted-foreground mt-1">{p.price}</div>
                </button>
              ))}
            </div>
          </div>

          {/* Billing cycle */}
          <div className="flex items-center gap-4">
            <Label>Ödeme Periyodu:</Label>
            <div className="flex gap-2">
              {["monthly", "yearly"].map((c) => (
                <button
                  key={c}
                  type="button"
                  onClick={() => setForm({ ...form, billing_cycle: c })}
                  className={`px-3 py-1.5 rounded-lg text-sm border transition-all ${
                    form.billing_cycle === c
                      ? "border-blue-500 bg-blue-50 dark:bg-blue-950 font-medium"
                      : "border-border hover:border-blue-300"
                  }`}
                >
                  {c === "monthly" ? "Aylık" : "Yıllık"}
                </button>
              ))}
            </div>
          </div>

          <Button type="submit" className="w-full h-11" disabled={loading} data-testid="signup-submit">
            {loading ? "Kayıt yapılıyor..." : "Ücretsiz Deneyin"}
          </Button>

          <p className="text-center text-sm text-muted-foreground">
            Zaten hesabınız var mı?{" "}
            <Link to="/login" className="text-blue-600 hover:underline">Giriş yapın</Link>
          </p>
        </form>
      </div>
    </div>
  );
}
