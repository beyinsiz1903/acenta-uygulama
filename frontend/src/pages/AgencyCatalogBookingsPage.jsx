import React, { useEffect, useState } from "react";
import { api, apiErrorMessage } from "../lib/api";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { Card } from "../components/ui/card";
import { toast } from "react-hot-toast";
import { Link, useNavigate } from "react-router-dom";

const STATUS_OPTIONS = [
  { value: "all", label: "Tümü" },
  { value: "new", label: "Yeni" },
  { value: "approved", label: "Onaylandı" },
  { value: "rejected", label: "Reddedildi" },
  { value: "cancelled", label: "İptal" },
];

export default function AgencyCatalogBookingsPage() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState("all");
  const [type, setType] = useState("");
  const [creating, setCreating] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const [products, setProducts] = useState([]);
  const [variants, setVariants] = useState([]);
  const [form, setForm] = useState({
    product_id: "",
    variant_id: "",
    full_name: "",
    phone: "",
    email: "",
    start: "",
    end: "",
    pax: 1,
    commission_rate: 0.1,
  });

  const navigate = useNavigate();

  async function load() {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (status && status !== "all") params.set("status", status);
      if (type) params.set("product_type", type);
      const resp = await api.get(`/agency/catalog/bookings?${params.toString()}`);
      setItems(resp.data?.items || []);
    } catch (err) {
      toast.error(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  async function loadProducts() {
    try {
      const resp = await api.get("/agency/catalog/products?active=true");
      setProducts(resp.data?.items || []);
    } catch (err) {
      toast.error(apiErrorMessage(err));
    }
  }

  async function loadVariants(productId) {
    if (!productId) {
      setVariants([]);
      return;
    }
    try {
      const resp = await api.get(`/agency/catalog/products/${productId}/variants`);
      setVariants(resp.data?.items || []);
    } catch (err) {
      toast.error(apiErrorMessage(err));
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function openCreate() {
    setCreateOpen(true);
    await loadProducts();
  }

  async function handleCreate(e) {
    e.preventDefault();
    setCreating(true);
    try {
      const body = {
        product_id: form.product_id,
        variant_id: form.variant_id || null,
        guest: {
          full_name: form.full_name,
          phone: form.phone,
          email: form.email,
        },
        dates: { start: form.start, end: form.end || null },
        pax: Number(form.pax) || 1,
        commission_rate: Number(form.commission_rate) || 0.1,
      };
      const resp = await api.post("/agency/catalog/bookings", body);
      toast.success("Rezervasyon talebi oluşturuldu.");
      setCreateOpen(false);
      setForm({
        product_id: "",
        variant_id: "",
        full_name: "",
        phone: "",
        email: "",
        start: "",
        end: "",
        pax: 1,
        commission_rate: 0.1,
      });
      await load();
      if (resp.data?.id) {
        navigate(`/app/agency/catalog/bookings/${resp.data.id}`);
      }
    } catch (err) {
      toast.error(apiErrorMessage(err));
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="space-y-4 p-4">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">Katalog Rezervasyonları</h1>
          <p className="text-sm text-muted-foreground">
            Agentis-benzeri yeni rezervasyon omurgası. Mevcut otel rezervasyon listesinden bağımsızdır.
          </p>
        </div>
        <Button
          type="button"
          size="sm"
          onClick={openCreate}
          data-testid="btn-catalog-create-booking"
        >
          Yeni Rezervasyon
        </Button>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">Durum</span>
          <Select value={status} onValueChange={setStatus}>
            <SelectTrigger className="w-[160px]">
              <SelectValue placeholder="Tümü" />
            </SelectTrigger>
            <SelectContent>
              {STATUS_OPTIONS.map((s) => (
                <SelectItem key={s.value || "all"} value={s.value}>
                  {s.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <Button size="sm" variant="outline" onClick={load} disabled={loading}>
          Filtrele
        </Button>
      </div>

      <div className="grid gap-3">
        {loading && <div className="text-sm text-muted-foreground">Yükleniyor...</div>}
        {!loading && items.length === 0 && (
          <div className="text-sm text-muted-foreground">Henüz hiç katalog rezervasyonu yok.</div>
        )}
        {!loading &&
          items.map((b) => (
            <Card
              key={b.id}
              className="p-3 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2"
              data-testid="catalog-booking-row"
            >
              <div className="space-y-1 text-sm">
                <div className="font-medium">
                  {b.guest?.full_name || "Misafir"}
                </div>
                <div className="text-xs text-muted-foreground">
                  {b.product_type} • {b.dates?.start} • {b.pax} kişi
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span
                  className="text-xs px-2 py-1 rounded-full border bg-muted"
                  data-testid="catalog-booking-status-badge"
                >
                  {b.status}
                </span>
                <Button
                  asChild
                  size="sm"
                  variant="outline"
                >
                  <Link to={`/app/agency/catalog/bookings/${b.id}`}>Detay</Link>
                </Button>
              </div>
            </Card>
          ))}
      </div>

      {createOpen && (
        <div
          className="fixed inset-0 bg-black/40 flex items-center justify-center z-50"
          data-testid="catalog-booking-create-modal"
        >
          <div className="bg-white rounded-lg shadow-lg w-full max-w-lg p-4 space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-semibold">Yeni Katalog Rezervasyonu</h2>
              <Button
                type="button"
                size="sm"
                variant="ghost"
                onClick={() => setCreateOpen(false)}
              >
                Kapat
              </Button>
            </div>
            <form className="space-y-3" onSubmit={handleCreate}>
              <div className="space-y-1 text-sm">
                <label className="font-medium">Ürün</label>
                <Select
                  value={form.product_id}
                  onValueChange={async (v) => {
                    setForm((p) => ({ ...p, product_id: v, variant_id: "" }));
                    await loadVariants(v);
                  }}
                >
                  <SelectTrigger data-testid="catalog-booking-select-product">
                    <SelectValue placeholder="Ürün seçin" />
                  </SelectTrigger>
                  <SelectContent>
                    {products.map((p) => (
                      <SelectItem
                        key={p.id}
                        value={p.id}
                        data-testid="catalog-booking-product-item"
                      >
                        {p.title} [{p.type}]
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-1 text-sm">
                <label className="font-medium">Variant</label>
                <Select
                  value={form.variant_id}
                  onValueChange={(v) => setForm((p) => ({ ...p, variant_id: v }))}
                >
                  <SelectTrigger data-testid="catalog-booking-select-variant">
                    <SelectValue placeholder="Variant seçin (opsiyonel)" />
                  </SelectTrigger>
                  <SelectContent>
                    {variants.map((v) => (
                      <SelectItem key={v.id} value={v.id}>
                        {v.name} - {v.price} {v.currency}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-sm">
                <div className="space-y-1">
                  <label className="font-medium">Misafir Adı</label>
                  <Input
                    value={form.full_name}
                    onChange={(e) => setForm((p) => ({ ...p, full_name: e.target.value }))}
                    required
                  />
                </div>
                <div className="space-y-1">
                  <label className="font-medium">Telefon</label>
                  <Input
                    value={form.phone}
                    onChange={(e) => setForm((p) => ({ ...p, phone: e.target.value }))}
                  />
                </div>
                <div className="space-y-1">
                  <label className="font-medium">E-posta</label>
                  <Input
                    type="email"
                    value={form.email}
                    onChange={(e) => setForm((p) => ({ ...p, email: e.target.value }))}
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-sm">
                <div className="space-y-1">
                  <label className="font-medium">Başlangıç Tarihi</label>
                  <Input
                    type="date"
                    value={form.start}
                    onChange={(e) => setForm((p) => ({ ...p, start: e.target.value }))}
                    required
                  />
                </div>
                <div className="space-y-1">
                  <label className="font-medium">Bitiş Tarihi</label>
                  <Input
                    type="date"
                    value={form.end}
                    onChange={(e) => setForm((p) => ({ ...p, end: e.target.value }))}
                  />
                </div>
                <div className="space-y-1">
                  <label className="font-medium">Kişi Sayısı</label>
                  <Input
                    type="number"
                    min={1}
                    value={form.pax}
                    onChange={(e) => setForm((p) => ({ ...p, pax: e.target.value }))}
                  />
                </div>
              </div>

              <div className="space-y-1 text-sm">
                <label className="font-medium">Komisyon Oranı</label>
                <Input
                  type="number"
                  step="0.01"
                  min="0"
                  max="0.5"
                  value={form.commission_rate}
                  onChange={(e) => setForm((p) => ({ ...p, commission_rate: e.target.value }))}
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setCreateOpen(false)}
                >
                  Vazgeç
                </Button>
                <Button type="submit" size="sm" disabled={creating}>
                  {creating ? "Kaydediliyor..." : "Oluştur"}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
