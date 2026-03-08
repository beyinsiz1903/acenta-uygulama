import React, { useEffect, useMemo, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { ArrowRight, BadgeCheck, CheckCircle2, Clock3, Sparkles, Users } from "lucide-react";
import { toast } from "sonner";

import { Button } from "../../components/ui/button";
import { Tabs, TabsList, TabsTrigger } from "../../components/ui/tabs";
import { api, getUser } from "../../lib/api";
import { createCheckoutSession } from "../../lib/billing";
import { getActiveTenantId } from "../../lib/tenantContext";
import { useSeo } from "../../hooks/useSeo";

const PAID_PLAN_ORDER = ["starter", "pro", "enterprise"];

const PLAN_DISPLAY = {
  starter: {
    key: "starter",
    label: "Starter",
    audience: "Küçük acenteler için",
    description: "Excel ile büyümeye çalışan ekipler için net başlangıç paketi.",
    features: [
      "100 rezervasyon",
      "3 kullanıcı",
      "Temel raporlar",
      "Google Sheets entegrasyonu",
    ],
    pricing: {
      monthly: { amount: 990, label: "₺990", period: "/ ay" },
      yearly: { amount: 9900, label: "₺9.900", period: "/ yıl", badge: "2 ay ücretsiz" },
    },
  },
  pro: {
    key: "pro",
    label: "Pro",
    audience: "Önerilen plan",
    description: "Satış ve operasyon akışını tek panelde toplamak isteyen büyüyen acenteler için.",
    features: [
      "500 rezervasyon",
      "10 kullanıcı",
      "Tüm raporlar",
      "Export ve entegrasyonlar",
    ],
    pricing: {
      monthly: { amount: 2490, label: "₺2.490", period: "/ ay" },
      yearly: { amount: 24900, label: "₺24.900", period: "/ yıl", badge: "2 ay ücretsiz" },
    },
    is_popular: true,
  },
  enterprise: {
    key: "enterprise",
    label: "Enterprise",
    audience: "Büyük operasyonlar için",
    description: "Yüksek hacim, özel entegrasyon ve sözleşmeli destek gerektiren ekipler için.",
    features: [
      "Sınırsız rezervasyon",
      "Sınırsız kullanıcı",
      "API erişimi",
      "Özel entegrasyon",
    ],
    pricing: {
      monthly: { amount: 6990, label: "₺6.990", period: "/ ay" },
      yearly: { amount: 69900, label: "Özel teklif", period: "" },
    },
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

const PRICING_PROBLEMS = [
  "Excel ile rezervasyon takibi",
  "WhatsApp ile müşteri yönetimi",
  "Dağınık operasyon süreçleri",
];

const PRICING_SOLUTIONS = [
  "Rezervasyon yönetimi",
  "Müşteri yönetimi",
  "Raporlama",
  "Entegrasyonlar",
];

export default function PricingPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const [plans, setPlans] = useState([]);
  const [billingCycle, setBillingCycle] = useState("monthly");
  const [checkoutPlan, setCheckoutPlan] = useState("");

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
      const fallbackPlan = PLAN_DISPLAY[key];
      const fetchedPlan = fetchedMap.get(key) || {};

      return {
        ...fallbackPlan,
        ...fetchedPlan,
        key,
        label: fetchedPlan.label || fallbackPlan.label,
        audience: fallbackPlan.audience,
        description: fallbackPlan.description,
        features: fallbackPlan.features,
        pricing: fallbackPlan.pricing,
        is_popular: key === "pro",
      };
    });
  }, [plans]);

  const resolvedUser = getUser();
  const hasCheckoutIdentity = Boolean(resolvedUser?.email && (getActiveTenantId() || resolvedUser?.organization_id));

  async function handlePlanCheckout(planKey) {
    if (planKey === "enterprise") {
      navigate("/demo");
      return;
    }

    if (!hasCheckoutIdentity) {
      toast.info("Önce trial hesabınızı oluşturun, sonra ödeme adımına geçin.");
      navigate(`/signup?plan=trial&selectedPlan=${planKey}`);
      return;
    }

    setCheckoutPlan(planKey);
    try {
      const result = await createCheckoutSession({
        plan: planKey,
        interval: billingCycle,
        origin_url: window.location.origin,
        cancel_path: `${location.pathname}${location.search}`,
      });
      window.location.href = result.url;
    } catch (err) {
      toast.error(err?.message || "Stripe checkout başlatılamadı.");
    } finally {
      setCheckoutPlan("");
    }
  }

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
          <div className="flex flex-col gap-5 md:flex-row md:items-end md:justify-between">
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.22em] text-[#d16024]" data-testid="pricing-section-eyebrow">
                Planlar
              </p>
              <h2 className="mt-2 text-4xl font-extrabold tracking-[-0.03em] text-slate-900" style={{ fontFamily: "Manrope, Inter, sans-serif" }} data-testid="pricing-section-title">
                Küçük ekibiniz de büyük operasyonunuz da aynı panelde büyüsün
              </h2>
            </div>

            <div className="space-y-3" data-testid="pricing-billing-cycle-wrap">
              <p className="text-sm text-slate-600" data-testid="pricing-billing-cycle-description">Starter ve Pro için Stripe test mode checkout aktif. Enterprise için satış görüşmesi yapılır.</p>
              <Tabs value={billingCycle} onValueChange={setBillingCycle} data-testid="pricing-billing-cycle-tabs">
                <TabsList className="h-11 rounded-xl bg-[#f4f6f6] p-1" data-testid="pricing-billing-cycle-list">
                  <TabsTrigger value="monthly" className="rounded-lg px-4" data-testid="pricing-billing-cycle-monthly">Aylık</TabsTrigger>
                  <TabsTrigger value="yearly" className="rounded-lg px-4" data-testid="pricing-billing-cycle-yearly">Yıllık</TabsTrigger>
                </TabsList>
              </Tabs>
            </div>
          </div>

          <div className="grid gap-6 lg:grid-cols-3" data-testid="pricing-plan-grid">
            {publicPlans.map((plan) => {
              const activePricing = plan.pricing?.[billingCycle] || plan.pricing?.monthly;
              const isEnterprise = plan.key === "enterprise";
              const isLoading = checkoutPlan === plan.key;

              return (
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

                    <div className="flex flex-wrap items-end gap-2" data-testid={`pricing-plan-price-wrap-${plan.key}`}>
                      <span className="text-4xl font-extrabold tracking-[-0.04em] text-slate-900" style={{ fontFamily: "Manrope, Inter, sans-serif" }} data-testid={`pricing-plan-price-${plan.key}`}>
                        {activePricing?.label}
                      </span>
                      <span className="pb-1 text-sm font-medium text-slate-500" data-testid={`pricing-plan-period-${plan.key}`}>
                        {activePricing?.period}
                      </span>
                      {activePricing?.badge ? (
                        <span className="rounded-full bg-[#fff1e8] px-3 py-1 text-xs font-semibold text-[#d16024]" data-testid={`pricing-plan-savings-${plan.key}`}>
                          {activePricing.badge}
                        </span>
                      ) : null}
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

                  <div className="mt-6 space-y-3 pt-2">
                    {isEnterprise ? (
                      <Button asChild className="h-12 w-full rounded-xl bg-[#264653] text-sm font-semibold text-white hover:bg-[#1f3742]" data-testid={`pricing-plan-cta-${plan.key}`}>
                        <Link to="/demo">İletişime Geç</Link>
                      </Button>
                    ) : (
                      <Button onClick={() => void handlePlanCheckout(plan.key)} disabled={isLoading} className={`h-12 w-full rounded-xl text-sm font-semibold ${plan.is_popular ? "bg-[#f3722c] text-white hover:bg-[#e05d1b]" : "bg-[#264653] text-white hover:bg-[#1f3742]"}`} data-testid={`pricing-plan-cta-${plan.key}`}>
                        {isLoading ? "Yönlendiriliyor..." : "Planı Seç"}
                      </Button>
                    )}
                    <p className="text-xs text-slate-500" data-testid={`pricing-plan-note-${plan.key}`}>
                      {isEnterprise ? "Enterprise planı özel teklif ve sözleşmeli kurulum ile ilerler." : hasCheckoutIdentity ? "Stripe Checkout ile güvenli ödeme akışına yönlendirilirsiniz." : "Ödeme adımından önce trial hesabınız açılır ve hedef planınız kaydedilir."}
                    </p>
                  </div>
                </article>
              );
            })}
          </div>
        </section>

        <section className="grid gap-6 lg:grid-cols-2" data-testid="pricing-problem-solution-section">
          <article className="rounded-[2rem] border border-[#f1e3d8] bg-[#fffaf6] p-8 shadow-[0_25px_80px_rgba(38,70,83,0.06)]" data-testid="pricing-problem-card">
            <p className="text-sm font-semibold uppercase tracking-[0.24em] text-[#d16024]" data-testid="pricing-problem-eyebrow">
              Problem bölümü
            </p>
            <h2 className="mt-3 text-4xl font-extrabold tracking-[-0.03em] text-slate-900" style={{ fontFamily: "Manrope, Inter, sans-serif" }} data-testid="pricing-problem-title">
              Acentelerde en büyük sorun operasyon karmaşası
            </h2>
            <div className="mt-6 grid gap-3" data-testid="pricing-problem-list">
              {PRICING_PROBLEMS.map((item, index) => (
                <div key={item} className="rounded-2xl border border-white bg-white px-4 py-4" data-testid={`pricing-problem-item-${index + 1}`}>
                  <p className="text-sm font-semibold leading-6 text-slate-900" data-testid={`pricing-problem-item-text-${index + 1}`}>{item}</p>
                </div>
              ))}
            </div>
          </article>

          <article className="rounded-[2rem] border border-[#dbe8e6] bg-white/95 p-8 shadow-[0_25px_80px_rgba(38,70,83,0.08)]" data-testid="pricing-solution-card">
            <p className="text-sm font-semibold uppercase tracking-[0.24em] text-[#2a9d8f]" data-testid="pricing-solution-eyebrow">
              Çözüm bölümü
            </p>
            <h2 className="mt-3 text-4xl font-extrabold tracking-[-0.03em] text-slate-900" style={{ fontFamily: "Manrope, Inter, sans-serif" }} data-testid="pricing-solution-title">
              Syroce ile tüm operasyon tek panelde
            </h2>
            <div className="mt-6 grid gap-3" data-testid="pricing-solution-list">
              {PRICING_SOLUTIONS.map((item, index) => (
                <div key={item} className="rounded-2xl bg-[#f7fbfb] px-4 py-4" data-testid={`pricing-solution-item-${index + 1}`}>
                  <p className="text-sm font-semibold leading-6 text-slate-900" data-testid={`pricing-solution-item-text-${index + 1}`}>{item}</p>
                </div>
              ))}
            </div>
          </article>
        </section>

        <section className="grid gap-6 lg:grid-cols-[1.05fr_0.95fr]" data-testid="pricing-roi-section">
          <article className="rounded-[2rem] bg-[#264653] px-8 py-10 text-white shadow-[0_25px_80px_rgba(38,70,83,0.12)] lg:px-10" data-testid="pricing-social-proof-card">
            <p className="text-sm font-semibold uppercase tracking-[0.24em] text-[#e9c46a]" data-testid="pricing-social-proof-eyebrow">
              ROI bölümü
            </p>
            <h2 className="mt-3 text-4xl font-extrabold tracking-[-0.03em]" style={{ fontFamily: "Manrope, Inter, sans-serif" }} data-testid="pricing-social-proof-title">
              Syroce kullanan acenteler operasyon süresini %40 azaltıyor
            </h2>
            <p className="mt-4 max-w-2xl text-base leading-7 text-white/80" data-testid="pricing-social-proof-text">
              Turizm acenteleri Syroce ile operasyon süreçlerini %40 daha hızlı yönetiyor. Bu da daha az dağınıklık, daha hızlı ekip koordinasyonu ve daha net satış takibi anlamına gelir.
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