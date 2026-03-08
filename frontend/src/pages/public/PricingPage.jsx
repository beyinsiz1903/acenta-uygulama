import React, { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, BadgeCheck, CheckCircle2, Clock3, Sparkles, Users } from "lucide-react";

import { Button } from "../../components/ui/button";
import { api } from "../../lib/api";
import { useSeo } from "../../hooks/useSeo";

const PAID_PLAN_ORDER = ["starter", "pro", "enterprise"];

const STATIC_PLANS = {
  starter: {
    key: "starter",
    label: "Starter",
    audience: "Küçük acenteler için",
    pricing: { monthly: 990 },
    description: "Excel ile büyümeye çalışan ekipler için net başlangıç paketi.",
    features: [
      "100 rezervasyon",
      "3 kullanıcı",
      "Temel raporlar",
      "Google Sheets entegrasyonu",
    ],
  },
  pro: {
    key: "pro",
    label: "Pro",
    audience: "Önerilen plan",
    pricing: { monthly: 2490 },
    description: "Satış ve operasyon akışını tek panelde toplamak isteyen büyüyen acenteler için.",
    features: [
      "500 rezervasyon",
      "10 kullanıcı",
      "Tüm raporlar",
      "Export ve entegrasyonlar",
    ],
    is_popular: true,
  },
  enterprise: {
    key: "enterprise",
    label: "Enterprise",
    audience: "Büyük operasyonlar için",
    pricing: { monthly: 6990 },
    description: "Yüksek hacim, API erişimi ve özel entegrasyon gerektiren ekipler için.",
    features: [
      "Sınırsız rezervasyon",
      "Sınırsız kullanıcı",
      "API erişimi",
      "Özel entegrasyon",
    ],
  },
};

const HERO_POINTS = [
  {
    icon: Clock3,
    title: "14 gün trial",
    desc: "Kredi kartı olmadan başlayın, gerçek akışınızı deneyin.",
  },
  {
    icon: Users,
    title: "100 rezervasyon",
    desc: "Trial içinde canlı kullanım senaryonuzu güvenle test edin.",
  },
  {
    icon: BadgeCheck,
    title: "Net yükseltme",
    desc: "İşiniz büyüdükçe doğru planı seçip kaldığınız yerden devam edin.",
  },
];

const TRUST_POINTS = [
  "Dakikalar içinde trial hesabı açın",
  "Rezervasyon, müşteri ve operasyonu tek panelde yönetin",
  "İlk kullanım için teknik kurulum zorunlu değil",
];

function formatMonthlyPrice(pricing = {}) {
  if (typeof pricing?.monthly === "number") {
    return `₺${pricing.monthly.toLocaleString("tr-TR")}`;
  }

  return "İletişime geçin";
}

export default function PricingPage() {
  const [plans, setPlans] = useState([]);

  useSeo({
    title: "Acenteniz için doğru planı seçin",
    description: "Starter, Pro ve Enterprise planlarını karşılaştırın. 14 gün ücretsiz deneyin ve Syroce ile operasyonu tek panelde yönetin.",
    canonicalPath: "/pricing",
    type: "website",
  });

  useEffect(() => {
    api
      .get("/onboarding/plans")
      .then((response) => setPlans(response.data?.plans || []))
      .catch(() => setPlans([]));
  }, []);

  const publicPlans = useMemo(() => {
    const fetchedMap = new Map((plans || []).map((plan) => [plan.key || plan.name, plan]));

    return PAID_PLAN_ORDER.map((key) => {
      const fallbackPlan = STATIC_PLANS[key];
      const fetchedPlan = fetchedMap.get(key) || {};

      return {
        ...fallbackPlan,
        ...fetchedPlan,
        key,
        label: fetchedPlan.label || fallbackPlan.label,
        audience: fallbackPlan.audience,
        description: fallbackPlan.description,
        pricing: fetchedPlan.pricing || fallbackPlan.pricing,
        features: fallbackPlan.features,
        is_popular: key === "pro",
      };
    });
  }, [plans]);

  return (
    <div
      className="min-h-screen bg-[linear-gradient(180deg,#fbfaf7_0%,#fff4eb_42%,#f6fbfa_100%)] text-slate-900"
      style={{ fontFamily: "Inter, sans-serif" }}
      data-testid="pricing-page"
    >
      <div className="mx-auto flex max-w-7xl flex-col gap-16 px-4 py-12 sm:px-6 lg:px-8 lg:py-20">
        <section
          className="grid gap-8 overflow-hidden rounded-[2.25rem] border border-[#f1ddcf] bg-white/90 p-8 shadow-[0_30px_120px_rgba(38,70,83,0.10)] backdrop-blur lg:grid-cols-[1.1fr_0.9fr] lg:p-12"
          data-testid="pricing-hero-section"
        >
          <div className="space-y-6">
            <div
              className="inline-flex items-center gap-2 rounded-full border border-[#f6d2bd] bg-[#fff4ec] px-4 py-2 text-xs font-semibold uppercase tracking-[0.24em] text-[#d16024]"
              data-testid="pricing-hero-badge"
            >
              <Sparkles className="h-4 w-4" />
              14 Gün Ücretsiz Deneyin
            </div>

            <div className="space-y-4">
              <p className="text-sm font-semibold uppercase tracking-[0.28em] text-[#264653]" data-testid="pricing-hero-eyebrow">
                Syroce Fiyatlandırma
              </p>
              <h1
                className="text-4xl font-extrabold leading-[1.02] tracking-[-0.04em] text-slate-900 sm:text-5xl lg:text-6xl"
                style={{ fontFamily: "Manrope, Inter, sans-serif" }}
                data-testid="pricing-title"
              >
                Acenteniz için doğru planı seçin
              </h1>
              <p className="max-w-2xl text-base leading-7 text-slate-600 md:text-lg" data-testid="pricing-subtitle">
                Acentenizi Excel'den kurtarın. Rezervasyon, müşteri ve operasyon süreçlerini tek panelde yönetin; 14 gün boyunca ücretsiz deneyin.
              </p>
            </div>

            <div className="flex flex-wrap gap-3" data-testid="pricing-hero-cta-group">
              <Button asChild className="h-12 rounded-xl bg-[#f3722c] px-6 text-sm font-semibold text-white hover:bg-[#e05d1b]" data-testid="pricing-hero-primary-cta">
                <Link to="/signup?plan=trial&selectedPlan=pro">
                  14 Gün Ücretsiz Dene
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Link>
              </Button>
              <Button asChild variant="outline" className="h-12 rounded-xl border-[#264653] px-6 text-sm font-semibold text-[#264653] hover:bg-[#fdf8f2]" data-testid="pricing-hero-secondary-cta">
                <Link to="/demo">Demo sayfasını gör</Link>
              </Button>
            </div>

            <div className="grid gap-3 sm:grid-cols-3" data-testid="pricing-hero-points">
              {HERO_POINTS.map((item, index) => (
                <article key={item.title} className="rounded-2xl border border-slate-200 bg-[#fbfcfc] p-4" data-testid={`pricing-hero-point-${index + 1}`}>
                  <item.icon className="h-5 w-5 text-[#2a9d8f]" />
                  <p className="mt-3 text-sm font-semibold text-slate-900" data-testid={`pricing-hero-point-title-${index + 1}`}>{item.title}</p>
                  <p className="mt-1 text-sm leading-6 text-slate-600" data-testid={`pricing-hero-point-text-${index + 1}`}>{item.desc}</p>
                </article>
              ))}
            </div>
          </div>

          <div className="relative overflow-hidden rounded-[1.9rem] bg-[#264653] p-6 text-white" data-testid="pricing-trial-panel">
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(233,196,106,0.24),transparent_38%),radial-gradient(circle_at_bottom_left,rgba(42,157,143,0.24),transparent_36%)]" />
            <div className="relative space-y-5">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[#e9c46a]" data-testid="pricing-trial-panel-eyebrow">
                  Trial ile başlarsınız
                </p>
                <h2 className="mt-3 text-3xl font-extrabold tracking-[-0.03em]" style={{ fontFamily: "Manrope, Inter, sans-serif" }} data-testid="pricing-trial-panel-title">
                  Önce deneyin, sonra paket seçin
                </h2>
              </div>

              <div className="grid gap-3" data-testid="pricing-trial-panel-list">
                {[
                  "14 günlük trial erişimi",
                  "100 rezervasyon hakkı",
                  "2 kullanıcı ile ekip testi",
                  "Tüm çekirdek özellikler açık",
                ].map((item, index) => (
                  <div key={item} className="flex items-center gap-3 rounded-2xl bg-white/10 px-4 py-3" data-testid={`pricing-trial-panel-item-${index + 1}`}>
                    <CheckCircle2 className="h-4 w-4 text-[#e9c46a]" />
                    <span className="text-sm text-white/90">{item}</span>
                  </div>
                ))}
              </div>

              <div className="rounded-[1.5rem] border border-white/10 bg-white/10 p-5" data-testid="pricing-trial-panel-footer">
                <p className="text-sm font-medium text-white/70" data-testid="pricing-trial-panel-footer-label">Bu sayfa ne için?</p>
                <p className="mt-2 text-base font-semibold text-white" data-testid="pricing-trial-panel-footer-text">
                  Demo hesabınızı açıp hangi paketin işinize uyduğunu net şekilde görün.
                </p>
              </div>
            </div>
          </div>
        </section>

        <section className="space-y-8" data-testid="pricing-cards-section">
          <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.22em] text-[#d16024]" data-testid="pricing-section-eyebrow">
                Planlar
              </p>
              <h2 className="mt-2 text-4xl font-extrabold tracking-[-0.03em] text-slate-900" style={{ fontFamily: "Manrope, Inter, sans-serif" }} data-testid="pricing-section-title">
                Küçük ekibiniz de büyük operasyonunuz da aynı panelde büyüsün
              </h2>
            </div>
            <p className="max-w-xl text-sm leading-6 text-slate-600" data-testid="pricing-section-description">
              İhtiyacınıza göre başlayın; işiniz büyüdükçe paketiniz de sizinle birlikte büyüsün.
            </p>
          </div>

          <div className="grid gap-6 lg:grid-cols-3" data-testid="pricing-plan-grid">
            {publicPlans.map((plan) => (
              <article
                key={plan.key}
                className={`relative flex h-full flex-col overflow-hidden rounded-[1.9rem] border p-7 shadow-[0_25px_80px_rgba(38,70,83,0.08)] transition-transform duration-300 hover:-translate-y-1 ${plan.is_popular ? "border-[#f3722c] bg-[#fff8f2]" : "border-white bg-white/95"}`}
                data-testid={`pricing-plan-${plan.key}`}
              >
                {plan.is_popular ? (
                  <div className="absolute right-5 top-5 rounded-full bg-[#f3722c] px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-white" data-testid={`pricing-plan-badge-${plan.key}`}>
                    Önerilen
                  </div>
                ) : null}

                <div className="space-y-5">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[#2a9d8f]" data-testid={`pricing-plan-audience-${plan.key}`}>
                      {plan.audience}
                    </p>
                    <h3 className="mt-3 text-3xl font-extrabold tracking-[-0.03em] text-slate-900" style={{ fontFamily: "Manrope, Inter, sans-serif" }} data-testid={`pricing-plan-label-${plan.key}`}>
                      {plan.label}
                    </h3>
                    <p className="mt-2 text-sm leading-6 text-slate-600" data-testid={`pricing-plan-description-${plan.key}`}>
                      {plan.description}
                    </p>
                  </div>

                  <div className="flex items-end gap-2" data-testid={`pricing-plan-price-wrap-${plan.key}`}>
                    <span className="text-4xl font-extrabold tracking-[-0.04em] text-slate-900" style={{ fontFamily: "Manrope, Inter, sans-serif" }} data-testid={`pricing-plan-price-${plan.key}`}>
                      {formatMonthlyPrice(plan.pricing)}
                    </span>
                    <span className="pb-1 text-sm font-medium text-slate-500" data-testid={`pricing-plan-period-${plan.key}`}>
                      / ay
                    </span>
                  </div>

                  <ul className="grid gap-3" data-testid={`pricing-plan-feature-list-${plan.key}`}>
                    {plan.features.map((feature, index) => (
                      <li key={feature} className="flex items-start gap-3 rounded-2xl bg-slate-50 px-4 py-3 text-sm text-slate-700" data-testid={`pricing-plan-feature-${plan.key}-${index + 1}`}>
                        <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-[#f3722c]" />
                        <span>{feature}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                <div className="mt-6 pt-2">
                  <Button asChild className={`h-12 w-full rounded-xl text-sm font-semibold ${plan.is_popular ? "bg-[#f3722c] text-white hover:bg-[#e05d1b]" : "bg-[#264653] text-white hover:bg-[#1f3742]"}`} data-testid={`pricing-plan-cta-${plan.key}`}>
                    <Link to={`/signup?plan=trial&selectedPlan=${plan.key}`}>14 Gün Ücretsiz Dene</Link>
                  </Button>
                </div>
              </article>
            ))}
          </div>
        </section>

        <section className="grid gap-6 lg:grid-cols-[1.05fr_0.95fr]" data-testid="pricing-social-proof-section">
          <article className="rounded-[2rem] bg-[#264653] px-8 py-10 text-white shadow-[0_25px_80px_rgba(38,70,83,0.12)] lg:px-10" data-testid="pricing-social-proof-card">
            <p className="text-sm font-semibold uppercase tracking-[0.24em] text-[#e9c46a]" data-testid="pricing-social-proof-eyebrow">
              Sosyal kanıt
            </p>
            <h2 className="mt-3 text-4xl font-extrabold tracking-[-0.03em]" style={{ fontFamily: "Manrope, Inter, sans-serif" }} data-testid="pricing-social-proof-title">
              Turizm acenteleri Syroce ile operasyon süreçlerini %40 daha hızlı yönetiyor.
            </h2>
            <p className="mt-4 max-w-2xl text-base leading-7 text-white/80" data-testid="pricing-social-proof-text">
              Excel, WhatsApp ve dağınık takip araçları yerine tek panel kullanan ekipler daha hızlı cevap verir, daha az iş kaybı yaşar ve daha net rapor alır.
            </p>
          </article>

          <article className="rounded-[2rem] border border-[#dbe8e6] bg-white/90 p-8 shadow-[0_25px_80px_rgba(38,70,83,0.08)]" data-testid="pricing-trust-points-card">
            <p className="text-sm font-semibold uppercase tracking-[0.22em] text-[#2a9d8f]" data-testid="pricing-trust-points-eyebrow">
              Neden şimdi?
            </p>
            <div className="mt-6 grid gap-4" data-testid="pricing-trust-points-list">
              {TRUST_POINTS.map((item, index) => (
                <div key={item} className="rounded-2xl bg-[#f7fbfb] px-4 py-4" data-testid={`pricing-trust-point-${index + 1}`}>
                  <p className="text-sm font-semibold leading-6 text-slate-900" data-testid={`pricing-trust-point-text-${index + 1}`}>{item}</p>
                </div>
              ))}
            </div>
          </article>
        </section>

        <section className="rounded-[2rem] border border-[#e4eceb] bg-white/90 p-8 shadow-[0_25px_80px_rgba(38,70,83,0.08)] lg:p-10" data-testid="pricing-conversion-section">
          <div className="grid gap-6 lg:grid-cols-[0.95fr_1.05fr] lg:items-center">
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.22em] text-[#d16024]" data-testid="pricing-conversion-eyebrow">
                Dönüşüm akışı
              </p>
              <h2 className="mt-3 text-4xl font-extrabold tracking-[-0.03em] text-slate-900" style={{ fontFamily: "Manrope, Inter, sans-serif" }} data-testid="pricing-conversion-title">
                Instagram'dan gelen kullanıcıyı trial'a, trial'dan ücretli plana taşıyın
              </h2>
            </div>

            <div className="grid gap-3 sm:grid-cols-3" data-testid="pricing-conversion-cards">
              {[
                "Demo hesabını aç",
                "14 gün ücretsiz kullan",
                "Doğru plan ile devam et",
              ].map((item, index) => (
                <div key={item} className="rounded-2xl border border-slate-200 bg-[#fbfcfc] px-4 py-4" data-testid={`pricing-conversion-card-${index + 1}`}>
                  <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[#2a9d8f]" data-testid={`pricing-conversion-card-step-${index + 1}`}>Adım {index + 1}</p>
                  <p className="mt-3 text-sm font-semibold leading-6 text-slate-900" data-testid={`pricing-conversion-card-text-${index + 1}`}>{item}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="rounded-[2rem] bg-[#264653] px-8 py-10 text-white lg:px-12" data-testid="pricing-final-cta-section">
          <div className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.24em] text-[#e9c46a]" data-testid="pricing-final-cta-eyebrow">
                Hazırsanız başlayalım
              </p>
              <h2 className="mt-3 text-4xl font-extrabold tracking-[-0.03em]" style={{ fontFamily: "Manrope, Inter, sans-serif" }} data-testid="pricing-final-cta-title">
                14 Gün Ücretsiz Dene
              </h2>
            </div>

            <div className="flex flex-wrap gap-3" data-testid="pricing-final-cta-group">
              <Button asChild className="h-12 rounded-xl bg-[#f3722c] px-6 text-sm font-semibold text-white hover:bg-[#e05d1b]" data-testid="pricing-final-cta-primary">
                <Link to="/signup?plan=trial&selectedPlan=pro">14 Gün Ücretsiz Dene</Link>
              </Button>
              <Button asChild variant="outline" className="h-12 rounded-xl border-white/40 bg-transparent px-6 text-sm font-semibold text-white hover:bg-white/10" data-testid="pricing-final-cta-secondary">
                <Link to="/demo">Önce demo sayfasını incele</Link>
              </Button>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}