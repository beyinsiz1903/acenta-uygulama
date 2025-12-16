import React, { useCallback, useEffect, useMemo, useState } from "react";
import { CalendarDays, Save, RefreshCw } from "lucide-react";
import { addDays, format, startOfToday } from "date-fns";

import { api, apiErrorMessage } from "../lib/api";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";

export default function InventoryPage() {
  const [products, setProducts] = useState([]);
  const [productId, setProductId] = useState("");
  const [rangeDays, setRangeDays] = useState(14);
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const start = useMemo(() => format(startOfToday(), "yyyy-MM-dd"), []);
  const end = useMemo(
    () => format(addDays(startOfToday(), Number(rangeDays || 14)), "yyyy-MM-dd"),
    [rangeDays]
  );

  const loadProducts = useCallback(async () => {
    const resp = await api.get("/products");
    setProducts(resp.data || []);
    setProductId((prev) => prev || (resp.data || [])[0]?.id || "");
  }, []);

  const loadInventory = useCallback(async (pid) => {
    if (!pid) return;
    setLoading(true);
    setError("");
    try {
      const resp = await api.get("/inventory", {
        params: { product_id: pid, start, end },
      });
      setRows(resp.data || []);
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setLoading(false);
    }
  }, [start, end]);

  useEffect(() => {
    (async () => {
      try {
        await loadProducts();
      } catch (e) {
        setError(apiErrorMessage(e));
      }
    })();
  }, [loadProducts]);

  useEffect(() => {
    if (productId) loadInventory(productId);
  }, [productId, rangeDays, loadInventory]);

  const grid = useMemo(() => {
    const map = new Map(rows.map((r) => [r.date, r]));
    const days = [];
    for (let i = 0; i < Number(rangeDays || 14); i++) {
      const d = format(addDays(startOfToday(), i), "yyyy-MM-dd");
      const item = map.get(d) || {
        date: d,
        capacity_total: 0,
        capacity_available: 0,
        price: null,
        restrictions: { closed: false },
      };
      days.push(item);
    }
    return days;
  }, [rows, rangeDays]);

  const upsertDay = useCallback(async (day) => {
    try {
      await api.post("/inventory/upsert", {
        product_id: productId,
        date: day.date,
        capacity_total: Number(day.capacity_total || 0),
        capacity_available: Number(day.capacity_available || 0),
        price: day.price === "" || day.price === null ? null : Number(day.price),
        restrictions: { closed: !!day.closed, cta: false, ctd: false },
      });
      await loadInventory(productId);
    } catch (e) {
      alert(apiErrorMessage(e));
    }
  }, [productId, loadInventory]);

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-2xl font-semibold text-slate-900">Müsaitlik & Kontenjan</h2>
        <p className="text-sm text-slate-600">
          Tarih bazında kapasite ve fiyat güncelle.
        </p>
      </div>

      <Card className="rounded-2xl shadow-sm">
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <CalendarDays className="h-4 w-4 text-slate-500" />
            Takvim
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div className="space-y-2">
              <Label>Ürün</Label>
              <Select value={productId} onValueChange={setProductId}>
                <SelectTrigger data-testid="inventory-product">
                  <SelectValue placeholder="Ürün seç" />
                </SelectTrigger>
                <SelectContent>
                  {products.map((p) => (
                    <SelectItem key={p.id} value={p.id}>
                      {p.title} ({p.type})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Gün sayısı</Label>
              <Input
                type="number"
                min={7}
                max={60}
                value={rangeDays}
                onChange={(e) => setRangeDays(e.target.value)}
                data-testid="inventory-range"
              />
            </div>

            <div className="flex items-end gap-2">
              <Button
                variant="outline"
                onClick={() => loadInventory(productId)}
                className="gap-2"
                data-testid="inventory-refresh"
              >
                <RefreshCw className="h-4 w-4" />
                Yenile
              </Button>
              <div className="text-xs text-slate-500">
                Aralık: {start} → {end}
              </div>
            </div>
          </div>

          {error ? (
            <div className="mt-4 rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700" data-testid="inventory-error">
              {error}
            </div>
          ) : null}

          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-sm" data-testid="inventory-table">
              <thead>
                <tr className="text-left text-slate-500">
                  <th className="py-2">Tarih</th>
                  <th className="py-2">Kapasite</th>
                  <th className="py-2">Müsait</th>
                  <th className="py-2">Fiyat</th>
                  <th className="py-2">Kapalı</th>
                  <th className="py-2 text-right">Kaydet</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan={6} className="py-6 text-slate-500">Yükleniyor...</td>
                  </tr>
                ) : (
                  grid.map((d) => (
                    <InventoryRow key={d.date} day={d} onSave={upsertDay} />
                  ))
                )}
              </tbody>
            </table>
          </div>

          <div className="mt-3 text-xs text-slate-500">
            İpucu: Fiyat boş ise sistem rate plan üzerinden fiyat hesaplar.
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function InventoryRow({ day, onSave }) {
  const [capacityTotal, setCapacityTotal] = useState(day.capacity_total || 0);
  const [capacityAvail, setCapacityAvail] = useState(day.capacity_available || 0);
  const [price, setPrice] = useState(day.price ?? "");
  const [closed, setClosed] = useState(!!day?.restrictions?.closed);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setCapacityTotal(day.capacity_total || 0);
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setCapacityAvail(day.capacity_available || 0);
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setPrice(day.price ?? "");
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setClosed(!!day?.restrictions?.closed);
  }, [day]);

  return (
    <tr className="border-t">
      <td className="py-3 font-medium text-slate-900">{day.date}</td>
      <td className="py-3">
        <Input
          className="w-24"
          type="number"
          value={capacityTotal}
          onChange={(e) => setCapacityTotal(e.target.value)}
          data-testid={`inv-total-${day.date}`}
        />
      </td>
      <td className="py-3">
        <Input
          className="w-24"
          type="number"
          value={capacityAvail}
          onChange={(e) => setCapacityAvail(e.target.value)}
          data-testid={`inv-avail-${day.date}`}
        />
      </td>
      <td className="py-3">
        <Input
          className="w-32"
          type="number"
          value={price}
          onChange={(e) => setPrice(e.target.value)}
          placeholder="(rate plan)"
          data-testid={`inv-price-${day.date}`}
        />
      </td>
      <td className="py-3">
        <input
          type="checkbox"
          checked={closed}
          onChange={(e) => setClosed(e.target.checked)}
          data-testid={`inv-closed-${day.date}`}
        />
      </td>
      <td className="py-3 text-right">
        <Button
          size="sm"
          className="gap-2"
          onClick={() =>
            onSave({
              date: day.date,
              capacity_total: capacityTotal,
              capacity_available: capacityAvail,
              price,
              closed,
            })
          }
          data-testid={`inv-save-${day.date}`}
        >
          <Save className="h-4 w-4" />
          Kaydet
        </Button>
      </td>
    </tr>
  );
}
