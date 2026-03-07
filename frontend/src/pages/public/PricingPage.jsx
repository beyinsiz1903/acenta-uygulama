import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../lib/api";
import { Button } from "../../components/ui/button";
import { Check } from "lucide-react";
import { LIMIT_LABELS, USAGE_ALLOWANCE_LABELS, formatEntitlementValue } from "../../lib/entitlementLabels";

const PLAN_PRICES = {
  starter: { monthly: "Ücretsiz Deneme", yearly: "Ücretsiz Deneme" },
  pro: { monthly: "₺299/ay", yearly: "₺2.990/yıl" },
  enterprise: { monthly: "₺799/ay", yearly: "₺7.990/yıl" },
};

const FEATURE_LABELS = {
  dashboard: "Dashboard",
  reservations: "Rezervasyonlar",
  crm: "CRM",
  inventory: "Müsaitlik",
  reports: "Raporlar",
  accounting: "Muhasebe",
  webpos: "WebPOS",
  partners: "Partnerler",
  b2b: "B2B Marketplace",
  ops: "Operasyon",
};

export default function PricingPage() {
  const [plans, setPlans] = useState([]);
  const [cycle, setCycle] = useState("monthly");

  useEffect(() => {
    api.get("/onboarding/plans").then((r) => setPlans(r.data.plans || [])).catch(() => {});
  }, []);

  const sortedPlans = [...plans].sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0));

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50 dark:from-slate-950 dark:to-slate-900 py-16 px-4">
      <div className="max-w-5xl mx-auto">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-foreground" data-testid="pricing-title">Fiyatlandırma</h1>
          <p className="text-lg text-muted-foreground mt-3">Her ölçekte işletme için doğru plan</p>

          <div className="flex justify-center mt-6 gap-2">
            {["monthly", "yearly"].map((c) => (
              <button
                key={c}
                onClick={() => setCycle(c)}
                data-testid={`pricing-cycle-${c}-button`}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                  cycle === c
                    ? "bg-blue-600 text-white shadow-lg"
                    : "bg-white dark:bg-slate-800 border hover:bg-blue-50"
                }`}
              >
                {c === "monthly" ? "Aylık" : "Yıllık (2 ay hediye)"}
              </button>
            ))}
          </div>
        </div>

        <div className="grid md:grid-cols-3 gap-6">
          {sortedPlans.map((plan, idx) => (
            <div
              key={plan.key || plan.name}
              className={`bg-white dark:bg-slate-900 rounded-2xl border-2 p-8 transition-all hover:shadow-xl ${
                idx === 1 ? "border-blue-500 relative" : "border-border"
              }`}
              data-testid={`pricing-plan-${plan.key || plan.name}`}
            >
              {idx === 1 && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-blue-500 text-white text-xs font-bold px-3 py-1 rounded-full">
                  Popüler
                </div>
              )}
              <h3 className="text-xl font-bold" data-testid={`pricing-plan-label-${plan.key || plan.name}`}>{plan.label}</h3>
              <div className="text-2xl font-bold mt-2 text-blue-600" data-testid={`pricing-plan-price-${plan.key || plan.name}`}>
                {PLAN_PRICES[plan.key || plan.name]?.[cycle] || "İletişime geçin"}
              </div>
              <p className="text-sm text-muted-foreground mt-1" data-testid={`pricing-plan-description-${plan.key || plan.name}`}>
                {plan.description || "14 gün ücretsiz deneme"}
              </p>

              <div className="mt-4 grid gap-2">
                {Object.entries(plan.limits || {}).map(([key, value]) => (
                  <div
                    key={key}
                    className="flex items-center justify-between rounded-lg bg-blue-50/70 px-3 py-2 text-xs text-slate-700"
                    data-testid={`pricing-plan-limit-${plan.key || plan.name}-${key.replace(/\./g, "-")}`}
                  >
                    <span>{LIMIT_LABELS[key] || key}</span>
                    <span className="font-semibold">{formatEntitlementValue(value, key === "reservations.monthly" ? "/ay" : "")}</span>
                  </div>
                ))}
              </div>

              <ul className="mt-6 space-y-3">
                {plan.features.map((f) => (
                  <li key={f} className="flex items-center gap-2 text-sm">
                    <Check className="h-4 w-4 text-green-500 shrink-0" />
                    <span>{FEATURE_LABELS[f] || f}</span>
                  </li>
                ))}
              </ul>

              <div className="mt-6 rounded-xl border border-dashed border-border/80 p-4" data-testid={`pricing-plan-usage-${plan.key || plan.name}`}>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">Usage allowances</p>
                <div className="mt-3 space-y-2">
                  {Object.entries(plan.usage_allowances || {}).slice(0, 3).map(([key, value]) => (
                    <div key={key} className="flex items-center justify-between text-xs text-muted-foreground">
                      <span>{USAGE_ALLOWANCE_LABELS[key] || key}</span>
                      <span className="font-medium text-foreground">{formatEntitlementValue(value, "/ay")}</span>
                    </div>
                  ))}
                </div>
              </div>

              <Link to={`/signup?plan=${plan.key || plan.name}`}>
                <Button className="w-full mt-8 h-11" variant={idx === 1 ? "default" : "outline"} data-testid={`pricing-plan-cta-${plan.key || plan.name}`}>
                  Ücretsiz Başla
                </Button>
              </Link>
            </div>
          ))}
        </div>

        <div className="text-center mt-12">
          <Link to="/login" className="text-sm text-muted-foreground hover:text-blue-600">
            Zaten hesabınız var mı? Giriş yapın →
          </Link>
        </div>
      </div>
    </div>
  );
}
