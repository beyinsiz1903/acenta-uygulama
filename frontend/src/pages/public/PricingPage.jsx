import React, { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, CheckCircle2, Sparkles, Phone, Mail, Clock, Shield, Zap, Users } from "lucide-react";

import { PublicNavbar } from "../../components/marketing/PublicNavbar";
import { SyroceFaqSection } from "../../components/marketing/SyroceFaqSection";
import { SyrocePricingCard } from "../../components/marketing/SyrocePricingCard";
import { SyrocePricingComparison } from "../../components/marketing/SyrocePricingComparison";
import { Button } from "../../components/ui/button";
import { Tabs, TabsList, TabsTrigger } from "../../components/ui/tabs";
import { useSeo } from "../../hooks/useSeo";
import { SYROCE_FAQS, SYROCE_PUBLIC_PACKAGES } from "../../lib/syrocePricingContent";

const HERO_POINTS = [
  "Rezervasyon sınırı yok",
  "Google Sheets / E-Tablo entegrasyonu ikinci paketten itibaren dahil",
  "Yıllık fiyatlarda kurulum + ilk yıl kullanım birlikte planlanır",
];

const TRUST_ITEMS = [
  { icon: Shield, label: "SSL ve güvenlik dahil" },
  { icon: Zap, label: "7/24 bulut altyapı" },
  { icon: Users, label: "Çözüm odaklı destek" },
  { icon: Clock, label: "1 iş gününde kurulum" },
];

export default function PricingPage() {
  const [billingCycle, setBillingCycle] = useState("yearly");

  useSeo({
    title: "Syroce fiyatları ve paket karşılaştırması",
    description:
      "Syroce paketlerini aylık, yıllık ve özel teklif yapısında karşılaştırın. Google Sheets / E-Tablo entegrasyonu, operasyon modülleri ve destek modeli net şekilde görünür.",
    canonicalPath: "/pricing",
    type: "website",
  });

  const packages = useMemo(() => SYROCE_PUBLIC_PACKAGES, []);

  return (
    <div className="min-h-screen bg-[#fafcff]" data-testid="pricing-page">
      <PublicNavbar testIdPrefix="pricing-nav" />

      <div className="mx-auto flex max-w-7xl flex-col gap-16 px-4 py-12 sm:px-6 lg:px-8 lg:py-16">
        {/* Promo banner */}
        <div className="rounded-2xl border border-amber-200 bg-gradient-to-r from-amber-50 to-orange-50 px-6 py-4 text-center" data-testid="pricing-promo-banner">
          <p className="text-sm font-semibold text-amber-800" data-testid="pricing-promo-text">
            <Sparkles className="inline-block h-4 w-4 mr-1.5 -mt-0.5" />
            Süre Sınırlı Teklif: 2 yıllık alımlarda +1 yıl bizden!
          </p>
          <p className="mt-1 text-xs text-amber-700">
            Karmaşık iş süreçlerinizi geride bırakın, satışlarınızı arttırın, iş ortaklarınıza bağlanın.
          </p>
        </div>

        {/* Hero Section */}
        <section className="grid gap-8 overflow-hidden rounded-[2.3rem] border border-[#e7eefc] bg-white/92 p-8 shadow-[0_28px_120px_rgba(15,23,42,0.08)] lg:grid-cols-[1.04fr_0.96fr] lg:p-12" data-testid="pricing-hero-section">
          <div className="space-y-6">
            <div className="inline-flex items-center gap-2 rounded-full border border-blue-100 bg-[#eef6ff] px-4 py-2 text-xs font-semibold uppercase tracking-[0.24em] text-[#2563EB]" data-testid="pricing-hero-badge">
              <Sparkles className="h-4 w-4" />
              Şeffaf, net ve operasyon odaklı
            </div>

            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.24em] text-[#2563EB]" data-testid="pricing-hero-eyebrow">
                Syroce Paketleri
              </p>
              <h1 className="mt-4 text-4xl font-extrabold leading-[1.02] tracking-[-0.05em] text-slate-950 sm:text-5xl lg:text-6xl" style={{ fontFamily: "Manrope, Inter, sans-serif" }} data-testid="pricing-title">
                Bulut Acenta Yönetim
                <span className="block text-[#2563EB]" data-testid="pricing-title-highlight">ve Operasyon Çözümü</span>
              </h1>
              <p className="mt-5 max-w-2xl text-base leading-8 text-slate-600 md:text-lg" data-testid="pricing-subtitle">
                Paketlerimizi rezervasyon limitiyle değil; entegrasyon seviyesi, ekip yapısı, destek modeli ve operasyon kapsamı ile ayırıyoruz. Google Sheets / E-Tablo entegrasyonu Standart paket ile başlar.
              </p>
            </div>

            <div className="flex flex-wrap gap-3" data-testid="pricing-hero-cta-group">
              <Button asChild className="h-12 rounded-full bg-[linear-gradient(135deg,#2563EB,#0EA5E9)] px-6 text-sm font-semibold text-white hover:brightness-110" data-testid="pricing-hero-primary-cta">
                <Link to="/signup?plan=trial&selectedPlan=pro">
                  14 Gün Ücretsiz Dene
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Link>
              </Button>
              <Button asChild variant="outline" className="h-12 rounded-full border-slate-200 bg-white px-6 text-sm font-semibold text-slate-700 hover:bg-slate-50" data-testid="pricing-hero-secondary-cta">
                <Link to="/demo">Demo isteyin</Link>
              </Button>
            </div>
          </div>

          <div className="rounded-[2rem] bg-slate-950 p-6 text-white shadow-[0_26px_80px_rgba(15,23,42,0.18)]" data-testid="pricing-side-panel">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-sky-200/80" data-testid="pricing-side-panel-eyebrow">
              Fiyat yapısı
            </p>
            <h2 className="mt-4 text-3xl font-extrabold tracking-[-0.03em]" style={{ fontFamily: "Manrope, Inter, sans-serif" }} data-testid="pricing-side-panel-title">
              Aylık, yıllık ve özel teklif seçenekleri
            </h2>
            <div className="mt-6 grid gap-3" data-testid="pricing-side-panel-list">
              {HERO_POINTS.map((point, index) => (
                <div key={point} className="flex items-start gap-3 rounded-2xl bg-white/8 px-4 py-4 text-sm text-white/90" data-testid={`pricing-side-panel-point-${index + 1}`}>
                  <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-[#38BDF8]" />
                  <span>{point}</span>
                </div>
              ))}
            </div>
            <div className="mt-6 rounded-[1.5rem] border border-white/10 bg-white/10 p-5" data-testid="pricing-side-panel-footer">
              <p className="text-sm font-medium text-white/70" data-testid="pricing-side-panel-footer-label">Ek not</p>
              <p className="mt-2 text-base font-semibold text-white" data-testid="pricing-side-panel-footer-text">
                Yıllık fiyatlarda kurulum dahil yapı sunuyoruz; çok yıllı anlaşmalar için özel teklif planlanabilir.
              </p>
            </div>
          </div>
        </section>

        {/* Trust Bar */}
        <section className="grid grid-cols-2 gap-4 lg:grid-cols-4" data-testid="pricing-trust-bar">
          {TRUST_ITEMS.map((item, i) => (
            <div
              key={i}
              className="flex items-center gap-3 rounded-2xl border border-slate-100 bg-white p-4 shadow-sm"
              data-testid={`pricing-trust-item-${i}`}
            >
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-blue-50">
                <item.icon className="h-5 w-5 text-[#2563EB]" />
              </div>
              <span className="text-sm font-medium text-slate-700">{item.label}</span>
            </div>
          ))}
        </section>

        {/* Pricing Cards Section */}
        <section className="space-y-8" data-testid="pricing-cards-section">
          <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between" data-testid="pricing-section-header">
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.24em] text-[#d16024]" data-testid="pricing-section-eyebrow">
                Paketler
              </p>
              <h2 className="mt-3 text-4xl font-extrabold tracking-[-0.03em] text-slate-950" style={{ fontFamily: "Manrope, Inter, sans-serif" }} data-testid="pricing-section-title">
                Girişten Platinum'a kadar 4 farklı seviye
              </h2>
              <p className="mt-3 max-w-3xl text-sm leading-7 text-slate-600 sm:text-base" data-testid="pricing-section-description">
                E-Ticaret, rezervasyon ve süreç yönetimi için şeffaf, net fiyatlar. Sizi gizli ve sürpriz giderlerden korur.
              </p>
            </div>

            <div className="space-y-3" data-testid="pricing-billing-cycle-wrap">
              <p className="text-sm text-slate-600" data-testid="pricing-billing-cycle-description">
                Aylık veya yıllık görünümü değiştirin
              </p>
              <Tabs value={billingCycle} onValueChange={setBillingCycle} data-testid="pricing-billing-cycle-tabs">
                <TabsList className="h-11 rounded-full bg-white p-1 shadow-[0_12px_30px_rgba(15,23,42,0.05)]" data-testid="pricing-billing-cycle-list">
                  <TabsTrigger value="monthly" className="rounded-full px-5" data-testid="pricing-billing-cycle-monthly">Aylık</TabsTrigger>
                  <TabsTrigger value="yearly" className="rounded-full px-5" data-testid="pricing-billing-cycle-yearly">Yıllık</TabsTrigger>
                </TabsList>
              </Tabs>
            </div>
          </div>

          {/* Net fiyat strip */}
          <div className="rounded-[2rem] border border-[#f1ddcf] bg-[linear-gradient(135deg,#fff8f2,#ffffff)] px-6 py-5 shadow-[0_20px_70px_rgba(15,23,42,0.04)]" data-testid="pricing-offer-strip">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[#d16024]" data-testid="pricing-offer-eyebrow">Net fiyat politikası</p>
                <p className="mt-2 text-base font-semibold text-slate-900" data-testid="pricing-offer-title">
                  Gizli sürpriz maliyetler yerine kurulum, operasyon ve entegrasyon kapsamını baştan netleştiriyoruz.
                </p>
              </div>
              <div className="rounded-full bg-white px-4 py-2 text-sm font-semibold text-slate-700" data-testid="pricing-offer-badge">
                KDV dahil fiyatlar
              </div>
            </div>
          </div>

          {/* Pricing Plan Grid */}
          <div className="grid gap-6 lg:grid-cols-2 2xl:grid-cols-4" data-testid="pricing-plan-grid">
            {packages.map((pkg) => (
              <SyrocePricingCard key={`${billingCycle}-${pkg.key}`} pkg={pkg} billingCycle={billingCycle} testIdPrefix="pricing-plan" />
            ))}
          </div>

          {/* Note */}
          <div className="text-center text-xs text-slate-500 max-w-3xl mx-auto leading-6" data-testid="pricing-note">
            Yukarıdaki fiyatlara KDV, kurulum ve ilk yıl kullanım ücretleri, hizmet (Altyapı, Destek, SSL, CDN v.b) ve lisans bedelleri dahildir.
            Kampanyalar birleştirilemez ve kontenjan ile sınırlıdır.
          </div>
        </section>

        {/* Comparison Table */}
        <div className="overflow-x-auto" data-testid="pricing-comparison-scroll-wrap">
          <SyrocePricingComparison packages={packages} testIdPrefix="pricing-comparison" />
        </div>

        {/* FAQ Section */}
        <SyroceFaqSection
          items={SYROCE_FAQS}
          title="Sıkça sorulan sorular"
          description="Paketlerin kapsamı, E-Tablo entegrasyonu, sözleşme modeli ve geçiş süreci hakkında en çok gelen soruları burada topladık."
          sectionTestId="pricing-faq-section"
        />

        {/* Contact Section */}
        <section className="grid gap-8 lg:grid-cols-2" data-testid="pricing-contact-section">
          <div className="rounded-[2rem] bg-[linear-gradient(135deg,#2563EB,#0EA5E9)] p-8 text-white shadow-[0_28px_90px_rgba(37,99,235,0.24)] lg:p-10">
            <p className="text-sm font-semibold uppercase tracking-[0.24em] text-blue-100" data-testid="pricing-contact-eyebrow">
              Hazırsanız başlayalım
            </p>
            <h2 className="mt-3 text-3xl font-extrabold tracking-[-0.03em] lg:text-4xl" style={{ fontFamily: "Manrope, Inter, sans-serif" }} data-testid="pricing-contact-title">
              Önce deneyin, sonra size uyan paketi birlikte netleştirelim
            </h2>
            <div className="mt-6 flex flex-wrap gap-3" data-testid="pricing-contact-cta-group">
              <Button asChild className="h-12 rounded-full bg-white px-6 text-sm font-semibold text-[#2563EB] hover:bg-slate-100" data-testid="pricing-contact-primary-cta">
                <Link to="/signup?plan=trial&selectedPlan=pro">14 Gün Ücretsiz Dene</Link>
              </Button>
              <Button asChild variant="outline" className="h-12 rounded-full border-white/50 bg-transparent px-6 text-sm font-semibold text-white hover:bg-white/10" data-testid="pricing-contact-secondary-cta">
                <Link to="/demo">Demo ve teklif iste</Link>
              </Button>
            </div>
          </div>

          <div className="rounded-[2rem] border border-slate-200 bg-white p-8 shadow-sm lg:p-10" data-testid="pricing-contact-info">
            <h3 className="text-xl font-bold text-slate-900" style={{ fontFamily: "Manrope, Inter, sans-serif" }} data-testid="pricing-contact-info-title">
              Bize Ulaşın
            </h3>
            <p className="mt-2 text-sm text-slate-600">
              Sorularınız için bize ulaşabilir, özel teklif talep edebilirsiniz.
            </p>
            <div className="mt-6 space-y-4">
              <div className="flex items-center gap-3 text-sm text-slate-700" data-testid="pricing-contact-phone">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-slate-100">
                  <Phone className="h-4 w-4 text-slate-600" />
                </div>
                <div>
                  <p className="text-xs text-slate-500">Telefon</p>
                  <p className="font-medium">0 850 840 00 60</p>
                </div>
              </div>
              <div className="flex items-center gap-3 text-sm text-slate-700" data-testid="pricing-contact-email">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-slate-100">
                  <Mail className="h-4 w-4 text-slate-600" />
                </div>
                <div>
                  <p className="text-xs text-slate-500">E-posta</p>
                  <p className="font-medium">info@syroce.com</p>
                </div>
              </div>
              <div className="flex items-center gap-3 text-sm text-slate-700" data-testid="pricing-contact-hours">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-slate-100">
                  <Clock className="h-4 w-4 text-slate-600" />
                </div>
                <div>
                  <p className="text-xs text-slate-500">Çalışma saatleri</p>
                  <p className="font-medium">Pazartesi - Cuma, 09:00 - 18:00</p>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Footer */}
        <footer className="border-t border-slate-200 pt-8 pb-4 text-center text-xs text-slate-500" data-testid="pricing-footer">
          <p>&copy; {new Date().getFullYear()} Syroce. Tüm hakları saklıdır.</p>
          <div className="mt-2 flex items-center justify-center gap-4">
            <Link to="/privacy" className="hover:text-slate-700 transition-colors">Gizlilik Politikası</Link>
            <Link to="/terms" className="hover:text-slate-700 transition-colors">Kullanım Şartları</Link>
          </div>
        </footer>
      </div>
    </div>
  );
}
