import React, { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  Globe,
  BarChart3,
  Shield,
  Zap,
  Building2,
  Users,
  TrendingUp,
  ArrowRight,
  CheckCircle2,
  Hotel,
  Plane,
  CreditCard,
  ChevronRight,
  Menu,
  X,
} from "lucide-react";

import { Button } from "../components/ui/button";
import { useSeo } from "../hooks/useSeo";
import { apiErrorMessage } from "../lib/publicBooking";
import { api } from "../lib/api";

const HERO_IMAGE =
  "https://images.unsplash.com/photo-1602693680104-b8ae3138c22b?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjY2NjV8MHwxfHNlYXJjaHwxfHxsdXh1cnklMjBob3RlbCUyMHJlc29ydHxlbnwwfHx8Ymx1ZXwxNzcxOTM2OTE4fDA&ixlib=rb-4.1.0&q=85";
const CTA_IMAGE =
  "https://images.pexels.com/photos/35747632/pexels-photo-35747632.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940";

const FEATURES = [
  {
    icon: Globe,
    title: "B2B Ağ Yönetimi",
    desc: "Alt acenta ağınızı tek panelden yönetin. Fiyatlama, indirimler ve portföy paylaşımı ile iş ortaklıklarınızı güçlendirin.",
  },
  {
    icon: BarChart3,
    title: "Akıllı Fiyatlama Motoru",
    desc: "Graf tabanlı fiyat hesaplama, kural motoru ve anomali tespiti ile her zaman doğru fiyat. Komisyon ve marj kontrolü dahil.",
  },
  {
    icon: Shield,
    title: "Enterprise Güvenlik",
    desc: "RBAC, 2FA, IP kısıtlama, denetim izi (audit chain) ve KVKK uyumlu veri yönetimi ile kurumsal seviyede güvenlik.",
  },
  {
    icon: Zap,
    title: "Operasyonel Mükemmellik",
    desc: "Otomatik yedekleme, sistem sağlık izleme, olay yönetimi ve preflight kontrolleri ile kesintisiz operasyon.",
  },
];

const STATS = [
  { value: "590+", label: "API Endpoint", icon: Zap },
  { value: "149", label: "Yönetim Sayfası", icon: Building2 },
  { value: "98", label: "Veri Koleksiyonu", icon: TrendingUp },
  { value: "7/24", label: "Sistem İzleme", icon: Shield },
];

const STEPS = [
  {
    num: "01",
    title: "Kaydolun & Yapılandırın",
    desc: "Dakikalar içinde hesabınızı oluşturun. Ürünlerinizi, fiyat kurallarınızı ve acenta ağınızı tanımlayın.",
    icon: Users,
  },
  {
    num: "02",
    title: "Rezervasyonları Yönetin",
    desc: "Oteller, villalar ve turlar için tek platformdan rezervasyon alın. Otomatik onay, voucher ve bildirim sistemi ile.",
    icon: Hotel,
  },
  {
    num: "03",
    title: "Büyüyün & Ölçeklendirin",
    desc: "CRM, finans raporları, mutabakat ve B2B marketplace ile işinizi büyütün. Her adımda veri odaklı kararlar alın.",
    icon: TrendingUp,
  },
];

const MODULES = [
  { name: "Rezervasyon Yönetimi", icon: Hotel },
  { name: "CRM & Müşteri 360°", icon: Users },
  { name: "B2B Portal & Marketplace", icon: Globe },
  { name: "Fiyatlama & Komisyon", icon: TrendingUp },
  { name: "Finans & Mutabakat", icon: CreditCard },
  { name: "Tur & Transfer", icon: Plane },
];

export default function PublicHomePage() {
  const [searchParams] = useSearchParams();
  const org = searchParams.get("org") || "";
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const [navPages, setNavPages] = useState([]);
  const [featuredProducts, setFeaturedProducts] = useState([]);
  const [featuredTours, setFeaturedTours] = useState([]);
  const [campaigns, setCampaigns] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useSeo({
    title: "Syroce — Turizm Operasyon Platformu",
    description:
      "B2B acentalar ve oteller için tasarlanmış enterprise seviyede rezervasyon, fiyatlama, CRM ve operasyon yönetim platformu.",
    canonicalPath: "/",
    type: "website",
  });

  useEffect(() => {
    if (!org) return;
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError("");
      try {
        const cmsRes = await api.get("/public/cms/pages", { params: { org } });
        if (!cancelled) setNavPages(cmsRes.data?.items || []);
        const prodRes = await api.get("/public/search", {
          params: { org, page: 1, page_size: 4, sort: "price_asc" },
        });
        if (!cancelled) setFeaturedProducts(prodRes.data?.items || []);
        const tourRes = await api.get("/public/tours/search", {
          params: { org, page: 1, page_size: 4 },
        });
        if (!cancelled) setFeaturedTours(tourRes.data?.items || []);
        const campRes = await api.get("/public/campaigns", { params: { org } });
        if (!cancelled) setCampaigns(campRes.data?.items || []);
      } catch (e) {
        if (!cancelled) setError(apiErrorMessage(e));
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, [org]);

  const buildBookUrl = () => {
    const qp = new URLSearchParams();
    if (org) qp.set("org", org);
    const qs = qp.toString();
    return qs ? `/book?${qs}` : "/book";
  };
  const buildCmsUrl = (slug) => {
    const qp = new URLSearchParams();
    if (org) qp.set("org", org);
    const qs = qp.toString();
    return qs ? `/p/${slug}?${qs}` : `/p/${slug}`;
  };

  return (
    <div className="min-h-screen flex flex-col bg-white text-gray-900">
      {/* ═══════════ NAVBAR ═══════════ */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-white/80 backdrop-blur-lg border-b border-gray-100">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <Link to="/" className="flex items-center gap-2.5 group">
              <div className="h-9 w-9 rounded-xl bg-gradient-to-br from-blue-600 to-cyan-500 text-white grid place-items-center font-bold text-sm shadow-md shadow-blue-200/50 group-hover:shadow-blue-300/60 transition-shadow">
                S
              </div>
              <span className="text-lg font-bold tracking-tight bg-gradient-to-r from-gray-900 to-gray-600 bg-clip-text text-transparent">
                Syroce
              </span>
            </Link>

            {/* Desktop Nav */}
            <div className="hidden md:flex items-center gap-1">
              <Link to={buildBookUrl()} className="px-3 py-2 text-sm font-medium text-gray-600 hover:text-gray-900 rounded-lg hover:bg-gray-50 transition-colors">
                Rezervasyon
              </Link>
              <Link to="/partners/apply" className="px-3 py-2 text-sm font-medium text-gray-600 hover:text-gray-900 rounded-lg hover:bg-gray-50 transition-colors">
                İş Ortağı
              </Link>
              <Link to="/pricing" className="px-3 py-2 text-sm font-medium text-gray-600 hover:text-gray-900 rounded-lg hover:bg-gray-50 transition-colors">
                Fiyatlar
              </Link>
              {navPages.map((p) => (
                <Link key={p.id} to={buildCmsUrl(p.slug)} className="px-3 py-2 text-sm font-medium text-gray-600 hover:text-gray-900 rounded-lg hover:bg-gray-50 transition-colors">
                  {p.title || p.slug}
                </Link>
              ))}
            </div>

            {/* Desktop CTAs */}
            <div className="hidden md:flex items-center gap-2">
              <Link to="/b2b/login">
                <Button variant="ghost" size="sm" className="text-sm font-medium text-gray-600 hover:text-gray-900">
                  B2B Giriş
                </Button>
              </Link>
              <Link to="/login">
                <Button size="sm" className="bg-gradient-to-r from-blue-600 to-cyan-500 hover:from-blue-700 hover:to-cyan-600 text-white shadow-md shadow-blue-200/50 text-sm font-medium">
                  Giriş Yap
                </Button>
              </Link>
            </div>

            {/* Mobile menu button */}
            <button
              className="md:hidden p-2 rounded-lg hover:bg-gray-100 transition-colors"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              aria-label="Menü"
            >
              {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </button>
          </div>
        </div>

        {/* Mobile Menu */}
        {mobileMenuOpen && (
          <div className="md:hidden border-t border-gray-100 bg-white/95 backdrop-blur-lg">
            <div className="px-4 py-4 space-y-1">
              <Link to={buildBookUrl()} className="block px-3 py-2.5 text-sm font-medium text-gray-700 rounded-lg hover:bg-gray-50" onClick={() => setMobileMenuOpen(false)}>
                Rezervasyon
              </Link>
              <Link to="/partners/apply" className="block px-3 py-2.5 text-sm font-medium text-gray-700 rounded-lg hover:bg-gray-50" onClick={() => setMobileMenuOpen(false)}>
                İş Ortağı Başvurusu
              </Link>
              <Link to="/pricing" className="block px-3 py-2.5 text-sm font-medium text-gray-700 rounded-lg hover:bg-gray-50" onClick={() => setMobileMenuOpen(false)}>
                Fiyatlar
              </Link>
              <div className="pt-3 space-y-2 border-t border-gray-100 mt-3">
                <Link to="/b2b/login" className="block" onClick={() => setMobileMenuOpen(false)}>
                  <Button variant="outline" className="w-full text-sm">B2B Giriş</Button>
                </Link>
                <Link to="/login" className="block" onClick={() => setMobileMenuOpen(false)}>
                  <Button className="w-full bg-gradient-to-r from-blue-600 to-cyan-500 text-white text-sm">Giriş Yap</Button>
                </Link>
              </div>
            </div>
          </div>
        )}
      </nav>

      {/* ═══════════ HERO SECTION ═══════════ */}
      <section className="relative pt-16 overflow-hidden">
        <div className="absolute inset-0">
          <img
            src={HERO_IMAGE}
            alt="Lüks otel havuz manzarası"
            className="w-full h-full object-cover"
            loading="eager"
          />
          <div className="absolute inset-0 bg-gradient-to-b from-gray-900/70 via-gray-900/60 to-gray-900/80" />
        </div>

        <div className="relative z-10 mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-24 sm:py-32 lg:py-40">
          <div className="max-w-3xl">
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/10 backdrop-blur-sm border border-white/20 text-white/90 text-xs font-medium mb-6">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
              Enterprise Turizm Operasyon Platformu
            </div>

            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold text-white leading-[1.1] tracking-tight">
              Turizm Operasyonunuzu{" "}
              <span className="bg-gradient-to-r from-cyan-300 to-blue-300 bg-clip-text text-transparent">
                Tek Platformdan
              </span>{" "}
              Yönetin
            </h1>

            <p className="mt-6 text-lg sm:text-xl text-gray-200 leading-relaxed max-w-2xl">
              Rezervasyon, fiyatlama, B2B ağ yönetimi, CRM ve finansal mutabakat — hepsi bir arada.
              Acentanızı dijital dönüşümle geleceğe taşıyın.
            </p>

            <div className="mt-8 flex flex-col sm:flex-row gap-3">
              <Link to="/signup">
                <Button size="lg" className="bg-gradient-to-r from-blue-500 to-cyan-400 hover:from-blue-600 hover:to-cyan-500 text-white shadow-xl shadow-blue-500/25 text-base px-8 h-12 rounded-xl font-semibold group">
                  Ücretsiz Deneyin
                  <ArrowRight className="ml-2 h-4 w-4 group-hover:translate-x-1 transition-transform" />
                </Button>
              </Link>
              <Link to={buildBookUrl()}>
                <Button size="lg" variant="outline" className="border-white/30 text-white hover:bg-white/10 hover:text-white text-base px-8 h-12 rounded-xl font-semibold backdrop-blur-sm">
                  Ürünleri İnceleyin
                </Button>
              </Link>
            </div>

            <div className="mt-10 flex flex-wrap items-center gap-x-6 gap-y-2 text-sm text-gray-300">
              {["14 gün ücretsiz deneme", "Kurulum gerektirmez", "7/24 destek"].map((t) => (
                <div key={t} className="flex items-center gap-1.5">
                  <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                  {t}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Bottom wave */}
        <div className="absolute bottom-0 left-0 right-0">
          <svg viewBox="0 0 1440 60" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full">
            <path d="M0 60L48 53.3C96 46.7 192 33.3 288 28.3C384 23.3 480 26.7 576 33.3C672 40 768 50 864 50C960 50 1056 40 1152 33.3C1248 26.7 1344 23.3 1392 21.7L1440 20V60H0Z" fill="white"/>
          </svg>
        </div>
      </section>

      {/* ═══════════ FEATURES SECTION ═══════════ */}
      <section className="py-20 sm:py-28 bg-white">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-2xl mx-auto mb-16">
            <p className="text-sm font-semibold text-blue-600 tracking-wide uppercase mb-3">Özellikler</p>
            <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-gray-900">
              Her Şey Tek Platformda
            </h2>
            <p className="mt-4 text-base text-gray-500 leading-relaxed">
              Turizm sektörünün ihtiyaç duyduğu tüm araçları enterprise kalitesinde sunan, uçtan uca operasyon platformu.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {FEATURES.map((f, i) => (
              <div
                key={i}
                className="group relative p-6 rounded-2xl border border-gray-100 bg-white hover:border-blue-100 hover:shadow-xl hover:shadow-blue-50/50 transition-all duration-300"
              >
                <div className="h-12 w-12 rounded-xl bg-gradient-to-br from-blue-50 to-cyan-50 grid place-items-center mb-5 group-hover:from-blue-100 group-hover:to-cyan-100 transition-colors">
                  <f.icon className="h-6 w-6 text-blue-600" />
                </div>
                <h3 className="text-base font-semibold text-gray-900 mb-2">{f.title}</h3>
                <p className="text-sm text-gray-500 leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ═══════════ STATS SECTION ═══════════ */}
      <section className="py-16 bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-6 sm:gap-8">
            {STATS.map((s, i) => (
              <div key={i} className="text-center group">
                <div className="inline-flex items-center justify-center h-12 w-12 rounded-xl bg-white/5 border border-white/10 mb-4 group-hover:bg-white/10 transition-colors">
                  <s.icon className="h-5 w-5 text-cyan-400" />
                </div>
                <div className="text-3xl sm:text-4xl font-bold text-white mb-1">{s.value}</div>
                <div className="text-sm text-gray-400 font-medium">{s.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ═══════════ HOW IT WORKS ═══════════ */}
      <section className="py-20 sm:py-28 bg-gray-50/50">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-2xl mx-auto mb-16">
            <p className="text-sm font-semibold text-blue-600 tracking-wide uppercase mb-3">Nasıl Çalışır</p>
            <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-gray-900">
              3 Adımda Başlayın
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 lg:gap-12">
            {STEPS.map((step, i) => (
              <div key={i} className="relative group">
                <div className="flex items-start gap-4">
                  <div className="flex-shrink-0">
                    <div className="h-14 w-14 rounded-2xl bg-gradient-to-br from-blue-600 to-cyan-500 text-white grid place-items-center shadow-lg shadow-blue-200/40 group-hover:shadow-blue-300/50 transition-shadow">
                      <step.icon className="h-6 w-6" />
                    </div>
                  </div>
                  <div>
                    <div className="text-xs font-bold text-blue-600 mb-1.5">ADIM {step.num}</div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">{step.title}</h3>
                    <p className="text-sm text-gray-500 leading-relaxed">{step.desc}</p>
                  </div>
                </div>
                {i < STEPS.length - 1 && (
                  <div className="hidden md:block absolute top-7 left-[calc(100%_-_16px)] w-8">
                    <ChevronRight className="h-5 w-5 text-gray-300" />
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ═══════════ MODULES STRIP ═══════════ */}
      <section className="py-14 bg-white border-y border-gray-100">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <p className="text-center text-sm font-semibold text-gray-400 tracking-wide uppercase mb-8">
            Dahil Modüller
          </p>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
            {MODULES.map((m, i) => (
              <div
                key={i}
                className="flex items-center gap-2.5 px-4 py-3 rounded-xl bg-gray-50 border border-gray-100 hover:border-blue-100 hover:bg-blue-50/30 transition-colors"
              >
                <m.icon className="h-4 w-4 text-blue-600 flex-shrink-0" />
                <span className="text-xs font-medium text-gray-700 whitespace-nowrap">{m.name}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ═══════════ ORG-SPECIFIC CONTENT ═══════════ */}
      {error && <p className="text-xs text-red-600 text-center mt-4 px-4">{error}</p>}
      {!error && org && (
        <section className="py-16 bg-white">
          <div className="mx-auto max-w-5xl px-4 sm:px-6 lg:px-8 space-y-10">
            {campaigns.length > 0 && (
              <div className="space-y-4">
                <h2 className="text-lg font-bold tracking-tight text-gray-900">Öne Çıkan Kampanyalar</h2>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {campaigns.map((c) => {
                    const qp = new URLSearchParams();
                    if (org) qp.set("org", org);
                    const url = `/campaigns/${c.slug}?${qp.toString()}`;
                    return (
                      <Link key={c.id} to={url} className="flex items-center justify-between rounded-xl border border-gray-100 px-4 py-3 hover:border-blue-200 hover:bg-blue-50/30 transition-colors group">
                        <div>
                          <div className="text-sm font-semibold text-gray-900 group-hover:text-blue-700 transition-colors">{c.name}</div>
                          {c.description && <div className="text-xs text-gray-500 mt-0.5 line-clamp-1">{c.description}</div>}
                        </div>
                        <ChevronRight className="h-4 w-4 text-gray-400 group-hover:text-blue-600 transition-colors" />
                      </Link>
                    );
                  })}
                </div>
              </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              {featuredProducts.length > 0 && (
                <div className="space-y-4">
                  <h2 className="text-lg font-bold tracking-tight text-gray-900">Öne Çıkan Ürünler</h2>
                  <div className="space-y-2">
                    {featuredProducts.map((item) => {
                      const qp = new URLSearchParams();
                      if (org) qp.set("org", org);
                      const url = `/book/${item.product_id || item.id}?${qp.toString()}`;
                      return (
                        <Link key={item.product_id || item.id} to={url} className="flex items-center justify-between rounded-xl border border-gray-100 px-4 py-3 hover:border-blue-200 hover:bg-blue-50/30 transition-colors group">
                          <div>
                            <div className="text-sm font-semibold text-gray-900 group-hover:text-blue-700">{item.title}</div>
                            {item.summary && <div className="text-xs text-gray-500 mt-0.5 line-clamp-1">{item.summary}</div>}
                          </div>
                          <ChevronRight className="h-4 w-4 text-gray-400 group-hover:text-blue-600" />
                        </Link>
                      );
                    })}
                  </div>
                </div>
              )}

              {featuredTours.length > 0 && (
                <div className="space-y-4">
                  <h2 className="text-lg font-bold tracking-tight text-gray-900">Öne Çıkan Turlar</h2>
                  <div className="space-y-2">
                    {featuredTours.map((tour) => {
                      const qp = new URLSearchParams();
                      if (org) qp.set("org", org);
                      const url = `/book/tour/${tour.id}?${qp.toString()}`;
                      return (
                        <Link key={tour.id} to={url} className="flex items-center justify-between rounded-xl border border-gray-100 px-4 py-3 hover:border-blue-200 hover:bg-blue-50/30 transition-colors group">
                          <div>
                            <div className="text-sm font-semibold text-gray-900 group-hover:text-blue-700">{tour.name}</div>
                            {tour.destination && <div className="text-xs text-gray-500 mt-0.5">{tour.destination}</div>}
                          </div>
                          <ChevronRight className="h-4 w-4 text-gray-400 group-hover:text-blue-600" />
                        </Link>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          </div>
        </section>
      )}

      {/* ═══════════ CTA SECTION ═══════════ */}
      <section className="relative py-20 sm:py-28 overflow-hidden">
        <div className="absolute inset-0">
          <img
            src={CTA_IMAGE}
            alt="Göl ve karlı dağlar manzarası"
            className="w-full h-full object-cover"
            loading="lazy"
          />
          <div className="absolute inset-0 bg-gradient-to-r from-blue-900/90 to-cyan-800/85" />
        </div>

        <div className="relative z-10 mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl sm:text-4xl font-bold text-white tracking-tight">
            Operasyonunuzu Dönüştürmeye Hazır mısınız?
          </h2>
          <p className="mt-4 text-lg text-blue-100 max-w-2xl mx-auto">
            Yüzlerce acenta ve otelin güvendiği Syroce ile tanışın. 14 gün ücretsiz deneyin, kredi kartı gerekmez.
          </p>
          <div className="mt-8 flex flex-col sm:flex-row gap-3 justify-center">
            <Link to="/signup">
              <Button size="lg" className="bg-white text-blue-700 hover:bg-gray-50 shadow-xl text-base px-8 h-12 rounded-xl font-semibold group">
                Hemen Başlayın
                <ArrowRight className="ml-2 h-4 w-4 group-hover:translate-x-1 transition-transform" />
              </Button>
            </Link>
            <Link to="/pricing">
              <Button size="lg" variant="outline" className="border-white/30 text-white hover:bg-white/10 hover:text-white text-base px-8 h-12 rounded-xl font-semibold backdrop-blur-sm">
                Fiyatları İnceleyin
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* ═══════════ FOOTER ═══════════ */}
      <footer className="bg-gray-900 text-gray-400">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-12">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            {/* Brand */}
            <div className="col-span-2 md:col-span-1">
              <div className="flex items-center gap-2.5 mb-4">
                <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-blue-500 to-cyan-400 text-white grid place-items-center font-bold text-xs">
                  S
                </div>
                <span className="text-base font-bold text-white">Syroce</span>
              </div>
              <p className="text-xs leading-relaxed">
                Enterprise seviyede turizm operasyon platformu. B2B acentalar ve oteller için.
              </p>
            </div>

            {/* Platform */}
            <div>
              <h4 className="text-xs font-semibold text-gray-200 uppercase tracking-wider mb-3">Platform</h4>
              <ul className="space-y-2 text-xs">
                <li><Link to="/book" className="hover:text-white transition-colors">Rezervasyon</Link></li>
                <li><Link to="/pricing" className="hover:text-white transition-colors">Fiyatlandırma</Link></li>
                <li><Link to="/signup" className="hover:text-white transition-colors">Kayıt Ol</Link></li>
              </ul>
            </div>

            {/* Portallar */}
            <div>
              <h4 className="text-xs font-semibold text-gray-200 uppercase tracking-wider mb-3">Portallar</h4>
              <ul className="space-y-2 text-xs">
                <li><Link to="/login" className="hover:text-white transition-colors">Admin Girişi</Link></li>
                <li><Link to="/b2b/login" className="hover:text-white transition-colors">B2B Portal</Link></li>
                <li><Link to="/partners/apply" className="hover:text-white transition-colors">İş Ortağı Başvurusu</Link></li>
              </ul>
            </div>

            {/* Legal */}
            <div>
              <h4 className="text-xs font-semibold text-gray-200 uppercase tracking-wider mb-3">Yasal</h4>
              <ul className="space-y-2 text-xs">
                <li><Link to="/p/gizlilik" className="hover:text-white transition-colors">Gizlilik Politikası</Link></li>
                <li><Link to="/p/kullanim-kosullari" className="hover:text-white transition-colors">Kullanım Koşulları</Link></li>
                <li><Link to="/p/kvkk" className="hover:text-white transition-colors">KVKK Aydınlatma</Link></li>
              </ul>
            </div>
          </div>

          <div className="mt-10 pt-6 border-t border-gray-800 flex flex-col sm:flex-row items-center justify-between gap-3">
            <div className="text-xs">© {new Date().getFullYear()} Syroce. Tüm hakları saklıdır.</div>
            <div className="text-xs">Enterprise Turizm Operasyon Platformu</div>
          </div>
        </div>
      </footer>
    </div>
  );
}
