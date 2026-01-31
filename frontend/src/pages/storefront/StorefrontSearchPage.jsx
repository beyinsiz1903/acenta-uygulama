import React, { useEffect, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { api, apiErrorMessage } from "../../lib/api";
import { Card } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import EmptyState from "../../components/EmptyState";

function TenantHeader({ loading, error, tenant }) {
  const title = tenant?.theme_config?.home_title || tenant?.brand_name || tenant?.tenant_key;
  const logoUrl = tenant?.theme_config?.logo_url;

  return (
    <header className="border-b bg-white/80 backdrop-blur">
      <div className="mx-auto flex max-w-5xl items-center justify-between gap-3 px-4 py-3">
        <div className="flex items-center gap-2">
          {logoUrl && (
            <img
              src={logoUrl}
              alt={title}
              className="h-8 w-8 rounded-sm border object-cover"
            />
          )}
          <div>
            <div className="text-base font-semibold leading-tight">{title || "Storefront"}</div>
            <div className="text-[10px] text-muted-foreground">
              {tenant?.tenant_key ? `Tenant: ${tenant.tenant_key}` : "White-label B2C vitrini"}
            </div>
          </div>
        </div>
        {loading && (
          <div className="text-[11px] text-muted-foreground">
            Tema yükleniyor...
          </div>
        )}
        {error && (
          <div className="text-[11px] text-destructive" title={error}>
            Tema yüklenemedi
          </div>
        )}
      </div>
    </header>
  );
}

export default function StorefrontSearchPage() {
  const { tenantKey } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  const [tenant, setTenant] = useState(null);
  const [tenantLoading, setTenantLoading] = useState(false);
  const [tenantError, setTenantError] = useState("");

  // Apply simple theme CSS variables based on tenant.theme_config
  useEffect(() => {
    if (!tenant || !tenant.theme_config) return;
    const root = document.documentElement;
    const cfg = tenant.theme_config || {};
    if (cfg.primary_color) {
      root.style.setProperty("--sf-primary", cfg.primary_color);
    }
    if (cfg.secondary_color) {
      root.style.setProperty("--sf-secondary", cfg.secondary_color);
    }
    if (cfg.font_family) {
      root.style.setProperty("--sf-font", cfg.font_family);
    }
    root.setAttribute("data-storefront-tenant", tenant.tenant_key || "");
  }, [tenant]);

  const [city, setCity] = useState(searchParams.get("city") || "IST");
  const [checkIn, setCheckIn] = useState(searchParams.get("check_in") || "");
  const [checkOut, setCheckOut] = useState(searchParams.get("check_out") || "");
  const [guests, setGuests] = useState(Number(searchParams.get("guests") || 2));

  const [searchId, setSearchId] = useState(searchParams.get("search_id") || "");
  const [lastSearchParams, setLastSearchParams] = useState({
    city: searchParams.get("city") || "IST",
    check_in: searchParams.get("check_in") || "",
    check_out: searchParams.get("check_out") || "",
    guests: Number(searchParams.get("guests") || 2),
  });
  const [offers, setOffers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!tenantKey) return;

    const cacheKey = `storefront:tenant:${tenantKey}`;
    const cached = window.sessionStorage.getItem(cacheKey);
    if (cached) {
      try {
        const parsed = JSON.parse(cached);
        setTenant(parsed);
      } catch {
        // ignore parse errors
      }
    }

    async function loadTheme() {
      setTenantLoading(true);
      setTenantError("");
      try {
        const res = await api.get("/storefront/health", {
          headers: { "X-Tenant-Key": tenantKey },
        });
        const data = res.data || null;
        setTenant(data);
        if (data) {
          window.sessionStorage.setItem(cacheKey, JSON.stringify(data));
        }
      } catch (err) {
        const msg = apiErrorMessage(err);
        setTenantError(msg);
      } finally {
        setTenantLoading(false);
      }
    }
    if (!cached) {
  const handleSearch = async (e) => {
    e.preventDefault();
    await runSearch({ city, check_in: checkIn, check_out: checkOut, guests });
  };

  const handleRetryExpired = async () => {
    await runSearch(lastSearchParams);
  };

      void loadTheme();
    }
  }, [tenantKey]);

  const runSearch = async (paramsObj) => {
    if (!tenantKey) return;
    setLoading(true);
    setError("");
    setOffers([]);
    try {
      const params = new URLSearchParams();
      if (paramsObj.check_in) params.set("check_in", paramsObj.check_in);
      if (paramsObj.check_out) params.set("check_out", paramsObj.check_out);
      if (paramsObj.city) params.set("city", paramsObj.city);
      if (paramsObj.guests) params.set("guests", String(paramsObj.guests));

      const res = await api.get(`/storefront/search?${params.toString()}`, {
        headers: { "X-Tenant-Key": tenantKey },
      });
      const data = res.data || {};
      setSearchId(data.search_id || "");
      setOffers(data.offers || []);
      const next = new URLSearchParams(searchParams);
      if (data.search_id) next.set("search_id", data.search_id);
      next.set("city", paramsObj.city || "");
      if (paramsObj.check_in) next.set("check_in", paramsObj.check_in);
      if (paramsObj.check_out) next.set("check_out", paramsObj.check_out);
      next.set("guests", String(paramsObj.guests || ""));
      setSearchParams(next, { replace: true });
      setLastSearchParams(paramsObj);
    } catch (err) {
      const resp = err?.response?.data;
      const code = resp?.error?.code;
      if (code === "SESSION_EXPIRED") {
        setError("Arama oturumu süresi doldu. Lütfen tekrar arama yapın.");
      } else if (code === "TENANT_NOT_FOUND") {
        setError("Bu site bulunamadı. Lütfen geçerli bir bağlantı kullanın.");
      } else {
        setError(apiErrorMessage(err));
      }
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async (e) => {
    e.preventDefault();
    await runSearch({ city, check_in: checkIn, check_out: checkOut, guests });
  };

  const handleSelectOffer = (offer) => {
    if (!tenantKey || !searchId) return;
    const qp = new URLSearchParams();
    qp.set("search_id", searchId);
    navigate(`/s/${encodeURIComponent(tenantKey)}/offers/${encodeURIComponent(offer.offer_id)}?${qp.toString()}`);
  };

  if (!tenantKey) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 px-4">
        <EmptyState
          title="Tenant anahtarı eksik"
          description="Lütfen URL'yi /s/:tenantKey formatında kullanın."
        />
      </div>
    );
  }

  if (tenantError && !tenantLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 px-4">
        <EmptyState
          title="Bu site bulunamadı"
          description="Lütfen bağlantıyı kontrol edin veya destek ile iletişime geçin."
        />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <TenantHeader loading={tenantLoading} error={tenantError} tenant={tenant} />
      <main className="flex-1">
        <div className="mx-auto flex max-w-5xl flex-col gap-4 px-4 py-6">
          <form
            className="grid grid-cols-1 gap-3 rounded-md border bg-white p-3 text-[11px] sm:grid-cols-4"
            onSubmit={handleSearch}
          >
            <div className="space-y-1">
              <Label className="text-[11px]">Şehir</Label>
              <Input
                className="h-8 text-xs"
                value={city}
                onChange={(e) => setCity(e.target.value)}
                placeholder="IST veya şehir adı"
              />
            </div>
            <div className="space-y-1">
              <Label className="text-[11px]">Giriş</Label>
              <Input
                type="date"
                className="h-8 text-xs"
                value={checkIn}
                onChange={(e) => setCheckIn(e.target.value)}
              />
            </div>
            <div className="space-y-1">
              <Label className="text-[11px]">Çıkış</Label>
              <Input
                type="date"
                className="h-8 text-xs"
                value={checkOut}
                onChange={(e) => setCheckOut(e.target.value)}
              />
            </div>
            <div className="space-y-1">
              <Label className="text-[11px]">Misafir</Label>
              <Input
                type="number"
                min={1}
                className="h-8 text-xs"
                value={guests}
                onChange={(e) => setGuests(Number(e.target.value) || 1)}
              />
            </div>
            <div className="sm:col-span-4 flex justify-end gap-2">
              <Button type="submit" size="sm" className="h-8 text-xs" disabled={loading}>
                {loading ? "Aranıyor..." : "Ara"}
              </Button>
            </div>
          </form>

          {error && (
            <div className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-[11px] text-destructive">
              {error}
            </div>
          )}

          {!loading && !error && offers.length === 0 && searchId && (
            <EmptyState
              title="Sonuç bulunamadı"
              description="Bu kriterlerle uygun teklif bulunamadı. Farklı tarih veya şehir deneyebilirsiniz."
            />
          )}

          {!loading && offers.length > 0 && (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              {offers.map((offer) => (
                <Card key={offer.offer_id} className="flex flex-col justify-between p-3 text-[11px]">
                  <div className="space-y-1">
                    <div className="text-xs font-semibold">Teklif #{offer.offer_id}</div>
                    <div className="text-xs text-muted-foreground">
                      {offer.supplier || "mock"}
                    </div>
                    <div className="mt-1 text-sm font-bold">
                      {offer.total_amount} {offer.currency}
                    </div>
                  </div>
                  <div className="mt-3 flex justify-end">
                    <Button
                      size="sm"
                      className="h-8 text-xs"
                      onClick={() => handleSelectOffer(offer)}
                    >
                      Devam et
                    </Button>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
