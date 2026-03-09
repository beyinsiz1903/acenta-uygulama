import React, { useRef, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowRight, CheckCircle2, ShieldCheck, Sparkles } from "lucide-react";

import { apiErrorMessage } from "../lib/api";
import { useCurrentUser, useLogin } from "../hooks/useAuth";
import { consumePostLoginRedirect, hasSessionExpired } from "../lib/authRedirect";
import { redirectByRole } from "../utils/redirectByRole";
import { loginSchema } from "../lib/validations";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";

const LOGIN_PROOF = [
  "Rezervasyon, müşteri ve finans tek panelde görünür.",
  "Bulut tabanlı erişimle ekibiniz aynı veride buluşur.",
  "14 gün ücretsiz trial ile kurulum yapmadan deneyebilirsiniz.",
];

export default function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const [serverError, setServerError] = useState("");
  const hasHandledAuthRedirect = useRef(false);
  const loginMutation = useLogin();
  const { data: currentUser, isLoading: isBootstrapping } = useCurrentUser();

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "" },
  });

  async function onSubmit(data) {
    setServerError("");
    try {
      const resp = await loginMutation.mutateAsync({
        email: data.email,
        password: data.password,
      });

      if (resp.requires_2fa) {
        setServerError(resp.message || "İki aşamalı doğrulama gerekli.");
        return;
      }

      if (!resp.user) {
        setServerError("Giriş yanıtı eksik. Lütfen tekrar deneyin.");
        return;
      }

      const redirectPath = consumePostLoginRedirect(redirectByRole(resp.user));
      hasHandledAuthRedirect.current = true;
      navigate(redirectPath, { replace: true });
    } catch (err) {
      setServerError(apiErrorMessage(err));
    }
  }

  React.useEffect(() => {
    if (!currentUser) {
      return;
    }

    if (hasHandledAuthRedirect.current) {
      return;
    }

    hasHandledAuthRedirect.current = true;
    const redirectPath = consumePostLoginRedirect(redirectByRole(currentUser));
    navigate(redirectPath, { replace: true });
  }, [currentUser, navigate]);

  const params = new URLSearchParams(location.search);
  const reason = params.get("reason");
  const showExpired = reason === "session_expired" || hasSessionExpired();

  return (
    <div className="relative min-h-screen overflow-hidden bg-[linear-gradient(180deg,#f8fbff_0%,#eff6ff_42%,#f8fafc_100%)]" data-testid="login-page">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(14,165,233,0.16),transparent_30%),radial-gradient(circle_at_bottom_left,rgba(37,99,235,0.12),transparent_36%)]" />
      <div className="landing-noise pointer-events-none absolute inset-0 opacity-40" />

      <div className="relative z-10 mx-auto grid min-h-screen max-w-7xl gap-10 px-4 py-8 sm:px-6 lg:grid-cols-[0.92fr_0.88fr] lg:items-center lg:px-8 lg:py-12">
        <section className="max-w-2xl" data-testid="login-brand-panel">
          <Link to="/" className="inline-flex items-center gap-3" data-testid="login-brand-link">
            <div className="grid h-12 w-12 place-items-center rounded-2xl bg-[linear-gradient(135deg,#2563EB,#0EA5E9)] text-lg font-bold text-white shadow-[0_18px_40px_rgba(37,99,235,0.26)]" data-testid="login-brand-mark">
              S
            </div>
            <div>
              <p className="text-lg font-extrabold tracking-tight text-slate-950" data-testid="login-brand-name">Syroce</p>
              <p className="text-xs uppercase tracking-[0.22em] text-slate-500" data-testid="login-brand-tagline">Travel Agency Operating System</p>
            </div>
          </Link>

          <div className="mt-8 inline-flex items-center gap-2 rounded-full border border-blue-100 bg-white/80 px-4 py-2 text-xs font-semibold uppercase tracking-[0.24em] text-[#2563EB] shadow-[0_10px_30px_rgba(37,99,235,0.08)]" data-testid="login-hero-badge">
            <Sparkles className="h-4 w-4" />
            Syroce hesabınıza giriş yapın
          </div>

          <h1 className="mt-6 text-4xl font-extrabold leading-[1.04] tracking-[-0.05em] text-slate-950 sm:text-5xl lg:text-6xl" data-testid="login-title">
            Giriş alanı burada.
            <span className="block text-[#2563EB]" data-testid="login-title-highlight">Syroce hesabınıza devam edin.</span>
          </h1>

          <p className="mt-6 max-w-xl text-base leading-8 text-slate-600 md:text-lg" data-testid="login-subtitle">
            Rezervasyon, müşteri ve finans operasyonlarınızı yönettiğiniz panele güvenli şekilde giriş yapın veya hemen ücretsiz trial başlatın.
          </p>

          <div className="mt-8 grid gap-3" data-testid="login-proof-list">
            {LOGIN_PROOF.map((item, index) => (
              <div key={item} className="inline-flex items-start gap-3 rounded-2xl border border-white/80 bg-white/86 px-4 py-4 text-sm text-slate-700 shadow-[0_16px_40px_rgba(15,23,42,0.04)]" data-testid={`login-proof-item-${index + 1}`}>
                <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-[#2563EB]" />
                <span>{item}</span>
              </div>
            ))}
          </div>

          <div className="mt-8 flex flex-wrap gap-3" data-testid="login-secondary-cta-group">
            <Button asChild className="h-12 rounded-full bg-[linear-gradient(135deg,#2563EB,#0EA5E9)] px-6 text-sm font-semibold text-white hover:brightness-110" data-testid="login-trial-cta">
              <Link to="/signup?plan=trial">
                14 Gün Ücretsiz Dene
                <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
            <Button asChild variant="outline" className="h-12 rounded-full border-slate-200 bg-white/90 px-6 text-sm font-semibold text-slate-700 hover:bg-white" data-testid="login-back-home-cta">
              <Link to="/">Ana sayfaya dön</Link>
            </Button>
          </div>
        </section>

        <section className="w-full max-w-xl justify-self-end" data-testid="login-form-panel">
          <div className="rounded-[32px] border border-white/80 bg-white/88 p-5 shadow-[0_30px_90px_rgba(37,99,235,0.12)] backdrop-blur-xl sm:p-7">
            {showExpired && (
              <div className="mb-4 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900" data-testid="login-session-expired-banner">
                Oturumunuz sona erdi. Tekrar giriş yaptıktan sonra kaldığınız sayfaya döneceksiniz.
              </div>
            )}

            {isBootstrapping && !currentUser ? (
              <div className="mb-4 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700" data-testid="login-bootstrap-status">
                Aktif oturum kontrol ediliyor...
              </div>
            ) : null}

            <Card className="border-0 bg-transparent shadow-none">
              <CardHeader className="space-y-3 px-0 pt-0">
                <div className="inline-flex items-center gap-2 rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-[#2563EB]" data-testid="login-form-badge">
                  <CheckCircle2 className="h-4 w-4" />
                  Giriş Yap
                </div>
                <CardTitle className="text-3xl font-extrabold tracking-[-0.04em] text-slate-950" data-testid="login-form-title">
                  Hesabınıza erişin
                </CardTitle>
                <p className="text-sm leading-7 text-slate-600" data-testid="login-form-description">
                  Demo veya mevcut hesabınız için e-posta ve şifrenizle giriş yapın.
                </p>
              </CardHeader>
              <CardContent className="px-0 pb-0">
                <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" data-testid="login-form" noValidate>
                  <div className="space-y-2">
                    <Label htmlFor="email">E-posta</Label>
                    <Input
                      id="email"
                      type="email"
                      autoComplete="email"
                      placeholder="ornek@acenta.com"
                      aria-invalid={!!errors.email}
                      aria-describedby={errors.email ? "email-error" : undefined}
                      data-testid="login-email"
                      {...register("email")}
                    />
                    {errors.email && (
                      <p id="email-error" className="text-xs text-rose-600" role="alert" data-testid="login-email-error">
                        {errors.email.message}
                      </p>
                    )}
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="password">Şifre</Label>
                    <Input
                      id="password"
                      type="password"
                      autoComplete="current-password"
                      aria-invalid={!!errors.password}
                      aria-describedby={errors.password ? "password-error" : undefined}
                      data-testid="login-password"
                      {...register("password")}
                    />
                    {errors.password && (
                      <p id="password-error" className="text-xs text-rose-600" role="alert" data-testid="login-password-error">
                        {errors.password.message}
                      </p>
                    )}
                  </div>

                  {serverError ? (
                    <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700" data-testid="login-error" role="alert">
                      {serverError}
                    </div>
                  ) : null}

                  <Button
                    type="submit"
                    className="h-12 w-full rounded-full bg-[linear-gradient(135deg,#2563EB,#0EA5E9)] text-sm font-semibold text-white hover:brightness-110"
                    disabled={isSubmitting || loginMutation.isPending}
                    data-testid="login-submit"
                  >
                    {isSubmitting || loginMutation.isPending ? "Giriş yapılıyor..." : "Giriş Yap"}
                  </Button>
                </form>

                <div className="mt-6 rounded-[24px] border border-slate-200 bg-slate-50/90 px-4 py-4" data-testid="login-trial-callout">
                  <p className="text-sm font-semibold text-slate-900" data-testid="login-trial-callout-title">
                    Henüz hesabınız yok mu?
                  </p>
                  <p className="mt-2 text-sm leading-7 text-slate-600" data-testid="login-trial-callout-text">
                    14 gün ücretsiz deneyin, kredi kartı gerekmeden Syroce’un acentenize nasıl uyduğunu görün.
                  </p>
                  <Link to="/signup?plan=trial" className="mt-3 inline-flex items-center gap-2 text-sm font-semibold text-[#2563EB] transition-colors duration-200 hover:text-[#1D4ED8]" data-testid="login-trial-callout-link">
                    Trial başlat
                    <ArrowRight className="h-4 w-4" />
                  </Link>
                </div>
              </CardContent>
            </Card>
          </div>
        </section>
      </div>
    </div>
  );
}