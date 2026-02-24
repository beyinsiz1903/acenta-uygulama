import React, { useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

import { api, apiErrorMessage, setToken, setUser } from "../lib/api";
import { loginSchema } from "../lib/validations";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";

export default function B2BLoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const [serverError, setServerError] = useState("");

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

  async function onSubmit(data) {
    setServerError("");
    try {
      const resp = await api.post("/auth/login", {
        email: data.email,
        password: data.password,
      });
      setToken(resp.data.access_token);
      setUser(resp.data.user);

      // Store tenant_id for API calls
      try {
        const tid = resp.data.tenant_id || resp.data.user?.tenant_id;
        if (tid) {
          localStorage.setItem("acenta_tenant_id", tid);
        }
      } catch {}

      // Verify that this user has B2B access via /api/b2b/me
      await api.get("/b2b/me");

      navigate(next, { replace: true });
    } catch (err) {
      setServerError(apiErrorMessage(err));
    }
  }

  return (
    <div className="min-h-screen bg-background flex items-center justify-center px-4">
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
          <div className="mb-4 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
            {reasonText}
          </div>
        )}

        <div className="rounded-2xl shadow-sm border bg-card">
          <div className="p-6">
            <form
              onSubmit={handleSubmit(onSubmit)}
              className="space-y-4"
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
                  {...register("password")}
                />
                {errors.password && (
                  <p id="b2b-password-error" className="text-xs text-rose-600" role="alert">
                    {errors.password.message}
                  </p>
                )}
              </div>

              {serverError ? (
                <div className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700" role="alert">
                  {serverError}
                </div>
              ) : null}

              <Button
                type="submit"
                className="w-full"
                disabled={isSubmitting}
              >
                {isSubmitting ? "Giriş yapılıyor..." : "Giriş Yap"}
              </Button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
