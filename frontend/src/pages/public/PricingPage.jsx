import React, { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, CheckCircle2, Clock3, FileSpreadsheet, MessagesSquare, ShieldCheck, Users } from "lucide-react";

import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "../../components/ui/accordion";
import { Button } from "../../components/ui/button";
import { api } from "../../lib/api";
import { LIMIT_LABELS, formatEntitlementValue } from "../../lib/entitlementLabels";
import { useSeo } from "../../hooks/useSeo";

const PAID_PLAN_ORDER = ["starter", "pro", "enterprise"];

const PLAN_COPY = {
  starter: {
    eyebrow: "Küçük acenteler",
    headline: "Excel kullanan ekipler için sıcak başlangıç",
    bullets: [
      "Müşteri yönetimi",
      "Temel raporlar",
      "Google Sheets entegrasyonu",
      "Export araçları",
    ],
  },
  pro: {
    eyebrow: "Büyüyen acenteler",
    headline: "Satış ve operasyonu tek panelde toplayın",
    bullets: [
      "Gelişmiş raporlar",
      "Tüm export araçları",
      "Operasyon araçları",
      "Entegrasyonlar",
    ],
  },
  enterprise: {
    eyebrow: "Büyük operasyonlar",
    headline: "Özel entegrasyon ve sınırsız kapasite isteyen ekipler için",
    bullets: [
      "API erişimi",
      "Özel entegrasyon",
      "White label",
      "Öncelikli destek",
    ],
  },
};

const FAQ_ITEMS = [
  {
    id: "trial",
    question: "14 günlük trial nasıl çalışıyor?",
    answer: "Hesabınız Trial planı ile açılır. 14 gün boyunca tüm özellikleri deneyebilir, 100 rezervasyon ve 2 kullanıcı ile gerçek akışınızı test edebilirsiniz.",
  },
  {
    id: "card",
    question: "Kredi kartı gerekiyor mu?",
    answer: "Hayır. Trial başlatmak için kredi kartı gerekmiyor. Önce sistemi deneyin, sonra size uyan planı seçin.",
  },
  {
    id: "upgrade",
    question: "Daha sonra planımı değiştirebilir miyim?",
    answer: "Evet. Trial sonrasında Starter, Pro veya Enterprise planına geçebilir; ihtiyaç büyüdükçe yükseltebilirsiniz.",
  },
  {
    id: "support",
    question: "Kurulum ne kadar sürer?",
    answer: "Demo hesabınızı dakikalar içinde açabilirsiniz. İlk kullanım için teknik kurulum zorunlu değil; ekip akışınızı hemen test etmeye başlayabilirsiniz.",
  },
];

function formatMonthlyPrice(pricing = {}) {
  if (pricing?.monthly === 0) {
    return pricing?.label || "Ücretsiz";
  }
  if (typeof pricing?.monthly === "number") {
    return `₺${pricing.monthly.toLocaleString("tr-TR")}`;
  }
  return "İletişime geçin";
}

export default function PricingPage() {
  const [plans, setPlans] = useState([]);

  useSeo({
    title: "Turizm acenteleri için fiyatlandırma",
    description: "Starter, Pro ve Enterprise planlarını karşılaştırın. 14 gün ücretsiz deneyin, kredi kartı olmadan başlayın.",
    canonicalPath: "/pricing",
    type: "website",
  });

  useEffect(() => {
    api.get("/onboarding/plans").then((response) => setPlans(response.data?.plans || [])).catch(() => setPlans([]));
  }, []);

  const publicPlans = useMemo(() => {
    const byKey = new Map((plans || []).map((plan) => [plan.key || plan.name, plan]));
    return PAID_PLAN_ORDER.map((key) => byKey.get(key)).filter(Boolean);
  }, [plans]);

  return (
    <div className="min-h-screen bg-[linear-gradient(180deg,#fdfbf7_0%,#fff5f0_42%,#f8fbfb_100%)] text-slate-900" style={{ fontFamily: "Inter, sans-serif" }} data-testid="pricing-page">
      <div className="mx-auto flex max-w-7xl flex-col gap-20 px-4 py-12 sm:px-6 lg:px-8 lg:py-20">
        <section className="grid gap-8 rounded-[2rem] border border-[#f4d9ca] bg-white/85 p-8 shadow-[0_30px_120px_rgba(38,70,83,0.10)] backdrop-blur md:grid-cols-[1.2fr_0.8fr] lg:p-12" data-testid="pricing-hero-section">
          <div className="space-y-6">
            <div className="inline-flex items-center gap-2 rounded-full border border-[#f4c9b2] bg-[#fff3ec] px-4 py-2 text-xs font-semibold uppercase tracking-[0.24em] text-[#d16024]" data-testid="pricing-hero-badge">
              <Clock3 className="h-4 w-4" />
              14 Gün Ücretsiz Deneyin
            </div>

            <div className="space-y-4">
              <p className="text-sm font-semibold uppercase tracking-[0.28em] text-[#264653]" data-testid="pricing-hero-eyebrow">Turizm Acenteleri İçin Bulut Yazılım</p>
              <h1 className="text-4xl font-extrabold leading-[1.02] tracking-[-0.03em] text-slate-900 sm:text-5xl lg:text-6xl" style={{ fontFamily: "Manrope, Inter, sans-serif" }} data-testid="pricing-title">
                Acentenizi <span className="text-[#f3722c]">Excel'den kurtarın</span>
              </h1>
              <p className="max-w-2xl text-base leading-7 text-slate-600 md:text-lg" data-testid="pricing-subtitle">
                Rezervasyonları, müşterileri ve ödemeleri tek panelden yönetin. Gizli ücret yok, kredi kartı gerekmez.
              </p>
            </div>

            <div className="flex flex-wrap gap-3">
              <Button asChild className="h-12 rounded-xl bg-[#f3722c] px-6 text-sm font-semibold text-white hover:bg-[#e05d1b]" data-testid="pricing-hero-primary-cta">
                <Link to="/signup?plan=trial&selectedPlan=pro">
                  14 Gün Ücretsiz Dene
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Link>
              </Button>
              <Button asChild variant="outline" className="h-12 rounded-xl border-[#264653] px-6 text-sm font-semibold text-[#264653] hover:bg-[#fdfbf7]" data-testid="pricing-hero-secondary-cta">
                <Link to="/demo">Canlı demoyu gör</Link>
              </Button>
            </div>

            <div className="grid gap-3 sm:grid-cols-3" data-testid="pricing-hero-points">
              {[
                { icon: CheckCircle2, title: "Trial", desc: "14 gün boyunca tüm özellikler açık" },
                { icon: Users, title: "Kullanıcı", desc: "Trial içinde 2 kullanıcı ile ekip akışını test edin" },
                { icon: ShieldCheck, title: "Geçiş", desc: "Trial sonunda size uyan paketi seçin" },
              ].map((item) => (
                <div key={item.title} className="rounded-2xl border border-slate-200 bg-slate-50/80 p-4" data-testid={`pricing-hero-point-${item.title.toLowerCase()}`}>
                  <item.icon className="h-5 w-5 text-[#2a9d8f]" />
                  <p className="mt-3 text-sm font-semibold text-slate-900">{item.title}</p>
                  <p className="mt-1 text-sm leading-6 text-slate-600">{item.desc}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="grid gap-4 self-stretch rounded-[1.75rem] bg-[#264653] p-6 text-white" data-testid="pricing-trial-card">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[#e9c46a]" data-testid="pricing-trial-card-eyebrow">Trial nasıl başlar?</p>
              <h2 className="mt-3 text-3xl font-extrabold tracking-[-0.03em]" style={{ fontFamily: "Manrope, Inter, sans-serif" }} data-testid="pricing-trial-card-title">
                Önce deneyin, sonra karar verin
              </h2>
            </div>

            <div className="space-y-3">
              {[
                "14 gün boyunca aktif trial",
                "100 rezervasyon limiti",
                "2 kullanıcı ile deneme",
                "Tüm çekirdek özellikler açık",
              ].map((row, index) => (
                <div key={row} className="flex items-center gap-3 rounded-2xl bg-white/10 px-4 py-3" data-testid={`pricing-trial-card-row-${index + 1}`}>
                  <CheckCircle2 className="h-4 w-4 text-[#e9c46a]" />
                  <span className="text-sm text-white/90">{row}</span>
                </div>
              ))}
            </div>

            <div className="rounded-2xl bg-white/10 p-5" data-testid="pricing-trial-card-footer">
              <p className="text-sm font-medium text-white/80">Trial sonunda ne olur?</p>
              <p className="mt-2 text-base font-semibold text-white">Planınızı seçerek kaldığınız yerden devam edersiniz.</p>
            </div>
          </div>
        </section>

        <section className="space-y-8" data-testid="pricing-cards-section">
          <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.22em] text-[#d16024]" data-testid="pricing-section-eyebrow">Planlar</p>
              <h2 className="mt-2 text-4xl font-extrabold tracking-[-0.03em] text-slate-900" style={{ fontFamily: "Manrope, Inter, sans-serif" }} data-testid="pricing-section-title">
                Her ölçekte acenteye göre net fiyatlar
              </h2>
            </div>
            <p className="max-w-xl text-sm leading-6 text-slate-600" data-testid="pricing-section-description">
              Küçük ekipler Starter ile başlar, büyüyen acenteler Pro'ya geçer, büyük operasyonlar Enterprise ile tam kapasiteye çıkar.
            </p>
          </div>

          <div className="grid gap-6 lg:grid-cols-3" data-testid="pricing-plan-grid">
            {publicPlans.map((plan) => {
              const key = plan.key || plan.name;
              const copy = PLAN_COPY[key] || {};
              const isPopular = Boolean(plan.is_popular);

              return (
                <article
                  key={key}
                  className={`relative overflow-hidden rounded-[1.75rem] border p-7 shadow-[0_25px_80px_rgba(38,70,83,0.08)] transition-transform duration-300 hover:-translate-y-1 ${isPopular ? "border-[#f3722c] bg-[#fff8f3]" : "border-white bg-white/90"}`}
                  data-testid={`pricing-plan-${key}`}
                >
                  {isPopular && (
                    <div className="absolute right-5 top-5 rounded-full bg-[#f3722c] px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-white" data-testid={`pricing-plan-badge-${key}`}>
                      En Popüler
                    </div>
                  )}

                  <div className="space-y-4">
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[#2a9d8f]" data-testid={`pricing-plan-eyebrow-${key}`}>{copy.eyebrow || plan.audience || "Plan"}</p>
                      <h3 className="mt-3 text-3xl font-extrabold tracking-[-0.03em] text-slate-900" style={{ fontFamily: "Manrope, Inter, sans-serif" }} data-testid={`pricing-plan-label-${key}`}>{plan.label}</h3>
                      <p className="mt-2 text-sm leading-6 text-slate-600" data-testid={`pricing-plan-headline-${key}`}>{copy.headline || plan.description}</p>
                    </div>

                    <div className="flex items-end gap-2" data-testid={`pricing-plan-price-wrap-${key}`}>
                      <span className="text-4xl font-extrabold tracking-[-0.04em] text-slate-900" style={{ fontFamily: "Manrope, Inter, sans-serif" }} data-testid={`pricing-plan-price-${key}`}>
                        {formatMonthlyPrice(plan.pricing)}
                      </span>
                      <span className="pb-1 text-sm font-medium text-slate-500" data-testid={`pricing-plan-period-${key}`}>/ ay</span>
                    </div>

                    <div className="grid gap-2" data-testid={`pricing-plan-limits-${key}`}>
                      {Object.entries(plan.limits || {}).map(([limitKey, value]) => (
                        <div key={limitKey} className="flex items-center justify-between rounded-2xl bg-slate-50 px-4 py-3 text-sm text-slate-700" data-testid={`pricing-plan-limit-${key}-${limitKey.replace(/\./g, "-")}`}>
                          <span>{LIMIT_LABELS[limitKey] || limitKey}</span>
                          <span className="font-semibold text-slate-900">{formatEntitlementValue(value, limitKey === "reservations.monthly" ? " / ay" : "")}</span>
                        </div>
                      ))}
                    </div>

                    <ul className="space-y-3" data-testid={`pricing-plan-bullets-${key}`}>
                      {(copy.bullets || []).map((bullet, index) => (
                        <li key={bullet} className="flex items-start gap-3 text-sm leading-6 text-slate-700" data-testid={`pricing-plan-bullet-${key}-${index + 1}`}>
                          <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-[#f3722c]" />
                          <span>{bullet}</span>
                        </li>
                      ))}
                    </ul>

                    <Button asChild className={`mt-2 h-12 rounded-xl text-sm font-semibold ${isPopular ? "bg-[#f3722c] text-white hover:bg-[#e05d1b]" : "bg-[#264653] text-white hover:bg-[#1f3742]"}`} data-testid={`pricing-plan-cta-${key}`}>
                      <Link to={`/signup?plan=trial&selectedPlan=${key}`}>14 Gün Ücretsiz Dene</Link>
                    </Button>
                  </div>
                </article>
              );
            })}
          </div>
        </section>

        <section className="grid gap-6 lg:grid-cols-3" data-testid="pricing-why-trial-section">
          {[
            { icon: FileSpreadsheet, title: "Excel'den gerçek geçiş", text: "Trial içinde mevcut operasyonunuzu sistem üzerinde birebir deneyebilirsiniz." },
            { icon: MessagesSquare, title: "WhatsApp karmaşasını görün", text: "Rezervasyon ve müşteri takibini tek panelde toplayarak dağınık iletişimi azaltın." },
            { icon: Clock3, title: "Upgrade zamanı netleşir", text: "Usage warning sistemi ne zaman üst pakete geçmeniz gerektiğini otomatik gösterir." },
          ].map((item, index) => (
            <div key={item.title} className="rounded-[1.75rem] border border-[#dde8e7] bg-white/80 p-6" data-testid={`pricing-why-card-${index + 1}`}>
              <item.icon className="h-5 w-5 text-[#2a9d8f]" />
              <h3 className="mt-4 text-2xl font-extrabold tracking-[-0.03em] text-slate-900" style={{ fontFamily: "Manrope, Inter, sans-serif" }} data-testid={`pricing-why-card-title-${index + 1}`}>{item.title}</h3>
              <p className="mt-3 text-sm leading-6 text-slate-600" data-testid={`pricing-why-card-text-${index + 1}`}>{item.text}</p>
            </div>
          ))}
        </section>

        <section className="rounded-[2rem] border border-slate-200 bg-white/90 p-8 shadow-[0_25px_80px_rgba(38,70,83,0.08)] lg:p-10" data-testid="pricing-faq-section">
          <div className="max-w-3xl">
            <p className="text-sm font-semibold uppercase tracking-[0.22em] text-[#d16024]" data-testid="pricing-faq-eyebrow">Sık sorulanlar</p>
            <h2 className="mt-2 text-4xl font-extrabold tracking-[-0.03em] text-slate-900" style={{ fontFamily: "Manrope, Inter, sans-serif" }} data-testid="pricing-faq-title">
              Kararsız kalmadan başlayın
            </h2>
          </div>

          <Accordion type="single" collapsible className="mt-8" data-testid="pricing-faq-accordion">
            {FAQ_ITEMS.map((item) => (
              <AccordionItem key={item.id} value={item.id} data-testid={`pricing-faq-item-${item.id}`}>
                <AccordionTrigger className="text-base font-semibold text-slate-900" data-testid={`pricing-faq-trigger-${item.id}`}>
                  {item.question}
                </AccordionTrigger>
                <AccordionContent className="text-sm leading-7 text-slate-600" data-testid={`pricing-faq-content-${item.id}`}>
                  {item.answer}
                </AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        </section>

        <section className="rounded-[2rem] bg-[#264653] px-8 py-10 text-white lg:px-12" data-testid="pricing-final-cta-section">
          <div className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.24em] text-[#e9c46a]" data-testid="pricing-final-cta-eyebrow">Hazırsanız başlayalım</p>
              <h2 className="mt-3 text-4xl font-extrabold tracking-[-0.03em]" style={{ fontFamily: "Manrope, Inter, sans-serif" }} data-testid="pricing-final-cta-title">
                Önce demo hesabınızı açın, sonra size uyan planı seçin
              </h2>
            </div>

            <div className="flex flex-wrap gap-3">
              <Button asChild className="h-12 rounded-xl bg-[#f3722c] px-6 text-sm font-semibold text-white hover:bg-[#e05d1b]" data-testid="pricing-final-cta-primary">
                <Link to="/signup?plan=trial&selectedPlan=pro">14 Gün Ücretsiz Dene</Link>
              </Button>
              <Button asChild variant="outline" className="h-12 rounded-xl border-white/40 bg-transparent px-6 text-sm font-semibold text-white hover:bg-white/10" data-testid="pricing-final-cta-secondary">
                <Link to="/demo">Demo sayfasını incele</Link>
              </Button>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}