import React from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { Button } from "../components/ui/button";
import { ArrowLeft, Home, Compass } from "lucide-react";
import { getUser } from "../lib/api";

/**
 * 404 — sayfa bulunamadı.
 *
 * Polished in T013:
 *   - Suggests the most useful destination based on auth state (logged-in
 *     users go to /app, guests go to /login).
 *   - Provides a "Geri dön" action that uses browser history when available.
 *   - Surfaces the unknown path so users can spot typos in the address bar.
 */
export default function NotFoundPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const user = (() => {
    try {
      return getUser();
    } catch {
      return null;
    }
  })();
  const isAuthed = Boolean(user);
  const homeHref = isAuthed ? "/app" : "/login";
  const homeLabel = isAuthed ? "Panele dön" : "Giriş ekranına dön";

  const handleBack = () => {
    if (window.history.length > 1) {
      navigate(-1);
    } else {
      navigate(homeHref, { replace: true });
    }
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4 bg-background">
      <div className="max-w-md w-full text-center space-y-6">
        <div className="space-y-2">
          <div className="text-7xl font-bold tracking-tighter text-muted-foreground/40 select-none">
            404
          </div>
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">
            Sayfa bulunamadı
          </h1>
          <p className="text-sm text-muted-foreground">
            Aradığınız sayfa mevcut değil veya taşınmış olabilir. Lütfen
            adresi kontrol edin ya da aşağıdaki seçeneklerden birini kullanın.
          </p>
        </div>

        {location.pathname && (
          <div className="rounded-md border border-border bg-muted/30 px-3 py-2 text-xs text-muted-foreground font-mono break-all">
            {location.pathname}
          </div>
        )}

        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-center gap-2 pt-2">
          <Button variant="outline" onClick={handleBack} className="gap-2">
            <ArrowLeft className="h-4 w-4" />
            Geri dön
          </Button>
          <Button asChild className="gap-2">
            <Link to={homeHref}>
              <Home className="h-4 w-4" />
              {homeLabel}
            </Link>
          </Button>
        </div>

        {isAuthed && (
          <div className="pt-2">
            <Link
              to="/app"
              className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
            >
              <Compass className="h-3 w-3" />
              Ana panelden navigasyon menüsünü kullanın
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
