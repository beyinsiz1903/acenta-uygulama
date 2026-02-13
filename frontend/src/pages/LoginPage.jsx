import React, { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";

import { api, apiErrorMessage, setToken, setUser } from "../lib/api";
import { redirectByRole } from "../utils/redirectByRole";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";

export default function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("admin@acenta.test");
  const [password, setPassword] = useState("admin123");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function onSubmit(e) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const resp = await api.post("/auth/login", { email, password });
      setToken(resp.data.access_token);
      setUser(resp.data.user);
      
      // Store tenant_id for API calls (X-Tenant-Id header)
      try {
        const tid = resp.data.tenant_id || resp.data.user?.tenant_id;
        if (tid) {
          localStorage.setItem("acenta_tenant_id", tid);
        }
      } catch {}
      
      // Role-based redirect with optional return-to from sessionStorage
      let redirectPath = redirectByRole(resp.data.user);
      try {
        const saved = window.sessionStorage.getItem("acenta_post_login_redirect");

        // Minimal guard: only allow internal app routes
        if (saved && typeof saved === "string" && saved.startsWith("/app")) {
          redirectPath = saved;
        }

        window.sessionStorage.removeItem("acenta_post_login_redirect");
        window.sessionStorage.removeItem("acenta_session_expired");
      } catch {
        // ignore storage errors
      }

      navigate(redirectPath, { replace: true });
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  const params = new URLSearchParams(location.search);
  const reason = params.get("reason");

  let showExpired = reason === "session_expired";
  try {
    if (!showExpired && typeof window !== "undefined") {
      showExpired = window.sessionStorage.getItem("acenta_session_expired") === "1";
    }
  } catch {
    // ignore storage errors
  }

  return (
    <div className="min-h-screen bg-background flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        <div className="mb-6 text-center">
          <div className="mx-auto h-12 w-12 rounded-2xl bg-primary text-primary-foreground grid place-items-center font-bold">
            A
          </div>
          <h1 className="mt-3 text-2xl font-semibold text-foreground">Acenta Master</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Acenta operasyonlarınızı tek yerden yönetin.
          </p>
        </div>

        {showExpired && (
          <div className="mb-4 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
            Oturumunuz sona erdi. Tekrar giriş yaptıktan sonra kaldığınız sayfaya döneceksiniz.
          </div>
        )}

        <Card className="rounded-2xl shadow-sm">
          <CardHeader>
            <CardTitle>Giriş Yap</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={onSubmit} className="space-y-4" data-testid="login-form">
              <div className="space-y-2">
                <Label htmlFor="email">E-posta</Label>
                <Input
                  id="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="ornek@acenta.com"
                  data-testid="login-email"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="password">Şifre</Label>
                <Input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  data-testid="login-password"
                />
              </div>

              {error ? (
                <div className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700" data-testid="login-error">
                  {error}
                </div>
              ) : null}

              <Button
                type="submit"
                className="w-full"
                disabled={loading}
                data-testid="login-submit"
              >
                {loading ? "Giriş yapılıyor..." : "Giriş Yap"}
              </Button>

              <div className="text-xs text-muted-foreground">
                Demo: <span className="font-medium">admin@acenta.test</span> / <span className="font-medium">admin123</span>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
