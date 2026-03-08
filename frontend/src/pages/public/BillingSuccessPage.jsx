import React, { useEffect, useMemo, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ArrowRight, CheckCircle2, Clock3, ShieldCheck, XCircle } from "lucide-react";

import { Button } from "../../components/ui/button";
import { getCheckoutStatus } from "../../lib/billing";
import { useSeo } from "../../hooks/useSeo";
import { getUser } from "../../lib/api";
import { redirectByRole } from "../../utils/redirectByRole";

const MAX_ATTEMPTS = 6;
const POLL_INTERVAL = 2000;
const RESERVATION_ENABLED_ROLES = ["super_admin", "admin", "sales", "ops", "accounting", "b2b_agent"];
const AGENCY_BOOKING_ROLES = ["agency_admin", "agency_agent"];
const ACTIVATION_CHECKLIST = [
  "Profil bilgilerinizi kontrol edin",
  "İlk turunuzu veya ürününüzü ekleyin",
  "İlk müşterinizi ekleyin",
  "İlk rezervasyonu oluşturun",
];

function resolveDashboardPath(user) {
  const candidate = redirectByRole(user);
  if (!candidate || candidate === "/login" || candidate === "/unauthorized") {
    return "/app";
  }
  return candidate;
}

function resolveReservationCta(user) {
  const roles = user?.roles || [];

  if (roles.some((role) => AGENCY_BOOKING_ROLES.includes(role))) {
    return {
      href: "/app/agency/booking/new",
      label: "İlk Rezervasyonu Oluştur",
    };
  }

  if (roles.some((role) => RESERVATION_ENABLED_ROLES.includes(role))) {
    return {
      href: "/app/reservations",
      label: "İlk Rezervasyonu Oluştur",
    };
  }

  return null;
}

export default function BillingSuccessPage() {
  const [searchParams] = useSearchParams();
  const sessionId = searchParams.get("session_id") || "";
  const [phase, setPhase] = useState(sessionId ? "checking" : "missing");
  const [payload, setPayload] = useState(null);
  const [error, setError] = useState("");
  const timeoutRef = useRef(null);
  const currentUser = useMemo(() => getUser(), []);
  const dashboardHref = useMemo(() => resolveDashboardPath(currentUser), [currentUser]);
  const reservationCta = useMemo(() => resolveReservationCta(currentUser), [currentUser]);

  useSeo({
    title: "Ödeme durumu",
    description: "Stripe ödeme sonucunuz doğrulanıyor. Syroce hesabınızın aktivasyon durumunu buradan görebilirsiniz.",
    canonicalPath: "/payment-success",
    type: "website",
  });

  useEffect(() => {
    async function pollStatus(attempt = 0) {
      try {
        const result = await getCheckoutStatus(sessionId);
        setPayload(result);

        if (result?.payment_status === "paid" || result?.activated) {
          setPhase("success");
          return;
        }

        if (result?.status === "expired") {
          setPhase("expired");
          return;
        }

        if (attempt >= MAX_ATTEMPTS - 1) {
          setPhase("pending");
          return;
        }

        timeoutRef.current = window.setTimeout(() => {
          void pollStatus(attempt + 1);
        }, POLL_INTERVAL);
      } catch (err) {
        if (attempt >= MAX_ATTEMPTS - 1) {
          setError(err?.message || "Ödeme durumu doğrulanamadı.");
          setPhase("error");
          return;
        }

        timeoutRef.current = window.setTimeout(() => {
          void pollStatus(attempt + 1);
        }, POLL_INTERVAL);
      }
    }

    if (sessionId) {
      void pollStatus();
    }

    return () => {
      if (timeoutRef.current) {
        window.clearTimeout(timeoutRef.current);
      }
    };
  }, [sessionId]);

  const stateConfig = {
    success: {
      icon: CheckCircle2,
      iconColor: "text-[#2a9d8f]",
      title: "Ödemeniz başarıyla tamamlandı",
      text: "Syroce hesabınız artık aktif. İlk rezervasyonunuzu oluşturarak hemen kullanmaya başlayabilirsiniz.",
    },
    checking: {
      icon: Clock3,
      iconColor: "text-[#d16024]",
      title: "Ödemeniz doğrulanıyor",
      text: "Stripe dönüşünüz alındı. Plan aktivasyonunuz birkaç saniye içinde tamamlanır.",
    },
    pending: {
      icon: Clock3,
      iconColor: "text-[#d16024]",
      title: "Ödeme işleniyor",
      text: "Ödeme onayı henüz tamamlanmadı. Birkaç dakika sonra tekrar kontrol edebilirsiniz.",
    },
    expired: {
      icon: XCircle,
      iconColor: "text-rose-500",
      title: "Ödeme oturumu sona erdi",
      text: "Lütfen tekrar plan seçip ödeme akışını yeniden başlatın.",
    },
    missing: {
      icon: XCircle,
      iconColor: "text-rose-500",
      title: "Ödeme oturumu bulunamadı",
      text: "Bu sayfaya geçerli bir ödeme oturumu olmadan geldiniz.",
    },
    error: {
      icon: XCircle,
      iconColor: "text-rose-500",
      title: "Ödeme doğrulanamadı",
      text: error || "Lütfen birkaç dakika sonra tekrar deneyin.",
    },
  };

  const current = stateConfig[phase] || stateConfig.checking;
  const Icon = current.icon;

  return (
    <div className="min-h-screen bg-[linear-gradient(180deg,#fbfaf7_0%,#fff4eb_42%,#f6fbfa_100%)] px-4 py-12" style={{ fontFamily: "Inter, sans-serif" }} data-testid="billing-success-page">
      <div className="mx-auto max-w-4xl rounded-[2rem] border border-[#ebddd1] bg-white/95 p-8 shadow-[0_30px_120px_rgba(38,70,83,0.10)] lg:p-12" data-testid="billing-success-card">
        <div className="grid gap-8 lg:grid-cols-[0.95fr_1.05fr] lg:items-center">
          <section className="space-y-5" data-testid="billing-success-copy-section">
            <div className="inline-flex items-center gap-2 rounded-full border border-[#f6d2bd] bg-[#fff4ec] px-4 py-2 text-xs font-semibold uppercase tracking-[0.24em] text-[#d16024]" data-testid="billing-success-badge">
              <Icon className={`h-4 w-4 ${current.iconColor}`} />
              Stripe ödeme durumu
            </div>

            <div className="space-y-4">
              <h1 className="text-4xl font-extrabold tracking-[-0.04em] text-slate-900 sm:text-5xl" style={{ fontFamily: "Manrope, Inter, sans-serif" }} data-testid="billing-success-title">
                {current.title}
              </h1>
              <p className="max-w-2xl text-base leading-7 text-slate-600 md:text-lg" data-testid="billing-success-text">
                {current.text}
              </p>
            </div>

            {payload ? (
              <div className="rounded-[1.5rem] bg-[#f8fbfb] p-5" data-testid="billing-success-summary">
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[#2a9d8f]" data-testid="billing-success-summary-eyebrow">Aktivasyon özeti</p>
                <div className="mt-4 grid gap-3 sm:grid-cols-3" data-testid="billing-success-summary-grid">
                  <div className="rounded-2xl bg-white px-4 py-4" data-testid="billing-success-summary-plan">
                    <p className="text-xs text-slate-500">Plan</p>
                    <p className="mt-2 text-sm font-semibold text-slate-900">{payload?.plan || "—"}</p>
                  </div>
                  <div className="rounded-2xl bg-white px-4 py-4" data-testid="billing-success-summary-interval">
                    <p className="text-xs text-slate-500">Periyot</p>
                    <p className="mt-2 text-sm font-semibold text-slate-900">{payload?.interval === "yearly" ? "Yıllık" : "Aylık"}</p>
                  </div>
                  <div className="rounded-2xl bg-white px-4 py-4" data-testid="billing-success-summary-status">
                    <p className="text-xs text-slate-500">Durum</p>
                    <p className="mt-2 text-sm font-semibold text-slate-900">{payload?.payment_status || payload?.status || "—"}</p>
                  </div>
                </div>
              </div>
            ) : null}
          </section>

          <section className="rounded-[1.8rem] bg-[#264653] p-6 text-white" data-testid="billing-success-actions-section">
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[#e9c46a]" data-testid="billing-success-actions-eyebrow">
              {phase === "success" ? "Aktivasyon checklist" : "Sonraki adım"}
            </p>

            {phase === "success" ? (
              <div className="mt-5 space-y-4" data-testid="billing-success-onboarding-panel">
                <p className="text-sm leading-6 text-white/75" data-testid="billing-success-onboarding-description">
                  İlk değeri en hızlı şekilde görmek için bu adımlarla başlayın.
                </p>
                <div className="grid gap-3" data-testid="billing-success-checklist">
                  {ACTIVATION_CHECKLIST.map((item, index) => (
                    <div
                      key={item}
                      className="flex items-center gap-3 rounded-2xl bg-white/10 px-4 py-4 text-sm leading-6 text-white/90"
                      data-testid={`billing-success-checklist-item-${index + 1}`}
                    >
                      <ShieldCheck className="h-4 w-4 shrink-0 text-[#e9c46a]" />
                      <span>{item}</span>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="mt-5 grid gap-3" data-testid="billing-success-actions-list">
                {[
                  "Planınız aktif olduğunda quota ve entitlement ayarlarınız güncellenir",
                  "Tüm trial verileriniz korunur",
                  "Panelinize dönerek kullanıma hemen devam edebilirsiniz",
                ].map((item, index) => (
                  <div key={item} className="rounded-2xl bg-white/10 px-4 py-4 text-sm leading-6 text-white/90" data-testid={`billing-success-action-${index + 1}`}>
                    {item}
                  </div>
                ))}
              </div>
            )}

            <div className="mt-6 flex flex-wrap gap-3" data-testid="billing-success-cta-group">
              <Button asChild className="h-12 rounded-xl bg-[#f3722c] px-6 text-sm font-semibold text-white hover:bg-[#e05d1b]" data-testid="billing-success-go-dashboard-button">
                <Link to={dashboardHref}>
                  Panele Git
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Link>
              </Button>

              {phase === "success" && reservationCta ? (
                <Button asChild variant="outline" className="h-12 rounded-xl border-white/30 bg-transparent px-6 text-sm font-semibold text-white hover:bg-white/10" data-testid="billing-success-create-reservation-button">
                  <Link to={reservationCta.href}>{reservationCta.label}</Link>
                </Button>
              ) : null}

              {phase !== "success" ? (
                <Button asChild variant="outline" className="h-12 rounded-xl border-white/30 bg-transparent px-6 text-sm font-semibold text-white hover:bg-white/10" data-testid="billing-success-back-pricing-button">
                  <Link to="/pricing">Fiyatlara Dön</Link>
                </Button>
              ) : null}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}