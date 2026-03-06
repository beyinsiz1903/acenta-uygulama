import React, { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

import { apiErrorMessage } from "../lib/api";
import { useCurrentUser, useLogin } from "../hooks/useAuth";
import { redirectByRole } from "../utils/redirectByRole";
import { loginSchema } from "../lib/validations";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";

export default function LoginPage() {
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

      // Role-based redirect with optional return-to from sessionStorage
      let redirectPath = redirectByRole(resp.user);
      try {
        const saved = window.sessionStorage.getItem("acenta_post_login_redirect");
        if (saved && typeof saved === "string" && saved.startsWith("/app")) {
          redirectPath = saved;
        }
        window.sessionStorage.removeItem("acenta_post_login_redirect");
        window.sessionStorage.removeItem("acenta_session_expired");
      } catch {}

      navigate(redirectPath, { replace: true });
    } catch (err) {
      setServerError(apiErrorMessage(err));
    }
  }

  React.useEffect(() => {
    if (!currentUser) {
      return;
    }

    let redirectPath = redirectByRole(currentUser);
    try {
      const saved = window.sessionStorage.getItem("acenta_post_login_redirect");
      if (saved && typeof saved === "string" && saved.startsWith("/app")) {
        redirectPath = saved;
      }
      window.sessionStorage.removeItem("acenta_post_login_redirect");
      window.sessionStorage.removeItem("acenta_session_expired");
    } catch {
      // ignore sessionStorage errors
    }

    navigate(redirectPath, { replace: true });
  }, [currentUser, navigate]);

  const params = new URLSearchParams(location.search);
  const reason = params.get("reason");

  let showExpired = reason === "session_expired";
  try {
    if (!showExpired && typeof window !== "undefined") {
      showExpired =
        window.sessionStorage.getItem("acenta_session_expired") === "1";
    }
  } catch {}

  return (
    <div className="min-h-screen bg-background flex items-center justify-center px-4" data-testid="login-page">
      <div className="w-full max-w-md">
        <div className="mb-6 text-center">
          <div className="mx-auto h-12 w-12 rounded-2xl bg-primary text-primary-foreground grid place-items-center font-bold">
            A
          </div>
          <h1 className="mt-3 text-2xl font-semibold text-foreground">
            Acenta Master
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Acenta operasyonlarınızı tek yerden yönetin.
          </p>
        </div>

        {showExpired && (
          <div className="mb-4 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900" data-testid="login-session-expired-banner">
            Oturumunuz sona erdi. Tekrar giriş yaptıktan sonra kaldığınız
            sayfaya döneceksiniz.
          </div>
        )}

        {isBootstrapping && !currentUser ? (
          <div className="mb-4 rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700" data-testid="login-bootstrap-status">
            Aktif oturum kontrol ediliyor...
          </div>
        ) : null}

        <Card className="rounded-2xl shadow-sm">
          <CardHeader>
            <CardTitle>Giriş Yap</CardTitle>
          </CardHeader>
          <CardContent>
            <form
              onSubmit={handleSubmit(onSubmit)}
              className="space-y-4"
              data-testid="login-form"
              noValidate
            >
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
                  <p id="email-error" className="text-xs text-rose-600" role="alert">
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
                  <p id="password-error" className="text-xs text-rose-600" role="alert">
                    {errors.password.message}
                  </p>
                )}
              </div>

              {serverError ? (
                <div
                  className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700"
                  data-testid="login-error"
                  role="alert"
                >
                  {serverError}
                </div>
              ) : null}

              <Button
                type="submit"
                className="w-full"
                disabled={isSubmitting || loginMutation.isPending}
                data-testid="login-submit"
              >
                {isSubmitting || loginMutation.isPending ? "Giriş yapılıyor..." : "Giriş Yap"}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
