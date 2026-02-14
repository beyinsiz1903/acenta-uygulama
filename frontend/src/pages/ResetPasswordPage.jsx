import React, { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { AlertCircle, CheckCircle2, Loader2, Lock } from "lucide-react";
import { api, apiErrorMessage } from "../lib/api";
import { Input } from "../components/ui/input";
import { Button } from "../components/ui/button";
import { Label } from "../components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";

function useQuery() {
  const { search } = useLocation();
  return React.useMemo(() => new URLSearchParams(search), [search]);
}

export default function ResetPasswordPage() {
  const query = useQuery();
  const navigate = useNavigate();

  const token = query.get("token") || "";

  const [status, setStatus] = useState("validating"); // validating | form | success | invalid | expired | used | not_found
  const [info, setInfo] = useState({ email: "", expires_at: "" });
  const [loading, setLoading] = useState(false);
  const [password, setPassword] = useState("");
  const [password2, setPassword2] = useState("");
  const [passwordError, setPasswordError] = useState("");
  const [globalError, setGlobalError] = useState("");

  useEffect(() => {
    if (!token) {
      setStatus("invalid");
      return;
    }

    let cancelled = false;

    async function validate() {
      setStatus("validating");
      setGlobalError("");
      try {
        const resp = await api.get(`/auth/password-reset/validate`, { params: { token } });
        if (cancelled) return;
        setInfo({ email: resp.data?.user_email || "", expires_at: resp.data?.expires_at || "" });
        setStatus("form");
      } catch (err) {
        if (cancelled) return;
        const resp = err?.response?.data;
        const code = resp?.error?.code;
        if (code === "token_expired") {
          setStatus("expired");
        } else if (code === "token_used") {
          setStatus("used");
        } else if (code === "token_not_found") {
          setStatus("not_found");
        } else {
          setStatus("invalid");
        }
      }
    }

    validate();

    return () => {
      cancelled = true;
    };
  }, [token]);

  function validatePasswords() {
    if (!password || password.length < 8) {
      setPasswordError("Şifre en az 8 karakter olmalıdır.");
      return false;
    }
    if (password !== password2) {
      setPasswordError("Şifreler uyuşmuyor.");
      return false;
    }
    setPasswordError("");
    return true;
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!validatePasswords()) return;

    setLoading(true);
    setGlobalError("");
    try {
      await api.post(`/auth/password-reset/confirm`, {
        token,
        new_password: password,
      });
      setStatus("success");
    } catch (err) {
      const resp = err?.response?.data;
      const code = resp?.error?.code;
      if (code === "token_expired") {
        setStatus("expired");
      } else if (code === "token_used") {
        setStatus("used");
      } else if (code === "token_not_found" || code === "invalid_token") {
        setStatus("invalid");
      } else if (code === "weak_password") {
        setPasswordError("Şifre en az 8 karakter olmalıdır.");
      } else {
        setGlobalError(apiErrorMessage(err));
      }
    } finally {
      setLoading(false);
    }
  }

  const title = "Şifre Sıfırlama";

  function renderStateContent() {
    if (!token || status === "invalid") {
      return (
        <div className="space-y-4">
          <div className="flex items-center gap-2 text-destructive">
            <AlertCircle className="h-5 w-5" />
            <div className="font-medium">Reset bağlantısı geçersiz.</div>
          </div>
          <p className="text-sm text-muted-foreground">
            Link yanlış veya eksik olabilir. Admin&apos;den yeni bir reset bağlantısı isteyebilirsiniz.
          </p>
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" onClick={() => navigate("/login")}>Giriş sayfasına dön</Button>
          </div>
        </div>
      );
    }

    if (status === "validating") {
      return (
        <div className="flex flex-col items-center justify-center gap-3 py-6">
          <Loader2 className="h-6 w-6 animate-spin text-primary" />
          <p className="text-sm text-muted-foreground">Bağlantı doğrulanıyor...</p>
        </div>
      );
    }

    if (status === "expired") {
      return (
        <div className="space-y-4">
          <div className="flex items-center gap-2 text-destructive">
            <AlertCircle className="h-5 w-5" />
            <div className="font-medium">Reset bağlantısının süresi dolmuş.</div>
          </div>
          <p className="text-sm text-muted-foreground">
            Bu reset bağlantısı artık kullanılamaz. Admin&apos;den yeni bir bağlantı talep etmeniz gerekir.
          </p>
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" onClick={() => navigate("/login")}>Giriş sayfasına dön</Button>
          </div>
        </div>
      );
    }

    if (status === "used") {
      return (
        <div className="space-y-4">
          <div className="flex items-center gap-2 text-destructive">
            <AlertCircle className="h-5 w-5" />
            <div className="font-medium">Bu reset bağlantısı daha önce kullanılmış.</div>
          </div>
          <p className="text-sm text-muted-foreground">
            Güvenlik nedeniyle aynı bağlantı birden fazla kez kullanılamaz. Gerekirse admin&apos;den yeni bir
            bağlantı isteyebilirsiniz.
          </p>
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" onClick={() => navigate("/login")}>Giriş sayfasına dön</Button>
          </div>
        </div>
      );
    }

    if (status === "not_found") {
      return (
        <div className="space-y-4">
          <div className="flex items-center gap-2 text-destructive">
            <AlertCircle className="h-5 w-5" />
            <div className="font-medium">Reset bağlantısı bulunamadı.</div>
          </div>
          <p className="text-sm text-muted-foreground">
            Bağlantı hatalı olabilir veya süresi dolmuş olabilir. Admin&apos;den yeni bir bağlantı isteyebilirsiniz.
          </p>
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" onClick={() => navigate("/login")}>Giriş sayfasına dön</Button>
          </div>
        </div>
      );
    }

    if (status === "success") {
      return (
        <div className="space-y-4">
          <div className="flex items-center gap-2 text-emerald-600">
            <CheckCircle2 className="h-5 w-5" />
            <div className="font-medium">Şifren başarıyla güncellendi.</div>
          </div>
          <p className="text-sm text-muted-foreground">
            Artık yeni şifrenle sisteme giriş yapabilirsin.
          </p>
          <div className="flex flex-wrap gap-2">
            <Button onClick={() => navigate("/login")}>Giriş sayfasına git</Button>
          </div>
        </div>
      );
    }

    // status === "form"
    return (
      <form onSubmit={handleSubmit} className="space-y-4">
        {info.email && (
          <div className="rounded-md border bg-muted/40 px-3 py-2 text-xs text-muted-foreground">
            E-posta: <span className="font-mono">{info.email}</span>
            {info.expires_at && (
              <>
                <br />
                Son geçerlilik: <span className="font-mono">{info.expires_at}</span>
              </>
            )}
          </div>
        )}

        <div className="space-y-2">
          <Label htmlFor="password">Yeni şifre</Label>
          <Input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Yeni şifreniz"
            autoComplete="new-password"
          />
          <p className="text-xs text-muted-foreground">En az 8 karakter olmalıdır.</p>
        </div>

        <div className="space-y-2">
          <Label htmlFor="password2">Yeni şifre (tekrar)</Label>
          <Input
            id="password2"
            type="password"
            value={password2}
            onChange={(e) => setPassword2(e.target.value)}
            placeholder="Yeni şifrenizi tekrar girin"
            autoComplete="new-password"
          />
        </div>

        {passwordError && <p className="text-xs text-destructive">{passwordError}</p>}
        {globalError && <p className="text-xs text-destructive">{globalError}</p>}

        <div className="flex justify-end gap-2 pt-2">
          <Button type="submit" disabled={loading} className="gap-2">
            {loading && <Loader2 className="h-4 w-4 animate-spin" />}
            Şifreyi Güncelle
          </Button>
        </div>
      </form>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-muted/40 px-4 py-6">
      <Card className="w-full max-w-md border border-border/60 shadow-lg">
        <CardHeader className="space-y-1 text-center">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 text-primary mb-2">
            <Lock className="h-6 w-6" />
          </div>
          <CardTitle className="text-xl font-semibold">{title}</CardTitle>
        </CardHeader>
        <CardContent>{renderStateContent()}</CardContent>
      </Card>
    </div>
  );
}
