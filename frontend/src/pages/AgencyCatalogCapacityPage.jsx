import React, { useEffect, useState } from "react";
import { api, apiErrorMessage } from "../lib/api";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { Card } from "../components/ui/card";
import { toast } from "react-hot-toast";

function startOfTodayISO() {
  return new Date().toISOString().slice(0, 10);
}

function addDaysISO(iso, days) {
  const d = new Date(iso + "T00:00:00Z");
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

export default function AgencyCatalogCapacityPage() {
  const [products, setProducts] = useState([]);
  const [variants, setVariants] = useState([]);
  const [productId, setProductId] = useState("");
  const [variantId, setVariantId] = useState("");
  const [range, setRange] = useState(() => {
    const start = startOfTodayISO();
    const end = addDaysISO(start, 30);
    return { start, end };
  });
  const [loading, setLoading] = useState(false);
  const [dashboard, setDashboard] = useState(null);

  async function loadProducts() {
    try {
      const resp = await api.get("/agency/catalog/products?active=true");
      setProducts(resp.data?.items || []);
    } catch (err) {
      toast.error(apiErrorMessage(err));
    }
  }

  async function loadVariantsForProduct(pid) {
    if (!pid) {
      setVariants([]);
      return;
    }
    try {
      const resp = await api.get(`/agency/catalog/products/${pid}/variants`);
      setVariants(resp.data?.items || []);
    } catch (err) {
      toast.error(apiErrorMessage(err));
    }
  }

  useEffect(() => {
    loadProducts();
  }, []);

  async function handleShow(e) {
    e.preventDefault();
    if (!productId || !variantId || !range.start || !range.end) {
      toast.error("Ürün, variant ve tarih aralığı seçin.");
      return;
    }
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.set("variant_id", variantId);
      params.set("start", range.start);
      params.set("end", range.end);
      const resp = await api.get(`/agency/catalog/capacity-dashboard?${params.toString()}`);
      setDashboard(resp.data || null);
    } catch (err) {
      setDashboard(null);
      toast.error(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  function handleProductChange(v) {
    setProductId(v);
    setVariantId("");
    setDashboard(null);
    loadVariantsForProduct(v);
  }

  const days = dashboard?.days || [];

  // build calendar weeks (7 columns)
  const dayMap = new Map();
  days.forEach((d) => {
    dayMap.set(d.day, d);
  });

  const calendarDays = [];
  if (dashboard?.range?.start && dashboard?.range?.end) {
    const { start, end } = dashboard.range;
    let cur = new Date(start + "T00:00:00Z");
    const endDate = new Date(end + "T00:00:00Z");
    while (cur <= endDate) {
      const iso = cur.toISOString().slice(0, 10);
      calendarDays.push(iso);
      cur.setUTCDate(cur.getUTCDate() + 1);
    }
  }

  const weeks = [];
  let currentWeek = [];
  calendarDays.forEach((iso) => {
    currentWeek.push(iso);
    if (currentWeek.length === 7) {
      weeks.push(currentWeek);
      currentWeek = [];
    }
  });
  if (currentWeek.length) {
    weeks.push(currentWeek);
  }

  return (
    <div className="space-y-4 p-4">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">Katalog Kapasite Takvimi</h1>
          <p className="text-sm text-muted-foreground">
            Variant bazlı kapasite kullanımını tarih aralığında özetleyen basit takvim görünümü.
          </p>
        </div>
      </div>

      <form className="grid gap-3 md:grid-cols-4 items-end" onSubmit={handleShow}>
        <div className="space-y-1 text-sm">
          <label className="font-medium">Ürün</label>
          <Select value={productId} onValueChange={handleProductChange}>
            <SelectTrigger>
              <SelectValue placeholder="Ürün seçin" />
            </SelectTrigger>
            <SelectContent>
              {products.map((p) => (
                <SelectItem key={p.id} value={p.id}>
                  {p.title} [{p.type}]
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-1 text-sm">
          <label className="font-medium">Variant</label>
          <Select value={variantId} onValueChange={setVariantId}>
            <SelectTrigger>
              <SelectValue placeholder="Variant seçin" />
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

        <div className="space-y-1 text-sm">
          <label className="font-medium">Başlangıç</label>
          <Input
            type="date"
            value={range.start}
            onChange={(e) => setRange((r) => ({ ...r, start: e.target.value }))}
          />
        </div>
        <div className="space-y-1 text-sm">
          <label className="font-medium">Bitiş</label>
          <Input
            type="date"
            value={range.end}
            onChange={(e) => setRange((r) => ({ ...r, end: e.target.value }))}
          />
        </div>

        <div className="flex items-center gap-2">
          <Button type="submit" size="sm" disabled={loading}>
            Göster
          </Button>
        </div>
      </form>

      {dashboard && (
        <div className="space-y-3">
          <div className="grid gap-3 md:grid-cols-3 text-sm">
            <Card className="p-3">
              <div className="text-xs text-muted-foreground">Toplam Gün</div>
              <div className="text-lg font-semibold">{dashboard.summary?.total_days ?? "-"}</div>
            </Card>
            <Card className="p-3">
              <div className="text-xs text-muted-foreground">Tam Dolu Gün</div>
              <div className="text-lg font-semibold">{dashboard.summary?.full_days ?? "-"}</div>
            </Card>
            <Card className="p-3">
              <div className="text-xs text-muted-foreground">Ortalama Kullanım</div>
              <div className="text-lg font-semibold">{dashboard.summary?.avg_used ?? "-"}</div>
            </Card>
          </div>

          <div className="space-y-2">
            <div className="text-xs text-muted-foreground">
              Mod: {dashboard.mode} • Günlük kapasite: {dashboard.max_per_day ?? "∞"}
            </div>
            <div className="border rounded-md overflow-hidden">
              {weeks.length === 0 && (
                <div className="p-3 text-xs text-muted-foreground">Seçilen aralıkta gün yok.</div>
              )}
              {weeks.map((week, wi) => (
                <div key={wi} className="grid grid-cols-7 border-b last:border-b-0">
                  {week.map((iso) => {
                    const d = dayMap.get(iso) || {
                      day: iso,
                      used: 0,
                      max: dashboard.max_per_day,
                      remaining: dashboard.max_per_day,
                      can_book: true,
                      mode: dashboard.mode,
                    };
                    const isFull = d.max != null && d.used >= d.max;
                    const bg = isFull ? "bg-red-50" : d.used > 0 ? "bg-yellow-50" : "bg-green-50";
                    return (
                      <div
                        key={iso}
                        className={`border-r last:border-r-0 p-2 min-h-[60px] text-xs ${bg}`}
                        data-testid={`capacity-cell-${iso}`}
                      >
                        <div className="font-semibold text-[11px] mb-1">{iso}</div>
                        <div
                          className="text-[11px]"
                          data-testid={`capacity-used-${iso}`}
                        >
                          Kullanım: {d.used}
                        </div>
                        <div
                          className="text-[11px]"
                          data-testid={`capacity-remaining-${iso}`}
                        >
                          Kalan: {d.remaining ?? "∞"}
                        </div>
                        <div
                          className="text-[11px] mt-1"
                          data-testid={`capacity-status-${iso}`}
                        >
                          {d.max != null && d.used >= d.max ? "Dolu" : "Uygun"}
                        </div>
                      </div>
                    );
                  })}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
