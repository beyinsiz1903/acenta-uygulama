import React, { useEffect, useMemo, useState } from "react";
import { api, apiErrorMessage, parseErrorDetails } from "../../lib/api";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Card } from "../../components/ui/card";
import { AlertCircle, Loader2 } from "lucide-react";

function useTenantKey() {
  const STORAGE_KEY = "marketplace:tenantKey";
  const [tenantKey, setTenantKey] = useState(() => {
    if (typeof window === "undefined") return "";
    return window.localStorage.getItem(STORAGE_KEY) || "";
  });

  const saveTenantKey = (value) => {
    setTenantKey(value);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(STORAGE_KEY, value || "");
    }
  };

  return { tenantKey, saveTenantKey };
}

export default function B2BMarketplaceCatalogPage() {
  const { tenantKey, saveTenantKey } = useTenantKey();

  const [q, setQ] = useState("");
  const [category, setCategory] = useState("");
  const [tag, setTag] = useState("");
  const [minPrice, setMinPrice] = useState("");
  const [maxPrice, setMaxPrice] = useState("");

  const [items, setItems] = useState([]);
  const [nextCursor, setNextCursor] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const headers = useMemo(() => {
    const h = {};
    if (tenantKey) h["X-Tenant-Key"] = tenantKey;
    return h;
  }, [tenantKey]);

  const fetchPage = async ({ append = false, cursor = null } = {}) => {
    if (!tenantKey) return;
    setLoading(true);
    setError("");
    try {
      const params = {};
      if (q) params.q = q;
      if (category) params.category = category;
      if (tag) params.tag = tag;
      if (minPrice) params.min_price = minPrice;
      if (maxPrice) params.max_price = maxPrice;
      if (cursor) params.cursor = cursor;

      const res = await api.get("/marketplace/catalog", { headers, params });
      const data = res.data || {};
      const newItems = data.items || [];
      setNextCursor(data.next_cursor || null);
      setItems((prev) => (append ? [...prev, ...newItems] : newItems));
    } catch (err) {
      const details = parseErrorDetails(err);
      if (details.code === "TENANT_CONTEXT_REQUIRED" || details.message?.includes("TENANT_CONTEXT_REQUIRED")) {
        setError("Marketplace kataloğunu görmek için tenant seçmelisiniz.");
      } else {
        setError(apiErrorMessage(err));
      }
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async (e) => {
    e.preventDefault();
    await fetchPage({ append: false, cursor: null });
  };

  useEffect(() => {
    if (tenantKey) {
      void fetchPage({ append: false, cursor: null });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tenantKey]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <div className="text-lg font-semibold">B2B Marketplace</div>
          <div className="max-w-xl text-[11px] text-muted-foreground">
            Diğer tenantların yayınladığı marketplace listinglerini buradan görebilir, kiminle çalışmak istediğinizi
            keşfedebilirsiniz. V1 de sadece katalog görünürlüğü vardır; rezervasyon akışı ayrıdır.
          </div>
        </div>
      </div>

      {/* Tenant key selector */}
      <div className="rounded-md border bg-white p-3 text-[11px]">
        <div className="flex flex-wrap items-center gap-3">
          <div className="space-y-1">
            <Label className="text-[11px]">Tenant Key (buyer)</Label>
            <Input
              className="h-8 text-xs min-w-[200px]"
              value={tenantKey}
              onChange={(e) => saveTenantKey(e.target.value)}
              placeholder="buyer-tenant"
            />
          </div>
          {!tenantKey && (
            <div className="flex items-center gap-1 text-[11px] text-destructive">
              <AlertCircle className="h-4 w-4" />
              <span>Marketplace erişimi için bir tenant key girin.</span>
            </div>
          )}
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-2 rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-[11px] text-destructive">
          <AlertCircle className="h-4 w-4" />
          <span>{error}</span>
        </div>
      )}

      <form
        className="grid grid-cols-1 gap-3 rounded-md border bg-white p-3 text-[11px] sm:grid-cols-5"
        onSubmit={handleSearch}
      >
        <div className="space-y-1 sm:col-span-2">
          <Label className="text-[11px]">Arama</Label>
          <Input
            className="h-8 text-xs"
            placeholder="Başlık veya açıklama"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
        </div>
        <div className="space-y-1">
          <Label className="text-[11px]">Kategori</Label>
          <Input
            className="h-8 text-xs"
            placeholder="hotel / tour / transfer"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
          />
        </div>
        <div className="space-y-1">
          <Label className="text-[11px]">Tag</Label>
          <Input
            className="h-8 text-xs"
            placeholder="örn. antalya"
            value={tag}
            onChange={(e) => setTag(e.target.value)}
          />
        </div>
        <div className="space-y-1">
          <Label className="text-[11px]">Fiyat Aralığı</Label>
          <div className="flex gap-1">
            <Input
              className="h-8 text-xs"
              placeholder="min"
              value={minPrice}
              onChange={(e) => setMinPrice(e.target.value)}
            />
            <Input
              className="h-8 text-xs"
              placeholder="max"
              value={maxPrice}
              onChange={(e) => setMaxPrice(e.target.value)}
            />
          </div>
        </div>
        <div className="flex items-end justify-end">
          <Button type="submit" size="sm" className="h-8 text-xs" disabled={loading || !tenantKey}>
            {loading ? "Yükleniyor..." : "Ara"}
          </Button>
        </div>
      </form>

      {!loading && items.length === 0 && tenantKey && !error && (
        <p className="text-[11px] text-muted-foreground">
          Şu an için bu tenant için görünür bir marketplace listingi bulunmuyor. Erişimi olan satıcılar henüz
          yayınlamamış olabilir.
        </p>
      )}

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        {items.map((item) => (
          <Card key={item.id} className="flex flex-col justify-between p-3 text-[11px]">
            <div className="space-y-1">
              <div className="flex items-center justify-between gap-2">
                <div>
                  <div className="text-xs font-semibold">{item.title}</div>
                  <div className="text-[10px] text-muted-foreground">
                    Kategori: {item.category || "-"}
                  </div>
                </div>
                <div className="text-sm font-bold">
                  {item.price} {item.currency}
                </div>
              </div>
              <div className="text-[10px] text-muted-foreground">
                Seller tenant: <span className="font-mono">{item.seller_tenant_id}</span>
              </div>
              <div className="mt-1 flex flex-wrap gap-1">
                {(item.tags || []).map((t) => (
                  <span
                    key={t}
                    className="rounded-full bg-muted px-2 py-0.5 text-[10px] text-muted-foreground"
                  >
                    #{t}
                  </span>
                ))}
              </div>
            </div>
            <div className="mt-2 flex items-center justify-between text-[10px] text-muted-foreground">
              <span>
                Bu kart sadece katalog içindir; rezervasyon/teklif akışı ayrı PR'larda eklenecektir.
              </span>
              <div className="flex items-center gap-2">
                <Button
                  type="button"
                  size="xs"
                  className="h-7 text-[11px]"
                  variant="default"
                  onClick={async () => {
                    try {
                      if (!tenantKey) {
                        setError("Marketplace kataloğunu görmek için tenant seçmelisiniz.");
                        return;
                      }

                      setError("");
                      const res = await api.post(
                        "/b2b/bookings",
                        {
                          source: "marketplace",
                          listing_id: item.id,
                          customer: {
                            full_name: "Marketplace M 7f3131eri",
                            email: "marketplace@example.com",
                            phone: "+900000000000",
                          },
                          travellers: [
                            { first_name: "Test", last_name: "User" },
                          ],
                        },
                        { headers },
                      );

                      const bookingId = res?.data?.booking_id;
                      if (bookingId) {
                        window.alert(`Taslak olu7fturuldu: ${bookingId}`);
                      } else {
                        setError("Taslak olu7fturma cevab31 beklenen formatta de31l.");
                      }
                    } catch (err) {
                      const details = parseErrorDetails(err);
                      const code = details?.code;
                      if (code === "TENANT_CONTEXT_REQUIRED") {
                        setError("Tenant se31melisiniz.");
                      } else if (code === "MARKETPLACE_ACCESS_FORBIDDEN") {
                        setError("Bu listing'e eri5fiminiz yok.");
                      } else {
                        setError(apiErrorMessage(err));
                      }
                    }
                  }}
                >
                  B2B Taslak Olu7ftur
                </Button>
                <Button
                  type="button"
                  size="xs"
                  className="h-7 text-[11px]"
                  variant="outline"
                  onClick={async () => {
                  try {
                    if (!tenantKey) {
                      setError("Marketplace kataloğunu görmek için tenant seçmelisiniz.");
                      return;
                    }
                    setError("");
                    const res = await api.post(
                      `/marketplace/catalog/${encodeURIComponent(item.id)}/create-storefront-session`,
                      null,
                      { headers },
                    );
                    const redirectUrl = res?.data?.redirect_url;
                    if (redirectUrl) {
                      window.open(redirectUrl, "_blank");
                    } else {
                      setError("Redirect URL alınamadı.");
                    }
                  } catch (err) {
                    const details = parseErrorDetails(err);
                    const code = details?.code;
                    if (code === "TENANT_CONTEXT_REQUIRED") {
                      setError("Marketplace kataloğunu görmek için tenant seçmelisiniz.");
                    } else if (code === "MARKETPLACE_ACCESS_FORBIDDEN") {
                      setError("Bu listing'e erişimin yok.");
                    } else {
                      setError(apiErrorMessage(err));
                    }
                  }
                }}
              >
                Vitrine gönder
              </Button>
            </div>
          </Card>
        ))}
      </div>

      {nextCursor && (
        <div className="flex justify-center pt-2">
          <Button
            type="button"
            size="sm"
            className="h-8 text-xs"
            disabled={loading}
            onClick={() => fetchPage({ append: true, cursor: nextCursor })}
          >
            {loading ? "Yükleniyor..." : "Daha fazla yükle"}
          </Button>
        </div>
      )}
    </div>
  );
}
