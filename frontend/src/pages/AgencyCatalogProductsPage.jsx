import React, { useEffect, useState } from "react";
import { api, apiErrorMessage, getUser } from "../lib/api";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { Switch } from "../components/ui/switch";
import { Label } from "../components/ui/label";
import { Card } from "../components/ui/card";
import { toast } from "react-hot-toast";

const PRODUCT_TYPES = [
  { value: "", label: "Tümü" },
  { value: "tour", label: "Tur" },
  { value: "hotel", label: "Otel" },
  { value: "transfer", label: "Transfer" },
  { value: "car", label: "Araç" },
  { value: "activity", label: "Aktivite" },
];

function isAdmin() {
  const user = getUser();
  return user?.roles?.includes("agency_admin");
}

export default function AgencyCatalogProductsPage() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [type, setType] = useState("");
  const [activeOnly, setActiveOnly] = useState(true);
  const [q, setQ] = useState("");
  const [creating, setCreating] = useState(false);
  const [openVariantsFor, setOpenVariantsFor] = useState(null);
  const [variants, setVariants] = useState({});
  const [newVariant, setNewVariant] = useState({
    name: "",
    price: "",
    currency: "TRY",
    min_pax: 1,
    max_pax: 1,
  });
  const [newProduct, setNewProduct] = useState({
    type: "tour",
    title: "",
    description: "",
    location_city: "",
    location_country: "TR",
  });

  const admin = isAdmin();

  async function load() {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (type) params.set("type", type);
      if (q) params.set("q", q);
  const loadVariants = async (productId) => {
    try {
      const res = await api.get(`/agency/catalog/products/${productId}/variants`);
      setVariants((prev) => ({
        ...prev,
        [productId]: res.data.items || [],
      }));
    } catch (err) {
      toast.error(apiErrorMessage(err));
    }
  };


      if (activeOnly) params.set("active", "true");
      const resp = await api.get(`/agency/catalog/products?${params.toString()}`);
      setItems(resp.data?.items || []);
    } catch (err) {
      toast.error(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleCreate(e) {
    e.preventDefault();
    setCreating(true);
    try {
      const body = {
        type: newProduct.type,
        title: newProduct.title,
        description: newProduct.description,
        location: {
          city: newProduct.location_city || undefined,
          country: newProduct.location_country || undefined,
        },
        base_currency: "TRY",
        images: [],
      };
      await api.post("/agency/catalog/products", body);
      toast.success("Ürün oluşturuldu.");
      setNewProduct({
        type: "tour",
        title: "",
        description: "",
        location_city: "",
        location_country: "TR",
      });
      await load();
    } catch (err) {
      toast.error(apiErrorMessage(err));
    } finally {
      setCreating(false);
    }
  }

  async function toggleActive(product) {
    try {
      await api.post(`/agency/catalog/products/${product.id}/toggle-active`, {
        active: !product.active,
      });
      toast.success("Ürün durumu güncellendi.");
      await load();
    } catch (err) {
      toast.error(apiErrorMessage(err));
    }
  }

  return (
    <div className="space-y-4 p-4">
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
        <div className="space-y-2">
          <h1 className="text-xl font-semibold">Katalog Ürünleri</h1>
          <p className="text-sm text-muted-foreground">
            Agentis benzeri ürün/variant kataloğu. Bu modül mevcut otel rezervasyon akışından bağımsız çalışır.
          </p>
        </div>
        {admin && (
          <form
            onSubmit={handleCreate}
            className="border rounded-lg p-3 flex flex-col sm:flex-row gap-2 items-center"
          >
            <Select
              value={newProduct.type}
              onValueChange={(v) => setNewProduct((p) => ({ ...p, type: v }))}
            >
              <SelectTrigger className="w-[120px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {PRODUCT_TYPES.filter((t) => t.value).map((t) => (
                  <SelectItem key={t.value} value={t.value}>
                    {t.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Input
              placeholder="Başlık"
              value={newProduct.title}
              onChange={(e) => setNewProduct((p) => ({ ...p, title: e.target.value }))}
              className="w-[200px]"
              data-testid="catalog-product-title-input"
            />
            <Input
              placeholder="Şehir"
              value={newProduct.location_city}
              onChange={(e) => setNewProduct((p) => ({ ...p, location_city: e.target.value }))}
              className="w-[140px]"
            />
            <Button
              type="submit"
              size="sm"
              disabled={creating}
              data-testid="btn-catalog-create-product"
            >
              {creating ? "Kaydediliyor..." : "Ürün Oluştur"}
            </Button>
          </form>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2">
          <Label htmlFor="catalog-type">Tür</Label>
          <Select
            value={type}
            onValueChange={(v) => setType(v)}
            data-testid="catalog-products-filter-type"
          >
            <SelectTrigger id="catalog-type" className="w-[160px]">
              <SelectValue placeholder="Tümü" />
            </SelectTrigger>
            <SelectContent>
              {PRODUCT_TYPES.map((t) => (
                <SelectItem key={t.value || "all"} value={t.value}>
                  {t.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="flex items-center gap-2">
          <Label htmlFor="catalog-q">Ara</Label>
          <Input
            id="catalog-q"
            placeholder="Başlık / açıklama"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            className="w-[200px]"
          />
        </div>
        <div className="flex items-center gap-2">
          <Switch
            id="catalog-active"
            checked={activeOnly}
            onCheckedChange={setActiveOnly}
          />
          <Label htmlFor="catalog-active">Sadece aktifler</Label>
        </div>
        <Button size="sm" variant="outline" onClick={load} disabled={loading}>
          Filtrele
        </Button>
      </div>

      <div className="grid gap-3">
        {loading && <div className="text-sm text-muted-foreground">Yükleniyor...</div>}
        {!loading && items.length === 0 && (
          <div className="text-sm text-muted-foreground">Henüz hiç katalog ürünü yok.</div>
        )}
        {!loading &&
          items.map((p) => (
            <Card
              key={p.id}
              className="p-3 space-y-2"
              data-testid="catalog-product-row"
            >
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                <div className="space-y-1 text-sm">
                  <div className="font-medium">
                    {p.title}{" "}
                    <span className="text-xs text-muted-foreground">[{p.type}]</span>
                  </div>
                  {p.location?.city && (
                    <div className="text-xs text-muted-foreground">
                      {p.location.city} {p.location.country ? `(${p.location.country})` : ""}
                    </div>
                  )}
                </div>
                <div className="flex flex-wrap gap-2 items-center">
                  <span className="text-xs px-2 py-1 rounded-full border bg-muted">
                    {p.active ? "Aktif" : "Pasif"}
                  </span>
                  {admin && (
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      onClick={() => toggleActive(p)}
                    >
                      {p.active ? "Pasife Al" : "Aktife Al"}
                    </Button>
                  )}
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    data-testid="btn-catalog-open-variants"
                    onClick={async () => {
                      if (openVariantsFor === p.id) {
                        setOpenVariantsFor(null);
                        return;
                      }
                      setOpenVariantsFor(p.id);
                      await loadVariants(p.id);
                    }}
                  >
                    Variantlar
                  </Button>
                </div>
              </div>

              {openVariantsFor === p.id && (
                <div className="mt-3 rounded-md border p-3 space-y-3 bg-muted/30">
                  {(variants[p.id] || []).map((v) => (
                    <div
                      key={v.id}
                      className="flex items-center justify-between text-sm border-b pb-1"
                      data-testid="catalog-variant-row"
                    >
                      <div>
                        <div className="font-medium">{v.name}</div>
                        <div className="text-xs text-muted-foreground">
                          {v.price} {v.currency} · pax {v.rules?.min_pax}–
                          {v.rules?.max_pax}
                        </div>
                      </div>
                      {admin && (
                        <Button
                          size="xs"
                          variant="outline"
                          onClick={async () => {
                            await api.post(
                              `/agency/catalog/variants/${v.id}/toggle-active`,
                              { active: !v.active }
                            );
                            await loadVariants(p.id);
                          }}
                        >
                          {v.active ? "Pasif Yap" : "Aktif Yap"}
                        </Button>
                      )}
                    </div>
                  ))}

                  {admin && (
                    <div className="pt-2 space-y-2">
                      <Input
                        placeholder="Variant adı"
                        value={newVariant.name}
                        onChange={(e) =>
                          setNewVariant({ ...newVariant, name: e.target.value })
                        }
                      />
                      <div className="flex gap-2">
                        <Input
                          type="number"
                          placeholder="Fiyat"
                          value={newVariant.price}
                          onChange={(e) =>
                            setNewVariant({ ...newVariant, price: e.target.value })
                          }
                        />
                        <Input
                          placeholder="Para birimi"
                          value={newVariant.currency}
                          onChange={(e) =>
                            setNewVariant({ ...newVariant, currency: e.target.value })
                          }
                        />
                      </div>
                      <div className="flex gap-2">
                        <Input
                          type="number"
                          placeholder="Min pax"
                          value={newVariant.min_pax}
                          onChange={(e) =>
                            setNewVariant({ ...newVariant, min_pax: e.target.value })
                          }
                        />
                        <Input
                          type="number"
                          placeholder="Max pax"
                          value={newVariant.max_pax}
                          onChange={(e) =>
                            setNewVariant({ ...newVariant, max_pax: e.target.value })
                          }
                        />
                      </div>

                      <Button
                        size="sm"
                        data-testid="btn-catalog-create-variant"
                        onClick={async () => {
                          try {
                            await api.post(`/agency/catalog/variants`, {
                              product_id: p.id,
                              name: newVariant.name,
                              price: Number(newVariant.price),
                              currency: newVariant.currency,
                              rules: {
                                min_pax: Number(newVariant.min_pax),
                                max_pax: Number(newVariant.max_pax),
                              },
                              active: true,
                            });
                            setNewVariant({
                              name: "",
                              price: "",
                              currency: p.base_currency || "TRY",
                              min_pax: 1,
                              max_pax: 1,
                            });
                            await loadVariants(p.id);
                            toast.success("Variant oluşturuldu.");
                          } catch (err) {
                            toast.error(apiErrorMessage(err));
                          }
                        }}
                      >
                        Variant Ekle
                      </Button>
                    </div>
                  )}
                </div>
              )}
            </Card>
          ))}
      </div>
    </div>
  );
}
