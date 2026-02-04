import React, { useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { api, apiErrorMessage, setToken, setUser } from "../lib/api";

export default function B2BLoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("agency1@acenta.test");
  const [password, setPassword] = useState("agency123");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

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

  async function onSubmit(e) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const resp = await api.post("/auth/login", { email, password });
      setToken(resp.data.access_token);
      setUser(resp.data.user);

      // Verify that this user has B2B access via /api/b2b/me
      await api.get("/b2b/me");

      navigate(next, { replace: true });
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-background flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        <div className="mb-6 text-center">
          <div className="mx-auto h-12 w-12 rounded-2xl bg-primary text-primary-foreground grid place-items-center font-bold">
            B2B
          </div>
          <h1 className="mt-3 text-2xl font-semibold text-foreground">B2B Portal Giriş</h1>
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
            <form onSubmit={onSubmit} className="space-y-4">
              <div className="space-y-2">
                <label htmlFor="email" className="text-sm font-medium">
                  Email
                </label>
                <input
                  id="email"
                  className="w-full border rounded-md px-3 py-2 text-sm"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="ornek@acenta.com"
                />
              </div>
              <div className="space-y-2">
                <label htmlFor="password" className="text-sm font-medium">
                  Şifre
                </label>
                <input
                  id="password"
                  type="password"
                  className="w-full border rounded-md px-3 py-2 text-sm"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </div>

              {error ? (
                <div className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
                  {error}
                </div>
              ) : null}

              <button
                type="submit"
                className="w-full inline-flex items-center justify-center rounded-md bg-primary text-primary-foreground text-sm px-3 py-2 disabled:opacity-60"
                disabled={loading}
              >
                {loading ? "Giriş yapılıyor..." : "Giriş Yap"}
              </button>

              <div className="text-xs text-muted-foreground mt-1">
                Demo: <span className="font-medium">agency1@demo.test</span> / <span className="font-medium">agency123</span>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
