import React, { useEffect, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { AlertCircle, Building2, Loader2, ShieldOff } from "lucide-react";

import { api, apiErrorMessage } from "../lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table";
import { Input } from "../components/ui/input";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";

function ProductTypeBadge({ type }) {
  if (!type) return null;
  const t = String(type);
  if (t === "tour") return <Badge variant="secondary">Tur</Badge>;
  if (t === "hotel") return <Badge variant="outline">Otel</Badge>;
  return <Badge variant="outline">{t}</Badge>;
}

export default function AdminB2BAgencyProductsPage() {
  const queryClient = useQueryClient();
  const [searchParams] = useSearchParams();
  const agencyId = searchParams.get("agency_id") || "";
  const agencyName = searchParams.get("agency_name") || "";

  const [q, setQ] = useState("");
  const [savingId, setSavingId] = useState("");

  const { data: items = [], isLoading: loading, error: fetchError, refetch } = useQuery({
    queryKey: ["admin", "b2b", "agency-products", agencyId, q],
    queryFn: async () => {
      if (!agencyId) return [];
      const params = new URLSearchParams();
      params.set("limit", "100");
      if (q) params.set("q", q);
      const resp = await api.get(`/admin/b2b/visibility/agencies/${agencyId}/products?${params.toString()}`);
      return resp.data?.items || [];
    },
    staleTime: 30_000,
    enabled: !!agencyId,
  });
  const error = fetchError ? apiErrorMessage(fetchError) : "";

  const toggleMutation = useMutation({
    mutationFn: ({ productId, blocked }) => api.put(`/admin/b2b/visibility/agencies/${agencyId}/products/${productId}`, { blocked }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin", "b2b", "agency-products"] }),
    onError: (e) => alert(apiErrorMessage(e)),
    onSettled: () => setSavingId(""),
  });

  function toggleBlocked(productId, currentBlocked) {
    if (!agencyId) return;
    setSavingId(productId);
    toggleMutation.mutate({ productId, blocked: !currentBlocked });
  }

  const headerTitle = agencyName ? `${agencyName} – Ürün Erişimi` : "B2B Ürün Erişimi";

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold text-foreground">{headerTitle}</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Bu ekrandan ilgili acentenin hangi ürünleri B2C vitrinde/iframe içinde görebileceğini
          yönetebilirsiniz. Engellenen ürünler, partner parametresi ile gelen aramalarda listeden
          düşer ve public quote almaya çalıştığında bloklanır.
        </p>
        {agencyId && (
          <p className="mt-1 text-xs text-muted-foreground font-mono">Agency ID: {agencyId}</p>
        )}
      </div>

      {!agencyId && (
        <div className="rounded-2xl border bg-card shadow-sm p-8 flex flex-col items-center gap-3 text-center">
          <ShieldOff className="h-10 w-10 text-muted-foreground" />
          <p className="font-semibold text-foreground">Acenta seçilmedi</p>
          <p className="text-sm text-muted-foreground">
            Lütfen B2B Acenteler – Finans Özeti ekranından bir acentaya tıklayarak bu sayfaya gelin.
          </p>
        </div>
      )}

      {agencyId && (
        <Card>
          <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <CardTitle className="text-sm font-medium">Ürün listesi</CardTitle>
              <p className="text-xs text-muted-foreground mt-1">
                Aktif ürünler listelenir. Engelli durumuna aldığınız ürünler, ilgili bayi için
                public arama sonuçlarında görünmez.
              </p>
            </div>
            <div className="flex gap-2 items-center">
              <Input
                className="h-8 w-56 text-xs"
                placeholder="Ürün adı filtrele"
                value={q}
                onChange={(e) => setQ(e.target.value)}
              />
              <Button
                type="button"
                size="sm"
                variant="outline"
                className="text-xs"
                onClick={() => refetch()}
                disabled={loading}
              >
                {loading ? "Yükleniyor..." : "Yenile"}
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {loading && items.length === 0 ? (
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" /> Ürünler yükleniyor...
              </div>
            ) : error ? (
              <div className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
                <AlertCircle className="h-4 w-4 mt-0.5" />
                <div>{error}</div>
              </div>
            ) : items.length === 0 ? (
              <div className="rounded-2xl border bg-card shadow-sm p-12 flex flex-col items-center justify-center gap-4">
                <div className="h-16 w-16 rounded-full bg-muted flex items-center justify-center">
                  <Building2 className="h-8 w-8 text-muted-foreground" />
                </div>
                <div className="text-center max-w-md">
                  <p className="font-semibold text-foreground">Görüntülenecek ürün bulunamadı</p>
                  <p className="text-sm text-muted-foreground mt-2">
                    Katalogta hiç aktif ürün olmayabilir veya filtre çok dar olabilir.
                  </p>
                </div>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="text-xs">Ürün</TableHead>
                      <TableHead className="text-xs">Tür</TableHead>
                      <TableHead className="text-xs">Durum</TableHead>
                      <TableHead className="text-xs text-right">Bayi erişimi</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {items.map((it) => (
                      <TableRow key={it.id}>
                        <TableCell className="text-xs">
                          <div className="flex flex-col">
                            <span className="font-medium truncate max-w-[260px]">{it.title}</span>
                            <span className="text-xs text-muted-foreground font-mono">{it.id}</span>
                          </div>
                        </TableCell>
                        <TableCell className="text-xs">
                          <ProductTypeBadge type={it.type} />
                        </TableCell>
                        <TableCell className="text-xs">
                          {it.status === "active" ? (
                            <Badge className="bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/20">
                              Aktif
                            </Badge>
                          ) : (
                            <Badge variant="secondary">Pasif</Badge>
                          )}
                        </TableCell>
                        <TableCell className="text-xs text-right">
                          <Button
                            type="button"
                            size="sm"
                            variant={it.blocked ? "destructive" : "outline"}
                            className="text-xs px-3 py-1"
                            disabled={savingId === it.id}
                            onClick={() => toggleBlocked(it.id, it.blocked)}
                          >
                            {savingId === it.id
                              ? "Kaydediliyor..."
                              : it.blocked
                              ? "Engelli (aç)"
                              : "Erişilebilir (kapat)"}
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
