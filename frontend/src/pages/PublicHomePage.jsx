import React, { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  BarChart3,
  CalendarRange,
  CheckCircle2,
  ChevronRight,
  CreditCard,
  Menu,
  Network,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  UserSquare2,
  Users2,
  WalletCards,
  X,
} from "lucide-react";

import { LandingDashboardMockup } from "../components/landing/LandingDashboardMockup";
import { LandingSectionHeading } from "../components/landing/LandingSectionHeading";
import { Button } from "../components/ui/button";
import { useSeo } from "../hooks/useSeo";

const NAV_LINKS = [
  { label: "Çözüm", href: "#cozumler" },
  { label: "Nasıl Çalışır", href: "#nasil-calisir" },
  { label: "Fiyatlandırma", href: "#fiyatlandirma" },
  { label: "Demo", href: "#final-cta" },
];

const TRUST_METRICS = [
  { value: "5000+", label: "rezervasyon yönetildi" },
  { value: "%40", label: "operasyon süresi tasarrufu" },
  { value: "7/24", label: "bulut erişim ve ekip görünürlüğü" },
  { value: "5 dk", label: "ilk hesap kurulumu" },
];

const PROBLEMS = [
  {
    icon: CalendarRange,
    title: "Excel ile rezervasyon takibi",
    text: "Versiyon karmaşası büyüdükçe ekip aynı rezervasyonda farklı bilgiyle çalışır.",
  },
  {
    icon: UserSquare2,
    title: "WhatsApp ile müşteri yönetimi",
    text: "Teklif, not ve ödeme bilgileri kişisel sohbetlerde kaldığı için müşteri hafızası kaybolur.",
  },
  {
    icon: WalletCards,
    title: "Dağınık operasyon süreçleri",
    text: "Satış, operasyon ve finans ayrı sistemlerde ilerlediğinde tahsilat ve hata kontrolü yavaşlar.",
  },
];

const SOLUTIONS = [
  {
    icon: CalendarRange,
    title: "Rezervasyon yönetimi",
    text: "Durum, oda, tedarikçi, operasyon notu ve ödeme bilgisi tek akışta birleşir.",
    stat: "Her rezervasyonda tek kaynak",
  },
  {
    icon: Users2,
    title: "CRM müşteri yönetimi",
    text: "Müşteri geçmişi, teklif akışı ve ekip notları aynı müşteri kartında görünür.",
    stat: "Satış ekibi için ortak hafıza",
  },
  {
    icon: CreditCard,
    title: "Finans ve tahsilat",
    text: "Vadesi yaklaşan ödemeler, tahsilatlar ve komisyon dağılımı finans ekibine net görünür.",
    stat: "Nakit akışında görünürlük",
  },
  {
    icon: BarChart3,
    title: "Raporlama",
    text: "Rezervasyon hacmi, gelir kırılımı ve operasyon sağlığı anlık raporlarla izlenir.",
    stat: "Karar için hazır raporlar",
  },
];

const PREVIEW_PANELS = [
  {
    title: "Dashboard",
    subtitle: "KPI özeti, günlük operasyon ve tahsilat görünümü",
    badge: "Yönetici görünümü",
    tone: "from-blue-50 to-white",
  },
  {
    title: "Rezervasyon paneli",
    subtitle: "Durum, misafir, acente ve operasyon notu aynı kartta",
    badge: "Operasyon ekibi",
    tone: "from-sky-50 to-white",
  },
  {
    title: "Müşteri listesi & finans raporu",
    subtitle: "CRM geçmişi ve tahsilat akışını birlikte okuyun",
    badge: "Satış + finans",
    tone: "from-slate-50 to-white",
  },
];

const STEPS = [
  {
    step: "01",
    title: "Hesap oluştur",
    text: "14 günlük trial hesabınızı açın; kredi kartı olmadan ekibinizi içeri alın.",
  },
  {
    step: "02",
    title: "Ürünlerini tanımla",
    text: "Otel, tur, fiyat ve komisyon kurallarınızı 5 dakikada sisteme girin.",
  },
  {
    step: "03",
    title: "Rezervasyonları yönet",
    text: "Satış, operasyon ve finans ekipleri aynı panelde çalışmaya başlasın.",
  },
];

const ROI_POINTS = [
  "Daha hızlı rezervasyon akışı",
  "Daha az operasyon hatası",
  "Daha hızlı tahsilat ve takip",
];

const NETWORK_POINTS = [
  "Alt acentelerle aynı ürün havuzunu paylaşın",
  "Komisyon kurallarını kanal bazlı yönetin",
  "B2B iş ortaklıklarını ek panel açmadan büyütün",
];

const PRICING = {
  monthly: [
    {
      key: "starter",
      name: "Starter",
      price: "₺990",
      period: "/ ay",
      description: "Excel'den çıkmak isteyen çekirdek ekipler için.",
      features: ["100 rezervasyon", "3 kullanıcı", "Temel raporlar"],
      cta: "/signup?plan=trial&selectedPlan=starter",
    },
    {
      key: "pro",
      name: "Pro",
      price: "₺2.490",
      period: "/ ay",
      description: "Rezervasyon ve operasyon hacmi büyüyen acenteler için.",
      features: ["500 rezervasyon", "10 kullanıcı", "Tüm raporlar + entegrasyonlar"],
      featured: true,
      cta: "/signup?plan=trial&selectedPlan=pro",
    },
    {
      key: "enterprise",
      name: "Enterprise",
      price: "₺6.990",
      period: "/ ay",
      description: "Sınırsız hacim, API ve özel entegrasyon isteyen ekipler için.",
      features: ["Sınırsız rezervasyon", "API erişimi", "Özel entegrasyon"],
      cta: "/login",
    },
  ],
  yearly: [
    {
      key: "starter",
      name: "Starter",
      price: "₺9.900",
      period: "/ yıl",
      description: "Yıllık geçişle ekip maliyetini sabitleyin.",
      features: ["100 rezervasyon", "3 kullanıcı", "2 ay avantaj"],
      cta: "/signup?plan=trial&selectedPlan=starter&billingCycle=yearly",
    },
    {
      key: "pro",
      name: "Pro",
      price: "₺24.900",
      period: "/ yıl",
      description: "Büyüme odaklı acenteler için en popüler plan.",
      features: ["500 rezervasyon", "10 kullanıcı", "2 ay avantaj + entegrasyonlar"],
      featured: true,
      cta: "/signup?plan=trial&selectedPlan=pro&billingCycle=yearly",
    },
    {
      key: "enterprise",
      name: "Enterprise",
      price: "Özel teklif",
      period: "",
      description: "Yüksek hacimli ağlar için sözleşmeli kurulum.",
      features: ["Sınırsız rezervasyon", "Özel entegrasyon", "API erişimi"],
      cta: "/login",
    },
  ],
};

const HERO_SIGNALS = ["Kurulum gerektirmez", "5 dakikada hesap aç", "Kredi kartı gerekmez"];

function ProblemBoard({ mode }) {
  if (mode === "old") {
    return (
      <div className="grid gap-4 md:grid-cols-3" data-testid="landing-problem-board-old">
        {[
          { title: "Excel", items: ["Versiyon karmaşası", "Manuel durum güncelleme", "Kopyala-yapıştır işlem"] },
          { title: "WhatsApp", items: ["Kişisel telefonlarda müşteri geçmişi", "Kaybolan notlar", "Takip edilemeyen talepler"] },
          { title: "Ayrı finans", items: ["Geciken tahsilat", "Dağınık komisyon hesabı", "Rapor için ekstra efor"] },
        ].map((column, index) => (
          <article key={column.title} className="rounded-[24px] border border-rose-100 bg-white p-5 shadow-[0_14px_40px_rgba(15,23,42,0.05)]" data-testid={`landing-problem-column-${index + 1}`}>
            <p className="text-sm font-semibold uppercase tracking-[0.24em] text-rose-500" data-testid={`landing-problem-column-title-${index + 1}`}>
              {column.title}
            </p>
            <div className="mt-4 space-y-3" data-testid={`landing-problem-column-items-${index + 1}`}>
              {column.items.map((item, itemIndex) => (
                <div key={item} className="rounded-2xl bg-rose-50 px-4 py-3 text-sm text-slate-700" data-testid={`landing-problem-column-item-${index + 1}-${itemIndex + 1}`}>
                  {item}
                </div>
              ))}
            </div>
          </article>
        ))}
      </div>
    );
  }

  return (
    <div className="rounded-[30px] border border-blue-100 bg-[linear-gradient(180deg,rgba(255,255,255,0.98),rgba(239,246,255,0.78))] p-5 shadow-[0_20px_70px_rgba(37,99,235,0.12)]" data-testid="landing-problem-board-new">
      <div className="grid gap-4 lg:grid-cols-[0.95fr_1.05fr]" data-testid="landing-problem-board-new-grid">
        <div className="rounded-[24px] bg-slate-950 p-5 text-white" data-testid="landing-problem-board-new-summary">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-sky-200/80" data-testid="landing-problem-board-new-eyebrow">
            Syroce çalışma akışı
          </p>
          <h3 className="mt-3 text-2xl font-extrabold tracking-tight" data-testid="landing-problem-board-new-title">
            Satış, operasyon ve finans aynı panelde hizalanır.
          </h3>
          <div className="mt-6 space-y-3" data-testid="landing-problem-board-new-list">
            {[
              "Rezervasyon durumları ekipler arasında anlık görünür.",
              "Müşteri geçmişi ve teklif akışı tek müşteri kartında tutulur.",
              "Tahsilat ve komisyon takibi finans paneline otomatik akar.",
            ].map((item, index) => (
              <div key={item} className="rounded-2xl bg-white/10 px-4 py-3 text-sm text-white/90" data-testid={`landing-problem-board-new-item-${index + 1}`}>
                {item}
              </div>
            ))}
          </div>
        </div>
        <LandingDashboardMockup compact testIdPrefix="landing-problem-board-mockup" />
      </div>
    </div>
  );
}

export default function PublicHomePage() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [problemMode, setProblemMode] = useState("old");
  const [billingCycle, setBillingCycle] = useState("monthly");

  useSeo({
    title: "Syroce — Turizm Acentenizin Tüm Operasyonunu Tek Panelden Yönetin",
    description:
      "Rezervasyon, CRM, finans ve raporlamayı Excel yerine tek sistemde yönetin. 14 gün ücretsiz trial, kredi kartı gerekmez.",
    canonicalPath: "/",
    type: "website",
  });

  const pricingPlans = useMemo(() => PRICING[billingCycle], [billingCycle]);

  return (
    <div className="relative min-h-screen overflow-x-hidden bg-[#F8FAFC] text-slate-900" data-testid="syroce-landing-page">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(14,165,233,0.14),transparent_32%),radial-gradient(circle_at_top_left,rgba(37,99,235,0.12),transparent_28%),linear-gradient(180deg,rgba(248,250,252,0.92),rgba(248,250,252,1))]" />
      <div className="landing-noise pointer-events-none absolute inset-0 opacity-40" />

      <nav className="sticky top-0 z-50 border-b border-white/60 bg-[#F8FAFC]/82 backdrop-blur-2xl" data-testid="landing-navbar">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-4 sm:px-6 lg:px-8" data-testid="landing-navbar-inner">
          <Link to="/" className="flex items-center gap-3" data-testid="landing-navbar-logo-link">
            <div className="grid h-11 w-11 place-items-center rounded-2xl bg-[linear-gradient(135deg,#2563EB,#0EA5E9)] text-base font-bold text-white shadow-[0_16px_34px_rgba(37,99,235,0.28)]" data-testid="landing-navbar-logo-mark">
              S
            </div>
            <div>
              <p className="text-base font-extrabold tracking-tight text-slate-950" data-testid="landing-navbar-logo-name">Syroce</p>
              <p className="hidden text-xs uppercase tracking-[0.18em] text-slate-500 sm:block sm:tracking-[0.22em]" data-testid="landing-navbar-logo-tagline">Travel Agency Operating System</p>
            </div>
          </Link>

          <div className="hidden items-center gap-5 xl:gap-7 lg:flex" data-testid="landing-navbar-links">
            {NAV_LINKS.map((item, index) => (
              <a key={item.href} href={item.href} className="text-sm font-medium text-slate-600 transition-colors duration-200 hover:text-[#2563EB]" data-testid={`landing-navbar-link-${index + 1}`}>
                {item.label}
              </a>
            ))}
          </div>

          <div className="hidden items-center gap-2 xl:gap-3 lg:flex" data-testid="landing-navbar-cta-group">
            <Link to="/login" className="text-sm font-semibold text-slate-600 transition-colors duration-200 hover:text-[#2563EB]" data-testid="landing-navbar-login-link">
              Giriş
            </Link>
            <Button asChild variant="outline" className="h-11 rounded-full border-slate-200 px-5 text-sm font-semibold text-slate-700 hover:bg-slate-50" data-testid="landing-navbar-demo-cta">
              <Link to="/demo">Demo</Link>
            </Button>
            <Button asChild className="h-11 rounded-full bg-[linear-gradient(135deg,#2563EB,#0EA5E9)] px-5 text-sm font-semibold text-white shadow-[0_16px_34px_rgba(37,99,235,0.28)] hover:brightness-110" data-testid="landing-navbar-trial-cta">
              <Link to="/signup?plan=trial">14 Gün Ücretsiz Dene</Link>
            </Button>
          </div>

          <button type="button" className="inline-flex rounded-2xl border border-slate-200 bg-white p-2 text-slate-700 lg:hidden" onClick={() => setMobileMenuOpen((value) => !value)} data-testid="landing-mobile-menu-toggle" aria-label="Mobil menüyü aç">
            {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>

        {mobileMenuOpen ? (
          <div className="border-t border-slate-200 bg-white/96 px-4 py-4 backdrop-blur-2xl lg:hidden" data-testid="landing-mobile-menu">
            <div className="space-y-2" data-testid="landing-mobile-menu-links">
              {NAV_LINKS.map((item, index) => (
                <a key={item.href} href={item.href} className="block rounded-2xl px-3 py-3 text-sm font-medium text-slate-700 hover:bg-slate-50" onClick={() => setMobileMenuOpen(false)} data-testid={`landing-mobile-link-${index + 1}`}>
                  {item.label}
                </a>
              ))}
            </div>
            <div className="mt-4 grid gap-3" data-testid="landing-mobile-menu-ctas">
              <Button asChild variant="outline" className="h-11 rounded-full border-slate-200 text-sm font-semibold" data-testid="landing-mobile-login-cta">
                <Link to="/login" onClick={() => setMobileMenuOpen(false)}>Giriş Yap</Link>
              </Button>
              <Button asChild variant="outline" className="h-11 rounded-full border-slate-200 text-sm font-semibold" data-testid="landing-mobile-demo-cta">
                <Link to="/demo" onClick={() => setMobileMenuOpen(false)}>Demo Hesabı</Link>
              </Button>
              <Button asChild className="h-11 rounded-full bg-[linear-gradient(135deg,#2563EB,#0EA5E9)] text-sm font-semibold text-white" data-testid="landing-mobile-trial-cta">
                <Link to="/signup?plan=trial" onClick={() => setMobileMenuOpen(false)}>14 Gün Ücretsiz Dene</Link>
              </Button>
            </div>
          </div>
        ) : null}
      </nav>

      <main className="relative z-10" data-testid="landing-main">
        <section className="mx-auto grid max-w-7xl gap-10 px-4 pb-16 pt-10 sm:px-6 md:pb-24 md:pt-16 lg:gap-12 lg:px-8 lg:pt-20 xl:grid-cols-[minmax(0,0.94fr)_minmax(0,1.06fr)] xl:items-center xl:gap-14" data-testid="landing-hero-section">
          <div className="max-w-2xl lg:max-w-3xl" data-testid="landing-hero-copy">
            <div className="inline-flex items-center gap-2 rounded-full border border-blue-100 bg-white/80 px-4 py-2 text-xs font-semibold uppercase tracking-[0.24em] text-[#2563EB] shadow-[0_10px_30px_rgba(37,99,235,0.08)]" data-testid="landing-hero-badge">
              <Sparkles className="h-4 w-4" />
              Türkiye'deki turizm acenteleri için tasarlandı
            </div>
            <h1 className="mt-6 text-4xl font-extrabold leading-[1.04] tracking-[-0.05em] text-slate-950 sm:text-5xl lg:text-6xl" data-testid="landing-hero-title">
              Turizm Acentenizin
              <span className="block text-[#2563EB]" data-testid="landing-hero-title-highlight">Tüm Operasyonunu</span>
              Tek Panelden Yönetin
            </h1>
            <p className="mt-6 max-w-xl text-sm leading-8 text-slate-600 sm:text-base md:text-lg" data-testid="landing-hero-subtitle">
              Rezervasyonları, müşterileri ve finans süreçlerini Excel yerine tek sistemde yönetin. Syroce; satış, operasyon ve finans ekiplerini aynı ekranda buluşturur.
            </p>

            <div className="mt-8 flex flex-col gap-3 sm:flex-row" data-testid="landing-hero-cta-group">
              <Button asChild className="h-14 rounded-full bg-[linear-gradient(135deg,#2563EB,#0EA5E9)] px-7 text-base font-semibold text-white shadow-[0_20px_40px_rgba(37,99,235,0.28)] hover:brightness-110" data-testid="hero-cta-trial">
                <Link to="/signup?plan=trial">
                  14 Gün Ücretsiz Dene
                  <ArrowRight className="h-4 w-4" />
                </Link>
              </Button>
              <Button asChild variant="outline" className="h-14 rounded-full border-slate-200 bg-white/90 px-7 text-base font-semibold text-slate-700 shadow-[0_14px_34px_rgba(15,23,42,0.06)] hover:bg-white" data-testid="hero-cta-demo">
                <Link to="/demo">Demo Hesap Oluştur</Link>
              </Button>
            </div>

            <div className="mt-8 flex flex-wrap gap-3" data-testid="landing-hero-signals">
              {HERO_SIGNALS.map((signal, index) => (
                <div key={signal} className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white/85 px-4 py-2 text-sm font-medium text-slate-700" data-testid={`landing-hero-signal-${index + 1}`}>
                  <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                  {signal}
                </div>
              ))}
            </div>

            <div className="mt-6 flex flex-wrap items-center gap-2 text-sm text-slate-600" data-testid="landing-hero-login-helper">
              <span data-testid="landing-hero-login-helper-text">Zaten hesabınız var mı?</span>
              <Link to="/login" className="font-semibold text-[#2563EB] transition-colors duration-200 hover:text-[#1D4ED8]" data-testid="landing-hero-login-helper-link">
                Giriş Yap
              </Link>
            </div>
          </div>

          <div className="relative mx-auto w-full max-w-4xl xl:max-w-none xl:pl-2 2xl:pl-6" data-testid="landing-hero-visual-wrap">
            <div className="absolute -left-4 top-10 hidden rounded-[24px] border border-white/70 bg-white/80 px-4 py-3 shadow-[0_22px_50px_rgba(37,99,235,0.15)] backdrop-blur-xl 2xl:block" data-testid="landing-floating-card-1">
              <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-400" data-testid="landing-floating-card-1-label">Operasyon</p>
              <p className="mt-1 text-sm font-semibold text-slate-900" data-testid="landing-floating-card-1-value">12 yeni rezervasyon bugün</p>
            </div>
            <div className="absolute right-0 top-8 hidden rounded-[24px] border border-blue-100 bg-[#0F172A] px-4 py-3 text-white shadow-[0_24px_50px_rgba(15,23,42,0.28)] 2xl:block" data-testid="landing-floating-card-2">
              <p className="text-xs font-semibold uppercase tracking-[0.22em] text-sky-200/70" data-testid="landing-floating-card-2-label">Finans</p>
              <p className="mt-1 text-sm font-semibold" data-testid="landing-floating-card-2-value">Tahsilat süresi %40 daha hızlı</p>
            </div>
            <div className="mx-auto w-full max-w-[860px] xl:max-w-[760px]" data-testid="landing-hero-dashboard-wrap">
              <LandingDashboardMockup testIdPrefix="landing-hero-dashboard" />
            </div>
          </div>
        </section>

        <section className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8" data-testid="landing-trust-wrap">
          <div className="grid gap-4 rounded-[32px] border border-white/70 bg-white/72 px-6 py-6 shadow-[0_22px_60px_rgba(15,23,42,0.06)] backdrop-blur-xl md:grid-cols-4" data-testid="landing-trust-bar">
            {TRUST_METRICS.map((metric, index) => (
              <article key={metric.label} className="rounded-[24px] border border-slate-100 bg-white/80 px-5 py-5" data-testid={`landing-trust-metric-${index + 1}`}>
                <p className="text-3xl font-extrabold tracking-[-0.04em] text-slate-950" data-testid={`landing-trust-value-${index + 1}`}>{metric.value}</p>
                <p className="mt-2 text-sm text-slate-600" data-testid={`landing-trust-label-${index + 1}`}>{metric.label}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="mx-auto max-w-7xl px-4 py-24 sm:px-6 lg:px-8 lg:py-28" data-testid="landing-problem-section">
          <LandingSectionHeading
            eyebrow="Problem"
            title="Turizm Acentelerinde Operasyon Neden Zor?"
            description="Acenteler büyüdükçe rezervasyon, müşteri iletişimi ve tahsilat ayrı araçlarda dağılır. Sonuç: daha yavaş ekip, daha fazla hata ve daha geç tahsilat."
            testIdPrefix="landing-problem-heading"
          />

          <div className="mt-10 grid gap-6 lg:grid-cols-[0.88fr_1.12fr]" data-testid="landing-problem-layout">
            <div className="grid gap-5" data-testid="landing-problem-cards">
              {PROBLEMS.map((problem, index) => (
                <article key={problem.title} className="rounded-[28px] border border-white/80 bg-white/86 p-6 shadow-[0_20px_60px_rgba(15,23,42,0.05)]" data-testid={`landing-problem-card-${index + 1}`}>
                  <div className="flex items-start gap-4">
                    <div className="grid h-12 w-12 place-items-center rounded-2xl bg-rose-50 text-rose-500" data-testid={`landing-problem-icon-${index + 1}`}>
                      <problem.icon className="h-5 w-5" />
                    </div>
                    <div>
                      <h3 className="text-xl font-extrabold tracking-tight text-slate-950 sm:text-2xl" data-testid={`landing-problem-title-${index + 1}`}>
                        {problem.title}
                      </h3>
                      <p className="mt-3 text-sm leading-7 text-slate-600" data-testid={`landing-problem-text-${index + 1}`}>
                        {problem.text}
                      </p>
                    </div>
                  </div>
                </article>
              ))}
            </div>

            <div className="rounded-[32px] border border-slate-200 bg-[linear-gradient(180deg,rgba(255,255,255,0.94),rgba(241,245,249,0.82))] p-6 shadow-[0_24px_70px_rgba(15,23,42,0.06)]" data-testid="landing-problem-board">
              <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between" data-testid="landing-problem-board-header">
                <div>
                  <p className="text-sm font-semibold uppercase tracking-[0.24em] text-[#2563EB]" data-testid="landing-problem-board-eyebrow">
                    Eski düzen vs Syroce
                  </p>
                  <p className="mt-2 text-base font-semibold text-slate-900 sm:text-lg" data-testid="landing-problem-board-title">
                    Aynı operasyonun iki farklı deneyimi
                  </p>
                </div>
                <div className="inline-flex flex-wrap rounded-full border border-slate-200 bg-white p-1" data-testid="landing-problem-toggle-group">
                  <button type="button" className={`flex-1 rounded-full px-4 py-2 text-center text-sm font-semibold transition-colors duration-200 sm:flex-none ${problemMode === "old" ? "bg-slate-950 text-white" : "text-slate-600"}`} onClick={() => setProblemMode("old")} data-testid="landing-problem-toggle-old">
                    Eski düzen
                  </button>
                  <button type="button" className={`flex-1 rounded-full px-4 py-2 text-center text-sm font-semibold transition-colors duration-200 sm:flex-none ${problemMode === "new" ? "bg-[#2563EB] text-white" : "text-slate-600"}`} onClick={() => setProblemMode("new")} data-testid="landing-problem-toggle-new">
                    Syroce ile
                  </button>
                </div>
              </div>

              <div className="mt-6" data-testid="landing-problem-board-content">
                <ProblemBoard mode={problemMode} />
              </div>
            </div>
          </div>
        </section>

        <section id="cozumler" className="mx-auto max-w-7xl px-4 pb-24 sm:px-6 lg:px-8 lg:pb-28" data-testid="landing-solution-section">
          <LandingSectionHeading
            eyebrow="Çözüm"
            title="Syroce ile tüm operasyon tek panelde"
            description="Rezervasyon, CRM, finans, raporlama ve B2B ağını aynı ürün içinde birleştirerek ekipler arası kopukluğu kapatır."
            testIdPrefix="landing-solution-heading"
          />

          <div className="mt-10 grid gap-6 md:grid-cols-2" data-testid="landing-solution-grid">
            {SOLUTIONS.map((item, index) => (
              <article key={item.title} className="rounded-[30px] border border-white/80 bg-white/90 p-7 shadow-[0_22px_70px_rgba(15,23,42,0.05)]" data-testid={`landing-solution-card-${index + 1}`}>
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between" data-testid={`landing-solution-card-header-${index + 1}`}>
                  <div className="grid h-14 w-14 place-items-center rounded-[22px] bg-blue-50 text-[#2563EB]" data-testid={`landing-solution-icon-${index + 1}`}>
                    <item.icon className="h-6 w-6" />
                  </div>
                  <span className="max-w-full rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-slate-500" data-testid={`landing-solution-stat-${index + 1}`}>
                    {item.stat}
                  </span>
                </div>
                <h3 className="mt-6 text-xl font-extrabold tracking-tight text-slate-950 sm:text-2xl" data-testid={`landing-solution-title-${index + 1}`}>{item.title}</h3>
                <p className="mt-4 text-sm leading-7 text-slate-600" data-testid={`landing-solution-text-${index + 1}`}>{item.text}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="mx-auto max-w-7xl px-4 pb-24 sm:px-6 lg:px-8 lg:pb-28" data-testid="landing-product-preview-section">
          <div className="grid gap-8 lg:grid-cols-[0.88fr_1.12fr] lg:items-start" data-testid="landing-product-preview-layout">
            <div data-testid="landing-product-preview-copy">
              <LandingSectionHeading
                eyebrow="Ürün Önizleme"
                title="Dashboard, rezervasyon ve finans görünümü ilk bakışta anlaşılır"
                description="Ekipleriniz menüler arasında kaybolmadan rezervasyon durumunu, müşteri geçmişini ve tahsilat akışını aynı deneyimde görür."
                testIdPrefix="landing-product-preview-heading"
              />
              <div className="mt-6 flex flex-wrap gap-3" data-testid="landing-product-preview-cta-group">
                <Button asChild className="h-12 rounded-full bg-[linear-gradient(135deg,#2563EB,#0EA5E9)] px-6 text-sm font-semibold text-white hover:brightness-110" data-testid="landing-product-preview-trial-cta">
                  <Link to="/signup?plan=trial">Trial Başlat</Link>
                </Button>
                <Button asChild variant="outline" className="h-12 rounded-full border-slate-200 bg-white px-6 text-sm font-semibold text-slate-700" data-testid="landing-product-preview-demo-cta">
                  <Link to="/demo">Demo Hesabı Gör</Link>
                </Button>
              </div>
            </div>

            <div className="grid gap-5 xl:grid-cols-3" data-testid="landing-preview-card-grid">
              {PREVIEW_PANELS.map((panel, index) => (
                <article key={panel.title} className={`rounded-[30px] border border-white/80 bg-gradient-to-b ${panel.tone} p-5 shadow-[0_22px_70px_rgba(15,23,42,0.05)]`} data-testid={`landing-preview-card-${index + 1}`}>
                  <div className="flex items-center justify-between" data-testid={`landing-preview-card-header-${index + 1}`}>
                    <span className="rounded-full bg-white/90 px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-[#2563EB]" data-testid={`landing-preview-card-badge-${index + 1}`}>
                      {panel.badge}
                    </span>
                    <ChevronRight className="h-4 w-4 text-slate-400" />
                  </div>
                  <h3 className="mt-5 text-lg font-extrabold tracking-tight text-slate-950 sm:text-xl" data-testid={`landing-preview-card-title-${index + 1}`}>{panel.title}</h3>
                  <p className="mt-3 text-sm leading-7 text-slate-600" data-testid={`landing-preview-card-text-${index + 1}`}>{panel.subtitle}</p>
                  <div className="mt-5 rounded-[24px] border border-white/80 bg-white/90 p-4" data-testid={`landing-preview-card-mockup-${index + 1}`}>
                    <div className="flex items-center justify-between" data-testid={`landing-preview-card-topbar-${index + 1}`}>
                      <div className="flex gap-1.5" data-testid={`landing-preview-card-dots-${index + 1}`}>
                        <span className="h-2.5 w-2.5 rounded-full bg-slate-200" />
                        <span className="h-2.5 w-2.5 rounded-full bg-slate-200" />
                        <span className="h-2.5 w-2.5 rounded-full bg-slate-200" />
                      </div>
                      <span className="rounded-full bg-blue-50 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-[#2563EB]" data-testid={`landing-preview-card-chip-${index + 1}`}>
                        Canlı görünüm
                      </span>
                    </div>
                    <div className="mt-4 space-y-3" data-testid={`landing-preview-card-lines-${index + 1}`}>
                      <div className="h-3 rounded-full bg-slate-100" data-testid={`landing-preview-card-line-${index + 1}-1`} />
                      <div className="grid grid-cols-2 gap-3" data-testid={`landing-preview-card-grid-${index + 1}`}>
                        <div className="rounded-2xl bg-slate-50 px-3 py-4" data-testid={`landing-preview-card-box-${index + 1}-1`}>
                          <div className="h-2.5 rounded-full bg-slate-200" />
                          <div className="mt-2 h-2.5 w-4/5 rounded-full bg-slate-100" />
                        </div>
                        <div className="rounded-2xl bg-blue-50 px-3 py-4" data-testid={`landing-preview-card-box-${index + 1}-2`}>
                          <div className="h-2.5 rounded-full bg-blue-200" />
                          <div className="mt-2 h-2.5 w-3/4 rounded-full bg-blue-100" />
                        </div>
                      </div>
                      <div className="rounded-2xl bg-slate-950 px-3 py-4" data-testid={`landing-preview-card-chart-${index + 1}`}>
                        <div className="grid grid-cols-5 gap-2">
                          {[42, 60, 72, 52, 84].map((height, barIndex) => (
                            <div key={`${panel.title}-${height}-${barIndex}`} className="flex h-14 items-end rounded-full bg-white/10" data-testid={`landing-preview-card-chart-bar-${index + 1}-${barIndex + 1}`}>
                              <div className="w-full rounded-full bg-[linear-gradient(180deg,#38BDF8,#2563EB)]" style={{ height: `${height}%` }} />
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section id="nasil-calisir" className="mx-auto max-w-7xl px-4 pb-24 sm:px-6 lg:px-8 lg:pb-28" data-testid="landing-how-it-works-section">
          <LandingSectionHeading
            eyebrow="Nasıl Çalışır"
            title="3 adımda Syroce ile çalışmaya başlayın"
            description="Kurulumdan ilk rezervasyon yönetimine kadar akış hızlı ve sade kurgulandı."
            align="center"
            testIdPrefix="landing-how-heading"
          />

          <div className="mt-10 grid gap-5 md:grid-cols-3" data-testid="landing-steps-grid">
            {STEPS.map((item, index) => (
              <article key={item.step} className="rounded-[28px] border border-white/80 bg-white/90 p-6 shadow-[0_22px_60px_rgba(15,23,42,0.05)]" data-testid={`landing-step-card-${index + 1}`}>
                <div className="flex items-center justify-between" data-testid={`landing-step-header-${index + 1}`}>
                  <span className="text-sm font-semibold uppercase tracking-[0.24em] text-[#2563EB]" data-testid={`landing-step-number-${index + 1}`}>Adım {item.step}</span>
                  <div className="grid h-11 w-11 place-items-center rounded-2xl bg-blue-50 text-[#2563EB]" data-testid={`landing-step-icon-${index + 1}`}>
                    <CheckCircle2 className="h-5 w-5" />
                  </div>
                </div>
                <h3 className="mt-6 text-xl font-extrabold tracking-tight text-slate-950 sm:text-2xl" data-testid={`landing-step-title-${index + 1}`}>{item.title}</h3>
                <p className="mt-4 text-sm leading-7 text-slate-600" data-testid={`landing-step-text-${index + 1}`}>{item.text}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="mx-auto max-w-7xl px-4 pb-24 sm:px-6 lg:px-8 lg:pb-28" data-testid="landing-roi-section">
          <div className="overflow-hidden rounded-[36px] bg-slate-950 px-6 py-8 text-white shadow-[0_34px_100px_rgba(15,23,42,0.22)] lg:px-10 lg:py-10" data-testid="landing-roi-card">
            <div className="grid gap-8 lg:grid-cols-[1fr_0.92fr] lg:items-center" data-testid="landing-roi-layout">
              <div data-testid="landing-roi-copy">
                <p className="text-sm font-semibold uppercase tracking-[0.28em] text-sky-200/80" data-testid="landing-roi-eyebrow">ROI</p>
                <h2 className="mt-4 text-3xl font-extrabold leading-[1.08] tracking-[-0.04em] text-white sm:text-4xl lg:text-5xl" data-testid="landing-roi-title">
                  Syroce kullanan acenteler operasyon süresini %40 azaltıyor
                </h2>
                <p className="mt-4 max-w-2xl text-base leading-8 text-white/70" data-testid="landing-roi-description">
                  Çünkü ekipler tek bir kaynaktan çalışıyor; rezervasyon, müşteri ve finans akışı her an görünür oluyor.
                </p>
                <div className="mt-8 grid gap-3" data-testid="landing-roi-points">
                  {ROI_POINTS.map((point, index) => (
                    <div key={point} className="flex items-center gap-3 rounded-2xl bg-white/8 px-4 py-4 text-sm text-white/90" data-testid={`landing-roi-point-${index + 1}`}>
                      <TrendingUp className="h-4 w-4 text-sky-300" />
                      {point}
                    </div>
                  ))}
                </div>
              </div>

              <div className="grid gap-4 sm:grid-cols-2" data-testid="landing-roi-stats">
                {[
                  { value: "+%22", label: "daha hızlı teklif dönüşü" },
                  { value: "-%31", label: "manuel hata oranı" },
                  { value: "+%18", label: "daha hızlı tahsilat" },
                  { value: "1 panel", label: "ekibin ortak çalışma alanı" },
                ].map((item, index) => (
                  <article key={item.label} className="rounded-[26px] border border-white/10 bg-white/6 px-5 py-5" data-testid={`landing-roi-stat-${index + 1}`}>
                    <p className="text-3xl font-extrabold tracking-tight text-white" data-testid={`landing-roi-stat-value-${index + 1}`}>{item.value}</p>
                    <p className="mt-2 text-sm text-white/70" data-testid={`landing-roi-stat-label-${index + 1}`}>{item.label}</p>
                  </article>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section className="mx-auto max-w-7xl px-4 pb-24 sm:px-6 lg:px-8 lg:pb-28" data-testid="landing-network-section">
          <div className="grid gap-8 rounded-[36px] border border-blue-100 bg-white/92 px-6 py-8 shadow-[0_24px_80px_rgba(15,23,42,0.05)] lg:grid-cols-[0.92fr_1.08fr] lg:px-10" data-testid="landing-network-card">
            <div data-testid="landing-network-copy">
              <p className="text-sm font-semibold uppercase tracking-[0.28em] text-[#2563EB]" data-testid="landing-network-eyebrow">B2B Acenta Ağı</p>
              <h2 className="mt-4 text-3xl font-extrabold leading-[1.08] tracking-[-0.04em] text-slate-950 sm:text-4xl lg:text-5xl" data-testid="landing-network-title">
                Alt acentelerle çalışın, ürün paylaşın, komisyon yönetin
              </h2>
              <p className="mt-4 text-base leading-8 text-slate-600" data-testid="landing-network-description">
                Syroce sadece iç operasyonu değil, acente ağınızı da düzenler. B2B iş ortaklarınızla ürün, fiyat ve komisyon paylaşımını daha kontrollü yönetin.
              </p>
            </div>

            <div className="grid gap-4" data-testid="landing-network-points">
              {NETWORK_POINTS.map((point, index) => (
                <article key={point} className="flex items-start gap-4 rounded-[28px] border border-slate-100 bg-slate-50/80 px-5 py-5" data-testid={`landing-network-point-${index + 1}`}>
                  <div className="grid h-12 w-12 place-items-center rounded-2xl bg-blue-50 text-[#2563EB]" data-testid={`landing-network-icon-${index + 1}`}>
                    <Network className="h-5 w-5" />
                  </div>
                  <div>
                    <p className="text-base font-semibold text-slate-900" data-testid={`landing-network-point-title-${index + 1}`}>{point}</p>
                    <p className="mt-2 text-sm leading-7 text-slate-600" data-testid={`landing-network-point-text-${index + 1}`}>
                      Acenta ağını büyütürken operasyon görünürlüğünü kaybetmeyin.
                    </p>
                  </div>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section id="fiyatlandirma" className="mx-auto max-w-7xl px-4 pb-24 sm:px-6 lg:px-8 lg:pb-28" data-testid="landing-pricing-section">
          <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between" data-testid="landing-pricing-header">
            <LandingSectionHeading
              eyebrow="Fiyatlandırma"
              title="Acenteniz büyürken paketiniz de birlikte büyüsün"
              description="14 gün ücretsiz trial ile başlayın; işiniz netleştiğinde size uygun planı seçin."
              testIdPrefix="landing-pricing-heading"
            />
            <div className="inline-flex rounded-full border border-slate-200 bg-white p-1 shadow-[0_12px_26px_rgba(15,23,42,0.04)]" data-testid="landing-pricing-toggle-group">
              <button type="button" className={`rounded-full px-4 py-2 text-sm font-semibold transition-colors duration-200 ${billingCycle === "monthly" ? "bg-slate-950 text-white" : "text-slate-600"}`} onClick={() => setBillingCycle("monthly")} data-testid="landing-pricing-toggle-monthly">
                Aylık
              </button>
              <button type="button" className={`rounded-full px-4 py-2 text-sm font-semibold transition-colors duration-200 ${billingCycle === "yearly" ? "bg-[#2563EB] text-white" : "text-slate-600"}`} onClick={() => setBillingCycle("yearly")} data-testid="landing-pricing-toggle-yearly">
                Yıllık
              </button>
            </div>
          </div>

          <div className="mt-10 grid gap-6 lg:grid-cols-3" data-testid="landing-pricing-grid">
            {pricingPlans.map((plan, index) => (
              <article key={`${billingCycle}-${plan.key}`} className={`relative flex h-full flex-col rounded-[34px] p-7 shadow-[0_24px_80px_rgba(15,23,42,0.05)] ${plan.featured ? "border border-slate-950 bg-slate-950 text-white" : "border border-white/80 bg-white/92 text-slate-900"}`} data-testid={`pricing-plan-${plan.key}`}>
                {plan.featured ? (
                  <span className="absolute right-6 top-6 rounded-full bg-white px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-slate-950" data-testid={`landing-pricing-badge-${plan.key}`}>
                    En popüler
                  </span>
                ) : null}
                <div data-testid={`landing-pricing-card-body-${index + 1}`}>
                  <p className={`text-sm font-semibold uppercase tracking-[0.22em] ${plan.featured ? "text-sky-200/80" : "text-[#2563EB]"}`} data-testid={`landing-pricing-name-${index + 1}`}>
                    {plan.name}
                  </p>
                  <div className="mt-5 flex items-end gap-2" data-testid={`landing-pricing-price-wrap-${index + 1}`}>
                    <span className="text-4xl font-extrabold tracking-[-0.05em]" data-testid={`landing-pricing-price-${index + 1}`}>{plan.price}</span>
                    <span className={`pb-1 text-sm ${plan.featured ? "text-white/65" : "text-slate-500"}`} data-testid={`landing-pricing-period-${index + 1}`}>{plan.period}</span>
                  </div>
                  <p className={`mt-4 text-sm leading-7 ${plan.featured ? "text-white/72" : "text-slate-600"}`} data-testid={`landing-pricing-description-${index + 1}`}>{plan.description}</p>
                  <div className="mt-6 grid gap-3" data-testid={`landing-pricing-features-${index + 1}`}>
                    {plan.features.map((feature, featureIndex) => (
                      <div key={feature} className={`flex items-center gap-3 rounded-2xl px-4 py-3 text-sm ${plan.featured ? "bg-white/10 text-white/90" : "bg-slate-50 text-slate-700"}`} data-testid={`landing-pricing-feature-${index + 1}-${featureIndex + 1}`}>
                        <ShieldCheck className={`h-4 w-4 ${plan.featured ? "text-sky-300" : "text-[#2563EB]"}`} />
                        {feature}
                      </div>
                    ))}
                  </div>
                </div>

                <div className="mt-8" data-testid={`landing-pricing-cta-wrap-${index + 1}`}>
                  <Button asChild className={`h-12 w-full rounded-full text-sm font-semibold ${plan.featured ? "bg-white text-slate-950 hover:bg-slate-100" : "bg-[linear-gradient(135deg,#2563EB,#0EA5E9)] text-white hover:brightness-110"}`} data-testid={`landing-pricing-cta-${index + 1}`}>
                    <Link to={plan.key === "enterprise" ? "/demo" : plan.cta}>{plan.key === "enterprise" ? "Demo Hesap Oluştur" : "Planı Seç"}</Link>
                  </Button>
                </div>
              </article>
            ))}
          </div>
        </section>

        <section id="final-cta" className="mx-auto max-w-7xl px-4 pb-16 sm:px-6 lg:px-8 lg:pb-24" data-testid="landing-final-cta-section">
          <div className="overflow-hidden rounded-[40px] bg-[linear-gradient(135deg,#2563EB,#0EA5E9)] px-6 py-10 text-white shadow-[0_34px_100px_rgba(37,99,235,0.28)] lg:px-10" data-testid="landing-final-cta-card">
            <div className="grid gap-8 lg:grid-cols-[1fr_0.72fr] lg:items-center" data-testid="landing-final-cta-layout">
              <div data-testid="landing-final-cta-copy">
                <p className="text-sm font-semibold uppercase tracking-[0.28em] text-blue-100" data-testid="landing-final-cta-eyebrow">Final CTA</p>
                <h2 className="mt-4 text-3xl font-extrabold leading-[1.08] tracking-[-0.05em] sm:text-4xl lg:text-5xl" data-testid="landing-final-cta-title">
                  Acentenizin operasyonunu dijitalleştirmeye hazır mısınız?
                </h2>
                <p className="mt-4 max-w-2xl text-base leading-8 text-blue-50/88" data-testid="landing-final-cta-text">
                  14 günlük trial hesabınızı açın veya demo girişine geçin. İlk 5 dakikada Syroce’un acentenize nasıl uyduğunu görün.
                </p>
              </div>

              <div className="grid gap-3" data-testid="landing-final-cta-buttons">
                <Button asChild className="h-14 rounded-full bg-white text-base font-semibold text-[#2563EB] hover:bg-slate-100" data-testid="landing-final-cta-trial">
                  <Link to="/signup?plan=trial">14 Gün Ücretsiz Dene</Link>
                </Button>
                <Button asChild variant="outline" className="h-14 rounded-full border-white/60 bg-transparent text-base font-semibold text-white hover:bg-white/10" data-testid="landing-final-cta-demo">
                  <Link to="/demo">Demo Hesap Oluştur</Link>
                </Button>
              </div>
            </div>
          </div>
        </section>
      </main>

      <footer className="relative z-10 border-t border-white/70 bg-white/72 backdrop-blur-xl" data-testid="landing-footer">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 px-4 py-6 text-sm text-slate-600 sm:px-6 lg:flex-row lg:items-center lg:justify-between lg:px-8" data-testid="landing-footer-inner">
          <p data-testid="landing-footer-copy">Syroce · Turizm acenteleri için modern operasyon sistemi</p>
          <div className="flex flex-wrap gap-4" data-testid="landing-footer-links">
            <Link to="/pricing" className="transition-colors duration-200 hover:text-[#2563EB]" data-testid="landing-footer-pricing-link">Fiyatlar</Link>
            <Link to="/privacy" className="transition-colors duration-200 hover:text-[#2563EB]" data-testid="landing-footer-privacy-link">Gizlilik</Link>
            <Link to="/terms" className="transition-colors duration-200 hover:text-[#2563EB]" data-testid="landing-footer-terms-link">Koşullar</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
