import React, { useEffect, useMemo, useState } from "react";
import { api, apiErrorMessage } from "../lib/api";
import { useToast } from "../hooks/use-toast";

import { Input } from "../components/ui/input";
import { Badge } from "../components/ui/badge";
import { Card, CardContent } from "../components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import { Button } from "../components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/table";
import { Label } from "../components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "../components/ui/dialog";

function effectiveCatalog(catalog) {
  const c = catalog || {};
  const commission = c.commission || {};
  const pricing = c.pricing_policy || {};

  return {
    hasCatalog: !!catalog,
    saleEnabled: Boolean(c.sale_enabled),
    visibility: c.visibility || "private",
    commissionPercent:
      typeof commission.value === "number" && !Number.isNaN(commission.value)
        ? commission.value
        : 0,
    minNights:
      typeof c.min_nights === "number" && c.min_nights > 0 ? c.min_nights : 1,
    markupPercent:
      typeof pricing.markup_percent === "number" && !Number.isNaN(pricing.markup_percent)
        ? pricing.markup_percent
        : 0,
  };
}

function buildPayloadFromEffective(eff) {
  return {
    sale_enabled: Boolean(eff.saleEnabled),
    visibility: eff.visibility || "private",
    commission: {
      type: "percent",
      value: Number.isFinite(eff.commissionPercent)
        ? eff.commissionPercent
        : 0,
      currency: "TRY",
    },
    min_nights: eff.minNights || 1,
    pricing_policy: {
      mode: "pms_plus",
      markup_percent: Number.isFinite(eff.markupPercent)
        ? eff.markupPercent
        : 0,
      markup_absolute: null,
      currency: "TRY",
    },
    booking_policy: null,
    public_slug: null,
    public_hotel_slug: null,
  };
}

function catalogStatusBadge(eff) {
  if (!eff.hasCatalog) {
    return { label: "Ayarlanmadı", variant: "outline" };
  }
  if (eff.saleEnabled) {
    return { label: "Satış Açık", variant: "default" };
  }
  return { label: "Satış Kapalı", variant: "secondary" };
}

function shortId(id) {
  if (!id) return "-";
  const s = String(id);
  if (s.length <= 10) return s;
  return `${s.slice(0, 6)}…${s.slice(-4)}`;
}

export default function AgencyCatalogHotelsPage() {
  const { toast } = useToast();

  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [search, setSearch] = useState("");
  const [saleFilter, setSaleFilter] = useState("all"); // all|open|closed
  const [visibilityFilter, setVisibilityFilter] = useState("all"); // all|public|private
  const [publicOnly, setPublicOnly] = useState(false);

  // Edit sheet state
  const [editOpen, setEditOpen] = useState(false);
  const [editHotel, setEditHotel] = useState(null);
  const [formSaleEnabled, setFormSaleEnabled] = useState(true);
  const [formVisibility, setFormVisibility] = useState("private");
  const [formCommissionPercent, setFormCommissionPercent] = useState(0);
  const [formMinNights, setFormMinNights] = useState(1);
  const [formMarkupPercent, setFormMarkupPercent] = useState(0);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadItems();
  }, []);

  async function loadItems() {
    setLoading(true);
    setError("");
    try {
      const resp = await api.get("/agency/catalog/hotels");
      const list = resp.data?.items || resp.data || [];
      setItems(Array.isArray(list) ? list : []);
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  function openEdit(item) {
    const eff = effectiveCatalog(item.catalog);
    setEditHotel(item);
    setFormSaleEnabled(eff.saleEnabled);
    setFormVisibility(eff.visibility);
    setFormCommissionPercent(eff.commissionPercent);
    setFormMinNights(eff.minNights);
    setFormMarkupPercent(eff.markupPercent);
    setEditOpen(true);
  }

  async function saveEdit() {
    if (!editHotel) return;

    // Basit frontend validasyonları
    const c = Number(formCommissionPercent) || 0;
    const m = Number(formMarkupPercent) || 0;
    const mn = Number(formMinNights) || 1;

    if (c < 0 || c > 99) {
      toast({
        title: "Geçersiz komisyon",
        description: "Komisyon yüzdesi 0 ile 99 arasında olmalıdır.",
        variant: "destructive",
      });
      return;
    }
    if (mn < 1 || mn > 30) {
      toast({
        title: "Geçersiz minimum gece",
        description: "Min. gece 1 ile 30 arasında olmalıdır.",
        variant: "destructive",
      });
      return;
    }

    let visibility = formVisibility || "private";
    let saleEnabled = !!formSaleEnabled;
    if (visibility === "public" && !saleEnabled) {
      // Backend de buna kızıyor; UI’da erken yakalayalım
      toast({
        title: "Geçersiz ayar",
        description: "Public görünür bir otel için satışın açık olması gerekir.",
        variant: "destructive",
      });
      return;
    }

    const eff = {
      hasCatalog: !!editHotel.catalog,
      saleEnabled,
      visibility,
      commissionPercent: c,
      minNights: mn,
      markupPercent: m,
    };

    const payload = buildPayloadFromEffective(eff);

    setSaving(true);
    try {
      await api.put(`/agency/catalog/hotels/${encodeURIComponent(editHotel.hotel_id)}`, payload);
      toast({ title: "Katalog kaydedildi", description: "Otel satış ayarları güncellendi." });
      setEditOpen(false);
      setEditHotel(null);
      await loadItems();
    } catch (err) {
      toast({ title: "Kaydedilemedi", description: apiErrorMessage(err), variant: "destructive" });
    } finally {
      setSaving(false);
    }
  }

  async function toggleSale(item, nextSaleEnabled) {
    const eff = effectiveCatalog(item.catalog);
    const saleEnabled = !!nextSaleEnabled;
    let visibility = eff.visibility || "private";

    // visibility=public & sale_enabled=false yasağını önlemek için
    if (!saleEnabled && visibility === "public") {
      visibility = "private";
    }

    const payload = buildPayloadFromEffective({
      hasCatalog: eff.hasCatalog,
      saleEnabled,
      visibility,
      commissionPercent: eff.commissionPercent,
      minNights: eff.minNights,
      markupPercent: eff.markupPercent,
    });

    try {
      await api.put(`/agency/catalog/hotels/${encodeURIComponent(item.hotel_id)}`, payload);
      toast({ title: "Satış durumu güncellendi" });
      await loadItems();
    } catch (err) {
      toast({ title: "Satış durumu güncellenemedi", description: apiErrorMessage(err), variant: "destructive" });
    }
  }

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();

    return items.filter((item) => {
      const eff = effectiveCatalog(item.catalog);
      const name = (item.hotel_name || "").toLowerCase();
      const loc = (item.location || "").toLowerCase();

      if (q && !name.includes(q) && !loc.includes(q)) return false;

      if (saleFilter === "open" && !eff.saleEnabled) return false;
      if (saleFilter === "closed" && eff.saleEnabled) return false;

      if (visibilityFilter === "public" && eff.visibility !== "public") return false;
      if (visibilityFilter === "private" && eff.visibility !== "private") return false;

      if (publicOnly && !(eff.saleEnabled && eff.visibility === "public")) {
        return false;
      }

      return true;
    });
  }, [items, search, saleFilter, visibilityFilter, publicOnly]);

  const anyCatalog = useMemo(() => items.some((i) => i.catalog), [items]);

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Ürünler • Oteller</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Acenta portföyünüzdeki oteller için satış ve görünürlük ayarlarını yönetin.
          </p>
        </div>
        <div className="rounded-2xl border bg-card shadow-sm p-10 text-sm text-muted-foreground flex items-center justify-center">
          Otel kataloğu yükleniyor…
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Ürünler • Oteller</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Acenta portföyünüzdeki oteller için satış ve görünürlük ayarlarını yönetin.
          </p>
        </div>
        <div className="rounded-2xl border border-destructive/40 bg-destructive/5 p-8 flex flex-col gap-3">
          <div className="font-semibold text-destructive">Otel kataloğu yüklenemedi</div>
          <div className="text-sm text-muted-foreground">{error}</div>
          <div>
            <Button variant="outline" size="sm" onClick={loadItems}>
              Tekrar Dene
            </Button>
          </div>
        </div>
      </div>
    );
  }

  if (!loading && items.length === 0) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Ürünler • Oteller</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Portföyünüzde size tanımlı otel bulunmuyor.
          </p>
        </div>
        <div className="rounded-2xl border bg-card shadow-sm p-10 text-sm text-muted-foreground">
          Merkez ekip size otel linklediğinde, bu ekranda satış ayarlarını yönetebileceksiniz.
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Ürünler • Oteller</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Portföyünüzdeki oteller için satışa aç/kapat, public görünürlük, komisyon ve fiyatlandırma
            kurallarını yönetin.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={loadItems}>
            Yenile
          </Button>
        </div>
      </div>

      <Card className="rounded-2xl border bg-card shadow-sm p-4 mb-2">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex-1 min-w-[220px]">
            <Input
              placeholder="🔍 Otel ara... (ad / lokasyon)"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <Select value={saleFilter} onValueChange={setSaleFilter}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Satış durumu" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Tüm Satış Durumları</SelectItem>
                <SelectItem value="open">Satış Açık</SelectItem>
                <SelectItem value="closed">Satış Kapalı / Ayarsız</SelectItem>
              </SelectContent>
            </Select>

            <Select value={visibilityFilter} onValueChange={setVisibilityFilter}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Görünürlük" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Tüm Görünümler</SelectItem>
                <SelectItem value="public">Public</SelectItem>
                <SelectItem value="private">Private</SelectItem>
              </SelectContent>
            </Select>

            <Button
              type="button"
              variant={publicOnly ? "default" : "outline"}
              size="sm"
              onClick={() => setPublicOnly((v) => !v)}
            >
              Sadece Public
            </Button>
          </div>
        </div>
      </Card>

      <Card className="rounded-2xl border bg-card shadow-sm">
        <CardContent className="p-4">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Otel</TableHead>
                <TableHead>Link</TableHead>
                <TableHead>Katalog</TableHead>
                <TableHead>Görünürlük</TableHead>
                <TableHead>Komisyon %</TableHead>
                <TableHead>Min Gece</TableHead>
                <TableHead>Markup %</TableHead>
                <TableHead>Satış</TableHead>
                <TableHead className="text-right">İşlemler</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.map((item) => {
                const eff = effectiveCatalog(item.catalog);
                const status = catalogStatusBadge(eff);

                return (
                  <TableRow key={item.hotel_id}>
                    <TableCell>
                      <div className="text-sm font-medium">{item.hotel_name || "-"}</div>
                      <div className="text-xs text-muted-foreground">{item.location || "-"}</div>
                    </TableCell>
                    <TableCell>
                      {item.link_active ? (
                        <Badge className="bg-emerald-500/10 text-emerald-700 border-emerald-500/20">
                          Link Aktif
                        </Badge>
                      ) : (
                        <Badge variant="outline">Pasif</Badge>
                      )}
                    </TableCell>
                    <TableCell>
                      <Badge variant={status.variant}>{status.label}</Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">{eff.visibility === "public" ? "Public" : "Private"}</Badge>
                    </TableCell>
                    <TableCell className="text-xs">{eff.commissionPercent.toFixed(1)}</TableCell>
                    <TableCell className="text-xs">{eff.minNights}</TableCell>
                    <TableCell className="text-xs">{eff.markupPercent.toFixed(1)}</TableCell>
                    <TableCell>
                      <input
                        type="checkbox"
                        className="h-4 w-4"
                        checked={eff.saleEnabled}
                        onChange={(e) => toggleSale(item, e.target.checked)}
                      />
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => openEdit(item)}
                      >
                        Düzenle
                      </Button>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>

          {filtered.length === 0 ? (
            <div className="text-sm text-muted-foreground mt-4">
              Filtrelere uygun otel bulunamadı.
            </div>
          ) : null}
        </CardContent>
      </Card>

      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent className="max-w-xl">
          <DialogHeader>
            <DialogTitle>Otel Satış Ayarları</DialogTitle>
            <DialogDescription>
              Bu otel için satışa aç/kapat, public görünürlük ve fiyatlandırma kurallarını güncelleyin.
            </DialogDescription>
          </DialogHeader>

          {editHotel ? (
            <div className="space-y-4 mt-2">
              <div className="space-y-1">
                <div className="text-sm font-medium">{editHotel.hotel_name}</div>
                <div className="text-xs text-muted-foreground">
                  ID: <span className="font-mono">{shortId(editHotel.hotel_id)}</span>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      className="h-4 w-4"
                      checked={formSaleEnabled}
                      onChange={(e) => setFormSaleEnabled(e.target.checked)}
                    />
                    Satışa Açık
                  </Label>
                  <div className="text-xs text-muted-foreground">
                    Oteli public görünür yapsanız bile satış kapalıysa public sayfada gösterilmeyecek.
                  </div>
                </div>

                <div className="space-y-2">
                  <Label>Görünürlük</Label>
                  <Select
                    value={formVisibility}
                    onValueChange={setFormVisibility}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="private">Private (sadece acenta içi)</SelectItem>
                      <SelectItem value="public">Public (public booking için)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label>Komisyon %</Label>
                  <Input
                    type="number"
                    step="0.1"
                    min={0}
                    max={99}
                    value={formCommissionPercent}
                    onChange={(e) => setFormCommissionPercent(e.target.value)}
                  />
                  <div className="text-xs text-muted-foreground">0–99 arası önerilir.</div>
                </div>

                <div className="space-y-2">
                  <Label>Minimum Gece</Label>
                  <Input
                    type="number"
                    min={1}
                    max={30}
                    value={formMinNights}
                    onChange={(e) => setFormMinNights(e.target.value)}
                  />
                </div>

                <div className="space-y-2">
                  <Label>Fiyat Politikası</Label>
                  <div className="text-xs text-muted-foreground">
                    MVP: PMS fiyatı + markup % uygulanır.
                  </div>
                </div>

                <div className="space-y-2">
                  <Label>Markup % (PMS+)</Label>
                  <Input
                    type="number"
                    step="0.1"
                    min={0}
                    value={formMarkupPercent}
                    onChange={(e) => setFormMarkupPercent(e.target.value)}
                  />
                </div>
              </div>
            </div>
          ) : null}

          <DialogFooter className="mt-4">
            <Button
              type="button"
              variant="outline"
              onClick={() => setEditOpen(false)}
            >
              İptal
            </Button>
            <Button type="button" onClick={saveEdit} disabled={saving}>
              {saving ? "Kaydediliyor…" : "Kaydet"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
