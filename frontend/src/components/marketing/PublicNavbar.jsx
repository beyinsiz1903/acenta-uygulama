import React, { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { Menu, X } from "lucide-react";
import { Button } from "../ui/button";

const NAV_LINKS = [
  { label: "Ana Sayfa", href: "/" },
  { label: "Fiyatlar", href: "/pricing" },
  { label: "Demo", href: "/demo" },
];

export const PublicNavbar = ({ testIdPrefix = "public-nav" }) => {
  const [mobileOpen, setMobileOpen] = useState(false);
  const location = useLocation();

  return (
    <nav
      className="sticky top-0 z-50 border-b border-slate-200/60 bg-white/90 backdrop-blur-md supports-[backdrop-filter]:bg-white/75"
      data-testid={`${testIdPrefix}-bar`}
    >
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 sm:px-6 lg:px-8">
        <Link to="/" className="flex items-center gap-2.5" data-testid={`${testIdPrefix}-logo`}>
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-slate-950">
            <span className="text-sm font-bold text-white" style={{ fontFamily: "Manrope, sans-serif" }}>S</span>
          </div>
          <span className="text-lg font-bold tracking-tight text-slate-900" style={{ fontFamily: "Manrope, Inter, sans-serif" }}>
            Syroce
          </span>
        </Link>

        <div className="hidden items-center gap-6 md:flex" data-testid={`${testIdPrefix}-links`}>
          {NAV_LINKS.map((link) => (
            <Link
              key={link.href}
              to={link.href}
              className={`text-sm font-medium transition-colors duration-200 ${
                location.pathname === link.href
                  ? "text-[#2563EB]"
                  : "text-slate-600 hover:text-slate-900"
              }`}
              data-testid={`${testIdPrefix}-link-${link.href.replace("/", "") || "home"}`}
            >
              {link.label}
            </Link>
          ))}
        </div>

        <div className="hidden items-center gap-3 md:flex" data-testid={`${testIdPrefix}-actions`}>
          <Button
            asChild
            variant="ghost"
            className="h-9 rounded-full px-4 text-sm font-medium text-slate-700 hover:bg-slate-100"
            data-testid={`${testIdPrefix}-login-btn`}
          >
            <Link to="/login">Giriş Yap</Link>
          </Button>
          <Button
            asChild
            className="h-9 rounded-full bg-slate-950 px-5 text-sm font-semibold text-white hover:bg-slate-800"
            data-testid={`${testIdPrefix}-signup-btn`}
          >
            <Link to="/signup?plan=trial">Ücretsiz Deneyin</Link>
          </Button>
        </div>

        <button
          className="md:hidden p-2 rounded-lg hover:bg-slate-100 transition-colors"
          onClick={() => setMobileOpen(!mobileOpen)}
          aria-label="Menu"
          data-testid={`${testIdPrefix}-mobile-toggle`}
        >
          {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </div>

      {mobileOpen && (
        <div className="border-t border-slate-100 bg-white px-4 py-4 md:hidden animate-in slide-in-from-top-2 duration-200" data-testid={`${testIdPrefix}-mobile-menu`}>
          <div className="flex flex-col gap-3">
            {NAV_LINKS.map((link) => (
              <Link
                key={link.href}
                to={link.href}
                className={`rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                  location.pathname === link.href
                    ? "bg-slate-100 text-[#2563EB]"
                    : "text-slate-700 hover:bg-slate-50"
                }`}
                onClick={() => setMobileOpen(false)}
                data-testid={`${testIdPrefix}-mobile-link-${link.href.replace("/", "") || "home"}`}
              >
                {link.label}
              </Link>
            ))}
            <div className="mt-2 flex flex-col gap-2 border-t border-slate-100 pt-3">
              <Button asChild variant="outline" className="h-10 rounded-full text-sm font-medium" data-testid={`${testIdPrefix}-mobile-login`}>
                <Link to="/login" onClick={() => setMobileOpen(false)}>Giris Yap</Link>
              </Button>
              <Button asChild className="h-10 rounded-full bg-slate-950 text-sm font-semibold text-white" data-testid={`${testIdPrefix}-mobile-signup`}>
                <Link to="/signup?plan=trial" onClick={() => setMobileOpen(false)}>Ucretsiz Deneyin</Link>
              </Button>
            </div>
          </div>
        </div>
      )}
    </nav>
  );
};
