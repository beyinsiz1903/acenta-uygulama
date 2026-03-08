import React from "react";
import { Link } from "react-router-dom";
import { BadgeCheck, LockKeyhole, ShieldCheck } from "lucide-react";

import { Button } from "./ui/button";

const EXPIRED_PLANS = [
  { key: "starter", label: "Starter", price: "₺990 / ay" },
  { key: "pro", label: "Pro", price: "₺2.490 / ay", recommended: true },
  { key: "enterprise", label: "Enterprise", price: "₺6.990 / ay" },
];

export default function TrialExpiredGate() {
  return (
    <div className="fixed inset-0 z-[120] bg-[radial-gradient(circle_at_top,rgba(243,114,44,0.10),transparent_28%),linear-gradient(180deg,rgba(250,247,243,0.97)_0%,rgba(255,244,235,0.98)_46%,rgba(246,251,250,0.98)_100%)] backdrop-blur-sm" data-testid="trial-expired-gate">
      <div className="flex min-h-screen items-center justify-center px-4 py-8">
        <div className="w-full max-w-6xl overflow-hidden rounded-[2rem] border border-[#ecdccf] bg-white/95 shadow-[0_40px_160px_rgba(38,70,83,0.14)]" data-testid="trial-expired-card">
          <div className="grid gap-8 p-8 lg:grid-cols-[0.88fr_1.12fr] lg:p-12">
            <section className="space-y-6" data-testid="trial-expired-copy-section">
              <div className="inline-flex items-center gap-2 rounded-full border border-[#f3d4c1] bg-[#fff4ec] px-4 py-2 text-xs font-semibold uppercase tracking-[0.24em] text-[#d16024]" data-testid="trial-expired-badge">
                <LockKeyhole className="h-4 w-4" />
                Trial sona erdi
              </div>

              <div className="space-y-4">
                <h1 className="text-4xl font-extrabold tracking-[-0.04em] text-slate-900 sm:text-5xl" style={{ fontFamily: "Manrope, Inter, sans-serif" }} data-testid="trial-expired-title">
                  Deneme süreniz sona erdi
                </h1>
                <p className="max-w-xl text-base leading-7 text-slate-600 md:text-lg" data-testid="trial-expired-subtitle">
                  Syroce'u kullanmaya devam etmek için bir plan seçin. Tüm verileriniz korunuyor.
                </p>
              </div>

              <div className="grid gap-3" data-testid="trial-expired-benefits">
                {[
                  "Tüm verileriniz korunuyor",
                  "Aynı hesapla kaldığınız yerden devam edersiniz",
                  "Doğru planı seçip hemen kullanıma dönersiniz",
                ].map((item, index) => (
                  <div key={item} className="flex items-center gap-3 rounded-2xl bg-[#f8fbfb] px-4 py-4" data-testid={`trial-expired-benefit-${index + 1}`}>
                    <ShieldCheck className="h-4 w-4 text-[#2a9d8f]" />
                    <span className="text-sm font-medium text-slate-800">{item}</span>
                  </div>
                ))}
              </div>
            </section>

            <section className="space-y-4" data-testid="trial-expired-plans-section">
              <div>
                <p className="text-sm font-semibold uppercase tracking-[0.24em] text-[#264653]" data-testid="trial-expired-plans-eyebrow">
                  Planlar
                </p>
              </div>

              <div className="grid gap-4 md:grid-cols-3" data-testid="trial-expired-plan-grid">
                {EXPIRED_PLANS.map((plan) => (
                  <article key={plan.key} className={`relative rounded-[1.75rem] border p-5 shadow-[0_20px_60px_rgba(38,70,83,0.08)] ${plan.recommended ? "border-[#f3722c] bg-[#fff8f2]" : "border-slate-200 bg-white"}`} data-testid={`trial-expired-plan-${plan.key}`}>
                    {plan.recommended ? (
                      <div className="absolute right-4 top-4 rounded-full bg-[#f3722c] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-white" data-testid={`trial-expired-plan-badge-${plan.key}`}>
                        Önerilen
                      </div>
                    ) : null}
                    <div className="space-y-4">
                      <div>
                        <h2 className="text-2xl font-extrabold tracking-[-0.03em] text-slate-900" style={{ fontFamily: "Manrope, Inter, sans-serif" }} data-testid={`trial-expired-plan-title-${plan.key}`}>
                          {plan.label}
                        </h2>
                        <p className="mt-2 text-sm font-semibold text-[#d16024]" data-testid={`trial-expired-plan-price-${plan.key}`}>
                          {plan.price}
                        </p>
                      </div>

                      <Button asChild className={`h-11 w-full rounded-xl text-sm font-semibold ${plan.recommended ? "bg-[#f3722c] text-white hover:bg-[#e05d1b]" : "bg-[#264653] text-white hover:bg-[#1f3742]"}`} data-testid={`trial-expired-plan-cta-${plan.key}`}>
                        <Link to="/pricing">
                          Plan Seç
                          <BadgeCheck className="ml-2 h-4 w-4" />
                        </Link>
                      </Button>
                    </div>
                  </article>
                ))}
              </div>
            </section>
          </div>
        </div>
      </div>
    </div>
  );
}