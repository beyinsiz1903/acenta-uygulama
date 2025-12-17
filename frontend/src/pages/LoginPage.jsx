import React, { useState } from "react";
import { useNavigate } from "react-router-dom";

import { api, apiErrorMessage, setToken, setUser } from "../lib/api";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";

export default function LoginPage() {
  const navigate = useNavigate();
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
      navigate("/app");
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
            A
          </div>
          <h1 className="mt-3 text-2xl font-semibold text-foreground">Acenta Master</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Acenta operasyonlarını tek panelden yönet.
          </p>
        </div>

        <Card className="rounded-2xl shadow-sm">
          <CardHeader>
            <CardTitle>Giriş Yap</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={onSubmit} className="space-y-4" data-testid="login-form">
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
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
