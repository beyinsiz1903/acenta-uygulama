import React, { useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

import { api, apiErrorMessage } from "../lib/api";
import { useCurrentUser, useLogin } from "../hooks/useAuth";
import { loginSchema } from "../lib/validations";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";

export default function B2BLoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const [serverError, setServerError] = useState("");
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

  const params = new URLSearchParams(location.search);
  const reason = params.get("reason");
  const next = params.get("next") || "/b2b/bookings";
  const hasSessionExpired = reason === "session_expired";

  const reasonText = useMemo(() => {
    if (hasSessionExpired) {
      return "Oturumunuz sona erdi. Lütfen tekrar giriş yapın.";
    }
    return null;
  }, [hasSessionExpired]);

  React.useEffect(() => {
    if (!currentUser) {
      return;
    }

    api.get("/b2b/me")
      .then(() => {
        navigate(next, { replace: true });
      })
      .catch(() => {
        // aktif oturum var ama B2B yetkisi yoksa login ekranında kal
      });
  }, [currentUser, navigate, next]);

  async function onSubmit(data) {
    setServerError("");
    try {
      const resp = await loginMutation.mutateAsync({
        email: data.email,
        password: data.password,
      });

      if (!resp?.user) {
        setServerError("Giriş yanıtı eksik. Lütfen tekrar deneyin.");
        return;
      }

      // Verify that this user has B2B access via /api/b2b/me
      await api.get("/b2b/me");

      try {
        window.sessionStorage.removeItem("acenta_session_expired");
      } catch {
        // ignore sessionStorage errors
      }

      navigate(next, { replace: true });
    } catch (err) {
      setServerError(apiErrorMessage(err));
    }
  }

  return (
    <div className="min-h-screen bg-background flex items-center justify-center px-4" data-testid="b2b-login-page">
      <div className="w-full max-w-md">
        <div className="mb-6 text-center">
          <div className="mx-auto h-12 w-12 rounded-2xl bg-primary text-primary-foreground grid place-items-center font-bold text-xs">
            B2B
          </div>
          <h1 className="mt-3 text-2xl font-semibold text-foreground">
            B2B Portal Giriş
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Bayi rezervasyonlarını ve carini bu ekrandan yönet.
          </p>
        </div>

        {reasonText && (
          <div className="mb-4 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900" data-testid="b2b-login-session-expired-banner">
            {reasonText}
          </div>
        )}

        {isBootstrapping && !currentUser ? (
          <div className="mb-4 rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700" data-testid="b2b-login-bootstrap-status">
            Aktif oturum kontrol ediliyor...
          </div>
        ) : null}

        <div className="rounded-2xl shadow-sm border bg-card">
          <div className="p-6">
            <form
              onSubmit={handleSubmit(onSubmit)}
              className="space-y-4"
              data-testid="b2b-login-form"
              noValidate
            >
              <div className="space-y-2">
                <Label htmlFor="b2b-email">Email</Label>
                <Input
                  id="b2b-email"
                  type="email"
                  autoComplete="email"
                  placeholder="ornek@acenta.com"
                  aria-invalid={!!errors.email}
                  aria-describedby={errors.email ? "b2b-email-error" : undefined}
                  data-testid="b2b-login-email"
                  {...register("email")}
                />
                {errors.email && (
                  <p id="b2b-email-error" className="text-xs text-rose-600" role="alert">
                    {errors.email.message}
                  </p>
                )}
              </div>
              <div className="space-y-2">
                <Label htmlFor="b2b-password">Şifre</Label>
                <Input
                  id="b2b-password"
                  type="password"
                  autoComplete="current-password"
                  aria-invalid={!!errors.password}
                  aria-describedby={errors.password ? "b2b-password-error" : undefined}
                  data-testid="b2b-login-password"
                  {...register("password")}
                />
                {errors.password && (
                  <p id="b2b-password-error" className="text-xs text-rose-600" role="alert">
                    {errors.password.message}
                  </p>
                )}
              </div>

              {serverError ? (
                <div className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700" role="alert" data-testid="b2b-login-error">
                  {serverError}
                </div>
              ) : null}

              <Button
                type="submit"
                className="w-full"
                disabled={isSubmitting || loginMutation.isPending}
                data-testid="b2b-login-submit"
              >
                {isSubmitting || loginMutation.isPending ? "Giriş yapılıyor..." : "Giriş Yap"}
              </Button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
