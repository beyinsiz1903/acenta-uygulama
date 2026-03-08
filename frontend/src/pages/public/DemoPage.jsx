import React from "react";
import { Link } from "react-router-dom";
import { ArrowRight, BarChart3, CheckCircle2, Files, MessageSquareMore, NotebookPen, Plane, ShieldCheck, UsersRound } from "lucide-react";

import { Button } from "../../components/ui/button";
import { useSeo } from "../../hooks/useSeo";

const PROBLEMS = [
  {
    icon: Files,
    title: "Excel ile rezervasyon takibi",
    text: "Rezervasyon dosyaları çoğaldıkça hata payı artar ve ekip aynı veride buluşamaz.",
  },
  {
    icon: MessageSquareMore,
    title: "WhatsApp üzerinden müşteri yönetimi",
    text: "Müşteri konuşmaları dağılır, kim ne istedi sorusu ekip içinde sürekli tekrar eder.",
  },
  {
    icon: NotebookPen,
    title: "Dağınık operasyon süreçleri",
    text: "Tur, otel ve ödeme takibi farklı yerlerde tutulduğu için operasyon yavaşlar.",
  },
];

const SOLUTIONS = [
  {
    icon: ShieldCheck,
    title: "Rezervasyon yönetimi",
    text: "Gelen talebi, durumu ve sonraki adımı aynı ekranda takip edin.",
  },
  {
    icon: UsersRound,
    title: "Müşteri yönetimi",
    text: "Müşteri detayları, geçmiş rezervasyonları ve ekip notları tek yerde toplansın.",
  },
  {
    icon: Plane,
    title: "Tur ve otel takibi",
    text: "Tur, otel ve operasyon akışını tek panelde görün; dağınıklığı azaltın.",
  },
  {
    icon: BarChart3,
    title: "Raporlama",
    text: "Satış ve operasyon performansını net raporlarla izleyin, tahmin değil veriyle yönetin.",
  },
];

const HERO_BENEFITS = [
  "14 gün ücretsiz trial",
  "100 rezervasyon ile gerçek kullanım testi",
  "2 kullanıcı ile ekip akışını görün",
];

export default function DemoPage() {
  useSeo({
    title: "Acentelerde Excel dönemi bitiyor",
    description: "Syroce ile rezervasyon, müşteri ve operasyon süreçlerini tek panelden yönetin. 14 gün ücretsiz deneyin.",
    canonicalPath: "/demo",
    type: "website",
  });

  return (
    <div
      className="min-h-screen bg-[linear-gradient(180deg,#fbfaf7_0%,#fff4ec_42%,#f6fbfa_100%)] text-slate-900"
      style={{ fontFamily: "Inter, sans-serif" }}
      data-testid="demo-page"
    >
      <div className="mx-auto flex max-w-7xl flex-col gap-16 px-4 py-12 sm:px-6 lg:px-8 lg:py-20">
        <section
          className="grid items-center gap-8 overflow-hidden rounded-[2.25rem] border border-[#f1ddcf] bg-white/90 p-8 shadow-[0_30px_120px_rgba(38,70,83,0.10)] backdrop-blur lg:grid-cols-[1.08fr_0.92fr] lg:p-12"
          data-testid="demo-hero-section"
        >
          <div className="space-y-6">
            <div className="inline-flex items-center gap-2 rounded-full border border-[#f6d2bd] bg-[#fff4ec] px-4 py-2 text-xs font-semibold uppercase tracking-[0.24em] text-[#d16024]" data-testid="demo-hero-badge">
              <CheckCircle2 className="h-4 w-4" />
              14 Gün Ücretsiz Deneyin
            </div>

            <div className="space-y-4">
              <p className="text-sm font-semibold uppercase tracking-[0.28em] text-[#264653]" data-testid="demo-hero-eyebrow">
                Turizm acenteleri için
              </p>
              <h1 className="text-4xl font-extrabold leading-[1.02] tracking-[-0.04em] text-slate-900 sm:text-5xl lg:text-6xl" style={{ fontFamily: "Manrope, Inter, sans-serif" }} data-testid="demo-hero-title">
                Acentelerde Excel dönemi bitiyor
              </h1>
              <p className="max-w-2xl text-base leading-7 text-slate-600 md:text-lg" data-testid="demo-hero-subtitle">
                Syroce ile rezervasyon, müşteri ve operasyon süreçlerini tek panelden yönetin. 14 gün ücretsiz deneyin.
              </p>
            </div>

            <div className="flex flex-wrap gap-3" data-testid="demo-hero-cta-group">
              <Button asChild className="h-12 rounded-xl bg-[#f3722c] px-6 text-sm font-semibold text-white hover:bg-[#e05d1b]" data-testid="demo-hero-primary-cta">
                <Link to="/signup?plan=trial">Demo Hesap Oluştur</Link>
              </Button>
              <Button asChild variant="outline" className="h-12 rounded-xl border-[#264653] px-6 text-sm font-semibold text-[#264653] hover:bg-[#fdf8f2]" data-testid="demo-hero-secondary-cta">
                <Link to="/pricing">Fiyatları Gör</Link>
              </Button>
            </div>

            <div className="grid gap-3 sm:grid-cols-3" data-testid="demo-hero-benefits">
              {HERO_BENEFITS.map((item, index) => (
                <div key={item} className="rounded-2xl border border-slate-200 bg-[#fbfcfc] px-4 py-4 text-sm leading-6 text-slate-700" data-testid={`demo-hero-benefit-${index + 1}`}>
                  {item}
                </div>
              ))}
            </div>
          </div>

          <div className="relative rounded-[2rem] bg-[#264653] p-6 text-white shadow-[0_25px_80px_rgba(38,70,83,0.15)]" data-testid="demo-hero-visual">
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(233,196,106,0.22),transparent_38%),radial-gradient(circle_at_bottom_left,rgba(42,157,143,0.24),transparent_40%)]" />
            <div className="relative space-y-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[#e9c46a]" data-testid="demo-hero-visual-eyebrow">
                  Önce böyle
                </p>
                <div className="mt-4 grid gap-3" data-testid="demo-hero-chaos-list">
                  {[
                    { icon: Files, text: "Excel dosyaları" },
                    { icon: MessageSquareMore, text: "WhatsApp mesajları" },
                    { icon: NotebookPen, text: "Dağınık operasyon notları" },
                  ].map((item, index) => (
                    <div key={item.text} className="flex items-center gap-3 rounded-2xl bg-white/10 px-4 py-3" data-testid={`demo-hero-chaos-item-${index + 1}`}>
                      <item.icon className="h-4 w-4 text-[#e9c46a]" />
                      <span className="text-sm text-white/90">{item.text}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="flex justify-center" data-testid="demo-hero-arrow-wrap">
                <ArrowRight className="h-5 w-5 text-white/80" />
              </div>

              <div className="rounded-[1.6rem] bg-white px-5 py-5 text-slate-900" data-testid="demo-hero-solution-panel">
                <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[#2a9d8f]" data-testid="demo-hero-solution-panel-eyebrow">
                  Sonra böyle
                </p>
                <p className="mt-3 text-2xl font-extrabold tracking-[-0.03em]" style={{ fontFamily: "Manrope, Inter, sans-serif" }} data-testid="demo-hero-solution-panel-title">
                  Tek panel, net operasyon
                </p>
                <div className="mt-4 grid gap-3" data-testid="demo-hero-solution-panel-list">
                  {[
                    "Rezervasyonlar görünür",
                    "Müşteri geçmişi tek yerde",
                    "Raporlar hazır",
                  ].map((item, index) => (
                    <div key={item} className="rounded-2xl bg-[#f6fbfa] px-4 py-3 text-sm font-semibold text-slate-900" data-testid={`demo-hero-solution-panel-item-${index + 1}`}>
                      {item}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="rounded-[2rem] border border-[#f1e3d9] bg-[#fffaf6] p-8 lg:p-10" data-testid="demo-problem-section">
          <div className="max-w-3xl">
            <p className="text-sm font-semibold uppercase tracking-[0.24em] text-[#d16024]" data-testid="demo-problem-eyebrow">
              Problem
            </p>
            <h2 className="mt-3 text-4xl font-extrabold tracking-[-0.03em] text-slate-900" style={{ fontFamily: "Manrope, Inter, sans-serif" }} data-testid="demo-problem-title">
              Acentelerde en yaygın sorunlar
            </h2>
          </div>

          <div className="mt-8 grid gap-5 lg:grid-cols-3" data-testid="demo-problem-grid">
            {PROBLEMS.map((item, index) => (
              <article key={item.title} className="rounded-[1.75rem] border border-white bg-white p-6 shadow-[0_20px_60px_rgba(38,70,83,0.06)]" data-testid={`demo-problem-card-${index + 1}`}>
                <item.icon className="h-5 w-5 text-[#f3722c]" />
                <h3 className="mt-4 text-2xl font-extrabold tracking-[-0.03em] text-slate-900" style={{ fontFamily: "Manrope, Inter, sans-serif" }} data-testid={`demo-problem-card-title-${index + 1}`}>
                  {item.title}
                </h3>
                <p className="mt-3 text-sm leading-6 text-slate-600" data-testid={`demo-problem-card-text-${index + 1}`}>
                  {item.text}
                </p>
              </article>
            ))}
          </div>
        </section>

        <section className="space-y-8" data-testid="demo-solution-section">
          <div className="max-w-3xl space-y-4">
            <p className="text-sm font-semibold uppercase tracking-[0.24em] text-[#2a9d8f]" data-testid="demo-solution-eyebrow">
              Çözüm
            </p>
            <h2 className="text-4xl font-extrabold tracking-[-0.03em] text-slate-900" style={{ fontFamily: "Manrope, Inter, sans-serif" }} data-testid="demo-solution-title">
              Syroce ile tüm operasyon tek panelde
            </h2>
          </div>

          <div className="grid gap-5 md:grid-cols-2" data-testid="demo-solution-grid">
            {SOLUTIONS.map((item, index) => (
              <article key={item.title} className="rounded-[1.75rem] border border-[#dce9e7] bg-white/90 p-6 shadow-[0_20px_60px_rgba(38,70,83,0.08)]" data-testid={`demo-solution-card-${index + 1}`}>
                <item.icon className="h-5 w-5 text-[#2a9d8f]" />
                <h3 className="mt-4 text-2xl font-extrabold tracking-[-0.03em] text-slate-900" style={{ fontFamily: "Manrope, Inter, sans-serif" }} data-testid={`demo-solution-card-title-${index + 1}`}>
                  {item.title}
                </h3>
                <p className="mt-3 text-sm leading-6 text-slate-600" data-testid={`demo-solution-card-text-${index + 1}`}>
                  {item.text}
                </p>
              </article>
            ))}
          </div>
        </section>

        <section className="rounded-[2rem] bg-[#264653] px-8 py-10 text-white lg:px-12" data-testid="demo-final-cta-section">
          <div className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.24em] text-[#e9c46a]" data-testid="demo-final-cta-eyebrow">
                Şimdi deneyin
              </p>
              <h2 className="mt-3 text-4xl font-extrabold tracking-[-0.03em]" style={{ fontFamily: "Manrope, Inter, sans-serif" }} data-testid="demo-final-cta-title">
                14 Gün Ücretsiz Dene
              </h2>
              <p className="mt-3 max-w-2xl text-base leading-7 text-white/80" data-testid="demo-final-cta-text">
                Demo hesabınızı açın, ilk rezervasyon akışınızı görün ve sonra size uyan planı seçin.
              </p>
            </div>

            <div className="flex flex-wrap gap-3" data-testid="demo-final-cta-group">
              <Button asChild className="h-12 rounded-xl bg-[#f3722c] px-6 text-sm font-semibold text-white hover:bg-[#e05d1b]" data-testid="demo-final-cta-primary">
                <Link to="/signup?plan=trial">
                  14 Gün Ücretsiz Dene
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Link>
              </Button>
              <Button asChild variant="outline" className="h-12 rounded-xl border-white/30 bg-transparent px-6 text-sm font-semibold text-white hover:bg-white/10" data-testid="demo-final-cta-secondary">
                <Link to="/signup?plan=trial&selectedPlan=pro">Hemen Başla</Link>
              </Button>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}