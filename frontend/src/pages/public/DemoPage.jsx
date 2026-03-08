import React from "react";
import { Link } from "react-router-dom";
import { ArrowRight, BarChart3, CheckCircle2, Files, MessageSquareMore, NotebookPen, ShieldCheck, UsersRound } from "lucide-react";

import { Button } from "../../components/ui/button";
import { useSeo } from "../../hooks/useSeo";

const HERO_IMAGE = "https://images.unsplash.com/photo-1720139291006-585bc5d18b3b?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2Njd8MHwxfHNlYXJjaHwyfHxtb2Rlcm4lMjB0cmF2ZWwlMjBhZ2VudCUyMGhhcHB5JTIwd29ya2luZyUyMG9mZmljZXxlbnwwfHx8fDE3NzI5Nzg5NTR8MA&ixlib=rb-4.1.0&q=85";
const PROBLEM_IMAGE = "https://images.unsplash.com/photo-1566699270403-3f7e3f340664?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjA2ODl8MHwxfHNlYXJjaHwxfHxmcnVzdHJhdGVkJTIwb2ZmaWNlJTIwd29ya2VyJTIwbWVzc3klMjBkZXNrJTIwcGFwZXJ3b3JrfGVufDB8fHx8MTc3Mjk3ODk1NXww&ixlib=rb-4.1.0&q=85";

const PROBLEMS = [
  { icon: Files, label: "Excel dosyaları" },
  { icon: MessageSquareMore, label: "WhatsApp karmaşası" },
  { icon: NotebookPen, label: "Kağıt notlar" },
];

const SOLUTIONS = [
  {
    icon: UsersRound,
    title: "Müşterileri tek yerde toplayın",
    desc: "Kim ne istedi, hangi rezervasyon bekliyor, hangi ödeme açık kaldı anında görün.",
  },
  {
    icon: ShieldCheck,
    title: "Operasyonu tek panelden yönetin",
    desc: "Rezervasyon, operasyon ve ekip akışını dağınık araçlardan çıkarıp tek yere taşıyın.",
  },
  {
    icon: BarChart3,
    title: "Raporları gerçekten kullanın",
    desc: "Satışı, performansı ve kapasiteyi gözünüzün önünde tutun; sezgilerle değil verilerle karar verin.",
  },
];

const FUNNEL = [
  "Demo hesap oluştur",
  "14 günlük Trial ile sistemi test et",
  "Usage warning ile doğru zamanı gör",
  "Planını seçip devam et",
];

export default function DemoPage() {
  useSeo({
    title: "Acentelerde Excel dönemi bitiyor",
    description: "Rezervasyon, müşteri ve ödemeleri tek panelden yönetin. 14 gün ücretsiz deneyin ve demo hesabınızı açın.",
    canonicalPath: "/demo",
    type: "website",
  });

  return (
    <div className="min-h-screen bg-[linear-gradient(180deg,#fdfbf7_0%,#fff7f2_48%,#f6faf9_100%)] text-slate-900" style={{ fontFamily: "Inter, sans-serif" }} data-testid="demo-page">
      <div className="mx-auto flex max-w-7xl flex-col gap-20 px-4 py-12 sm:px-6 lg:px-8 lg:py-20">
        <section className="grid items-center gap-8 rounded-[2rem] border border-[#f2d8ca] bg-white/85 p-8 shadow-[0_30px_120px_rgba(38,70,83,0.10)] backdrop-blur lg:grid-cols-[1.05fr_0.95fr] lg:p-12" data-testid="demo-hero-section">
          <div className="space-y-6">
            <div className="inline-flex items-center gap-2 rounded-full border border-[#f7d7c4] bg-[#fff3ec] px-4 py-2 text-xs font-semibold uppercase tracking-[0.24em] text-[#d16024]" data-testid="demo-hero-badge">
              <CheckCircle2 className="h-4 w-4" />
              14 Gün Ücretsiz Deneyin
            </div>

            <div className="space-y-4">
              <p className="text-sm font-semibold uppercase tracking-[0.28em] text-[#264653]" data-testid="demo-hero-eyebrow">Turizm Acenteleri İçin Bulut Yazılım</p>
              <h1 className="text-4xl font-extrabold leading-[1.02] tracking-[-0.03em] sm:text-5xl lg:text-6xl" style={{ fontFamily: "Manrope, Inter, sans-serif" }} data-testid="demo-hero-title">
                Acentelerde <span className="text-[#f3722c]">Excel dönemi</span> bitiyor
              </h1>
              <p className="max-w-2xl text-base leading-7 text-slate-600 md:text-lg" data-testid="demo-hero-subtitle">
                Rezervasyon, müşteri ve ödemeleri tek panelden yönetin. 14 gün ücretsiz deneyin, dağınık operasyonunuzu birkaç dakikada görünür hale getirin.
              </p>
            </div>

            <div className="flex flex-wrap gap-3">
              <Button asChild className="h-12 rounded-xl bg-[#f3722c] px-6 text-sm font-semibold text-white hover:bg-[#e05d1b]" data-testid="demo-hero-primary-cta">
                <Link to="/signup?plan=trial">Demo Hesap Oluştur</Link>
              </Button>
              <Button asChild variant="outline" className="h-12 rounded-xl border-[#264653] px-6 text-sm font-semibold text-[#264653] hover:bg-[#fdfbf7]" data-testid="demo-hero-secondary-cta">
                <Link to="/pricing">Fiyatları Gör</Link>
              </Button>
            </div>

            <div className="grid gap-3 sm:grid-cols-3" data-testid="demo-hero-benefits">
              {[
                "100 rezervasyon ile gerçek kullanım testi",
                "2 kullanıcı ile ekip akışını gör",
                "Trial sonunda planını net seç",
              ].map((item, index) => (
                <div key={item} className="rounded-2xl border border-slate-200 bg-slate-50/80 px-4 py-4 text-sm leading-6 text-slate-700" data-testid={`demo-hero-benefit-${index + 1}`}>
                  {item}
                </div>
              ))}
            </div>
          </div>

          <div className="relative overflow-hidden rounded-[1.75rem] border border-white/60 bg-[#264653]" data-testid="demo-hero-visual">
            <img src={HERO_IMAGE} alt="Travel agent working in a modern office" className="aspect-[4/4.2] w-full object-cover" data-testid="demo-hero-image" />
            <div className="absolute inset-0 bg-[linear-gradient(180deg,rgba(38,70,83,0.10),rgba(38,70,83,0.55))]" />
            <div className="absolute bottom-0 left-0 right-0 p-6 text-white">
              <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[#e9c46a]" data-testid="demo-hero-visual-eyebrow">Canlı akış</p>
              <p className="mt-2 text-2xl font-extrabold tracking-[-0.03em]" style={{ fontFamily: "Manrope, Inter, sans-serif" }} data-testid="demo-hero-visual-title">
                Tek panel, daha az kayıp, daha hızlı dönüş
              </p>
            </div>
          </div>
        </section>

        <section className="grid gap-8 lg:grid-cols-[0.95fr_1.05fr]" data-testid="demo-problem-section">
          <div className="overflow-hidden rounded-[2rem] border border-[#ead7ce] bg-white shadow-[0_25px_80px_rgba(38,70,83,0.08)]" data-testid="demo-problem-image-wrap">
            <img src={PROBLEM_IMAGE} alt="Messy desk with papers" className="aspect-[4/4.1] w-full object-cover" data-testid="demo-problem-image" />
          </div>

          <div className="rounded-[2rem] border border-[#f1e4dc] bg-[#fffaf6] p-8" data-testid="demo-problem-copy">
            <p className="text-sm font-semibold uppercase tracking-[0.24em] text-[#d16024]" data-testid="demo-problem-eyebrow">Problem</p>
            <h2 className="mt-3 text-4xl font-extrabold tracking-[-0.03em] text-slate-900" style={{ fontFamily: "Manrope, Inter, sans-serif" }} data-testid="demo-problem-title">
              Hâlâ Excel ve WhatsApp arasında mı kayboluyorsunuz?
            </h2>
            <p className="mt-4 text-base leading-7 text-slate-600" data-testid="demo-problem-description">
              Notlar kaybolur, dosyalar karışır, müşteri bekler. Eski yöntemler sadece kafa karıştırmaz; satış ve operasyon hızınızı da yavaşlatır.
            </p>

            <div className="mt-8 grid gap-4 sm:grid-cols-3" data-testid="demo-problem-grid">
              {PROBLEMS.map((item, index) => (
                <div key={item.label} className="rounded-2xl border border-white bg-white p-5 text-center shadow-sm" data-testid={`demo-problem-card-${index + 1}`}>
                  <item.icon className="mx-auto h-5 w-5 text-[#f3722c]" />
                  <p className="mt-3 text-sm font-semibold text-slate-900" data-testid={`demo-problem-card-label-${index + 1}`}>{item.label}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="space-y-8" data-testid="demo-solution-section">
          <div className="max-w-3xl space-y-4">
            <p className="text-sm font-semibold uppercase tracking-[0.24em] text-[#2a9d8f]" data-testid="demo-solution-eyebrow">Çözüm</p>
            <h2 className="text-4xl font-extrabold tracking-[-0.03em] text-slate-900" style={{ fontFamily: "Manrope, Inter, sans-serif" }} data-testid="demo-solution-title">
              Tek panel, rezervasyon, müşteri, operasyon ve rapor
            </h2>
            <p className="text-base leading-7 text-slate-600" data-testid="demo-solution-description">
              Karmaşık iş akışını tek bir ekranda görün. Kim ne yapıyor, hangi rezervasyon nerede, hangi müşteri ne bekliyor; hepsi aynı yerde.
            </p>
          </div>

          <div className="grid gap-6 lg:grid-cols-3" data-testid="demo-solution-grid">
            {SOLUTIONS.map((item, index) => (
              <article key={item.title} className="rounded-[1.75rem] border border-[#dbe9e7] bg-white/85 p-6 shadow-[0_25px_80px_rgba(38,70,83,0.08)]" data-testid={`demo-solution-card-${index + 1}`}>
                <item.icon className="h-5 w-5 text-[#2a9d8f]" />
                <h3 className="mt-4 text-2xl font-extrabold tracking-[-0.03em] text-slate-900" style={{ fontFamily: "Manrope, Inter, sans-serif" }} data-testid={`demo-solution-card-title-${index + 1}`}>{item.title}</h3>
                <p className="mt-3 text-sm leading-6 text-slate-600" data-testid={`demo-solution-card-text-${index + 1}`}>{item.desc}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="rounded-[2rem] border border-[#dce8e7] bg-white/90 p-8 shadow-[0_25px_80px_rgba(38,70,83,0.08)] lg:p-10" data-testid="demo-funnel-section">
          <div className="flex flex-col gap-8 lg:flex-row lg:items-center lg:justify-between">
            <div className="max-w-2xl">
              <p className="text-sm font-semibold uppercase tracking-[0.24em] text-[#d16024]" data-testid="demo-funnel-eyebrow">Demo akışı</p>
              <h2 className="mt-3 text-4xl font-extrabold tracking-[-0.03em] text-slate-900" style={{ fontFamily: "Manrope, Inter, sans-serif" }} data-testid="demo-funnel-title">
                Demo → Trial → Usage uyarısı → Plan seçimi
              </h2>
            </div>

            <Button asChild className="h-12 rounded-xl bg-[#264653] px-6 text-sm font-semibold text-white hover:bg-[#1f3742]" data-testid="demo-funnel-cta">
              <Link to="/signup?plan=trial">
                Hemen Başla
                <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
          </div>

          <div className="mt-8 grid gap-4 md:grid-cols-4" data-testid="demo-funnel-grid">
            {FUNNEL.map((step, index) => (
              <div key={step} className="rounded-2xl bg-[#f8fbfb] px-5 py-5" data-testid={`demo-funnel-step-${index + 1}`}>
                <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[#2a9d8f]" data-testid={`demo-funnel-step-number-${index + 1}`}>Adım {index + 1}</p>
                <p className="mt-3 text-sm font-semibold leading-6 text-slate-900" data-testid={`demo-funnel-step-text-${index + 1}`}>{step}</p>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}