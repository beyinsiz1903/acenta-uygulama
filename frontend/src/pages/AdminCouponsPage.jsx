import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, apiErrorMessage } from "../lib/api";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Badge } from "../components/ui/badge";
import { Card } from "../components/ui/card";
import { AlertCircle, Loader2 } from "lucide-react";

function FieldError({ text }) {
  if (!text) return null;
  return (
    <div className="mt-2 flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/5 p-2 text-xs text-destructive">
      <AlertCircle className="h-4 w-4 mt-0.5" />
      <div>{text}</div>
    </div>
  );
}

export default function AdminCouponsPage() {
  const queryClient = useQueryClient();
  const [code, setCode] = useState("");
  const [discountType, setDiscountType] = useState("PERCENT");
  const [value, setValue] = useState("10");
  const [scope, setScope] = useState("BOTH");
  const [minTotal, setMinTotal] = useState("0");
  const [usageLimit, setUsageLimit] = useState("");
  const [perCustomerLimit, setPerCustomerLimit] = useState("");
  const [validFrom, setValidFrom] = useState("");
  const [validTo, setValidTo] = useState("");
  const [err, setErr] = useState("");

  const { data: items = [], isLoading: loading, refetch } = useQuery({
    queryKey: ["admin", "coupons"],
    queryFn: async () => {
      const res = await api.get("/admin/coupons");
      return res.data || [];
    },
    staleTime: 30_000,
  });

  const resetForm = () => {
    setCode("");
    setDiscountType("PERCENT");
    setValue("10");
    setScope("BOTH");
    setMinTotal("0");
    setUsageLimit("");
    setPerCustomerLimit("");
    setValidFrom("");
    setValidTo("");
  };

  const toISO = (value) => {
    if (!value) return null;
    // datetime-local -> ISO
    const d = new Date(value);
    if (Number.isNaN(d.getTime())) return null;
    return d.toISOString();
  };

  const createMutation = useMutation({
    mutationFn: (payload) => api.post("/admin/coupons", payload),
    onSuccess: () => {
      resetForm();
      queryClient.invalidateQueries({ queryKey: ["admin", "coupons"] });
    },
    onError: (e) => setErr(apiErrorMessage(e)),
  });

  const create = () => {
    setErr("");
    const payload = {
      code: code.trim().toUpperCase(),
      discount_type: discountType,
      value: Number(value) || 0,
      scope,
      min_total: Number(minTotal) || 0,
      usage_limit: usageLimit ? Number(usageLimit) : null,
      per_customer_limit: perCustomerLimit ? Number(perCustomerLimit) : null,
      valid_from: toISO(validFrom),
      valid_to: toISO(validTo),
      active: true,
    };

    if (!payload.valid_from || !payload.valid_to) {
      setErr("Geçerlilik başlangıç ve bitiş tarihleri zorunludur.");
      return;
    }

    createMutation.mutate(payload);
  };

  const toggleMutation = useMutation({
    mutationFn: ({ id, active }) => api.patch(`/admin/coupons/${id}`, { active }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin", "coupons"] }),
    onError: (e) => setErr(apiErrorMessage(e)),
  });

  const toggleActive = (coupon) => {
    setErr("");
    toggleMutation.mutate({ id: coupon.id, active: !coupon.active });
  };

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold">Kuponlar</h1>
        <p className="text-xs text-muted-foreground">
          B2B ve B2C kanalları için kupon ve kampanya kodlarını yönetin.
        </p>
      </div>

      <Card className="p-3 space-y-3 text-xs">
        <div className="flex items-center justify-between">
          <div className="text-sm font-semibold">Yeni Kupon</div>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <span>Alanlar:</span>
            <span>Kod, Tip, Değer, Kapsam, Min. Tutar, Limitler, Geçerlilik</span>
          </div>
        </div>

        <FieldError text={err} />

        <div className="grid grid-cols-1 md:grid-cols-4 gap-2">
          <div className="space-y-1">
            <Label className="text-xs">Kod</Label>
            <Input
              className="h-8 text-xs uppercase"
              value={code}
              onChange={(e) => setCode(e.target.value.toUpperCase())}
              placeholder="YAZ2025"
            />
          </div>
          <div className="space-y-1">
            <Label className="text-xs">İndirim Tipi</Label>
            <select
              className="h-8 w-full rounded-md border bg-background px-2 text-xs"
              value={discountType}
              onChange={(e) => setDiscountType(e.target.value)}
            >
              <option value="PERCENT">Yüzde (%)</option>
              <option value="AMOUNT">Sabit Tutar</option>
            </select>
          </div>
          <div className="space-y-1">
            <Label className="text-xs">Değer</Label>
            <Input
              type="number"
              className="h-8 text-xs"
              value={value}
              onChange={(e) => setValue(e.target.value)}
              placeholder="10"
            />
          </div>
          <div className="space-y-1">
            <Label className="text-xs">Kapsam</Label>
            <select
              className="h-8 w-full rounded-md border bg-background px-2 text-xs"
              value={scope}
              onChange={(e) => setScope(e.target.value)}
            >
              <option value="B2B">B2B</option>
              <option value="B2C">B2C</option>
              <option value="BOTH">Her ikisi</option>
            </select>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-2">
          <div className="space-y-1">
            <Label className="text-xs">Min. Tutar</Label>
            <Input
              type="number"
              className="h-8 text-xs"
              value={minTotal}
              onChange={(e) => setMinTotal(e.target.value)}
              placeholder="0"
            />
          </div>
          <div className="space-y-1">
            <Label className="text-xs">Toplam Kullanım Limiti</Label>
            <Input
              type="number"
              className="h-8 text-xs"
              value={usageLimit}
              onChange={(e) => setUsageLimit(e.target.value)}
              placeholder="Boş bırak = sınırsız"
            />
          </div>
          <div className="space-y-1">
            <Label className="text-xs">Kişi Başına Limit</Label>
            <Input
              type="number"
              className="h-8 text-xs"
              value={perCustomerLimit}
              onChange={(e) => setPerCustomerLimit(e.target.value)}
              placeholder="Boş bırak = sınırsız"
            />
          </div>
          <div className="space-y-1">
            <Label className="text-xs">Geçerlilik Başlangıç</Label>
            <Input
              type="datetime-local"
              className="h-8 text-xs"
              value={validFrom}
              onChange={(e) => setValidFrom(e.target.value)}
            />
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-2">
          <div className="space-y-1">
            <Label className="text-xs">Geçerlilik Bitiş</Label>
            <Input
              type="datetime-local"
              className="h-8 text-xs"
              value={validTo}
              onChange={(e) => setValidTo(e.target.value)}
            />
          </div>
        </div>

        <div className="flex justify-end">
          <Button size="sm" className="h-8 text-xs" onClick={create} disabled={createMutation.isPending}>
            {createMutation.isPending && <Loader2 className="h-3 w-3 mr-1 animate-spin" />}
            Kupon Oluştur
          </Button>
        </div>
      </Card>

      <Card className="p-3 space-y-2 text-xs">
        <div className="flex items-center justify-between">
          <div className="text-sm font-semibold">Mevcut Kuponlar</div>
          <Button size="sm" variant="outline" onClick={() => refetch()} disabled={loading}>
            {loading && <Loader2 className="h-3 w-3 mr-1 animate-spin" />}
            Yenile
          </Button>
        </div>

        <div className="mt-2 rounded-md border overflow-hidden">
          <div className="grid grid-cols-8 bg-muted/40 px-2 py-2 font-semibold">
            <div>Kod</div>
            <div>Tip</div>
            <div>Değer</div>
            <div>Scope</div>
            <div>Min. Tutar</div>
            <div>Kullanım</div>
            <div>Geçerlilik</div>
            <div>Durum</div>
          </div>
          <div className="max-h-72 overflow-y-auto">
            {items.map((c) => (
              <div key={c.id} className="grid grid-cols-8 border-t px-2 py-2 items-center">
                <div className="font-mono text-xs truncate" title={c.code}>
                  {c.code}
                </div>
                <div>{c.discount_type === "PERCENT" ? "%" : "₺"}</div>
                <div>{c.value}</div>
                <div>{c.scope}</div>
                <div>{c.min_total}</div>
                <div>
                  <span>
                    {c.usage_count || 0}
                    {c.usage_limit ? ` / ${c.usage_limit}` : ""}
                  </span>
                  {c.per_customer_limit && (
                    <span className="ml-1 text-2xs text-muted-foreground">(kişi: {c.per_customer_limit})</span>
                  )}
                </div>
                <div>
                  <div>{String(c.valid_from).slice(0, 16)}</div>
                  <div>{String(c.valid_to).slice(0, 16)}</div>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant={c.active ? "secondary" : "outline"}>{c.active ? "Aktif" : "Pasif"}</Badge>
                  <Button
                    size="xs"
                    variant="outline"
                    className="h-6 px-2 text-2xs"
                    onClick={() => toggleActive(c)}
                  >
                    {c.active ? "Pasifleştir" : "Aktifleştir"}
                  </Button>
                </div>
              </div>
            ))}
            {!items.length && !loading && (
              <div className="px-2 py-3 text-xs text-muted-foreground">Henüz kupon yok.</div>
            )}
          </div>
        </div>
      </Card>
    </div>
  );
}
