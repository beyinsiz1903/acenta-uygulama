import React, { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { searchPublic, apiErrorMessage } from "../../lib/publicBooking";
import { Card } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import EmptyState from "../../components/EmptyState";

function formatAmount(amountCents, currency) {
  const amount = (amountCents || 0) / 100;
  try {
    return new Intl.NumberFormat("tr-TR", {
      style: "currency",
      currency: currency || "EUR",
      minimumFractionDigits: 2,
    }).format(amount);
  } catch {
    return `${amount.toFixed(2)} ${currency || "EUR"}`;
  }
}

import { useSeo } from "../../hooks/useSeo";

export default function BookSearchPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  const org = searchParams.get("org") || "";
  const partner = searchParams.get("partner") || "";
  const q = searchParams.get("q") || "";
  const page = Number(searchParams.get("page") || "1");
  const sort = searchParams.get("sort") || "price_asc";

  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [productType, setProductType] = useState("hotel");
  useSeo({
    title: "Otel Ara | " + (typeof window !== "undefined" ? window.document.title || "Syroce" : "Syroce"),
    description:
      "Organizasyonunuza ait yayındaki otel ve ürünleri arayın; tarihler ve misafir bilgileri ile hızlıca rezervasyon akışına geçin.",
    canonicalPath: "/book",
    type: "website",
  });

  const [reloadSeq, setReloadSeq] = useState(0);

  useEffect(() => {
    if (!org) {
      setItems([]);
      setTotal(0);
      return;
    }

    async function load() {
      setLoading(true);
      setError("");
      try {
        const data = await searchPublic({ org, q, page, page_size: 10, sort, partner: partner || undefined, type: productType });
        setItems(data.items || []);
        setTotal(data.total || 0);
      } catch (e) {
        // Normalized error from searchPublic: { status, code, message, raw }
        if (e && typeof e === "object" && (e.status || e.message)) {
          setError(e);
        } else {
          setError({ status: null, code: null, message: apiErrorMessage(e) });
        }
        setItems([]);
        setTotal(0);
      } finally {
        setLoading(false);
      }
    }

    load();
  }, [org, q, page, sort, partner, reloadSeq, productType]);

  const handleSearchChange = (e) => {
    const value = e.target.value;
    const next = new URLSearchParams(searchParams);
    if (value) {
      next.set("q", value);
    } else {
      next.delete("q");
    }
    next.set("page", "1");
    setSearchParams(next);
  };

  const handlePageChange = (nextPage) => {
    const value = Math.max(1, nextPage);
    const next = new URLSearchParams(searchParams);
    next.set("page", String(value));
    setSearchParams(next);
  };

  const handleSelect = (productId) => {
    if (!org) return;
    const qp = new URLSearchParams();
    qp.set("org", org);
    if (partner) qp.set("partner", partner);
    const qs = qp.toString();
    navigate(qs ? `/book/${productId}?${qs}` : `/book/${productId}`);
  };

  return (
    <div className="min-h-screen bg-slate-50 px-4 py-6 flex justify-center">
      <div className="w-full max-w-5xl space-y-4">
        <div className="space-y-1">
          <h1 className="text-xl font-semibold">Rezervasyon Yap</h1>
          <p className="text-xs text-muted-foreground">
            Organizasyonunuza ait yayındaki otel ve ürünleri listeleyin, devam adımında tarih ve misafir bilgilerini
            tamamlayın.
          </p>
        </div>

        {!org && (
          <EmptyState
            title="Kuruluş parametresi eksik"
            description="Lütfen URL&apos;ye ?org=&lt;organization_id&gt; parametresi ekleyin."
          />
        )}

        {org && (
          <Card className="p-3 flex flex-col gap-3">
            <div className="flex flex-col sm:flex-row sm:items-center gap-2">
              <div className="flex-1 flex items-center gap-2">
                <label className="text-xs text-muted-foreground w-16">Arama</label>
                <input
                  type="text"
                  className="flex-1 rounded-md border px-2 py-1 text-sm"
                  placeholder="Otel, şehir veya ürün adı"
                  value={q}
                  onChange={handleSearchChange}
                />
              </div>
              <div className="flex items-center gap-2">
                <label className="text-xs text-muted-foreground">Ürün tipi</label>
                <select
                  className="h-7 rounded-md border bg-background px-2 text-xs"
                  value={productType}
                  onChange={(e) => setProductType(e.target.value)}
                >
                  <option value="hotel">Oteller</option>
                  <option value="tour">Turlar</option>
                </select>
              </div>
              <div className="text-[11px] text-muted-foreground">
                Org: <span className="font-mono">{org}</span>
              </div>
            </div>

            {loading && (
              <div className="text-xs text-muted-foreground">Sonuçlar yükleniyor...</div>
            )}
            {!loading && error && (
              <div className="flex flex-col gap-1 text-xs text-red-600">
                <div>
                  {error.status === 429 || error.code === "RATE_LIMITED"
                    ? "Çok fazla istek atıldı, lütfen 1 dakika sonra tekrar deneyin."
                    : error.message || String(error)}
                </div>
                <div>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setReloadSeq((x) => x + 1)}
                  >
                    Tekrar dene
                  </Button>
                </div>
              </div>
            )}

            {!loading && !error && items.length === 0 && (
              <div className="space-y-2">
                <EmptyState
                  title="Sonuç bulunamadı"
                  description="Filtreleri değiştirerek tekrar deneyebilirsiniz."
                />
                <div className="border-t pt-2 mt-2 text-xs space-y-1">
                  <div className="font-medium">Demo / debug girişi</div>
                  <p className="text-[11px] text-muted-foreground">
                    Test veya demo ortamında, doğrudan bir ürün ID yazarak akışa devam edebilirsiniz.
                  </p>
                  <div className="flex gap-2 items-center">
                    <input
                      id="debug-product-id-input"
                      type="text"
                      className="flex-1 rounded-md border px-2 py-1 text-xs font-mono"
                      placeholder="örn: 65f... (productId)"
                      onKeyDown={(e) => {
                        if (e.key === "Enter" && e.currentTarget.value && org) {
                          navigate(`/book/${e.currentTarget.value}?org=${encodeURIComponent(org)}`);
                        }
                      }}
                    />
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => {
                        const input = document.querySelector("#debug-product-id-input");
                        if (input && input.value && org) {
                          navigate(`/book/${input.value}?org=${encodeURIComponent(org)}`);
                        }
                      }}
                    >
                      Devam et
                    </Button>
                  </div>
                </div>
              </div>
            )}

            {!loading && !error && items.length > 0 && (
              <div className="space-y-3">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {items.map((item) => (
                    <Card key={item.product_id} className="p-3 flex flex-col justify-between">
                      <div className="space-y-1">
                        <h2 className="text-sm font-semibold line-clamp-1">{item.title}</h2>
                        {item.summary && (
                          <p className="text-xs text-muted-foreground line-clamp-2">{item.summary}</p>
                        )}
                        <p className="text-sm font-medium mt-1">
                          {formatAmount(item.price?.amount_cents, item.price?.currency)}
                        </p>
                      </div>
                      <div className="mt-3 flex justify-end">
                        <Button size="sm" onClick={() => handleSelect(item.product_id)}>
                          Seç
                        </Button>
                      </div>
                    </Card>
                  ))}
                </div>

                <div className="flex items-center justify-between text-xs text-muted-foreground">
                  <div>
                    Sayfa {page} / {Math.max(1, Math.ceil(total / 10) || 1)}
                  </div>
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={page <= 1}
                      onClick={() => handlePageChange(page - 1)}
                    >
                      Önceki
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={items.length < 10}
                      onClick={() => handlePageChange(page + 1)}
                    >
                      Sonraki
                    </Button>
                  </div>
                </div>
              </div>
            )}
          </Card>
        )}
      </div>
    </div>
  );
}
