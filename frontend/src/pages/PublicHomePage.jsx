import React, { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Button } from "../components/ui/button";
import { useSeo } from "../hooks/useSeo";
import { apiErrorMessage } from "../lib/publicBooking";
import { api } from "../lib/api";

export default function PublicHomePage() {
  const [searchParams] = useSearchParams();
  const org = searchParams.get("org") || "";

  const [navPages, setNavPages] = useState([]);
  const [featuredProducts, setFeaturedProducts] = useState([]);
  const [featuredTours, setFeaturedTours] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useSeo({
    title: null,
    description:
      "Syroce ile B2B acentalar ve oteller için modern rezervasyon, fiyatlama ve funnel izleme çözümleri.",
    canonicalPath: "/",
    type: "website",
  });

  useEffect(() => {
    if (!org) return;

    let cancelled = false;

    async function load() {
      setLoading(true);
      setError("");
      try {
        // CMS nav pages
        const cmsRes = await api.get("/public/cms/pages", { params: { org } });
        if (!cancelled) {
          setNavPages(cmsRes.data?.items || []);
        }

        // Featured products (hotels etc.)
        const prodRes = await api.get("/public/search", {
          params: { org, page: 1, page_size: 4, sort: "price_asc" },
        });
        if (!cancelled) {
          setFeaturedProducts(prodRes.data?.items || []);
        }

        // Featured tours (from tours collection)
        const tourRes = await api.get("/public/tours/search", {
          params: { org, page: 1, page_size: 4 },
        });
        if (!cancelled) {
          setFeaturedTours(tourRes.data?.items || []);
        }
      } catch (e) {
        if (cancelled) return;
        setError(apiErrorMessage(e));
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [org]);

  const buildCmsUrl = (slug) => {
    if (!slug) return "/";
    const qp = new URLSearchParams();
    if (org) qp.set("org", org);
    const qs = qp.toString();
    return qs ? `/p/${slug}?${qs}` : `/p/${slug}`;
  };

  const buildBookUrl = () => {
    const qp = new URLSearchParams();
    if (org) qp.set("org", org);
    const qs = qp.toString();
    return qs ? `/book?${qs}` : "/book";
  };

  const buildB2BUrl = () => "/b2b/login";
  const buildAdminUrl = () => "/login";

  return (
    <div
      className="min-h-screen flex flex-col"
      style={{ backgroundColor: "var(--color-background)", color: "var(--color-foreground)" }}
    >
      <header className="w-full border-b" style={{ borderColor: "var(--color-border)" }}>
        <div className="mx-auto max-w-4xl px-4 py-3 flex items-center justify-between">
          <div className="text-sm font-semibold tracking-tight">Syroce</div>
          <div className="flex items-center gap-3 text-xs">
            <Link to={buildBookUrl()} className="hover:underline">
              Rezervasyon
            </Link>
            {navPages.map((p) => (
              <Link key={p.id} to={buildCmsUrl(p.slug)} className="hover:underline">
                {p.title || p.slug}
              </Link>
            ))}
            <Link to={buildB2BUrl()} className="hover:underline">
              B2B Giriş
            </Link>
            <Link to={buildAdminUrl()} className="hover:underline">
              Admin Giriş
            </Link>
          </div>
        </div>
      </header>

      <main className="flex-1 flex items-center justify-center">
        <div className="text-center space-y-4">
          <h1 className="text-3xl sm:text-4xl font-semibold tracking-tight">
            Syroce ile Akıllı Rezervasyon Yönetimi
          </h1>
          <p className="text-sm sm:text-base text-muted-foreground">
            B2B acentalar ve oteller için tasarlanmış modern fiyatlama, funnel izleme ve operasyon araçları.
          </p>
          <div className="flex flex-col sm:flex-row gap-3 justify-center mt-4">
            <Button
              asChild
              className="px-6"
              style={{
                backgroundColor: "var(--color-primary)",
                color: "var(--color-primary-foreground)",
              }}
            >
              <Link to={buildBookUrl()}>Hemen Ara</Link>
            </Button>
            <Button asChild variant="outline" className="px-6 text-xs sm:text-sm">
              <Link to={buildB2BUrl()}>B2B Portala Giriş</Link>
            </Button>
          </div>
        </div>

        {error && (
          <p className="text-xs text-red-600 text-center mt-4">{error}</p>
        )}

        {!error && org && (
          <div className="mt-8 grid grid-cols-1 md:grid-cols-2 gap-6">
            <section className="space-y-3">
              <h2 className="text-sm font-semibold tracking-tight">Öne Çıkan Ürünler</h2>
              {loading && featuredProducts.length === 0 ? (
                <p className="text-xs text-muted-foreground">Ürünler yükleniyor...</p>
              ) : featuredProducts.length === 0 ? (
                <p className="text-xs text-muted-foreground">Henüz öne çıkan ürün bulunmuyor.</p>
              ) : (
                <ul className="space-y-2 text-xs">
                  {featuredProducts.map((item) => {
                    const qp = new URLSearchParams();
                    if (org) qp.set("org", org);
                    const qs = qp.toString();
                    const url = qs
                      ? `/book/${item.product_id || item.id}?${qs}`
                      : `/book/${item.product_id || item.id}`;
                    return (
                      <li
                        key={item.product_id || item.id}
                        className="flex items-center justify-between rounded-md border px-3 py-2 bg-card/50"
                      >
                        <div className="space-y-0.5">
                          <div className="text-sm font-medium line-clamp-1">{item.title}</div>
                          {item.summary && (
                            <div className="text-[11px] text-muted-foreground line-clamp-2">{item.summary}</div>
                          )}
                        </div>
                        <Button asChild size="sm" variant="outline" className="ml-3 text-[11px] px-3 py-1">
                          <Link to={url}>İncele</Link>
                        </Button>
                      </li>
                    );
                  })}
                </ul>
              )}
            </section>

            <section className="space-y-3">
              <h2 className="text-sm font-semibold tracking-tight">Öne Çıkan Turlar</h2>
              {loading && featuredTours.length === 0 ? (
                <p className="text-xs text-muted-foreground">Turlar yükleniyor...</p>
              ) : featuredTours.length === 0 ? (
                <p className="text-xs text-muted-foreground">Henüz öne çıkan tur bulunmuyor.</p>
              ) : (
                <ul className="space-y-2 text-xs">
                  {featuredTours.map((tour) => {
                    const qp = new URLSearchParams();
                    if (org) qp.set("org", org);
                    const qs = qp.toString();
                    const url = qs ? `/book/tour/${tour.id}?${qs}` : `/book/tour/${tour.id}`;
                    return (
                      <li
                        key={tour.id}
                        className="flex items-center justify-between rounded-md border px-3 py-2 bg-card/50"
                      >
                        <div className="space-y-0.5">
                          <div className="text-sm font-medium line-clamp-1">{tour.name}</div>
                          {tour.destination && (
                            <div className="text-[11px] text-muted-foreground line-clamp-1">
                              {tour.destination}
                            </div>
                          )}
                        </div>
                        <Button asChild size="sm" variant="outline" className="ml-3 text-[11px] px-3 py-1">
                          <Link to={url}>Detay</Link>
                        </Button>
                      </li>
                    );
                  })}
                </ul>
              )}
            </section>
          </div>
        )}
      </main>

      <footer
        className="w-full border-t mt-8 text-[11px] text-muted-foreground"
        style={{ borderColor: "var(--color-border)" }}
      >
        <div className="mx-auto max-w-4xl px-4 py-3 flex items-center justify-between">
          <div>© {new Date().getFullYear()} Syroce</div>
          <div className="flex gap-3">
            <Link to="/book" className="hover:underline">
              Rezervasyon
            </Link>
            <Link to="/b2b/login" className="hover:underline">
              B2B Portal
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
